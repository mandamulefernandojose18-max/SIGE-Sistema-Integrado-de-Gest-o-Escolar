"""Testes do módulo xlsx_seguro: ficheiros Excel que têm de abrir sempre."""
import io

import openpyxl
import pytest
from PIL import Image

from apps.documentos.services.xlsx_seguro import (
    XlsxInvalidoError, guardar_xlsx_seguro, nome_folha, normalizar_logo_png,
    texto_seguro, validar_xlsx_bytes,
)


def test_nome_folha_remove_proibidos_e_limita():
    assert nome_folha('Pauta 10ª A/B:1') == 'Pauta 10ª A-B-1'
    assert len(nome_folha('x' * 80)) == 31
    assert nome_folha('') == 'Folha'
    assert nome_folha("'abc'") == 'abc'
    assert nome_folha('History') == 'Historico'


def test_nome_folha_unico():
    assert nome_folha('Aviso', existentes=['aviso']) == 'Aviso (2)'
    assert len(nome_folha('y' * 40, existentes=['y' * 31])) <= 31


def test_nome_folha_aceite_pelo_openpyxl():
    wb = openpyxl.Workbook()
    wb.active.title = nome_folha('Caderneta [10ª] A/B?*:\\ ' + 'z' * 50)


def test_texto_nunca_e_formula_e_sem_controlo():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws['A1'] = '=HYPERLINK("http://x")'
    ws['A2'] = texto_seguro('ok\x07mau')  # openpyxl rejeita controlo na atribuição
    ws['A3'] = 'a' * 40000
    dados = guardar_xlsx_seguro(wb)
    ws2 = openpyxl.load_workbook(io.BytesIO(dados)).active
    assert ws2['A1'].data_type == 's'
    assert ws2['A1'].value == '=HYPERLINK("http://x")'
    assert ws2['A2'].value == 'okmau'
    assert len(ws2['A3'].value) == 32767
    assert texto_seguro(5) == 5


def test_validar_rejeita_lixo():
    with pytest.raises(XlsxInvalidoError):
        validar_xlsx_bytes(b'<html>erro</html>')
    with pytest.raises(XlsxInvalidoError):
        validar_xlsx_bytes(b'PK\x03\x04lixo')


def test_validar_rejeita_fusoes_sobrepostas():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.merge_cells('A1:C1')
    ws.merge_cells('B1:D1')
    buf = io.BytesIO()
    wb.save(buf)
    with pytest.raises(XlsxInvalidoError):
        validar_xlsx_bytes(buf.getvalue())


@pytest.mark.parametrize('modo,fmt', [('P', 'PNG'), ('CMYK', 'JPEG'), ('RGBA', 'WEBP'), ('L', 'PNG')])
def test_logo_normalizado_para_png(modo, fmt):
    buf = io.BytesIO()
    Image.new(modo, (300, 200)).save(buf, format=fmt)
    png = normalizar_logo_png(buf.getvalue())
    assert png and png[:8] == b'\x89PNG\r\n\x1a\n'
    assert max(Image.open(io.BytesIO(png)).size) <= 256


def test_logo_invalido_devolve_none():
    assert normalizar_logo_png(b'nao e imagem') is None
    assert normalizar_logo_png(b'') is None
