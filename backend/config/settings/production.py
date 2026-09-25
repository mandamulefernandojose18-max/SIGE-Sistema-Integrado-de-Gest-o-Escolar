from .base import *
import os
import re

DEBUG = False

db_url = os.environ.get('DATABASE_URL', '')

if db_url.startswith('postgres://') or db_url.startswith('postgresql://'):
    pattern = r'postgres(?:ql)?://([^:]+):([^@]+)@([^:/]+):?(\d+)?/(.+)'
    match = re.match(pattern, db_url)
    if match:
        user, password, host, port, name = match.groups()
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': name.split('?')[0],
                'USER': user,
                'PASSWORD': password,
                'HOST': host,
                'PORT': port or '5432',
                'CONN_MAX_AGE': 60,
            }
        }
    else:
        raise ValueError("DATABASE_URL inválida para produção PostgreSQL.")
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('POSTGRES_DB', 'sige_db'),
            'USER': os.environ.get('POSTGRES_USER', 'sige_user'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
            'HOST': os.environ.get('POSTGRES_HOST', 'postgres'),
            'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        }
    }

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
