"""2FA (TOTP): algoritmo, activação, login em dois passos, códigos de recuperação e reposição."""
import pytest
from rest_framework.test import APIClient

from apps.accounts import totp
from apps.accounts.models import Usuario, LogAuditoria
from apps.tenants.models import Escola, Plano


def test_totp_vector_oficial_rfc6238():
    # RFC 6238, apêndice B: segredo "12345678901234567890", T=59s -> 94287082 (8 díg.); os 6 últimos são 287082.
    segredo = 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ'
    assert totp.codigo_para(segredo, 59 // 30) == '287082'
    assert totp.verificar_codigo(segredo, '287082', agora=59) == 1


def test_totp_rejeita_reutilizacao_e_codigo_errado():
    segredo = totp.gerar_segredo()
    passo = totp.passo_actual()
    codigo = totp.codigo_para(segredo, passo)
    assert totp.verificar_codigo(segredo, codigo) == passo
    assert totp.verificar_codigo(segredo, codigo, ultimo_passo=passo) is None
    assert totp.verificar_codigo(segredo, 'abc') is None


def test_codigos_recuperacao_so_servem_uma_vez():
    claros, hashes = totp.gerar_codigos_recuperacao()
    assert len(claros) == totp.N_CODIGOS_RECUPERACAO
    restantes = totp.consumir_codigo_recuperacao(hashes, claros[0].upper())
    assert restantes is not None and len(restantes) == len(hashes) - 1
    assert totp.consumir_codigo_recuperacao(restantes, claros[0]) is None


@pytest.mark.django_db
class TestFluxo2FA:
    def setup_method(self):
        self.client = APIClient()
        plano = Plano.objects.create(nome='PLANO_2FA', preco=2000, duracao_dias=30)
        self.escola = Escola.objects.create(nome='Escola 2FA', nif_cnpj='NIF_2FA', email='e@sige.mz', status='ATIVA', plano=plano)
        self.admin = Usuario.objects.create_user(email='admin@2fa.mz', password='PassA123!', role='ADMIN_ESCOLA', escola=self.escola)
        self.prof = Usuario.objects.create_user(email='prof@2fa.mz', password='PassP123!', role='PROFESSOR', escola=self.escola)

    def _login(self, email, senha, **extra):
        return self.client.post('/api/v1/auth/login/', {'email': email, 'password': senha, **extra}, format='json')

    def _autenticar(self, email, senha):
        res = self._login(email, senha)
        assert res.status_code == 200, res.data
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['token']}")

    def _activar(self):
        self._autenticar('admin@2fa.mz', 'PassA123!')
        cfg = self.client.post('/api/v1/auth/2fa/configurar/', format='json')
        assert cfg.status_code == 200
        assert cfg.data['data']['qr'].startswith('data:image/png;base64,')
        segredo = cfg.data['data']['segredo']
        res = self.client.post('/api/v1/auth/2fa/activar/', {
            'password': 'PassA123!', 'codigo': totp.codigo_para(segredo, totp.passo_actual())}, format='json')
        assert res.status_code == 200, res.data
        self.client.credentials()
        return segredo, res.data['data']['codigos_recuperacao']

    def test_perfil_nao_elegivel_nao_configura(self):
        self._autenticar('prof@2fa.mz', 'PassP123!')
        assert self.client.post('/api/v1/auth/2fa/configurar/', format='json').status_code == 403

    def test_activar_exige_codigo_valido_e_palavra_passe(self):
        self._autenticar('admin@2fa.mz', 'PassA123!')
        self.client.post('/api/v1/auth/2fa/configurar/', format='json')
        assert self.client.post('/api/v1/auth/2fa/activar/', {'password': 'PassA123!', 'codigo': '123456'}, format='json').status_code == 400
        assert self.client.post('/api/v1/auth/2fa/activar/', {'password': 'errada', 'codigo': '123456'}, format='json').status_code == 400
        self.admin.refresh_from_db()
        assert self.admin.totp_ativo is False

    def test_login_em_dois_passos(self):
        segredo, codigos = self._activar()
        # Sem código: pede o segundo factor e NÃO emite tokens.
        res = self._login('admin@2fa.mz', 'PassA123!')
        assert res.status_code == 401 and res.data['requer_2fa'] is True
        assert 'token' not in res.data and 'access' not in res.data
        # Código errado: recusado.
        assert self._login('admin@2fa.mz', 'PassA123!', codigo_2fa='000000').status_code == 401
        # Código certo (passo seguinte, ainda dentro da janela): aceite uma vez.
        codigo = totp.codigo_para(segredo, totp.passo_actual() + 1)
        ok = self._login('admin@2fa.mz', 'PassA123!', codigo_2fa=codigo)
        assert ok.status_code == 200 and ok.data['token']
        # O mesmo código não pode ser reutilizado.
        assert self._login('admin@2fa.mz', 'PassA123!', codigo_2fa=codigo).status_code == 401

    def test_codigo_de_recuperacao_serve_uma_vez(self):
        _, codigos = self._activar()
        assert self._login('admin@2fa.mz', 'PassA123!', codigo_2fa=codigos[0]).status_code == 200
        assert self._login('admin@2fa.mz', 'PassA123!', codigo_2fa=codigos[0]).status_code == 401
        assert LogAuditoria.objects.filter(entidade='SEGURANCA', acao='2FA_CODIGO_RECUPERACAO').exists()

    def test_palavra_passe_errada_nao_revela_o_segundo_factor(self):
        self._activar()
        res = self._login('admin@2fa.mz', 'errada')
        assert res.status_code == 401 and not res.data.get('requer_2fa')

    def test_desactivar_exige_palavra_passe_e_codigo(self):
        segredo, codigos = self._activar()
        res = self._login('admin@2fa.mz', 'PassA123!', codigo_2fa=codigos[0])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['token']}")
        assert self.client.post('/api/v1/auth/2fa/desactivar/', {'password': 'PassA123!', 'codigo': '000000'}, format='json').status_code == 400
        ok = self.client.post('/api/v1/auth/2fa/desactivar/', {'password': 'PassA123!', 'codigo': codigos[1]}, format='json')
        assert ok.status_code == 200
        self.admin.refresh_from_db()
        assert self.admin.totp_ativo is False and self.admin.totp_secret == ''
        self.client.credentials()
        assert self._login('admin@2fa.mz', 'PassA123!').status_code == 200

    def test_administrador_repoe_2fa_de_utilizador_da_mesma_escola(self):
        _, codigos = self._activar()
        director = Usuario.objects.create_user(email='dir@2fa.mz', password='PassD123!', role='DIRECTOR_ESCOLA', escola=self.escola)
        director.totp_ativo, director.totp_secret = True, totp.gerar_segredo()
        director.save()
        outra = Escola.objects.create(nome='Outra', nif_cnpj='NIF_2FA_B', email='o@sige.mz', status='ATIVA', plano=self.escola.plano)
        estranho = Usuario.objects.create_user(email='x@2fa.mz', password='PassX123!', role='DIRECTOR_ESCOLA', escola=outra)
        estranho.totp_ativo, estranho.totp_secret = True, totp.gerar_segredo()
        estranho.save()

        res = self._login('admin@2fa.mz', 'PassA123!', codigo_2fa=codigos[0])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['token']}")
        assert self.client.post(f'/api/v1/auth/usuarios/{director.id}/2fa/repor/').status_code == 200
        director.refresh_from_db()
        assert director.totp_ativo is False
        # Não pode repor contas de outra escola.
        assert self.client.post(f'/api/v1/auth/usuarios/{estranho.id}/2fa/repor/').status_code == 404
        estranho.refresh_from_db()
        assert estranho.totp_ativo is True

    def test_segredo_nunca_aparece_na_api_de_utilizador(self):
        self._activar()
        from apps.accounts.serializers import UsuarioSerializer
        self.admin.refresh_from_db()
        dados = UsuarioSerializer(self.admin).data
        assert 'totp_secret' not in dados and 'totp_codigos_recuperacao' not in dados
