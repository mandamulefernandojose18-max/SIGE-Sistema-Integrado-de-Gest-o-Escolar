import pytest
from django.core.cache import cache
from rest_framework.throttling import ScopedRateThrottle


@pytest.fixture(autouse=True)
def _isolar_limites_de_requisicoes(monkeypatch):
    """Cada teste começa com contadores limpos e limites folgados (o limite real é testado à parte)."""
    cache.clear()
    monkeypatch.setattr(
        ScopedRateThrottle,
        'THROTTLE_RATES',
        {'login': '10000/min', 'verificacao': '10000/min'},
    )
    yield
    cache.clear()
