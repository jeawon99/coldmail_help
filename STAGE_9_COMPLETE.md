# Stage 9: Analytics API - 완료 ✅

## 개요

프론트엔드에서 바로 그래프를 그릴 수 있도록 집계된 데이터를 제공하는 5개의 Analytics API를 구현했습니다.

**완료 일시**: 2026-01-23  
**구현 파일**:
- `campaigns/views.py` - CampaignViewSet에 5개 analytics 액션 추가
- `campaigns/serializers_analytics.py` - Analytics 전용 serializers
- `test_stage9_analytics.py` - 전체 테스트 스크립트

---

## 구현된 엔드포인트

### 1. 📊 Overview API
**엔드포인트**: `GET /api/v1/campaigns/{id}/analytics/overview/`

**설명**: 캠페인의 전체 성과 지표를 한눈에 볼 수 있는 요약 데이터

**Query Parameters**:
- `from_date` (optional): 시작 날짜 (ISO 8601 형식, 예: `2026-01-01T00:00:00Z`)
- `to_date` (optional): 종료 날짜 (ISO 8601 형식)

**Response**:
```json
{
  "success": true,
  "data": {
    "total_sent": 5,
    "total_delivered": 5,
    "total_opened": 1,
    "total_clicked": 14,
    "total_replied": 0,
    "total_bounced": 0,
    "unique_opens": 1,
    "unique_clicks": 1,
    "open_rate": 20.0,
    "click_rate": 20.0,
    "click_to_open_rate": 100.0,
    "bounce_rate": 0.0,
    "reply_rate": 0.0
  }
}
```

**주요 지표**:
- `total_sent`: 총 발송 수
- `unique_opens`: 고유 오픈 수 (1명이 여러 번 열어도 1번만 카운트)
- `open_rate`: 오픈율 = unique_opens / total_delivered × 100
- `click_rate`: 클릭율 = unique_clicks / total_delivered × 100
- `click_to_open_rate`: 클릭/오픈율 = unique_clicks / unique_opens × 100

---

### 2. 📈 Timeseries API
**엔드포인트**: `GET /api/v1/campaigns/{id}/analytics/timeseries/`

**설명**: 날짜/시간별 이벤트 추이를 시계열 데이터로 제공

**Query Parameters**:
- `granularity` (optional): 집계 단위
  - `hourly`: 시간별 집계
  - `daily`: 일별 집계 (기본값)
- `from_date` (optional): 시작 날짜 (기본값: 30일 전)
- `to_date` (optional): 종료 날짜 (기본값: 현재)

**Response**:
```json
{
  "success": true,
  "data": {
    "granularity": "daily",
    "data_points": [
      {
        "timestamp": "2026-01-23T00:00:00Z",
        "date": "2026-01-23",
        "sent": 5,
        "opened": 1,
        "clicked": 14,
        "replied": 0,
        "bounced": 0
      }
    ]
  }
}
```

**사용 예시**:
```
# 일별 집계 (기본값)
GET /campaigns/{id}/analytics/timeseries/

# 시간별 집계
GET /campaigns/{id}/analytics/timeseries/?granularity=hourly

# 특정 기간 조회
GET /campaigns/{id}/analytics/timeseries/?from_date=2026-01-01T00:00:00Z&to_date=2026-01-31T23:59:59Z
```

**프론트엔드 활용**:
- Chart.js, Recharts 등으로 라인 차트 구현
- 발송/오픈/클릭 추이를 시각화

---

### 3. 📄 Templates API
**엔드포인트**: `GET /api/v1/campaigns/{id}/analytics/templates/`

**설명**: 캠페인에 사용된 템플릿 버전별 성과 비교

**Query Parameters**:
- `from_date` (optional): 시작 날짜
- `to_date` (optional): 종료 날짜

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "template_id": "550e8400-e29b-41d4-a716-446655440000",
      "template_name": "Stage6 테스트 템플릿",
      "version": 5,
      "sent": 5,
      "opened": 1,
      "clicked": 1,
      "open_rate": 20.0,
      "click_rate": 20.0
    }
  ]
}
```

**활용 사례**:
- A/B 테스트 결과 분석
- 템플릿 버전별 성과 비교
- 최적 템플릿 버전 식별

---

### 4. 🏷️ Breakdown API
**엔드포인트**: `GET /api/v1/campaigns/{id}/analytics/breakdown/`

**설명**: 태그 또는 세그먼트별로 성과를 분석

**Query Parameters**:
- `breakdown_type` (required): 분류 타입
  - `tag`: 리드 태그별 분석
  - `segment`: 세그먼트별 분석 (추후 구현 예정)
- `from_date` (optional): 시작 날짜
- `to_date` (optional): 종료 날짜

**Response**:
```json
{
  "success": true,
  "data": {
    "breakdown_type": "tag",
    "items": [
      {
        "key": "123",
        "label": "VIP 고객",
        "sent": 50,
        "opened": 30,
        "clicked": 15,
        "open_rate": 60.0,
        "click_rate": 30.0
      },
      {
        "key": "456",
        "label": "신규 가입자",
        "sent": 100,
        "opened": 40,
        "clicked": 10,
        "open_rate": 40.0,
        "click_rate": 10.0
      }
    ]
  }
}
```

**사용 예시**:
```
# 태그별 분석
GET /campaigns/{id}/analytics/breakdown/?breakdown_type=tag
```

**활용 사례**:
- 고객 세그먼트별 반응 차이 분석
- 타겟팅 전략 개선
- 고성과 세그먼트 식별

---

### 5. ⏱️ Response Time API
**엔드포인트**: `GET /api/v1/campaigns/{id}/analytics/response-time/`

**설명**: 이메일 발송 후 오픈/클릭/답장까지 걸린 시간 분석

**Query Parameters**:
- `from_date` (optional): 시작 날짜
- `to_date` (optional): 종료 날짜

**Response**:
```json
{
  "success": true,
  "data": {
    "avg_time_to_open": 820.18,
    "avg_time_to_click": 820.20,
    "avg_time_to_reply": null,
    "median_time_to_open": 820.18,
    "median_time_to_click": 820.20,
    "open_time_distribution": [
      {"bucket": "0-1h", "count": 1, "percentage": 100.0},
      {"bucket": "1-6h", "count": 0, "percentage": 0.0},
      {"bucket": "6-24h", "count": 0, "percentage": 0.0},
      {"bucket": "24h+", "count": 0, "percentage": 0.0}
    ],
    "click_time_distribution": [
      {"bucket": "0-1h", "count": 1, "percentage": 100.0},
      {"bucket": "1-6h", "count": 0, "percentage": 0.0},
      {"bucket": "6-24h", "count": 0, "percentage": 0.0},
      {"bucket": "24h+", "count": 0, "percentage": 0.0}
    ]
  }
}
```

**시간 단위**: 초(seconds)

**시간 버킷**:
- `0-1h`: 1시간 이내
- `1-6h`: 1~6시간
- `6-24h`: 6~24시간
- `24h+`: 24시간 이상

**활용 사례**:
- 최적 발송 시간 분석
- 빠른 응답을 유도하는 콘텐츠 식별
- 발송 타이밍 최적화

---

## 성능 최적화

### 인덱스 활용
기존 Stage 8에서 생성한 인덱스를 활용합니다:

```python
class EmailEvent:
    class Meta:
        indexes = [
            models.Index(fields=['event_at']),  # 시계열 쿼리 최적화
            models.Index(fields=['email_message', 'event_type']),  # 이벤트 필터링 최적화
            models.Index(fields=['event_type', 'event_at']),  # 복합 조건 최적화
        ]
```

### 쿼리 최적화 기법

1. **집계 쿼리 사용**:
   ```python
   events.values('event_type').annotate(count=Count('id'))
   ```
   - 데이터베이스 레벨에서 집계
   - Python 루프보다 훨씬 빠름

2. **시간 단위 집계**:
   ```python
   events.annotate(time_bucket=TruncDate('event_at'))
   ```
   - Django ORM의 TruncDate/TruncHour 사용
   - 인덱스 활용 가능

3. **고유 카운트**:
   ```python
   events.filter(event_type='opened_pixel').values('email_message').distinct().count()
   ```
   - SQL DISTINCT 사용
   - 중복 제거 후 카운트

4. **필터 우선 적용**:
   ```python
   # 날짜 필터를 먼저 적용하여 데이터셋 크기 축소
   events = events.filter(event_at__gte=from_date, event_at__lte=to_date)
   ```

---

## 테스트 결과

### 실행 방법
```bash
python test_stage9_analytics.py
```

### 테스트 결과 요약
```
✅ Overview API: 정상 작동
   - 총 발송: 5개
   - 오픈율: 20.0%
   - 클릭율: 20.0%

✅ Timeseries API: 정상 작동
   - granularity: daily
   - 데이터 포인트: 1개

✅ Templates API: 정상 작동
   - 템플릿: 1개
   - 버전별 성과 비교 가능

✅ Breakdown API: 정상 작동
   - breakdown_type: tag
   - 항목: 0개 (태그가 없는 경우)

✅ Response Time API: 정상 작동
   - 평균 오픈 시간: 820.18초 (0.23시간)
   - 시간 분포: 0-1h에 100% 집중
```

---

## 프론트엔드 통합 가이드

### 1. 대시보드 KPI 카드
```javascript
// Overview API로 전체 통계 표시
const response = await fetch(
  `/api/v1/campaigns/${campaignId}/analytics/overview/`,
  {
    headers: {
      'Authorization': `Token ${authToken}`
    }
  }
);
const { data } = await response.json();

// KPI 카드에 표시
<div className="kpi-grid">
  <KPICard title="발송 수" value={data.total_sent} />
  <KPICard title="오픈율" value={`${data.open_rate}%`} />
  <KPICard title="클릭율" value={`${data.click_rate}%`} />
  <KPICard title="CTR" value={`${data.click_to_open_rate}%`} />
</div>
```

### 2. 시계열 차트 (Chart.js)
```javascript
// Timeseries API로 라인 차트 생성
const response = await fetch(
  `/api/v1/campaigns/${campaignId}/analytics/timeseries/?granularity=daily`,
  {
    headers: {
      'Authorization': `Token ${authToken}`
    }
  }
);
const { data } = await response.json();

const chartData = {
  labels: data.data_points.map(p => p.date),
  datasets: [
    {
      label: '발송',
      data: data.data_points.map(p => p.sent),
      borderColor: 'rgb(75, 192, 192)',
    },
    {
      label: '오픈',
      data: data.data_points.map(p => p.opened),
      borderColor: 'rgb(255, 99, 132)',
    },
    {
      label: '클릭',
      data: data.data_points.map(p => p.clicked),
      borderColor: 'rgb(54, 162, 235)',
    }
  ]
};

<Line data={chartData} />
```

### 3. 템플릿 성과 비교 테이블
```javascript
// Templates API로 성과 비교 테이블
const response = await fetch(
  `/api/v1/campaigns/${campaignId}/analytics/templates/`,
  {
    headers: {
      'Authorization': `Token ${authToken}`
    }
  }
);
const { data } = await response.json();

<table>
  <thead>
    <tr>
      <th>템플릿</th>
      <th>버전</th>
      <th>발송</th>
      <th>오픈율</th>
      <th>클릭율</th>
    </tr>
  </thead>
  <tbody>
    {data.map(template => (
      <tr key={template.template_id}>
        <td>{template.template_name}</td>
        <td>v{template.version}</td>
        <td>{template.sent}</td>
        <td>{template.open_rate}%</td>
        <td>{template.click_rate}%</td>
      </tr>
    ))}
  </tbody>
</table>
```

### 4. 세그먼트별 성과 차트 (Recharts)
```javascript
// Breakdown API로 바 차트 생성
const response = await fetch(
  `/api/v1/campaigns/${campaignId}/analytics/breakdown/?breakdown_type=tag`,
  {
    headers: {
      'Authorization': `Token ${authToken}`
    }
  }
);
const { data } = await response.json();

<BarChart data={data.items}>
  <XAxis dataKey="label" />
  <YAxis />
  <Bar dataKey="open_rate" fill="#8884d8" name="오픈율" />
  <Bar dataKey="click_rate" fill="#82ca9d" name="클릭율" />
</BarChart>
```

### 5. 응답 시간 분포 (Pie Chart)
```javascript
// Response Time API로 파이 차트 생성
const response = await fetch(
  `/api/v1/campaigns/${campaignId}/analytics/response-time/`,
  {
    headers: {
      'Authorization': `Token ${authToken}`
    }
  }
);
const { data } = await response.json();

const pieData = data.open_time_distribution.map(item => ({
  name: item.bucket,
  value: item.percentage
}));

<PieChart>
  <Pie data={pieData} dataKey="value" nameKey="name" />
</PieChart>
```

---

## 구현 세부사항

### 파일 구조
```
campaigns/
├── views.py                        # CampaignViewSet에 5개 analytics 액션 추가
│   ├── analytics_overview()
│   ├── analytics_timeseries()
│   ├── analytics_templates()
│   ├── analytics_breakdown()
│   └── analytics_response_time()
│
├── serializers_analytics.py        # Analytics 전용 serializers
│   ├── OverviewAnalyticsSerializer
│   ├── TimeseriesAnalyticsSerializer
│   ├── TimeseriesDataPointSerializer
│   ├── TemplatePerformanceSerializer
│   ├── BreakdownAnalyticsSerializer
│   ├── BreakdownItemSerializer
│   ├── ResponseTimeAnalyticsSerializer
│   └── ResponseTimeDistributionSerializer
│
└── views_analytics.py              # 참고용 (standalone ViewSet)
```

### URL 라우팅
```python
# campaigns/urls.py
router.register('campaigns', CampaignViewSet, basename='campaign')

# 자동 생성되는 URL:
# GET /api/v1/campaigns/{id}/analytics/overview/
# GET /api/v1/campaigns/{id}/analytics/timeseries/
# GET /api/v1/campaigns/{id}/analytics/templates/
# GET /api/v1/campaigns/{id}/analytics/breakdown/
# GET /api/v1/campaigns/{id}/analytics/response-time/
```

### 날짜 파라미터 파싱
```python
def _parse_date_params(self, request):
    """날짜 파라미터 파싱 헬퍼"""
    from_date_str = request.query_params.get('from_date')
    to_date_str = request.query_params.get('to_date')
    
    from_date = None
    to_date = None
    
    if from_date_str:
        from_date = timezone.datetime.fromisoformat(from_date_str.replace('Z', '+00:00'))
    if to_date_str:
        to_date = timezone.datetime.fromisoformat(to_date_str.replace('Z', '+00:00'))
    
    return from_date, to_date
```

---

## 향후 개선 사항

### 1. 캐싱 추가
```python
from django.core.cache import cache

@action(detail=True, methods=['get'])
def analytics_overview(self, request, pk=None):
    cache_key = f'campaign_{pk}_analytics_overview'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return self.success_response(data=cached_data)
    
    # 집계 로직...
    
    cache.set(cache_key, data, 300)  # 5분 캐싱
    return self.success_response(data=data)
```

### 2. 세그먼트 분석 구현
현재는 태그별 분석만 지원하며, 세그먼트별 분석은 추후 구현 예정입니다.

### 3. 응답 시간 최적화
현재는 sent_events를 루프하며 개별 쿼리를 실행합니다. 대규모 데이터셋의 경우 다음과 같이 최적화할 수 있습니다:

```python
# 서브쿼리 또는 윈도우 함수 사용
from django.db.models import Subquery, OuterRef, F
from django.db.models.functions import Coalesce

first_opens = EmailEvent.objects.filter(
    email_message=OuterRef('email_message'),
    event_type='opened_pixel'
).order_by('event_at').values('event_at')[:1]

sent_with_opens = EmailEvent.objects.filter(
    email_message__send_job__campaign=campaign,
    event_type='sent'
).annotate(
    first_open_at=Subquery(first_opens)
).filter(
    first_open_at__isnull=False
).annotate(
    time_diff=F('first_open_at') - F('event_at')
)
```

### 4. 실시간 업데이트
WebSocket을 통한 실시간 analytics 업데이트:

```python
# channels를 사용한 실시간 업데이트
from channels.layers import get_channel_layer

channel_layer = get_channel_layer()
await channel_layer.group_send(
    f'campaign_{campaign_id}_analytics',
    {
        'type': 'analytics_update',
        'data': analytics_data
    }
)
```

---

## 마무리

Stage 9에서는 프론트엔드에서 바로 사용할 수 있는 5개의 Analytics API를 구현했습니다:

1. ✅ **Overview API** - 전체 통계 요약
2. ✅ **Timeseries API** - 시계열 데이터
3. ✅ **Templates API** - 템플릿별 성과
4. ✅ **Breakdown API** - 태그/세그먼트별 분석
5. ✅ **Response Time API** - 응답 시간 분석

모든 API는:
- ✅ 인덱스를 활용한 성능 최적화
- ✅ 날짜 필터 지원 (from_date, to_date)
- ✅ DRF 기본 인증/권한 시스템 사용
- ✅ drf-spectacular 문서화 지원
- ✅ 테스트 완료

**다음 단계**: Stage 10으로 진행하거나 프론트엔드 통합 시작
