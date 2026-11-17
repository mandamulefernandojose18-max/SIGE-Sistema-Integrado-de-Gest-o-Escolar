"""Auditoria de notas: lançamento/alteração com valores antes/depois e PUT/DELETE bloqueados.

Os registos existem apenas na base de dados temporária dos testes.
"""
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Usuario, LogAuditoria
from apps.alunos.models import Aluno
from apps.disciplinas.models import Disciplina
from apps.notas.models import Nota
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma


@pytest.mark.django_db
class TestAuditoriaNotas:
    def setup_method(self):
        self.client = APIClient()
        plano = Plano.objects.create(nome='PLANO_AUD_NOTAS', preco=2000, duracao_dias=30)
        self.escola = Escola.objects.create(nome='Escola Aud', nif_cnpj='NIF_AUD', email='aud@sige.mz', status='ATIVA', plano=plano)
        Usuario.objects.create_user(email='super@aud.mz', password='PassS123!', role='SUPERADMIN', escola=self.escola)
        Usuario.objects.create_user(email='dir@aud.mz', password='PassD123!', role='DIRECTOR_ESCOLA', escola=self.escola)
        self.turma = Turma.objects.create(escola=self.escola, nome='10ª A', grau_ano='10ª Classe')
        self.aluno = Aluno.objects.create(escola=self.escola, turma=self.turma, matricula='MAT_AUD', nome='Aluno Aud',
                                          data_nascimento='2009-01-01', genero='M')
        self.disc = Disciplina.objects.create(escola=self.escola, nome='Matemática', codigo='MAT')

    def _login(self, email, senha):
        res = self.client.post('/api/v1/auth/login/', {'email': email, 'password': senha}, format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['token']}")

    def _lancar(self, t1):
        return self.client.post('/api/v1/notas/', {
            'aluno_id': str(self.aluno.id), 'turma_id': str(self.turma.id), 'disciplina_id': str(self.disc.id),
            'periodo': '1_TRIMESTRE', 'teste1': t1, 'teste2': 12, 'trabalho': 12, 'avaliacao_trimestral': 12,
        }, format='json')

    def test_lancamento_e_alteracao_ficam_auditados_com_antes_e_depois(self):
        self._login('super@aud.mz', 'PassS123!')
        r1 = self._lancar(10)
        assert r1.status_code in (200, 201), r1.data
        r2 = self._lancar(15)
        assert r2.status_code in (200, 201), r2.data
        logs = list(LogAuditoria.objects.filter(entidade='NOTA').order_by('created_at'))
        assert [l.acao for l in logs] == ['CRIACAO', 'ALTERACAO']
        assert logs[0].detalhes_antes is None
        assert logs[1].detalhes_antes['teste1'] != logs[1].detalhes_depois['teste1']

    def test_gravar_sem_mudancas_nao_gera_registo(self):
        self._login('super@aud.mz', 'PassS123!')
        self._lancar(10)
        self._lancar(10)
        assert LogAuditoria.objects.filter(entidade='NOTA').count() == 1

    def test_put_patch_e_delete_genericos_bloqueados(self):
        self._login('super@aud.mz', 'PassS123!')
        self._lancar(10)
        nota = Nota.objects.get(aluno=self.aluno)
        assert self.client.patch(f'/api/v1/notas/{nota.id}/', {'teste1': 20}, format='json').status_code == 405
        assert self.client.put(f'/api/v1/notas/{nota.id}/', {'teste1': 20}, format='json').status_code == 405
        assert self.client.delete(f'/api/v1/notas/{nota.id}/').status_code == 405
        nota.refresh_from_db()
        assert float(nota.teste1) == 10

    def test_endpoint_de_auditoria_filtra_por_data_e_pagina(self):
        self._login('super@aud.mz', 'PassS123!')
        self._lancar(10)
        self._lancar(15)
        self._login('dir@aud.mz', 'PassD123!')
        res = self.client.get('/api/v1/auth/auditoria/?entidade=NOTA&limit=1&offset=1')
        assert res.status_code == 200
        assert res.data['total'] == 2 and len(res.data['data']) == 1
        res = self.client.get('/api/v1/auth/auditoria/?entidade=NOTA&data_inicio=2999-01-01')
        assert res.data['total'] == 0
