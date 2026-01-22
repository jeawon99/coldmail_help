"""
캠페인 모델: LeadSegment, Campaign, CampaignTarget, SendJob, EmailMessage, EmailEvent
"""
from django.db import models
from core.models import BaseModel
from crm.models import Lead
from templates.models import TemplateVersion


class LeadSegment(BaseModel):
    """동적 세그먼트 (필터 조건 저장)"""
    name = models.CharField(max_length=200, help_text="세그먼트 이름")
    filter_json = models.JSONField(help_text="필터 조건 DSL")
    
    class Meta:
        db_table = 'lead_segment'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class CampaignStatusChoices(models.TextChoices):
    """캠페인 상태"""
    DRAFT = 'draft', 'Draft'
    RUNNING = 'running', 'Running'
    PAUSED = 'paused', 'Paused'
    FINISHED = 'finished', 'Finished'


class Campaign(BaseModel):
    """캠페인"""
    name = models.CharField(max_length=200, help_text="캠페인 이름")
    segment = models.ForeignKey(
        LeadSegment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='campaigns',
        help_text="세그먼트"
    )
    status = models.CharField(
        max_length=20,
        choices=CampaignStatusChoices.choices,
        default=CampaignStatusChoices.DRAFT,
        db_index=True,
        help_text="캠페인 상태"
    )
    daily_cap = models.IntegerField(default=50, help_text="일일 발송 제한")
    timezone = models.CharField(
        max_length=50,
        default='Asia/Seoul',
        help_text="타임존"
    )
    
    # 스냅샷 정보
    frozen_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="대상 확정 시점"
    )
    frozen_target_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="확정된 대상 수"
    )
    
    class Meta:
        db_table = 'campaign'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.status})"


class CampaignTargetStatusChoices(models.TextChoices):
    """캠페인 대상 상태"""
    PENDING = 'pending', 'Pending'
    QUEUED = 'queued', 'Queued'
    SENT = 'sent', 'Sent'
    REPLIED = 'replied', 'Replied'
    SKIPPED = 'skipped', 'Skipped'
    FAILED = 'failed', 'Failed'


class CampaignTarget(BaseModel):
    """캠페인 대상 (스냅샷: 고정된 리드 목록)"""
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='targets',
        help_text="캠페인"
    )
    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name='campaign_targets',
        help_text="리드"
    )
    snapshot = models.JSONField(
        null=True,
        blank=True,
        help_text="당시 리드 정보 스냅샷"
    )
    status = models.CharField(
        max_length=20,
        choices=CampaignTargetStatusChoices.choices,
        default=CampaignTargetStatusChoices.PENDING,
        help_text="대상 상태"
    )
    
    class Meta:
        db_table = 'campaign_target'
        constraints = [
            models.UniqueConstraint(
                fields=['campaign', 'lead'],
                name='unique_campaign_lead'
            )
        ]
        indexes = [
            models.Index(fields=['campaign', 'status']),
            models.Index(fields=['lead']),
        ]
    
    def __str__(self):
        return f"{self.campaign.name} - {self.lead.channel_name}"


class SendJobStatusChoices(models.TextChoices):
    """발송 잡 상태"""
    SCHEDULED = 'scheduled', 'Scheduled'
    PROCESSING = 'processing', 'Processing'
    SENT = 'sent', 'Sent'
    CANCELLED = 'cancelled', 'Cancelled'
    FAILED = 'failed', 'Failed'


class SendJob(BaseModel):
    """예약 큐 (발송 잡)"""
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='send_jobs',
        help_text="캠페인"
    )
    campaign_target = models.ForeignKey(
        CampaignTarget,
        on_delete=models.CASCADE,
        related_name='send_jobs',
        help_text="캠페인 대상"
    )
    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name='send_jobs',
        help_text="리드 (조회 최적화용)"
    )
    to_email = models.EmailField(help_text="수신 이메일")
    template_version = models.ForeignKey(
        TemplateVersion,
        on_delete=models.PROTECT,
        related_name='send_jobs',
        help_text="템플릿 버전"
    )
    
    scheduled_at = models.DateTimeField(
        db_index=True,
        help_text="예약 시간"
    )
    status = models.CharField(
        max_length=20,
        choices=SendJobStatusChoices.choices,
        default=SendJobStatusChoices.SCHEDULED,
        db_index=True,
        help_text="잡 상태"
    )
    
    locked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="처리 잠금 시간"
    )
    attempt_count = models.IntegerField(default=0, help_text="시도 횟수")
    last_error = models.TextField(
        null=True,
        blank=True,
        help_text="마지막 에러 메시지"
    )
    
    class Meta:
        db_table = 'send_job'
        ordering = ['scheduled_at']
        indexes = [
            models.Index(fields=['status', 'scheduled_at']),
            models.Index(fields=['campaign', 'status']),
        ]
    
    def __str__(self):
        return f"Job {self.id} - {self.to_email} ({self.status})"


class EmailProviderChoices(models.TextChoices):
    """이메일 제공자"""
    LARK = 'lark', 'Lark Suite'


class SendStatusChoices(models.TextChoices):
    """발송 상태"""
    SENT = 'sent', 'Sent'
    FAILED = 'failed', 'Failed'


class FailureTypeChoices(models.TextChoices):
    """실패 타입"""
    INVALID_RECIPIENT = 'invalid_recipient', 'Invalid Recipient'
    RATE_LIMIT = 'rate_limit', 'Rate Limit'
    PROVIDER_ERROR = 'provider_error', 'Provider Error'
    OTHER = 'other', 'Other'


class EmailMessage(BaseModel):
    """실제 발송 결과"""
    send_job = models.OneToOneField(
        SendJob,
        on_delete=models.CASCADE,
        related_name='email_message',
        help_text="발송 잡"
    )
    provider = models.CharField(
        max_length=20,
        choices=EmailProviderChoices.choices,
        default=EmailProviderChoices.LARK,
        help_text="발송 제공자"
    )
    provider_message_id = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="제공자 메시지 ID"
    )
    
    from_email = models.EmailField(
        null=True,
        blank=True,
        help_text="발신 이메일"
    )
    to_email = models.EmailField(help_text="수신 이메일")
    
    subject_final = models.TextField(help_text="렌더된 제목")
    body_final = models.TextField(
        null=True,
        blank=True,
        help_text="렌더된 본문"
    )
    body_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="본문 해시"
    )
    
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="발송 시간"
    )
    send_status = models.CharField(
        max_length=20,
        choices=SendStatusChoices.choices,
        help_text="발송 상태"
    )
    failure_type = models.CharField(
        max_length=30,
        choices=FailureTypeChoices.choices,
        null=True,
        blank=True,
        help_text="실패 타입"
    )
    
    class Meta:
        db_table = 'email_message'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['sent_at']),
            models.Index(fields=['to_email', 'sent_at']),
        ]
    
    def __str__(self):
        return f"Email to {self.to_email} - {self.send_status}"


class EventTypeChoices(models.TextChoices):
    """이벤트 타입"""
    OPENED_PIXEL = 'opened_pixel', 'Opened (Pixel)'
    CLICKED = 'clicked', 'Clicked'
    REPLIED = 'replied', 'Replied'
    BOUNCED = 'bounced', 'Bounced'


class EmailEvent(BaseModel):
    """이메일 이벤트 (분석용)"""
    email_message = models.ForeignKey(
        EmailMessage,
        on_delete=models.CASCADE,
        related_name='events',
        help_text="이메일 메시지"
    )
    event_type = models.CharField(
        max_length=20,
        choices=EventTypeChoices.choices,
        help_text="이벤트 타입"
    )
    event_at = models.DateTimeField(
        db_index=True,
        help_text="이벤트 발생 시간"
    )
    meta = models.JSONField(
        null=True,
        blank=True,
        help_text="이벤트 메타데이터 (clicked_url, user_agent 등)"
    )
    
    class Meta:
        db_table = 'email_event'
        ordering = ['-event_at']
        indexes = [
            models.Index(fields=['event_type', 'event_at']),
            models.Index(fields=['email_message', 'event_type', 'event_at']),
        ]
    
    def __str__(self):
        return f"{self.event_type} at {self.event_at}"
