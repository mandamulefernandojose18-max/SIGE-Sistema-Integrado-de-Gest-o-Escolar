"""Lista de notas da avaliação (PDF e Excel): estrutura, colunas e regras de formato (docs/REGRAS_EXCEL_E_PDF.md)."""
import io
from types import SimpleNamespace as NS

import openpyxl
import pymupdf
from PIL import Image

from apps.documentos.services import pdf_service
from apps.notas import lista_avaliacao as la


def _dados(com_sem_aluno=True):
    esc = NS(nome='Escola de Verificação', provincia='Inhambane', distrito='Massinga')
    cab = {'escola': esc, 'disciplina': 'Física', 'tipo': 'Avaliação de Teste', 'titulo': 'Teste', 'periodo': '1.º Trimestre',
           'ano': '2026', 'turma': 'Turma 12', 'classe': '11.ª Classe', 'professor': 'Professor', 'emitido': '22/11/2026',
           'corrigidas': 3, 'total': 4, 'sem_aluno': 1 if com_sem_aluno else 0, 'positivas': 2, 'negativas': 1, 'media': 11.0,
           'maior': 15.0, 'menor': 7.0, 'aproveitamento': 66.7}
    linhas = [[1, '0101S0001.12.01.2026.cg.01', 'Nome Completo Um', 'Turma 12', '11.ª Classe', '30/40', 15.0, 'Positiva', 'Lançada'],
              [2, '0101S0001.12.01.2026.cg.02', 'Nome Completo Dois', 'Turma 12', '11.ª Classe', '20/40', 10.0, 'Positiva', 'Corrigida'],
              [3, '0101S0001.12.01.2026.cg.03', 'Nome Completo Três', 'Turma 12', '11.ª Classe', '14/40', 7.0, 'Negativa', 'Corrigida']]
    if com_sem_aluno:
        linhas.append(['—', '—', 'Por identificar · folhas.pdf (pág. 4)', 'Turma 12', '11.ª Classe', '20/40', 10.0, 'Positiva', 'Sem aluno'])
    return cab, linhas


def _logo(monkeypatch):
    buf = io.BytesIO()
    Image.new('RGB', (80, 80), (30, 58, 138)).save(buf, 'PNG')
    monkeypatch.setattr(pdf_service, 'resolver_logo_documento_escola', lambda e: (buf.getvalue(), 'png', None, None))
    monkeypatch.setattr('apps.documentos.services.xlsx_seguro.normalizar_logo_png', lambda b, lado_max=256: buf.getvalue(), raising=False)


def test_colunas_incluem_classe_e_nota_na_posicao_certa():
    assert 'Classe' in la.COLUNAS and la.COLUNAS[la.I_NOTA] == 'Nota (0–20)'


def test_pdf_horizontal_com_rodape_e_sem_palavras_cortadas(monkeypatch):
    _logo(monkeypatch)
    cab, linhas = _dados()
    doc = pymupdf.open(stream=la.pdf_lista(cab, linhas), filetype='pdf')
    assert doc.page_count >= 1 and doc[0].rect.width > doc[0].rect.height          # A4 horizontal
    texto = ' '.join(p.get_text() for p in doc)
    assert 'Página 1 de' in texto and 'Classe' in texto and 'Por identificar' in texto
    for palavra in ('Acertos', 'Resultado', 'Nota', 'Estado', 'Código do aluno'):
        assert palavra in texto.replace('\n', ' ')                                  # cabeçalhos inteiros (sem «Acerto/s»)


def test_xlsx_moldura_profissional_e_fontes(monkeypatch):
    _logo(monkeypatch)
    cab, linhas = _dados()
    wb = openpyxl.load_workbook(io.BytesIO(la.xlsx_lista(cab, linhas)))
    ws = wb.active
    assert ws.page_setup.orientation == 'landscape' and ws.freeze_panes
    cab_row = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 1).value == 'Nº')
    assert [ws.cell(cab_row, c).value for c in range(1, 10)] == la.COLUNAS
    h = ws.cell(cab_row, 3)
    assert h.border.top.style == 'thick' and h.border.bottom.style == 'double'      # moldura exterior grossa + linha dupla dourada
    assert ws.cell(cab_row + 1, 3).border.bottom.style == 'dotted'
    assert h.alignment.horizontal == 'center' and h.font.name == 'Times New Roman' and h.font.size == 12
    nota_neg = ws.cell(cab_row + 3, la.I_NOTA + 1)
    assert nota_neg.value == 7.0 and nota_neg.font.color.rgb.endswith('C00000')     # nota negativa a vermelho
    assert not any(ws.row_dimensions[r].hidden for r in range(1, cab_row + 4))
