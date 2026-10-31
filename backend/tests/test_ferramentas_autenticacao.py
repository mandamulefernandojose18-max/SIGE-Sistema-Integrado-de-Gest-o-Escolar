import json

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.alunos.models import Aluno
from apps.ferramentas.models import ProvaBlindada
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma


@pytest.fixture
def duas_escolas(db):
    plano = Plano.objects.create(nome='PLANO_FERRAMENTAS_TEST', preco=2000, duracao_dias=30)
    a = Escola.objects.create(nome='Escola A', nif_cnpj='NIF_FA', email='fa@sige.mz', status='ATIVA', plano=plano)
    b = Escola.objects.create(nome='Escola B', nif_cnpj='NIF_FB', email='fb@sige.mz', status='ATIVA', plano=plano)
    Usuario.objects.create_user(email='admin.fa@sige.mz', password='PassFa123!', role='ADMIN_ESCOLA', escola=a)
    return a, b


def _token(client, email, senha):
    res = client.post('/api/v1/auth/login/', {'email': email, 'password': senha}, format='json')
    assert res.status_code == 200
    return res.data['token']


def test_cabecalho_x_user_role_nao_autentica(db):
    res = APIClient().get('/api/v1/ferramentas/stats/', HTTP_X_USER_ROLE='SUPERADMIN')
    assert res.status_code == 401


def test_token_forjado_nao_autentica(db):
    import jwt
    forjado = jwt.encode({'role': 'SUPERADMIN'}, 'qualquer-segredo', algorithm='HS256')
    res = APIClient().get('/api/v1/ferramentas/stats/', HTTP_AUTHORIZATION=f'Bearer {forjado}')
    assert res.status_code == 401


def test_webhook_sms_exige_autenticacao(db):
    res = APIClient().post(
        '/api/v1/ferramentas/reconciliacao/sms-webhook/',
        data=json.dumps({'message': 'Recebeu 100.00MT Ref: ABC123'}),
        content_type='application/json',
    )
    assert res.status_code == 401


def test_provas_de_outra_escola_nao_sao_acessiveis(duas_escolas):
    a, b = duas_escolas
    prova_b = ProvaBlindada.objects.create(
        escola=b, titulo='Prova B', disciplina='Matemática', classe='10ª Classe',
        codigo_autenticidade='PROVA_B_001', data_bloqueio_ia='2099-01-01T00:00:00Z',
        questoes=[], total_questoes=0, cotacao_total=20,
    )
    client = APIClient()
    assert client.get('/api/v1/ferramentas/provas-anti-ia/lista/').status_code == 401
    assert client.get(f'/api/v1/ferramentas/provas-anti-ia/{prova_b.id}/detalhe/').status_code == 401

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(client, 'admin.fa@sige.mz', 'PassFa123!')}")
    assert client.get(f'/api/v1/ferramentas/provas-anti-ia/{prova_b.id}/detalhe/').status_code == 404
    assert client.get(f'/api/v1/ferramentas/provas-anti-ia/{prova_b.id}/descarregar-pdf/').status_code == 404
    lista = client.get('/api/v1/ferramentas/provas-anti-ia/lista/').json()
    assert all(p['id'] != str(prova_b.id) for p in lista['data'])
