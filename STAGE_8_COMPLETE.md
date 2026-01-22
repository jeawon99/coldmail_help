# Stage 8: 이벤트 트래킹 완료 ✅

## 📋 구현 내역

### 1. 이벤트 모델 (기존 활용)
- **EmailEvent** 모델 활용
  - `event_type`: opened_pixel, clicked, replied, bounced
  - `event_at`: 이벤트 발생 시간
  - `meta`: JSON 필드 (user_agent, IP, URL 등)

### 2. 트래킹 엔드포인트

#### 오픈 픽셀 트래킹
```
GET /api/v1/campaigns/t/open/{message_id}.png
```
- 1x1 투명 PNG 반환
- `opened_pixel` 이벤트 기록
- **중복 방지**: 같은 메시지의 첫 오픈만 기록
- 메타데이터: user_agent, IP, referer

#### 클릭 트래킹
```
GET /api/v1/campaigns/t/click/{message_id}?u=https://example.com
```
- `clicked` 이벤트 기록 후 원본 URL로 리다이렉트
- **중복 허용**: 모든 클릭 기록
- 메타데이터: clicked_url, user_agent, IP, referer

### 3. 이벤트 조회 API

#### 메시지별 이벤트 조회
```
GET /api/v1/campaigns/messages/{message_id}/events/
GET /api/v1/campaigns/messages/{message_id}/events/?event_type=opened_pixel
```

**응답 예시:**
```json
{
  "status": "success",
  "data": {
    "count": 3,
    "results": [
      {
        "id": "uuid",
        "email_message": "uuid",
        "event_type": "opened_pixel",
        "event_at": "2026-01-22T14:30:00Z",
        "meta": {
          "user_agent": "Mozilla/5.0...",
          "ip_address": "192.168.1.1",
          "referer": ""
        }
      },
      {
        "id": "uuid",
        "email_message": "uuid",
        "event_type": "clicked",
        "event_at": "2026-01-22T14:31:00Z",
        "meta": {
          "clicked_url": "https://example.com/product",
          "user_agent": "Mozilla/5.0...",
          "ip_address": "192.168.1.1"
        }
      }
    ]
  }
}
```

#### 캠페인별 이벤트 조회
```
GET /api/v1/campaigns/campaigns/{campaign_id}/events/
GET /api/v1/campaigns/campaigns/{campaign_id}/events/?event_type=clicked
GET /api/v1/campaigns/campaigns/{campaign_id}/events/?from_date=2026-01-01&to_date=2026-01-31
```

**쿼리 파라미터:**
- `event_type`: opened_pixel, clicked, replied, bounced
- `from_date`: 시작 날짜 (YYYY-MM-DD)
- `to_date`: 종료 날짜 (YYYY-MM-DD)

**응답 예시:**
```json
{
  "status": "success",
  "data": {
    "count": 150,
    "results": [
      {
        "id": "uuid",
        "email_message": "uuid",
        "email_to": "user@example.com",
        "campaign_id": "uuid",
        "campaign_name": "Q1 캠페인",
        "event_type": "opened_pixel",
        "event_at": "2026-01-22T14:30:00Z",
        "meta": {...}
      }
    ]
  }
}
```

### 4. 이벤트 중복 처리 정책

#### opened_pixel (오픈)
- **최초 1회만 기록**
- 같은 EmailMessage의 opened_pixel 이벤트가 이미 존재하면 기록하지 않음
- 코드 위치: `tracking_views.py::OpenPixelView`

```python
existing_open = EmailEvent.objects.filter(
    email_message=email_message,
    event_type='opened_pixel'
).exists()

if not existing_open:
    # 이벤트 기록
    EmailEvent.objects.create(...)
```

#### clicked (클릭)
- **모든 클릭 기록**
- 같은 링크를 여러 번 클릭해도 모두 기록
- 각 클릭의 메타데이터에 clicked_url 포함

#### replied, bounced
- 외부 시스템(이메일 서버, webhook)에서 전송
- 현재는 수동 기록 가능

### 5. 메타데이터 수집

모든 이벤트에 다음 정보 저장:
- `user_agent`: HTTP User-Agent 헤더
- `ip_address`: 클라이언트 IP (X-Forwarded-For 고려)
- `referer`: HTTP Referer 헤더
- `clicked_url`: (클릭 이벤트만) 클릭한 URL

### 6. 이메일에 트래킹 코드 삽입

발송 시 이메일 본문에 자동 삽입:

#### 오픈 픽셀 (HTML 이메일 끝에 추가)
```html
<img src="https://yourdomain.com/api/v1/campaigns/t/open/{message_id}.png" 
     width="1" height="1" style="display:none" />
```

#### 링크 클릭 트래킹 (링크 URL 변환)
```html
<!-- 원본 -->
<a href="https://example.com/product">상품 보기</a>

<!-- 변환 후 -->
<a href="https://yourdomain.com/api/v1/campaigns/t/click/{message_id}?u=https%3A%2F%2Fexample.com%2Fproduct">상품 보기</a>
```

**참고**: 실제 URL 변환은 `campaigns/tasks.py`의 `send_single_email_task`에서 구현 필요

## 🧪 테스트 방법

### 1. Django 서버 실행
```bash
python manage.py runserver
```

### 2. EmailMessage ID 확인
```bash
python manage.py shell
```
```python
from campaigns.models import SendJob
job = SendJob.objects.filter(status='sent').first()
if job and hasattr(job, 'email_message'):
    msg = job.email_message
    print(f"EmailMessage ID: {msg.id}")
```

### 3. 오픈 픽셀 테스트
```bash
# 브라우저나 curl로 접근
curl http://127.0.0.1:8000/api/v1/campaigns/t/open/{message_id}.png

# 이벤트 확인
python manage.py shell
```
```python
from campaigns.models import EmailMessage, EmailEvent
msg = EmailMessage.objects.get(id='...')
opens = EmailEvent.objects.filter(email_message=msg, event_type='opened_pixel')
print(f"오픈 이벤트: {opens.count()}개")
for event in opens:
    print(f"  - {event.event_at}: {event.meta}")
```

### 4. 클릭 트래킹 테스트
```bash
curl -L http://127.0.0.1:8000/api/v1/campaigns/t/click/{message_id}?u=https://example.com
```

### 5. 이벤트 조회 API 테스트
```bash
# 메시지 이벤트
curl -H "Authorization: Bearer {token}" \
  http://127.0.0.1:8000/api/v1/campaigns/messages/{message_id}/events/

# 캠페인 이벤트 (오픈만)
curl -H "Authorization: Bearer {token}" \
  "http://127.0.0.1:8000/api/v1/campaigns/campaigns/{campaign_id}/events/?event_type=opened_pixel"

# 캠페인 이벤트 (기간 필터)
curl -H "Authorization: Bearer {token}" \
  "http://127.0.0.1:8000/api/v1/campaigns/campaigns/{campaign_id}/events/?from_date=2026-01-01&to_date=2026-01-31"
```

### 6. 자동 테스트 스크립트
```bash
python test_stage8_events.py
```

## 📁 파일 구조

```
campaigns/
├── models.py                     # EmailEvent 모델 (기존)
├── serializers_events.py         # 이벤트 시리얼라이저 (신규)
├── views.py                      # CampaignViewSet.get_events() 추가
├── views_messages.py             # EmailMessageViewSet (신규)
├── tracking_views.py             # 오픈/클릭 트래킹 View (신규)
├── urls.py                       # 트래킹 URL 추가
└── tasks.py                      # (TODO) 이메일 발송 시 트래킹 코드 삽입

test_stage8_events.py             # 테스트 스크립트 (신규)
STAGE_8_COMPLETE.md               # 이 문서
```

## ✅ 완료 기준 체크리스트

- [x] **이벤트 조회 API**
  - [x] GET /messages/{id}/events
  - [x] GET /campaigns/{id}/events
  - [x] 이벤트 타입 필터링 (event_type)
  - [x] 날짜 범위 필터링 (from_date, to_date)

- [x] **오픈 픽셀 트래킹**
  - [x] GET /t/open/{messageId}.png
  - [x] 1x1 투명 PNG 반환
  - [x] opened_pixel 이벤트 기록
  - [x] 중복 방지 (첫 오픈만 기록)

- [x] **클릭 트래킹**
  - [x] GET /t/click/{messageId}?u=...
  - [x] clicked 이벤트 기록
  - [x] 원본 URL로 리다이렉트
  - [x] 중복 허용 (모든 클릭 기록)

- [x] **메타데이터 저장**
  - [x] user_agent
  - [x] IP 주소
  - [x] referer
  - [x] clicked_url (클릭 이벤트)

- [ ] **이메일 트래킹 코드 삽입** (TODO)
  - [ ] HTML 이메일에 오픈 픽셀 추가
  - [ ] 링크 URL을 클릭 트래킹 URL로 변환

## 🔄 다음 단계 (Stage 9)

트래킹 코드를 자동으로 이메일에 삽입하는 기능 구현:

1. **오픈 픽셀 자동 삽입**
   - `campaigns/tasks.py`의 `send_single_email_task` 수정
   - HTML 본문 끝에 `<img>` 태그 추가

2. **링크 URL 자동 변환**
   - BeautifulSoup으로 HTML 파싱
   - 모든 `<a href="...">` 태그의 URL을 트래킹 URL로 변환
   - 원본 URL을 `u` 파라미터로 인코딩

## 📊 예상 데이터 흐름

```
1. 이메일 발송
   ↓
2. 수신자가 이메일 열람
   ↓
3. 브라우저가 오픈 픽셀 로드
   → GET /t/open/{message_id}.png
   → EmailEvent 생성 (opened_pixel)
   ↓
4. 수신자가 링크 클릭
   ↓
5. 브라우저가 트래킹 URL 요청
   → GET /t/click/{message_id}?u=...
   → EmailEvent 생성 (clicked)
   → 원본 URL로 리다이렉트
   ↓
6. 분석 대시보드에서 이벤트 조회
   → GET /campaigns/{id}/events/
   → 오픈율, 클릭률 등 통계 생성
```

## 🎉 Stage 8 완료!

모든 이벤트 트래킹 기능이 구현되었습니다. 다음은 이메일 발송 시 트래킹 코드를 자동으로 삽입하는 기능을 구현하면 완전한 이메일 분석 시스템이 완성됩니다!
