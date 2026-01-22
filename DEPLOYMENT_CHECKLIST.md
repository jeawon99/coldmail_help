# 🚀 프로덕션 배포 체크리스트

## 현재 상태 점검 (2026-01-23)

### ✅ 이미 준비된 것들

1. **Docker 설정**
   - ✅ Dockerfile 존재
   - ✅ docker-compose.yml 존재
   - ✅ entrypoint.sh 존재
   - ✅ MySQL 8.0 설정
   - ✅ Redis 설정
   - ✅ Celery Worker 설정
   - ✅ Celery Beat 설정

2. **Django 설정**
   - ✅ 환경별 settings 분리 (base, dev, prod)
   - ✅ requirements.txt
   - ✅ Gunicorn 설정
   - ✅ 정적 파일 수집 설정

3. **애플리케이션**
   - ✅ Stage 9까지 완료 (Analytics API)
   - ✅ CRM, Campaigns, Templates, Analytics 모듈
   - ✅ Celery 작업 스케줄링

---

## ⚠️ 수정/추가 필요 사항

### 1. 🔒 보안 설정

#### 문제점:
- `.env` 파일에 실제 비밀번호가 노출됨
- SECRET_KEY가 하드코딩됨
- DEBUG=True로 설정됨
- ALLOWED_HOSTS가 제한적

#### 해결 방법:
```bash
# .env.example 생성 (템플릿)
# .env는 .gitignore에 추가
# 프로덕션 환경변수는 서버에서 별도 설정
```

**우선순위: 🔴 높음**

---

### 2. 🌐 Nginx 리버스 프록시

#### 현재 문제:
- Gunicorn이 직접 외부에 노출됨
- 정적 파일 서빙이 비효율적
- SSL/TLS 설정 없음
- 로드 밸런싱 없음

#### 필요 작업:
- Nginx 컨테이너 추가
- SSL 인증서 설정 (Let's Encrypt)
- 정적 파일 Nginx로 서빙
- 리버스 프록시 설정

**우선순위: 🔴 높음**

---

### 3. 📦 Docker 이미지 최적화

#### 현재 문제:
- 멀티 스테이지 빌드 미사용
- 이미지 크기 최적화 필요
- 불필요한 파일 포함 가능성

#### 개선 사항:
- .dockerignore 파일 생성
- 멀티 스테이지 빌드 적용
- Python 패키지 캐시 최적화

**우선순위: 🟡 중간**

---

### 4. 🗄️ 데이터베이스 최적화

#### 현재 문제:
- MySQL root 비밀번호가 .env에 노출
- 백업 전략 없음
- 성능 튜닝 미설정

#### 필요 작업:
- MySQL 성능 설정 (my.cnf)
- 자동 백업 스크립트
- 연결 풀 설정

**우선순위: 🟡 중간**

---

### 5. 📊 모니터링 & 로깅

#### 현재 상태:
- 기본 로깅만 설정됨
- 모니터링 도구 없음
- 에러 추적 없음

#### 추가 필요:
- Sentry (에러 추적)
- Prometheus + Grafana (메트릭 수집)
- ELK Stack (로그 중앙화) 또는 CloudWatch

**우선순위: 🟡 중간**

---

### 6. ⚡ 성능 최적화

#### 필요 작업:
- Redis 캐싱 전략
- DB 커넥션 풀링
- Celery 동시성 설정 조정
- 정적 파일 CDN 연동

**우선순위: 🟢 낮음** (초기 배포 후)

---

## 📝 즉시 수정해야 할 파일들

### 1. `.env.production` (새 파일 생성)
```bash
# Django Settings
SECRET_KEY=<strong-random-key>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DB_NAME=coldmail_prod
DB_USER=coldmail_user
DB_PASSWORD=<strong-db-password>
DB_HOST=db
DB_PORT=3306

# Redis
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Email (실제 SMTP 서버로 변경 필요)
SMTP_EMAIL_HOST=smtp.gmail.com
SMTP_EMAIL_PORT=587
SMTP_EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=<app-password>

# Security (HTTPS 사용시)
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### 2. `.dockerignore` (새 파일 생성)
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
*.egg-info/
dist/
build/

# Django
*.log
db.sqlite3
/staticfiles/
/mediafiles/

# Environment
.env
.env.*

# IDE
.vscode/
.idea/
*.swp
*.swo

# Git
.git/
.gitignore

# Tests
*.xlsx
*.csv
test_*.py
test_*.ps1
check_*.py
prepare_*.py
update_*.py
import_*.py
retry_*.py

# Documentation
*.md
!README.md
```

### 3. `docker-compose.prod.yml` (새 파일 생성)
```yaml
version: "3.8"

services:
  nginx:
    image: nginx:alpine
    container_name: coldmail_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - static_volume:/app/staticfiles:ro
      - ./certbot/conf:/etc/letsencrypt:ro
      - ./certbot/www:/var/www/certbot:ro
    depends_on:
      - web
    networks:
      - coldmail_network
    restart: always

  db:
    image: mysql:8.0
    container_name: coldmail_db
    environment:
      MYSQL_DATABASE: ${DB_NAME}
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD}
      MYSQL_USER: ${DB_USER}
      MYSQL_PASSWORD: ${DB_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
      - ./mysql/my.cnf:/etc/mysql/conf.d/custom.cnf:ro
    networks:
      - coldmail_network
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: always

  redis:
    image: redis:7-alpine
    container_name: coldmail_redis
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    networks:
      - coldmail_network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    restart: always

  web:
    build:
      context: .
      dockerfile: Dockerfile
    image: ${DOCKER_USERNAME}/coldmail-app:${VERSION:-latest}
    container_name: coldmail_web
    command: gunicorn --bind 0.0.0.0:8000 --workers 4 --threads 2 --timeout 60 --max-requests 1000 --max-requests-jitter 50 coldmail_project.wsgi:application
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/mediafiles
      - ./logs:/app/logs
    env_file:
      - .env.production
    environment:
      - DJANGO_SETTINGS_MODULE=coldmail_project.settings.prod
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - coldmail_network
    restart: always

  celery_worker:
    build:
      context: .
      dockerfile: Dockerfile
    image: ${DOCKER_USERNAME}/coldmail-app:${VERSION:-latest}
    container_name: coldmail_worker
    command: celery -A coldmail_project worker --loglevel=info --concurrency=4 --max-tasks-per-child=100
    volumes:
      - ./logs:/app/logs
    env_file:
      - .env.production
    environment:
      - DJANGO_SETTINGS_MODULE=coldmail_project.settings.prod
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - coldmail_network
    restart: always

  celery_beat:
    build:
      context: .
      dockerfile: Dockerfile
    image: ${DOCKER_USERNAME}/coldmail-app:${VERSION:-latest}
    container_name: coldmail_beat
    command: celery -A coldmail_project beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    volumes:
      - ./logs:/app/logs
    env_file:
      - .env.production
    environment:
      - DJANGO_SETTINGS_MODULE=coldmail_project.settings.prod
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - coldmail_network
    restart: always

volumes:
  mysql_data:
  redis_data:
  static_volume:
  media_volume:

networks:
  coldmail_network:
    driver: bridge
```

### 4. `Dockerfile` (개선 버전)
```dockerfile
# 멀티 스테이지 빌드
FROM python:3.12-slim as builder

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config && \
    rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# 프로덕션 이미지
FROM python:3.12-slim

WORKDIR /app

# 런타임 의존성만 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    netcat-traditional && \
    rm -rf /var/lib/apt/lists/*

# builder 스테이지에서 설치된 패키지 복사
COPY --from=builder /root/.local /root/.local

# PATH 설정
ENV PATH=/root/.local/bin:$PATH

# 프로젝트 파일 복사
COPY . .

# 정적 파일 디렉토리 생성
RUN mkdir -p /app/staticfiles /app/mediafiles /app/logs

# 엔트리포인트 실행 권한
RUN chmod +x /app/entrypoint.sh

# 비root 유저로 실행 (보안)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "coldmail_project.wsgi:application"]
```

### 5. `nginx/conf.d/coldmail.conf` (새 파일)
```nginx
upstream django {
    server web:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Let's Encrypt 인증
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    # HTTPS로 리다이렉트
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    client_max_body_size 100M;
    
    # SSL 인증서
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # SSL 설정
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # 정적 파일
    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias /app/mediafiles/;
        expires 7d;
    }
    
    # Django 애플리케이션
    location / {
        proxy_pass http://django;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $host;
        proxy_redirect off;
        
        # Timeout 설정
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check
    location /health/ {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

---

## 🚀 배포 프로세스

### Phase 1: 로컬에서 이미지 빌드 & 테스트

```bash
# 1. .dockerignore 생성
# 2. .env.production 생성 (실제 비밀번호 입력)
# 3. Nginx 설정 파일 생성

# 4. 이미지 빌드
docker build -t your-dockerhub-username/coldmail-app:v1.0 .

# 5. 로컬 테스트
docker-compose -f docker-compose.prod.yml up -d

# 6. 헬스 체크
curl http://localhost/health/
```

### Phase 2: Docker Hub에 푸시

```bash
# 1. Docker Hub 로그인
docker login

# 2. 이미지 태그
docker tag coldmail-app:v1.0 your-dockerhub-username/coldmail-app:v1.0
docker tag coldmail-app:v1.0 your-dockerhub-username/coldmail-app:latest

# 3. 푸시
docker push your-dockerhub-username/coldmail-app:v1.0
docker push your-dockerhub-username/coldmail-app:latest
```

### Phase 3: 리눅스 서버 배포

```bash
# 서버에서 실행

# 1. Docker 설치 (Ubuntu)
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker

# 2. 프로젝트 디렉토리 생성
mkdir -p ~/coldmail-prod
cd ~/coldmail-prod

# 3. 필요한 파일만 복사 (git clone 또는 scp)
# - docker-compose.prod.yml
# - .env.production
# - nginx/ 디렉토리
# - mysql/ 디렉토리 (my.cnf)

# 4. 환경 변수 설정
nano .env.production
# SECRET_KEY, DB_PASSWORD 등 실제 값으로 수정

# 5. Docker Hub에서 이미지 가져오기
docker pull your-dockerhub-username/coldmail-app:latest

# 6. 서비스 시작
docker-compose -f docker-compose.prod.yml up -d

# 7. 로그 확인
docker-compose -f docker-compose.prod.yml logs -f

# 8. 마이그레이션 확인
docker-compose exec web python manage.py showmigrations

# 9. 슈퍼유저 생성
docker-compose exec web python manage.py createsuperuser
```

---

## 🔍 배포 후 체크리스트

- [ ] 모든 컨테이너가 running 상태인가?
  ```bash
  docker-compose ps
  ```

- [ ] 데이터베이스 연결이 정상인가?
  ```bash
  docker-compose exec web python manage.py dbshell
  ```

- [ ] Celery Worker가 작동하는가?
  ```bash
  docker-compose exec celery_worker celery -A coldmail_project inspect active
  ```

- [ ] Celery Beat가 작동하는가?
  ```bash
  docker-compose logs celery_beat
  ```

- [ ] API가 정상 응답하는가?
  ```bash
  curl -H "Authorization: Token YOUR_TOKEN" https://yourdomain.com/api/v1/campaigns/
  ```

- [ ] 정적 파일이 로드되는가?
  ```bash
  curl https://yourdomain.com/static/admin/css/base.css
  ```

- [ ] SSL 인증서가 유효한가?
  ```bash
  curl -I https://yourdomain.com
  ```

- [ ] 로그가 기록되는가?
  ```bash
  docker-compose exec web ls -la /app/logs/
  ```

---

## 🔐 보안 체크리스트

- [ ] SECRET_KEY가 충분히 강력하고 고유한가?
- [ ] DEBUG=False로 설정되었는가?
- [ ] ALLOWED_HOSTS가 실제 도메인으로 제한되었는가?
- [ ] 데이터베이스 비밀번호가 강력한가?
- [ ] .env 파일이 .gitignore에 포함되었는가?
- [ ] SSL/TLS가 활성화되었는가?
- [ ] CSRF 보호가 활성화되었는가?
- [ ] 불필요한 포트가 닫혀있는가?
- [ ] 컨테이너가 비root 유저로 실행되는가?

---

## 📊 모니터링 설정 (선택)

### Prometheus + Grafana

```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - coldmail_network

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - coldmail_network
```

---

## 🆘 문제 해결

### 컨테이너가 시작되지 않을 때
```bash
docker-compose logs <service-name>
```

### 데이터베이스 연결 오류
```bash
docker-compose exec db mysql -u root -p
# 연결 테스트
```

### Celery Worker가 작동하지 않을 때
```bash
docker-compose exec celery_worker celery -A coldmail_project inspect ping
```

### 정적 파일이 로드되지 않을 때
```bash
docker-compose exec web python manage.py collectstatic --noinput
```

---

## 📞 다음 단계

1. **즉시 작업**: 보안 설정 (.env.production, .dockerignore)
2. **배포 전**: Nginx 설정, docker-compose.prod.yml
3. **배포 후**: 모니터링, 백업, 로깅 설정
4. **장기**: 성능 최적화, CDN 연동, 오토스케일링

---

## 📚 참고 문서

- [Django Deployment Checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Nginx Configuration](https://nginx.org/en/docs/)
- [Let's Encrypt](https://letsencrypt.org/getting-started/)
