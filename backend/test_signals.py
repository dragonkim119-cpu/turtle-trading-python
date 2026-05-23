"""국내주식 + 해외주식 터틀 신호 테스트"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from data.kis_api import get_domestic_ohlcv, get_overseas_ohlcv, get_account_balance
from turtle_system.signals import generate_signals
from turtle_system.indicators import calc_signals

DOMESTIC = [
    ("005930", "삼성전자"),
    ("000660", "SK하이닉스"),
    ("035420", "NAVER"),
    ("051910", "LG화학"),
    ("035720", "카카오"),
]

OVERSEAS = [
    ("AAPL", "NAS"),
    ("MSFT", "NAS"),
    ("NVDA", "NAS"),
    ("TSLA", "NAS"),
    ("AMZN", "NAS"),
]


def main():
    balance = get_account_balance()
    print(f"운용 계좌: {balance:,.0f}원\n")

    print("=== 국내주식 신호 스캔 ===")
    for code, name in DOMESTIC:
        try:
            df = get_domestic_ohlcv(code, days=100)
            df_sig = calc_signals(df)
            last = df_sig.iloc[-1]
            price = last["close"]
            atr = last["atr20"]
            s1_high = df["high"].shift(1).rolling(20).max().iloc[-1]
            s2_high = df["high"].shift(1).rolling(55).max().iloc[-1]
            signals = generate_signals(code, "domestic", df, balance)
            status = "★신호★" if signals else "신호없음"
            print(f"  [{name}] {status} | 현재:{price:,.0f} | "
                  f"S1돌파:{s1_high:,.0f} | S2돌파:{s2_high:,.0f} | ATR:{atr:,.0f}")
            for s in signals:
                print(f"    → System{s.system} {s.signal} 손절:{s.stop_loss:,.0f} 수량:{s.unit_size}주")
        except Exception as e:
            print(f"  [{name}] 오류: {e}")

    print("\n=== 해외주식 신호 스캔 ===")
    for symbol, exch in OVERSEAS:
        try:
            df = get_overseas_ohlcv(symbol, exch, days=100)
            df_sig = calc_signals(df)
            last = df_sig.iloc[-1]
            price = last["close"]
            atr = last["atr20"]
            s1_high = df["high"].shift(1).rolling(20).max().iloc[-1]
            s2_high = df["high"].shift(1).rolling(55).max().iloc[-1]
            signals = generate_signals(symbol, "overseas", df, balance)
            status = "★신호★" if signals else "신호없음"
            print(f"  [{symbol}] {status} | 현재:{price:.2f} | "
                  f"S1돌파:{s1_high:.2f} | S2돌파:{s2_high:.2f} | ATR:{atr:.2f}")
            for s in signals:
                print(f"    → System{s.system} {s.signal} 손절:{s.stop_loss:.2f} 수량:{s.unit_size}주")
        except Exception as e:
            print(f"  [{symbol}] 오류: {e}")


if __name__ == "__main__":
    main()
