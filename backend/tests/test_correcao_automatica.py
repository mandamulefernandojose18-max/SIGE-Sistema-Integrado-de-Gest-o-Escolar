"""Correcção automática: importação do gabarito e leitura óptica da folha pela API (fluxo completo, isolamento
e permissões). As fotografias são simuladas (ver test_omr_leitura); os registos existem só na base de testes.
"""
import cv2
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.alunos.models import Aluno
from apps.disciplinas.models import Disciplina
from apps.notas.gabarito_importacao import ErroImportacao, extrair_gabarito
from apps.professores.models import AlocacaoDocente, Professor
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma
from tests.test_omr_leitura import _desenhar_folha_pdf, _fotografar, _pintar, _renderizar

BASE = '/api/v1/notas/provas-fisicas/'


# ---------------------------------------------------------------------------
# Importação do gabarito (sem base de dados)
# ---------------------------------------------------------------------------
def test_gabarito_formatos_de_texto():
    esperado = ['A', 'C', 'B', 'D', 'A', 'B']
    for txt in ('1-A 2-C 3-B 4-D 5-A 6-B', '1. A\n2. C\n3. B\n4. D\n5. A\n6. B', '1) a 2) c 3) b 4) d 5) a 6) b',
                '1 | A\n2 | C\n3 | B\n4 | D\n5 | A\n6 | B', 'ACBDAB   ', 'A, C, B, D, A, B'):
        r = extrair_gabarito(texto=txt)
        assert r['versoes'] == {'-': esperado}, txt
        assert r['n_perguntas'] == 6 and r['n_alternativas'] == 4


def test_gabarito_ignora_texto_corrido_e_artigos():
    txt = 'Prova de Matemática 2026\nGuião de correcção\n1-B 2-A 3-C 4-D\nO resultado é 5 A casa tem 10 m'
    r = extrair_gabarito(texto=txt)
    assert r['versoes']['-'][:4] == ['B', 'A', 'C', 'D']


def test_gabarito_com_versoes():
    txt = 'Versão A\n1-A 2-B 3-C 4-D\nVersão B\n1-D 2-C 3-B 4-A'
    r = extrair_gabarito(texto=txt)
    assert r['versoes'] == {'A': list('ABCD'), 'B': list('DCBA')}


def test_gabarito_lacuna_e_aviso():
    r = extrair_gabarito(texto='1-A 2-B 4-D 5-A 6-C 7-B 8-A 9-D 10-C 11-A 12-B')
    assert r['lacunas']['-'] == [3]
    assert any('perguntas 3' in a for a in r['avisos'])


def test_gabarito_recusa_o_que_nao_e_chave():
    with pytest.raises(ErroImportacao):
        extrair_gabarito(texto='Esta prova tem perguntas e respostas escritas por extenso.')
    with pytest.raises(ErroImportacao):
        extrair_gabarito(dados=b'\xff\xd8\xff\xe0' + b'0' * 50, nome='foto.jpg')
    with pytest.raises(ErroImportacao):
        extrair_gabarito(dados=b'', nome='x.txt')


def test_gabarito_docx_xlsx_csv_e_pdf():
    import io
    import docx
    from openpyxl import Workbook
    d = docx.Document()
    t = d.add_table(rows=3, cols=2)
    for i, (a, b) in enumerate((('1', 'B'), ('2', 'D'), ('3', 'A'))):
        t.rows[i].cells[0].text, t.rows[i].cells[1].text = a, b
    buf = io.BytesIO()
    d.save(buf)
    assert extrair_gabarito(dados=buf.getvalue(), nome='g.docx')['versoes']['-'] == ['B', 'D', 'A']

    wb = Workbook()
    ws = wb.active
    ws.append([1, 2, 3, 4])
    ws.append(['C', 'A', 'B', 'D'])
    buf = io.BytesIO()
    wb.save(buf)
    assert extrair_gabarito(dados=buf.getvalue(), nome='g.xlsx')['versoes']['-'] == list('CABD')

    assert extrair_gabarito(dados='n;resp\n1;A\n2;B\n3;C\n'.encode(), nome='g.csv')['versoes']['-'] == list('ABC')

    import fitz
    pdf = fitz.open()
    pg = pdf.new_page()
    pg.insert_text((72, 72), '1-D 2-C 3-B 4-A')
    assert extrair_gabarito(dados=pdf.tobytes(), nome='g.pdf')['versoes']['-'] == list('DCBA')
    vazio = fitz.open()
    vazio.new_page()
    with pytest.raises(ErroImportacao) as e:
        extrair_gabarito(dados=vazio.tobytes(), nome='scan.pdf')
    assert 'imagem' in str(e.value)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _media_temporaria(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


@pytest.mark.django_db
class TestCorreccaoAutomaticaApi:
    def setup_method(self):
        plano = Plano.objects.create(nome='PLANO_OMR', preco=2000, duracao_dias=30)
        self.escola = Escola.objects.create(nome='Escola Omr', nif_cnpj='NIF_OMR', email='omr@sige.mz', status='ATIVA', plano=plano)
        self.outra = Escola.objects.create(nome='Escola Alheia', nif_cnpj='NIF_OMR2', email='omr2@sige.mz', status='ATIVA', plano=plano)
        self.turma = Turma.objects.create(escola=self.escola, nome='A', grau_ano='10ª Classe', ano_letivo='2026')
        self.disc = Disciplina.objects.create(escola=self.escola, nome='Matemática', codigo='MAT', classe='10ª Classe', area='Geral')
        self.aluno = Aluno.objects.create(escola=self.escola, turma=self.turma, matricula='OMR_001', nome='Aluno Um',
                                          data_nascimento='2009-01-01', genero='M')
        prof = Professor.objects.create(escola=self.escola, nome='Prof', email='prof.omr@sige.mz', especialidade='Matemática')
        AlocacaoDocente.objects.create(escola=self.escola, professor=prof, disciplina=self.disc, turma=self.turma)
        self.professor = Usuario.objects.get(professor_id=prof.id)
        self.director = Usuario.objects.create_user(email='dir@omr.mz', password='PassD123!', role='DIRECTOR_ESCOLA', escola=self.escola)

    def _como(self, user):
        c = APIClient()
        c.force_authenticate(user)
        return c

    def _prova(self, gabarito='ABCDABCDAB'):
        folha = {'tipo_avaliacao': 'ACS1', 'n_perguntas': len(gabarito), 'n_alternativas': 4, 'gabarito': gabarito}
        r = self._como(self.professor).post(BASE, {
            'turma_id': str(self.turma.id), 'disciplina_id': str(self.disc.id), 'periodo': '1_TRIMESTRE',
            'titulo': 'ACS1', 'tipo': 'MULTIPLA_ESCOLHA', 'folha': folha}, format='json')
        assert r.status_code == 201, r.data
        return r.data['data']

    def _foto(self, respostas, escola_id=None, codigo=None, n=None):
        n = n or len(respostas)
        codigo = codigo or Aluno.objects.get(pk=self.aluno.pk).matricula   # a folha traz a matrícula real do aluno
        img = _renderizar(_desenhar_folha_pdf(n, 4, escola_id=escola_id or self.escola.id, codigo=codigo))
        img = _pintar(img, n, 4, {i + 1: ch for i, ch in enumerate(respostas) if ch != '-'})
        ok, buf = cv2.imencode('.jpg', _fotografar(img, graus=3), [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        assert ok
        return SimpleUploadedFile('folha.jpg', buf.tobytes(), content_type='image/jpeg')

    def test_importar_gabarito_por_texto_e_ficheiro(self):
        c = self._como(self.professor)
        r = c.post(BASE + 'gabarito/importar/', {'texto': '1-A 2-B 3-C 4-D'}, format='json')
        assert r.status_code == 200 and r.data['data']['versoes'] == {'-': list('ABCD')}
        r = c.post(BASE + 'gabarito/importar/',
                   {'ficheiro': SimpleUploadedFile('g.txt', b'1-D 2-C 3-B 4-A')}, format='multipart')
        assert r.status_code == 200 and r.data['data']['versoes']['-'] == list('DCBA')
        assert c.post(BASE + 'gabarito/importar/', {}, format='json').status_code == 400
        assert c.post(BASE + 'gabarito/importar/', {'texto': 'sem chave nenhuma'}, format='json').status_code == 400

    def test_gabaritos_guardados_guardar_listar_substituir_eliminar(self):
        c, url = self._como(self.professor), BASE + 'gabaritos-guardados/'
        corpo = {'nome': 'Física 11ª · AT', 'n_perguntas': 5, 'n_alternativas': 4, 'versoes': [],
                 'gabaritos': {'-': 'abcda'}}
        r = c.post(url, corpo, format='json')
        assert r.status_code == 201 and r.data['data']['gabaritos'] == {'-': 'ABCDA'}
        # mesmo nome substitui (não duplica)
        corpo['gabaritos'] = {'-': 'DDDDD'}
        r2 = c.post(url, corpo, format='json')
        assert r2.status_code == 200
        lista = c.get(url).data['data']
        assert len(lista) == 1 and lista[0]['gabaritos'] == {'-': 'DDDDD'} and lista[0]['n_perguntas'] == 5
        # chave incompleta / letra inválida / sem nome são recusadas com mensagem clara
        assert 'falta' in c.post(url, {**corpo, 'nome': 'x', 'gabaritos': {'-': 'ABC'}}, format='json').data['message']
        assert c.post(url, {**corpo, 'nome': 'x', 'gabaritos': {'-': 'ABCDZ'}}, format='json').status_code == 400
        assert c.post(url, {**corpo, 'nome': ''}, format='json').status_code == 400
        # com versões
        rv = c.post(url, {'nome': 'Duas versões', 'n_perguntas': 3, 'n_alternativas': 3, 'versoes': ['A', 'B'],
                          'gabaritos': {'A': 'ABC', 'B': 'CBA'}}, format='json')
        assert rv.status_code == 201 and rv.data['data']['versoes'] == ['A', 'B']
        # exportar o gabarito em PDF (uma tabela por versão)
        import fitz
        pdf = c.get(f'{url}{rv.data["data"]["id"]}/pdf/?carimbo=nao')
        assert pdf.status_code == 200 and pdf.content[:5] == b'%PDF-' and 'Gabarito' in pdf['Content-Disposition']
        texto = ''.join(p.get_text() for p in fitz.open(stream=pdf.content, filetype='pdf'))
        assert 'GUIÃO DE CORRECÇÃO' in texto and 'Versão A' in texto and 'Versão B' in texto and 'CBA' in texto
        outro_p = Usuario.objects.create_user(email='prof3@omr.mz', password='PassP123!', role='PROFESSOR', escola=self.escola)
        assert self._como(outro_p).get(f'{url}{rv.data["data"]["id"]}/pdf/?carimbo=nao').status_code == 404   # só o dono
        assert self._como(self.director).get(f'{url}{rv.data["data"]["id"]}/pdf/?carimbo=nao').status_code == 403
        # só o próprio professor, só da sua escola; a direcção não guarda
        assert self._como(self.director).get(url).status_code == 403
        assert self._como(self.director).post(url, corpo, format='json').status_code == 403
        outro = Usuario.objects.create_user(email='prof2@alheia.mz', password='PassP123!', role='PROFESSOR', escola=self.outra)
        assert self._como(outro).get(url).data['data'] == []
        gid = lista[0]['id']
        assert self._como(outro).delete(f'{url}{gid}/').status_code == 404
        assert c.delete(f'{url}{gid}/').status_code == 200
        assert [g['nome'] for g in c.get(url).data['data']] == ['Duas versões']

    def test_importar_gabarito_so_professor(self):
        assert self._como(self.director).post(BASE + 'gabarito/importar/', {'texto': '1-A 2-B'}, format='json').status_code == 403

    def test_leitura_identifica_aluno_le_respostas_e_corrige(self):
        prova = self._prova()
        resp = 'ABCDAB-DAB'            # gabarito ABCDABCDAB: só a pergunta 7 (em branco) fica errada → 9 certas em 10
        c = self._como(self.professor)
        r = c.post(f'{BASE}{prova["id"]}/leitura-omr/', {'ficheiro': self._foto(resp)}, format='multipart')
        assert r.status_code == 200, r.data
        p = r.data['data']['paginas'][0]
        assert p['ok'], p
        assert p['aluno'], p['avisos']
        assert p['aluno']['id'] == str(self.aluno.id)
        assert p['respostas'] == resp and p['duvidas'] == []
        assert p['imagem'].startswith('data:image/jpeg;base64,') and p['previa'].startswith('data:image/jpeg')
        # a leitura já devolve a prova corrigida (a vermelho) com acertos e nota, sem gravar nada
        assert p['acertos'] == 9 and p['nota'] == 18.0 and p['corrigida'].startswith('data:image/jpeg;base64,')
        # nada foi gravado pela leitura
        assert c.get(f'{BASE}{prova["id"]}/correcoes/{self.aluno.id}/').data['data'] is None
        # o professor confirma → grava e corrige contra o gabarito (9 certas em 10, cotação 2)
        g = c.put(f'{BASE}{prova["id"]}/correcoes/{self.aluno.id}/', {'respostas': p['respostas'], 'versao': ''}, format='json')
        assert g.status_code == 200, g.data
        assert g.data['data']['nota'] == 18.0 and g.data['data']['estado'] == 'CORRIGIDA'

    def test_confirmar_corrige_lanca_descarrega_pdf_e_elimina(self):
        import base64

        from apps.notas.models import Nota
        prova = self._prova()
        c = self._como(self.professor)
        p = c.post(f'{BASE}{prova["id"]}/leitura-omr/', {'ficheiro': self._foto('ABCDAB-DAB')}, format='multipart').data['data']['paginas'][0]
        url = f'{BASE}{prova["id"]}/correcoes/{self.aluno.id}/'
        r = c.post(url + 'confirmar-omr/', {'respostas': 'ABCDABNDAB', 'versao': '', 'imagem': p['imagem']}, format='json')
        assert r.status_code == 200, r.data
        assert r.data['data']['nota'] == 18.0 and r.data['data']['respostas'] == 'ABCDABNDAB'   # nula vale 0
        assert r.data['imagem'] and not r.data['aviso_imagem']
        assert r.data['lancamento'] == {'ok': True} and r.data['data']['estado'] == 'LANCADA'
        assert Nota.objects.filter(aluno=self.aluno, periodo='1_TRIMESTRE').exists()
        # PDF das folhas corrigidas (do aluno e da turma)
        for q in ('?carimbo=nao', f'?aluno_id={self.aluno.id}&carimbo=nao'):
            pdf = c.get(f'{BASE}{prova["id"]}/folhas-corrigidas/{q}')
            assert pdf.status_code == 200 and pdf['Content-Type'] == 'application/pdf' and pdf.content[:5] == b'%PDF-'
        assert self._como(self.director).get(f'{BASE}{prova["id"]}/folhas-corrigidas/?carimbo=nao').status_code == 200   # só consulta
        # lista de notas (PDF e Excel) com Nº, código, nome, turma, acertos, nota, resultado e estado
        lp = c.get(f'{BASE}{prova["id"]}/lista-notas/?formato=pdf&carimbo=nao')
        assert lp.status_code == 200 and lp.content[:5] == b'%PDF-' and 'Lista%20de%20notas' in lp['Content-Disposition']
        lx = c.get(f'{BASE}{prova["id"]}/lista-notas/?formato=xlsx&carimbo=nao')
        assert lx.status_code == 200
        import io

        from openpyxl import load_workbook
        ws = load_workbook(io.BytesIO(lx.content)).active
        textos = [str(c_.value) for linha in ws.iter_rows() for c_ in linha if c_.value is not None]
        assert any('Disciplina: Matemática' in t for t in textos) and any('Ano lectivo: 2026' in t for t in textos)
        assert 'Aluno Um' in textos and Aluno.objects.get(pk=self.aluno.pk).matricula in textos   # nome e código do aluno
        assert '18.0' in textos or 18.0 in [c_.value for linha in ws.iter_rows() for c_ in linha]
        assert c.get(f'{BASE}{prova["id"]}/lista-notas/?formato=doc').status_code == 400
        assert 'Avaliacao corrigida - Matem' in pdf['Content-Disposition'] or 'Avaliacao%20corrigida' in pdf['Content-Disposition']
        assert '2026' in pdf['Content-Disposition']
        # eliminar: só a prova corrigida (PDF); a correcção e a nota na caderneta ficam; o director não pode
        assert self._como(self.director).delete(url).status_code == 403
        d = c.delete(url)
        assert d.status_code == 200
        dados = c.get(url).data['data']
        assert dados['imagens'] == [] and dados['estado'] == 'LANCADA' and dados['nota'] == 18.0
        assert Nota.objects.filter(aluno=self.aluno, periodo='1_TRIMESTRE').exists()
        assert c.get(f'{BASE}{prova["id"]}/folhas-corrigidas/?carimbo=nao').status_code == 404
        assert c.delete(url).status_code == 404

    def test_folha_sem_aluno_fica_guardada_atribui_se_e_elimina_se_quiser(self):
        prova = self._prova()
        c = self._como(self.professor)
        base = f'{BASE}{prova["id"]}/'
        r = c.post(base + 'leitura-omr/', {'ficheiro': self._foto('ABCDABCDAB', codigo='NAO_EXISTE')}, format='multipart')
        p = r.data['data']['paginas'][0]
        assert p['ok'] and p['aluno'] is None and p['pendente_id']          # guardada no sistema
        # lê-se outra vez o mesmo ficheiro: não duplica
        c.post(base + 'leitura-omr/', {'ficheiro': self._foto('ABCDABCDAB', codigo='NAO_EXISTE')}, format='multipart')
        lista = c.get(base + 'folhas-pendentes/').data['data']
        assert len(lista) == 1 and lista[0]['id'] == p['pendente_id'] and lista[0]['respostas'] == 'ABCDABCDAB'
        img = c.get(f'{base}folhas-pendentes/{p["pendente_id"]}/imagem/')
        assert img.status_code == 200 and img.content[:3] == b'\xff\xd8\xff'
        # sem nenhum aluno atribuído, o PDF das provas corrigidas e a lista de notas JÁ funcionam (incluem a folha pendente)
        pdf = c.get(base + 'folhas-corrigidas/?carimbo=nao')
        assert pdf.status_code == 200 and pdf.content[:5] == b'%PDF-'
        import io

        import fitz
        assert fitz.open(stream=pdf.content, filetype='pdf').page_count == 1
        from openpyxl import load_workbook
        ws = load_workbook(io.BytesIO(c.get(base + 'lista-notas/?formato=xlsx&carimbo=nao').content)).active
        assert any('Por identificar' in str(x.value) for linha in ws.iter_rows() for x in linha if x.value)
        assert c.get(base + 'lista-notas/?formato=pdf&carimbo=nao').content[:5] == b'%PDF-'
        # alheios e direcção não acedem a escrever
        assert self._como(self.director).delete(f'{base}folhas-pendentes/{p["pendente_id"]}/').status_code == 403
        # atribuir a um aluno SEM reenviar a imagem (página recarregada) corrige, guarda a folha corrigida e retira a pendente
        r2 = c.post(f'{base}correcoes/{self.aluno.id}/confirmar-omr/',
                    {'respostas': 'ABCDABCDAB', 'versao': '', 'pendente_id': p['pendente_id'], 'lancar': False}, format='json')
        assert r2.status_code == 200 and r2.data['imagem'] and r2.data['data']['nota'] == 20.0
        assert c.get(base + 'folhas-pendentes/').data['data'] == []
        # outra pendente: o professor elimina quando quiser
        p2 = c.post(base + 'leitura-omr/', {'ficheiro': self._foto('ABCDABCDAB', codigo='NAO_EXISTE')},
                    format='multipart').data['data']['paginas'][0]
        assert c.delete(f'{base}folhas-pendentes/{p2["pendente_id"]}/').status_code == 200
        assert c.get(base + 'folhas-pendentes/').data['data'] == []
        assert c.delete(f'{base}folhas-pendentes/{p2["pendente_id"]}/').status_code == 404

    def test_guardar_na_leitura_corrige_e_guarda_em_alta_resolucao_sem_lancar(self):
        from apps.notas.models import Nota
        prova = self._prova()
        c = self._como(self.professor)
        base = f'{BASE}{prova["id"]}/'
        r = c.post(base + 'leitura-omr/', {'ficheiro': self._foto('ABCDABCDAB'), 'guardar': '1'}, format='multipart')
        p = r.data['data']['paginas'][0]
        assert p['ok'] and p['guardada'] and p['nota'] == 20.0 and p['acertos'] == 10
        assert not p['imagem'] and not p['previa'] and not p['corrigida']          # nada de imagens pelo navegador
        corr = c.get(f'{base}correcoes/{self.aluno.id}/').data['data']
        assert corr['estado'] == 'CORRIGIDA' and corr['respostas'] == 'ABCDABCDAB' and len(corr['imagens']) == 1
        assert not Nota.objects.filter(aluno=self.aluno).exists()                     # só lança no passo seguinte
        # a prova corrigida sai nítida e direita: A4 a ≈ 250 dpi (2100 × 2970), não uma miniatura ampliada
        import numpy as np
        img = c.get(f'{BASE}imagens/{corr["imagens"][0]["id"]}/')
        im = cv2.imdecode(np.frombuffer(b''.join(img.streaming_content), np.uint8), cv2.IMREAD_COLOR)
        assert im.shape[1] >= 2000 and im.shape[0] >= 2800
        # ler outra vez substitui, não duplica
        c.post(base + 'leitura-omr/', {'ficheiro': self._foto('ABCDABCDAB'), 'guardar': '1'}, format='multipart')
        assert len(c.get(f'{base}correcoes/{self.aluno.id}/').data['data']['imagens']) == 1

    def test_ficheiro_envia_se_uma_vez_e_le_se_por_referencia(self):
        prova = self._prova()
        c = self._como(self.professor)
        base = f'{BASE}{prova["id"]}/leitura-omr/'
        up = c.post(base + 'upload/', {'ficheiro': self._foto('ABCDABCDAB')}, format='multipart')
        assert up.status_code == 200 and up.data['data']['total_paginas'] == 1
        uid = up.data['data']['upload_id']
        r = c.post(base, {'upload_id': uid, 'nome': 'folhas.jpg', 'pagina_ini': 0}, format='multipart')
        p = r.data['data']['paginas'][0]
        assert r.status_code == 200 and p['ok'] and p['aluno'] and p['respostas'] == 'ABCDABCDAB'
        # outro utilizador/escola não usa o envio; identificador inventado ou apagado dá 410
        intruso = Usuario.objects.create_user(email='adm2@alheia.mz', password='PassA123!', role='ADMIN_ESCOLA', escola=self.outra)
        assert self._como(intruso).post(base, {'upload_id': uid}, format='multipart').status_code == 404
        assert c.delete(f'{base}upload/{uid}/').status_code == 200
        assert c.post(base, {'upload_id': uid, 'pagina_ini': 0}, format='multipart').status_code == 410
        assert c.post(base, {'upload_id': 'nao-e-um-uuid'}, format='multipart').status_code == 410
        assert self._como(self.director).post(base + 'upload/', {'ficheiro': self._foto('ABCDABCDAB')}, format='multipart').status_code == 403

    def test_leitura_recusa_folha_de_outra_escola_e_de_outra_prova(self):
        prova = self._prova()
        c = self._como(self.professor)
        r = c.post(f'{BASE}{prova["id"]}/leitura-omr/', {'ficheiro': self._foto('ABCDABCDAB', escola_id=self.outra.id)},
                   format='multipart')
        p = r.data['data']['paginas'][0]
        assert not p['ok'] and 'outra instituição' in p['erro']
        r = c.post(f'{BASE}{prova["id"]}/leitura-omr/', {'ficheiro': self._foto('ABCDABCDABCDABCDABCD')}, format='multipart')
        p = r.data['data']['paginas'][0]
        assert not p['ok']

    def test_leitura_aluno_de_fora_da_turma_pede_escolha_manual(self):
        prova = self._prova()
        r = self._como(self.professor).post(
            f'{BASE}{prova["id"]}/leitura-omr/', {'ficheiro': self._foto('ABCDABCDAB', codigo='NAO_EXISTE')}, format='multipart')
        p = r.data['data']['paginas'][0]
        assert p['ok'] and p['aluno'] is None
        assert any('escolha o aluno' in a for a in p['avisos'])

    def test_leitura_permissoes_e_prova_discursiva(self):
        prova = self._prova()
        url = f'{BASE}{prova["id"]}/leitura-omr/'
        assert self._como(self.director).post(url, {'ficheiro': self._foto('ABCDABCDAB')}, format='multipart').status_code == 403
        assert self._como(self.professor).post(url, {}, format='multipart').status_code == 400
        disc = self._como(self.professor).post(BASE, {
            'turma_id': str(self.turma.id), 'disciplina_id': str(self.disc.id), 'periodo': '1_TRIMESTRE',
            'instrumento': 'teste1', 'titulo': 'Discursiva', 'perguntas': [{'cotacao': 20}]}, format='json').data['data']
        r = self._como(self.professor).post(f'{BASE}{disc["id"]}/leitura-omr/', {'ficheiro': self._foto('ABCDABCDAB')},
                                            format='multipart')
        assert r.status_code == 400

    def test_leitura_prova_alheia_da_404(self):
        prova = self._prova()
        intruso = Usuario.objects.create_user(email='adm@alheia.mz', password='PassA123!', role='ADMIN_ESCOLA', escola=self.outra)
        r = self._como(intruso).post(f'{BASE}{prova["id"]}/leitura-omr/', {'ficheiro': self._foto('ABCDABCDAB')},
                                     format='multipart')
        assert r.status_code in (403, 404)

    def test_leitura_ficheiro_invalido(self):
        prova = self._prova()
        r = self._como(self.professor).post(
            f'{BASE}{prova["id"]}/leitura-omr/', {'ficheiro': SimpleUploadedFile('x.gif', b'GIF89a' + b'0' * 30)},
            format='multipart')
        assert r.status_code == 200 and not r.data['data']['paginas'][0]['ok']
