"""
템플릿 모델: Template, TemplateVersion
"""
from django.db import models
from core.models import BaseModel


class TemplatePurposeChoices(models.TextChoices):
    """템플릿 목적"""
    INTRO = 'intro', 'Introduction'
    DEMO = 'demo', 'Demo Request'
    PARTNERSHIP = 'partnership', 'Partnership'
    FOLLOWUP = 'followup', 'Follow-up'
    OTHER = 'other', 'Other'


class Template(BaseModel):
    """메일 템플릿"""
    name = models.CharField(max_length=200, help_text="템플릿 이름")
    purpose = models.CharField(
        max_length=20,
        choices=TemplatePurposeChoices.choices,
        default=TemplatePurposeChoices.INTRO,
        help_text="템플릿 목적"
    )
    is_active = models.BooleanField(default=True, help_text="활성화 여부")
    
    class Meta:
        db_table = 'template'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.purpose})"


class TemplateFormatChoices(models.TextChoices):
    """템플릿 포맷"""
    HTML = 'html', 'HTML'
    TEXT = 'text', 'Plain Text'


class CTATypeChoices(models.TextChoices):
    """CTA 타입"""
    REPLY = 'reply', 'Reply'
    LINK = 'link', 'Link'
    NONE = 'none', 'None'


class TemplateVersion(BaseModel):
    """템플릿 버전"""
    FORMAT_CHOICES = TemplateFormatChoices.choices
    CTA_TYPE_CHOICES = CTATypeChoices.choices
    
    template = models.ForeignKey(
        Template,
        on_delete=models.CASCADE,
        related_name='versions',
        help_text="템플릿"
    )
    version = models.IntegerField(help_text="버전 번호")
    
    subject_tpl = models.TextField(help_text="제목 템플릿")
    body_tpl = models.TextField(help_text="본문 템플릿")
    format = models.CharField(
        max_length=10,
        choices=TemplateFormatChoices.choices,
        default=TemplateFormatChoices.TEXT,
        help_text="포맷"
    )
    
    # 분석용 메타데이터
    subject_length = models.IntegerField(
        null=True,
        blank=True,
        help_text="제목 길이"
    )
    body_length = models.IntegerField(
        null=True,
        blank=True,
        help_text="본문 길이"
    )
    cta_type = models.CharField(
        max_length=10,
        choices=CTATypeChoices.choices,
        default=CTATypeChoices.NONE,
        help_text="CTA 타입"
    )
    personalization_level = models.SmallIntegerField(
        default=0,
        help_text="개인화 수준 (0-2)"
    )
    
    # 첨부파일 (외부 URL)
    attachment_url = models.URLField(
        null=True,
        blank=True,
        max_length=500,
        help_text="첨부파일 URL (예: https://cdn.example.com/file.pdf)"
    )
    attachment_name = models.CharField(
        null=True,
        blank=True,
        max_length=255,
        help_text="첨부파일 이름 (예: 제품카탈로그.pdf)"
    )
    
    class Meta:
        db_table = 'template_version'
        ordering = ['-version']
        constraints = [
            models.UniqueConstraint(
                fields=['template', 'version'],
                name='unique_template_version'
            )
        ]
        indexes = [
            models.Index(fields=['template', 'version']),
        ]
    
    def save(self, *args, **kwargs):
        """저장 시 길이 자동 계산"""
        if self.subject_tpl:
            self.subject_length = len(self.subject_tpl)
        if self.body_tpl:
            self.body_length = len(self.body_tpl)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.template.name} v{self.version}"
