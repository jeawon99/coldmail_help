"""
트래킹 API 테스트 (requests 사용)
"""
import os
import sys
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coldmail_project.settings.dev')
django.setup()

from campaigns.models import EmailMessage, EmailEvent
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()

print("="*60)
print("트래킹 API 자동 테스트")
print("="*60)

# 1. EmailMessage 확인
message = EmailMessage.objects.order_by('-created_at').first()
if not message:
    print("⚠️ 발송된 메시지가 없습니다.")
    sys.exit(1)

print(f"\n테스트 메시지 ID: {message.id}")
print(f"수신자: {message.to_email}")

# 2. 인증 토큰 가져오기
user = User.objects.filter(is_superuser=True).first()
if not user:
    print("⚠️ 슈퍼유저가 없습니다.")
    sys.exit(1)

token, _ = Token.objects.get_or_create(user=user)
headers = {'Authorization': f'Token {token.key}'}

base_url = "http://127.0.0.1:8000/api/v1"

print(f"\n인증 토큰: {token.key[:20]}...")

# 3. 오픈 픽셀 테스트
print("\n" + "="*60)
print("1. 오픈 픽셀 테스트")
print("="*60)

pixel_url = f"{base_url}/t/open/{message.id}.png"
print(f"URL: {pixel_url}")

try:
    response = requests.get(pixel_url)
    print(f"상태 코드: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"Content-Length: {len(response.content)} bytes")
    
    if response.status_code == 200:
        print("✅ 오픈 픽셀 반환 성공")
        
        # 이벤트 확인
        open_events = EmailEvent.objects.filter(
            email_message=message,
            event_type='opened_pixel'
        )
        print(f"opened_pixel 이벤트: {open_events.count()}개")
        
        if open_events.exists():
            event = open_events.first()
            print(f"  - 이벤트 시간: {event.event_at}")
            print(f"  - 메타데이터: {event.meta}")
    else:
        print(f"❌ 오픈 픽셀 실패: {response.text}")
        
except Exception as e:
    print(f"❌ 오픈 픽셀 요청 실패: {e}")

# 4. 중복 오픈 테스트
print("\n중복 오픈 테스트 (두 번째 요청)...")
try:
    response2 = requests.get(pixel_url)
    print(f"상태 코드: {response2.status_code}")
    
    open_events = EmailEvent.objects.filter(
        email_message=message,
        event_type='opened_pixel'
    )
    print(f"opened_pixel 이벤트 (여전히): {open_events.count()}개")
    
    if open_events.count() == 1:
        print("✅ 중복 방지 성공 (첫 오픈만 기록)")
    else:
        print(f"⚠️ 중복 기록됨: {open_events.count()}개")
        
except Exception as e:
    print(f"❌ 중복 오픈 테스트 실패: {e}")

# 5. 클릭 트래킹 테스트
print("\n" + "="*60)
print("2. 클릭 트래킹 테스트")
print("="*60)

click_url = f"{base_url}/t/click/{message.id}?u=https://example.com"
print(f"URL: {click_url}")

try:
    response = requests.get(click_url, allow_redirects=False)
    print(f"상태 코드: {response.status_code}")
    
    if response.status_code == 302:
        print(f"리다이렉트 위치: {response.headers.get('Location')}")
        print("✅ 클릭 트래킹 리다이렉트 성공")
        
        # 이벤트 확인
        click_events = EmailEvent.objects.filter(
            email_message=message,
            event_type='clicked'
        )
        print(f"clicked 이벤트: {click_events.count()}개")
        
        if click_events.exists():
            event = click_events.first()
            print(f"  - 이벤트 시간: {event.event_at}")
            print(f"  - 메타데이터: {event.meta}")
    else:
        print(f"❌ 클릭 트래킹 실패: {response.text}")
        
except Exception as e:
    print(f"❌ 클릭 트래킹 요청 실패: {e}")

# 6. 중복 클릭 테스트
print("\n중복 클릭 테스트 (두 번째 요청)...")
try:
    response2 = requests.get(click_url, allow_redirects=False)
    print(f"상태 코드: {response2.status_code}")
    
    click_events = EmailEvent.objects.filter(
        email_message=message,
        event_type='clicked'
    )
    print(f"clicked 이벤트: {click_events.count()}개")
    
    if click_events.count() >= 2:
        print("✅ 중복 클릭 기록 성공 (모든 클릭 기록)")
    else:
        print(f"⚠️ 클릭이 기록되지 않음")
        
except Exception as e:
    print(f"❌ 중복 클릭 테스트 실패: {e}")

# 7. 메시지 이벤트 조회 API
print("\n" + "="*60)
print("3. 메시지 이벤트 조회 API")
print("="*60)

events_url = f"{base_url}/messages/{message.id}/events/"
print(f"URL: {events_url}")

try:
    response = requests.get(events_url, headers=headers)
    print(f"상태 코드: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        data_wrapper = result.get('data', {})
        
        # 페이지네이션된 응답 처리
        if isinstance(data_wrapper, dict) and 'results' in data_wrapper:
            events = data_wrapper['results']
            total_count = data_wrapper.get('count', len(events))
            print(f"✅ 이벤트 조회 성공: {total_count}개 (현재 페이지: {len(events)}개)")
        elif isinstance(data_wrapper, list):
            events = data_wrapper
            print(f"✅ 이벤트 조회 성공: {len(events)}개")
        else:
            events = []
            print(f"⚠️ 예상치 못한 응답 형식")
        
        # 이벤트 출력
        for event in events[:3]:
            print(f"  - {event['event_type']} at {event['event_at']}")
    else:
        print(f"❌ 이벤트 조회 실패: {response.text}")
        
except Exception as e:
    import traceback
    print(f"❌ 이벤트 조회 요청 실패: {e}")
    traceback.print_exc()

# 8. 캠페인 이벤트 조회 API
print("\n" + "="*60)
print("4. 캠페인 이벤트 조회 API")
print("="*60)

campaign_id = message.send_job.campaign.id
campaign_events_url = f"{base_url}/campaigns/{campaign_id}/events/"
print(f"URL: {campaign_events_url}")

try:
    response = requests.get(campaign_events_url, headers=headers)
    print(f"상태 코드: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        data_wrapper = result.get('data', {})
        
        # 페이지네이션된 응답 처리
        if isinstance(data_wrapper, dict) and 'results' in data_wrapper:
            events = data_wrapper['results']
            total_count = data_wrapper.get('count', len(events))
            print(f"✅ 캠페인 이벤트 조회 성공: {total_count}개 (현재 페이지: {len(events)}개)")
        elif isinstance(data_wrapper, list):
            events = data_wrapper
            print(f"✅ 캠페인 이벤트 조회 성공: {len(events)}개")
        else:
            events = []
            print(f"⚠️ 예상치 못한 응답 형식")
        
        # 이벤트 타입별 집계
        if events and len(events) > 0:
            from collections import Counter
            event_types = Counter([e['event_type'] for e in events])
            print("  이벤트 타입 분포:")
            for event_type, count in event_types.items():
                print(f"    - {event_type}: {count}개")
    else:
        print(f"❌ 캠페인 이벤트 조회 실패: {response.text}")
        
except Exception as e:
    import traceback
    print(f"❌ 캠페인 이벤트 조회 요청 실패: {e}")
    traceback.print_exc()

# 9. 이벤트 필터링 테스트
print("\n" + "="*60)
print("5. 이벤트 필터링 테스트")
print("="*60)

filter_url = f"{campaign_events_url}?event_type=sent"
print(f"URL: {filter_url}")

try:
    response = requests.get(filter_url, headers=headers)
    print(f"상태 코드: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        data_wrapper = result.get('data', {})
        
        # 페이지네이션된 응답 처리
        if isinstance(data_wrapper, dict) and 'results' in data_wrapper:
            events = data_wrapper['results']
            total_count = data_wrapper.get('count', len(events))
            print(f"✅ 필터링 성공: sent 이벤트 {total_count}개 (현재 페이지: {len(events)}개)")
        elif isinstance(data_wrapper, list):
            events = data_wrapper
            print(f"✅ 필터링 성공: sent 이벤트 {len(events)}개")
        else:
            print(f"⚠️ 예상치 못한 응답 형식")
    else:
        print(f"❌ 필터링 실패: {response.text}")
        
except Exception as e:
    print(f"❌ 필터링 요청 실패: {e}")

print("\n" + "="*60)
print("테스트 완료!")
print("="*60)
