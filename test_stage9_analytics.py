"""
Stage 9: Analytics API 테스트
"""
import os
import sys
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coldmail_project.settings.dev')
django.setup()

from campaigns.models import Campaign
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()

print("="*60)
print("Analytics API 테스트")
print("="*60)

# 1. 캠페인 확인
campaign = Campaign.objects.first()
if not campaign:
    print("⚠️ 캠페인이 없습니다.")
    sys.exit(1)

print(f"\n테스트 캠페인: {campaign.name}")
print(f"캠페인 ID: {campaign.id}")

# 2. 인증 토큰 가져오기
user = User.objects.filter(is_superuser=True).first()
if not user:
    print("⚠️ 슈퍼유저가 없습니다.")
    sys.exit(1)

token, _ = Token.objects.get_or_create(user=user)
headers = {'Authorization': f'Token {token.key}'}

base_url = f"http://127.0.0.1:8000/api/v1/campaigns/{campaign.id}/analytics"

print(f"\n인증 토큰: {token.key[:20]}...")

# 3. Overview API 테스트
print("\n" + "="*60)
print("1. Overview API 테스트")
print("="*60)

overview_url = f"{base_url}/overview/"
print(f"URL: {overview_url}")

try:
    response = requests.get(overview_url, headers=headers)
    print(f"상태 코드: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        data = result.get('data', {})
        
        print(f"✅ Overview 조회 성공:")
        print(f"  📧 총 발송: {data.get('total_sent')}개")
        print(f"  👁️  총 오픈: {data.get('total_opened')}개 (고유: {data.get('unique_opens')}개)")
        print(f"  👆 총 클릭: {data.get('total_clicked')}개 (고유: {data.get('unique_clicks')}개)")
        print(f"  📊 오픈율: {data.get('open_rate')}%")
        print(f"  📊 클릭율: {data.get('click_rate')}%")
        print(f"  📊 클릭/오픈율: {data.get('click_to_open_rate')}%")
    else:
        print(f"❌ Overview 조회 실패: {response.text}")
        
except Exception as e:
    import traceback
    print(f"❌ Overview 요청 실패: {e}")
    traceback.print_exc()

# 4. Timeseries API 테스트
print("\n" + "="*60)
print("2. Timeseries API 테스트")
print("="*60)

timeseries_url = f"{base_url}/timeseries/?granularity=daily"
print(f"URL: {timeseries_url}")

try:
    response = requests.get(timeseries_url, headers=headers)
    print(f"상태 코드: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        data = result.get('data', {})
        
        granularity = data.get('granularity')
        data_points = data.get('data_points', [])
        
        print(f"✅ Timeseries 조회 성공:")
        print(f"  집계 단위: {granularity}")
        print(f"  데이터 포인트: {len(data_points)}개")
        
        if data_points:
            print(f"\n  최근 3개 데이터 포인트:")
            for point in data_points[-3:]:
                print(f"    - {point['date']}: sent={point['sent']}, opened={point['opened']}, clicked={point['clicked']}")
    else:
        print(f"❌ Timeseries 조회 실패: {response.text}")
        
except Exception as e:
    import traceback
    print(f"❌ Timeseries 요청 실패: {e}")
    traceback.print_exc()

# 5. Templates API 테스트
print("\n" + "="*60)
print("3. Templates API 테스트")
print("="*60)

templates_url = f"{base_url}/templates/"
print(f"URL: {templates_url}")

try:
    response = requests.get(templates_url, headers=headers)
    print(f"상태 코드: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        data = result.get('data', [])
        
        print(f"✅ Templates 조회 성공: {len(data)}개 템플릿")
        
        for template in data:
            print(f"\n  📄 {template['template_name']} (v{template['version']})")
            print(f"     발송: {template['sent']}개")
            print(f"     오픈율: {template['open_rate']}%")
            print(f"     클릭율: {template['click_rate']}%")
    else:
        print(f"❌ Templates 조회 실패: {response.text}")
        
except Exception as e:
    import traceback
    print(f"❌ Templates 요청 실패: {e}")
    traceback.print_exc()

# 6. Breakdown API 테스트
print("\n" + "="*60)
print("4. Breakdown API 테스트 (태그별)")
print("="*60)

breakdown_url = f"{base_url}/breakdown/?breakdown_type=tag"
print(f"URL: {breakdown_url}")

try:
    response = requests.get(breakdown_url, headers=headers)
    print(f"상태 코드: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        data = result.get('data', {})
        
        breakdown_type = data.get('breakdown_type')
        items = data.get('items', [])
        
        print(f"✅ Breakdown 조회 성공 ({breakdown_type}):")
        print(f"  분류 항목: {len(items)}개")
        
        for item in items[:5]:  # 처음 5개만 출력
            print(f"\n  🏷️  {item['label']}")
            print(f"     발송: {item['sent']}개")
            print(f"     오픈율: {item['open_rate']}%")
            print(f"     클릭율: {item['click_rate']}%")
    else:
        print(f"❌ Breakdown 조회 실패: {response.text}")
        
except Exception as e:
    import traceback
    print(f"❌ Breakdown 요청 실패: {e}")
    traceback.print_exc()

# 7. Response Time API 테스트
print("\n" + "="*60)
print("5. Response Time API 테스트")
print("="*60)

response_time_url = f"{base_url}/response-time/"
print(f"URL: {response_time_url}")

try:
    response = requests.get(response_time_url, headers=headers)
    print(f"상태 코드: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        data = result.get('data', {})
        
        print(f"✅ Response Time 조회 성공:")
        
        avg_open = data.get('avg_time_to_open')
        avg_click = data.get('avg_time_to_click')
        median_open = data.get('median_time_to_open')
        
        if avg_open:
            print(f"  평균 오픈 시간: {avg_open:.2f}초 ({avg_open/3600:.2f}시간)")
        if median_open:
            print(f"  중간값 오픈 시간: {median_open:.2f}초 ({median_open/3600:.2f}시간)")
        if avg_click:
            print(f"  평균 클릭 시간: {avg_click:.2f}초 ({avg_click/3600:.2f}시간)")
        
        open_dist = data.get('open_time_distribution', [])
        if open_dist:
            print(f"\n  오픈 시간 분포:")
            for bucket in open_dist:
                print(f"    {bucket['bucket']}: {bucket['count']}개 ({bucket['percentage']}%)")
    else:
        print(f"❌ Response Time 조회 실패: {response.text}")
        
except Exception as e:
    import traceback
    print(f"❌ Response Time 요청 실패: {e}")
    traceback.print_exc()

print("\n" + "="*60)
print("테스트 완료!")
print("="*60)
