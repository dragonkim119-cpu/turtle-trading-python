"""FCM v1 API — 푸시 알림 발송 및 토큰 관리"""
import json
import logging
import os
import tempfile

import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

_SCOPES = ['https://www.googleapis.com/auth/firebase.messaging']
_SERVICE_ACCOUNT_PATH = os.getenv(
    'FCM_SERVICE_ACCOUNT_PATH',
    os.path.join(os.path.dirname(__file__), '../config/firebase-service-account.json'),
)
_PROJECT_ID = os.getenv('FCM_PROJECT_ID', '')
_TOKENS_PATH = os.path.join(os.path.dirname(__file__), '../data/fcm_tokens.json')

_credentials = None


def _get_access_token() -> str:
    global _credentials
    if _credentials is None:
        if not os.path.exists(_SERVICE_ACCOUNT_PATH):
            raise FileNotFoundError(f"서비스 계정 파일 없음: {_SERVICE_ACCOUNT_PATH}")
        _credentials = service_account.Credentials.from_service_account_file(
            _SERVICE_ACCOUNT_PATH, scopes=_SCOPES
        )
    if not _credentials.valid:
        _credentials.refresh(Request())
    return _credentials.token


def load_tokens() -> list[str]:
    try:
        if os.path.exists(_TOKENS_PATH):
            with open(_TOKENS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f).get('tokens', [])
    except Exception as e:
        logger.error("토큰 로드 실패: %s", e)
    return []


def save_token(token: str) -> None:
    """FCM 토큰 등록 (중복 제거)"""
    tokens = set(load_tokens())
    tokens.add(token)
    _write_tokens(list(tokens))
    logger.info("FCM 토큰 등록 완료 (총 %d개)", len(tokens))


def _write_tokens(tokens: list[str]) -> None:
    """Atomic write"""
    os.makedirs(os.path.dirname(_TOKENS_PATH), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(_TOKENS_PATH), suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump({'tokens': tokens}, f)
        os.replace(tmp, _TOKENS_PATH)
    except Exception:
        os.unlink(tmp)
        raise


def send_notification(title: str, body: str) -> int:
    """등록된 모든 기기에 알림 발송. 성공 건수 반환."""
    if not _PROJECT_ID:
        logger.warning("FCM_PROJECT_ID 미설정 — 알림 건너뜀")
        return 0

    tokens = load_tokens()
    if not tokens:
        logger.info("등록된 FCM 토큰 없음 — 알림 건너뜀")
        return 0

    try:
        access_token = _get_access_token()
    except Exception as e:
        logger.error("FCM 인증 실패: %s", e)
        return 0

    url = f'https://fcm.googleapis.com/v1/projects/{_PROJECT_ID}/messages:send'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    success = 0
    invalid_tokens = []

    for token in tokens:
        payload = {
            'message': {
                'token': token,
                'notification': {'title': title, 'body': body},
                'android': {'priority': 'HIGH'},
            }
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                success += 1
            elif resp.status_code in (400, 404):
                # 만료/잘못된 토큰
                invalid_tokens.append(token)
                logger.warning("FCM 토큰 만료 — 제거: %.20s...", token)
            else:
                logger.error("FCM 발송 실패 [%s]: %s", resp.status_code, resp.text)
        except Exception as e:
            logger.error("FCM 요청 오류: %s", e)

    if invalid_tokens:
        valid = [t for t in tokens if t not in invalid_tokens]
        _write_tokens(valid)

    logger.info("FCM 알림 발송 완료: %d/%d 성공", success, len(tokens))
    return success
