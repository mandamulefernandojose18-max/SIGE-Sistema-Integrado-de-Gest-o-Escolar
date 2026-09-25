# Dockerfile para o Backend Django REST Framework (SIGE)
FROM python:3.12-slim

# Evita arquivos .pyc e forca flush imediato de stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

# Dependencias de sistema para compilar pacotes e manipular imagens/documentos
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalacao de dependencias Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia codigo-fonte do Backend
COPY . /app/

# Remove venv local e caches locais caso tenham sido copiados
RUN rm -rf /app/venv /app/.pytest_cache /app/__pycache__

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120"]
