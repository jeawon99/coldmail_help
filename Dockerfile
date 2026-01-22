# 멀티 스테이지 빌드 - 빌더 스테이지
FROM python:3.12-slim as builder

WORKDIR /app

# 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 빌드 의존성 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config && \
    rm -rf /var/lib/apt/lists/*

# Python 패키지 설치 (유저 디렉토리에)
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# 프로덕션 스테이지
FROM python:3.12-slim

WORKDIR /app

# 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/root/.local/bin:$PATH

# 런타임 의존성만 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    netcat-traditional && \
    rm -rf /var/lib/apt/lists/*

# 빌더 스테이지에서 설치된 패키지 복사
COPY --from=builder /root/.local /root/.local

# 프로젝트 파일 복사
COPY . .

# 필요한 디렉토리 생성
RUN mkdir -p /app/staticfiles /app/mediafiles /app/logs

# 엔트리포인트 실행 권한
RUN chmod +x /app/entrypoint.sh

# 비root 유저 생성 및 권한 설정 (보안)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# 비root 유저로 전환
USER appuser

# 포트 노출
EXPOSE 8000

# 엔트리포인트 실행
ENTRYPOINT ["/app/entrypoint.sh"]

# 기본 명령어
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "coldmail_project.wsgi:application"]
