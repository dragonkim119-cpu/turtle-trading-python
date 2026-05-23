"""전종목 터틀 신호 스캔 — 장 마감 후 실행"""
import json
import os
from datetime import datetime

from data.kis_api import get_domestic_ohlcv, get_overseas_ohlcv, get_account_balance
from data.upbit_api import get_crypto_ohlcv
from turtle_system.signals import generate_signals

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
            signals = generate_signals(symbol, "domestic", df, balance)
            all_signals.extend([s.to_dict() for s in signals])
        except Exception as e:
            print(f"[WARN] {symbol} 국내주식 오류: {e}")

    # 해외주식 스캔
    for item in OVERSEAS_WATCHLIST:
        try:
            df = get_overseas_ohlcv(item["symbol"], item["exchange"], days=100)
            if df.empty:
                continue
            signals = generate_signals(item["symbol"], "overseas", df, balance)
            all_signals.extend([s.to_dict() for s in signals])
        except Exception as e:
            print(f"[WARN] {item['symbol']} 해외주식 오류: {e}")

    # 가상자산 스캔
    for symbol in CRYPTO_WATCHLIST:
        try:
            df = get_crypto_ohlcv(symbol, days=100)
            if df.empty:
                continue
            signals = generate_signals(symbol, "crypto", df, balance)
            all_signals.extend([s.to_dict() for s in signals])
        except Exception as e:
            print(f"[WARN] {symbol} 가상자산 오류: {e}")

    # 캐시 저장
    os.makedirs(os.path.dirname(SIGNALS_CACHE_PATH), exist_ok=True)
    with open(SIGNALS_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"updated_at": datetime.now().isoformat(), "signals": all_signals}, f, ensure_ascii=False, indent=2)

    print(f"[{datetime.now()}] 스캔 완료 — 신호 {len(all_signals)}개")
    return all_signals


def get_cached_signals() -> dict:
    """캐시된 신호 조회"""
    if not os.path.exists(SIGNALS_CACHE_PATH):
        return {"updated_at": None, "signals": []}
    with open(SIGNALS_CACHE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
