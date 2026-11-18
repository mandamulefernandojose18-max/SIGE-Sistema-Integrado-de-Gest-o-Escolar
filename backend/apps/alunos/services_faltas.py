"""Estrutura avançada das faltas: lista geral (aluno × disciplina × trimestre), detalhe por data,
justificação por quantidade (reduz as faltas efectivas) e exportações PDF/Excel.

Regras:
- aula simples = 1 falta; aula dupla = 2 faltas (automático, campo PresencaAluno.aulas);
- faltas efectivas = faltas brutas - faltas justificadas;
- o trimestre de cada falta vem do «Calendário Oficial de Prazos de Lançamento» da escola.
Só dados reais (PresencaAluno); sem registos os documentos mostram o estado vazio.
"""
import io
from xml.sax.saxutils import escape

from django.db import transaction
from django.utils import timezone
from reportlab.lib import colors

from apps.documentos.services.xlsx_seguro import guardar_xlsx_seguro

from .models import JustificacaoFalta, PresencaAluno
from .services_assiduidade import STATUS_FALTA, _intervalos_trimestres, agregar_faltas, trimestre_da_data

ROT_TRIM = {1: '1.º Trimestre', 2: '2.º Trimestre', 3: '3.º Trimestre'}


def periodo_do_calendario(escola, periodo):
    """(inicio, fim) de 'T1'|'T2'|'T3' segundo o Calendário Oficial de Prazos; None se não configurado."""
    try:
        t = int(str(periodo)[-1])
    except ValueError:
        return None
    return _intervalos_trimestres(escola).get(t)


def _sigla(codigo, nome):
    c = (codigo or '').strip()
    if c:
        return c.title()
    return (nome or '')[:3].title()


# --------------------------------------------------------------------------- lista geral (pivot)

def montar_pivot(qs, escola):
    """Uma linha por aluno; disciplinas na horizontal, cada uma com faltas efectivas do 1.º/2.º/3.º trimestre."""
    agg = agregar_faltas(qs, escola, ('aluno_id', 'disciplina_id'))
    base = qs.order_by().values(
        'aluno_id', 'aluno__matricula', 'aluno__nome', 'aluno__apelido', 'turma__nome', 'turma__grau_ano',
        'turma__area', 'disciplina_id', 'disciplina__nome', 'disciplina__codigo',
    ).distinct()
    discs, alunos = {}, {}
    for l in base:
        did = str(l['disciplina_id'] or '')
        discs.setdefault(did, {'id': did, 'nome': l['disciplina__nome'] or 'Sem disciplina',
                               'sigla': _sigla(l['disciplina__codigo'], l['disciplina__nome'])})
        aid = str(l['aluno_id'])
        al = alunos.setdefault(aid, {
            'aluno': aid, 'matricula': l['aluno__matricula'],
            'nome': f"{l['aluno__nome']} {l['aluno__apelido'] or ''}".strip(),
            'classe': l['turma__grau_ano'] or '', 'turma': l['turma__nome'] or '', 'area': l['turma__area'] or '',
            'disc': {}, 'total': 0, 'justificadas_total': 0,
        })
        a = agg.get((aid, did), {'b': {1: 0, 2: 0, 3: 0}, 'j': {1: 0, 2: 0, 3: 0}})
        f = {t: a['b'][t] - a['j'][t] for t in (1, 2, 3)}
        j = sum(a['j'].values())
        al['disc'][did] = {'f1': f[1], 'f2': f[2], 'f3': f[3], 'j': j, 'total': sum(f.values())}
        al['total'] += sum(f.values())
        al['justificadas_total'] += j
    lista_discs = sorted(discs.values(), key=lambda d: d['nome'].lower())
    linhas = sorted(alunos.values(), key=lambda x: (x['classe'], x['turma'], x['nome'].lower()))
    for al in linhas:
        partes = [f"{d['sigla']}: {al['disc'][d['id']]['j']}" for d in lista_discs
                  if d['id'] in al['disc'] and al['disc'][d['id']]['j']]
        al['justificadas_txt'] = ' · '.join(partes)
    return {'disciplinas': lista_discs, 'alunos': linhas}


# --------------------------------------------------------------------------- detalhe por data

def montar_detalhe(qs, escola):
    """Cada falta com a data, o trimestre, o tipo de aula e as faltas justificadas/efectivas."""
    regs = qs.order_by().filter(status__in=STATUS_FALTA).select_related('aluno', 'turma', 'disciplina') \
        .order_by('turma__grau_ano', 'turma__nome', 'aluno__nome', 'disciplina__nome', 'data')
    out = []
    for p in regs:
        just = min(p.aulas_justificadas or 0, p.aulas or 1)
        out.append({
            'id': str(p.id), 'aluno': str(p.aluno_id), 'matricula': p.aluno.matricula,
            'nome': p.aluno.nome_completo, 'classe': p.turma.grau_ano or '', 'turma': p.turma.nome or '',
            'disciplina_id': str(p.disciplina_id or ''), 'disciplina': p.disciplina.nome if p.disciplina else '',
            'data': p.data.isoformat(), 'trimestre': trimestre_da_data(p.data, escola),
            'aulas': p.aulas or 1, 'justificadas': just, 'efectivas': (p.aulas or 1) - just,
            'status': p.status, 'observacao': p.observacao or '', 'justificacao': p.justificacao or '',
        })
    return out


# --------------------------------------------------------------------------- justificação por quantidade

class ErroJustificacao(ValueError):
    pass


def _pendentes(escola, aluno_id, disciplina_id, trimestre):
    regs = PresencaAluno.objects.filter(escola=escola, aluno_id=aluno_id, disciplina_id=disciplina_id,
                                        status__in=STATUS_FALTA).order_by('data', 'created_at')
    return [p for p in regs
            if trimestre_da_data(p.data, escola) == trimestre and (p.aulas or 1) - (p.aulas_justificadas or 0) > 0]


@transaction.atomic
def justificar_faltas(escola, user, aluno_id, disciplina_id, trimestre, quantidade, motivo):
    """Abate `quantidade` faltas (as mais antigas primeiro) do aluno nessa disciplina e trimestre."""
    if trimestre not in (1, 2, 3):
        raise ErroJustificacao('Trimestre inválido.')
    if not isinstance(quantidade, int) or quantidade < 1:
        raise ErroJustificacao('Indique o número de faltas a justificar (mínimo 1).')
    motivo = (motivo or '').strip()[:255]
    if not motivo:
        raise ErroJustificacao('Indique o motivo da justificação.')
    regs = _pendentes(escola, aluno_id, disciplina_id, trimestre)
    pendente = sum((p.aulas or 1) - (p.aulas_justificadas or 0) for p in regs)
    if quantidade > pendente:
        raise ErroJustificacao(f'Só existem {pendente} falta(s) por justificar nesta disciplina e trimestre.')
    agora, resta, aloc = timezone.now(), quantidade, {}
    for p in regs:
        if resta <= 0:
            break
        n = min(resta, (p.aulas or 1) - (p.aulas_justificadas or 0))
        p.aulas_justificadas = (p.aulas_justificadas or 0) + n
        if p.aulas_justificadas >= (p.aulas or 1):
            p.status = 'FALTA_JUSTIFICADA'
        p.justificacao, p.justificada_por, p.justificada_em = motivo, user, agora
        p.save(update_fields=['aulas_justificadas', 'status', 'justificacao', 'justificada_por', 'justificada_em', 'updated_at'])
        aloc[str(p.id)] = n
        resta -= n
    return JustificacaoFalta.objects.create(
        escola=escola, aluno_id=aluno_id, disciplina_id=disciplina_id, trimestre=trimestre, quantidade=quantidade,
        motivo=motivo, alocacao=aloc, justificada_por=user)


@transaction.atomic
def anular_justificacao(just, user):
    """Devolve as faltas abatidas por uma justificação (volta a contar nas faltas efectivas)."""
    if just.anulada:
        raise ErroJustificacao('Esta justificação já foi anulada.')
    for pid, n in (just.alocacao or {}).items():
        p = PresencaAluno.objects.filter(id=pid, escola=just.escola).first()
        if not p:
            continue
        p.aulas_justificadas = max((p.aulas_justificadas or 0) - n, 0)
        if p.aulas_justificadas < (p.aulas or 1) and p.status == 'FALTA_JUSTIFICADA':
            p.status = 'FALTA_INJUSTIFICADA'
        if p.aulas_justificadas == 0:
            p.justificacao, p.justificada_por, p.justificada_em = '', None, None
        p.save(update_fields=['aulas_justificadas', 'status', 'justificacao', 'justificada_por', 'justificada_em', 'updated_at'])
    just.anulada, just.anulada_por, just.anulada_em = True, user, timezone.now()
    just.save(update_fields=['anulada', 'anulada_por', 'anulada_em'])
    return just


# --------------------------------------------------------------------------- exportação

def _subtitulo(filtros):
    return ' | '.join(f'{k}: {v}' for k, v in filtros.items() if v)


def _data_pt(iso):
    a, m, d = iso.split('-')
    return f'{d}/{m}/{a}'


def _xlsx_cabecalho(ws, escola, titulo, filtros, n_cols):
    from openpyxl.styles import Alignment, Font
    ws.append([(escola.nome if escola else '').upper()])
    ws.append([titulo])
    ws.append([_subtitulo(filtros)])
    ws.append([])
    for r in (1, 2, 3):
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=n_cols)
        ws.cell(r, 1).alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        ws.cell(r, 1).font = Font(name='Times New Roman', size=13 if r < 3 else 12, bold=r < 3, italic=r == 3)


def _xlsx_titulo_tabela(cell):
    from openpyxl.styles import Alignment, Font, PatternFill
    cell.font = Font(name='Times New Roman', size=12, bold=True, color='FFFFFFFF')
    cell.fill = PatternFill('solid', fgColor='FF1E3A8A')
    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)


def gerar_pivot_xlsx(pivot, escola, filtros):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    discs, alunos = pivot['disciplinas'], pivot['alunos']
    wb = Workbook()
    ws = wb.active
    ws.title = 'Faltas acumuladas'
    n_cols = 5 + 3 * len(discs) + 2
    _xlsx_cabecalho(ws, escola, 'LISTA GERAL DE FALTAS ACUMULADAS (faltas efectivas por trimestre)', filtros, n_cols)
    if not alunos:
        ws.append(['Sem registos de faltas para os filtros indicados.'])
        return guardar_xlsx_seguro(wb)
    r1, r2 = 5, 6
    fixos = ['N.º', 'Matrícula', 'Nome do aluno', 'Classe', 'Turma']
    for i, t in enumerate(fixos, start=1):
        ws.cell(r1, i, t)
        ws.merge_cells(start_row=r1, start_column=i, end_row=r2, end_column=i)
    for k, d in enumerate(discs):
        c = 6 + 3 * k
        ws.cell(r1, c, d['nome'])
        ws.merge_cells(start_row=r1, start_column=c, end_row=r1, end_column=c + 2)
        for j, rot in enumerate(('1.º T', '2.º T', '3.º T')):
            ws.cell(r2, c + j, rot)
    c_tot, c_just = 6 + 3 * len(discs), 7 + 3 * len(discs)
    ws.cell(r1, c_tot, 'Total de faltas')
    ws.merge_cells(start_row=r1, start_column=c_tot, end_row=r2, end_column=c_tot)
    ws.cell(r1, c_just, 'Faltas justificadas')
    ws.merge_cells(start_row=r1, start_column=c_just, end_row=r2, end_column=c_just)
    for r in (r1, r2):
        for c in range(1, n_cols + 1):
            _xlsx_titulo_tabela(ws.cell(r, c))
    for i, a in enumerate(alunos, start=1):
        linha = [i, a['matricula'], a['nome'], a['classe'], a['turma']]
        for d in discs:
            x = a['disc'].get(d['id'])
            linha += [x['f1'], x['f2'], x['f3']] if x else ['-', '-', '-']
        linha += [a['total'], a['justificadas_txt'] or '-']
        ws.append(linha)
    for row in ws.iter_rows(min_row=r2 + 1):
        for c in row:
            c.font = Font(name='Times New Roman', size=12)
            c.alignment = Alignment(horizontal='left' if c.column in (3, c_just) else 'center', vertical='center', wrap_text=True)
    ws.column_dimensions['C'].width = 34
    return guardar_xlsx_seguro(wb)


COL_DETALHE = ['N.º', 'Aluno', 'Turma', 'Disciplina', 'Data da falta', 'Trimestre', 'Tipo de aula', 'Faltas', 'Justificadas',
               'Efectivas', 'Estado']


def _linhas_detalhe(det):
    out = []
    for i, r in enumerate(det, start=1):
        estado = ('Justificada' if r['efectivas'] == 0 else 'Parcialmente justificada' if r['justificadas'] else 'Injustificada')
        out.append([i, f"{r['nome']} ({r['matricula']})", f"{r['classe']} {r['turma']}".strip(), r['disciplina'],
                    _data_pt(r['data']), f"{r['trimestre']}.º" if r['trimestre'] else '-',
                    'Dupla (2 aulas)' if r['aulas'] == 2 else 'Simples (1 aula)',
                    r['aulas'], r['justificadas'], r['efectivas'], estado])
    return out


def gerar_detalhe_xlsx(det, escola, filtros):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    wb = Workbook()
    ws = wb.active
    ws.title = 'Faltas detalhadas'
    _xlsx_cabecalho(ws, escola, 'RELATÓRIO DETALHADO DE FALTAS (por data)', filtros, len(COL_DETALHE))
    if not det:
        ws.append(['Sem faltas registadas para os filtros indicados.'])
        return guardar_xlsx_seguro(wb)
    ws.append(COL_DETALHE)
    for c in ws[5]:
        _xlsx_titulo_tabela(c)
    for linha in _linhas_detalhe(det):
        ws.append(linha)
    ws.append(['', 'TOTAL', '', '', '', '', '', sum(r['aulas'] for r in det), sum(r['justificadas'] for r in det),
               sum(r['efectivas'] for r in det), ''])
    for row in ws.iter_rows(min_row=6):
        for c in row:
            c.font = Font(name='Times New Roman', size=12, bold=row[1].value == 'TOTAL')
            c.alignment = Alignment(horizontal='left' if c.column in (2, 4) else 'center', vertical='center', wrap_text=True)
    ws.column_dimensions['B'].width = 36
    ws.column_dimensions['D'].width = 24
    return guardar_xlsx_seguro(wb)


def _pdf_base(escola, titulo, filtros, largura_cm):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    s_c = ParagraphStyle('FC', fontName='Times-Bold', fontSize=13, leading=17, alignment=1)
    s_s = ParagraphStyle('FS', fontName='Times-Italic', fontSize=10, leading=13, alignment=1)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=(max(largura_cm, 29.7) * cm, 21 * cm), leftMargin=1 * cm, rightMargin=1 * cm,
                            topMargin=1.4 * cm, bottomMargin=1.4 * cm)
    el = [Paragraph(escape((escola.nome if escola else '').upper()), s_c), Paragraph(escape(titulo), s_c),
          Paragraph(escape(_subtitulo(filtros)), s_s), Spacer(1, 0.4 * cm)]
    return doc, buf, el


def _estilo_tabela(n_cab, zebra_ate, grupos=None):
    from reportlab.platypus import TableStyle
    azul = colors.HexColor('#1E3A8A')
    e = [
        ('BACKGROUND', (0, 0), (-1, n_cab - 1), azul), ('TEXTCOLOR', (0, 0), (-1, n_cab - 1), colors.white),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#94A3B8')), ('BOX', (0, 0), (-1, -1), 1.2, azul),
        ('LINEBELOW', (0, n_cab - 1), (-1, n_cab - 1), 1.6, colors.HexColor('#C9A227')),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]
    for i in range(n_cab, zebra_ate):
        if (i - n_cab) % 2 == 1:
            e.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F1F5F9')))
    return TableStyle(e + (grupos or []))


def gerar_pivot_pdf(pivot, escola, filtros):
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, Table
    discs, alunos = pivot['disciplinas'], pivot['alunos']
    fixos = [0.8, 2.1, 4.4, 2.6]          # N.º, matrícula, nome, turma (classe + turma)
    fim = [1.3, 3.2]                      # total, justificadas
    largura = sum(fixos) + sum(fim) + 0.9 * 3 * len(discs) + 2
    doc, buf, el = _pdf_base(escola, 'LISTA GERAL DE FALTAS ACUMULADAS (faltas efectivas por trimestre)', filtros, largura)
    s_h = ParagraphStyle('FH', fontName='Times-Bold', fontSize=9, leading=11, alignment=1, textColor=colors.white)
    s_n = ParagraphStyle('FN', fontName='Times-Roman', fontSize=9, leading=11)
    s_c = ParagraphStyle('FCe', fontName='Times-Roman', fontSize=9, leading=11, alignment=1)
    if not alunos:
        el.append(Paragraph('Sem registos de faltas para os filtros indicados.', s_n))
        doc.build(el)
        return buf.getvalue()
    n_disc = len(discs)
    cab1 = [Paragraph(t, s_h) for t in ('N.º', 'Matrícula', 'Nome do aluno', 'Turma')]
    cab2 = [''] * 4
    for d in discs:
        cab1 += [Paragraph(escape(d['nome']), s_h), '', '']
        cab2 += [Paragraph(t, s_h) for t in ('1.º T', '2.º T', '3.º T')]
    cab1 += [Paragraph('Total', s_h), Paragraph('Faltas justificadas', s_h)]
    cab2 += ['', '']
    dados = [cab1, cab2]
    for i, a in enumerate(alunos, start=1):
        linha = [str(i), Paragraph(escape(a['matricula'] or ''), s_c), Paragraph(escape(a['nome']), s_n),
                 Paragraph(escape(f"{a['classe']} {a['turma']}".strip()), s_c)]
        for d in discs:
            x = a['disc'].get(d['id'])
            linha += [str(x['f1']), str(x['f2']), str(x['f3'])] if x else ['-', '-', '-']
        linha += [Paragraph(f"<b>{a['total']}</b>", s_c), Paragraph(escape(a['justificadas_txt'] or '-'), s_c)]
        dados.append(linha)
    larguras = [w * cm for w in fixos] + [0.9 * cm] * (3 * n_disc) + [w * cm for w in fim]
    # a coluna do nome absorve a folga da página
    util = (max(largura, 29.7) - 2) * cm
    larguras[2] += max(util - sum(larguras), 0)
    grupos = [('SPAN', (i, 0), (i, 1)) for i in (0, 1, 2, 3, 4 + 3 * n_disc, 5 + 3 * n_disc)]
    grupos += [('SPAN', (4 + 3 * k, 0), (6 + 3 * k, 0)) for k in range(n_disc)]
    grupos += [('LINEBEFORE', (4 + 3 * k, 0), (4 + 3 * k, -1), 1.2, colors.HexColor('#1E3A8A')) for k in range(n_disc)]
    tb = Table(dados, colWidths=larguras, repeatRows=2)
    tb.setStyle(_estilo_tabela(2, len(dados), grupos))
    el.append(tb)
    doc.build(el)
    return buf.getvalue()


def gerar_detalhe_pdf(det, escola, filtros):
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, Table
    doc, buf, el = _pdf_base(escola, 'RELATÓRIO DETALHADO DE FALTAS (por data)', filtros, 29.7)
    s_h = ParagraphStyle('DH', fontName='Times-Bold', fontSize=10, leading=12, alignment=1, textColor=colors.white)
    s_n = ParagraphStyle('DN', fontName='Times-Roman', fontSize=10, leading=12)
    s_c = ParagraphStyle('DC', fontName='Times-Roman', fontSize=10, leading=12, alignment=1)
    if not det:
        el.append(Paragraph('Sem faltas registadas para os filtros indicados.', s_n))
        doc.build(el)
        return buf.getvalue()
    dados = [[Paragraph(escape(c), s_h) for c in COL_DETALHE]]
    for l in _linhas_detalhe(det):
        dados.append([str(l[0]), Paragraph(escape(l[1]), s_n), Paragraph(escape(l[2]), s_c), Paragraph(escape(l[3]), s_n)] +
                     [Paragraph(escape(str(x)), s_c) for x in l[4:]])
    dados.append(['', Paragraph('<b>TOTAL</b>', s_n), '', '', '', '', '',
                  Paragraph(f"<b>{sum(r['aulas'] for r in det)}</b>", s_c),
                  Paragraph(f"<b>{sum(r['justificadas'] for r in det)}</b>", s_c),
                  Paragraph(f"<b>{sum(r['efectivas'] for r in det)}</b>", s_c), ''])
    larg = [0.9, 5.6, 2.4, 3.4, 2.2, 1.6, 2.6, 1.3, 1.9, 1.6, 3.0]
    tb = Table(dados, colWidths=[w * cm for w in larg], repeatRows=1)
    tb.setStyle(_estilo_tabela(1, len(dados)))
    el.append(tb)
    doc.build(el)
    return buf.getvalue()
