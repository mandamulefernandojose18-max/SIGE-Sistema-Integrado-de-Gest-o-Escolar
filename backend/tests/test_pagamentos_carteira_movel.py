import pytest
from rest_framework.test import APIClient
from django.utils import timezone
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma
from apps.alunos.models import Aluno
from apps.pagamentos.models import Pagamento, PlanoPagamentoEscola


@pytest.mark.django_db
class TestPagamentoSaldoCarteiraMovel:
    def setup_method(self):
        self.client = APIClient()
        self.saas_plano = Plano.objects.create(nome='SAAS_PLANO_TESTE', preco=5000, duracao_dias=30)

        # Escola A
        self.escola_a = Escola.objects.create(
            nome='Escola Secundária de Massinga',
            nif_cnpj='NIF_MAS_001',
            email='massinga@sige.edu.mz',
            status='ATIVA',
            plano=self.saas_plano
        )
        self.admin_a = Usuario.objects.create_user(
            email='admin.mas@sige.edu.mz',
            password='Password123!',
            role='ADMIN_ESCOLA',
            escola=self.escola_a
        )
        self.turma_a = Turma.objects.create(escola=self.escola_a, nome='10ª A', grau_ano='10ª')
        self.aluno_a = Aluno.objects.create(
            escola=self.escola_a,
            turma=self.turma_a,
            matricula='MAT_MAS_101',
            nome='Fernando Mandamule Aluno',
            data_nascimento='2009-05-15',
            genero='M'
        )
        self.user_aluno_a = Usuario.objects.create_user(
            email='aluno.mas@sige.edu.mz',
            password='Password123!',
            role='ALUNO',
            escola=self.escola_a,
            aluno_id=self.aluno_a.id
        )

        # Cobrança de propina para Aluno A
        self.pagamento_a = Pagamento.objects.create(
            escola=self.escola_a,
            aluno=self.aluno_a,
            descricao='Propina de Março 2026',
            mes_referencia='2026-03',
            valor=2500,
            status='PENDENTE',
            data_vencimento=timezone.now() + timezone.timedelta(days=10)
        )

        # Escola B
        self.escola_b = Escola.objects.create(
            nome='Escola Comunitária de Maputo',
            nif_cnpj='NIF_MAP_002',
            email='maputo@sige.edu.mz',
            status='ATIVA',
            plano=self.saas_plano
        )
        self.aluno_b = Aluno.objects.create(
            escola=self.escola_b,
            matricula='MAT_MAP_202',
            nome='Aluno Maputo',
            data_nascimento='2009-08-20',
            genero='F'
        )
        self.user_aluno_b = Usuario.objects.create_user(
            email='aluno.map@sige.edu.mz',
            password='Password123!',
            role='ALUNO',
            escola=self.escola_b,
            aluno_id=self.aluno_b.id
        )

    def test_liquidar_saldo_com_mpesa_por_admin(self):
        """Administrador ou secretaria liquida saldo com M-Pesa."""
        self.client.force_authenticate(user=self.admin_a)
        url = f'/api/v1/pagamentos/{self.pagamento_a.id}/liquidar/'
        payload = {
            'metodo_pagamento': 'MPESA',
            'valor_pago': 2500,
            'telefone': '841234567',
            'referencia': 'MP261017.0001'
        }
        res = self.client.post(url, payload, format='json')
        assert res.status_code == 200
        assert res.data['success'] is True
        assert res.data['metodo_pagamento'] == 'MPESA'
        assert res.data['recibo_numero'].startswith('REC-')

        self.pagamento_a.refresh_from_db()
        assert self.pagamento_a.status == 'PAGO'
        assert self.pagamento_a.metodo_pagamento == 'MPESA'
        assert self.pagamento_a.valor_pago == 2500

    def test_liquidar_saldo_com_emola_por_admin(self):
        """Administrador liquida saldo com e-Mola."""
        self.client.force_authenticate(user=self.admin_a)
        url = f'/api/v1/pagamentos/{self.pagamento_a.id}/liquidar/'
        payload = {
            'metodo_pagamento': 'EMOLA',
            'valor_pago': 2500,
            'telefone': '861234567',
            'referencia': 'EM261017.0002'
        }
        res = self.client.post(url, payload, format='json')
        assert res.status_code == 200
        assert res.data['success'] is True
        assert res.data['metodo_pagamento'] == 'EMOLA'

    def test_aluno_paga_proprio_saldo_carteira_movel(self):
        """Aluno autenticado liquida com sucesso o seu próprio saldo com carteira móvel."""
        self.client.force_authenticate(user=self.user_aluno_a)
        url = '/api/v1/alunos/me/pagamentos/'
        payload = {
            'pagamento_id': str(self.pagamento_a.id),
            'metodo_pagamento': 'MPESA',
            'telefone': '849988776',
            'referencia': 'MP_ALUNO_7788'
        }
        res = self.client.post(url, payload, format='json')
        assert res.status_code == 200
        assert res.data['success'] is True
        assert res.data['metodo_pagamento'] == 'MPESA'
        assert res.data['recibo_numero'].startswith('REC-')

        self.pagamento_a.refresh_from_db()
        assert self.pagamento_a.status == 'PAGO'

    def test_aluno_nao_pode_liquidar_propina_de_outro_aluno(self):
        """Aluno B não pode liquidar propina do Aluno A (isolamento estrito)."""
        self.client.force_authenticate(user=self.user_aluno_b)
        url = '/api/v1/alunos/me/pagamentos/'
        payload = {
            'pagamento_id': str(self.pagamento_a.id),
            'metodo_pagamento': 'MPESA',
            'telefone': '841112233'
        }
        res = self.client.post(url, payload, format='json')
        assert res.status_code == 404
        self.pagamento_a.refresh_from_db()
        assert self.pagamento_a.status == 'PENDENTE'
