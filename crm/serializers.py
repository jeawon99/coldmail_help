"""
CRM app serializers
"""
from rest_framework import serializers
from core.serializers import BaseSerializer
from .models import Lead, Tag, LeadTag, Suppression


class TagSerializer(BaseSerializer):
    """태그 시리얼라이저"""
    
    class Meta:
        model = Tag
        fields = ['id', 'name', 'created_at']
        read_only_fields = ['id', 'created_at']


class LeadSerializer(BaseSerializer):
    """리드(유튜버) 시리얼라이저"""
    
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        help_text="태그 ID 리스트"
    )
    
    class Meta:
        model = Lead
        fields = [
            'id', 'platform', 'channel_name', 'channel_url',
            'subscriber_count', 'primary_email', 'keywords_raw',
            'keywords_norm', 'status', 'notes',
            'tags', 'tag_ids',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        """태그 포함 리드 생성"""
        tag_ids = validated_data.pop('tag_ids', [])
        lead = super().create(validated_data)
        
        if tag_ids:
            tags = Tag.objects.filter(id__in=tag_ids)
            lead.tags.set(tags)
        
        return lead
    
    def update(self, instance, validated_data):
        """태그 포함 리드 업데이트"""
        tag_ids = validated_data.pop('tag_ids', None)
        lead = super().update(instance, validated_data)
        
        if tag_ids is not None:
            tags = Tag.objects.filter(id__in=tag_ids)
            lead.tags.set(tags)
        
        return lead


class LeadListSerializer(BaseSerializer):
    """리드 리스트용 경량 시리얼라이저 (태그는 이름만)"""
    
    tag_names = serializers.SerializerMethodField()
    
    class Meta:
        model = Lead
        fields = [
            'id', 'platform', 'channel_name', 'channel_url',
            'subscriber_count', 'primary_email', 'status',
            'tag_names', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_tag_names(self, obj):
        """태그 이름 리스트 반환"""
        return [tag.name for tag in obj.tags.all()]


class LeadTagSerializer(BaseSerializer):
    """리드-태그 관계 시리얼라이저"""
    
    lead = LeadListSerializer(read_only=True)
    tag = TagSerializer(read_only=True)
    
    class Meta:
        model = LeadTag
        fields = ['lead', 'tag', 'created_at']
        read_only_fields = ['lead', 'tag', 'created_at']


class SuppressionSerializer(BaseSerializer):
    """차단/수신거부 시리얼라이저"""
    
    class Meta:
        model = Suppression
        fields = ['id', 'type', 'value', 'reason', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def validate(self, attrs):
        """중복 검증"""
        if self.instance is None:  # 생성 시에만
            suppression_type = attrs.get('type')
            value = attrs.get('value')
            
            if Suppression.objects.filter(type=suppression_type, value=value).exists():
                raise serializers.ValidationError({
                    'value': f'이미 차단된 {suppression_type}입니다.'
                })
        
        return attrs


class LeadImportSerializer(serializers.Serializer):
    """리드 일괄 등록 시리얼라이저"""
    
    FORMAT_CHOICES = ['csv', 'json']
    
    format = serializers.ChoiceField(
        choices=FORMAT_CHOICES,
        default='csv',
        help_text="데이터 형식 (csv 또는 json)"
    )
    file = serializers.FileField(
        help_text="업로드할 파일 (CSV 또는 JSON)"
    )
    upsert = serializers.BooleanField(
        default=True,
        help_text="True: 중복 시 업데이트, False: 중복 시 스킵"
    )
    
    class Meta:
        fields = ['format', 'file', 'upsert']
