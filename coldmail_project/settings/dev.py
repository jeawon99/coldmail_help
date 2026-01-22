"""
Development settings - SQLite 사용
로컬 개발 환경에서 MySQL 없이 개발 가능
"""

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']

# Database - SQLite (개발용)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# 개발 환경에서 실제 SMTP로 메일 발송 (테스트용)
# 주석 처리하면 콘솔로 출력됩니다
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# 개발 환경 로깅
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
