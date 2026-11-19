"""Lixeira de escolas (eliminação reversível), métricas SaaS unificadas e avisos de pagamento à escola."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import LogAuditoria, Usuario
from apps.assistente.alertas import alertas_do_utilizador
from apps.tenants.models import (Escola, SaasAssinatura, SaasFatura, SaasLogAssinatura, SaasPagamento, SaasPlano)
from apps.tenants.saas_metricas import calcular_metricas_saas
from apps.tenants.saas_middleware import limpar_cache_assinatura
from apps.tenants.saas_services import executar_rotina_diaria_saas_python


@pytest.fixture
def base(db):
    limpar_cache_assinatura()
    sa = Usuario.objects.create_superuser(email='sa.fase3@sige.mz', password='AdminPassword2026!', nome='Super Admin')
    a = Escola.objects.create(nome='Escola Alfa Teste', nif_cnpj='NUIT_ALFA', email='alfa@sige.mz', status='ATIVA')
    b = Escola.objects.create(nome='Escola Beta Teste', nif_cnpj='NUIT_BETA', email='beta@sige.mz', status='ATIVA')
    plano = SaasPlano.objects.create(nome='Plano Fase3', preco_mensal=Decimal('3000.00'), limite_alunos=1000, limite_professores=100)
    c = APIClient()
    c.force_authenticate(sa)
    return {'c': c, 'sa': sa, 'a': a, 'b': b, 'plano': plano}


def _ass(escola, plano, estado='activa', periodicidade='mensal'):
    return SaasAssinatura.objects.create(instituicao=escola, plano=plano, periodicidade=periodicidade, estado=estado,
                                         proxima_fatura_em=timezone.localdate())


def _lixo(base, escola, nome=None):
    return base['c'].delete(f'/api/v1/saas-admin/escolas/{escola.id}/', {'confirmar_nome': nome or escola.nome}, format='json')


@pytest.mark.django_db
class TestLixeira:
    def test_eliminar_move_para_a_lixeira_e_esconde(self, base):
        r = _lixo(base, base['a'])
        assert r.status_code == 200 and 'lixeira' in r.data['message']
        assert not Escola.objects.filter(id=base['a'].id).exists()
        e = Escola.todas.get(id=base['a'].id)
        assert e.status == 'ELIMINADA' and e.status_antes_eliminacao == 'ATIVA' and e.eliminada_em and e.eliminada_por
        lista = base['c'].get('/api/v1/saas-admin/escolas/').data['data']
        assert str(base['a'].id) not in [x['id'] for x in lista]
        lixo = base['c'].get('/api/v1/saas-admin/escolas/?lixeira=1').data['data']
        assert [x['id'] for x in lixo] == [str(base['a'].id)]
        assert LogAuditoria.objects.filter(entidade='ESCOLA', acao='ELIMINAR', objeto_id=str(base['a'].id)).exists()

    def test_nome_errado_nao_elimina(self, base):
        assert _lixo(base, base['a'], 'Outra').status_code == 400
        assert Escola.objects.filter(id=base['a'].id).exists()

    def test_restaurar_devolve_o_estado_anterior(self, base):
        _lixo(base, base['a'])
        r = base['c'].post(f"/api/v1/saas-admin/escolas/{base['a'].id}/restaurar/")
        assert r.status_code == 200
        e = Escola.objects.get(id=base['a'].id)
        assert e.status == 'ATIVA' and e.eliminada_em is None and e.status_antes_eliminacao == ''
        assert LogAuditoria.objects.filter(entidade='ESCOLA', acao='RESTAURAR').exists()

    def test_restaurar_ou_apagar_escola_que_nao_esta_na_lixeira_da_404(self, base):
        assert base['c'].post(f"/api/v1/saas-admin/escolas/{base['a'].id}/restaurar/").status_code == 404
        assert base['c'].post(f"/api/v1/saas-admin/escolas/{base['a'].id}/eliminar-definitivo/", {'confirmar_nome': base['a'].nome}, format='json').status_code == 404

    def test_apagar_de_vez_so_apos_retencao_e_com_nome(self, base):
        _lixo(base, base['a'])
        url = f"/api/v1/saas-admin/escolas/{base['a'].id}/eliminar-definitivo/"
        r = base['c'].post(url, {'confirmar_nome': base['a'].nome}, format='json')
        assert r.status_code == 400 and 'dias na lixeira' in r.data['message']
        Escola.todas.filter(id=base['a'].id).update(eliminada_em=timezone.now() - timedelta(days=31))
        assert base['c'].post(url, {'confirmar_nome': 'errado'}, format='json').status_code == 400
        assert Escola.todas.filter(id=base['a'].id).exists()
        r = base['c'].post(url, {'confirmar_nome': base['a'].nome}, format='json')
        assert r.status_code == 200
        assert not Escola.todas.filter(id=base['a'].id).exists()
        assert LogAuditoria.objects.filter(entidade='ESCOLA', acao='ELIMINAR_DEFINITIVO').exists()

    def test_so_superadmin(self, base):
        admin = Usuario.objects.create_user(email='dir.fase3@sige.mz', password='SchoolPass2026!', role='ADMIN_ESCOLA', nome='Dir', escola=base['b'])
        c = APIClient()
        c.force_authenticate(admin)
        for url, met in ((f"/api/v1/saas-admin/escolas/{base['a'].id}/restaurar/", 'post'),
                         (f"/api/v1/saas-admin/escolas/{base['a'].id}/eliminar-definitivo/", 'post')):
            assert getattr(c, met)(url).status_code == 403

    def test_nuit_de_escola_na_lixeira_da_400_amigavel(self, base):
        _lixo(base, base['a'])
        r = base['c'].post('/api/v1/saas-admin/escolas/', {'nome': 'Nova', 'nif_cnpj': 'NUIT_ALFA', 'email': 'nova@sige.mz'}, format='json')
        assert r.status_code == 400 and 'NUIT' in r.data['message']

    def test_escola_na_lixeira_nao_e_facturada_nem_aparece_nas_listas(self, base):
        ass = _ass(base['a'], base['plano'])
        _lixo(base, base['a'])
        executar_rotina_diaria_saas_python()
        assert not SaasFatura.objects.filter(instituicao=base['a']).exists()
        ass.refresh_from_db()
        assert ass.estado == 'activa'
        r = base['c'].get('/api/v1/saas/assinaturas/')
        assert r.status_code == 200
        assert 'Escola Alfa Teste' not in str(r.data)
        assert base['c'].get('/api/v1/saas/resumo/').data['data']['total_instituicoes'] == 1

    def test_utilizador_da_escola_na_lixeira_fica_bloqueado(self, base):
        Usuario.objects.create_user(email='dir.alfa@sige.mz', password='SchoolPass2026!', role='ADMIN_ESCOLA', nome='Dir Alfa', escola=base['a'])
        c = APIClient()
        login = c.post('/api/v1/auth/login/', {'email': 'dir.alfa@sige.mz', 'password': 'SchoolPass2026!'}, format='json')
        assert login.status_code == 200
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")
        assert c.get('/api/v1/escola-admin/info/').status_code == 200
        _lixo(base, base['a'])
        # sessão já aberta: o middleware bloqueia a escola na lixeira
        assert c.get('/api/v1/escola-admin/info/').status_code == 403
        # e já não consegue iniciar sessão de novo
        novo = APIClient().post('/api/v1/auth/login/', {'email': 'dir.alfa@sige.mz', 'password': 'SchoolPass2026!'}, format='json')
        assert novo.status_code in (401, 403, 404)


@pytest.mark.django_db
class TestMetricas:
    def test_mrr_arr_sobre_assinaturas_contratadas(self, base):
        _ass(base['a'], base['plano'], 'activa', 'mensal')            # 3000
        _ass(base['b'], base['plano'], 'em_atraso', 'anual')          # 3000 x 12 x 0,85 / 12 = 2550
        c = Escola.objects.create(nome='Escola Gama Teste', nif_cnpj='NUIT_GAMA', email='gama@sige.mz')
        d = Escola.objects.create(nome='Escola Delta Teste', nif_cnpj='NUIT_DELTA', email='delta@sige.mz')
        _ass(c, base['plano'], 'teste')                               # não conta
        _ass(d, base['plano'], 'suspensa')                            # não conta
        m = calcular_metricas_saas()
        assert m['mrr'] == 5550.0 and m['arr'] == 66600.0 and m['pagantes'] == 2
        assert m['escolas'] == {'total': 4, 'ativas': 3, 'expiradas': 1}
        r = base['c'].get('/api/v1/saas-admin/metrics/')
        assert r.status_code == 200 and r.data['data']['mrr'] == 5550.0

    def test_churn_real_so_conta_perdas_recentes_que_continuam(self, base):
        ass_a = _ass(base['a'], base['plano'], 'activa')
        ass_b = _ass(base['b'], base['plano'], 'suspensa')
        SaasLogAssinatura.objects.create(instituicao=base['b'], assinatura=ass_b, accao='SUSPENSAO_AUTOMATICA',
                                         estado_anterior='activa', estado_novo='suspensa')
        m = calcular_metricas_saas()
        assert m['churn_escolas'] == 1 and m['churn'] == 50.0
        # reactivada entretanto: deixa de contar
        ass_b.estado = 'activa'
        ass_b.save()
        assert calcular_metricas_saas()['churn'] == 0.0
        # perda antiga (fora da janela de 30 dias): não conta
        ass_b.estado = 'suspensa'
        ass_b.save()
        SaasLogAssinatura.objects.all().update(criado_em=timezone.now() - timedelta(days=45))
        assert calcular_metricas_saas()['churn'] == 0.0
        assert ass_a.estado == 'activa'

    def test_sem_assinaturas_tudo_a_zero_e_escola_na_lixeira_fica_de_fora(self, base):
        m = calcular_metricas_saas()
        assert m['mrr'] == 0 and m['churn'] == 0 and m['escolas']['total'] == 2
        _ass(base['a'], base['plano'], 'activa')
        _lixo(base, base['a'])
        m = calcular_metricas_saas()
        assert m['mrr'] == 0 and m['escolas']['total'] == 1


@pytest.mark.django_db
class TestAvisosDePagamento:
    def _fatura(self, base):
        hoje = timezone.localdate()
        ass = _ass(base['a'], base['plano'])
        return SaasFatura.objects.create(assinatura=ass, instituicao=base['a'], numero_fatura='FAT-AV-1', periodo_inicio=hoje,
                                         periodo_fim=hoje + timedelta(days=30), valor=Decimal('3000.00'), data_abertura=hoje,
                                         data_limite=hoje + timedelta(days=5), estado='aberta')

    def _pag(self, base, fat, ref, estado, motivo=None, dias=0):
        return SaasPagamento.objects.create(fatura=fat, instituicao=base['a'], metodo='M-Pesa', referencia=ref, valor=Decimal('3000.00'),
                                            estado=estado, motivo_rejeicao=motivo, confirmado_em=timezone.now() - timedelta(days=dias))

    def _titulos(self, user, escola):
        return [a['titulo'] for a in alertas_do_utilizador(user, escola)]

    def test_rejeitado_aparece_com_motivo_e_some_quando_ha_novo_comprovativo(self, base):
        dir_ = Usuario.objects.create_user(email='dir.av@sige.mz', password='SchoolPass2026!', role='DIRECTOR_ESCOLA', nome='Dir', escola=base['a'])
        fat = self._fatura(base)
        rej = self._pag(base, fat, 'REF-REJ', 'rejeitado', 'Comprovativo ilegível')
        alertas = alertas_do_utilizador(dir_, base['a'])
        a = next(x for x in alertas if 'REF-REJ' in x['titulo'])
        assert a['nivel'] == 'alta' and 'ilegível' in a['detalhe'] and a['destino'] == 'assinatura-escola'
        SaasPagamento.objects.create(fatura=fat, instituicao=base['a'], metodo='M-Pesa', referencia='REF-NOVO', valor=Decimal('3000.00'))
        assert not any('REF-REJ' in t for t in self._titulos(dir_, base['a']))
        assert rej.estado == 'rejeitado'

    def test_confirmado_so_durante_7_dias_e_perfis_sem_acesso_nao_veem(self, base):
        fin = Usuario.objects.create_user(email='fin.av@sige.mz', password='SchoolPass2026!', role='FINANCEIRO', nome='Fin', escola=base['a'])
        prof = Usuario.objects.create_user(email='prof.av@sige.mz', password='SchoolPass2026!', role='PROFESSOR', nome='Prof', escola=base['a'])
        fat = self._fatura(base)
        self._pag(base, fat, 'REF-OK-RECENTE', 'confirmado', dias=1)
        self._pag(base, fat, 'REF-OK-ANTIGO', 'confirmado', dias=10)
        titulos = self._titulos(fin, base['a'])
        assert any('REF-OK-RECENTE' in t for t in titulos) and not any('REF-OK-ANTIGO' in t for t in titulos)
        assert not any('REF-OK' in t for t in self._titulos(prof, base['a']))
        # financeiro não tem o ecrã "assinatura-escola" no menu: sem destino
        assert next(x for x in alertas_do_utilizador(fin, base['a']) if 'REF-OK-RECENTE' in x['titulo'])['destino'] is None

    def test_nao_mostra_pagamentos_de_outra_escola(self, base):
        dir_b = Usuario.objects.create_user(email='dir.b.av@sige.mz', password='SchoolPass2026!', role='DIRECTOR_ESCOLA', nome='Dir B', escola=base['b'])
        fat = self._fatura(base)
        self._pag(base, fat, 'REF-DE-A', 'rejeitado', 'x')
        assert not any('REF-DE-A' in t for t in self._titulos(dir_b, base['b']))
