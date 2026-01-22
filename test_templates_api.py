import requests
import json

BASE_URL = "http://127.0.0.1:8001/api/v1"

# 토큰 발급
login_data = {"username": "admin", "password": "admin123"}
token_response = requests.post(f"{BASE_URL}/auth/token/", json=login_data)
token = token_response.json()["access"]
headers = {"Authorization": f"Bearer {token}"}

print("=" * 60)
print("Templates API 테스트")
print("=" * 60)

# 1. Template 생성
print("\n=== 1. Template 생성 ===")
template_data = {
    "name": "Introduction Email",
    "purpose": "intro",
    "is_active": True
}
t1 = requests.post(f"{BASE_URL}/templates/", json=template_data, headers=headers)
template_id = t1.json()["data"]["id"]
print(f"Template ID: {template_id}")
print(f"Name: {t1.json()['data']['name']}")
print(f"Latest Version: {t1.json()['data']['latest_version']}")

# 2. Template 버전 생성
print("\n=== 2. Template 버전 생성 ===")
version_data = {
    "subject_tpl": "안녕하세요 {{channel_name}}님",
    "body_tpl": "안녕하세요 {{channel_name}}님,\n\n저희는 {{subscriber_count}}명의 구독자를 보유하신 귀하의 채널에 관심이 있습니다.\n\n협업 제안을 드리고 싶습니다.\n\n감사합니다.",
    "format": "text",
    "cta_type": "reply",
    "personalization_level": 1
}
v1 = requests.post(f"{BASE_URL}/templates/{template_id}/versions/", json=version_data, headers=headers)
version_id = v1.json()["data"]["id"]
print(f"Version ID: {version_id}")
print(f"Version Number: {v1.json()['data']['version']}")
print(f"Subject Length: {v1.json()['data']['subject_length']}")

# 3. 실제 Lead 조회
print("\n=== 3. Lead 조회 (렌더링용) ===")
leads_response = requests.get(f"{BASE_URL}/leads/", headers=headers)
if leads_response.json()["count"] > 0:
    first_lead = leads_response.json()["results"][0]
    lead_id = first_lead["id"]
    print(f"Lead ID: {lead_id}")
    print(f"Channel Name: {first_lead['channel_name']}")
else:
    print("리드가 없습니다.")
    lead_id = None

# 4. 템플릿 렌더링 (실제 리드 데이터)
if lead_id:
    print("\n=== 4. 템플릿 렌더링 (실제 리드) ===")
    render_data = {"lead_id": lead_id}
    r1 = requests.post(f"{BASE_URL}/template-versions/{version_id}/render-preview/", json=render_data, headers=headers)
    if r1.status_code == 200:
        result = r1.json()["data"]
        print(f"Subject: {result['subject_final']}")
        print(f"Body Preview:\n{result['body_final'][:200]}...")
        print(f"Variables Used: {', '.join(result['variables_used'])}")
    else:
        print(f"Error: {r1.json()}")

# 5. 템플릿 렌더링 (샘플 데이터)
print("\n=== 5. 템플릿 렌더링 (샘플 데이터) ===")
sample_data = {
    "sample_data": {
        "channel_name": "테스트채널",
        "subscriber_count": 50000
    }
}
r2 = requests.post(f"{BASE_URL}/template-versions/{version_id}/render-preview/", json=sample_data, headers=headers)
if r2.status_code == 200:
    result = r2.json()["data"]
    print(f"Subject: {result['subject_final']}")
    print(f"Body:\n{result['body_final']}")
else:
    print(f"Error: {r2.json()}")

# 6. 템플릿 버전 2 추가
print("\n=== 6. Template 버전 2 추가 ===")
version2_data = {
    "subject_tpl": "[협업 제안] {{channel_name}} 채널 운영자님께",
    "body_tpl": "안녕하세요,\n\n{{channel_name}} 채널을 구독하고 있습니다.\n구독자 {{subscriber_count}}명 달성을 축하드립니다!\n\n{% if tags %}관심 분야: {{ tags|join(', ') }}{% endif %}\n\n협업 논의하고 싶습니다.\n\n감사합니다.",
    "format": "text",
    "cta_type": "reply",
    "personalization_level": 2
}
v2 = requests.post(f"{BASE_URL}/templates/{template_id}/versions/", json=version2_data, headers=headers)
print(f"Version Number: {v2.json()['data']['version']}")
print(f"Message: {v2.json()['message']}")

# 7. Template 목록 조회
print("\n=== 7. Template 목록 조회 ===")
templates = requests.get(f"{BASE_URL}/templates/", headers=headers)
print(f"Total Templates: {templates.json()['count']}")
for t in templates.json()["results"]:
    print(f"  - {t['name']} (Purpose: {t['purpose']}, Versions: {t['version_count']})")

# 8. Template 상세 조회 (버전 포함)
print("\n=== 8. Template 상세 조회 ===")
template_detail = requests.get(f"{BASE_URL}/templates/{template_id}/", headers=headers)
td = template_detail.json()["data"]
print(f"Name: {td['name']}")
print(f"Latest Version: {td['latest_version']}")
print(f"Total Versions: {len(td['versions'])}")
for v in td['versions']:
    print(f"  - Version {v['version']}: {v['subject_length']} chars, Level {v['personalization_level']}")

# 9. 렌더링 오류 테스트 (정의되지 않은 변수)
print("\n=== 9. 렌더링 오류 테스트 ===")
error_version_data = {
    "subject_tpl": "Hello {{undefined_variable}}",
    "body_tpl": "Test",
    "format": "text",
    "cta_type": "none",
    "personalization_level": 0
}
v3 = requests.post(f"{BASE_URL}/templates/{template_id}/versions/", json=error_version_data, headers=headers)
error_version_id = v3.json()["data"]["id"]
error_render = requests.post(
    f"{BASE_URL}/template-versions/{error_version_id}/render-preview/",
    json={"sample_data": {"channel_name": "Test"}},
    headers=headers
)
if error_render.status_code == 400:
    print("예상된 오류 발생:")
    print(f"  Error: {error_render.json()['error']['message']}")
else:
    print(f"Unexpected result: {error_render.json()}")

print("\n" + "=" * 60)
print("테스트 완료!")
print("=" * 60)
