"""Resumo e exportação (PDF/XLSX) da assiduidade dos alunos.

Tudo vem de registos reais de PresencaAluno; sem registos os documentos mostram apenas o estado vazio.
Tipografia oficial: Times New Roman.
"""
import io

from apps.documentos.services.xlsx_seguro import guardar_xlsx_seguro
from django.db.models import Count, Q

COLUNAS = ['N.º', 'Matrícula', 'Nome do aluno', 'Aulas', 'Presenças', 'F. justif.', 'F. injustif.', 'Atrasos', '% Faltas']


STATUS_FALTA = ('FALTA_JUSTIFICADA', 'FALTA_INJUSTIFICADA')


def _intervalos_trimestres(escola):
    """{1: (ini, fim), ...} do «Calendário Oficial de Prazos de Lançamento» da escola
    (modo manual ou automático); omite trimestres sem datas."""
    from apps.notas.prazos_service import obter_configuracao_prazos
    cfg = obter_configuracao_prazos(escola) if escola is not None else {}
    out = {}
    for t in (1, 2, 3):
        c = cfg.get(f'{t}_TRIMESTRE') or {}
        if c.get('inicio') and c.get('fim'):
            out[t] = (c['inicio'], c['fim'])
    return out


def trimestre_da_data(data, escola):
    """Trimestre (1-3) a que pertence a data, segundo o calendário de prazos da escola. Sem datas
    configuradas usa o calendário lectivo por meses (jan-abr, mai-ago, set-dez); fora dos intervalos -> None."""
    intervalos = _intervalos_trimestres(escola)
    if intervalos:
        for t, (ini, fim) in intervalos.items():
            if ini <= data <= fim:
                return t
        return None
    return 1 if data.month <= 4 else 2 if data.month <= 8 else 3


def agregar_faltas(qs, escola, chaves):
    """Faltas por (chaves..., trimestre): {chave: {'b': {1,2,3}, 'j': {1,2,3}}} onde b = brutas
    (aula simples 1, dupla 2) e j = justificadas. Efectivas = b - j."""
    out = {}
    cache = {}
    for r in qs.order_by().filter(status__in=STATUS_FALTA).values(*chaves, 'data', 'aulas', 'aulas_justificadas'):
        if r['data'] not in cache:
            cache[r['data']] = trimestre_da_data(r['data'], escola)
        t = cache[r['data']]
        if t is None:
            continue
        k = tuple(str(r[c]) for c in chaves)
        d = out.setdefault(k, {'b': {1: 0, 2: 0, 3: 0}, 'j': {1: 0, 2: 0, 3: 0}})
        d['b'][t] += r['aulas'] or 1
        d['j'][t] += min(r['aulas_justificadas'] or 0, r['aulas'] or 1)
    return out


def soma_faltas(qs, escola, chaves):
    """Faltas efectivas (brutas - justificadas) por (chaves..., trimestre): {chave: {1: n, 2: n, 3: n}}."""
    return {k: {t: v['b'][t] - v['j'][t] for t in (1, 2, 3)} for k, v in agregar_faltas(qs, escola, chaves).items()}


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
