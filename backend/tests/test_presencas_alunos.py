import pytest
from rest_framework.test import APIClient
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma
from apps.alunos.models import Aluno, PresencaAluno
from apps.disciplinas.models import Disciplina
from apps.professores.models import Professor, AlocacaoDocente


@pytest.mark.django_db
class TestPresencasAlunos:
    def setup_method(self):
        plano = Plano.objects.create(nome='PLANO_PRES_TEST', preco=2000, duracao_dias=30)
        self.escola = Escola.objects.create(nome='Escola Pres', nif_cnpj='NIF_PRES', email='pres@sige.mz', status='ATIVA', plano=plano)
        self.turma26 = Turma.objects.create(escola=self.escola, nome='A', grau_ano='7ª Classe', ano_letivo='2026')
        self.turma25 = Turma.objects.create(escola=self.escola, nome='B', grau_ano='7ª Classe', ano_letivo='2025')
        self.disc = Disciplina.objects.create(escola=self.escola, nome='Matemática', codigo='MAT', classe='7ª Classe', area='Geral')
        self.outra_disc = Disciplina.objects.create(escola=self.escola, nome='Física', codigo='FIS', classe='7ª Classe', area='Geral')
        self.aluno = Aluno.objects.create(escola=self.escola, turma=self.turma26, matricula='PR_001', nome='Aluno Um',
                                          data_nascimento='2012-01-01', genero='M')
        prof = Professor.objects.create(escola=self.escola, nome='Prof', email='prof.pres@sige.mz', especialidade='Matemática')
        AlocacaoDocente.objects.create(escola=self.escola, professor=prof, disciplina=self.disc, turma=self.turma26)
        self.user = Usuario.objects.get(professor_id=prof.id)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _lote(self, **extra):
        body = {'turma': str(self.turma26.id), 'disciplina': str(self.disc.id), 'data': '2026-03-02',
                'registos': [{'aluno': str(self.aluno.id), 'status': 'FALTA_INJUSTIFICADA', 'observacao': 'sem aviso'}]}
        body.update(extra)
        return self.client.post('/api/v1/alunos/presencas/lote/', body, format='json')

    def test_lote_regista_e_actualiza(self):
        assert self._lote().status_code == 200
        assert self._lote(registos=[{'aluno': str(self.aluno.id), 'status': 'PRESENTE'}]).status_code == 200
        assert PresencaAluno.objects.count() == 1
        assert PresencaAluno.objects.get().status == 'PRESENTE'

    def test_professor_nao_lanca_em_disciplina_nao_atribuida(self):
        assert self._lote(disciplina=str(self.outra_disc.id)).status_code == 403

    def test_nao_aceita_data_futura(self):
        assert self._lote(data='2999-01-01').status_code == 400

    def test_listagem_filtra_por_ano_lectivo(self):
        self._lote()
        r26 = self.client.get('/api/v1/alunos/presencas/?ano_letivo=2026&turma_id=%s' % self.turma26.id)
        r25 = self.client.get('/api/v1/alunos/presencas/?ano_letivo=2025')
        assert r26.status_code == 200 and r25.status_code == 200
        n = lambda r: len(r.data['results'] if isinstance(r.data, dict) and 'results' in r.data else r.data)
        assert n(r26) == 1
        assert n(r25) == 0

    def _cliente(self, role, email):
        u = Usuario.objects.create_user(email=email, password='PassTeste123!', role=role, escola=self.escola)
        c = APIClient()
        c.force_authenticate(u)
        return c

    def test_secretaria_justifica_falta_injustificada(self):
        self._lote()
        reg = PresencaAluno.objects.get()
        sec = self._cliente('SECRETARIA', 'sec.just@sige.mz')
        assert sec.post(f'/api/v1/alunos/presencas/{reg.id}/justificar/', {}, format='json').status_code == 400
        r = sec.post(f'/api/v1/alunos/presencas/{reg.id}/justificar/', {'motivo': 'doença'}, format='json')
        assert r.status_code == 200
        reg.refresh_from_db()
        assert reg.status == 'FALTA_JUSTIFICADA' and reg.justificacao == 'doença' and reg.justificada_em
        # já justificada: não repete
        assert sec.post(f'/api/v1/alunos/presencas/{reg.id}/justificar/', {'motivo': 'x'}, format='json').status_code == 400

    def test_professor_nao_justifica(self):
        self._lote()
        reg = PresencaAluno.objects.get()
        r = self.client.post(f'/api/v1/alunos/presencas/{reg.id}/justificar/', {'motivo': 'x'}, format='json')
        assert r.status_code == 403

    def test_justificar_nao_cruza_escolas(self):
        self._lote()
        reg = PresencaAluno.objects.get()
        plano = Plano.objects.create(nome='PLANO_PRES_2', preco=2000, duracao_dias=30)
        outra = Escola.objects.create(nome='Outra', nif_cnpj='NIF_OUTRA', email='outra@sige.mz', status='ATIVA', plano=plano)
        u = Usuario.objects.create_user(email='sec.outra@sige.mz', password='PassTeste123!', role='SECRETARIA', escola=outra)
        c = APIClient()
        c.force_authenticate(u)
        assert c.post(f'/api/v1/alunos/presencas/{reg.id}/justificar/', {'motivo': 'x'}, format='json').status_code == 404

    def test_resumo_agrega_faltas(self):
        self._lote()
        r = self.client.get('/api/v1/alunos/presencas/resumo/?ano_letivo=2026')
        assert r.status_code == 200
        linha = r.data['resultados'][0]
        assert linha['total'] == 1 and linha['injustificadas'] == 1 and linha['percent_faltas'] == 100.0
        assert self.client.get('/api/v1/alunos/presencas/resumo/?ano_letivo=2025').data['resultados'] == []

    def test_perfil_sem_permissao_nao_lanca(self):
        sec = Usuario.objects.create_user(email='sec.pres@sige.mz', password='PassSec123!', role='SECRETARIA', escola=self.escola)
        c = APIClient()
        c.force_authenticate(sec)
        res = c.post('/api/v1/alunos/presencas/lote/', {'turma': str(self.turma26.id), 'disciplina': str(self.disc.id),
                     'data': '2026-03-02', 'registos': []}, format='json')
        assert res.status_code == 403
