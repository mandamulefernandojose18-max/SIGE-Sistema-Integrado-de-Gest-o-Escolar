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

    def test_bloqueio_automatico_tenant_expirado_http_402(self):
        # User de Escola Expirada deve receber HTTP 402
        login_res = self.client.post('/api/v1/auth/login/', {'email': 'admin.exp@sige.mz', 'password': 'PassExp123!'}, format='json')
        assert login_res.status_code == 200  # Login é permitido para exibir mensagem no frontend

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res.data['token']}")
        res = self.client.get('/api/v1/alunos/')
        assert res.status_code == 402
        assert res.json()['code'] == 'TENANT_EXPIRED'
        assert "expiração da assinatura" in res.json()['message']

    def test_rota_publica_certificados_funciona_mesmo_escola_expirada(self):
        # Certificados públicos não sofrem bloqueio 402
        cert = Certificado.objects.create(
            escola=self.escola_expirada,
            aluno=self.aluno_a,
            tipo='CONCLUSAO',
            codigo_autenticidade='AUTENTICIDADE_123',
            qrcode_data='https://sige.co.mz/verificar'
        )

        res = self.client.get('/api/v1/certificados/verificar/AUTENTICIDADE_123/')
        assert res.status_code == 200
        assert res.data['autentico'] is True
        assert res.data['data']['codigo'] == 'AUTENTICIDADE_123'
