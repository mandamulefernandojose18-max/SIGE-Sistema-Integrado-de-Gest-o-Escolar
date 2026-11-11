"""Lista de todos os alunos do âmbito: quem teve a folha/prova gerada (e quantos) e quem ficou de fora, a outra cor e com o motivo.

Sai em PDF e em Excel, seguindo docs/REGRAS_EXCEL_E_PDF.md: Times New Roman, cabeçalho de tabela azul centrado, palavras inteiras
(células com Paragraph), moldura exterior grossa, linha dupla sob o cabeçalho e zebra; no Excel grava-se sempre por
guardar_xlsx_seguro. A cor dos excluídos é personalizável; o texto adapta-se à cor para continuar legível. Só dados reais.
"""
import datetime
import io
import re

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
COR_EXCLUIDOS_PADRAO = '#FDE2E2'   # rosa claro: legível com texto preto

COLUNAS = [('Ordem', 1.0), ('Nº', 1.0), ('Código', 2.3), ('Apelido', 2.5), ('Nome', 3.3), ('Classe', 1.4), ('Turma', 1.4),
           ('Sexo', 1.0), ('Situação / motivo', 3.1)]
CENTRADAS = ('Ordem', 'Nº', 'Classe', 'Turma', 'Sexo')


def cor_valida(valor, padrao=COR_EXCLUIDOS_PADRAO):
    """«#RRGGBB» (com ou sem #); qualquer outra coisa volta à cor por omissão."""
    v = str(valor or '').strip().lstrip('#')
    return '#' + v.upper() if re.fullmatch(r'[0-9A-Fa-f]{6}', v) else padrao


def _sexo_bruto(v, m_feminino=False):
    v = str(v or '').strip().lower()
    if v == 'm':
        return 'M' if m_feminino else 'H'
    if v[:1] == 'h' or v.startswith('masc'):
        return 'H'
    if v[:1] == 'f' or v.startswith('mulher') or v.startswith('fem'):
        return 'M'
    return ''


def preparar_sexo(*grupos):
    """Fixa em cada aluno (d['_sexo']) «H» (homem) ou «M» (mulher). A letra «M» sozinha é ambígua: no sistema é
    Masculino (M/F), mas numa lista com H/M significa Mulher; decide-se pela convenção usada nos dados."""
    todos = [d for g in grupos for d in (g or []) if isinstance(d, dict)]
    valores = {str(d.get('genero') or '').strip().lower() for d in todos}
    m_feminino = any(v[:1] == 'h' for v in valores) and not any(v[:1] == 'f' for v in valores)
    for d in todos:
        d['_sexo'] = _sexo_bruto(d.get('genero'), m_feminino)


def sexo_hm(d):
    """«H» (homem), «M» (mulher) ou '' (não indicado)."""
    if isinstance(d, dict) and '_sexo' in d:
        return d['_sexo']
    return _sexo_bruto((d or {}).get('genero'))


def estatistica(incluidos, excluidos):
    """[(grupo, H, M, HM)]: gerados, excluídos e total do âmbito. HM conta todos (também os sem sexo indicado)."""
    def conta(lista):
        h = sum(1 for d in lista if sexo_hm(d) == 'H')
        m = sum(1 for d in lista if sexo_hm(d) == 'M')
        return h, m, len(lista)
    g, e = conta(list(incluidos)), conta([d for d, _ in excluidos])
    return [('Folha gerada', *g), ('Excluídos', *e), ('Total do âmbito', g[0] + e[0], g[1] + e[1], g[2] + e[2])]


def _escura(hex_cor):
    h = hex_cor.lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return (0.299 * r + 0.587 * g + 0.114 * b) < 140


def _linhas(todos, incluidos, excluidos):
    """[(linha, motivo|None)] pela ordem original do âmbito (todos), com a situação de cada aluno."""
    motivo = {id(d): m for d, m in excluidos}
    ids_incluidos = {id(d) for d in incluidos}
    ordem = [d for d in (todos or []) if id(d) in ids_incluidos or id(d) in motivo]
    vistos = {id(d) for d in ordem}
    ordem += [d for d in incluidos if id(d) not in vistos] + [d for d, _ in excluidos if id(d) not in vistos]
    saida = []
    for k, d in enumerate(ordem, start=1):
        m = motivo.get(id(d))
        saida.append(([k, d.get('numero') or '', d.get('codigo') or '', d.get('apelido') or '', d.get('nome') or '',
                       d.get('classe') or '', d.get('turma') or '', sexo_hm(d), f'Excluído: {m}' if m else 'Folha gerada'], m))
    return saida


def _tabela(linhas, estilos, cor):
    from reportlab.platypus import Table
    cab = ParagraphStyle('LAcab', parent=estilos['Normal'], alignment=TA_CENTER, fontName='Times-Bold', fontSize=12,
                         leading=15, textColor=colors.white)
    cel = ParagraphStyle('LAcel', parent=estilos['Normal'], alignment=TA_LEFT, fontName='Times-Roman', fontSize=12, leading=15)
    cen = ParagraphStyle('LAcen', parent=cel, alignment=TA_CENTER)
    claro = ParagraphStyle('LAclaro', parent=cel, textColor=colors.white)
    claro_c = ParagraphStyle('LAclaroc', parent=cen, textColor=colors.white)
    escura = _escura(cor)
    dados = [[Paragraph(nome, cab) for nome, _ in COLUNAS]]
    for linha, motivo in linhas:
        dados.append([Paragraph(str(v), (claro_c if COLUNAS[i][0] in CENTRADAS else claro) if (motivo and escura)
                                else (cen if COLUNAS[i][0] in CENTRADAS else cel)) for i, v in enumerate(linha)])
    t = Table(dados, colWidths=[w * cm for _, w in COLUNAS], repeatRows=1)
    est = [
        ('BACKGROUND', (0, 0), (-1, 0), AZUL), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1.2, AZUL), ('LINEBELOW', (0, 0), (-1, 0), 2.2, DOURADO),
        ('INNERGRID', (0, 1), (-1, -1), 0.4, CINZA), ('LINEAFTER', (0, 0), (-2, 0), 0.4, colors.HexColor('#5B74B8')),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]
    for r, (_, motivo) in enumerate(linhas, start=1):
        if motivo:
            est.append(('BACKGROUND', (0, r), (-1, r), colors.HexColor(cor)))
        elif r % 2 == 0:
            est.append(('BACKGROUND', (0, r), (-1, r), ZEBRA))
    t.setStyle(TableStyle(est))
    return t


def _tabela_estatistica(incluidos, excluidos, estilos, cor):
    from reportlab.platypus import Table
    cab = ParagraphStyle('LAecab', parent=estilos['Normal'], alignment=TA_CENTER, fontName='Times-Bold', fontSize=12, leading=15, textColor=colors.white)
    cel = ParagraphStyle('LAecel', parent=estilos['Normal'], alignment=TA_LEFT, fontName='Times-Roman', fontSize=12, leading=15)
    cen = ParagraphStyle('LAecen', parent=cel, alignment=TA_CENTER)
    escura = _escura(cor)
    dados = [[Paragraph(t, cab) for t in ('Estatística', 'H', 'M', 'HM')]]
    for k, (g, h, m, hm) in enumerate(estatistica(incluidos, excluidos), start=1):
        sc, sn = (ParagraphStyle('LAeW1', parent=cel, textColor=colors.white), ParagraphStyle('LAeW2', parent=cen, textColor=colors.white)) \
            if (k == 2 and escura) else (cel, cen)
        dados.append([Paragraph(g if g != 'Total do âmbito' else f'<b>{g}</b>', sc)] + [Paragraph(str(v), sn) for v in (h, m, hm)])
    t = Table(dados, colWidths=[5 * cm, 2.2 * cm, 2.2 * cm, 2.2 * cm], hAlign='LEFT')
    est = [('BACKGROUND', (0, 0), (-1, 0), AZUL), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('BOX', (0, 0), (-1, -1), 1.2, AZUL),
           ('LINEBELOW', (0, 0), (-1, 0), 2.2, DOURADO), ('INNERGRID', (0, 1), (-1, -1), 0.4, CINZA),
           ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3), ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor(cor))]
    t.setStyle(TableStyle(est))
    return t


def lista_pdf(escola, titulo, dados_incluidos, excluidos=(), referencia='', todos=None, cor=None):
    """PDF A4: cabeçalho oficial, totais e UMA tabela com todos os alunos; os excluídos levam outra cor e o motivo."""
    cor = cor_valida(cor)
    excluidos = list(excluidos)
    preparar_sexo(dados_incluidos, [d for d, _ in excluidos], todos)
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
    el.append(Paragraph(f'<b>Total de folhas/provas geradas: {len(dados_incluidos)}</b>'
                        + (f' · <b>Excluídos: {len(excluidos)}</b> (linhas coloridas, com o motivo)' if excluidos else '')
                        + f' · Emitido em {datetime.date.today().strftime("%d/%m/%Y")}', norm))
    el.append(Spacer(1, 0.2 * cm))
    el.append(_tabela_estatistica(dados_incluidos, excluidos, estilos, cor))
    el.append(Spacer(1, 0.3 * cm))
    el.append(_tabela(_linhas(todos, dados_incluidos, excluidos), estilos, cor))
    doc.build(el)
    return buf.getvalue()


def lista_xlsx(escola, titulo, dados_incluidos, excluidos=(), referencia='', todos=None, cor=None):
    """Excel (gravado por guardar_xlsx_seguro), folha «Alunos»: estatística H/M/HM e lista com os excluídos a outra cor e o motivo."""
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    excluidos = list(excluidos)
    preparar_sexo(dados_incluidos, [d for d, _ in excluidos], todos)

    from .xlsx_seguro import guardar_xlsx_seguro

    cor = cor_valida(cor)
    TNR = 'Times New Roman'
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Alunos'
    ws.sheet_view.showGridLines = False
    hoje = datetime.date.today().strftime('%d/%m/%Y')
    ws.cell(row=1, column=1, value=f'{titulo} · {escola.nome}').font = Font(name=TNR, size=12, bold=True)
    resumo = f'Total de folhas/provas geradas: {len(dados_incluidos)}'
    if excluidos:
        resumo += f' · Excluídos: {len(excluidos)} (linhas coloridas, com o motivo)'
    ws.cell(row=2, column=1, value=resumo + f' · Emitido em {hoje}' + (f' · {referencia}' if referencia else '')).font = Font(name=TNR, size=12)
    larguras = [8, 8, 24, 22, 28, 12, 12, 8, 40]
    escura = _escura(cor)
    # estatística H / M / HM dos dois grupos (gerados e excluídos) na mesma lista
    for i, t in enumerate(('Estatística', 'H', 'M', 'HM'), start=1):
        c = ws.cell(row=4, column=i + 2, value=t)
        c.font = Font(name=TNR, size=12, bold=True, color='FFFFFF')
        c.fill = PatternFill('solid', start_color='1E3A8A')
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    for k, (g, h, m, hm) in enumerate(estatistica(dados_incluidos, excluidos), start=5):
        for i, v in enumerate((g, h, m, hm), start=1):
            c = ws.cell(row=k, column=i + 2, value=v)
            c.font = Font(name=TNR, size=12, bold=(g == 'Total do âmbito'), color='FFFFFF' if (k == 6 and escura) else '000000')
            c.alignment = Alignment(horizontal='left' if i == 1 else 'center', vertical='center', wrap_text=True)
            if k == 6:
                c.fill = PatternFill('solid', start_color=cor.lstrip('#'))
    ini = 9
    for i, ((nome_col, _), w) in enumerate(zip(COLUNAS, larguras), start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
        c = ws.cell(row=ini, column=i, value=nome_col)
        c.font = Font(name=TNR, size=12, bold=True, color='FFFFFF')
        c.fill = PatternFill('solid', start_color='1E3A8A')
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    for r, (linha, motivo) in enumerate(_linhas(todos, dados_incluidos, excluidos), start=ini + 1):
        for i, v in enumerate(linha, start=1):
            c = ws.cell(row=r, column=i, value=v)
            c.font = Font(name=TNR, size=12, color='FFFFFF' if (motivo and escura) else '000000')
            c.alignment = Alignment(horizontal='center' if COLUNAS[i - 1][0] in CENTRADAS else 'left', vertical='center', wrap_text=True)
            if motivo:
                c.fill = PatternFill('solid', start_color=cor.lstrip('#'))
    ws.page_setup.orientation = 'portrait'
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr = openpyxl.worksheet.properties.PageSetupProperties(fitToPage=True)
    return guardar_xlsx_seguro(wb)
