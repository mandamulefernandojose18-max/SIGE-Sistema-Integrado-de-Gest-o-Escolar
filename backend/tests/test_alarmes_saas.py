import pytest
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.tenants.models import (
    Escola, SaasPlano, SaasAssinatura, SaasFatura, SaasPagamento, SaasLogAssinatura, SaasRotinaExecucao,
)
from apps.tenants.saas_alarmes import calcular_alarmes
from apps.tenants.saas_middleware import limpar_cache_assinatura
from apps.tenants.saas_services import executar_rotina_diaria_saas_python


def _codigos(dados):
    return {a['codigo']: a for a in dados['alarmes']}


@pytest.mark.django_db
class TestAlarmesSupervisaoSaaS:
    def setup_method(self):
        limpar_cache_assinatura()
        self.client = APIClient()
        self.plano = SaasPlano.objects.create(nome='Plano Alarme', preco_mensal=Decimal('1500'))
        self.super = Usuario.objects.create_superuser(email='alarme.super@sige.mz', password='AdminPassword2026!', nome='Super')
        self.escola = Escola.objects.create(nome='Escola Alarme', nif_cnpj='NUIT_ALARME_1', email='alarme1@sige.mz', status='ATIVA')
        self.admin = Usuario.objects.create_user(email='alarme.admin@sige.mz', password='SchoolPass2026!',
                                                 role='ADMIN_ESCOLA', escola=self.escola)
        self.hoje = timezone.localdate()
        self.ass = SaasAssinatura.objects.create(
            instituicao=self.escola, plano=self.plano, periodicidade='mensal', modo_data_limite='manual',
            dias_tolerancia=5, dias_ate_suspensao=15, estado='fatura_pendente',
            proxima_fatura_em=self.hoje + timedelta(days=30))

    def _fatura(self, numero, limite, valor='1500', estado='aberta'):
        return SaasFatura.objects.create(
            assinatura=self.ass, instituicao=self.escola, numero_fatura=numero,
            periodo_inicio=self.hoje - timedelta(days=40), periodo_fim=self.hoje - timedelta(days=10),
            valor=Decimal(valor), data_abertura=self.hoje - timedelta(days=40), data_limite=limite,
            data_limite_manual=limite, estado=estado)

    def _login(self, email, senha):
        res = self.client.post('/api/v1/auth/login/', {'email': email, 'password': senha}, format='json')
        assert res.status_code == 200
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['token']}")

    def test_so_superadmin_ve_alarmes(self):
        self._login('alarme.admin@sige.mz', 'SchoolPass2026!')
        assert self.client.get('/api/v1/saas/alarmes').status_code == 403
        self.client.credentials()
        self._login('alarme.super@sige.mz', 'AdminPassword2026!')
        res = self.client.get('/api/v1/saas/alarmes')
        assert res.status_code == 200 and 'alarmes' in res.json()['data']

    def test_comprovativo_pendente_ha_mais_de_24h_e_critico(self):
        fat = self._fatura('FAT-AL-1', self.hoje + timedelta(days=3))
        pag = SaasPagamento.objects.create(fatura=fat, instituicao=self.escola, metodo='M-Pesa', referencia='REF1', valor=Decimal('1500'))
        SaasPagamento.objects.filter(id=pag.id).update(criado_em=timezone.now() - timedelta(hours=30))
        a = _codigos(calcular_alarmes())['comprovativos_pendentes']
        assert a['severidade'] == 'critica' and a['total'] == 1

    def test_fatura_a_vencer_em_atraso_e_a_entrar_em_suspensao(self):
        self._fatura('FAT-AL-VENCER', self.hoje + timedelta(days=2))
        d = _codigos(calcular_alarmes())
        assert d['faturas_a_vencer']['total'] == 1 and d['faturas_a_vencer']['severidade'] == 'aviso'

        self.escola2 = Escola.objects.create(nome='Escola Atraso', nif_cnpj='NUIT_ALARME_2', email='alarme2@sige.mz', status='ATIVA')
        ass2 = SaasAssinatura.objects.create(instituicao=self.escola2, plano=self.plano, periodicidade='mensal',
                                             modo_data_limite='manual', dias_tolerancia=5, dias_ate_suspensao=15,
                                             estado='em_atraso', proxima_fatura_em=self.hoje + timedelta(days=30))
        # limite há 15 dias: tolerância (5) + suspensão (15) => corte em 5 dias
        limite = self.hoje - timedelta(days=15)
        SaasFatura.objects.create(assinatura=ass2, instituicao=self.escola2, numero_fatura='FAT-AL-ATR',
                                  periodo_inicio=limite, periodo_fim=self.hoje, valor=Decimal('1500'),
                                  data_abertura=limite, data_limite=limite, data_limite_manual=limite, estado='em_atraso')
        d = _codigos(calcular_alarmes())
        assert d['faturas_em_atraso']['total'] == 1
        assert d['a_entrar_em_suspensao']['total'] == 1
        assert d['a_entrar_em_suspensao']['itens'][0]['instituicao'] == 'Escola Atraso'

    def test_anomalia_referencia_duplicada(self):
        fat = self._fatura('FAT-AL-DUP', self.hoje + timedelta(days=20))
        SaasPagamento.objects.create(fatura=fat, instituicao=self.escola, metodo='M-Pesa', referencia='DUP1', valor=Decimal('1500'))
        SaasPagamento.objects.create(fatura=fat, instituicao=self.escola, metodo='e-Mola', referencia='DUP1', valor=Decimal('1500'))
        a = _codigos(calcular_alarmes())['anomalias']
        assert a['total'] >= 2

    def test_rotina_diaria_regista_execucao_e_alarme_desaparece(self):
        assert 'rotina_diaria' in _codigos(calcular_alarmes())
        executar_rotina_diaria_saas_python()
        assert SaasRotinaExecucao.objects.filter(sucesso=True).count() == 1
        assert 'rotina_diaria' not in _codigos(calcular_alarmes())

        SaasRotinaExecucao.objects.update(executada_em=timezone.now() - timedelta(hours=40))
        assert _codigos(calcular_alarmes())['rotina_diaria']['severidade'] == 'critica'

    def test_pagamento_parcial_nao_reactiva_e_total_reactiva(self):
        self.client.credentials()
        limite = self.hoje - timedelta(days=40)  # além de tolerância + corte
        fat = self._fatura('FAT-AL-PARC', limite, estado='em_atraso')
        self.ass.estado = 'suspensa'
        self.ass.save()
        Escola.objects.filter(id=self.escola.id).update(status='SUSPENSA')
        self._login('alarme.super@sige.mz', 'AdminPassword2026!')

        parcial = SaasPagamento.objects.create(fatura=fat, instituicao=self.escola, metodo='M-Pesa', referencia='PARC1', valor=Decimal('500'))
        res = self.client.post(f'/api/v1/saas/pagamentos/{parcial.id}/confirmar/')
        assert res.status_code == 200
        self.escola.refresh_from_db()
        assert self.escola.status == 'SUSPENSA'

        restante = SaasPagamento.objects.create(fatura=fat, instituicao=self.escola, metodo='M-Pesa', referencia='PARC2', valor=Decimal('1000'))
        res = self.client.post(f'/api/v1/saas/pagamentos/{restante.id}/confirmar/')
        assert res.status_code == 200
        self.escola.refresh_from_db()
        self.ass.refresh_from_db()
        assert self.escola.status == 'ATIVA' and self.ass.estado == 'activa'
        assert SaasLogAssinatura.objects.filter(accao='PAGAMENTO_CONFIRMADO', instituicao=self.escola).count() == 2
