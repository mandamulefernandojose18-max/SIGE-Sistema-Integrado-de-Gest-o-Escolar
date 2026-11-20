"""Capacidades estatísticas e de calendário do Assistente: perfis, isolamento por escola e valores calculados."""
import datetime

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.alunos.models import Aluno
from apps.disciplinas.models import Disciplina
from apps.documentos.models import CalendarioEscolar
from apps.notas.models import Nota
from apps.professores.models import AlocacaoDocente, Professor
from apps.tenants.models import Escola
from apps.turmas.models import Turma

URL = '/api/v1/assistente/perguntar/'
HOJE = datetime.date.today()


def _escola(nome, n):
    return Escola.objects.create(nome=nome, nif_cnpj=f'NIF_EST{n}', email=f'est{n}@sige.mz', status='ATIVA', ano_letivo_ativo='2026')


@pytest.mark.django_db
class TestEstatisticas:
    def setup_method(self):
        self.escola = _escola('Escola Estat', 1)
        self.outra = _escola('Escola Alheia', 2)
        self.t7 = Turma.objects.create(escola=self.escola, nome='A', grau_ano='7ª Classe', ano_letivo='2026')
        self.t7_ant = Turma.objects.create(escola=self.escola, nome='A', grau_ano='7ª Classe', ano_letivo='2025')
        self.disc = [Disciplina.objects.create(escola=self.escola, nome=n, codigo=n[:3].upper(), classe='7ª Classe', area='Geral', ano_letivo='2026')
                     for n in ('Matemática', 'Português', 'Física')]
        mk = lambda mat, g, turma: Aluno.objects.create(escola=self.escola, turma=turma, matricula=mat, nome=f'Aluno{mat}', data_nascimento='2012-01-01', genero=g)
        self.a1, self.a2, self.a3 = mk('E1', 'M', self.t7), mk('E2', 'F', self.t7), mk('E3', 'F', self.t7)
        Aluno.objects.create(escola=self.escola, turma=self.t7, matricula='E4', nome='Saiu', data_nascimento='2012-01-01', genero='M', status='TRANSFERIDO')
        # a2 já frequentou a 7.ª em 2025 -> repetente em 2026
        self._notas(self.a2, self.t7_ant, [(12, 12, 12)] * 3)
        # a1: 3 trimestres positivos; a2: negativa a Física no 1.º trimestre → reprovada; a3 só tem o 1.º trimestre → pendente
        self._notas(self.a1, self.t7, [(14, 14, 14), (15, 15, 15), (16, 16, 16)])
        self._notas(self.a2, self.t7, [(12, 12, 12), (12, 12, 12), (6, 6, 6)])
        for d, v in zip(self.disc, (10, 11, 12)):
            Nota.objects.create(escola=self.escola, aluno=self.a3, disciplina=d, turma=self.t7, periodo='1_TRIMESTRE', media_final=v)
        self.dir = self._cli('DIRECTOR_ESCOLA', 'dir.est@sige.mz')

    def _notas(self, aluno, turma, por_disc):
        for d, medias in zip(self.disc, por_disc):
            for per, v in zip(('1_TRIMESTRE', '2_TRIMESTRE', '3_TRIMESTRE'), medias):
                Nota.objects.get_or_create(escola=self.escola, aluno=aluno, disciplina=d, turma=turma, periodo=per, defaults={'media_final': v})

    def _cli(self, role, email, escola=None, **extra):
        u = Usuario.objects.create_user(email=email, password='PassTeste123!', role=role, escola=escola or self.escola, **extra)
        c = APIClient()
        c.force_authenticate(u)
        return c

    def _r(self, cli, pergunta):
        r = cli.post(URL, {'pergunta': pergunta}, format='json')
        assert r.status_code == 200, r.data
        return r.data

    # ------------------------------------------------------------ alunos
    def test_estatistica_de_alunos_hm_e_situacao(self):
        d = self._r(self.dir, 'Estatística de alunos (H, M e HM)')
        assert d['intencao'] == 'estat_alunos'
        assert '4 HM (2 H, 2 M)' in d['resposta'] and '1 transferidos' in d['resposta']

    def test_ano_lectivo_escolhido_na_pergunta(self):
        d = self._r(self.dir, 'Estatística de alunos do ano lectivo 2025')
        assert d['intencao'] == 'estat_alunos' and 'ano lectivo 2025' in d['resposta']

    def test_aprovados_reprovados_e_repetentes(self):
        d = self._r(self.dir, 'Quantos alunos aprovados, reprovados e repetentes?')
        assert d['intencao'] == 'estat_resultados'
        assert 'aprovados 1 (1 H, 0 M)' in d['resposta'] and 'reprovados 1 (0 H, 1 M)' in d['resposta']
        assert '1 aluno(s) ainda sem as 3 notas' in d['resposta'] and 'Repetentes (mesma classe do ano 2025): 1' in d['resposta']

    def test_melhores_alunos_ordenados_pela_media(self):
        d = self._r(self.dir, 'Quais são os melhores alunos?')
        assert d['intencao'] == 'melhores_alunos' and d['resposta'].index('AlunoE1') < d['resposta'].index('AlunoE2')

    def test_comparacao_do_aproveitamento_entre_anos(self):
        d = self._r(self.dir, 'Compare o aproveitamento pedagógico entre os anos')
        assert d['intencao'] == 'aproveitamento_avancado' and '2025' in d['resposta'] and '2026' in d['resposta']

    def test_aproveitamento_por_disciplina(self):
        d = self._r(self.dir, 'Aproveitamento por disciplina')
        assert d['intencao'] == 'aproveitamento_avancado' and 'Matemática' in d['resposta']

    # ------------------------------------------------------------ pessoal
    def test_estatistica_do_pessoal(self):
        Professor.objects.create(escola=self.escola, nome='Prof H', email='ph@sige.mz', especialidade='Matemática', genero='M')
        Professor.objects.create(escola=self.escola, nome='Prof M', email='pm@sige.mz', especialidade='Física', genero='F', ativo=False)
        d = self._r(self.dir, 'Estatística do pessoal docente e não docente')
        assert d['intencao'] == 'estat_pessoal' and '1 H, 1 M' in d['resposta'] and '1 inactivo(s)' in d['resposta']

    # ------------------------------------------------------------ calendário
    def test_calendario_para_todos_os_paineis(self):
        CalendarioEscolar.objects.create(escola=self.escola, titulo='Reunião geral', tipo='REUNIAO_ENCARREGADOS', data_inicio=HOJE + datetime.timedelta(days=3))
        for role in ('ALUNO', 'ENCARREGADO', 'PROFESSOR', 'FINANCEIRO', 'SECRETARIA', 'DAP', 'DIRECTOR_ESCOLA'):
            d = self._r(self._cli(role, f'cal.{role.lower()}@sige.mz'), 'Mostre o calendário académico')
            assert d['intencao'] == 'calendario_academico', role
            assert 'Reunião geral' in d['resposta'], role

    def test_calendario_nao_mostra_eventos_de_outra_escola(self):
        CalendarioEscolar.objects.create(escola=self.outra, titulo='Evento secreto', tipo='EVENTO_ESCOLAR', data_inicio=HOJE + datetime.timedelta(days=2))
        assert 'Evento secreto' not in self._r(self.dir, 'Mostre o calendário académico')['resposta']

    # ------------------------------------------------------------ painéis de aluno/encarregado não veem estatísticas da escola
    @pytest.mark.parametrize('role', ['ALUNO', 'ENCARREGADO'])
    @pytest.mark.parametrize('pergunta', ['Estatística de alunos (H, M e HM)', 'Estatística do pessoal docente e não docente', 'Quantos alunos aprovados e reprovados?',
                                          'Quais são os melhores alunos?', 'Compare o aproveitamento pedagógico entre os anos'])
    def test_aluno_e_encarregado_nao_recebem_estatisticas(self, role, pergunta):
        d = self._r(self._cli(role, f'x.{role.lower()}@sige.mz'), pergunta)
        assert d['intencao'] in ('fora_do_painel', 'desconhecida') or d['intencao'].startswith('consulta') or 'HM' not in d['resposta']
        assert 'AlunoE1' not in d['resposta'] and '4 HM' not in d['resposta']

    # ------------------------------------------------------------ professor só vê o que lhe pertence
    def test_professor_so_ve_as_suas_turmas(self):
        prof = Professor.objects.create(escola=self.escola, nome='Prof Teste', email='prof.est@sige.mz', especialidade='Matemática')
        outra = Turma.objects.create(escola=self.escola, nome='B', grau_ano='8ª Classe', ano_letivo='2026')
        Aluno.objects.create(escola=self.escola, turma=outra, matricula='E9', nome='AlunoOutra', data_nascimento='2011-01-01', genero='M')
        AlocacaoDocente.objects.create(escola=self.escola, professor=prof, disciplina=self.disc[0], turma=self.t7)
        cli = APIClient()
        cli.force_authenticate(Usuario.objects.get(professor_id=prof.id))
        d = self._r(cli, 'Estatística de alunos (H, M e HM)')
        assert '4 HM' in d['resposta'] and '8.ª' not in d['resposta'] and '8ª' not in d['resposta']
        d = self._r(cli, 'Aproveitamento por disciplina')
        assert 'Matemática' in d['resposta'] and 'Português' not in d['resposta']

    # ------------------------------------------------------------ sugestões
    def test_sugestoes_incluem_calendario_e_estatistica(self):
        s = self.dir.get('/api/v1/assistente/sugestoes/').data['sugestoes']
        assert any('calendário' in x.lower() for x in s) and len(s) <= 8
        aluno = self._cli('ALUNO', 'sug.aluno@sige.mz').get('/api/v1/assistente/sugestoes/').data['sugestoes']
        assert any('calendário' in x.lower() for x in aluno) and not any('aprovados' in x.lower() for x in aluno)


@pytest.mark.django_db
class TestPlataforma:
    def setup_method(self):
        self.escola = _escola('Escola Plat', 3)
        t = Turma.objects.create(escola=self.escola, nome='A', grau_ano='7ª Classe', ano_letivo='2026')
        Aluno.objects.create(escola=self.escola, turma=t, matricula='P1', nome='AlunoP1', data_nascimento='2012-01-01', genero='F')
        u = Usuario.objects.create_user(email='super.est@sige.mz', password='PassTeste123!', role='SUPERADMIN')
        self.cli = APIClient()
        self.cli.force_authenticate(u)

    def _r(self, p):
        r = self.cli.post(URL, {'pergunta': p}, format='json')
        assert r.status_code == 200, r.data
        return r.data

    def test_superadmin_novas_sugestoes_de_plataforma(self):
        s = self.cli.get('/api/v1/assistente/sugestoes/').data['sugestoes']
        assert len(s) <= 8 and any('província' in x for x in s)

    def test_escolas_por_provincia(self):
        d = self._r('Quantas escolas e alunos há por província?')
        assert d['intencao'] == 'plat_provincias' and '1 M' in d['resposta']

    def test_ranking_de_escolas(self):
        d = self._r('Quais as escolas com mais alunos?')
        assert d['intencao'] == 'plat_ranking' and 'Escola Plat (1)' in d['resposta']

    def test_calendario_da_plataforma_sem_eventos(self):
        d = self._r('Mostre o calendário académico')
        assert d['intencao'] == 'plat_calendario' and 'Nenhuma escola' in d['resposta']
