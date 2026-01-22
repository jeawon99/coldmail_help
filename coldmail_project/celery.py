"""
Celery Configuration
"""
import os
from celery import Celery

# Django settings 모듈 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coldmail_project.settings')

app = Celery('coldmail')

# Django settings에서 CELERY_ prefix로 시작하는 설정 로드
app.config_from_object('django.conf:settings', namespace='CELERY')

# Django app에서 tasks.py 자동 발견
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """디버그용 테스트 태스크"""
    print(f'Request: {self.request!r}')
