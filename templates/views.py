"""
Templates app views
"""
from jinja2 import Template as Jinja2Template, TemplateSyntaxError, UndefinedError
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema

from core.viewsets import BaseViewSet
from crm.models import Lead
from .models import Template, TemplateVersion
from .serializers import (
    TemplateSerializer, TemplateListSerializer,
    TemplateVersionSerializer, TemplateVersionListSerializer,
    TemplateVersionCreateSerializer, RenderPreviewSerializer
)


class TemplateViewSet(BaseViewSet):
    """
    이메일 템플릿 관리
    
    Jinja2 템플릿 엔진을 사용하여 개인화된 이메일을 생성합니다.
    템플릿 버전 관리를 지원하며, render-preview로 실제 렌더링 결과를 미리 확인할 수 있습니다.
    
    **템플릿 변수:**
    - `{{ lead.channel_name }}`: 채널명
    - `{{ lead.subscriber_count }}`: 구독자 수
    - `{{ lead.primary_email }}`: 이메일
    - `{{ lead.keywords_raw }}`: 키워드
    - `{{ custom_var }}`: 사용자 정의 변수 (context로 전달)
    
    **Jinja2 제어문:**
    - `{% if condition %}...{% endif %}`
    - `{% for item in items %}...{% endfor %}`
    - 필터: `{{ text|upper }}`, `{{ number|round(2) }}`
    """
    
    queryset = Template.objects.prefetch_related('versions').all()
    serializer_class = TemplateSerializer
    search_fields = ['name']
    ordering_fields = ['name', 'created_at', 'updated_at', 'purpose']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """리스트 조회 시 경량 시리얼라이저 사용"""
        if self.action == 'list':
            return TemplateListSerializer
        return TemplateSerializer
    
    def get_queryset(self):
        """쿼리셋 필터링"""
        queryset = super().get_queryset()
        
        # is_active 필터
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            is_active_bool = is_active.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_active=is_active_bool)
        
        # purpose 필터
        purpose = self.request.query_params.get('purpose')
        if purpose:
            queryset = queryset.filter(purpose=purpose)
        
        return queryset
    
    @extend_schema(
        summary="템플릿에 새 버전 추가",
        description="템플릿에 새로운 버전을 생성합니다. 버전 번호는 자동으로 증가합니다.",
        request=TemplateVersionCreateSerializer,
        responses={201: TemplateVersionSerializer}
    )
    @action(detail=True, methods=['post'], url_path='versions')
    def create_version(self, request, pk=None):
        """템플릿에 새 버전 추가"""
        template = self.get_object()
        
        if not template.is_active:
            return self.error_response(
                message="비활성화된 템플릿에는 버전을 추가할 수 없습니다.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = TemplateVersionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 최신 버전 번호 조회
        latest_version = template.versions.order_by('-version').first()
        next_version = (latest_version.version + 1) if latest_version else 1
        
        # 새 버전 생성
        version_data = serializer.validated_data
        new_version = TemplateVersion.objects.create(
            template=template,
            version=next_version,
            **version_data
        )
        
        result_serializer = TemplateVersionSerializer(new_version)
        return self.success_response(
            data=result_serializer.data,
            message=f"버전 {next_version}이 생성되었습니다.",
            status_code=status.HTTP_201_CREATED
        )


class TemplateVersionViewSet(BaseViewSet):
    """템플릿 버전 ViewSet"""
    
    queryset = TemplateVersion.objects.select_related('template').all()
    serializer_class = TemplateVersionSerializer
    ordering_fields = ['version', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """리스트 조회 시 경량 시리얼라이저 사용"""
        if self.action == 'list':
            return TemplateVersionListSerializer
        return TemplateVersionSerializer
    
    def get_queryset(self):
        """쿼리셋 필터링"""
        queryset = super().get_queryset()
        
        # template_id 필터
        template_id = self.request.query_params.get('template_id')
        if template_id:
            queryset = queryset.filter(template_id=template_id)
        
        # format 필터
        format_type = self.request.query_params.get('format')
        if format_type:
            queryset = queryset.filter(format=format_type)
        
        return queryset
    
    @extend_schema(
        summary="템플릿 렌더링 미리보기",
        description="""
        실제 리드 데이터 또는 샘플 데이터로 Jinja2 템플릿을 렌더링하여 미리보기를 제공합니다.
        
        **사용 방법:**
        1. `lead_id` 지정: 실제 리드 데이터로 렌더링
        2. `sample_data` 지정: 커스텀 샘플 데이터로 렌더링
        
        **사용 가능한 변수:**
        - `{{ channel_name }}`: 채널명
        - `{{ channel_url }}`: 채널 URL
        - `{{ subscriber_count }}`: 구독자 수
        - `{{ platform }}`: 플랫폼 (youtube, instagram 등)
        - `{{ primary_email }}`: 이메일
        - `{{ tags }}`: 태그 리스트
        - `{{ keywords_raw }}`: 키워드
        
        **Jinja2 기능:**
        - 조건문: `{% if subscriber_count > 100000 %}인기 유튜버{% endif %}`
        - 반복문: `{% for tag in tags %}{{ tag }}{% endfor %}`
        - 필터: `{{ channel_name|upper }}`
        """,
        request=RenderPreviewSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'subject_final': {'type': 'string', 'example': '안녕하세요, 게임 챌린지님!'},
                            'body_final': {'type': 'string', 'example': '구독자 150,000명의 인기 유튜버이시네요...'},
                            'variables_used': {
                                'type': 'array',
                                'items': {'type': 'string'},
                                'example': ['channel_name', 'subscriber_count']
                            },
                            'context': {
                                'type': 'object',
                                'example': {
                                    'channel_name': '게임 챌린지',
                                    'subscriber_count': 150000
                                }
                            }
                        }
                    }
                }
            }
        }
    )
    @action(detail=True, methods=['post'], url_path='render-preview')
    def render_preview(self, request, pk=None):
        """템플릿 렌더링 미리보기"""
        template_version = self.get_object()
        
        serializer = RenderPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 컨텍스트 데이터 준비
        context = {}
        lead = None
        
        if serializer.validated_data.get('lead_id'):
            # 실제 리드 데이터 사용
            try:
                lead = Lead.objects.prefetch_related('tags').get(
                    id=serializer.validated_data['lead_id']
                )
                context = self._lead_to_context(lead)
            except Lead.DoesNotExist:
                return self.error_response(
                    message="리드를 찾을 수 없습니다.",
                    status_code=status.HTTP_404_NOT_FOUND
                )
        else:
            # 샘플 데이터 사용
            context = serializer.validated_data.get('sample_data', {})
        
        # 기본값 설정 (누락된 변수 대비)
        default_context = {
            'channel_name': '채널명',
            'subscriber_count': 0,
            'platform': 'youtube',
            'primary_email': 'example@email.com',
            'tags': [],
            'keywords_raw': '',
        }
        default_context.update(context)
        context = default_context
        
        # 템플릿 렌더링
        try:
            subject_final = self._render_template(
                template_version.subject_tpl,
                context
            )
            body_final = self._render_template(
                template_version.body_tpl,
                context
            )
            
            # 사용된 변수 추출
            variables_used = self._extract_variables(
                template_version.subject_tpl,
                template_version.body_tpl
            )
            
            return self.success_response(
                data={
                    'subject_final': subject_final,
                    'body_final': body_final,
                    'variables_used': variables_used,
                    'context': context
                }
            )
        
        except TemplateSyntaxError as e:
            return self.error_response(
                message=f"템플릿 문법 오류: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST,
                errors={'syntax_error': str(e)}
            )
        except UndefinedError as e:
            return self.error_response(
                message=f"정의되지 않은 변수: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST,
                errors={'undefined_variable': str(e)}
            )
        except Exception as e:
            return self.error_response(
                message=f"렌더링 오류: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                errors={'render_error': str(e)}
            )
    
    def _lead_to_context(self, lead):
        """Lead 객체를 템플릿 컨텍스트로 변환"""
        return {
            'channel_name': lead.channel_name,
            'channel_url': lead.channel_url,
            'subscriber_count': lead.subscriber_count or 0,
            'platform': lead.platform,
            'primary_email': lead.primary_email or '',
            'tags': [tag.name for tag in lead.tags.all()],
            'keywords_raw': lead.keywords_raw or '',
            'status': lead.status,
        }
    
    def _render_template(self, template_string, context):
        """Jinja2 템플릿 렌더링"""
        template = Jinja2Template(template_string)
        return template.render(**context)
    
    def _extract_variables(self, *template_strings):
        """템플릿에서 사용된 변수명 추출"""
        import re
        variables = set()
        
        for template_string in template_strings:
            # Jinja2 변수 패턴: {{ variable }} 또는 {% ... variable ... %}
            matches = re.findall(r'\{\{\\s*([a-zA-Z_][a-zA-Z0-9_.]*)\\s*\}\}', template_string)
            variables.update(matches)
            
            # for 루프 등에서 사용되는 변수
            matches = re.findall(r'\{%\\s*for\\s+[a-zA-Z_][a-zA-Z0-9_]*\\s+in\\s+([a-zA-Z_][a-zA-Z0-9_.]*)\\s*%\}', template_string)
            variables.update(matches)
        
        return sorted(list(variables))

