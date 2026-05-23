"""한국투자증권 KIS API 연동 — 국내주식 + 해외주식 OHLCV"""
import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../config/.env"))

APP_KEY = os.getenv("KIS_APP_KEY", "")
APP_SECRET = os.getenv("KIS_APP_SECRET", "")
ACCOUNT_NO = os.getenv("KIS_ACCOUNT_NO", "")
IS_REAL = os.getenv("KIS_IS_REAL", "false").lower() == "true"
DEFAULT_BALANCE = float(os.getenv("DEFAULT_BALANCE", "100000000"))

BASE_URL = "https://openapi.koreainvestment.com:9443" if IS_REAL else "https://openapivts.koreainvestment.com:29443"

_token_cache: dict = {}


def _clear_token() -> None:
    """토큰 캐시 초기화 (401 수신 시 호출)"""
    _token_cache.clear()


def get_access_token() -> str:
    """액세스 토큰 발급 (캐시 사용)"""
    now = datetime.now()
    if _token_cache.get("expires_at") and _token_cache["expires_at"] > now:
        return _token_cache["token"]

    resp = requests.post(
        f"{BASE_URL}/oauth2/tokenP",
        json={
            "grant_type": "client_credentials",
            "appkey": APP_KEY,
            "appsecret": APP_SECRET,
        },
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = now + timedelta(hours=23)
    return _token_cache["token"]


def _headers(tr_id: str) -> dict:
    # KIS API 필수 구조: appkey/appsecret 매 요청 헤더 포함
    # 로그/프록시 노출 위험 → BASE_URL이 반드시 HTTPS여야 함 (현재 설정 확인됨)
    return {
        "content-type": "application/json",
        "authorization": f"Bearer {get_access_token()}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": tr_id,
    }


def _get(url: str, tr_id: str, params: dict) -> dict:
    """GET 요청 + 401 시 토큰 갱신 후 1회 재시도"""
    resp = requests.get(url, headers=_headers(tr_id), params=params)
    if resp.status_code == 401:
        _clear_token()
        resp = requests.get(url, headers=_headers(tr_id), params=params)
    resp.raise_for_status()
    return resp.json()


def get_domestic_ohlcv(symbol: str, days: int = 100) -> pd.DataFrame:
    """국내주식 일봉 OHLCV 조회

    Args:
        symbol: 종목코드 (예: "005930" = 삼성전자)
        days: 조회 일수

    Returns:
        DataFrame (date, open, high, low, close, volume)
    """
    # KIS inquire-daily-itemchartprice 엔드포인트 — 최대 100건/요청, 페이지네이션
    all_records = []
    end_date = datetime.now()

    while len(all_records) < days:
        end_str = end_date.strftime("%Y%m%d")
        start_str = (end_date - timedelta(days=120)).strftime("%Y%m%d")

        data = _get(
            f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
            "FHKST03010100",
            {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": symbol,
                "FID_INPUT_DATE_1": start_str,
                "FID_INPUT_DATE_2": end_str,
                "FID_PERIOD_DIV_CODE": "D",
                "FID_ORG_ADJ_PRC": "0",
            },
        )
        raw = data.get("output2", [])
        if not raw:
            break

        for item in raw:
            if not item.get("stck_bsop_date"):
                continue
            all_records.append({
                "date": item["stck_bsop_date"],
                "open": float(item.get("stck_oprc") or 0),
                "high": float(item.get("stck_hgpr") or 0),
                "low": float(item.get("stck_lwpr") or 0),
                "close": float(item.get("stck_clpr") or 0),
                "volume": float(item.get("acml_vol") or 0),
            })

        # 다음 페이지: 조회 기간 앞으로 이동
        end_date = end_date - timedelta(days=120)
        if len(raw) < 10:  # 데이터 소진
            break

    df = pd.DataFrame(all_records)
    if df.empty:
        return df
    df = df.drop_duplicates(subset=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df.loc[:, "date"] = pd.to_datetime(df["date"])
    return df.tail(days)


def get_overseas_ohlcv(symbol: str, exchange: str = "NAS", days: int = 100) -> pd.DataFrame:
    """해외주식 일봉 OHLCV 조회

    Args:
        symbol: 종목코드 (예: "AAPL")
        exchange: 거래소코드 ("NAS"=나스닥, "NYS"=뉴욕, "TSE"=도쿄)
        days: 조회 일수
    """
    end = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")

    data = _get(
        f"{BASE_URL}/uapi/overseas-price/v1/quotations/dailyprice",
        "HHDFS76240000",
        {
            "AUTH": "",
            "EXCD": exchange,
            "SYMB": symbol,
            "GUBN": "0",  # 0=일, 1=주, 2=월
            "BYMD": end,
            "MODP": "0",
        },
    )
    raw = data.get("output2", [])

    records = []
    for item in raw:
        if not item.get("xymd"):
            continue
        records.append({
            "date": item["xymd"],
            "open": float(item["open"] or 0),
            "high": float(item["high"] or 0),
            "low": float(item["low"] or 0),
            "close": float(item["clos"] or 0),
            "volume": float(item["tvol"] or 0),
        })

    df = pd.DataFrame(records)
    if df.empty:
        return df
    df = df.sort_values("date").reset_index(drop=True)
    df.loc[:, "date"] = pd.to_datetime(df["date"])
    return df.tail(days)


def get_domestic_current_price(symbol: str) -> float:
    """국내주식 현재가 조회"""
    try:
        data = _get(
            f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price",
            "FHKST01010100",
            {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": symbol},
        )
        price = float(data.get("output", {}).get("stck_prpr") or 0)
        return price if price > 0 else 0.0
    except Exception:
        return 0.0


def get_overseas_current_price(symbol: str, exchange: str = "NAS") -> float:
    """해외주식 현재가 조회"""
    try:
        data = _get(
            f"{BASE_URL}/uapi/overseas-price/v1/quotations/price",
            "HHDFS00000300",
            {"AUTH": "", "EXCD": exchange, "SYMB": symbol},
        )
        price = float(data.get("output", {}).get("last") or 0)
        return price if price > 0 else 0.0
    except Exception:
        return 0.0


def get_account_balance() -> float:
    """계좌 예수금 조회. 실패 시 DEFAULT_BALANCE 반환 (모의투자 미지원)."""
    if not IS_REAL:
        return DEFAULT_BALANCE

    cano = ACCOUNT_NO.split("-")[0]
    acnt_cd = ACCOUNT_NO.split("-")[1] if "-" in ACCOUNT_NO else "01"

    try:
        resp_data = _get(
            f"{BASE_URL}/uapi/domestic-stock/v1/trading/inquire-balance",
            "TTTC8434R",
            {
                "CANO": cano,
                "ACNT_PRDT_CD": acnt_cd,
                "AFHR_FLPR_YN": "N",
                "OFL_YN": "N",
                "INQR_DVSN": "02",
                "UNPR_DVSN": "01",
                "FUND_STTL_ICLD_YN": "N",
                "FNCG_AMT_AUTO_RDPT_YN": "N",
                "PRCS_DVSN": "01",
                "CTX_AREA_FK100": "",
                "CTX_AREA_NK100": "",
            },
        )
        data = resp_data.get("output2", {})
        if isinstance(data, list):
            data = data[0] if data else {}
        balance = float(data.get("dnca_tot_amt", 0))
        return balance if balance > 0 else DEFAULT_BALANCE
    except Exception:
        return DEFAULT_BALANCE
