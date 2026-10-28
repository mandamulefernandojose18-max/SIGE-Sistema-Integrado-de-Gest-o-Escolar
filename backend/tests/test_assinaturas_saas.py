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
            nome='Plano SaaS Básico Teste',
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

    def test_coordenadas_oficiais_pagamento_em_branco_e_configuracao(self):
        """Valida que coordenadas iniciam em branco sem dados fictícios e podem ser configuradas pelo superadmin"""
        # 1. Admin escola consulta coordenadas - devem vir em branco
        self.client.force_authenticate(user=self.admin_escola)
        res = self.client.get('/api/v1/saas/coordenadas/')
        assert res.status_code == 200
        assert res.data['success'] is True
        dados = res.data['data']
        # Sem dados fictícios: campos em branco
        assert dados['mpesa_numero'] == ''
        assert dados['emola_numero'] == ''
        assert dados['bim_conta'] == ''
        assert dados['bci_conta'] == ''

        # 2. Minha Assinatura também expõe coordenadas
        res_minha = self.client.get('/api/v1/saas/minha-assinatura/')
        assert res_minha.status_code == 200
        assert 'coordenadas' in res_minha.data['data']
        assert res_minha.data['data']['coordenadas']['mpesa_numero'] == ''

        # 3. Superadmin configura dados oficiais
        self.client.force_authenticate(user=self.superadmin)
        res_salvar = self.client.post('/api/v1/saas/coordenadas/', {
            'mpesa_numero': '841112233',
            'mpesa_titular': 'SIGE Oficial',
            'bim_conta': '555444333',
            'nuit_entidade': '999111222'
        }, format='json')
        assert res_salvar.status_code == 200
        assert res_salvar.data['success'] is True
        assert res_salvar.data['data']['mpesa_numero'] == '841112233'

        # 4. Consulta subsequente reflecte dados actualizados
        self.client.force_authenticate(user=self.admin_escola)
        res_depois = self.client.get('/api/v1/saas/coordenadas/')
        assert res_depois.data['data']['mpesa_numero'] == '841112233'
        assert res_depois.data['data']['bim_conta'] == '555444333'

    def test_suspensao_e_reactivacao_manual(self):
        """Valida suspensão e reactivação manual com justificação obrigatória e registo de auditoria"""
        self.client.force_authenticate(user=self.superadmin)

        # 1. Tentativa sem justificativa deve falhar
        res_fail = self.client.post(f'/api/v1/saas/instituicoes/{self.escola.id}/suspender-reactivar/', {
            'acao': 'suspender',
            'motivo': ''
        }, format='json')
        assert res_fail.status_code == 400

        # 2. Suspensão manual com sucesso
        res_susp = self.client.post(f'/api/v1/saas/instituicoes/{self.escola.id}/suspender-reactivar/', {
            'acao': 'suspender',
            'motivo': 'Bloqueio administrativo temporário'
        }, format='json')
        assert res_susp.status_code == 200
        self.escola.refresh_from_db()
        self.assinatura.refresh_from_db()
        assert self.escola.status == 'SUSPENSA'
        assert self.escola.bloqueada_manualmente is True
        assert self.assinatura.estado == 'suspensa'

        # 3. Reactivação manual com sucesso
        res_react = self.client.post(f'/api/v1/saas/instituicoes/{self.escola.id}/suspender-reactivar/', {
            'acao': 'reactivar',
            'motivo': 'Regularização administrativa manual confirmada'
        }, format='json')
        assert res_react.status_code == 200
        self.escola.refresh_from_db()
        self.assinatura.refresh_from_db()
        assert self.escola.status == 'ATIVA'
        assert self.escola.bloqueada_manualmente is False
        assert self.assinatura.estado == 'activa'

    def test_suspensao_e_reactivacao_automatica_por_regras(self):
        """Valida suspensão automática (apenas quando há corte) e reactivação automática (apenas quando regularizado)"""
        self.client.force_authenticate(user=self.superadmin)
        hoje = timezone.localdate()

        # 1. Sem faturas em corte: auto_suspender deve recusar suspensão automática
        res_sem_corte = self.client.post(f'/api/v1/saas/instituicoes/{self.escola.id}/suspender-reactivar/', {
            'acao': 'auto_suspender'
        }, format='json')
        assert res_sem_corte.status_code == 400
        assert 'não possui faturas que excedam o prazo de corte' in res_sem_corte.data['message']

        # 2. Criar fatura vencida há 25 dias (excede 5 dias de tolerância + 15 dias até suspensão = 20 dias)
        fatura = SaasFatura.objects.create(
            assinatura=self.assinatura,
            instituicao=self.escola,
            numero_fatura='FAT-AUTO-CORTE',
            periodo_inicio=hoje - timedelta(days=40),
            periodo_fim=hoje - timedelta(days=10),
            valor=Decimal('3000.00'),
            data_abertura=hoje - timedelta(days=40),
            data_limite=hoje - timedelta(days=25),
            data_limite_manual=hoje - timedelta(days=25),
            estado='aberta'
        )

        # 3. Com fatura em corte: auto_reactivar deve recusar e avisar das faturas pendentes
        res_recusa_react = self.client.post(f'/api/v1/saas/instituicoes/{self.escola.id}/suspender-reactivar/', {
            'acao': 'auto_reactivar'
        }, format='json')
        assert res_recusa_react.status_code == 400
        assert 'Não é possível reactivar automaticamente' in res_recusa_react.data['message']

        # 4. Executar auto_suspender agora deve aplicar Suspensão Automática com sucesso
        res_susp_auto = self.client.post(f'/api/v1/saas/instituicoes/{self.escola.id}/suspender-reactivar/', {
            'acao': 'auto_suspender'
        }, format='json')
        assert res_susp_auto.status_code == 200
        self.escola.refresh_from_db()
        self.assinatura.refresh_from_db()
        assert self.escola.status == 'SUSPENSA'
        assert self.escola.bloqueada_manualmente is False
        assert self.assinatura.estado == 'suspensa'

        # 5. Regularizar a fatura (paga)
        fatura.estado = 'paga'
        fatura.valor_pago = Decimal('3000.00')
        fatura.save()

        # 6. Agora auto_reactivar deve ter sucesso total!
        res_react_auto = self.client.post(f'/api/v1/saas/instituicoes/{self.escola.id}/suspender-reactivar/', {
            'acao': 'auto_reactivar'
        }, format='json')
        assert res_react_auto.status_code == 200
        self.escola.refresh_from_db()
        self.assinatura.refresh_from_db()
        assert self.escola.status == 'ATIVA'
        assert self.escola.bloqueada_manualmente is False
        assert self.assinatura.estado == 'activa'

    def test_repor_modo_automatico_e_ciclo_diario(self):
        """Valida que repor modo automático limpa bloqueio manual e ciclo diário reactiva escolas regularizadas"""
        self.client.force_authenticate(user=self.superadmin)

        # 1. Instituição bloqueada manualmente sem dívida
        self.escola.status = 'SUSPENSA'
        self.escola.bloqueada_manualmente = True
        self.escola.save()
        self.assinatura.estado = 'suspensa'
        self.assinatura.save()

        # 2. Superadmin clica em 'Repor Modo Automático'
        res_repor = self.client.post(f'/api/v1/saas/instituicoes/{self.escola.id}/suspender-reactivar/', {
            'acao': 'auto_avaliar'
        }, format='json')
        assert res_repor.status_code == 200
        self.escola.refresh_from_db()
        self.assinatura.refresh_from_db()
        assert self.escola.status == 'ATIVA'
        assert self.escola.bloqueada_manualmente is False
        assert self.assinatura.estado in ['activa', 'fatura_pendente']

        # 3. Serializer expõe modo de controlo correcto
        res_ficha = self.client.get(f'/api/v1/saas/assinaturas/{self.assinatura.id}/')
        assert res_ficha.data['data']['assinatura']['modo_controlo'] == 'automatico'


    def test_periodicidade_editavel_individualmente(self):
        """Valida que cada instituição tem a sua própria periodicidade e que esta é editável"""
        self.client.force_authenticate(user=self.superadmin)

        # Alterar para trimestral
        res = self.client.patch(f'/api/v1/saas/assinaturas/{self.assinatura.id}/configurar/', {
            'periodicidade': 'trimestral'
        }, format='json')
        assert res.status_code == 200
        self.assinatura.refresh_from_db()
        assert self.assinatura.periodicidade == 'trimestral'

        # Instituição pode também alterar a sua periodicidade directamente
        self.client.force_authenticate(user=self.admin_escola)
        res_escola = self.client.post('/api/v1/saas/minha-assinatura/configurar/', {
            'periodicidade': 'anual'
        }, format='json')
        assert res_escola.status_code == 200
        self.assinatura.refresh_from_db()
        assert self.assinatura.periodicidade == 'anual'

    def test_pagamento_adiantado_calcula_tempo_e_estende_prazo(self):
        """Valida que o valor pago a mais calcula automaticamente o tempo correspondente e estende o prazo"""
        self.client.force_authenticate(user=self.superadmin)

        # Plano custa 3000 MZN/mês. Periodicidade mensal.
        self.assinatura.periodicidade = 'mensal'
        self.assinatura.proxima_fatura_em = date(2026, 11, 16)
        self.assinatura.save()

        # Fatura de 3000 MZN
        fat = SaasFatura.objects.create(
            assinatura=self.assinatura,
            instituicao=self.escola,
            numero_fatura='FAT-TEST-ADV-01',
            periodo_inicio=date(2026, 10, 16),
            periodo_fim=date(2026, 11, 15),
            valor=Decimal('3000.00'),
            data_abertura=date(2026, 10, 1),
            data_limite=date(2026, 10, 10),
            estado='aberta'
        )

        # Pagamento de 9000 MZN (3000 da fatura + 6000 adiantados = 2 meses adicionais)
        pag = SaasPagamento.objects.create(
            fatura=fat,
            instituicao=self.escola,
            metodo='M-Pesa',
            referencia='ADVANCE9000',
            valor=Decimal('9000.00'),
            estado='enviado'
        )

        res = self.client.post(f'/api/v1/saas/pagamentos/{pag.id}/confirmar/')
        assert res.status_code == 200
        assert res.data['data']['sucesso'] is True

        fat.refresh_from_db()
        self.assinatura.refresh_from_db()

        assert fat.estado == 'paga'
        # 16/11/2026 + 2 meses = 16/01/2027
        assert self.assinatura.proxima_fatura_em == date(2027, 1, 16)
        assert res.data['data']['info_adiantado']['meses'] == 2
        assert res.data['data']['info_adiantado']['dias'] == 0

    def test_calculo_adiantamento_endpoint(self):
        """Valida a rota de pré-visualização de adiantamento"""
        self.client.force_authenticate(user=self.admin_escola)
        fat = SaasFatura.objects.create(
            assinatura=self.assinatura,
            instituicao=self.escola,
            numero_fatura='FAT-TEST-CALC-01',
            periodo_inicio=date(2026, 10, 1),
            periodo_fim=date(2026, 10, 31),
            valor=Decimal('3000.00'),
            data_abertura=date(2026, 10, 1),
            data_limite=date(2026, 10, 10),
            estado='aberta'
        )
        res = self.client.get(f'/api/v1/saas/calcular-adiantamento/?fatura_id={fat.id}&valor=6000')
        assert res.status_code == 200
        assert res.data['success'] is True
        assert res.data['data']['valor_excedente'] == 3000.0
        assert res.data['data']['meses_adicionais'] == 1
