# Cold Mail API 사용 가이드

## 📋 목차
1. [인증 (Authentication)](#인증)
2. [캠페인 워크플로우](#캠페인-워크플로우)
3. [주요 API 사용법](#주요-api-사용법)
4. [에러 처리](#에러-처리)

---

## 🔐 인증

### 1. JWT 토큰 발급
```http
POST /api/v1/auth/token/
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

**응답:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**사용:**
- `access` 토큰을 Authorization 헤더에 포함: `Authorization: Bearer {access_token}`
- access 토큰은 1시간 유효

### 2. 토큰 갱신
```http
POST /api/v1/auth/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

## 📧 캠페인 워크플로우

### 전체 흐름 (7단계)

```
1. 리드 등록 → 2. 템플릿 생성 → 3. 세그먼트 생성 
→ 4. 캠페인 생성 → 5. 타겟 확정 → 6. 발송 예약 → 7. 캠페인 시작
```

#### Step 1: 리드 등록
```http
POST /api/v1/leads/
Content-Type: application/json

{
  "channel_name": "테크유튜버",
  "channel_url": "https://youtube.com/@tech",
  "primary_email": "tech@example.com",
  "subscriber_count": 100000,
  "keywords_raw": "기술, IT, 리뷰"
}
```

**대량 등록 (CSV/JSON):**
```http
POST /api/v1/leads/import/
Content-Type: multipart/form-data

file: leads.csv (또는 leads.json)
format: "csv" (또는 "json")
```

#### Step 2: 템플릿 생성
```http
POST /api/v1/templates/
Content-Type: application/json

{
  "name": "협업 제안 템플릿",
  "purpose": "partnership",
  "is_active": true
}
```

**템플릿 버전 추가:**
```http
POST /api/v1/templates/{template_id}/versions/
Content-Type: application/json

{
  "subject_tpl": "[협업 제안] {{name}}님, 같이 프로젝트 하실래요?",
  "body_tpl": "안녕하세요 {{name}}님,\n\n{{company}}에서 {{position}}를 맡고 있는 {{sender_name}}입니다...",
  "format": "html",
  "cta_type": "reply",
  "personalization_level": 2
}
```

**사용 가능한 변수:**
- `{{name}}`: 채널 이름
- `{{company}}`: 회사명
- `{{position}}`: 직책
- `{{sender_name}}`: 발신자 이름

#### Step 3: 세그먼트 생성
```http
POST /api/v1/segments/
Content-Type: application/json

{
  "name": "10만 구독자 이상 테크유튜버",
  "description": "기술 리뷰 중심 채널",
  "filter_json": {
    "all": [
      {
        "field": "subscriber_count",
        "op": "gte",
        "value": 100000
      },
      {
        "field": "tags",
        "op": "in",
        "value": ["기술", "IT"]
      }
    ],
    "not": [
      {
        "field": "status",
        "op": "eq",
        "value": "do_not_contact"
      }
    ]
  }
}
```

**세그먼트 미리보기:**
```http
POST /api/v1/segments/{segment_id}/preview/
```

#### Step 4: 캠페인 생성
```http
POST /api/v1/campaigns/
Content-Type: application/json

{
  "name": "2024년 1월 협업 제안",
  "segment": "{segment_id}",
  "daily_cap": 50,
  "status": "draft"
}
```

#### Step 5: 타겟 확정 (스냅샷 고정)
```http
POST /api/v1/campaigns/{campaign_id}/freeze-targets/
```

**이유:** 세그먼트는 동적이므로, 발송 시점에 타겟을 스냅샷으로 고정합니다.

**응답:**
```json
{
  "campaign_id": "uuid",
  "total_targets": 150,
  "created_at": "2024-01-23T10:00:00Z"
}
```

#### Step 6: 발송 잡 예약
```http
POST /api/v1/campaigns/{campaign_id}/schedule/
Content-Type: application/json

{
  "template_version": "{template_version_id}",
  "scheduled_at": "2024-01-24T09:00:00+09:00"
}
```

**주의:** `scheduled_at`는 미래 시간이어야 합니다!

#### Step 7: 캠페인 시작
```http
POST /api/v1/campaigns/{campaign_id}/start/
```

**상태 변화:** `draft` → `running`

---

## 🔧 주요 API 사용법

### 리드 (Leads)

#### 리드 목록 조회 (필터링, 검색, 정렬)
```http
GET /api/v1/leads/?search=tech&ordering=-subscriber_count&status=active
```

**쿼리 파라미터:**
- `search`: 채널명, URL, 이메일 검색
- `status`: active, do_not_contact
- `tags`: 태그 ID (콤마 구분)
- `subscriber_count__gte`: 최소 구독자 수
- `subscriber_count__lte`: 최대 구독자 수
- `ordering`: created_at, -created_at, subscriber_count, -subscriber_count

#### 리드에 태그 추가
```http
POST /api/v1/leads/{lead_id}/tags/
Content-Type: application/json

{
  "tag_ids": ["tag_uuid_1", "tag_uuid_2"]
}
```

#### 리드에서 태그 제거
```http
DELETE /api/v1/leads/{lead_id}/tags/{tag_id}/
```

---

### 캠페인 (Campaigns)

#### 캠페인 목록 조회
```http
GET /api/v1/campaigns/?status=running&ordering=-created_at
```

#### 캠페인 상태 변경

**시작:**
```http
POST /api/v1/campaigns/{campaign_id}/start/
```

**일시정지:**
```http
POST /api/v1/campaigns/{campaign_id}/pause/
```

**종료:**
```http
POST /api/v1/campaigns/{campaign_id}/finish/
```

#### 타겟 수동 추가/제거

**추가:**
```http
POST /api/v1/campaigns/{campaign_id}/targets/add/
Content-Type: application/json

{
  "lead_ids": ["lead_uuid_1", "lead_uuid_2"]
}
```

**제거:**
```http
POST /api/v1/campaigns/{campaign_id}/targets/remove/
Content-Type: application/json

{
  "target_ids": ["target_uuid_1", "target_uuid_2"]
}
```

---

### 발송 잡 (Jobs)

#### 발송 잡 목록 조회
```http
GET /api/v1/campaigns/{campaign_id}/jobs/
```

#### 발송 잡 재예약 (시간 변경)
```http
PATCH /api/v1/jobs/{job_id}/reschedule/
Content-Type: application/json

{
  "scheduled_at": "2024-01-25T10:00:00+09:00"
}
```

#### 발송 잡 재시도
```http
POST /api/v1/jobs/{job_id}/retry/
```

**사용 시나리오:**
- 예약 시간이 지났는데 실행 안 됨
- 실패한 작업 재실행

#### 발송 잡 취소
```http
POST /api/v1/jobs/{job_id}/cancel/
```

---

### 분석 (Analytics)

#### 캠페인 개요 분석
```http
GET /api/v1/campaigns/{campaign_id}/analytics/overview/
```

**응답:**
```json
{
  "total_sent": 150,
  "total_delivered": 145,
  "total_opened": 80,
  "total_clicked": 30,
  "total_replied": 10,
  "total_bounced": 5,
  "open_rate": 55.17,
  "click_rate": 20.69,
  "reply_rate": 6.90,
  "bounce_rate": 3.45
}
```

#### 시계열 분석
```http
GET /api/v1/campaigns/{campaign_id}/analytics/timeseries/?interval=day
```

**쿼리 파라미터:**
- `interval`: hour, day, week, month

#### 템플릿별 성과 분석
```http
GET /api/v1/campaigns/{campaign_id}/analytics/templates/
```

#### 분류별 분석
```http
GET /api/v1/campaigns/{campaign_id}/analytics/breakdown/?breakdown_by=tags
```

**쿼리 파라미터:**
- `breakdown_by`: tags, subscriber_range

#### 응답 시간 분석
```http
GET /api/v1/campaigns/{campaign_id}/analytics/response-time/
```

---

### 템플릿 (Templates)

#### 템플릿 목록 조회
```http
GET /api/v1/templates/?is_active=true&purpose=partnership
```

#### 템플릿 버전 미리보기 (렌더링)
```http
POST /api/v1/template-versions/{version_id}/render-preview/
Content-Type: application/json

{
  "context": {
    "name": "테크유튜버",
    "company": "CLFY",
    "position": "마케팅 매니저",
    "sender_name": "김재원"
  }
}
```

**응답:**
```json
{
  "subject": "[협업 제안] 테크유튜버님, 같이 프로젝트 하실래요?",
  "body": "안녕하세요 테크유튜버님,\n\nCLFY에서 마케팅 매니저를 맡고 있는 김재원입니다..."
}
```

---

### 이벤트 (Events)

#### 캠페인 이벤트 조회
```http
GET /api/v1/campaigns/{campaign_id}/events/?event_type=opened&page=1
```

**쿼리 파라미터:**
- `event_type`: sent, delivered, opened, clicked, replied, bounced
- `page`: 페이지 번호
- `page_size`: 페이지 크기 (기본: 20)

#### 메시지별 이벤트 조회
```http
GET /api/v1/messages/{message_id}/events/
```

---

### 세그먼트 (Segments)

#### 세그먼트 생성 (동적 필터)
```http
POST /api/v1/segments/
Content-Type: application/json

{
  "name": "Shorts 크리에이터 (1만~10만)",
  "description": "Shorts 콘텐츠 제작 유튜버",
  "filter_json": {
    "all": [
      {
        "field": "keywords_raw",
        "op": "contains_any",
        "value": ["shorts", "쇼츠", "숏폼"]
      },
      {
        "field": "subscriber_count",
        "op": ">=",
        "value": 10000
      },
      {
        "field": "subscriber_count",
        "op": "<=",
        "value": 100000
      },
      {
        "field": "primary_email",
        "op": "is_not_null"
      }
    ],
    "not": [
      {
        "field": "status",
        "op": "==",
        "value": "do_not_contact"
      }
    ]
  }
}
```

**filter_json 구조:**

| 필드 | 연산자 (op) | 설명 | 예시 |
|------|-------------|------|------|
| tags | in, not_in | 태그 포함 여부 | `{"field": "tags", "op": "in", "value": ["게임", "리뷰"]}` |
| subscriber_count | >=, <=, >, <, == | 구독자 수 비교 | `{"field": "subscriber_count", "op": ">=", "value": 50000}` |
| keywords_raw | contains_any | 키워드 포함 (OR) | `{"field": "keywords_raw", "op": "contains_any", "value": ["tech", "IT"]}` |
| primary_email | is_not_null, is_null | 이메일 존재 여부 | `{"field": "primary_email", "op": "is_not_null"}` |
| status | ==, in | 상태 비교 | `{"field": "status", "op": "==", "value": "active"}` |

#### 세그먼트 미리보기
```http
POST /api/v1/segments/{segment_id}/preview/
Content-Type: application/json

{
  "exclude_suppression": true,
  "exclude_do_not_contact": true,
  "sample_size": 10
}
```

**응답:**
```json
{
  "total_count": 347,
  "sample_leads": [
    {
      "id": "uuid",
      "channel_name": "Shorts 크리에이터",
      "subscriber_count": 25000,
      "primary_email": "creator@example.com",
      "tags": ["Shorts", "엔터테인먼트"],
      "status": "active"
    }
  ],
  "filter_summary": {
    "conditions_count": 5,
    "suppression_excluded": true,
    "do_not_contact_excluded": true
  }
}
```

#### 세그먼트 리드 Export
```http
GET /api/v1/segments/{segment_id}/export/?format=csv
```

**쿼리 파라미터:**
- `format`: csv, json (기본: csv)

**응답:** CSV 또는 JSON 파일 다운로드

---

### 메시지 (Messages)

#### 메시지 목록 조회
```http
GET /api/v1/messages/?campaign={campaign_id}&status=sent
```

**쿼리 파라미터:**
- `campaign`: 캠페인 ID 필터
- `status`: sent, delivered, bounced, failed
- `to_email`: 수신자 이메일 검색
- `ordering`: -sent_at, sent_at

**응답:**
```json
{
  "count": 150,
  "next": "https://coldmail.clfy.ai.kr/api/v1/messages/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "campaign": "campaign_uuid",
      "to_email": "recipient@example.com",
      "subject": "[협업 제안] 테크유튜버님",
      "status": "sent",
      "sent_at": "2024-01-23T10:30:00Z",
      "opened_at": "2024-01-23T14:20:00Z",
      "clicked_at": null,
      "replied_at": null
    }
  ]
}
```

#### 메시지 상세 조회
```http
GET /api/v1/messages/{message_id}/
```

**응답:**
```json
{
  "id": "uuid",
  "campaign": {
    "id": "campaign_uuid",
    "name": "2024년 1월 협업 제안"
  },
  "to_email": "recipient@example.com",
  "to_name": "테크유튜버",
  "subject": "[협업 제안] 테크유튜버님, 같이 프로젝트 하실래요?",
  "body": "안녕하세요 테크유튜버님...",
  "status": "sent",
  "sent_at": "2024-01-23T10:30:00Z",
  "opened_at": "2024-01-23T14:20:00Z",
  "clicked_at": null,
  "replied_at": null,
  "tracking_pixel_url": "https://coldmail.clfy.ai.kr/api/v1/t/open/uuid.png",
  "click_tracking_url": "https://coldmail.clfy.ai.kr/api/v1/t/click/uuid"
}
```

#### 메시지 이벤트 조회
```http
GET /api/v1/messages/{message_id}/events/
```

**응답:**
```json
{
  "count": 3,
  "results": [
    {
      "id": "event_uuid_1",
      "event_type": "sent",
      "timestamp": "2024-01-23T10:30:00Z",
      "metadata": {}
    },
    {
      "id": "event_uuid_2",
      "event_type": "delivered",
      "timestamp": "2024-01-23T10:30:15Z",
      "metadata": {}
    },
    {
      "id": "event_uuid_3",
      "event_type": "opened",
      "timestamp": "2024-01-23T14:20:30Z",
      "metadata": {
        "ip": "1.2.3.4",
        "user_agent": "Mozilla/5.0..."
      }
    }
  ]
}
```

---

### 태그 (Tags)

#### 태그 생성
```http
POST /api/v1/tags/
Content-Type: application/json

{
  "name": "기술",
  "color": "#FF5733"
}
```

#### 태그 목록 조회
```http
GET /api/v1/tags/
```

---

### 억제 목록 (Suppressions)

#### 억제 목록 추가 (차단)
```http
POST /api/v1/suppressions/
Content-Type: application/json

{
  "email": "blocked@example.com",
  "reason": "spam_complaint",
  "notes": "사용자가 스팸 신고함"
}
```

**reason 옵션:**
- `user_request`: 사용자 요청
- `spam_complaint`: 스팸 신고
- `hard_bounce`: 하드 바운스
- `unsubscribe`: 구독 취소
- `manual`: 수동 추가

---

## ⚠️ 에러 처리

### 일반적인 에러 응답 형식
```json
{
  "error": "에러 코드",
  "message": "에러 설명",
  "details": {}
}
```

### HTTP 상태 코드

| 코드 | 의미 | 예시 |
|------|------|------|
| 200 | 성공 | GET, PUT 성공 |
| 201 | 생성 성공 | POST 성공 |
| 204 | 성공 (응답 없음) | DELETE 성공 |
| 400 | 잘못된 요청 | 필수 필드 누락, 유효성 검증 실패 |
| 401 | 인증 실패 | 토큰 없음, 만료된 토큰 |
| 403 | 권한 없음 | 다른 사용자의 리소스 접근 |
| 404 | 리소스 없음 | 존재하지 않는 ID |
| 409 | 충돌 | 중복 이메일, 잘못된 상태 전환 |
| 500 | 서버 에러 | 내부 서버 오류 |

### 자주 발생하는 에러

#### 1. 토큰 만료
```json
{
  "detail": "Given token not valid for any token type",
  "code": "token_not_valid"
}
```
**해결:** `/api/v1/auth/token/refresh/`로 토큰 갱신

#### 2. 캠페인 상태 오류
```json
{
  "error": "invalid_state_transition",
  "message": "캠페인이 이미 종료되었습니다."
}
```
**해결:** 캠페인 상태 확인 후 올바른 액션 수행

#### 3. 타겟 미확정 상태에서 발송 시도
```json
{
  "error": "targets_not_frozen",
  "message": "타겟을 먼저 확정해주세요."
}
```
**해결:** `POST /api/v1/campaigns/{id}/freeze-targets/` 먼저 호출

---

## 💡 Best Practices

### 1. 페이지네이션 활용
```http
GET /api/v1/leads/?page=2&page_size=50
```

### 2. 필터링으로 필요한 데이터만 가져오기
```http
GET /api/v1/campaigns/?status=running&segment={segment_id}
```

### 3. 검색 최적화
```http
GET /api/v1/leads/?search=tech&fields=id,channel_name,primary_email
```

### 4. 정렬 활용
```http
GET /api/v1/campaigns/?ordering=-created_at,name
```

### 5. CORS 설정 확인
모든 API 요청 헤더에 다음 포함:
```
Authorization: Bearer {access_token}
Content-Type: application/json
Origin: https://your-frontend-domain.com
```

---

## 📞 문의

- API 문서: `https://coldmail.clfy.ai.kr/api/docs/`
- Redoc: `https://coldmail.clfy.ai.kr/api/redoc/`
- Health Check: `https://coldmail.clfy.ai.kr/api/v1/health/`

---

## 🎯 실전 예시 (Frontend 구현 가이드)

### 예시 1: 캠페인 생성 플로우 (React)

```javascript
// 1. 리드 목록 조회
const fetchLeads = async () => {
  const response = await fetch('https://coldmail.clfy.ai.kr/api/v1/leads/?page_size=100', {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    }
  });
  const data = await response.json();
  return data.results;
};

// 2. 세그먼트 생성
const createSegment = async (segmentData) => {
  const response = await fetch('https://coldmail.clfy.ai.kr/api/v1/segments/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      name: "10만 구독자 이상 게임 유튜버",
      description: "게임 콘텐츠 중심 채널",
      filter_json: {
        all: [
          { field: "tags", op: "in", value: ["게임"] },
          { field: "subscriber_count", op: ">=", value: 100000 },
          { field: "primary_email", op: "is_not_null" }
        ]
      }
    })
  });
  return await response.json();
};

// 3. 세그먼트 미리보기
const previewSegment = async (segmentId) => {
  const response = await fetch(`https://coldmail.clfy.ai.kr/api/v1/segments/${segmentId}/preview/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      sample_size: 10
    })
  });
  const data = await response.json();
  console.log(`타겟 수: ${data.total_count}명`);
  return data;
};

// 4. 캠페인 생성
const createCampaign = async (segmentId) => {
  const response = await fetch('https://coldmail.clfy.ai.kr/api/v1/campaigns/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      name: "2024년 2월 게임 유튜버 협업",
      segment: segmentId,
      daily_cap: 50,
      status: "draft"
    })
  });
  return await response.json();
};

// 5. 타겟 확정
const freezeTargets = async (campaignId) => {
  const response = await fetch(`https://coldmail.clfy.ai.kr/api/v1/campaigns/${campaignId}/freeze-targets/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
  return await response.json();
};

// 6. 발송 예약
const scheduleJob = async (campaignId, templateVersionId) => {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  tomorrow.setHours(9, 0, 0, 0);

  const response = await fetch(`https://coldmail.clfy.ai.kr/api/v1/campaigns/${campaignId}/schedule/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      template_version: templateVersionId,
      scheduled_at: tomorrow.toISOString()
    })
  });
  return await response.json();
};

// 7. 캠페인 시작
const startCampaign = async (campaignId) => {
  const response = await fetch(`https://coldmail.clfy.ai.kr/api/v1/campaigns/${campaignId}/start/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
  return await response.json();
};

// 전체 플로우 실행
const createFullCampaign = async () => {
  try {
    // 1. 세그먼트 생성
    const segment = await createSegment();
    console.log('세그먼트 생성:', segment.id);

    // 2. 미리보기
    const preview = await previewSegment(segment.id);
    console.log('예상 타겟:', preview.total_count);

    // 3. 캠페인 생성
    const campaign = await createCampaign(segment.id);
    console.log('캠페인 생성:', campaign.id);

    // 4. 타겟 확정
    const frozen = await freezeTargets(campaign.id);
    console.log('타겟 확정:', frozen.total_targets);

    // 5. 발송 예약 (템플릿 ID는 미리 생성되어 있다고 가정)
    const job = await scheduleJob(campaign.id, 'template_version_uuid');
    console.log('발송 예약:', job.scheduled_at);

    // 6. 캠페인 시작
    await startCampaign(campaign.id);
    console.log('캠페인 시작 완료!');

    return campaign;
  } catch (error) {
    console.error('캠페인 생성 실패:', error);
    throw error;
  }
};
```

### 예시 2: 실시간 분석 대시보드

```javascript
// 캠페인 개요 조회
const fetchCampaignOverview = async (campaignId) => {
  const response = await fetch(
    `https://coldmail.clfy.ai.kr/api/v1/campaigns/${campaignId}/analytics/overview/`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );
  return await response.json();
};

// 시계열 데이터 조회
const fetchTimeseries = async (campaignId, interval = 'day') => {
  const response = await fetch(
    `https://coldmail.clfy.ai.kr/api/v1/campaigns/${campaignId}/analytics/timeseries/?interval=${interval}`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );
  return await response.json();
};

// React 컴포넌트 예시
const CampaignDashboard = ({ campaignId }) => {
  const [overview, setOverview] = useState(null);
  const [timeseries, setTimeseries] = useState([]);

  useEffect(() => {
    const loadData = async () => {
      const overviewData = await fetchCampaignOverview(campaignId);
      const timeseriesData = await fetchTimeseries(campaignId, 'day');
      
      setOverview(overviewData);
      setTimeseries(timeseriesData);
    };

    loadData();
    
    // 5분마다 자동 갱신
    const interval = setInterval(loadData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [campaignId]);

  if (!overview) return <div>로딩 중...</div>;

  return (
    <div className="dashboard">
      <h2>캠페인 성과</h2>
      <div className="metrics">
        <div className="metric">
          <h3>발송</h3>
          <p>{overview.total_sent}</p>
        </div>
        <div className="metric">
          <h3>오픈율</h3>
          <p>{overview.open_rate.toFixed(2)}%</p>
        </div>
        <div className="metric">
          <h3>클릭률</h3>
          <p>{overview.click_rate.toFixed(2)}%</p>
        </div>
        <div className="metric">
          <h3>응답률</h3>
          <p>{overview.reply_rate.toFixed(2)}%</p>
        </div>
      </div>
      
      {/* 시계열 차트는 Chart.js나 Recharts 사용 */}
      <div className="chart">
        {/* <LineChart data={timeseries} /> */}
      </div>
    </div>
  );
};
```

### 예시 3: CSV 대량 리드 등록

```javascript
const importLeadsFromCSV = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('format', 'csv');

  const response = await fetch('https://coldmail.clfy.ai.kr/api/v1/leads/import/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`
      // Content-Type은 FormData 사용 시 자동 설정됨
    },
    body: formData
  });

  const result = await response.json();
  
  if (response.ok) {
    console.log(`성공: ${result.created}개 생성, ${result.updated}개 업데이트`);
    console.log(`실패: ${result.failed}개`);
    if (result.errors.length > 0) {
      console.error('에러 목록:', result.errors);
    }
  }
  
  return result;
};

// React 파일 업로드 컴포넌트
const LeadImporter = () => {
  const [file, setFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState(null);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleImport = async () => {
    if (!file) return;
    
    setImporting(true);
    try {
      const result = await importLeadsFromCSV(file);
      setResult(result);
    } catch (error) {
      console.error('Import failed:', error);
    } finally {
      setImporting(false);
    }
  };

  return (
    <div>
      <input 
        type="file" 
        accept=".csv,.json" 
        onChange={handleFileChange}
      />
      <button 
        onClick={handleImport} 
        disabled={!file || importing}
      >
        {importing ? '업로드 중...' : '리드 가져오기'}
      </button>
      
      {result && (
        <div className="result">
          <p>✅ 생성: {result.created}</p>
          <p>🔄 업데이트: {result.updated}</p>
          <p>❌ 실패: {result.failed}</p>
          {result.errors.length > 0 && (
            <details>
              <summary>에러 상세</summary>
              <ul>
                {result.errors.map((err, idx) => (
                  <li key={idx}>{err.row}: {err.error}</li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}
    </div>
  );
};
```

### 예시 4: 에러 처리 및 토큰 갱신

```javascript
// API 클라이언트 (Axios 사용)
import axios from 'axios';

const API_BASE_URL = 'https://coldmail.clfy.ai.kr/api/v1';
let accessToken = localStorage.getItem('access_token');
let refreshToken = localStorage.getItem('refresh_token');

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Request 인터셉터 - 토큰 자동 추가
apiClient.interceptors.request.use(
  (config) => {
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response 인터셉터 - 토큰 만료 시 자동 갱신
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // 401 에러이고, 아직 재시도하지 않은 경우
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // 토큰 갱신
        const response = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, {
          refresh: refreshToken
        });

        const newAccessToken = response.data.access;
        accessToken = newAccessToken;
        localStorage.setItem('access_token', newAccessToken);

        // 원래 요청 재시도
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        // 리프레시 토큰도 만료됨 -> 로그아웃
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// 사용 예시
const getCampaigns = async () => {
  try {
    const response = await apiClient.get('/campaigns/');
    return response.data;
  } catch (error) {
    if (error.response) {
      // 서버 응답이 있는 에러
      console.error('Status:', error.response.status);
      console.error('Data:', error.response.data);
    } else if (error.request) {
      // 요청은 보냈으나 응답 없음
      console.error('No response received');
    } else {
      // 요청 설정 중 에러
      console.error('Error:', error.message);
    }
    throw error;
  }
};
```

### 예시 5: WebSocket 실시간 이벤트 (선택사항)

```javascript
// 만약 WebSocket 지원이 추가된다면 (현재는 REST API만 지원)
// 실시간 캠페인 진행 상황 모니터링

const connectWebSocket = (campaignId) => {
  const ws = new WebSocket(`wss://coldmail.clfy.ai.kr/ws/campaigns/${campaignId}/`);

  ws.onopen = () => {
    console.log('WebSocket 연결됨');
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
      case 'email_sent':
        console.log('이메일 발송:', data.message_id);
        break;
      case 'email_opened':
        console.log('이메일 오픈:', data.message_id);
        break;
      case 'email_clicked':
        console.log('링크 클릭:', data.message_id);
        break;
      case 'email_replied':
        console.log('답장 수신:', data.message_id);
        break;
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket 에러:', error);
  };

  ws.onclose = () => {
    console.log('WebSocket 연결 종료');
  };

  return ws;
};

// React Hook 예시
const useCampaignEvents = (campaignId) => {
  const [events, setEvents] = useState([]);

  useEffect(() => {
    const ws = connectWebSocket(campaignId);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setEvents(prev => [...prev, data]);
    };

    return () => ws.close();
  }, [campaignId]);

  return events;
};
```

---

## 🔍 필드 상세 설명

### Lead 모델

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| id | UUID | - | 자동 생성 ID |
| channel_name | String(200) | ✅ | 유튜브 채널 이름 |
| channel_url | String(500) | ✅ | 유튜브 채널 URL (중복 불가) |
| primary_email | Email | | 주 연락 이메일 |
| subscriber_count | Integer | | 구독자 수 (0 이상) |
| keywords_raw | Text | | 키워드 (콤마 구분) |
| status | Choice | | active, do_not_contact (기본: active) |
| tags | Many-to-Many | | 태그 목록 |
| created_at | DateTime | - | 생성 시간 (자동) |
| updated_at | DateTime | - | 수정 시간 (자동) |

### Campaign 모델

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| id | UUID | - | 자동 생성 ID |
| name | String(200) | ✅ | 캠페인 이름 |
| segment | ForeignKey | ✅ | 타겟 세그먼트 |
| status | Choice | | draft, running, paused, finished (기본: draft) |
| daily_cap | Integer | | 일일 발송 제한 (1~1000, 기본: 100) |
| timezone | String(50) | | 타임존 (기본: Asia/Seoul) |
| created_at | DateTime | - | 생성 시간 |
| targets_frozen_at | DateTime | | 타겟 확정 시간 |

### SendJob 모델

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| id | UUID | - | 자동 생성 ID |
| campaign | ForeignKey | ✅ | 소속 캠페인 |
| template_version | ForeignKey | ✅ | 사용할 템플릿 버전 |
| scheduled_at | DateTime | ✅ | 예약 시간 (미래 시간) |
| status | Choice | | scheduled, queued, completed, failed, cancelled |
| attempt_count | Integer | | 재시도 횟수 (기본: 0) |
| created_at | DateTime | - | 생성 시간 |

### Template 모델

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| id | UUID | - | 자동 생성 ID |
| name | String(200) | ✅ | 템플릿 이름 |
| purpose | Choice | | intro, demo, partnership, followup, other |
| is_active | Boolean | | 활성 상태 (기본: true) |
| created_at | DateTime | - | 생성 시간 |

### TemplateVersion 모델

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| id | UUID | - | 자동 생성 ID |
| template | ForeignKey | ✅ | 부모 템플릿 |
| subject_tpl | String(500) | ✅ | 제목 템플릿 (Jinja2) |
| body_tpl | Text | ✅ | 본문 템플릿 (Jinja2) |
| format | Choice | | text, html (기본: html) |
| cta_type | Choice | | reply, link, none (기본: reply) |
| personalization_level | Integer | | 개인화 수준 (0~2, 기본: 1) |
| subject_length | Integer | - | 제목 길이 (자동 계산) |
| body_length | Integer | - | 본문 길이 (자동 계산) |
| created_at | DateTime | - | 생성 시간 |

---

## 📞 문의

- API 문서: `https://coldmail.clfy.ai.kr/api/docs/`
- Redoc: `https://coldmail.clfy.ai.kr/api/redoc/`
- Health Check: `https://coldmail.clfy.ai.kr/api/v1/health/`
