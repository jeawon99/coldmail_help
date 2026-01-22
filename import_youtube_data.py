#!/usr/bin/env python
"""엑셀 파일에서 리드 데이터 가져와서 Import"""
import requests
import pandas as pd
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

print("=== 유튜버 테스트 데이터 Import 시작 ===\n")

# 0. JWT 토큰 발급
print("[0] JWT 토큰 발급")
resp_token = requests.post(f"{BASE_URL}/auth/token/", json={
    "username": "admin",
    "password": "admin123"
})
token_data = resp_token.json()
access_token = token_data["access"]
headers = {"Authorization": f"Bearer {access_token}"}
print(f"✓ Access Token 발급 완료\n")

# 1. 엑셀 파일 읽기
print("[1] 엑셀 파일 읽기: 유튜버 테스트 데이터.xlsx")
df = pd.read_excel("유튜버 테스트 데이터.xlsx")
print(f"✓ 총 {len(df)}개 행 읽음")
print(f"✓ 컬럼: {df.columns.tolist()}\n")

# 2. 데이터 미리보기
print("[2] 데이터 미리보기 (첫 3행):")
print(df.head(3).to_string())
print()

# 3. 리드 데이터로 변환 (CSV용)
print("[3] CSV 파일로 변환 중...")

# CSV용 데이터프레임 생성
csv_data = []
for idx, row in df.iterrows():
    csv_row = {
        "platform": "youtube",
        "channel_name": str(row.get("채널명", f"Channel_{idx}")),
        "channel_url": str(row.get("채널링크", row.get("채널 URL", f"https://youtube.com/channel_{idx}"))),
        "subscriber_count": int(row.get("구독자수", 0)) if pd.notna(row.get("구독자수")) else 0,
        "primary_email": "test@test.com",
        "status": "new"
    }
    
    # keywords_raw 처리
    keywords = row.get("관련키워드", row.get("키워드", ""))
    if pd.notna(keywords):
        csv_row["keywords_raw"] = str(keywords)
    else:
        csv_row["keywords_raw"] = ""
    
    # tags 처리 - 키워드에서 첫 3개만 태그로
    if pd.notna(keywords) and str(keywords).strip():
        keyword_list = [k.strip() for k in str(keywords).split(",")]
        csv_row["tags"] = ",".join(keyword_list[:3])  # 첫 3개만
    else:
        csv_row["tags"] = ""
    
    csv_data.append(csv_row)

# CSV 파일로 저장
import_df = pd.DataFrame(csv_data)
csv_filename = "import_leads.csv"
import_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
print(f"✓ CSV 파일 저장: {csv_filename}")
print(f"✓ {len(csv_data)}개 리드 데이터 준비 완료\n")

# 4. Import API 호출 (CSV 파일 업로드)
print("[4] Import API 호출 중 (CSV 파일 업로드)...")
with open(csv_filename, 'rb') as f:
    files = {'file': (csv_filename, f, 'text/csv')}
    resp_import = requests.post(
        f"{BASE_URL}/leads/import/",
        headers=headers,
        files=files
    )

print(f"Status Code: {resp_import.status_code}")
result = resp_import.json()
print(f"응답:\n{json.dumps(result, indent=2, ensure_ascii=False)}\n")

if result.get("success"):
    print("✅ Import 성공!")
    data = result.get("data", {})
    print(f"  - 생성: {data.get('created', 0)}개")
    print(f"  - 업데이트: {data.get('updated', 0)}개")
    print(f"  - 실패: {data.get('failed', 0)}개")
    
    if data.get('errors'):
        print(f"\n⚠️ 에러 목록:")
        for err in data['errors'][:5]:  # 처음 5개만
            print(f"  - {err}")
else:
    print("❌ Import 실패")
    print(f"에러: {result.get('error', {}).get('message')}")

print("\n=== Import 완료 ===")
