"""
Stage 5 - Campaign CRUD + Freeze Targets 테스트
"""
import requests
import json
from pprint import pprint

BASE_URL = "http://localhost:8000/api/v1"

# JWT 토큰 (test_stage4_segments.py에서 발급받은 토큰 재사용)
TOKEN = None

def get_headers():
    """인증 헤더"""
    if TOKEN:
        return {
            'Authorization': f'Bearer {TOKEN}',
            'Content-Type': 'application/json'
        }
    return {'Content-Type': 'application/json'}

def login():
    """로그인"""
    global TOKEN
    response = requests.post(
        f"{BASE_URL}/auth/token/",
        json={
            "username": "admin",
            "password": "admin123"
        }
    )
    if response.status_code == 200:
        data = response.json()
        TOKEN = data['access']
        print("✅ 로그인 성공")
        print(f"Token: {TOKEN[:50]}...")
    else:
        print("❌ 로그인 실패")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")

def test_1_create_segment():
    """1. 테스트용 세그먼트 생성"""
    print("\n" + "="*50)
    print("TEST 1: 세그먼트 생성")
    print("="*50)
    
    response = requests.post(
        f"{BASE_URL}/segments/",
        headers=get_headers(),
        json={
            "name": "Stage5 테스트 - Shorts 유튜버",
            "filter_json": {
                "all": [
                    {"field": "keywords_raw", "op": "contains_any", "value": ["shorts", "쇼츠"]},
                    {"field": "subscriber_count", "op": ">=", "value": 50000},
                    {"field": "primary_email", "op": "is_not_null"}
                ]
            }
        }
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    pprint(data)
    
    if response.status_code == 201:
        segment_id = data['data']['id']
        print(f"\n✅ 세그먼트 생성 성공: {segment_id}")
        return segment_id
    else:
        print("\n❌ 세그먼트 생성 실패")
        return None

def test_2_preview_segment(segment_id):
    """2. 세그먼트 미리보기 (대상 수 확인)"""
    print("\n" + "="*50)
    print("TEST 2: 세그먼트 미리보기")
    print("="*50)
    
    response = requests.post(
        f"{BASE_URL}/segments/{segment_id}/preview/",
        headers=get_headers(),
        json={
            "exclude_suppression": True,
            "exclude_do_not_contact": True,
            "sample_size": 3
        }
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    
    if response.status_code == 200:
        total_count = data['data']['total_count']
        print(f"\n✅ 대상 리드 수: {total_count}개")
        print(f"샘플 리드:")
        for lead in data['data']['sample_leads']:
            print(f"  - {lead['channel_name']} (구독자: {lead['subscriber_count']:,})")
        return total_count
    else:
        print("\n❌ 미리보기 실패")
        pprint(data)
        return 0

def test_3_create_campaign(segment_id):
    """3. 캠페인 생성"""
    print("\n" + "="*50)
    print("TEST 3: 캠페인 생성")
    print("="*50)
    
    response = requests.post(
        f"{BASE_URL}/campaigns/",
        headers=get_headers(),
        json={
            "name": "Stage5 테스트 캠페인",
            "segment": segment_id,
            "daily_cap": 30,
            "timezone": "Asia/Seoul"
        }
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    pprint(data)
    
    if response.status_code == 201:
        campaign_id = data['data']['id']
        print(f"\n✅ 캠페인 생성 성공: {campaign_id}")
        print(f"상태: {data['data']['status']}")
        print(f"세그먼트: {data['data']['segment_name']}")
        return campaign_id
    else:
        print("\n❌ 캠페인 생성 실패")
        return None

def test_4_freeze_targets(campaign_id):
    """4. 타겟 확정 (freeze-targets)"""
    print("\n" + "="*50)
    print("TEST 4: 타겟 확정 (Freeze Targets)")
    print("="*50)
    
    response = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/freeze-targets/",
        headers=get_headers(),
        json={
            "force": False,
            "save_snapshot": True
        }
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    pprint(data)
    
    if response.status_code == 200:
        frozen_count = data['data']['frozen_target_count']
        print(f"\n✅ 타겟 확정 성공: {frozen_count}개")
        print(f"확정 시각: {data['data']['frozen_at']}")
        return frozen_count
    else:
        print("\n❌ 타겟 확정 실패")
        return 0

def test_5_freeze_idempotent(campaign_id):
    """5. 타겟 확정 Idempotent 테스트 (중복 확정 방지)"""
    print("\n" + "="*50)
    print("TEST 5: Idempotent 테스트 (중복 확정 시도)")
    print("="*50)
    
    response = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/freeze-targets/",
        headers=get_headers(),
        json={
            "force": False,
            "save_snapshot": True
        }
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    pprint(data)
    
    if response.status_code == 400:
        print("\n✅ Idempotent 성공: 중복 확정 방지됨")
        print(f"메시지: {data.get('message', data.get('error'))}")
    else:
        print("\n⚠️ Idempotent 실패: 중복 확정이 허용됨")

def test_6_get_targets(campaign_id):
    """6. 타겟 목록 조회"""
    print("\n" + "="*50)
    print("TEST 6: 타겟 목록 조회")
    print("="*50)
    
    response = requests.get(
        f"{BASE_URL}/campaigns/{campaign_id}/targets/?page_size=5",
        headers=get_headers()
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    
    if response.status_code == 200:
        results = data['data']['results'] if 'results' in data['data'] else data['data']
        print(f"\n✅ 타겟 목록 조회 성공")
        print(f"총 {data['data'].get('count', len(results))}개 타겟")
        print(f"\n샘플 타겟 (최대 5개):")
        for target in results[:5]:
            snapshot = target.get('snapshot', {})
            print(f"  - {target['lead_channel_name']} (구독자: {target['lead_subscriber_count']:,})")
            print(f"    이메일: {target['lead_primary_email']}, 상태: {target['status']}")
            if snapshot:
                print(f"    스냅샷 저장됨: frozen_at={snapshot.get('frozen_at', 'N/A')[:19]}")
    else:
        print("\n❌ 타겟 목록 조회 실패")
        pprint(data)

def test_7_targets_filter(campaign_id):
    """7. 타겟 필터링 (구독자 수 범위)"""
    print("\n" + "="*50)
    print("TEST 7: 타겟 필터링 (구독자 10만+ 이상)")
    print("="*50)
    
    response = requests.get(
        f"{BASE_URL}/campaigns/{campaign_id}/targets/?subscriber_count_min=100000&page_size=3",
        headers=get_headers()
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    
    if response.status_code == 200:
        results = data['data']['results'] if 'results' in data['data'] else data['data']
        print(f"\n✅ 필터링 성공")
        print(f"구독자 10만+ 타겟: {data['data'].get('count', len(results))}개")
        for target in results[:3]:
            print(f"  - {target['lead_channel_name']} (구독자: {target['lead_subscriber_count']:,})")
    else:
        print("\n❌ 필터링 실패")
        pprint(data)

def test_8_campaign_list():
    """8. 캠페인 목록 조회"""
    print("\n" + "="*50)
    print("TEST 8: 캠페인 목록 조회")
    print("="*50)
    
    response = requests.get(
        f"{BASE_URL}/campaigns/",
        headers=get_headers()
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    
    if response.status_code == 200:
        results = data['data']['results'] if 'results' in data['data'] else data['data']
        print(f"\n✅ 캠페인 목록 조회 성공")
        print(f"총 {len(results)}개 캠페인")
        for campaign in results:
            print(f"\n캠페인: {campaign['name']}")
            print(f"  상태: {campaign['status']}")
            print(f"  세그먼트: {campaign.get('segment_name', 'N/A')}")
            print(f"  확정 타겟 수: {campaign.get('frozen_target_count', 'N/A')}")
            print(f"  실제 타겟 수: {campaign.get('targets_count', 'N/A')}")
    else:
        print("\n❌ 캠페인 목록 조회 실패")
        pprint(data)

def test_9_start_campaign(campaign_id):
    """9. 캠페인 시작"""
    print("\n" + "="*50)
    print("TEST 9: 캠페인 시작")
    print("="*50)
    
    response = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/start/",
        headers=get_headers()
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    pprint(data)
    
    if response.status_code == 200:
        print(f"\n✅ 캠페인 시작 성공")
        print(f"상태: {data['data']['status']}")
    else:
        print("\n❌ 캠페인 시작 실패")

def test_10_pause_campaign(campaign_id):
    """10. 캠페인 일시정지"""
    print("\n" + "="*50)
    print("TEST 10: 캠페인 일시정지")
    print("="*50)
    
    response = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/pause/",
        headers=get_headers()
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    pprint(data)
    
    if response.status_code == 200:
        print(f"\n✅ 캠페인 일시정지 성공")
        print(f"상태: {data['data']['status']}")
    else:
        print("\n❌ 캠페인 일시정지 실패")

def test_11_targets_add(campaign_id):
    """11. 타겟 수동 추가"""
    print("\n" + "="*50)
    print("TEST 11: 타겟 수동 추가")
    print("="*50)
    
    # 임의의 리드 1개 조회 (세그먼트 조건 밖)
    leads_response = requests.get(
        f"{BASE_URL}/leads/?page_size=1&subscriber_count_max=10000",
        headers=get_headers()
    )
    
    if leads_response.status_code == 200:
        leads_data = leads_response.json()
        results = leads_data['data']['results'] if 'results' in leads_data['data'] else leads_data['data']
        if results:
            lead_id = results[0]['id']
            print(f"추가할 리드: {results[0]['channel_name']} (ID: {lead_id})")
            
            response = requests.post(
                f"{BASE_URL}/campaigns/{campaign_id}/targets/add/",
                headers=get_headers(),
                json={
                    "lead_ids": [lead_id],
                    "save_snapshot": True
                }
            )
            
            print(f"\nStatus: {response.status_code}")
            data = response.json()
            pprint(data)
            
            if response.status_code == 200:
                print(f"\n✅ 타겟 추가 성공")
                print(f"추가된 타겟: {data['data']['added_count']}개")
                print(f"전체 타겟: {data['data']['total_targets']}개")
            else:
                print("\n❌ 타겟 추가 실패")
        else:
            print("\n⚠️ 추가할 리드를 찾을 수 없음")
    else:
        print("\n❌ 리드 조회 실패")

def test_12_get_campaign_detail(campaign_id):
    """12. 캠페인 상세 조회"""
    print("\n" + "="*50)
    print("TEST 12: 캠페인 상세 조회")
    print("="*50)
    
    response = requests.get(
        f"{BASE_URL}/campaigns/{campaign_id}/",
        headers=get_headers()
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    pprint(data)
    
    if response.status_code == 200:
        print(f"\n✅ 캠페인 상세 조회 성공")
        campaign = data['data']
        print(f"\n캠페인 요약:")
        print(f"  이름: {campaign['name']}")
        print(f"  상태: {campaign['status']}")
        print(f"  세그먼트: {campaign['segment_name']}")
        print(f"  확정 타겟 수: {campaign['frozen_target_count']}")
        print(f"  실제 타겟 수: {campaign['targets_count']}")
        print(f"  일일 발송 제한: {campaign['daily_cap']}")
        print(f"  확정 시각: {campaign['frozen_at']}")
    else:
        print("\n❌ 캠페인 상세 조회 실패")


def main():
    """메인 테스트"""
    print("="*50)
    print("Stage 5 - Campaign CRUD + Freeze Targets 테스트")
    print("="*50)
    
    # 로그인
    login()
    
    if not TOKEN:
        print("\n❌ 로그인 실패로 테스트 중단")
        return
    
    # 1. 세그먼트 생성
    segment_id = test_1_create_segment()
    if not segment_id:
        print("\n❌ 세그먼트 생성 실패로 테스트 중단")
        return
    
    # 2. 세그먼트 미리보기
    expected_count = test_2_preview_segment(segment_id)
    
    # 3. 캠페인 생성
    campaign_id = test_3_create_campaign(segment_id)
    if not campaign_id:
        print("\n❌ 캠페인 생성 실패로 테스트 중단")
        return
    
    # 4. 타겟 확정
    frozen_count = test_4_freeze_targets(campaign_id)
    
    # 5. Idempotent 테스트
    test_5_freeze_idempotent(campaign_id)
    
    # 6. 타겟 목록 조회
    test_6_get_targets(campaign_id)
    
    # 7. 타겟 필터링
    test_7_targets_filter(campaign_id)
    
    # 8. 캠페인 목록 조회
    test_8_campaign_list()
    
    # 9. 캠페인 시작
    test_9_start_campaign(campaign_id)
    
    # 10. 캠페인 일시정지
    test_10_pause_campaign(campaign_id)
    
    # 11. 타겟 수동 추가
    test_11_targets_add(campaign_id)
    
    # 12. 캠페인 상세 조회 (최종 상태)
    test_12_get_campaign_detail(campaign_id)
    
    print("\n" + "="*50)
    print("테스트 완료!")
    print("="*50)
    print(f"\n생성된 리소스:")
    print(f"  Segment ID: {segment_id}")
    print(f"  Campaign ID: {campaign_id}")
    print(f"  예상 대상 수: {expected_count}개")
    print(f"  확정 타겟 수: {frozen_count}개")

if __name__ == '__main__':
    main()
