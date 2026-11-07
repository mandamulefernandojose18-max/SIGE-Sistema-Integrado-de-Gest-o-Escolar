import io
import openpyxl
from openpyxl.styles import Border, Font, PatternFill, Side
from apps.documentos.services.xlsx_seguro import guardar_xlsx_seguro


def _wb():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws['A1'] = 'Cabecalho'
    ws['A1'].font = Font(name='Arial', size=8, bold=True, color='FFFFFF')
    ws['A1'].fill = PatternFill('solid', start_color='1E3A8A')
    ws['B1'] = 'Outro'
    ws['B1'].font = Font(name='Arial', size=9, color='FFFFFF')
    ws['B1'].fill = PatternFill('solid', start_color='1E3A8A')
    ws['A2'] = 'dado'
    ws['A2'].font = Font(name='Calibri', size=10)
    fino = Side(style='thin')
    for r in ws['A1:B2']:
        for c in r:
            c.border = Border(left=fino, right=fino, top=fino, bottom=fino)
    return wb


def test_regra_mestra_fontes_cabecalho_e_ocultacao():
    wb = openpyxl.load_workbook(io.BytesIO(guardar_xlsx_seguro(_wb())))
    ws = wb.active
    for cel in ('A1', 'B1', 'A2'):
        assert ws[cel].font.name == 'Times New Roman' and ws[cel].font.size == 12
    assert ws['A1'].alignment.horizontal == 'center' and ws['A1'].alignment.vertical == 'center'
    assert ws['A1'].font.bold is True
    assert ws.sheet_format.zeroHeight is True  # linhas sem conteudo escondidas
    assert any(cd.hidden for cd in ws.column_dimensions.values())  # colunas sem conteudo escondidas
    assert ws['A1'].border.top.style == 'thick'  # moldura profissional

