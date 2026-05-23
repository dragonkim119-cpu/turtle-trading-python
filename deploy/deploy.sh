#!/bin/bash
# Oracle Cloud VM.Standard.A1.Flex (ARM Ubuntu 22.04) 배포 스크립트
# 실행: bash deploy.sh

set -e

APP_DIR="/opt/turtle-trading"
VENV_DIR="$APP_DIR/venv"
REPO_URL="https://github.com/dragonkim119-cpu/turtle-trading.git"  # 실제 repo URL로 교체
SERVICE_NAME="turtle-trading"
USER="ubuntu"

echo "=== 1. 시스템 패키지 설치 ==="
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git

echo "=== 2. 앱 디렉토리 준비 ==="
sudo mkdir -p "$APP_DIR"
sudo chown "$USER:$USER" "$APP_DIR"

# 처음 배포: git clone
# 업데이트 시: git pull
if [ -d "$APP_DIR/.git" ]; then
    echo "=== 업데이트: git pull ==="
    cd "$APP_DIR"
    git pull origin main
else
    echo "=== 첫 배포: git clone ==="
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi

echo "=== 3. Python 가상환경 설정 ==="
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r backend/requirements.txt

echo "=== 4. 환경변수 파일 확인 ==="
if [ ! -f "$APP_DIR/backend/config/.env" ]; then
    echo "ERROR: backend/config/.env 파일이 없습니다."
    echo "backend/config/.env.example 참고하여 생성 후 재실행하세요."
    exit 1
fi

if [ ! -f "$APP_DIR/backend/config/firebase-service-account.json" ]; then
    echo "WARNING: firebase-service-account.json 없음 — FCM 알림 비활성화됨"
fi

echo "=== 5. systemd 서비스 등록 ==="
sudo cp "$APP_DIR/deploy/turtle-trading.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "=== 6. 방화벽 설정 ==="
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
# 재부팅 후 iptables 규칙 유지
if command -v netfilter-persistent &> /dev/null; then
    sudo netfilter-persistent save
else
    sudo apt-get install -y iptables-persistent
    sudo netfilter-persistent save
fi

echo "=== 배포 완료 ==="
echo "서비스 상태: sudo systemctl status $SERVICE_NAME"
echo "로그 확인:   sudo journalctl -u $SERVICE_NAME -f"
echo "서버 주소:   http://$(curl -s ifconfig.me):8000/health"
