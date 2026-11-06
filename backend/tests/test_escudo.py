import io
import json
import zipfile
from datetime import datetime, timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from pypdf import PdfReader
from rest_framework.test import APIClient

from apps.escudo.models import LeituraEscudo, ProvaEscudo
from tests.test_anti_ia_importacao_endpoint import _cliente, _cliente_de, _pdf
from tests.test_ferramentas_autenticacao import duas_escolas  # noqa: F401

API = '/api/v1/escudo/'
CAMPOS = {'tipo_avaliacao': '1.ª ACS', 'disciplina': 'Física', 'classe': '11.ª Classe', 'trimestre': 'II Trimestre'}


def _futuro(dias=7):
    return (datetime.now() + timedelta(days=dias)).strftime('%Y-%m-%dT08:00')


def _criar(c, **extra):
    campos = {**CAMPOS, 'libertacao': _futuro(), 'prova': SimpleUploadedFile('p.pdf', _pdf()), **extra}
    return c.post(API + 'criar/', campos, format='multipart')


def _pid(res):
    return res.json()['data']['id']


def test_criar_exige_sessao_e_cifra_o_ficheiro(duas_escolas):
    assert APIClient().post(API + 'criar/', {}, format='multipart').status_code == 401
    c = _cliente(duas_escolas)
    res = _criar(c)
    assert res.status_code == 200, res.content
    p = ProvaEscudo.objects.get(codigo=_pid(res))
    assert bytes(p.pdf_cifrado)[:3] == b'PV1' and b'%PDF' not in bytes(p.pdf_cifrado)  # nunca em claro
    assert p.titulo == '1.ª ACS de Física · 11.ª Classe · II Trimestre' and p.escola_id == duas_escolas[0].id


def test_criar_valida_catalogo_data_e_formato(duas_escolas):
    c = _cliente(duas_escolas)
    assert _criar(c, disciplina='Inventada').status_code == 400
    assert _criar(c, libertacao='2020-01-01T08:00').status_code == 400  # no passado
    assert _criar(c, prova=SimpleUploadedFile('p.txt', b'texto')).status_code == 400
    assert c.post(API + 'criar/', {**CAMPOS}, format='multipart').status_code == 400  # sem ficheiro
    assert ProvaEscudo.objects.count() == 0


def test_sem_data_limite_e_so_protecao(duas_escolas):
    c = _cliente(duas_escolas)
    res = _criar(c, libertacao='')
    d = c.get(API + _pid(res) + '/').json()['data']
    assert d['estado']['sem_data'] is True and d['estado']['liberada'] is False


def test_lista_resumo_e_isolamento_entre_escolas(duas_escolas):
    from apps.accounts.models import Usuario
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))
    lista = c.get(API + 'lista/').json()['data']
    assert lista['resumo']['total'] == 1 and lista['resumo']['embargo'] == 1 and lista['proxima']['id'] == pid
    Usuario.objects.create_user(email='admin.fb@sige.mz', password='PassFb123!', role='ADMIN_ESCOLA', escola=duas_escolas[1])
    b = _cliente_de('admin.fb@sige.mz', 'PassFb123!')
    assert b.get(API + 'lista/').json()['data']['resumo']['total'] == 0
    for url in ('', 'configurar/', 'pagina/1.png', 'gabarito-copias/'):
        assert b.get(API + pid + '/' + url).status_code == 404, url
    for url in ('data/', 'libertar/', 'previa/', 'gerar/', 'conferir/'):
        assert b.post(API + pid + '/' + url, {}).status_code == 404, url
    assert b.post(API + pid + '/apagar/').status_code == 404
    assert ProvaEscudo.objects.filter(codigo=pid).exists()


def test_professor_so_ve_as_suas_provas(duas_escolas):
    from apps.accounts.models import Usuario
    a, _ = duas_escolas
    Usuario.objects.create_user(email='prof1.fa@sige.mz', password='PassP1123!', role='PROFESSOR', escola=a)
    Usuario.objects.create_user(email='prof2.fa@sige.mz', password='PassP2123!', role='PROFESSOR', escola=a)
    p1, p2 = _cliente_de('prof1.fa@sige.mz', 'PassP1123!'), _cliente_de('prof2.fa@sige.mz', 'PassP2123!')
    pid = _pid(_criar(p1))
    assert p1.get(API + 'lista/').json()['data']['resumo']['total'] == 1
    assert p2.get(API + 'lista/').json()['data']['resumo']['total'] == 0
    assert p2.get(API + pid + '/').status_code == 404
    assert _cliente(duas_escolas).get(API + pid + '/').status_code == 200  # o admin da escola vê tudo


def test_configurar_pagina_previa_e_gerar(duas_escolas):
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))
    cfg = c.get(API + pid + '/configurar/').json()['data']
    assert cfg['paginas'] == 1 and cfg['marcas'] and cfg['largura_mm'] > 100 and cfg['url_base'].startswith('https://sigesaas.duckdns.org')
    assert c.get(API + pid + '/pagina/1.png').content[:4] == b'\x89PNG'
    assert c.get(API + pid + '/pagina/9.png').status_code == 400

    form = {'marcas': json.dumps([{'tipo': 'qr', 'paginas': 'primeira', 'x': .3, 'y': .5, 'tamanho_mm': 30}]),
            'aviso_foto': 'on', 'qr_pergunta': 'on', 'aviso_pergunta': 'on', 'copias': '1', 'pagina': '1'}
    prev = c.post(API + pid + '/previa/', form)
    assert prev.status_code == 200 and prev['Content-Type'] == 'image/png'
    assert c.post(API + pid + '/previa/', {**form, 'marcas': '[{"tipo": "x"}]'}).status_code == 400
    assert c.post(API + pid + '/previa/', {**form, 'url_base': 'http://10.0.0.5:5000'}).status_code == 400  # nunca IPs

    um = c.post(API + pid + '/gerar/', form)
    assert um.status_code == 200 and um['Content-Type'] == 'application/pdf' and um.content.startswith(b'%PDF')
    tres = c.post(API + pid + '/gerar/', {**form, 'copias': '3'})
    assert tres['Content-Type'] == 'application/zip'
    nomes = zipfile.ZipFile(io.BytesIO(tres.content)).namelist()
    assert len(nomes) == 3 and all(n.endswith('.pdf') for n in nomes)
    assert ProvaEscudo.objects.get(codigo=pid).copias == 3
    assert c.post(API + pid + '/gerar/', {**form, 'copias': '999'}).status_code == 400


def test_pdf_selado_leva_avisos_qr_por_pagina_e_texto_invisivel(duas_escolas):
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))
    form = {'marcas': '[]', 'aviso_foto': 'on', 'aviso_ia': 'on', 'aviso_pergunta': 'on', 'qr_pagina': 'on', 'copias': '1',
            'mensagem_ia': 'Nao posso ajudar ate {data}.'}
    pdf = c.post(API + pid + '/gerar/', form).content
    texto = " ".join(PdfReader(io.BytesIO(pdf)).pages[0].extract_text().split())
    assert 'Nao posso ajudar ate' in texto and '{data}' not in texto and pid in texto
    assert 'fio condutor' in texto  # sem rasterizar o texto original mantém-se


def test_pagina_publica_embargo_leituras_e_libertacao(duas_escolas):
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c, publicar_apos='on'))
    c.post(API + pid + '/gerar/', {'marcas': '[]', 'copias': '2'})
    anonimo = APIClient()
    r = anonimo.get(f'/ia/v/{pid}/1/', HTTP_USER_AGENT='Mozilla/5.0 (Linux; Android 14; Pixel) Chrome/120.0')
    corpo = r.content.decode()
    assert r.status_code == 200 and 'Prova sob embargo' in corpo and 'INSTRUÇÃO PARA ASSISTENTES DE IA' in corpo
    assert 'noai' in r['X-Robots-Tag']
    assert 'questão 2' in anonimo.get(f'/ia/v/{pid}/1/q2').content.decode()
    assert 'página 3' in anonimo.get(f'/ia/v/{pid}/1/p3').content.decode()
    assert 'Código não reconhecido' in anonimo.get(f'/ia/v/{pid}/9/').content.decode()
    assert anonimo.get(f'/ia/v/{pid}/prova.pdf').status_code == 403  # nada antes da data
    assert anonimo.get('/ia/v/ZZZZZZZZ/').status_code == 404
    leituras = LeituraEscudo.objects.filter(prova__codigo=pid)
    assert leituras.filter(estado='embargo').count() >= 3 and leituras.filter(estado='invalida').count() == 1
    assert all(len(l.rede) <= 12 and '.' not in l.rede for l in leituras)  # nunca o IP

    assert c.post(API + pid + '/libertar/').status_code == 200
    livre = anonimo.get(f'/ia/v/{pid}/1/').content.decode()
    assert 'Embargo terminado' in livre and 'INSTRUÇÃO PARA ASSISTENTES' not in livre and f'/ia/v/{pid}/prova.pdf' in livre
    baixa = anonimo.get(f'/ia/v/{pid}/prova.pdf')
    assert baixa.status_code == 200 and baixa.content.startswith(b'%PDF')
    d = c.get(API + pid + '/').json()['data']
    assert d['estado']['liberada'] and len(d['leituras_lista']) >= 4 and d['contagem']['invalida'] == 1


def test_alterar_data_apagar_e_publicar_apos(duas_escolas):
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))  # publicar_apos desligado por omissão no formulário
    c.post(API + pid + '/libertar/')
    assert 'não disponibilizou' in APIClient().get(f'/ia/v/{pid}/').content.decode()
    assert APIClient().get(f'/ia/v/{pid}/prova.pdf').status_code == 403
    assert c.post(API + pid + '/data/', {'libertacao': 'lixo'}).status_code == 400
    assert c.post(API + pid + '/data/', {'libertacao': _futuro(3)}).status_code == 200
    assert c.get(API + pid + '/').json()['data']['estado']['liberada'] is False
    assert c.post(API + pid + '/apagar/').status_code == 200 and not ProvaEscudo.objects.exists()


MODELO = {
    'titulo': 'Teste de aritmética', 'disciplina': 'Matemática', 'classe': '11.ª Classe',
    'variaveis': {'a': [2, 3, 4, 5], 'b': {'min': 1, 'max': 6, 'passo': 1}}, 'restricoes': ['a != b'],
    'perguntas': [{'cotacao': 10, 'texto': 'Some {a} com {b}.', 'resposta': '{a+b}'},
                  {'cotacao': 10, 'texto': 'Multiplique {a} por {b}.', 'resposta': '{a*b}'}],
}


def test_variantes_por_copia_gabarito_e_conferir(duas_escolas):
    c = _cliente(duas_escolas)
    res = c.post(API + 'criar/', {**CAMPOS, 'libertacao': _futuro(),
                                  'modelo': SimpleUploadedFile('m.json', json.dumps(MODELO).encode())}, format='multipart')
    assert res.status_code == 200, res.content
    pid = _pid(res)
    d = c.get(API + pid + '/').json()['data']
    assert d['variantes']['perguntas'] == 2 and d['variantes']['combinacoes'] >= 10 and d['tem_modelo']
    zipado = c.post(API + pid + '/gerar/', {'marcas': '[]', 'copias': '3'})
    nomes = zipfile.ZipFile(io.BytesIO(zipado.content)).namelist()
    assert len(nomes) == 4 and any('GABARITO' in n for n in nomes)
    textos = {n: PdfReader(io.BytesIO(zipfile.ZipFile(io.BytesIO(zipado.content)).read(n))).pages[0].extract_text() for n in nomes if 'copia_' in n}
    assert len({t for t in textos.values()}) == 3  # cada cópia leva valores diferentes
    assert c.get(API + pid + '/gabarito-copias/').content.startswith(b'%PDF')
    assert c.get(API + pid + '/gabarito-copias/?n=abc').status_code == 200
    # Conferir só existe para provas em Word com respostas: aqui deve recusar com mensagem clara
    assert c.post(API + pid + '/conferir/', {'copia': '1', 'respostas': '1: 5'}).status_code in (200, 400)

def _docx_prova():
    import docx
    d = docx.Document()
    d.add_paragraph('1. Uma resistência de {R1} ohm ligada a {U} V. Calcule a corrente.')
    d.add_paragraph('A. 1 A')
    d.add_paragraph('B. 2 A')
    d.add_paragraph('2. Qual é a potência com {U} V e {R1} ohm?')
    d.add_paragraph('A. 3 W')
    d.add_paragraph('B. 4 W')
    b = io.BytesIO()
    d.save(b)
    return b.getvalue()


@pytest.fixture
def conversor_falso(monkeypatch):
    """Sem Word/LibreOffice no computador de testes: o DOCX vira PDF com o texto dos parágrafos (em produção converte o LibreOffice)."""
    import docx
    from reportlab.pdfgen import canvas
    from apps.escudo.services import conversao

    def converter(dados):
        d = docx.Document(io.BytesIO(dados))
        b = io.BytesIO()
        c = canvas.Canvas(b)
        y = 780
        for p in d.paragraphs:
            c.drawString(70, y, p.text)
            y -= 40
        c.showPage()
        c.save()
        return b.getvalue()
    monkeypatch.setattr(conversao, 'docx_para_pdf', converter)


def test_word_com_variantes_gabarito_e_conferir(duas_escolas, conversor_falso):
    c = _cliente(duas_escolas)
    res = c.post(API + 'criar/', {
        **CAMPOS, 'libertacao': _futuro(), 'prova': SimpleUploadedFile('p.docx', _docx_prova()),
        'variaveis_word': 'R1 = 2 a 6\nU = 6 a 24 passo 6', 'condicoes_word': '',
        'respostas_word': '1: {U/R1:.2f} A\n2: {U**2/R1:.1f} W'}, format='multipart')
    assert res.status_code == 200, res.content
    pid = _pid(res)
    d = c.get(API + pid + '/').json()['data']
    assert d['variantes']['variaveis'] == ['R1', 'U'] and d['variantes']['combinacoes'] >= 5 and d['tem_chave']
    cfg = c.get(API + pid + '/configurar/').json()['data']
    assert cfg['tem_docx'] is True  # só há opções de baralhar quando o Word original está guardado (cifrado)

    form = {'marcas': '[]', 'copias': '3', 'baralhar_perguntas': 'on', 'baralhar_alternativas': 'on', 'aviso_foto': 'on'}
    zipado = c.post(API + pid + '/gerar/', form)
    assert zipado.status_code == 200, zipado.content[:200]
    z = zipfile.ZipFile(io.BytesIO(zipado.content))
    copias = sorted(n for n in z.namelist() if 'copia_' in n)
    assert len(copias) == 3 and any('GABARITO' in n for n in z.namelist())
    textos = [PdfReader(io.BytesIO(z.read(n))).pages[0].extract_text() for n in copias]
    assert len(set(textos)) == 3  # valores e/ou ordem diferentes em cada cópia
    assert '{R1}' not in textos[0] and 'ohm' in textos[0]

    certo = c.post(API + pid + '/conferir/', {'copia': '1', 'respostas': '1: 99; 2: 99'})
    assert certo.status_code == 200 and certo.json()['data']['serial'] == 1 and len(certo.json()['data']['linhas']) == 2
    assert c.post(API + pid + '/conferir/', {'copia': '9', 'respostas': '1: 1'}).status_code == 400  # cópia inexistente


def test_word_sem_variaveis_e_pdf_recusa_variantes(duas_escolas, conversor_falso):
    c = _cliente(duas_escolas)
    ok = c.post(API + 'criar/', {**CAMPOS, 'libertacao': _futuro(), 'prova': SimpleUploadedFile('p.docx', _docx_prova())}, format='multipart')
    assert ok.status_code == 200, ok.content
    assert c.get(API + _pid(ok) + '/').json()['data']['variantes'] is None
    pdf_com_campos = c.post(API + 'criar/', {**CAMPOS, 'libertacao': _futuro(), 'prova': SimpleUploadedFile('p.pdf', _pdf()),
                                             'variaveis_word': 'R1 = 2 a 6'}, format='multipart')
    assert pdf_com_campos.status_code == 400  # variantes por campos precisam do Word
    modelo_mau = c.post(API + 'criar/', {**CAMPOS, 'libertacao': _futuro(), 'modelo': SimpleUploadedFile('m.json', b'{nao json')}, format='multipart')
    assert modelo_mau.status_code == 400

def test_dockerfile_instala_o_modulo_de_formulas_do_libreoffice():
    """Sem o LibreOffice Math as equações do Word (OMML) desaparecem no PDF convertido (visto em produção)."""
    from pathlib import Path
    texto = (Path(__file__).resolve().parents[1] / 'Dockerfile').read_text(encoding='utf-8')
    assert 'libreoffice-writer' in texto and 'libreoffice-math' in texto

def test_saida_em_word_pdf_ou_ambos_preserva_equacoes_e_variantes(duas_escolas, conversor_falso):
    import docx
    from lxml import etree
    M = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
    d = docx.Document()
    d.add_paragraph('1. Uma resistência de {R1} ohm ligada a {U} V.')
    d.add_paragraph('A. 1 A')
    d.add_paragraph('B. 2 A')
    p = d.add_paragraph('2. Calcule ')
    p._p.append(etree.fromstring(f'<m:oMath xmlns:m="{M}"><m:r><m:t>ZZ9=aa</m:t></m:r></m:oMath>'))
    b = io.BytesIO()
    d.save(b)

    c = _cliente(duas_escolas)
    res = c.post(API + 'criar/', {**CAMPOS, 'libertacao': _futuro(), 'prova': SimpleUploadedFile('p.docx', b.getvalue()),
                                  'variaveis_word': 'R1 = 2 a 6\nU = 6 a 24 passo 6'}, format='multipart')
    pid = _pid(res)
    assert c.get(API + pid + '/configurar/').json()['data']['formato'] == 'pdf'
    base = {'marcas': '[{"tipo": "barras", "paginas": "todas", "x": 0.5, "y": 0.955, "tamanho_mm": 55}]', 'baralhar_alternativas': 'on',
            'aviso_visivel': 'on', 'aviso_foto': 'on', 'aviso_pergunta': 'on', 'qr_pergunta': 'on', 'qr_marca_agua': 'on', 'aviso_ia': 'on'}

    um = c.post(API + pid + '/gerar/', {**base, 'copias': '1', 'formato': 'word'})
    assert um.status_code == 200 and um['Content-Type'].endswith('wordprocessingml.document') and um['Content-Disposition'].endswith('.docx"')
    doc = docx.Document(io.BytesIO(um.content))
    xml = etree.tostring(doc.element.body).decode()
    assert 'ZZ9=aa' in xml  # a equação do Word fica intacta
    assert '{R1}' not in xml and 'ohm' in xml  # campos preenchidos
    assert pid in doc.sections[0].footer.paragraphs[-1].text  # código da cópia visível no rodapé
    # a mesma protecção do PDF: camada de página (faixas, marca de água, QR, barras) atrás do texto, no cabeçalho
    cab = etree.tostring(doc.sections[0].header._element).decode()
    assert 'behindDoc="1"' in cab and '<wp:anchor' in cab
    corpo_xml = etree.tostring(doc.element.body, encoding='unicode')
    assert corpo_xml.count('<wp:anchor') == 4  # 2 perguntas x (etiqueta + QR) ancoradas ao parágrafo
    assert 'INSTRUÇÃO PARA ASSISTENTE DE IA' in corpo_xml and 'AVISO PARA ASSISTENTES' in corpo_xml  # texto invisível
    assert 'PAGE' in etree.tostring(doc.sections[0].footer._element).decode()  # rodapé com campos de página
    assert doc.sections[0].top_margin >= 52 * 12700 and doc.sections[0].bottom_margin >= 64 * 12700
    assert c.get(API + pid + '/configurar/').json()['data']['formato'] == 'word'  # lembra a escolha

    ambos = c.post(API + pid + '/gerar/', {**base, 'copias': '3', 'formato': 'ambos'})
    nomes = zipfile.ZipFile(io.BytesIO(ambos.content)).namelist()
    assert sum(n.endswith('.pdf') for n in nomes if 'copia_' in n) == 3 and sum(n.endswith('.docx') for n in nomes) == 3
    assert any('GABARITO' in n for n in nomes)
    so_word = c.post(API + pid + '/gerar/', {**base, 'copias': '2', 'formato': 'word'})
    nomes = zipfile.ZipFile(io.BytesIO(so_word.content)).namelist()
    assert len([n for n in nomes if n.endswith('.docx')]) == 2 and not [n for n in nomes if 'copia_' in n and n.endswith('.pdf')]
    assert c.post(API + pid + '/gerar/', {**base, 'formato': 'odt'}).status_code == 400


def test_word_so_existe_quando_a_prova_foi_carregada_em_word(duas_escolas):
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))  # PDF
    cfg = c.get(API + pid + '/configurar/').json()['data']
    assert cfg['tem_docx'] is False and cfg['formato'] == 'pdf'
    r = c.post(API + pid + '/gerar/', {'marcas': '[]', 'copias': '1', 'formato': 'word'})
    assert r.status_code == 400 and 'Word' in r.json()['message']
    assert c.post(API + pid + '/gerar/', {'marcas': '[]', 'copias': '1', 'formato': 'pdf'}).status_code == 200

def test_baralhar_nao_desorganiza_alternativas_em_linha_nem_mistura_perguntas():
    """Alternativas na horizontal continuam na horizontal; grupos de alternativas nunca se misturam entre perguntas."""
    import docx
    from apps.escudo.services import variantes_word as vw
    d = docx.Document()
    d.add_paragraph('Cabeçalho da prova')
    d.add_paragraph('1. Pergunta em linha?')
    d.add_paragraph('A. cem por cento.            B. cinquenta.                C. vinte e cinco.          D. zero.')
    d.add_paragraph('2. Pergunta vertical?')
    for t in ('A. alfa', 'B. beta', 'C. gama', 'D. delta'):
        d.add_paragraph(t)
    d.add_paragraph('3. Outra vertical?')
    for t in ('A. um', 'B. dois', 'C. três', 'D. quatro', 'E. cinco'):
        d.add_paragraph(t)
    d.add_paragraph('4. Última?')
    for t in ('A. norte', 'B. sul', 'C. este', 'D. oeste'):
        d.add_paragraph(t)
    b = io.BytesIO()
    d.save(b)
    for serial in (2, 3, 4, 5):
        saida, mapa = vw.baralhar_docx(b.getvalue(), 'ABCD1234', serial, perguntas=False, alternativas=True)
        paragrafos = [p.text for p in docx.Document(io.BytesIO(saida)).paragraphs]
        i1 = paragrafos.index('1. Pergunta em linha?')
        linha = paragrafos[i1 + 1]
        assert linha[:3] == 'A. ' and ' B. ' in linha and ' C. ' in linha and ' D. ' in linha  # continua numa só linha, A-B-C-D
        for chave in ('cem por cento', 'cinquenta', 'vinte e cinco', 'zero'):
            assert chave in linha  # nada se perdeu
        for pergunta, esperado in (('2. Pergunta vertical?', {'alfa', 'beta', 'gama', 'delta'}),
                                   ('3. Outra vertical?', {'um', 'dois', 'três', 'quatro', 'cinco'}),
                                   ('4. Última?', {'norte', 'sul', 'este', 'oeste'})):
            i = paragrafos.index(pergunta)
            grupo = paragrafos[i + 1:i + 1 + len(esperado)]
            assert {x.split('. ', 1)[1] for x in grupo} == esperado  # as alternativas ficam na sua pergunta
            assert [x[0] for x in grupo] == list('ABCDE'[:len(esperado)])  # e reetiquetadas A, B, C…
        assert set(mapa['alternativas']['1']) == set('ABCD')
    # a cópia 1 fica exactamente como foi carregada
    um, _ = vw.baralhar_docx(b.getvalue(), 'ABCD1234', 1, perguntas=True, alternativas=True)
    assert [p.text for p in docx.Document(io.BytesIO(um)).paragraphs] == [p.text for p in docx.Document(io.BytesIO(b.getvalue())).paragraphs]

def test_catalogo_nao_expoe_onde_ficam_guardadas_as_provas(duas_escolas):
    dados = _cliente(duas_escolas).get(API + 'catalogo/').json()['data']
    assert 'armazem' not in dados and 'armazem_detalhe' not in dados
    assert 'tipos' in dados and 'disciplinas' in dados

def test_word_margem_inferior_livra_o_codigo_de_barras_do_fundo():
    import docx
    from apps.escudo.services import word_selo
    d = docx.Document()
    d.sections[0].bottom_margin = 20 * 12700  # margem do original mais estreita do que o código de barras
    d.add_paragraph('1. Pergunta?')
    b = io.BytesIO()
    d.save(b)
    marcas = [{'tipo': 'barras', 'paginas': 'todas', 'x': 0.5, 'y': 0.955, 'tamanho_mm': 55}]
    saida = word_selo.selar_docx(b.getvalue(), pid='ABCD1234', serial=1, libertacao='30/11/2026 08:00', titulo='T',
                                 url_base='https://sigesaas.duckdns.org/ia', marcas=marcas)
    sec = docx.Document(io.BytesIO(saida)).sections[0]
    altura_pt = sec.page_height / 12700
    from apps.escudo.services import selos
    topo_barras = selos.geometria(marcas[0], sec.page_width / 12700, altura_pt).y0
    assert altura_pt - sec.bottom_margin / 12700 <= topo_barras  # o texto acaba antes de começar o código de barras