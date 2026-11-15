"""PDF dos júris de exame e da lista de excluídos (regras: docs/REGRAS_EXCEL_E_PDF.md, secção 2)."""
import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle

from apps.documentos.services.pdf_service import (
    PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    gerar_cabecalho_mec, getSampleStyleSheet,
)

AZUL = colors.HexColor('#1E3A8A')
ZEBRA = colors.HexColor('#F1F5F9')
CINZA = colors.HexColor('#94A3B8')
PERIODOS = {'MANHA': 'Manhã', 'TARDE': 'Tarde', 'NOITE': 'Noturno'}


def _esc(t):
    return str(t if t is not None else '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _fmt_nota(v):
    if v is None:
        return '—'
    return f'{v:.1f}'.replace('.', ',')


def _data_pt(iso):
    if not iso:
        return 'Data por definir'
    y, m, d = (int(x) for x in iso.split('-'))
    return f'{d:02d}/{m:02d}/{y}'


def _tabela(cabecalho, linhas, larguras):
    st_h = ParagraphStyle('ExH', fontName='Times-Bold', alignment=1, textColor=colors.white)
    st_c = ParagraphStyle('ExC', fontName='Times-Roman')
    st_cc = ParagraphStyle('ExCC', fontName='Times-Roman', alignment=1)
    dados = [[Paragraph(_esc(h), st_h) for h in cabecalho]]
    for ln in linhas:
        dados.append([Paragraph(c if isinstance(c, str) and c.startswith('<font') else _esc(c),
                                st_cc if i != 1 else st_c) for i, c in enumerate(ln)])
    t = Table(dados, colWidths=larguras, repeatRows=1)
    cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), AZUL),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1.2, AZUL),
        ('LINEBELOW', (0, 0), (-1, 0), 1.6, colors.HexColor('#C9A227')),
        ('INNERGRID', (0, 1), (-1, -1), 0.4, CINZA),
    ]
    for i in range(2, len(dados), 2):
        cmds.append(('BACKGROUND', (0, i), (-1, i), ZEBRA))
    t.setStyle(TableStyle(cmds))
    return t


def _cabecalho(escola, titulo, subtitulo):
    styles = getSampleStyleSheet()
    el = gerar_cabecalho_mec(styles, escola.nome, escola.provincia, escola.distrito, compacto=True, escola=escola)
    el.append(Paragraph(f'<b>{_esc(titulo)}</b>', ParagraphStyle('ExT', alignment=1, fontName='Times-Bold')))
    if subtitulo:
        el.append(Paragraph(_esc(subtitulo), ParagraphStyle('ExS', alignment=1, fontName='Times-Roman')))
    el.append(Spacer(1, 0.3 * cm))
    return el


def _doc(buf):
    return SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                             topMargin=1.0 * cm, bottomMargin=1.2 * cm)


def pdf_juris(escola, ano, epoca, juris):
    buf = io.BytesIO()
    el = []
    larg = [1.4 * cm, 7.6 * cm, 2.8 * cm, 2.6 * cm, 2.6 * cm]  # soma 17,0 cm = largura útil
    for k, j in enumerate(juris):
        if k:
            el.append(PageBreak())
        el += _cabecalho(escola, f'JÚRI Nº {j["numero"]} — EXAME DA {epoca}ª CHAMADA/ÉPOCA', f'Ano lectivo {ano}')
        horario = (f'{j["hora_inicio"]} às {j["hora_fim"]} ({j["duracao_minutos"]} min)'
                   if j['hora_inicio'] else 'Horário por definir')
        info = [
            ['Disciplina', j['disciplina'], 'Classe', j['classe']],
            ['Data', _data_pt(j['data']), 'Período', PERIODOS.get(j['periodo'], '—')],
            ['Horário', horario, 'Sala', j['sala'] or 'Por atribuir'],
        ]
        st = ParagraphStyle('ExI', fontName='Times-Roman')
        sb = ParagraphStyle('ExIB', fontName='Times-Bold')
        dados = [[Paragraph(_esc(c), sb if i % 2 == 0 else st) for i, c in enumerate(r)] for r in info]
        ti = Table(dados, colWidths=[2.6 * cm, 6.4 * cm, 2.4 * cm, 5.6 * cm])
        ti.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), 1.2, AZUL), ('INNERGRID', (0, 0), (-1, -1), 0.4, CINZA),
                                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                ('BACKGROUND', (0, 0), (0, -1), ZEBRA), ('BACKGROUND', (2, 0), (2, -1), ZEBRA)]))
        el += [ti, Spacer(1, 0.3 * cm)]
        linhas = [[a['ordem'], a['nome'], a['matricula'] or '', a['turma'],
                   _fmt_nota(a['freq'])] for a in j['alunos']]
        el.append(_tabela(['Nº', 'Nome completo', 'Matrícula', 'Turma', 'Nota de Frequência'], linhas, larg))
        el.append(Spacer(1, 0.2 * cm))
        el.append(Paragraph(f'Total de alunos no júri: <b>{len(j["alunos"])}</b>',
                            ParagraphStyle('ExF', fontName='Times-Roman')))
    if not juris:
        el += _cabecalho(escola, 'JÚRIS DE EXAME', f'Ano lectivo {ano}')
        el.append(Paragraph('Ainda não há júris formados.', ParagraphStyle('ExV', fontName='Times-Roman')))
    _doc(buf).build(el)
    return buf.getvalue()


def pdf_excluidos(escola, ano, classe, grupos):
    """grupos: [(disciplina, [dados de aluno excluído...])]."""
    buf = io.BytesIO()
    el = _cabecalho(escola, f'ALUNOS EXCLUÍDOS DO EXAME — {classe}',
                    f'Ano lectivo {ano} · Frequência igual ou inferior a 9,4 valores (sem direito ao exame)')
    larg = [1.4 * cm, 8.0 * cm, 2.8 * cm, 2.4 * cm, 2.4 * cm]
    vazio = True
    for disciplina, alunos in grupos:
        if not alunos:
            continue
        vazio = False
        el.append(Paragraph(f'<b>Disciplina: {_esc(disciplina)}</b>', ParagraphStyle('ExD', fontName='Times-Bold')))
        linhas = [[i, a['nome'], a['aluno'].matricula or '', a['turma'],
                   f'<font color="#C00000">{_fmt_nota(a["freq"])}</font>'] for i, a in enumerate(alunos, 1)]
        el += [_tabela(['Nº', 'Nome completo', 'Matrícula', 'Turma', 'Nota de Frequência'], linhas, larg),
               Spacer(1, 0.4 * cm)]
    if vazio:
        el.append(Paragraph('Não há alunos excluídos nesta classe.', ParagraphStyle('ExV', fontName='Times-Roman')))
    el.append(Paragraph(f'Emitido em {date.today():%d/%m/%Y}.', ParagraphStyle('ExE', fontName='Times-Italic')))
    _doc(buf).build(el)
    return buf.getvalue()
