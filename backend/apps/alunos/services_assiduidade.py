"""Resumo e exportação (PDF/XLSX) da assiduidade dos alunos.

Tudo vem de registos reais de PresencaAluno; sem registos os documentos mostram apenas o estado vazio.
Tipografia oficial: Times New Roman.
"""
import io

from apps.documentos.services.xlsx_seguro import guardar_xlsx_seguro
from django.db.models import Count, Q

COLUNAS = ['N.º', 'Matrícula', 'Nome do aluno', 'Aulas', 'Presenças', 'F. justif.', 'F. injustif.', 'Atrasos', '% Faltas']


STATUS_FALTA = ('FALTA_JUSTIFICADA', 'FALTA_INJUSTIFICADA')
COLUNAS_GERAL = ['N.º', 'Matrícula', 'Nome do aluno', 'Classe', 'Turma', 'Secção / Área', 'Disciplina',
                 'Faltas 1.º Trim.', 'Faltas 2.º Trim.', 'Faltas 3.º Trim.', 'Total de faltas']


def _intervalos_trimestres(escola):
    """{1: (ini, fim), ...} com as datas configuradas na escola (omite trimestres sem datas)."""
    out = {}
    for t in (1, 2, 3):
        ini, fim = getattr(escola, f'data_inicio_t{t}', None), getattr(escola, f'data_fim_t{t}', None)
        if ini and fim:
            out[t] = (ini, fim)
    return out


def trimestre_da_data(data, escola):
    """Trimestre (1-3) a que pertence a data. Sem datas configuradas na escola usa o calendário
    lectivo por meses (jan-abr, mai-ago, set-dez); datas fora dos intervalos configurados -> None."""
    intervalos = _intervalos_trimestres(escola)
    if intervalos:
        for t, (ini, fim) in intervalos.items():
            if ini <= data <= fim:
                return t
        return None
    return 1 if data.month <= 4 else 2 if data.month <= 8 else 3


def soma_faltas(qs, escola, chaves):
    """Faltas ponderadas (aula simples = 1, aula dupla = 2) por (chaves..., trimestre).
    `chaves` são campos de `values()`. Devolve {tuplo_chaves: {1: n, 2: n, 3: n}}."""
    out = {}
    for r in qs.order_by().filter(status__in=STATUS_FALTA).values(*chaves, 'data', 'aulas'):
        t = trimestre_da_data(r['data'], escola)
        if t is None:
            continue
        k = tuple(str(r[c]) for c in chaves)
        out.setdefault(k, {1: 0, 2: 0, 3: 0})[t] += r['aulas'] or 1
    return out


def calcular_geral(qs, escola):
    """Lista geral de faltas acumuladas por aluno e disciplina (1.º, 2.º, 3.º trimestre e total)."""
    faltas = soma_faltas(qs, escola, ('aluno_id', 'disciplina_id'))
    base = qs.order_by().values(
        'aluno_id', 'aluno__matricula', 'aluno__nome', 'aluno__apelido', 'disciplina_id',
        'disciplina__nome', 'turma__nome', 'turma__grau_ano', 'turma__area',
    ).distinct()
    linhas = []
    for l in base:
        f = faltas.get((str(l['aluno_id']), str(l['disciplina_id'])), {1: 0, 2: 0, 3: 0})
        linhas.append({
            'aluno': str(l['aluno_id']), 'matricula': l['aluno__matricula'],
            'nome': f"{l['aluno__nome']} {l['aluno__apelido'] or ''}".strip(),
            'classe': l['turma__grau_ano'] or '', 'turma': l['turma__nome'] or '',
            'area': l['turma__area'] or '', 'disciplina_id': str(l['disciplina_id'] or ''),
            'disciplina': l['disciplina__nome'] or '',
            'f1': f[1], 'f2': f[2], 'f3': f[3], 'total': f[1] + f[2] + f[3],
        })
    linhas.sort(key=lambda x: (x['classe'], x['turma'], x['nome'].lower(), x['disciplina']))
    return linhas


def _linhas_geral(geral):
    return [[i, r['matricula'], r['nome'], r['classe'], r['turma'], r['area'], r['disciplina'],
             r['f1'], r['f2'], r['f3'], r['total']] for i, r in enumerate(geral, start=1)]


def gerar_geral_xlsx(geral, escola, filtros):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, Side
    wb = Workbook()
    ws = wb.active
    ws.title = 'Faltas acumuladas'
    n = len(COLUNAS_GERAL)
    ws.append([(escola.nome if escola else '').upper()])
    ws.append(['LISTA GERAL DE FALTAS ACUMULADAS'])
    ws.append([_subtitulo(filtros)])
    ws.append([])
    for r in (1, 2):
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=n)
        ws.cell(r, 1).font = Font(name='Times New Roman', size=13, bold=True)
        ws.cell(r, 1).alignment = Alignment(horizontal='center')
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=n)
    ws.cell(3, 1).font = Font(name='Times New Roman', size=12, italic=True)
    ws.cell(3, 1).alignment = Alignment(horizontal='center')
    ws.append(COLUNAS_GERAL)
    lado = Side(style='thin', color='FF000000')
    borda = Border(left=lado, right=lado, top=lado, bottom=lado)
    for c in ws[5]:
        c.font = Font(name='Times New Roman', size=12, bold=True)
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        c.border = borda
    if not geral:
        ws.append(['Sem registos de faltas para os filtros indicados.'])
    for linha in _linhas_geral(geral):
        ws.append(linha)
    for row in ws.iter_rows(min_row=6):
        for c in row:
            c.font = Font(name='Times New Roman', size=12)
            if geral:
                c.border = borda
                c.alignment = Alignment(horizontal='left' if c.column in (3, 7) else 'center', vertical='center')
    for i, w in enumerate([6, 16, 34, 9, 12, 16, 26, 13, 13, 13, 14], start=1):
        ws.column_dimensions[chr(64 + i)].width = w
    return guardar_xlsx_seguro(wb)


def gerar_geral_pdf(geral, escola, filtros):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from xml.sax.saxutils import escape
    s_c = ParagraphStyle('GC', fontName='Times-Bold', fontSize=12, leading=16, alignment=1)
    s_s = ParagraphStyle('GS', fontName='Times-Italic', fontSize=9, leading=12, alignment=1)
    s_n = ParagraphStyle('GN', fontName='Times-Roman', fontSize=9, leading=11)
    s_h = ParagraphStyle('GH', fontName='Times-Bold', fontSize=9, leading=11, alignment=1)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=1.2 * cm, rightMargin=1.2 * cm,
                            topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    el = [Paragraph(escape((escola.nome if escola else '').upper()), s_c),
          Paragraph('LISTA GERAL DE FALTAS ACUMULADAS', s_c),
          Paragraph(escape(_subtitulo(filtros)), s_s), Spacer(1, 0.4 * cm)]
    if not geral:
        el.append(Paragraph('Sem registos de faltas para os filtros indicados.', s_n))
    else:
        dados = [[Paragraph(escape(c), s_h) for c in COLUNAS_GERAL]]
        for l in _linhas_geral(geral):
            dados.append([l[0], l[1], Paragraph(escape(l[2]), s_n), l[3], l[4],
                          Paragraph(escape(l[5]), s_n), Paragraph(escape(l[6]), s_n)] + l[7:])
        tb = Table(dados, repeatRows=1, colWidths=[1 * cm, 2.6 * cm, 6 * cm, 1.5 * cm, 1.8 * cm, 2.6 * cm, 4.4 * cm,
                                                   1.7 * cm, 1.7 * cm, 1.7 * cm, 1.9 * cm])
        tb.setStyle(TableStyle([
            ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'), ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.black), ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ALIGN', (0, 1), (1, -1), 'CENTER'), ('ALIGN', (3, 1), (-1, -1), 'CENTER'),
            ('FONTNAME', (10, 1), (10, -1), 'Times-Bold'),
        ]))
        el.append(tb)
    doc.build(el)
    return buf.getvalue()


def calcular_resumo(qs, limite=None, escola=None):
    """Agrega por aluno. `qs` já filtrado e limitado ao tenant.
    `limite` (% de faltas da escola; None = desactivado) marca `em_risco` os alunos que o atingem."""
    linhas = qs.order_by().values('aluno_id', 'aluno__matricula', 'aluno__nome', 'aluno__apelido').annotate(
        total=Count('id'),
        presentes=Count('id', filter=Q(status='PRESENTE')),
        justificadas=Count('id', filter=Q(status='FALTA_JUSTIFICADA')),
        injustificadas=Count('id', filter=Q(status='FALTA_INJUSTIFICADA')),
        atrasos=Count('id', filter=Q(status='ATRASO')),
    ).order_by('-injustificadas', 'aluno__nome')
    out = []
    por_tri = soma_faltas(qs, escola, ('aluno_id',)) if escola is not None else {}
    for l in linhas:
        faltas = l['justificadas'] + l['injustificadas']
        ft = por_tri.get((str(l['aluno_id']),), {1: 0, 2: 0, 3: 0})
        out.append({
            'f1': ft[1], 'f2': ft[2], 'f3': ft[3], 'faltas_total': ft[1] + ft[2] + ft[3],
            'aluno': str(l['aluno_id']), 'matricula': l['aluno__matricula'],
            'nome': f"{l['aluno__nome']} {l['aluno__apelido'] or ''}".strip(),
            'total': l['total'], 'presentes': l['presentes'], 'justificadas': l['justificadas'],
            'injustificadas': l['injustificadas'], 'atrasos': l['atrasos'],
            'percent_faltas': round(100 * faltas / l['total'], 1) if l['total'] else 0,
        })
        out[-1]['em_risco'] = bool(limite) and out[-1]['percent_faltas'] >= limite
    return out


def _fmt_pct(v):
    return f'{v:.1f}'.replace('.', ',') + '%'


def _linhas_tabela(resumo):
    return [[i, r['matricula'], r['nome'], r['total'], r['presentes'], r['justificadas'],
             r['injustificadas'], r['atrasos'], _fmt_pct(r['percent_faltas'])]
            for i, r in enumerate(resumo, start=1)]


def _subtitulo(filtros):
    partes = [f'{k}: {v}' for k, v in filtros.items() if v]
    return ' | '.join(partes)


def gerar_xlsx(resumo, escola, filtros):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    wb = Workbook()
    ws = wb.active
    ws.title = 'Assiduidade'
    n = len(COLUNAS)
    ws.append([(escola.nome if escola else '').upper()])
    ws.append(['ASSIDUIDADE DOS ALUNOS'])
    ws.append([_subtitulo(filtros)])
    ws.append([])
    for r in (1, 2):
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=n)
        ws.cell(r, 1).font = Font(name='Times New Roman', size=13, bold=True)
        ws.cell(r, 1).alignment = Alignment(horizontal='center')
    ws.cell(3, 1).font = Font(name='Times New Roman', size=10, italic=True)
    ws.append(COLUNAS)
    for c in ws[5]:
        c.font = Font(name='Times New Roman', size=11, bold=True)
    if not resumo:
        ws.append(['Sem registos de assiduidade para os filtros indicados.'])
    for linha in _linhas_tabela(resumo):
        ws.append(linha)
    vermelho = Font(name='Times New Roman', size=11, color='FFC00000')
    normal = Font(name='Times New Roman', size=11)
    for row in ws.iter_rows(min_row=6):
        for c in row:
            c.font = normal
        # faltas injustificadas a vermelho
        if len(row) >= 7 and isinstance(row[6].value, int) and row[6].value > 0:
            row[6].font = vermelho
    for i, w in enumerate([6, 20, 36, 8, 11, 11, 13, 9, 10], start=1):
        ws.column_dimensions[chr(64 + i)].width = w
    return guardar_xlsx_seguro(wb)


def gerar_pdf(resumo, escola, filtros):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from xml.sax.saxutils import escape
    s_c = ParagraphStyle('AC', fontName='Times-Bold', fontSize=12, leading=16, alignment=1)
    s_s = ParagraphStyle('AS', fontName='Times-Italic', fontSize=9, leading=12, alignment=1)
    s_n = ParagraphStyle('AN', fontName='Times-Roman', fontSize=9, leading=11)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                            topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    el = [Paragraph(escape((escola.nome if escola else '').upper()), s_c),
          Paragraph('ASSIDUIDADE DOS ALUNOS', s_c),
          Paragraph(escape(_subtitulo(filtros)), s_s), Spacer(1, 0.4 * cm)]
    if not resumo:
        el.append(Paragraph('Sem registos de assiduidade para os filtros indicados.', s_n))
    else:
        dados = [COLUNAS] + [[l[0], l[1], Paragraph(escape(l[2]), s_n)] + l[3:] for l in _linhas_tabela(resumo)]
        tb = Table(dados, repeatRows=1, colWidths=[1.2 * cm, 3.4 * cm, 8 * cm, 1.8 * cm, 2.2 * cm, 2.2 * cm, 2.6 * cm, 1.8 * cm, 2 * cm])
        estilo = [
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'), ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 0), (-1, -1), 9), ('GRID', (0, 0), (-1, -1), 0.4, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (3, 1), (-1, -1), 'CENTER'),
        ]
        for i, l in enumerate(_linhas_tabela(resumo), start=1):
            if l[6] > 0:
                estilo.append(('TEXTCOLOR', (6, i), (6, i), colors.HexColor('#C00000')))
        tb.setStyle(TableStyle(estilo))
        el.append(tb)
    doc.build(el)
    return buf.getvalue()
