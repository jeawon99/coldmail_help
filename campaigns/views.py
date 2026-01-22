"""Campaigns & Segments Views"""
import datetime
from django.db.models import Q, Count
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from core.viewsets import BaseViewSet
from campaigns.models import LeadSegment, Campaign, CampaignTarget, SendJob, EmailMessage, EmailEvent
from campaigns.serializers import (
    LeadSegmentSerializer,
    SegmentPreviewSerializer,
    CampaignSerializer,
    CampaignListSerializer,
    CampaignTargetSerializer,
    FreezeTargetsRequestSerializer,
    FreezeTargetsResponseSerializer,
    TargetAddRequestSerializer,
    TargetRemoveRequestSerializer,
    SendJobSerializer,
    SendJobListSerializer,
    ScheduleJobsRequestSerializer,
    ScheduleJobsResponseSerializer,
    RescheduleJobRequestSerializer,
    CancelJobRequestSerializer,
)
from campaigns.serializers_events import EmailEventDetailSerializer
from crm.models import Lead, Tag, Suppression
from templates.models import TemplateVersion


class SegmentFilterEngine:
    """세그먼트 필터 엔진 - filter_json을 Django ORM 쿼리로 변환"""
    
    def __init__(self, filter_json, exclude_suppression=True, exclude_do_not_contact=True):
        self.filter_json = filter_json
        self.exclude_suppression = exclude_suppression
        self.exclude_do_not_contact = exclude_do_not_contact
    
    def apply_filters(self, queryset=None):
        """필터를 적용하여 쿼리셋 반환"""
        if queryset is None:
            queryset = Lead.objects.all()
        
        # 'all' 조건 (AND)
        if 'all' in self.filter_json:
            for condition in self.filter_json['all']:
                queryset = self._apply_condition(queryset, condition, negate=False)
        
        # 'not' 조건 (NOT)
        if 'not' in self.filter_json:
            for condition in self.filter_json['not']:
                queryset = self._apply_condition(queryset, condition, negate=True)
        
        # Suppression 제외
        if self.exclude_suppression:
            queryset = self._exclude_suppression(queryset)
        
        # Do not contact 제외
        if self.exclude_do_not_contact:
            queryset = queryset.exclude(status='do_not_contact')
        
        return queryset
    
    def _apply_condition(self, queryset, condition, negate=False):
        """단일 조건 적용"""
        field = condition['field']
        op = condition['op']
        value = condition.get('value')
        
        # tags 필드 처리
        if field == 'tags':
            return self._apply_tags_filter(queryset, op, value, negate)
        
        # subscriber_count 필드 처리
        elif field == 'subscriber_count':
            return self._apply_numeric_filter(queryset, 'subscriber_count', op, value, negate)
        
        # keywords_raw 필드 처리
        elif field == 'keywords_raw':
            return self._apply_keywords_filter(queryset, op, value, negate)
        
        # primary_email 필드 처리
        elif field == 'primary_email':
            return self._apply_email_filter(queryset, op, negate)
        
        # status 필드 처리
        elif field == 'status':
            return self._apply_status_filter(queryset, op, value, negate)
        
        return queryset
    
    def _apply_tags_filter(self, queryset, op, value, negate):
        """태그 필터 적용"""
        if op == 'in':
            # value에 있는 태그 이름들 중 하나라도 가진 리드
            tag_names = value if isinstance(value, list) else [value]
            q = Q(tags__name__in=tag_names)
            if negate:
                queryset = queryset.exclude(q).distinct()
            else:
                queryset = queryset.filter(q).distinct()
        
        elif op == 'not_in':
            # value에 있는 태그를 하나도 안 가진 리드
            tag_names = value if isinstance(value, list) else [value]
            q = Q(tags__name__in=tag_names)
            if negate:
                queryset = queryset.filter(q).distinct()
            else:
                queryset = queryset.exclude(q).distinct()
        
        return queryset
    
    def _apply_numeric_filter(self, queryset, field_name, op, value, negate):
        """숫자 필드 필터 적용"""
        q_filter = {}
        
        if op == '>=':
            q_filter[f'{field_name}__gte'] = value
        elif op == '<=':
            q_filter[f'{field_name}__lte'] = value
        elif op == '>':
            q_filter[f'{field_name}__gt'] = value
        elif op == '<':
            q_filter[f'{field_name}__lt'] = value
        elif op == '==':
            q_filter[f'{field_name}'] = value
        
        if q_filter:
            if negate:
                queryset = queryset.exclude(**q_filter)
            else:
                queryset = queryset.filter(**q_filter)
        
        return queryset
    
    def _apply_keywords_filter(self, queryset, op, value, negate):
        """키워드 필터 적용"""
        if op == 'contains_any':
            # value에 있는 키워드 중 하나라도 포함
            keywords = value if isinstance(value, list) else [value]
            q = Q()
            for keyword in keywords:
                q |= Q(keywords_raw__icontains=keyword)
            
            if negate:
                queryset = queryset.exclude(q)
            else:
                queryset = queryset.filter(q)
        
        return queryset
    
    def _apply_email_filter(self, queryset, op, negate):
        """이메일 필터 적용"""
        if op == 'is_not_null':
            q = Q(primary_email__isnull=False) & ~Q(primary_email='')
            if negate:
                queryset = queryset.exclude(q)
            else:
                queryset = queryset.filter(q)
        
        elif op == 'is_null':
            q = Q(primary_email__isnull=True) | Q(primary_email='')
            if negate:
                queryset = queryset.exclude(q)
            else:
                queryset = queryset.filter(q)
        
        return queryset
    
    def _apply_status_filter(self, queryset, op, value, negate):
        """상태 필터 적용"""
        if op == 'in':
            statuses = value if isinstance(value, list) else [value]
            q = Q(status__in=statuses)
            if negate:
                queryset = queryset.exclude(q)
            else:
                queryset = queryset.filter(q)
        
        elif op == '==':
            q = Q(status=value)
            if negate:
                queryset = queryset.exclude(q)
            else:
                queryset = queryset.filter(q)
        
        return queryset
    
    def _exclude_suppression(self, queryset):
        """Suppression 제외"""
        # Email suppression
        suppressed_emails = Suppression.objects.filter(
            type='email'
        ).values_list('value', flat=True)
        
        if suppressed_emails:
            queryset = queryset.exclude(primary_email__in=suppressed_emails)
        
        # Lead suppression
        suppressed_lead_ids = Suppression.objects.filter(
            type='lead'
        ).values_list('value', flat=True)
        
        if suppressed_lead_ids:
            queryset = queryset.exclude(id__in=suppressed_lead_ids)
        
        # Domain suppression
        suppressed_domains = Suppression.objects.filter(
            type='domain'
        ).values_list('value', flat=True)
        
        for domain in suppressed_domains:
            queryset = queryset.exclude(primary_email__icontains=f'@{domain}')
        
        return queryset


class LeadSegmentViewSet(BaseViewSet):
    """
    리드 세그먼트 관리
    
    동적 필터 조건으로 타겟 리드를 선정하는 세그먼트를 관리합니다.
    filter_json DSL을 사용하여 복잡한 조건을 조합할 수 있습니다.
    """
    queryset = LeadSegment.objects.all()
    serializer_class = LeadSegmentSerializer
    
    @extend_schema(
        summary="세그먼트 생성",
        description="""
        filter_json DSL을 사용하여 새 세그먼트를 생성합니다.
        
        **filter_json 구조:**
        ```json
        {
            "all": [조건1, 조건2, ...],  // AND 조건
            "not": [조건3, 조건4, ...]   // NOT 조건 (옵션)
        }
        ```
        
        **각 조건 형식:**
        ```json
        {
            "field": "필드명",
            "op": "연산자",
            "value": 값
        }
        ```
        
        **지원 필드:**
        - `tags`: 태그 목록
        - `subscriber_count`: 구독자 수
        - `keywords_raw`: 키워드 문자열
        - `primary_email`: 이메일 주소
        - `status`: 리드 상태
        
        **지원 연산자:**
        - `in`, `not_in`: 배열 포함 여부
        - `>=`, `<=`, `>`, `<`, `==`: 숫자/문자열 비교
        - `contains_any`: 문자열에 배열 값 중 하나라도 포함 (대소문자 무시)
        - `is_not_null`, `is_null`: null 체크
        """,
        request=LeadSegmentSerializer,
        responses={201: LeadSegmentSerializer},
        examples=[
            OpenApiExample(
                '게임 유튜버 세그먼트',
                value={
                    "name": "게임 유튜버 (구독자 10만+)",
                    "filter_json": {
                        "all": [
                            {"field": "tags", "op": "in", "value": ["게임", "유튜버"]},
                            {"field": "subscriber_count", "op": ">=", "value": 100000},
                            {"field": "primary_email", "op": "is_not_null"}
                        ],
                        "not": [
                            {"field": "status", "op": "==", "value": "do_not_contact"}
                        ]
                    }
                },
                request_only=True
            ),
            OpenApiExample(
                'Shorts/몰카 콘텐츠 세그먼트',
                value={
                    "name": "Shorts/몰카 유튜버",
                    "filter_json": {
                        "all": [
                            {"field": "keywords_raw", "op": "contains_any", "value": ["shorts", "몰카", "쇼츠"]},
                            {"field": "primary_email", "op": "is_not_null"}
                        ]
                    }
                },
                request_only=True
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @extend_schema(
        summary="세그먼트 미리보기",
        description="""
        세그먼트 조건에 맞는 리드를 미리보기합니다.
        
        **응답 내용:**
        - `total_count`: 조건에 맞는 전체 리드 수
        - `sample_leads`: 샘플 리드 목록 (기본 5개)
        - `filter_summary`: 적용된 필터 조건 요약
        
        **옵션 파라미터:**
        - `exclude_suppression`: Suppression 리스트 제외 여부 (기본: true)
        - `exclude_do_not_contact`: Do Not Contact 상태 제외 여부 (기본: true)
        - `sample_size`: 샘플 리드 개수 (0-100, 기본: 5)
        """,
        request=SegmentPreviewSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "total_count": {"type": "integer", "example": 3034},
                            "sample_leads": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "channel_name": {"type": "string"},
                                        "subscriber_count": {"type": "integer"},
                                        "primary_email": {"type": "string"},
                                        "tags": {"type": "array", "items": {"type": "string"}},
                                        "status": {"type": "string"}
                                    }
                                }
                            },
                            "filter_summary": {
                                "type": "object",
                                "properties": {
                                    "conditions": {"type": "object"},
                                    "exclude_suppression": {"type": "boolean"},
                                    "exclude_do_not_contact": {"type": "boolean"}
                                }
                            }
                        }
                    }
                }
            }
        },
        examples=[
            OpenApiExample(
                '기본 미리보기',
                value={
                    "exclude_suppression": True,
                    "exclude_do_not_contact": True,
                    "sample_size": 5
                },
                request_only=True
            ),
            OpenApiExample(
                '미리보기 응답',
                value={
                    "success": True,
                    "data": {
                        "total_count": 3034,
                        "sample_leads": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "channel_name": "게임 챌린지",
                                "subscriber_count": 150000,
                                "primary_email": "test@test.com",
                                "tags": ["게임"],
                                "status": "new"
                            }
                        ],
                        "filter_summary": {
                            "conditions": {
                                "all": [
                                    {"field": "keywords_raw", "op": "contains_any", "value": ["shorts", "몰카"]}
                                ]
                            },
                            "exclude_suppression": True,
                            "exclude_do_not_contact": True
                        }
                    }
                },
                response_only=True
            )
        ]
    )
    @action(detail=True, methods=['post'], url_path='preview')
    def preview(self, request, pk=None):
        """세그먼트 미리보기 - 조건에 맞는 리드 카운트 + 샘플"""
        segment = self.get_object()
        
        # 요청 파라미터 파싱
        preview_serializer = SegmentPreviewSerializer(data=request.data)
        preview_serializer.is_valid(raise_exception=True)
        
        exclude_suppression = preview_serializer.validated_data['exclude_suppression']
        exclude_do_not_contact = preview_serializer.validated_data['exclude_do_not_contact']
        sample_size = preview_serializer.validated_data['sample_size']
        
        # 필터 엔진 적용
        engine = SegmentFilterEngine(
            filter_json=segment.filter_json,
            exclude_suppression=exclude_suppression,
            exclude_do_not_contact=exclude_do_not_contact
        )
        
        queryset = engine.apply_filters()
        
        # 카운트
        total_count = queryset.count()
        
        # 샘플 리드 (옵션)
        sample_leads = []
        if sample_size > 0:
            sample_queryset = queryset.prefetch_related('tags')[:sample_size]
            for lead in sample_queryset:
                sample_leads.append({
                    'id': str(lead.id),
                    'channel_name': lead.channel_name,
                    'subscriber_count': lead.subscriber_count,
                    'primary_email': lead.primary_email,
                    'tags': [tag.name for tag in lead.tags.all()],
                    'status': lead.status
                })
        
        # 필터 요약
        filter_summary = {
            'conditions': segment.filter_json,
            'exclude_suppression': exclude_suppression,
            'exclude_do_not_contact': exclude_do_not_contact
        }
        
        return self.success_response({
            'total_count': total_count,
            'sample_leads': sample_leads,
            'filter_summary': filter_summary
        })
    
    @extend_schema(
        summary="세그먼트 리드 Export",
        description="""
        세그먼트 조건에 맞는 리드 ID 목록을 반환합니다.
        
        캠페인 실행 시 타겟 리드를 선정하는 데 사용됩니다.
        자동으로 Suppression과 Do Not Contact 상태를 제외합니다.
        
        **응답 내용:**
        - `total_count`: 전체 리드 수
        - `lead_ids`: 리드 ID 배열 (UUID 문자열)
        """,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "total_count": {"type": "integer", "example": 3034},
                            "lead_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "example": ["550e8400-e29b-41d4-a716-446655440000", "550e8400-e29b-41d4-a716-446655440001"]
                            }
                        }
                    }
                }
            }
        }
    )
    @action(detail=True, methods=['get'], url_path='export')
    def export(self, request, pk=None):
        """세그먼트 대상 리드 ID 목록 내보내기"""
        segment = self.get_object()
        
        # 필터 엔진 적용
        engine = SegmentFilterEngine(
            filter_json=segment.filter_json,
            exclude_suppression=True,
            exclude_do_not_contact=True
        )
        
        queryset = engine.apply_filters()
        
        # ID 목록
        lead_ids = list(queryset.values_list('id', flat=True))
        
        return self.success_response({
            'total_count': len(lead_ids),
            'lead_ids': [str(lid) for lid in lead_ids]
        })


# ========== Campaign ViewSet ==========

class CampaignViewSet(BaseViewSet):
    """
    캠페인 관리
    
    세그먼트 조건으로 선정된 리드에게 이메일을 발송하는 캠페인을 관리합니다.
    
    **캠페인 워크플로우:**
    1. 캠페인 생성 (draft) + segment 선택
    2. freeze-targets로 대상 확정 (스냅샷 생성)
    3. 상태 변경: draft → running → paused/finished
    """
    queryset = Campaign.objects.select_related('segment').all()
    serializer_class = CampaignSerializer
    search_fields = ['name']
    ordering_fields = ['created_at', 'updated_at', 'frozen_at', 'name']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """리스트 조회 시 경량 시리얼라이저 사용"""
        if self.action == 'list':
            return CampaignListSerializer
        return CampaignSerializer
    
    def get_queryset(self):
        """쿼리셋 필터링 및 최적화"""
        queryset = super().get_queryset()
        
        # targets_count 어노테이션 추가
        queryset = queryset.annotate(_targets_count=Count('targets'))
        
        # status 필터
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    @extend_schema(
        summary="타겟 확정 (스냅샷 고정)",
        description="""
        세그먼트 조건으로 리드를 조회하여 campaign_target에 확정합니다.
        
        **처리 과정:**
        1. segment 조건으로 Lead 조회
        2. suppression 제외 (email/domain/lead 타입)
        3. lead.status='do_not_contact' 제외
        4. campaign_target bulk insert (idempotent)
        5. campaign.frozen_at, frozen_target_count 갱신
        
        **Idempotent 보장:**
        - unique constraint (campaign, lead)로 중복 방지
        - force=true 시 기존 타겟 삭제 후 재생성
        
        **스냅샷 옵션:**
        - save_snapshot=true: 리드 정보를 snapshot 필드에 저장
        """,
        request=FreezeTargetsRequestSerializer,
        responses={
            200: FreezeTargetsResponseSerializer,
            400: {"description": "세그먼트 미지정 또는 이미 확정됨"}
        },
        examples=[
            OpenApiExample(
                '기본 확정',
                value={
                    "force": False,
                    "save_snapshot": True
                },
                request_only=True
            ),
            OpenApiExample(
                '강제 재확정',
                value={
                    "force": True,
                    "save_snapshot": False
                },
                request_only=True
            )
        ]
    )
    @action(detail=True, methods=['post'], url_path='freeze-targets')
    def freeze_targets(self, request, pk=None):
        """타겟 확정 (스냅샷 고정)"""
        campaign = self.get_object()
        
        # 요청 파라미터 파싱
        request_serializer = FreezeTargetsRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        
        force = request_serializer.validated_data['force']
        save_snapshot = request_serializer.validated_data['save_snapshot']
        
        # 세그먼트 확인
        if not campaign.segment:
            return self.error_response(
                message="세그먼트가 지정되지 않았습니다.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # 이미 확정되어 있는지 확인
        if campaign.frozen_at and not force:
            return self.error_response(
                message=f"이미 {campaign.frozen_at.strftime('%Y-%m-%d %H:%M:%S')}에 확정되었습니다. force=true로 재확정 가능합니다.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # force=true 시 기존 타겟 삭제
            if force and campaign.frozen_at:
                deleted_count = campaign.targets.all().delete()[0]
                if deleted_count > 0:
                    # 삭제 로그 (선택)
                    pass
            
            # 세그먼트 필터 엔진으로 리드 조회
            engine = SegmentFilterEngine(
                filter_json=campaign.segment.filter_json,
                exclude_suppression=True,
                exclude_do_not_contact=True
            )
            
            queryset = engine.apply_filters()
            queryset = queryset.prefetch_related('tags')
            
            # 이미 타겟에 있는 리드 제외 (idempotent)
            existing_lead_ids = campaign.targets.values_list('lead_id', flat=True)
            queryset = queryset.exclude(id__in=existing_lead_ids)
            
            # Bulk create용 리스트 준비
            targets_to_create = []
            for lead in queryset:
                snapshot_data = None
                if save_snapshot:
                    snapshot_data = {
                        'channel_name': lead.channel_name,
                        'channel_url': lead.channel_url,
                        'subscriber_count': lead.subscriber_count,
                        'primary_email': lead.primary_email,
                        'tags': [tag.name for tag in lead.tags.all()],
                        'keywords_raw': lead.keywords_raw,
                        'status': lead.status,
                        'frozen_at': timezone.now().isoformat()
                    }
                
                targets_to_create.append(
                    CampaignTarget(
                        campaign=campaign,
                        lead=lead,
                        snapshot=snapshot_data,
                        status='pending'
                    )
                )
            
            # Bulk insert (ignore_conflicts로 중복 방지)
            created_targets = CampaignTarget.objects.bulk_create(
                targets_to_create,
                ignore_conflicts=True
            )
            
            # 전체 타겟 수 계산
            total_target_count = campaign.targets.count()
            
            # 캠페인 frozen 정보 갱신
            campaign.frozen_at = timezone.now()
            campaign.frozen_target_count = total_target_count
            campaign.save(update_fields=['frozen_at', 'frozen_target_count'])
        
        return self.success_response(
            data={
                'frozen_at': campaign.frozen_at.isoformat(),
                'frozen_target_count': campaign.frozen_target_count,
                'message': f"{campaign.frozen_target_count}개 타겟이 확정되었습니다."
            }
        )
    
    @extend_schema(
        summary="타겟 목록 조회",
        description="""
        캠페인에 확정된 타겟(리드) 목록을 조회합니다.
        
        **필터 옵션:**
        - `status`: 타겟 상태 (pending, queued, sent, replied, skipped, failed)
        - `has_email`: 이메일 보유 여부 (true/false)
        - `subscriber_count_min`, `subscriber_count_max`: 구독자 수 범위
        """,
        parameters=[
            OpenApiParameter(
                'status',
                OpenApiTypes.STR,
                description="타겟 상태 필터",
                enum=['pending', 'queued', 'sent', 'replied', 'skipped', 'failed']
            ),
            OpenApiParameter(
                'has_email',
                OpenApiTypes.BOOL,
                description="이메일 보유 여부"
            ),
            OpenApiParameter(
                'subscriber_count_min',
                OpenApiTypes.INT,
                description="최소 구독자 수"
            ),
            OpenApiParameter(
                'subscriber_count_max',
                OpenApiTypes.INT,
                description="최대 구독자 수"
            )
        ],
        responses={200: CampaignTargetSerializer(many=True)}
    )
    @action(detail=True, methods=['get'], url_path='targets')
    def targets_list(self, request, pk=None):
        """타겟 목록 조회"""
        campaign = self.get_object()
        
        queryset = campaign.targets.select_related('lead').prefetch_related('lead__tags').all()
        
        # status 필터
        target_status = request.query_params.get('status')
        if target_status:
            queryset = queryset.filter(status=target_status)
        
        # has_email 필터
        has_email = request.query_params.get('has_email')
        if has_email is not None:
            has_email_bool = has_email.lower() in ['true', '1', 'yes']
            if has_email_bool:
                queryset = queryset.exclude(lead__primary_email__isnull=True)
            else:
                queryset = queryset.filter(lead__primary_email__isnull=True)
        
        # subscriber_count 범위 필터
        subscriber_count_min = request.query_params.get('subscriber_count_min')
        if subscriber_count_min:
            queryset = queryset.filter(lead__subscriber_count__gte=int(subscriber_count_min))
        
        subscriber_count_max = request.query_params.get('subscriber_count_max')
        if subscriber_count_max:
            queryset = queryset.filter(lead__subscriber_count__lte=int(subscriber_count_max))
        
        # 페이지네이션
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = CampaignTargetSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = CampaignTargetSerializer(queryset, many=True)
        return self.success_response(serializer.data)
    
    @extend_schema(
        summary="타겟 수동 추가",
        description="""
        세그먼트 조건 밖의 리드를 수동으로 타겟에 추가합니다.
        
        **사용 예:**
        - VIP 리드를 수동 추가
        - 세그먼트 조건엔 안 맞지만 타겟팅 필요한 리드
        """,
        request=TargetAddRequestSerializer,
        responses={
            200: {"description": "추가 성공"},
            400: {"description": "잘못된 요청"}
        }
    )
    @action(detail=True, methods=['post'], url_path='targets/add')
    def targets_add(self, request, pk=None):
        """타겟 수동 추가"""
        campaign = self.get_object()
        
        request_serializer = TargetAddRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        
        lead_ids = request_serializer.validated_data['lead_ids']
        save_snapshot = request_serializer.validated_data['save_snapshot']
        
        # 리드 존재 확인
        leads = Lead.objects.filter(id__in=lead_ids).prefetch_related('tags')
        if leads.count() != len(lead_ids):
            return self.error_response(
                message="일부 리드를 찾을 수 없습니다.",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # 이미 타겟에 있는 리드 제외
        existing_lead_ids = set(campaign.targets.filter(lead_id__in=lead_ids).values_list('lead_id', flat=True))
        leads_to_add = [lead for lead in leads if lead.id not in existing_lead_ids]
        
        # Bulk create
        targets_to_create = []
        for lead in leads_to_add:
            snapshot_data = None
            if save_snapshot:
                snapshot_data = {
                    'channel_name': lead.channel_name,
                    'subscriber_count': lead.subscriber_count,
                    'primary_email': lead.primary_email,
                    'tags': [tag.name for tag in lead.tags.all()],
                    'added_manually': True,
                    'added_at': timezone.now().isoformat()
                }
            
            targets_to_create.append(
                CampaignTarget(
                    campaign=campaign,
                    lead=lead,
                    snapshot=snapshot_data,
                    status='pending'
                )
            )
        
        CampaignTarget.objects.bulk_create(targets_to_create)
        
        # frozen_target_count 갱신
        campaign.frozen_target_count = campaign.targets.count()
        campaign.save(update_fields=['frozen_target_count'])
        
        return self.success_response({
            'added_count': len(targets_to_create),
            'skipped_count': len(existing_lead_ids),
            'total_targets': campaign.frozen_target_count,
            'message': f"{len(targets_to_create)}개 타겟이 추가되었습니다."
        })
    
    @extend_schema(
        summary="타겟 제거",
        description="""
        확정된 타겟에서 특정 리드를 제거합니다.
        
        **주의:**
        - 이미 발송된(sent) 타겟은 제거되지 않습니다.
        - pending/queued 상태만 제거 가능
        """,
        request=TargetRemoveRequestSerializer,
        responses={
            200: {"description": "제거 성공"},
            400: {"description": "잘못된 요청"}
        }
    )
    @action(detail=True, methods=['post'], url_path='targets/remove')
    def targets_remove(self, request, pk=None):
        """타겟 제거"""
        campaign = self.get_object()
        
        request_serializer = TargetRemoveRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        
        lead_ids = request_serializer.validated_data['lead_ids']
        
        # pending/queued 상태만 제거 가능
        removable_targets = campaign.targets.filter(
            lead_id__in=lead_ids,
            status__in=['pending', 'queued']
        )
        
        removed_count = removable_targets.count()
        removable_targets.delete()
        
        # frozen_target_count 갱신
        campaign.frozen_target_count = campaign.targets.count()
        campaign.save(update_fields=['frozen_target_count'])
        
        skipped_count = len(lead_ids) - removed_count
        
        return self.success_response({
            'removed_count': removed_count,
            'skipped_count': skipped_count,
            'total_targets': campaign.frozen_target_count,
            'message': f"{removed_count}개 타겟이 제거되었습니다. (이미 발송된 타겟 {skipped_count}개는 제거 불가)"
        })
    
    @extend_schema(
        summary="캠페인 시작",
        description="캠페인을 running 상태로 변경합니다.",
        responses={200: CampaignSerializer}
    )
    @action(detail=True, methods=['post'], url_path='start')
    def start_campaign(self, request, pk=None):
        """캠페인 시작"""
        campaign = self.get_object()
        
        if campaign.status != 'draft':
            return self.error_response(
                message=f"draft 상태만 시작할 수 있습니다. (현재: {campaign.status})",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        if not campaign.frozen_at:
            return self.error_response(
                message="타겟을 먼저 확정해주세요. (freeze-targets)",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        campaign.status = 'running'
        campaign.save(update_fields=['status'])
        
        serializer = self.get_serializer(campaign)
        return self.success_response(
            data=serializer.data,
            message="캠페인이 시작되었습니다."
        )
    
    @extend_schema(
        summary="캠페인 일시정지",
        description="running 상태의 캠페인을 paused로 변경합니다.",
        responses={200: CampaignSerializer}
    )
    @action(detail=True, methods=['post'], url_path='pause')
    def pause_campaign(self, request, pk=None):
        """캠페인 일시정지"""
        campaign = self.get_object()
        
        if campaign.status != 'running':
            return self.error_response(
                message=f"running 상태만 일시정지할 수 있습니다. (현재: {campaign.status})",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        campaign.status = 'paused'
        campaign.save(update_fields=['status'])
        
        serializer = self.get_serializer(campaign)
        return self.success_response(
            data=serializer.data,
            message="캠페인이 일시정지되었습니다."
        )
    
    @extend_schema(
        summary="캠페인 종료",
        description="캠페인을 finished 상태로 변경합니다. (되돌릴 수 없음)",
        responses={200: CampaignSerializer}
    )
    @action(detail=True, methods=['post'], url_path='finish')
    def finish_campaign(self, request, pk=None):
        """캠페인 종료"""
        campaign = self.get_object()
        
        if campaign.status == 'finished':
            return self.error_response(
                message="이미 종료된 캠페인입니다.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        campaign.status = 'finished'
        campaign.save(update_fields=['status'])
        
        serializer = self.get_serializer(campaign)
        return self.success_response(
            data=serializer.data,
            message="캠페인이 종료되었습니다."
        )
    
    @extend_schema(
        summary="발송 잡 예약 생성",
        description="""
        캠페인 타겟을 기반으로 발송 잡(SendJob)을 생성합니다.
        
        **처리 과정:**
        1. campaign_target 중 status='pending'만 선택
        2. primary_email이 있는 타겟만 선택
        3. suppression 체크 (email/domain/lead)
        4. daily_cap에 맞춰 scheduled_at 분배
        5. SendJob bulk create
        
        **scheduled_at 분배 규칙:**
        - daily_cap개씩 하루 단위로 분배
        - 예: daily_cap=50, 타겟 150개 → 3일에 걸쳐 분배
        - start_at부터 시작하여 매일 같은 시각에 발송
        
        **스킵 사유:**
        - no_email: 이메일 없음
        - suppressed: 차단 리스트에 등재됨
        - already_scheduled: 이미 예약됨
        - not_pending: pending 상태 아님
        """,
        request=ScheduleJobsRequestSerializer,
        responses={
            200: ScheduleJobsResponseSerializer,
            400: {"description": "잘못된 요청 (타겟 미확정, 템플릿 없음 등)"}
        },
        examples=[
            OpenApiExample(
                '기본 예약',
                value={
                    "template_version_id": "550e8400-e29b-41d4-a716-446655440000",
                    "start_at": "2026-01-23T09:00:00+09:00",
                    "daily_cap": 50
                },
                request_only=True
            )
        ]
    )
    @action(detail=True, methods=['post'], url_path='schedule')
    def schedule_jobs(self, request, pk=None):
        """발송 잡 예약 생성"""
        campaign = self.get_object()
        
        # 요청 파라미터 파싱
        req_serializer = ScheduleJobsRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        
        template_version_id = req_serializer.validated_data['template_version_id']
        start_at = req_serializer.validated_data['start_at']
        daily_cap = req_serializer.validated_data['daily_cap']
        
        # 타겟 확정 여부 확인
        if not campaign.frozen_at:
            return self.error_response(
                message="타겟을 먼저 확정해주세요. (freeze-targets)",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # 템플릿 버전 확인
        try:
            template_version = TemplateVersion.objects.get(id=template_version_id)
        except TemplateVersion.DoesNotExist:
            return self.error_response(
                message="템플릿 버전을 찾을 수 없습니다.",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # 스킵 사유 집계
        skip_reasons = {
            'no_email': 0,
            'suppressed': 0,
            'already_scheduled': 0,
            'not_pending': 0
        }
        
        # pending 타겟만 선택
        targets = campaign.targets.select_related('lead').filter(status='pending')
        total_targets = targets.count()
        
        # 이메일 없는 타겟 제외
        targets_with_email = []
        for target in targets:
            if not target.lead.primary_email:
                skip_reasons['no_email'] += 1
                continue
            targets_with_email.append(target)
        
        # Suppression 체크
        suppressed_emails = set(
            Suppression.objects.filter(type='email').values_list('value', flat=True)
        )
        suppressed_domains = set(
            Suppression.objects.filter(type='domain').values_list('value', flat=True)
        )
        suppressed_lead_ids = set(
            Suppression.objects.filter(type='lead').values_list('value', flat=True)
        )
        
        # 이미 예약된 타겟 제외
        already_scheduled_target_ids = set(
            SendJob.objects.filter(
                campaign=campaign,
                status__in=['scheduled', 'processing']
            ).values_list('campaign_target_id', flat=True)
        )
        
        # 필터링된 타겟 리스트
        valid_targets = []
        for target in targets_with_email:
            # 이미 예약됨
            if target.id in already_scheduled_target_ids:
                skip_reasons['already_scheduled'] += 1
                continue
            
            # 이메일 차단
            if target.lead.primary_email in suppressed_emails:
                skip_reasons['suppressed'] += 1
                continue
            
            # 도메인 차단
            email_domain = target.lead.primary_email.split('@')[1] if '@' in target.lead.primary_email else ''
            if email_domain in suppressed_domains:
                skip_reasons['suppressed'] += 1
                continue
            
            # 리드 차단
            if str(target.lead.id) in suppressed_lead_ids:
                skip_reasons['suppressed'] += 1
                continue
            
            valid_targets.append(target)
        
        # SendJob 생성 (daily_cap에 맞춰 분배)
        jobs_to_create = []
        scheduled_dates = set()
        
        for idx, target in enumerate(valid_targets):
            # 날짜 계산 (daily_cap개씩 하루 단위)
            day_offset = idx // daily_cap
            scheduled_time = start_at + timedelta(days=day_offset)
            scheduled_dates.add(scheduled_time.date())
            
            jobs_to_create.append(
                SendJob(
                    campaign=campaign,
                    campaign_target=target,
                    lead=target.lead,
                    to_email=target.lead.primary_email,
                    template_version=template_version,
                    scheduled_at=scheduled_time,
                    status='scheduled'
                )
            )
        
        # Bulk create
        with transaction.atomic():
            SendJob.objects.bulk_create(jobs_to_create)
        
        return self.success_response(
            data={
                'total_targets': total_targets,
                'scheduled_count': len(jobs_to_create),
                'skipped_count': total_targets - len(jobs_to_create),
                'skip_reasons': skip_reasons,
                'scheduled_dates': sorted([d.isoformat() for d in scheduled_dates]),
                'message': f"{len(jobs_to_create)}개 발송 잡이 예약되었습니다."
            }
        )
    
    @extend_schema(
        summary="발송 잡 목록 조회",
        description="""
        캠페인의 발송 잡 목록을 조회합니다.
        
        **필터 옵션:**
        - `status`: 잡 상태 (scheduled, processing, sent, cancelled, failed)
        - `date_from`, `date_to`: 예약 시간 범위
        """,
        parameters=[
            OpenApiParameter(
                'status',
                OpenApiTypes.STR,
                description="잡 상태 필터",
                enum=['scheduled', 'processing', 'sent', 'cancelled', 'failed']
            ),
            OpenApiParameter(
                'date_from',
                OpenApiTypes.DATE,
                description="예약 시간 시작 (YYYY-MM-DD)"
            ),
            OpenApiParameter(
                'date_to',
                OpenApiTypes.DATE,
                description="예약 시간 종료 (YYYY-MM-DD)"
            )
        ],
        responses={200: SendJobListSerializer(many=True)}
    )
    @action(detail=True, methods=['get'], url_path='jobs')
    def jobs_list(self, request, pk=None):
        """발송 잡 목록 조회"""
        # pk로 직접 캠페인 조회 (get_object() 대신)
        try:
            campaign = Campaign.objects.get(pk=pk)
        except Campaign.DoesNotExist:
            return self.error_response(
                '캠페인을 찾을 수 없습니다.',
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        queryset = SendJob.objects.filter(campaign=campaign).select_related(
            'lead', 'template_version__template'
        )
        
        # status 필터
        job_status = request.query_params.get('status')
        if job_status:
            queryset = queryset.filter(status=job_status)
        
        # 날짜 범위 필터
        date_from = request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(scheduled_at__date__gte=date_from)
        
        date_to = request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(scheduled_at__date__lte=date_to)
        
        # 페이지네이션
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SendJobListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = SendJobListSerializer(queryset, many=True)
        return self.success_response(serializer.data)
    
    @extend_schema(
        summary="캠페인 이벤트 조회",
        description="캠페인에 속한 모든 이메일 이벤트 조회",
        parameters=[
            OpenApiParameter(name='event_type', type=str, description='이벤트 타입 필터'),
            OpenApiParameter(name='from_date', type=str, description='시작 날짜 (YYYY-MM-DD)'),
            OpenApiParameter(name='to_date', type=str, description='종료 날짜 (YYYY-MM-DD)'),
        ],
        responses={200: EmailEventDetailSerializer(many=True)}
    )
    @action(detail=True, methods=['get'], url_path='events')
    def get_events(self, request, pk=None):
        """캠페인 이벤트 조회"""
        campaign = self.get_object()
        
        # 캠페인에 속한 SendJob → EmailMessage → EmailEvent 조회
        events = EmailEvent.objects.filter(
            email_message__send_job__campaign=campaign
        ).select_related(
            'email_message',
            'email_message__send_job',
            'email_message__send_job__campaign'
        )
        
        # 이벤트 타입 필터
        event_type = request.query_params.get('event_type')
        if event_type:
            events = events.filter(event_type=event_type)
        
        # 날짜 범위 필터
        from_date = request.query_params.get('from_date')
        if from_date:
            events = events.filter(event_at__gte=from_date)
        
        to_date = request.query_params.get('to_date')
        if to_date:
            events = events.filter(event_at__lte=to_date)
        
        # 페이지네이션 적용
        page = self.paginate_queryset(events)
        if page is not None:
            serializer = EmailEventDetailSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = EmailEventDetailSerializer(events, many=True)
        return self.success_response(data=serializer.data)
    
    # ========== Analytics Actions ==========
    
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
            OpenApiParameter(name='from_date', type=OpenApiTypes.DATETIME, description='시작 날짜 (ISO 8601)'),
            OpenApiParameter(name='to_date', type=OpenApiTypes.DATETIME, description='종료 날짜 (ISO 8601)'),
        ],
    )
    @action(detail=True, methods=['get'], url_path='analytics/overview')
    def analytics_overview(self, request, pk=None):
        """캠페인 개요 통계"""
        from campaigns.serializers_analytics import OverviewAnalyticsSerializer
        
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
        
        # 고유 오픈/클릭
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
        responses={200: 'campaigns.serializers_analytics.TimeseriesAnalyticsSerializer'}
    )
    @action(detail=True, methods=['get'], url_path='analytics/timeseries')
    def analytics_timeseries(self, request, pk=None):
        """시계열 분석"""
        from campaigns.serializers_analytics import TimeseriesAnalyticsSerializer
        from django.db.models.functions import TruncHour, TruncDate
        
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
                # timestamp와 date 처리
                if isinstance(bucket, datetime.date) and not isinstance(bucket, datetime.datetime):
                    # TruncDate의 경우 date 객체 반환
                    timestamp = timezone.make_aware(datetime.datetime.combine(bucket, datetime.time.min))
                    date_value = bucket
                else:
                    # TruncHour의 경우 datetime 객체 반환
                    timestamp = bucket
                    date_value = bucket.date()
                
                data_points[bucket] = {
                    'timestamp': timestamp,
                    'date': date_value,
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
        responses={200: 'campaigns.serializers_analytics.TemplatePerformanceSerializer'}
    )
    @action(detail=True, methods=['get'], url_path='analytics/templates')
    def analytics_templates(self, request, pk=None):
        """템플릿별 성과 분석"""
        from campaigns.serializers_analytics import TemplatePerformanceSerializer
        
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
        responses={200: 'campaigns.serializers_analytics.BreakdownAnalyticsSerializer'}
    )
    @action(detail=True, methods=['get'], url_path='analytics/breakdown')
    def analytics_breakdown(self, request, pk=None):
        """분류별 분석"""
        from campaigns.serializers_analytics import BreakdownAnalyticsSerializer
        
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
        responses={200: 'campaigns.serializers_analytics.ResponseTimeAnalyticsSerializer'}
    )
    @action(detail=True, methods=['get'], url_path='analytics/response-time')
    def analytics_response_time(self, request, pk=None):
        """응답 시간 분석"""
        from campaigns.serializers_analytics import ResponseTimeAnalyticsSerializer
        
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


# ========== SendJob ViewSet ==========

class SendJobViewSet(BaseViewSet):
    """
    발송 잡 관리
    
    예약된 이메일 발송 작업을 조회, 수정, 취소, 재시도합니다.
    """
    queryset = SendJob.objects.select_related(
        'campaign', 'lead', 'template_version__template'
    ).all()
    serializer_class = SendJobSerializer
    ordering_fields = ['scheduled_at', 'created_at', 'status']
    ordering = ['scheduled_at']
    
    def get_serializer_class(self):
        """리스트 조회 시 경량 시리얼라이저 사용"""
        if self.action == 'list':
            return SendJobListSerializer
        return SendJobSerializer
    
    def get_queryset(self):
        """쿼리셋 필터링"""
        queryset = super().get_queryset()
        
        # status 필터
        job_status = self.request.query_params.get('status')
        if job_status:
            queryset = queryset.filter(status=job_status)
        
        # campaign 필터
        campaign_id = self.request.query_params.get('campaign_id')
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id)
        
        return queryset
    
    @extend_schema(
        summary="잡 재예약",
        description="""
        scheduled 상태의 잡 예약 시간을 변경합니다.
        
        **제약:**
        - scheduled 상태만 변경 가능
        - processing/sent/cancelled는 변경 불가
        """,
        request=RescheduleJobRequestSerializer,
        responses={200: SendJobSerializer}
    )
    @action(detail=True, methods=['patch'], url_path='reschedule')
    def reschedule(self, request, pk=None):
        """잡 재예약"""
        job = self.get_object()
        
        if job.status != 'scheduled':
            return self.error_response(
                message=f"scheduled 상태만 재예약 가능합니다. (현재: {job.status})",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        req_serializer = RescheduleJobRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        
        new_scheduled_at = req_serializer.validated_data['scheduled_at']
        
        job.scheduled_at = new_scheduled_at
        job.save(update_fields=['scheduled_at'])
        
        serializer = self.get_serializer(job)
        return self.success_response(
            data=serializer.data,
            message="예약 시간이 변경되었습니다."
        )
    
    @extend_schema(
        summary="잡 취소",
        description="""
        scheduled 또는 failed 상태의 잡을 취소합니다.
        
        **제약:**
        - scheduled, failed 상태만 취소 가능
        - processing, sent는 취소 불가
        """,
        request=CancelJobRequestSerializer,
        responses={200: SendJobSerializer}
    )
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_job(self, request, pk=None):
        """잡 취소"""
        job = self.get_object()
        
        if job.status not in ['scheduled', 'failed']:
            return self.error_response(
                message=f"scheduled 또는 failed 상태만 취소 가능합니다. (현재: {job.status})",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        req_serializer = CancelJobRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        
        reason = req_serializer.validated_data.get('reason', '')
        
        job.status = 'cancelled'
        if reason:
            job.last_error = f"[취소] {reason}"
        job.save(update_fields=['status', 'last_error'])
        
        serializer = self.get_serializer(job)
        return self.success_response(
            data=serializer.data,
            message="잡이 취소되었습니다."
        )
    
    @extend_schema(
        summary="잡 재시도",
        description="""
        failed 상태의 잡을 scheduled 상태로 되돌려 재시도합니다.
        
        **처리:**
        - status: failed → scheduled
        - attempt_count 증가
        - last_error 초기화
        - scheduled_at을 현재 시각 + 1시간으로 재설정
        """,
        responses={200: SendJobSerializer}
    )
    @action(detail=True, methods=['post'], url_path='retry')
    def retry_job(self, request, pk=None):
        """잡 재시도"""
        job = self.get_object()
        
        if job.status != 'failed':
            return self.error_response(
                message=f"failed 상태만 재시도 가능합니다. (현재: {job.status})",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # 재시도 설정
        job.status = 'scheduled'
        job.attempt_count += 1
        job.last_error = None
        job.locked_at = None
        job.scheduled_at = timezone.now() + timedelta(hours=1)
        job.save(update_fields=['status', 'attempt_count', 'last_error', 'locked_at', 'scheduled_at'])
        
        serializer = self.get_serializer(job)
        return self.success_response(
            data=serializer.data,
            message=f"잡이 재시도 예약되었습니다. (시도 횟수: {job.attempt_count})"
        )
    
    @extend_schema(
        summary="캠페인 이벤트 조회",
        description="""
        캠페인에 속한 모든 이메일의 이벤트를 조회합니다.
        
        **이벤트 타입:**
        - opened_pixel: 이메일 오픈 (최초 1회만 기록)
        - clicked: 링크 클릭 (중복 허용)
        - replied: 답장
        - bounced: 반송
        
        **필터:**
        - event_type: 이벤트 타입 필터
        - from_date: 시작 날짜 (YYYY-MM-DD)
        - to_date: 종료 날짜 (YYYY-MM-DD)
        """,
        parameters=[
            OpenApiParameter(name='event_type', type=str, description='이벤트 타입 필터 (opened_pixel, clicked, replied, bounced)'),
            OpenApiParameter(name='from_date', type=str, description='시작 날짜 (YYYY-MM-DD)'),
            OpenApiParameter(name='to_date', type=str, description='종료 날짜 (YYYY-MM-DD)'),
        ],
        responses={200: EmailEventDetailSerializer(many=True)}
    )
    @action(detail=True, methods=['get'], url_path='events')
    def get_events(self, request, pk=None):
        """캠페인 이벤트 조회"""
        campaign = self.get_object()
        
        # 캠페인에 속한 SendJob → EmailMessage → EmailEvent 조회
        events = EmailEvent.objects.filter(
            email_message__send_job__campaign=campaign
        ).select_related(
            'email_message',
            'email_message__send_job',
            'email_message__send_job__campaign'
        )
        
        # 이벤트 타입 필터
        event_type = request.query_params.get('event_type')
        if event_type:
            events = events.filter(event_type=event_type)
        
        # 날짜 범위 필터
        from_date = request.query_params.get('from_date')
        if from_date:
            events = events.filter(event_at__gte=from_date)
        
        to_date = request.query_params.get('to_date')
        if to_date:
            events = events.filter(event_at__lte=to_date)
        
        # 페이지네이션 적용
        page = self.paginate_queryset(events)
        if page is not None:
            serializer = EmailEventDetailSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = EmailEventDetailSerializer(events, many=True)
        return self.success_response(data=serializer.data)
