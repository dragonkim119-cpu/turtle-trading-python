# Oracle Cloud 배포 가이드

## VM 스펙 (Always Free)
- **Shape**: VM.Standard.A1.Flex (ARM64)
- **OCPU**: 4, **Memory**: 24GB (Always Free 한도)
- **OS**: Ubuntu 22.04 (ARM)
- **Region**: ap-seoul-1 (서울)

## 1. VM 생성 후 SSH 접속

```bash
ssh -i ~/.ssh/oracle_key ubuntu@<PUBLIC_IP>
```

## 2. 민감 파일 업로드 (배포 전)

```bash
# 로컬 Windows에서 실행
scp -i ~/.ssh/oracle_key backend/config/.env ubuntu@<PUBLIC_IP>:/tmp/
scp -i ~/.ssh/oracle_key backend/config/firebase-service-account.json ubuntu@<PUBLIC_IP>:/tmp/

# VM에서 실행
sudo mkdir -p /opt/turtle-trading/backend/config
sudo mv /tmp/.env /opt/turtle-trading/backend/config/
sudo mv /tmp/firebase-service-account.json /opt/turtle-trading/backend/config/
sudo chmod 600 /opt/turtle-trading/backend/config/.env
sudo chmod 600 /opt/turtle-trading/backend/config/firebase-service-account.json
```

## 3. 배포 스크립트 실행

```bash
# deploy.sh의 REPO_URL을 실제 GitHub repo URL로 수정 후:
bash deploy.sh
```

## 4. Oracle Security List 방화벽 설정

Oracle Cloud 콘솔 → VCN → Security Lists → Default Security List:

**Ingress Rule 추가:**
- Source CIDR: `0.0.0.0/0`
- Protocol: TCP
- Destination Port: `8000`

## 5. 동작 확인

```bash
# VM에서
sudo systemctl status turtle-trading
curl http://localhost:8000/health

# 외부에서
curl http://<PUBLIC_IP>:8000/health
```

## 6. Flutter 앱 URL 업데이트

`mobile/lib/services/api_service.dart` 또는 앱 설정 화면에서:
```
http://<PUBLIC_IP>:8000
```

## 업데이트 배포

```bash
ssh -i ~/.ssh/oracle_key ubuntu@<PUBLIC_IP>
cd /opt/turtle-trading
git pull origin main
/opt/turtle-trading/venv/bin/pip install -r backend/requirements.txt
sudo systemctl restart turtle-trading
```

## 로그 확인

```bash
sudo journalctl -u turtle-trading -f          # 실시간
sudo journalctl -u turtle-trading --since today  # 오늘치
```

## 주의사항
- `.env`, `firebase-service-account.json`, `google-services.json` — git 제외 (이미 .gitignore)
- APScheduler 평일 16:00 스캔 — VM 시간대 확인 (`timedatectl` → KST 필요시 `sudo timedatectl set-timezone Asia/Seoul`)
- ARM 환경에서 일부 패키지 빌드 시간 길 수 있음 (특히 pandas, numpy)
