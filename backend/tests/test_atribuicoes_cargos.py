import pytest
from rest_framework.test import APIClient
from apps.accounts.models import Usuario
from apps.disciplinas.models import Disciplina
from apps.professores.models import Professor
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma


def _cliente(email, senha):
    c = APIClient()
    res = c.post('/api/v1/auth/login/', {'email': email, 'password': senha}, format='json')
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['token']}")
    return c


@pytest.mark.django_db
class TestAtribuicoesCargos:
    def setup_method(self):
        plano = Plano.objects.create(nome='PLANO_ATRIB', preco=2000, duracao_dias=30)
        self.escola = Escola.objects.create(nome='Escola A', nif_cnpj='NIF_AT_A', email='a@sige.mz', status='ATIVA', plano=plano)
        self.outra = Escola.objects.create(nome='Escola B', nif_cnpj='NIF_AT_B', email='b@sige.mz', status='ATIVA', plano=plano)
        Usuario.objects.create_user(email='dap@sige.mz', password='Dap12345!', role='DAP', escola=self.escola)
        self.prof = Professor.objects.create(escola=self.escola, nome='Prof', apelido='Um', email='p1@sige.mz', especialidade='Matemática')
        self.prof_outro = Professor.objects.create(escola=self.outra, nome='Prof', apelido='Dois', email='p2@sige.mz', especialidade='Física')
        self.user_prof = Usuario.objects.get(professor_id=self.prof.id)
        self.user_prof.set_password('Prof12345!')
        self.user_prof.save()
        self.turma = Turma.objects.create(escola=self.escola, nome='10ª A', grau_ano='10ª Classe', ano_letivo='2026')
        self.disc = Disciplina.objects.create(escola=self.escola, nome='Matemática', codigo='MAT', classe='10ª Classe', ano_letivo='2026')

    def test_sugestoes_e_atribuicao_multipla(self):
        c = _cliente('dap@sige.mz', 'Dap12345!')
        res = c.get('/api/v1/atribuicoes/sugestoes/?cargo=DIRECTOR_TURMA')
        assert res.status_code == 200 and len(res.data['data']) > 3
        res = c.post('/api/v1/atribuicoes/', {
            'cargo': 'DIRECTOR_TURMA', 'professor_id': str(self.prof.id), 'turma_id': str(self.turma.id),
            'atividades': [
                {'titulo': 'Conferir a pauta', 'prazo': '2026-12-01'},
                {'titulo': 'Actividade própria da escola', 'guardar_modelo': True},
            ]}, format='json')
        assert res.status_code == 201 and len(res.data['data']) == 2
        # a actividade própria passa a fazer parte das sugestões
        titulos = [s['titulo'] for s in c.get('/api/v1/atribuicoes/sugestoes/?cargo=DIRECTOR_TURMA').data['data']]
        assert 'Actividade própria da escola' in titulos
        assert c.get('/api/v1/atribuicoes/?ano=2026&cargo=DIRECTOR_TURMA').data['total'] == 2

    def test_delegado_exige_disciplina(self):
        c = _cliente('dap@sige.mz', 'Dap12345!')
        base = {'cargo': 'DELEGADO_DISCIPLINA', 'professor_id': str(self.prof.id), 'atividades': [{'titulo': 'X'}]}
        assert c.post('/api/v1/atribuicoes/', base, format='json').status_code == 400
        base['disciplina_id'] = str(self.disc.id)
        assert c.post('/api/v1/atribuicoes/', base, format='json').status_code == 201

    def test_professor_so_ve_e_actualiza_as_suas(self):
        dap = _cliente('dap@sige.mz', 'Dap12345!')
        dap.post('/api/v1/atribuicoes/', {
            'cargo': 'DIRECTOR_CLASSE', 'professor_id': str(self.prof.id), 'classe': '10ª Classe', 'ano_letivo': '2026',
            'atividades': [{'titulo': 'Reunião de classe'}]}, format='json')
        c = _cliente(self.user_prof.email, 'Prof12345!')
        lista = c.get('/api/v1/atribuicoes/').data['data']
        assert len(lista) == 1
        assert c.post('/api/v1/atribuicoes/', {}, format='json').status_code == 403
        res = c.patch(f"/api/v1/atribuicoes/{lista[0]['id']}/", {'estado': 'CONCLUIDA', 'titulo': 'hack'}, format='json')
        assert res.data['data']['estado'] == 'CONCLUIDA' and res.data['data']['titulo'] == 'Reunião de classe'

    def test_isolamento_entre_escolas(self):
        c = _cliente('dap@sige.mz', 'Dap12345!')
        res = c.post('/api/v1/atribuicoes/', {
            'cargo': 'DIRECTOR_CLASSE', 'professor_id': str(self.prof_outro.id), 'classe': '10ª Classe', 'ano_letivo': '2026',
            'atividades': [{'titulo': 'X'}]}, format='json')
        assert res.status_code == 400
