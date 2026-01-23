"""
Campaigns Celery Tasks
이메일 발송 워커 태스크
"""
import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.core.mail import EmailMessage
from django.conf import settings
from jinja2 import Template
import requests

from campaigns.models import SendJob, EmailMessage, EmailEvent

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_single_email_task(self, send_job_id):
    """
    단일 이메일 발송 태스크
    
    Args:
        send_job_id: SendJob의 ID
    
    Returns:
        dict: 발송 결과
    """
    try:
        # SendJob 조회 및 락 획득
        with transaction.atomic():
            send_job = SendJob.objects.select_for_update().get(
                id=send_job_id,
                status='scheduled'
            )
            
            # 중복 발송 방지: locked_at 확인
            if send_job.locked_at is not None:
                logger.warning(f"SendJob {send_job_id} is already locked")
                return {'status': 'skipped', 'reason': 'already_locked'}
            
            # 락 설정
            send_job.status = 'processing'
            send_job.locked_at = timezone.now()
            send_job.save(update_fields=['status', 'locked_at'])
        
        # 템플릿 렌더링
        try:
            subject = render_template(
                send_job.template_version.subject_tpl,
                send_job.lead
            )
            body = render_template(
                send_job.template_version.body_tpl,
                send_job.lead
            )
        except Exception as e:
            logger.error(f"Template rendering failed for SendJob {send_job_id}: {e}")
            mark_job_failed(send_job, f"템플릿 렌더링 실패: {str(e)}")
            return {'status': 'failed', 'reason': 'template_error', 'error': str(e)}
        
        # 이메일 발송
        try:
            # EmailMessage 객체 생성
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=settings.EMAIL_HOST_USER,
                to=[send_job.to_email],
            )
            
            # HTML 포맷 설정
            if send_job.template_version.format == 'html':
                email.content_subtype = "html"
            
            # 첨부파일 처리
            if send_job.template_version.attachment_url:
                try:
                    response = requests.get(
                        send_job.template_version.attachment_url,
                        timeout=10
                    )
                    response.raise_for_status()
                    
                    attachment_name = send_job.template_version.attachment_name or 'attachment.pdf'
                    email.attach(
                        filename=attachment_name,
                        content=response.content,
                        mimetype=response.headers.get('content-type', 'application/octet-stream')
                    )
                    logger.info(f"Attachment added: {attachment_name}")
                except Exception as att_error:
                    logger.warning(f"Failed to attach file for SendJob {send_job_id}: {att_error}")
                    # 첨부파일 실패해도 이메일은 발송
            
            # 발송
            email.send(fail_silently=False)
            
            # 발송 성공: EmailMessage 생성, SendJob 상태 업데이트
            with transaction.atomic():
                email_message, created = EmailMessage.objects.get_or_create(
                    send_job=send_job,
                    defaults={
                        'from_email': settings.EMAIL_HOST_USER,
                        'to_email': send_job.to_email,
                        'subject_final': subject,
                        'body_final': body,
                        'sent_at': timezone.now()
                    }
                )
                
                if not created:
                    # 이미 존재하면 업데이트
                    email_message.sent_at = timezone.now()
                    email_message.save()
                
                # 이벤트 로그
                EmailEvent.objects.create(
                    email_message=email_message,
                    event_type='sent',
                    event_at=timezone.now(),
                    meta={'attempt': send_job.attempt_count + 1}
                )
                
                # SendJob 상태 업데이트
                send_job.status = 'sent'
                send_job.attempt_count += 1
                send_job.save(update_fields=['status', 'attempt_count'])
            
            logger.info(f"Email sent successfully for SendJob {send_job_id}")
            return {
                'status': 'success',
                'send_job_id': str(send_job_id),
                'to_email': send_job.to_email
            }
            
        except Exception as e:
            logger.error(f"Email sending failed for SendJob {send_job_id}: {e}")
            
            # 실패 처리
            mark_job_failed(send_job, str(e))
            
            # 재시도 (최대 3번)
            if send_job.attempt_count < 3:
                logger.info(f"Retrying SendJob {send_job_id} (attempt {send_job.attempt_count + 1}/3)")
                raise self.retry(exc=e, countdown=60 * (send_job.attempt_count + 1))
            
            return {
                'status': 'failed',
                'reason': 'smtp_error',
                'error': str(e),
                'attempts': send_job.attempt_count
            }
    
    except SendJob.DoesNotExist:
        logger.error(f"SendJob {send_job_id} not found or not scheduled")
        return {'status': 'error', 'reason': 'job_not_found'}
    
    except Exception as e:
        logger.exception(f"Unexpected error in send_single_email_task for {send_job_id}")
        return {'status': 'error', 'reason': 'unexpected_error', 'error': str(e)}


def render_template(template_str, lead):
    """
    Jinja2 템플릿 렌더링
    
    Args:
        template_str: 템플릿 문자열
        lead: Lead 객체
    
    Returns:
        str: 렌더링된 문자열
    """
    template = Template(template_str)
    
    # Lead 데이터 준비 (실제 모델 필드만 사용)
    context = {
        'lead': lead,  # Lead 객체 전체 전달
        'channel_name': lead.channel_name or '',
        'channel_url': lead.channel_url or '',
        'subscriber_count': lead.subscriber_count or 0,
        'email': lead.primary_email or '',
        'platform': lead.platform or '',
    }
    
    return template.render(**context)


def mark_job_failed(send_job, error_message):
    """
    SendJob을 failed 상태로 표시
    
    Args:
        send_job: SendJob 인스턴스
        error_message: 에러 메시지
    """
    with transaction.atomic():
        send_job.status = 'failed'
        send_job.last_error = error_message[:1000]  # 최대 1000자
        send_job.attempt_count += 1
        send_job.save(update_fields=['status', 'last_error', 'attempt_count'])


@shared_task
def send_due_jobs_task():
    """
    예약된 시간이 도래한 SendJob들을 스캔하여 발송 태스크 큐에 추가
    
    주기적으로 실행되는 태스크 (예: 1분마다)
    """
    now = timezone.now()
    
    # scheduled 상태이면서 scheduled_at이 현재 시각 이전인 잡 조회
    due_jobs = SendJob.objects.filter(
        status='scheduled',
        scheduled_at__lte=now,
        locked_at__isnull=True  # 락 걸리지 않은 것만
    ).select_related('lead', 'template_version')[:100]  # 한 번에 최대 100개
    
    queued_count = 0
    for job in due_jobs:
        try:
            # Celery 큐에 추가
            send_single_email_task.delay(str(job.id))
            queued_count += 1
            logger.info(f"Queued SendJob {job.id} for sending")
        except Exception as e:
            logger.error(f"Failed to queue SendJob {job.id}: {e}")
    
    logger.info(f"Queued {queued_count} due jobs for sending")
    return {
        'queued': queued_count,
        'timestamp': now.isoformat()
    }
