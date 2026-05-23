"""터틀 트레이딩 백테스트 엔진"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field

from .indicators import calc_signals
from .position import calc_unit_size, calc_stop_loss


@dataclass
class Trade:
    symbol: str
    system: int
    direction: str
    entry_date: str
    entry_price: float
    exit_date: str = ""
    exit_price: float = 0.0
    units: int = 0
    pnl: float = 0.0
    pnl_pct: float = 0.0


@dataclass
class BacktestResult:
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)
    initial_balance: float = 10_000_000
    final_balance: float = 0.0

    @property
    def total_trades(self) -> int:
        return len(self.trades)

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        wins = sum(1 for t in self.trades if t.pnl > 0)
        return wins / len(self.trades)

    @property
    def total_return_pct(self) -> float:
        return (self.final_balance - self.initial_balance) / self.initial_balance * 100

    @property
    def max_drawdown(self) -> float:
        if not self.equity_curve:
            return 0.0
        equity = pd.Series(self.equity_curve)
        rolling_max = equity.cummax()
        drawdown = (equity - rolling_max) / rolling_max
        return float(drawdown.min() * 100)

    def summary(self) -> dict:
        return {
            "initial_balance": self.initial_balance,
            "final_balance": round(self.final_balance, 0),
            "total_return_pct": round(self.total_return_pct, 2),
            "total_trades": self.total_trades,
            "win_rate": round(self.win_rate * 100, 1),
            "max_drawdown_pct": round(self.max_drawdown, 2),
            "avg_pnl": round(np.mean([t.pnl for t in self.trades]), 0) if self.trades else 0,
        }


def run_backtest(
    symbol: str,
    df: pd.DataFrame,
    system: int = 1,
    initial_balance: float = 10_000_000,
    is_crypto: bool = False,
) -> BacktestResult:
    """단일 종목 터틀 백테스트

    Args:
        symbol: 종목코드
        df: OHLCV DataFrame
        system: 1 (20일) or 2 (55일)
        initial_balance: 초기 자본

    Returns:
        BacktestResult
    """
    df = calc_signals(df.copy())
    result = BacktestResult(initial_balance=initial_balance)
    balance = initial_balance
    result.equity_curve.append(balance)

    prefix = f"s{system}"
    position = None  # 현재 보유 포지션

    for i, row in df.iterrows():
        if pd.isna(row.get("atr20", None)) or row["atr20"] == 0:
            continue

        price = row["close"]
        atr = row["atr20"]
        date = str(row.get("date", i))[:10]

        # 포지션 없음 → 진입 신호 체크
        if position is None:
            if row.get(f"{prefix}_entry_long", False):
                units = calc_unit_size(balance, atr, price, is_crypto=is_crypto)
                if units == 0:
                    continue  # 계좌 대비 변동성 너무 큼 — 진입 불가
                stop = calc_stop_loss(price, atr, "long")
                position = {
                    "direction": "long",
                    "entry_date": date,
                    "entry_price": price,
                    "units": units,
                    "stop": stop,
                    "atr": atr,
                }

        # 포지션 있음 → 청산/손절 체크
        elif position:
            direction = position["direction"]
            exit_triggered = False
            exit_price = price

            # 손절
            if direction == "long" and price <= position["stop"]:
                exit_triggered = True
            # 채널 청산
            elif direction == "long" and row.get(f"{prefix}_exit_long", False):
                exit_triggered = True

            if exit_triggered:
                pnl = (exit_price - position["entry_price"]) * position["units"]
                pnl_pct = (exit_price - position["entry_price"]) / position["entry_price"] * 100
                balance += pnl

                result.trades.append(Trade(
                    symbol=symbol,
                    system=system,
                    direction=direction,
                    entry_date=position["entry_date"],
                    entry_price=position["entry_price"],
                    exit_date=date,
                    exit_price=exit_price,
                    units=position["units"],
                    pnl=round(pnl, 0),
                    pnl_pct=round(pnl_pct, 2),
                ))
                position = None

        result.equity_curve.append(balance)

    result.final_balance = balance
    return result
