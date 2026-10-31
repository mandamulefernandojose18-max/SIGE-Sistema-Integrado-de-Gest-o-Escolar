import re

import pytest
from django.conf import settings
from rest_framework.test import APIClient

IP_RE = re.compile(r'\d{1,3}(?:[.-]\d{1,3}){3}')


def _origens_e_hosts():
    return (
        list(settings.ALLOWED_HOSTS)
        + list(settings.CSRF_TRUSTED_ORIGINS)
        + list(settings.CORS_ALLOWED_ORIGINS)
    )


def test_allowed_hosts_sem_wildcard():
    assert '*' not in settings.ALLOWED_HOSTS
    assert 'sigesaas.duckdns.org' in settings.ALLOWED_HOSTS


def test_sem_ips_nem_dominios_derivados_de_ip():
    for valor in _origens_e_hosts():
        assert not IP_RE.search(valor.replace('127.0.0.1', '').replace('0.0.0.0', '')), valor
        assert 'sslip.io' not in valor, valor


def test_cors_nao_aceita_qualquer_origem():
    assert not getattr(settings, 'CORS_ALLOW_ALL_ORIGINS', False)
    assert not getattr(settings, 'CORS_ALLOWED_ORIGIN_REGEXES', [])


def test_secret_key_definida():
    assert settings.SECRET_KEY


@pytest.mark.django_db
def test_login_tem_limite_de_tentativas(monkeypatch):
    from rest_framework.throttling import ScopedRateThrottle
    monkeypatch.setattr(ScopedRateThrottle, 'THROTTLE_RATES', {'login': '3/min'})

    client = APIClient()
    codigos = [
        client.post('/api/v1/auth/login/', {'email': 'x@sige.mz', 'password': 'errada'}, format='json').status_code
        for _ in range(5)
    ]
    assert 429 in codigos
