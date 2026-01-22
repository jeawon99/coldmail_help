"""
CRM app filters
"""
from django_filters import rest_framework as filters
from .models import Lead, Suppression


class LeadFilter(filters.FilterSet):
    """리드 필터"""
    
    # 태그 필터 (태그 이름 또는 ID로 필터링)
    tag = filters.CharFilter(method='filter_tag', help_text="태그 이름")
    tag_id = filters.UUIDFilter(field_name='tags__id', help_text="태그 ID")
    
    # 이메일 유무
    has_email = filters.BooleanFilter(method='filter_has_email', help_text="이메일 보유 여부")
    
    # 구독자 수 범위
    subscriber_count_min = filters.NumberFilter(
        field_name='subscriber_count',
        lookup_expr='gte',
        help_text="최소 구독자 수"
    )
    subscriber_count_max = filters.NumberFilter(
        field_name='subscriber_count',
        lookup_expr='lte',
        help_text="최대 구독자 수"
    )
    
    # 키워드 검색
    keyword = filters.CharFilter(method='filter_keyword', help_text="키워드 검색")
    
    # 상태
    status = filters.ChoiceFilter(choices=Lead.STATUS_CHOICES, help_text="리드 상태")
    
    # 채널명 검색
    channel_name = filters.CharFilter(lookup_expr='icontains', help_text="채널명 검색")
    
    class Meta:
        model = Lead
        fields = [
            'platform', 'status', 'tag', 'tag_id', 'has_email',
            'subscriber_count_min', 'subscriber_count_max',
            'keyword', 'channel_name'
        ]
    
    def filter_tag(self, queryset, name, value):
        """태그 이름으로 필터링"""
        return queryset.filter(tags__name__iexact=value).distinct()
    
    def filter_has_email(self, queryset, name, value):
        """이메일 유무로 필터링"""
        if value:
            return queryset.exclude(primary_email__isnull=True).exclude(primary_email='')
        else:
            return queryset.filter(primary_email__isnull=True) | queryset.filter(primary_email='')
    
    def filter_keyword(self, queryset, name, value):
        """키워드로 검색 (keywords_raw 필드에서)"""
        return queryset.filter(keywords_raw__icontains=value)


class SuppressionFilter(filters.FilterSet):
    """차단 필터"""
    
    type = filters.ChoiceFilter(choices=Suppression.TYPE_CHOICES, help_text="차단 유형")
    reason = filters.ChoiceFilter(choices=Suppression.REASON_CHOICES, help_text="차단 사유")
    value = filters.CharFilter(lookup_expr='icontains', help_text="차단 값 검색")
    
    class Meta:
        model = Suppression
        fields = ['type', 'reason', 'value']
