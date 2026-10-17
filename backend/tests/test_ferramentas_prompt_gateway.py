import pytest
from unittest.mock import patch
from django.urls import reverse
from django.test import Client
from apps.accounts.models import Usuario

@pytest.fixture
def client():
    return Client()

@pytest.fixture
def superadmin_user(db):
    u = Usuario.objects.filter(email='admin.prompt@sige.com').first()
    if not u:
        u = Usuario.objects.create_user(
            email='admin.prompt@sige.com',
            username='admin.prompt@sige.com',
            password='testpassword123',
            role='SUPERADMIN',
            nome='Super Administrador Teste'
        )
    return u

@pytest.fixture
def aluno_user(db):
    u = Usuario.objects.filter(email='aluno.prompt@sige.com').first()
    if not u:
        u = Usuario.objects.create_user(
            email='aluno.prompt@sige.com',
            username='aluno.prompt@sige.com',
            password='testpassword123',
            role='ALUNO',
            nome='Aluno Teste'
        )
    return u

@pytest.fixture
def financeiro_user(db):
    u = Usuario.objects.filter(email='fin.prompt@sige.com').first()
    if not u:
        u = Usuario.objects.create_user(
            email='fin.prompt@sige.com',
            username='fin.prompt@sige.com',
            password='testpassword123',
            role='FINANCEIRO',
            nome='Gestor Financeiro Teste'
        )
    return u

@pytest.mark.django_db
def test_prompt_gateway_sem_sessao(client):
    """Sem sessão: a página redireciona (ou 401) e o download retorna 401."""
    resp_page = client.get('/ferramentas/prompt-gateway')
    assert resp_page.status_code in [302, 401]

    resp_down = client.get('/ferramentas/prompt-gateway/descarregar')
    assert resp_down.status_code == 401
    assert resp_down.headers.get('Cache-Control') is not None
    assert 'no-store' in resp_down.headers.get('Cache-Control')

@pytest.mark.django_db
def test_prompt_gateway_sem_permissao_aluno(client, aluno_user):
    """Com sessão mas sem permissão (ALUNO): retorna 403 Forbidden."""
    client.force_login(aluno_user)

    resp_page = client.get('/ferramentas/prompt-gateway')
    assert resp_page.status_code == 403

    resp_down = client.get('/ferramentas/prompt-gateway/descarregar')
    assert resp_down.status_code == 403

@pytest.mark.django_db
def test_prompt_gateway_com_superadmin(client, superadmin_user):
    """Com administrador: página devolve 200, texto escapado e cabeçalhos de segurança."""
    client.force_login(superadmin_user)

    resp_page = client.get('/ferramentas/prompt-gateway')
    assert resp_page.status_code == 200
    html = resp_page.content.decode('utf-8')
    assert 'Prompt: Gateway SMS, USSD e Pagamentos Móveis' in html
    assert 'noindex' in html
    assert resp_page.headers.get('X-Robots-Tag') == 'noindex, nofollow'
    assert 'no-store' in resp_page.headers.get('Cache-Control')

    # Validação do download
    resp_down = client.get('/ferramentas/prompt-gateway/descarregar')
    assert resp_down.status_code == 200
    assert resp_down.headers.get('Content-Type') == 'text/plain; charset=utf-8'
    assert 'prompt-gateway-sms-ussd.txt' in resp_down.headers.get('Content-Disposition')
    assert len(resp_down.content) > 100

@pytest.mark.django_db
def test_prompt_gateway_financeiro(client, financeiro_user):
    """Com perfil Financeiro: acesso autorizado."""
    client.force_login(financeiro_user)

    resp_page = client.get('/ferramentas/prompt-gateway')
    assert resp_page.status_code == 200
    assert 'Prompt: Gateway SMS, USSD e Pagamentos Móveis' in resp_page.content.decode('utf-8')

@pytest.mark.django_db
def test_prompt_gateway_ficheiro_em_falta(client, superadmin_user):
    """Ficheiro de conteúdo em falta: resposta 500 genérica sem vazar caminhos internos."""
    client.force_login(superadmin_user)

    with patch('apps.ferramentas.views._ler_conteudo_prompt', return_value=None):
        resp_page = client.get('/ferramentas/prompt-gateway')
        assert resp_page.status_code == 500
        html = resp_page.content.decode('utf-8')
        assert '500 — Ocorreu um erro' in html
        assert 'Traceback' not in html
        assert 'Exception' not in html
        assert 'prompt-gateway.txt' not in html
