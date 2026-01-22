"""
Failed 상태의 SendJob을 scheduled로 되돌려서 재발송
"""
import os
import sys
import django
from datetime import datetime, timedelta, timezone

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coldmail_project.settings.dev')
django.setup()

from campaigns.models import SendJob

# Failed 잡 5개 선택
failed_jobs = SendJob.objects.filter(status='failed').order_by('scheduled_at')[:5]

count = 0
now = datetime.now(timezone.utc)

for job in failed_jobs:
    job.status = 'scheduled'
    job.scheduled_at = now - timedelta(minutes=1)  # 1분 전으로 설정 (즉시 발송)
    job.locked_at = None
    job.attempt_count = 0
    job.last_error = None
    job.save()
    count += 1
    print(f"✅ {job.id}: scheduled로 복구 (scheduled_at: {job.scheduled_at})")

print(f"\n총 {count}개 잡을 scheduled 상태로 되돌림")
print("이제 'python manage.py send_due_jobs --async'를 실행하세요")
