# 🚀 Cold Mail Platform - 빠른 배포 가이드

## 전제 조건

- Docker Hub 계정
- 리눅스 서버 (Ubuntu 20.04+ 권장)
- 도메인 (선택사항, IP로도 가능)

---

## 1단계: 로컬에서 Docker 이미지 빌드

```bash
# 1. .env.production 파일 생성 및 수정
cp .env.example .env.production
nano .env.production

# 반드시 수정해야 할 항목:
# - SECRET_KEY (강력한 랜덤 키 생성)
# - DB_PASSWORD, DB_ROOT_PASSWORD
# - ALLOWED_HOSTS (실제 도메인 또는 서버 IP)
# - DOCKER_USERNAME (Docker Hub 사용자명)
# - EMAIL_HOST_USER, EMAIL_HOST_PASSWORD (실제 이메일 설정)

# 2. SECRET_KEY 생성 (Python으로)
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# 3. Docker 이미지 빌드
docker build -t limjeawon99/coldmail-app:v1.0 .

# 4. 로컬 테스트 (선택사항)
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml logs -f
```

---

## 2단계: Docker Hub에 푸시

```bash
# 1. Docker Hub 로그인
docker login

# 2. 이미지 태그
docker tag limjeawon99/coldmail-app:v1.0 limjeawon99/coldmail-app:latest

# 3. 푸시
docker push limjeawon99/coldmail-app:v1.0
docker push limjeawon99/coldmail-app:latest
```

---

## 3단계: 서버 준비

### 3.1. 서버에 SSH 접속
```bash
ssh user@your-server-ip
```

### 3.2. Docker 설치 (Ubuntu)
```bash
# 기존 Docker 제거 (있다면)
sudo apt-get remove docker docker-engine docker.io containerd runc

# 패키지 업데이트
sudo apt-get update

# 의존성 설치
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Docker GPG 키 추가
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Docker 저장소 추가
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Docker 설치
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Docker 서비스 시작 및 활성화
sudo systemctl start docker
sudo systemctl enable docker

# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER

# 재로그인 또는
newgrp docker

# Docker 버전 확인
docker --version
docker compose version
```

### 3.3. 프로젝트 디렉토리 생성
```bash
mkdir -p ~/coldmail-prod
cd ~/coldmail-prod
```

---

## 4단계: 배포 파일 전송

### 방법 1: Git으로 전송 (권장)
```bash
# 서버에서 실행
git clone https://github.com/your-username/coldmail-platform.git .

# 또는 특정 파일만 필요하다면:
wget https://raw.githubusercontent.com/your-username/coldmail-platform/main/docker-compose.prod.yml
wget https://raw.githubusercontent.com/your-username/coldmail-platform/main/.env.example
```

### 방법 2: SCP로 전송
```bash
# 로컬에서 실행
scp docker-compose.prod.yml user@your-server-ip:~/coldmail-prod/
scp -r nginx user@your-server-ip:~/coldmail-prod/
scp -r mysql user@your-server-ip:~/coldmail-prod/
scp .env.example user@your-server-ip:~/coldmail-prod/
```

---

## 5단계: 환경 변수 설정

```bash
# 서버에서 실행
cd ~/coldmail-prod

# .env.production 생성
cp .env.example .env.production

# 환경 변수 수정
nano .env.production

# 필수 수정 항목:
# SECRET_KEY=<strong-random-key>
# DEBUG=False
# ALLOWED_HOSTS=your-domain.com,your-server-ip
# DB_PASSWORD=<strong-password>
# DB_ROOT_PASSWORD=<strong-password>
# DOCKER_USERNAME=limjeawon99
# EMAIL_HOST_USER=your-email@gmail.com
# EMAIL_HOST_PASSWORD=<app-password>
```

---

## 6단계: 배포 시작

```bash
# Docker Hub에서 이미지 가져오기
docker pull limjeawon99/coldmail-app:latest

# 서비스 시작
docker compose -f docker-compose.prod.yml up -d

# 로그 확인
docker compose -f docker-compose.prod.yml logs -f

# 컨테이너 상태 확인
docker compose ps
```

---

## 7단계: 초기 설정

```bash
# 슈퍼유저 생성
docker compose exec web python manage.py createsuperuser

# 마이그레이션 확인
docker compose exec web python manage.py showmigrations

# Celery Worker 상태 확인
docker compose exec celery_worker celery -A coldmail_project inspect active

# Celery Beat 로그 확인
docker compose logs celery_beat
```

---

## 8단계: 동작 확인

### 8.1. Health Check
```bash
curl http://your-server-ip/health/
# 출력: healthy
```

### 8.2. API 테스트
```bash
# 로그인하여 토큰 받기
curl -X POST http://your-server-ip/api/v1/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"your-username","password":"your-password"}'

# 캠페인 목록 조회
curl -H "Authorization: Token YOUR_TOKEN" \
  http://your-server-ip/api/v1/campaigns/
```

### 8.3. Admin 페이지 접속
```
http://your-server-ip/admin/
```

---

## 9단계: 방화벽 설정 (Ubuntu UFW)

```bash
# UFW 활성화
sudo ufw enable

# SSH 허용 (필수!)
sudo ufw allow 22/tcp

# HTTP/HTTPS 허용
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 상태 확인
sudo ufw status
```

---

## 10단계: SSL 설정 (선택사항, 도메인 있을 때)

### Let's Encrypt로 무료 SSL 인증서 발급

```bash
# Certbot 설치
sudo apt-get install -y certbot

# 인증서 발급 (Nginx 컨테이너 일시 중지 필요)
docker compose stop nginx

sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Nginx 재시작
docker compose start nginx

# nginx/conf.d/coldmail.conf에서 HTTPS 섹션 주석 해제
nano nginx/conf.d/coldmail.conf

# Nginx 설정 리로드
docker compose exec nginx nginx -s reload

# 자동 갱신 설정 (cron)
sudo crontab -e
# 추가: 0 0 1 * * certbot renew --quiet && docker compose exec nginx nginx -s reload
```

---

## 유용한 명령어

### 로그 확인
```bash
# 전체 로그
docker compose logs -f

# 특정 서비스 로그
docker compose logs -f web
docker compose logs -f celery_worker
docker compose logs -f celery_beat

# 최근 100줄만
docker compose logs --tail=100 -f
```

### 서비스 재시작
```bash
# 전체 재시작
docker compose restart

# 특정 서비스만
docker compose restart web
docker compose restart celery_worker
```

### 데이터베이스 접속
```bash
docker compose exec db mysql -u root -p
# 비밀번호: DB_ROOT_PASSWORD
```

### Redis 접속
```bash
docker compose exec redis redis-cli
```

### Django 명령 실행
```bash
# 마이그레이션
docker compose exec web python manage.py migrate

# 정적 파일 수집
docker compose exec web python manage.py collectstatic --noinput

# Django 쉘
docker compose exec web python manage.py shell
```

### 업데이트 배포
```bash
# 1. 로컬에서 새 이미지 빌드 & 푸시
docker build -t limjeawon99/coldmail-app:v1.1 .
docker push limjeawon99/coldmail-app:v1.1

# 2. 서버에서 새 이미지 가져오기
docker pull limjeawon99/coldmail-app:v1.1

# 3. .env.production의 VERSION 변경
nano .env.production
# VERSION=v1.1로 변경

# 4. 서비스 재시작
docker compose down
docker compose -f docker-compose.prod.yml up -d

# 또는 무중단 재시작
docker compose up -d --no-deps --build web
docker compose restart celery_worker celery_beat
```

---

## 백업 & 복구

### 데이터베이스 백업
```bash
# 백업
docker compose exec db mysqldump -u root -p$DB_ROOT_PASSWORD $DB_NAME > backup_$(date +%Y%m%d_%H%M%S).sql

# 복구
docker compose exec -T db mysql -u root -p$DB_ROOT_PASSWORD $DB_NAME < backup_20260123_120000.sql
```

### 볼륨 백업
```bash
# MySQL 데이터
docker run --rm \
  -v coldmail-prod_mysql_data:/data \
  -v $(pwd):/backup \
  ubuntu tar czf /backup/mysql_backup.tar.gz /data

# Redis 데이터
docker run --rm \
  -v coldmail-prod_redis_data:/data \
  -v $(pwd):/backup \
  ubuntu tar czf /backup/redis_backup.tar.gz /data
```

---

## 문제 해결

### 컨테이너가 계속 재시작될 때
```bash
docker compose logs <service-name>
docker compose exec <service-name> bash
```

### 데이터베이스 연결 오류
```bash
# 컨테이너 간 통신 확인
docker compose exec web ping db

# 데이터베이스 상태 확인
docker compose exec db mysqladmin -u root -p status
```

### 정적 파일이 로드되지 않을 때
```bash
# 정적 파일 재수집
docker compose exec web python manage.py collectstatic --noinput

# Nginx 설정 확인
docker compose exec nginx nginx -t

# Nginx 리로드
docker compose exec nginx nginx -s reload
```

### Celery Worker가 작동하지 않을 때
```bash
# Worker 상태 확인
docker compose exec celery_worker celery -A coldmail_project inspect ping

# Redis 연결 확인
docker compose exec celery_worker python -c "import redis; r=redis.Redis(host='redis'); print(r.ping())"
```

---

## 모니터링

### 리소스 사용량 확인
```bash
docker stats
```

### 디스크 사용량
```bash
docker system df
```

### 불필요한 이미지/컨테이너 정리
```bash
docker system prune -a
```

---

## 성공적인 배포 체크리스트

- [ ] 모든 컨테이너가 running 상태
- [ ] Health check 통과 (`curl http://server-ip/health/`)
- [ ] Admin 페이지 접속 가능
- [ ] API 정상 응답
- [ ] Celery Worker 작동
- [ ] Celery Beat 작동
- [ ] 정적 파일 로드
- [ ] 데이터베이스 연결 정상
- [ ] 로그에 에러 없음

---

## 다음 단계

1. **도메인 연결**: DNS A 레코드를 서버 IP로 설정
2. **SSL 인증서**: Let's Encrypt로 HTTPS 활성화
3. **모니터링**: Prometheus + Grafana 또는 Sentry 추가
4. **백업 자동화**: cron으로 일일 백업 설정
5. **CI/CD**: GitHub Actions로 자동 배포 파이프라인 구축

---

**문제가 발생하면 로그를 먼저 확인하세요!**
```bash
docker compose logs -f
```
