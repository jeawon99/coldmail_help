"""
Templates app serializers
"""
from rest_framework import serializers
from core.serializers import BaseSerializer
from .models import Template, TemplateVersion


class TemplateVersionSerializer(BaseSerializer):
    """템플릿 버전 시리얼라이저"""
    
    class Meta:
        model = TemplateVersion
        fields = [
            'id', 'template', 'version', 'subject_tpl', 'body_tpl',
            'format', 'subject_length', 'body_length', 'cta_type',
            'personalization_level', 'attachment_url', 'attachment_name',
            'created_at'
        ]
        read_only_fields = [
            'id', 'version', 'subject_length', 'body_length', 'created_at'
        ]
    
    def validate_template(self, value):
        """템플릿 활성화 여부 확인"""
        if not value.is_active:
            raise serializers.ValidationError("비활성화된 템플릿에는 버전을 추가할 수 없습니다.")
        return value


class TemplateVersionListSerializer(BaseSerializer):
    """템플릿 버전 리스트용 경량 시리얼라이저"""
    
    class Meta:
        model = TemplateVersion
        fields = [
            'id', 'version', 'format', 'subject_length', 'body_length',
            'cta_type', 'personalization_level', 'created_at'
        ]
        read_only_fields = fields


class TemplateSerializer(BaseSerializer):
    """템플릿 시리얼라이저"""
    
    versions = TemplateVersionListSerializer(many=True, read_only=True)
    latest_version = serializers.SerializerMethodField()
    version_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Template
        fields = [
            'id', 'name', 'purpose', 'is_active',
            'versions', 'latest_version', 'version_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_latest_version(self, obj):
        """최신 버전 번호"""
        latest = obj.versions.order_by('-version').first()
        return latest.version if latest else 0
    
    def get_version_count(self, obj):
        """버전 개수"""
        return obj.versions.count()


class TemplateListSerializer(BaseSerializer):
    """템플릿 리스트용 경량 시리얼라이저"""
    
    latest_version = serializers.SerializerMethodField()
    version_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Template
        fields = [
            'id', 'name', 'purpose', 'is_active',
            'latest_version', 'version_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields
    
    def get_latest_version(self, obj):
        """최신 버전 번호"""
        latest = obj.versions.order_by('-version').first()
        return latest.version if latest else 0
    
    def get_version_count(self, obj):
        """버전 개수"""
        return obj.versions.count()


class TemplateVersionCreateSerializer(serializers.Serializer):
    """템플릿 버전 생성 시리얼라이저"""
    
    subject_tpl = serializers.CharField(
        help_text="제목 템플릿 (예: 안녕하세요 {{channel_name}}님)"
    )
    body_tpl = serializers.CharField(
        help_text="본문 템플릿 (Jinja2 문법 지원)"
    )
    format = serializers.ChoiceField(
        choices=TemplateVersion.FORMAT_CHOICES,
        default='text',
        help_text="템플릿 형식"
    )
    cta_type = serializers.ChoiceField(
        choices=TemplateVersion.CTA_TYPE_CHOICES,
        default='reply',
        help_text="CTA 유형"
    )
    personalization_level = serializers.IntegerField(
        default=0,
        min_value=0,
        max_value=2,
        help_text="개인화 수준 (0=기본, 1=중간, 2=높음)"
    )


class RenderPreviewSerializer(serializers.Serializer):
    """템플릿 렌더링 미리보기 시리얼라이저"""
    
    lead_id = serializers.UUIDField(
        required=False,
        help_text="리드 ID (실제 데이터 사용)"
    )
    sample_data = serializers.JSONField(
        required=False,
        help_text="샘플 데이터 (예: {\"channel_name\": \"테스트채널\", \"subscriber_count\": 10000})"
    )
    
    def validate(self, attrs):
        """lead_id 또는 sample_data 중 하나는 필수"""
        if not attrs.get('lead_id') and not attrs.get('sample_data'):
            raise serializers.ValidationError(
                "lead_id 또는 sample_data 중 하나는 필수입니다."
            )
        return attrs
