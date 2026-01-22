# 🔐 SSL 인증서 자동 갱신 가이드

## 📋 개요

Let's Encrypt SSL 인증서는 **90일마다 만료**되며, 이 프로젝트는 **자동 갱신**이 설정되어 있습니다.

---

## ✨ 자동 갱신 작동 방식

### Docker Compose 구성

```yaml
certbot:
  image: certbot/certbot
  volumes:
    - ./certbot/conf:/etc/letsencrypt
    - ./certbot/www:/var/www/certbot
  # 12시간마다 갱신 확인
  entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"

nginx:
  # 6시간마다 설정 리로드
  command: "/bin/sh -c 'while :; do sleep 6h & wait $${!}; nginx -s reload; done & nginx -g \"daemon off;\"'"
```

### 갱신 주기

| 컨테이너 | 작업 | 주기 |
|----------|------|------|
| **certbot** | 인증서 갱신 확인 | 12시간 |
| **nginx** | 설정 리로드 | 6시간 |
| **자동 갱신 시작** | 만료 30일 전 | - |

**결과**: 사용자가 아무것도 하지 않아도 인증서가 자동으로 갱신됩니다! 🎉

---

## 🚀 초기 설정 (최초 1회)

### 1단계: 스크립트 실행 권한
```bash
chmod +x init-letsencrypt.sh
chmod +x renew-cert.sh
```

### 2단계: 이메일 주소 수정
```bash
nano init-letsencrypt.sh

# 다음 줄을 실제 이메일로 변경
EMAIL="admin@clfy.ai.kr"
```

### 3단계: 인증서 발급
```bash
./init-letsencrypt.sh
```

**스크립트가 자동으로**:
- ✅ certbot 디렉토리 생성
- ✅ Nginx 일시 중지
- ✅ SSL 인증서 발급
- ✅ 인증서 정보 출력

### 4단계: Nginx HTTPS 활성화
```bash
nano nginx/conf.d/coldmail.conf

# HTTPS server 블록의 모든 # 제거 (주석 해제)
```

### 5단계: 서비스 재시작
```bash
docker compose down
docker compose -f docker-compose.prod.yml up -d
```

---

## 🔍 인증서 상태 확인

### 인증서 정보 보기
```bash
docker compose run --rm certbot certificates
```

**출력 예시**:
```
Certificate Name: coldmail.clfy.ai.kr
  Serial Number: 123456789abcdef...
  Domains: coldmail.clfy.ai.kr
  Expiry Date: 2026-04-23 12:34:56+00:00 (VALID: 89 days)
  Certificate Path: /etc/letsencrypt/live/coldmail.clfy.ai.kr/fullchain.pem
  Private Key Path: /etc/letsencrypt/live/coldmail.clfy.ai.kr/privkey.pem
```

### 자동 갱신 로그 확인
```bash
# 전체 로그
docker compose logs certbot

# 최근 50줄
docker compose logs --tail=50 certbot

# 실시간 모니터링
docker compose logs -f certbot
```

### HTTPS 작동 확인
```bash
# 인증서 유효성 검증
curl -vI https://coldmail.clfy.ai.kr 2>&1 | grep "SSL certificate verify"

# 출력: SSL certificate verify ok

# 인증서 만료일 확인
echo | openssl s_client -servername coldmail.clfy.ai.kr -connect coldmail.clfy.ai.kr:443 2>/dev/null | openssl x509 -noout -dates
```

---

## 🔄 수동 갱신 (필요시)

### 방법 1: 스크립트 사용 (권장)
```bash
./renew-cert.sh
```

### 방법 2: 직접 명령어 실행
```bash
# 인증서 강제 갱신
docker compose run --rm certbot renew --force-renewal

# Nginx 리로드
docker compose exec nginx nginx -s reload
```

### Dry-run 테스트 (실제 갱신 X)
```bash
# 갱신 시뮬레이션 (테스트)
docker compose run --rm certbot renew --dry-run

# 성공 메시지: "Congratulations, all simulated renewals succeeded"
```

---

## 📅 갱신 일정 예시

인증서 발급일: **2026-01-23**

| 날짜 | 일수 | 이벤트 |
|------|------|--------|
| 2026-01-23 | 0일 | ✅ 인증서 발급 |
| 2026-03-24 | 60일 | ⚠️ 만료 30일 전 → **자동 갱신 시작** |
| 2026-04-23 | 90일 | 🔴 인증서 만료 (자동 갱신되므로 문제 없음) |

**자동 갱신 덕분에 만료되기 전에 새 인증서로 교체됩니다!**

---

## ⚠️ 문제 해결

### 인증서 갱신 실패
```bash
# 로그 확인
docker compose logs certbot

# DNS 확인
nslookup coldmail.clfy.ai.kr

# 80 포트 확인 (HTTP-01 challenge)
curl -I http://coldmail.clfy.ai.kr/.well-known/acme-challenge/test
```

**일반적인 원인**:
- DNS 설정 오류 (도메인 → IP 매핑)
- 방화벽이 80 포트 차단
- Nginx가 /.well-known/acme-challenge/ 경로 차단

### Nginx 설정 오류
```bash
# Nginx 설정 테스트
docker compose exec nginx nginx -t

# 설정 리로드
docker compose exec nginx nginx -s reload

# Nginx 재시작
docker compose restart nginx
```

### 인증서 파일 권한 문제
```bash
# certbot 디렉토리 권한 확인
ls -la certbot/conf/live/

# 권한 수정 (필요시)
sudo chown -R $USER:$USER certbot/
```

---

## 📂 파일 구조

```
프로젝트/
├── certbot/
│   ├── conf/                    # 인증서 저장
│   │   ├── live/
│   │   │   └── coldmail.clfy.ai.kr/
│   │   │       ├── fullchain.pem    # 인증서
│   │   │       ├── privkey.pem      # 개인키
│   │   │       ├── chain.pem
│   │   │       └── cert.pem
│   │   ├── archive/
│   │   └── renewal/
│   └── www/                     # ACME challenge
│
├── docker-compose.prod.yml      # Certbot 컨테이너 포함
├── init-letsencrypt.sh          # 초기 발급 스크립트
└── renew-cert.sh                # 수동 갱신 스크립트
```

---

## 🎯 체크리스트

### 초기 설정 (최초 1회)
- [ ] `init-letsencrypt.sh` 실행 권한 부여
- [ ] 이메일 주소 수정
- [ ] 인증서 발급 (`./init-letsencrypt.sh`)
- [ ] Nginx HTTPS 설정 활성화
- [ ] 서비스 재시작

### 정기 점검 (월 1회 권장)
- [ ] 인증서 상태 확인 (`docker compose run --rm certbot certificates`)
- [ ] 만료일 확인 (60일 이상 남았는지)
- [ ] 갱신 로그 확인 (에러 없는지)

### 자동 갱신 확인 (90일마다)
- [ ] 새 인증서로 교체되었는지 확인
- [ ] HTTPS 정상 작동 확인
- [ ] 브라우저에서 자물쇠 아이콘 확인

---

## 💡 추가 팁

### 여러 도메인 사용
```bash
# 여러 도메인을 하나의 인증서로
docker compose run --rm certbot certonly \
  --standalone \
  -d coldmail.clfy.ai.kr \
  -d www.coldmail.clfy.ai.kr \
  -d api.coldmail.clfy.ai.kr \
  --email admin@clfy.ai.kr \
  --agree-tos
```

### 인증서 백업
```bash
# certbot/conf 전체 백업
tar -czf certbot-backup-$(date +%Y%m%d).tar.gz certbot/

# 복구
tar -xzf certbot-backup-20260123.tar.gz
```

### 만료 알림 이메일
Let's Encrypt는 만료 20일, 10일, 1일 전에 이메일을 발송합니다.
초기 설정 시 입력한 이메일로 알림이 전송됩니다.

---

## 🔗 참고 링크

- [Let's Encrypt 공식 문서](https://letsencrypt.org/docs/)
- [Certbot 문서](https://certbot.eff.org/docs/)
- [Nginx + Certbot Docker](https://github.com/wmnnd/nginx-certbot)

---

## ✨ 결론

**자동 갱신이 설정되어 있으므로 신경 쓸 필요가 없습니다!**

- ✅ 12시간마다 갱신 확인
- ✅ 만료 30일 전 자동 갱신
- ✅ Nginx 자동 리로드
- ✅ 90일 후 새 인증서로 자동 교체

**월 1회 상태만 확인하면 됩니다:**
```bash
docker compose run --rm certbot certificates
```

문제가 발생하면 로그를 확인하세요:
```bash
docker compose logs certbot
```
