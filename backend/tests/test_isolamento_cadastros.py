import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.alunos.models import Aluno
from apps.professores.models import Professor
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma


@pytest.mark.django_db
class TestIsolamentoCadastros:
    """Turmas, professores e alunos de uma escola nunca aparecem nem são acessíveis noutra."""

    def setup_method(self):
        cache.clear()
        plano = Plano.objects.create(nome='PLANO_CADASTROS_TEST', preco=2000, duracao_dias=30)
        self.escola_a = Escola.objects.create(nome='Escola A', nif_cnpj='NIF_CA', email='a@sige.mz', status='ATIVA', plano=plano)
        self.escola_b = Escola.objects.create(nome='Escola B', nif_cnpj='NIF_CB', email='b@sige.mz', status='ATIVA', plano=plano)
        Usuario.objects.create_user(email='admin.ca@sige.mz', password='PassA123!', role='ADMIN_ESCOLA', escola=self.escola_a)

        self.turma_a = Turma.objects.create(escola=self.escola_a, nome='Turma A', grau_ano='10ª Classe')
        self.turma_b = Turma.objects.create(escola=self.escola_b, nome='Turma B', grau_ano='10ª Classe')
        self.prof_a = Professor.objects.create(escola=self.escola_a, nome='Prof A', email='pa@sige.mz', especialidade='Matemática')
        self.prof_b = Professor.objects.create(escola=self.escola_b, nome='Prof B', email='pb@sige.mz', especialidade='Física')
        self.aluno_b = Aluno.objects.create(
            escola=self.escola_b, turma=self.turma_b, matricula='MAT_CB_001',
            nome='Aluno B', data_nascimento='2009-01-01', genero='F',
        )

        self.client = APIClient()
        res = self.client.post('/api/v1/auth/login/', {'email': 'admin.ca@sige.mz', 'password': 'PassA123!'}, format='json')
        assert res.status_code == 200
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['token']}")

    @staticmethod
    def _ids(res):
        corpo = res.data
        itens = corpo['data'] if isinstance(corpo, dict) and 'data' in corpo else corpo
        if isinstance(itens, dict) and 'results' in itens:
            itens = itens['results']
        return {str(i['id']) for i in itens}

    def test_lista_de_turmas_so_da_propria_escola(self):
        res = self.client.get('/api/v1/turmas/')
        assert res.status_code == 200
        ids = self._ids(res)
        assert str(self.turma_a.id) in ids
        assert str(self.turma_b.id) not in ids

    def test_lista_de_professores_so_da_propria_escola(self):
        res = self.client.get('/api/v1/professores/')
        assert res.status_code == 200
        ids = self._ids(res)
        assert str(self.prof_a.id) in ids
        assert str(self.prof_b.id) not in ids

    def test_detalhe_de_outra_escola_devolve_404(self):
        assert self.client.get(f'/api/v1/turmas/{self.turma_b.id}/').status_code == 404
        assert self.client.get(f'/api/v1/professores/{self.prof_b.id}/').status_code == 404
        assert self.client.get(f'/api/v1/alunos/{self.aluno_b.id}/').status_code == 404

    def test_nao_e_possivel_alterar_nem_apagar_de_outra_escola(self):
        assert self.client.patch(f'/api/v1/turmas/{self.turma_b.id}/', {'nome': 'X'}, format='json').status_code == 404
        assert self.client.delete(f'/api/v1/professores/{self.prof_b.id}/').status_code == 404
        assert Professor.objects.filter(id=self.prof_b.id).exists()
        assert Turma.objects.get(id=self.turma_b.id).nome == 'Turma B'

    def test_sem_autenticacao_e_negado(self):
        anon = APIClient()
        for rota in ('/api/v1/turmas/', '/api/v1/professores/', '/api/v1/alunos/'):
            assert anon.get(rota).status_code in (401, 403), rota
