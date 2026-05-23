"""업비트 API 연동 — 가상자산 OHLCV"""
import os
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../config/.env"))

UPBIT_BASE = "https://api.upbit.com/v1"


def get_crypto_ohlcv(symbol: str = "KRW-BTC", days: int = 100) -> pd.DataFrame:
    """업비트 일봉 OHLCV 조회

    Args:
        symbol: 마켓코드 (예: "KRW-BTC", "KRW-ETH", "KRW-XRP")
        days: 조회 일수 (최대 200)

    Returns:
        DataFrame (date, open, high, low, close, volume)
    """
    count = min(days, 200)
    resp = requests.get(
        f"{UPBIT_BASE}/candles/days",
        params={
            "market": symbol,
            "count": count,
        },
        headers={"Accept": "application/json"},
    )
    resp.raise_for_status()
    raw = resp.json()

    records = []
    for item in raw:
        records.append({
            "date": item["candle_date_time_kst"][:10],
            "open": float(item["opening_price"]),
            "high": float(item["high_price"]),
            "low": float(item["low_price"]),
            "close": float(item["trade_price"]),
            "volume": float(item["candle_acc_trade_volume"]),
        })

    df = pd.DataFrame(records)
    if df.empty:
        return df
    df = df.sort_values("date").reset_index(drop=True)
    df.loc[:, "date"] = pd.to_datetime(df["date"])
    return df


def get_available_markets() -> list[str]:
    """KRW 마켓 전체 종목 코드 조회"""
    resp = requests.get(f"{UPBIT_BASE}/market/all", params={"isDetails": False})
    resp.raise_for_status()
    markets = resp.json()
    return [m["market"] for m in markets if m["market"].startswith("KRW-")]
