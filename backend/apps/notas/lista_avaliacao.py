"""Lista de resultados de uma avaliação corrigida (PDF e Excel).

Colunas: Nº, Código do aluno, Nome, Turma, Acertos, Nota (0–20), Resultado, Estado; e, no cabeçalho, escola,
disciplina, tipo de avaliação, trimestre, ano lectivo, turma, professor e data de emissão.
Regras de formato: docs/REGRAS_EXCEL_E_PDF.md (Times New Roman, cabeçalhos centrados, nada sobreposto, notas
negativas a vermelho, Excel gravado por guardar_xlsx_seguro).
"""
import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm

from apps.alunos.models import Aluno
from apps.documentos.services.pdf_service import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, gerar_cabecalho_mec, getSampleStyleSheet,
)

from .models import CorrecaoProva

AZUL = colors.HexColor('#1E3A8A')
ZEBRA = colors.HexColor('#F1F5F9')
CINZA = colors.HexColor('#94A3B8')
PERIODOS = {'1_TRIMESTRE': '1.º Trimestre', '2_TRIMESTRE': '2.º Trimestre', '3_TRIMESTRE': '3.º Trimestre'}
ESTADOS = {'RASCUNHO': 'Incompleta', 'CORRIGIDA': 'Corrigida', 'LANCADA': 'Lançada na caderneta'}
COLUNAS = ['Nº', 'Código do aluno', 'Nome completo', 'Turma', 'Acertos', 'Nota (0–20)', 'Resultado', 'Estado']


def _fmt(v):
    return f'{float(v):.1f}'.replace('.', ',')


def montar(prova, professor_nome=''):
    """Dados da lista: (cabecalho: dict, linhas: list[list]). Todos os alunos activos da turma, por ordem alfabética."""
    correcoes = {c.aluno_id: c for c in CorrecaoProva.objects.filter(prova=prova)}
    n_mc = sum(1 for p in prova.perguntas if p.get('tipo') == 'MC')
    linhas = []
    alunos = Aluno.objects.filter(escola=prova.escola, turma=prova.turma, status='ATIVO').order_by('nome')
    for i, a in enumerate(alunos, 1):
        c = correcoes.get(a.id)
        if c and c.estado != 'RASCUNHO':
            chave = prova.gabaritos.get(c.versao or '-') or (next(iter(prova.gabaritos.values()), '') if prova.gabaritos else '')
            acertos = sum(1 for x, y in zip(c.respostas, chave) if x == y) if c.respostas else None
            linhas.append([i, a.matricula or '', a.nome, prova.turma.nome,
                           '—' if acertos is None else f'{acertos}/{n_mc}', float(c.nota),
                           'Positiva' if c.nota >= 10 else 'Negativa', ESTADOS.get(c.estado, c.estado)])
        else:
            linhas.append([i, a.matricula or '', a.nome, prova.turma.nome, '—', None, '—',
                           ESTADOS.get(c.estado, 'Sem correcção') if c else 'Sem correcção'])
    notas = [l[5] for l in linhas if l[5] is not None]
    cab = {
        'escola': prova.escola, 'disciplina': prova.disciplina.nome, 'tipo': prova.get_instrumento_display(),
        'titulo': prova.titulo, 'periodo': PERIODOS.get(prova.periodo, prova.periodo), 'ano': prova.turma.ano_letivo,
        'turma': prova.turma.nome, 'classe': getattr(prova.turma, 'grau_ano', '') or '', 'professor': professor_nome,
        'emitido': date.today().strftime('%d/%m/%Y'), 'corrigidas': len(notas), 'total': len(linhas),
        'positivas': sum(1 for n in notas if n >= 10), 'negativas': sum(1 for n in notas if n < 10),
        'media': (sum(notas) / len(notas)) if notas else None,
    }
    return cab, linhas


def _esc(t):
    return str(t if t is not None else '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def nome_ficheiro(cab, extensao):
    import re
    return re.sub(r'[\\/:*?"<>|\r\n]+', ' ', f'Lista de notas - {cab["disciplina"]} - {cab["tipo"]} - {cab["ano"]}').strip() + '.' + extensao


def pdf_lista(cab, linhas):
    buf = io.BytesIO()
    escola = cab['escola']
    styles = getSampleStyleSheet()
    el = gerar_cabecalho_mec(styles, escola.nome, escola.provincia, escola.distrito, compacto=True, escola=escola)
    el.append(Paragraph('<b>LISTA DE RESULTADOS DA AVALIAÇÃO CORRIGIDA</b>', ParagraphStyle('LaT', fontName='Times-Bold', alignment=1)))
    el.append(Spacer(1, 0.25 * cm))
    sb, sr = ParagraphStyle('LaB', fontName='Times-Bold'), ParagraphStyle('LaR', fontName='Times-Roman')
    info = [['Disciplina', cab['disciplina'], 'Tipo de avaliação', cab['tipo']],
            ['Turma', cab['turma'] + (f' ({cab["classe"]})' if cab['classe'] else ''), 'Trimestre', cab['periodo']],
            ['Ano lectivo', cab['ano'], 'Professor(a)', cab['professor'] or '—'],
            ['Avaliação', cab['titulo'], 'Emitida em', cab['emitido']]]
    ti = Table([[Paragraph(_esc(c), sb if k % 2 == 0 else sr) for k, c in enumerate(r)] for r in info],
               colWidths=[2.6 * cm, 6.0 * cm, 3.2 * cm, 5.2 * cm])
    ti.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), 1.2, AZUL), ('INNERGRID', (0, 0), (-1, -1), 0.4, CINZA),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('BACKGROUND', (0, 0), (0, -1), ZEBRA), ('BACKGROUND', (2, 0), (2, -1), ZEBRA)]))
    el += [ti, Spacer(1, 0.3 * cm)]

    st_h = ParagraphStyle('LaH', fontName='Times-Bold', alignment=1, textColor=colors.white)
    st_c = ParagraphStyle('LaC', fontName='Times-Roman')
    st_m = ParagraphStyle('LaM', fontName='Times-Roman', alignment=1)
    dados = [[Paragraph(_esc(h), st_h) for h in COLUNAS]]
    for ln in linhas:
        cel = []
        for k, v in enumerate(ln):
            if k == 5:
                txt = '—' if v is None else _fmt(v)
                if v is not None and v < 10:
                    txt = f'<font color="#C00000"><b>{txt}</b></font>'
                else:
                    txt = f'<b>{txt}</b>'
                cel.append(Paragraph(txt, st_m))
            else:
                cel.append(Paragraph(_esc(v), st_c if k in (1, 2) else st_m))
        dados.append(cel)
    larg = [0.9 * cm, 3.6 * cm, 4.6 * cm, 1.5 * cm, 1.5 * cm, 1.4 * cm, 1.6 * cm, 2.4 * cm]   # 17,5 cm (largura útil)
    t = Table(dados, colWidths=larg, repeatRows=1)
    cmds = [('BACKGROUND', (0, 0), (-1, 0), AZUL), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1.2, AZUL), ('LINEBELOW', (0, 0), (-1, 0), 1.6, colors.HexColor('#C9A227')),
            ('INNERGRID', (0, 1), (-1, -1), 0.4, CINZA)]
    for i in range(2, len(dados), 2):
        cmds.append(('BACKGROUND', (0, i), (-1, i), ZEBRA))
    t.setStyle(TableStyle(cmds))
    el += [t, Spacer(1, 0.3 * cm)]
    media = '—' if cab['media'] is None else _fmt(cab['media'])
    el.append(Paragraph(f'Corrigidas: <b>{cab["corrigidas"]}</b> de {cab["total"]} · Positivas: <b>{cab["positivas"]}</b> · '
                        f'Negativas: <b>{cab["negativas"]}</b> · Média: <b>{media}</b>', sr))
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.0 * cm,
                      bottomMargin=1.2 * cm).build(el)
    return buf.getvalue()


def xlsx_lista(cab, linhas):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    from apps.documentos.services.xlsx_seguro import guardar_xlsx_seguro
    wb = Workbook()
    ws = wb.active
    ws.title = 'Resultados'
    neg = Font(name='Times New Roman', size=12, bold=True)
    ws.append([(cab['escola'].nome or '').upper()])
    ws.append(['LISTA DE RESULTADOS DA AVALIAÇÃO CORRIGIDA'])
    for r in (1, 2):
        ws.cell(r, 1).font = neg
    for rot, val in (('Disciplina', cab['disciplina']), ('Tipo de avaliação', cab['tipo']), ('Avaliação', cab['titulo']),
                     ('Trimestre', cab['periodo']), ('Ano lectivo', cab['ano']),
                     ('Turma', cab['turma'] + (f' ({cab["classe"]})' if cab['classe'] else '')),
                     ('Professor(a)', cab['professor'] or '—'), ('Emitida em', cab['emitido'])):
        ws.append([f'{rot}: {val}'])
    ws.append([])
    ws.append(COLUNAS)
    for c in ws[ws.max_row]:
        c.fill = PatternFill('solid', fgColor='1E3A8A')
        c.font = Font(name='Times New Roman', size=12, bold=True, color='FFFFFF')
    for ln in linhas:
        ws.append([ln[0], ln[1], ln[2], ln[3], ln[4], '—' if ln[5] is None else round(ln[5], 1), ln[6], ln[7]])
        if ln[5] is not None and ln[5] < 10:
            ws.cell(ws.max_row, 6).font = Font(name='Times New Roman', size=12, bold=True, color='C00000')
    if not linhas:
        ws.append(['Esta turma não tem alunos activos.'])
    ws.append([])
    media = '—' if cab['media'] is None else _fmt(cab['media'])
    ws.append([f'Corrigidas: {cab["corrigidas"]} de {cab["total"]} · Positivas: {cab["positivas"]} · '
               f'Negativas: {cab["negativas"]} · Média: {media}'])
    return guardar_xlsx_seguro(wb)
