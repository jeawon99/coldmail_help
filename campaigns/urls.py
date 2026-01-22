"""Campaigns URL Configuration"""
from rest_framework.routers import DefaultRouter
from campaigns.views import LeadSegmentViewSet, CampaignViewSet, SendJobViewSet
from campaigns.views_messages import EmailMessageViewSet

router = DefaultRouter()
router.register(r'segments', LeadSegmentViewSet, basename='segment')
router.register(r'campaigns', CampaignViewSet, basename='campaign')
router.register(r'jobs', SendJobViewSet, basename='sendjob')
router.register(r'messages', EmailMessageViewSet, basename='message')

urlpatterns = router.urls
