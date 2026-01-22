import requests

# 로그인
r = requests.post('http://127.0.0.1:8000/api/v1/auth/token/', json={'username':'admin','password':'admin123'})
token = r.json()['access']
headers = {'Authorization': f'Bearer {token}'}

# URL 테스트
urls = [
    '/api/v1/segments/',
    '/api/v1/campaigns/segments/',
    '/api/v1/campaigns/',
]

for url in urls:
    r = requests.get(f'http://127.0.0.1:8000{url}', headers=headers)
    print(f'{url}: {r.status_code}')
