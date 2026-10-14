import pytest
from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano, AssinaturaEscola
from apps.turmas.models import Turma
from apps.alunos.models import Aluno
from apps.certificados.models import Certificado

@pytest.mark.django_db
class TestMultiTenancy:
    def setup_method(self):
        self.client = APIClient()
        self.plano = Plano.objects.create(nome='PLANO_TENANT_TEST', preco=2000, duracao_dias=30)
        
        # Tenant A (Escola A - ATIVA)
        self.escola_a = Escola.objects.create(nome='Escola Alfa', nif_cnpj='NIF_A', email='alfa@sige.mz', status='ATIVA', plano=self.plano)
        self.user_a = Usuario.objects.create_user(email='admin.a@sige.mz', password='PassA123!', role='ADMIN_ESCOLA', escola=self.escola_a)
        self.turma_a = Turma.objects.create(escola=self.escola_a, nome='10ª A Alfa', grau_ano='10ª Classe')
        self.aluno_a = Aluno.objects.create(escola=self.escola_a, turma=self.turma_a, matricula='MAT_A_001', nome='Aluno de Alfa', data_nascimento='2009-01-01', genero='M')

        # Tenant B (Escola B - ATIVA)
        self.escola_b = Escola.objects.create(nome='Escola Beta', nif_cnpj='NIF_B', email='beta@sige.mz', status='ATIVA', plano=self.plano)
        self.user_b = Usuario.objects.create_user(email='admin.b@sige.mz', password='PassB123!', role='ADMIN_ESCOLA', escola=self.escola_b)
        self.turma_b = Turma.objects.create(escola=self.escola_b, nome='10ª B Beta', grau_ano='10ª Classe')
        self.aluno_b = Aluno.objects.create(escola=self.escola_b, turma=self.turma_b, matricula='MAT_B_001', nome='Aluno de Beta', data_nascimento='2009-02-02', genero='F')

        # Tenant C (Escola C - EXPIRADA)
        self.escola_expirada = Escola.objects.create(nome='Escola Expirada', nif_cnpj='NIF_EXP', email='exp@sige.mz', status='EXPIRADA', plano=self.plano)
        self.user_expirado = Usuario.objects.create_user(email='admin.exp@sige.mz', password='PassExp123!', role='ADMIN_ESCOLA', escola=self.escola_expirada)

    def test_isolamento_leitura_entre_tenants(self):
        # User A lista alunos -> DEVE ver apenas Aluno A
        login_res = self.client.post('/api/v1/auth/login/', {'email': 'admin.a@sige.mz', 'password': 'PassA123!'}, format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res.data['token']}")

        res = self.client.get('/api/v1/alunos/')
        assert res.status_code == 200
        alunos_ids = [a['id'] for a in res.data['data']]
        assert str(self.aluno_a.id) in alunos_ids
        assert str(self.aluno_b.id) not in alunos_ids

    def test_bloqueio_tentativa_acesso_direto_outro_tenant(self):
        # User A tenta acessar detalhe do Aluno B -> DEVE ser 404 (não encontrado no seu escopo)
        login_res = self.client.post('/api/v1/auth/login/', {'email': 'admin.a@sige.mz', 'password': 'PassA123!'}, format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res.data['token']}")

        res_get = self.client.get(f'/api/v1/alunos/{self.aluno_b.id}/')
        assert res_get.status_code == 404

        res_delete = self.client.delete(f'/api/v1/alunos/{self.aluno_b.id}/')
        assert res_delete.status_code == 404

    def test_bloqueio_automatico_tenant_expirado(self):
        # User de Escola Expirada tem login bloqueado com mensagem explícita
        login_res = self.client.post('/api/v1/auth/login/', {'email': 'admin.exp@sige.mz', 'password': 'PassExp123!'}, format='json')
        assert login_res.status_code == 401
        assert "Acesso bloqueado" in str(login_res.data)
        assert "EXPIRADA" in str(login_res.data)

    def test_rota_publica_certificados_funciona_mesmo_escola_expirada(self):
        # Certificados públicos não sofrem bloqueio 402
        turma_exp = Turma.objects.create(escola=self.escola_expirada, nome='10ª Exp', grau_ano='10ª Classe')
        aluno_exp = Aluno.objects.create(escola=self.escola_expirada, turma=turma_exp, matricula='MAT_EXP_001', nome='Aluno Exp', data_nascimento='2009-03-03', genero='M')
        cert = Certificado.objects.create(
            escola=self.escola_expirada,
            aluno=aluno_exp,
            tipo='CONCLUSAO',
            codigo_autenticidade='AUTENTICIDADE_123',
            qrcode_data='https://sige.co.mz/verificar'
        )

        res = self.client.get('/api/v1/certificados/verificar/AUTENTICIDADE_123/')
        assert res.status_code == 200
        assert res.data['autentico'] is True
        assert res.data['data']['codigo'] == 'AUTENTICIDADE_123'

    def test_publicacoes_feitas_numa_escola_nao_reflectem_noutras_escolas(self):
        from apps.material_escolar.models import MaterialEscolar

        # Criar publicação na Escola A
        mat_a = MaterialEscolar.objects.create(
            escola=self.escola_a,
            classe='10ª Classe',
            titulo='Manual de Matemática - Escola Alfa',
            tipo='MANUAL',
            publicado_por='Admin Alfa'
        )

        # Criar publicação na Escola B
        mat_b = MaterialEscolar.objects.create(
            escola=self.escola_b,
            classe='10ª Classe',
            titulo='Ficha de Física - Escola Beta',
            tipo='FICHA',
            publicado_por='Admin Beta'
        )

        # 1. Utilizador da Escola A consulta materiais: vê apenas os da Escola A
        login_res_a = self.client.post('/api/v1/auth/login/', {'email': 'admin.a@sige.mz', 'password': 'PassA123!'}, format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res_a.data['token']}")

        res_a = self.client.get('/api/v1/material-escolar/')
        assert res_a.status_code == 200
        titulos_a = [m['titulo'] for m in res_a.data['data']]
        assert 'Manual de Matemática - Escola Alfa' in titulos_a
        assert 'Ficha de Física - Escola Beta' not in titulos_a

        # Contagem de classes na Escola A: apenas 1 material na 10ª Classe
        res_classes_a = self.client.get('/api/v1/material-escolar/classes/')
        assert res_classes_a.status_code == 200
        c10_a = next(item for item in res_classes_a.data['data'] if item['classe'] == '10ª Classe')
        assert c10_a['totalMateriais'] == 1

        # 2. Utilizador da Escola B consulta materiais: vê apenas os da Escola B
        login_res_b = self.client.post('/api/v1/auth/login/', {'email': 'admin.b@sige.mz', 'password': 'PassB123!'}, format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res_b.data['token']}")

        res_b = self.client.get('/api/v1/material-escolar/')
        assert res_b.status_code == 200
        titulos_b = [m['titulo'] for m in res_b.data['data']]
        assert 'Ficha de Física - Escola Beta' in titulos_b
        assert 'Manual de Matemática - Escola Alfa' not in titulos_b

        # 3. SuperAdmin inspecionando Escola A vê apenas Escola A
        u_super = Usuario.objects.create_superuser(email='super@sige.mz', password='PassSuper123!')
        login_res_super = self.client.post('/api/v1/auth/login/', {'email': 'super@sige.mz', 'password': 'PassSuper123!'}, format='json')
        
        # Com header X-Tenant-ID da Escola A
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res_super.data['token']}", HTTP_X_TENANT_ID=str(self.escola_a.id))
        res_super_a = self.client.get('/api/v1/material-escolar/')
        titulos_super_a = [m['titulo'] for m in res_super_a.data['data']]
        assert 'Manual de Matemática - Escola Alfa' in titulos_super_a
        assert 'Ficha de Física - Escola Beta' not in titulos_super_a

        # Com header X-Tenant-ID da Escola B
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res_super.data['token']}", HTTP_X_TENANT_ID=str(self.escola_b.id))
        res_super_b = self.client.get('/api/v1/material-escolar/')
        titulos_super_b = [m['titulo'] for m in res_super_b.data['data']]
        assert 'Ficha de Física - Escola Beta' in titulos_super_b
        assert 'Manual de Matemática - Escola Alfa' not in titulos_super_b

        # SuperAdmin sem tenant selecionado não recebe vazamento de nenhuma escola
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res_super.data['token']}")
        res_super_none = self.client.get('/api/v1/material-escolar/')
        assert len(res_super_none.data['data']) == 0

    def test_isolamento_absoluto_cadastros_notas_documentos_entre_escolas(self):
        from apps.professores.models import Professor
        from apps.disciplinas.models import Disciplina
        from apps.notas.models import Nota
        from apps.pagamentos.models import Pagamento

        prof_a = Professor.objects.create(escola=self.escola_a, nome='Professor Alfa', email='prof.alfa@sige.mz')
        prof_b = Professor.objects.create(escola=self.escola_b, nome='Professor Beta', email='prof.beta@sige.mz')

        disc_a = Disciplina.objects.create(escola=self.escola_a, nome='Matemática Alfa', codigo='MAT_A')
        disc_b = Disciplina.objects.create(escola=self.escola_b, nome='Matemática Beta', codigo='MAT_B')

        nota_a = Nota.objects.create(
            escola=self.escola_a, aluno=self.aluno_a, turma=self.turma_a,
            disciplina=disc_a, periodo='1_TRIMESTRE', media_final=15.0, resultado='Aprovado'
        )
        nota_b = Nota.objects.create(
            escola=self.escola_b, aluno=self.aluno_b, turma=self.turma_b,
            disciplina=disc_b, periodo='1_TRIMESTRE', media_final=12.0, resultado='Aprovado'
        )

        pag_a = Pagamento.objects.create(
            escola=self.escola_a, aluno=self.aluno_a, descricao='Propina Março',
            mes_referencia='2026-03', valor=1500, valor_pago=1500,
            status='PAGO', data_vencimento=timezone.now()
        )
        pag_b = Pagamento.objects.create(
            escola=self.escola_b, aluno=self.aluno_b, descricao='Propina Março',
            mes_referencia='2026-03', valor=2500, valor_pago=2500,
            status='PAGO', data_vencimento=timezone.now()
        )

        # Autenticar como Admin da Escola A
        login_a = self.client.post('/api/v1/auth/login/', {'email': 'admin.a@sige.mz', 'password': 'PassA123!'}, format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_a.data['token']}")

        # 1. Professores: vê apenas prof_a
        res_profs = self.client.get('/api/v1/professores/')
        assert res_profs.status_code == 200
        nomes_profs = [p['nome'] for p in res_profs.data['data']]
        assert 'Professor Alfa' in nomes_profs
        assert 'Professor Beta' not in nomes_profs

        # 2. Turmas: vê apenas turma_a
        res_turmas = self.client.get('/api/v1/turmas/')
        assert res_turmas.status_code == 200
        nomes_turmas = [t['nome'] for t in res_turmas.data['data']]
        assert '10ª A Alfa' in nomes_turmas
        assert '10ª B Beta' not in nomes_turmas

        # 3. Disciplinas: vê apenas disc_a
        res_discs = self.client.get('/api/v1/disciplinas/')
        assert res_discs.status_code == 200
        nomes_discs = [d['nome'] for d in res_discs.data['data']]
        assert 'Matemática Alfa' in nomes_discs
        assert 'Matemática Beta' not in nomes_discs

        # 4. Notas: vê apenas notas da Escola A
        res_notas = self.client.get('/api/v1/notas/')
        assert res_notas.status_code == 200
        raw_notas = res_notas.data.get('results', res_notas.data.get('data', res_notas.data)) if isinstance(res_notas.data, dict) else res_notas.data
        notas_ids = [str(n['id']) for n in raw_notas]
        assert str(nota_a.id) in notas_ids
        assert str(nota_b.id) not in notas_ids

        # 5. Pagamentos: vê apenas pagamentos da Escola A
        res_pags = self.client.get('/api/v1/pagamentos/')
        assert res_pags.status_code == 200
        pags_ids = [str(p['id']) for p in res_pags.data['data']]
        assert str(pag_a.id) in pags_ids
        assert str(pag_b.id) not in pags_ids

        # 6. Tentativa de acessar Pauta da Escola B sendo utilizador da Escola A -> 403 Forbidden
        res_pauta_cross = self.client.get(f'/api/v1/pautas/turma/{self.turma_b.id}/completa/')
        assert res_pauta_cross.status_code == 403

        # 7. Tentativa de obter Recibo de Pagamento da Escola B sendo utilizador da Escola A -> 403 Forbidden
        res_recibo_cross = self.client.get(f'/api/v1/impressao/recibo/{pag_b.id}/')
        assert res_recibo_cross.status_code == 403

    def test_superadmin_acesso_irrestrito_escola_inactiva_suspensa_expirada(self):
        # 1. SuperAdmin com escola EXPIRADA vinculada faz login normalmente
        u_super = Usuario.objects.create_superuser(
            email='super.irrestrito@sige.mz',
            password='SuperPass123!',
            escola=self.escola_expirada
        )
        login_super = self.client.post('/api/v1/auth/login/', {'email': 'super.irrestrito@sige.mz', 'password': 'SuperPass123!'}, format='json')
        assert login_super.status_code == 200
        assert login_super.data['user']['role'] == 'SUPERADMIN'
        token = login_super.data['token']

        # 2. SuperAdmin acede à API inspecionando escola expirada -> 200 OK
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}", HTTP_X_TENANT_ID=str(self.escola_expirada.id))
        res = self.client.get('/api/v1/alunos/')
        assert res.status_code == 200

        # 3. Escola Suspensa: SuperAdmin acede livremente
        escola_susp = Escola.objects.create(nome='Escola Suspensa Super', nif_cnpj='NIF_SUSP_S', email='susp_s@sige.mz', status='SUSPENSA', plano=self.plano)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}", HTTP_X_TENANT_ID=str(escola_susp.id))
        res_susp = self.client.get('/api/v1/alunos/')
        assert res_susp.status_code == 200

        # 4. Escola Bloqueada Manualmente: SuperAdmin acede livremente
        escola_bloq = Escola.objects.create(nome='Escola Bloqueada Super', nif_cnpj='NIF_BLOQ_S', email='bloq_s@sige.mz', status='ATIVA', bloqueada_manualmente=True, plano=self.plano)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}", HTTP_X_TENANT_ID=str(escola_bloq.id))
        res_bloq = self.client.get('/api/v1/alunos/')
        assert res_bloq.status_code == 200

    def test_utilizador_comum_bloqueado_quando_escola_suspensa_ou_bloqueada_manualmente(self):
        # 1. Escola Suspensa: Utilizador comum tem login bloqueado
        escola_susp = Escola.objects.create(nome='Escola Suspensa Teste', nif_cnpj='NIF_SUSP_2', email='susp2@sige.mz', status='SUSPENSA', plano=self.plano)
        user_susp = Usuario.objects.create_user(email='admin.susp@sige.mz', password='PassSusp123!', role='ADMIN_ESCOLA', escola=escola_susp)
        login_susp = self.client.post('/api/v1/auth/login/', {'email': 'admin.susp@sige.mz', 'password': 'PassSusp123!'}, format='json')
        assert login_susp.status_code == 401
        assert "Acesso bloqueado" in str(login_susp.data)
        assert "SUSPENSA" in str(login_susp.data)

        # 2. Escola Bloqueada Manualmente: Utilizador comum tem login bloqueado
        escola_bloq = Escola.objects.create(nome='Escola Bloqueada Teste', nif_cnpj='NIF_BLOQ_2', email='bloq2@sige.mz', status='ATIVA', bloqueada_manualmente=True, plano=self.plano)
        user_bloq = Usuario.objects.create_user(email='admin.bloq@sige.mz', password='PassBloq123!', role='ADMIN_ESCOLA', escola=escola_bloq)
        login_bloq = self.client.post('/api/v1/auth/login/', {'email': 'admin.bloq@sige.mz', 'password': 'PassBloq123!'}, format='json')
        assert login_bloq.status_code == 401
        assert "Acesso bloqueado" in str(login_bloq.data)
        assert "BLOQUEADA MANUALMENTE" in str(login_bloq.data)

        # 3. Escola PENDENTE: Utilizador comum tem login bloqueado
        escola_pend = Escola.objects.create(nome='Escola Pendente Teste', nif_cnpj='NIF_PEND', email='pend@sige.mz', status='PENDENTE', plano=self.plano)
        user_pend = Usuario.objects.create_user(email='admin.pend@sige.mz', password='PassPend123!', role='ADMIN_ESCOLA', escola=escola_pend)
        login_pend = self.client.post('/api/v1/auth/login/', {'email': 'admin.pend@sige.mz', 'password': 'PassPend123!'}, format='json')
        assert login_pend.status_code == 401
        assert "Acesso bloqueado" in str(login_pend.data)
        assert "PENDENTE" in str(login_pend.data)

        # 4. Requisição à API com token de utilizador de escola suspensa -> 403 Forbidden
        from rest_framework_simplejwt.tokens import RefreshToken
        token_susp = str(RefreshToken.for_user(user_susp).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_susp}")
        res_api = self.client.get('/api/v1/alunos/')
        assert res_api.status_code == 403
        content_str = res_api.content.decode('utf-8') if hasattr(res_api, 'content') else str(res_api.data)
        assert "Acesso bloqueado" in content_str



