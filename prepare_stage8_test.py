"""
Stage 8 테스트 준비: 이메일 발송 및 이벤트 생성
"""
import os
import sys
import django
from datetime import datetime, timedelta, timezone

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coldmail_project.settings.dev')
django.setup()

from campaigns.models import SendJob, EmailMessage
from crm.models import Lead

print("="*60)
print("Stage 8 테스트 준비")
print("="*60)

# 1. Lead 이메일 업데이트
print("\n1. Lead 이메일 업데이트 중...")
leads = Lead.objects.all()
count = 0
for lead in leads:
    if lead.primary_email != 'test@example.com':
        lead.primary_email = 'test@example.com'
        lead.save(update_fields=['primary_email'])
        count += 1

print(f"   ✅ {count}개 Lead의 이메일을 test@example.com으로 변경")

# 2. 기존 SendJob 중 5개를 scheduled로 리셋
print("\n2. SendJob 리셋 중...")
failed_jobs = SendJob.objects.filter(status='failed').order_by('scheduled_at')[:5]

if not failed_jobs:
    print("   ⚠️ failed 상태의 SendJob이 없습니다. sent 상태 확인...")
    sent_jobs = SendJob.objects.filter(status='sent')[:5]
    
    if sent_jobs:
        print(f"   ℹ️ {sent_jobs.count()}개의 sent 잡이 있습니다. (이미 EmailMessage 존재)")
        # EmailMessage 확인
        for job in sent_jobs:
            if hasattr(job, 'email_message'):
                msg = job.email_message
                print(f"   - EmailMessage ID: {msg.id}, To: {msg.to_email}")
    else:
        print("   ⚠️ sent 상태의 SendJob도 없습니다. 새로 생성 필요.")
else:
    # failed → scheduled로 변경
    now = datetime.now(timezone.utc)
    reset_count = 0
    
    for job in failed_jobs:
        job.status = 'scheduled'
        job.scheduled_at = now - timedelta(minutes=1)
        job.locked_at = None
        job.attempt_count = 0
        job.last_error = None
        job.to_email = 'test@example.com'  # 이메일 주소 업데이트
        job.save()
        reset_count += 1
        print(f"   - {job.id}: scheduled로 복구 (to: {job.to_email})")
    
    print(f"   ✅ {reset_count}개 SendJob을 scheduled 상태로 복구")

# 3. 상태 요약
print("\n3. 현재 상태 요약")
print("="*60)

total_jobs = SendJob.objects.count()
scheduled_count = SendJob.objects.filter(status='scheduled').count()
sent_count = SendJob.objects.filter(status='sent').count()
failed_count = SendJob.objects.filter(status='failed').count()

print(f"총 SendJob: {total_jobs}개")
print(f"  - scheduled: {scheduled_count}개")
print(f"  - sent: {sent_count}개")
print(f"  - failed: {failed_count}개")

# EmailMessage 확인
email_messages = EmailMessage.objects.count()
print(f"\n총 EmailMessage: {email_messages}개")

if email_messages > 0:
    recent_message = EmailMessage.objects.order_by('-sent_at').first()
    print(f"\n가장 최근 EmailMessage:")
    print(f"  - ID: {recent_message.id}")
    print(f"  - To: {recent_message.to_email}")
    print(f"  - Subject: {recent_message.subject_final}")
    print(f"  - Sent: {recent_message.sent_at}")
    
    # 이벤트 확인
    event_count = recent_message.events.count()
    print(f"  - Events: {event_count}개")

print("\n" + "="*60)
print("다음 단계:")
print("="*60)

if scheduled_count > 0:
    print("1. Celery worker가 실행 중인지 확인")
    print("2. 다음 명령 실행: python manage.py send_due_jobs --async")
    print("3. Celery worker 로그에서 발송 결과 확인")
elif email_messages > 0:
    print("1. 이미 EmailMessage가 존재합니다.")
    print("2. 바로 이벤트 트래킹 테스트 가능:")
    print(f"   - 오픈 픽셀: http://127.0.0.1:8000/api/v1/campaigns/t/open/{recent_message.id}.png")
    print(f"   - 클릭: http://127.0.0.1:8000/api/v1/campaigns/t/click/{recent_message.id}?u=https://example.com")
else:
    print("1. SendJob 생성 필요:")
    print("   python test_stage7_worker.py")
