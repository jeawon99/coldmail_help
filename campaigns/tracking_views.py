"""
이메일 트래킹 엔드포인트 (오픈 픽셀, 클릭)
"""
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import timezone
from django.views import View
from django.shortcuts import get_object_or_404
from .models import EmailMessage, EmailEvent
import base64
import logging

logger = logging.getLogger(__name__)

# 1x1 투명 PNG (base64 인코딩)
TRACKING_PIXEL = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='
)


class OpenPixelView(View):
    """
    오픈 픽셀 트래킹 (GET /t/open/{message_id}.png)
    
    이메일에 삽입되는 1x1 투명 픽셀 이미지.
    이메일이 열릴 때 브라우저가 이 이미지를 로드하면서 오픈 이벤트를 기록.
    """
    
    def get(self, request, message_id):
        """
        오픈 이벤트 기록 후 1x1 투명 PNG 반환
        
        중복 방지: 같은 메시지의 opened_pixel 이벤트는 최초 1회만 기록
        """
        try:
            # EmailMessage 조회
            email_message = get_object_or_404(EmailMessage, id=message_id)
            
            # 이미 opened_pixel 이벤트가 있는지 확인 (중복 방지)
            existing_open = EmailEvent.objects.filter(
                email_message=email_message,
                event_type='opened_pixel'
            ).exists()
            
            if not existing_open:
                # 메타데이터 수집
                meta = {
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'ip_address': self._get_client_ip(request),
                    'referer': request.META.get('HTTP_REFERER', ''),
                }
                
                # 오픈 이벤트 기록
                EmailEvent.objects.create(
                    email_message=email_message,
                    event_type='opened_pixel',
                    event_at=timezone.now(),
                    meta=meta
                )
                
                logger.info(f"Open tracked: message={message_id}, ip={meta['ip_address']}")
            else:
                logger.debug(f"Duplicate open ignored: message={message_id}")
        
        except Exception as e:
            logger.error(f"Open tracking error for message {message_id}: {e}")
        
        # 항상 1x1 투명 PNG 반환 (에러가 있어도)
        return HttpResponse(TRACKING_PIXEL, content_type='image/png')
    
    def _get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip


class ClickTrackingView(View):
    """
    클릭 트래킹 (GET /t/click/{message_id}?u=...)
    
    이메일 본문의 링크를 이 엔드포인트로 변경.
    클릭 이벤트 기록 후 원본 URL로 리다이렉트.
    """
    
    def get(self, request, message_id):
        """
        클릭 이벤트 기록 후 원본 URL로 리다이렉트
        
        중복 허용: 같은 링크를 여러 번 클릭하면 모두 기록
        """
        # 원본 URL 파라미터
        target_url = request.GET.get('u', '')
        
        if not target_url:
            return HttpResponse("Missing target URL", status=400)
        
        try:
            # EmailMessage 조회
            email_message = get_object_or_404(EmailMessage, id=message_id)
            
            # 메타데이터 수집
            meta = {
                'clicked_url': target_url,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'ip_address': self._get_client_ip(request),
                'referer': request.META.get('HTTP_REFERER', ''),
            }
            
            # 클릭 이벤트 기록 (중복 허용)
            EmailEvent.objects.create(
                email_message=email_message,
                event_type='clicked',
                event_at=timezone.now(),
                meta=meta
            )
            
            logger.info(f"Click tracked: message={message_id}, url={target_url}")
        
        except Exception as e:
            logger.error(f"Click tracking error for message {message_id}: {e}")
        
        # 원본 URL로 리다이렉트 (에러가 있어도 리다이렉트)
        return HttpResponseRedirect(target_url)
    
    def _get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
