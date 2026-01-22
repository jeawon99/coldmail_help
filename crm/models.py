"""
CRM 모델: Lead(유튜버), Tag, LeadTag, Suppression
"""
from django.db import models
from core.models import BaseModel


class PlatformChoices(models.TextChoices):
    """플랫폼 선택"""
    YOUTUBE = 'youtube', 'YouTube'


class LeadStatusChoices(models.TextChoices):
    """리드 상태"""
    NEW = 'new', 'New'
    QUALIFIED = 'qualified', 'Qualified'
    DO_NOT_CONTACT = 'do_not_contact', 'Do Not Contact'


class Lead(BaseModel):
    """
    리드(유튜버) 모델
    """
    STATUS_CHOICES = LeadStatusChoices.choices
    
    platform = models.CharField(
        max_length=20,
        choices=PlatformChoices.choices,
        default=PlatformChoices.YOUTUBE,
        help_text="플랫폼 (추후 확장 대비)"
    )
    channel_name = models.CharField(max_length=255, help_text="채널명")
    channel_url = models.URLField(max_length=500, help_text="채널 URL")
    
    subscriber_count = models.BigIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="구독자 수"
    )
    primary_email = models.EmailField(
        null=True,
        blank=True,
        help_text="빠른 조회용 메일"
    )
    
    keywords_raw = models.TextField(
        null=True,
        blank=True,
        help_text="콤마 구분 키워드 문자열"
    )
    keywords_norm = models.JSONField(
        null=True,
        blank=True,
        help_text="정규화된 키워드 배열"
    )
    
    status = models.CharField(
        max_length=20,
        choices=LeadStatusChoices.choices,
        default=LeadStatusChoices.NEW,
        db_index=True,
        help_text="리드 상태"
    )
    notes = models.TextField(null=True, blank=True, help_text="메모")
    
    # Many-to-Many relationship with Tag
    tags = models.ManyToManyField(
        'Tag',
        through='LeadTag',
        related_name='leads',
        help_text="태그"
    )
    
    class Meta:
        db_table = 'lead'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['platform', 'channel_url'],
                name='unique_platform_channel'
            )
        ]
        indexes = [
            models.Index(fields=['subscriber_count']),
            models.Index(fields=['status']),
            models.Index(fields=['primary_email']),
        ]
    
    def __str__(self):
        return f"{self.channel_name} ({self.platform})"


class Tag(BaseModel):
    """태그 모델"""
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="태그명 (예: 유튜버, 게임, KPOP)"
    )
    
    class Meta:
        db_table = 'tag'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class LeadTag(models.Model):
    """리드-태그 다대다 관계"""
    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name='lead_tags'
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name='lead_tags'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'lead_tag'
        constraints = [
            models.UniqueConstraint(
                fields=['lead', 'tag'],
                name='unique_lead_tag'
            )
        ]
        indexes = [
            models.Index(fields=['tag']),
            models.Index(fields=['lead']),
        ]
    
    def __str__(self):
        return f"{self.lead.channel_name} - {self.tag.name}"


class SuppressionTypeChoices(models.TextChoices):
    """차단 타입"""
    EMAIL = 'email', 'Email'
    DOMAIN = 'domain', 'Domain'
    LEAD = 'lead', 'Lead'


class SuppressionReasonChoices(models.TextChoices):
    """차단 사유"""
    UNSUBSCRIBE = 'unsubscribe', 'Unsubscribe'
    COMPLAINT = 'complaint', 'Complaint'
    BOUNCE = 'bounce', 'Bounce'
    MANUAL = 'manual', 'Manual'


class Suppression(BaseModel):
    """차단/수신거부 리스트"""
    TYPE_CHOICES = SuppressionTypeChoices.choices
    REASON_CHOICES = SuppressionReasonChoices.choices
    
    type = models.CharField(
        max_length=20,
        choices=SuppressionTypeChoices.choices,
        help_text="차단 타입"
    )
    value = models.CharField(
        max_length=500,
        help_text="차단 값 (email, domain, lead UUID)"
    )
    reason = models.CharField(
        max_length=20,
        choices=SuppressionReasonChoices.choices,
        help_text="차단 사유"
    )
    
    class Meta:
        db_table = 'suppression'
        constraints = [
            models.UniqueConstraint(
                fields=['type', 'value'],
                name='unique_suppression'
            )
        ]
        indexes = [
            models.Index(fields=['type', 'value']),
        ]
    
    def __str__(self):
        return f"{self.type}: {self.value}"
