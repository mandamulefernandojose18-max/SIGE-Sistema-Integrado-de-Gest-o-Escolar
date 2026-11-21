"""Correcção assistida de provas físicas: cotações, correcção por aluno, imagens autenticadas, lançamento
na caderneta (com auditoria) e isolamento entre escolas/professores.

Os registos existem apenas na base de dados temporária dos testes.
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.accounts.models import LogAuditoria, Usuario
from apps.alunos.models import Aluno
from apps.disciplinas.models import Disciplina
from apps.notas.models import CorrecaoProva, Nota, ProvaFisica
from apps.professores.models import AlocacaoDocente, Professor
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma

PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 32
BASE = '/api/v1/notas/provas-fisicas/'


@pytest.fixture(autouse=True)
def _media_temporaria(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


@pytest.mark.django_db
class TestCorrecaoProvas:
    def setup_method(self):
        plano = Plano.objects.create(nome='PLANO_CORR_PROVAS', preco=2000, duracao_dias=30)
        self.escola = Escola.objects.create(nome='Escola Corr', nif_cnpj='NIF_CORR', email='corr@sige.mz', status='ATIVA', plano=plano)
        self.outra = Escola.objects.create(nome='Escola Outra', nif_cnpj='NIF_CORR2', email='corr2@sige.mz', status='ATIVA', plano=plano)
        self.turma = Turma.objects.create(escola=self.escola, nome='A', grau_ano='10ª Classe', ano_letivo='2026')
        self.disc = Disciplina.objects.create(escola=self.escola, nome='Matemática', codigo='MAT', classe='10ª Classe', area='Geral')
        self.outra_disc = Disciplina.objects.create(escola=self.escola, nome='Física', codigo='FIS', classe='10ª Classe', area='Geral')
        self.aluno = Aluno.objects.create(escola=self.escola, turma=self.turma, matricula='CP_001', nome='Aluno Um',
                                          data_nascimento='2009-01-01', genero='M')
        prof = Professor.objects.create(escola=self.escola, nome='Prof', email='prof.corr@sige.mz', especialidade='Matemática')
        AlocacaoDocente.objects.create(escola=self.escola, professor=prof, disciplina=self.disc, turma=self.turma)
        self.professor = Usuario.objects.get(professor_id=prof.id)

        prof2 = Professor.objects.create(escola=self.escola, nome='Prof Dois', email='prof2.corr@sige.mz', especialidade='Física')
        AlocacaoDocente.objects.create(escola=self.escola, professor=prof2, disciplina=self.outra_disc, turma=self.turma)
        self.professor2 = Usuario.objects.get(professor_id=prof2.id)

        self.director = Usuario.objects.create_user(email='dir@corr.mz', password='PassD123!', role='DIRECTOR_ESCOLA', escola=self.escola)
        self.admin_outra = Usuario.objects.create_user(email='adm@outra.mz', password='PassA123!', role='ADMIN_ESCOLA', escola=self.outra)

    def _como(self, user):
        c = APIClient()
        c.force_authenticate(user)
        return c

    def _criar_prova(self, cliente=None, **extra):
        corpo = {'turma_id': str(self.turma.id), 'disciplina_id': str(self.disc.id), 'periodo': '1_TRIMESTRE',
                 'instrumento': 'teste1', 'titulo': '1º Teste', 'perguntas': [{'cotacao': 5}, {'cotacao': 5}, {'cotacao': 10}]}
        corpo.update(extra)
        return (cliente or self._como(self.professor)).post(BASE, corpo, format='json')

    def test_cria_prova_e_soma_cotacoes(self):
        r = self._criar_prova()
        assert r.status_code == 201, r.data
        assert r.data['data']['cotacao_total'] == 20
        assert len(r.data['data']['perguntas']) == 3

    def test_professor_nao_cria_prova_em_disciplina_nao_atribuida(self):
        assert self._criar_prova(disciplina_id=str(self.outra_disc.id)).status_code == 403

    def test_cotacao_invalida_e_instrumento_invalido(self):
        assert self._criar_prova(perguntas=[{'cotacao': 0}]).status_code == 400
        assert self._criar_prova(perguntas=[]).status_code == 400
        assert self._criar_prova(instrumento='nota_secreta').status_code == 400

    def test_correcao_converte_para_escala_0_20(self):
        prova = self._criar_prova().data['data']
        c = self._como(self.professor)
        r = c.put(f'{BASE}{prova["id"]}/correcoes/{self.aluno.id}/', {'pontos': [5, 2.5, 5]}, format='json')
        assert r.status_code == 200, r.data
        assert r.data['data']['total'] == 12.5
        assert r.data['data']['nota'] == 12.5  # cotação total 20 → nota igual
        assert r.data['data']['estado'] == 'CORRIGIDA'

    def test_cotacao_total_diferente_de_20_e_reescalada(self):
        prova = self._criar_prova(perguntas=[{'cotacao': 10}] * 5).data['data']
        assert prova['cotacao_total'] == 50
        r = self._como(self.professor).put(f'{BASE}{prova["id"]}/correcoes/{self.aluno.id}/',
                                           {'pontos': [10, 10, 5, 0, 0]}, format='json')
        assert r.data['data']['nota'] == 10.0

    def test_pontos_acima_da_cotacao_ou_negativos_sao_recusados(self):
        prova = self._criar_prova().data['data']
        c = self._como(self.professor)
        url = f'{BASE}{prova["id"]}/correcoes/{self.aluno.id}/'
        assert c.put(url, {'pontos': [6, 0, 0]}, format='json').status_code == 400
        assert c.put(url, {'pontos': [-1, 0, 0]}, format='json').status_code == 400
        assert c.put(url, {'pontos': [1, 1]}, format='json').status_code == 400

    def test_correcao_incompleta_fica_rascunho_e_nao_lanca(self):
        prova = self._criar_prova().data['data']
        c = self._como(self.professor)
        r = c.put(f'{BASE}{prova["id"]}/correcoes/{self.aluno.id}/', {'pontos': [5, None, 5]}, format='json')
        assert r.data['data']['estado'] == 'RASCUNHO'
        r = c.post(f'{BASE}{prova["id"]}/lancar/', {}, format='json')
        assert r.status_code == 409
        assert not Nota.objects.exists()

    def test_lancamento_grava_so_o_instrumento_e_audita(self):
        prova = self._criar_prova().data['data']
        c = self._como(self.professor)
        c.put(f'{BASE}{prova["id"]}/correcoes/{self.aluno.id}/', {'pontos': [5, 5, 4]}, format='json')
        assert not Nota.objects.exists(), 'nada chega à caderneta sem pedido de lançamento'
        r = c.post(f'{BASE}{prova["id"]}/lancar/', {}, format='json')
        assert r.status_code == 200, r.data
        assert r.data['lancadas'] == 1, r.data
        nota = Nota.objects.get(aluno=self.aluno, periodo='1_TRIMESTRE')
        assert nota.teste1 == 14
        assert CorrecaoProva.objects.get().estado == 'LANCADA'
        assert LogAuditoria.objects.filter(entidade='NOTA', acao='CRIACAO').count() == 1

    def test_lancamento_preserva_os_outros_instrumentos(self):
        Nota.objects.create(escola=self.escola, aluno=self.aluno, disciplina=self.disc, turma=self.turma,
                            periodo='1_TRIMESTRE', teste1=8, teste2=11, trabalho=12, avaliacao_trimestral=13)
        prova = self._criar_prova().data['data']
        c = self._como(self.professor)
        c.put(f'{BASE}{prova["id"]}/correcoes/{self.aluno.id}/', {'pontos': [5, 5, 10]}, format='json')
        assert c.post(f'{BASE}{prova["id"]}/lancar/', {}, format='json').status_code == 200
        nota = Nota.objects.get(aluno=self.aluno)
        assert (nota.teste1, nota.teste2, nota.trabalho, nota.avaliacao_trimestral) == (20, 11, 12, 13)
        assert LogAuditoria.objects.filter(entidade='NOTA', acao='ALTERACAO').count() == 1

    def test_alterar_correcao_lancada_exige_novo_lancamento(self):
        prova = self._criar_prova().data['data']
        c = self._como(self.professor)
        url = f'{BASE}{prova["id"]}/correcoes/{self.aluno.id}/'
        c.put(url, {'pontos': [5, 5, 4]}, format='json')
        c.post(f'{BASE}{prova["id"]}/lancar/', {}, format='json')
        assert c.put(url, {'pontos': [5, 5, 4]}, format='json').data['data']['estado'] == 'LANCADA'
        assert c.put(url, {'pontos': [5, 5, 5]}, format='json').data['data']['estado'] == 'CORRIGIDA'
        assert Nota.objects.get().teste1 == 14

    def test_prova_com_notas_lancadas_elimina_se_o_professor_quiser_e_mantem_a_caderneta(self):
        prova = self._criar_prova().data['data']
        c = self._como(self.professor)
        c.put(f'{BASE}{prova["id"]}/correcoes/{self.aluno.id}/', {'pontos': [5, 5, 4]}, format='json')
        c.post(f'{BASE}{prova["id"]}/lancar/', {}, format='json')
        d = c.delete(f'{BASE}{prova["id"]}/')
        assert d.status_code == 200 and d.data['lancadas_mantidas'] == 1
        assert Nota.objects.get().teste1 == 14               # a caderneta não muda
        assert c.get(f'{BASE}{prova["id"]}/').status_code == 404
        assert self._como(self.director).delete(f'{BASE}{prova["id"]}/').status_code in (403, 404)

    def test_direccao_consulta_mas_nao_corrige_nem_lanca(self):
        prova = self._criar_prova().data['data']
        d = self._como(self.director)
        assert d.get(f'{BASE}{prova["id"]}/').status_code == 200
        assert len(d.get(BASE).data['data']) == 1
        assert d.put(f'{BASE}{prova["id"]}/correcoes/{self.aluno.id}/', {'pontos': [1, 1, 1]}, format='json').status_code == 403
        assert d.post(f'{BASE}{prova["id"]}/lancar/', {}, format='json').status_code == 403
        assert self._criar_prova(cliente=d).status_code == 403

    def test_outro_professor_e_outra_escola_nao_veem_a_prova(self):
        prova = self._criar_prova().data['data']
        for user in (self.professor2, self.admin_outra):
            c = self._como(user)
            assert c.get(f'{BASE}{prova["id"]}/').status_code == 404
            assert c.put(f'{BASE}{prova["id"]}/correcoes/{self.aluno.id}/', {'pontos': [1, 1, 1]}, format='json').status_code in (403, 404)
            assert c.get(BASE).data['data'] == []

    def test_aluno_e_encarregado_sem_acesso(self):
        aluno_user = Usuario.objects.create_user(email='al@corr.mz', password='PassL123!', role='ALUNO', escola=self.escola)
        assert self._como(aluno_user).get(BASE).status_code == 403

    def test_imagem_so_png_jpg_pdf_e_acesso_autenticado(self):
        prova = self._criar_prova().data['data']
        c = self._como(self.professor)
        url = f'{BASE}{prova["id"]}/correcoes/{self.aluno.id}/imagens/'
        mau = SimpleUploadedFile('x.png', b'<script>alert(1)</script>', content_type='image/png')
        assert c.post(url, {'ficheiro': mau}, format='multipart').status_code == 400
        bom = SimpleUploadedFile('p.png', PNG, content_type='image/png')
        r = c.post(url, {'ficheiro': bom}, format='multipart')
        assert r.status_code == 201, r.data
        img_id = r.data['data']['id']
        ok = c.get(f'{BASE}imagens/{img_id}/')
        assert ok.status_code == 200
        assert b''.join(ok.streaming_content) == PNG
        assert ok['X-Content-Type-Options'] == 'nosniff'
        # outro professor, outra escola e anónimo não acedem
        assert self._como(self.professor2).get(f'{BASE}imagens/{img_id}/').status_code == 404
        assert self._como(self.admin_outra).get(f'{BASE}imagens/{img_id}/').status_code == 404
        assert APIClient().get(f'{BASE}imagens/{img_id}/').status_code in (401, 403)
        assert c.delete(f'{BASE}imagens/{img_id}/').status_code == 200
        assert c.get(f'{BASE}imagens/{img_id}/').status_code == 404

    def test_limite_de_paginas_por_prova(self):
        prova = self._criar_prova().data['data']
        c = self._como(self.professor)
        url = f'{BASE}{prova["id"]}/correcoes/{self.aluno.id}/imagens/'
        for _ in range(6):
            assert c.post(url, {'ficheiro': SimpleUploadedFile('p.png', PNG)}, format='multipart').status_code == 201
        assert c.post(url, {'ficheiro': SimpleUploadedFile('p.png', PNG)}, format='multipart').status_code == 400

    def test_aluno_de_outra_turma_e_recusado(self):
        outra_turma = Turma.objects.create(escola=self.escola, nome='B', grau_ano='10ª Classe', ano_letivo='2026')
        estranho = Aluno.objects.create(escola=self.escola, turma=outra_turma, matricula='CP_002', nome='Aluno Dois',
                                        data_nascimento='2009-02-02', genero='F')
        prova = self._criar_prova().data['data']
        r = self._como(self.professor).put(f'{BASE}{prova["id"]}/correcoes/{estranho.id}/', {'pontos': [1, 1, 1]}, format='json')
        assert r.status_code == 404

    # ---- Escolha múltipla: a prova nasce da configuração da Folha de Resposta gerada ----
    def _prova_mc(self, **folha):
        cfg = {'tipo_avaliacao': 'ACS1', 'n_perguntas': 4, 'n_alternativas': 4, 'gabarito': 'ABCD'}
        cfg.update(folha)
        return self._criar_prova(tipo='MULTIPLA_ESCOLHA', folha=cfg, perguntas=None, instrumento=None)

    def test_mc_cria_pela_config_da_folha_e_nao_expoe_gabarito(self):
        r = self._prova_mc()
        assert r.status_code == 201, r.data
        d = r.data['data']
        assert d['tipo'] == 'MULTIPLA_ESCOLHA' and d['instrumento'] == 'teste1' and d['n_alternativas'] == 4
        assert d['cotacao_total'] == 20 and len(d['perguntas']) == 4
        assert 'gabarito' not in str(r.data).lower()
        det = self._como(self.professor).get(f'{BASE}{d["id"]}/')
        assert 'ABCD' not in str(det.data)

    def test_mc_exige_gabarito_e_recusa_exame_e_config_invalida(self):
        assert self._prova_mc(gabarito='').status_code == 400
        assert self._prova_mc(tipo_avaliacao='EXAME').status_code == 400
        assert self._prova_mc(gabarito='ABC').status_code == 400   # tamanho não bate com as perguntas
        assert self._prova_mc(gabarito='ABCE').status_code == 400  # E não existe com 4 alternativas
        assert self._prova_mc(n_perguntas=0).status_code == 400

    def test_mc_corrige_contra_o_gabarito_e_lanca(self):
        prova = self._prova_mc().data['data']
        c = self._como(self.professor)
        r = c.put(f'{BASE}{prova["id"]}/correcoes/{self.aluno.id}/', {'respostas': 'AB-A'}, format='json')
        assert r.status_code == 200, r.data
        assert r.data['data']['pontos'] == [5, 5, 0, 0]  # certas: 1 e 2; a 3 em branco; a 4 errada
        assert r.data['data']['nota'] == 10 and r.data['data']['estado'] == 'CORRIGIDA'
        assert r.data['data']['respostas'] == 'AB-A'
        assert c.post(f'{BASE}{prova["id"]}/lancar/', {}, format='json').data['lancadas'] == 1
        assert Nota.objects.get(aluno=self.aluno).teste1 == 10

    def test_mc_respostas_invalidas(self):
        prova = self._prova_mc().data['data']
        c = self._como(self.professor)
        url = f'{BASE}{prova["id"]}/correcoes/{self.aluno.id}/'
        assert c.put(url, {'respostas': 'ABC'}, format='json').status_code == 400
        assert c.put(url, {'respostas': 'ABCE'}, format='json').status_code == 400

    def test_mc_cotacao_nao_inteira_e_20_sobre_3(self):
        prova = self._prova_mc(n_perguntas=3, gabarito='ABC').data['data']
        r = self._como(self.professor).put(f'{BASE}{prova["id"]}/correcoes/{self.aluno.id}/', {'respostas': 'ABC'}, format='json')
        assert r.status_code == 200, r.data
        assert r.data['data']['nota'] == 20

    def test_mc_versoes_com_chave_propria(self):
        prova = self._prova_mc(versoes='A B', gabaritos={'A': 'ABCD', 'B': 'DCBA'}).data['data']
        assert prova['versoes'] == ['A', 'B']
        c = self._como(self.professor)
        url = f'{BASE}{prova["id"]}/correcoes/{self.aluno.id}/'
        assert c.put(url, {'respostas': 'DCBA'}, format='json').status_code == 400  # falta a versão
        assert c.put(url, {'respostas': 'DCBA', 'versao': 'A'}, format='json').data['data']['nota'] == 0
        assert c.put(url, {'respostas': 'DCBA', 'versao': 'B'}, format='json').data['data']['nota'] == 20
        assert self._prova_mc(versoes='A B', gabaritos={'A': 'ABCD'}).status_code == 400  # falta a chave de B

    def test_mc_com_perguntas_abertas_fica_rascunho_ate_o_professor_dar_pontos(self):
        prova = self._prova_mc(n_perguntas=2, gabarito='AB', cotacao_pergunta=5,
                               abertas=[{'rotulo': 'Parte B', 'n': 2, 'cotacao': 5}]).data['data']
        assert prova['cotacao_total'] == 20 and [p['tipo'] for p in prova['perguntas']] == ['MC', 'MC', 'ABERTA', 'ABERTA']
        c = self._como(self.professor)
        url = f'{BASE}{prova["id"]}/correcoes/{self.aluno.id}/'
        r = c.put(url, {'respostas': 'AB'}, format='json')
        assert r.data['data']['estado'] == 'RASCUNHO'  # faltam as abertas
        r = c.put(url, {'respostas': 'AB', 'pontos': [None, None, 3, 4]}, format='json')
        assert r.data['data']['estado'] == 'CORRIGIDA' and r.data['data']['nota'] == 17
        assert c.put(url, {'respostas': 'AB', 'pontos': [None, None, 6, 4]}, format='json').status_code == 400

    def test_estado_vazio_sem_provas(self):
        r = self._como(self.professor).get(BASE)
        assert r.status_code == 200 and r.data['data'] == []
        assert not ProvaFisica.objects.exists()
