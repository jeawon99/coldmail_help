"""
공통 Serializer 기본 클래스
"""
from rest_framework import serializers


class BaseSerializer(serializers.ModelSerializer):
    """
    기본 Serializer
    - 공통 필드 처리
    """
    class Meta:
        abstract = True
    
    def to_representation(self, instance):
        """
        모델 인스턴스를 dict로 변환
        - created_at, updated_at은 ISO 8601 형식
        """
        representation = super().to_representation(instance)
        return representation


class TimestampedSerializer(serializers.ModelSerializer):
    """
    타임스탬프 필드가 있는 Serializer
    """
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    class Meta:
        abstract = True
