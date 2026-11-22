"""Lista de resultados de uma avaliação corrigida (PDF e Excel).

Colunas: Nº, Código do aluno, Nome completo, Turma, Classe, Acertos, Nota (0–20), Resultado, Estado; e, no cabeçalho,
escola, disciplina, tipo de avaliação, trimestre, ano lectivo, turma, classe, professor e data de emissão, com um
quadro-resumo (alunos, corrigidas, positivas, negativas, média, aproveitamento) e espaço para assinaturas.
Regras de formato: docs/REGRAS_EXCEL_E_PDF.md (Times New Roman, cabeçalhos centrados, nada sobreposto, notas
negativas a vermelho, Excel gravado por guardar_xlsx_seguro).
"""
import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import KeepTogether

from apps.alunos.models import Aluno
from apps.documentos.services.pdf_service import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, gerar_cabecalho_mec, getSampleStyleSheet,
)

from .models import CorrecaoProva, FolhaPendente

AZUL = colors.HexColor('#1E3A8A')
AZUL_CLARO = colors.HexColor('#DBEAFE')
DOURADO = colors.HexColor('#C9A227')
ZEBRA = colors.HexColor('#F1F5F9')
CINZA = colors.HexColor('#94A3B8')
AMBAR = colors.HexColor('#FEF3C7')
VERMELHO = '#C00000'
VERDE = '#166534'
PERIODOS = {'1_TRIMESTRE': '1.º Trimestre', '2_TRIMESTRE': '2.º Trimestre', '3_TRIMESTRE': '3.º Trimestre'}
ESTADOS = {'RASCUNHO': 'Incompleta', 'CORRIGIDA': 'Corrigida', 'LANCADA': 'Lançada'}
COLUNAS = ['Nº', 'Código do aluno', 'Nome completo', 'Turma', 'Classe', 'Acertos', 'Nota (0–20)', 'Resultado', 'Estado']
I_NOTA = 6          # posição da nota nas linhas


def _fmt(v):
    return f'{float(v):.1f}'.replace('.', ',')


def montar(prova, professor_nome=''):
    """Dados da lista: (cabecalho: dict, linhas: list[list]). Todos os alunos activos da turma, por ordem alfabética,
    e no fim as folhas corrigidas ainda sem aluno atribuído."""
    correcoes = {c.aluno_id: c for c in CorrecaoProva.objects.filter(prova=prova)}
    n_mc = sum(1 for p in prova.perguntas if p.get('tipo') == 'MC')
    classe_turma = getattr(prova.turma, 'grau_ano', '') or ''
    linhas = []
    alunos = Aluno.objects.filter(escola=prova.escola, turma=prova.turma, status='ATIVO').order_by('nome')
    for i, a in enumerate(alunos, 1):
        c = correcoes.get(a.id)
        classe = a.classe or classe_turma
        if c and c.estado != 'RASCUNHO':
            chave = prova.gabaritos.get(c.versao or '-') or (next(iter(prova.gabaritos.values()), '') if prova.gabaritos else '')
            acertos = sum(1 for x, y in zip(c.respostas, chave) if x == y) if c.respostas else None
            linhas.append([i, a.matricula or '', a.nome, prova.turma.nome, classe,
                           '—' if acertos is None else f'{acertos}/{n_mc}', float(c.nota),
                           'Positiva' if c.nota >= 10 else 'Negativa', ESTADOS.get(c.estado, c.estado)])
        else:
            linhas.append([i, a.matricula or '', a.nome, prova.turma.nome, classe, '—', None, '—',
                           ESTADOS.get(c.estado, 'Sem correcção') if c else 'Sem correcção'])
    sem_aluno = 0
    for f in FolhaPendente.objects.filter(prova=prova).order_by('origem', 'pagina'):
        sem_aluno += 1
        chave = prova.gabaritos.get(f.versao or '-') or (next(iter(prova.gabaritos.values()), '') if prova.gabaritos else '')
        acertos = f.acertos if f.acertos is not None else (sum(1 for x, y in zip(f.respostas, chave) if x == y) if f.respostas else None)
        linhas.append(['—', '—', f'Por identificar · {f.origem} (pág. {f.pagina})', prova.turma.nome, classe_turma,
                       '—' if acertos is None else f'{acertos}/{n_mc}', None if f.nota is None else float(f.nota),
                       '—' if f.nota is None else ('Positiva' if f.nota >= 10 else 'Negativa'), 'Sem aluno'])
    notas = [l[I_NOTA] for l in linhas if l[I_NOTA] is not None]
    cab = {
        'escola': prova.escola, 'disciplina': prova.disciplina.nome, 'tipo': prova.get_instrumento_display(),
        'titulo': prova.titulo, 'periodo': PERIODOS.get(prova.periodo, prova.periodo), 'ano': prova.turma.ano_letivo,
        'turma': prova.turma.nome, 'classe': classe_turma, 'professor': professor_nome,
        'emitido': date.today().strftime('%d/%m/%Y'), 'corrigidas': len(notas), 'total': len(linhas), 'sem_aluno': sem_aluno,
        'positivas': sum(1 for n in notas if n >= 10), 'negativas': sum(1 for n in notas if n < 10),
        'media': (sum(notas) / len(notas)) if notas else None,
        'maior': max(notas) if notas else None, 'menor': min(notas) if notas else None,
        'aproveitamento': (100.0 * sum(1 for n in notas if n >= 10) / len(notas)) if notas else None,
    }
    return cab, linhas


def _esc(t):
    return str(t if t is not None else '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def nome_ficheiro(cab, extensao):
    import re
    return re.sub(r'[\\/:*?"<>|\r\n]+', ' ', f'Lista de notas - {cab["disciplina"]} - {cab["tipo"]} - {cab["ano"]}').strip() + '.' + extensao


def _pct(v):
    return '—' if v is None else f'{v:.0f}%'.replace('.', ',')


class _NumeradoCanvas(rl_canvas.Canvas):
    """Rodapé em todas as páginas: «Documento emitido pelo SIGE · Página x de y»."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._paginas = []

    def showPage(self):
        self._paginas.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._paginas)
        for estado in self._paginas:
            self.__dict__.update(estado)
            self._rodape(total)
            super().showPage()
        super().save()

    def _rodape(self, total):
        larg, _alt = self._pagesize
        self.setStrokeColor(AZUL)
        self.setLineWidth(0.8)
        self.line(1.5 * cm, 1.05 * cm, larg - 1.5 * cm, 1.05 * cm)
        self.setFont('Times-Roman', 9)
        self.setFillColor(colors.HexColor('#475569'))
        self.drawString(1.5 * cm, 0.6 * cm, 'Documento emitido pelo SIGE — Sistema Integrado de Gestão Escolar')
        self.drawRightString(larg - 1.5 * cm, 0.6 * cm, f'Página {self._pageNumber} de {total}')


def pdf_lista(cab, linhas):
    buf = io.BytesIO()
    escola = cab['escola']
    pagina = landscape(A4)
    util = pagina[0] - 3.0 * cm                      # 26,7 cm
    styles = getSampleStyleSheet()
    el = gerar_cabecalho_mec(styles, escola.nome, escola.provincia, escola.distrito, compacto=True, escola=escola)
    el.append(Paragraph('<b>LISTA DE RESULTADOS DA AVALIAÇÃO CORRIGIDA</b>',
                        ParagraphStyle('LaT', fontName='Times-Bold', alignment=1, textColor=AZUL)))
    el.append(Spacer(1, 0.2 * cm))
    sb, sr = ParagraphStyle('LaB', fontName='Times-Bold'), ParagraphStyle('LaR', fontName='Times-Roman')
    turma_txt = cab['turma'] + (f' ({cab["classe"]})' if cab['classe'] else '')
    info = [['Disciplina', cab['disciplina'], 'Tipo de avaliação', cab['tipo'], 'Trimestre', cab['periodo']],
            ['Turma / Classe', turma_txt, 'Avaliação', cab['titulo'], 'Ano lectivo', cab['ano']],
            ['Professor(a)', cab['professor'] or '—', 'Emitida em', cab['emitido'], 'Alunos', cab['total']]]
    wi = [2.7 * cm, 6.2 * cm, 3.3 * cm, 7.0 * cm, 2.6 * cm, util - 21.8 * cm]
    ti = Table([[Paragraph(_esc(c), sb if k % 2 == 0 else sr) for k, c in enumerate(r)] for r in info], colWidths=wi)
    ti.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1.2, AZUL), ('INNERGRID', (0, 0), (-1, -1), 0.4, CINZA), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (0, -1), AZUL_CLARO), ('BACKGROUND', (2, 0), (2, -1), AZUL_CLARO), ('BACKGROUND', (4, 0), (4, -1), AZUL_CLARO),
        ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2)]))
    el += [ti, Spacer(1, 0.25 * cm)]

    # quadro-resumo
    sk = ParagraphStyle('LaK', fontName='Times-Roman', alignment=1, fontSize=9, leading=11, textColor=colors.HexColor('#475569'))
    sv = ParagraphStyle('LaV', fontName='Times-Bold', alignment=1, fontSize=16, leading=19, textColor=AZUL)
    kp = [('Corrigidas', f'{cab["corrigidas"]} / {cab["total"]}'), ('Positivas', str(cab['positivas'])), ('Negativas', str(cab['negativas'])),
          ('Média da turma', '—' if cab['media'] is None else _fmt(cab['media'])),
          ('Maior nota', '—' if cab['maior'] is None else _fmt(cab['maior'])), ('Menor nota', '—' if cab['menor'] is None else _fmt(cab['menor'])),
          ('Aproveitamento', _pct(cab['aproveitamento']))]
    tk = Table([[Paragraph(f'<font color="{VERMELHO if k[0] == "Negativas" and cab["negativas"] else "#1E3A8A"}">{_esc(k[1])}</font>', sv) for k in kp],
                [Paragraph(_esc(k[0]), sk) for k in kp]], colWidths=[util / len(kp)] * len(kp))
    tk.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), 1.2, AZUL), ('LINEAFTER', (0, 0), (-2, -1), 0.4, CINZA),
                            ('BACKGROUND', (0, 0), (-1, -1), ZEBRA), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('TOPPADDING', (0, 0), (-1, 0), 4), ('BOTTOMPADDING', (0, 1), (-1, 1), 4)]))
    el += [tk, Spacer(1, 0.3 * cm)]

    st_h = ParagraphStyle('LaH', fontName='Times-Bold', alignment=1, textColor=colors.white)
    st_c = ParagraphStyle('LaC', fontName='Times-Roman')
    st_m = ParagraphStyle('LaM', fontName='Times-Roman', alignment=1)
    dados = [[Paragraph(_esc(h), st_h) for h in COLUNAS]]
    for ln in linhas:
        cel = []
        for k, v in enumerate(ln):
            if k == I_NOTA:
                txt = '—' if v is None else _fmt(v)
                cor = VERMELHO if (v is not None and v < 10) else '#000000'
                cel.append(Paragraph(f'<font color="{cor}"><b>{txt}</b></font>', st_m))
            elif k == I_NOTA + 1 and v in ('Positiva', 'Negativa'):
                cel.append(Paragraph(f'<font color="{VERDE if v == "Positiva" else VERMELHO}"><b>{v}</b></font>', st_m))
            else:
                cel.append(Paragraph(_esc(v), st_c if k in (1, 2) else st_m))
        dados.append(cel)
    if not linhas:
        dados.append([Paragraph('Esta turma não tem alunos activos.', st_c)] + [''] * (len(COLUNAS) - 1))
    larg = [1.0 * cm, 5.4 * cm, 6.0 * cm, 2.3 * cm, 2.6 * cm, 2.2 * cm, 1.9 * cm, 2.7 * cm]
    larg.append(util - sum(larg))
    t = Table(dados, colWidths=larg, repeatRows=1)
    cmds = [('BACKGROUND', (0, 0), (-1, 0), AZUL), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1.4, AZUL), ('LINEBELOW', (0, 0), (-1, 0), 1.8, DOURADO),
            ('LINEBEFORE', (0, 1), (-1, -1), 0.4, colors.HexColor('#CBD5E1')),
            ('LINEBELOW', (0, 1), (-1, -2), 0.4, CINZA), ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]
    if not linhas:
        cmds.append(('SPAN', (0, 1), (-1, 1)))
    for i, ln in enumerate(linhas, start=1):
        if ln[0] == '—':
            cmds.append(('BACKGROUND', (0, i), (-1, i), AMBAR))
        elif i % 2 == 0:
            cmds.append(('BACKGROUND', (0, i), (-1, i), ZEBRA))
    t.setStyle(TableStyle(cmds))
    el.append(t)
    if cab.get('sem_aluno'):
        el += [Spacer(1, 0.15 * cm), Paragraph(
            f'<i>Linhas a amarelo: {cab["sem_aluno"]} folha(s) já corrigida(s) e guardada(s) cujo aluno ainda não foi identificado.</i>', sr)]
    # assinaturas
    sa = ParagraphStyle('LaA', fontName='Times-Roman', alignment=1)
    ta = Table([[Paragraph('_______________________________________', sa), '', Paragraph('_______________________________________', sa)],
                [Paragraph(f'O(A) Professor(a){(": " + _esc(cab["professor"])) if cab["professor"] else ""}', sa), '',
                 Paragraph('O(A) Director(a) Pedagógico(a)', sa)]], colWidths=[10 * cm, util - 20 * cm, 10 * cm])
    ta.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'BOTTOM')]))
    el.append(KeepTogether([Spacer(1, 1.1 * cm), ta]))
    SimpleDocTemplate(buf, pagesize=pagina, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.0 * cm,
                      bottomMargin=1.6 * cm).build(el, canvasmaker=_NumeradoCanvas)
    return buf.getvalue()


def xlsx_lista(cab, linhas):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    from apps.documentos.services.excel_service import configurar_pagina_excel, inserir_logo_cabecalho_xlsx
    from apps.documentos.services.xlsx_seguro import guardar_xlsx_seguro
    escola = cab['escola']
    wb = Workbook()
    ws = wb.active
    ws.title = 'Resultados'
    configurar_pagina_excel(ws, orientacao='landscape', fit_to_height=0)
    inserir_logo_cabecalho_xlsx(ws, escola, cell='A1')
    n = len(COLUNAS)                                   # 9 colunas
    fim = get_column_letter(n)
    tnr = lambda **kw: Font(name='Times New Roman', size=12, **kw)  # noqa: E731
    fina = Side(style='thin', color='94A3B8')
    borda = Border(left=fina, right=fina, top=fina, bottom=fina)      # marca as células como «tabela»: guardar_xlsx_seguro aplica a moldura profissional
    centro = Alignment(horizontal='center', vertical='center', wrap_text=True)
    esq = Alignment(horizontal='left', vertical='center', wrap_text=True)
    for col, larg in zip('ABCDEFGHI', (6, 30, 44, 10, 12, 11, 12, 13, 14)):
        ws.column_dimensions[col].width = larg

    def linha_fundida(r, texto, fonte, alt, cor=None):
        ws.merge_cells(f'A{r}:{fim}{r}')
        c = ws.cell(r, 1, texto)
        c.font, c.alignment = fonte, centro
        if cor:
            c.fill = PatternFill('solid', fgColor=cor)
        ws.row_dimensions[r].height = alt

    linha_fundida(1, 'REPÚBLICA DE MOÇAMBIQUE', tnr(bold=True), 50)           # (o logótipo fica sobre esta linha)
    linha_fundida(2, (escola.nome or '').upper(), tnr(bold=True), 22)
    linha_fundida(3, 'LISTA DE RESULTADOS DA AVALIAÇÃO CORRIGIDA', tnr(bold=True, color='1E3A8A'), 24)
    turma_txt = cab['turma'] + (f' ({cab["classe"]})' if cab['classe'] else '')
    pares = [(('Disciplina', cab['disciplina']), ('Tipo de avaliação', cab['tipo']), ('Trimestre', cab['periodo'])),
             (('Turma / Classe', turma_txt), ('Avaliação', cab['titulo']), ('Ano lectivo', cab['ano'])),
             (('Professor(a)', cab['professor'] or '—'), ('Emitida em', cab['emitido']), ('Alunos', cab['total']))]
    r = 5
    for trio in pares:
        # A:B rótulo+valor 1, C:E rótulo+valor 2 (fundido), F:I rótulo+valor 3
        blocos = [(1, 2, trio[0]), (3, 5, trio[1]), (6, 9, trio[2])]
        for c1, c2, (rot, val) in blocos:
            ws.merge_cells(start_row=r, start_column=c1, end_row=r, end_column=c2)
            c = ws.cell(r, c1, f'{rot}: {val}')
            c.font, c.alignment = tnr(), esq
            c.fill = PatternFill('solid', fgColor='EFF6FF')
            c.border = borda
        ws.row_dimensions[r].height = 22
        r += 1
    r += 1
    media = '—' if cab['media'] is None else _fmt(cab['media'])
    resumo = (f'Corrigidas: {cab["corrigidas"]} de {cab["total"]}   ·   Positivas: {cab["positivas"]}   ·   '
              f'Negativas: {cab["negativas"]}   ·   Média: {media}   ·   Aproveitamento: {_pct(cab["aproveitamento"])}')
    linha_fundida(r, resumo, tnr(bold=True), 24, 'F1F5F9')
    ws.cell(r, 1).border = borda
    r += 2
    for k, h in enumerate(COLUNAS, 1):                                   # cabeçalho da tabela (azul, letra branca, centrado)
        c = ws.cell(r, k, h)
        c.fill = PatternFill('solid', fgColor='1E3A8A')
        c.font = tnr(bold=True, color='FFFFFF')
        c.alignment = centro
        c.border = borda
    ws.row_dimensions[r].height = 30
    ws.freeze_panes = ws.cell(r + 1, 1)
    for ln in linhas:
        r += 1
        for k, v in enumerate(ln, 1):
            if k - 1 == I_NOTA:
                c = ws.cell(r, k, '—' if v is None else round(v, 1))
                if v is not None:
                    c.number_format = '0.0'
            else:
                c = ws.cell(r, k, v)
            neg = (k - 1 == I_NOTA and v is not None and v < 10) or (k - 1 == I_NOTA + 1 and v == 'Negativa')
            c.font = tnr(bold=(k - 1 in (I_NOTA, I_NOTA + 1)), color=('C00000' if neg else ('166534' if v == 'Positiva' else '000000')))
            c.alignment = esq if k in (2, 3) else centro
            c.border = borda
            if ln[0] == '—':
                c.fill = PatternFill('solid', fgColor='FEF3C7')
        ws.row_dimensions[r].height = 22
    if not linhas:
        r += 1
        ws.merge_cells(f'A{r}:{fim}{r}')
        ws.cell(r, 1, 'Esta turma não tem alunos activos.').alignment = centro
    r += 2
    if cab.get('sem_aluno'):
        ws.merge_cells(f'A{r}:{fim}{r}')
        c = ws.cell(r, 1, f'Linhas a amarelo: {cab["sem_aluno"]} folha(s) corrigida(s) e guardada(s) cujo aluno ainda não foi identificado.')
        c.font, c.alignment = tnr(italic=True), esq
        r += 2
    ws.merge_cells(f'A{r}:D{r}')
    ws.merge_cells(f'F{r}:{fim}{r}')
    ws.cell(r, 1, '_____________________________________').alignment = centro
    ws.cell(r, 6, '_____________________________________').alignment = centro
    r += 1
    ws.merge_cells(f'A{r}:D{r}')
    ws.merge_cells(f'F{r}:{fim}{r}')
    ws.cell(r, 1, 'O(A) Professor(a)' + (f': {cab["professor"]}' if cab['professor'] else '')).alignment = centro
    ws.cell(r, 6, 'O(A) Director(a) Pedagógico(a)').alignment = centro
    ws.print_options.horizontalCentered = True
    return guardar_xlsx_seguro(wb)
