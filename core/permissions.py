"""
공통 권한 클래스
"""
from rest_framework import permissions


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    인증된 사용자는 모든 작업 가능
    비인증 사용자는 읽기만 가능
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    객체의 소유자만 수정/삭제 가능
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 객체에 user 필드가 있는 경우
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # 객체에 created_by 필드가 있는 경우
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        
        return False
