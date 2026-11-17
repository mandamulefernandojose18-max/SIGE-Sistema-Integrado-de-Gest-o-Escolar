"""Isolamento multi-tenant: alocações docentes e acessos por id em ferramentas (pagamentos/SMS).

Os registos criados aqui existem apenas na base de dados temporária dos testes.
"""
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.alunos.models import Aluno
from apps.disciplinas.models import Disciplina
from apps.pagamentos.models import Pagamento
from apps.professores.models import Professor, AlocacaoDocente
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma


@pytest.mark.django_db
class TestIsolamentoAlocacoesEFerramentas:
    def setup_method(self):
        self.client = APIClient()
        plano = Plano.objects.create(nome='PLANO_ISOL_ALOC', preco=2000, duracao_dias=30)
        self.escola_a = Escola.objects.create(nome='Escola A', nif_cnpj='NIF_ISO_A', email='a@sige.mz', status='ATIVA', plano=plano)
        self.escola_b = Escola.objects.create(nome='Escola B', nif_cnpj='NIF_ISO_B', email='b@sige.mz', status='ATIVA', plano=plano)
        Usuario.objects.create_user(email='admin.a@iso.mz', password='PassA123!', role='ADMIN_ESCOLA', escola=self.escola_a)

        turma_b = Turma.objects.create(escola=self.escola_b, nome='10ª B', grau_ano='10ª Classe')
        self.aluno_b = Aluno.objects.create(escola=self.escola_b, turma=turma_b, matricula='MAT_ISO_B', nome='Aluno B',
                                            data_nascimento='2009-02-02', genero='F')
        prof_b = Professor.objects.create(escola=self.escola_b, nome='Prof B', email='prof.b@iso.mz', especialidade='Matemática')
        disc_b = Disciplina.objects.create(escola=self.escola_b, nome='Matemática', codigo='MAT')
        self.aloc_b = AlocacaoDocente.objects.create(escola=self.escola_b, professor=prof_b, disciplina=disc_b, turma=turma_b)
        self.pagamento_b = Pagamento.objects.create(
            escola=self.escola_b, aluno=self.aluno_b, descricao='Propina', mes_referencia='2026-03',
            valor=1000, status='PENDENTE', data_vencimento=timezone.now())

        res = self.client.post('/api/v1/auth/login/', {'email': 'admin.a@iso.mz', 'password': 'PassA123!'}, format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['token']}")

    def test_nao_apaga_alocacao_de_outra_escola(self):
        res = self.client.delete(f'/api/v1/professores/alocar/{self.aloc_b.id}/')
        assert res.status_code == 404
        assert AlocacaoDocente.objects.filter(id=self.aloc_b.id).exists()

    def test_nao_le_caderneta_de_outra_escola(self):
        res = self.client.get(f'/api/v1/professores/caderneta/{self.aloc_b.id}/completa/')
        assert res.status_code == 404

    def test_nao_liquida_pagamento_de_outra_escola(self):
        self.client.post('/api/v1/ferramentas/pagamentos/liquidar-manual/',
                         {'pagamento_id': str(self.pagamento_b.id), 'metodo': 'NUMERARIO'}, format='json')
        self.pagamento_b.refresh_from_db()
        assert self.pagamento_b.status == 'PENDENTE'

    def test_nao_associa_reconciliacao_com_aluno_de_outra_escola(self):
        res = self.client.post('/api/v1/ferramentas/reconciliacao/associar/',
                               {'reconciliacao_id': '00000000-0000-0000-0000-000000000000',
                                'aluno_id': str(self.aluno_b.id)}, format='json')
        assert res.status_code == 404
