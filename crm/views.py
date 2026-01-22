"""
CRM app views
"""
import csv
import json
from io import TextIOWrapper

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiParameter

from core.viewsets import BaseViewSet
from .models import Lead, Tag, LeadTag, Suppression
from .serializers import (
    LeadSerializer, LeadListSerializer, TagSerializer,
    SuppressionSerializer, LeadImportSerializer
)
from .filters import LeadFilter, SuppressionFilter


class LeadViewSet(BaseViewSet):
    """
    리드(유튜버) 관리
    
    리드는 콜드메일 타겟이 되는 유튜버 정보를 관리합니다.
    채널 정보, 이메일, 태그, 상태 등을 CRUD하고 CSV/JSON 일괄 등록을 지원합니다.
    """
    
    queryset = Lead.objects.prefetch_related('tags').all()
    serializer_class = LeadSerializer
    filterset_class = LeadFilter
    search_fields = ['channel_name', 'channel_url', 'primary_email', 'keywords_raw']
    ordering_fields = ['created_at', 'updated_at', 'subscriber_count', 'channel_name']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """리스트 조회 시 경량 시리얼라이저 사용"""
        if self.action == 'list':
            return LeadListSerializer
        return LeadSerializer
    
    @extend_schema(
        summary="리드에 태그 추가",
        description="리드에 하나 이상의 태그를 추가합니다.",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'tag_ids': {
                        'type': 'array',
                        'items': {'type': 'string', 'format': 'uuid'},
                        'description': '추가할 태그 ID 리스트'
                    }
                },
                'required': ['tag_ids']
            }
        },
        responses={200: LeadSerializer}
    )
    @action(detail=True, methods=['post'], url_path='tags')
    def add_tags(self, request, pk=None):
        """리드에 태그 추가"""
        lead = self.get_object()
        tag_ids = request.data.get('tag_ids', [])
        
        if not tag_ids:
            return self.error_response(
                message="tag_ids가 필요합니다.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        tags = Tag.objects.filter(id__in=tag_ids)
        if len(tags) != len(tag_ids):
            return self.error_response(
                message="일부 태그를 찾을 수 없습니다.",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        lead.tags.add(*tags)
        serializer = self.get_serializer(lead)
        
        return self.success_response(
            data=serializer.data,
            message=f"{len(tags)}개의 태그가 추가되었습니다."
        )
    
    @extend_schema(
        summary="리드에서 태그 제거",
        description="리드에서 특정 태그를 제거합니다.",
        responses={200: LeadSerializer}
    )
    @action(detail=True, methods=['delete'], url_path='tags/(?P<tag_id>[^/.]+)')
    def remove_tag(self, request, pk=None, tag_id=None):
        """리드에서 태그 제거"""
        lead = self.get_object()
        
        try:
            tag = Tag.objects.get(id=tag_id)
        except Tag.DoesNotExist:
            return self.error_response(
                message="태그를 찾을 수 없습니다.",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        lead.tags.remove(tag)
        serializer = self.get_serializer(lead)
        
        return self.success_response(
            data=serializer.data,
            message="태그가 제거되었습니다."
        )
    
    @extend_schema(
        summary="리드 일괄 등록",
        description="CSV 또는 JSON 파일로 리드를 일괄 등록합니다. channel_url 기준으로 중복 처리(upsert)됩니다.",
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {'type': 'string', 'format': 'binary'},
                    'format': {'type': 'string', 'enum': ['csv', 'json'], 'default': 'csv'},
                    'upsert': {'type': 'boolean', 'default': True}
                },
                'required': ['file']
            }
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'total': {'type': 'integer'},
                            'created': {'type': 'integer'},
                            'updated': {'type': 'integer'},
                            'skipped': {'type': 'integer'},
                            'failed': {'type': 'integer'},
                            'errors': {'type': 'array', 'items': {'type': 'object'}}
                        }
                    }
                }
            }
        }
    )
    @action(
        detail=False,
        methods=['post'],
        url_path='import',
        parser_classes=[MultiPartParser, FormParser]
    )
    def import_leads(self, request):
        """리드 일괄 등록 (CSV/JSON)"""
        serializer = LeadImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        file_obj = serializer.validated_data['file']
        file_format = serializer.validated_data['format']
        upsert = serializer.validated_data['upsert']
        
        result = {
            'total': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            if file_format == 'csv':
                result = self._import_csv(file_obj, upsert)
            else:  # json
                result = self._import_json(file_obj, upsert)
            
            return self.success_response(
                data=result,
                message=f"총 {result['total']}건 처리: 생성 {result['created']}, "
                        f"업데이트 {result['updated']}, 실패 {result['failed']}"
            )
        
        except Exception as e:
            return self.error_response(
                message=f"파일 처리 중 오류가 발생했습니다: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST
            )
    
    def _import_csv(self, file_obj, upsert):
        """CSV 파일 import"""
        result = {
            'total': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'failed': 0,
            'errors': []
        }
        
        text_file = TextIOWrapper(file_obj, encoding='utf-8')
        reader = csv.DictReader(text_file)
        
        for row_num, row in enumerate(reader, start=2):  # 2부터 시작 (헤더 제외)
            result['total'] += 1
            
            try:
                # 필수 필드 검증
                if not row.get('channel_url'):
                    result['failed'] += 1
                    result['errors'].append({
                        'row': row_num,
                        'error': 'channel_url은 필수입니다.'
                    })
                    continue
                
                # 데이터 준비
                data = {
                    'platform': row.get('platform', 'youtube'),
                    'channel_name': row.get('channel_name', ''),
                    'channel_url': row['channel_url'],
                    'subscriber_count': int(row['subscriber_count']) if row.get('subscriber_count') else None,
                    'primary_email': row.get('primary_email') or None,
                    'keywords_raw': row.get('keywords_raw') or None,
                    'status': row.get('status', 'new'),
                    'notes': row.get('notes') or None,
                }
                
                # Upsert 처리
                lead, created = self._upsert_lead(data, upsert)
                
                if created:
                    result['created'] += 1
                elif lead:
                    result['updated'] += 1
                else:
                    result['skipped'] += 1
            
            except Exception as e:
                result['failed'] += 1
                result['errors'].append({
                    'row': row_num,
                    'error': str(e)
                })
        
        return result
    
    def _import_json(self, file_obj, upsert):
        """JSON 파일 import"""
        result = {
            'total': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            data_list = json.load(file_obj)
            
            if not isinstance(data_list, list):
                raise ValueError("JSON은 객체 배열이어야 합니다.")
            
            for idx, item in enumerate(data_list):
                result['total'] += 1
                
                try:
                    if not item.get('channel_url'):
                        result['failed'] += 1
                        result['errors'].append({
                            'index': idx,
                            'error': 'channel_url은 필수입니다.'
                        })
                        continue
                    
                    # Upsert 처리
                    lead, created = self._upsert_lead(item, upsert)
                    
                    if created:
                        result['created'] += 1
                    elif lead:
                        result['updated'] += 1
                    else:
                        result['skipped'] += 1
                
                except Exception as e:
                    result['failed'] += 1
                    result['errors'].append({
                        'index': idx,
                        'error': str(e)
                    })
        
        except json.JSONDecodeError as e:
            result['failed'] = 1
            result['errors'].append({
                'error': f'JSON 파싱 오류: {str(e)}'
            })
        
        return result
    
    @transaction.atomic
    def _upsert_lead(self, data, upsert):
        """리드 생성 또는 업데이트"""
        platform = data.get('platform', 'youtube')
        channel_url = data['channel_url']
        
        # 기존 리드 검색
        existing_lead = Lead.objects.filter(
            platform=platform,
            channel_url=channel_url
        ).first()
        
        if existing_lead:
            if upsert:
                # 업데이트
                for key, value in data.items():
                    if key not in ['platform', 'channel_url']:  # unique 키는 변경 안 함
                        setattr(existing_lead, key, value)
                existing_lead.save()
                return existing_lead, False
            else:
                # 스킵
                return None, False
        else:
            # 생성
            lead = Lead.objects.create(**data)
            return lead, True


class TagViewSet(BaseViewSet):
    """태그 ViewSet"""
    
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class SuppressionViewSet(BaseViewSet):
    """차단/수신거부 ViewSet"""
    
    queryset = Suppression.objects.all()
    serializer_class = SuppressionSerializer
    filterset_class = SuppressionFilter
    search_fields = ['value']
    ordering_fields = ['created_at', 'type', 'reason']
    ordering = ['-created_at']
