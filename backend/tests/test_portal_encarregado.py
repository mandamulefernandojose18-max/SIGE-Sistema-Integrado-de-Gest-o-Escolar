import datetime
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma
from apps.alunos.models import Aluno, PresencaAluno
from apps.pagamentos.models import Pagamento
from apps.crm.models import VinculoEncarregado

HOJE = datetime.date.today()


@pytest.mark.django_db
class TestPortalEncarregado:
    """Portal do Aluno para encarregados com vários educandos: sempre o educando escolhido e validado."""

    def setup_method(self):
        plano = Plano.objects.create(nome='PLANO_PORTAL', preco=2000, duracao_dias=30)
        self.escola = Escola.objects.create(nome='Escola Portal', nif_cnpj='NIF_POR1', email='por1@sige.mz', status='ATIVA', plano=plano)
        self.outra = Escola.objects.create(nome='Outra Portal', nif_cnpj='NIF_POR2', email='por2@sige.mz', status='ATIVA', plano=plano)
        self.turma = Turma.objects.create(escola=self.escola, nome='A', grau_ano='7ª Classe', ano_letivo=str(HOJE.year))
        mk = lambda mat, nome: Aluno.objects.create(escola=self.escola, turma=self.turma, matricula=mat, nome=nome, data_nascimento='2012-01-01', genero='M')
        self.filho1, self.filho2, self.estranho = mk('PO_001', 'Filho Um'), mk('PO_002', 'Filho Dois'), mk('PO_003', 'Aluno Estranho')
        self.aluno_outra = Aluno.objects.create(escola=self.outra, matricula='PO_009', nome='Aluno Outra', data_nascimento='2012-01-01', genero='F')
        self.enc_user = Usuario.objects.create_user(email='enc.portal@sige.mz', password='PassTeste123!', role='ENCARREGADO', escola=self.escola)
        for f in (self.filho1, self.filho2):
            VinculoEncarregado.objects.create(escola=self.escola, usuario=self.enc_user, aluno=f)
        self.enc = self._cli(self.enc_user)
        for aluno, n in ((self.filho1, 1), (self.filho2, 3), (self.estranho, 5)):
            PresencaAluno.objects.create(escola=self.escola, aluno=aluno, turma=self.turma, data=HOJE - datetime.timedelta(days=1),
                                         status='FALTA_INJUSTIFICADA', aulas=1)
            Pagamento.objects.create(escola=self.escola, aluno=aluno, mes_referencia=f'{HOJE.year}-0{n}', valor=100 * n, status='PENDENTE',
                                     descricao=f'Propina {n}', data_vencimento=timezone.now() + datetime.timedelta(days=5))

    def _cli(self, user):
        c = APIClient()
        c.force_authenticate(user)
        return c

    def test_varios_educandos_exigem_escolha_e_so_devolvem_o_escolhido(self):
        r = self.enc.get('/api/v1/alunos/me/pagamentos')
        assert r.status_code == 400 and 'escolher_educando' in r.data                  # dois educandos, nenhum escolhido
        d2 = self.enc.get(f'/api/v1/alunos/me/pagamentos?aluno_id={self.filho2.id}')
        assert d2.status_code == 200 and [p['valor'] for p in d2.data['data']] == ['300.00']
        d1 = self.enc.get(f'/api/v1/alunos/me/pagamentos?aluno_id={self.filho1.id}')
        assert [p['valor'] for p in d1.data['data']] == ['100.00']

    def test_aluno_que_nao_e_seu_e_recusado_em_todos_os_endpoints(self):
        for alvo in (self.estranho, self.aluno_outra):
            q = f'?aluno_id={alvo.id}'
            for url in ('/api/v1/alunos/me/pagamentos', '/api/v1/alunos/me/notas', '/api/v1/alunos/perfil/me', '/api/v1/alunos/me/anos',
                        f'/api/v1/alunos/me/faltas?ano={HOJE.year}'):
                sep = '&' if '?' in url else '?'
                assert self.enc.get(url + sep + q[1:]).status_code == 403, (url, alvo.nome)

    def test_perfil_notas_e_faltas_do_educando_escolhido(self):
        p = self.enc.get(f'/api/v1/alunos/perfil/me?aluno_id={self.filho2.id}')
        assert p.status_code == 200 and p.data['data']['nome'] == 'Filho Dois'
        n = self.enc.get(f'/api/v1/alunos/me/notas?aluno_id={self.filho1.id}')
        assert n.status_code == 200
        f = self.enc.get(f'/api/v1/alunos/me/faltas?ano={HOJE.year}&aluno_id={self.filho2.id}')
        assert f.status_code == 200
        assert self.enc.get('/api/v1/alunos/perfil/me').status_code == 400        # sem escolher

    def test_um_so_educando_nao_precisa_de_escolher(self):
        mae = Usuario.objects.create_user(email='enc.um@sige.mz', password='PassTeste123!', role='ENCARREGADO', escola=self.escola)
        VinculoEncarregado.objects.create(escola=self.escola, usuario=mae, aluno=self.filho1)
        r = self._cli(mae).get('/api/v1/alunos/me/pagamentos')
        assert r.status_code == 200 and [p['valor'] for p in r.data['data']] == ['100.00']

    def test_aluno_continua_igual_e_ignora_aluno_id(self):
        user = Usuario.objects.create_user(email='aluno.portal@sige.mz', password='PassTeste123!', role='ALUNO', escola=self.escola, aluno_id=self.filho1.id)
        r = self._cli(user).get(f'/api/v1/alunos/me/pagamentos?aluno_id={self.estranho.id}')
        assert [p['valor'] for p in r.data['data']] == ['100.00']

    def test_notas_nao_vazam_entre_escolas_nem_a_alunos_sem_vinculo(self):
        sec = Usuario.objects.create_user(email='sec.portal@sige.mz', password='PassTeste123!', role='SECRETARIA', escola=self.escola)
        assert self._cli(sec).get(f'/api/v1/alunos/me/notas?aluno_id={self.filho1.id}').status_code == 200
        assert self._cli(sec).get(f'/api/v1/alunos/me/notas?aluno_id={self.aluno_outra.id}').status_code == 404   # outra escola
        sem_vinculo = Usuario.objects.create_user(email='enc.sem@sige.mz', password='PassTeste123!', role='ENCARREGADO', escola=self.escola)
        assert self._cli(sem_vinculo).get(f'/api/v1/alunos/me/notas?aluno_id={self.filho1.id}').status_code == 403
        aluno_sem = Usuario.objects.create_user(email='aluno.sem@sige.mz', password='PassTeste123!', role='ALUNO', escola=self.escola)
        assert self._cli(aluno_sem).get(f'/api/v1/alunos/me/notas?aluno_id={self.filho1.id}').status_code == 403

    def test_encarregado_so_ve_propinas_dos_seus_educandos_na_api_geral(self):
        r = self.enc.get('/api/v1/pagamentos/')
        valores = sorted(float(p['valor']) for p in (r.data['data'] if isinstance(r.data, dict) and 'data' in r.data else r.data['results']))
        assert valores == [100.0, 300.0]                       # o aluno estranho (500) não aparece

    def test_encarregado_so_liquida_propina_de_educando_seu(self):
        alheia = Pagamento.objects.get(aluno=self.estranho)
        r = self.enc.post(f'/api/v1/pagamentos/{alheia.id}/liquidar/', {'metodo_pagamento': 'NUMERARIO'}, format='json')
        assert r.status_code == 404        # a propina de outro aluno nem aparece para o encarregado (não revela que existe)

    def test_presencas_so_dos_educandos(self):
        r = self.enc.get('/api/v1/alunos/presencas/')
        itens = r.data['results'] if isinstance(r.data, dict) and 'results' in r.data else r.data
        assert {str(i['aluno'] if 'aluno' in i else i.get('aluno_id')) for i in itens} == {str(self.filho1.id), str(self.filho2.id)}

    def test_pagar_mensalidade_de_um_educando_pelo_portal(self):
        pag = Pagamento.objects.get(aluno=self.filho2)
        alheia = Pagamento.objects.get(aluno=self.estranho)
        r = self.enc.post('/api/v1/alunos/me/pagamentos/', {'pagamento_id': str(alheia.id), 'metodo_pagamento': 'NUMERARIO'}, format='json')
        assert r.status_code == 404                                                    # não é de nenhum dos seus educandos
        ok = self.enc.post('/api/v1/alunos/me/pagamentos/', {'pagamento_id': str(pag.id), 'metodo_pagamento': 'NUMERARIO'}, format='json')
        assert ok.status_code != 404
