"""Excel (.xlsx) do calendário de exames, júris, excluídos e exames do aluno.

Gravação sempre por guardar_xlsx_seguro (docs/REGRAS_EXCEL_E_PDF.md): Times New Roman 12, cabeçalhos
centrados, linhas/colunas vazias ocultas, molduras e zebra aplicadas por embelezar_workbook.
"""
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from apps.documentos.services.xlsx_seguro import guardar_xlsx_seguro

PERIODOS = {'MANHA': 'Manhã', 'TARDE': 'Tarde', 'NOITE': 'Noturno'}
_AZUL = PatternFill('solid', fgColor='1E3A8A')
_BRANCO_B = Font(name='Times New Roman', size=12, bold=True, color='FFFFFF')
_NEGRITO = Font(name='Times New Roman', size=12, bold=True)


def _data_pt(iso):
    if not iso:
        return 'Por definir'
    y, m, d = (int(x) for x in iso.split('-'))
    return f'{d:02d}/{m:02d}/{y}'


def _nota(v):
    return '—' if v is None else float(f'{v:.1f}')


def _titulos(ws, escola, titulo, subtitulo=''):
    ws.append([(escola.nome or '').upper()])
    ws.append([titulo])
    if subtitulo:
        ws.append([subtitulo])
    ws.append([])
    for r in range(1, ws.max_row + 1):
        ws.cell(r, 1).font = _NEGRITO


def _cabecalho(ws, colunas):
    ws.append(colunas)
    for c in ws[ws.max_row]:
        c.fill = _AZUL
        c.font = _BRANCO_B


def _bytes(wb):
    return guardar_xlsx_seguro(wb)


def xlsx_calendario(escola, ano, grupos):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Calendário'
    _titulos(ws, escola, 'CALENDÁRIO DOS EXAMES', f'Ano lectivo {ano}')
    colunas = ['Classe', 'Disciplina', 'Chamada', 'Data', 'Período', 'Início', 'Duração (min)', 'Fim']
    _cabecalho(ws, colunas)
    linhas = 0
    for classe, entradas in grupos:
        for c in entradas:
            ws.append([classe, c.disciplina, f'{c.epoca}ª', c.data.strftime('%d/%m/%Y'), PERIODOS.get(c.periodo, ''),
                       c.hora_inicio.strftime('%H:%M'), c.duracao_minutos, c.hora_fim.strftime('%H:%M')])
            linhas += 1
    if not linhas:
        ws.append(['Ainda não há datas definidas no calendário de exames.'])
    return _bytes(wb)


def xlsx_juris(escola, ano, epoca, juris):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Júris'
    _titulos(ws, escola, f'JÚRIS DE EXAME — {epoca}ª CHAMADA/ÉPOCA', f'Ano lectivo {ano}')
    if not juris:
        ws.append(['Ainda não há júris formados.'])
    for j in juris:
        ws.append([f'Júri {j["numero"]} · {j["classe"]} · {j["disciplina"]}'])
        ws.cell(ws.max_row, 1).font = _NEGRITO
        horario = f'{j["hora_inicio"]} – {j["hora_fim"]} ({j["duracao_minutos"]} min)' if j['hora_inicio'] else 'por definir'
        ws.append([f'Data: {_data_pt(j["data"])} | Período: {PERIODOS.get(j["periodo"], "—")} | '
                   f'Horário: {horario} | Sala: {j["sala"] or "Por atribuir"}'])
        _cabecalho(ws, ['Nº', 'Nome completo', 'Matrícula', 'Turma', 'Nota de Frequência'])
        for a in j['alunos']:
            ws.append([a['ordem'], a['nome'], a['matricula'] or '', a['turma'], _nota(a['freq'])])
        ws.append([])
    return _bytes(wb)


def xlsx_excluidos(escola, ano, classe, grupos):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Excluídos'
    _titulos(ws, escola, f'ALUNOS EXCLUÍDOS DO EXAME — {classe}',
             f'Ano lectivo {ano} · frequência igual ou inferior a 9,4 (sem direito ao exame)')
    vazio = True
    for disciplina, alunos in grupos:
        if not alunos:
            continue
        vazio = False
        ws.append([f'Disciplina: {disciplina}'])
        ws.cell(ws.max_row, 1).font = _NEGRITO
        _cabecalho(ws, ['Nº', 'Nome completo', 'Matrícula', 'Turma', 'Nota de Frequência'])
        for i, a in enumerate(alunos, 1):
            ws.append([i, a['nome'], a['aluno'].matricula or '', a['turma'], _nota(a['freq'])])
            ws.cell(ws.max_row, 5).font = Font(name='Times New Roman', size=12, color='C00000')
        ws.append([])
    if vazio:
        ws.append(['Não há alunos excluídos nesta classe.'])
    return _bytes(wb)


def xlsx_exames_aluno(escola, nome, ano, classe, itens):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Meus Exames'
    _titulos(ws, escola, 'OS MEUS EXAMES', f'{nome} · {classe} · Ano lectivo {ano}')
    _cabecalho(ws, ['Disciplina', 'Chamada', 'Data', 'Período', 'Horário', 'Júri', 'Sala'])
    linhas = 0
    for it in itens:
        if it['estado'] == 'EXCLUIDO':
            ws.append([it['disciplina'], '—', f'Excluído(a): frequência {_nota(it["nota_frequencia"])}', '', '', '', ''])
            linhas += 1
            continue
        for c in it['chamadas']:
            ws.append([it['disciplina'], f'{c["epoca"]}ª', _data_pt(c['data']), PERIODOS.get(c['periodo'], '—'),
                       f'{c["hora_inicio"]} – {c["hora_fim"]}' if c['hora_inicio'] else 'Por definir',
                       f'Júri {c["juri"]}' if c['juri'] else '—', c['sala'] or ('Por atribuir' if c['juri'] else '—')])
            linhas += 1
    if not linhas:
        ws.append(['Não há exames para si neste ano lectivo.'])
    return _bytes(wb)
