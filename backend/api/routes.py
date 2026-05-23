"""API 라우트 정의"""
import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List

logger = logging.getLogger(__name__)

from .scanner import run_full_scan, get_cached_signals
from .fcm import save_token
from data.kis_api import (
    get_domestic_ohlcv, get_overseas_ohlcv,
    get_domestic_current_price, get_overseas_current_price,
)
from data.binance_api import get_crypto_ohlcv_long
from turtle_system.signals import generate_signals

router = APIRouter()


# ── FCM 토큰 등록 ─────────────────────────────────────────


class DeviceTokenRequest(BaseModel):
    token: str


@router.post("/device/token")
def register_device_token(req: DeviceTokenRequest):
    """앱에서 FCM 토큰 등록/갱신"""
    save_token(req.token)
    return {"message": "토큰 등록 완료"}


# ── 신호 조회 ────────────────────────────────────────────


@router.get("/signals")
def get_signals(
    asset_type: str = Query(None, description="domestic | overseas | crypto"),
    signal_type: str = Query(None, description="entry_long | entry_short | exit_long | exit_short"),
):
    """캐시된 신호 목록 조회"""
    data = get_cached_signals()
    signals = data.get("signals", [])

    if asset_type:
        signals = [s for s in signals if s["asset_type"] == asset_type]
    if signal_type:
        signals = [s for s in signals if s["signal"] == signal_type]

    return {
        "updated_at": data.get("updated_at"),
        "count": len(signals),
        "signals": signals,
    }


@router.post("/signals/scan")
def trigger_scan():
    """수동 스캔 실행 (즉시)"""
    signals = run_full_scan()
    return {"message": "스캔 완료", "count": len(signals)}


# ── 단일 종목 신호 ────────────────────────────────────────


class SingleScanRequest(BaseModel):
    symbol: str
    asset_type: str          # domestic | overseas | crypto
    exchange: str = "NAS"    # 해외주식 거래소코드
    account_balance: float = 10_000_000


@router.post("/signals/single")
def scan_single(req: SingleScanRequest):
    """단일 종목 즉시 신호 조회"""
    cur_price = 0.0
    try:
        if req.asset_type == "domestic":
            df = get_domestic_ohlcv(req.symbol, days=100)
            cur_price = get_domestic_current_price(req.symbol)
        elif req.asset_type == "overseas":
            df = get_overseas_ohlcv(req.symbol, req.exchange, days=100)
            cur_price = get_overseas_current_price(req.symbol, req.exchange)
        elif req.asset_type == "crypto":
            df = get_crypto_ohlcv_long(req.symbol, days=100)
        else:
            raise HTTPException(status_code=400, detail="asset_type 오류: domestic | overseas | crypto")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 조회 실패: {e}")

    if df.empty:
        raise HTTPException(status_code=404, detail="데이터 없음")

    signals = generate_signals(req.symbol, req.asset_type, df, req.account_balance, current_price=cur_price)
    return {
        "symbol": req.symbol,
        "count": len(signals),
        "signals": [s.to_dict() for s in signals],
    }


# ── 종목 상태 일괄 조회 ───────────────────────────────────────


class WatchlistItem(BaseModel):
    symbol: str
    asset_type: str
    exchange: str = "NAS"
    name: str = ""


class WatchlistStatusRequest(BaseModel):
    items: List[WatchlistItem]
    account_balance: float = 10_000_000


@router.post("/signals/watchlist-status")
def get_watchlist_status(req: WatchlistStatusRequest):
    """종목 목록 전체 신호 상태 조회 (신호없음 포함)"""
    results = []
    for item in req.items:
        try:
            if item.asset_type == "domestic":
                df = get_domestic_ohlcv(item.symbol, days=100)
            elif item.asset_type == "overseas":
                df = get_overseas_ohlcv(item.symbol, item.exchange, days=100)
            elif item.asset_type == "crypto":
                df = get_crypto_ohlcv_long(item.symbol, days=100)
            else:
                continue

            if df.empty:
                results.append({"symbol": item.symbol, "name": item.name,
                                 "asset_type": item.asset_type, "status": "오류", "signals": []})
                continue

            signals = generate_signals(item.symbol, item.asset_type, df, req.account_balance)
            entry_signals = [s for s in signals if s.isEntry]

            if entry_signals:
                sig = entry_signals[0]
                status = "매수" if sig.isLong else "매도"
            elif signals:
                status = "청산"
            else:
                status = "신호없음"

            results.append({
                "symbol": item.symbol,
                "name": item.name,
                "asset_type": item.asset_type,
                "status": status,
                "signals": [s.to_dict() for s in signals],
            })
        except Exception as e:
            logger.error("[watchlist-status] %s (%s) 오류: %s", item.symbol, item.asset_type, e, exc_info=True)
            results.append({"symbol": item.symbol, "name": item.name,
                             "asset_type": item.asset_type, "status": "오류", "signals": []})

    return {"count": len(results), "items": results}


# ── OHLCV 차트 데이터 ─────────────────────────────────────


@router.get("/chart/{asset_type}/{symbol}")
def get_chart_data(asset_type: str, symbol: str, exchange: str = "NAS", days: int = 100):
    """차트용 OHLCV 데이터 조회"""
    try:
        if asset_type == "domestic":
            df = get_domestic_ohlcv(symbol, days)
        elif asset_type == "overseas":
            df = get_overseas_ohlcv(symbol, exchange, days)
        elif asset_type == "crypto":
            df = get_crypto_ohlcv_long(symbol, days)
        else:
            raise HTTPException(status_code=400, detail="asset_type 오류")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if df.empty:
        raise HTTPException(status_code=404, detail="데이터 없음")

    return {
        "symbol": symbol,
        "data": df.to_dict(orient="records"),
    }
