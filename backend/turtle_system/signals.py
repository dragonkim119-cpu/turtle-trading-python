"""터틀 트레이딩 신호 생성 — 종목별 매수/매도 신호"""
import logging
from dataclasses import dataclass
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

from .indicators import calc_signals
from .position import calc_unit_size, calc_stop_loss, calc_pyramid_prices, KRW_USD_RATE


@dataclass
class TurtleSignal:
    symbol: str
    asset_type: str        # "domestic", "overseas", "crypto"
    system: int            # 1 or 2
    signal: str            # "entry_long", "entry_short", "exit_long", "exit_short", "pyramid"
    price: float
    atr: float
    stop_loss: float
    unit_size: int
    pyramid_targets: list[float]
    generated_at: datetime

    @property
    def isEntry(self) -> bool:
        return self.signal.startswith("entry")

    @property
    def isLong(self) -> bool:
        return "long" in self.signal

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "asset_type": self.asset_type,
            "system": self.system,
            "signal": self.signal,
            "price": self.price,
            "atr": round(self.atr, 4),
            "stop_loss": round(self.stop_loss, 4),
            "unit_size": self.unit_size,
            "pyramid_targets": [round(p, 4) for p in self.pyramid_targets],
            "generated_at": self.generated_at.isoformat(),
        }


def generate_signals(
    symbol: str,
    asset_type: str,
    df: pd.DataFrame,
    account_balance: float = 10_000_000,
) -> list[TurtleSignal]:
    """OHLCV 데이터로 터틀 신호 생성

    Args:
        symbol: 종목코드 (예: "005930", "AAPL", "KRW-BTC")
        asset_type: "domestic" | "overseas" | "crypto"
        df: OHLCV DataFrame (columns: open, high, low, close, volume)
        account_balance: 계좌잔고 (포지션 사이징용)

    Returns:
        신호 리스트 (없으면 빈 리스트)
    """
    if len(df) < 60:
        return []

    df = calc_signals(df)
    latest = df.iloc[-1]
    signals = []
    now = datetime.now()

    atr = latest.get("atr20", 0)
    if atr == 0 or pd.isna(atr):
        return []

    price = latest["close"]
    is_crypto = asset_type == "crypto"
    # 해외주식·가상자산(Binance)은 ATR이 USD → 계좌잔고(KRW)를 USD로 환산
    fx = KRW_USD_RATE if asset_type in ("overseas", "crypto") else 1.0
    unit_size = calc_unit_size(account_balance, atr, price, is_crypto=is_crypto, fx_rate=fx)

    for system in [1, 2]:
        prefix = f"s{system}"

        # 롱 진입
        if latest.get(f"{prefix}_entry_long", False):
            signals.append(TurtleSignal(
                symbol=symbol,
                asset_type=asset_type,
                system=system,
                signal="entry_long",
                price=price,
                atr=atr,
                stop_loss=calc_stop_loss(price, atr, "long"),
                unit_size=unit_size,
                pyramid_targets=calc_pyramid_prices(price, atr, "long"),
                generated_at=now,
            ))

        # 숏 진입 (가상자산/해외주식만)
        elif latest.get(f"{prefix}_entry_short", False) and asset_type == "domestic":
            logger.debug("[%s] System%d 숏 신호 감지 — 국내주식 숏 거래 불가, 건너뜀", symbol, system)
        elif latest.get(f"{prefix}_entry_short", False):
            signals.append(TurtleSignal(
                symbol=symbol,
                asset_type=asset_type,
                system=system,
                signal="entry_short",
                price=price,
                atr=atr,
                stop_loss=calc_stop_loss(price, atr, "short"),
                unit_size=unit_size,
                pyramid_targets=calc_pyramid_prices(price, atr, "short"),
                generated_at=now,
            ))

        # 청산 신호
        elif latest.get(f"{prefix}_exit_long", False):
            signals.append(TurtleSignal(
                symbol=symbol, asset_type=asset_type, system=system,
                signal="exit_long", price=price, atr=atr,
                stop_loss=0, unit_size=0, pyramid_targets=[],
                generated_at=now,
            ))
        elif latest.get(f"{prefix}_exit_short", False):
            signals.append(TurtleSignal(
                symbol=symbol, asset_type=asset_type, system=system,
                signal="exit_short", price=price, atr=atr,
                stop_loss=0, unit_size=0, pyramid_targets=[],
                generated_at=now,
            ))

    return signals
