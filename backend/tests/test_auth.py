import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano

@pytest.mark.django_db
class TestAuthAPI:
    def setup_method(self):
        self.client = APIClient()
        self.plano = Plano.objects.create(nome='TEST_PLANO', preco=1000, duracao_dias=30)
        self.escola = Escola.objects.create(nome='Escola Teste', nif_cnpj='123456789', email='teste@escola.mz', status='ATIVA', plano=self.plano)
        
        self.superadmin = Usuario.objects.create_superuser(email='super@sige.com', password='SuperPassword123')
        
        self.user = Usuario.objects.create_user(
            email='director@escola.mz',
            password='DirectorPass123',
            nome='Prof. Director',
            role='DIRECTOR_ESCOLA',
            escola=self.escola
        )

    def test_login_sucesso_superadmin(self):
        url = '/api/v1/auth/login/'
        response = self.client.post(url, {'email': 'super@sige.com', 'password': 'SuperPassword123'}, format='json')
        assert response.status_code == 200
        assert response.data['success'] is True
        assert 'token' in response.data
        assert response.data['user']['role'] == 'SUPERADMIN'

    def test_login_sucesso_diretor_escola(self):
        url = '/api/v1/auth/login/'
        response = self.client.post(url, {'email': 'director@escola.mz', 'password': 'DirectorPass123'}, format='json')
        assert response.status_code == 200
        assert response.data['success'] is True
        assert 'token' in response.data
        assert response.data['user']['role'] == 'DIRECTOR_ESCOLA'
        assert str(response.data['user']['escola_id']) == str(self.escola.id)

    def test_login_falha_credenciais_incorretas(self):
        url = '/api/v1/auth/login/'
        response = self.client.post(url, {'email': 'director@escola.mz', 'password': 'WrongPassword!'}, format='json')
        assert response.status_code == 401
        assert response.data['success'] is False

    def test_auth_me_com_token_valido(self):
        login_res = self.client.post('/api/v1/auth/login/', {'email': 'director@escola.mz', 'password': 'DirectorPass123'}, format='json')
        token = login_res.data['token']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        res = self.client.get('/api/v1/auth/me/')
        assert res.status_code == 200
        assert res.data['success'] is True
        assert res.data['user']['email'] == 'director@escola.mz'

    def test_auth_me_sem_token(self):
        res = self.client.get('/api/v1/auth/me/')
        assert res.status_code == 401
