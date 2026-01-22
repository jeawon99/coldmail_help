"""
공통 페이지네이션 클래스
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    """표준 페이지네이션"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'data': {
                'count': self.page.paginator.count,
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'page': self.page.number,
                'page_size': self.page_size,
                'total_pages': self.page.paginator.num_pages,
                'results': data
            }
        })
