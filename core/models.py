"""
공통 모델 기본 클래스
"""
import uuid
from django.db import models


class UUIDModel(models.Model):
    """UUID를 PK로 사용하는 모델"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    class Meta:
        abstract = True


class TimestampedModel(models.Model):
    """타임스탬프 필드를 가진 모델"""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
        ordering = ['-created_at']


class BaseModel(UUIDModel, TimestampedModel):
    """
    기본 모델 (UUID + Timestamp)
    대부분의 모델이 상속받아 사용
    """
    class Meta:
        abstract = True
