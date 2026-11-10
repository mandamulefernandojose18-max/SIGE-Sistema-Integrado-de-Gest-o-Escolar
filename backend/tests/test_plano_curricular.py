import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.disciplinas.models import AreaSeccao, Disciplina
from apps.tenants.models import Escola, Plano


@pytest.mark.django_db
class TestPlanoCurricular:
    """Classe/Nível -> Disciplinas -> Área/Secção -> disciplinas da área (com exame) e ligação às turmas."""

    def setup_method(self):
        cache.clear()
        plano = Plano.objects.create(nome='PLANO_CURRICULAR_TEST', preco=2000, duracao_dias=30)
        self.escola = Escola.objects.create(
            nome='Escola PC', nif_cnpj='NIF_PC', email='pc@sige.mz', status='ATIVA', plano=plano,
            config_classes_exames={'11ª Classe': False, '12ª Classe': True},
        )
        self.outra = Escola.objects.create(
            nome='Escola Outra', nif_cnpj='NIF_PO', email='po@sige.mz', status='ATIVA', plano=plano,
            config_classes_exames={'11ª Classe': True},
        )
        Usuario.objects.create_user(email='admin.pc@sige.mz', password='PassA123!', role='ADMIN_ESCOLA', escola=self.escola)
        Usuario.objects.create_user(email='prof.pc@sige.mz', password='PassA123!', role='PROFESSOR', escola=self.escola)
        self.client = self._login('admin.pc@sige.mz')

    def _login(self, email):
        c = APIClient()
        res = c.post('/api/v1/auth/login/', {'email': email, 'password': 'PassA123!'}, format='json')
        assert res.status_code == 200
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['token']}")
        return c

    def _disc(self, classe, codigo, nome, escola=None):
        return Disciplina.objects.create(escola=escola or self.escola, classe=classe, codigo=codigo, nome=nome)

    def _area(self, classe, nome):
        res = self.client.post('/api/v1/plano-curricular/areas/', {'classe': classe, 'nome': nome}, format='json')
        assert res.status_code == 201, res.data
        return res.data['data']['id']

    def test_estrutura_lista_classes_com_exame_e_areas(self):
        self._area('12ª Classe', 'Ciências')
        res = self.client.get('/api/v1/plano-curricular/estrutura/')
        assert res.status_code == 200
        classes = {c['nome']: c for c in res.data['data']['classes']}
        assert classes['11ª Classe']['tem_exame'] is False
        assert classes['12ª Classe']['tem_exame'] is True
        assert [a['nome'] for a in classes['12ª Classe']['areas']] == ['Ciências']

    def test_area_exige_classe_cadastrada_e_nome_unico(self):
        r = self.client.post('/api/v1/plano-curricular/areas/', {'classe': '9ª Classe', 'nome': 'Letras'}, format='json')
        assert r.status_code == 400
        self._area('11ª Classe', 'Letras')
        r2 = self.client.post('/api/v1/plano-curricular/areas/', {'classe': '11ª Classe', 'nome': 'letras'}, format='json')
        assert r2.status_code == 400

    def test_disciplinas_da_area_so_da_propria_classe(self):
        d11 = self._disc('11ª Classe', 'MAT11', 'Matemática')
        d12 = self._disc('12ª Classe', 'MAT12', 'Matemática 12')
        area = self._area('11ª Classe', 'Ciências')
        ok = self.client.put(f'/api/v1/plano-curricular/areas/{area}/disciplinas/',
                             {'disciplinas': [{'disciplina': str(d11.id), 'tem_exame': False}]}, format='json')
        assert ok.status_code == 200
        errada = self.client.put(f'/api/v1/plano-curricular/areas/{area}/disciplinas/',
                                 {'disciplinas': [{'disciplina': str(d12.id), 'tem_exame': False}]}, format='json')
        assert errada.status_code == 400

    def test_exame_so_permitido_se_a_classe_tem_exame(self):
        d11 = self._disc('11ª Classe', 'FIS11', 'Física')
        a11 = self._area('11ª Classe', 'Ciências')
        r = self.client.put(f'/api/v1/plano-curricular/areas/{a11}/disciplinas/',
                            {'disciplinas': [{'disciplina': str(d11.id), 'tem_exame': True}]}, format='json')
        assert r.status_code == 400

        d12 = self._disc('12ª Classe', 'FIS12', 'Física 12')
        a12 = self._area('12ª Classe', 'Ciências')
        r2 = self.client.put(f'/api/v1/plano-curricular/areas/{a12}/disciplinas/',
                             {'disciplinas': [{'disciplina': str(d12.id), 'tem_exame': True}]}, format='json')
        assert r2.status_code == 200
        d12.refresh_from_db()
        assert d12.tem_exame is True and d12.area == 'Ciências'

        # Retirar a disciplina da área repõe os valores gerais.
        self.client.put(f'/api/v1/plano-curricular/areas/{a12}/disciplinas/', {'disciplinas': []}, format='json')
        d12.refresh_from_db()
        assert d12.tem_exame is False and d12.area == 'Geral'

    def test_plano_da_classe_devolve_disciplinas_e_areas(self):
        d = self._disc('12ª Classe', 'QUI12', 'Química')
        area = self._area('12ª Classe', 'Ciências')
        self.client.put(f'/api/v1/plano-curricular/areas/{area}/disciplinas/',
                        {'disciplinas': [{'disciplina': str(d.id), 'tem_exame': True}]}, format='json')
        res = self.client.get('/api/v1/plano-curricular/classe/', {'classe': '12ª Classe'})
        assert res.status_code == 200
        dados = res.data['data']
        assert dados['tem_exame'] is True
        assert dados['disciplinas'][0]['areas'] == ['Ciências']
        assert dados['areas'][0]['disciplinas'][0]['tem_exame'] is True

    def test_nao_ve_nem_altera_plano_de_outra_escola(self):
        da_outra = AreaSeccao.objects.create(escola=self.outra, classe='11ª Classe', nome='Outra Área')
        assert self.client.patch(f'/api/v1/plano-curricular/areas/{da_outra.id}/', {'nome': 'X'}, format='json').status_code == 404
        assert self.client.delete(f'/api/v1/plano-curricular/areas/{da_outra.id}/').status_code == 404
        nomes = [a['nome'] for c in self.client.get('/api/v1/plano-curricular/estrutura/').data['data']['classes'] for a in c['areas']]
        assert 'Outra Área' not in nomes

    def test_professor_so_le_nao_edita(self):
        prof = self._login('prof.pc@sige.mz')
        assert prof.get('/api/v1/plano-curricular/estrutura/').status_code == 200
        assert prof.post('/api/v1/plano-curricular/areas/', {'classe': '11ª Classe', 'nome': 'Letras'}, format='json').status_code == 403

    def test_disciplina_exige_classe_do_plano(self):
        r = self.client.post('/api/v1/disciplinas/', {'nome': 'Arte', 'codigo': 'ART9', 'classe': '9ª Classe'}, format='json')
        assert r.status_code == 400
        ok = self.client.post('/api/v1/disciplinas/', {'nome': 'Arte', 'codigo': 'ART11', 'classe': '11a classe'}, format='json')
        assert ok.status_code == 201, ok.data
        assert ok.data['data']['classe'] == '11ª Classe'

    def test_turma_exige_classe_e_area_do_plano(self):
        self._area('11ª Classe', 'Letras')
        base = {'nome': 'A', 'ano_letivo': '2026', 'capacidade_maxima': 40}
        sem_classe = self.client.post('/api/v1/turmas/', {**base, 'grau_ano': '5ª Classe'}, format='json')
        assert sem_classe.status_code == 400
        sem_area = self.client.post('/api/v1/turmas/', {**base, 'grau_ano': '11ª Classe', 'area': 'Geral'}, format='json')
        assert sem_area.status_code == 400
        area_errada = self.client.post('/api/v1/turmas/', {**base, 'grau_ano': '11ª Classe', 'area': 'Inventada'}, format='json')
        assert area_errada.status_code == 400
        ok = self.client.post('/api/v1/turmas/', {**base, 'grau_ano': '11ª Classe', 'area': 'Letras'}, format='json')
        assert ok.status_code in (200, 201), ok.data

    def test_classe_com_dependentes_nao_pode_ser_removida(self):
        self._disc('11ª Classe', 'GEO11', 'Geografia')
        r = self.client.put('/api/v1/escola-admin/classes-exames', {'remover_nome': '11ª Classe'}, format='json')
        assert r.status_code == 409
        livre = self.client.put('/api/v1/escola-admin/classes-exames', {'nome': '9ª Classe', 'tem_exame': False}, format='json')
        assert livre.status_code == 200
        assert self.client.put('/api/v1/escola-admin/classes-exames', {'remover_nome': '9ª Classe'}, format='json').status_code == 200

    def test_classe_passa_a_sem_exame_retira_exame_das_disciplinas(self):
        d12 = self._disc('12ª Classe', 'BIO12', 'Biologia')
        area = self._area('12ª Classe', 'Ciências')
        self.client.put(f'/api/v1/plano-curricular/areas/{area}/disciplinas/',
                        {'disciplinas': [{'disciplina': str(d12.id), 'tem_exame': True}]}, format='json')
        r = self.client.put('/api/v1/escola-admin/classes-exames', {'nome': '12ª Classe', 'tem_exame': False}, format='json')
        assert r.status_code == 200
        d12.refresh_from_db()
        assert d12.tem_exame is False

    def test_matricula_sem_turma_exige_classe_do_plano(self):
        base = {'nome': 'Aluno Teste', 'data_nascimento': '2009-01-01', 'genero': 'F'}
        fora = self.client.post('/api/v1/alunos/', {**base, 'classe': '5ª Classe'}, format='json')
        assert fora.status_code == 400
        assert 'classe' in str(fora.data)
        dentro = self.client.post('/api/v1/alunos/', {**base, 'classe': '11a classe'}, format='json')
        assert dentro.status_code in (200, 201), dentro.data

    def test_catalogo_cadastra_em_massa_e_recusa_repetidas(self):
        r = self.client.post('/api/v1/plano-curricular/catalogo/', {'nomes': ['Matemática', 'matemática', 'Física', '']}, format='json')
        assert r.status_code == 201
        assert [d['nome'] for d in r.data['data']] == ['Matemática', 'Física']
        assert r.data['repetidas'] == ['matemática']
        igual = self.client.post('/api/v1/plano-curricular/catalogo/', {'nome': 'FÍSICA'}, format='json')
        assert igual.status_code == 409
        lista = self.client.get('/api/v1/plano-curricular/catalogo/')
        assert sorted(d['nome'] for d in lista.data['data']) == ['Física', 'Matemática']

    def test_disciplina_da_classe_escolhida_do_catalogo(self):
        cat = self.client.post('/api/v1/plano-curricular/catalogo/', {'nome': 'Biologia'}, format='json').data['data'][0]
        r = self.client.post('/api/v1/disciplinas/', {'catalogo': cat['id'], 'codigo': 'BIO11', 'classe': '11ª Classe', 'carga_horaria': 3}, format='json')
        assert r.status_code == 201, r.data
        assert r.data['data']['nome'] == 'Biologia' and str(r.data['data']['catalogo']) == cat['id']
        usos = self.client.get('/api/v1/plano-curricular/catalogo/').data['data'][0]['usos']
        assert usos == 1
        # em uso: não pode ser eliminada do catálogo
        assert self.client.delete(f"/api/v1/plano-curricular/catalogo/{cat['id']}/").status_code == 409

    def test_disciplina_com_nome_novo_entra_no_catalogo(self):
        r = self.client.post('/api/v1/disciplinas/', {'nome': 'Química', 'codigo': 'QUI11', 'classe': '11ª Classe'}, format='json')
        assert r.status_code == 201
        nomes = [d['nome'] for d in self.client.get('/api/v1/plano-curricular/catalogo/').data['data']]
        assert 'Química' in nomes

    def test_renomear_no_catalogo_actualiza_as_classes(self):
        cat = self.client.post('/api/v1/plano-curricular/catalogo/', {'nome': 'Geo'}, format='json').data['data'][0]
        self.client.post('/api/v1/disciplinas/', {'catalogo': cat['id'], 'codigo': 'GEO11', 'classe': '11ª Classe'}, format='json')
        r = self.client.patch(f"/api/v1/plano-curricular/catalogo/{cat['id']}/", {'nome': 'Geografia'}, format='json')
        assert r.status_code == 200
        assert Disciplina.objects.get(codigo='GEO11').nome == 'Geografia'

    def test_catalogo_isolado_e_so_leitura_para_professor(self):
        from apps.disciplinas.models import DisciplinaCatalogo
        alheia = DisciplinaCatalogo.objects.create(escola=self.outra, nome='Alheia')
        nomes = [d['nome'] for d in self.client.get('/api/v1/plano-curricular/catalogo/').data['data']]
        assert 'Alheia' not in nomes
        assert self.client.patch(f'/api/v1/plano-curricular/catalogo/{alheia.id}/', {'nome': 'X'}, format='json').status_code == 404
        prof = self._login('prof.pc@sige.mz')
        assert prof.get('/api/v1/plano-curricular/catalogo/').status_code == 200
        assert prof.post('/api/v1/plano-curricular/catalogo/', {'nome': 'Nova'}, format='json').status_code == 403

    def test_nao_elimina_area_em_uso_por_turma(self):
        area = self._area('11ª Classe', 'Letras')
        self.client.post('/api/v1/turmas/', {'nome': 'B', 'ano_letivo': '2026', 'grau_ano': '11ª Classe', 'area': 'Letras'}, format='json')
        r = self.client.delete(f'/api/v1/plano-curricular/areas/{area}/')
        assert r.status_code == 409
