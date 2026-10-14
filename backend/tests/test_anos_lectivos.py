import pytest
from rest_framework.test import APIClient
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano, AnoLectivo
from apps.tenants.services import garantir_anos_lectivos_escola
from apps.turmas.models import Turma
from apps.alunos.models import Aluno
from apps.notas.models import Nota
from apps.disciplinas.models import Disciplina

@pytest.mark.django_db
class TestAnosLectivos:
    def setup_method(self):
        self.client = APIClient()
        self.plano = Plano.objects.create(nome='PLANO_ANOS_TEST', preco=2500, duracao_dias=30)
        self.escola = Escola.objects.create(
            nome='Escola Secundária de Teste',
            nif_cnpj='NIF_TEST_ANOS',
            email='secretaria.anos@sige.mz',
            status='ATIVA',
            ano_letivo_ativo='2026',
            plano=self.plano
        )
        self.admin = Usuario.objects.create_user(
            email='admin.anos@sige.mz',
            password='Password123!',
            role='ADMIN_ESCOLA',
            escola=self.escola
        )
        # Login
        login_res = self.client.post('/api/v1/auth/login/', {'email': 'admin.anos@sige.mz', 'password': 'Password123!'}, format='json')
        self.token = login_res.data['token']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_criacao_automatica_anos_lectivos(self):
        """O sistema deve criar automaticamente os anos lectivos (findos e actual) para a escola."""
        anos = garantir_anos_lectivos_escola(self.escola)
        anos_codigos = [a.ano for a in anos]
        
        # Garante que pelo menos 2026, 2025, 2024, 2023 foram gerados automaticamente
        for y in ['2026', '2025', '2024', '2023']:
            assert y in anos_codigos

        # O ano activo deve ter descricao no formato oficial
        ano_2026 = AnoLectivo.objects.get(escola=self.escola, ano='2026')
        assert ano_2026.descricao == 'Ano Lectivo de 2026'
        assert ano_2026.ativo is True

        # Anos findos não devem estar como activos
        ano_2025 = AnoLectivo.objects.get(escola=self.escola, ano='2025')
        assert ano_2025.descricao == 'Ano Lectivo de 2025'
        assert ano_2025.ativo is False

    def test_api_listagem_anos_lectivos(self):
        """Endpoint /api/v1/anos-letivos deve retornar anos ordenados decrescentemente."""
        res = self.client.get('/api/v1/anos-letivos/')
        assert res.status_code == 200
        assert res.data['success'] is True
        assert res.data['ano_ativo'] == '2026'
        
        anos_retornados = res.data['data']
        assert len(anos_retornados) >= 4
        # Primeiro ano deve ser o mais recente
        assert int(anos_retornados[0]['ano']) >= int(anos_retornados[1]['ano'])
        assert anos_retornados[0]['descricao'].startswith('Ano Lectivo de ')

    def test_busca_informacoes_ano_findo_vs_ano_actual(self):
        """Permitir busca de informações (turmas e alunos) em função do ano findo ou actual."""
        # Criar dados em ano findo (2025)
        turma_2025 = Turma.objects.create(
            escola=self.escola,
            nome='10ª B 2025',
            grau_ano='10ª Classe',
            ano_letivo='2025'
        )
        aluno_2025 = Aluno.objects.create(
            escola=self.escola,
            turma=turma_2025,
            matricula='MAT2025_001',
            nome='Carlos Past',
            ano_ingresso='2025',
            data_nascimento='2008-05-10',
            genero='M'
        )

        # Criar dados em ano actual (2026)
        turma_2026 = Turma.objects.create(
            escola=self.escola,
            nome='10ª A 2026',
            grau_ano='10ª Classe',
            ano_letivo='2026'
        )
        aluno_2026 = Aluno.objects.create(
            escola=self.escola,
            turma=turma_2026,
            matricula='MAT2026_001',
            nome='Beatriz Present',
            ano_ingresso='2026',
            data_nascimento='2009-08-15',
            genero='F'
        )

        # 1. Busca de Turmas por Ano Findo (2025)
        res_turmas_2025 = self.client.get('/api/v1/turmas/?ano_letivo=2025')
        assert res_turmas_2025.status_code == 200
        turmas_ids_2025 = [t['id'] for t in res_turmas_2025.data['data']]
        assert str(turma_2025.id) in turmas_ids_2025
        assert str(turma_2026.id) not in turmas_ids_2025

        # 2. Busca de Turmas por Ano Actual (2026)
        res_turmas_2026 = self.client.get('/api/v1/turmas/?ano_letivo=2026')
        assert res_turmas_2026.status_code == 200
        turmas_ids_2026 = [t['id'] for t in res_turmas_2026.data['data']]
        assert str(turma_2026.id) in turmas_ids_2026
        assert str(turma_2025.id) not in turmas_ids_2026

        # 3. Busca de Alunos por Ano Findo (2025)
        res_alunos_2025 = self.client.get('/api/v1/alunos/?ano_letivo=2025')
        assert res_alunos_2025.status_code == 200
        alunos_ids_2025 = [a['id'] for a in res_alunos_2025.data['data']]
        assert str(aluno_2025.id) in alunos_ids_2025
        assert str(aluno_2026.id) not in alunos_ids_2025

        # 4. Busca de Alunos por Ano Actual (2026)
        res_alunos_2026 = self.client.get('/api/v1/alunos/?ano_letivo=2026')
        assert res_alunos_2026.status_code == 200
        alunos_ids_2026 = [a['id'] for a in res_alunos_2026.data['data']]
        assert str(aluno_2026.id) in alunos_ids_2026
        assert str(aluno_2025.id) not in alunos_ids_2026

    def test_definir_novo_ano_activo(self):
        """Ao definir novo ano activo (ex: 2027), o sistema deve registar e actualizar automaticamente."""
        res = self.client.post('/api/v1/anos-letivos/definir-ativo/', {'ano': '2027'}, format='json')
        assert res.status_code == 200
        assert res.data['success'] is True
        assert res.data['ano_ativo'] == '2027'

        # Verificar se o ano 2027 foi criado e está activo
        ano_2027 = AnoLectivo.objects.get(escola=self.escola, ano='2027')
        assert ano_2027.descricao == 'Ano Lectivo de 2027'
        assert ano_2027.ativo is True

        # O ano anterior 2026 agora é findo (ativo=False)
        ano_2026 = AnoLectivo.objects.get(escola=self.escola, ano='2026')
        assert ano_2026.ativo is False
