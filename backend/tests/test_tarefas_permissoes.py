import pytest
from common.permissions.matriz import MATRIZ_PERMISSOES, checar_permissao_matriz
from apps.accounts.models import Usuario, LogAuditoria
from apps.accounts.audit import registrar_auditoria
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma, HorarioEscolar
from apps.alunos.models import Aluno, PresencaAluno, TransferenciaAnulacao
from apps.disciplinas.models import Disciplina
from apps.professores.models import Professor
from apps.notas.models import PlanoAulaSumario, OcorrenciaDisciplinar
from apps.pagamentos.models import TransacaoFinanceira, FolhaSalario, ItemPatrimonio
from apps.documentos.models import CalendarioEscolar, ComunicadoEscolar
from rest_framework.test import APIClient
from django.utils import timezone
import datetime

@pytest.fixture
def escola_db(db):
    plano = Plano.objects.create(nome='Profissional', max_alunos=1000, preco=3500)
    return Escola.objects.create(
        nome='Escola Secundária de Massinga',
        codigo_escola='0101S001',
        plano=plano,
        status='ATIVA'
    )

@pytest.fixture
def user_director(db, escola_db):
    return Usuario.objects.create_user(
        email='director@escola.mz',
        nome='Director Geral',
        role='DIRECTOR_ESCOLA',
        escola=escola_db,
        password='pass'
    )

@pytest.fixture
def user_dap(db, escola_db):
    return Usuario.objects.create_user(
        email='dap@escola.mz',
        nome='Director Pedagógico',
        role='DAP',
        escola=escola_db,
        password='pass'
    )

@pytest.fixture
def user_financeiro(db, escola_db):
    return Usuario.objects.create_user(
        email='financeiro@escola.mz',
        nome='Chefe Financeiro',
        role='FINANCEIRO',
        escola=escola_db,
        password='pass'
    )

@pytest.fixture
def user_professor(db, escola_db):
    prof = Professor.objects.create(
        escola=escola_db,
        nome='Professor Fernando',
        email='prof.fernando@escola.mz'
    )
    return Usuario.objects.create_user(
        email='prof.fernando@escola.mz',
        nome='Professor Fernando',
        role='PROFESSOR',
        escola=escola_db,
        professor_id=prof.id,
        password='pass'
    )

@pytest.fixture
def user_aluno(db, escola_db):
    turma = Turma.objects.create(
        escola=escola_db,
        nome='Turma A',
        grau_ano='11ª Classe',
        ano_letivo='2026'
    )
    aluno = Aluno.objects.create(
        escola=escola_db,
        turma=turma,
        nome='João Mandamule',
        data_nascimento=datetime.date(2008, 5, 10),
        genero='M'
    )
    return Usuario.objects.filter(aluno_id=aluno.id).first()


@pytest.mark.django_db
class TestMatrizPermissoes:
    def test_matriz_regras_documento(self):
        # Director
        assert checar_permissao_matriz('DIRECTOR_ESCOLA', 'utilizadores_permissoes', 'V') is True
        assert checar_permissao_matriz('DIRECTOR_ESCOLA', 'utilizadores_permissoes', 'A') is True
        assert checar_permissao_matriz('DIRECTOR_ESCOLA', 'receitas_despesas', 'A') is True

        # DAP
        assert checar_permissao_matriz('DAP', 'utilizadores_permissoes', 'V') is False
        assert checar_permissao_matriz('DAP', 'calendario_escolar', 'C') is True
        assert checar_permissao_matriz('DAP', 'calendario_escolar', 'E') is True
        assert checar_permissao_matriz('DAP', 'notas_medias', 'A') is True

        # Professor
        assert checar_permissao_matriz('PROFESSOR', 'notas_medias', 'C') is True
        assert checar_permissao_matriz('PROFESSOR', 'notas_medias', 'A') is False
        assert checar_permissao_matriz('PROFESSOR', 'plano_aula_sumarios', 'C') is True
        assert checar_permissao_matriz('PROFESSOR', 'propinas_pagamentos', 'V') is False

        # Secretaria
        assert checar_permissao_matriz('SECRETARIA', 'matriculas', 'C') is True
        assert checar_permissao_matriz('SECRETARIA', 'declaracoes_certificados', 'C') is True
        assert checar_permissao_matriz('SECRETARIA', 'receitas_despesas', 'C') is False

        # Financeiro
        assert checar_permissao_matriz('FINANCEIRO', 'receitas_despesas', 'C') is True
        assert checar_permissao_matriz('FINANCEIRO', 'receitas_despesas', 'A') is False
        assert checar_permissao_matriz('FINANCEIRO', 'salarios_pessoal', 'C') is True
        assert checar_permissao_matriz('FINANCEIRO', 'inventario_patrimonio', 'C') is True

    def test_auditoria_registro(self, escola_db, user_director):
        log = registrar_auditoria(
            usuario=user_director,
            escola=escola_db,
            entidade='NOTA',
            acao='EDICAO',
            objeto_id='12345',
            descricao='Alteração de teste 1 para 14.5'
        )
        assert log is not None
        assert log.entidade == 'NOTA'
        assert log.acao == 'EDICAO'
        assert LogAuditoria.objects.filter(objeto_id='12345').exists()

    def test_separacao_funcoes_despesa(self, escola_db, user_director, user_financeiro):
        # Finanças cria despesa
        despesa = TransacaoFinanceira.objects.create(
            escola=escola_db,
            tipo='DESPESA',
            categoria='Material de Limpeza',
            descricao='Compra de detergente e vassouras',
            valor=1500.00,
            data=timezone.now().date(),
            registado_por=user_financeiro,
            status_aprovacao='PENDENTE'
        )

        client = APIClient()

        # Finanças tenta aprovar -> DEVE SER RECUSADO (403 Forbidden)
        client.force_authenticate(user=user_financeiro)
        res_fin = client.post(f'/api/v1/pagamentos/transacoes/{despesa.id}/aprovar/')
        assert res_fin.status_code == 403
        assert 'separação de funções' in res_fin.data['message'].lower()

        # Director aprova -> DEVE SER ACEITE (200 OK)
        client.force_authenticate(user=user_director)
        res_dir = client.post(f'/api/v1/pagamentos/transacoes/{despesa.id}/aprovar/')
        assert res_dir.status_code == 200
        despesa.refresh_from_db()
        assert despesa.status_aprovacao == 'APROVADO_DIRECTOR'

    def test_aluno_painel_preservado(self, escola_db, user_aluno):
        """Garante que o painel do aluno e seus endpoints continuam 100% funcionais."""
        assert user_aluno is not None
        assert user_aluno.role == 'ALUNO'
        client = APIClient()
        client.force_authenticate(user=user_aluno)
        res_perfil = client.get('/api/v1/alunos/perfil/me/')
        assert res_perfil.status_code == 200
        assert res_perfil.data['success'] is True
        assert res_perfil.data['data']['nome'] == 'João Mandamule'
