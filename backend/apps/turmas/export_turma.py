"""Documentos de uma turma, descarregados a partir do botão «Descarregar» da linha da turma:
a ficha da turma e a relação nominal dos alunos (PDF ou Excel), entregues num ZIP.

Regras: docs/REGRAS_EXCEL_E_PDF.md (Times New Roman, cabeçalhos centrados, Excel por guardar_xlsx_seguro).
Assinaturas: «O Director da Escola» no topo, à direita do cabeçalho (é aí que o carimbo é sempre aplicado,
pelo detector de assinatura do carimbo) e «O Director Pedagógico (DAP)» no fim do documento.
"""
import io
import zipfile
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Table, TableStyle

from apps.documentos.services.pdf_service import Paragraph, Spacer
from apps.documentos.services.xlsx_seguro import guardar_xlsx_seguro
from apps.notas.exames_pdf import _cabecalho, _doc, _esc, _tabela
from apps.notas.exames_xlsx import _cabecalho as _cab_xlsx, _titulos

TURNOS = {'MANHA': 'Manhã', 'TARDE': 'Tarde', 'NOITE': 'Noite'}
LINHA = '________________________'
TNR = 'Times New Roman'


def _director(nome, status, codigo):
    if not nome:
        return 'Não definido'
    if status == 'HOMOLOGADO' and codigo:
        return f'{nome} (homologado · código {codigo})'
    if status in ('PENDENTE', 'PENDENTE_HOMOLOGACAO'):
        return f'{nome} (nomeado, a aguardar homologação)'
    return nome


def alunos_da_turma(turma):
    return list(turma.alunos.filter(status='ATIVO').order_by('nome', 'apelido'))


def _nome_aluno(a):
    return f'{a.nome} {getattr(a, "apelido", "") or ""}'.strip()


def _nascimento(a):
    return a.data_nascimento.strftime('%d/%m/%Y') if a.data_nascimento else ''


def linhas_ficha(turma, ocupacao):
    maximo = turma.capacidade_maxima or 50
    pct = round(ocupacao * 100 / maximo) if maximo else 0
    dt = turma.director_turma.nome if turma.director_turma_id else ''
    dc = turma.director_classe.nome if turma.director_classe_id else ''
    return [
        ['Turma', turma.nome],
        ['Classe / Grau', turma.grau_ano],
        ['Secção / Área', turma.area or 'Geral'],
        ['Ano lectivo', turma.ano_letivo],
        ['Turno', TURNOS.get(turma.turno, turma.turno or '—')],
        ['Sala', turma.sala or '—'],
        ['Ocupação / Máx', f'{ocupacao} / {maximo} alunos ({pct}%)'],
        ['Vagas livres', max(0, maximo - ocupacao)],
        ['Director de Turma', _director(dt, turma.dt_status_homologacao, turma.codigo_director_turma)],
        ['Director de Classe', _director(dc, turma.dc_status_homologacao, turma.codigo_director_classe)],
    ]


# ------------------------------------------------------------------------------------------------ PDF
def _assinatura_director_topo(escola):
    """Bloco no topo, à direita: espaço para o carimbo, linha, «O Director da Escola» e o nome."""
    st = ParagraphStyle('AsD', fontName='Times-Roman', fontSize=10, leading=12, alignment=1)
    stb = ParagraphStyle('AsDB', fontName='Times-Bold', fontSize=10, leading=12, alignment=1)
    bloco = Table([[Spacer(1, 1.3 * cm)], [Paragraph(LINHA, st)], [Paragraph('O Director da Escola', stb)],
                   [Paragraph(_esc(getattr(escola, 'director_nome', '') or ''), st)]], colWidths=[6.5 * cm])
    bloco.setStyle(TableStyle([('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
    topo = Table([['', bloco]], colWidths=[10.5 * cm, 6.5 * cm])
    topo.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    return [topo, Spacer(1, 1.7 * cm)]  # folga abaixo: o círculo do carimbo ocupa ~2 cm por baixo da linha


def _assinatura_dap_fim(escola):
    st = ParagraphStyle('AsP', fontName='Times-Roman', fontSize=10, leading=12, alignment=1)
    stb = ParagraphStyle('AsPB', fontName='Times-Bold', fontSize=10, leading=12, alignment=1)
    t = Table([[Paragraph(LINHA, st)], [Paragraph('O Director Pedagógico (DAP)', stb)],
               [Paragraph(_esc(getattr(escola, 'dap_nome', '') or ''), st)]], colWidths=[6.5 * cm])
    t.setStyle(TableStyle([('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
    return [Spacer(1, 1.6 * cm), t]


def _pdf(escola, titulo, subtitulo, corpo):
    buf = io.BytesIO()
    el = _assinatura_director_topo(escola) + _cabecalho(escola, titulo, subtitulo) + corpo + _assinatura_dap_fim(escola)
    _doc(buf).build(el)
    return buf.getvalue()


def pdf_turma(escola, turma, ocupacao):
    linhas = [[_esc(c), v] for c, v in linhas_ficha(turma, ocupacao)]
    corpo = [_tabela(['Campo', 'Informação'], linhas, [5.0 * cm, 12.0 * cm], esq=1),
             Spacer(1, 0.3 * cm),
             Paragraph(f'Emitido em {date.today():%d/%m/%Y}.', ParagraphStyle('ExE', fontName='Times-Italic'))]
    return _pdf(escola, f'FICHA DA TURMA — {turma.nome}', f'{turma.grau_ano} · Ano lectivo {turma.ano_letivo}', corpo)


def pdf_relacao_nominal(escola, turma, alunos):
    st = ParagraphStyle('ExV', fontName='Times-Roman')
    if alunos:
        linhas = [[i, _nome_aluno(a), a.matricula or '', a.genero or '', _nascimento(a)] for i, a in enumerate(alunos, 1)]
        corpo = [_tabela(['Nº', 'Nome completo', 'Matrícula', 'Género', 'Data de nascimento'], linhas,
                         [1.0 * cm, 5.4 * cm, 5.7 * cm, 1.9 * cm, 3.0 * cm]),
                 Spacer(1, 0.2 * cm), Paragraph(f'Total de alunos: <b>{len(alunos)}</b>', st)]
    else:
        corpo = [Paragraph('Nenhum aluno matriculado nesta turma.', st)]
    corpo += [Paragraph(f'Emitido em {date.today():%d/%m/%Y}.', ParagraphStyle('ExE', fontName='Times-Italic'))]
    return _pdf(escola, f'RELAÇÃO NOMINAL DOS ALUNOS — {turma.nome}',
                f'{turma.grau_ano} · Ano lectivo {turma.ano_letivo}', corpo)


# ---------------------------------------------------------------------------------------------- Excel
def _assinatura_topo_xlsx(ws, escola, col):
    """Topo, à direita do cabeçalho: «O Director da Escola» (linha, rótulo e nome)."""
    ws.cell(1, col, LINHA)
    ws.cell(2, col, 'O Director da Escola').font = Font(name=TNR, size=12, bold=True)
    ws.cell(3, col, getattr(escola, 'director_nome', '') or '')
    for r in (1, 2, 3):
        ws.cell(r, col).alignment = Alignment(horizontal='center', vertical='center')


def _assinatura_dap_xlsx(ws, escola):
    ws.append([])
    ws.append([LINHA])
    ws.append(['O Director Pedagógico (DAP)'])
    ws.append([getattr(escola, 'dap_nome', '') or ''])
    ws.cell(ws.max_row - 1, 1).font = Font(name=TNR, size=12, bold=True)


def xlsx_turma(escola, turma, ocupacao):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Turma'
    _titulos(ws, escola, f'FICHA DA TURMA — {turma.nome}', f'{turma.grau_ano} · Ano lectivo {turma.ano_letivo}')
    _cab_xlsx(ws, ['Campo', 'Informação'])
    for c, v in linhas_ficha(turma, ocupacao):
        ws.append([c, v])
    _assinatura_dap_xlsx(ws, escola)
    _assinatura_topo_xlsx(ws, escola, 2)
    return guardar_xlsx_seguro(wb)


def xlsx_relacao_nominal(escola, turma, alunos):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Relação nominal'
    _titulos(ws, escola, f'RELAÇÃO NOMINAL DOS ALUNOS — {turma.nome}', f'{turma.grau_ano} · Ano lectivo {turma.ano_letivo}')
    _cab_xlsx(ws, ['Nº', 'Nome completo', 'Matrícula', 'Género', 'Data de nascimento'])
    if alunos:
        for i, a in enumerate(alunos, 1):
            ws.append([i, _nome_aluno(a), a.matricula or '', a.genero or '', _nascimento(a)])
        ws.append([])
        ws.append([f'Total de alunos: {len(alunos)}'])
    else:
        ws.append(['Nenhum aluno matriculado nesta turma.'])
    _assinatura_dap_xlsx(ws, escola)
    _assinatura_topo_xlsx(ws, escola, 5)
    return guardar_xlsx_seguro(wb)


# ------------------------------------------------------------------------------------------------ ZIP
def zip_turma(escola, turma, formato):
    """ZIP com a ficha da turma e a relação nominal dos alunos, ambos em `formato` (pdf ou xlsx)."""
    ocupacao_alunos = alunos_da_turma(turma)
    if formato == 'xlsx':
        ficheiros = {'1_ficha_da_turma.xlsx': xlsx_turma(escola, turma, len(ocupacao_alunos)),
                     '2_relacao_nominal_dos_alunos.xlsx': xlsx_relacao_nominal(escola, turma, ocupacao_alunos)}
    else:
        ficheiros = {'1_ficha_da_turma.pdf': pdf_turma(escola, turma, len(ocupacao_alunos)),
                     '2_relacao_nominal_dos_alunos.pdf': pdf_relacao_nominal(escola, turma, ocupacao_alunos)}
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, 'w', zipfile.ZIP_DEFLATED) as z:
        for nome, dados in ficheiros.items():
            z.writestr(nome, dados)
    return saida.getvalue()
