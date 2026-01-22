"""
헬스 체크 및 유틸리티 뷰
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import connection
from datetime import datetime


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    헬스 체크 엔드포인트
    서비스 상태 및 DB 연결 확인
    """
    try:
        # DB 연결 확인
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        db_status = 'healthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'
    
    return Response({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'service': 'Cold Mail API',
        'version': '1.0.0',
        'database': db_status
    })
