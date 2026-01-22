"""
공통 예외 핸들러
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404


def custom_exception_handler(exc, context):
    """
    DRF 커스텀 예외 핸들러
    일관된 에러 응답 형식 제공
    """
    # DRF 기본 핸들러 호출
    response = exception_handler(exc, context)
    
    # DRF가 처리하지 못한 예외 처리
    if response is None:
        if isinstance(exc, DjangoValidationError):
            response = Response(
                {
                    'success': False,
                    'error': {
                        'code': 'validation_error',
                        'message': 'Validation error',
                        'details': exc.message_dict if hasattr(exc, 'message_dict') else str(exc)
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        elif isinstance(exc, Http404):
            response = Response(
                {
                    'success': False,
                    'error': {
                        'code': 'not_found',
                        'message': 'Resource not found'
                    }
                },
                status=status.HTTP_404_NOT_FOUND
            )
        else:
            # 기타 예외
            response = Response(
                {
                    'success': False,
                    'error': {
                        'code': 'internal_server_error',
                        'message': str(exc)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # DRF 응답을 통일된 형식으로 변환
    if response is not None:
        custom_response_data = {
            'success': False,
            'error': {
                'code': getattr(exc, 'default_code', 'error'),
                'message': getattr(exc, 'detail', str(exc)) if hasattr(exc, 'detail') else str(exc),
            }
        }
        
        # detail이 dict인 경우 (validation errors)
        if hasattr(exc, 'detail') and isinstance(exc.detail, dict):
            custom_response_data['error']['details'] = exc.detail
        
        response.data = custom_response_data
    
    return response
