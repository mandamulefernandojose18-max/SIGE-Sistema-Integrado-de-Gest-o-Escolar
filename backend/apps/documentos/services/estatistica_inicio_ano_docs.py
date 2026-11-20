"""PDF e Excel do Mapa Estatístico de Início do Ano (turma, classe e escola).

Um só modelo de documento (`montar_paginas`) alimenta os dois formatos, para que PDF e Excel tragam
exactamente os mesmos números. Regras de qualidade: docs/REGRAS_EXCEL_E_PDF.md (Times New Roman,
cabeçalhos centrados, palavras inteiras, Excel gravado por guardar_xlsx_seguro).
"""
import datetime
import io
import re

LEGENDA_NEE = (
    'DV – Deficiência visual; DAU – Deficiência auditiva; DFM – Deficiência física/motora; '
    'DAP – Dificuldades de aprendizagem; ALB – Albinismo; PC – Problemas comportamentais; OUTRA – Outras necessidades.'
)
SIGLAS_NEE = ['DV', 'DAU', 'DFM', 'DAP', 'ALB', 'PC', 'OUTRA']


# ---------------------------------------------------------------------------
# Modelo comum
# ---------------------------------------------------------------------------
def _tabela(titulo, cab, linhas, esq=(), total=False, nota=''):
    return {'titulo': titulo, 'cab': cab, 'linhas': linhas, 'esq': tuple(esq), 'total': total, 'nota': nota}


def _horizontal(titulo, itens, rotulo_total='Total', nota=''):
    """Tabela com Sexo nas linhas (H, M, HM) e as categorias nas colunas."""
    cab = ['Sexo'] + [i['rotulo'] for i in itens] + [rotulo_total]
    h = [i['h'] for i in itens]
    m = [i['m'] for i in itens]
    linhas = [['H'] + h + [sum(h)], ['M'] + m + [sum(m)], ['HM'] + [a + b for a, b in zip(h, m)] + [sum(h) + sum(m)]]
    return _tabela(titulo, cab, linhas, total=True, nota=nota)


def _tabelas_do_mapa(mapa):
    mat = mapa['matriculados']
    tabelas = [_tabela('1. Efectivo escolar matriculado', ['Homens (H)', 'Mulheres (M)', 'Total (HM)'],
                       [[mat['h'], mat['m'], mat['t']]])]
    idades = mapa['idades']
    if idades:
        tabelas.append(_horizontal('2. Idade dos alunos (anos completados no ano lectivo)', idades))
    else:
        tabelas.append(_tabela('2. Idade dos alunos (anos completados no ano lectivo)', ['Sexo', 'Total'],
                               [['H', 0], ['M', 0], ['HM', 0]], total=True))
    nee = [dict(i, rotulo=i['codigo']) for i in mapa['nee']]
    tabelas.append(_horizontal('3. Necessidades educativas especiais', nee, nota=LEGENDA_NEE))
    tabelas.append(_horizontal('4. Alunos órfãos', mapa['orfaos']))
    tabelas.append(_horizontal('5. Meios de transporte para o acesso à escola', mapa['transporte']))
    linhas = [[i['rotulo'], i['h'], i['m'], i['t'], i.get('locais') or '-'] for i in mapa['tempo']]
    th, tm = sum(i['h'] for i in mapa['tempo']), sum(i['m'] for i in mapa['tempo'])
    linhas.append(['Total', th, tm, th + tm, ''])
    tabelas.append(_tabela('6. Tempo gasto de casa à escola e local de residência',
                           ['Tempo', 'H', 'M', 'HM', 'Local de residência'], linhas, esq=(0, 4), total=True))
    return tabelas


def _tabela_disciplinas(disciplinas, com_classe=True):
    cab = (['Classe'] if com_classe else []) + ['Secção / Área', 'Disciplina', 'Professor(es)', 'Turmas', 'H', 'M', 'HM']
    linhas = []
    for d in disciplinas:
        linhas.append(([d['classe']] if com_classe else []) + [d['area'], d['nome'], d['professor'] or '-',
                                                              d['turmas'], d['h'], d['m'], d['t']])
    n = 3 if com_classe else 2
    if not linhas:
        linhas = [['Sem disciplinas no Plano Curricular desta classe/secção.'] + [''] * (len(cab) - 1)]
    return _tabela('7. Disciplinas do 2º Ciclo (por secção/área)', cab, linhas, esq=tuple(range(n + 1)))


def _total_linhas(linhas, colunas_soma, rotulo='Total', n_cols=None):
    n = n_cols or len(linhas[0])
    tot = [rotulo] + [''] * (n - 1)
    for c in colunas_soma:
        tot[c] = sum(l[c] for l in linhas)
    return tot


def _data_ref(ano):
    return f'03/03/{ano}'


def montar_paginas(dados):
    """Devolve lista de páginas: {'titulo','subtitulo','nome_folha','tabelas'}."""
    tipo, ano = dados['tipo'], dados['ano']
    if tipo == 'turma':
        t = dados['turma']
        tabelas = _tabelas_do_mapa(dados['mapa'])
        if dados['ciclo'] == 2:
            tabelas.append(_tabela_disciplinas(dados['disciplinas'], com_classe=False))
        sub = (f"{t['classe']} | Secção/Área: {t['area']} | Turno: {t['turno']} | "
               f"Director de Turma: {t['director_turma'] or '-'} | Referência: {_data_ref(ano)}")
        return [{'titulo': f"MAPA ESTATÍSTICO DE INÍCIO DO ANO LECTIVO {ano} — TURMA {t['nome']}",
                 'subtitulo': sub, 'nome_folha': f"Turma {t['nome']}", 'tabelas': tabelas,
                 'mat_total': dados['mapa']['matriculados']['t']}]
    if tipo == 'classe':
        linhas = [[x['rotulo'], x['area'], x['turno'], x['director_turma'] or '-', x['h'], x['m'], x['t']]
                  for x in dados['turmas']]
        tabelas = []
        if linhas:
            linhas.append(_total_linhas(linhas, (4, 5, 6)))
            tabelas.append(_tabela('Turmas da classe (mapas das turmas somados automaticamente)',
                                   ['Turma', 'Secção / Área', 'Turno', 'Director de Turma', 'H', 'M', 'HM'],
                                   linhas, esq=(0, 1, 2, 3), total=True))
        tabelas += _tabelas_do_mapa(dados['mapa'])
        if dados['ciclo'] == 2:
            tabelas.append(_tabela_disciplinas(dados['disciplinas'], com_classe=False))
        sub = f"Director de Classe: {dados['director_classe'] or '-'} | Referência: {_data_ref(ano)}"
        return [{'titulo': f"MAPA ESTATÍSTICO DE INÍCIO DO ANO LECTIVO {ano} — {str(dados['classe']).upper()}",
                 'subtitulo': sub, 'nome_folha': dados['classe'], 'tabelas': tabelas,
                 'mat_total': dados['mapa']['matriculados']['t']}]
    paginas = []
    for g in dados['grupos']:
        tabelas = []
        linhas = [[c['rotulo'], c['turmas'], c['h'], c['m'], c['t']] for c in g['classes']]
        if linhas:
            linhas.append(_total_linhas(linhas, (1, 2, 3, 4)))
            tabelas.append(_tabela('Classes (mapas das classes somados automaticamente)',
                                   ['Classe', 'Turmas', 'H', 'M', 'HM'], linhas, esq=(0,), total=True))
        tabelas += _tabelas_do_mapa(g['mapa'])
        if g['chave'] == 'CICLO2':
            tabelas.append(_tabela_disciplinas(g['disciplinas'], com_classe=True))
        paginas.append({
            'titulo': f"MAPA ESTATÍSTICO GERAL DA ESCOLA — INÍCIO DO ANO LECTIVO {ano}",
            'subtitulo': f"{g['titulo']} | Referência: {_data_ref(ano)}",
            'nome_folha': g['titulo'].split('(')[0].strip(), 'tabelas': tabelas,
            'mat_total': g['mapa']['matriculados']['t'],
        })
    return paginas


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------
def gerar_estatistica_inicio_ano_pdf(escola, dados) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak
    from .pdf_service import (
        _ReportLabSimpleDocTemplate, obter_tamanho_pagina, getSampleStyleSheet, gerar_cabecalho_mec,
        _estilo_denso, _obter_campo_escola,
    )
    from xml.sax.saxutils import escape

    buffer = io.BytesIO()
    page_size = obter_tamanho_pagina('landscape', padrao='landscape')
    doc = _ReportLabSimpleDocTemplate(buffer, pagesize=page_size, rightMargin=1.0 * cm, leftMargin=1.0 * cm,
                                      topMargin=0.8 * cm, bottomMargin=0.8 * cm)
    styles = getSampleStyleSheet()
    nome = _obter_campo_escola(escola, 'nome', 'Escola Secundária')
    prov = _obter_campo_escola(escola, 'provincia', '')
    dist = _obter_campo_escola(escola, 'distrito', '')
    NAVY, OURO = colors.HexColor('#1e3a8a'), colors.HexColor('#c9a227')
    s_tit = _estilo_denso('InTit', parent=styles['Normal'], alignment=1, fontSize=13, leading=16, fontName='Times-Bold')
    s_sub = _estilo_denso('InSub', parent=styles['Normal'], alignment=1, fontSize=10, leading=12.5, fontName='Times-Roman')
    s_sec = _estilo_denso('InSec', parent=styles['Normal'], fontSize=11, leading=14, fontName='Times-Bold', textColor=NAVY)
    s_nota = _estilo_denso('InNota', parent=styles['Normal'], fontSize=9, leading=11, fontName='Times-Italic')
    s_c = _estilo_denso('InC', fontName='Times-Roman', fontSize=10.5, leading=12.5, alignment=1)
    s_cb = _estilo_denso('InCB', fontName='Times-Bold', fontSize=10.5, leading=12.5, alignment=1)
    s_l = _estilo_denso('InL', fontName='Times-Roman', fontSize=10.5, leading=12.5, alignment=0)
    s_lb = _estilo_denso('InLB', fontName='Times-Bold', fontSize=10.5, leading=12.5, alignment=0)
    s_h = _estilo_denso('InH', fontName='Times-Bold', fontSize=10, leading=12, alignment=1, textColor=colors.white)
    largura = page_size[0] - 2.0 * cm
    plain = lambda v: re.sub(r'<[^>]+>', '', str(v))

    elements = []
    paginas = montar_paginas(dados)
    for pi, pg in enumerate(paginas):
        if pi:
            elements.append(PageBreak())
        elements += list(gerar_cabecalho_mec(styles, nome, prov, dist, compacto=True, escola=escola))
        elements.append(Paragraph(escape(pg['titulo']), s_tit))
        elements.append(Paragraph(escape(pg['subtitulo']), s_sub))
        elements.append(Spacer(1, 0.2 * cm))
        vazio = _vazio(dados, pg)
        if vazio:
            elements.append(Paragraph(escape(vazio), s_l))
            continue
        for tb in pg['tabelas']:
            elements.append(Paragraph(escape(tb['titulo']), s_sec))
            elements.append(Spacer(1, 0.08 * cm))
            n = len(tb['cab'])
            rows = [[Paragraph(escape(str(h)), s_h) for h in tb['cab']]]
            for li, ln in enumerate(tb['linhas']):
                ult = tb['total'] and li == len(tb['linhas']) - 1
                rows.append([Paragraph(escape(str(v)), (s_lb if ult else s_l) if ci in tb['esq'] else (s_cb if ult else s_c))
                             for ci, v in enumerate(ln)])
            minimo, natural = [], []
            for ci in range(n):
                palavras = plain(tb['cab'][ci]).split() or ['']
                w_min = max(stringWidth(w, 'Times-Bold', 10) for w in palavras) + 10
                textos = [plain(ln[ci]) for ln in tb['linhas']] or ['']
                w_nat = max([stringWidth(t, 'Times-Roman', 10.5) for t in textos] + [stringWidth(' '.join(palavras), 'Times-Bold', 10)]) + 12
                minimo.append(w_min)
                natural.append(max(w_nat, w_min))
            tot_nat = sum(natural)
            if tot_nat > largura:
                livre, exc = largura - sum(minimo), tot_nat - sum(minimo)
                larg = [m + (nt - m) * (livre / exc if exc > 0 else 0) for m, nt in zip(minimo, natural)]
            else:
                larg = [nt + (largura - tot_nat) * (nt / tot_nat) for nt in natural]
            larg[-1] += largura - sum(larg)
            t = Table(rows, colWidths=larg, repeatRows=1)
            est = [
                ('BACKGROUND', (0, 0), (-1, 0), NAVY), ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#94a3b8')),
                ('BOX', (0, 0), (-1, -1), 1.4, NAVY), ('LINEBELOW', (0, 0), (-1, 0), 1.4, OURO),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3), ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f1f5f9')]),
            ]
            if tb['total']:
                est.append(('BACKGROUND', (0, len(rows) - 1), (-1, len(rows) - 1), colors.HexColor('#e2e8f0')))
            t.setStyle(TableStyle(est))
            elements.append(t)
            if tb['nota']:
                elements.append(Paragraph(escape(tb['nota']), s_nota))
            elements.append(Spacer(1, 0.2 * cm))
        elements += _assinaturas(Table, TableStyle, Paragraph, s_c, largura, escape, dados)
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def _assinaturas(Table, TableStyle, Paragraph, estilo, largura, escape, dados):
    from reportlab.lib.units import cm
    from reportlab.platypus import Spacer
    quem = {'turma': 'O Director de Turma', 'classe': 'O Director de Classe'}.get(dados['tipo'], 'O Director Pedagógico')
    t = Table([[Paragraph(escape(quem), estilo), Paragraph('O Director da Escola', estilo)]], colWidths=[largura / 2] * 2)
    t.setStyle(TableStyle([('LINEABOVE', (0, 0), (0, 0), 0.6, '#000000'), ('LINEABOVE', (1, 0), (1, 0), 0.6, '#000000')]))
    return [Spacer(1, 0.9 * cm), t]


def _vazio(dados, pg):
    """Estado vazio real: sem alunos matriculados (ATIVO) não há mapa a apresentar; nenhum dado é inventado."""
    if pg.get('mat_total', 0) == 0:
        return 'Sem alunos matriculados (estado ATIVO) nesta selecção para o ano lectivo %s.' % dados['ano']
    return ''


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------
def gerar_estatistica_inicio_ano_xlsx(escola, dados) -> bytes:
    import openpyxl
    from openpyxl.utils import get_column_letter
    from .xlsx_seguro import nome_folha
    from .excel_service import (
        configurar_pagina_excel, inserir_logo_cabecalho_xlsx, salvar_xlsx_padronizado, _obter_campo_escola,
        FONT_TITLE, FONT_SUBTITLE, FONT_REGULAR, FONT_REGULAR_BOLD, FONT_HEADER, FILL_NAVY, FILL_GRAY,
        ALIGN_CENTER, ALIGN_LEFT, THIN_BORDER,
    )
    wb = openpyxl.Workbook()
    nome = _obter_campo_escola(escola, 'nome', 'Escola Secundária')
    paginas = montar_paginas(dados)
    for pi, pg in enumerate(paginas):
        ws = wb.active if pi == 0 else wb.create_sheet()
        ws.title = nome_folha(pg['nome_folha'])
        configurar_pagina_excel(ws, orientacao='landscape')
        inserir_logo_cabecalho_xlsx(ws, escola, cell='A1')
        ncols = max([len(t['cab']) for t in pg['tabelas']] + [8])
        fim = get_column_letter(ncols)
        textos = [
            ('REPÚBLICA DE MOÇAMBIQUE — MINISTÉRIO DA EDUCAÇÃO E CULTURA', FONT_SUBTITLE),
            (nome.upper(), FONT_TITLE), (pg['titulo'], FONT_TITLE), (pg['subtitulo'], FONT_REGULAR),
        ]
        for i, (txt, fonte) in enumerate(textos, start=1):
            ws.merge_cells(f'A{i}:{fim}{i}')
            ws[f'A{i}'] = txt
            ws[f'A{i}'].font = fonte
            ws[f'A{i}'].alignment = ALIGN_CENTER
            ws.row_dimensions[i].height = 40 if i == 4 else 24
        row = 6
        vazio = _vazio(dados, pg)
        if vazio:
            ws.merge_cells(f'A{row}:{fim}{row}')
            ws[f'A{row}'] = vazio
            ws[f'A{row}'].font = FONT_REGULAR
            ws[f'A{row}'].alignment = ALIGN_LEFT
            continue
        largura = [10] * ncols
        for tb in pg['tabelas']:
            ws.cell(row=row, column=1, value=tb['titulo']).font = FONT_REGULAR_BOLD
            row += 1
            for ci, h in enumerate(tb['cab'], start=1):
                c = ws.cell(row=row, column=ci, value=h)
                c.font, c.fill, c.alignment, c.border = FONT_HEADER, FILL_NAVY, ALIGN_CENTER, THIN_BORDER
                largura[ci - 1] = max(largura[ci - 1], max(len(p) for p in (str(h).split() or [''])) + 3)
            row += 1
            for li, ln in enumerate(tb['linhas']):
                ult = tb['total'] and li == len(tb['linhas']) - 1
                for ci, v in enumerate(ln, start=1):
                    c = ws.cell(row=row, column=ci, value=v)
                    c.font = FONT_REGULAR_BOLD if ult else FONT_REGULAR
                    c.alignment = ALIGN_LEFT if (ci - 1) in tb['esq'] else ALIGN_CENTER
                    c.border = THIN_BORDER
                    if ult:
                        c.fill = FILL_GRAY
                    largura[ci - 1] = max(largura[ci - 1], min(len(str(v)) + 3, 60))
                row += 1
            if tb['nota']:
                ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncols)
                ws.cell(row=row, column=1, value=tb['nota']).alignment = ALIGN_LEFT
                ws.cell(row=row, column=1).font = FONT_REGULAR
                ws.row_dimensions[row].height = 40
                row += 1
            row += 1
        for ci, w in enumerate(largura, start=1):
            ws.column_dimensions[get_column_letter(ci)].width = w
        row += 1
        quem = {'turma': 'O Director de Turma', 'classe': 'O Director de Classe'}.get(dados['tipo'], 'O Director Pedagógico')
        ws.cell(row=row, column=2, value=quem).font = FONT_REGULAR_BOLD
        ws.cell(row=row, column=min(6, ncols), value='O Director da Escola').font = FONT_REGULAR_BOLD
    buffer = io.BytesIO()
    salvar_xlsx_padronizado(wb, buffer)
    buffer.seek(0)
    return buffer.getvalue()

