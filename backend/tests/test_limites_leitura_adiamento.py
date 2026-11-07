import pytest
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.alunos.models import Aluno
from apps.professores.models import Professor
from apps.tenants.models import Escola, Pacote, SaasPlano, SaasAssinatura, SaasFatura, SaasLogAssinatura
from apps.tenants.pacotes import PACOTES_PADRAO, DESCONTOS_PADRAO, limpar_cache_funcionalidades
from apps.tenants.saas_middleware import limpar_cache_assinatura
from apps.tenants.saas_services import avaliar_regras_automaticas_instituicao
from apps.turmas.models import Turma


def _pacote(codigo, **extra):
    dados = next(p for p in PACOTES_PADRAO if p['codigo'] == codigo)
    obj, _ = Pacote.objects.get_or_create(
        codigo=codigo, defaults={**{k: v for k, v in dados.items() if k != 'codigo'}, 'descontos': dict(DESCONTOS_PADRAO)})
    for k, v in extra.items():
        setattr(obj, k, v)
    obj.save()
    return obj


@pytest.mark.django_db
class TestLimitesEModoLeitura:
    def setup_method(self):
        limpar_cache_assinatura()
        limpar_cache_funcionalidades()
        self.client = APIClient()
        self.super = Usuario.objects.create_superuser(email='lim.super@sige.mz', password='AdminPassword2026!', nome='Super')
        self.plano = SaasPlano.objects.create(nome='Plano Lim', preco_mensal=Decimal('1000'))
        self.hoje = timezone.localdate()

    def _escola(self, nif, pacote=None, status='ATIVA'):
        e = Escola.objects.create(nome=f'Escola {nif}', nif_cnpj=nif, email=f'{nif.lower()}@sige.mz', status=status, pacote=pacote)
        u = Usuario.objects.create_user(email=f'admin.{nif.lower()}@sige.mz', password='SchoolPass2026!', role='ADMIN_ESCOLA', escola=e)
        return e, u

    def _login(self, email, senha):
        self.client.credentials()
        res = self.client.post('/api/v1/auth/login/', {'email': email, 'password': senha}, format='json')
        assert res.status_code == 200, res.content
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['token']}")

    # ---- Limites do pacote ----
    def test_limite_de_alunos_e_professores_do_pacote(self):
        pacote = _pacote('essencial', limite_alunos=2, limite_professores=1)
        escola, _ = self._escola('NIF_LIM1', pacote)
        turma = Turma.objects.create(escola=escola, nome='10A', grau_ano='10ª Classe')
        for i in range(2):
            Aluno.objects.create(escola=escola, turma=turma, matricula=f'M{i}', nome=f'Aluno {i}', data_nascimento='2009-01-01', genero='M')
        Professor.objects.create(escola=escola, nome='Prof Um', codigo='P1', email='p1@sige.mz', especialidade='Matemática')
        self._login('admin.nif_lim1@sige.mz', 'SchoolPass2026!')

        res = self.client.post('/api/v1/alunos/', {'nome': 'Excedente', 'turma': str(turma.id), 'genero': 'F',
                                                    'data_nascimento': '2010-02-02'}, format='json')
        assert res.status_code == 400 and 'Limite do pacote' in res.content.decode('utf-8')
        res = self.client.post('/api/v1/professores/', {'nome': 'Prof Dois', 'email': 'p2@sige.mz', 'especialidade': 'Física'}, format='json')
        assert res.status_code == 400 and 'Limite do pacote' in res.content.decode('utf-8')

    def test_escola_sem_pacote_nao_tem_limite(self):
        from apps.tenants.pacotes import mensagem_limite_excedido
        escola, _ = self._escola('NIF_LIM2', None)
        assert mensagem_limite_excedido(escola, 'alunos') is None

    # ---- Modo leitura na suspensão ----
    def _suspender(self, escola):
        ass = SaasAssinatura.objects.create(instituicao=escola, plano=self.plano, periodicidade='mensal',
                                            modo_data_limite='manual', dias_tolerancia=5, dias_ate_suspensao=15,
                                            estado='suspensa', proxima_fatura_em=self.hoje + timedelta(days=30))
        Escola.objects.filter(id=escola.id).update(status='SUSPENSA')
        limpar_cache_assinatura()
        return ass

    def test_escola_suspensa_por_pagamento_entra_em_modo_leitura(self):
        escola, _ = self._escola('NIF_LEI1')
        self._suspender(escola)
        self._login('admin.nif_lei1@sige.mz', 'SchoolPass2026!')  # login permitido
        assert self.client.get('/api/v1/alunos/').status_code == 200
        res = self.client.post('/api/v1/alunos/', {'nome': 'X'}, format='json')
        assert res.status_code == 403 and res.json()['codigo'] == 'ASSINATURA_RESTRITA'

    def test_desactivacao_manual_continua_a_bloquear_tudo(self):
        escola, _ = self._escola('NIF_LEI2', status='SUSPENSA')  # sem assinatura suspensa => manual
        res = self.client.post('/api/v1/auth/login/', {'email': 'admin.nif_lei2@sige.mz', 'password': 'SchoolPass2026!'}, format='json')
        assert res.status_code in (400, 401, 403)

    def test_bloqueio_manual_bloqueia_mesmo_com_assinatura_suspensa(self):
        escola, _ = self._escola('NIF_LEI3')
        self._suspender(escola)
        Escola.objects.filter(id=escola.id).update(bloqueada_manualmente=True)
        res = self.client.post('/api/v1/auth/login/', {'email': 'admin.nif_lei3@sige.mz', 'password': 'SchoolPass2026!'}, format='json')
        assert res.status_code in (400, 401, 403)

    # ---- Excepção: não suspender até uma data ----
    def _com_fatura_em_corte(self, escola):
        ass = SaasAssinatura.objects.create(instituicao=escola, plano=self.plano, periodicidade='mensal',
                                            modo_data_limite='manual', dias_tolerancia=5, dias_ate_suspensao=15,
                                            estado='em_atraso', proxima_fatura_em=self.hoje + timedelta(days=30))
        limite = self.hoje - timedelta(days=40)
        SaasFatura.objects.create(assinatura=ass, instituicao=escola, numero_fatura='FAT-ADI', periodo_inicio=limite,
                                  periodo_fim=self.hoje, valor=Decimal('1000'), data_abertura=limite, data_limite=limite,
                                  data_limite_manual=limite, estado='em_atraso')
        return ass

    def test_excepcao_adia_suspensao_e_fica_registada(self):
        escola, _ = self._escola('NIF_ADI')
        self._com_fatura_em_corte(escola)
        self._login('lim.super@sige.mz', 'AdminPassword2026!')
        url = f'/api/v1/saas/instituicoes/{escola.id}/adiar-suspensao/'

        assert self.client.post(url, {'ate': str(self.hoje + timedelta(days=10)), 'motivo': ''}, format='json').status_code == 400
        assert self.client.post(url, {'ate': str(self.hoje + timedelta(days=200)), 'motivo': 'acordo de pagamento'}, format='json').status_code == 400

        res = self.client.post(url, {'ate': str(self.hoje + timedelta(days=10)), 'motivo': 'Acordo de pagamento'}, format='json')
        assert res.status_code == 200
        r = avaliar_regras_automaticas_instituicao(escola.id, 'auto_avaliar')
        assert r['estado_novo'] == 'restrita'
        assert SaasLogAssinatura.objects.filter(instituicao=escola, accao='SUSPENSAO_ADIADA').exists()

        assert self.client.post(url, {'ate': None}, format='json').status_code == 200
        r = avaliar_regras_automaticas_instituicao(escola.id, 'auto_avaliar')
        assert r['estado_novo'] == 'suspensa'

    def test_so_superadmin_adia_suspensao(self):
        escola, _ = self._escola('NIF_ADI2')
        self._com_fatura_em_corte(escola)
        self._login('admin.nif_adi2@sige.mz', 'SchoolPass2026!')
        res = self.client.post(f'/api/v1/saas/instituicoes/{escola.id}/adiar-suspensao/',
                               {'ate': str(self.hoje + timedelta(days=5)), 'motivo': 'tentativa indevida'}, format='json')
        assert res.status_code == 403
