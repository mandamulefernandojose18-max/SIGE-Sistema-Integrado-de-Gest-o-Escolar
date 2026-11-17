"""Ficha de uma turma em PDF ou Excel (descarregada a partir do botão «Descarregar» da linha da turma).

Regras: docs/REGRAS_EXCEL_E_PDF.md (Times New Roman, cabeçalhos centrados, Excel por guardar_xlsx_seguro).
O carimbo é aplicado pelo CarimboDownloadsMiddleware a partir de `?carimbo=sim|nao`.
"""
import io
from datetime import date

from openpyxl import Workbook

from apps.documentos.services.xlsx_seguro import guardar_xlsx_seguro
from apps.notas.exames_pdf import _cabecalho, _doc, _esc, _tabela
from apps.notas.exames_xlsx import _cabecalho as _cab_xlsx, _titulos
from apps.documentos.services.pdf_service import Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm

TURNOS = {'MANHA': 'Manhã', 'TARDE': 'Tarde', 'NOITE': 'Noite'}


def _director(nome, status, codigo):
    if not nome:
        return 'Não definido'
    if status == 'HOMOLOGADO' and codigo:
        return f'{nome} (homologado · código {codigo})'
    if status in ('PENDENTE', 'PENDENTE_HOMOLOGACAO'):
        return f'{nome} (nomeado, a aguardar homologação)'
    return nome


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


def pdf_turma(escola, turma, ocupacao):
    buf = io.BytesIO()
    el = _cabecalho(escola, f'FICHA DA TURMA — {turma.nome}', f'{turma.grau_ano} · Ano lectivo {turma.ano_letivo}')
    linhas = [[c, v] for c, v in linhas_ficha(turma, ocupacao)]
    el.append(_tabela(['Campo', 'Informação'], [[_esc(c), v] for c, v in linhas], [5.0 * cm, 12.0 * cm], esq=1))
    el += [Spacer(1, 0.3 * cm), Paragraph(f'Emitido em {date.today():%d/%m/%Y}.', ParagraphStyle('ExE', fontName='Times-Italic'))]
    _doc(buf).build(el)
    return buf.getvalue()


def xlsx_turma(escola, turma, ocupacao):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Turma'
    _titulos(ws, escola, f'FICHA DA TURMA — {turma.nome}', f'{turma.grau_ano} · Ano lectivo {turma.ano_letivo}')
    _cab_xlsx(ws, ['Campo', 'Informação'])
    for c, v in linhas_ficha(turma, ocupacao):
        ws.append([c, v])
    return guardar_xlsx_seguro(wb)
