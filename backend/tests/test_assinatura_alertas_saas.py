"""Alerta/resposta de assinatura da escola sobre o modelo SaaS (com o antigo como alternativa) e mensagens de bloqueio."""
import datetime
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.assistente.alertas import alertas_do_utilizador
from apps.tenants.assinatura_estado import estado_assinatura_escola, mensagem_bloqueio
from apps.tenants.models import AssinaturaEscola, Escola, Plano, SaasAssinatura, SaasPlano

HOJE = datetime.date.today()


@pytest.fixture
def escola_dir(db):
    escola = Escola.objects.create(nome='Escola Alerta Teste', nif_cnpj='NUIT_AL_1', email='alerta@sige.mz', status='ATIVA')
    dir_ = Usuario.objects.create_user(email='dir.alerta@sige.mz', password='SchoolPass2026!', role='DIRECTOR_ESCOLA', nome='Dir', escola=escola)
    plano = SaasPlano.objects.create(nome='Plano Alerta', preco_mensal=Decimal('3000.00'), limite_alunos=100, limite_professores=10)
    return escola, dir_, plano


def _saas(escola, plano, estado, dias):
    return SaasAssinatura.objects.create(instituicao=escola, plano=plano, estado=estado, proxima_fatura_em=HOJE + datetime.timedelta(days=dias))


def _titulos(user, escola):
    return [a['titulo'] for a in alertas_do_utilizador(user, escola) if 'ssinatura' in a['titulo'] or 'acesso da institui' in a['titulo'] or 'fatura' in a['titulo']]


@pytest.mark.django_db
class TestAlertaAssinaturaSaas:
    def test_vencimento_proximo(self, escola_dir):
        escola, dir_, plano = escola_dir
        _saas(escola, plano, 'activa', 6)
        assert 'A fatura da assinatura vence em 6 dia(s)' in _titulos(dir_, escola)

    def test_longe_do_vencimento_nao_avisa(self, escola_dir):
        escola, dir_, plano = escola_dir
        _saas(escola, plano, 'activa', 40)
        assert _titulos(dir_, escola) == []

    @pytest.mark.parametrize('estado,texto', [('em_atraso', 'em atraso'), ('restrita', 'em atraso'), ('suspensa', 'suspenso'), ('cancelada', 'suspenso')])
    def test_estados_criticos_sao_alta_prioridade(self, escola_dir, estado, texto):
        escola, dir_, plano = escola_dir
        _saas(escola, plano, estado, -3)
        alertas = [a for a in alertas_do_utilizador(dir_, escola) if texto in a['titulo']]
        assert alertas and alertas[0]['nivel'] == 'alta' and alertas[0]['destino'] == 'assinatura-escola'

    def test_fatura_vencida_sem_estado_critico(self, escola_dir):
        escola, dir_, plano = escola_dir
        _saas(escola, plano, 'fatura_pendente', -2)
        assert 'A fatura da assinatura venceu' in _titulos(dir_, escola)

    def test_assinatura_saas_prevalece_sobre_a_antiga(self, escola_dir):
        escola, dir_, plano = escola_dir
        legado = Plano.objects.create(nome='Plano Legado', preco=Decimal('100'))
        AssinaturaEscola.objects.create(escola=escola, plano=legado, data_fim=timezone.now() + datetime.timedelta(days=3), valor=100)
        _saas(escola, plano, 'activa', 90)
        assert _titulos(dir_, escola) == []
        info = estado_assinatura_escola(escola)
        assert info['origem'] == 'saas' and info['dias'] == 90

    def test_sem_assinatura_saas_usa_a_antiga(self, escola_dir):
        escola, dir_, _ = escola_dir
        legado = Plano.objects.create(nome='Plano Legado 2', preco=Decimal('100'))
        AssinaturaEscola.objects.create(escola=escola, plano=legado, data_fim=timezone.now() + datetime.timedelta(days=5), valor=100)
        assert 'A assinatura do sistema termina em 5 dia(s)' in _titulos(dir_, escola)
        assert estado_assinatura_escola(escola)['origem'] == 'legado'

    def test_sem_nenhuma_assinatura(self, escola_dir):
        escola, dir_, _ = escola_dir
        assert estado_assinatura_escola(escola) is None and _titulos(dir_, escola) == []


@pytest.mark.django_db
class TestMensagemBloqueio:
    def test_textos_por_motivo(self):
        assert 'removida da plataforma' in mensagem_bloqueio('Escola X', 'ELIMINADA')
        assert 'subscrição expirada' in mensagem_bloqueio('Escola X', 'EXPIRADA')
        assert 'subscrição expirada' in mensagem_bloqueio('Escola X', 'SUSPENSA')

    def test_sessao_aberta_numa_escola_eliminada_recebe_a_mensagem_certa(self, escola_dir):
        escola, dir_, _ = escola_dir
        c = APIClient()
        login = c.post('/api/v1/auth/login/', {'email': 'dir.alerta@sige.mz', 'password': 'SchoolPass2026!'}, format='json')
        assert login.status_code == 200
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")
        Escola.objects.filter(id=escola.id).update(status='ELIMINADA', eliminada_em=timezone.now())
        r = c.get('/api/v1/escola-admin/info/')
        assert r.status_code == 403 and 'removida da plataforma' in r.json()['message']

    def test_escola_expirada_mantem_a_mensagem_antiga(self, escola_dir):
        escola, dir_, _ = escola_dir
        c = APIClient()
        login = c.post('/api/v1/auth/login/', {'email': 'dir.alerta@sige.mz', 'password': 'SchoolPass2026!'}, format='json')
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")
        Escola.objects.filter(id=escola.id).update(status='EXPIRADA')
        r = c.get('/api/v1/escola-admin/info/')
        assert r.status_code == 403 and 'subscrição expirada' in r.json()['message']
