import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Pacote
from apps.tenants.pacotes import PACOTES_PADRAO, DESCONTOS_PADRAO, preco_periodo, tabela_precos, limpar_cache_funcionalidades


def _pacote(codigo):
    dados = next(p for p in PACOTES_PADRAO if p['codigo'] == codigo)
    obj, _ = Pacote.objects.get_or_create(
        codigo=codigo,
        defaults={**{k: v for k, v in dados.items() if k != 'codigo'}, 'descontos': dict(DESCONTOS_PADRAO)},
    )
    return obj


def _precos(codigo):
    t = tabela_precos(_pacote(codigo))
    return [int(t[p]['preco']) for p in ('mensal', 'trimestral', 'semestral', 'anual')]


@pytest.mark.django_db
class TestPrecosPacotes:
    def test_pedagogico_mantem_precos_actuais(self):
        assert _precos('pedagogico') == [1500, 4200, 7800, 14500]

    def test_essencial_e_completo(self):
        assert _precos('essencial') == [900, 2500, 4700, 8700]
        assert _precos('completo') == [2400, 6700, 12500, 23200]

    def test_arredondamento_a_50(self):
        assert preco_periodo(Decimal('1000'), 3, 0) == Decimal('3000')
        assert preco_periodo(Decimal('333'), 1, 0) == Decimal('350')

    def test_migracao_criou_tres_pacotes(self):
        for codigo in ('essencial', 'pedagogico', 'completo'):
            assert _pacote(codigo).nome


@pytest.mark.django_db
class TestFuncionalidadesPorPacote:
    def setup_method(self):
        limpar_cache_funcionalidades()
        self.client = APIClient()
        self.super = Usuario.objects.create_user(email='root@sige.co.mz', password='SuperPassword123!', role='SUPERADMIN')
        self.essencial, self.completo = _pacote('essencial'), _pacote('completo')
        _pacote('pedagogico')
        self.escola = Escola.objects.create(nome='Escola Pacote', nif_cnpj='NIF_PAC_1', email='pac1@sige.edu.mz',
                                            status='ATIVA', pacote=self.essencial)
        self.admin = Usuario.objects.create_user(email='admin.pac@sige.edu.mz', password='PassPacote123!',
                                                 role='ADMIN_ESCOLA', escola=self.escola)

    def _login(self, email, senha):
        res = self.client.post('/api/v1/auth/login/', {'email': email, 'password': senha}, format='json')
        assert res.status_code == 200
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['token']}")

    def test_essencial_bloqueia_financas_e_gateway(self):
        self._login('admin.pac@sige.edu.mz', 'PassPacote123!')
        for url in ('/api/v1/pagamentos/', '/api/v1/ferramentas/sms/historico', '/api/v1/material-escolar/'):
            res = self.client.get(url)
            assert res.status_code == 403, url
            assert res.json().get('codigo') == 'FUNCIONALIDADE_NAO_INCLUIDA'

    def test_nucleo_mec_nunca_e_bloqueado(self):
        self._login('admin.pac@sige.edu.mz', 'PassPacote123!')
        res = self.client.get('/api/v1/alunos/')
        assert res.status_code != 403 or res.json().get('codigo') != 'FUNCIONALIDADE_NAO_INCLUIDA'

    def test_completo_permite_financas(self):
        self.escola.pacote = self.completo
        self.escola.save()
        self._login('admin.pac@sige.edu.mz', 'PassPacote123!')
        res = self.client.get('/api/v1/pagamentos/')
        assert not (res.status_code == 403 and res.json().get('codigo') == 'FUNCIONALIDADE_NAO_INCLUIDA')

    def test_escola_sem_pacote_tem_acesso_total(self):
        self.escola.pacote = None
        self.escola.save()
        self._login('admin.pac@sige.edu.mz', 'PassPacote123!')
        res = self.client.get('/api/v1/pagamentos/')
        assert not (res.status_code == 403 and res.json().get('codigo') == 'FUNCIONALIDADE_NAO_INCLUIDA')

    def test_mudar_pacote_invalida_cache(self):
        self._login('admin.pac@sige.edu.mz', 'PassPacote123!')
        assert self.client.get('/api/v1/pagamentos/').status_code == 403
        self.escola.pacote = self.completo
        self.escola.save()
        res = self.client.get('/api/v1/pagamentos/')
        assert not (res.status_code == 403 and res.json().get('codigo') == 'FUNCIONALIDADE_NAO_INCLUIDA')

    def test_info_da_escola_devolve_funcionalidades(self):
        self._login('admin.pac@sige.edu.mz', 'PassPacote123!')
        res = self.client.get('/api/v1/escola-admin/info')
        assert res.status_code == 200
        data = res.json()['data']
        assert data['pacote_codigo'] == 'essencial'
        assert data['funcionalidades'] == []

    def test_superadmin_atribui_pacote_a_escola_e_cria_com_pedagogico_por_omissao(self):
        from apps.tenants.models import Plano
        _pacote('pedagogico')
        Plano.objects.create(nome='MENSAL', preco=1500, duracao_dias=30)
        self._login('root@sige.co.mz', 'SuperPassword123!')

        res = self.client.patch(f'/api/v1/saas-admin/escolas/{self.escola.id}/', {'pacote': str(self.completo.id)}, format='json')
        assert res.status_code == 200, res.content
        self.escola.refresh_from_db()
        assert self.escola.pacote_id == self.completo.id

        res = self.client.patch(f'/api/v1/saas-admin/escolas/{self.escola.id}/', {'pacote': None}, format='json')
        assert res.status_code == 200
        self.escola.refresh_from_db()
        assert self.escola.pacote_id is None

        res = self.client.post('/api/v1/saas-admin/escolas', {
            'nome': 'Escola Nova Pacote', 'nif_cnpj': 'NIF_PAC_NOVA', 'email': 'nova.pac@sige.edu.mz',
            'provincia': 'Gaza', 'distrito': 'Chibuto', 'tipo_escola': 'S',
        }, format='json')
        assert res.status_code in (200, 201), res.content
        nova = Escola.objects.get(nif_cnpj='NIF_PAC_NOVA')
        assert nova.pacote and nova.pacote.codigo == 'pedagogico'

    def test_impacto_do_pacote_antes_de_guardar_e_auditoria(self):
        from apps.accounts.models import LogAuditoria
        from apps.alunos.models import Aluno
        from apps.turmas.models import Turma
        completo = self.completo
        self.escola.pacote = completo
        self.escola.facturar_por_pacote = True
        self.escola.save()
        turma = Turma.objects.create(escola=self.escola, nome='T1', grau_ano='10ª Classe')
        for i in range(3):
            Aluno.objects.create(escola=self.escola, turma=turma, matricula=f'IMP{i}', nome=f'Aluno {i}',
                                 data_nascimento='2009-01-01', genero='M')
        self._login('root@sige.co.mz', 'SuperPassword123!')

        payload = {'preco_mensal': 3000, 'funcionalidades': ['exames'], 'limite_alunos': 2}
        res = self.client.post(f'/api/v1/saas-admin/pacotes/{completo.id}/impacto/', payload, format='json')
        assert res.status_code == 200, res.content
        d = res.json()['data']
        assert d['total_escolas'] == 1 and d['escolas_facturadas_por_pacote'] == 1
        assert d['variacao_receita_mensal'] == 600.0
        assert 'Finanças escolares' in d['funcionalidades_removidas']
        assert d['total_acima_do_limite'] == 1 and d['escolas_acima_do_limite'][0]['alunos'] == 3
        completo.refresh_from_db()
        assert float(completo.preco_mensal) == 2400.0  # a pré-visualização não grava

        res = self.client.patch(f'/api/v1/saas-admin/pacotes/{completo.id}/', {'preco_mensal': 2500}, format='json')
        assert res.status_code == 200
        log = LogAuditoria.objects.filter(entidade='PACOTE', acao='ALTERAR', objeto_id=str(completo.id)).first()
        assert log and log.detalhes_antes['preco_mensal'] == 2400.0 and log.detalhes_depois['preco_mensal'] == 2500.0

    def test_api_pacotes_so_superadmin_e_edicao(self):
        self._login('admin.pac@sige.edu.mz', 'PassPacote123!')
        assert self.client.get('/api/v1/saas-admin/pacotes/').status_code == 403

        self.client.credentials()
        self._login('root@sige.co.mz', 'SuperPassword123!')
        res = self.client.get('/api/v1/saas-admin/pacotes/')
        assert res.status_code == 200
        body = res.json()
        assert len(body['catalogo']) >= 10 and {p['codigo'] for p in body['data']} >= {'essencial', 'pedagogico', 'completo'}

        res = self.client.patch(f'/api/v1/saas-admin/pacotes/{self.essencial.id}/',
                                {'preco_mensal': 1000, 'funcionalidades': ['exames']}, format='json')
        assert res.status_code == 200
        assert res.json()['data']['precos']['mensal']['preco'] == 1000.0

        res = self.client.patch(f'/api/v1/saas-admin/pacotes/{self.essencial.id}/',
                                {'funcionalidades': ['inexistente']}, format='json')
        assert res.status_code == 400
        res = self.client.patch(f'/api/v1/saas-admin/pacotes/{self.essencial.id}/',
                                {'descontos': {'anual': 99}}, format='json')
        assert res.status_code == 400
        assert self.client.delete(f'/api/v1/saas-admin/pacotes/{self.essencial.id}/').status_code == 405
