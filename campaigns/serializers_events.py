"""
이벤트 관련 Serializers
"""
from rest_framework import serializers
from .models import EmailEvent, EmailMessage


class EmailEventSerializer(serializers.ModelSerializer):
    """EmailEvent 시리얼라이저"""
    
    class Meta:
        model = EmailEvent
        fields = [
            'id',
            'email_message',
            'event_type',
            'event_at',
            'meta',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class EmailEventDetailSerializer(serializers.ModelSerializer):
    """EmailEvent 상세 시리얼라이저 (메시지 정보 포함)"""
    email_to = serializers.CharField(source='email_message.to_email', read_only=True)
    campaign_id = serializers.UUIDField(source='email_message.send_job.campaign.id', read_only=True)
    campaign_name = serializers.CharField(source='email_message.send_job.campaign.name', read_only=True)
    
    class Meta:
        model = EmailEvent
        fields = [
            'id',
            'email_message',
            'email_to',
            'campaign_id',
            'campaign_name',
            'event_type',
            'event_at',
            'meta',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
