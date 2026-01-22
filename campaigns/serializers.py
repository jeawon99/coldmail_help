"""Campaigns & Segments Serializers"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from campaigns.models import LeadSegment, Campaign, CampaignTarget, SendJob
from templates.models import TemplateVersion


class LeadSegmentSerializer(serializers.ModelSerializer):
    """
    리드 세그먼트 직렬화
    
    세그먼트는 동적 필터 조건을 저장하여 타겟 리드를 선정합니다.
    filter_json DSL을 사용하여 복잡한 조건을 조합할 수 있습니다.
    """
    
    filter_json = serializers.JSONField(
        help_text="""
        필터 조건 DSL (Domain Specific Language)
        
        구조:
        {
            "all": [조건1, 조건2, ...],  // AND 조건
            "not": [조건3, 조건4, ...]   // NOT 조건
        }
        
        각 조건 형식:
        {
            "field": "필드명",
            "op": "연산자",
            "value": 값
        }
        
        지원 필드:
        - tags: 태그 목록
        - subscriber_count: 구독자 수
        - keywords_raw: 키워드 문자열
        - primary_email: 이메일 주소
        - status: 리드 상태
        
        지원 연산자:
        - in, not_in: 배열 포함 여부
        - >=, <=, >, <, ==: 숫자/문자열 비교
        - contains_any: 문자열에 배열 값 중 하나라도 포함
        - is_not_null, is_null: null 체크
        
        예시:
        {
            "all": [
                {"field": "tags", "op": "in", "value": ["게임", "유튜버"]},
                {"field": "subscriber_count", "op": ">=", "value": 100000},
                {"field": "keywords_raw", "op": "contains_any", "value": ["shorts", "몰카"]},
                {"field": "primary_email", "op": "is_not_null"}
            ],
            "not": [
                {"field": "status", "op": "==", "value": "do_not_contact"}
            ]
        }
        """
    )
    
    class Meta:
        model = LeadSegment
        fields = [
            'id',
            'name',
            'filter_json',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        
    def to_representation(self, instance):
        """응답 형식 커스터마이징"""
        data = super().to_representation(instance)
        # filter_json을 읽기 쉽게 포맷팅
        return data
    
    def validate_filter_json(self, value):
        """filter_json 유효성 검사"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("filter_json은 딕셔너리여야 합니다.")
        
        # 기본 구조 검증
        if 'all' in value and not isinstance(value['all'], list):
            raise serializers.ValidationError("filter_json.all은 배열이어야 합니다.")
        
        if 'not' in value and not isinstance(value['not'], list):
            raise serializers.ValidationError("filter_json.not은 배열이어야 합니다.")
        
        # 각 조건 검증
        conditions = value.get('all', []) + value.get('not', [])
        for condition in conditions:
            if not isinstance(condition, dict):
                raise serializers.ValidationError("각 조건은 딕셔너리여야 합니다.")
            
            if 'field' not in condition or 'op' not in condition:
                raise serializers.ValidationError("각 조건은 'field'와 'op'를 포함해야 합니다.")
            
            # 지원되는 필드 검증
            allowed_fields = ['tags', 'subscriber_count', 'keywords_raw', 'primary_email', 'status']
            if condition['field'] not in allowed_fields:
                raise serializers.ValidationError(
                    f"지원되지 않는 필드: {condition['field']}. "
                    f"지원 필드: {', '.join(allowed_fields)}"
                )
            
            # 지원되는 연산자 검증
            allowed_ops = ['in', 'not_in', '>=', '<=', '>', '<', '==', 'contains_any', 'is_not_null', 'is_null']
            if condition['op'] not in allowed_ops:
                raise serializers.ValidationError(
                    f"지원되지 않는 연산자: {condition['op']}. "
                    f"지원 연산자: {', '.join(allowed_ops)}"
                )
        
        return value


class SegmentPreviewSerializer(serializers.Serializer):
    """세그먼트 미리보기 요청"""
    exclude_suppression = serializers.BooleanField(default=True)
    exclude_do_not_contact = serializers.BooleanField(default=True)
    sample_size = serializers.IntegerField(default=5, min_value=0, max_value=50)


class SegmentPreviewResponseSerializer(serializers.Serializer):
    """세그먼트 미리보기 응답"""
    total_count = serializers.IntegerField()
    sample_leads = serializers.ListField(child=serializers.DictField(), required=False)
    filter_summary = serializers.DictField()


# ========== Campaign Serializers ==========

class CampaignSerializer(serializers.ModelSerializer):
    """
    캠페인 직렬화
    
    캠페인은 세그먼트 조건으로 선정된 리드에게 이메일을 발송하는 작업 단위입니다.
    freeze-targets로 대상을 확정한 후 발송을 시작합니다.
    """
    
    # 읽기 전용 필드
    segment_name = serializers.CharField(source='segment.name', read_only=True)
    targets_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Campaign
        fields = [
            'id',
            'name',
            'segment',
            'segment_name',
            'status',
            'daily_cap',
            'timezone',
            'frozen_at',
            'frozen_target_count',
            'targets_count',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'frozen_at',
            'frozen_target_count',
            'created_at',
            'updated_at'
        ]
    
    def get_targets_count(self, obj):
        """실제 타겟 수 (DB 조회)"""
        if hasattr(obj, '_targets_count'):
            return obj._targets_count
        return obj.targets.count()
    
    def validate_status(self, value):
        """상태 전환 검증"""
        if self.instance:
            # 수정 시에만 상태 전환 검증
            current_status = self.instance.status
            
            # finished는 변경 불가
            if current_status == 'finished':
                raise serializers.ValidationError("종료된 캠페인은 수정할 수 없습니다.")
        
        return value


class CampaignListSerializer(serializers.ModelSerializer):
    """캠페인 리스트용 경량 시리얼라이저"""
    
    segment_name = serializers.CharField(source='segment.name', read_only=True)
    targets_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Campaign
        fields = [
            'id',
            'name',
            'segment',
            'segment_name',
            'status',
            'daily_cap',
            'frozen_at',
            'frozen_target_count',
            'targets_count',
            'created_at'
        ]


class CampaignTargetSerializer(serializers.ModelSerializer):
    """
    캠페인 타겟 직렬화
    
    freeze-targets로 확정된 캠페인 대상 리드입니다.
    스냅샷에 당시 리드 정보를 저장할 수 있습니다.
    """
    
    # 리드 정보 (읽기 전용)
    lead_channel_name = serializers.CharField(source='lead.channel_name', read_only=True)
    lead_primary_email = serializers.EmailField(source='lead.primary_email', read_only=True)
    lead_subscriber_count = serializers.IntegerField(source='lead.subscriber_count', read_only=True)
    lead_tags = serializers.SerializerMethodField()
    
    class Meta:
        model = CampaignTarget
        fields = [
            'id',
            'campaign',
            'lead',
            'lead_channel_name',
            'lead_primary_email',
            'lead_subscriber_count',
            'lead_tags',
            'snapshot',
            'status',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_lead_tags(self, obj):
        """리드 태그 목록"""
        return [tag.name for tag in obj.lead.tags.all()]


class FreezeTargetsRequestSerializer(serializers.Serializer):
    """타겟 확정 요청"""
    force = serializers.BooleanField(
        default=False,
        help_text="이미 확정되어 있어도 다시 확정할지 여부 (기존 타겟 삭제 후 재생성)"
    )
    save_snapshot = serializers.BooleanField(
        default=True,
        help_text="리드 정보 스냅샷 저장 여부"
    )


class FreezeTargetsResponseSerializer(serializers.Serializer):
    """타겟 확정 응답"""
    frozen_at = serializers.DateTimeField()
    frozen_target_count = serializers.IntegerField()
    message = serializers.CharField()


class TargetAddRequestSerializer(serializers.Serializer):
    """타겟 수동 추가 요청"""
    lead_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="추가할 리드 ID 목록"
    )
    save_snapshot = serializers.BooleanField(default=True)


class TargetRemoveRequestSerializer(serializers.Serializer):
    """타겟 제거 요청"""
    lead_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="제거할 리드 ID 목록"
    )


# ========== SendJob Serializers ==========

class SendJobSerializer(serializers.ModelSerializer):
    """
    발송 잡 직렬화
    
    예약된 이메일 발송 작업을 관리합니다.
    campaign_target 기반으로 생성되며, scheduled_at에 따라 발송됩니다.
    """
    
    # 읽기 전용 필드
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    lead_channel_name = serializers.CharField(source='lead.channel_name', read_only=True)
    template_name = serializers.CharField(source='template_version.template.name', read_only=True)
    template_version_number = serializers.IntegerField(source='template_version.version', read_only=True)
    
    class Meta:
        model = SendJob
        fields = [
            'id',
            'campaign',
            'campaign_name',
            'campaign_target',
            'lead',
            'lead_channel_name',
            'to_email',
            'template_version',
            'template_name',
            'template_version_number',
            'scheduled_at',
            'status',
            'locked_at',
            'attempt_count',
            'last_error',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'campaign',
            'campaign_target',
            'lead',
            'to_email',
            'locked_at',
            'attempt_count',
            'last_error',
            'created_at',
            'updated_at'
        ]


class SendJobListSerializer(serializers.ModelSerializer):
    """발송 잡 리스트용 경량 시리얼라이저"""
    
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    lead_channel_name = serializers.CharField(source='lead.channel_name', read_only=True)
    
    class Meta:
        model = SendJob
        fields = [
            'id',
            'campaign',
            'campaign_name',
            'lead_channel_name',
            'to_email',
            'scheduled_at',
            'status',
            'attempt_count',
            'created_at'
        ]


class ScheduleJobsRequestSerializer(serializers.Serializer):
    """발송 잡 예약 생성 요청"""
    template_version_id = serializers.UUIDField(
        help_text="사용할 템플릿 버전 ID"
    )
    start_at = serializers.DateTimeField(
        help_text="발송 시작 시간 (첫 배치 발송 시각)"
    )
    daily_cap = serializers.IntegerField(
        default=50,
        min_value=1,
        max_value=1000,
        help_text="하루 발송 제한 (기본: 50)"
    )
    
    def validate_template_version_id(self, value):
        """템플릿 버전 존재 확인"""
        if not TemplateVersion.objects.filter(id=value).exists():
            raise serializers.ValidationError("템플릿 버전을 찾을 수 없습니다.")
        return value


class ScheduleJobsResponseSerializer(serializers.Serializer):
    """발송 잡 예약 생성 응답"""
    total_targets = serializers.IntegerField(help_text="전체 타겟 수")
    scheduled_count = serializers.IntegerField(help_text="예약된 잡 수")
    skipped_count = serializers.IntegerField(help_text="스킵된 타겟 수")
    skip_reasons = serializers.DictField(
        child=serializers.IntegerField(),
        help_text="스킵 사유별 카운트"
    )
    scheduled_dates = serializers.ListField(
        child=serializers.DateField(),
        help_text="예약된 날짜 목록"
    )
    message = serializers.CharField()


class RescheduleJobRequestSerializer(serializers.Serializer):
    """잡 재예약 요청"""
    scheduled_at = serializers.DateTimeField(
        help_text="새로운 예약 시간"
    )


class CancelJobRequestSerializer(serializers.Serializer):
    """잡 취소 요청"""
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="취소 사유 (선택)"
    )
