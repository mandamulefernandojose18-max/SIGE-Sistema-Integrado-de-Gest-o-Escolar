import datetime
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano, AssinaturaEscola
from apps.turmas.models import Turma
from apps.alunos.models import Aluno, PresencaAluno, TransferenciaAnulacao
from apps.pagamentos.models import Pagamento, TransacaoFinanceira
from apps.professores.models import Professor
from apps.atribuicoes.models import AtribuicaoCargo
from apps.crm.models import Atendimento, VinculoEncarregado
from apps.documentos.models import ComunicadoEscolar, CalendarioEscolar
from apps.pautas.models import Pauta

URL = '/api/v1/assistente/alertas/'
HOJE = datetime.date.today()


@pytest.mark.django_db
class TestAlertas:
    def setup_method(self):
        self.plano = Plano.objects.create(nome='PLANO_ALR', preco=2000, duracao_dias=30)
        self.escola = Escola.objects.create(nome='Escola Alr', nif_cnpj='NIF_ALR1', email='alr1@sige.mz', status='ATIVA', plano=self.plano)
        self.outra = Escola.objects.create(nome='Outra Alr', nif_cnpj='NIF_ALR2', email='alr2@sige.mz', status='ATIVA', plano=self.plano)
        self.turma = Turma.objects.create(escola=self.escola, nome='A', grau_ano='7ª Classe', ano_letivo='2026')
        self.aluno = Aluno.objects.create(escola=self.escola, turma=self.turma, matricula='AL_001', nome='Aluno Um', data_nascimento='2012-01-01', genero='M')
        self.irmao = Aluno.objects.create(escola=self.escola, turma=self.turma, matricula='AL_002', nome='Aluno Dois', data_nascimento='2012-01-01', genero='F')
        self.aluno_outra = Aluno.objects.create(escola=self.outra, matricula='AL_009', nome='Aluno Outra', data_nascimento='2012-01-01', genero='F')

    def _cli(self, role, email, escola=None, **extra):
        u = Usuario.objects.create_user(email=email, password='PassTeste123!', role=role, escola=escola or self.escola, **extra)
        c = APIClient()
        c.force_authenticate(u)
        return c

    def _get(self, cli):
        r = cli.get(URL)
        assert r.status_code == 200
        return r.data

    def _titulos(self, cli):
        return [a['titulo'] for a in self._get(cli)['alertas']]

    def _atraso(self, aluno, mes, valor=1000, dias=30):
        Pagamento.objects.create(escola=aluno.escola, aluno=aluno, mes_referencia=mes, valor=valor, status='PENDENTE', descricao=f'Propina {mes}',
                                 data_vencimento=timezone.now() - datetime.timedelta(days=dias))

    def test_sem_login_e_sem_dados(self):
        assert APIClient().get(URL).status_code == 401
        d = self._get(self._cli('DIRECTOR_ESCOLA', 'dir.alr@sige.mz'))
        assert d == {'alertas': [], 'total': 0, 'urgentes': 0}          # nada a assinalar → lista vazia (sem inventar)

    def test_encarregado_ve_alertas_de_cada_educando(self):
        enc = self._cli('ENCARREGADO', 'enc.alr@sige.mz')
        for a in (self.aluno, self.irmao):
            VinculoEncarregado.objects.create(escola=self.escola, usuario=Usuario.objects.get(email='enc.alr@sige.mz'), aluno=a)
        self._atraso(self.aluno, '2026-01'), self._atraso(self.aluno, '2026-02'), self._atraso(self.irmao, '2026-03', valor=700)
        PresencaAluno.objects.create(escola=self.escola, aluno=self.irmao, turma=self.turma, data=HOJE, status='FALTA_INJUSTIFICADA', aulas=2)
        d = self._get(enc)
        titulos = [a['titulo'] for a in d['alertas']]
        assert 'Aluno Um: 2 propina(s) em atraso' in titulos and 'Aluno Dois: 1 propina(s) em atraso' in titulos
        assert 'Aluno Dois: 2 falta(s) por justificar' in titulos
        assert d['alertas'][0]['nivel'] == 'alta' and d['urgentes'] == 1      # 2 propinas em atraso = urgente; ordenado por urgência
        assert all('Aluno Outra' not in t for t in titulos)

    def test_aluno_ve_so_o_seu_com_voce(self):
        al = self._cli('ALUNO', 'aluno.alr@sige.mz', aluno_id=self.aluno.id)
        self._atraso(self.aluno, '2026-01'), self._atraso(self.irmao, '2026-02')
        assert self._titulos(al) == ['Você: 1 propina(s) em atraso']

    def test_notas_negativas_so_publicadas(self):
        from apps.disciplinas.models import Disciplina
        from apps.notas.models import Nota
        mat = Disciplina.objects.create(escola=self.escola, nome='Matemática', codigo='MAT', classe='7ª Classe', area='Geral', ano_letivo='2026')
        Nota.objects.create(escola=self.escola, aluno=self.aluno, disciplina=mat, turma=self.turma, periodo='1_TRIMESTRE', media_final=7)
        al = self._cli('ALUNO', 'aluno.neg@sige.mz', aluno_id=self.aluno.id)
        assert any('negativa(s) no 1.º trimestre' in t for t in self._titulos(al))
        self.escola.permitir_visualizacao_notas = False
        self.escola.save()
        assert not any('negativa' in t for t in self._titulos(al))

    def test_gestao_ve_transferencias_crm_risco_e_isolamento(self):
        sec = self._cli('SECRETARIA', 'sec.alr@sige.mz')
        adm = Usuario.objects.get(email='sec.alr@sige.mz')
        TransferenciaAnulacao.objects.create(escola=self.escola, aluno=self.aluno, tipo='ANULACAO_MATRICULA', motivo='x', solicitado_por=adm)
        Atendimento.objects.create(escola=self.escola, assunto='Pedido', prioridade='ALTA')
        for i in range(6):
            PresencaAluno.objects.create(escola=self.escola, aluno=self.aluno, turma=self.turma, data=HOJE - datetime.timedelta(days=i + 1),
                                         status='FALTA_INJUSTIFICADA', aulas=2)
        # dados de OUTRA escola não aparecem
        TransferenciaAnulacao.objects.create(escola=self.outra, aluno=self.aluno_outra, tipo='ANULACAO_MATRICULA', motivo='x', solicitado_por=adm)
        Atendimento.objects.create(escola=self.outra, assunto='Outra')
        titulos = self._titulos(sec)
        assert '1 transferência(s)/anulação(ões) pendente(s)' in titulos
        assert '1 atendimento(s) por resolver' in titulos and '1 aluno(s) em risco de evasão' in titulos
        # a secretaria não vê alertas da Direcção
        assert not any('assinatura' in t or 'pauta' in t or 'Director' in t for t in titulos)

    def test_direccao_pautas_assinatura_e_despesas(self):
        dirc = self._cli('DIRECTOR_ESCOLA', 'dir2.alr@sige.mz')
        Pauta.objects.create(escola=self.escola, turma=self.turma, ano_letivo='2026', periodo='1_TRIMESTRE', status='ABERTA')
        AssinaturaEscola.objects.create(escola=self.escola, plano=self.plano, data_fim=timezone.now() + datetime.timedelta(days=5), valor=100)
        TransacaoFinanceira.objects.create(escola=self.escola, tipo='DESPESA', categoria='Material', descricao='Giz', valor=10, data=HOJE, status_aprovacao='PENDENTE')
        titulos = self._titulos(dirc)
        assert '1 pauta(s) por fechar' in titulos
        assert 'A assinatura do sistema termina em 5 dia(s)' in titulos
        assert '1 movimento(s) a aguardar a aprovação do Director' in titulos
        AssinaturaEscola.objects.filter(escola=self.escola).update(data_inicio=timezone.now() - datetime.timedelta(days=40),
                                                                   data_fim=timezone.now() - datetime.timedelta(days=3))
        assert any(a['nivel'] == 'alta' and 'terminou' in a['titulo'] for a in self._get(dirc)['alertas'])

    def test_professor_so_as_suas_actividades_e_financeiro_propinas(self):
        prof = Professor.objects.create(escola=self.escola, nome='Prof', email='prof.alr@sige.mz', especialidade='Matemática')
        outro = Professor.objects.create(escola=self.escola, nome='Outro', email='outro.alr@sige.mz', especialidade='Física')
        for p, n in ((prof, 1), (outro, 3)):
            for i in range(n):
                AtribuicaoCargo.objects.create(escola=self.escola, ano_letivo='2026', cargo='DIRECTOR_TURMA', professor=p, turma=self.turma,
                                               titulo=f'Act {p.nome}{i}', prazo=HOJE - datetime.timedelta(days=2))
        cli = APIClient()
        cli.force_authenticate(Usuario.objects.get(professor_id=prof.id))
        assert self._titulos(cli) == ['1 actividade(s) de cargo com o prazo ultrapassado']
        self._atraso(self.aluno, '2026-01', valor=500)
        fin = self._cli('FINANCEIRO', 'fin.alr@sige.mz')
        assert '1 propina(s) em atraso de 1 aluno(s)' in self._titulos(fin)
        assert not any('transfer' in t or 'pauta' in t for t in self._titulos(fin))

    def test_comunicados_por_publico_e_calendario(self):
        ComunicadoEscolar.objects.create(escola=self.escola, titulo='Só professores', conteudo='x', publico_alvo='PROFESSORES', status='PUBLICADO')
        ComunicadoEscolar.objects.create(escola=self.escola, titulo='Para todos', conteudo='x', publico_alvo='TODOS', status='PUBLICADO', prioridade='URGENTE')
        ComunicadoEscolar.objects.create(escola=self.outra, titulo='De outra escola', conteudo='x', publico_alvo='TODOS', status='PUBLICADO')
        CalendarioEscolar.objects.create(escola=self.escola, titulo='Reunião de pais', tipo='AVALIACAO_TESTE', data_inicio=HOJE + datetime.timedelta(days=2))
        al = self._cli('ALUNO', 'aluno.com2@sige.mz', aluno_id=self.aluno.id)
        d = self._get(al)['alertas']
        com = next(a for a in d if 'comunicado' in a['titulo'])
        assert com['nivel'] == 'media' and 'Para todos' in com['detalhe'] and 'Só professores' not in com['detalhe'] and 'outra escola' not in com['detalhe']
        cal = next(a for a in d if 'calendário' in a['titulo'])
        assert cal['destino'] == 'aluno-calendario' and 'Reunião de pais' in cal['detalhe']
        prof = self._cli('PROFESSOR', 'prof2.alr@sige.mz')
        assert 'Só professores' in next(a for a in self._get(prof)['alertas'] if 'comunicado' in a['titulo'])['detalhe']

    def test_limite_de_alertas(self):
        sec = self._cli('DIRECTOR_ESCOLA', 'dir3.alr@sige.mz')
        assert self._get(sec)['total'] <= 12
