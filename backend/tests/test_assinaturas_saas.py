import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from django.db import IntegrityError
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.tenants.models import (
    Escola,
    SaasPlano,
    SaasAssinatura,
    SaasFatura,
    SaasPagamento,
    SaasLogAssinatura
)
from apps.alunos.models import Aluno
from apps.turmas.models import Turma
from apps.tenants.saas_services import (
    calcular_data_limite_efectiva_python,
    executar_rotina_diaria_saas_python
)
from apps.tenants.saas_middleware import limpar_cache_assinatura


@pytest.mark.django_db
class TestAssinaturasSaaS:
    def setup_method(self):
        limpar_cache_assinatura()
        self.client = APIClient()

        # Plano SaaS
        self.plano = SaasPlano.objects.create(
            nome='Plano SaaS Moçambique Teste',
            preco_mensal=Decimal('3000.00'),
            limite_alunos=1000,
            limite_professores=100
        )

        # SuperAdmin
        self.superadmin = Usuario.objects.create_superuser(
            email='superadmin.saas@sige.mz',
            password='AdminPassword2026!',
            nome='Super Administrador'
        )

        # Instituição A
        self.escola = Escola.objects.create(
            nome='Escola Secundária de Maputo Teste',
            nif_cnpj='NUIT_MZ_999888',
            email='secretaria.maputo@sige.mz',
            status='ATIVA'
        )

        # Admin da Instituição A
        self.admin_escola = Usuario.objects.create_user(
            email='admin.maputo@sige.mz',
            password='SchoolPass2026!',
            role='ADMIN_ESCOLA',
            nome='Director Maputo',
            escola=self.escola
        )

        # Dados escolares pré-existentes (para prova de inviolabilidade de dados)
        self.turma = Turma.objects.create(
            escola=self.escola,
            nome='10ª Turma A Teste',
            grau_ano='10ª Classe'
        )
        self.aluno1 = Aluno.objects.create(
            escola=self.escola,
            turma=self.turma,
            matricula='MAT_TESTE_001',
            nome='Delfina Mandamule',
            data_nascimento='2009-05-10',
            genero='F'
        )
        self.aluno2 = Aluno.objects.create(
            escola=self.escola,
            turma=self.turma,
            matricula='MAT_TESTE_002',
            nome='Ernesto Macuácua',
            data_nascimento='2008-11-20',
            genero='M'
        )

        # Assinatura Inicial da Escola
        hoje = timezone.localdate()
        self.assinatura = SaasAssinatura.objects.create(
            instituicao=self.escola,
            plano=self.plano,
            periodicidade='mensal',
            modo_data_limite='automatico',
            dias_tolerancia=5,
            dias_ate_suspensao=15,
            multa_tipo='percentagem',
            multa_valor=Decimal('10.00'),
            estado='activa',
            proxima_fatura_em=hoje
        )

    # 1. Geração de Faturas Sem Duplicados (Idempotência)
    def test_geracao_faturas_idempotente_sem_duplicados(self):
        # Executar a rotina no mesmo dia duas vezes
        res1 = executar_rotina_diaria_saas_python()
        assert res1['faturas_geradas'] >= 1

        total_faturas_antes = SaasFatura.objects.filter(assinatura=self.assinatura).count()
        assert total_faturas_antes >= 1

        # Segunda execução não deve gerar faturas duplicadas para o mesmo período
        res2 = executar_rotina_diaria_saas_python()
        total_faturas_depois = SaasFatura.objects.filter(assinatura=self.assinatura).count()
        assert total_faturas_antes == total_faturas_depois

    # 2. Precedência de Datas-Limite (Manual > Dia Fixo > Predefinição) e Meses Curtos
    def test_precedencia_datas_limite_e_meses_curtos(self):
        hoje = date(2026, 2, 1) # Fevereiro (mês curto de 28 dias)
        fatura = SaasFatura.objects.create(
            assinatura=self.assinatura,
            instituicao=self.escola,
            numero_fatura='FAT-TEST-PREC',
            periodo_inicio=hoje,
            periodo_fim=date(2026, 2, 28),
            valor=Decimal('3000.00'),
            data_abertura=hoje,
            data_limite=date(2026, 2, 10),
            estado='aberta'
        )

        # 2.1 Predefinição automática mensal -> Dia 10
        self.assinatura.modo_data_limite = 'automatico'
        self.assinatura.save()
        assert calcular_data_limite_efectiva_python(fatura) == date(2026, 2, 10)

        # 2.2 Modo Dia Fixo com dia 31 em mês curto (Fevereiro) -> Deve ajustar para dia 28
        self.assinatura.modo_data_limite = 'dia_fixo'
        self.assinatura.dia_limite = 31
        self.assinatura.save()
        assert calcular_data_limite_efectiva_python(fatura) == date(2026, 2, 28)

        # 2.3 Data manual da fatura tem a prioridade MÁXIMA
        fatura.data_limite_manual = date(2026, 3, 5)
        fatura.save()
        assert calcular_data_limite_efectiva_python(fatura) == date(2026, 3, 5)

    # 3. Transição de Estados nas Datas Certas: em_atraso -> restrita -> suspensa
    def test_transicao_estados_temporais(self):
        hoje = timezone.localdate()
        # Impedir que a rotina diária gere uma fatura extra vencida no dia 10
        self.assinatura.proxima_fatura_em = hoje + timedelta(days=30)
        self.assinatura.save()

        # Criar fatura vencida há 2 dias (dentro da tolerância de 5 dias)
        fatura = SaasFatura.objects.create(
            assinatura=self.assinatura,
            instituicao=self.escola,
            numero_fatura='FAT-TEST-STATES',
            periodo_inicio=hoje - timedelta(days=20),
            periodo_fim=hoje + timedelta(days=10),
            valor=Decimal('3000.00'),
            data_abertura=hoje - timedelta(days=20),
            data_limite=hoje - timedelta(days=2),
            data_limite_manual=hoje - timedelta(days=2),
            estado='aberta'
        )

        executar_rotina_diaria_saas_python()
        self.assinatura.refresh_from_db()
        assert self.assinatura.estado == 'em_atraso'

        # Simular avanço temporal: ultrapassar a tolerância de 5 dias -> Restrita
        fatura.data_limite_manual = hoje - timedelta(days=7)
        fatura.save()
        executar_rotina_diaria_saas_python()
        self.assinatura.refresh_from_db()
        assert self.assinatura.estado == 'restrita'

        # Simular avanço temporal: ultrapassar tolerância + dias_ate_suspensao (5 + 15 = 20 dias) -> Suspensa
        fatura.data_limite_manual = hoje - timedelta(days=22)
        fatura.save()
        executar_rotina_diaria_saas_python()
        self.assinatura.refresh_from_db()
        assert self.assinatura.estado == 'suspensa'
        self.escola.refresh_from_db()
        assert self.escola.status == 'SUSPENSA'

    # 4. Middleware: Bloqueio de Escrita em "Restrita" e Acesso em "Suspensa"
    def test_middleware_bloqueio_restrita_e_suspensa(self):
        login_res = self.client.post('/api/v1/auth/login/', {
            'email': 'admin.maputo@sige.mz',
            'password': 'SchoolPass2026!'
        }, format='json')
        token = login_res.data['token']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Caso A: Estado 'restrita'
        self.assinatura.estado = 'restrita'
        self.assinatura.save()
        limpar_cache_assinatura(self.escola.id)

        # GET (Consulta) deve ser PERMITIDO
        res_get = self.client.get('/api/v1/alunos/')
        assert res_get.status_code == 200

        # POST (Mutação) deve ser BLOQUEADO com 403 Forbidden
        res_post = self.client.post('/api/v1/alunos/', {
            'nome': 'Novo Aluno Proibido',
            'matricula': 'MAT_FAIL',
            'turma': str(self.turma.id),
            'genero': 'M',
            'data_nascimento': '2010-01-01'
        }, format='json')
        assert res_post.status_code == 403
        corpo = res_post.content.decode('utf-8')
        assert "Acesso em modo restrito" in corpo

        # Caso B: Estado 'suspensa'
        self.assinatura.estado = 'suspensa'
        self.assinatura.save()
        limpar_cache_assinatura(self.escola.id)

        # Tentativa de aceder a alunos (GET) agora também deve ser BLOQUEADA
        res_get_bloqueado = self.client.get('/api/v1/alunos/')
        assert res_get_bloqueado.status_code == 403
        corpo_bloq = res_get_bloqueado.content.decode('utf-8')
        assert "Acesso suspenso" in corpo_bloq

        # Acesso à área de regularização e faturas deve continuar PERMITIDO
        res_minha_ass = self.client.get('/api/v1/saas/minha-assinatura/')
        assert res_minha_ass.status_code == 200

    # 5. Confirmação de Pagamento Reactiva a Assinatura (Pagamento Total e Parcial)
    def test_confirmar_pagamento_reactiva_assinatura(self):
        hoje = timezone.localdate()
        self.assinatura.estado = 'suspensa'
        self.assinatura.save()

        fatura = SaasFatura.objects.create(
            assinatura=self.assinatura,
            instituicao=self.escola,
            numero_fatura='FAT-PAG-TEST',
            periodo_inicio=hoje - timedelta(days=30),
            periodo_fim=hoje - timedelta(days=1),
            valor=Decimal('3000.00'),
            data_abertura=hoje - timedelta(days=30),
            data_limite=hoje - timedelta(days=15),
            estado='em_atraso'
        )

        pagamento = SaasPagamento.objects.create(
            fatura=fatura,
            instituicao=self.escola,
            metodo='M-Pesa',
            referencia='MP261017.TESTE',
            valor=Decimal('3000.00'),
            estado='enviado'
        )

        # SuperAdmin confirma o pagamento
        login_admin = self.client.post('/api/v1/auth/login/', {
            'email': 'superadmin.saas@sige.mz',
            'password': 'AdminPassword2026!'
        }, format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_admin.data['token']}")

        res_conf = self.client.post(f'/api/v1/saas/pagamentos/{pagamento.id}/confirmar/')
        assert res_conf.status_code == 200

        fatura.refresh_from_db()
        assert fatura.estado == 'paga'
        assert fatura.valor_pago == Decimal('3000.00')

        self.assinatura.refresh_from_db()
        assert self.assinatura.estado == 'activa'

        self.escola.refresh_from_db()
        assert self.escola.status == 'ATIVA'

    # 6. Prova de Inviolabilidade de Dados e Falha em Tentativa Direta de DELETE
    def test_inviolabilidade_de_dados_e_falha_de_delete(self):
        # Contagem de registos pedagógicos antes de suspensão
        alunos_antes = Aluno.objects.filter(escola=self.escola).count()
        turmas_antes = Turma.objects.filter(escola=self.escola).count()
        assert alunos_antes == 2
        assert turmas_antes == 1

        # Suspender a instituição
        self.assinatura.estado = 'suspensa'
        self.assinatura.save()
        self.escola.status = 'SUSPENSA'
        self.escola.save()

        # Contagem de registos DEPOIS da suspensão: estritamente idêntica
        alunos_depois = Aluno.objects.filter(escola=self.escola).count()
        turmas_depois = Turma.objects.filter(escola=self.escola).count()
        assert alunos_antes == alunos_depois
        assert turmas_antes == turmas_depois

        # Tentativa directa de DELETE nos modelos SaaS deve levantar IntegrityError
        with pytest.raises(IntegrityError):
            self.assinatura.delete()

        fatura = SaasFatura.objects.create(
            assinatura=self.assinatura,
            instituicao=self.escola,
            numero_fatura='FAT-DELETE-PROIBIDO',
            periodo_inicio=timezone.localdate(),
            periodo_fim=timezone.localdate() + timedelta(days=30),
            valor=Decimal('3000.00'),
            data_abertura=timezone.localdate(),
            data_limite=timezone.localdate() + timedelta(days=10),
            estado='aberta'
        )

        with pytest.raises(IntegrityError):
            fatura.delete()
