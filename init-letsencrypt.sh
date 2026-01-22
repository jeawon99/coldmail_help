#!/bin/bash

# SSL 인증서 초기 발급 스크립트
# Let's Encrypt Certbot을 사용하여 SSL 인증서를 발급합니다.

DOMAIN="coldmail.clfy.ai.kr"
EMAIL="admin@clfy.ai.kr"  # 실제 이메일로 변경하세요

echo "================================================"
echo "SSL 인증서 초기 발급 스크립트"
echo "도메인: $DOMAIN"
echo "================================================"

# certbot 디렉토리 생성
echo "📁 certbot 디렉토리 생성..."
mkdir -p certbot/conf
mkdir -p certbot/www

# 기존 인증서 확인
if [ -d "certbot/conf/live/$DOMAIN" ]; then
    echo "⚠️  기존 인증서가 존재합니다."
    read -p "기존 인증서를 삭제하고 새로 발급하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 취소되었습니다."
        exit 1
    fi
    echo "🗑️  기존 인증서 삭제 중..."
    sudo rm -rf certbot/conf/live/$DOMAIN
    sudo rm -rf certbot/conf/archive/$DOMAIN
    sudo rm -rf certbot/conf/renewal/$DOMAIN.conf
fi

# Nginx 컨테이너가 실행 중인지 확인
if docker compose -f docker-compose.prod.yml ps | grep -q "coldmail_nginx.*Up"; then
    echo "🛑 Nginx 컨테이너 중지 중..."
    docker compose -f docker-compose.prod.yml stop nginx
    NGINX_WAS_RUNNING=true
else
    NGINX_WAS_RUNNING=false
fi

# Certbot standalone 모드로 인증서 발급
echo "🔐 SSL 인증서 발급 중..."
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
    --standalone \
    --preferred-challenges http \
    -d $DOMAIN \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    --force-renewal

# 발급 결과 확인
if [ $? -eq 0 ]; then
    echo "✅ SSL 인증서가 성공적으로 발급되었습니다!"
    echo "📂 인증서 위치: certbot/conf/live/$DOMAIN/"
    
    # 인증서 정보 출력
    echo ""
    echo "📋 인증서 정보:"
    docker compose -f docker-compose.prod.yml run --rm certbot certificates
    
    # nginx 설정 파일 안내
    echo ""
    echo "================================================"
    echo "다음 단계:"
    echo "1. nginx/conf.d/coldmail.conf 파일에서 HTTPS server 블록 주석 해제"
    echo "2. docker compose -f docker-compose.prod.yml up -d 로 서비스 재시작"
    echo "================================================"
else
    echo "❌ SSL 인증서 발급에 실패했습니다."
    echo "DNS 설정을 확인하세요: $DOMAIN → 서버 IP"
    exit 1
fi

# Nginx 재시작 여부 확인
if [ "$NGINX_WAS_RUNNING" = true ]; then
    read -p "Nginx를 다시 시작하시겠습니까? (Y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        echo "ℹ️  나중에 'docker compose -f docker-compose.prod.yml start nginx'로 시작하세요."
    else
        echo "🚀 Nginx 시작 중..."
        docker compose -f docker-compose.prod.yml start nginx
    fi
fi

echo ""
echo "✨ 완료!"
