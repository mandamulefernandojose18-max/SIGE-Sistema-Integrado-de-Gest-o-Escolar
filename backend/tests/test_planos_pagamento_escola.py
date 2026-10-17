import pytest
from rest_framework.test import APIClient
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma
from apps.alunos.models import Aluno
from apps.pagamentos.models import PlanoPagamentoEscola, Pagamento


@pytest.mark.django_db
class TestPlanosPagamentoMultiTenant:
    def setup_method(self):
        self.client = APIClient()
        self.saas_plano = Plano.objects.create(nome='PLANO_SAAS_SUPERADMIN', preco=5000, duracao_dias=30)

        # Super Admin
        self.superadmin = Usuario.objects.create_user(
            email='super@sige.co.mz', password='SuperPassword123!', role='SUPERADMIN'
        )

        # Escola A (Tenant A)
        self.escola_a = Escola.objects.create(
            nome='Escola Secundária de Massinga',
            nif_cnpj='NIF_MASSINGA',
            email='massinga@sige.edu.mz',
            status='ATIVA',
            plano=self.saas_plano
        )
        self.admin_a = Usuario.objects.create_user(
            email='admin.massinga@sige.edu.mz',
            password='PassMassinga123!',
            role='ADMIN_ESCOLA',
            escola=self.escola_a
        )
        self.turma_a = Turma.objects.create(escola=self.escola_a, nome='10ª A Massinga', grau_ano='10ª Classe')
        self.aluno_a = Aluno.objects.create(
            escola=self.escola_a, turma=self.turma_a, matricula='MAT_MAS_001', nome='Carlos Alberto',
            data_nascimento='2009-01-01', genero='M'
        )
        self.user_aluno_a = Usuario.objects.create_user(
            email='carlos.aluno@sige.edu.mz', password='PassAluno123!', role='ALUNO',
            escola=self.escola_a, aluno_id=self.aluno_a.id
        )

        # Escola B (Tenant B)
        self.escola_b = Escola.objects.create(
            nome='Escola Comunitária de Maputo',
            nif_cnpj='NIF_MAPUTO',
            email='maputo@sige.edu.mz',
            status='ATIVA',
            plano=self.saas_plano
        )
        self.admin_b = Usuario.objects.create_user(
            email='admin.maputo@sige.edu.mz',
            password='PassMaputo123!',
            role='ADMIN_ESCOLA',
            escola=self.escola_b
        )
        self.turma_b = Turma.objects.create(escola=self.escola_b, nome='10ª B Maputo', grau_ano='10ª Classe')
        self.aluno_b = Aluno.objects.create(
            escola=self.escola_b, turma=self.turma_b, matricula='MAT_MAP_001', nome='Beatriz Silva',
            data_nascimento='2009-02-02', genero='F'
        )

    def login(self, email, password):
        res = self.client.post('/api/v1/auth/login/', {'email': email, 'password': password}, format='json')
        assert res.status_code == 200, f"Falha no login de {email}: {res.data}"
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['token']}")

    def test_planos_saas_bloqueados_para_usuarios_comuns_da_escola(self):
        """
        O plano do Super Admin aplica-se unicamente às instituições (B2B).
        Usuários comuns da escola (Alunos, Professores) não têm acesso aos planos SaaS.
        """
        # Aluno tenta aceder à lista de planos SaaS do Super Admin -> Bloqueado (403)
        self.login('carlos.aluno@sige.edu.mz', 'PassAluno123!')
        res_saas_planos = self.client.get('/api/v1/saas-admin/planos/')
        assert res_saas_planos.status_code == 403

        # Aluno tenta aceder a Minha Assinatura SaaS -> Bloqueado (403)
        res_minha_ass = self.client.get('/api/v1/saas/minha-assinatura/')
        assert res_minha_ass.status_code == 403
        assert 'não reflectem para os usuários escolares' in res_minha_ass.data['message']

    def test_escola_cria_seu_proprio_plano_de_pagamentos(self):
        """
        Cada instituição cria o seu plano de pagamentos a aplicar aos seus usuários no sistema.
        """
        self.login('admin.massinga@sige.edu.mz', 'PassMassinga123!')

        payload = {
            'nome': 'Propina Regular 10ª Classe - Massinga',
            'descricao': 'Propina mensal padrão para o ensino secundário geral',
            'valor': 1800.00,
            'periodicidade': 'MENSAL',
            'dia_vencimento_padrao': 10
        }
        res = self.client.post('/api/v1/pagamentos/planos-escola/', payload, format='json')
        assert res.status_code == 201
        dados = res.data.get('data') or res.data
        assert dados['nome'] == 'Propina Regular 10ª Classe - Massinga'
        assert float(dados['valor']) == 1800.00

        # Verifica persistência vinculada à Escola A
        plano_criado = PlanoPagamentoEscola.objects.get(id=dados['id'])
        assert plano_criado.escola_id == self.escola_a.id

    def test_isolamento_total_entre_instituicoes_planos_escola(self):
        """
        Tudo o que uma instituição faz no seu sistema não pode comprometer ou refletir noutra.
        A Escola B nunca vê nem altera os planos de pagamento da Escola A.
        """
        # Escola A cria plano
        plano_a = PlanoPagamentoEscola.objects.create(
            escola=self.escola_a,
            nome='Propina Exclusiva Escola A',
            valor=2200.00,
            periodicidade='MENSAL'
        )

        # Escola B cria plano
        plano_b = PlanoPagamentoEscola.objects.create(
            escola=self.escola_b,
            nome='Propina Exclusiva Escola B',
            valor=3000.00,
            periodicidade='MENSAL'
        )

        # 1. Admin da Escola A lista planos escolares: DEVE ver apenas plano_a
        self.login('admin.massinga@sige.edu.mz', 'PassMassinga123!')
        res_a = self.client.get('/api/v1/pagamentos/planos-escola/')
        assert res_a.status_code == 200
        lista_a = res_a.data.get('data') if isinstance(res_a.data, dict) and 'data' in res_a.data else res_a.data
        ids_a = [p['id'] for p in lista_a]
        assert str(plano_a.id) in ids_a
        assert str(plano_b.id) not in ids_a

        # Admin da Escola A tenta aceder diretamente ao plano da Escola B -> 404
        res_detalhe_b = self.client.get(f'/api/v1/pagamentos/planos-escola/{plano_b.id}/')
        assert res_detalhe_b.status_code == 404

        # Admin da Escola A tenta apagar plano da Escola B -> 404
        res_del_b = self.client.delete(f'/api/v1/pagamentos/planos-escola/{plano_b.id}/')
        assert res_del_b.status_code == 404

        # 2. Admin da Escola B lista planos escolares: DEVE ver apenas plano_b
        self.login('admin.maputo@sige.edu.mz', 'PassMaputo123!')
        res_b = self.client.get('/api/v1/pagamentos/planos-escola/')
        assert res_b.status_code == 200
        lista_b = res_b.data.get('data') if isinstance(res_b.data, dict) and 'data' in res_b.data else res_b.data
        ids_b = [p['id'] for p in lista_b]
        assert str(plano_b.id) in ids_b
        assert str(plano_a.id) not in ids_b

    def test_impedir_vinculacao_cruzada_pagamento_com_plano_de_outra_escola(self):
        """
        Garante que um pagamento de aluno da Escola A não pode ser associado a plano da Escola B.
        """
        plano_b = PlanoPagamentoEscola.objects.create(
            escola=self.escola_b,
            nome='Propina Escola B',
            valor=2500.00
        )

        self.login('admin.massinga@sige.edu.mz', 'PassMassinga123!')

        # Tentativa de lançar cobrança para Aluno A com plano da Escola B
        payload = {
            'aluno_id': str(self.aluno_a.id),
            'plano_pagamento_id': str(plano_b.id),
            'descricao': 'Mensalidade',
            'mes_referencia': '2026-04',
            'valor': 2500.00,
            'data_vencimento': '2026-04-10'
        }
        res = self.client.post('/api/v1/pagamentos/', payload, format='json')
        # DEVE ser rejeitado por violar a integridade multi-tenant
        assert res.status_code in [400, 404]

    def test_aluno_apenas_visualiza_cobrancas_da_sua_propria_escola(self):
        """
        O aluno visualiza apenas as cobranças aplicadas pela sua escola e sob o plano da sua escola.
        """
        plano_a = PlanoPagamentoEscola.objects.create(
            escola=self.escola_a,
            nome='Propina Mensal Regular',
            valor=1500.00
        )

        pag_a = Pagamento.objects.create(
            escola=self.escola_a,
            aluno=self.aluno_a,
            plano_pagamento=plano_a,
            descricao='Mensalidade de Março',
            mes_referencia='2026-03',
            valor=1500.00,
            data_vencimento='2026-03-10'
        )

        pag_b = Pagamento.objects.create(
            escola=self.escola_b,
            aluno=self.aluno_b,
            descricao='Mensalidade de Março Escola B',
            mes_referencia='2026-03',
            valor=3500.00,
            data_vencimento='2026-03-10'
        )

        self.login('carlos.aluno@sige.edu.mz', 'PassAluno123!')
        res = self.client.get('/api/v1/pagamentos/')
        assert res.status_code == 200

        # Aluno A vê apenas cobranças da Escola A
        pags_retornados = res.data['data'] if 'data' in res.data else res.data
        ids_pags = [p['id'] for p in pags_retornados]
        assert str(pag_a.id) in ids_pags
        assert str(pag_b.id) not in ids_pags
