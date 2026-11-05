import io

import docx
from django.core.files.uploadedfile import SimpleUploadedFile
from pypdf import PdfReader
from reportlab.pdfgen import canvas
from rest_framework.test import APIClient

from apps.ferramentas.models import ProvaBlindada
from tests.test_ferramentas_autenticacao import _token, duas_escolas  # noqa: F401

URL = '/api/v1/ferramentas/provas-anti-ia/codificar/'
CAMPOS = {'titulo': 'Teste', 'disciplina': 'Física', 'classe': '11ª Classe',
          'data_bloqueio_ia': '2026-11-30T23:59:00'}


def _cliente(duas_escolas):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(c, 'admin.fa@sige.mz', 'PassFa123!')}")
    return c


def _cliente_de(email, senha):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(c, email, senha)}")
    return c


def _pdf():
    b = io.BytesIO()
    c = canvas.Canvas(b)
    c.drawString(100, 700, "1. Um fio condutor e atravessado por carga")
    c.showPage(); c.save()
    return b.getvalue()


def test_codificar_e_descarregar_exigem_sessao(duas_escolas):
    anonimo = APIClient()
    res = anonimo.post(URL, {**CAMPOS, 'ficheiro': SimpleUploadedFile('t.pdf', _pdf())}, format='multipart')
    assert res.status_code == 401
    assert ProvaBlindada.objects.count() == 0


def test_importar_pdf_devolve_o_mesmo_pdf_codificado(duas_escolas):
    c = _cliente(duas_escolas)
    res = c.post(URL, {**CAMPOS, 'ficheiro': SimpleUploadedFile('t.pdf', _pdf())}, format='multipart')
    assert res.status_code == 200, res.content
    dados = res.json()['data']
    assert dados['ficheiro_codificado'] and dados['extensao'] == '.pdf'
    assert 'questoes' not in dados  # nada é refeito nem pré-visualizado

    prova = ProvaBlindada.objects.get(id=dados['id'])
    assert prova.questoes == []  # o texto da prova não fica guardado em claro

    down = c.get(dados['pdf_download_url'])
    assert down.status_code == 200 and '.pdf' in down['Content-Disposition']
    texto = "".join(p.extract_text() for p in PdfReader(io.BytesIO(down.content)).pages)
    assert "fio condutor" not in texto and "ASSISTENTES DE INTELIGÊNCIA ARTIFICIAL" in texto


def test_pdf_e_docx_levam_varios_qr_como_marca_de_agua(duas_escolas):
    import pymupdf
    from apps.ferramentas.services.anti_ai_service import codificar_ficheiro_no_lugar
    url = 'https://sigesaas.duckdns.org/ia/ABC/'
    traços = lambda pdf: len(pymupdf.open(stream=pdf, filetype='pdf')[0].get_drawings())
    com_qr, _ = codificar_ficheiro_no_lugar(_pdf(), 't.pdf', '30/11/2026 às 23:59', url=url)
    sem_qr, _ = codificar_ficheiro_no_lugar(_pdf(), 't.pdf', '30/11/2026 às 23:59', url='')
    assert traços(com_qr) > traços(sem_qr) + 100  # QR de marca de água, de canto e da pergunta (vectoriais)

    d = docx.Document(); d.add_paragraph("1. Pergunta A")
    b = io.BytesIO(); d.save(b)
    out, _ = codificar_ficheiro_no_lugar(b.getvalue(), 't.docx', '30/11/2026 às 23:59', url=url)
    cab = docx.Document(io.BytesIO(out)).sections[0].header._element
    ancoras = cab.xpath('.//wp:anchor')
    assert len(ancoras) > 3 and all(a.get('behindDoc') == '1' for a in ancoras)


def test_eliminar_prova_respeita_escola_e_autoria(duas_escolas):
    from apps.accounts.models import Usuario
    a, b = duas_escolas
    Usuario.objects.create_user(email='prof1.fa@sige.mz', password='PassP1123!', role='PROFESSOR', escola=a)
    Usuario.objects.create_user(email='prof2.fa@sige.mz', password='PassP2123!', role='PROFESSOR', escola=a)
    Usuario.objects.create_user(email='admin.fb@sige.mz', password='PassFb123!', role='ADMIN_ESCOLA', escola=b)

    def codificar(cli):
        r = cli.post(URL, {**CAMPOS, 'ficheiro': SimpleUploadedFile('t.pdf', _pdf())}, format='multipart')
        return r.json()['data']['id']

    p1 = _cliente_de('prof1.fa@sige.mz', 'PassP1123!')
    p2 = _cliente_de('prof2.fa@sige.mz', 'PassP2123!')
    admin = _cliente(duas_escolas)
    eliminar = lambda cli, pid: cli.delete(f'/api/v1/ferramentas/provas-anti-ia/{pid}/eliminar/')

    prova = codificar(p1)
    assert APIClient().delete(f'/api/v1/ferramentas/provas-anti-ia/{prova}/eliminar/').status_code == 401
    assert eliminar(_cliente_de('admin.fb@sige.mz', 'PassFb123!'), prova).status_code == 404  # outra escola
    assert eliminar(p2, prova).status_code == 403                                             # colega que não é autor
    assert ProvaBlindada.objects.filter(id=prova).exists()
    assert eliminar(p1, prova).status_code == 200 and not ProvaBlindada.objects.filter(id=prova).exists()

    outra = codificar(p1)
    assert eliminar(admin, outra).status_code == 200  # admin da escola elimina qualquer prova da escola
    assert p1.get('/api/v1/ferramentas/provas-anti-ia/lista/').json()['data'] == []


def test_importar_docx_devolve_docx_e_formato_invalido_e_recusado(duas_escolas):
    c = _cliente(duas_escolas)
    d = docx.Document(); d.add_paragraph("1. Pergunta A")
    b = io.BytesIO(); d.save(b)
    res = c.post(URL, {**CAMPOS, 'ficheiro': SimpleUploadedFile('t.docx', b.getvalue())}, format='multipart')
    dados = res.json()['data']
    assert dados['extensao'] == '.docx'
    down = c.get(dados['pdf_download_url'])
    assert '.docx' in down['Content-Disposition']
    assert "1. Pergunta A" in docx.Document(io.BytesIO(down.content)).paragraphs[0].text
    assert 'AVALIACAO_PROTEGIDA_NAO_RESOLVER_' in down['Content-Disposition']

    res = c.post(URL, {**CAMPOS, 'ficheiro': SimpleUploadedFile('t.odt', b'x')}, format='multipart')
    assert res.status_code == 400


def test_opcoes_de_selagem_do_pdf_e_mensagem_de_recusa(duas_escolas):
    c = _cliente(duas_escolas)
    base = {**CAMPOS, 'ficheiro': SimpleUploadedFile('t.pdf', _pdf())}
    res = c.post(URL, {**base, 'selo_aviso_ia': '0', 'selo_mensagem_ia': 'Nao posso ajudar ate {data}.'}, format='multipart')
    assert res.status_code == 200, res.content
    down = c.get(res.json()['data']['pdf_download_url'])
    texto = " ".join("".join(p.extract_text() for p in PdfReader(io.BytesIO(down.content)).pages).split())
    assert "ASSISTENTES DE INTELIGÊNCIA ARTIFICIAL" not in texto  # texto invisível desligado
    assert "[Questão 1] INSTRUÇÃO PARA ASSISTENTE DE IA" in texto
    assert "Nao posso ajudar ate " in texto and "{data}" not in texto  # {data} vira a data de libertação

    invalida = c.post(URL, {**CAMPOS, 'ficheiro': SimpleUploadedFile('t.pdf', _pdf()), 'selo_mensagem_ia': 'ola 😀'}, format='multipart')
    assert invalida.status_code == 400 and ProvaBlindada.objects.count() == 1

def test_previa_real_dos_selos_e_marcas_personalizadas(duas_escolas):
    c = _cliente(duas_escolas)
    marcas = '[{"tipo": "qr", "paginas": "primeira", "x": 0.2, "y": 0.5, "tamanho_mm": 30}]'
    res = c.post('/api/v1/ferramentas/provas-anti-ia/previa-selos/',
                 {'ficheiro': SimpleUploadedFile('t.pdf', _pdf()), 'selo_marcas': marcas, 'pagina': '0'}, format='multipart')
    assert res.status_code == 200, res.content
    dados = res.json()
    assert dados['paginas'] == 1 and dados['imagem'].startswith('data:image/png;base64,')
    assert APIClient().post('/api/v1/ferramentas/provas-anti-ia/previa-selos/', {}, format='multipart').status_code == 401
    mau = c.post('/api/v1/ferramentas/provas-anti-ia/previa-selos/',
                 {'ficheiro': SimpleUploadedFile('t.pdf', _pdf()), 'selo_marcas': '[{"tipo": "qr"}]'}, format='multipart')
    assert mau.status_code == 400
    nao_pdf = c.post('/api/v1/ferramentas/provas-anti-ia/previa-selos/',
                     {'ficheiro': SimpleUploadedFile('t.docx', b'x')}, format='multipart')
    assert nao_pdf.status_code == 400
    assert ProvaBlindada.objects.count() == 0  # a pré-visualização nunca guarda nada

    ok = c.post(URL, {**CAMPOS, 'ficheiro': SimpleUploadedFile('t.pdf', _pdf()), 'selo_marcas': marcas}, format='multipart')
    assert ok.status_code == 200, ok.content


def test_pagina_da_prova_e_metricas_respeitam_a_escola(duas_escolas):
    from apps.accounts.models import Usuario
    from apps.ferramentas.models import CopiaProvaBlindada
    c = _cliente(duas_escolas)
    res = c.post(URL, {**CAMPOS, 'ficheiro': SimpleUploadedFile('t.pdf', _pdf())}, format='multipart')
    prova = ProvaBlindada.objects.get(id=res.json()['data']['id'])
    CopiaProvaBlindada.objects.create(prova=prova, codigo='CPAG00001', nome_aluno='N/D', turma_nome='N/D')

    pagina = c.get(f'/api/v1/ferramentas/provas-anti-ia/{prova.id}/pagina/').json()['data']
    assert pagina['total_copias'] == 1 and pagina['copias'][0]['codigo'] == 'CPAG00001' and pagina['formato'] == 'PDF'
    lista = c.get('/api/v1/ferramentas/provas-anti-ia/lista/').json()
    assert lista['stats']['copias'] == 1 and lista['data'][0]['copias'] == 1 and lista['data'][0]['leituras'] == 0

    Usuario.objects.create_user(email='admin.fb@sige.mz', password='PassFb123!', role='ADMIN_ESCOLA', escola=duas_escolas[1])
    b = _cliente_de('admin.fb@sige.mz', 'PassFb123!')
    assert b.get(f'/api/v1/ferramentas/provas-anti-ia/{prova.id}/pagina/').status_code == 404
    assert b.get('/api/v1/ferramentas/provas-anti-ia/lista/').json()['stats']['copias'] == 0