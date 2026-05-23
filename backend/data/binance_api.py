"""바이낸스 API — 가상자산 장기 OHLCV (API 키 불필요)"""
import time
import requests
import pandas as pd
from datetime import datetime, timedelta

BINANCE_BASE = "https://api.binance.com/api/v3"

# 업비트 심볼 → 바이낸스 심볼 변환
SYMBOL_MAP = {
    "KRW-BTC": "BTCUSDT",
    "KRW-ETH": "ETHUSDT",
    "KRW-XRP": "XRPUSDT",
    "KRW-SOL": "SOLUSDT",
    "KRW-ADA": "ADAUSDT",
    "KRW-DOGE": "DOGEUSDT",
    "KRW-DOT": "DOTUSDT",
}


def to_binance_symbol(symbol: str) -> str:
    """KRW-BTC → BTCUSDT 변환"""
    if symbol in SYMBOL_MAP:
        return SYMBOL_MAP[symbol]
    # 직접 입력 허용 (예: "BTCUSDT")
    return symbol


def get_crypto_ohlcv_long(
    symbol: str,
    days: int = 1095,  # 기본 3년
    interval: str = "1d",
) -> pd.DataFrame:
    """바이낸스 일봉 OHLCV 장기 조회 (최대 ~10년)

    Args:
        symbol: "KRW-BTC" 또는 "BTCUSDT"
        days: 조회 일수 (바이낸스 최대 1000개/요청 → 자동 페이징)
        interval: "1d"=일봉, "1w"=주봉

    Returns:
        DataFrame (date, open, high, low, close, volume) — 가격 단위: USDT
    """
    binance_symbol = to_binance_symbol(symbol)
    end_ms = int(datetime.now().timestamp() * 1000)
    start_ms = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)

    all_records = []
    current_start = start_ms
    limit = 1000  # 바이낸스 최대

    while current_start < end_ms:
        resp = requests.get(
            f"{BINANCE_BASE}/klines",
            params={
                "symbol": binance_symbol,
                "interval": interval,
                "startTime": current_start,
                "endTime": end_ms,
                "limit": limit,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        if not data:
            break

        for candle in data:
            all_records.append({
                "date": datetime.fromtimestamp(candle[0] / 1000),
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "volume": float(candle[5]),
            })

        # 마지막 캔들 다음 시간부터 재요청
        last_close_time = data[-1][6]
        current_start = last_close_time + 1

        if len(data) < limit:
            break

        time.sleep(0.1)  # API 레이트 리밋 방지

    df = pd.DataFrame(all_records)
    if df.empty:
        return df

    df = df.sort_values("date").reset_index(drop=True)
    return df
