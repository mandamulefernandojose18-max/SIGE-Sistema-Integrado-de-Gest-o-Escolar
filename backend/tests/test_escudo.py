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
    # marca de água e QR de fundo ficam atrás do texto (cabeçalho); faixas e laterais, só nas margens, à frente em cada página
    assert 'behindDoc="1"' in cab and '<wp:anchor' in cab
    a_frente = True
    corpo_xml = etree.tostring(doc.element.body, encoding='unicode')
    assert corpo_xml.count('<wp:anchor') == (7 if a_frente else 6) # 2 perguntas x (etiqueta + QR) + barras da 1.a pagina + QR lateral da pagina; parágrafo
    assert 'INSTRUÇÃO PARA ASSISTENTE DE IA' in corpo_xml and 'AVISO PARA ASSISTENTES' in corpo_xml  # texto invisível
    assert 'PAGE' in etree.tostring(doc.sections[0].footer._element).decode()  # rodapé com campos de página
    assert doc.sections[0].top_margin == 72 * 12700 and doc.sections[0].bottom_margin == 72 * 12700  # margens do original: a paginação não muda
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

def test_word_nao_muda_margens_nem_paginacao_e_faixas_cabem_nas_margens():
    import docx
    from apps.escudo.services import word_selo
    d = docx.Document()
    sec = d.sections[0]
    sec.top_margin, sec.bottom_margin = 32 * 12700, 40 * 12700  # margens estreitas, como a de provas reais
    d.add_paragraph('1. Pergunta?')
    b = io.BytesIO()
    d.save(b)
    marcas = [{'tipo': 'barras', 'paginas': 'todas', 'x': 0.5, 'y': 0.955, 'tamanho_mm': 55}]
    saida = word_selo.selar_docx(b.getvalue(), pid='ABCD1234', serial=1, libertacao='30/11/2026 08:00', titulo='T',
                                 url_base='https://sigesaas.duckdns.org/ia', marcas=marcas)
    novo = docx.Document(io.BytesIO(saida)).sections[0]
    assert (novo.top_margin, novo.bottom_margin) == (32 * 12700, 40 * 12700)  # nada é alargado
    assert (novo.left_margin, novo.right_margin, novo.page_width, novo.page_height) == (sec.left_margin, sec.right_margin, sec.page_width, sec.page_height)


def test_faixa_de_aviso_do_pdf_continua_igual_e_a_do_word_adapta_se_as_margens():
    import pymupdf
    from apps.escudo.services import selos
    em_branco = pymupdf.open()
    em_branco.new_page(width=612, height=792)
    base = em_branco.tobytes()

    def altura_da_faixa(limite):
        pdf = selos.selar(base, [], url_base='https://sigesaas.duckdns.org/ia', pid='ABCD1234', serial=1, libertacao='30/11/2026 08:00',
                          aviso_foto=True, aviso_visivel=False, aviso_ia=False, limite_faixa=limite)
        with pymupdf.open(stream=pdf, filetype='pdf') as d:
            pix = d[0].get_pixmap(dpi=72, alpha=False)
        # linhas do topo que têm o cinzento da faixa (0.93 -> 237)
        return sum(1 for y in range(pix.height // 2) if pix.pixel(2, y)[0] == 237)
    assert altura_da_faixa(None) > 32 >= altura_da_faixa((32, 40)) > 0  # PDF: faixa normal; Word: cabe nos 32 pt da margem  # Word: cabe na margem superior que a prova já tem

def test_word_preserva_cabecalho_rodape_e_nao_activa_primeira_pagina_diferente():
    import docx
    from apps.escudo.services import word_selo
    d = docx.Document()
    d.sections[0].header.paragraphs[0].text = 'Cabeçalho original'
    d.sections[0].footer.paragraphs[0].text = 'Rodapé original'
    d.add_paragraph('1. Pergunta?')
    d.add_section()  # 2.ª secção herda o cabeçalho e o rodapé da 1.ª
    d.add_paragraph('2. Outra?')
    b = io.BytesIO()
    d.save(b)
    marcas = [{'tipo': 'barras', 'paginas': 'primeira', 'x': 0.5, 'y': 0.91, 'tamanho_mm': 50}]  # as marcas por omissão
    saida = word_selo.selar_docx(b.getvalue(), pid='ABCD1234', serial=1, libertacao='30/11/2026 08:00', titulo='T',
                                 url_base='https://sigesaas.duckdns.org/ia', marcas=marcas)
    novo = docx.Document(io.BytesIO(saida))
    s0, s1 = novo.sections
    assert s0.different_first_page_header_footer is False and s1.different_first_page_header_footer is False
    assert s0.header.paragraphs[0].text == 'Cabeçalho original'
    assert 'Rodapé original' in [p.text for p in s0.footer.paragraphs]
    assert s1.header.is_linked_to_previous and s1.footer.is_linked_to_previous  # continuam a herdar: nada foi duplicado
    from lxml import etree
    primeiro = etree.tostring(novo.paragraphs[0]._p, encoding='unicode')
    assert '<wp:anchor' in primeiro  # a marca «só na primeira página» vai no corpo, ancorada ao primeiro parágrafo


def test_word_com_paginacao_real_poe_qr_laterais_e_barras_pagina_a_pagina():
    import docx
    import pymupdf
    from lxml import etree
    from apps.escudo.services import selos, word_selo
    textos = ['Primeira pergunta sobre equacoes lineares', 'Segunda pergunta sobre geometria plana']
    d = docx.Document()
    for t in textos:
        d.add_paragraph(t)
    b = io.BytesIO()
    d.save(b)
    layout = pymupdf.open()
    for t in textos:
        layout.new_page(width=595, height=842).insert_text((72, 100), t)
    pdf_layout = layout.tobytes()
    marcas = [{'tipo': 'barras', 'paginas': 'ultima', 'x': 0.5, 'y': 0.91, 'tamanho_mm': 50}]

    def ancoras_de(qr_pagina):
        saida = word_selo.selar_docx(b.getvalue(), pid='ABCD1234', serial=1, libertacao='30/11/2026 08:00', titulo='T',
                                     url_base='https://sigesaas.duckdns.org/ia', marcas=marcas, qr_pagina=qr_pagina,
                                     pdf_layout=pdf_layout, aviso_foto=False, qr_marca_agua=False)
        novo = docx.Document(io.BytesIO(saida))
        return [etree.tostring(p._p, encoding='unicode').count('<wp:anchor') for p in novo.paragraphs[:2]]

    assert ancoras_de(0) == [0, 1]       # sem QR lateral: só o código de barras, na última página
    assert ancoras_de(1) == [1, 2]       # 1 QR por página (+ barras na última)
    assert ancoras_de(3) == [3, 4]       # a escolha do número vale para cada página
    assert selos.contar_qr_pagina(True) == 1 and selos.contar_qr_pagina('on') == 1 and selos.contar_qr_pagina(99) == selos.MAX_QR_PAGINA
    assert selos.contar_qr_pagina(None) == 0 and selos.contar_qr_pagina('x') == 0

# ----------------------------------------------------------------- Guião (IA do SIGE)
GUIAO_FALSO = {
    'questoes': [
        {'numero': '1', 'enunciado': 'Resolva $x^2-5x+6=0$.', 'tipo': 'escolha_multipla',
         'passos': [{'descricao': 'Aplica-se a fórmula resolvente', 'equacao': r'x=\frac{-b\pm\sqrt{b^{2}-4ac}}{2a}'},
                    {'descricao': 'Substituem-se $a=1$, $b=-5$ e $c=6$', 'equacao': r'x=\frac{5\pm\sqrt{25-24}}{2}'},
                    {'descricao': 'Calculam-se as duas raízes', 'equacao': r'x_{1}=3 \quad\text{ou}\quad x_{2}=2'}],
         'resposta_final': r'$x\in\{2,3\}$', 'opcao_correcta': 'B', 'texto_opcao_correcta': '2 e 3',
         'justificacao_opcao': 'As outras alternativas não verificam a equação.', 'confianca': 'alta', 'observacao': ''},
        {'numero': '2', 'enunciado': 'Calcule $\\int_0^1 x\\,dx$.', 'tipo': 'calculo',
         'passos': [{'descricao': 'Primitiva de $x$', 'equacao': r'\int_0^1 x\,dx=\left[\frac{x^{2}}{2}\right]_0^1'},
                    {'descricao': 'Aplica-se a regra de Barrow', 'equacao': r'=\frac{1}{2}-0=\frac{1}{2}'}],
         'resposta_final': r'$\frac{1}{2}$', 'opcao_correcta': '', 'texto_opcao_correcta': '', 'justificacao_opcao': '',
         'confianca': 'baixa', 'observacao': 'O limite superior está pouco legível.'},
    ],
    'observacoes_gerais': 'Resolução de teste.',
}


@pytest.fixture
def ia_falsa(monkeypatch):
    from apps.escudo.services import guiao_job, ia_sige
    monkeypatch.setattr(ia_sige, 'disponivel', lambda: True)
    monkeypatch.setattr(guiao_job, 'SINCRONO', True)
    chamadas = []

    def resolver(pdf, titulo='', disciplina='', classe=''):
        chamadas.append((pdf[:5], titulo))
        return {'dados': GUIAO_FALSO, 'uso': {'modelo': 'claude-opus-5-5', 'entrada': 3000, 'saida': 9000, 'custo_usd': 0.192}}
    monkeypatch.setattr(ia_sige, 'resolver_prova', resolver)
    return chamadas


def test_latex_para_equacoes_nativas_em_duas_dimensoes():
    from lxml import etree
    from apps.escudo.services.latex_omml import latex_para_omml
    casos = {
        r'x=\frac{-b\pm\sqrt{b^2-4ac}}{2a}': {'f', 'rad', 'sSup', 'num', 'den'},
        r'\int_0^1 x^2\,dx=\frac{1}{3}': {'nary', 'f', 'sSup'},
        r'\sum_{i=1}^{n} i=\frac{n(n+1)}{2}': {'nary', 'f'},
        r'\lim_{x\to 0}\frac{\sin x}{x}=1': {'limLow', 'f'},
        r'\begin{cases}x+y=3\\x-y=1\end{cases}': {'d', 'eqArr'},
        r'\vec{F}=m\vec{a}': {'acc'},
        r'\left(\frac{a}{b}\right)^{2}': {'d', 'f', 'sSup'},
        r'\begin{pmatrix}1&2\\3&4\end{pmatrix}': {'m', 'mr'},
        r'\sqrt[3]{27}=3': {'rad', 'deg'},
        r'v=3,5\ \text{m/s}': {'nor'},
    }
    for latex, esperado in casos.items():
        tags = {t.tag.split('}')[1] for t in etree.fromstring(latex_para_omml(latex)).iter() if isinstance(t.tag, str)}
        assert esperado <= tags, (latex, esperado - tags)
    assert latex_para_omml('') == '' and latex_para_omml('$$') == ''
    texto = ''.join(etree.fromstring(latex_para_omml(r'a \neq b \leq \pi')).itertext())
    assert '≠' in texto and '≤' in texto and 'π' in texto and '\\' not in texto


def test_guiao_em_word_tem_equacoes_nativas_passos_e_opcao_correcta():
    import docx
    from lxml import etree
    from apps.escudo.services import guiao
    saida = guiao.construir_docx(GUIAO_FALSO, '2.ª ACS de Matemática', 'Matemática', '11.ª Classe', 'ABCD1234')
    d = docx.Document(io.BytesIO(saida))
    xml = etree.tostring(d.element.body, encoding='unicode')
    assert xml.count('<m:oMathPara') >= 5 and '<m:f>' in xml and '<m:rad>' in xml and '<m:nary>' in xml  # equações nativas, não texto linear
    assert '\\frac' not in xml and '\\sqrt' not in xml  # nenhum LaTeX cru no documento
    texto = '\n'.join(p.text for p in d.paragraphs)
    assert 'Questão 1' in texto and 'Questão 2' in texto and 'Opção correcta: B) 2 e 3' in texto
    assert '1. Aplica-se a fórmula resolvente' in texto and '3. Calculam-se as duas raízes' in texto
    assert 'Atenção: O limite superior' in texto  # confiança baixa avisa o professor
    assert 'reservado ao professor' in texto
    assert 'Times New Roman' in xml or d.styles['Normal'].font.name == 'Times New Roman'


def test_guiao_sem_chave_da_ia_diz_porque_nao_gera(duas_escolas, monkeypatch):
    from apps.escudo.services import ia_sige
    monkeypatch.setattr(ia_sige, 'disponivel', lambda: False)
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))
    e = c.get(API + pid + '/guiao/').json()['data']
    assert e['disponivel'] is False and e['estado'] == 'nenhum' and e['pronto'] is False
    r = c.post(API + pid + '/guiao/gerar/')
    assert r.status_code == 503 and 'chave da IA' in r.json()['message']


def test_guiao_fluxo_completo_gerar_rever_corrigir_e_sair_nos_dois_formatos(duas_escolas, ia_falsa, conversor_falso):
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))
    antes = c.post(API + pid + '/gerar/', {'marcas': '[]', 'copias': '1', 'guiao': 'com'})
    assert antes.status_code == 400 and 'Guião ainda não está pronto' in antes.json()['message']  # nada sai sem Guião gerado

    r = c.post(API + pid + '/guiao/gerar/')
    assert r.status_code == 202, r.content
    e = c.get(API + pid + '/guiao/').json()['data']
    assert e['estado'] == 'pronto' and e['pronto'] and e['custo_usd'] == 0.192 and e['modelo']
    assert [q['numero'] for q in e['questoes']] == ['1', '2'] and e['questoes'][0]['opcao_correcta'] == 'B'
    assert e['questoes'][1]['confianca'] == 'baixa' and e['geracoes_24h'] == 1
    assert ia_falsa and ia_falsa[0][0] == b'%PDF-'  # a IA recebe o PDF da prova

    corr = c.post(API + pid + '/guiao/corrigir/', {'numero': '1', 'opcao_correcta': 'C'})
    assert corr.status_code == 200 and corr.json()['data']['questoes'][0]['opcao_correcta'] == 'C' and corr.json()['data']['revisto']
    assert c.post(API + pid + '/guiao/corrigir/', {'numero': '1', 'opcao_correcta': 'Z'}).status_code == 400
    assert c.post(API + pid + '/guiao/corrigir/', {'numero': '99', 'opcao_correcta': 'A'}).status_code == 400

    zipado = c.post(API + pid + '/gerar/', {'marcas': '[]', 'copias': '1', 'guiao': 'com', 'formato': 'pdf'})
    assert zipado.status_code == 200 and zipado['Content-Type'] == 'application/zip'
    nomes = zipfile.ZipFile(io.BytesIO(zipado.content)).namelist()
    assert any('_copia_001.pdf' in n for n in nomes)  # a prova, em PDF
    assert any(n.endswith('GUIAO_so_professor.pdf') for n in nomes) and any(n.endswith('GUIAO_so_professor.docx') for n in nomes)  # Guião: PDF e Word
    sem = c.post(API + pid + '/gerar/', {'marcas': '[]', 'copias': '1', 'guiao': 'sem'})
    assert sem['Content-Type'] == 'application/pdf'  # «Sem Guião»: sai só a prova, como antes
    assert c.get(API + pid + '/configurar/').json()['data']['usa_guiao'] == 'sem'

    word = c.get(API + pid + '/guiao/descarregar/?formato=word')
    assert word.status_code == 200 and word['Content-Type'].endswith('wordprocessingml.document')
    pdf = c.get(API + pid + '/guiao/descarregar/')
    assert pdf.status_code == 200 and pdf.content.startswith(b'%PDF')
    import docx
    assert 'Opção correcta: C' in '\n'.join(p.text for p in docx.Document(io.BytesIO(word.content)).paragraphs)  # a correcção do professor vale

    p = ProvaEscudo.objects.get(codigo=pid)
    assert b'x^' not in bytes(p.pdf_cifrado) and 'guiao_cifrado' in p.config and 'Aplica-se' not in json.dumps(p.config)  # o guião fica cifrado


def test_guiao_erros_da_ia_e_limite_diario(duas_escolas, ia_falsa, monkeypatch):
    from apps.escudo.services import guiao_job, ia_sige
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))

    def falha(*a, **k):
        raise ia_sige.IAIndisponivel('A IA está com muitos pedidos neste momento. Tente de novo dentro de alguns minutos.')
    monkeypatch.setattr(ia_sige, 'resolver_prova', falha)
    c.post(API + pid + '/guiao/gerar/')
    e = c.get(API + pid + '/guiao/').json()['data']
    assert e['estado'] == 'erro' and 'muitos pedidos' in e['mensagem'] and e['pronto'] is False

    monkeypatch.setattr(guiao_job, 'LIMITE_24H', 2)
    c.post(API + pid + '/guiao/gerar/')  # 2.ª tentativa do dia
    limite = c.post(API + pid + '/guiao/gerar/')
    assert limite.status_code == 429 and 'Limite' in limite.json()['message']


def test_guiao_respeita_a_escola_e_a_autoria(duas_escolas, ia_falsa):
    from apps.accounts.models import Usuario
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))
    c.post(API + pid + '/guiao/gerar/')
    Usuario.objects.create_user(email='admin.fb@sige.mz', password='PassFb123!', role='ADMIN_ESCOLA', escola=duas_escolas[1])
    b = _cliente_de('admin.fb@sige.mz', 'PassFb123!')
    for sufixo in ('guiao/', 'guiao/descarregar/'):
        assert b.get(API + pid + '/' + sufixo).status_code == 404
    assert b.post(API + pid + '/guiao/gerar/').status_code == 404
    assert b.post(API + pid + '/guiao/corrigir/', {'numero': '1', 'opcao_correcta': 'A'}).status_code == 404
    assert APIClient().get(API + pid + '/guiao/').status_code == 401
    assert 'guiao' not in APIClient().get(f'/ia/v/{pid}/prova.pdf').content.decode().lower()  # nunca público

def test_equacao_que_continua_a_anterior_leva_marca_para_nao_aparecer_um_placeholder():
    from apps.escudo.services.latex_omml import latex_para_omml
    assert '\u200b' in latex_para_omml(r'=(2^{3}+2)-(0^{3}+0)=10')  # sem isto o LibreOffice desenha «¿» à esquerda do «=»
    assert '\u200b' not in latex_para_omml(r'x=\frac{1}{2}')

# ----------------------------------------------------------------- IA do SIGE: fornecedores (gratuitos e pagos)
def _limpar_chaves(monkeypatch):
    for v in ('GEMINI_API_KEY', 'GROQ_API_KEY', 'OPENROUTER_API_KEY', 'SIGE_IA_CHAVE', 'SIGE_IA_URL', 'ANTHROPIC_API_KEY',
              'ANTHROPIC_AUTH_TOKEN', 'SIGE_IA_PROVEDOR', 'SIGE_IA_MODELO'):
        monkeypatch.delenv(v, raising=False)


def test_ia_escolhe_o_fornecedor_gratuito_antes_do_pago(monkeypatch):
    from apps.escudo.services import ia_sige
    _limpar_chaves(monkeypatch)
    assert ia_sige.provedor() is None and not ia_sige.disponivel() and not ia_sige.gratuito()
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-ant-xxxxxxxxxxxxxxxxxxxxxxxx')
    assert ia_sige.provedor() == 'anthropic' and not ia_sige.gratuito() and ia_sige.modelo() == 'claude-opus-5-5'
    monkeypatch.setenv('GROQ_API_KEY', 'gsk_x')
    assert ia_sige.provedor() == 'groq' and ia_sige.gratuito()  # nunca gasta dinheiro se houver um serviço gratuito
    monkeypatch.setenv('GEMINI_API_KEY', 'AIzaxxxxxxxx')
    assert ia_sige.provedor() == 'gemini' and ia_sige.gratuito() and 'Google' in ia_sige.aviso_privacidade()
    monkeypatch.setenv('SIGE_IA_PROVEDOR', 'anthropic')
    assert ia_sige.provedor() == 'anthropic'  # a escolha explícita do administrador manda
    monkeypatch.setenv('SIGE_IA_PROVEDOR', 'groq')
    monkeypatch.setenv('SIGE_IA_MODELO', 'outro-modelo')
    assert ia_sige.provedor() == 'groq' and ia_sige.modelo() == 'outro-modelo'
    assert ia_sige.custo_estimado(1000, 1000) == 0.0
    _limpar_chaves(monkeypatch)
    monkeypatch.setenv('SIGE_IA_CHAVE', 'k')
    assert ia_sige.provedor() is None  # serviço genérico precisa também de SIGE_IA_URL
    monkeypatch.setenv('SIGE_IA_URL', 'http://localhost:11434/v1')
    assert ia_sige.provedor() == 'openai'


def test_ia_extrai_json_de_respostas_sujas_e_completa_campos():
    from apps.escudo.services import ia_sige
    assert ia_sige._extrair_json('```json\n{"questoes": []}\n```') == {'questoes': []}
    assert ia_sige._extrair_json('Aqui está: {"questoes": [{"numero": 1}]} fim') == {'questoes': [{'numero': 1}]}
    with pytest.raises(ia_sige.IAIndisponivel):
        ia_sige._extrair_json('sem json nenhum')
    norm = ia_sige._normalizar({'questoes': [{'numero': 1, 'passos': [{'descricao': 'a'}], 'opcao_correcta': 'b', 'tipo': 'xpto'}]})
    q = norm['questoes'][0]
    assert q['numero'] == '1' and q['opcao_correcta'] == 'B' and q['tipo'] == 'aberta' and q['confianca'] == 'media'
    assert q['passos'] == [{'descricao': 'a', 'equacao': ''}] and q['resposta_final'] == ''
    with pytest.raises(ia_sige.IAIndisponivel):
        ia_sige._normalizar({'questoes': []})


class _RespostaHttp:
    def __init__(self, corpo):
        self._corpo = json.dumps(corpo).encode()

    def read(self):
        return self._corpo

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _pdf_de_paginas(n):
    from reportlab.pdfgen import canvas
    b = io.BytesIO()
    c = canvas.Canvas(b)
    for i in range(n):
        c.drawString(72, 700, f'{i + 1}. Pergunta numero {i + 1}?')
        c.showPage()
    c.save()
    return b.getvalue()


def test_ia_gratuita_envia_paginas_como_imagens_em_lotes_e_junta_as_questoes(monkeypatch):
    import urllib.request
    from apps.escudo.services import ia_sige
    _limpar_chaves(monkeypatch)
    monkeypatch.setenv('GROQ_API_KEY', 'gsk_teste')  # o Groq recebe 2 páginas por pedido
    pedidos = []

    def falso(req, timeout=None):
        corpo = json.loads(req.data.decode())
        pedidos.append((req.full_url, req.headers.get('Authorization'), corpo))
        imagens = [p for m in corpo['messages'] for p in (m['content'] if isinstance(m['content'], list) else []) if p['type'] == 'image_url']
        n = len(pedidos)
        qs = [{'numero': str(n), 'enunciado': 'E', 'tipo': 'calculo', 'passos': [{'descricao': 'p', 'equacao': 'x=1'}],
               'resposta_final': '1', 'opcao_correcta': '', 'texto_opcao_correcta': '', 'justificacao_opcao': '', 'confianca': 'alta', 'observacao': ''}]
        if n == 2:
            qs.append({**qs[0], 'numero': '1'})  # repetida: só entra uma vez
        return _RespostaHttp({'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps({'questoes': qs, 'observacoes_gerais': f'o{n}'})}}],
                              'usage': {'prompt_tokens': 100 * len(imagens), 'completion_tokens': 50}})
    monkeypatch.setattr(urllib.request, 'urlopen', falso)
    r = ia_sige.resolver_prova(_pdf_de_paginas(3), 'Teste', 'Matemática', '11.ª Classe')
    assert len(pedidos) == 2  # 3 páginas, 2 por pedido
    assert pedidos[0][0] == 'https://api.groq.com/openai/v1/chat/completions' and pedidos[0][1] == 'Bearer gsk_teste'
    msg = pedidos[0][2]['messages']
    assert msg[0]['role'] == 'system' and 'GUIÃO' in msg[0]['content'] and 'JSON' in msg[0]['content']
    imgs = [p for p in msg[1]['content'] if p['type'] == 'image_url']
    assert len(imgs) == 2 and imgs[0]['image_url']['url'].startswith('data:image/png;base64,')
    assert [q['numero'] for q in r['dados']['questoes']] == ['1', '2']  # sem duplicados
    assert r['uso']['gratuito'] is True and r['uso']['custo_usd'] == 0.0 and r['uso']['provedor'] == 'groq'
    assert r['uso']['entrada'] == 300 and r['dados']['observacoes_gerais'] == 'o1 o2'


def test_ia_gratuita_espera_e_repete_no_limite_e_explica_os_erros(monkeypatch):
    import urllib.error
    import urllib.request
    from apps.escudo.services import ia_sige
    _limpar_chaves(monkeypatch)
    monkeypatch.setenv('GEMINI_API_KEY', 'AIzaTeste')
    monkeypatch.setattr(ia_sige.time, 'sleep', lambda s: None)
    estados = iter([429, 200])
    quest = {'questoes': [{'numero': '1', 'enunciado': 'E', 'tipo': 'aberta', 'passos': [], 'resposta_final': '', 'opcao_correcta': '',
                           'texto_opcao_correcta': '', 'justificacao_opcao': '', 'confianca': 'alta', 'observacao': ''}], 'observacoes_gerais': ''}

    def com_limite(req, timeout=None):
        if next(estados) == 429:
            raise urllib.error.HTTPError(req.full_url, 429, 'too many', {}, io.BytesIO(b'{}'))
        return _RespostaHttp({'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(quest)}}]})
    monkeypatch.setattr(urllib.request, 'urlopen', com_limite)
    r = ia_sige.resolver_prova(_pdf_de_paginas(1))
    assert len(r['dados']['questoes']) == 1 and r['uso']['provedor'] == 'gemini'  # esperou e repetiu

    def recusada(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, 'no', {}, io.BytesIO(b'{}'))
    monkeypatch.setattr(urllib.request, 'urlopen', recusada)
    with pytest.raises(ia_sige.IAIndisponivel, match='chave da IA foi recusada'):
        ia_sige.resolver_prova(_pdf_de_paginas(1))

    def cortada(req, timeout=None):
        return _RespostaHttp({'choices': [{'finish_reason': 'length', 'message': {'content': '{'}}]})
    monkeypatch.setattr(urllib.request, 'urlopen', cortada)
    with pytest.raises(ia_sige.IAIndisponivel, match='cortada'):
        ia_sige.resolver_prova(_pdf_de_paginas(1))
    monkeypatch.delenv('GEMINI_API_KEY')
    with pytest.raises(ia_sige.IAIndisponivel, match='activada'):
        ia_sige.resolver_prova(_pdf_de_paginas(1))

def test_editar_prova_guardada_mantem_codigo_copias_e_leituras(duas_escolas):
    from apps.accounts.models import Usuario
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))
    form = {'marcas': '[]', 'aviso_foto': 'on', 'copias': '3', 'pagina': '1', 'tamanho_qr_fundo': '90', 'tamanho_qr_pagina': '25', 'qr_pagina': '2'}
    assert c.post(API + pid + '/gerar/', form).status_code == 200
    cfg = c.get(API + pid + '/configurar/').json()['data']
    assert cfg['tamanho_qr_fundo'] == 90 and cfg['tamanho_qr_pagina'] == 25 and cfg['qr_pagina'] == 2
    assert c.post(API + pid + '/editar/', {}).status_code == 400  # nada para alterar
    novo = _pdf()
    r = c.post(API + pid + '/editar/', {'titulo': 'Título corrigido', 'disciplina': 'Química', 'classe': '12.ª Classe',
                                         'prova': SimpleUploadedFile('n.pdf', novo), 'gabarito': SimpleUploadedFile('g.pdf', novo)}, format='multipart')
    assert r.status_code == 200, r.content
    p = ProvaEscudo.objects.get(codigo=pid)
    assert p.titulo == 'Título corrigido' and p.disciplina == 'Química' and p.copias == 3 and p.gabarito_cifrado
    assert b'%PDF' not in bytes(p.pdf_cifrado) and p.config['tamanho_qr_fundo'] == 90  # continua cifrada; opções mantidas
    assert c.post(API + pid + '/editar/', {'remover_gabarito': 'on'}).status_code == 200
    assert ProvaEscudo.objects.get(codigo=pid).gabarito_cifrado is None
    assert c.post(API + pid + '/editar/', {'prova': SimpleUploadedFile('x.txt', b'texto')}, format='multipart').status_code == 400
    # outra escola não edita; o professor que não é dono também não
    Usuario.objects.create_user(email='admin.fc@sige.mz', password='PassFc123!', role='ADMIN_ESCOLA', escola=duas_escolas[1])
    assert _cliente_de('admin.fc@sige.mz', 'PassFc123!').post(API + pid + '/editar/', {'titulo': 'x'}).status_code == 404
    assert c.post(API + pid + '/apagar/').status_code == 200 and not ProvaEscudo.objects.filter(codigo=pid).exists()


def test_tamanho_do_qr_de_fundo_e_do_lateral():
    import pymupdf
    from apps.escudo.services import selos
    assert selos.limitar_lado_qr_fundo(None) is None and selos.limitar_lado_qr_fundo(5) == 40 and selos.limitar_lado_qr_fundo(999) == 200
    assert selos.limitar_lado_qr_pagina('x') == selos.LADO_QR_PAGINA_MM and selos.limitar_lado_qr_pagina(1) == 10
    base = pymupdf.open()
    base.new_page(width=595, height=842)
    pdf = base.tobytes()
    pag = pymupdf.open(stream=pdf, filetype='pdf')[0]
    pequenos = selos.posicoes_qr_pagina(pag, [], 'ABCD1234', 1, 0, 2, set(), 12)
    grandes = selos.posicoes_qr_pagina(pag, [], 'ABCD1234', 1, 0, 2, set(), 40)
    assert len(pequenos) == len(grandes) == 2 and round(pequenos[0].width / selos.MM) == 12 and round(grandes[0].width / selos.MM) == 40
    kw = dict(url_base='https://sigesaas.duckdns.org/ia', pid='ABCD1234', serial=1, libertacao='x', aviso_ia=False, aviso_visivel=False,
              qr_marca_agua=True, zonas_marca_agua=[(100, 100, 300, 300)])
    def tinta(mm):
        with pymupdf.open(stream=selos.selar(pdf, [], tamanho_qr_fundo=mm, **kw), filetype='pdf') as d:
            pix = d[0].get_pixmap(dpi=40)
        xs = [x for x in range(pix.width) for y in range(pix.height) if sum(pix.pixel(x, y)[:3]) < 740]
        return max(xs) - min(xs)
    assert tinta(150) > tinta(50) * 2  # o tamanho pedido manda no QR de fundo


def test_so_o_super_admin_ve_provas_de_outras_escolas(duas_escolas):
    from types import SimpleNamespace
    from apps.accounts.models import Usuario
    from apps.escudo import views
    a, b = duas_escolas
    pid = _pid(_criar(_cliente(duas_escolas)))
    p = ProvaEscudo.objects.get(codigo=pid)
    prova = {'escola_id': p.escola_id, 'dono_id': p.criado_por_id}
    gestor_b = SimpleNamespace(role='ADMIN_ESCOLA', escola_id=b.id, id=999)
    sem_escola = SimpleNamespace(role='ADMIN_ESCOLA', escola_id=None, id=998)
    super_admin = SimpleNamespace(role='SUPERADMIN', escola_id=None, id=997)
    assert not views._visivel(gestor_b, prova) and not views._visivel(sem_escola, prova)
    assert not views._visivel(sem_escola, {'escola_id': None, 'dono_id': 1})  # None == None nunca dá acesso
    assert views._visivel(super_admin, prova)
    Usuario.objects.create_user(email='sa.x@sige.mz', password='PassSa123!', role='SUPERADMIN')
    sa = _cliente_de('sa.x@sige.mz', 'PassSa123!')
    assert sa.get(API + pid + '/').status_code == 200
    Usuario.objects.create_user(email='admin.fd@sige.mz', password='PassFd123!', role='ADMIN_ESCOLA', escola=b)
    estranho = _cliente_de('admin.fd@sige.mz', 'PassFd123!')
    for url in ('', 'configurar/', 'guiao/', 'guiao/descarregar/', 'pagina/1.png', 'gabarito-copias/'):
        assert estranho.get(API + pid + '/' + url).status_code == 404, url
    for url in ('editar/', 'apagar/', 'data/', 'libertar/', 'guiao/gerar/', 'gerar/', 'previa/'):
        assert estranho.post(API + pid + '/' + url, {'titulo': 'x'}).status_code == 404, url
    assert estranho.get(API + 'lista/').json()['data']['resumo']['total'] == 0
    assert ProvaEscudo.objects.get(codigo=pid).titulo == p.titulo


def test_leitura_no_embargo_pede_local_guarda_so_com_token_e_avisa_o_dono_por_email(duas_escolas, monkeypatch, settings):
    import re
    from django.core import mail
    from apps.escudo.services import alertas
    monkeypatch.setenv('EMAIL_HOST', 'smtp.exemplo.test')
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    monkeypatch.setattr(alertas, 'agendar', lambda *a, **k: None)  # o envio é testado a seguir, sem esperar
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))
    pag = APIClient().get(f'/ia/v/{pid}/1/q2', HTTP_USER_AGENT='Mozilla/5.0 (Linux; Android 14; SM-A546B) Chrome/120')
    assert pag.status_code == 200
    html = pag.content.decode()
    assert 'navigator.geolocation' in html and 'registada' in html  # aviso visível + pedido do navegador (recusável)
    token = re.search(r"t:'([^']+)'", html).group(1)
    local = f'/ia/v/{pid}/local/'
    ok = {'t': token, 'lat': -25.9653, 'lon': 32.5892, 'acc': 35}
    assert APIClient().post(local, {**ok, 't': 'falso'}, format='json').status_code == 400   # token forjado
    assert APIClient().post(local, {**ok, 'lat': 123}, format='json').status_code == 400     # coordenadas impossíveis
    outra = _pid(_criar(c))
    assert APIClient().post(f'/ia/v/{outra}/local/', ok, format='json').status_code == 400   # token de outra prova
    assert APIClient().post(local, ok, format='json').status_code == 204
    assert APIClient().post(local, {**ok, 'lat': 1.0}, format='json').status_code == 204      # 2.ª tentativa não altera
    l = LeituraEscudo.objects.get(prova__codigo=pid)
    assert round(l.latitude, 3) == -25.965 and l.precisao_m == 35
    assert alertas.enviar_aviso(pid) == 1 and len(mail.outbox) == 1
    corpo = mail.outbox[0].body
    assert 'openstreetmap.org' in corpo and pid + '-001' in corpo and 'aparelho:' in corpo
    assert not re.search(r'\b\d{1,3}(\.\d{1,3}){3}\b', corpo)  # nunca IPs
    assert mail.outbox[0].to == [ProvaEscudo.objects.get(codigo=pid).criado_por.email]
    APIClient().get(f'/ia/v/{pid}/1')
    assert alertas.enviar_aviso(pid) == -1 and len(mail.outbox) == 1   # no máximo 1 e-mail por janela
    # desligar os avisos
    assert c.post(API + pid + '/editar/', {'notificar_leituras': '0'}).status_code == 200
    LeituraEscudo.objects.filter(prova__codigo=pid).update(notificada=False)
    assert alertas.enviar_aviso(pid) == 0 and len(mail.outbox) == 1
    d = c.get(API + pid + '/').json()['data']
    assert d['avisos']['ativos'] is False and d['avisos']['email_activo'] is True
    assert d['leituras_lista'][-1]['latitude'] is not None


def test_sem_email_configurado_nao_avisa_e_depois_da_libertacao_nao_pede_local(duas_escolas, monkeypatch):
    from apps.escudo.services import alertas
    monkeypatch.delenv('EMAIL_HOST', raising=False)
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))
    APIClient().get(f'/ia/v/{pid}/1')
    assert alertas.email_activo() is False and alertas.enviar_aviso(pid) == 0
    ProvaEscudo.objects.filter(codigo=pid).update(libertacao=datetime(2020, 1, 1))
    html = APIClient().get(f'/ia/v/{pid}/1').content.decode()
    assert 'navigator.geolocation' not in html  # sem embargo, não se pede local


def test_email_dos_avisos_definido_no_sistema(duas_escolas, monkeypatch, settings):
    from django.core import mail
    from apps.escudo.services import alertas
    monkeypatch.setenv('EMAIL_HOST', 'smtp.exemplo.test')
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    monkeypatch.setattr(alertas, 'agendar', lambda *a, **k: None)
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))
    assert c.post(API + pid + '/editar/', {'email_avisos': 'isto nao e email'}).status_code == 400
    assert c.post(API + pid + '/editar/', {'email_avisos': 'direccao@escola.test'}).status_code == 200
    d = c.get(API + pid + '/').json()['data']['avisos']
    assert d['email'] == 'direccao@escola.test' and d['email_conta']
    APIClient().get(f'/ia/v/{pid}/1')
    assert alertas.enviar_aviso(pid) == 1 and mail.outbox[0].to == ['direccao@escola.test']
    assert c.post(API + pid + '/editar/', {'email_avisos': ''}).status_code == 200  # vazio: volta ao e-mail da conta
    assert c.get(API + pid + '/').json()['data']['avisos']['email'] == ''


def test_email_dos_avisos_definido_ao_carregar_a_prova(duas_escolas):
    c = _cliente(duas_escolas)
    assert _criar(c, email_avisos='nao-e-email').status_code == 400
    assert ProvaEscudo.objects.count() == 0  # nada fica guardado se o e-mail é inválido
    pid = _pid(_criar(c, email_avisos='prof.fisica@escola.test'))
    assert c.get(API + pid + '/').json()['data']['avisos']['email'] == 'prof.fisica@escola.test'


def test_leituras_novas_aparecem_no_painel_ate_o_professor_abrir_a_prova(duas_escolas):
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))
    assert c.get(API + 'lista/').json()['data']['resumo']['novas'] == 0
    APIClient().get(f'/ia/v/{pid}/1/q3')
    APIClient().get(f'/ia/v/{pid}/1')
    d = c.get(API + 'lista/').json()['data']
    assert d['resumo']['novas'] == 2 and d['provas'][0]['novas'] == 2
    assert c.get(API + pid + '/').json()['data']['novas_antes'] == 2  # abrir a prova mostra quantas eram novas
    d = c.get(API + 'lista/').json()['data']
    assert d['resumo']['novas'] == 0 and d['provas'][0]['novas'] == 0  # e passam a vistas
    ProvaEscudo.objects.filter(codigo=pid).update(libertacao=datetime(2020, 1, 1))
    APIClient().get(f'/ia/v/{pid}/1')  # depois do embargo já não é alerta
    assert c.get(API + 'lista/').json()['data']['resumo']['novas'] == 0


def test_armadilha_por_copia_no_pdf_e_no_word_e_verificacao_de_autoria(duas_escolas):
    import pymupdf
    from apps.escudo.services import selos, word_selo
    import docx
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))
    p1, p2 = selos.palavra_armadilha(f'{pid}-001'), selos.palavra_armadilha(f'{pid}-002')
    assert p1 != p2 and len(p1) == 6 and selos.palavra_armadilha(f'{pid}-001') == p1  # estável, e diferente por cópia
    form = {'marcas': '[]', 'aviso_foto': 'on', 'aviso_ia': 'on', 'copias': '1', 'pagina': '1'}

    def texto_pdf(extra):
        r = c.post(API + pid + '/gerar/', {**form, **extra})
        assert r.status_code == 200
        with pymupdf.open(stream=r.content, filetype='pdf') as d:
            return ' '.join(pg.get_text() for pg in d)
    assert p1 in texto_pdf({}) and 'termina a resposta' in texto_pdf({})      # ligada por omissão: na camada de texto e na marca de água
    assert p1 not in texto_pdf({'armadilha': '0'})                            # desligada: nada muda
    d = docx.Document()
    d.add_paragraph('1. Pergunta?')
    b = io.BytesIO()
    d.save(b)
    kw = dict(pid=pid, serial=1, libertacao='30/11/2026 08:00', titulo='T', url_base='https://sigesaas.duckdns.org/ia', marcas=[])
    com = word_selo.selar_docx(b.getvalue(), armadilha=True, **kw)
    sem = word_selo.selar_docx(b.getvalue(), armadilha=False, **kw)
    assert p1.encode() in __import__('zipfile').ZipFile(io.BytesIO(com)).read('word/document.xml')
    assert p1.encode() not in __import__('zipfile').ZipFile(io.BytesIO(sem)).read('word/document.xml')
    # verificação: a palavra (sem acentos/maiúsculas) denuncia a resposta; a cópia errada não
    r = c.post(API + pid + '/armadilha/', {'copia': '1', 'texto': f'... portanto x=3. {p1.upper()}'}).json()['data']
    assert r['encontrada'] and r['palavra'] == p1
    assert not c.post(API + pid + '/armadilha/', {'copia': '1', 'texto': 'x=3'}).json()['data']['encontrada']
    assert c.post(API + pid + '/armadilha/', {'copia': '9', 'texto': 'x'}).status_code == 400


def test_dados_da_sala_so_aparecem_na_janela_cifrados_e_com_leitura_registada(duas_escolas):
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))
    assert c.get(API + pid + '/').json()['data']['sala'] is None
    assert c.post(API + pid + '/sala/', {'texto': 'g = 9,8', 'inicio': '', 'minutos': '60'}).status_code == 400
    assert c.post(API + pid + '/sala/', {'texto': 'g = 9,8', 'inicio': _futuro(1), 'minutos': '5'}).status_code == 400
    dt_ini = datetime.now() + timedelta(days=1)
    r = c.post(API + pid + '/sala/', {'texto': 'Use g = 9,8 m/s² e R = 4 Ω', 'inicio': dt_ini.strftime('%Y-%m-%dT%H:%M'), 'minutos': '90'})
    assert r.status_code == 200, r.content
    cfg = ProvaEscudo.objects.get(codigo=pid).config
    assert 'sala_cifrado' in cfg and 'g = 9,8' not in json.dumps(cfg)  # nunca em claro
    antes = APIClient().get(f'/ia/v/{pid}/1').content.decode()
    assert 'g = 9,8' not in antes and 'abrem às' in antes                # fora da janela
    d = c.get(API + pid + '/').json()['data']['sala']
    assert d['estado'] == 'antes' and d['texto'].startswith('Use g') and d['minutos'] == 90
    # abre a janela: início no passado, fim no futuro
    from apps.escudo.services import tempo
    agora = tempo.agora()
    cfg['sala_janela'] = {'inicio': tempo.para_iso(agora - timedelta(minutes=5)), 'fim': tempo.para_iso(agora + timedelta(minutes=30))}
    ProvaEscudo.objects.filter(codigo=pid).update(config=cfg)
    dentro = APIClient().get(f'/ia/v/{pid}/1/q2').content.decode()
    assert 'Use g = 9,8' in dentro and 'Dados da sala' in dentro
    assert LeituraEscudo.objects.filter(prova__codigo=pid).count() == 2   # as duas aberturas ficaram registadas
    cfg['sala_janela'] = {'inicio': tempo.para_iso(agora - timedelta(hours=3)), 'fim': tempo.para_iso(agora - timedelta(hours=1))}
    ProvaEscudo.objects.filter(codigo=pid).update(config=cfg)
    assert 'Use g = 9,8' not in APIClient().get(f'/ia/v/{pid}/1').content.decode()  # depois de fechar, já não
    assert c.post(API + pid + '/sala/', {'texto': ''}).status_code == 200
    assert 'sala_cifrado' not in ProvaEscudo.objects.get(codigo=pid).config


def test_qr_automatico_procura_espaco_livre_e_o_de_fundo_respeita_a_posicao():
    import pymupdf
    from apps.escudo.services import selos
    # página cheia: texto por todo o lado excepto um quadrado em branco
    doc = pymupdf.open()
    pg = doc.new_page(width=595, height=842)
    for y in range(70, 800, 14):
        for x0, x1 in ((40, 200), (330, 560)):
            pg.insert_text((x0, y), 'texto da prova ' * 3, fontsize=9)
    pdf = doc.tobytes()
    pag = pymupdf.open(stream=pdf, filetype='pdf')[0]
    ocupados = selos._retangulos_ocupados(pag)
    achados = selos.posicoes_qr_pagina(pag, ocupados, 'ABCD1234', 1, 0, 2, set(), 20, 'auto')
    for r in achados:
        assert not any(r.intersects(o) for o in ocupados)  # nunca tapa conteúdo
    # modo «margens»: só esquerda/direita; legado «grade» continua a existir
    vazia = pymupdf.open(stream=pymupdf.open().tobytes() if False else pdf, filetype='pdf')[0]
    assert selos.limitar_modo_qr_pagina('xx') == 'auto' and selos.limitar_modo_qr_pagina(None, 'grade') == 'grade'
    livre = pymupdf.open(); livre.new_page(width=595, height=842)
    p2 = pymupdf.open(stream=livre.tobytes(), filetype='pdf')[0]
    m = selos.posicoes_qr_pagina(p2, [], 'ABCD1234', 2, 3, 2, set(), 20, 'margens')
    assert m and all(abs(r.x0 - 14) < 1 or abs(r.x1 - (595 - 14)) < 1 for r in m)
    # QR de fundo: posições fixas e validação
    assert selos.limitar_posicao_qr_fundo('xx') == 'auto' and selos.limitar_posicao_qr_fundo('canto_inf_dir') == 'canto_inf_dir'
    base = livre.tobytes()
    kw = dict(url_base='https://sigesaas.duckdns.org/ia', pid='ABCD1234', serial=1, libertacao='x', aviso_ia=False, aviso_visivel=False,
              qr_marca_agua=True, zonas_marca_agua=[(100, 100, 300, 300)], tamanho_qr_fundo=60)

    def centro_tinta(pos):
        with pymupdf.open(stream=selos.selar(base, [], posicao_qr_fundo=pos, **kw), filetype='pdf') as d:
            pix = d[0].get_pixmap(dpi=40)
        pts = [(x, y) for x in range(pix.width) for y in range(pix.height) if sum(pix.pixel(x, y)[:3]) < 740]
        return sum(p[0] for p in pts) / len(pts) / pix.width, sum(p[1] for p in pts) / len(pts) / pix.height
    esq, dir_ = centro_tinta('esquerda'), centro_tinta('direita')
    sup, inf = centro_tinta('canto_sup_esq'), centro_tinta('canto_inf_dir')
    assert esq[0] < 0.3 and dir_[0] > 0.7 and abs(esq[1] - 0.5) < 0.1
    assert sup[0] < 0.3 and sup[1] < 0.3 and inf[0] > 0.7 and inf[1] > 0.7
    assert abs(centro_tinta('centro')[0] - 0.5) < 0.1


def test_posicoes_do_qr_ficam_guardadas_na_configuracao(duas_escolas):
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))
    form = {'marcas': '[]', 'aviso_foto': 'on', 'copias': '2', 'pagina': '1', 'modo_qr_pagina': 'margens', 'posicao_qr_fundo': 'canto_sup_dir'}
    assert c.post(API + pid + '/gerar/', form).status_code == 200
    cfg = c.get(API + pid + '/configurar/').json()['data']
    assert cfg['modo_qr_pagina'] == 'margens' and cfg['posicao_qr_fundo'] == 'canto_sup_dir' and 'centro' in cfg['posicoes_qr_fundo']


def test_qr_automatico_fica_alinhado_igualmente_espacado_e_igual_em_todas_as_paginas():
    import pymupdf
    from apps.escudo.services import selos
    d = pymupdf.open()
    for _ in range(2):
        pg = d.new_page(width=595, height=842)
        y = 80
        while y < 760:
            pg.insert_text((50, y), 'Qual a solução da equação?', fontsize=10)
            for i in range(4):
                pg.insert_text((60 + i * 110, y + 16), f'{"ABCD"[i]}. {i}', fontsize=10)
            y += 42
    doc = pymupdf.open(stream=d.tobytes(), filetype='pdf')
    usadas, por_pagina = set(), []
    for pag in doc:
        por_pagina.append(selos.posicoes_qr_pagina(pag, selos._retangulos_ocupados(pag), 'ABCD1234', 1, pag.number, 4, usadas, 18, 'auto'))
    assert all(len(r) == 4 for r in por_pagina)
    for rects in por_pagina:
        assert len({round(r.x0) for r in rects}) == 1  # uma só coluna
        passos = [round(b.y0 - a.y0) for a, b in zip(rects, rects[1:])]
        assert max(passos) - min(passos) <= 12  # espaçamento praticamente igual
    assert round(por_pagina[0][0].x0) == round(por_pagina[1][0].x0)  # a mesma coluna em todas as páginas


def test_palavra_chave_da_armadilha_definida_pelo_professor(duas_escolas):
    from apps.escudo.services import selos
    assert selos.limpar_palavra_armadilha('  ') is None and selos.limpar_palavra_armadilha('Girassol') == 'Girassol'
    for mau in ('ab', 'duas palavras', 'abc123', 'x' * 21):
        with pytest.raises(ValueError):
            selos.limpar_palavra_armadilha(mau)
    auto1, auto2 = selos.palavra_armadilha('ABCD1234-001'), selos.palavra_armadilha('ABCD1234-002')
    assert auto1 != auto2  # automática: uma por cópia
    assert selos.palavra_armadilha('ABCD1234-001', 'Girassol') == selos.palavra_armadilha('ABCD1234-002', 'Girassol') == 'girassol'
    assert 'girassol' in selos.texto_ia('x', 'ABCD1234-001', 'm', 'Girassol') and selos.contem_armadilha('c', 'Resposta ... GIRASSOL', 'Girassol')
    assert selos.armadilha_efetiva(False, 'girassol') is False and selos.armadilha_efetiva(True, None) is True
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))
    form = {'marcas': '[]', 'aviso_foto': 'on', 'copias': '2', 'pagina': '1', 'armadilha': '1', 'armadilha_palavra': 'Girassol'}
    assert c.post(API + pid + '/gerar/', form).status_code == 200
    assert c.get(API + pid + '/configurar/').json()['data']['opcoes']['armadilha_palavra'] == 'Girassol'
    r = c.post(API + pid + '/armadilha/', {'copia': '2', 'texto': 'A resposta final é girassol.'}).json()['data']
    assert r['encontrada'] is True and r['palavra'] == 'girassol'
    assert c.post(API + pid + '/gerar/', {**form, 'armadilha_palavra': 'a b'}).status_code == 400


def test_codigo_de_barras_automatico_vai_para_espaco_vazio_e_qr_entre_alternativas():
    import pymupdf
    from apps.escudo.services import selos
    d = pymupdf.open()
    pg = d.new_page(width=595, height=842)
    y, q = 70, 1
    while y < 800:  # a página está cheia até ao fundo, excepto um espaço no meio, à direita
        pg.draw_line((40, y - 14), (555, y - 14), width=0.6)
        pg.insert_text((50, y), f'{q}. Qual a solução da equação?', fontsize=10)
        for i, x in enumerate((60, 170, 330, 450)):
            pg.insert_text((x, y + 16), f'{"ABCD"[i]}. {i}', fontsize=10)
        y += 44
        q += 1
    doc = pymupdf.open(stream=d.tobytes(), filetype='pdf')
    pag = doc[0]
    oc = selos._retangulos_ocupados(pag)
    marcas = selos.validar_marcas([{'tipo': 'barras', 'paginas': 'primeira', 'x': 0.5, 'y': 0.91, 'tamanho_mm': 50}])
    assert marcas[0]['auto'] is True
    (m, rect), = selos.resolver_marcas(pag, oc, marcas)
    assert not any(rect.intersects(o) for o in oc)  # não tapa a prova
    fixa = selos.validar_marcas([{'tipo': 'barras', 'paginas': 'primeira', 'x': 0.5, 'y': 0.91, 'tamanho_mm': 50, 'auto': False}])
    (_, rect_fixa), = selos.resolver_marcas(pag, oc, fixa)
    assert rect_fixa == selos.geometria(fixa[0], 595, 842)  # posição manual respeitada
    # QR de página: nos vazios entre alternativas, alinhados, sem tocar em nada e encolhendo para caber
    qrs = selos.posicoes_qr_pagina(pag, oc + [rect + (-4, -4, 4, 4)], 'ABCD1234', 1, 0, 4, set(), 20, 'auto')
    assert len(qrs) == 4 and len({round(r.x0) for r in qrs}) == 1
    assert all(not any(r.intersects(o) for o in oc) for r in qrs)
    esq = selos.posicoes_qr_pagina(pag, oc, 'ABCD1234', 1, 0, 3, set(), 20, 'esquerda')
    dir_ = selos.posicoes_qr_pagina(pag, oc, 'ABCD1234', 1, 0, 3, set(), 20, 'direita')
    assert not esq or not dir_ or esq[0].x0 < dir_[0].x0  # ajuste manual da coluna

# ----------------------------------------------------------------- folha de resposta opcional (1.ª página)
def _alunos_reais(escola, n=3):
    from apps.alunos.models import Aluno
    from apps.turmas.models import Turma
    t = Turma.objects.create(escola=escola, nome='Turma 1', grau_ano='11.ª Classe', ano_letivo=escola.ano_letivo_ativo, area='Ciências')
    for i in range(n):
        Aluno.objects.create(escola=escola, turma=t, matricula=f'MAT_FOLHA_{i}', nome=f'Nome{i}', apelido='Silva',
                             data_nascimento='2009-01-01', genero='F')
    return t


def test_folha_nao_e_opcional_por_omissao_e_sai_na_primeira_pagina(duas_escolas):
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))
    base = {'marcas': '[]', 'copias': '1'}
    sem = c.post(API + pid + '/gerar/', base)
    paginas_sem = len(PdfReader(io.BytesIO(sem.content)).pages)
    com = c.post(API + pid + '/gerar/', {**base, 'folha_resposta': 'sim', 'folha_n_perguntas': '20', 'folha_personalizada': 'nao'})
    assert com.status_code == 200, com.content
    leitor = PdfReader(io.BytesIO(com.content))
    assert len(leitor.pages) > paginas_sem
    assert 'FOLHA' in (leitor.pages[0].extract_text() or '').upper()
    nao = c.post(API + pid + '/gerar/', {**base, 'folha_resposta': 'nao'})
    assert len(PdfReader(io.BytesIO(nao.content)).pages) == paginas_sem


def test_folha_exige_numero_de_perguntas(duas_escolas):
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))
    r = c.post(API + pid + '/gerar/', {'marcas': '[]', 'copias': '1', 'folha_resposta': 'sim'})
    assert r.status_code == 400


def test_folha_personalizada_uma_copia_por_aluno_real_da_turma(duas_escolas):
    a, _ = duas_escolas
    turma = _alunos_reais(a, 3)
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))
    form = {'marcas': '[]', 'copias': '1', 'folha_resposta': 'sim', 'folha_n_perguntas': '20',
            'folha_personalizada': 'sim', 'folha_classe': '11.ª Classe', 'folha_area': 'Ciências', 'folha_turma_id': str(turma.id)}
    r = c.post(API + pid + '/gerar/', form)
    assert r.status_code == 200, r.content
    nomes = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert len(nomes) == 3 and any('Nome0' in n for n in nomes)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    primeira = PdfReader(io.BytesIO(z.read(nomes[0]))).pages[0].extract_text()
    assert 'Nome0' in primeira or 'NOME0' in primeira.upper()


def test_folha_personalizada_sem_alunos_reais_nao_inventa_folhas(duas_escolas):
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))
    r = c.post(API + pid + '/gerar/', {'marcas': '[]', 'copias': '1', 'folha_resposta': 'sim', 'folha_n_perguntas': '20',
                                       'folha_personalizada': 'sim', 'folha_classe': '11.ª Classe'})
    assert r.status_code == 400 and 'alunos' in r.json()['message']


def _zip(r):
    assert r.status_code == 200, r.content
    return zipfile.ZipFile(io.BytesIO(r.content))


def test_folha_exclui_por_faltas_ppf_e_outros_e_regista_o_motivo(duas_escolas):
    from apps.alunos.models import Aluno
    from apps.disciplinas.models import Disciplina
    from apps.notas.models import Nota
    a, _ = duas_escolas
    turma = _alunos_reais(a, 4)
    d = Disciplina.objects.create(escola=a, nome='Física', codigo='FIS', classe='11.ª Classe', ano_letivo=a.ano_letivo_ativo)
    al = list(Aluno.objects.filter(turma=turma).order_by('nome'))
    Nota.objects.create(escola=a, aluno=al[0], disciplina=d, turma=turma, periodo='1_TRIMESTRE', faltas=12)
    Nota.objects.create(escola=a, aluno=al[1], disciplina=d, turma=turma, periodo='1_TRIMESTRE', anotacao='PPF')
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))
    form = {'marcas': '[]', 'copias': '1', 'folha_resposta': 'sim', 'folha_n_perguntas': '20', 'folha_personalizada': 'sim',
            'folha_classe': '11.ª Classe', 'folha_excluir': 'sim', 'folha_excluir_motivo': ['faltas', 'ppf', 'outros'],
            'folha_excluir_faltas': '10', 'folha_excluir_outros': al[3].matricula}
    z = _zip(c.post(API + pid + '/gerar/', form))
    nomes = z.namelist()
    assert len([n for n in nomes if n.endswith('.pdf')]) == 1  # só sobra o aluno 2
    rel = [n for n in nomes if n.endswith('.csv')]
    texto = z.read(rel[0]).decode('utf-8-sig')
    assert 'Faltas: 12' in texto and 'PPF' in texto and 'Outros' in texto
    # exclusão sem motivo ou sem mínimo de faltas é recusada
    assert c.post(API + pid + '/gerar/', {**form, 'folha_excluir_motivo': []}).status_code == 400
    assert c.post(API + pid + '/gerar/', {**form, 'folha_excluir_faltas': ''}).status_code == 400


def test_folha_personalizada_a_partir_de_lista_importada(duas_escolas):
    c = _cliente(duas_escolas)
    pid = _pid(_criar(c))
    csv_ = 'Nº;Apelido;Nome;Turma;Situação\n1;Matsinhe;Ana;A;\n2;Cossa;Beto;A;Transferida\n3;Nhaca;Carla;A;\n'.encode('utf-8')
    form = {'marcas': '[]', 'copias': '1', 'folha_resposta': 'sim', 'folha_n_perguntas': '20', 'folha_personalizada': 'sim',
            'folha_fonte': 'lista', 'folha_lista': SimpleUploadedFile('alunos.csv', csv_), 'folha_excluir': 'sim',
            'folha_excluir_motivo': ['transferida']}
    z = _zip(c.post(API + pid + '/gerar/', form, format='multipart'))
    pdfs = [n for n in z.namelist() if n.endswith('.pdf')]
    assert len(pdfs) == 2 and not any('Cossa' in n for n in pdfs)
    assert 'Transferida' in z.read([n for n in z.namelist() if n.endswith('.csv')][0]).decode('utf-8-sig')
    assert c.post(API + pid + '/gerar/', {**form, 'folha_lista': SimpleUploadedFile('x.csv', b'Turma\nA\n')}, format='multipart').status_code == 400
