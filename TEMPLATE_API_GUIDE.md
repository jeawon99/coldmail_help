# 템플릿 API 사용 가이드

이메일 템플릿 생성 및 관리를 위한 완벽 가이드

## 📋 목차
1. [템플릿 개요](#템플릿-개요)
2. [기본 사용법](#기본-사용법)
3. [Jinja2 템플릿 문법](#jinja2-템플릿-문법)
4. [변수 및 컨텍스트](#변수-및-컨텍스트)
5. [버전 관리](#버전-관리)
6. [렌더링 미리보기](#렌더링-미리보기)
7. [실전 예시](#실전-예시)
8. [Best Practices](#best-practices)

---

## 📌 템플릿 개요

### 템플릿이란?
템플릿은 개인화된 이메일을 대량으로 발송하기 위한 재사용 가능한 양식입니다. Jinja2 템플릿 엔진을 사용하여 각 수신자에게 맞춤화된 메시지를 자동으로 생성합니다.

### 구조
- **Template**: 기본 정보 (이름, 목적, 활성화 상태)
- **TemplateVersion**: 실제 내용 (제목, 본문, 포맷)

하나의 Template은 여러 TemplateVersion을 가질 수 있어 A/B 테스트가 가능합니다.

### 지원하는 목적 (Purpose)
- `intro`: 첫 소개 메일
- `demo`: 데모/시연 요청
- `partnership`: 협업 제안
- `followup`: 후속 메일
- `other`: 기타

---

## 🚀 기본 사용법

### 1. 템플릿 생성

```http
POST /api/v1/templates/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "협업 제안 템플릿",
  "purpose": "partnership",
  "is_active": true
}
```

**응답:**
```json
{
  "id": "template_uuid",
  "name": "협업 제안 템플릿",
  "purpose": "partnership",
  "is_active": true,
  "created_at": "2024-01-23T10:00:00Z",
  "versions": []
}
```

### 2. 템플릿 목록 조회

```http
GET /api/v1/templates/
Authorization: Bearer {access_token}
```

**필터링 옵션:**
- `?is_active=true`: 활성화된 템플릿만
- `?purpose=partnership`: 특정 목적의 템플릿
- `?search=협업`: 이름 검색
- `?ordering=-created_at`: 최신순 정렬

**예시:**
```http
GET /api/v1/templates/?is_active=true&purpose=partnership&ordering=-created_at
```

### 3. 템플릿 상세 조회

```http
GET /api/v1/templates/{template_id}/
Authorization: Bearer {access_token}
```

**응답:**
```json
{
  "id": "template_uuid",
  "name": "협업 제안 템플릿",
  "purpose": "partnership",
  "is_active": true,
  "created_at": "2024-01-23T10:00:00Z",
  "updated_at": "2024-01-23T10:00:00Z",
  "versions": [
    {
      "id": "version_uuid",
      "version": 1,
      "subject_tpl": "안녕하세요 {{ channel_name }}님",
      "format": "html",
      "created_at": "2024-01-23T10:05:00Z"
    }
  ]
}
```

### 4. 템플릿 수정

```http
PATCH /api/v1/templates/{template_id}/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "협업 제안 템플릿 v2",
  "is_active": false
}
```

### 5. 템플릿 삭제

```http
DELETE /api/v1/templates/{template_id}/
Authorization: Bearer {access_token}
```

---

## 📝 Jinja2 템플릿 문법

### 기본 변수 출력

```jinja2
안녕하세요 {{ channel_name }}님!
```

**결과:** "안녕하세요 게임유튜버님!"

### 조건문 (if)

```jinja2
{% if subscriber_count > 100000 %}
구독자 {{ subscriber_count }}명의 인기 크리에이터시네요!
{% elif subscriber_count > 10000 %}
성장하는 채널이시네요!
{% else %}
앞으로 더 성장하실 채널이라고 생각합니다.
{% endif %}
```

### 반복문 (for)

```jinja2
관심 분야: 
{% for tag in tags %}
- {{ tag }}
{% endfor %}
```

**결과:**
```
관심 분야:
- 게임
- 리뷰
- IT
```

### 필터 (Filters)

```jinja2
{# 대문자 변환 #}
{{ channel_name|upper }}

{# 소문자 변환 #}
{{ channel_name|lower }}

{# 첫 글자만 대문자 #}
{{ channel_name|capitalize }}

{# 숫자 포맷 #}
구독자: {{ subscriber_count|round(2) }}명

{# 기본값 설정 #}
이메일: {{ primary_email|default("이메일 없음") }}

{# 문자열 길이 #}
채널명 길이: {{ channel_name|length }}

{# 문자열 자르기 #}
{{ body_text|truncate(100) }}
```

### 주석

```jinja2
{# 이것은 주석입니다. 렌더링 결과에 나타나지 않습니다. #}

{# 
  여러 줄 주석도
  가능합니다.
#}
```

### 복합 예시

```jinja2
안녕하세요 {{ channel_name }}님,

{% if subscriber_count > 100000 %}
구독자 {{ subscriber_count|round(-3) }}명의 인기 유튜버시군요!
{% endif %}

귀하의 채널 주제인 
{% for tag in tags %}
{{ tag }}{% if not loop.last %}, {% endif %}
{% endfor %}
에 대해 협업 제안을 드리고자 합니다.

{% if platform == 'youtube' %}
YouTube에서 큰 활약을 하고 계시네요!
{% elif platform == 'instagram' %}
Instagram에서 멋진 콘텐츠를 만들고 계시네요!
{% endif %}

감사합니다.
```

---

## 🔧 변수 및 컨텍스트

### 기본 제공 변수

| 변수명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `channel_name` | String | 채널 이름 | "게임 챌린지" |
| `channel_url` | String | 채널 URL | "https://youtube.com/@game" |
| `subscriber_count` | Integer | 구독자 수 | 150000 |
| `platform` | String | 플랫폼 | "youtube", "instagram" |
| `primary_email` | String | 이메일 | "creator@example.com" |
| `tags` | Array | 태그 리스트 | ["게임", "리뷰"] |
| `keywords_raw` | String | 키워드 | "게임, 리뷰, IT" |
| `status` | String | 상태 | "active", "do_not_contact" |

### 커스텀 변수 사용

렌더링 미리보기 시 `sample_data`로 커스텀 변수를 전달할 수 있습니다:

```json
{
  "sample_data": {
    "company_name": "CLFY",
    "sender_name": "김재원",
    "position": "마케팅 매니저",
    "meeting_date": "2024년 2월 1일"
  }
}
```

**템플릿:**
```jinja2
안녕하세요,

{{ company_name }}의 {{ position }} {{ sender_name }}입니다.
{{ meeting_date }}에 미팅이 가능하신가요?
```

---

## 📦 버전 관리

### 템플릿 버전 생성

```http
POST /api/v1/templates/{template_id}/versions/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "subject_tpl": "[협업 제안] {{ channel_name }}님, 같이 프로젝트 하실래요?",
  "body_tpl": "안녕하세요 {{ channel_name }}님,\n\n{% if subscriber_count > 100000 %}인기 크리에이터시군요!{% endif %}\n\n협업 제안 드립니다.",
  "format": "html",
  "cta_type": "reply",
  "personalization_level": 2,
  "attachment_url": "https://cdn.clfy.cloud/files/product-catalog.pdf",
  "attachment_name": "제품 카탈로그.pdf"
}
```

**필드 설명:**
- `subject_tpl`: 제목 템플릿 (필수, 최대 500자)
- `body_tpl`: 본문 템플릿 (필수)
- `format`: "html" 또는 "text" (기본: "html")
- `cta_type`: "reply", "link", "none" (기본: "reply")
- `personalization_level`: 0~2 (기본: 1)
  - 0: 개인화 없음
  - 1: 이름/채널 정도만
  - 2: 세밀한 개인화
- `attachment_url`: 첨부파일 URL (선택, 외부 호스팅 파일)
- `attachment_name`: 첨부파일 이름 (선택, 예: "카탈로그.pdf")

**응답:**
```json
{
  "id": "version_uuid",
  "template": "template_uuid",
  "version": 1,
  "subject_tpl": "[협업 제안] {{ channel_name }}님, 같이 프로젝트 하실래요?",
  "body_tpl": "안녕하세요 {{ channel_name }}님...",
  "format": "html",
  "subject_length": 45,
  "body_length": 150,
  "cta_type": "reply",
  "personalization_level": 2,
  "created_at": "2024-01-23T11:00:00Z"
}
```

### 템플릿 버전 목록 조회

```http
GET /api/v1/template-versions/
Authorization: Bearer {access_token}
```

**필터링:**
- `?template_id={uuid}`: 특정 템플릿의 버전들만
- `?format=html`: HTML 포맷만
- `?ordering=-version`: 최신 버전순

**예시:**
```http
GET /api/v1/template-versions/?template_id=xxx&ordering=-version
```

### 특정 버전 조회

```http
GET /api/v1/template-versions/{version_id}/
Authorization: Bearer {access_token}
```

### 버전 수정

```http
PATCH /api/v1/template-versions/{version_id}/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "subject_tpl": "[업데이트] {{ channel_name }}님께 드리는 제안",
  "personalization_level": 2
}
```

### 버전 삭제

```http
DELETE /api/v1/template-versions/{version_id}/
Authorization: Bearer {access_token}
```

---

## 🎨 렌더링 미리보기

### 실제 리드 데이터로 미리보기

```http
POST /api/v1/template-versions/{version_id}/render-preview/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "lead_id": "lead_uuid"
}
```

**응답:**
```json
{
  "success": true,
  "data": {
    "subject_final": "[협업 제안] 게임 챌린지님, 같이 프로젝트 하실래요?",
    "body_final": "안녕하세요 게임 챌린지님,\n\n인기 크리에이터시군요!\n\n협업 제안 드립니다.",
    "variables_used": [
      "channel_name",
      "subscriber_count"
    ],
    "context": {
      "channel_name": "게임 챌린지",
      "channel_url": "https://youtube.com/@gamechallenge",
      "subscriber_count": 150000,
      "platform": "youtube",
      "primary_email": "game@example.com",
      "tags": ["게임", "리뷰"],
      "keywords_raw": "게임, 리뷰, 챌린지",
      "status": "active"
    }
  }
}
```

### 샘플 데이터로 미리보기

```http
POST /api/v1/template-versions/{version_id}/render-preview/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "sample_data": {
    "channel_name": "테스트 채널",
    "subscriber_count": 50000,
    "platform": "youtube",
    "tags": ["테스트", "샘플"],
    "company_name": "CLFY",
    "sender_name": "김철수"
  }
}
```

**응답:**
```json
{
  "success": true,
  "data": {
    "subject_final": "[협업 제안] 테스트 채널님, 같이 프로젝트 하실래요?",
    "body_final": "안녕하세요 테스트 채널님,\n\nCLFY의 김철수입니다...",
    "variables_used": [
      "channel_name",
      "subscriber_count",
      "company_name",
      "sender_name"
    ],
    "context": {
      "channel_name": "테스트 채널",
      "subscriber_count": 50000,
      "platform": "youtube",
      "tags": ["테스트", "샘플"],
      "company_name": "CLFY",
      "sender_name": "김철수",
      "primary_email": "example@email.com",
      "keywords_raw": ""
    }
  }
}
```

### 에러 처리

**템플릿 문법 오류:**
```json
{
  "success": false,
  "error": "template_syntax_error",
  "message": "템플릿 문법 오류: unexpected '}'",
  "errors": {
    "syntax_error": "unexpected '}'"
  }
}
```

**정의되지 않은 변수:**
```json
{
  "success": false,
  "error": "undefined_variable",
  "message": "정의되지 않은 변수: 'unknown_var' is undefined",
  "errors": {
    "undefined_variable": "'unknown_var' is undefined"
  }
}
```

---

## 💡 실전 예시

### 예시 1: 협업 제안 템플릿 (단계별)

#### Step 1: 템플릿 생성
```javascript
const createTemplate = async () => {
  const response = await fetch('https://coldmail.clfy.ai.kr/api/v1/templates/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      name: "유튜버 협업 제안",
      purpose: "partnership",
      is_active: true
    })
  });
  
  const template = await response.json();
  return template.id;
};
```

#### Step 2: 버전 추가 (첨부파일 포함)
```javascript
const addVersion = async (templateId) => {
  const response = await fetch(
    `https://coldmail.clfy.ai.kr/api/v1/templates/${templateId}/versions/`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        subject_tpl: "[협업 제안] {{ channel_name }}님께 드리는 제안",
        body_tpl: `안녕하세요 {{ channel_name }}님,

CLFY에서 마케팅을 담당하고 있는 김재원입니다.

{% if subscriber_count > 100000 %}
구독자 {{ subscriber_count|round(-3) }}명의 인기 유튜버시군요! 정말 대단하십니다.
{% elif subscriber_count > 10000 %}
꾸준히 성장하고 계시는 채널이네요!
{% endif %}

{% if tags %}
특히 {{ tags|join(', ') }} 분야에 대한 콘텐츠가 인상적이었습니다.
{% endif %}

저희와 함께 프로젝트를 진행해보시는 것은 어떠신가요?
첨부한 제품 카탈로그를 참고해주세요.

회신 부탁드립니다.
감사합니다.

김재원 드림
CLFY
contact@clfy.cloud`,
        format: "html",
        cta_type: "reply",
        personalization_level: 2,
        // 첨부파일 추가
        attachment_url: "https://cdn.clfy.cloud/files/product-catalog.pdf",
        attachment_name: "제품카탈로그.pdf"
      })
    }
  );
  
  return await response.json();
};
```

#### Step 3: 미리보기
```javascript
const previewTemplate = async (versionId) => {
  const response = await fetch(
    `https://coldmail.clfy.ai.kr/api/v1/template-versions/${versionId}/render-preview/`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        sample_data: {
          channel_name: "게임 리뷰왕",
          subscriber_count: 250000,
          tags: ["게임", "리뷰", "IT"]
        }
      })
    }
  );
  
  const preview = await response.json();
  console.log('제목:', preview.data.subject_final);
  console.log('본문:', preview.data.body_final);
  console.log('사용된 변수:', preview.data.variables_used);
};
```

#### Step 4: 전체 플로우
```javascript
const createCompleteTemplate = async () => {
  try {
    // 1. 템플릿 생성
    const templateId = await createTemplate();
    console.log('템플릿 생성:', templateId);
    
    // 2. 버전 추가
    const version = await addVersion(templateId);
    console.log('버전 생성:', version.id, `(v${version.version})`);
    
    // 3. 미리보기
    await previewTemplate(version.id);
    
    return { templateId, versionId: version.id };
  } catch (error) {
    console.error('템플릿 생성 실패:', error);
  }
};
```

### 예시 2: A/B 테스트용 다중 버전

```javascript
const createABTestVersions = async (templateId) => {
  // 버전 A: 짧고 직접적
  const versionA = await fetch(
    `https://coldmail.clfy.ai.kr/api/v1/templates/${templateId}/versions/`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        subject_tpl: "{{ channel_name }}님, 협업하실래요?",
        body_tpl: "안녕하세요!\n\n간단히 협업 제안 드립니다.\n\n회신 부탁드려요!",
        format: "text",
        cta_type: "reply",
        personalization_level: 1
      })
    }
  );
  
  // 버전 B: 길고 상세한
  const versionB = await fetch(
    `https://coldmail.clfy.ai.kr/api/v1/templates/${templateId}/versions/`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        subject_tpl: "[협업 제안] {{ channel_name }}님의 채널과 함께하고 싶습니다",
        body_tpl: `안녕하세요 {{ channel_name }}님,

CLFY에서 근무하고 있는 김재원입니다.

귀하의 채널을 오랫동안 지켜봐왔으며, 특히 {{ tags|join(', ') }} 관련 콘텐츠가 인상 깊었습니다.

{% if subscriber_count > 100000 %}
구독자 {{ subscriber_count }}명이라는 놀라운 성과를 이루신 점 축하드립니다.
{% endif %}

저희와 함께 다음과 같은 프로젝트를 진행해보시면 어떨까요?

1. 제품 리뷰
2. 스폰서십
3. 장기 파트너십

관심 있으시다면 회신 부탁드립니다.

감사합니다.`,
        format: "html",
        cta_type: "reply",
        personalization_level: 2
      })
    }
  );
  
  const [a, b] = await Promise.all([versionA.json(), versionB.json()]);
  console.log('A 버전:', a.version);
  console.log('B 버전:', b.version);
  
  return { versionA: a, versionB: b };
};
```

### 예시 3: React 컴포넌트

```javascript
import React, { useState, useEffect } from 'react';

const TemplateEditor = () => {
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [preview, setPreview] = useState(null);
  
  // 템플릿 목록 로드
  useEffect(() => {
    const fetchTemplates = async () => {
      const response = await fetch(
        'https://coldmail.clfy.ai.kr/api/v1/templates/?is_active=true',
        {
          headers: {
            'Authorization': `Bearer ${accessToken}`
          }
        }
      );
      const data = await response.json();
      setTemplates(data.results);
    };
    
    fetchTemplates();
  }, []);
  
  // 미리보기 생성
  const handlePreview = async (versionId) => {
    const response = await fetch(
      `https://coldmail.clfy.ai.kr/api/v1/template-versions/${versionId}/render-preview/`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          sample_data: {
            channel_name: "샘플 채널",
            subscriber_count: 100000,
            tags: ["게임", "리뷰"]
          }
        })
      }
    );
    
    const data = await response.json();
    setPreview(data.data);
  };
  
  return (
    <div className="template-editor">
      <h2>템플릿 관리</h2>
      
      {/* 템플릿 목록 */}
      <div className="template-list">
        {templates.map(template => (
          <div key={template.id} className="template-item">
            <h3>{template.name}</h3>
            <span className="badge">{template.purpose}</span>
            <button onClick={() => setSelectedTemplate(template)}>
              선택
            </button>
          </div>
        ))}
      </div>
      
      {/* 버전 목록 */}
      {selectedTemplate && (
        <div className="version-list">
          <h3>{selectedTemplate.name} - 버전</h3>
          {selectedTemplate.versions.map(version => (
            <div key={version.id} className="version-item">
              <span>v{version.version}</span>
              <button onClick={() => handlePreview(version.id)}>
                미리보기
              </button>
            </div>
          ))}
        </div>
      )}
      
      {/* 미리보기 */}
      {preview && (
        <div className="preview">
          <h3>미리보기</h3>
          <div className="preview-subject">
            <strong>제목:</strong> {preview.subject_final}
          </div>
          <div className="preview-body">
            <strong>본문:</strong>
            <pre>{preview.body_final}</pre>
          </div>
          <div className="preview-variables">
            <strong>사용된 변수:</strong>
            {preview.variables_used.join(', ')}
          </div>
        </div>
      )}
    </div>
  );
};

export default TemplateEditor;
```

---

## ✅ Best Practices

### 1. 템플릿 작성 팁

#### ✅ 좋은 예시
```jinja2
안녕하세요 {{ channel_name }}님,

{% if subscriber_count > 100000 %}
구독자 {{ subscriber_count|round(-3) }}명의 인기 크리에이터시군요!
{% endif %}

{{ tags|join(', ') }} 분야에 관심이 많으시군요.
```

#### ❌ 나쁜 예시
```jinja2
{# 너무 복잡한 로직 #}
{% if subscriber_count > 100000 and subscriber_count < 200000 and 'game' in keywords_raw and status == 'active' %}
...
{% endif %}

{# 정의되지 않은 변수 사용 #}
{{ undefined_variable }}

{# 문법 오류 #}
{% if subscriber_count > 100000 %
```

### 2. 개인화 수준별 가이드

#### Level 0: 개인화 없음
```jinja2
안녕하세요,

협업 제안 드립니다.
회신 부탁드립니다.
```

#### Level 1: 기본 개인화 (이름)
```jinja2
안녕하세요 {{ channel_name }}님,

협업 제안 드립니다.
회신 부탁드립니다.
```

#### Level 2: 세밀한 개인화
```jinja2
안녕하세요 {{ channel_name }}님,

{% if subscriber_count > 100000 %}
구독자 {{ subscriber_count|round(-3) }}명의 인기 크리에이터시군요!
{% endif %}

특히 {{ tags[0] }} 분야 콘텐츠가 인상적이었습니다.
{{ channel_url }}에서 귀하의 작업을 봤습니다.

협업 제안 드립니다.
```

### 3. 에러 방지

#### 안전한 변수 접근
```jinja2
{# 변수가 없을 경우 기본값 사용 #}
{{ primary_email|default("이메일 없음") }}

{# 리스트가 비어있을 경우 체크 #}
{% if tags %}
태그: {{ tags|join(', ') }}
{% endif %}

{# 숫자 변수 안전하게 사용 #}
{% if subscriber_count %}
구독자: {{ subscriber_count }}명
{% endif %}
```

### 4. 성능 최적화

- ✅ 짧고 간결한 템플릿 작성
- ✅ 복잡한 로직은 백엔드에서 처리
- ✅ 불필요한 반복문 피하기
- ❌ 너무 많은 조건문 중첩 지양

### 5. A/B 테스트 전략

```javascript
// 다양한 버전 생성
const versions = [
  {
    name: "짧고 직접적",
    subject: "{{ channel_name }}님, 협업하실래요?",
    body: "간단히 제안 드립니다..."
  },
  {
    name: "길고 상세한",
    subject: "[협업 제안] {{ channel_name }}님의 채널과 함께하고 싶습니다",
    body: "자세한 제안 내용..."
  },
  {
    name: "친근한 톤",
    subject: "{{ channel_name }}님! 같이 재미있는 거 해봐요 😊",
    body: "가볍게 제안..."
  }
];

// 각 버전 성과 측정 후 최적 버전 선택
```

### 6. 디버깅 팁

```javascript
// 1. 먼저 샘플 데이터로 테스트
const testWithSample = async (versionId) => {
  const preview = await renderPreview(versionId, {
    sample_data: {
      channel_name: "테스트",
      subscriber_count: 50000
    }
  });
  
  console.log('변수 사용:', preview.data.variables_used);
  console.log('렌더링 결과:', preview.data.subject_final);
};

// 2. 실제 리드로 테스트 전 문법 검증
// 3. 에러 메시지 확인
// 4. variables_used로 누락된 변수 확인
```

---

## � 첨부파일 사용 가이드

### 첨부파일 기능

템플릿 버전에 PDF, 이미지, Excel 등의 파일을 첨부할 수 있습니다. 이메일 발송 시 자동으로 첨부됩니다.

### 첨부파일 추가

```http
POST /api/v1/templates/{template_id}/versions/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "subject_tpl": "제품 카탈로그를 보내드립니다",
  "body_tpl": "안녕하세요,\n\n첨부된 카탈로그를 확인해주세요.",
  "format": "html",
  "attachment_url": "https://cdn.example.com/catalog.pdf",
  "attachment_name": "2024_제품카탈로그.pdf"
}
```

### 지원하는 파일 형식

- **문서**: PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX
- **이미지**: PNG, JPG, JPEG, GIF
- **압축**: ZIP, RAR
- **기타**: TXT, CSV

### 주의사항

1. **외부 호스팅 필수**: 파일은 외부 URL로 호스팅되어야 함
2. **권장 CDN**: AWS S3, Cloudinary, Google Cloud Storage
3. **파일 크기**: 25MB 이하 권장 (이메일 서버 제한)
4. **접근 권한**: URL은 public 또는 signed URL 사용
5. **파일명**: 한글 파일명 가능 (자동 인코딩)

### 실전 예시

#### PDF 카탈로그 첨부
```javascript
const createTemplateWithPDF = async (templateId) => {
  const response = await fetch(
    `https://coldmail.clfy.ai.kr/api/v1/templates/${templateId}/versions/`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        subject_tpl: "[CLFY] 제품 소개서를 보내드립니다",
        body_tpl: `안녕하세요 {{ channel_name }}님,

저희 CLFY의 제품 소개서를 첨부파일로 보내드립니다.

자세한 내용은 첨부된 PDF를 참고해주세요.

감사합니다.`,
        format: "html",
        attachment_url: "https://cdn.clfy.cloud/files/CLFY_Product_Guide.pdf",
        attachment_name: "CLFY_제품소개서.pdf"
      })
    }
  );
  
  return await response.json();
};
```

### Best Practices

#### ✅ 권장사항
- PDF는 5MB 이하로 최적화
- 파일명은 명확하게 (예: "제품소개서_2024.pdf")
- CDN 사용으로 다운로드 속도 보장
- 첨부 전 미리보기로 확인

#### ❌ 피해야 할 것
- 너무 큰 파일 (25MB 초과)
- 인증 필요한 private URL
- 만료되는 임시 링크

---

## �📞 문의

- **API 문서**: https://coldmail.clfy.ai.kr/api/docs/
- **Swagger UI**: https://coldmail.clfy.ai.kr/api/docs/#/templates
- **전체 가이드**: [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)

---

**Version**: 1.0.0  
**Last Updated**: 2024-01-23
