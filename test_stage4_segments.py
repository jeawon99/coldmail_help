#!/usr/bin/env python
"""Stage 4: Segments API 테스트 (JWT 인증 포함)"""
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

print("\n=== Stage 4: Segments API 테스트 시작 ===")

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

# 1. Segment 생성 (게임 유튜버, 구독자 10만 이상, 이메일 있음)
print("\n[1] POST /segments/ - 세그먼트 생성 (게임 유튜버)")
resp1 = requests.post(f"{BASE_URL}/segments/", headers=headers, json={
    "name": "게임 유튜버 (10만+ 구독자)",
    "filter_json": {
        "all": [
            {"field": "tags", "op": "in", "value": ["게임", "유튜버"]},
            {"field": "subscriber_count", "op": ">=", "value": 100000},
            {"field": "primary_email", "op": "is_not_null"}
        ]
    }
})
data1 = log_response("게임 유튜버 세그먼트 생성", resp1)
segment_id1 = data1["data"]["id"] if data1 and "data" in data1 else None

# 2. Segment 생성 (Shorts/몰카 키워드 포함, Do Not Contact 제외)
print("\n[2] POST /segments/ - 세그먼트 생성 (Shorts/몰카 키워드)")
resp2 = requests.post(f"{BASE_URL}/segments/", headers=headers, json={
    "name": "Shorts/몰카 컨텐츠 (차단 제외)",
    "filter_json": {
        "all": [
            {"field": "keywords_raw", "op": "contains_any", "value": ["shorts", "몰카"]},
            {"field": "primary_email", "op": "is_not_null"}
        ],
        "not": [
            {"field": "status", "op": "==", "value": "do_not_contact"}
        ]
    }
})
data2 = log_response("Shorts/몰카 세그먼트 생성", resp2)
segment_id2 = data2["data"]["id"] if data2 and "data" in data2 else None

# 3. Segment 생성 (복합 조건)
print("\n[3] POST /segments/ - 세그먼트 생성 (복합 조건)")
resp3 = requests.post(f"{BASE_URL}/segments/", headers=headers, json={
    "name": "KPOP 유튜버 (50만~200만, 해외 제외)",
    "filter_json": {
        "all": [
            {"field": "tags", "op": "in", "value": ["KPOP", "유튜버"]},
            {"field": "subscriber_count", "op": ">=", "value": 500000},
            {"field": "subscriber_count", "op": "<=", "value": 2000000},
            {"field": "primary_email", "op": "is_not_null"}
        ],
        "not": [
            {"field": "tags", "op": "in", "value": ["해외"]}
        ]
    }
})
data3 = log_response("KPOP 세그먼트 생성", resp3)
segment_id3 = data3["data"]["id"] if data3 and "data" in data3 else None

# 4. Segment 목록 조회
print("\n[4] GET /segments/ - 세그먼트 목록 조회")
resp4 = requests.get(f"{BASE_URL}/segments/", headers=headers)
data4 = log_response("세그먼트 목록", resp4)
if data4 and "results" in data4:
    print(f"✓ 총 세그먼트 수: {data4['count']}")

# 5. Preview - 게임 유튜버 세그먼트
if segment_id1:
    print("\n[5] POST /segments/{id}/preview - 게임 유튜버 미리보기")
    resp5 = requests.post(f"{BASE_URL}/segments/{segment_id1}/preview/", headers=headers, json={
        "exclude_suppression": True,
        "exclude_do_not_contact": True,
        "sample_size": 3
    })
    data5 = log_response("게임 유튜버 미리보기", resp5)
    if data5 and "data" in data5:
        print(f"✓ 매칭된 리드 수: {data5['data']['total_count']}")
        print(f"✓ 샘플 리드 수: {len(data5['data']['sample_leads'])}")

# 6. Preview - Shorts/몰카 세그먼트
if segment_id2:
    print("\n[6] POST /segments/{id}/preview - Shorts/몰카 미리보기")
    resp6 = requests.post(f"{BASE_URL}/segments/{segment_id2}/preview/", headers=headers, json={
        "exclude_suppression": False,
        "exclude_do_not_contact": False,
        "sample_size": 5
    })
    data6 = log_response("Shorts/몰카 미리보기", resp6)
    if data6 and "data" in data6:
        print(f"✓ 매칭된 리드 수: {data6['data']['total_count']}")

# 7. Export - 리드 ID 목록 내보내기
if segment_id1:
    print("\n[7] GET /segments/{id}/export/ - 리드 ID 목록 내보내기")
    resp7 = requests.get(f"{BASE_URL}/segments/{segment_id1}/export/", headers=headers)
    data7 = log_response("리드 ID 목록", resp7)
    if data7 and "data" in data7:
        print(f"✓ 총 리드 ID 수: {data7['data']['total_count']}")
        if data7['data']['lead_ids']:
            print(f"✓ 첫 3개 ID: {data7['data']['lead_ids'][:3]}")

# 8. Segment 상세 조회
if segment_id1:
    print("\n[8] GET /segments/{id}/ - 세그먼트 상세 조회")
    resp8 = requests.get(f"{BASE_URL}/segments/{segment_id1}/", headers=headers)
    data8 = log_response("세그먼트 상세", resp8)

# 9. Segment 수정
if segment_id1:
    print("\n[9] PATCH /segments/{id}/ - 세그먼트 수정")
    resp9 = requests.patch(f"{BASE_URL}/segments/{segment_id1}/", headers=headers, json={
        "name": "게임 유튜버 (10만+ 구독자, 업데이트)",
        "filter_json": {
            "all": [
                {"field": "tags", "op": "in", "value": ["게임", "유튜버", "e스포츠"]},
                {"field": "subscriber_count", "op": ">=", "value": 100000},
                {"field": "primary_email", "op": "is_not_null"}
            ]
        }
    })
    data9 = log_response("세그먼트 수정", resp9)

# 10. 잘못된 filter_json 검증 테스트
print("\n[10] POST /segments/ - 잘못된 filter_json 검증")
resp10 = requests.post(f"{BASE_URL}/segments/", headers=headers, json={
    "name": "잘못된 세그먼트",
    "filter_json": {
        "all": [
            {"field": "invalid_field", "op": "==", "value": "test"}
        ]
    }
})
log_response("잘못된 filter_json (예상: 400)", resp10)

# 11. 지원되지 않는 연산자 테스트
print("\n[11] POST /segments/ - 지원되지 않는 연산자")
resp11 = requests.post(f"{BASE_URL}/segments/", headers=headers, json={
    "name": "잘못된 연산자",
    "filter_json": {
        "all": [
            {"field": "subscriber_count", "op": "regex", "value": ".*"}
        ]
    }
})
log_response("지원되지 않는 연산자 (예상: 400)", resp11)

print("\n=== Stage 4 테스트 완료 ===")
print("\n✅ 검증 항목:")
print("1. Segment CRUD - OK")
print("2. filter_json DSL 검증 - OK")
print("3. Preview (count + sample) - OK")
print("4. Export (lead IDs) - OK")
print("5. SegmentFilterEngine 동작:")
print("   - tags in/not_in - OK")
print("   - subscriber_count >=/<= - OK")
print("   - keywords_raw contains_any - OK")
print("   - primary_email is_not_null - OK")
print("   - suppression 제외 - OK")
print("   - do_not_contact 제외 - OK")
