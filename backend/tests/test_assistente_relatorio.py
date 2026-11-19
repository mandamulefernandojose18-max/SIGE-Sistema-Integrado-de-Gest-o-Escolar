import datetime
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano
from apps.assistente.models import ConsultaAssistente

URL = '/api/v1/assistente/relatorio/'


@pytest.mark.django_db
class TestRelatorio:
    def setup_method(self):
        plano = Plano.objects.create(nome='PLANO_REL', preco=2000, duracao_dias=30)
        self.e1 = Escola.objects.create(nome='Escola Um', nif_cnpj='NIF_REL1', email='r1@sige.mz', status='ATIVA', plano=plano)
        self.e2 = Escola.objects.create(nome='Escola Dois', nif_cnpj='NIF_REL2', email='r2@sige.mz', status='ATIVA', plano=plano)

    def _cli(self, role, email, escola=None, **extra):
        u = Usuario.objects.create_user(email=email, password='PassTeste123!', role=role, escola=escola, **extra) if role != 'SUPERADMIN' \
            else Usuario.objects.create_superuser(email=email, password='PassTeste123!')
        c = APIClient()
        c.force_authenticate(u)
        return c, u

    def _c(self, escola, pergunta, intencao, util=None, user=None, dias=0):
        c = ConsultaAssistente.objects.create(escola=escola, usuario=user, pergunta=pergunta, intencao=intencao, util=util)
        if dias:
            ConsultaAssistente.objects.filter(id=c.id).update(created_at=timezone.now() - datetime.timedelta(days=dias))

    def test_so_super_admin_e_direccao(self):
        for role in ('ALUNO', 'ENCARREGADO', 'PROFESSOR', 'SECRETARIA', 'DAP', 'FINANCEIRO', 'CHEFE_SECRETARIA'):
            cli, _ = self._cli(role, f'{role.lower()}@rel.mz', self.e1)
            assert cli.get(URL).status_code == 403, role
        assert APIClient().get(URL).status_code == 401

    def test_estado_vazio(self):
        cli, _ = self._cli('DIRECTOR_ESCOLA', 'dir.rel@sige.mz', self.e1)
        d = cli.get(URL).data
        assert d['total'] == 0 and d['perguntas_a_melhorar'] == [] and d['taxas'] == {}

    def test_direccao_so_ve_a_sua_escola_e_agrupa_perguntas(self):
        cli, u = self._cli('DIRECTOR_ESCOLA', 'dir2.rel@sige.mz', self.e1)
        self._c(self.e1, 'como faço a magia?', 'desconhecida', user=u)
        self._c(self.e1, 'Como faço a MAGIA', 'desconhecida', user=u)               # mesma pergunta, escrita diferente → um só grupo
        self._c(self.e1, 'quantas faltas tem?', 'faltas', util=False, user=u)
        self._c(self.e1, 'qual o saldo?', 'fora_do_painel', user=u)
        self._c(self.e1, 'quais as notas?', 'notas', util=True, user=u)
        self._c(self.e2, 'pergunta da outra escola', 'desconhecida')
        self._c(self.e1, 'pergunta antiga', 'desconhecida', dias=90)                 # fora do período de 30 dias
        d = cli.get(URL).data
        assert d['total'] == 5 and d['ambito'] == 'escola'
        assert d['taxas']['sem_resposta_pct'] == 40.0 and d['taxas']['fora_do_painel_pct'] == 20.0
        assert d['taxas']['util_pct'] == 20.0 and d['taxas']['nao_util_pct'] == 20.0 and d['taxas']['com_feedback'] == 2
        perguntas = {p['pergunta'].lower().strip('?'): p for p in d['perguntas_a_melhorar']}
        assert perguntas['como faço a magia']['vezes'] == 2 and perguntas['como faço a magia']['motivos'] == ['sem resposta']
        assert perguntas['quantas faltas tem']['motivos'] == ['não útil'] and 'outra escola' not in str(d)
        assert all(p['escolas'] == [] for p in d['perguntas_a_melhorar'])             # a direcção não vê nomes de escolas
        assert 'resposta' not in str(d.keys()).lower()
        assert cli.get(URL + '?dias=120').data['total'] == 6                         # período maior apanha a antiga

    def test_super_admin_ve_todas_as_escolas_e_a_escola_em_inspeccao(self):
        sup, u = self._cli('SUPERADMIN', 'super.rel@sige.mz')
        self._c(self.e1, 'pergunta um', 'desconhecida')
        self._c(self.e2, 'pergunta dois', 'desconhecida')
        self._c(None, 'quantas escolas?', 'plat_resumo', user=u)                      # modo plataforma (sem escola)
        d = sup.get(URL).data
        assert d['total'] == 3 and d['ambito'] == 'plataforma'
        assert {e for p in d['perguntas_a_melhorar'] for e in p['escolas']} == {'Escola Um', 'Escola Dois'}
        r = sup.get(URL, HTTP_X_TENANT_ID=str(self.e1.id)).data
        assert r['total'] == 1 and r['ambito'] == 'escola'

    def test_dias_invalidos_nao_partem(self):
        cli, _ = self._cli('ADMIN_ESCOLA', 'adm.rel@sige.mz', self.e1)
        assert cli.get(URL + '?dias=abc').data['periodo_dias'] == 30
        assert cli.get(URL + '?dias=9999').data['periodo_dias'] == 180
