"""
URL configuration for coldmail_project project.
"""

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from core.views import health_check
from campaigns.tracking_views import OpenPixelView, ClickTrackingView

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # API v1
    path("api/v1/", include([
        # Health check
        path("health/", health_check, name="health-check"),
        
        # Authentication
        path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
        path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
        
        # CRM (Leads, Tags, Suppressions)
        path("", include("crm.urls")),
        
        # Templates
        path("", include("templates.urls")),
        
        # Campaigns (Segments)
        path("", include("campaigns.urls")),
        
        # Tracking endpoints (트래킹 엔드포인트 - 최상위 레벨)
        path("t/open/<uuid:message_id>.png", OpenPixelView.as_view(), name="tracking-open"),
        path("t/click/<uuid:message_id>", ClickTrackingView.as_view(), name="tracking-click"),
        
        # Apps (추후 구현)
        # path("analytics/", include("analytics.urls")),
        
        # Legacy email API (임시)
        path("emails/", include("api.urls")),
    ])),
    
    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
