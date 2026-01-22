"""
Templates app URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TemplateViewSet, TemplateVersionViewSet

router = DefaultRouter()
router.register(r'templates', TemplateViewSet, basename='template')
router.register(r'template-versions', TemplateVersionViewSet, basename='template-version')

urlpatterns = [
    path('', include(router.urls)),
]
