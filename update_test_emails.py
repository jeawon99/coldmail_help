"""
Lead 이메일 주소를 test@example.com으로 일괄 변경
"""
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coldmail_project.settings.dev')
django.setup()

from crm.models import Lead

# 모든 Lead의 primary_email을 test@example.com으로 변경
leads = Lead.objects.all()
count = 0

for lead in leads:
    if lead.primary_email != 'test@example.com':
        lead.primary_email = 'test@example.com'
        lead.save(update_fields=['primary_email'])
        count += 1

print(f"✅ {count}개 Lead의 이메일을 test@example.com으로 변경했습니다.")
print(f"   총 Lead 수: {leads.count()}개")
print(f"   변경되지 않은 Lead: {leads.count() - count}개 (이미 test@example.com)")
