"""
Settings package for coldmail_project.
Automatically loads the correct settings based on DJANGO_ENV environment variable.
"""

import os

# DJANGO_ENV 환경 변수로 설정 파일 결정 (기본값: dev)
env = os.getenv('DJANGO_ENV', 'dev')

if env == 'prod':
    from .prod import *
else:
    from .dev import *
