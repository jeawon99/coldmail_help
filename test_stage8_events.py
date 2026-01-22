"""
Stage 8: 이벤트 트래킹 테스트

오픈 픽셀, 클릭 트래킹, 이벤트 조회 API 테스트
"""
import requests
import time
from pprint import pprint

BASE_URL = "http://127.0.0.1:8000/api/v1"

# 인증 토큰 (실제 토큰으로 교체 필요)
TOKEN = "your-auth-token-here"

def get_headers():
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }


def test_1_get_email_message():
    """1. EmailMessage ID 가져오기"""
    print("\n" + "="*50)
    print("TEST 1: EmailMessage ID 조회")
    print("="*50)
    
    # SendJob에서 sent 상태인 것 조회
    response = requests.get(
        f"{BASE_URL}/campaigns/jobs/?status=sent&page_size=1",
        headers=get_headers()
    )
    
    if response.status_code != 200:
        print("❌ SendJob 조회 실패")
        return None
    
    data = response.json()['data']
    if not data['results']:
        print("⚠️ sent 상태의 SendJob이 없습니다.")
        return None
    
    send_job = data['results'][0]
    send_job_id = send_job['id']
    
    print(f"✅ SendJob 발견: {send_job_id}")
    print(f"   수신자: {send_job['to_email']}")
    print(f"   상태: {send_job['status']}")
    
    # EmailMessage 조회 (send_job.email_message 관계)
    # 직접 DB에서 조회하거나 API로 조회
    # 여기서는 간단히 send_job_id를 반환
    return send_job_id


def test_2_track_open_pixel(message_id):
    """2. 오픈 픽셀 트래킹 테스트"""
    print("\n" + "="*50)
    print("TEST 2: 오픈 픽셀 트래킹")
    print("="*50)
    
    # 오픈 픽셀 요청 (인증 불필요)
    url = f"{BASE_URL}/campaigns/t/open/{message_id}.png"
    print(f"픽셀 URL: {url}")
    
    # 첫 번째 오픈 (기록됨)
    response1 = requests.get(url)
    print(f"\n첫 번째 오픈: {response1.status_code}")
    print(f"Content-Type: {response1.headers.get('Content-Type')}")
    print(f"Content-Length: {len(response1.content)} bytes")
    
    time.sleep(1)
    
    # 두 번째 오픈 (중복, 기록 안됨)
    response2 = requests.get(url)
    print(f"\n두 번째 오픈: {response2.status_code} (중복, 기록되지 않음)")
    
    if response1.status_code == 200 and response1.headers.get('Content-Type') == 'image/png':
        print("\n✅ 오픈 픽셀 트래킹 성공")
        return True
    else:
        print("\n❌ 오픈 픽셀 트래킹 실패")
        return False


def test_3_track_click(message_id):
    """3. 클릭 트래킹 테스트"""
    print("\n" + "="*50)
    print("TEST 3: 클릭 트래킹")
    print("="*50)
    
    # 클릭 트래킹 URL (인증 불필요)
    target_url = "https://example.com/landing"
    url = f"{BASE_URL}/campaigns/t/click/{message_id}?u={target_url}"
    print(f"클릭 URL: {url}")
    print(f"타겟 URL: {target_url}")
    
    # 클릭 (리다이렉트 비활성화하여 302 확인)
    response = requests.get(url, allow_redirects=False)
    print(f"\n응답: {response.status_code}")
    
    if response.status_code == 302:
        redirect_url = response.headers.get('Location')
        print(f"리다이렉트: {redirect_url}")
        
        if redirect_url == target_url:
            print("\n✅ 클릭 트래킹 성공 (올바른 리다이렉트)")
            return True
        else:
            print(f"\n❌ 잘못된 리다이렉트 URL: {redirect_url}")
            return False
    else:
        print("\n❌ 클릭 트래킹 실패")
        return False


def test_4_get_message_events(message_id):
    """4. 메시지 이벤트 조회"""
    print("\n" + "="*50)
    print("TEST 4: 메시지 이벤트 조회")
    print("="*50)
    
    # EmailMessage ID로 이벤트 조회
    # 실제로는 EmailMessage의 진짜 ID가 필요함
    # 여기서는 테스트를 위해 Django shell로 확인 필요
    
    print("⚠️ 이 테스트는 Django shell에서 EmailMessage ID를 직접 확인 후 실행하세요:")
    print(f"   python manage.py shell")
    print(f"   from campaigns.models import SendJob, EmailMessage")
    print(f"   job = SendJob.objects.get(id='{message_id}')")
    print(f"   msg = job.email_message")
    print(f"   print(msg.id)")
    print(f"   # 그 다음: GET /api/v1/campaigns/messages/{{msg_id}}/events/")


def test_5_get_campaign_events(campaign_id=None):
    """5. 캠페인 이벤트 조회"""
    print("\n" + "="*50)
    print("TEST 5: 캠페인 이벤트 조회")
    print("="*50)
    
    if not campaign_id:
        # 첫 번째 캠페인 조회
        response = requests.get(
            f"{BASE_URL}/campaigns/campaigns/?page_size=1",
            headers=get_headers()
        )
        
        if response.status_code != 200:
            print("❌ 캠페인 조회 실패")
            return
        
        data = response.json()['data']
        if not data['results']:
            print("⚠️ 캠페인이 없습니다.")
            return
        
        campaign_id = data['results'][0]['id']
    
    print(f"캠페인 ID: {campaign_id}")
    
    # 캠페인 이벤트 조회
    response = requests.get(
        f"{BASE_URL}/campaigns/campaigns/{campaign_id}/events/",
        headers=get_headers()
    )
    
    print(f"\n응답: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()['data']
        print(f"\n총 이벤트: {data['count']}개")
        
        if data['results']:
            print("\n최근 이벤트 3개:")
            for event in data['results'][:3]:
                print(f"  - {event['event_type']} @ {event['event_at']}")
                print(f"    메시지: {event['email_message']}")
                if event.get('meta'):
                    print(f"    메타: {event['meta']}")
        
        print("\n✅ 캠페인 이벤트 조회 성공")
    else:
        print("\n❌ 캠페인 이벤트 조회 실패")
        pprint(response.json())


def test_6_event_type_filter(campaign_id=None):
    """6. 이벤트 타입 필터링 테스트"""
    print("\n" + "="*50)
    print("TEST 6: 이벤트 타입 필터링")
    print("="*50)
    
    if not campaign_id:
        # 첫 번째 캠페인 조회
        response = requests.get(
            f"{BASE_URL}/campaigns/campaigns/?page_size=1",
            headers=get_headers()
        )
        
        if response.status_code == 200:
            data = response.json()['data']
            if data['results']:
                campaign_id = data['results'][0]['id']
    
    if not campaign_id:
        print("⚠️ 캠페인을 찾을 수 없습니다.")
        return
    
    print(f"캠페인 ID: {campaign_id}")
    
    # opened_pixel 이벤트만 조회
    response = requests.get(
        f"{BASE_URL}/campaigns/campaigns/{campaign_id}/events/?event_type=opened_pixel",
        headers=get_headers()
    )
    
    if response.status_code == 200:
        data = response.json()['data']
        print(f"\n오픈 이벤트: {data['count']}개")
    
    # clicked 이벤트만 조회
    response = requests.get(
        f"{BASE_URL}/campaigns/campaigns/{campaign_id}/events/?event_type=clicked",
        headers=get_headers()
    )
    
    if response.status_code == 200:
        data = response.json()['data']
        print(f"클릭 이벤트: {data['count']}개")
    
    print("\n✅ 이벤트 타입 필터링 테스트 완료")


if __name__ == "__main__":
    print("="*50)
    print("Stage 8: 이벤트 트래킹 테스트")
    print("="*50)
    
    # TEST 1: EmailMessage ID 조회
    send_job_id = test_1_get_email_message()
    
    if send_job_id:
        # TEST 2: 오픈 픽셀 트래킹
        # 참고: send_job_id를 EmailMessage ID로 변환 필요
        # 실제로는 Django shell에서 EmailMessage ID를 확인해야 함
        print("\n⚠️ 오픈 픽셀과 클릭 트래킹 테스트는 실제 EmailMessage ID가 필요합니다.")
        print("   Django shell에서 확인:")
        print(f"   job = SendJob.objects.get(id='{send_job_id}')")
        print(f"   msg = job.email_message")
        print(f"   print(msg.id)")
    
    # TEST 5: 캠페인 이벤트 조회
    test_5_get_campaign_events()
    
    # TEST 6: 이벤트 타입 필터링
    test_6_event_type_filter()
    
    print("\n" + "="*50)
    print("테스트 완료!")
    print("="*50)
    print("\n다음 단계:")
    print("1. Django shell에서 EmailMessage ID 확인")
    print("2. 오픈 픽셀 URL 테스트: GET /api/v1/campaigns/t/open/{message_id}.png")
    print("3. 클릭 트래킹 URL 테스트: GET /api/v1/campaigns/t/click/{message_id}?u=https://example.com")
    print("4. 이벤트 조회: GET /api/v1/campaigns/messages/{message_id}/events/")
