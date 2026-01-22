"""
Analytics ViewSet
캠페인 분석 데이터 제공 (프론트엔드 차트용)
"""
from django.db.models import Count, Q, Avg, F, ExpressionWrapper, DurationField
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import action
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from core.viewsets import BaseViewSet
from campaigns.models import Campaign, SendJob, EmailMessage, EmailEvent
from campaigns.serializers_analytics import (
    OverviewAnalyticsSerializer,
    TimeseriesAnalyticsSerializer,
    TemplatePerformanceSerializer,
    BreakdownAnalyticsSerializer,
    ResponseTimeAnalyticsSerializer
)


class CampaignAnalyticsViewSet(BaseViewSet):
    """
    캠페인 분석 API
    
    프론트엔드가 바로 차트를 그릴 수 있도록 집계된 데이터를 제공합니다.
    """
    queryset = Campaign.objects.all()
    serializer_class = None  # Action별로 다른 serializer 사용
    
    def _parse_date_params(self, request):
        """날짜 파라미터 파싱"""
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        
        if from_date:
            from_date = timezone.datetime.fromisoformat(from_date.replace('Z', '+00:00'))
        if to_date:
            to_date = timezone.datetime.fromisoformat(to_date.replace('Z', '+00:00'))
            
        return from_date, to_date
    
    @extend_schema(
        summary="캠페인 개요 분석",
        description="""
        캠페인의 전체 통계를 반환합니다.
        
        **반환 데이터:**
        - total_sent: 총 발송 수
        - total_opened: 총 오픈 수
        - total_clicked: 총 클릭 수
        - open_rate: 오픈율 (%)
        - click_rate: 클릭율 (%)
        - bounce_rate: 반송율 (%)
        """,
        parameters=[
            OpenApiParameter(
                name='from_date',
                type=OpenApiTypes.DATETIME,
                description='시작 날짜 (ISO 8601)'
            ),
            OpenApiParameter(
                name='to_date',
                type=OpenApiTypes.DATETIME,
                description='종료 날짜 (ISO 8601)'
            ),
        ],
        responses={200: OverviewAnalyticsSerializer}
    )
    @action(detail=True, methods=['get'], url_path='analytics/overview')
    def analytics_overview(self, request, pk=None):
        """캠페인 개요 통계"""
        campaign = self.get_object()
        from_date, to_date = self._parse_date_params(request)
        
        # 발송 잡 필터링
        jobs = SendJob.objects.filter(campaign=campaign)
        if from_date:
            jobs = jobs.filter(scheduled_at__gte=from_date)
        if to_date:
            jobs = jobs.filter(scheduled_at__lte=to_date)
        
        # 기본 통계
        total_sent = jobs.filter(status='sent').count()
        
        # 이메일 메시지 필터링
        messages = EmailMessage.objects.filter(send_job__campaign=campaign)
        if from_date or to_date:
            message_ids = jobs.values_list('email_message__id', flat=True)
            messages = messages.filter(id__in=message_ids)
        
        # 이벤트 집계
        events = EmailEvent.objects.filter(email_message__in=messages)
        
        event_counts = events.values('event_type').annotate(count=Count('id'))
        event_dict = {item['event_type']: item['count'] for item in event_counts}
        
        total_opened = event_dict.get('opened_pixel', 0)
        total_clicked = event_dict.get('clicked', 0)
        total_replied = event_dict.get('replied', 0)
        total_bounced = event_dict.get('bounced', 0)
        
        # 고유 오픈/클릭 (메시지별 첫 이벤트만 카운트)
        unique_opens = events.filter(event_type='opened_pixel').values('email_message').distinct().count()
        unique_clicks = events.filter(event_type='clicked').values('email_message').distinct().count()
        
        # 비율 계산
        total_delivered = total_sent - total_bounced
        open_rate = (unique_opens / total_delivered * 100) if total_delivered > 0 else 0
        click_rate = (unique_clicks / total_delivered * 100) if total_delivered > 0 else 0
        click_to_open_rate = (unique_clicks / unique_opens * 100) if unique_opens > 0 else 0
        bounce_rate = (total_bounced / total_sent * 100) if total_sent > 0 else 0
        reply_rate = (total_replied / total_delivered * 100) if total_delivered > 0 else 0
        
        data = {
            'total_sent': total_sent,
            'total_delivered': total_delivered,
            'total_opened': total_opened,
            'total_clicked': total_clicked,
            'total_replied': total_replied,
            'total_bounced': total_bounced,
            'unique_opens': unique_opens,
            'unique_clicks': unique_clicks,
            'open_rate': round(open_rate, 2),
            'click_rate': round(click_rate, 2),
            'click_to_open_rate': round(click_to_open_rate, 2),
            'bounce_rate': round(bounce_rate, 2),
            'reply_rate': round(reply_rate, 2),
        }
        
        serializer = OverviewAnalyticsSerializer(data)
        return self.success_response(data=serializer.data)
    
    @extend_schema(
        summary="시계열 분석",
        description="""
        날짜/시간별 이벤트 추이를 반환합니다.
        
        **granularity:**
        - hourly: 시간별 집계
        - daily: 일별 집계 (기본값)
        """,
        parameters=[
            OpenApiParameter(
                name='from_date',
                type=OpenApiTypes.DATETIME,
                description='시작 날짜 (ISO 8601)'
            ),
            OpenApiParameter(
                name='to_date',
                type=OpenApiTypes.DATETIME,
                description='종료 날짜 (ISO 8601)'
            ),
            OpenApiParameter(
                name='granularity',
                type=OpenApiTypes.STR,
                description='집계 단위 (hourly, daily)',
                enum=['hourly', 'daily']
            ),
        ],
        responses={200: TimeseriesAnalyticsSerializer}
    )
    @action(detail=True, methods=['get'], url_path='analytics/timeseries')
    def analytics_timeseries(self, request, pk=None):
        """시계열 분석"""
        campaign = self.get_object()
        from_date, to_date = self._parse_date_params(request)
        granularity = request.query_params.get('granularity', 'daily')
        
        # 기본 날짜 범위 설정 (지정되지 않은 경우)
        if not from_date:
            from_date = timezone.now() - timedelta(days=30)
        if not to_date:
            to_date = timezone.now()
        
        # 이벤트 필터링
        events = EmailEvent.objects.filter(
            email_message__send_job__campaign=campaign,
            event_at__gte=from_date,
            event_at__lte=to_date
        )
        
        # 시간 단위 집계
        if granularity == 'hourly':
            trunc_func = TruncHour
        else:
            trunc_func = TruncDate
        
        # 이벤트별 집계
        timeseries_data = events.annotate(
            time_bucket=trunc_func('event_at')
        ).values('time_bucket', 'event_type').annotate(
            count=Count('id')
        ).order_by('time_bucket')
        
        # 데이터 포인트 생성
        data_points = {}
        for item in timeseries_data:
            bucket = item['time_bucket']
            event_type = item['event_type']
            count = item['count']
            
            if bucket not in data_points:
                data_points[bucket] = {
                    'timestamp': bucket,
                    'date': bucket.date(),
                    'sent': 0,
                    'opened': 0,
                    'clicked': 0,
                    'replied': 0,
                    'bounced': 0,
                }
            
            if event_type == 'sent':
                data_points[bucket]['sent'] = count
            elif event_type == 'opened_pixel':
                data_points[bucket]['opened'] = count
            elif event_type == 'clicked':
                data_points[bucket]['clicked'] = count
            elif event_type == 'replied':
                data_points[bucket]['replied'] = count
            elif event_type == 'bounced':
                data_points[bucket]['bounced'] = count
        
        # 정렬된 리스트로 변환
        sorted_points = sorted(data_points.values(), key=lambda x: x['timestamp'])
        
        data = {
            'granularity': granularity,
            'data_points': sorted_points
        }
        
        serializer = TimeseriesAnalyticsSerializer(data)
        return self.success_response(data=serializer.data)
    
    @extend_schema(
        summary="템플릿별 성과 분석",
        description="캠페인에 사용된 템플릿 버전별 성과를 비교합니다.",
        parameters=[
            OpenApiParameter(
                name='from_date',
                type=OpenApiTypes.DATETIME,
                description='시작 날짜 (ISO 8601)'
            ),
            OpenApiParameter(
                name='to_date',
                type=OpenApiTypes.DATETIME,
                description='종료 날짜 (ISO 8601)'
            ),
        ],
        responses={200: TemplatePerformanceSerializer(many=True)}
    )
    @action(detail=True, methods=['get'], url_path='analytics/templates')
    def analytics_templates(self, request, pk=None):
        """템플릿별 성과 분석"""
        campaign = self.get_object()
        from_date, to_date = self._parse_date_params(request)
        
        # 발송 잡 필터링
        jobs = SendJob.objects.filter(campaign=campaign, status='sent')
        if from_date:
            jobs = jobs.filter(scheduled_at__gte=from_date)
        if to_date:
            jobs = jobs.filter(scheduled_at__lte=to_date)
        
        # 템플릿 버전별 집계
        template_stats = jobs.values(
            'template_version__template__id',
            'template_version__template__name',
            'template_version__version'
        ).annotate(
            sent_count=Count('id')
        )
        
        results = []
        for stat in template_stats:
            template_id = stat['template_version__template__id']
            template_name = stat['template_version__template__name']
            version = stat['template_version__version']
            sent = stat['sent_count']
            
            # 해당 템플릿의 이벤트 집계
            messages = EmailMessage.objects.filter(
                send_job__campaign=campaign,
                send_job__template_version__template__id=template_id,
                send_job__template_version__version=version
            )
            
            opened = EmailEvent.objects.filter(
                email_message__in=messages,
                event_type='opened_pixel'
            ).values('email_message').distinct().count()
            
            clicked = EmailEvent.objects.filter(
                email_message__in=messages,
                event_type='clicked'
            ).values('email_message').distinct().count()
            
            open_rate = (opened / sent * 100) if sent > 0 else 0
            click_rate = (clicked / sent * 100) if sent > 0 else 0
            
            results.append({
                'template_id': template_id,
                'template_name': template_name,
                'version': version,
                'sent': sent,
                'opened': opened,
                'clicked': clicked,
                'open_rate': round(open_rate, 2),
                'click_rate': round(click_rate, 2),
            })
        
        serializer = TemplatePerformanceSerializer(results, many=True)
        return self.success_response(data=serializer.data)
    
    @extend_schema(
        summary="분류별 분석",
        description="""
        태그 또는 세그먼트별로 성과를 분석합니다.
        
        **breakdown_type:**
        - tag: 리드 태그별 분석
        - segment: 세그먼트별 분석 (추후 구현)
        """,
        parameters=[
            OpenApiParameter(
                name='breakdown_type',
                type=OpenApiTypes.STR,
                description='분류 타입 (tag, segment)',
                enum=['tag', 'segment']
            ),
            OpenApiParameter(
                name='from_date',
                type=OpenApiTypes.DATETIME,
                description='시작 날짜 (ISO 8601)'
            ),
            OpenApiParameter(
                name='to_date',
                type=OpenApiTypes.DATETIME,
                description='종료 날짜 (ISO 8601)'
            ),
        ],
        responses={200: BreakdownAnalyticsSerializer}
    )
    @action(detail=True, methods=['get'], url_path='analytics/breakdown')
    def analytics_breakdown(self, request, pk=None):
        """분류별 분석"""
        campaign = self.get_object()
        breakdown_type = request.query_params.get('breakdown_type', 'tag')
        from_date, to_date = self._parse_date_params(request)
        
        # 발송 잡 필터링
        jobs = SendJob.objects.filter(campaign=campaign, status='sent')
        if from_date:
            jobs = jobs.filter(scheduled_at__gte=from_date)
        if to_date:
            jobs = jobs.filter(scheduled_at__lte=to_date)
        
        items = []
        
        if breakdown_type == 'tag':
            # 태그별 집계
            from crm.models import Tag
            
            tags = Tag.objects.all()
            for tag in tags:
                # 해당 태그를 가진 리드의 발송 수
                tag_jobs = jobs.filter(lead__tags=tag)
                sent = tag_jobs.count()
                
                if sent == 0:
                    continue
                
                # 이벤트 집계
                messages = EmailMessage.objects.filter(send_job__in=tag_jobs)
                
                opened = EmailEvent.objects.filter(
                    email_message__in=messages,
                    event_type='opened_pixel'
                ).values('email_message').distinct().count()
                
                clicked = EmailEvent.objects.filter(
                    email_message__in=messages,
                    event_type='clicked'
                ).values('email_message').distinct().count()
                
                open_rate = (opened / sent * 100) if sent > 0 else 0
                click_rate = (clicked / sent * 100) if sent > 0 else 0
                
                items.append({
                    'key': str(tag.id),
                    'label': tag.name,
                    'sent': sent,
                    'opened': opened,
                    'clicked': clicked,
                    'open_rate': round(open_rate, 2),
                    'click_rate': round(click_rate, 2),
                })
        
        data = {
            'breakdown_type': breakdown_type,
            'items': items
        }
        
        serializer = BreakdownAnalyticsSerializer(data)
        return self.success_response(data=serializer.data)
    
    @extend_schema(
        summary="응답 시간 분석",
        description="""
        이메일 발송 후 오픈/클릭/답장까지 걸린 시간을 분석합니다.
        
        **반환 데이터:**
        - avg_time_to_open: 평균 오픈 시간 (초)
        - median_time_to_open: 중간값 오픈 시간 (초)
        - open_time_distribution: 오픈 시간 분포
        """,
        parameters=[
            OpenApiParameter(
                name='from_date',
                type=OpenApiTypes.DATETIME,
                description='시작 날짜 (ISO 8601)'
            ),
            OpenApiParameter(
                name='to_date',
                type=OpenApiTypes.DATETIME,
                description='종료 날짜 (ISO 8601)'
            ),
        ],
        responses={200: ResponseTimeAnalyticsSerializer}
    )
    @action(detail=True, methods=['get'], url_path='analytics/response-time')
    def analytics_response_time(self, request, pk=None):
        """응답 시간 분석"""
        campaign = self.get_object()
        from_date, to_date = self._parse_date_params(request)
        
        # 발송 이벤트 가져오기
        sent_events = EmailEvent.objects.filter(
            email_message__send_job__campaign=campaign,
            event_type='sent'
        )
        if from_date:
            sent_events = sent_events.filter(event_at__gte=from_date)
        if to_date:
            sent_events = sent_events.filter(event_at__lte=to_date)
        
        # 오픈 시간 계산
        open_times = []
        for sent in sent_events:
            first_open = EmailEvent.objects.filter(
                email_message=sent.email_message,
                event_type='opened_pixel'
            ).order_by('event_at').first()
            
            if first_open:
                time_diff = (first_open.event_at - sent.event_at).total_seconds()
                open_times.append(time_diff)
        
        # 클릭 시간 계산
        click_times = []
        for sent in sent_events:
            first_click = EmailEvent.objects.filter(
                email_message=sent.email_message,
                event_type='clicked'
            ).order_by('event_at').first()
            
            if first_click:
                time_diff = (first_click.event_at - sent.event_at).total_seconds()
                click_times.append(time_diff)
        
        # 평균 계산
        avg_time_to_open = sum(open_times) / len(open_times) if open_times else None
        avg_time_to_click = sum(click_times) / len(click_times) if click_times else None
        
        # 중간값 계산
        median_time_to_open = None
        median_time_to_click = None
        if open_times:
            sorted_opens = sorted(open_times)
            median_time_to_open = sorted_opens[len(sorted_opens) // 2]
        if click_times:
            sorted_clicks = sorted(click_times)
            median_time_to_click = sorted_clicks[len(sorted_clicks) // 2]
        
        # 시간 분포 (0-1h, 1-6h, 6-24h, 24h+)
        def get_distribution(times):
            buckets = {
                '0-1h': 0,
                '1-6h': 0,
                '6-24h': 0,
                '24h+': 0
            }
            for t in times:
                hours = t / 3600
                if hours < 1:
                    buckets['0-1h'] += 1
                elif hours < 6:
                    buckets['1-6h'] += 1
                elif hours < 24:
                    buckets['6-24h'] += 1
                else:
                    buckets['24h+'] += 1
            
            total = len(times)
            return [
                {
                    'bucket': bucket,
                    'count': count,
                    'percentage': round(count / total * 100, 2) if total > 0 else 0
                }
                for bucket, count in buckets.items()
            ]
        
        open_time_distribution = get_distribution(open_times) if open_times else []
        click_time_distribution = get_distribution(click_times) if click_times else []
        
        data = {
            'avg_time_to_open': round(avg_time_to_open, 2) if avg_time_to_open else None,
            'avg_time_to_click': round(avg_time_to_click, 2) if avg_time_to_click else None,
            'avg_time_to_reply': None,  # 추후 구현
            'median_time_to_open': round(median_time_to_open, 2) if median_time_to_open else None,
            'median_time_to_click': round(median_time_to_click, 2) if median_time_to_click else None,
            'open_time_distribution': open_time_distribution,
            'click_time_distribution': click_time_distribution,
        }
        
        serializer = ResponseTimeAnalyticsSerializer(data)
        return self.success_response(data=serializer.data)
