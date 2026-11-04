import datetime

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import LogAuditoria, Usuario
from apps.alunos.models import Aluno, TransferenciaAnulacao
from apps.pagamentos.models import Pagamento
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma

BASE = '/api/v1/alunos/transferencias/'


def _cliente(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


def _lista(res):
    return res.data['data']


@pytest.mark.django_db
class TestTransferencias:
    def setup_method(self):
        plano = Plano.objects.create(nome='PLANO_TR', preco=2000, duracao_dias=30)
        self.escola = Escola.objects.create(nome='Escola TR', nif_cnpj='NIF_TR', email='tr@sige.mz', status='ATIVA', plano=plano,
                                            director_nome='Director Teste')
        self.outra = Escola.objects.create(nome='Outra TR', nif_cnpj='NIF_TR2', email='tr2@sige.mz', status='ATIVA', plano=plano)
        self.turma = Turma.objects.create(escola=self.escola, nome='A', grau_ano='7ª Classe', ano_letivo='2026')
        self.aluno = Aluno.objects.create(escola=self.escola, turma=self.turma, matricula='TR_001', nome='Aluno', apelido='Um',
                                          data_nascimento='2012-01-01', genero='M')
        self.aluno2 = Aluno.objects.create(escola=self.escola, turma=self.turma, matricula='TR_002', nome='Aluno', apelido='Dois',
                                           data_nascimento='2012-02-02', genero='F')
        self.aluno_outra = Aluno.objects.create(escola=self.outra, matricula='TR_X01', nome='Alheio',
                                                data_nascimento='2012-01-01', genero='M', classe='7ª Classe')
        mk = lambda email, role, esc=self.escola: Usuario.objects.create_user(email=email, password='PassTr123!', role=role, escola=esc)
        self.sec = _cliente(mk('sec.tr@sige.mz', 'SECRETARIA'))
        self.dir = _cliente(mk('dir.tr@sige.mz', 'DIRECTOR_ESCOLA'))
        self.fin = _cliente(mk('fin.tr@sige.mz', 'FINANCEIRO'))
        self.aluno_user = _cliente(Usuario.objects.get(aluno_id=self.aluno.id))
        self.dir_outra = _cliente(mk('dir.tr2@sige.mz', 'DIRECTOR_ESCOLA', self.outra))

    def _pedido(self, aluno=None, **extra):
        body = {'aluno': str((aluno or self.aluno).id), 'tipo': 'TRANSFERENCIA_SAIDA', 'motivo_categoria': 'MUDANCA_RESIDENCIA',
                'escola_origem_destino': 'Escola Destino'}
        body.update(extra)
        return self.sec.post(BASE, body, format='json')

    def _quitar(self, t_id):
        return self.sec.post(f'{BASE}{t_id}/quitacao/', {'biblioteca': True, 'material': True, 'documentos': True}, format='json')

    # ---------- criação e permissões ----------
    def test_secretaria_cria_com_retrato_do_aluno(self):
        r = self._pedido()
        assert r.status_code == 201
        d = r.data['data']
        assert d['status'] == 'PENDENTE' and d['classe_snapshot'] == '7ª Classe' and d['turma_snapshot'] == 'A'

    def test_cliente_nao_define_estado_nem_aprovador(self):
        r = self._pedido(status='APROVADO', aprovado_por=str(Usuario.objects.first().id))
        assert r.status_code == 201
        assert r.data['data']['status'] == 'PENDENTE' and r.data['data']['aprovado_por'] is None

    def test_aluno_e_director_nao_criam_e_aluno_nao_lista(self):
        corpo = {'aluno': str(self.aluno.id), 'tipo': 'ANULACAO_MATRICULA', 'motivo_categoria': 'DESISTENCIA'}
        assert self.aluno_user.post(BASE, corpo, format='json').status_code == 403
        assert self.dir.post(BASE, corpo, format='json').status_code == 403
        assert self.aluno_user.get(BASE).status_code == 403

    def test_secretaria_nao_aprova_nem_rejeita(self):
        t = self._pedido().data['data']['id']
        assert self.sec.post(f'{BASE}{t}/aprovar/').status_code == 403
        assert self.sec.post(f'{BASE}{t}/rejeitar/', {'motivo': 'qualquer coisa'}, format='json').status_code == 403
        assert self.sec.post(f'{BASE}aprovar-lote/', {'ids': [t]}, format='json').status_code == 403

    def test_validacoes_de_criacao(self):
        assert self._pedido(escola_origem_destino='').status_code == 400
        assert self._pedido(motivo_categoria='OUTRO', motivo='').status_code == 400
        assert self.sec.post(BASE, {'aluno': str(self.aluno_outra.id), 'tipo': 'ANULACAO_MATRICULA', 'motivo_categoria': 'DESISTENCIA'},
                             format='json').status_code == 400
        assert self._pedido().status_code == 201
        assert self._pedido().status_code == 400  # duplicado pendente

    def test_aluno_inactivo_nao_inicia_processo(self):
        Aluno.objects.filter(id=self.aluno.id).update(status='TRANSFERIDO')
        assert self._pedido().status_code == 400

    # ---------- isolamento ----------
    def test_isolamento_entre_escolas(self):
        t = self._pedido().data['data']['id']
        assert _lista(self.dir_outra.get(BASE)) == []
        assert self.dir_outra.get(f'{BASE}{t}/').status_code == 404
        assert self.dir_outra.post(f'{BASE}{t}/aprovar/').status_code == 404
        sec_outra = _cliente(Usuario.objects.create_user(email='sec.tr2@sige.mz', password='PassTr123!', role='SECRETARIA', escola=self.outra))
        assert sec_outra.get(f'{BASE}buscar-alunos/?q=Aluno').data['data'] == []
        assert self.dir_outra.get(f'{BASE}buscar-alunos/?q=Aluno').status_code == 403

    # ---------- quitação e aprovação ----------
    def test_aprovacao_exige_quitacao(self):
        t = self._pedido().data['data']['id']
        r = self.dir.post(f'{BASE}{t}/aprovar/')
        assert r.status_code == 400 and r.data['codigo'] == 'QUITACAO_INCOMPLETA'
        self._quitar(t)
        r = self.dir.post(f'{BASE}{t}/aprovar/')
        assert r.status_code == 200
        self.aluno.refresh_from_db()
        assert self.aluno.status == 'TRANSFERIDO'
        assert r.data['data']['numero_guia'] == f'GT-{timezone.now().year}-0001'

    def test_propinas_em_divida_bloqueiam_e_mostram_mzn(self):
        Pagamento.objects.create(escola=self.escola, aluno=self.aluno, descricao='Propina', mes_referencia='2026-01', valor=1500,
                                 status='ATRASADO', data_vencimento=timezone.now() - datetime.timedelta(days=30))
        t = self._pedido().data['data']['id']
        self._quitar(t)
        r = self.dir.post(f'{BASE}{t}/aprovar/')
        assert r.status_code == 400
        propinas = r.data['quitacao_info']['itens']['propinas']
        assert propinas['em_divida'] == 1 and propinas['total_mzn'] == '1500.00' and propinas['moeda'] == 'MZN'

    def test_dispensa_de_quitacao_exige_justificacao_e_fica_registada(self):
        t = self._pedido().data['data']['id']
        assert self.dir.post(f'{BASE}{t}/aprovar/', {'ignorar_quitacao': True}, format='json').status_code == 400
        r = self.dir.post(f'{BASE}{t}/aprovar/', {'ignorar_quitacao': True, 'justificacao': 'Encarregado comprometeu-se por escrito'},
                          format='json')
        assert r.status_code == 200 and r.data['data']['quitacao_dispensada'] is True
        assert LogAuditoria.objects.filter(entidade='TRANSFERENCIA', objeto_id=t, acao='APROVACAO', descricao__icontains='dispensa').exists()

    def test_anulacao_inactiva_o_aluno_e_numeracao_sequencial(self):
        a = self._pedido(tipo='ANULACAO_MATRICULA', motivo_categoria='DESISTENCIA', escola_origem_destino='').data['data']['id']
        b = self._pedido(aluno=self.aluno2).data['data']['id']
        self._quitar(a); self._quitar(b)
        ra = self.dir.post(f'{BASE}{a}/aprovar/')
        rb = self.dir.post(f'{BASE}{b}/aprovar/')
        ano = timezone.now().year
        assert ra.data['data']['numero_guia'] == f'DA-{ano}-0001'
        assert rb.data['data']['numero_guia'] == f'GT-{ano}-0002'
        self.aluno.refresh_from_db()
        assert self.aluno.status == 'INATIVO'
        assert self.dir.post(f'{BASE}{a}/aprovar/').status_code == 400  # já aprovado

    def test_aprovar_em_lote_so_aprova_os_elegiveis(self):
        a = self._pedido().data['data']['id']
        b = self._pedido(aluno=self.aluno2).data['data']['id']
        self._quitar(a)
        r = self.dir.post(f'{BASE}aprovar-lote/', {'ids': [a, b]}, format='json')
        assert r.status_code == 200
        assert r.data['aprovados'] == [a] and [f['id'] for f in r.data['falhas']] == [b]

    # ---------- rejeitar / cancelar ----------
    def test_rejeitar_exige_motivo(self):
        t = self._pedido().data['data']['id']
        assert self.dir.post(f'{BASE}{t}/rejeitar/', {'motivo': 'x'}, format='json').status_code == 400
        r = self.dir.post(f'{BASE}{t}/rejeitar/', {'motivo': 'Documentação incompleta'}, format='json')
        assert r.status_code == 200 and r.data['data']['status'] == 'REJEITADO'
        self.aluno.refresh_from_db()
        assert self.aluno.status == 'ATIVO'
        assert self.dir.post(f'{BASE}{t}/aprovar/').status_code == 400

    def test_cancelar_pedido_pendente_e_novo_pedido_possivel(self):
        t = self._pedido().data['data']['id']
        assert self.sec.post(f'{BASE}{t}/cancelar/').data['data']['status'] == 'CANCELADO'
        assert self._pedido().status_code == 201
        assert self.sec.post(f'{BASE}{t}/cancelar/').status_code == 400

    # ---------- transferência de entrada ----------
    def test_entrada_cria_matricula_pendente_e_activa_na_aprovacao(self):
        corpo = {'tipo': 'TRANSFERENCIA_ENTRADA', 'motivo_categoria': 'MUDANCA_RESIDENCIA', 'escola_origem_destino': 'Escola de Origem',
                 'novo_aluno': {'nome': 'Novo', 'apelido': 'Aluno', 'data_nascimento': '2011-05-05', 'genero': 'F', 'classe': '8ª Classe'}}
        r = self.sec.post(BASE, corpo, format='json')
        assert r.status_code == 201
        t = r.data['data']
        novo = Aluno.objects.get(id=t['aluno'])
        assert novo.status == 'PENDENTE' and novo.escola_id == self.escola.id
        assert self.dir.post(f'{BASE}{t["id"]}/aprovar/').status_code == 200
        novo.refresh_from_db()
        assert novo.status == 'ATIVO'

    def test_entrada_rejeitada_nao_deixa_aluno_activo(self):
        corpo = {'tipo': 'TRANSFERENCIA_ENTRADA', 'motivo_categoria': 'OUTRO', 'motivo': 'Pedido', 'escola_origem_destino': 'Origem',
                 'novo_aluno': {'nome': 'Novo', 'data_nascimento': '2011-05-05', 'genero': 'M', 'classe': '8ª Classe'}}
        t = self.sec.post(BASE, corpo, format='json').data['data']
        self.dir.post(f'{BASE}{t["id"]}/rejeitar/', {'motivo': 'Sem guia da escola de origem'}, format='json')
        assert Aluno.objects.get(id=t['aluno']).status == 'INATIVO'

    def test_entrada_exige_dados_do_novo_aluno(self):
        r = self.sec.post(BASE, {'tipo': 'TRANSFERENCIA_ENTRADA', 'motivo_categoria': 'OUTRO', 'motivo': 'x',
                                 'escola_origem_destino': 'O', 'novo_aluno': {'nome': 'Só nome'}}, format='json')
        assert r.status_code == 400

    # ---------- listagem, filtros, resumo, exportação ----------
    def test_listagem_paginada_e_filtros(self):
        self._pedido(); self._pedido(aluno=self.aluno2, tipo='ANULACAO_MATRICULA', motivo_categoria='DESISTENCIA', escola_origem_destino='')
        r = self.dir.get(BASE + '?page_size=1')
        assert r.data['count'] == 2 and r.data['pages'] == 2 and len(_lista(r)) == 1
        assert len(_lista(self.dir.get(BASE + '?tipo=ANULACAO_MATRICULA'))) == 1
        assert len(_lista(self.dir.get(BASE + '?search=Dois'))) == 1
        assert len(_lista(self.dir.get(BASE + '?classe=7ª Classe&status=APROVADO'))) == 0
        assert self.dir.get(BASE + '?page=abc').status_code == 400

    def test_resumo_e_atrasados(self):
        t = self._pedido().data['data']['id']
        TransferenciaAnulacao.objects.filter(id=t).update(data_solicitacao=timezone.localdate() - datetime.timedelta(days=20))
        d = self.dir.get(BASE + 'resumo/').data['data']
        assert d['pendentes'] == 1 and d['atrasados'] == 1
        assert len(_lista(self.dir.get(BASE + '?atrasados=1'))) == 1
        item = _lista(self.dir.get(BASE))[0]
        assert item['atrasado'] is True and item['dias_pendente'] >= 20

    def test_busca_de_alunos_so_activos_da_escola(self):
        r = self.sec.get(BASE + 'buscar-alunos/?q=Aluno')
        assert {a['matricula'] for a in r.data['data']} == {self.aluno.matricula, self.aluno2.matricula}
        assert self.sec.get(BASE + 'buscar-alunos/?q=A').data['data'] == []

    def test_exportar_xlsx_e_pdf(self):
        self._pedido()
        x = self.dir.get(BASE + 'exportar/?formato=xlsx')
        assert x.status_code == 200 and x.content[:2] == b'PK'
        p = self.dir.get(BASE + 'exportar/?formato=pdf')
        assert p.status_code == 200 and p.content[:4] == b'%PDF'
        assert self.dir.get(BASE + 'exportar/?formato=csv').status_code == 400

    # ---------- documento oficial e verificação pública ----------
    def test_guia_pdf_so_apos_aprovacao_e_verificacao_publica(self):
        t = self._pedido().data['data']['id']
        assert self.dir.get(f'{BASE}{t}/documento/').status_code == 400
        self._quitar(t)
        self.dir.post(f'{BASE}{t}/aprovar/')
        r = self.dir.get(f'{BASE}{t}/documento/')
        assert r.status_code == 200 and r.content[:4] == b'%PDF'
        codigo = TransferenciaAnulacao.objects.get(id=t).codigo_verificacao
        pub = APIClient().get(f'{BASE}verificar/{codigo}/')
        assert pub.status_code == 200 and pub.data['data']['aluno'] == 'Aluno U.'
        assert 'matricula' not in str(pub.data) and 'TR_001' not in str(pub.data)
        assert APIClient().get(f'{BASE}verificar/TR-NAOEXISTE/').status_code == 404

    def test_declaracao_de_anulacao_em_pdf(self):
        t = self._pedido(tipo='ANULACAO_MATRICULA', motivo_categoria='DESISTENCIA', escola_origem_destino='').data['data']['id']
        self._quitar(t)
        self.dir.post(f'{BASE}{t}/aprovar/')
        assert self.dir.get(f'{BASE}{t}/documento/').content[:4] == b'%PDF'

    def test_codigo_de_verificacao_so_valido_se_aprovado(self):
        t = self._pedido().data['data']['id']
        TransferenciaAnulacao.objects.filter(id=t).update(codigo_verificacao='TR-PENDENTE00')
        assert APIClient().get(f'{BASE}verificar/TR-PENDENTE00/').status_code == 404

    # ---------- anexos e histórico ----------
    def test_anexos_validam_formato_tamanho_e_isolamento(self, settings, tmp_path):
        settings.MEDIA_ROOT = str(tmp_path)
        t = self._pedido().data['data']['id']
        mau = SimpleUploadedFile('virus.exe', b'x')
        assert self.sec.post(f'{BASE}{t}/anexos/', {'ficheiro': mau}, format='multipart').status_code == 400
        grande = SimpleUploadedFile('grande.pdf', b'0' * (5 * 1024 * 1024 + 1))
        assert self.sec.post(f'{BASE}{t}/anexos/', {'ficheiro': grande}, format='multipart').status_code == 400
        ok = SimpleUploadedFile('pedido.pdf', b'%PDF-1.4 teste')
        r = self.sec.post(f'{BASE}{t}/anexos/', {'ficheiro': ok}, format='multipart')
        assert r.status_code == 201
        aid = r.data['data'][0]['id']
        assert self.dir.get(f'{BASE}{t}/anexos/{aid}/').status_code == 200
        assert self.dir_outra.get(f'{BASE}{t}/anexos/{aid}/').status_code == 404
        assert self.fin.delete(f'{BASE}{t}/anexos/{aid}/').status_code == 403
        assert self.sec.delete(f'{BASE}{t}/anexos/{aid}/').status_code == 200

    def test_historico_regista_os_passos(self):
        t = self._pedido().data['data']['id']
        self._quitar(t)
        self.dir.post(f'{BASE}{t}/aprovar/')
        acoes = [h['acao'] for h in self.dir.get(f'{BASE}{t}/historico/').data['data']]
        assert acoes == ['CRIACAO', 'QUITACAO', 'APROVACAO']

    def test_financeiro_so_consulta(self):
        self._pedido()
        assert self.fin.get(BASE).status_code == 200
        assert self.fin.post(BASE, {'aluno': str(self.aluno2.id), 'tipo': 'ANULACAO_MATRICULA', 'motivo_categoria': 'DESISTENCIA'},
                             format='json').status_code == 403
