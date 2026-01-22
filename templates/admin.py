"""
Templates Admin
"""
from django.contrib import admin
from .models import Template, TemplateVersion


class TemplateVersionInline(admin.TabularInline):
    model = TemplateVersion
    extra = 0
    readonly_fields = ['id', 'created_at', 'subject_length', 'body_length']
    fields = ['version', 'format', 'cta_type', 'personalization_level', 'created_at']


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'purpose', 'is_active', 'created_at']
    list_filter = ['purpose', 'is_active', 'created_at']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']
    inlines = [TemplateVersionInline]


@admin.register(TemplateVersion)
class TemplateVersionAdmin(admin.ModelAdmin):
    list_display = ['template', 'version', 'format', 'subject_length', 'body_length', 'cta_type', 'created_at']
    list_filter = ['format', 'cta_type', 'created_at']
    search_fields = ['template__name', 'subject_tpl', 'body_tpl']
    readonly_fields = ['id', 'created_at', 'updated_at', 'subject_length', 'body_length']
    raw_id_fields = ['template']
    ordering = ['-created_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('template', 'version', 'format')
        }),
        ('템플릿 내용', {
            'fields': ('subject_tpl', 'body_tpl')
        }),
        ('분석 메타', {
            'fields': ('subject_length', 'body_length', 'cta_type', 'personalization_level')
        }),
        ('시스템', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
