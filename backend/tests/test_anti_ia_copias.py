import io
import uuid

import docx
from django.core.files.uploadedfile import SimpleUploadedFile
from pypdf import PdfReader

from apps.ferramentas.models import CopiaProvaBlindada, ProvaBlindada
from apps.ferramentas.services.anti_ai_service import carimbar_copia, codificar_ficheiro_no_lugar, gerar_codigo_copia
from tests.test_anti_ia_importacao_endpoint import CAMPOS, URL, _cliente, _cliente_de, _pdf
from tests.test_ferramentas_autenticacao import duas_escolas  # noqa: F401

DATA = '30/11/2026 às 23:59'


def test_codigos_de_copia_sao_unicos_e_curtos():
    codigos = {gerar_codigo_copia() for _ in range(500)}
    assert len(codigos) == 500 and all(len(c) == 9 and c[0] == 'C' for c in codigos)


def test_carimbo_pdf_visivel_no_rodape_e_texto_oculto_sem_alterar_paginas():
    import pypdfium2 as pdfium
    base, _ = codificar_ficheiro_no_lugar(_pdf(), 't.pdf', DATA, url='')
    saida = carimbar_copia(base, '.pdf', 'CABC12345', 'Nome Exemplo — Turma')
    assert len(PdfReader(io.BytesIO(saida)).pages) == 1
    texto = PdfReader(io.BytesIO(saida)).pages[0].extract_text()
    assert 'CABC12345' in texto
    rodape = pdfium.PdfDocument(saida)[0].render(scale=2).to_pil().convert('L')
    faixa = rodape.crop((0, rodape.height - 14, rodape.width, rodape.height))
    assert min(faixa.getdata()) < 128  # o código está desenhado (visível), não só na camada de texto


def test_carimbo_docx_acrescenta_codigo_visivel_ao_rodape():
    from docx.oxml.ns import qn
    d = docx.Document(); d.add_paragraph("1. Pergunta"); b = io.BytesIO(); d.save(b)
    base, _ = codificar_ficheiro_no_lugar(b.getvalue(), 't.docx', DATA, url='')
    novo = docx.Document(io.BytesIO(carimbar_copia(base, '.docx', 'CABC12345', 'Nome Exemplo')))
    visiveis = [r.text for p in novo.sections[0].footer.paragraphs for r in p.runs
                if r._r.rPr is None or r._r.rPr.find(qn('w:vanish')) is None]
    assert any('CABC12345' in t for t in visiveis)
    assert carimbar_copia(b'x', '.xlsx', 'C1', 'x') is None


def _admin_escola_b(duas_escolas):
    from apps.accounts.models import Usuario
    Usuario.objects.create_user(email='admin.fb@sige.mz', password='PassFb123!', role='ADMIN_ESCOLA', escola=duas_escolas[1])
    return _cliente_de('admin.fb@sige.mz', 'PassFb123!')


def _prova_da_escola_a(duas_escolas):
    c = _cliente(duas_escolas)
    res = c.post(URL, {**CAMPOS, 'ficheiro': SimpleUploadedFile('t.pdf', _pdf())}, format='multipart')
    return c, ProvaBlindada.objects.get(id=res.json()['data']['id'])


def test_copias_exigem_sessao_e_turma_valida(duas_escolas):
    c, prova = _prova_da_escola_a(duas_escolas)
    url = f'/api/v1/ferramentas/provas-anti-ia/{prova.id}/copias/'
    from rest_framework.test import APIClient
    assert APIClient().get(url, {'turma_id': str(uuid.uuid4())}).status_code == 401
    assert c.get(url, {'turma_id': str(uuid.uuid4())}).status_code == 404
    assert c.get(url, {'turma_id': 'nao-e-uuid'}).status_code == 404


def test_copias_de_prova_de_outra_escola_nao_sao_acessiveis(duas_escolas):
    _, prova = _prova_da_escola_a(duas_escolas)
    b = _admin_escola_b(duas_escolas)
    assert b.get(f'/api/v1/ferramentas/provas-anti-ia/{prova.id}/copias/', {'turma_id': str(uuid.uuid4())}).status_code == 404


def test_verificar_codigo_respeita_o_isolamento_entre_escolas(duas_escolas):
    c, prova = _prova_da_escola_a(duas_escolas)
    CopiaProvaBlindada.objects.create(prova=prova, codigo='CTESTE001', nome_aluno='N/D', turma_nome='N/D')
    url = '/api/v1/ferramentas/provas-anti-ia/copias/verificar/cteste001/'  # minúsculas: o código normaliza-se
    ok = c.get(url)
    assert ok.status_code == 200 and ok.json()['data']['codigo'] == 'CTESTE001'
    assert _admin_escola_b(duas_escolas).get(url).status_code == 404
