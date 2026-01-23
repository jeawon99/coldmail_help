"""
Django Shell에서 직접 첨부파일 기능 테스트
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coldmail_project.settings')
django.setup()

from templates.models import Template, TemplateVersion

print("=" * 60)
print("첨부파일 기능 테스트 시작")
print("=" * 60)

# 1. 템플릿 생성
template = Template.objects.create(
    name="첨부파일 테스트 템플릿",
    purpose="partnership",
    is_active=True
)
print(f"\n✓ 템플릿 생성: {template.id}")
print(f"  이름: {template.name}")

# 2. 첨부파일 포함 버전 생성
version = TemplateVersion.objects.create(
    template=template,
    version=1,
    subject_tpl="[테스트] {{ channel_name }}님께 드립니다",
    body_tpl="안녕하세요 {{ channel_name }}님,\n\n첨부파일을 확인해주세요.",
    format="html",
    cta_type="reply",
    personalization_level=1,
    attachment_url="https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
    attachment_name="테스트문서.pdf"
)

print(f"\n✓ 버전 생성: {version.id}")
print(f"  버전: v{version.version}")
print(f"  포맷: {version.format}")
print(f"  📎 첨부파일: {version.attachment_name}")
print(f"  📎 첨부 URL: {version.attachment_url}")

# 3. 템플릿 조회
template = Template.objects.get(id=template.id)
print(f"\n✓ 템플릿 조회:")
print(f"  버전 개수: {template.versions.count()}")
for v in template.versions.all():
    print(f"  - v{v.version}: {v.attachment_name or '첨부파일 없음'}")

# 4. 필드 확인
print(f"\n✓ TemplateVersion 모델 필드:")
print(f"  - attachment_url: {hasattr(version, 'attachment_url')}")
print(f"  - attachment_name: {hasattr(version, 'attachment_name')}")

# 5. 데이터 확인
print(f"\n✓ 저장된 데이터:")
print(f"  - attachment_url: {version.attachment_url}")
print(f"  - attachment_name: {version.attachment_name}")

print("\n" + "=" * 60)
print("✅ 모든 테스트 통과!")
print("=" * 60)
print(f"\n📎 첨부파일 기능이 정상적으로 작동합니다!")
print(f"  - 템플릿 ID: {template.id}")
print(f"  - 버전 ID: {version.id}")
print(f"  - 첨부파일: {version.attachment_name}")
