"""
Stage 7 - Worker (내부) + 발송 결과 저장 테스트
"""
import requests
import json
import time
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

def test_1_create_scheduled_jobs():
    """1. 즉시 발송될 잡 생성"""
    print("\n" + "="*50)
    print("TEST 1: 즉시 발송될 잡 생성")
    print("="*50)
    
    # 기존 SendJob 삭제
    print("\n기존 SendJob 정리 중...")
    import subprocess
    cmd = [
        "conda", "run", "-n", "coldmail",
        "python", "manage.py", "shell", "-c",
        "from campaigns.models import SendJob; count = SendJob.objects.all().count(); SendJob.objects.all().delete(); print(f'삭제된 SendJob: {count}개')"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        print(result.stdout)
    except Exception as e:
        print(f"⚠️ SendJob 정리 실패 (무시하고 계속): {e}")
    
    # 기존 캠페인 조회
    response = requests.get(
        f"{BASE_URL}/campaigns/?page_size=1",
        headers=get_headers()
    )
    
    if response.status_code != 200 or not response.json()['data']['results']:
        print("\n❌ 캠페인이 없습니다. Stage 5를 먼저 실행하세요.")
        return None, None
    
    campaign = response.json()['data']['results'][0]
    campaign_id = campaign['id']
    print(f"캠페인: {campaign['name']} (ID: {campaign_id})")
    
    # 템플릿 조회 또는 생성
    response = requests.get(
        f"{BASE_URL}/templates/?page_size=1",
        headers=get_headers()
    )
    
    if response.status_code == 200 and response.json()['data']['results']:
        template = response.json()['data']['results'][0]
        template_id = template['id']
        print(f"기존 템플릿 사용: {template['name']}")
    else:
        # 템플릿 새로 생성
        print("템플릿이 없어서 새로 생성합니다...")
        response = requests.post(
            f"{BASE_URL}/templates/",
            headers=get_headers(),
            json={
                "name": "Stage7 테스트 템플릿",
                "purpose": "intro",
                "is_active": True
            }
        )
        
        if response.status_code != 201:
            print("\n❌ 템플릿 생성 실패")
            pprint(response.json())
            return None, None
        
        template_id = response.json()['data']['id']
        print(f"템플릿 생성 완료: {template_id}")
    
    # 템플릿 버전 조회 또는 생성
    response = requests.get(
        f"{BASE_URL}/templates/{template_id}/versions/?page_size=1",
        headers=get_headers()
    )
    
    if response.status_code == 200 and response.json()['data']['results']:
        version = response.json()['data']['results'][0]
        version_id = version['id']
        print(f"기존 템플릿 버전 사용: {version_id}")
    else:
        # 템플릿 버전 새로 생성
        print("템플릿 버전이 없어서 새로 생성합니다...")
        response = requests.post(
            f"{BASE_URL}/templates/{template_id}/versions/",
            headers=get_headers(),
            json={
                "subject_tpl": "안녕하세요 {{ channel_name }}님! [테스트]",
                "body_tpl": "구독자 {{ subscriber_count }}명의 인기 유튜버이시네요! 협업 제안드립니다.",
                "format": "text"
            }
        )
        
        if response.status_code != 201:
            print("\n❌ 템플릿 버전 생성 실패")
            pprint(response.json())
            return None, None
        
        version_id = response.json()['data']['id']
        print(f"템플릿 버전 생성 완료: {version_id}")
    
    # 즉시 발송될 잡 생성 (scheduled_at = 현재 - 5분, daily_cap = 20)
    start_at = datetime.now() - timedelta(minutes=5)
    
    response = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/schedule/",
        headers=get_headers(),
        json={
            "template_version_id": version_id,
            "start_at": start_at.isoformat(),
            "daily_cap": 20  # 20개만 테스트
        }
    )
    
    print(f"\nStatus: {response.status_code}")
    data = response.json()
    pprint(data)
    
    if response.status_code == 200:
        print(f"\n✅ 발송 잡 생성 성공")
        print(f"예약된 잡: {data['data']['scheduled_count']}개")
        return campaign_id, data['data']['scheduled_count']
    else:
        print("\n❌ 발송 잡 생성 실패")
        return None, None

def test_2_run_send_due_jobs():
    """2. send_due_jobs 명령 실행"""
    print("\n" + "="*50)
    print("TEST 2: send_due_jobs 명령 실행")
    print("="*50)
    
    import subprocess
    
    # 현재 경로
    import os
    workspace_path = os.path.dirname(os.path.abspath(__file__))
    
    print(f"작업 디렉토리: {workspace_path}")
    print("\nmanage.py send_due_jobs 실행 중...")
    
    try:
        result = subprocess.run(
            ["conda", "run", "-n", "coldmail", "python", "manage.py", "send_due_jobs"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"\nReturn Code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
        
        if result.returncode == 0:
            print("\n✅ send_due_jobs 실행 성공")
            return True
        else:
            print("\n❌ send_due_jobs 실행 실패")
            return False
    except subprocess.TimeoutExpired:
        print("\n⚠️ 타임아웃 (30초)")
        return False
    except Exception as e:
        print(f"\n❌ 실행 중 에러: {e}")
        return False

def test_3_check_job_status(campaign_id, expected_count):
    """3. 잡 상태 확인"""
    print("\n" + "="*50)
    print("TEST 3: 잡 상태 확인")
    print("="*50)
    
    # Celery worker가 처리할 시간 대기
    print("\nCelery worker가 태스크를 처리할 때까지 10초 대기...")
    time.sleep(10)
    
    response = requests.get(
        f"{BASE_URL}/campaigns/{campaign_id}/jobs/?page_size=100",
        headers=get_headers()
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        jobs = response.json()['data']['results']
        
        # 상태별 집계
        status_count = {}
        for job in jobs:
            status = job['status']
            status_count[status] = status_count.get(status, 0) + 1
        
        print(f"\n잡 상태 집계:")
        for status, count in status_count.items():
            print(f"  {status}: {count}개")
        
        # sent 잡 샘플
        sent_jobs = [j for j in jobs if j['status'] == 'sent']
        if sent_jobs:
            print(f"\n✅ 발송 완료된 잡 샘플:")
            for job in sent_jobs[:3]:
                print(f"  - {job['lead_channel_name']}: {job['status']}")
        
        # failed 잡 샘플
        failed_jobs = [j for j in jobs if j['status'] == 'failed']
        if failed_jobs:
            print(f"\n⚠️ 실패한 잡 샘플:")
            for job in failed_jobs[:3]:
                print(f"  - {job['lead_channel_name']}: {job.get('last_error', 'N/A')}")
        
        # processing 잡 (잠금 상태)
        processing_jobs = [j for j in jobs if j['status'] == 'processing']
        if processing_jobs:
            print(f"\n⚠️ 처리 중인 잡: {len(processing_jobs)}개")
        
        return status_count
    else:
        print("\n❌ 잡 조회 실패")
        pprint(response.json())
        return None

def test_4_check_email_messages():
    """4. EmailMessage 생성 확인"""
    print("\n" + "="*50)
    print("TEST 4: EmailMessage 생성 확인")
    print("="*50)
    
    # Django shell로 EmailMessage 조회
    import subprocess
    
    cmd = [
        "conda", "run", "-n", "coldmail",
        "python", "manage.py", "shell", "-c",
        "from campaigns.models import EmailMessage; print(f'Total EmailMessages: {EmailMessage.objects.count()}')"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        print(result.stdout)
        
        if "Total EmailMessages:" in result.stdout:
            print("✅ EmailMessage 조회 성공")
            return True
        else:
            print("⚠️ EmailMessage 조회 결과 확인 필요")
            return False
    except Exception as e:
        print(f"❌ EmailMessage 조회 실패: {e}")
        return False

def test_5_retry_failed_job():
    """5. 실패한 잡 재시도"""
    print("\n" + "="*50)
    print("TEST 5: 실패한 잡 재시도")
    print("="*50)
    
    # 기존 캠페인 조회
    response = requests.get(
        f"{BASE_URL}/campaigns/?page_size=1",
        headers=get_headers()
    )
    
    if response.status_code != 200 or not response.json()['data']['results']:
        print("\n⚠️ 캠페인 없음")
        return
    
    campaign_id = response.json()['data']['results'][0]['id']
    
    # failed 잡 조회
    response = requests.get(
        f"{BASE_URL}/campaigns/{campaign_id}/jobs/?status=failed&page_size=1",
        headers=get_headers()
    )
    
    if response.status_code == 200:
        jobs = response.json()['data']['results']
        
        if not jobs:
            print("ℹ️ 실패한 잡이 없습니다. (정상)")
            return
        
        job_id = jobs[0]['id']
        print(f"실패한 잡 ID: {job_id}")
        print(f"에러: {jobs[0].get('last_error', 'N/A')}")
        
        # 재시도
        response = requests.post(
            f"{BASE_URL}/jobs/{job_id}/retry/",
            headers=get_headers()
        )
        
        print(f"\nRetry Status: {response.status_code}")
        data = response.json()
        pprint(data)
        
        if response.status_code == 200:
            print("\n✅ 재시도 성공")
            print(f"새 상태: {data['data']['status']}")
            print(f"시도 횟수: {data['data']['attempt_count']}")
        else:
            print("\n❌ 재시도 실패")
    else:
        print("\n❌ 잡 조회 실패")

def test_6_check_locking():
    """6. 중복 발송 방지 (locking) 확인"""
    print("\n" + "="*50)
    print("TEST 6: 중복 발송 방지 (locking) 확인")
    print("="*50)
    
    # Django shell로 locked_at 확인
    import subprocess
    
    cmd = [
        "conda", "run", "-n", "coldmail",
        "python", "manage.py", "shell", "-c",
        "from campaigns.models import SendJob; locked = SendJob.objects.filter(locked_at__isnull=False).count(); print(f'Locked jobs: {locked}')"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        print(result.stdout)
        
        if "Locked jobs:" in result.stdout:
            print("✅ Locking 상태 확인 성공")
            return True
        else:
            print("⚠️ Locking 상태 확인 필요")
            return False
    except Exception as e:
        print(f"❌ Locking 상태 확인 실패: {e}")
        return False


def main():
    """메인 테스트"""
    print("="*50)
    print("Stage 7 - Worker + 발송 결과 저장 테스트")
    print("="*50)
    print("\n⚠️ 주의: 이 테스트를 실행하기 전에:")
    print("1. Redis 서버가 실행 중이어야 합니다")
    print("   - docker-compose -f docker-compose.dev.yml up -d redis")
    print("   - 또는 로컬 Redis: redis-server")
    print("2. Celery Worker가 실행 중이어야 합니다")
    print("   - celery -A coldmail_project worker --loglevel=info")
    print()
    
    input("계속하려면 Enter를 누르세요...")
    
    # 로그인
    login()
    
    if not TOKEN:
        print("\n❌ 로그인 실패로 테스트 중단")
        return
    
    # 1. 즉시 발송될 잡 생성
    campaign_id, scheduled_count = test_1_create_scheduled_jobs()
    
    if not campaign_id or not scheduled_count:
        print("\n❌ 잡 생성 실패로 테스트 중단")
        return
    
    # 2. send_due_jobs 실행
    success = test_2_run_send_due_jobs()
    
    if not success:
        print("\n⚠️ send_due_jobs 실행 실패, 하지만 테스트 계속...")
    
    # 3. 잡 상태 확인
    status_count = test_3_check_job_status(campaign_id, scheduled_count)
    
    # 4. EmailMessage 확인
    test_4_check_email_messages()
    
    # 5. 재시도 테스트
    test_5_retry_failed_job()
    
    # 6. Locking 확인
    test_6_check_locking()
    
    print("\n" + "="*50)
    print("테스트 완료!")
    print("="*50)
    
    if status_count:
        print(f"\n최종 결과:")
        print(f"  생성된 잡: {scheduled_count}개")
        for status, count in status_count.items():
            print(f"  {status}: {count}개")
        
        if status_count.get('sent', 0) > 0:
            print("\n✅ 이메일 발송 성공!")
        elif status_count.get('processing', 0) > 0:
            print("\n⚠️ 일부 잡이 아직 처리 중입니다. Celery worker 로그를 확인하세요.")
        else:
            print("\n⚠️ 발송된 잡이 없습니다. 설정을 확인하세요.")

if __name__ == '__main__':
    main()
