"""
Analytics Serializers
프론트엔드 차트용 집계 데이터 직렬화
"""
from rest_framework import serializers


class OverviewAnalyticsSerializer(serializers.Serializer):
    """캠페인 전체 개요 통계"""
    total_sent = serializers.IntegerField(help_text="총 발송 수")
    total_delivered = serializers.IntegerField(help_text="총 전달 수")
    total_opened = serializers.IntegerField(help_text="총 오픈 수")
    total_clicked = serializers.IntegerField(help_text="총 클릭 수")
    total_replied = serializers.IntegerField(help_text="총 답장 수")
    total_bounced = serializers.IntegerField(help_text="총 반송 수")
    
    unique_opens = serializers.IntegerField(help_text="고유 오픈 수 (중복 제거)")
    unique_clicks = serializers.IntegerField(help_text="고유 클릭 수 (중복 제거)")
    
    open_rate = serializers.FloatField(help_text="오픈율 (%)")
    click_rate = serializers.FloatField(help_text="클릭율 (%)")
    click_to_open_rate = serializers.FloatField(help_text="클릭/오픈율 (%)")
    bounce_rate = serializers.FloatField(help_text="반송율 (%)")
    reply_rate = serializers.FloatField(help_text="답장율 (%)")


class TimeseriesDataPointSerializer(serializers.Serializer):
    """시계열 데이터 포인트"""
    timestamp = serializers.DateTimeField(help_text="시간")
    date = serializers.DateField(help_text="날짜")
    sent = serializers.IntegerField(default=0)
    opened = serializers.IntegerField(default=0)
    clicked = serializers.IntegerField(default=0)
    replied = serializers.IntegerField(default=0)
    bounced = serializers.IntegerField(default=0)


class TimeseriesAnalyticsSerializer(serializers.Serializer):
    """시계열 분석 데이터"""
    granularity = serializers.CharField(help_text="집계 단위 (hourly, daily)")
    data_points = TimeseriesDataPointSerializer(many=True, help_text="데이터 포인트")


class TemplatePerformanceSerializer(serializers.Serializer):
    """템플릿 성과"""
    template_id = serializers.UUIDField(help_text="템플릿 ID")
    template_name = serializers.CharField(help_text="템플릿 이름")
    version = serializers.IntegerField(help_text="버전 번호")
    
    sent = serializers.IntegerField(help_text="발송 수")
    opened = serializers.IntegerField(help_text="오픈 수")
    clicked = serializers.IntegerField(help_text="클릭 수")
    
    open_rate = serializers.FloatField(help_text="오픈율 (%)")
    click_rate = serializers.FloatField(help_text="클릭율 (%)")


class BreakdownItemSerializer(serializers.Serializer):
    """분류별 항목"""
    key = serializers.CharField(help_text="분류 키 (태그명, 세그먼트명 등)")
    label = serializers.CharField(help_text="표시 레이블")
    
    sent = serializers.IntegerField(help_text="발송 수")
    opened = serializers.IntegerField(help_text="오픈 수")
    clicked = serializers.IntegerField(help_text="클릭 수")
    
    open_rate = serializers.FloatField(help_text="오픈율 (%)")
    click_rate = serializers.FloatField(help_text="클릭율 (%)")


class BreakdownAnalyticsSerializer(serializers.Serializer):
    """분류별 분석 데이터"""
    breakdown_type = serializers.CharField(help_text="분류 타입 (tag, segment)")
    items = BreakdownItemSerializer(many=True, help_text="분류 항목")


class ResponseTimeDistributionSerializer(serializers.Serializer):
    """응답 시간 분포"""
    bucket = serializers.CharField(help_text="시간 범위 (예: 0-1h, 1-6h)")
    count = serializers.IntegerField(help_text="건수")
    percentage = serializers.FloatField(help_text="비율 (%)")


class ResponseTimeAnalyticsSerializer(serializers.Serializer):
    """응답 시간 분석"""
    avg_time_to_open = serializers.FloatField(
        help_text="평균 오픈 시간 (초)",
        allow_null=True
    )
    avg_time_to_click = serializers.FloatField(
        help_text="평균 클릭 시간 (초)",
        allow_null=True
    )
    avg_time_to_reply = serializers.FloatField(
        help_text="평균 답장 시간 (초)",
        allow_null=True
    )
    
    median_time_to_open = serializers.FloatField(
        help_text="중간값 오픈 시간 (초)",
        allow_null=True
    )
    median_time_to_click = serializers.FloatField(
        help_text="중간값 클릭 시간 (초)",
        allow_null=True
    )
    
    open_time_distribution = ResponseTimeDistributionSerializer(
        many=True,
        help_text="오픈 시간 분포"
    )
    click_time_distribution = ResponseTimeDistributionSerializer(
        many=True,
        help_text="클릭 시간 분포"
    )
