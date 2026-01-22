"""
트래킹 URL 테스트 스크립트
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coldmail_project.settings.dev')
django.setup()

from campaigns.models import EmailMessage, EmailEvent

print("="*60)
print("이벤트 트래킹 테스트")
print("="*60)

# 1. EmailMessage 확인
messages = EmailMessage.objects.all().order_by('-created_at')
msg_count = messages.count()

print(f"\n총 EmailMessage: {msg_count}개")

if msg_count == 0:
    print("⚠️ 발송된 메시지가 없습니다.")
    sys.exit(1)

print("\n최근 발송된 메시지:")
for idx, msg in enumerate(messages[:5], 1):
    print(f"\n{idx}. EmailMessage ID: {msg.id}")
    print(f"   수신자: {msg.to_email}")
    print(f"   발송 시간: {msg.created_at}")
    
    # 이벤트 확인
    events = EmailEvent.objects.filter(email_message=msg)
    print(f"   이벤트 수: {events.count()}개")
    for event in events:
        print(f"     - {event.event_type} at {event.event_at}")

# 2. 트래킹 URL 생성
print("\n" + "="*60)
print("트래킹 URL")
print("="*60)

first_msg = messages.first()
base_url = "http://127.0.0.1:8000/api/v1/campaigns"

print(f"\n메시지 ID: {first_msg.id}")
print(f"수신자: {first_msg.to_email}")

print(f"\n1. 오픈 픽셀 URL:")
print(f"   {base_url}/t/open/{first_msg.id}.png")

print(f"\n2. 클릭 트래킹 URL (예시):")
print(f"   {base_url}/t/click/{first_msg.id}?u=https://example.com")

print(f"\n3. 메시지 이벤트 조회 API:")
print(f"   GET {base_url}/messages/{first_msg.id}/events/")
print(f"   (인증 필요: Authorization: Token YOUR_TOKEN)")

print(f"\n4. 캠페인 이벤트 조회 API:")
campaign_id = first_msg.send_job.campaign.id
print(f"   GET {base_url}/campaigns/{campaign_id}/events/")
print(f"   (인증 필요: Authorization: Token YOUR_TOKEN)")

print("\n" + "="*60)
print("테스트 방법:")
print("="*60)
print("1. 브라우저에서 오픈 픽셀 URL 접속 (1x1 PNG 이미지 표시)")
print("2. 브라우저에서 클릭 트래킹 URL 접속 (리다이렉트 확인)")
print("3. python test_tracking_api.py 실행 (API 테스트)")
print("4. 받은 이메일의 HTML 소스에서 트래킹 픽셀 확인")
