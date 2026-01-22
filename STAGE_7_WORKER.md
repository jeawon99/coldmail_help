# Stage 7: Worker (내부) + 발송 결과 저장

## 개발 환경 설정

### 1. 개발용 Docker Compose 실행

개발 환경에서 Redis와 Celery Worker를 Docker로 실행하는 방법:

```bash
# Redis + Celery Worker + Celery Beat + Flower 실행
docker-compose -f docker-compose.dev.yml up -d

# 로그 확인
docker-compose -f docker-compose.dev.yml logs -f

# 특정 서비스만 실행
docker-compose -f docker-compose.dev.yml up -d redis  # Redis만
docker-compose -f docker-compose.dev.yml up -d celery_worker  # Worker만

# 중지
docker-compose -f docker-compose.dev.yml down

# 볼륨까지 삭제 (Redis 데이터 초기화)
docker-compose -f docker-compose.dev.yml down -v
```

### 2. 로컬에서 직접 실행 (Docker 없이)

#### 2.1 Redis 설치 및 실행

**Windows (WSL 사용):**
```bash
# WSL에서 Redis 설치
sudo apt-get update
sudo apt-get install redis-server

# Redis 시작
sudo service redis-server start

# 연결 테스트
redis-cli ping  # PONG 응답 확인
```

**macOS:**
```bash
brew install redis
brew services start redis
```

#### 2.2 Celery Worker 실행

```bash
# 환경 활성화
conda activate coldmail

# Celery Worker 실행 (터미널 1)
celery -A coldmail_project worker --loglevel=info --concurrency=2

# Celery Beat 실행 (터미널 2 - 선택사항)
celery -A coldmail_project beat --loglevel=info

# Flower 모니터링 실행 (터미널 3 - 선택사항)
celery -A coldmail_project flower --port=5555
# 브라우저에서 http://localhost:5555 접속
```

### 3. 발송 잡 실행

```bash
# 환경 활성화
conda activate coldmail

# 예약된 잡 스캔 및 발송 큐에 추가
python manage.py send_due_jobs

# 비동기 실행 (Celery 태스크로)
python manage.py send_due_jobs --async
```

### 4. 테스트

```bash
# Stage 7 테스트 실행
python test_stage7_worker.py
```

## 프로덕션 배포

### 전체 서비스 실행 (Web + DB + Redis + Celery)

```bash
# 모든 서비스 실행
docker-compose up -d

# 특정 서비스만 재시작
docker-compose restart celery_worker

# 로그 확인
docker-compose logs -f celery_worker

# 중지
docker-compose down
```

## 아키텍처

```
┌──────────────┐
│ Django Web   │
└──────┬───────┘
       │
       ├─── HTTP API (발송 예약)
       │
       ├─── manage.py send_due_jobs (예약 잡 스캔)
       │         │
       │         v
       │   ┌──────────┐
       │   │  Redis   │  (메시지 브로커)
       │   └────┬─────┘
       │        │
       │        v
       │   ┌──────────────┐
       └───┤ Celery Worker│ (이메일 발송)
           └──────┬───────┘
                  │
                  v
            ┌──────────────┐
            │ SMTP Server  │
            └──────────────┘
```

## 주요 기능

### 1. 중복 발송 방지
- `SendJob.locked_at` 필드로 락 관리
- `select_for_update()`로 DB 레벨 잠금
- `processing` 상태로 변경

### 2. 실패 재시도
- 최대 3번 재시도
- 재시도 간격: 60초 * 시도 횟수
- `attempt_count` 증가
- `last_error` 기록

### 3. 발송 결과 저장
- `EmailMessage`: 발송된 이메일 메타데이터
- `EmailEvent`: 이벤트 로그 (sent, opened, clicked, etc.)
- `SendJob.status`: scheduled → processing → sent/failed

## 환경 변수

`.env` 파일에 추가:
```
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## 모니터링

### Flower (Celery 모니터링)
```bash
# Flower 실행
celery -A coldmail_project flower --port=5555

# 브라우저에서 접속
http://localhost:5555
```

### Redis 모니터링
```bash
# Redis CLI
redis-cli

# 큐 확인
KEYS celery*
LLEN celery

# 모니터링
MONITOR
```

## 문제 해결

### Celery Worker가 태스크를 처리하지 않을 때
```bash
# Worker 재시작
docker-compose restart celery_worker

# 또는 로컬
celery -A coldmail_project worker --loglevel=debug
```

### Redis 연결 실패
```bash
# Redis 상태 확인
redis-cli ping

# Docker Redis 재시작
docker-compose restart redis
```

### 태스크가 큐에 쌓이기만 하고 처리되지 않을 때
```bash
# Celery Worker가 실행 중인지 확인
celery -A coldmail_project inspect active

# 큐 초기화 (주의: 모든 태스크 삭제)
celery -A coldmail_project purge
```
