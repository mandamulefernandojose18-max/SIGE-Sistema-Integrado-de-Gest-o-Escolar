import os
from pathlib import Path
from datetime import timedelta
import sys

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Adicionar BASE_DIR e BASE_DIR/apps ao sys.path
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / 'apps'))

from dotenv import load_dotenv
load_dotenv(BASE_DIR.parent / '.env')
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.environ.get('SECRET_KEY', 'sige-django-secret-key-enterprise-2026-mz!')
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 't')

sys_host = os.environ.get('SYSTEM_HOSTNAME', '').strip()
extra_hosts = [sys_host] if sys_host else []

ALLOWED_HOSTS = list(set([host.strip() for host in os.environ.get('ALLOWED_HOSTS', '*').split(',') if host.strip()] + extra_hosts + ['*', '.duckdns.org', 'sigesaas.duckdns.org', 'sigesass.duckdns.org', '.sslip.io', 'sige.8b54e22e.sslip.io', 'sige.139-84-226-46.sslip.io', '139.84.226.46', 'localhost', '127.0.0.1']))
CSRF_TRUSTED_ORIGINS = [
    'https://sigesaas.duckdns.org',
    'https://sigesass.duckdns.org',
    'https://*.duckdns.org',
    'https://*.sslip.io',
    'https://sige.8b54e22e.sslip.io',
    'https://sige.139-84-226-46.sslip.io',
    'http://139.84.226.46:5173',
    'http://139.84.226.46',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]
APPEND_SLASH = False


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Terceiros
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_spectacular',

    # Apps locais do SIGE
    'apps.accounts',
    'apps.tenants',
    'apps.alunos',
    'apps.professores',
    'apps.turmas',
    'apps.disciplinas',
    'apps.notas',
    'apps.pautas',
    'apps.material_escolar',
    'apps.documentos',
    'apps.pagamentos',
    'apps.certificados',
    'apps.dashboard',
    'apps.ferramentas',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'common.middleware.tenant.TenantMiddleware',
    'apps.tenants.saas_middleware.VerificarAssinaturaMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

AUTH_USER_MODEL = 'accounts.Usuario'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 6}},
]

# Internacionalização e Fuso Horário de Moçambique
LANGUAGE_CODE = 'pt-pt'
TIME_ZONE = 'Africa/Maputo'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'common.pagination.StandardResultsSetPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# SimpleJWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.environ.get('JWT_ACCESS_LIFETIME_MINUTES', '120'))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.environ.get('JWT_REFRESH_LIFETIME_DAYS', '7'))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'SIGNING_KEY': os.environ.get('JWT_SECRET_KEY', SECRET_KEY),
}

# CORS Configuration
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https?://.*$",
]
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in os.environ.get(
        'CORS_ALLOWED_ORIGINS',
        'http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://localhost:80'
    ).split(',') if origin.strip()
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-tenant-id',
]

# OpenAPI / Swagger Documentation
SPECTACULAR_SETTINGS = {
    'TITLE': 'SIGE API — Sistema Integrado de Gestão Escolar',
    'DESCRIPTION': 'API RESTful corporativa SaaS Multi-Tenant conforme as normas do MEC.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# Limites de Upload de Documentos, Materiais Escolares (Base64 / PDF / DOCX) e Logótipos (100 MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

