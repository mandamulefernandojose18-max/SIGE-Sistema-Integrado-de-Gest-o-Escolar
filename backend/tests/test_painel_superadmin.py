"""Painel SuperAdmin: logs de acesso paginados, Cofre global filtrado e validação/auditoria do preço do plano."""
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import LogAcesso, LogAuditoria, Usuario
from apps.tenants.models import Escola, Plano


@pytest.fixture
def cenario(db):
    superadmin = Usuario.objects.create_superuser(email='sa.painel@sige.mz', password='AdminPassword2026!', nome='Super Admin')
    escola_a = Escola.objects.create(nome='Escola A Teste', nif_cnpj='NUIT_A_1', email='a@sige.mz', status='ATIVA')
    escola_b = Escola.objects.create(nome='Escola B Teste', nif_cnpj='NUIT_B_1', email='b@sige.mz', status='ATIVA')
    admin_a = Usuario.objects.create_user(email='admin.a@sige.mz', password='SchoolPass2026!', role='ADMIN_ESCOLA', nome='Director A', escola=escola_a)
    prof_b = Usuario.objects.create_user(email='prof.b@sige.mz', password='SchoolPass2026!', role='PROFESSOR', nome='Prof B', escola=escola_b)
    client = APIClient()
    client.force_authenticate(superadmin)
    return {'client': client, 'sa': superadmin, 'a': escola_a, 'b': escola_b, 'admin_a': admin_a, 'prof_b': prof_b}


@pytest.mark.django_db
class TestLogsAcesso:
    def test_lista_paginada_e_filtra_por_escola_e_tipo(self, cenario):
        for _ in range(30):
            LogAcesso.objects.create(escola=cenario['a'], usuario=cenario['admin_a'], ip='origem-teste-a', tipo='LOGIN_SUCESSO')
        LogAcesso.objects.create(escola=cenario['b'], usuario=cenario['prof_b'], ip='origem-teste-b', tipo='LOGIN_FALHA')
        c = cenario['client']

        r = c.get('/api/v1/saas-admin/logs-acesso?tamanho=25')
        assert r.status_code == 200
        assert len(r.data['data']) == 25
        assert r.data['meta']['total'] == 31 and r.data['meta']['paginas'] == 2

        r = c.get(f"/api/v1/saas-admin/logs-acesso?escola={cenario['b'].id}")
        assert [l['tipo'] for l in r.data['data']] == ['LOGIN_FALHA']
        assert r.data['data'][0]['escola_nome'] == 'Escola B Teste'

        r = c.get('/api/v1/saas-admin/logs-acesso?tipo=LOGIN_FALHA&q=Prof')
        assert r.data['meta']['total'] == 1

    def test_escola_invalida_devolve_400(self, cenario):
        assert cenario['client'].get('/api/v1/saas-admin/logs-acesso?escola=nao-e-uuid').status_code == 400

    def test_so_superadmin(self, cenario):
        c = APIClient()
        c.force_authenticate(cenario['admin_a'])
        assert c.get('/api/v1/saas-admin/logs-acesso').status_code == 403
        assert c.get('/api/v1/saas-admin/escolas-opcoes').status_code == 403

    def test_opcoes_de_escolas(self, cenario):
        r = cenario['client'].get('/api/v1/saas-admin/escolas-opcoes')
        assert r.status_code == 200
        assert {e['nome'] for e in r.data['data']} == {'Escola A Teste', 'Escola B Teste'}


@pytest.mark.django_db
class TestCofreSuperAdmin:
    def test_filtra_por_escola_perfil_e_pesquisa_com_paginacao(self, cenario):
        c = cenario['client']
        r = c.get('/api/v1/escola-admin/usuarios-credenciais?tamanho=2')
        assert r.status_code == 200
        assert len(r.data['data']) == 2
        assert r.data['meta']['total'] == 3 and r.data['meta']['paginas'] == 2

        r = c.get(f"/api/v1/escola-admin/usuarios-credenciais?escola={cenario['a'].id}")
        assert [u['email'] for u in r.data['data']] == ['admin.a@sige.mz']
        assert r.data['data'][0]['escola_nome'] == 'Escola A Teste'

        r = c.get('/api/v1/escola-admin/usuarios-credenciais?role=PROFESSOR')
        assert r.data['meta']['total'] == 1
        r = c.get('/api/v1/escola-admin/usuarios-credenciais?q=prof.b')
        assert r.data['meta']['total'] == 1

    def test_escola_invalida_devolve_400(self, cenario):
        assert cenario['client'].get('/api/v1/escola-admin/usuarios-credenciais?escola=xx').status_code == 400

    def test_tamanho_maximo_100(self, cenario):
        r = cenario['client'].get('/api/v1/escola-admin/usuarios-credenciais?tamanho=100000')
        assert r.data['meta']['tamanho'] == 100


@pytest.mark.django_db
class TestPrecoPlano:
    def _plano(self):
        return Plano.objects.create(nome='Plano Teste Preco', preco=Decimal('1000.00'))

    @pytest.mark.parametrize('valor', ['abc', -5, '-0.01', 'NaN', 'Infinity', 10 ** 12, ''])
    def test_rejeita_valores_invalidos(self, cenario, valor):
        plano = self._plano()
        r = cenario['client'].patch(f'/api/v1/saas-admin/planos/{plano.id}/preco', {'preco': valor}, format='json')
        assert r.status_code == 400
        plano.refresh_from_db()
        assert plano.preco == Decimal('1000.00')

    def test_actualiza_e_regista_auditoria(self, cenario):
        plano = self._plano()
        r = cenario['client'].patch(f'/api/v1/saas-admin/planos/{plano.id}/preco', {'preco': '1500,5'}, format='json')
        assert r.status_code == 200
        plano.refresh_from_db()
        assert plano.preco == Decimal('1500.50')
        log = LogAuditoria.objects.filter(entidade='PLANO', acao='ALTERAR_PRECO').first()
        assert log is not None and '1500.50' in log.descricao

    def test_escola_nao_altera_preco(self, cenario):
        plano = self._plano()
        c = APIClient()
        c.force_authenticate(cenario['admin_a'])
        assert c.patch(f'/api/v1/saas-admin/planos/{plano.id}/preco', {'preco': 1}, format='json').status_code == 403


@pytest.mark.django_db
class TestAuditoriaRedefinirSenha:
    def test_regista_quem_redefiniu_a_senha(self, cenario):
        r = cenario['client'].put(f"/api/v1/auth/usuarios/{cenario['prof_b'].id}/redefinir-senha",
                                  {'nova_senha': 'NovaSenhaSegura2026!'}, format='json')
        assert r.status_code == 200
        assert LogAuditoria.objects.filter(entidade='UTILIZADOR', acao='REDEFINIR_SENHA').exists()


# ---------------------------------------------------------------------------
# Pagamentos da assinatura SaaS: submissão validada e confirmação única
# ---------------------------------------------------------------------------
from datetime import timedelta  # noqa: E402

from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from django.utils import timezone  # noqa: E402

from apps.tenants.models import SaasAssinatura, SaasFatura, SaasPagamento, SaasPlano  # noqa: E402
from apps.tenants.saas_middleware import limpar_cache_assinatura  # noqa: E402


@pytest.fixture
def fatura_aberta(cenario):
    limpar_cache_assinatura()
    hoje = timezone.localdate()
    plano = SaasPlano.objects.create(nome='Plano Pagamentos Teste', preco_mensal=Decimal('3000.00'), limite_alunos=1000, limite_professores=100)
    ass = SaasAssinatura.objects.create(instituicao=cenario['a'], plano=plano, periodicidade='mensal', estado='activa', proxima_fatura_em=hoje)
    return SaasFatura.objects.create(
        assinatura=ass, instituicao=cenario['a'], numero_fatura='FAT-PAG-001',
        periodo_inicio=hoje, periodo_fim=hoje + timedelta(days=30), valor=Decimal('3000.00'),
        data_abertura=hoje, data_limite=hoje + timedelta(days=5), estado='aberta')


def _cliente(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


def _corpo(fatura, **extra):
    corpo = {'fatura_id': str(fatura.id), 'metodo': 'M-Pesa', 'referencia': 'REF-UNICA-1', 'valor': '3000.00'}
    corpo.update(extra)
    return corpo


@pytest.mark.django_db
class TestConfirmacaoUnica:
    def test_nao_confirma_duas_vezes(self, cenario, fatura_aberta):
        pag = SaasPagamento.objects.create(fatura=fatura_aberta, instituicao=cenario['a'], metodo='M-Pesa', referencia='X1', valor=Decimal('3000.00'))
        c = cenario['client']
        assert c.post(f'/api/v1/saas/pagamentos/{pag.id}/confirmar/').status_code == 200
        fatura_aberta.refresh_from_db()
        proxima = fatura_aberta.assinatura.proxima_fatura_em

        r2 = c.post(f'/api/v1/saas/pagamentos/{pag.id}/confirmar/')
        assert r2.status_code == 409
        fatura_aberta.refresh_from_db()
        assert fatura_aberta.valor_pago == Decimal('3000.00')
        assert fatura_aberta.assinatura.proxima_fatura_em == proxima

    def test_nao_confirma_pagamento_rejeitado(self, cenario, fatura_aberta):
        pag = SaasPagamento.objects.create(fatura=fatura_aberta, instituicao=cenario['a'], metodo='M-Pesa', referencia='X2', valor=Decimal('3000.00'))
        c = cenario['client']
        assert c.post(f'/api/v1/saas/pagamentos/{pag.id}/rejeitar/', {'motivo': 'Comprovativo ilegível'}, format='json').status_code == 200
        assert c.post(f'/api/v1/saas/pagamentos/{pag.id}/confirmar/').status_code == 409
        assert c.post(f'/api/v1/saas/pagamentos/{pag.id}/rejeitar/', {'motivo': 'outra vez'}, format='json').status_code == 409
        fatura_aberta.refresh_from_db()
        assert fatura_aberta.valor_pago == Decimal('0.00')

    def test_pagamento_inexistente_404(self, cenario):
        import uuid
        assert cenario['client'].post(f'/api/v1/saas/pagamentos/{uuid.uuid4()}/confirmar/').status_code == 404


@pytest.mark.django_db
class TestSubmissaoComprovativo:
    URL = '/api/v1/saas/registar-pagamento/'

    def test_admin_da_escola_submete(self, cenario, fatura_aberta):
        r = _cliente(cenario['admin_a']).post(self.URL, _corpo(fatura_aberta), format='json')
        assert r.status_code == 201
        assert SaasPagamento.objects.filter(instituicao=cenario['a'], estado='enviado').count() == 1

    @pytest.mark.parametrize('papel', ['DIRECTOR_ESCOLA', 'DAP', 'CHEFE_SECRETARIA', 'SECRETARIA', 'FINANCEIRO'])
    def test_pessoal_da_escola_pode_submeter(self, cenario, fatura_aberta, papel):
        u = Usuario.objects.create_user(email=f'{papel.lower()}@sige.mz', password='SchoolPass2026!', role=papel, nome=papel, escola=cenario['a'])
        assert _cliente(u).post(self.URL, _corpo(fatura_aberta), format='json').status_code == 201

    @pytest.mark.parametrize('papel', ['ENCARREGADO', 'PROFESSOR', 'ALUNO'])
    def test_perfis_sem_gestao_da_escola_sao_recusados(self, cenario, fatura_aberta, papel):
        u = Usuario.objects.create_user(email=f'{papel.lower()}@sige.mz', password='SchoolPass2026!', role=papel, nome=papel, escola=cenario['a'])
        assert _cliente(u).post(self.URL, _corpo(fatura_aberta), format='json').status_code == 403

    @pytest.mark.parametrize('extra', [
        {'metodo': 'Bitcoin'}, {'valor': '-5'}, {'valor': 'abc'}, {'valor': '1e30'}, {'valor': 'NaN'},
        {'valor': '999999999999'}, {'referencia': 'R' * 101},
    ])
    def test_entradas_invalidas_dao_400(self, cenario, fatura_aberta, extra):
        r = _cliente(cenario['admin_a']).post(self.URL, _corpo(fatura_aberta, **extra), format='json')
        assert r.status_code == 400

    def test_referencia_duplicada_e_recusada_mas_rejeitada_pode_repetir(self, cenario, fatura_aberta):
        c = _cliente(cenario['admin_a'])
        assert c.post(self.URL, _corpo(fatura_aberta), format='json').status_code == 201
        assert c.post(self.URL, _corpo(fatura_aberta, referencia='ref-unica-1'), format='json').status_code == 400
        SaasPagamento.objects.update(estado='rejeitado')
        assert c.post(self.URL, _corpo(fatura_aberta), format='json').status_code == 201

    def test_fatura_de_outra_escola_ou_id_invalido(self, cenario, fatura_aberta):
        outro = Usuario.objects.create_user(email='admin.b@sige.mz', password='SchoolPass2026!', role='ADMIN_ESCOLA', nome='Director B', escola=cenario['b'])
        assert _cliente(outro).post(self.URL, _corpo(fatura_aberta), format='json').status_code == 404
        assert _cliente(cenario['admin_a']).post(self.URL, _corpo(fatura_aberta, fatura_id='lixo'), format='json').status_code == 404

    @pytest.mark.parametrize('url', ['javascript:alert(1)', 'data:text/html;base64,PHNjcmlwdD4=', 'https://exemplo.invalido/x.pdf'])
    def test_base64_so_aceita_imagem_ou_pdf(self, cenario, fatura_aberta, url):
        r = _cliente(cenario['admin_a']).post(self.URL, _corpo(fatura_aberta, comprovativo_base64=url), format='json')
        assert r.status_code == 400
        assert not SaasPagamento.objects.exists()

    def test_base64_png_valido(self, cenario, fatura_aberta):
        r = _cliente(cenario['admin_a']).post(self.URL, _corpo(fatura_aberta, comprovativo_base64='data:image/png;base64,iVBORw0KGgo='), format='json')
        assert r.status_code == 201

    def test_ficheiro_com_conteudo_falso_ou_grande_e_recusado(self, cenario, fatura_aberta, settings, tmp_path):
        settings.MEDIA_ROOT = str(tmp_path)
        c = _cliente(cenario['admin_a'])
        falso = SimpleUploadedFile('comprovativo.pdf', b'<html><script>alert(1)</script></html>')
        assert c.post(self.URL, _corpo(fatura_aberta, comprovativo=falso), format='multipart').status_code == 400
        grande = SimpleUploadedFile('comprovativo.pdf', b'%PDF' + b'0' * (5 * 1024 * 1024))
        assert c.post(self.URL, _corpo(fatura_aberta, comprovativo=grande), format='multipart').status_code == 400
        bom = SimpleUploadedFile('comprovativo.pdf', b'%PDF-1.4 conteudo')
        assert c.post(self.URL, _corpo(fatura_aberta, comprovativo=bom), format='multipart').status_code == 201


# ---------------------------------------------------------------------------
# Registo directo pelo SuperAdmin e reconciliação por SMS
# ---------------------------------------------------------------------------
from apps.tenants.models import SaasLogAssinatura  # noqa: E402
from apps.tenants.saas_pagamentos import analisar_sms  # noqa: E402


@pytest.mark.django_db
class TestRegistoDirecto:
    URL = '/api/v1/saas/pagamentos/registar-directo/'

    def _corpo(self, cenario, fatura, **extra):
        corpo = {'instituicao_id': str(cenario['a'].id), 'fatura_id': str(fatura.id), 'metodo': 'numerario',
                 'valor': '3000.00', 'observacao': 'Entregue em mão na sede'}
        corpo.update(extra)
        return corpo

    def test_regista_confirma_e_audita(self, cenario, fatura_aberta):
        r = cenario['client'].post(self.URL, self._corpo(cenario, fatura_aberta), format='json')
        assert r.status_code == 201
        fatura_aberta.refresh_from_db()
        assert fatura_aberta.estado == 'paga' and fatura_aberta.valor_pago == Decimal('3000.00')
        pag = SaasPagamento.objects.get()
        assert pag.estado == 'confirmado' and pag.referencia.startswith('DIRECTO-')
        assert SaasLogAssinatura.objects.filter(accao='PAGAMENTO_REGISTADO_DIRECTO', instituicao=cenario['a']).exists()

    def test_so_superadmin(self, cenario, fatura_aberta):
        r = _cliente(cenario['admin_a']).post(self.URL, self._corpo(cenario, fatura_aberta), format='json')
        assert r.status_code == 403 and not SaasPagamento.objects.exists()

    @pytest.mark.parametrize('extra', [{'observacao': ''}, {'observacao': 'ab'}, {'metodo': 'Bitcoin'}, {'valor': '-1'}, {'valor': 'NaN'}])
    def test_entradas_invalidas(self, cenario, fatura_aberta, extra):
        assert cenario['client'].post(self.URL, self._corpo(cenario, fatura_aberta, **extra), format='json').status_code == 400
        assert not SaasPagamento.objects.exists()

    def test_fatura_de_outra_escola_ou_inexistente(self, cenario, fatura_aberta):
        r = cenario['client'].post(self.URL, self._corpo(cenario, fatura_aberta, instituicao_id=str(cenario['b'].id)), format='json')
        assert r.status_code == 404
        assert cenario['client'].post(self.URL, self._corpo(cenario, fatura_aberta, fatura_id='lixo'), format='json').status_code == 404

    def test_fatura_ja_paga_e_referencia_duplicada(self, cenario, fatura_aberta):
        c = cenario['client']
        assert c.post(self.URL, self._corpo(cenario, fatura_aberta, valor='1000', referencia='DEP-1'), format='json').status_code == 201
        assert c.post(self.URL, self._corpo(cenario, fatura_aberta, valor='500', referencia='dep-1'), format='json').status_code == 400
        assert c.post(self.URL, self._corpo(cenario, fatura_aberta, valor='2000', referencia='DEP-2'), format='json').status_code == 201
        # fatura liquidada: já não aceita mais pagamentos
        assert c.post(self.URL, self._corpo(cenario, fatura_aberta, valor='10', referencia='DEP-3'), format='json').status_code == 400


@pytest.mark.django_db
class TestReconciliacaoSms:
    URL = '/api/v1/saas/pagamentos/reconciliar-sms/'

    def _pag(self, cenario, fatura, ref='PP261118.1023.A12345', valor='3000.00'):
        return SaasPagamento.objects.create(fatura=fatura, instituicao=cenario['a'], metodo='M-Pesa', referencia=ref, valor=Decimal(valor))

    def _sms(self, ref='PP261118.1023.A12345', valor='3,000.00'):
        return f'Confirmado {ref}. Recebeu {valor}MT de 841234567 - JOAO SILVA aos 18/11/26 as 10:23. Ref: {ref}'

    def test_confirma_quando_referencia_e_valor_coincidem(self, cenario, fatura_aberta):
        pag = self._pag(cenario, fatura_aberta)
        r = cenario['client'].post(self.URL, {'message': self._sms()}, format='json')
        assert r.status_code == 200 and r.data['status'] == 'CONFIRMADO'
        pag.refresh_from_db()
        assert pag.estado == 'confirmado' and pag.confirmado_por.startswith('Automático (SMS)')
        assert SaasLogAssinatura.objects.filter(accao='PAGAMENTO_CONFIRMADO_SMS').exists()

    def test_segunda_sms_igual_nao_conta_duas_vezes(self, cenario, fatura_aberta):
        self._pag(cenario, fatura_aberta)
        c = cenario['client']
        assert c.post(self.URL, {'message': self._sms()}, format='json').data['status'] == 'CONFIRMADO'
        assert c.post(self.URL, {'message': self._sms()}, format='json').data['status'] == 'DUPLICADO'
        fatura_aberta.refresh_from_db()
        assert fatura_aberta.valor_pago == Decimal('3000.00')

    def test_valor_divergente_nao_confirma(self, cenario, fatura_aberta):
        pag = self._pag(cenario, fatura_aberta)
        r = cenario['client'].post(self.URL, {'message': self._sms(valor='2,000.00')}, format='json')
        assert r.data['status'] == 'VALOR_DIVERGENTE'
        pag.refresh_from_db()
        assert pag.estado == 'enviado'

    def test_sem_correspondencia_nao_cria_nada(self, cenario, fatura_aberta):
        r = cenario['client'].post(self.URL, {'message': self._sms(ref='ZZ999999.0000.B1')}, format='json')
        assert r.data['status'] == 'SEM_CORRESPONDENCIA'
        assert not SaasPagamento.objects.exists()

    def test_sms_ilegivel_e_texto_vazio(self, cenario):
        assert cenario['client'].post(self.URL, {'message': 'ola, tudo bem?'}, format='json').data['status'] == 'NAO_RECONHECIDA'
        assert cenario['client'].post(self.URL, {'message': ''}, format='json').status_code == 400

    def test_so_superadmin(self, cenario, fatura_aberta):
        self._pag(cenario, fatura_aberta)
        assert _cliente(cenario['admin_a']).post(self.URL, {'message': self._sms()}, format='json').status_code == 403

    def test_rejeitado_nao_e_confirmado_por_sms(self, cenario, fatura_aberta):
        pag = self._pag(cenario, fatura_aberta)
        pag.estado = 'rejeitado'
        pag.save()
        assert cenario['client'].post(self.URL, {'message': self._sms()}, format='json').data['status'] == 'SEM_CORRESPONDENCIA'

    @pytest.mark.parametrize('texto,valor,ref', [
        ('Recebeu 1,500.00MT de 841234567. Ref: AB12.34', Decimal('1500.00'), 'AB12.34'),
        ('Recebeu 1.500,50 MZN. Transacao ID: XY99887', Decimal('1500.50'), 'XY99887'),
        ('Recebeu 1500MT Ref ABCD1234', Decimal('1500'), 'ABCD1234'),
        ('841234567 3,000.00MT Ref: Q1W2E3', Decimal('3000.00'), 'Q1W2E3'),
    ])
    def test_analisador_de_sms(self, texto, valor, ref):
        assert analisar_sms(texto) == (valor, ref)
