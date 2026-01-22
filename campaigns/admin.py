"""
Campaigns Admin
"""
from django.contrib import admin
from .models import (
    LeadSegment, Campaign, CampaignTarget,
    SendJob, EmailMessage, EmailEvent
)


@admin.register(LeadSegment)
class LeadSegmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']


class CampaignTargetInline(admin.TabularInline):
    model = CampaignTarget
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['lead']
    fields = ['lead', 'status', 'created_at']


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'frozen_target_count', 'daily_cap', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'frozen_at', 'frozen_target_count']
    raw_id_fields = ['segment']
    ordering = ['-created_at']
    inlines = [CampaignTargetInline]
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('name', 'segment', 'status')
        }),
        ('설정', {
            'fields': ('daily_cap', 'timezone')
        }),
        ('스냅샷 정보', {
            'fields': ('frozen_at', 'frozen_target_count'),
            'classes': ('collapse',)
        }),
        ('시스템', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CampaignTarget)
class CampaignTargetAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'lead', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['campaign__name', 'lead__channel_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['campaign', 'lead']
    ordering = ['-created_at']


@admin.register(SendJob)
class SendJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'campaign', 'to_email', 'status', 'scheduled_at', 'attempt_count']
    list_filter = ['status', 'scheduled_at', 'created_at']
    search_fields = ['to_email', 'campaign__name', 'lead__channel_name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'locked_at']
    raw_id_fields = ['campaign', 'campaign_target', 'lead', 'template_version']
    ordering = ['-scheduled_at']
    
    fieldsets = (
        ('발송 정보', {
            'fields': ('campaign', 'campaign_target', 'lead', 'to_email')
        }),
        ('템플릿', {
            'fields': ('template_version',)
        }),
        ('스케줄', {
            'fields': ('scheduled_at', 'status', 'locked_at')
        }),
        ('실행 정보', {
            'fields': ('attempt_count', 'last_error')
        }),
        ('시스템', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class EmailEventInline(admin.TabularInline):
    model = EmailEvent
    extra = 0
    readonly_fields = ['created_at']
    fields = ['event_type', 'event_at', 'created_at']


@admin.register(EmailMessage)
class EmailMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'to_email', 'send_status', 'sent_at', 'provider']
    list_filter = ['send_status', 'provider', 'failure_type', 'sent_at']
    search_fields = ['to_email', 'from_email', 'subject_final']
    readonly_fields = ['id', 'created_at', 'updated_at', 'body_hash']
    raw_id_fields = ['send_job']
    ordering = ['-sent_at']
    inlines = [EmailEventInline]
    
    fieldsets = (
        ('발송 정보', {
            'fields': ('send_job', 'provider', 'provider_message_id')
        }),
        ('이메일', {
            'fields': ('from_email', 'to_email')
        }),
        ('내용', {
            'fields': ('subject_final', 'body_final', 'body_hash')
        }),
        ('상태', {
            'fields': ('sent_at', 'send_status', 'failure_type')
        }),
        ('시스템', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EmailEvent)
class EmailEventAdmin(admin.ModelAdmin):
    list_display = ['email_message', 'event_type', 'event_at', 'created_at']
    list_filter = ['event_type', 'event_at', 'created_at']
    search_fields = ['email_message__to_email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['email_message']
    ordering = ['-event_at']
