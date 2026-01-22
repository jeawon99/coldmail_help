# Stage 7 완료: Worker (내부) + 발송 결과 저장 ✅

## 📋 구현 내용

### 1. Celery 설정
- **coldmail_project/celery.py**: Celery 앱 초기화
- **coldmail_project/settings/base.py**: Celery 설정 추가
- **requirements.txt**: celery==5.4.0, redis==5.2.1 추가

### 2. 이메일 모델
- **campaigns/models.py**:
  - `EmailMessage`: 발송된 이메일 메타데이터 (SendJob과 1:1)
  - `EmailEvent`: 이메일 이벤트 로그 (sent, opened, clicked, etc.)

### 3. Celery Tasks
- **campaigns/tasks.py**:
  - `send_single_email_task`: 단일 이메일 발송
    - 중복 발송 방지 (locked_at)
    - 템플릿 렌더링 (Jinja2)
    - SMTP 발송
    - EmailMessage 생성
    - 실패 재시도 (최대 3번)
  - `send_due_jobs_task`: 예약된 잡 스캔 및 큐잉

### 4. Management Command
- **campaigns/management/commands/send_due_jobs.py**:
  - `python manage.py send_due_jobs`: 예약 잡 스캔
  - `--async` 옵션: Celery 태스크로 비동기 실행

### 5. Docker Compose
- **docker-compose.dev.yml**: 개발용 (Redis + Celery Worker + Beat + Flower)
- **docker-compose.yml**: 배포용 (전체 서비스)

### 6. 테스트
- **test_stage7_worker.py**: 전체 워크플로우 테스트

## 🚀 사용 방법

### 개발 환경

#### 1. Redis 시작 (Docker)
```bash
docker-compose -f docker-compose.dev.yml up -d redis
```

#### 2. Celery Worker 시작
```bash
# 터미널 1: Celery Worker
celery -A coldmail_project worker --loglevel=info --concurrency=2

# 터미널 2: Celery Beat (선택사항)
celery -A coldmail_project beat --loglevel=info

# 터미널 3: Flower 모니터링 (선택사항)
celery -A coldmail_project flower --port=5555
# http://localhost:5555
```

#### 3. 발송 잡 실행
```bash
# 예약된 잡 스캔 및 발송
python manage.py send_due_jobs
```

#### 4. 테스트
```bash
python test_stage7_worker.py
```

### 프로덕션 배포

```bash
# 전체 서비스 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f celery_worker

# 특정 서비스 재시작
docker-compose restart celery_worker
```

## 🔍 주요 기능

### 1. 중복 발송 방지
- `SendJob.locked_at` 필드로 락 관리
- `select_for_update()`로 DB 레벨 잠금
- `status = 'processing'` 상태 변경

### 2. 실패 재시도
- 최대 3번 재시도
- 재시도 간격: 60초 * 시도 횟수
- `attempt_count` 증가
- `last_error` 기록

### 3. 발송 결과 저장
- **EmailMessage**: 발송 메타데이터
  - from_email, to_email, subject, body
  - sent_at, smtp_response
  - 이벤트 추적 (opened_at, clicked_at, etc.)
- **EmailEvent**: 이벤트 로그
  - event_type (sent, opened, clicked, replied, bounced)
  - occurred_at, user_agent, ip_address

### 4. 템플릿 렌더링
- Jinja2 템플릿 엔진
- Lead 데이터 자동 주입
  - {{ channel_name }}
  - {{ subscriber_count }}
  - {{ email }}
  - {{ category }}
  - {{ description }}

## 📊 워크플로우

```
1. 캠페인 생성 (Stage 5)
   └─> 타겟 확정 (freeze-targets)

2. 발송 예약 (Stage 6)
   └─> SendJob 생성 (scheduled_at 설정)

3. 예약 잡 스캔 (Stage 7)
   └─> python manage.py send_due_jobs
       └─> scheduled_at <= now인 잡 조회
           └─> Celery 큐에 추가

4. Celery Worker 처리
   └─> send_single_email_task
       ├─> 락 획득 (locked_at)
       ├─> 템플릿 렌더링
       ├─> SMTP 발송
       ├─> EmailMessage 생성
       ├─> SendJob.status = 'sent'
       └─> 실패 시 재시도

5. 발송 결과 확인
   └─> GET /campaigns/{id}/jobs/
       └─> status: sent/failed/processing
```

## 🎯 완료 기준

✅ **중복 발송 방지 (locking)**
- `locked_at` 필드로 처리 중인 잡 추적
- `select_for_update()`로 동시성 제어
- Celery 워커 간 경쟁 조건 방지

✅ **실패 재시도 (attempt_count, last_error)**
- 최대 3번 자동 재시도
- 재시도 간격 증가 (60초, 120초, 180초)
- `last_error`에 실패 사유 기록
- `attempt_count` 증가

✅ **발송 결과 저장 (email_message/event)**
- EmailMessage: 발송된 이메일 전체 메타데이터
- EmailEvent: 이벤트 타임라인 기록
- SendJob 상태 업데이트 (scheduled → processing → sent/failed)

## 📝 환경 변수

`.env` 파일 예시:
```env
# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Email
EMAIL_HOST=smtp.larksuite.com
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-password
```

## 🔧 문제 해결

### Celery Worker가 태스크를 처리하지 않을 때
```bash
# Worker 로그 확인
celery -A coldmail_project worker --loglevel=debug

# Redis 연결 확인
redis-cli ping
```

### Redis 연결 실패
```bash
# Docker Redis 시작
docker-compose -f docker-compose.dev.yml up -d redis

# 로그 확인
docker-compose -f docker-compose.dev.yml logs redis
```

### 태스크가 큐에만 쌓이고 처리되지 않을 때
```bash
# Active 태스크 확인
celery -A coldmail_project inspect active

# 큐 초기화 (주의: 모든 태스크 삭제)
celery -A coldmail_project purge
```

## 📚 다음 단계

- Stage 8: 통계 및 대시보드
- Stage 9: 이메일 답장 수신 및 분석
- Stage 10: A/B 테스트 및 최적화

---

**Stage 7 완료!** 이제 실제 이메일 발송 파이프라인이 동작합니다! 🎉
