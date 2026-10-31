import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.alunos.models import Aluno
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma

ROTAS_ALUNO = (
    '/api/v1/impressao/boletim/{id}',
    '/api/v1/impressao/boletim/{id}/pdf',
    '/api/v1/impressao/declaracao/{id}/pdf',
    '/api/v1/impressao/certificado/{id}/pdf',
    '/api/v1/impressao/ficha/{id}/pdf',
)


@pytest.fixture
def cenario(db):
    plano = Plano.objects.create(nome='PLANO_DOCS_TEST', preco=2000, duracao_dias=30)
    a = Escola.objects.create(nome='Escola A', nif_cnpj='NIF_DA', email='da@sige.mz', status='ATIVA', plano=plano)
    b = Escola.objects.create(nome='Escola B', nif_cnpj='NIF_DB', email='db@sige.mz', status='ATIVA', plano=plano)
    Usuario.objects.create_user(email='admin.da@sige.mz', password='PassDa123!', role='ADMIN_ESCOLA', escola=a)
    turma_b = Turma.objects.create(escola=b, nome='Turma B', grau_ano='10ª Classe')
    aluno_b = Aluno.objects.create(
        escola=b, turma=turma_b, matricula='MAT_DB_001', nome='Aluno B',
        data_nascimento='2009-01-01', genero='F',
    )
    return a, b, aluno_b


@pytest.mark.parametrize('rota', ROTAS_ALUNO)
def test_documentos_sem_login_sao_negados(cenario, rota):
    _, _, aluno_b = cenario
    res = APIClient().get(rota.format(id=aluno_b.id))
    assert res.status_code in (401, 403)


@pytest.mark.parametrize('rota', ROTAS_ALUNO)
def test_documentos_de_aluno_de_outra_escola_sao_negados(cenario, rota):
    _, _, aluno_b = cenario
    client = APIClient()
    login = client.post('/api/v1/auth/login/', {'email': 'admin.da@sige.mz', 'password': 'PassDa123!'}, format='json')
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")
    res = client.get(rota.format(id=aluno_b.id), HTTP_X_TENANT_ID=str(aluno_b.escola_id))
    assert res.status_code in (403, 404)


def test_parametros_de_exame_exigem_login_e_nao_usam_primeira_escola(cenario):
    client = APIClient()
    assert client.get('/api/v1/pautas/exames/parametros').status_code in (401, 403)
    assert client.post('/api/v1/pautas/exames/parametros', {'peso_frequencia': 10, 'peso_exame': 90, 'nota_minima_exame': 5}, format='json').status_code in (401, 403)
