import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.professores.models import Professor
from apps.tenants.models import Escola, Plano


@pytest.fixture
def escola(db):
    plano = Plano.objects.create(nome='PLANO_PERFIL', preco=2000, duracao_dias=30)
    return Escola.objects.create(nome='Escola Perfil', nif_cnpj='NIF_P', email='p@sige.mz', status='ATIVA', plano=plano)


def _login(codigo, senha):
    return APIClient().post('/api/v1/auth/login/', {'codigo': codigo, 'password': senha}, format='json')


def test_professor_com_email_de_superadmin_entra_como_professor(escola):
    sa = Usuario.objects.create_superuser(email='dono@sige.mz', password='SenhaDono123')
    prof = Professor.objects.create(escola=escola, nome='Prof', email='dono@sige.mz', especialidade='Matemática')
    sa.refresh_from_db()
    assert sa.role == 'SUPERADMIN' and sa.escola_id is None and sa.professor_id is None
    r = _login(prof.codigo, prof.codigo)
    assert r.status_code == 200
    assert Usuario.objects.get(professor_id=prof.id).role == 'PROFESSOR'


def test_autocura_codigo_preso_a_conta_de_outro_perfil(escola):
    prof = Professor.objects.create(escola=escola, nome='Prof', email='prof@sige.mz', especialidade='Matemática')
    conta_prof = Usuario.objects.get(professor_id=prof.id)
    # simula dados antigos corrompidos: código preso a um Superadmin
    Usuario.objects.filter(pk=conta_prof.pk).update(codigo_acesso=None, professor_id=None)
    sa = Usuario.objects.create_superuser(email='sa@sige.mz', password='SenhaDono123')
    Usuario.objects.filter(pk=sa.pk).update(codigo_acesso=prof.codigo, professor_id=prof.id)
    r = _login(prof.codigo, prof.codigo)
    assert r.status_code == 200
    assert Usuario.objects.get(pk=sa.pk).role == 'SUPERADMIN'
    assert Usuario.objects.get(professor_id=prof.id).role == 'PROFESSOR'
