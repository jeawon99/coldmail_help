"""
CRM app URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LeadViewSet, TagViewSet, SuppressionViewSet

router = DefaultRouter()
router.register(r'leads', LeadViewSet, basename='lead')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'suppressions', SuppressionViewSet, basename='suppression')

urlpatterns = [
    path('', include(router.urls)),
]
