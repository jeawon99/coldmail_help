#!/usr/bin/env python
"""Stage 3: Templates API 테스트"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

def log_response(title, response):
    """응답 로깅"""
    print(f"\n{title}")
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except:
        print(f"Response: {response.text}")

print("\n=== Stage 3: Templates API 테스트 시작 ===")

# 1. Template 생성
print("\n[1] POST /templates/ - Template 생성")
resp1 = requests.post(f"{BASE_URL}/templates/", json={
    "name": "Welcome Email",
    "description": "Welcome email template for new leads"
})
log_response("Template 생성 응답", resp1)
template_id = resp1.json()["data"]["id"]

# 2. Template Version 생성 (v1)
print("\n[2] POST /templates/{id}/versions/ - Version 1 생성")
resp2 = requests.post(f"{BASE_URL}/templates/{template_id}/versions/", json={
    "subject_tpl": "Hello {{first_name}}!",
    "body_tpl": "Welcome, {{first_name}} {{last_name}}!\n\nWe're glad to contact you at {{email}}.",
    "format": "text",
    "cta_type": "none",
    "personalization_level": "medium"
})
log_response("Version 1 생성 응답", resp2)
version_id1 = resp2.json()["data"]["id"]

# 3. Template Version 생성 (v2) - 자동 버전 증가 테스트
print("\n[3] POST /templates/{id}/versions/ - Version 2 생성 (자동 증가)")
resp3 = requests.post(f"{BASE_URL}/templates/{template_id}/versions/", json={
    "subject_tpl": "{{first_name}}, Special Offer!",
    "body_tpl": "<h1>Hello {{first_name}}!</h1><p>{{company}} has a special offer for you.</p>",
    "format": "html",
    "cta_type": "button",
    "personalization_level": "high"
})
log_response("Version 2 생성 응답", resp3)
print(f"버전 번호 자동 증가 확인: {resp3.json()['data']['version_number']}")
version_id2 = resp3.json()["data"]["id"]

# 4. Template 목록 조회 (버전 포함)
print("\n[4] GET /templates/ - Template 목록 조회")
resp4 = requests.get(f"{BASE_URL}/templates/")
log_response("Template 목록 조회 응답", resp4)
result = resp4.json()["results"][0]
print(f"latest_version: {result.get('latest_version')}")
print(f"version_count: {result.get('version_count')}")

# 5. Render Preview (Lead ID 사용)
print("\n[5] POST /template-versions/{id}/render-preview/ - Lead ID로 렌더링")
resp5 = requests.post(f"{BASE_URL}/template-versions/{version_id2}/render-preview/", json={
    "lead_id": 1
})
log_response("Lead ID 렌더링 응답", resp5)

# 6. Render Preview (Sample Data 사용)
print("\n[6] POST /template-versions/{id}/render-preview/ - Sample Data로 렌더링")
resp6 = requests.post(f"{BASE_URL}/template-versions/{version_id2}/render-preview/", json={
    "sample_data": {
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "company": "Test Company Inc"
    }
})
log_response("Sample Data 렌더링 응답", resp6)

# 7. Template Syntax 에러 테스트
print("\n[7] Template Syntax 에러 테스트")
try:
    resp_error = requests.post(f"{BASE_URL}/templates/{template_id}/versions/", json={
        "subject_tpl": "Invalid template {{first_name",
        "body_tpl": "Test",
        "format": "text"
    })
    log_response("Syntax 에러 응답 (예상됨)", resp_error)
except Exception as e:
    print(f"에러 (예상됨): {e}")

# 8. Undefined Variable 에러 테스트
print("\n[8] Undefined Variable 에러 테스트")
resp8 = requests.post(f"{BASE_URL}/templates/{template_id}/versions/", json={
    "subject_tpl": "Hello {{nonexistent_variable}}",
    "body_tpl": "Test",
    "format": "text"
})
version_id_undef = resp8.json()["data"]["id"]

try:
    resp_undef = requests.post(f"{BASE_URL}/template-versions/{version_id_undef}/render-preview/", json={
        "sample_data": {
            "first_name": "Test"
        }
    })
    log_response("Undefined Variable 에러 응답 (예상됨)", resp_undef)
except Exception as e:
    print(f"에러 (예상됨): {e}")

print("\n=== Stage 3 테스트 완료 ===")
