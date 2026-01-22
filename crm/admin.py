"""
CRM Admin
"""
from django.contrib import admin
from .models import Lead, Tag, LeadTag, Suppression


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['channel_name', 'platform', 'status', 'subscriber_count', 'primary_email', 'created_at']
    list_filter = ['platform', 'status', 'created_at']
    search_fields = ['channel_name', 'channel_url', 'primary_email', 'keywords_raw']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('platform', 'channel_name', 'channel_url')
        }),
        ('상세 정보', {
            'fields': ('subscriber_count', 'primary_email', 'status')
        }),
        ('키워드', {
            'fields': ('keywords_raw', 'keywords_norm')
        }),
        ('메모', {
            'fields': ('notes',)
        }),
        ('시스템', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['name']


@admin.register(LeadTag)
class LeadTagAdmin(admin.ModelAdmin):
    list_display = ['lead', 'tag', 'created_at']
    list_filter = ['tag', 'created_at']
    search_fields = ['lead__channel_name', 'tag__name']
    raw_id_fields = ['lead', 'tag']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(Suppression)
class SuppressionAdmin(admin.ModelAdmin):
    list_display = ['type', 'value', 'reason', 'created_at']
    list_filter = ['type', 'reason', 'created_at']
    search_fields = ['value']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']
