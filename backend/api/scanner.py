"""전종목 터틀 신호 스캔 — 장 마감 후 실행"""
import json
import os
import tempfile
from datetime import datetime

from data.kis_api import (
    get_domestic_ohlcv, get_overseas_ohlcv, get_account_balance,
    get_domestic_current_price, get_overseas_current_price,
)
from data.binance_api import get_crypto_ohlcv_long
from turtle_system.signals import generate_signals
from .fcm import send_notification

# 모니터링 종목 리스트 (커스텀 가능)
DOMESTIC_WATCHLIST = [
    "005930",  # 삼성전자
    "000660",  # SK하이닉스
    "035420",  # NAVER
    "051910",  # LG화학
    "006400",  # 삼성SDI
    "035720",  # 카카오
    "207940",  # 삼성바이오로직스
    "068270",  # 셀트리온
]

OVERSEAS_WATCHLIST = [
    {"symbol": "AAPL", "exchange": "NAS"},
    {"symbol": "MSFT", "exchange": "NAS"},
    {"symbol": "NVDA", "exchange": "NAS"},
    {"symbol": "TSLA", "exchange": "NAS"},
    {"symbol": "AMZN", "exchange": "NAS"},
    {"symbol": "GOOGL", "exchange": "NAS"},
    {"symbol": "META", "exchange": "NAS"},
]

CRYPTO_WATCHLIST = [
    "KRW-BTC",
    "KRW-ETH",
    "KRW-XRP",
    "KRW-SOL",
    "KRW-ADA",
]

SIGNALS_CACHE_PATH = os.path.join(os.path.dirname(__file__), "../data/signals_cache.json")


def run_full_scan() -> list[dict]:
    """전 종목 터틀 신호 스캔 후 캐시 저장"""
    print(f"[{datetime.now()}] 터틀 스캔 시작...")

    try:
        balance = get_account_balance()
    except Exception:
        balance = 10_000_000  # API 오류 시 기본값

    all_signals = []

    # 국내주식 스캔
    for symbol in DOMESTIC_WATCHLIST:
        try:
            df = get_domestic_ohlcv(symbol, days=100)
            if df.empty:
                continue
            cur_price = get_domestic_current_price(symbol)
            signals = generate_signals(symbol, "domestic", df, balance, current_price=cur_price)
            all_signals.extend([s.to_dict() for s in signals])
        except Exception as e:
            print(f"[WARN] {symbol} 국내주식 오류: {e}")

    # 해외주식 스캔
    for item in OVERSEAS_WATCHLIST:
        try:
            df = get_overseas_ohlcv(item["symbol"], item["exchange"], days=100)
            if df.empty:
                continue
            cur_price = get_overseas_current_price(item["symbol"], item["exchange"])
            signals = generate_signals(item["symbol"], "overseas", df, balance, current_price=cur_price)
            all_signals.extend([s.to_dict() for s in signals])
        except Exception as e:
            print(f"[WARN] {item['symbol']} 해외주식 오류: {e}")

    # 가상자산 스캔 (Binance USD 기준 — fx_rate 환율 적용)
    # 오늘 미완성 캔들의 close = 현재 실시간 가격 (Binance mark price)
    for symbol in CRYPTO_WATCHLIST:
        try:
            df = get_crypto_ohlcv_long(symbol, days=100)
            if df.empty:
                continue
            signals = generate_signals(symbol, "crypto", df, balance)
            all_signals.extend([s.to_dict() for s in signals])
        except Exception as e:
            print(f"[WARN] {symbol} 가상자산 오류: {e}")

    # 캐시 저장 (atomic write — 읽는 중 손상 방지)
    cache_dir = os.path.dirname(SIGNALS_CACHE_PATH)
    os.makedirs(cache_dir, exist_ok=True)
    payload = json.dumps(
        {"updated_at": datetime.now().isoformat(), "signals": all_signals},
        ensure_ascii=False, indent=2
    )
    fd, tmp_path = tempfile.mkstemp(dir=cache_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp_path, SIGNALS_CACHE_PATH)  # atomic on same filesystem
    except Exception:
        os.unlink(tmp_path)
        raise

    print(f"[{datetime.now()}] 스캔 완료 — 신호 {len(all_signals)}개")

    # 진입 신호 있으면 푸시 알림 발송
    entry_signals = [s for s in all_signals if 'entry' in s['signal']]
    if entry_signals:
        symbols = list({s['symbol'] for s in entry_signals})
        direction_map = {'entry_long': '매수', 'entry_short': '매도'}
        details = [
            f"{s['symbol']} {direction_map.get(s['signal'], s['signal'])} (S{s['system']})"
            for s in entry_signals[:3]
        ]
        body = ', '.join(details)
        if len(entry_signals) > 3:
            body += f' 외 {len(entry_signals) - 3}개'
        send_notification('🐢 터틀 매매 신호 발생', body)

    return all_signals


def get_cached_signals() -> dict:
    """캐시된 신호 조회"""
    if not os.path.exists(SIGNALS_CACHE_PATH):
        return {"updated_at": None, "signals": []}
    with open(SIGNALS_CACHE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
