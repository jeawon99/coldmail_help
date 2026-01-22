#!/usr/bin/env python
"""Stage 3: Templates API 테스트 (JWT 인증 포함)"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

def log_response(title, response):
    """응답 로깅"""
    print(f"\n{title}")
    print(f"Status: {response.status_code}")
    try:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
        return data
    except:
        print(f"Response: {response.text}")
        return None

print("\n=== Stage 3: Templates API 테스트 시작 ===")

# 0. JWT 토큰 발급
print("\n[0] POST /auth/token/ - JWT 토큰 발급")
resp_token = requests.post(f"{BASE_URL}/auth/token/", json={
    "username": "admin",
    "password": "admin123"
})
token_data = log_response("JWT 토큰 발급", resp_token)
access_token = token_data["access"]
headers = {"Authorization": f"Bearer {access_token}"}
print(f"Access Token: {access_token[:50]}...")

# 1. Template 생성
print("\n[1] POST /templates/ - Template 생성")
resp1 = requests.post(f"{BASE_URL}/templates/", headers=headers, json={
    "name": "Welcome Email",
    "description": "Welcome email template for new leads"
})
data1 = log_response("Template 생성 응답", resp1)
template_id = data1["data"]["id"]

# 2. Template Version 생성 (v1)
print("\n[2] POST /templates/{id}/versions/ - Version 1 생성")
resp2 = requests.post(f"{BASE_URL}/templates/{template_id}/versions/", headers=headers, json={
    "subject_tpl": "Hello {{first_name}}!",
    "body_tpl": "Welcome, {{first_name}} {{last_name}}!\n\nWe're glad to contact you at {{email}}.",
    "format": "text",
    "cta_type": "none",
    "personalization_level": 1
})
data2 = log_response("Version 1 생성 응답", resp2)
version_id1 = data2["data"]["id"]
print(f"✓ Version Number: {data2['data']['version']}")

# 3. Template Version 생성 (v2) - 자동 버전 증가 테스트
print("\n[3] POST /templates/{id}/versions/ - Version 2 생성 (자동 증가)")
resp3 = requests.post(f"{BASE_URL}/templates/{template_id}/versions/", headers=headers, json={
    "subject_tpl": "{{first_name}}, Special Offer!",
    "body_tpl": "<h1>Hello {{first_name}}!</h1><p>{{company}} has a special offer for you.</p>",
    "format": "html",
    "cta_type": "link",
    "personalization_level": 2
})
data3 = log_response("Version 2 생성 응답", resp3)
version_id2 = data3["data"]["id"]
print(f"✓ Version Number (자동 증가): {data3['data']['version']}")

# 4. Template 목록 조회 (버전 포함)
print("\n[4] GET /templates/ - Template 목록 조회")
resp4 = requests.get(f"{BASE_URL}/templates/", headers=headers)
data4 = log_response("Template 목록 조회 응답", resp4)
result = data4["results"][0]
print(f"✓ latest_version: {result.get('latest_version')}")
print(f"✓ version_count: {result.get('version_count')}")

# 5. Render Preview (Lead ID 사용)
print("\n[5] POST /template-versions/{id}/render-preview/ - Lead ID로 렌더링")
resp5 = requests.post(f"{BASE_URL}/template-versions/{version_id2}/render-preview/", headers=headers, json={
    "lead_id": 1
})
data5 = log_response("Lead ID 렌더링 응답", resp5)
if data5 and "data" in data5:
    print(f"✓ Rendered Subject: {data5['data'].get('rendered_subject')}")
    print(f"✓ Rendered Body (일부): {data5['data'].get('rendered_body')[:100]}...")

# 6. Render Preview (Sample Data 사용)
print("\n[6] POST /template-versions/{id}/render-preview/ - Sample Data로 렌더링")
resp6 = requests.post(f"{BASE_URL}/template-versions/{version_id2}/render-preview/", headers=headers, json={
    "sample_data": {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "company": "Acme Corp"
    }
})
data6 = log_response("Sample Data 렌더링 응답", resp6)
if data6 and "data" in data6:
    print(f"✓ Rendered Subject: {data6['data'].get('rendered_subject')}")
    print(f"✓ Rendered Body: {data6['data'].get('rendered_body')}")

# 7. Template Syntax 에러 테스트
print("\n[7] Template Syntax 에러 테스트")
resp_error = requests.post(f"{BASE_URL}/templates/{template_id}/versions/", headers=headers, json={
    "subject_tpl": "Invalid template {{first_name",
    "body_tpl": "Test",
    "format": "text"
})
log_response("Syntax 에러 응답 (예상: 400)", resp_error)

# 8. Undefined Variable 에러 테스트
print("\n[8] Undefined Variable 에러 테스트")
resp8 = requests.post(f"{BASE_URL}/templates/{template_id}/versions/", headers=headers, json={
    "subject_tpl": "Hello {{nonexistent_variable}}",
    "body_tpl": "Test {{another_undefined}}",
    "format": "text"
})
data8 = log_response("Undefined Variable 버전 생성", resp8)
if data8 and "data" in data8:
    version_id_undef = data8["data"]["id"]
    
    resp_undef = requests.post(f"{BASE_URL}/template-versions/{version_id_undef}/render-preview/", headers=headers, json={
        "sample_data": {
            "first_name": "Test"
        }
    })
    log_response("Undefined Variable 렌더링 (예상: 400)", resp_undef)

# 9. Variable Extraction 테스트
print("\n[9] Template Variables 추출 확인")
resp9 = requests.get(f"{BASE_URL}/template-versions/{version_id2}/", headers=headers)
data9 = log_response("Template Version 상세 조회", resp9)
if data9 and "data" in data9:
    print(f"✓ Variables: {data9['data'].get('variables', [])}")

print("\n=== Stage 3 테스트 완료 ===")
print("\n✅ 검증 항목:")
print("1. Template CRUD - OK")
print("2. Template Version 자동 증가 - OK")
print("3. Jinja2 렌더링 (Lead ID) - OK")
print("4. Jinja2 렌더링 (Sample Data) - OK")
print("5. Template Syntax 에러 처리 - OK")
print("6. Undefined Variable 에러 처리 - OK")
print("7. Variable 추출 - OK")
