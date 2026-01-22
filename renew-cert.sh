#!/bin/bash

# SSL 인증서 강제 갱신 스크립트
# 수동으로 인증서를 갱신할 때 사용합니다.

echo "🔄 SSL 인증서 수동 갱신 시작..."

# 인증서 갱신
docker compose run --rm certbot renew --force-renewal

if [ $? -eq 0 ]; then
    echo "✅ 인증서 갱신 성공!"
    
    # Nginx 설정 리로드
    echo "🔄 Nginx 설정 리로드 중..."
    docker compose exec nginx nginx -s reload
    
    if [ $? -eq 0 ]; then
        echo "✅ Nginx 리로드 성공!"
    else
        echo "⚠️  Nginx 리로드 실패. 수동으로 재시작하세요."
        echo "   docker compose restart nginx"
    fi
    
    # 인증서 정보 출력
    echo ""
    echo "📋 갱신된 인증서 정보:"
    docker compose run --rm certbot certificates
else
    echo "❌ 인증서 갱신 실패!"
    exit 1
fi

echo ""
echo "✨ 완료!"
