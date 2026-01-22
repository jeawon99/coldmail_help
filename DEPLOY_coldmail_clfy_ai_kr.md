# 🚀 coldmail.clfy.ai.kr 배포 가이드

**서버 정보**:
- IP: 121.126.99.70
- 도메인: coldmail.clfy.ai.kr
- OS: Linux (Ubuntu 권장)

---

## 📋 전체 흐름도

```
사용자
  ↓
https://coldmail.clfy.ai.kr (443 포트)
  ↓
121.126.99.70:443 (Nginx 컨테이너)
  ↓
web:8000 (Django 컨테이너)
  ├─→ db:3306 (MySQL)
  └─→ redis:6379 (Redis)
        ├─→ celery_worker
        └─→ celery_beat
```

---

## 1단계: DNS 설정 (도메인 관리 업체)

### Cloudflare / 가비아 / AWS Route53 등에서 설정

```
레코드 타입: A
이름: coldmail
값: 121.126.99.70
TTL: Auto 또는 3600
```

**결과**: `coldmail.clfy.ai.kr` → `121.126.99.70`

**확인 방법**:
```bash
# DNS 전파 확인 (5분~24시간 소요)
nslookup coldmail.clfy.ai.kr

# 또는
dig coldmail.clfy.ai.kr
```

---

## 2단계: 서버 접속 & Docker 설치

### 2.1. SSH 접속
```bash
ssh root@121.126.99.70
# 또는
ssh username@121.126.99.70
```

### 2.2. Docker 설치
```bash
# Docker 설치 스크립트
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker Compose 설치
sudo apt-get update
sudo apt-get install -y docker-compose-plugin

# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER

# 재로그인 또는
newgrp docker

# 확인
docker --version
docker compose version
```

---

## 3단계: 프로젝트 파일 전송

### 방법 1: Git Clone (권장)
```bash
# 서버에서 실행
cd ~
git clone https://github.com/your-repo/coldmail-platform.git coldmail-prod
cd coldmail-prod
```

### 방법 2: 필수 파일만 SCP로 전송
```bash
# 로컬 PC에서 실행
scp docker-compose.prod.yml root@121.126.99.70:~/coldmail-prod/
scp -r nginx root@121.126.99.70:~/coldmail-prod/
scp -r mysql root@121.126.99.70:~/coldmail-prod/
scp .env.example root@121.126.99.70:~/coldmail-prod/
```

---

## 4단계: 환경 변수 설정

```bash
# 서버에서 실행
cd ~/coldmail-prod

# .env.production 생성
cp .env.example .env.production

# 환경 변수 수정
nano .env.production
```

### 필수 수정 항목:
```bash
# SECRET_KEY 새로 생성 (로컬 PC에서)
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# .env.production 내용
SECRET_KEY=<위에서-생성한-키>
DEBUG=False
ALLOWED_HOSTS=coldmail.clfy.ai.kr,121.126.99.70

DB_PASSWORD=Strong_Password_123!
DB_ROOT_PASSWORD=Strong_Root_Password_456!

# Docker Hub (이미지 배포 시)
DOCKER_USERNAME=your-dockerhub-username

# 이메일 설정 (실제 SMTP 정보)
EMAIL_HOST_USER=contact@clfy.cloud
EMAIL_HOST_PASSWORD=your-app-password
```

---

## 5단계: 방화벽 설정

```bash
# UFW 방화벽 설정
sudo ufw allow 22/tcp    # SSH (필수!)
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# 상태 확인
sudo ufw status
```

**결과**:
```
Status: active

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                     ALLOW       Anywhere
```

---

## 6단계: 배포 실행

### 6.1. Docker Hub에서 이미지 가져오기
```bash
# 이미지 pull
docker pull your-dockerhub-username/coldmail-app:latest

# 또는 로컬 빌드 (서버에서 직접 빌드)
docker build -t your-dockerhub-username/coldmail-app:latest .
```

### 6.2. 서비스 시작
```bash
# 백그라운드로 시작
docker compose -f docker-compose.prod.yml up -d

# 로그 확인
docker compose -f docker-compose.prod.yml logs -f
```

### 6.3. 컨테이너 상태 확인
```bash
docker compose ps
```

**정상 출력**:
```
NAME                STATUS              PORTS
coldmail_nginx      Up 2 minutes        0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
coldmail_web        Up 2 minutes        8000/tcp
coldmail_db         Up 2 minutes (healthy)
coldmail_redis      Up 2 minutes (healthy)
coldmail_worker     Up 2 minutes
coldmail_beat       Up 2 minutes
```

---

## 7단계: 초기 설정

### 7.1. 마이그레이션 확인
```bash
docker compose exec web python manage.py showmigrations
```

### 7.2. 슈퍼유저 생성
```bash
docker compose exec web python manage.py createsuperuser
```

### 7.3. Celery 상태 확인
```bash
# Worker 상태
docker compose exec celery_worker celery -A coldmail_project inspect active

# Beat 로그
docker compose logs celery_beat
```

---

## 8단계: 동작 확인 (HTTP)

### 8.1. Health Check
```bash
# IP로 접속
curl http://121.126.99.70/health/
# 출력: healthy

# 도메인으로 접속 (DNS 전파 후)
curl http://coldmail.clfy.ai.kr/health/
```

### 8.2. Admin 페이지
```
브라우저에서:
http://121.126.99.70/admin/

또는 (DNS 전파 후):
http://coldmail.clfy.ai.kr/admin/
```

### 8.3. API 테스트
```bash
# 토큰 받기
curl -X POST http://121.126.99.70/api/v1/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}'

# 캠페인 목록
curl -H "Authorization: Token YOUR_TOKEN" \
  http://121.126.99.70/api/v1/campaigns/
```

---

## 9단계: SSL 인증서 설정 (HTTPS) - 자동 갱신

### 방법 1: 자동화 스크립트 사용 (권장)

#### 9.1. 스크립트 실행 권한 부여
```bash
chmod +x init-letsencrypt.sh
chmod +x renew-cert.sh
```

#### 9.2. SSL 인증서 초기 발급
```bash
# 스크립트 내 이메일 주소 수정
nano init-letsencrypt.sh
# EMAIL="admin@clfy.ai.kr" 를 실제 이메일로 변경

# 인증서 발급 실행
./init-letsencrypt.sh
```

**스크립트가 자동으로 처리하는 작업**:
- certbot 디렉토리 생성
- Nginx 컨테이너 일시 중지
- Let's Encrypt 인증서 발급
- 인증서 정보 출력

#### 9.3. Nginx HTTPS 설정 활성화
```bash
nano nginx/conf.d/coldmail.conf

# HTTPS server 블록의 주석(#) 모두 제거
# HTTP server 블록은 그대로 유지 (80→443 리다이렉트용)
```

#### 9.4. 서비스 재시작
```bash
docker compose down
docker compose -f docker-compose.prod.yml up -d
```

### 방법 2: 수동 설정

#### 9.1. certbot 디렉토리 생성
```bash
mkdir -p certbot/conf
mkdir -p certbot/www
```

#### 9.2. Nginx 컨테이너 일시 중지
```bash
docker compose stop nginx
```

#### 9.3. 인증서 발급
```bash
docker compose run --rm certbot certonly \
  --standalone \
  -d coldmail.clfy.ai.kr \
  --email admin@clfy.ai.kr \
  --agree-tos \
  --no-eff-email
```

**발급 위치**: `certbot/conf/live/coldmail.clfy.ai.kr/`

#### 9.4. Nginx 설정 활성화
```bash
# nginx/conf.d/coldmail.conf 파일 수정
nano nginx/conf.d/coldmail.conf

# HTTPS server 블록 주석 해제 (# 제거)
```

#### 9.5. 서비스 재시작
```bash
docker compose down
docker compose -f docker-compose.prod.yml up -d
```

### 🔄 자동 갱신 설정

**인증서는 90일마다 만료되며, Certbot 컨테이너가 자동으로 갱신합니다.**

#### 자동 갱신 작동 방식:
1. **Certbot 컨테이너**: 12시간마다 인증서 갱신 확인
2. **Nginx 컨테이너**: 6시간마다 설정 리로드
3. 만료 30일 전부터 자동 갱신 시도

#### 갱신 로그 확인:
```bash
# Certbot 로그
docker compose logs certbot

# 최근 갱신 시도 확인
docker compose logs --tail=50 certbot
```

#### 수동 갱신 (필요시):
```bash
# 스크립트로 갱신
./renew-cert.sh

# 또는 직접 명령어 실행
docker compose run --rm certbot renew --force-renewal
docker compose exec nginx nginx -s reload
```

#### 인증서 상태 확인:
```bash
# 인증서 정보 및 만료일 확인
docker compose run --rm certbot certificates

# 출력 예시:
# Certificate Name: coldmail.clfy.ai.kr
#   Domains: coldmail.clfy.ai.kr
#   Expiry Date: 2026-04-23 00:00:00+00:00 (VALID: 89 days)
```

### 9.6. HTTPS 확인
```bash
curl https://coldmail.clfy.ai.kr/health/

# 또는 브라우저에서
https://coldmail.clfy.ai.kr/admin/
```

### 9.7. .env.production HTTPS 설정 활성화
```bash
nano .env.production

# 다음 값들을 True로 변경:
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

```bash
# 서비스 재시작
docker compose restart web
```

### 📋 자동 갱신 요약

| 항목 | 설정 |
|------|------|
| **갱신 주기** | 12시간마다 확인 |
| **갱신 시기** | 만료 30일 전부터 |
| **Nginx 리로드** | 6시간마다 자동 |
| **유효 기간** | 90일 |
| **수동 갱신** | `./renew-cert.sh` |

**인증서 자동 갱신이 활성화되어 있으므로 별도 설정이 필요 없습니다!**

### 9.8. 인증서 자동 갱신 테스트 (선택사항)
```bash
# Dry-run으로 갱신 테스트 (실제 갱신은 하지 않음)
docker compose run --rm certbot renew --dry-run

# 출력에 "Congratulations, all simulated renewals succeeded"가 나오면 성공
```

---

## 10단계: 최종 확인

### ✅ 체크리스트

```bash
# 1. 컨테이너 상태
docker compose ps
# 모두 Up, db/redis는 healthy

# 2. Health check
curl https://coldmail.clfy.ai.kr/health/
# 출력: healthy

# 3. HTTPS 리다이렉트
curl -I http://coldmail.clfy.ai.kr
# 301 → https://coldmail.clfy.ai.kr

# 4. SSL 인증서
curl -vI https://coldmail.clfy.ai.kr 2>&1 | grep "SSL certificate verify"
# SSL certificate verify ok

# 5. API 응답
curl https://coldmail.clfy.ai.kr/api/v1/campaigns/ \
  -H "Authorization: Token YOUR_TOKEN"

# 6. Admin 페이지
# 브라우저: https://coldmail.clfy.ai.kr/admin/

# 7. Celery Worker
docker compose exec celery_worker celery -A coldmail_project inspect ping
# pong

# 8. 로그 확인
docker compose logs --tail=50
# 에러 없음
```

---

## 📊 포트 정리

### 외부에서 접근 가능한 포트 (방화벽 오픈)
- **80**: HTTP (HTTPS로 리다이렉트)
- **443**: HTTPS (실제 서비스)
- **22**: SSH (관리용)

### 내부 Docker 네트워크 (외부 접근 불가)
- **8000**: Django (Gunicorn)
- **3306**: MySQL
- **6379**: Redis

**중요**: 외부에서는 80/443 포트로만 접속하며, Django의 8000 포트는 Nginx를 통해서만 접근 가능합니다.

---

## 🔧 유용한 명령어

### 로그 보기
```bash
# 전체 로그
docker compose logs -f

# 특정 서비스
docker compose logs -f web
docker compose logs -f nginx
docker compose logs -f celery_worker

# 최근 100줄만
docker compose logs --tail=100 -f
```

### 서비스 재시작
```bash
# 전체 재시작
docker compose restart

# 특정 서비스만
docker compose restart web
docker compose restart nginx
```

### Django 명령 실행
```bash
# 마이그레이션
docker compose exec web python manage.py migrate

# 정적 파일 수집
docker compose exec web python manage.py collectstatic --noinput

# Shell
docker compose exec web python manage.py shell
```

### 데이터베이스 백업
```bash
# 백업
docker compose exec db mysqldump -u root -p$DB_ROOT_PASSWORD coldmail_prod > backup_$(date +%Y%m%d).sql

# 복구
cat backup_20260123.sql | docker compose exec -T db mysql -u root -p$DB_ROOT_PASSWORD coldmail_prod
```

### 업데이트 배포
```bash
# 1. 새 이미지 pull
docker pull your-dockerhub-username/coldmail-app:v1.1

# 2. .env.production에서 VERSION 변경
nano .env.production
# VERSION=v1.1

# 3. 재시작
docker compose down
docker compose -f docker-compose.prod.yml up -d
```

---

## 🆘 문제 해결

### DNS가 전파되지 않을 때
```bash
# DNS 전파 확인
nslookup coldmail.clfy.ai.kr

# 또는
dig coldmail.clfy.ai.kr

# hosts 파일로 임시 테스트 (로컬 PC)
# Windows: C:\Windows\System32\drivers\etc\hosts
# Linux/Mac: /etc/hosts
121.126.99.70 coldmail.clfy.ai.kr
```

### 컨테이너가 시작되지 않을 때
```bash
docker compose logs <service-name>
docker compose exec <service-name> bash
```

### 502 Bad Gateway (Nginx 에러)
```bash
# Django 컨테이너 상태 확인
docker compose ps web

# Django 로그 확인
docker compose logs web

# Nginx 설정 테스트
docker compose exec nginx nginx -t
```

### SSL 인증서 오류
```bash
# 인증서 유효기간 확인
sudo certbot certificates

# 인증서 경로 확인
ls -la /etc/letsencrypt/live/coldmail.clfy.ai.kr/

# Nginx 설정 확인
docker compose exec nginx cat /etc/nginx/conf.d/coldmail.conf
```

---

## 📈 모니터링

### 리소스 사용량
```bash
# 컨테이너 리소스
docker stats

# 디스크 사용량
df -h

# Docker 디스크 사용량
docker system df
```

### 로그 파일 위치
```bash
# 서버에서
ls -la ~/coldmail-prod/logs/

# Django 로그
tail -f ~/coldmail-prod/logs/django.log
```

---

## 🎯 배포 완료!

**접속 URL**:
- HTTP: http://coldmail.clfy.ai.kr (→ HTTPS로 리다이렉트)
- HTTPS: https://coldmail.clfy.ai.kr
- Admin: https://coldmail.clfy.ai.kr/admin/
- API: https://coldmail.clfy.ai.kr/api/v1/

**주요 엔드포인트**:
- `/api/v1/campaigns/` - 캠페인 관리
- `/api/v1/campaigns/{id}/analytics/overview/` - 통계
- `/api/v1/segments/` - 세그먼트
- `/admin/` - 관리자 페이지

---

**문제가 발생하면 로그를 먼저 확인하세요!**
```bash
docker compose logs -f
```
