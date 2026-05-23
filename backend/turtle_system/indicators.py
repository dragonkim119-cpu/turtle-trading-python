"""터틀 트레이딩 핵심 지표 계산"""
import pandas as pd
import numpy as np


def calc_atr(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Average True Range 계산"""
    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return true_range.rolling(window=period).mean()


def calc_donchian(df: pd.DataFrame, period: int) -> tuple[pd.Series, pd.Series]:
    """도나치안 채널 (고가/저가 채널) 계산
    Returns: (upper_channel, lower_channel)
    """
    upper = df["high"].rolling(window=period).max()
    lower = df["low"].rolling(window=period).min()
    return upper, lower


def calc_signals(df: pd.DataFrame) -> pd.DataFrame:
    """터틀 System 1, System 2 신호 계산

    System 1: 20일 돌파 진입 / 10일 청산
    System 2: 55일 돌파 진입 / 20일 청산
    """
    df = df.copy()

    # ATR
    df.loc[:, "atr20"] = calc_atr(df, 20)

    # System 1
    s1_upper, s1_lower_exit = calc_donchian(df.shift(1), 20)  # 전일 기준
    s1_exit_upper, s1_exit_lower = calc_donchian(df.shift(1), 10)
    df.loc[:, "s1_entry_long"] = df["close"] > s1_upper
    df.loc[:, "s1_entry_short"] = df["close"] < s1_lower_exit
    df.loc[:, "s1_exit_long"] = df["close"] < s1_exit_lower
    df.loc[:, "s1_exit_short"] = df["close"] > s1_exit_upper

    # System 2
    s2_upper, s2_lower = calc_donchian(df.shift(1), 55)
    s2_exit_upper, s2_exit_lower = calc_donchian(df.shift(1), 20)
    df.loc[:, "s2_entry_long"] = df["close"] > s2_upper
    df.loc[:, "s2_entry_short"] = df["close"] < s2_lower
    df.loc[:, "s2_exit_long"] = df["close"] < s2_exit_lower
    df.loc[:, "s2_exit_short"] = df["close"] > s2_exit_upper

    return df
