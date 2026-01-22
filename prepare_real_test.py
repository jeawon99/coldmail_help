"""
실제 Gmail 테스트 준비: daily_cap=5로 제한
"""
import os
import sys
import django
from datetime import datetime, timedelta, timezone

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coldmail_project.settings.dev')
django.setup()

from campaigns.models import SendJob, Campaign, CampaignTarget
from crm.models import Lead
from templates.models import TemplateVersion

print("="*60)
print("실제 Gmail 테스트 준비 (daily_cap=5)")
print("="*60)

# 1. 모든 SendJob 삭제 (깨끗하게 시작)
print("\n1. 기존 SendJob 삭제 중...")
old_job_count = SendJob.objects.count()
SendJob.objects.all().delete()
print(f"   ✅ {old_job_count}개 SendJob 삭제 완료")

# 2. 캠페인 확인
print("\n2. 캠페인 확인 중...")
campaign = Campaign.objects.filter(status='running').first()

if not campaign:
    campaign = Campaign.objects.first()
    if campaign:
        print(f"   캠페인 발견: {campaign.name} (ID: {campaign.id})")
        print(f"   현재 상태: {campaign.status}")
    else:
        print("   ⚠️ 캠페인이 없습니다. 먼저 캠페인을 생성하세요.")
        sys.exit(1)
else:
    print(f"   ✅ 실행 중인 캠페인: {campaign.name} (ID: {campaign.id})")

# 3. 타겟 확인
target_count = campaign.targets.filter(status='pending').count()
print(f"\n3. 타겟 확인: {target_count}개 pending 타겟")

if target_count == 0:
    print("   ⚠️ pending 타겟이 없습니다. freeze-targets를 먼저 실행하세요.")
    sys.exit(1)

# 4. 템플릿 버전 확인
print("\n4. 템플릿 버전 확인 중...")
# Template의 is_active=True인 것의 최신 버전 가져오기
from templates.models import Template

active_template = Template.objects.filter(is_active=True).first()
if not active_template:
    print("   ⚠️ 활성 템플릿이 없습니다. 먼저 템플릿을 생성하세요.")
    sys.exit(1)

template_version = active_template.versions.order_by('-version').first()
if not template_version:
    print("   ⚠️ 템플릿 버전이 없습니다. 먼저 템플릿 버전을 생성하세요.")
    sys.exit(1)

print(f"   ✅ 템플릿: {active_template.name}")
print(f"   ✅ 템플릿 버전: v{template_version.version} (ID: {template_version.id})")
print(f"      제목: {template_version.subject_tpl[:50]}...")

# 5. SendJob 생성 (daily_cap=5)
print("\n5. SendJob 생성 중 (daily_cap=5)...")

# API 방식 대신 직접 생성
from campaigns.views import CampaignViewSet
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request

# 간단히 직접 로직 구현
from crm.models import Suppression

# pending 타겟만 선택
targets = campaign.targets.select_related('lead').filter(status='pending')

# 이메일 없는 타겟 제외
targets_with_email = []
for target in targets:
    if target.lead.primary_email:
        targets_with_email.append(target)

# Suppression 체크
suppressed_emails = set(
    Suppression.objects.filter(type='email').values_list('value', flat=True)
)
suppressed_domains = set(
    Suppression.objects.filter(type='domain').values_list('value', flat=True)
)

# 유효한 타겟 필터링
valid_targets = []
for target in targets_with_email:
    # 이메일 차단 체크
    if target.lead.primary_email in suppressed_emails:
        continue
    
    # 도메인 차단 체크
    email_domain = target.lead.primary_email.split('@')[1] if '@' in target.lead.primary_email else ''
    if email_domain in suppressed_domains:
        continue
    
    valid_targets.append(target)

print(f"   유효한 타겟: {len(valid_targets)}개")

# SendJob 생성 (daily_cap=5)
daily_cap = 5
start_at = datetime.now(timezone.utc) - timedelta(minutes=5)  # 즉시 발송

jobs_to_create = []
scheduled_dates = set()

for idx, target in enumerate(valid_targets[:25]):  # 최대 25개 (5일치)
    # 날짜 계산 (daily_cap=5개씩)
    day_offset = idx // daily_cap
    scheduled_time = start_at + timedelta(days=day_offset)
    scheduled_dates.add(scheduled_time.date())
    
    jobs_to_create.append(
        SendJob(
            campaign=campaign,
            campaign_target=target,
            lead=target.lead,  # lead 필드 추가
            template_version=template_version,
            to_email=target.lead.primary_email,
            scheduled_at=scheduled_time,
            status='scheduled',
            attempt_count=0
        )
    )

# 벌크 생성
SendJob.objects.bulk_create(jobs_to_create)

print(f"   ✅ {len(jobs_to_create)}개 SendJob 생성 완료")
print(f"   발송 날짜: {sorted(scheduled_dates)}")
print(f"   Daily cap: {daily_cap}개")

# 6. 상태 요약
print("\n6. 최종 상태")
print("="*60)

scheduled_count = SendJob.objects.filter(status='scheduled').count()
due_count = SendJob.objects.filter(
    status='scheduled',
    scheduled_at__lte=datetime.now(timezone.utc)
).count()

print(f"총 SendJob: {scheduled_count}개")
print(f"즉시 발송 가능: {due_count}개")

# 첫 5개 잡 확인
print("\n즉시 발송될 잡 (최대 5개):")
for job in SendJob.objects.filter(status='scheduled').order_by('scheduled_at')[:5]:
    print(f"  - {job.to_email}")
    print(f"    예약: {job.scheduled_at}")

print("\n" + "="*60)
print("다음 단계:")
print("="*60)
print("1. Celery worker 실행 확인")
print("2. 명령 실행: python manage.py send_due_jobs --async")
print("3. 실제 Gmail 수신함 확인")
print("\n⚠️ 주의: 실제 이메일이 발송됩니다!")
print(f"   - 첫 발송: {due_count}개 (rok585858+test1~test{due_count}@gmail.com)")
