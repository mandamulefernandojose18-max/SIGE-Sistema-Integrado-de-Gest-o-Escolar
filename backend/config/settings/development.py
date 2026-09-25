from .base import *
import os
from urllib.parse import urlparse, unquote, parse_qs

DEBUG = True

# Configuracao da Base de Dados
db_url = os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3')

if db_url.startswith('postgres://') or db_url.startswith('postgresql://'):
    parsed = urlparse(db_url)
    db_name = unquote(parsed.path.lstrip('/')).split('?')[0]
    username = unquote(parsed.username or '')
    password = unquote(parsed.password or '')
    hostname = parsed.hostname or 'localhost'
    port = str(parsed.port or 5432)

    query_params = parse_qs(parsed.query)

    # Suporte a Supabase (IPv4 Pooler fallback para redes locais sem suporte a IPv6 direto)
    if 'supabase.co' in hostname and hostname.startswith('db.'):
        parts = hostname.split('.')
        project_ref = parts[1]
        if '.' not in username:
            username = f"{username}.{project_ref}"
        hostname = "aws-0-us-west-2.pooler.supabase.com"

    options = {}
    if 'sslmode' in query_params:
        options['sslmode'] = query_params['sslmode'][0]
    elif 'supabase' in hostname or hostname not in ('localhost', '127.0.0.1', 'postgres'):
        options['sslmode'] = 'require'

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': db_name,
            'USER': username,
            'PASSWORD': password,
            'HOST': hostname,
            'PORT': port,
            'OPTIONS': options,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
