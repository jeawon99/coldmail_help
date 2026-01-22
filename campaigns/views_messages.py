"""
EmailMessage ViewSet
"""
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, OpenApiParameter
from core.viewsets import BaseViewSet
from campaigns.models import EmailMessage, EmailEvent
from campaigns.serializers_events import EmailEventSerializer


class EmailMessageViewSet(BaseViewSet):
    """
    이메일 메시지 관리
    
    발송된 이메일 메시지와 관련 이벤트를 조회합니다.
    """
    queryset = EmailMessage.objects.select_related('send_job', 'send_job__campaign').all()
    serializer_class = None  # 기본 serializer는 사용하지 않음
    
    @extend_schema(
        summary="메시지 이벤트 조회",
        description="""
        특정 이메일 메시지의 이벤트를 조회합니다.
        
        **이벤트 타입:**
        - opened_pixel: 이메일 오픈 (최초 1회만 기록)
        - clicked: 링크 클릭 (중복 허용)
        - replied: 답장
        - bounced: 반송
        
        **필터:**
        - event_type: 이벤트 타입 필터
        """,
        parameters=[
            OpenApiParameter(name='event_type', type=str, description='이벤트 타입 필터 (opened_pixel, clicked, replied, bounced)'),
        ],
        responses={200: EmailEventSerializer(many=True)}
    )
    @action(detail=True, methods=['get'], url_path='events')
    def get_events(self, request, pk=None):
        """메시지 이벤트 조회"""
        email_message = self.get_object()
        
        # EmailMessage의 모든 이벤트 조회
        events = email_message.events.all()
        
        # 이벤트 타입 필터
        event_type = request.query_params.get('event_type')
        if event_type:
            events = events.filter(event_type=event_type)
        
        # 페이지네이션 적용
        page = self.paginate_queryset(events)
        if page is not None:
            serializer = EmailEventSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = EmailEventSerializer(events, many=True)
        return self.success_response(data=serializer.data)
