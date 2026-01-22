"""
Celery Configuration
"""
import os
from celery import Celery
from celery.schedules import crontab

# Django settings 모듈 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coldmail_project.settings')

app = Celery('coldmail')

# Django settings에서 CELERY_ prefix로 시작하는 설정 로드
app.config_from_object('django.conf:settings', namespace='CELERY')

# Django app에서 tasks.py 자동 발견
app.autodiscover_tasks()

# Celery Beat 스케줄 설정 (주기적 작업)
app.conf.beat_schedule = {
    'send-due-jobs-every-minute': {
        'task': 'campaigns.tasks.send_due_jobs_task',
        'schedule': 60.0,  # 60초마다 실행
        'options': {
            'expires': 50.0,  # 50초 후 만료 (중복 실행 방지)
        }
    },
}

# Timezone 설정 (Django settings의 TIME_ZONE 사용)
app.conf.timezone = 'Asia/Seoul'

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """디버그용 테스트 태스크"""
    print(f'Request: {self.request!r}')
