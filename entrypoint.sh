#!/bin/bash
set -e

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}Cold Mail Platform - Starting...${NC}"
echo -e "${GREEN}================================================${NC}"

# 환경 변수 확인
echo -e "${YELLOW}Environment:${NC} ${DJANGO_SETTINGS_MODULE:-dev}"
echo -e "${YELLOW}Database:${NC} ${DB_HOST:-localhost}:${DB_PORT:-3306}"

# 데이터베이스 연결 대기
echo -e "${YELLOW}Waiting for database...${NC}"
MAX_RETRIES=30
RETRY_COUNT=0

while ! nc -z $DB_HOST $DB_PORT; do
  RETRY_COUNT=$((RETRY_COUNT+1))
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo -e "${GREEN}Error: Database connection timeout${NC}"
    exit 1
  fi
  echo "Attempt $RETRY_COUNT/$MAX_RETRIES..."
  sleep 2
done

echo -e "${GREEN}✓ Database is ready!${NC}"

# 마이그레이션 실행
echo -e "${YELLOW}Running migrations...${NC}"
python manage.py migrate --noinput
echo -e "${GREEN}✓ Migrations completed${NC}"

# 정적 파일 수집 (프로덕션만)
if [ "$DJANGO_SETTINGS_MODULE" = "coldmail_project.settings.prod" ]; then
  echo -e "${YELLOW}Collecting static files...${NC}"
  python manage.py collectstatic --noinput --clear
  echo -e "${GREEN}✓ Static files collected${NC}"
fi

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}Starting application...${NC}"
echo -e "${GREEN}================================================${NC}"

# 전달된 명령 실행
exec "$@"
