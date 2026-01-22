"""
공통 ViewSet 기본 클래스
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from .pagination import StandardResultsSetPagination


class BaseViewSet(viewsets.ModelViewSet):
    """
    기본 ViewSet
    - 표준 페이지네이션 적용
    - 일관된 응답 형식
    """
    pagination_class = StandardResultsSetPagination
    
    def success_response(self, data=None, message=None, status_code=status.HTTP_200_OK):
        """성공 응답"""
        response_data = {'success': True}
        if message:
            response_data['message'] = message
        if data is not None:
            response_data['data'] = data
        return Response(response_data, status=status_code)
    
    def error_response(self, message, status_code=status.HTTP_400_BAD_REQUEST, errors=None):
        """에러 응답"""
        response_data = {
            'success': False,
            'error': {
                'code': 'error',
                'message': message
            }
        }
        if errors:
            response_data['error']['details'] = errors
        return Response(response_data, status=status_code)
    
    def list(self, request, *args, **kwargs):
        """리스트 조회 - 페이지네이션 적용"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'count': len(serializer.data),
            'results': serializer.data
        })
    
    def create(self, request, *args, **kwargs):
        """생성"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED, headers=headers)
    
    def retrieve(self, request, *args, **kwargs):
        """상세 조회"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def update(self, request, *args, **kwargs):
        """수정"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def destroy(self, request, *args, **kwargs):
        """삭제"""
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'success': True,
            'message': 'Successfully deleted'
        }, status=status.HTTP_200_OK)
