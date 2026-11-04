"""Resumo e exportação (PDF/XLSX) da assiduidade dos alunos.

Tudo vem de registos reais de PresencaAluno; sem registos os documentos mostram apenas o estado vazio.
Tipografia oficial: Times New Roman.
"""
import io

from django.db.models import Count, Q

COLUNAS = ['N.º', 'Matrícula', 'Nome do aluno', 'Aulas', 'Presenças', 'F. justif.', 'F. injustif.', 'Atrasos', '% Faltas']


def calcular_resumo(qs, limite=None):
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
    for l in linhas:
        faltas = l['justificadas'] + l['injustificadas']
        out.append({
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
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


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
