import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano


@pytest.fixture
def utilizadores(db):
    plano = Plano.objects.create(nome='PLANO_SESSAO', preco=2000, duracao_dias=30)
    escola = Escola.objects.create(nome='Escola Sessao', nif_cnpj='NIF_S', email='s@sige.mz', status='ATIVA', plano=plano)
    admin = Usuario.objects.create_user(email='admin.s@sige.mz', password='SenhaForte123', role='ADMIN_ESCOLA', escola=escola)
    return escola, admin


def _login(email='admin.s@sige.mz', senha='SenhaForte123'):
    c = APIClient()
    r = c.post('/api/v1/auth/login/', {'email': email, 'password': senha}, format='json')
    assert r.status_code == 200, r.data
    return c, r.data


def _tokens(data):
    if 'refresh' in data:
        return data['access'], data['refresh']
    t = data['data']['tokens']
    return t['accessToken'], t['refreshToken']


def test_refresh_rodado_invalida_o_anterior(utilizadores):
    _, data = _login()
    _, refresh = _tokens(data)
    assert APIClient().post('/api/v1/auth/refresh/', {'refresh': refresh}, format='json').status_code == 200
    # o refresh usado fica na blacklist após a rotação
    assert APIClient().post('/api/v1/auth/refresh/', {'refresh': refresh}, format='json').status_code == 401


def test_logout_coloca_refresh_na_blacklist(utilizadores):
    _, data = _login()
    _, refresh = _tokens(data)
    assert APIClient().post('/api/v1/auth/logout/', {'refresh': refresh}, format='json').status_code == 200
    assert APIClient().post('/api/v1/auth/refresh/', {'refresh': refresh}, format='json').status_code == 401


def test_logout_e_idempotente_com_token_invalido(db):
    assert APIClient().post('/api/v1/auth/logout/', {'refresh': 'lixo'}, format='json').status_code == 200
    assert APIClient().post('/api/v1/auth/logout/', {}, format='json').status_code == 200


def test_senha_nova_exige_minimo_8(utilizadores):
    c, data = _login()
    access, _ = _tokens(data)
    c.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
    curta = c.post('/api/v1/auth/minha-senha/', {'senha_atual': 'SenhaForte123', 'nova_senha': '1234567'}, format='json')
    assert curta.status_code == 400
    ok = c.post('/api/v1/auth/minha-senha/', {'senha_atual': 'SenhaForte123', 'nova_senha': '12345678'}, format='json')
    assert ok.status_code == 200


def test_schema_openapi_exige_superadmin(utilizadores):
    assert APIClient().get('/api/schema/').status_code in (401, 403)
    c, data = _login()
    access, _ = _tokens(data)
    c.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
    assert c.get('/api/schema/').status_code == 403  # ADMIN_ESCOLA não é SUPERADMIN


@pytest.fixture(autouse=True)
def _limpar_cache():
    cache.clear()
    yield
    cache.clear()


def test_troca_de_senha_exige_senha_actual(utilizadores):
    c, data = _login()
    access, _ = _tokens(data)
    c.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
    # Sem senha actual (token roubado): recusa
    r = c.post('/api/v1/auth/minha-senha/', {'nova_senha': 'NovaSenha123'}, format='json')
    assert r.status_code == 400
    # Senha actual errada: recusa
    r = c.post('/api/v1/auth/minha-senha/', {'senha_atual': 'errada', 'nova_senha': 'NovaSenha123'}, format='json')
    assert r.status_code == 400
    # Senha actual correcta: aceita
    r = c.post('/api/v1/auth/minha-senha/', {'senha_atual': 'SenhaForte123', 'nova_senha': 'NovaSenha123'}, format='json')
    assert r.status_code == 200


def test_troca_de_senha_bloqueia_apos_varias_falhas(utilizadores):
    c, data = _login()
    access, _ = _tokens(data)
    c.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
    for _i in range(5):
        assert c.post('/api/v1/auth/minha-senha/', {'senha_atual': 'x', 'nova_senha': 'NovaSenha123'}, format='json').status_code == 400
    r = c.post('/api/v1/auth/minha-senha/', {'senha_atual': 'SenhaForte123', 'nova_senha': 'NovaSenha123'}, format='json')
    assert r.status_code == 429


def test_login_bloqueia_apos_5_falhas_mesmo_com_senha_certa(utilizadores):
    c = APIClient()
    for _i in range(5):
        r = c.post('/api/v1/auth/login/', {'email': 'admin.s@sige.mz', 'password': 'errada'}, format='json')
        assert r.status_code == 401
    r = c.post('/api/v1/auth/login/', {'email': 'admin.s@sige.mz', 'password': 'SenhaForte123'}, format='json')
    assert r.status_code == 429


def test_login_sucesso_zera_contador(utilizadores):
    c = APIClient()
    for _i in range(3):
        assert c.post('/api/v1/auth/login/', {'email': 'admin.s@sige.mz', 'password': 'errada'}, format='json').status_code == 401
    assert c.post('/api/v1/auth/login/', {'email': 'admin.s@sige.mz', 'password': 'SenhaForte123'}, format='json').status_code == 200
    for _i in range(4):
        assert c.post('/api/v1/auth/login/', {'email': 'admin.s@sige.mz', 'password': 'errada'}, format='json').status_code == 401
    assert c.post('/api/v1/auth/login/', {'email': 'admin.s@sige.mz', 'password': 'SenhaForte123'}, format='json').status_code == 200


def test_bloqueio_nao_afecta_outro_utilizador(utilizadores):
    escola, _ = utilizadores
    Usuario.objects.create_user(email='outro.s@sige.mz', password='OutraSenha123', role='ADMIN_ESCOLA', escola=escola)
    c = APIClient()
    for _i in range(5):
        c.post('/api/v1/auth/login/', {'email': 'admin.s@sige.mz', 'password': 'errada'}, format='json')
    r = c.post('/api/v1/auth/login/', {'email': 'outro.s@sige.mz', 'password': 'OutraSenha123'}, format='json')
    assert r.status_code == 200