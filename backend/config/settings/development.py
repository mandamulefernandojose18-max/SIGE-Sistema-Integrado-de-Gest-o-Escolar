from .base import *
import os
import re

DEBUG = True

# Configuração da Base de Dados
# Se DATABASE_URL estiver configurada para PostgreSQL usa psycopg, caso contrário usa SQLite como fallback de desenvolvimento
db_url = os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3')

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
            }
        }
    else:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
