import pytest
from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano, AssinaturaEscola
from apps.turmas.models import Turma
from apps.alunos.models import Aluno
from apps.certificados.models import Certificado

@pytest.mark.django_db
class TestMultiTenancy:
    def setup_method(self):
        self.client = APIClient()
        self.plano = Plano.objects.create(nome='PLANO_TENANT_TEST', preco=2000, duracao_dias=30)
        
        # Tenant A (Escola A - ATIVA)
        self.escola_a = Escola.objects.create(nome='Escola Alfa', nif_cnpj='NIF_A', email='alfa@sige.mz', status='ATIVA', plano=self.plano)
        self.user_a = Usuario.objects.create_user(email='admin.a@sige.mz', password='PassA123!', role='ADMIN_ESCOLA', escola=self.escola_a)
        self.turma_a = Turma.objects.create(escola=self.escola_a, nome='10ª A Alfa', grau_ano='10ª Classe')
        self.aluno_a = Aluno.objects.create(escola=self.escola_a, turma=self.turma_a, matricula='MAT_A_001', nome='Aluno de Alfa', data_nascimento='2009-01-01', genero='M')

        # Tenant B (Escola B - ATIVA)
        self.escola_b = Escola.objects.create(nome='Escola Beta', nif_cnpj='NIF_B', email='beta@sige.mz', status='ATIVA', plano=self.plano)
        self.user_b = Usuario.objects.create_user(email='admin.b@sige.mz', password='PassB123!', role='ADMIN_ESCOLA', escola=self.escola_b)
        self.turma_b = Turma.objects.create(escola=self.escola_b, nome='10ª B Beta', grau_ano='10ª Classe')
        self.aluno_b = Aluno.objects.create(escola=self.escola_b, turma=self.turma_b, matricula='MAT_B_001', nome='Aluno de Beta', data_nascimento='2009-02-02', genero='F')

        # Tenant C (Escola C - EXPIRADA)
        self.escola_expirada = Escola.objects.create(nome='Escola Expirada', nif_cnpj='NIF_EXP', email='exp@sige.mz', status='EXPIRADA', plano=self.plano)
        self.user_expirado = Usuario.objects.create_user(email='admin.exp@sige.mz', password='PassExp123!', role='ADMIN_ESCOLA', escola=self.escola_expirada)

    def test_isolamento_leitura_entre_tenants(self):
        # User A lista alunos -> DEVE ver apenas Aluno A
        login_res = self.client.post('/api/v1/auth/login/', {'email': 'admin.a@sige.mz', 'password': 'PassA123!'}, format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res.data['token']}")

        res = self.client.get('/api/v1/alunos/')
        assert res.status_code == 200
        alunos_ids = [a['id'] for a in res.data['data']]
        assert str(self.aluno_a.id) in alunos_ids
        assert str(self.aluno_b.id) not in alunos_ids

    def test_bloqueio_tentativa_acesso_direto_outro_tenant(self):
        # User A tenta acessar detalhe do Aluno B -> DEVE ser 404 (não encontrado no seu escopo)
        login_res = self.client.post('/api/v1/auth/login/', {'email': 'admin.a@sige.mz', 'password': 'PassA123!'}, format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res.data['token']}")

        res_get = self.client.get(f'/api/v1/alunos/{self.aluno_b.id}/')
        assert res_get.status_code == 404

        res_delete = self.client.delete(f'/api/v1/alunos/{self.aluno_b.id}/')
        assert res_delete.status_code == 404

    def test_bloqueio_automatico_tenant_expirado(self):
        # User de Escola Expirada tem login bloqueado com mensagem explícita
        login_res = self.client.post('/api/v1/auth/login/', {'email': 'admin.exp@sige.mz', 'password': 'PassExp123!'}, format='json')
        assert login_res.status_code == 401
        assert "Acesso bloqueado" in str(login_res.data)
        assert "EXPIRADA" in str(login_res.data)

    def test_rota_publica_certificados_funciona_mesmo_escola_expirada(self):
        # Certificados públicos não sofrem bloqueio 402
        turma_exp = Turma.objects.create(escola=self.escola_expirada, nome='10ª Exp', grau_ano='10ª Classe')
        aluno_exp = Aluno.objects.create(escola=self.escola_expirada, turma=turma_exp, matricula='MAT_EXP_001', nome='Aluno Exp', data_nascimento='2009-03-03', genero='M')
        cert = Certificado.objects.create(
            escola=self.escola_expirada,
            aluno=aluno_exp,
            tipo='CONCLUSAO',
            codigo_autenticidade='AUTENTICIDADE_123',
            qrcode_data='https://sige.co.mz/verificar'
        )

        res = self.client.get('/api/v1/certificados/verificar/AUTENTICIDADE_123/')
        assert res.status_code == 200
        assert res.data['autentico'] is True
        assert res.data['data']['codigo'] == 'AUTENTICIDADE_123'

    def test_publicacoes_feitas_numa_escola_nao_reflectem_noutras_escolas(self):
        from apps.material_escolar.models import MaterialEscolar

        # Criar publicação na Escola A
        mat_a = MaterialEscolar.objects.create(
            escola=self.escola_a,
            classe='10ª Classe',
            titulo='Manual de Matemática - Escola Alfa',
            tipo='MANUAL',
            publicado_por='Admin Alfa'
        )

        # Criar publicação na Escola B
        mat_b = MaterialEscolar.objects.create(
            escola=self.escola_b,
            classe='10ª Classe',
            titulo='Ficha de Física - Escola Beta',
            tipo='FICHA',
            publicado_por='Admin Beta'
        )

        # 1. Utilizador da Escola A consulta materiais: vê apenas os da Escola A
        login_res_a = self.client.post('/api/v1/auth/login/', {'email': 'admin.a@sige.mz', 'password': 'PassA123!'}, format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res_a.data['token']}")

        res_a = self.client.get('/api/v1/material-escolar/')
        assert res_a.status_code == 200
        titulos_a = [m['titulo'] for m in res_a.data['data']]
        assert 'Manual de Matemática - Escola Alfa' in titulos_a
        assert 'Ficha de Física - Escola Beta' not in titulos_a

        # Contagem de classes na Escola A: apenas 1 material na 10ª Classe
        res_classes_a = self.client.get('/api/v1/material-escolar/classes/')
        assert res_classes_a.status_code == 200
        c10_a = next(item for item in res_classes_a.data['data'] if item['classe'] == '10ª Classe')
        assert c10_a['totalMateriais'] == 1

        # 2. Utilizador da Escola B consulta materiais: vê apenas os da Escola B
        login_res_b = self.client.post('/api/v1/auth/login/', {'email': 'admin.b@sige.mz', 'password': 'PassB123!'}, format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res_b.data['token']}")

        res_b = self.client.get('/api/v1/material-escolar/')
        assert res_b.status_code == 200
        titulos_b = [m['titulo'] for m in res_b.data['data']]
        assert 'Ficha de Física - Escola Beta' in titulos_b
        assert 'Manual de Matemática - Escola Alfa' not in titulos_b

        # 3. SuperAdmin inspecionando Escola A vê apenas Escola A
        u_super = Usuario.objects.create_superuser(email='super@sige.mz', password='PassSuper123!')
        login_res_super = self.client.post('/api/v1/auth/login/', {'email': 'super@sige.mz', 'password': 'PassSuper123!'}, format='json')
        
        # Com header X-Tenant-ID da Escola A
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res_super.data['token']}", HTTP_X_TENANT_ID=str(self.escola_a.id))
        res_super_a = self.client.get('/api/v1/material-escolar/')
        titulos_super_a = [m['titulo'] for m in res_super_a.data['data']]
        assert 'Manual de Matemática - Escola Alfa' in titulos_super_a
        assert 'Ficha de Física - Escola Beta' not in titulos_super_a

        # Com header X-Tenant-ID da Escola B
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res_super.data['token']}", HTTP_X_TENANT_ID=str(self.escola_b.id))
        res_super_b = self.client.get('/api/v1/material-escolar/')
        titulos_super_b = [m['titulo'] for m in res_super_b.data['data']]
        assert 'Ficha de Física - Escola Beta' in titulos_super_b
        assert 'Manual de Matemática - Escola Alfa' not in titulos_super_b

        # SuperAdmin sem tenant selecionado não recebe vazamento de nenhuma escola
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res_super.data['token']}")
        res_super_none = self.client.get('/api/v1/material-escolar/')
        assert len(res_super_none.data['data']) == 0

