import pytest
from django.core.management import call_command
from io import StringIO
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano

SENHA_EXPOSTA = 'Deusamo8'  # a antiga "senha mestra" que esteve no repositório público


@pytest.fixture
def admin_escola(db):
    plano = Plano.objects.create(nome='PLANO_MESTRA', preco=2000, duracao_dias=30)
    escola = Escola.objects.create(nome='Escola Mestra', nif_cnpj='NIF_M', email='m@sige.mz', status='ATIVA', plano=plano)
    return Usuario.objects.create_user(email='admin.m@sige.mz', password='SenhaPropria123', role='ADMIN_ESCOLA', escola=escola)


def test_senha_mestra_ja_nao_entra_em_nenhuma_conta(admin_escola):
    for ident in ('admin.m@sige.mz', 'admin', 'mandamule'):
        r = APIClient().post('/api/v1/auth/login/', {'email': ident, 'password': SENHA_EXPOSTA}, format='json')
        assert r.status_code == 401, ident


def test_conta_continua_a_entrar_com_a_sua_propria_senha(admin_escola):
    r = APIClient().post('/api/v1/auth/login/', {'email': 'admin.m@sige.mz', 'password': 'SenhaPropria123'}, format='json')
    assert r.status_code == 200


def test_seed_nao_cria_superadmin_com_senha_fixa(db, monkeypatch):
    monkeypatch.delenv('SUPERADMIN_PASSWORD', raising=False)
    call_command('seed', stdout=StringIO())
    sa = Usuario.objects.get(email='mandamulefj@sige.com')
    assert sa.role == 'SUPERADMIN'
    assert not sa.has_usable_password()
    assert not sa.check_password(SENHA_EXPOSTA)


def test_seed_nao_repoe_senha_de_conta_existente(db, monkeypatch):
    monkeypatch.delenv('SUPERADMIN_PASSWORD', raising=False)
    call_command('seed', stdout=StringIO())
    sa = Usuario.objects.get(email='mandamulefj@sige.com')
    sa.set_password('MinhaNovaSenhaForte1')
    sa.save()
    call_command('seed', stdout=StringIO())  # reinício do contentor
    sa.refresh_from_db()
    assert sa.check_password('MinhaNovaSenhaForte1')


def test_seed_usa_superadmin_password_do_ambiente_e_rejeita_curta(db, monkeypatch):
    monkeypatch.setenv('SUPERADMIN_PASSWORD', 'curta')
    call_command('seed', stdout=StringIO())
    assert not Usuario.objects.get(email='mandamulefj@sige.com').has_usable_password()

    monkeypatch.setenv('SUPERADMIN_PASSWORD', 'SenhaDoAmbiente-2026!')
    call_command('seed', stdout=StringIO())
    assert Usuario.objects.get(email='mandamulefj@sige.com').check_password('SenhaDoAmbiente-2026!')


def test_auditoria_lista_e_neutraliza_contas_com_senha_exposta(db):
    plano = Plano.objects.create(nome='PLANO_AUD', preco=1, duracao_dias=30)
    escola = Escola.objects.create(nome='Escola Aud', nif_cnpj='NIF_A', email='a@sige.mz', status='ATIVA', plano=plano)
    afectada = Usuario.objects.create_user(email='dir.aud@sige.mz', password=SENHA_EXPOSTA, role='ADMIN_ESCOLA', escola=escola,
                                           codigo_acesso='GD-AUD-1')
    saudavel = Usuario.objects.create_user(email='ok.aud@sige.mz', password='OutraSenhaBoa123', role='ADMIN_ESCOLA', escola=escola)
    sa = Usuario.objects.create_user(email='sa.aud@sige.mz', password=SENHA_EXPOSTA, role='SUPERADMIN')

    out = StringIO()
    call_command('auditar_senha_conhecida', stdout=out)  # dry-run
    afectada.refresh_from_db()
    assert afectada.check_password(SENHA_EXPOSTA)
    assert 'dry-run' in out.getvalue()

    call_command('auditar_senha_conhecida', '--aplicar', stdout=StringIO())
    afectada.refresh_from_db(); saudavel.refresh_from_db(); sa.refresh_from_db()
    assert not afectada.check_password(SENHA_EXPOSTA)
    assert afectada.check_password('GD-AUD-1') and afectada.senha_redefinida is False
    assert saudavel.check_password('OutraSenhaBoa123')
    assert sa.check_password(SENHA_EXPOSTA)  # SUPERADMIN nunca é alterado pelo comando
