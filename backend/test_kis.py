"""KIS API 연결 테스트"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from data.kis_api import get_access_token, get_domestic_ohlcv, get_overseas_ohlcv, get_account_balance


def main():
    print("1. 액세스 토큰 발급...")
    try:
        token = get_access_token()
        print(f"   OK — 토큰: {token[:20]}...")
    except Exception as e:
        print(f"   FAIL — {e}")
        return

    print("\n2. 삼성전자 일봉 조회...")
    try:
        df = get_domestic_ohlcv("005930", days=10)
        print(f"   OK — {len(df)}일치")
        print(df.tail(3).to_string(index=False))
    except Exception as e:
        print(f"   FAIL — {e}")

    print("\n3. AAPL 해외주식 조회...")
    try:
        df = get_overseas_ohlcv("AAPL", "NAS", days=10)
        print(f"   OK — {len(df)}일치")
        print(df.tail(3).to_string(index=False))
    except Exception as e:
        print(f"   FAIL — {e}")

    print("\n4. 계좌 잔고 조회...")
    try:
        balance = get_account_balance()
        print(f"   OK — 주문가능금액: {balance:,.0f}원")
    except Exception as e:
        print(f"   FAIL — {e}")


if __name__ == "__main__":
    main()
