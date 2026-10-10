from .base import *
import os
from urllib.parse import urlparse, unquote, parse_qs

DEBUG = True

# Configuracao da Base de Dados
is_testing = 'pytest' in sys.modules or 'test' in sys.argv or os.environ.get('TESTING') == '1'
db_url = os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3')

if is_testing:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
elif db_url.startswith('postgres://') or db_url.startswith('postgresql://'):
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
        if not parsed.port or str(parsed.port) == '5432':
            port = '6543'

    options = {}
    if 'sslmode' in query_params:
        options['sslmode'] = query_params['sslmode'][0]
    elif 'supabase' in hostname or hostname not in ('localhost', '127.0.0.1', 'postgres'):
        options['sslmode'] = 'require'

    options['connect_timeout'] = 5
    options['keepalives'] = 1
    options['keepalives_idle'] = 30
    options['keepalives_interval'] = 10
    options['keepalives_count'] = 5
    options['prepare_threshold'] = None

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': db_name,
            'USER': username,
            'PASSWORD': password,
            'HOST': hostname,
            'PORT': port,
            'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', 60)),
            'CONN_HEALTH_CHECKS': True,
            'DISABLE_SERVER_SIDE_CURSORS': True,
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
