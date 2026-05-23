# 터틀 트레이딩 시스템 — 프로젝트 컨텍스트

## 프로젝트 개요
리처드 데니스의 터틀 트레이딩 시스템을 모바일에서 신호 수신하는 앱.
- **신호만 받고 수동 주문** (자동 주문 없음)
- 국내주식(KIS API), 해외주식(KIS API), 가상자산(Binance)
- FastAPI 백엔드 + Flutter Android 앱

## 프로젝트 구조
```
turtle-trading/
├── backend/                    # FastAPI 서버
│   ├── api/
│   │   ├── main.py             # FastAPI 앱, APScheduler (평일 16:00 자동 스캔)
│   │   ├── routes.py           # REST 엔드포인트
│   │   ├── scanner.py          # 전종목 스캔 + FCM 알림 발송
│   │   └── fcm.py              # Firebase FCM v1 API 발송 + 토큰 관리
│   ├── data/
│   │   ├── kis_api.py          # KIS OpenAPI (국내/해외주식)
│   │   ├── binance_api.py      # Binance (가상자산, API키 불필요)
│   │   ├── upbit_api.py        # Upbit (미사용 — Binance로 통일)
│   │   ├── signals_cache.json  # 스캔 결과 캐시 (atomic write)
│   │   └── fcm_tokens.json     # FCM 디바이스 토큰 저장소
│   ├── turtle_system/
│   │   ├── indicators.py       # ATR(20), Donchian 채널, S1/S2 신호
│   │   ├── position.py         # 포지션 사이징, 손절가, 피라미딩
│   │   ├── signals.py          # 신호 생성 (TurtleSignal 데이터클래스)
│   │   └── backtest.py         # 백테스트 엔진 (롱+숏)
│   ├── config/
│   │   ├── .env                # 실제 키 (git 제외)
│   │   ├── .env.example        # 키 템플릿
│   │   └── firebase-service-account.json  # FCM 서비스 계정 (git 제외)
│   ├── requirements.txt
│   ├── run.py                  # python run.py 로 서버 시작
│   ├── test_backtest.py        # 바이낸스 3년 백테스트
│   ├── test_signals.py         # KIS 신호 스캔 테스트
│   └── test_kis.py
└── mobile/                     # Flutter Android 앱
    ├── lib/
    │   ├── main.dart            # Firebase 초기화, NavigationBar (신호/종목/설정)
    │   ├── screens/
    │   │   ├── signals_screen.dart    # 신호 목록 (필터: 전체/국내/해외/가상자산)
    │   │   ├── watchlist_screen.dart  # 종목 관리 + 신호 스캔
    │   │   └── settings_screen.dart   # 서버 URL + 계좌잔고 설정
    │   ├── services/
    │   │   ├── api_service.dart        # HTTP 클라이언트, 설정 파일 관리
    │   │   ├── watchlist_service.dart  # 워치리스트 로컬 저장
    │   │   └── notification_service.dart  # FCM + flutter_local_notifications
    │   └── models/
    │       └── signal.dart
    └── android/
        └── app/
            ├── google-services.json   # Firebase 설정 (git 제외)
            └── build.gradle.kts
```

## 터틀 트레이딩 핵심 규칙
- **System 1**: 20일 Donchian 돌파 진입 / 10일 청산
- **System 2**: 55일 Donchian 돌파 진입 / 20일 청산
- **포지션 사이징**: `유닛 = (계좌잔고 × 1%) ÷ ATR(20)`
- **피라미딩**: 0.5 ATR 간격, 최대 4유닛
- **손절**: 진입가 ± 2 × ATR
- **국내주식**: 숏 진입 불가 (공매도 제한)

## 중요 설계 결정 (변경 금지)

### 1. 가상자산 데이터 소스 = Binance (USD)
- scanner.py, routes.py 모두 `get_crypto_ohlcv_long()` 사용
- Upbit(KRW) 혼용 시 환율 단위 불일치 발생 → **절대 혼용 금지**

### 2. 환율 변환 (KRW → USD)
- 해외주식·가상자산은 ATR이 USD 기준
- `position.py`의 `KRW_USD_RATE = float(os.getenv("KRW_USD_RATE", "1380"))`
- `calc_unit_size(..., fx_rate=KRW_USD_RATE)` 필수
- `.env`에서 `KRW_USD_RATE=1380` 오버라이드 가능

### 3. 설정 저장 방식 (Flutter)
- `shared_preferences` 사용 금지 — DataStore 빌드 오류 발생했음
- `path_provider` + `dart:io` 파일 방식 사용 (`turtle_config.json`)

### 4. Atomic Write
- `signals_cache.json`: `tempfile.mkstemp()` → `os.replace()` 사용
- `fcm_tokens.json`: 동일 방식

### 5. Gradle 설정
- `kotlin.incremental=false` — D:/C: 드라이브 분리 환경에서 캐시 충돌 방지
- `GRADLE_USER_HOME=D:\gradle` 환경변수 설정

## API 엔드포인트
```
GET  /health                          서버 상태 확인
GET  /api/v1/signals                  캐시된 신호 목록 (asset_type, signal_type 필터)
POST /api/v1/signals/scan             수동 전체 스캔 실행
POST /api/v1/signals/single           단일 종목 즉시 신호 조회
POST /api/v1/signals/watchlist-status 종목 목록 상태 일괄 조회
GET  /api/v1/chart/{asset_type}/{symbol} OHLCV 차트 데이터
POST /api/v1/device/token             FCM 디바이스 토큰 등록
```

## 환경변수 (.env)
```
KIS_APP_KEY=...
KIS_APP_SECRET=...
KIS_ACCOUNT_NO=계좌번호-01
KIS_IS_REAL=false              # true=실거래, false=모의투자
DEFAULT_BALANCE=100000000      # KIS 잔고 API 실패 시 기본값
KRW_USD_RATE=1380              # 환율 (해외/가상자산 포지션 사이징)
FCM_PROJECT_ID=...             # Firebase 프로젝트 ID
FCM_SERVICE_ACCOUNT_PATH=config/firebase-service-account.json
```

## 서버 실행 (로컬 PC)
```powershell
cd D:\Claude_code\turtle-trading\backend
python run.py

# 수동 스캔
irm -Uri http://localhost:8000/api/v1/signals/scan -Method POST

# 한글 깨짐 방지
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

## 앱 빌드 & 실행
```powershell
cd D:\Claude_code\turtle-trading\mobile
flutter run
```

## 남은 작업 (우선순위순)
1. **Oracle Cloud 배포** — VM.Standard.A1.Flex (ARM, Always Free, Seoul 리전)
   - systemd 서비스 등록으로 자동 시작
   - 포트 8000 방화벽 오픈 (Oracle Security List + iptables)
   - 배포 완료 후 앱 URL을 Public IP로 변경
2. **포지션 추적** — 진입한 포지션 기록, 피라미딩 현황, 손절가 추적
3. **차트 화면** — OHLCV 캔들 + Donchian 채널 오버레이 (fl_chart 패키지)
4. **거래 일지** — 진입/청산 기록, 누적 수익률, CSV 내보내기

## 백테스트 결과 (3년, Binance)
| 종목 | S1 수익률 | S2 수익률 |
|------|-----------|-----------|
| BTC (5억) | +12.60% | +16.24% |
| ETH (5천만) | +3.67% | +46.73% |
| XRP (1천만) | +53.36% | +42.57% |
| SOL (3천만) | +36.43% | +29.46% |

## 패키지 버전 (주요)
**Backend**: fastapi==0.111.0, pandas==2.2.2, apscheduler==3.10.4, google-auth==2.29.0  
**Flutter**: firebase_core ^3.6.0, firebase_messaging ^15.1.3, flutter_local_notifications ^17.2.2

## Flutter 앱 패키지명
`com.turtle.mobile` (android/app/build.gradle.kts)
