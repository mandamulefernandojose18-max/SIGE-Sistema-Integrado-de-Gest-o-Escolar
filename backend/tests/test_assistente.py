import datetime
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma
from apps.alunos.models import Aluno, PresencaAluno
from apps.pagamentos.models import Pagamento
from apps.assistente.models import ConsultaAssistente
from apps.assistente.engine import classificar

URL = '/api/v1/assistente/perguntar/'


@pytest.mark.django_db
class TestAssistente:
    def setup_method(self):
        plano = Plano.objects.create(nome='PLANO_ASS', preco=2000, duracao_dias=30)
        self.escola = Escola.objects.create(nome='Escola Ass', nif_cnpj='NIF_ASS1', email='ass1@sige.mz', status='ATIVA', plano=plano)
        self.outra = Escola.objects.create(nome='Outra Ass', nif_cnpj='NIF_ASS2', email='ass2@sige.mz', status='ATIVA', plano=plano)
        self.turma = Turma.objects.create(escola=self.escola, nome='A', grau_ano='7ª Classe', ano_letivo='2026')
        self.aluno = Aluno.objects.create(escola=self.escola, turma=self.turma, matricula='AS_001', nome='Aluno Um',
                                          data_nascimento='2012-01-01', genero='M')
        self.outro_aluno = Aluno.objects.create(escola=self.escola, turma=self.turma, matricula='AS_002', nome='Aluno Dois',
                                                data_nascimento='2012-01-01', genero='F')
        self.aluno_outra = Aluno.objects.create(escola=self.outra, matricula='AS_003', nome='Aluno Outra',
                                                data_nascimento='2012-01-01', genero='F')
        self.sec = self._cliente('SECRETARIA', 'sec.ass@sige.mz')

    def _cliente(self, role, email, **extra):
        u = Usuario.objects.create_user(email=email, password='PassTeste123!', role=role, escola=self.escola, **extra)
        c = APIClient()
        c.force_authenticate(u)
        return c

    def _p(self, cli, pergunta, **extra):
        return cli.post(URL, {'pergunta': pergunta, **extra}, format='json')

    def test_classificacao(self):
        assert classificar('Quantas faltas tem o aluno?')[0] == 'faltas'
        assert classificar('Há propinas em atraso?')[0] == 'propinas'
        assert classificar('Como se calcula a MFD?')[0] == 'faq_mfd'
        assert classificar('Regras de aprovação da 12ª classe')[0] == 'faq_aprovacao'
        assert classificar('qual a capital da França')[0] == 'desconhecida'

    def test_faq_nao_precisa_aluno(self):
        r = self._p(self.sec, 'Como se calcula a média trimestral (MT)?')
        assert r.status_code == 200 and r.data['intencao'] == 'faq_mt' and '2 × MAC' in r.data['resposta']
        r12 = self._p(self.sec, 'Qual a regra de aprovação na 12ª classe?')
        assert 'no máximo 2' in r12.data['resposta'] and 'zero negativas' not in r12.data['resposta']

    def test_desconhecida_nao_inventa(self):
        r = self._p(self.sec, 'qual a capital da França')
        assert r.data['intencao'] == 'desconhecida' and 'Ainda não sei' in r.data['resposta']

    def test_faltas_pede_aluno_e_estado_vazio(self):
        assert self._p(self.sec, 'Quantas faltas tem?').data['precisa_aluno'] is True
        r = self._p(self.sec, 'Quantas faltas tem?', aluno_id=str(self.aluno.id))
        assert r.data['dados']['faltas_efectivas'] == 0 and 'não tem faltas efectivas' in r.data['resposta']

    def test_faltas_reais_aula_dupla(self):
        PresencaAluno.objects.create(escola=self.escola, aluno=self.aluno, turma=self.turma, data=datetime.date.today(),
                                     status='FALTA_INJUSTIFICADA', aulas=2, aulas_justificadas=1)
        r = self._p(self.sec, 'Quantas faltas tem?', aluno_id=str(self.aluno.id))
        assert r.data['dados'] == {'faltas_efectivas': 1, 'por_justificar': 1}

    def test_propinas_reais(self):
        assert self._p(self.sec, 'tem propinas em atraso?', aluno_id=str(self.aluno.id)).data['dados']['em_atraso'] == 0
        Pagamento.objects.create(escola=self.escola, aluno=self.aluno, mes_referencia='2026-01', valor=1000, status='PENDENTE',
                                 descricao='Propina 2026-01', data_vencimento=timezone.now() - datetime.timedelta(days=30))
        r = self._p(self.sec, 'tem propinas em atraso?', aluno_id=str(self.aluno.id))
        assert r.data['dados']['em_atraso'] == 1 and r.data['dados']['valor_em_atraso'] == '1000.00'

    def test_nao_cruza_escolas_nem_id_invalido(self):
        r = self._p(self.sec, 'faltas', aluno_id=str(self.aluno_outra.id))
        assert 'Não encontrei' in r.data['resposta']
        assert self._p(self.sec, 'faltas', aluno_id='nao-e-uuid').status_code == 400

    def test_aluno_so_ve_o_proprio(self):
        cli = self._cliente('ALUNO', 'aluno.ass@sige.mz', aluno_id=self.aluno.id)
        r = self._p(cli, 'faltas', aluno_id=str(self.outro_aluno.id))  # tentativa de ver outro aluno
        assert 'Aluno Um' in r.data['resposta'] and 'Aluno Dois' not in r.data['resposta']

    def test_perfis_sem_permissao(self):
        fin = self._cliente('FINANCEIRO', 'fin.ass@sige.mz')
        assert 'permissão' in self._p(fin, 'faltas', aluno_id=str(self.aluno.id)).data['resposta']
        assert 'dados' in self._p(fin, 'propinas', aluno_id=str(self.aluno.id)).data
        prof = self._cliente('PROFESSOR', 'prof.ass@sige.mz')
        assert 'permissão' in self._p(prof, 'faltas', aluno_id=str(self.aluno.id)).data['resposta']
        assert 'permissão' in self._p(prof, 'propinas', aluno_id=str(self.aluno.id)).data['resposta']

    def test_validacao_e_auditoria(self):
        assert self._p(self.sec, '   ').status_code == 400
        assert self._p(self.sec, 'x' * 501).status_code == 400
        assert APIClient().post(URL, {'pergunta': 'faltas'}, format='json').status_code == 401
        self._p(self.sec, 'Como se calcula a MFD?')
        c = ConsultaAssistente.objects.get()
        assert c.escola == self.escola and c.intencao == 'faq_mfd'
