"""Lista dos alunos cujas folhas/provas foram geradas (quem e quantos) e dos que ficaram de fora (e porquê).

Sai em PDF e em Excel, seguindo docs/REGRAS_EXCEL_E_PDF.md: Times New Roman, cabeçalho de tabela azul centrado e repetido,
palavras inteiras (células com Paragraph), moldura exterior grossa, linha dupla sob o cabeçalho e zebra; no Excel grava-se
sempre por guardar_xlsx_seguro. Só dados reais recebidos: nada é inventado.
"""
import datetime
import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Spacer

from .pdf_service import (Paragraph, SimpleDocTemplate, TableStyle, gerar_cabecalho_mec, getSampleStyleSheet)

AZUL = colors.HexColor('#1E3A8A')
DOURADO = colors.HexColor('#C9A227')
ZEBRA = colors.HexColor('#F1F5F9')
CINZA = colors.HexColor('#94A3B8')

COLUNAS_INCLUIDOS = [('Ordem', 1.1), ('Nº', 1.3), ('Código', 3.0), ('Apelido', 3.5), ('Nome', 4.4), ('Classe', 1.9), ('Turma', 1.8)]
COLUNAS_EXCLUIDOS = [('Nº', 1.0), ('Código', 2.6), ('Apelido', 2.8), ('Nome', 3.4), ('Classe', 1.5), ('Turma', 1.5), ('Motivo', 4.2)]


def _linhas_incluidos(dados):
    return [[k, d.get('numero') or '', d.get('codigo') or '', d.get('apelido') or '', d.get('nome') or '',
             d.get('classe') or '', d.get('turma') or ''] for k, d in enumerate(dados, start=1)]


def _linhas_excluidos(excluidos):
    return [[d.get('numero') or '', d.get('codigo') or '', d.get('apelido') or '', d.get('nome') or '',
             d.get('classe') or '', d.get('turma') or '', motivo] for d, motivo in excluidos]


def _tabela(colunas, linhas, estilos):
    from reportlab.platypus import Table
    cab = ParagraphStyle('LAcab', parent=estilos['Normal'], alignment=TA_CENTER, fontName='Times-Bold', fontSize=12,
                         leading=15, textColor=colors.white)
    cel = ParagraphStyle('LAcel', parent=estilos['Normal'], alignment=TA_LEFT, fontName='Times-Roman', fontSize=12, leading=15)
    cen = ParagraphStyle('LAcen', parent=cel, alignment=TA_CENTER)
    dados = [[Paragraph(nome, cab) for nome, _ in colunas]]
    for linha in linhas:
        dados.append([Paragraph(str(v), cen if colunas[i][0] in ('Ordem', 'Nº', 'Classe', 'Turma') else cel)
                      for i, v in enumerate(linha)])
    t = Table(dados, colWidths=[w * cm for _, w in colunas], repeatRows=1)
    est = [
        ('BACKGROUND', (0, 0), (-1, 0), AZUL), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1.2, AZUL), ('LINEBELOW', (0, 0), (-1, 0), 2.2, DOURADO),
        ('INNERGRID', (0, 1), (-1, -1), 0.4, CINZA), ('LINEAFTER', (0, 0), (-2, 0), 0.4, colors.HexColor('#5B74B8')),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]
    for r in range(2, len(dados), 2):
        est.append(('BACKGROUND', (0, r), (-1, r), ZEBRA))
    t.setStyle(TableStyle(est))
    return t


def lista_pdf(escola, titulo, dados_incluidos, excluidos=(), referencia=''):
    """PDF A4 com o cabeçalho oficial, o total e a tabela dos alunos gerados (e dos excluídos, se houver)."""
    estilos = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.6 * cm, bottomMargin=1.6 * cm,
                            title=titulo)
    el = gerar_cabecalho_mec(estilos, escola.nome, escola.provincia, escola.distrito, compacto=True, escola=escola)
    centro = ParagraphStyle('LAtit', parent=estilos['Normal'], alignment=TA_CENTER, fontName='Times-Bold', fontSize=12, leading=16)
    norm = ParagraphStyle('LAnorm', parent=estilos['Normal'], alignment=TA_LEFT, fontName='Times-Roman', fontSize=12, leading=16)
    el.append(Paragraph(titulo.upper(), centro))
    if referencia:
        el.append(Paragraph(referencia, ParagraphStyle('LAref', parent=norm, alignment=TA_CENTER)))
    el.append(Spacer(1, 0.3 * cm))
    el.append(Paragraph(f'<b>Total de folhas/provas geradas: {len(dados_incluidos)}</b> · Emitido em '
                        f'{datetime.date.today().strftime("%d/%m/%Y")}', norm))
    el.append(Spacer(1, 0.2 * cm))
    el.append(_tabela(COLUNAS_INCLUIDOS, _linhas_incluidos(dados_incluidos), estilos))
    if excluidos:
        el.append(Spacer(1, 0.5 * cm))
        el.append(Paragraph(f'<b>Alunos que ficaram de fora: {len(excluidos)}</b>', norm))
        el.append(Spacer(1, 0.2 * cm))
        el.append(_tabela(COLUNAS_EXCLUIDOS, _linhas_excluidos(excluidos), estilos))
    doc.build(el)
    return buf.getvalue()


def lista_xlsx(escola, titulo, dados_incluidos, excluidos=(), referencia=''):
    """Excel (gravado por guardar_xlsx_seguro) com a folha «Gerados» e, se houver, «Excluídos»."""
    import openpyxl
    from openpyxl.styles import Alignment, Font

    from .xlsx_seguro import guardar_xlsx_seguro

    TNR = 'Times New Roman'
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    def folha(nome, cabecalho, linhas, linha_titulo, larguras):
        ws = wb.create_sheet(nome)
        ws.sheet_view.showGridLines = False
        ws.cell(row=1, column=1, value=f'{titulo} · {escola.nome}').font = Font(name=TNR, size=12, bold=True)
        ws.cell(row=2, column=1, value=linha_titulo).font = Font(name=TNR, size=12)
        for i, (nome_col, w) in enumerate(zip(cabecalho, larguras), start=1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
            c = ws.cell(row=4, column=i, value=nome_col)
            c.font = Font(name=TNR, size=12, bold=True, color='FFFFFF')
            c.fill = openpyxl.styles.PatternFill('solid', start_color='1E3A8A')
            c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        for r, linha in enumerate(linhas, start=5):
            for i, v in enumerate(linha, start=1):
                c = ws.cell(row=r, column=i, value=v)
                c.font = Font(name=TNR, size=12)
                c.alignment = Alignment(horizontal='center' if cabecalho[i - 1] in ('Ordem', 'Nº', 'Classe', 'Turma') else 'left',
                                        vertical='center', wrap_text=True)
        ws.freeze_panes = 'A5'
        ws.page_setup.orientation = 'portrait'
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr = openpyxl.worksheet.properties.PageSetupProperties(fitToPage=True)

    hoje = datetime.date.today().strftime('%d/%m/%Y')
    folha('Gerados', [n for n, _ in COLUNAS_INCLUIDOS], _linhas_incluidos(dados_incluidos),
          f'Total de folhas/provas geradas: {len(dados_incluidos)} · Emitido em {hoje}' + (f' · {referencia}' if referencia else ''),
          [8, 8, 24, 24, 34, 12, 12])
    if excluidos:
        folha('Excluídos', [n for n, _ in COLUNAS_EXCLUIDOS], _linhas_excluidos(excluidos),
              f'Alunos que ficaram de fora: {len(excluidos)} · Emitido em {hoje}', [8, 24, 22, 28, 12, 12, 40])
    return guardar_xlsx_seguro(wb)
