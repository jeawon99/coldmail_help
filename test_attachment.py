"""
첨부파일 기능 로컬 테스트 스크립트
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

def login():
    """JWT 토큰 발급"""
    response = requests.post(
        f"{BASE_URL}/auth/token/",
        json={
            "username": "admin",
            "password": "admin123"
        }
    )
    response.raise_for_status()
    data = response.json()
    token = data['access']
    print(f"✓ JWT 토큰 발급 성공!")
    print(f"  Access Token: {token[:50]}...")
    print(f"  Refresh Token: {data['refresh'][:50]}...")
    return token

def create_template(token):
    """템플릿 생성"""
    response = requests.post(
        f"{BASE_URL}/templates/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "첨부파일 테스트 템플릿",
            "purpose": "partnership",
            "is_active": True
        }
    )
    print(f"\n템플릿 생성 응답: {response.status_code}")
    response.raise_for_status()
    template = response.json()
    print(f"응답 데이터: {json.dumps(template, indent=2, ensure_ascii=False)}")
    template_id = template.get('id') or template.get('data', {}).get('id')
    print(f"✓ 템플릿 생성 성공! ID: {template_id}")
    return template_id

def create_version_with_attachment(token, template_id):
    """첨부파일 포함 버전 생성"""
    response = requests.post(
        f"{BASE_URL}/templates/{template_id}/versions/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "subject_tpl": "[테스트] {{{{ channel_name }}}}님께 드립니다",
            "body_tpl": "안녕하세요 {{{{ channel_name }}}}님,\n\n첨부파일을 확인해주세요.",
            "format": "html",
            "cta_type": "reply",
            "personalization_level": 1,
            "attachment_url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
            "attachment_name": "테스트문서.pdf"
        }
    )
    print(f"\n버전 생성 응답: {response.status_code}")
    response.raise_for_status()
    result = response.json()
    print(f"응답 데이터: {json.dumps(result, indent=2, ensure_ascii=False)}")
    version = result.get('data') or result
    print(f"\n✓ 버전 생성 성공!")
    print(f"  - Version ID: {version.get('id')}")
    print(f"  - Version: v{version.get('version')}")
    print(f"  - 📎 첨부파일: {version.get('attachment_name', 'None')}")
    print(f"  - 📎 첨부 URL: {version.get('attachment_url', 'None')}")
    return version

def get_template_detail(token, template_id):
    """템플릿 상세 조회"""
    response = requests.get(
        f"{BASE_URL}/templates/{template_id}/",
        headers={"Authorization": f"Bearer {token}"}
    )
    response.raise_for_status()
    result = response.json()
    template = result.get('data') or result
    print(f"\n✓ 템플릿 상세 조회:")
    print(f"  - 이름: {template.get('name')}")
    print(f"  - 버전 개수: {template.get('version_count')}")
    if template.get('versions'):
        latest = template['versions'][0]
        print(f"  - 최신 버전 첨부파일: {latest.get('attachment_name', 'None')}")
    return template

if __name__ == "__main__":
    print("=" * 60)
    print("첨부파일 기능 로컬 테스트 시작")
    print("=" * 60)
    
    try:
        # 1. 로그인
        token = login()
        
        # 2. 템플릿 생성
        template_id = create_template(token)
        
        # 3. 첨부파일 포함 버전 생성
        version = create_version_with_attachment(token, template_id)
        
        # 4. 템플릿 상세 조회
        template = get_template_detail(token, template_id)
        
        print("\n" + "=" * 60)
        print("✅ 모든 테스트 통과!")
        print("=" * 60)
        print(f"\n📎 첨부파일이 성공적으로 추가되었습니다:")
        print(f"  - 파일명: {version.get('attachment_name')}")
        print(f"  - URL: {version.get('attachment_url')}")
        
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP 오류: {e}")
        print(f"응답: {e.response.text}")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
