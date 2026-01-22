"""
Send Due Jobs Management Command

예약된 시간이 도래한 SendJob들을 스캔하여 발송 큐에 추가합니다.

사용법:
    python manage.py send_due_jobs
    
Celery Beat와 함께 사용하거나, cron job으로 주기적으로 실행하세요.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from campaigns.tasks import send_due_jobs_task


class Command(BaseCommand):
    help = '예약된 시간이 도래한 SendJob들을 발송 큐에 추가합니다'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--async',
            action='store_true',
            help='Celery 태스크로 비동기 실행 (기본: 동기 실행)'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(f'[{timezone.now()}] Scanning for due jobs...')
        )
        
        if options['async']:
            # Celery 태스크로 비동기 실행
            result = send_due_jobs_task.delay()
            self.stdout.write(
                self.style.SUCCESS(f'Task queued: {result.id}')
            )
        else:
            # 동기 실행
            result = send_due_jobs_task()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Queued {result['queued']} jobs for sending"
                )
            )
            
            if result['queued'] > 0:
                self.stdout.write(
                    self.style.WARNING(
                        'Note: Jobs are queued. Make sure Celery worker is running to process them.'
                    )
                )
