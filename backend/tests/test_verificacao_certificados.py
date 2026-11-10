import pytest
from rest_framework.test import APIClient

from apps.alunos.models import Aluno
from apps.certificados.models import Certificado
from apps.certificados.services import codigo_certificado_conclusao
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma


@pytest.fixture
def cenario(db):
    plano = Plano.objects.create(nome='PLANO_VERIF_CERT', preco=2000, duracao_dias=30)
    escola = Escola.objects.create(nome='Escola Verif', nif_cnpj='NIF_V', email='v@sige.mz', status='ATIVA', plano=plano)
    turma = Turma.objects.create(escola=escola, nome='12ª A', grau_ano='12ª Classe')
    aluno = Aluno.objects.create(escola=escola, turma=turma, matricula='MAT-1001', nome='Maria Joaquina Santos',
                                 data_nascimento='2005-01-01', genero='F')
    return escola, aluno


def _verificar(codigo):
    return APIClient().get(f'/api/v1/certificados/verificar/{codigo}/')


def test_codigo_inexistente_nao_verifica(cenario):
    assert _verificar('CERT-QUALQUER').status_code == 404


def test_matricula_no_codigo_nao_revela_aluno(cenario):
    # Antes, qualquer código que contivesse a matrícula devolvia os dados do aluno sem login.
    res = _verificar('CERT-MAT-1001-2026')
    assert res.status_code == 404
    assert 'Maria' not in str(res.data)


def test_codigo_valido_devolve_so_dados_minimos(cenario):
    escola, aluno = cenario
    codigo = codigo_certificado_conclusao(escola, aluno)
    res = _verificar(codigo)
    assert res.status_code == 200
    assert res.data['autentico'] is True
    assert res.data['data']['codigo'] == codigo
    corpo = str(res.data)
    assert 'Maria J. S.' in corpo
    assert 'Maria Joaquina Santos' not in corpo
    assert 'MAT-1001' not in corpo
    assert 'disciplinas' not in res.data['data']
    assert 'numero_documento' not in res.data['data']['aluno']
    assert 'nif_bi' not in res.data['data']['aluno']


def test_codigo_emitido_e_aleatorio_e_nao_deriva_da_matricula(cenario):
    escola, aluno = cenario
    codigo = codigo_certificado_conclusao(escola, aluno)
    assert 'MAT-1001' not in codigo
    # Idempotente: o mesmo aluno mantém o mesmo código.
    assert codigo_certificado_conclusao(escola, aluno) == codigo
    assert Certificado.objects.filter(escola=escola, aluno=aluno, tipo='CONCLUSAO').count() == 1
