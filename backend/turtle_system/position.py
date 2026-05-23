"""터틀 포지션 사이징 — ATR 기반 유닛 계산"""
import os

# 환율: KRW/USD (해외주식·가상자산 ATR이 USD 기준일 때 사용)
# .env 에서 KRW_USD_RATE=1380 형태로 오버라이드 가능
KRW_USD_RATE = float(os.getenv("KRW_USD_RATE", "1380"))


def calc_unit_size(
    account_balance: float,
    atr: float,
    price: float,
    risk_pct: float = 0.01,
    is_crypto: bool = False,
    fx_rate: float = 1.0,
) -> float:
    """1유닛 수량 계산

    공식: 유닛 = (계좌잔고 × 리스크%) ÷ ATR
    기본 리스크: 계좌의 1%

    Args:
        account_balance: 계좌 총 잔고 (국내=KRW, 해외/가상자산=KRW라도 fx_rate로 변환)
        atr: ATR(20) 값 (국내=KRW, 해외/가상자산=USD)
        price: 현재 가격
        risk_pct: 유닛당 리스크 비율 (기본 1%)
        is_crypto: True면 소수점 4자리 (BTC 0.0001단위), False면 정수 (주식)
        fx_rate: 계좌통화 → ATR통화 환율 (국내=1.0, 해외/가상자산=KRW_USD_RATE)
                 account_balance_in_atr_currency = account_balance / fx_rate

    Returns:
        매수 수량. 0이면 진입 불가.
    """
    if atr <= 0 or price <= 0:
        return 0

    # 계좌잔고를 ATR과 같은 통화 단위로 변환
    balance_in_atr_ccy = account_balance / fx_rate

    unit = (balance_in_atr_ccy * risk_pct) / atr

    if is_crypto:
        unit = round(unit, 4)  # 업비트 최소 단위
    else:
        unit = int(unit)       # 주식은 정수

    return unit


def calc_stop_loss(entry_price: float, atr: float, direction: str = "long") -> float:
    """손절가 계산 — 진입가 ± 2×ATR

    Args:
        direction: "long" or "short"
    """
    if direction == "long":
        return entry_price - 2 * atr
    return entry_price + 2 * atr


def calc_pyramid_prices(entry_price: float, atr: float, direction: str = "long") -> list[float]:
    """피라미딩 추가 진입가 계산 — 0.5 ATR 간격, 최대 4유닛

    Returns: [2차 진입가, 3차 진입가, 4차 진입가]
    """
    multiplier = 1 if direction == "long" else -1
    return [
        entry_price + multiplier * 0.5 * atr,
        entry_price + multiplier * 1.0 * atr,
        entry_price + multiplier * 1.5 * atr,
    ]


class TurtlePosition:
    """단일 포지션 상태 관리"""

    def __init__(self, symbol: str, direction: str, entry_price: float, atr: float, units: float):
        self.symbol = symbol
        self.direction = direction  # "long" / "short"
        self.entries: list[dict] = [{"price": entry_price, "units": units}]
        self.atr = atr
        self.stop_loss = calc_stop_loss(entry_price, atr, direction)
        self.pyramid_targets = calc_pyramid_prices(entry_price, atr, direction)
        self.total_units: float = units

    @property
    def avg_entry(self) -> float:
        total_cost = sum(e["price"] * e["units"] for e in self.entries)
        total_units = sum(e["units"] for e in self.entries)
        return total_cost / total_units if total_units > 0 else 0

    def can_pyramid(self) -> bool:
        return len(self.entries) < 4

    def add_unit(self, price: float, units: float):
        """피라미딩 추가"""
        if not self.can_pyramid():
            return
        self.entries.append({"price": price, "units": units})
        self.total_units += units
        # 손절가 갱신
        self.stop_loss = calc_stop_loss(price, self.atr, self.direction)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "entries": self.entries,
            "avg_entry": round(self.avg_entry, 4),
            "stop_loss": round(self.stop_loss, 4),
            "total_units": self.total_units,
            "pyramid_targets": [round(p, 4) for p in self.pyramid_targets],
        }
