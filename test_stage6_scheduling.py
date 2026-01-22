"""
Stage 6 - Scheduling API (SendJob) 테스트
"""
import requests
import json
from pprint import pprint
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api/v1"
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

def test_1_create_template():
    """1. 테스트용 템플릿 생성"""
    print("\n" + "="*50)
    print("TEST 1: 템플릿 생성")
    print("="*50)
    
    # 템플릿 생성
    response = requests.post(
        f"{BASE_URL}/templates/",
        headers=get_headers(),
        json={
            "name": "Stage6 테스트 템플릿",
            "purpose": "intro",
            "is_active": True
        }
    )
    
    print(f"템플릿 생성 Status: {response.status_code}")
    if response.status_code != 201:
        pprint(response.json())
        return None, None
    
    template_id = response.json()['data']['id']
    print(f"템플릿 ID: {template_id}")
    
    # 템플릿 버전 생성
    response2 = requests.post(
        f"{BASE_URL}/templates/{template_id}/versions/",
        headers=get_headers(),
        json={
            "subject_tpl": "안녕하세요 {{ channel_name }}님!",
            "body_tpl": "구독자 {{ subscriber_count }}명의 인기 유튜버이시네요! 협업 제안드립니다.",
            "format": "text"
        }
    )
    
    print(f"템플릿 버전 생성 Status: {response2.status_code}")
    if response2.status_code != 201:
        pprint(response2.json())
        return None, None
    
    version_id = response2.json()['data']['id']
    print(f"버전 ID: {version_id}")
    print(f"✅ 템플릿 생성 완료: version {version_id}")
    
    return template_id, version_id

def test_2_schedule_jobs(campaign_id, template_version_id):
    """2. 발송 잡 예약 생성"""
    print("\n" + "="*50)
    print("TEST 2: 발송 잡 예약 생성")
    print("="*50)
    
    # 시작 시간: 내일 오전 9시
    tomorrow = datetime.now() + timedelta(days=1)
    start_at = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
    
    response = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/schedule/",
        headers=get_headers(),
        json={
            "template_version_id": template_version_id,
            "start_at": start_at.isoformat(),
            "daily_cap": 50
        }
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    pprint(data)
    
    if response.status_code == 200:
        print(f"\n✅ 발송 잡 예약 성공")
        print(f"전체 타겟: {data['data']['total_targets']}개")
        print(f"예약된 잡: {data['data']['scheduled_count']}개")
        print(f"스킵된 타겟: {data['data']['skipped_count']}개")
        print(f"\n스킵 사유:")
        for reason, count in data['data']['skip_reasons'].items():
            if count > 0:
                print(f"  - {reason}: {count}개")
        print(f"\n예약된 날짜: {len(data['data']['scheduled_dates'])}일")
        for date in data['data']['scheduled_dates'][:5]:
            print(f"  - {date}")
        if len(data['data']['scheduled_dates']) > 5:
            print(f"  ... 외 {len(data['data']['scheduled_dates']) - 5}개")
        return data['data']['scheduled_count']
    else:
        print("\n❌ 발송 잡 예약 실패")
        return 0

def test_3_get_jobs(campaign_id):
    """3. 발송 잡 목록 조회"""
    print("\n" + "="*50)
    print("TEST 3: 발송 잡 목록 조회")
    print("="*50)
    
    response = requests.get(
        f"{BASE_URL}/campaigns/{campaign_id}/jobs/?page_size=5",
        headers=get_headers()
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    
    if response.status_code == 200:
        results = data['data']['results']
        total_count = data['data']['count']
        print(f"\n✅ 발송 잡 목록 조회 성공")
        print(f"총 {total_count}개 잡")
        print(f"\n샘플 잡 (최대 5개):")
        for job in results[:5]:
            print(f"  - {job['lead_channel_name']} ({job['to_email']})")
            print(f"    예약시간: {job['scheduled_at']}, 상태: {job['status']}")
        
        # 첫 번째 잡 ID 반환
        if results:
            return results[0]['id']
    else:
        print("\n❌ 발송 잡 목록 조회 실패")
        pprint(data)
    
    return None

def test_4_filter_jobs_by_status(campaign_id):
    """4. 상태별 잡 필터링"""
    print("\n" + "="*50)
    print("TEST 4: 상태별 잡 필터링 (scheduled)")
    print("="*50)
    
    # 캠페인 ID를 문자열로 전달
    url = f"{BASE_URL}/campaigns/{str(campaign_id)}/jobs/?status=scheduled&page_size=3"
    print(f"요청 URL: {url}")
    
    response = requests.get(
        url,
        headers=get_headers()
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    
    if response.status_code == 200:
        results = data['data']['results']
        count = data['data']['count']
        print(f"\n✅ 필터링 성공")
        print(f"scheduled 상태 잡: {count}개")
        for job in results[:3]:
            print(f"  - {job['lead_channel_name']}: {job['status']}")
    else:
        print("\n❌ 필터링 실패")
        pprint(data)

def test_5_reschedule_job(job_id):
    """5. 잡 재예약"""
    print("\n" + "="*50)
    print("TEST 5: 잡 재예약")
    print("="*50)
    
    # 새로운 예약 시간: 3일 후 오전 10시
    new_time = datetime.now() + timedelta(days=3)
    new_time = new_time.replace(hour=10, minute=0, second=0, microsecond=0)
    
    response = requests.patch(
        f"{BASE_URL}/jobs/{job_id}/reschedule/",
        headers=get_headers(),
        json={
            "scheduled_at": new_time.isoformat()
        }
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    pprint(data)
    
    if response.status_code == 200:
        print(f"\n✅ 재예약 성공")
        print(f"새 예약시간: {data['data']['scheduled_at']}")
    else:
        print("\n❌ 재예약 실패")

def test_6_cancel_job(job_id):
    """6. 잡 취소"""
    print("\n" + "="*50)
    print("TEST 6: 잡 취소")
    print("="*50)
    
    response = requests.post(
        f"{BASE_URL}/jobs/{job_id}/cancel/",
        headers=get_headers(),
        json={
            "reason": "테스트 목적 취소"
        }
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    pprint(data)
    
    if response.status_code == 200:
        print(f"\n✅ 취소 성공")
        print(f"상태: {data['data']['status']}")
        print(f"에러 메시지: {data['data'].get('last_error', 'N/A')}")
    else:
        print("\n❌ 취소 실패")

def test_7_get_job_detail(job_id):
    """7. 잡 상세 조회"""
    print("\n" + "="*50)
    print("TEST 7: 잡 상세 조회")
    print("="*50)
    
    response = requests.get(
        f"{BASE_URL}/jobs/{job_id}/",
        headers=get_headers()
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    pprint(data)
    
    if response.status_code == 200:
        job = data['data']
        print(f"\n✅ 잡 상세 조회 성공")
        print(f"\n잡 정보:")
        print(f"  캠페인: {job['campaign_name']}")
        print(f"  리드: {job['lead_channel_name']}")
        print(f"  수신: {job['to_email']}")
        print(f"  템플릿: {job['template_name']} v{job['template_version_number']}")
        print(f"  예약시간: {job['scheduled_at']}")
        print(f"  상태: {job['status']}")
        print(f"  시도 횟수: {job['attempt_count']}")
    else:
        print("\n❌ 잡 상세 조회 실패")

def test_8_simulate_failed_job(campaign_id):
    """8. Failed 잡 시뮬레이션 및 재시도"""
    print("\n" + "="*50)
    print("TEST 8: Failed 잡 재시도 테스트")
    print("="*50)
    
    # 잡 목록 조회
    response = requests.get(
        f"{BASE_URL}/campaigns/{campaign_id}/jobs/?status=scheduled&page_size=1",
        headers=get_headers()
    )
    
    if response.status_code != 200 or not response.json()['data']['results']:
        print("⚠️ scheduled 잡이 없어서 스킵")
        return
    
    job_id = response.json()['data']['results'][0]['id']
    
    # Django admin이나 직접 DB 수정으로 failed 상태로 변경해야 하는데,
    # 테스트 환경에서는 API로 직접 변경 불가능하므로 스킵
    print("ℹ️ Failed 상태 테스트는 실제 발송 실패 후 진행 가능")
    print(f"   (Job ID: {job_id}를 수동으로 failed 상태로 변경 후 retry 테스트)")

def test_9_schedule_duplicate(campaign_id, template_version_id):
    """9. 중복 예약 방지 테스트"""
    print("\n" + "="*50)
    print("TEST 9: 중복 예약 방지 테스트")
    print("="*50)
    
    # 동일한 조건으로 다시 예약 시도
    tomorrow = datetime.now() + timedelta(days=1)
    start_at = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
    
    response = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/schedule/",
        headers=get_headers(),
        json={
            "template_version_id": template_version_id,
            "start_at": start_at.isoformat(),
            "daily_cap": 50
        }
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    
    if response.status_code == 200:
        print(f"\n✅ 중복 예약 방지 동작")
        print(f"예약된 잡: {data['data']['scheduled_count']}개")
        print(f"already_scheduled: {data['data']['skip_reasons']['already_scheduled']}개")
        
        if data['data']['skip_reasons']['already_scheduled'] > 0:
            print("✅ 이미 예약된 타겟은 스킵됨")
    else:
        print("\n❌ 중복 예약 테스트 실패")
        pprint(data)

def test_10_daily_cap_distribution(campaign_id, template_version_id):
    """10. Daily Cap 분배 확인"""
    print("\n" + "="*50)
    print("TEST 10: Daily Cap 분배 확인")
    print("="*50)
    
    # 날짜별 잡 수 확인
    response = requests.get(
        f"{BASE_URL}/campaigns/{campaign_id}/jobs/?page_size=1000",
        headers=get_headers()
    )
    
    if response.status_code == 200:
        jobs = response.json()['data']['results']
        
        # 날짜별 그룹화
        from collections import defaultdict
        jobs_by_date = defaultdict(int)
        
        for job in jobs:
            if job['status'] == 'scheduled':
                date = job['scheduled_at'][:10]  # YYYY-MM-DD
                jobs_by_date[date] += 1
        
        print(f"\n✅ Daily Cap 분배 확인")
        print(f"총 scheduled 잡: {len([j for j in jobs if j['status'] == 'scheduled'])}개")
        print(f"\n날짜별 분배:")
        for date in sorted(jobs_by_date.keys()):
            count = jobs_by_date[date]
            print(f"  {date}: {count}개")
            if count > 50:
                print(f"    ⚠️ Daily cap(50) 초과!")
    else:
        print("\n❌ 잡 목록 조회 실패")
        pprint(response.json())


def main():
    """메인 테스트"""
    print("="*50)
    print("Stage 6 - Scheduling API (SendJob) 테스트")
    print("="*50)
    
    # 로그인
    login()
    
    if not TOKEN:
        print("\n❌ 로그인 실패로 테스트 중단")
        return
    
    # 기존 캠페인 조회 (Stage 5에서 생성된 캠페인 사용)
    response = requests.get(
        f"{BASE_URL}/campaigns/?page_size=1",
        headers=get_headers()
    )
    
    if response.status_code != 200 or not response.json()['data']['results']:
        print("\n❌ 캠페인이 없습니다. Stage 5를 먼저 실행하세요.")
        return
    
    campaign = response.json()['data']['results'][0]
    campaign_id = campaign['id']
    
    print(f"\n사용할 캠페인: {campaign['name']} (ID: {campaign_id})")
    print(f"확정 타겟 수: {campaign.get('frozen_target_count', 'N/A')}")
    
    if not campaign.get('frozen_target_count'):
        print("\n❌ 타겟이 확정되지 않았습니다. Stage 5의 freeze-targets를 먼저 실행하세요.")
        return
    
    # 1. 템플릿 생성
    template_id, template_version_id = test_1_create_template()
    if not template_version_id:
        print("\n❌ 템플릿 생성 실패로 테스트 중단")
        return
    
    # 2. 발송 잡 예약
    scheduled_count = test_2_schedule_jobs(campaign_id, template_version_id)
    
    if scheduled_count == 0:
        print("\n⚠️ 예약된 잡이 없어서 일부 테스트 스킵")
        return
    
    # 3. 잡 목록 조회
    first_job_id = test_3_get_jobs(campaign_id)
    
    # 4. 상태별 필터링
    test_4_filter_jobs_by_status(campaign_id)
    
    if first_job_id:
        # 5. 잡 재예약
        test_5_reschedule_job(first_job_id)
        
        # 6. 잡 취소
        test_6_cancel_job(first_job_id)
        
        # 7. 잡 상세 조회
        test_7_get_job_detail(first_job_id)
    
    # 8. Failed 잡 재시도 (시뮬레이션)
    test_8_simulate_failed_job(campaign_id)
    
    # 9. 중복 예약 방지
    test_9_schedule_duplicate(campaign_id, template_version_id)
    
    # 10. Daily Cap 분배 확인
    test_10_daily_cap_distribution(campaign_id, template_version_id)
    
    print("\n" + "="*50)
    print("테스트 완료!")
    print("="*50)
    print(f"\n생성된 리소스:")
    print(f"  Campaign ID: {campaign_id}")
    print(f"  Template ID: {template_id}")
    print(f"  Template Version ID: {template_version_id}")
    print(f"  Scheduled Jobs: {scheduled_count}개")

if __name__ == '__main__':
    main()
