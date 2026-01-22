from django.urls import path
from .views import SendEmailAPIView, ReceiveEmailAPIView

urlpatterns = [
    path('send-email/', SendEmailAPIView.as_view(), name='send-email'),
    path('emails/', ReceiveEmailAPIView.as_view(), name='receive-emails'),
]
