"""터틀 트레이딩 신호 API 서버"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

from .routes import router
from .scanner import run_full_scan

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../config/.env"))

app = FastAPI(title="Turtle Trading Signal API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

# 매일 장 마감 후 자동 스캔 (평일 오후 4시 KST)
scheduler = BackgroundScheduler(timezone="Asia/Seoul")
scheduler.add_job(run_full_scan, "cron", day_of_week="mon-fri", hour=16, minute=0)
scheduler.start()


@app.get("/health")
def health():
    return {"status": "ok"}
