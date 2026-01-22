# 0단계: 프로젝트 골격 완료

Django + DRF 기반 콜드메일 시스템의 기본 구조가 완성되었습니다.

## 완료된 작업

### 1. 앱 구조
```
coldmail_project/
├── core/           # 공통 유틸리티 (base classes, pagination, permissions)
├── crm/            # 리드(유튜버) 관리
├── campaigns/      # 캠페인 관리
├── templates/      # 메일 템플릿 관리
├── analytics/      # 분석 및 리포팅
└── api/            # 레거시 메일 발송 API
```

### 2. 공통 Base 클래스
- **models.py**: `UUIDModel`, `TimestampedModel`, `BaseModel`
- **serializers.py**: `BaseSerializer`, `TimestampedSerializer`
- **viewsets.py**: `BaseViewSet` (통일된 응답 형식)
- **pagination.py**: `StandardResultsSetPagination` (page_size, 커스텀 응답)
- **permissions.py**: `IsAuthenticatedOrReadOnly`, `IsOwnerOrReadOnly`
- **exceptions.py**: `custom_exception_handler` (통일된 에러 형식)

### 3. 인증
- **JWT 인증**: djangorestframework-simplejwt
  - Access Token: 1시간
  - Refresh Token: 7일
  - `/api/v1/auth/token/` - 토큰 발급
  - `/api/v1/auth/token/refresh/` - 토큰 갱신

### 4. API 엔드포인트
- **Health Check**: `GET /api/v1/health/` ✅
- **Authentication**: `POST /api/v1/auth/token/`, `POST /api/v1/auth/token/refresh/` ✅
- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/

### 5. 설정
- **Pagination**: 기본 20개, 최대 100개
- **Filter Backends**: DjangoFilterBackend, SearchFilter, OrderingFilter
- **Exception Handler**: 커스텀 에러 응답 형식
- **환경 분리**: dev (SQLite), prod (MySQL)

## 테스트 방법

### 1. Health Check
```bash
curl http://localhost:8000/api/v1/health/
```

응답:
```json
{
  "status": "ok",
  "timestamp": "2026-01-22T19:30:00+09:00",
  "service": "Cold Mail API",
  "version": "1.0.0",
  "database": "healthy"
}
```

### 2. 슈퍼유저 생성
```bash
python manage.py createsuperuser
```

### 3. JWT 토큰 발급
```bash
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'
```

## 응답 형식 표준

### 성공 응답
```json
{
  "success": true,
  "data": { ... }
}
```

### 리스트 응답
```json
{
  "count": 100,
  "next": "...",
  "previous": "...",
  "page": 1,
  "page_size": 20,
  "total_pages": 5,
  "results": [ ... ]
}
```

### 에러 응답
```json
{
  "success": false,
  "error": {
    "code": "error_code",
    "message": "Error message",
    "details": { ... }
  }
}
```

## 다음 단계

1단계에서는 DB 스키마 구현:
- Lead, Tag, LeadTag 모델
- Segment, Campaign, CampaignTarget 모델
- Template, TemplateVersion 모델
- SendJob, EmailMessage, EmailEvent 모델
- Suppression 모델

## 패키지 목록
- Django 5.2
- Django REST Framework 3.16.1
- djangorestframework-simplejwt 5.5.1
- drf-spectacular 0.29.0
- django-filter 25.2
- mysqlclient 2.2.7
- python-dotenv 1.2.1
- gunicorn 23.0.0
