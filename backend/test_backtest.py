"""바이낸스 장기 데이터로 백테스트 — 3년치"""
from data.binance_api import get_crypto_ohlcv_long
from turtle_system.backtest import run_backtest
from turtle_system.signals import generate_signals
from turtle_system.indicators import calc_atr


TESTS = [
    {"symbol": "KRW-BTC",  "balance": 500_000_000, "label": "BTC  (5억)"},
    {"symbol": "KRW-ETH",  "balance": 50_000_000,  "label": "ETH  (5천만)"},
    {"symbol": "KRW-XRP",  "balance": 10_000_000,  "label": "XRP  (1천만)"},
    {"symbol": "KRW-SOL",  "balance": 30_000_000,  "label": "SOL  (3천만)"},
]

YEARS = 3
DAYS = YEARS * 365


def run_test(cfg: dict):
    symbol = cfg["symbol"]
    balance = cfg["balance"]

    print(f"\n{'='*55}")
    print(f"종목: {cfg['label']}  |  기간: {YEARS}년")
    print(f"바이낸스 데이터 조회 중...", end=" ", flush=True)

    df = get_crypto_ohlcv_long(symbol, days=DAYS)
    print(f"{len(df)}일치 로드 ({df['date'].iloc[0].strftime('%Y-%m-%d')} ~ {df['date'].iloc[-1].strftime('%Y-%m-%d')})")

    atr = calc_atr(df, 20).iloc[-1]
    print(f"현재 ATR(20): {atr:,.4f} USDT  |  최소 권장 계좌: {atr/0.01:,.0f} USDT 상당")

    for system in [1, 2]:
        result = run_backtest(symbol, df, system=system, initial_balance=balance, is_crypto=True)
        s = result.summary()
        print(
            f"  System {system} │ 거래:{s['total_trades']:>3}건 │ "
            f"수익률:{s['total_return_pct']:>7.2f}% │ "
            f"승률:{s['win_rate']:>5.1f}% │ "
            f"MDD:{s['max_drawdown_pct']:>7.2f}%"
        )

    # 현재 신호 (실시간)
    signals = generate_signals(symbol, "crypto", df, account_balance=balance)
    if signals:
        print(f"\n  현재 신호 {len(signals)}개:")
        for s in signals:
            print(f"    System {s.system} | {s.signal:12} | "
                  f"가격: {s.price:>10.2f} | ATR: {s.atr:>8.2f} | "
                  f"손절: {s.stop_loss:>10.2f} | 수량: {s.unit_size}")
    else:
        print("  현재 신호: 없음")


def main():
    print("바이낸스 API 3년 백테스트 시작 (API 키 불필요)")
    for cfg in TESTS:
        run_test(cfg)
    print(f"\n{'='*55}")
    print("완료")


if __name__ == "__main__":
    main()
