"""
Lead 이메일을 실제 Gmail 주소로 변경
rok585858+test1@gmail.com, rok585858+test2@gmail.com, ...
"""
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coldmail_project.settings.dev')
django.setup()

from crm.models import Lead

print("="*60)
print("Lead 이메일을 실제 Gmail 주소로 업데이트")
print("="*60)

# 모든 Lead 조회
leads = Lead.objects.all().order_by('id')
total_count = leads.count()

print(f"\n총 Lead: {total_count}개")
print("이메일 업데이트 중...")

# 순차적으로 이메일 할당
for idx, lead in enumerate(leads, start=1):
    new_email = f"rok585858+test{idx}@gmail.com"
    lead.primary_email = new_email
    lead.save(update_fields=['primary_email'])
    
    if idx % 1000 == 0:
        print(f"  {idx}개 처리 완료...")

print(f"\n✅ {total_count}개 Lead의 이메일 업데이트 완료")

# 샘플 확인
print("\n처음 10개 Lead 이메일:")
for lead in Lead.objects.all().order_by('id')[:10]:
    print(f"  - {lead.channel_name}: {lead.primary_email}")

print("\n마지막 5개 Lead 이메일:")
for lead in Lead.objects.all().order_by('-id')[:5]:
    print(f"  - {lead.channel_name}: {lead.primary_email}")

print("\n" + "="*60)
print("완료!")
print("="*60)
