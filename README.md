# Cold Mail Django Project

Django 기반의 콜드메일 발송 시스템입니다.

## 기술 스택

- **Python**: 3.12.x
- **Django**: 5.2 LTS
- **Django REST Framework**: 3.16.1
- **Database**: MySQL 8.0
- **API Documentation**: drf-spectacular (Swagger/OpenAPI)
- **Deployment**: Docker & Docker Compose

## 개발 환경 설정

### 환경 구분

이 프로젝트는 개발(dev)과 프로덕션(prod) 환경을 분리하여 관리합니다:

- **개발 환경 (dev)**: SQLite 사용 - MySQL 설치 불필요
- **프로덕션 환경 (prod)**: MySQL 사용 - Docker로 배포

환경은 `DJANGO_ENV` 환경 변수로 자동 전환됩니다 (기본값: dev).

### 1. Conda 가상환경 생성 및 활성화

```bash
conda create -n coldmail python=3.12 -y
conda activate coldmail
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

`.env.example` 파일을 `.env`로 복사하고 필요한 값을 설정하세요:

```bash
cp .env.example .env
```

**개발 환경에서는 데이터베이스 설정이 필요 없습니다** (SQLite 자동 사용).

`.env` 파일 예시 (프로덕션용):
```
DB_NAME=coldmail_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=3306

SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 4. 마이그레이션 실행 (개발 환경 - SQLite)

**개발 환경에서는 MySQL이 필요 없습니다!** SQLite가 자동으로 사용됩니다.

```bash
python manage.py migrate
```

### 5. 슈퍼유저 생성 (선택사항)

```bash
python manage.py createsuperuser
```

### 6. 개발 서버 실행

```bash
python manage.py runserver
```

서버가 실행되면 다음 주소로 접속할 수 있습니다:
- **API Root**: http://localhost:8000/api/
- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **Admin Panel**: http://localhost:8000/admin/

## API 엔드포인트

### 테스트 API

- **GET** `/api/test/` - API 상태 확인
- **POST** `/api/test/` - 메시지 에코

Swagger UI에서 모든 API를 테스트할 수 있습니다: http://localhost:8000/api/docs/

## Docker를 사용한 배포

### 환경 전환

프로젝트는 `DJANGO_ENV` 환경 변수로 자동으로 환경을 전환합니다:

- **개발 환경 (기본값)**: `DJANGO_ENV=dev` 또는 설정 안 함 → SQLite 사용
- **프로덕션 환경**: `DJANGO_ENV=prod` → MySQL 사용

### 프로덕션 환경으로 로컬 테스트

```bash
# 환경 변수 설정
$env:DJANGO_ENV="prod"

# MySQL이 실행 중이어야 함
python manage.py migrate
python manage.py runserver
```

### Docker Compose로 실행 (프로덕션 환경)

```bash
# 컨테이너 빌드 및 실행
docker-compose up -d --build

# 로그 확인
docker-compose logs -f

# 컨테이너 중지
docker-compose down

# 볼륨까지 삭제 (데이터베이스 데이터 포함)
docker-compose down -v
```

Docker로 실행하면 다음이 자동으로 설정됩니다:
- MySQL 8.0 데이터베이스 컨테이너
- Django 애플리케이션 컨테이너
- 자동 마이그레이션
- 정적 파일 수집

## 프로젝트 구조

```
.
├── api/                    # API 앱
│   ├── serializers.py     # 시리얼라이저
│   ├── views.py           # API 뷰
│   └── urls.py            # API URL 라우팅
├── coldmail_project/       # 프로젝트 설정
│   ├── settings/          # 환경별 설정 디렉토리
│   │   ├── __init__.py   # 환경 자동 선택
│   │   ├── base.py       # 공통 설정
│   │   ├── dev.py        # 개발 환경 (SQLite)
│   │   └── prod.py       # 프로덕션 환경 (MySQL)
│   └── urls.py            # 메인 URL 라우팅
├── manage.py              # Django 관리 스크립트
├── requirements.txt       # Python 패키지 목록
├── Dockerfile            # Docker 이미지 빌드 파일
├── docker-compose.yml    # Docker Compose 설정
├── entrypoint.sh        # Docker 엔트리포인트 스크립트
├── .env.example         # 환경 변수 예시
└── .gitignore          # Git 제외 파일 목록
```

## 개발 가이드

### 새로운 앱 생성

```bash
python manage.py startapp <app_name>
```

### 마이그레이션 생성 및 적용

```bash
python manage.py makemigrations
python manage.py migrate
```

### 정적 파일 수집 (프로덕션)

```bash
python manage.py collectstatic
```

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.
