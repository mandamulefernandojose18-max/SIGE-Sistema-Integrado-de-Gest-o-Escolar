import pytest
from rest_framework.test import APIClient
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma
from apps.alunos.models import Aluno


@pytest.mark.django_db
class TestAlunoMeAnosFaltas:
    def setup_method(self):
        self.client = APIClient()
        plano = Plano.objects.create(nome='PLANO_ME_TEST', preco=2000, duracao_dias=30)
        self.escola = Escola.objects.create(nome='Escola Me', nif_cnpj='NIF_ME', email='me@sige.mz', status='ATIVA', plano=plano)
        self.turma = Turma.objects.create(escola=self.escola, nome='A', grau_ano='7ª Classe', ano_letivo='2026')
        self.aluno = Aluno.objects.create(escola=self.escola, turma=self.turma, matricula='ME_001', nome='Teste Me',
                                          data_nascimento='2012-01-01', genero='M')
        self.user = Usuario.objects.get(aluno_id=self.aluno.id)
        self.client.force_authenticate(self.user)

    def test_anos_devolve_so_classe_real(self):
        res = self.client.get('/api/v1/alunos/me/anos')
        assert res.status_code == 200
        assert [(a['ano'], a['classe']) for a in res.data['data']] == [('2026', '7ª Classe')]

    def test_faltas_pdf(self):
        res = self.client.get('/api/v1/alunos/me/faltas/pdf?ano=2026')
        assert res.status_code == 200
        assert res['Content-Type'] == 'application/pdf'
        assert res.content.startswith(b'%PDF')

    def test_faltas_pdf_ano_sem_matricula(self):
        res = self.client.get('/api/v1/alunos/me/faltas/pdf?ano=2019')
        assert res.status_code == 400
