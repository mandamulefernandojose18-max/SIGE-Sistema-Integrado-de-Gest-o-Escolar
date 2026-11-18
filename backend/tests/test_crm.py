import datetime
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma
from apps.alunos.models import Aluno, PresencaAluno
from apps.pagamentos.models import Pagamento
from apps.crm.models import Atendimento, Comunicacao


def _res(r):
    d = r.data
    return d['results'] if isinstance(d, dict) and 'results' in d else d


@pytest.mark.django_db
class TestCRM:
    def setup_method(self):
        plano = Plano.objects.create(nome='PLANO_CRM', preco=2000, duracao_dias=30)
        self.escola = Escola.objects.create(nome='Escola CRM', nif_cnpj='NIF_CRM1', email='crm1@sige.mz', status='ATIVA', plano=plano)
        self.outra = Escola.objects.create(nome='Outra CRM', nif_cnpj='NIF_CRM2', email='crm2@sige.mz', status='ATIVA', plano=plano)
        self.turma = Turma.objects.create(escola=self.escola, nome='A', grau_ano='7ª Classe', ano_letivo='2026')
        self.aluno = Aluno.objects.create(escola=self.escola, turma=self.turma, matricula='CRM_001', nome='Aluno CRM',
                                          data_nascimento='2012-01-01', genero='M', nome_responsavel='Encarregado X',
                                          contato_responsavel='840000000')
        self.aluno_outra = Aluno.objects.create(escola=self.outra, matricula='CRM_002', nome='Aluno Outra',
                                                data_nascimento='2012-01-01', genero='F')
        self.sec = self._cliente('SECRETARIA', 'sec.crm@sige.mz', self.escola)
        self.sec_outra = self._cliente('SECRETARIA', 'sec.crm2@sige.mz', self.outra)

    def _cliente(self, role, email, escola):
        u = Usuario.objects.create_user(email=email, password='PassTeste123!', role=role, escola=escola)
        c = APIClient()
        c.force_authenticate(u)
        return c

    def test_atendimento_ciclo_e_resolver(self):
        r = self.sec.post('/api/v1/crm/atendimentos/', {'aluno': str(self.aluno.id), 'assunto': 'Pedido de declaração'}, format='json')
        assert r.status_code == 201
        aid = r.data['id']
        assert self.sec.post(f'/api/v1/crm/atendimentos/{aid}/resolver/', {}, format='json').status_code == 400
        assert self.sec.post(f'/api/v1/crm/atendimentos/{aid}/resolver/', {'resolucao': 'Entregue'}, format='json').status_code == 200
        assert Atendimento.objects.get().estado == 'RESOLVIDO'
        assert self.sec.post(f'/api/v1/crm/atendimentos/{aid}/resolver/', {'resolucao': 'x'}, format='json').status_code == 400

    def test_atendimento_nao_cruza_escolas(self):
        r = self.sec.post('/api/v1/crm/atendimentos/', {'aluno': str(self.aluno_outra.id), 'assunto': 'X'}, format='json')
        assert r.status_code == 400
        self.sec.post('/api/v1/crm/atendimentos/', {'assunto': 'Meu'}, format='json')
        assert len(_res(self.sec_outra.get('/api/v1/crm/atendimentos/'))) == 0

    def test_professor_sem_acesso(self):
        prof = self._cliente('PROFESSOR', 'prof.crm@sige.mz', self.escola)
        assert prof.get('/api/v1/crm/atendimentos/').status_code == 403
        assert prof.get('/api/v1/crm/alertas-evasao/').status_code == 403

    def test_comunicacao_regista_destinatario_e_isola(self):
        r = self.sec.post('/api/v1/crm/comunicacoes/', {'aluno': str(self.aluno.id), 'tipo': 'FALTAS', 'mensagem': 'Faltas em excesso'}, format='json')
        assert r.status_code == 201 and r.data['destinatario'] == 'Encarregado X'
        assert self.sec.post('/api/v1/crm/comunicacoes/', {'aluno': str(self.aluno_outra.id), 'mensagem': 'x'}, format='json').status_code == 400
        assert len(_res(self.sec_outra.get('/api/v1/crm/comunicacoes/'))) == 0
        assert Comunicacao.objects.count() == 1

    def test_ficha_360_estado_vazio_e_isolamento(self):
        r = self.sec.get(f'/api/v1/crm/encarregado/{self.aluno.id}/')
        assert r.status_code == 200
        assert r.data['faltas_efectivas'] == 0 and r.data['propinas_em_atraso']['quantidade'] == 0
        assert r.data['encarregado']['nome'] == 'Encarregado X'
        assert self.sec_outra.get(f'/api/v1/crm/encarregado/{self.aluno.id}/').status_code == 404

    def test_alertas_evasao_faltas_e_propinas(self):
        assert self.sec.get('/api/v1/crm/alertas-evasao/').data['total'] == 0
        hoje = datetime.date.today()
        for i in range(3):
            PresencaAluno.objects.create(escola=self.escola, aluno=self.aluno, turma=self.turma,
                                         data=hoje - datetime.timedelta(days=i + 1), status='FALTA_INJUSTIFICADA', aulas=2)
        r = self.sec.get('/api/v1/crm/alertas-evasao/?min_faltas=5&ano_letivo=2026')
        assert r.data['total'] == 1 and r.data['resultados'][0]['faltas_efectivas'] == 6
        assert r.data['resultados'][0]['motivos'] == ['FALTAS']
        for m in ('2026-01', '2026-02'):
            Pagamento.objects.create(escola=self.escola, aluno=self.aluno, mes_referencia=m, valor=1000, status='PENDENTE', descricao=f'Propina {m}',
                                     data_vencimento=timezone.now() - datetime.timedelta(days=30))
        r = self.sec.get('/api/v1/crm/alertas-evasao/?min_faltas=5&ano_letivo=2026')
        assert r.data['resultados'][0]['motivos'] == ['FALTAS', 'PROPINAS']
        assert self.sec_outra.get('/api/v1/crm/alertas-evasao/?min_faltas=1').data['total'] == 0
