"""
Serviço de Exportação em Excel (XLSX) — SIGE (Sistema Integrado de Gestão Escolar)
Gera planilhas oficiais com OpenPyXL formatadas rigorosamente em Times New Roman,
com colunas auto-ajustadas (sem corte de textos nem '###'), bordas completas,
e controle de orientação de impressão (Landscape para Pauta e Portrait para Boletins/Declarações).
"""
import io
import re
import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.pagebreak import RowBreak, ColBreak
from common.utils.avaliacoes_mocambique import obter_nome_completo_aluno

# Estilos padrão Times New Roman — Rigorosamente Tamanho 12 e Espaçamento 1,5
FONT_TITLE = Font(name='Times New Roman', size=12, bold=True, color='000000')
FONT_SUBTITLE = Font(name='Times New Roman', size=12, bold=True, color='333333')
FONT_HEADER = Font(name='Times New Roman', size=12, bold=True, color='FFFFFF')
FONT_REGULAR = Font(name='Times New Roman', size=12, bold=False, color='000000')
FONT_REGULAR_BOLD = Font(name='Times New Roman', size=12, bold=True, color='000000')
FONT_SMALL = Font(name='Times New Roman', size=12, bold=False, color='222222')
FONT_SMALL_BOLD = Font(name='Times New Roman', size=12, bold=True, color='000000')
FONT_RED = Font(name='Times New Roman', size=12, bold=True, color='DC2626')
FONT_GREEN = Font(name='Times New Roman', size=12, bold=True, color='15803D')

FILL_NAVY = PatternFill(start_color='1E3A8A', end_color='1E3A8A', fill_type='solid')
FILL_LIGHT_GRAY = PatternFill(start_color='F1F5F9', end_color='F1F5F9', fill_type='solid')
FILL_LIGHT = PatternFill(start_color='F8FAFC', end_color='F8FAFC', fill_type='solid')
FILL_GRAY = PatternFill(start_color='E2E8F0', end_color='E2E8F0', fill_type='solid')

ALIGN_CENTER = Alignment(horizontal='center', vertical='center', wrap_text=True)
ALIGN_LEFT = Alignment(horizontal='left', vertical='center', wrap_text=True)
ALIGN_RIGHT = Alignment(horizontal='right', vertical='center', wrap_text=True)

THIN_BORDER = Border(
    left=Side(style='thin', color='94A3B8'),
    right=Side(style='thin', color='94A3B8'),
    top=Side(style='thin', color='94A3B8'),
    bottom=Side(style='thin', color='94A3B8')
)

THICK_BOTTOM_BORDER = Border(
    bottom=Side(style='medium', color='1E3A8A')
)

FONT_TINY = Font(name='Times New Roman', size=12, bold=False, color='000000')
FONT_TINY_BOLD = Font(name='Times New Roman', size=12, bold=True, color='000000')
FONT_HEADER_SM = Font(name='Times New Roman', size=12, bold=True, color='FFFFFF')
FONT_MUTED_ITALIC = Font(name='Times New Roman', size=12, italic=True, color='64748B')
FONT_SUCCESS_SM = Font(name='Times New Roman', size=12, bold=True, color='166534')
FONT_DANGER_SM = Font(name='Times New Roman', size=12, bold=True, color='DC2626')
FONT_GREEN_SM = Font(name='Times New Roman', size=12, bold=True, color='059669')
FONT_RED_SM = Font(name='Times New Roman', size=12, bold=True, color='DC2626')

def finalizar_formatacao_documento_xlsx(wb):
    for ws in wb.worksheets:
        ws.sheet_format.defaultRowHeight = 22
        for r_idx in range(1, ws.max_row + 1):
            cur_h = ws.row_dimensions[r_idx].height
            if cur_h is None or cur_h < 22:
                ws.row_dimensions[r_idx].height = 22
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is not None or cell.comment or (cell.fill and getattr(cell.fill, 'fill_type', None)):
                    curr_font = cell.font
                    if curr_font:
                        cell.font = Font(
                            name='Times New Roman',
                            size=12,
                            bold=curr_font.bold,
                            italic=curr_font.italic,
                            color=curr_font.color,
                            underline=curr_font.underline,
                            strike=curr_font.strike
                        )
                    else:
                        cell.font = FONT_REGULAR

def salvar_xlsx_padronizado(wb, buffer):
    finalizar_formatacao_documento_xlsx(wb)
    wb.save(buffer)

FILL_SUCCESS = PatternFill(start_color='DCFCE7', end_color='DCFCE7', fill_type='solid')
FILL_ROW_HM = PatternFill(start_color='F1F5F9', end_color='F1F5F9', fill_type='solid')
FILL_ROW_SUCCESS = PatternFill(start_color='D1FAE5', end_color='D1FAE5', fill_type='solid')
FILL_ROW_DANGER = PatternFill(start_color='FEE2E2', end_color='FEE2E2', fill_type='solid')
FILL_ROW_BLUE = PatternFill(start_color='DBEAFE', end_color='DBEAFE', fill_type='solid')
FILL_ROW_GRAY = PatternFill(start_color='E5E7EB', end_color='E5E7EB', fill_type='solid')

def aplicar_estilo_intervalo(ws, min_col, min_row, max_col, max_row, font=None, fill=None, border=THIN_BORDER, alignment=None):
    for r in range(min_row, max_row + 1):
        for c in range(min_col, max_col + 1):
            cell = ws.cell(row=r, column=c)
            if font is not None:
                cell.font = font
            if fill is not None:
                cell.fill = fill
            if border is not None:
                cell.border = border
            if alignment is not None:
                cell.alignment = alignment

def auto_ajustar_colunas(ws, padding=4):
    """Calcula largura automática para todas as colunas garantindo zero cortes de texto."""
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            # Não considerar células mescladas para o cálculo de largura de uma única coluna
            if cell.coordinate in ws.merged_cells:
                continue
            val_str = str(cell.value or '')
            if '\n' in val_str:
                lines = val_str.split('\n')
                max_len = max(max_len, max(len(l) for l in lines))
            else:
                max_len = max(max_len, len(val_str))
        ws.column_dimensions[col_letter].width = max(max_len + padding, 10)

def configurar_pagina_excel(ws, orientacao='portrait', fit_to_height=0):
    """Configura A4, orientação e ajuste de página para impressão sem cortes nem quebras indevidas."""
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    if orientacao.lower() in ('landscape', 'horizontal'):
        ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    else:
        ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
    
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = fit_to_height
    ws.page_margins.left = 0.5
    ws.page_margins.right = 0.5
    ws.page_margins.top = 0.5
    ws.page_margins.bottom = 0.5

def _obter_campo_escola(escola, campo, padrao=''):
    if not escola:
        return padrao
    if isinstance(escola, dict):
        return escola.get(campo, padrao) or padrao
    return getattr(escola, campo, padrao) or padrao

def inserir_logo_cabecalho_xlsx(ws, escola, cell='A1'):
    """
    Insere o logótipo oficial que a instituição escolheu para documentos na planilha Excel.
    Regra Mandatória: Nenhum documento deve ser descarregado sem o logótipo que a instituição terá escolhido para documentos.
    """
    from .pdf_service import resolver_logo_documento_escola, DocumentoSemLogoError
    logo_bytes, _, _, _ = resolver_logo_documento_escola(escola)
    if not logo_bytes:
        raise DocumentoSemLogoError(
            "Nenhum documento pode ser descarregado sem o logótipo que a instituição escolheu para usar em documentos. "
            "Por favor, aceda às Configurações da Escola (Identidade Visual) para definir o logótipo oficial nos documentos."
        )
    try:
        from openpyxl.drawing.image import Image as OpenpyxlImage
        img = OpenpyxlImage(io.BytesIO(logo_bytes))
        img.width = 46
        img.height = 46
        ws.add_image(img, cell)
    except Exception:
        pass

# ==================== 1. PAUTA GERAL DA TURMA (HORIZONTAL) ====================

def gerar_pauta_xlsx(turma, escola, periodo, ano_letivo, dados_alunos, disciplinas, orientacao='landscape') -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    turma_nome = turma.nome if getattr(turma, 'nome', None) else 'Turma'
    ws.title = f"Pauta {turma_nome[:25]}"
    configurar_pagina_excel(ws, orientacao=orientacao, fit_to_height=0)

    # Logótipo Oficial Escolhido pela Instituição
    inserir_logo_cabecalho_xlsx(ws, escola, cell='A1')

    n_discs = max(len(disciplinas), 1)
    # Total de colunas: 3 (Nº, Nome, Gén) + (n_discs * 4) + 3 (Médias Trim) + 4 (Negativas) + 1 (MG) + 1 (Resultado)
    total_cols = 3 + (n_discs * 4) + 3 + 4 + 1 + 1
    end_col_letter = get_column_letter(total_cols)

    prov_str = (getattr(escola, 'provincia', '') or 'Inhambane').upper()
    dist_str = (getattr(escola, 'distrito', '') or 'Morrumbene').upper()
    esc_nome = (getattr(escola, 'nome', '') or 'Escola Secundária').upper()
    dt_nome = turma.director_turma.nome if getattr(turma, 'director_turma', None) else "Manuel"
    grau_ano = turma.grau_ano if getattr(turma, 'grau_ano', None) else '10ª Classe'
    turno = turma.turno if getattr(turma, 'turno', None) else 'MANHA'

    # 1. Cabeçalho Oficial Idêntico ao de PDF
    ws.merge_cells(f'A1:{end_col_letter}1')
    ws['A1'] = "REPÚBLICA DE MOÇAMBIQUE"
    ws['A1'].font = FONT_SUBTITLE
    ws['A1'].alignment = ALIGN_CENTER
    ws.row_dimensions[1].height = 20

    ws.merge_cells(f'A2:{end_col_letter}2')
    ws['A2'] = f"GOVERNO DA PROVÍNCIA DE {prov_str} | DISTRITO DE {dist_str}"
    ws['A2'].font = FONT_REGULAR
    ws['A2'].alignment = ALIGN_CENTER
    ws.row_dimensions[2].height = 18

    ws.merge_cells(f'A3:{end_col_letter}3')
    ws['A3'] = esc_nome
    ws['A3'].font = FONT_TITLE
    ws['A3'].alignment = ALIGN_CENTER
    ws.row_dimensions[3].height = 22

    ws.merge_cells(f'A4:{end_col_letter}4')
    ws['A4'] = f"PAUTA OFICIAL DE APROVEITAMENTO PEDAGÓGICO — ANO LECTIVO {ano_letivo or 2026}"
    ws['A4'].font = FONT_TITLE
    ws['A4'].alignment = ALIGN_CENTER
    ws.row_dimensions[4].height = 24

    ws.merge_cells(f'A5:{end_col_letter}5')
    ws['A5'] = f"Turma: {turma_nome} | Classe: {grau_ano} | Turno: {turno} | Director de Turma: {dt_nome}"
    ws['A5'].font = FONT_REGULAR
    ws['A5'].alignment = ALIGN_CENTER
    ws.row_dimensions[5].height = 20

    # 2. Cabeçalho da Tabela em 2 Linhas (Linhas 7 e 8)
    ws.merge_cells('A7:A8')
    ws['A7'] = 'Nº'
    ws.merge_cells('B7:B8')
    ws['B7'] = 'Nome Completo do Aluno'
    ws.merge_cells('C7:C8')
    ws['C7'] = 'Gén'

    c_cur = 4
    for d in disciplinas:
        raw_disc = getattr(d, 'nome', None) or getattr(d, 'codigo', None) or str(d)
        nome_disc = str(raw_disc)
        c_end = c_cur + 3
        ws.merge_cells(start_row=7, start_column=c_cur, end_row=7, end_column=c_end)
        ws.cell(row=7, column=c_cur, value=nome_disc)
        ws.cell(row=8, column=c_cur, value='1º')
        ws.cell(row=8, column=c_cur + 1, value='2º')
        ws.cell(row=8, column=c_cur + 2, value='3º')
        ws.cell(row=8, column=c_cur + 3, value='MFD')
        c_cur += 4

    # Médias Trimestrais
    med_start = c_cur
    ws.merge_cells(start_row=7, start_column=med_start, end_row=7, end_column=med_start + 2)
    ws.cell(row=7, column=med_start, value='Médias Trimestrais')
    ws.cell(row=8, column=med_start, value='1º')
    ws.cell(row=8, column=med_start + 1, value='2º')
    ws.cell(row=8, column=med_start + 2, value='3º')
    c_cur += 3

    # Disciplinas Negativas
    neg_start = c_cur
    ws.merge_cells(start_row=7, start_column=neg_start, end_row=7, end_column=neg_start + 3)
    ws.cell(row=7, column=neg_start, value='Disciplinas Negativas')
    ws.cell(row=8, column=neg_start, value='1º')
    ws.cell(row=8, column=neg_start + 1, value='2º')
    ws.cell(row=8, column=neg_start + 2, value='3º')
    ws.cell(row=8, column=neg_start + 3, value='Total')
    c_cur += 4

    # Média Geral & Resultado
    mg_col = c_cur
    res_col = c_cur + 1
    ws.merge_cells(start_row=7, start_column=mg_col, end_row=8, end_column=mg_col)
    ws.cell(row=7, column=mg_col, value='Média Geral')
    ws.merge_cells(start_row=7, start_column=res_col, end_row=8, end_column=res_col)
    ws.cell(row=7, column=res_col, value='Resultado')

    ws.row_dimensions[7].height = 24
    ws.row_dimensions[8].height = 22
    aplicar_estilo_intervalo(ws, 1, 7, total_cols, 8, font=FONT_HEADER_SM, fill=FILL_NAVY, border=THIN_BORDER, alignment=ALIGN_CENTER)

    # 3. Linhas dos Alunos
    def _fmt_n(val):
        if val is None or val == '' or val == '-':
            return '-'
        try:
            f = float(val)
            return round(f, 1) if f % 1 != 0 else int(f)
        except (ValueError, TypeError):
            return str(val)

    current_row = 8
    for idx, aluno in enumerate(dados_alunos, start=1):
        current_row += 1
        ws.row_dimensions[current_row].height = 20

        # Nº
        c_num = ws.cell(row=current_row, column=1, value=aluno.get('numero') or idx)
        c_num.font = FONT_TINY
        c_num.alignment = ALIGN_CENTER
        c_num.border = THIN_BORDER

        # Nome Completo
        nome_c = aluno.get('nomeCompleto') or aluno.get('nome') or obter_nome_completo_aluno(aluno)
        c_nome = ws.cell(row=current_row, column=2, value=nome_c)
        c_nome.font = FONT_TINY_BOLD
        c_nome.alignment = ALIGN_LEFT
        c_nome.border = THIN_BORDER

        # Gén
        c_gen = ws.cell(row=current_row, column=3, value=aluno.get('genero') or 'M')
        c_gen.font = FONT_TINY
        c_gen.alignment = ALIGN_CENTER
        c_gen.border = THIN_BORDER

        # Disciplinas
        c_idx = 4
        nd_dict = aluno.get('notasDisciplinas') or {}
        notas_leg = aluno.get('notas') if isinstance(aluno.get('notas'), dict) else {}
        disc_leg = aluno.get('disciplinas') if isinstance(aluno.get('disciplinas'), dict) else {}

        for d in disciplinas:
            d_id = str(getattr(d, 'id', d))
            d_cod = str(getattr(d, 'codigo', d))
            d_nome = str(getattr(d, 'nome', d))

            nd = nd_dict.get(d_cod) or nd_dict.get(d_id) or nd_dict.get(d_nome) or {}
            if not nd:
                leg_item = notas_leg.get(d_id) or notas_leg.get(d_nome) or disc_leg.get(d_nome) or disc_leg.get(d_id) or {}
                if isinstance(leg_item, dict):
                    nd = {
                        't1': leg_item.get('t1', leg_item.get('nota', '-')),
                        't2': leg_item.get('t2', '-'),
                        't3': leg_item.get('t3', '-'),
                        'mfd': leg_item.get('media_final', leg_item.get('mfd', '-'))
                    }
                else:
                    nd = {'t1': leg_item, 't2': '-', 't3': '-', 'mfd': leg_item}

            for sub_k in ['t1', 't2', 't3', 'mfd']:
                val = _fmt_n(nd.get(sub_k))
                c_cell = ws.cell(row=current_row, column=c_idx, value=val)
                c_cell.border = THIN_BORDER
                c_cell.alignment = ALIGN_CENTER
                if sub_k == 'mfd':
                    c_cell.fill = FILL_LIGHT
                    if isinstance(val, (int, float)):
                        c_cell.font = FONT_RED_SM if val < 9.5 else FONT_TINY_BOLD
                    else:
                        c_cell.font = FONT_TINY_BOLD
                else:
                    if isinstance(val, (int, float)):
                        c_cell.font = FONT_RED_SM if val < 9.5 else FONT_TINY
                    else:
                        c_cell.font = FONT_TINY
                c_idx += 1

        # Médias Trimestrais
        meds = aluno.get('mediasTrimestrais') or {}
        for m_k in ['t1', 't2', 't3']:
            m_val = _fmt_n(meds.get(m_k))
            c_m = ws.cell(row=current_row, column=c_idx, value=m_val)
            c_m.border = THIN_BORDER
            c_m.alignment = ALIGN_CENTER
            if isinstance(m_val, (int, float)) and m_val < 9.5:
                c_m.font = FONT_RED_SM
            else:
                c_m.font = FONT_TINY
            c_idx += 1

        # Disciplinas Negativas
        negs = aluno.get('negativas') or {}
        for n_k in ['t1', 't2', 't3', 'fimDoAno']:
            n_val = negs.get(n_k, aluno.get('total_negativas', 0) if n_k == 'fimDoAno' else '-')
            c_n = ws.cell(row=current_row, column=c_idx, value=n_val if n_val is not None else '-')
            c_n.border = THIN_BORDER
            c_n.alignment = ALIGN_CENTER
            c_n.font = FONT_TINY
            c_idx += 1

        # Média Geral
        mg = _fmt_n(aluno.get('mediaFinalGeral') or aluno.get('media_geral'))
        c_mg = ws.cell(row=current_row, column=mg_col, value=mg)
        c_mg.border = THIN_BORDER
        c_mg.alignment = ALIGN_CENTER
        if isinstance(mg, (int, float)):
            c_mg.font = FONT_RED_SM if mg < 9.5 else FONT_TINY_BOLD
        else:
            c_mg.font = FONT_TINY_BOLD

        # Resultado
        res_val = str(aluno.get('resultadoFinal') or aluno.get('resultado') or 'Aprovado').strip()
        c_res = ws.cell(row=current_row, column=res_col, value=res_val)
        c_res.border = THIN_BORDER
        c_res.alignment = ALIGN_CENTER
        if res_val in ('Reprovado', 'R', 'Excluído'):
            c_res.font = FONT_RED_SM
        elif res_val in ('Aprovado', 'A'):
            c_res.font = FONT_GREEN_SM
        else:
            c_res.font = FONT_TINY_BOLD

    # 4. Linha de Estatísticas Oficial da Turma no Rodapé
    current_row += 1
    total_al = len(dados_alunos)
    aprovados = sum(1 for a in dados_alunos if str(a.get('resultadoFinal') or a.get('resultado') or '').startswith('Aprov'))
    reprovados = sum(1 for a in dados_alunos if str(a.get('resultadoFinal') or a.get('resultado') or '').startswith('Reprov'))
    h_tot = sum(1 for a in dados_alunos if (a.get('genero') or '').upper() == 'M')
    m_tot = sum(1 for a in dados_alunos if (a.get('genero') or '').upper().startswith('F'))
    pct_ap = round((aprovados / total_al) * 100, 1) if total_al > 0 else 0.0
    pct_rep = round((reprovados / total_al) * 100, 1) if total_al > 0 else 0.0

    resumo_pauta = f"Total Inscritos: {total_al} (H: {h_tot} | M: {m_tot}) | Avaliados: {total_al} | Aprovados: {aprovados} ({pct_ap}%) | Reprovados: {reprovados} ({pct_rep}%)"
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=total_cols)
    ws.cell(row=current_row, column=1, value=resumo_pauta)
    aplicar_estilo_intervalo(ws, 1, current_row, total_cols, current_row, font=FONT_REGULAR_BOLD, fill=FILL_GRAY, border=THIN_BORDER, alignment=ALIGN_LEFT)
    ws.row_dimensions[current_row].height = 22

    # 5. Assinaturas Oficiais da Pauta
    current_row += 2
    dap_nome = getattr(escola, 'dap_nome', 'O Director Pedagógico (DAP)') or 'O Director Pedagógico (DAP)'
    dir_nome = getattr(escola, 'director_nome', 'O Director da Escola') or 'O Director da Escola'

    col_b1_end = max(3, total_cols // 3)
    col_b2_start = col_b1_end + 1
    col_b2_end = max(col_b2_start + 2, (total_cols * 2) // 3)
    col_b3_start = col_b2_end + 1
    col_b3_end = total_cols

    # Linha Cargos
    ws.row_dimensions[current_row].height = 20
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=col_b1_end)
    ws.cell(row=current_row, column=1, value="O Director de Turma").font = FONT_REGULAR_BOLD
    ws.cell(row=current_row, column=1).alignment = ALIGN_CENTER

    ws.merge_cells(start_row=current_row, start_column=col_b2_start, end_row=current_row, end_column=col_b2_end)
    ws.cell(row=current_row, column=col_b2_start, value="O Director Pedagógico (DAP)").font = FONT_REGULAR_BOLD
    ws.cell(row=current_row, column=col_b2_start).alignment = ALIGN_CENTER

    ws.merge_cells(start_row=current_row, start_column=col_b3_start, end_row=current_row, end_column=col_b3_end)
    ws.cell(row=current_row, column=col_b3_start, value="O Director da Escola").font = FONT_REGULAR_BOLD
    ws.cell(row=current_row, column=col_b3_start).alignment = ALIGN_CENTER

    # Linha Traços
    current_row += 1
    ws.row_dimensions[current_row].height = 20
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=col_b1_end)
    ws.cell(row=current_row, column=1, value="______________________________").font = FONT_REGULAR
    ws.cell(row=current_row, column=1).alignment = ALIGN_CENTER

    ws.merge_cells(start_row=current_row, start_column=col_b2_start, end_row=current_row, end_column=col_b2_end)
    ws.cell(row=current_row, column=col_b2_start, value="______________________________").font = FONT_REGULAR
    ws.cell(row=current_row, column=col_b2_start).alignment = ALIGN_CENTER

    ws.merge_cells(start_row=current_row, start_column=col_b3_start, end_row=current_row, end_column=col_b3_end)
    ws.cell(row=current_row, column=col_b3_start, value="______________________________").font = FONT_REGULAR
    ws.cell(row=current_row, column=col_b3_start).alignment = ALIGN_CENTER

    # Linha Nomes
    current_row += 1
    ws.row_dimensions[current_row].height = 20
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=col_b1_end)
    ws.cell(row=current_row, column=1, value=str(dt_nome)).font = FONT_REGULAR
    ws.cell(row=current_row, column=1).alignment = ALIGN_CENTER

    ws.merge_cells(start_row=current_row, start_column=col_b2_start, end_row=current_row, end_column=col_b2_end)
    ws.cell(row=current_row, column=col_b2_start, value=str(dap_nome)).font = FONT_REGULAR
    ws.cell(row=current_row, column=col_b2_start).alignment = ALIGN_CENTER

    ws.merge_cells(start_row=current_row, start_column=col_b3_start, end_row=current_row, end_column=col_b3_end)
    ws.cell(row=current_row, column=col_b3_start, value=str(dir_nome)).font = FONT_REGULAR
    ws.cell(row=current_row, column=col_b3_start).alignment = ALIGN_CENTER

    # Ajuste Automático Milimétrico de Colunas em Função do Conteúdo
    max_nome_len = max((len(a.get('nomeCompleto') or a.get('nome') or obter_nome_completo_aluno(a) or '') for a in dados_alunos), default=25)
    ws.column_dimensions['A'].width = 5.0
    ws.column_dimensions['B'].width = max(28.0, min(45.0, max_nome_len + 3.0))
    ws.column_dimensions['C'].width = 5.5

    w_sub = 5.5 if n_discs >= 10 else 6.5
    for c_idx in range(4, total_cols - 1):
        col_letter = get_column_letter(c_idx)
        ws.column_dimensions[col_letter].width = w_sub

    ws.column_dimensions[get_column_letter(mg_col)].width = 9.0
    ws.column_dimensions[get_column_letter(res_col)].width = 14.0

    buffer = io.BytesIO()
    salvar_xlsx_padronizado(wb, buffer)
    buffer.seek(0)
    return buffer.getvalue()

# ==================== 1.1 PAUTA DE EXAMES OFICIAIS ====================

def gerar_pauta_exames_xlsx(dados_pauta, escola, ano_letivo='2026', orientacao='landscape') -> bytes:
    """
    Gera a planilha Excel oficial da Pauta de Exames fiel ao modelo MEC:
    - Disciplinas e Médias de Proveniência (Frequência) extraídas diretamente das pautas de frequência.
    - Sub-colunas para disciplinas com exame: Frequência (Proven.), Exame 1ª, Exame 2ª, Média.
    - Coluna única para disciplinas sem exame: Frequência.
    - RESULTADO FINAL: Aprovado(a), MF, Disciplina(s) que Reprovou.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    turma_info = dados_pauta.get('turma', {})
    turma_nome = turma_info.get('nome', 'Turma')
    ws.title = f"Exames {turma_nome[:20]}"
    configurar_pagina_excel(ws, orientacao=orientacao)

    disciplinas = dados_pauta.get('disciplinas', [])
    disciplinas_com_exame = dados_pauta.get('disciplinas_com_exame', [])
    disciplinas_sem_exame = dados_pauta.get('disciplinas_sem_exame', [])
    alunos = dados_pauta.get('alunos', [])

    # Total de colunas: 5 (Nº, Nº Candidato, Nome, Género, Turma) + len(com_exame)*4 + len(sem_exame)*1 + 3 (Aprovado, MF, Disciplinas que Reprovou)
    total_cols = 5 + (len(disciplinas_com_exame) * 4) + (len(disciplinas_sem_exame) * 1) + 3
    end_col_letter = get_column_letter(total_cols)

    esc_obj = escola or dados_pauta.get('escola', {})
    if isinstance(esc_obj, dict):
        esc_nome = esc_obj.get('nome') or 'Escola Secundária de Massinga'
        prov_str = esc_obj.get('provincia') or 'Inhambane'
        dist_str = esc_obj.get('distrito') or 'Massinga'
    else:
        esc_nome = getattr(esc_obj, 'nome', '') or 'Escola Secundária de Massinga'
        prov_str = getattr(esc_obj, 'provincia', '') or 'Inhambane'
        dist_str = getattr(esc_obj, 'distrito', '') or 'Massinga'

    esc_nome_clean = esc_nome.strip()
    if not esc_nome_clean.upper().startswith('ESCOLA') and not esc_nome_clean.upper().startswith('INSTITUTO'):
        esc_nome_clean = f"ESCOLA {esc_nome_clean}"

    grau_area = f"{turma_info.get('grau_ano', '')} / {turma_info.get('area', '')}".strip(' /')

    # Logótipo Oficial Escolhido pela Instituição
    inserir_logo_cabecalho_xlsx(ws, esc_obj, cell='A1')

    # Linha 1: REPÚBLICA DE MOÇAMBIQUE
    ws.merge_cells(f'C1:{end_col_letter}1')
    ws['C1'] = "REPÚBLICA DE MOÇAMBIQUE"
    ws['C1'].font = FONT_TITLE
    ws['C1'].alignment = ALIGN_CENTER
    ws.row_dimensions[1].height = 22

    # Linha 2: PROVÍNCIA, DISTRITO E ESCOLA
    ws.merge_cells(f'C2:{end_col_letter}2')
    ws['C2'] = f"PROVÍNCIA DE {prov_str.upper()} | DISTRITO DE {dist_str.upper()} — {esc_nome_clean.upper()}"
    ws['C2'].font = FONT_SUBTITLE
    ws['C2'].alignment = ALIGN_CENTER
    ws.row_dimensions[2].height = 20

    # Linha 3: Classe/Área ou Secção | PAUTA DE EXAMES / Ano
    ws.merge_cells('C3:E3')
    ws['C3'] = f"Classe/Área ou Secção: {grau_area}"
    ws['C3'].font = FONT_REGULAR_BOLD
    ws['C3'].alignment = ALIGN_LEFT

    col_pauta_ano = get_column_letter(6)
    ws.merge_cells(f'{col_pauta_ano}3:{end_col_letter}3')
    ws[f'{col_pauta_ano}3'] = f"PAUTA DE EXAMES / Ano {ano_letivo}"
    ws[f'{col_pauta_ano}3'].font = FONT_TITLE
    ws[f'{col_pauta_ano}3'].alignment = ALIGN_CENTER
    ws.row_dimensions[3].height = 22

    # Linhas de Cabeçalho da Tabela: Linhas 4, 5, 6
    cols_fixas = ['Nº de Ordem', 'Nº Candidato', 'Nome do Aluno', 'Género', 'Turma']
    for idx_c, nome_c in enumerate(cols_fixas, start=1):
        c_let = get_column_letter(idx_c)
        ws.merge_cells(f'{c_let}4:{c_let}6')
        cell = ws[f'{c_let}4']
        cell.value = nome_c
        cell.font = FONT_HEADER
        cell.fill = FILL_NAVY
        cell.alignment = ALIGN_CENTER
        aplicar_estilo_intervalo(ws, idx_c, 4, idx_c, 6, font=FONT_HEADER, fill=FILL_NAVY, border=THIN_BORDER, alignment=ALIGN_CENTER)

    curr_c = 6
    # Disciplinas com exame: 4 colunas cada (Frequência Proven., Exame 1ª, Exame 2ª, Média)
    for d in disciplinas_com_exame:
        d_nome = d['nome']
        c_start = curr_c
        c_end = curr_c + 3
        # Linha 4: Nome da Disciplina mesclado nas 4 colunas
        ws.merge_cells(start_row=4, start_column=c_start, end_row=4, end_column=c_end)
        cell = ws.cell(row=4, column=c_start, value=d_nome)
        cell.font = FONT_HEADER
        cell.fill = FILL_NAVY
        cell.alignment = ALIGN_CENTER
        aplicar_estilo_intervalo(ws, c_start, 4, c_end, 4, font=FONT_HEADER, fill=FILL_NAVY, border=THIN_BORDER, alignment=ALIGN_CENTER)

        # Linha 5 e 6:
        # Col c_start: Frequência
        ws.merge_cells(start_row=5, start_column=c_start, end_row=6, end_column=c_start)
        cell_f = ws.cell(row=5, column=c_start, value="Frequência")
        cell_f.font = FONT_SMALL_BOLD
        cell_f.alignment = ALIGN_CENTER
        # Col c_start + 1: Exame 1ª época
        ws.cell(row=5, column=c_start + 1, value="Exame").font = FONT_SMALL_BOLD
        ws.cell(row=6, column=c_start + 1, value="1ª").font = FONT_SMALL_BOLD
        # Col c_start + 2: Exame 2ª época
        ws.cell(row=5, column=c_start + 2, value="Exame").font = FONT_SMALL_BOLD
        ws.cell(row=6, column=c_start + 2, value="2ª").font = FONT_SMALL_BOLD
        # Col c_start + 3: Média
        ws.merge_cells(start_row=5, start_column=c_start + 3, end_row=6, end_column=c_end)
        cell_m = ws.cell(row=5, column=c_start + 3, value="Média")
        cell_m.font = FONT_SMALL_BOLD
        cell_m.alignment = ALIGN_CENTER

        aplicar_estilo_intervalo(ws, c_start, 5, c_end, 6, font=FONT_SMALL_BOLD, fill=FILL_GRAY, border=THIN_BORDER, alignment=ALIGN_CENTER)
        curr_c += 4

    # Disciplinas sem exame: 1 coluna cada (Frequência)
    for d in disciplinas_sem_exame:
        d_nome = d['nome']
        ws.cell(row=4, column=curr_c, value=d_nome).font = FONT_HEADER
        ws.cell(row=4, column=curr_c).fill = FILL_NAVY
        ws.cell(row=4, column=curr_c).alignment = ALIGN_CENTER
        ws.cell(row=4, column=curr_c).border = THIN_BORDER

        ws.cell(row=5, column=curr_c, value="Frequência").font = FONT_SMALL_BOLD
        ws.cell(row=6, column=curr_c, value="").font = FONT_SMALL_BOLD
        aplicar_estilo_intervalo(ws, curr_c, 5, curr_c, 6, font=FONT_SMALL_BOLD, fill=FILL_LIGHT, border=THIN_BORDER, alignment=ALIGN_CENTER)
        curr_c += 1

    # RESULTADO FINAL: 3 colunas
    c_res_start = curr_c
    ws.merge_cells(start_row=4, start_column=c_res_start, end_row=4, end_column=c_res_start + 2)
    ws.cell(row=4, column=c_res_start, value="RESULTADO FINAL").font = FONT_HEADER
    ws.cell(row=4, column=c_res_start).alignment = ALIGN_CENTER
    aplicar_estilo_intervalo(ws, c_res_start, 4, c_res_start + 2, 4, font=FONT_HEADER, fill=FILL_NAVY, border=THIN_BORDER, alignment=ALIGN_CENTER)

    # Sub-cabeçalhos de resultado
    ws.merge_cells(start_row=5, start_column=c_res_start, end_row=6, end_column=c_res_start)
    ws.cell(row=5, column=c_res_start, value="Aprovado(a)").font = FONT_SMALL_BOLD
    ws.cell(row=5, column=c_res_start).alignment = ALIGN_CENTER

    ws.merge_cells(start_row=5, start_column=c_res_start + 1, end_row=6, end_column=c_res_start + 1)
    ws.cell(row=5, column=c_res_start + 1, value="MF").font = FONT_SMALL_BOLD
    ws.cell(row=5, column=c_res_start + 1).alignment = ALIGN_CENTER

    ws.merge_cells(start_row=5, start_column=c_res_start + 2, end_row=6, end_column=c_res_start + 2)
    ws.cell(row=5, column=c_res_start + 2, value="Disciplina(s) que\nReprovou").font = FONT_SMALL_BOLD
    ws.cell(row=5, column=c_res_start + 2).alignment = ALIGN_CENTER
    aplicar_estilo_intervalo(ws, c_res_start, 5, c_res_start + 2, 6, font=FONT_SMALL_BOLD, fill=FILL_GRAY, border=THIN_BORDER, alignment=ALIGN_CENTER)

    ws.row_dimensions[4].height = 24
    ws.row_dimensions[5].height = 18
    ws.row_dimensions[6].height = 18

    # 4. Inserir dados dos alunos
    current_row = 7
    for aluno in alunos:
        ws.row_dimensions[current_row].height = 20
        # Nº de Ordem
        ws.cell(row=current_row, column=1, value=aluno.get('numero', '')).alignment = ALIGN_CENTER
        # Nº Candidato
        ws.cell(row=current_row, column=2, value=str(aluno.get('candidato', '') or aluno.get('matricula', ''))).alignment = ALIGN_CENTER
        # Nome Completo do Aluno (campo 'nome' ja contém o nome completo conforme cadastrado)
        ws.cell(row=current_row, column=3, value=obter_nome_completo_aluno(aluno)).alignment = ALIGN_LEFT
        # Género
        ws.cell(row=current_row, column=4, value=str(aluno.get('genero', ''))).alignment = ALIGN_CENTER
        # Turma
        ws.cell(row=current_row, column=5, value=str(aluno.get('turma', ''))).alignment = ALIGN_CENTER

        for c_idx in range(1, 6):
            ws.cell(row=current_row, column=c_idx).border = THIN_BORDER
            ws.cell(row=current_row, column=c_idx).font = FONT_REGULAR

        disc_map = aluno.get('disciplinas', {})
        c_cursor = 6

        # Disciplinas com exame: 4 colunas
        for d in disciplinas_com_exame:
            d_data = disc_map.get(d['id']) or {}
            v_freq = d_data.get('frequencia', '-')
            v_e1 = d_data.get('exame_1epoca', '')
            v_e2 = d_data.get('exame_2epoca', '')
            v_med = d_data.get('media', '-')

            # Frequência
            c_f = ws.cell(row=current_row, column=c_cursor, value=v_freq if v_freq is not None else '-')
            c_f.alignment = ALIGN_CENTER
            c_f.border = THIN_BORDER
            c_f.font = FONT_REGULAR

            # 1ª Época
            c_1 = ws.cell(row=current_row, column=c_cursor + 1, value=v_e1 if v_e1 is not None else '')
            c_1.alignment = ALIGN_CENTER
            c_1.border = THIN_BORDER
            c_1.font = FONT_REGULAR

            # 2ª Época
            c_2 = ws.cell(row=current_row, column=c_cursor + 2, value=v_e2 if v_e2 is not None else '')
            c_2.alignment = ALIGN_CENTER
            c_2.border = THIN_BORDER
            c_2.font = FONT_REGULAR

            # Média da Disciplina
            c_m = ws.cell(row=current_row, column=c_cursor + 3, value=v_med if v_med is not None else '-')
            c_m.alignment = ALIGN_CENTER
            c_m.border = THIN_BORDER
            if isinstance(v_med, (int, float)):
                c_m.font = FONT_GREEN if v_med >= 9.5 else FONT_RED
            else:
                c_m.font = FONT_REGULAR_BOLD

            c_cursor += 4

        # Disciplinas sem exame: 1 coluna
        for d in disciplinas_sem_exame:
            d_data = disc_map.get(d['id']) or {}
            v_freq = d_data.get('frequencia', '-')
            c_f = ws.cell(row=current_row, column=c_cursor, value=v_freq if v_freq is not None else '-')
            c_f.alignment = ALIGN_CENTER
            c_f.border = THIN_BORDER
            if isinstance(v_freq, (int, float)):
                c_f.font = FONT_GREEN if v_freq >= 9.5 else FONT_RED
            else:
                c_f.font = FONT_REGULAR
            c_cursor += 1

        # RESULTADO FINAL
        res_info = aluno.get('resultado_final', {})
        res_aprov = str(res_info.get('aprovado', '') or 'Pendente').strip()
        res_mf = res_info.get('mf', '-')
        res_disc_rep = str(res_info.get('disciplinas_reprovou', '---') or '---')

        # Aprovado(a): 'Aprovado' a preto e 'Reprovado' a vermelho (sem pintar fundo)
        c_ap = ws.cell(row=current_row, column=c_cursor, value=res_aprov)
        c_ap.alignment = ALIGN_CENTER
        c_ap.border = THIN_BORDER
        if 'Aprovad' in res_aprov:
            c_ap.font = FONT_REGULAR_BOLD
        else:
            c_ap.font = FONT_RED

        # MF
        c_mf = ws.cell(row=current_row, column=c_cursor + 1, value=res_mf if res_mf is not None else '-')
        c_mf.alignment = ALIGN_CENTER
        c_mf.border = THIN_BORDER
        c_mf.font = FONT_REGULAR_BOLD

        # Disciplinas que Reprovou
        c_rep = ws.cell(row=current_row, column=c_cursor + 2, value=res_disc_rep)
        c_rep.alignment = ALIGN_LEFT
        c_rep.border = THIN_BORDER
        c_rep.font = FONT_SMALL

        current_row += 1

    # 5. Rodapé Oficial com Resumo e Assinaturas
    current_row += 1
    estat = dados_pauta.get('estatisticas', {})
    tot = estat.get('total', len(alunos))
    aprov = estat.get('aprovados', 0)
    rep = estat.get('reprovados', 0)
    adm = estat.get('admitidos', 0)
    taxa = estat.get('taxa_aprovacao', 0.0)

    resumo_texto = f"Total Candidatos: {tot} | Aprovados: {aprov} | Reprovados: {rep} | Admitidos: {adm} | Taxa de Aprovação: {taxa}%"
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=total_cols)
    ws.cell(row=current_row, column=1, value=resumo_texto).font = FONT_REGULAR_BOLD
    ws.cell(row=current_row, column=1).alignment = ALIGN_LEFT
    current_row += 2

    # Assinaturas
    ws.cell(row=current_row, column=2, value="O Director de Turma:").font = FONT_REGULAR_BOLD
    ws.cell(row=current_row, column=total_cols - 3, value="O Director da Escola:").font = FONT_REGULAR_BOLD
    current_row += 2
    ws.cell(row=current_row, column=2, value="______________________________________").font = FONT_REGULAR
    ws.cell(row=current_row, column=total_cols - 3, value="______________________________________").font = FONT_REGULAR

    auto_ajustar_colunas(ws, padding=2)
    ws.column_dimensions['C'].width = 28  # Nome do Aluno

    buffer = io.BytesIO()
    salvar_xlsx_padronizado(wb, buffer)
    buffer.seek(0)
    return buffer.getvalue()

# ==================== 2. BOLETIM DE APROVEITAMENTO (VERTICAL) ====================

def gerar_boletim_xlsx(aluno, escola, ano_letivo, notas_disciplinas, orientacao='portrait') -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Boletim {aluno.matricula[:10]}"
    configurar_pagina_excel(ws, orientacao=orientacao)

    # Logótipo Oficial Escolhido pela Instituição
    inserir_logo_cabecalho_xlsx(ws, escola, cell='A1')

    # Cabeçalho Nacional
    ws.merge_cells('A1:F1')
    ws['A1'] = "REPÚBLICA DE MOÇAMBIQUE"
    ws['A1'].font = FONT_TITLE
    ws['A1'].alignment = ALIGN_CENTER

    prov = (getattr(escola, 'provincia', 'Inhambane') or 'Inhambane').upper()
    dist = (getattr(escola, 'distrito', 'Massinga') or 'Massinga').upper()
    ws.merge_cells('A2:F2')
    ws['A2'] = f"GOVERNO DA PROVÍNCIA DE {prov} — SDEJT DE {dist}"
    ws['A2'].font = FONT_SUBTITLE
    ws['A2'].alignment = ALIGN_CENTER

    ws.merge_cells('A3:F3')
    ws['A3'] = _obter_campo_escola(escola, 'nome', 'Escola Secundária').upper()
    ws['A3'].font = FONT_TITLE
    ws['A3'].alignment = ALIGN_CENTER

    ws.merge_cells('A4:F4')
    ws['A4'] = f"BOLETIM DE APROVEITAMENTO ESCOLAR — ANO LECTIVO {ano_letivo or 2026}"
    ws['A4'].font = FONT_SUBTITLE
    ws['A4'].alignment = ALIGN_CENTER

    # Identificação do Aluno
    turma_obj = getattr(aluno, 'turma', None)
    turma_nome = turma_obj.nome if turma_obj else '10ª Classe A'
    grau_nome = getattr(turma_obj, 'grau_ano', None) or getattr(aluno, 'classe', None) or '10ª Classe'
    classe_turma = f"{grau_nome} - {turma_nome}" if grau_nome not in turma_nome else turma_nome

    aluno_nome_str = obter_nome_completo_aluno(aluno).upper() if aluno else 'ALUNO'
    matricula_str = getattr(aluno, 'matricula', None) or getattr(aluno, 'codigo_matricula', '---')
    turno_str = getattr(turma_obj, 'turno', 'Manhã') if turma_obj else 'Manhã'

    ws['A6'] = "Nome do Aluno:"
    ws['A6'].font = FONT_REGULAR_BOLD
    ws.merge_cells('B6:D6')
    ws['B6'] = aluno_nome_str
    ws['B6'].font = FONT_REGULAR_BOLD

    ws['E6'] = "Classe/Turma:"
    ws['E6'].font = FONT_REGULAR_BOLD
    ws['F6'] = classe_turma
    ws['F6'].font = FONT_REGULAR

    ws['A7'] = "Nº Matrícula:"
    ws['A7'].font = FONT_REGULAR_BOLD
    ws['B7'] = matricula_str
    ws['B7'].font = FONT_REGULAR

    ws['E7'] = "Turno:"
    ws['E7'].font = FONT_REGULAR_BOLD
    ws['F7'] = turno_str
    ws['F7'].font = FONT_REGULAR

    for r in range(6, 8):
        for c in range(1, 7):
            ws.cell(row=r, column=c).border = THIN_BORDER

    # Cabeçalho das Disciplinas
    headers = ['Disciplina Curricular', '1º Trimestre', '2º Trimestre', '3º Trimestre', 'Média Final', 'Situação']
    ws.row_dimensions[9].height = 24
    for idx, h in enumerate(headers, start=1):
        c = ws.cell(row=9, column=idx, value=h)
        c.font = FONT_HEADER
        c.fill = FILL_NAVY
        c.alignment = ALIGN_CENTER
        c.border = THIN_BORDER

    # Linhas de notas
    cur_row = 10
    total_med = 0
    count_med = 0

    for disc in notas_disciplinas:
        ws.row_dimensions[cur_row].height = 20
        nome_d = disc.get('nome') or disc.get('disciplina') or 'Disciplina'
        t1 = disc.get('t1', disc.get('trimestre1', '-'))
        t2 = disc.get('t2', disc.get('trimestre2', '-'))
        t3 = disc.get('t3', disc.get('trimestre3', '-'))
        med = disc.get('media_anual', disc.get('mediaFinal', disc.get('media_final', '-')))
        sit = disc.get('situacao', disc.get('resultado', ''))

        if med not in (None, '-', '', '---'):
            try:
                m_val = float(med)
                total_med += m_val
                count_med += 1
                if not sit:
                    sit = 'Aprovado' if m_val >= 9.5 else 'Reprovado'
            except (ValueError, TypeError):
                pass

        c_nome = ws.cell(row=cur_row, column=1, value=str(nome_d))
        c_nome.font = FONT_REGULAR
        c_nome.alignment = ALIGN_LEFT
        c_nome.border = THIN_BORDER

        for col_idx, val in enumerate([t1, t2, t3], start=2):
            c = ws.cell(row=cur_row, column=col_idx, value=str(val if val is not None else '-'))
            c.font = FONT_REGULAR
            c.alignment = ALIGN_CENTER
            c.border = THIN_BORDER

        c_med = ws.cell(row=cur_row, column=5, value=str(med if med is not None else '-'))
        c_med.font = FONT_REGULAR_BOLD
        c_med.alignment = ALIGN_CENTER
        c_med.border = THIN_BORDER

        c_sit = ws.cell(row=cur_row, column=6, value=str(sit or '-'))
        c_sit.border = THIN_BORDER
        c_sit.alignment = ALIGN_CENTER
        if str(sit).startswith('Rep') or str(sit) == 'R':
            c_sit.font = FONT_RED
        else:
            c_sit.font = FONT_GREEN

        cur_row += 1

    # Decisão do Conselho
    media_global = round(total_med / count_med, 1) if count_med > 0 else '-'
    resultado = 'Transita' if (isinstance(media_global, (int, float)) and media_global >= 9.5) else ('Não Transita' if isinstance(media_global, (int, float)) else 'Em Avaliação')

    cur_row += 1
    ws.merge_cells(f'A{cur_row}:F{cur_row}')
    c_dec = ws[f'A{cur_row}']
    c_dec.value = f"Decisão do Conselho: Resultado Pedagógico: {resultado.upper()} | Média Global: {media_global} valores."
    c_dec.font = FONT_REGULAR_BOLD
    c_dec.alignment = ALIGN_LEFT

    # Assinaturas
    cur_row += 3
    ws.merge_cells(f'A{cur_row}:C{cur_row}')
    ws[f'A{cur_row}'] = "O Director de Turma: ____________________"
    ws[f'A{cur_row}'].font = FONT_REGULAR
    ws[f'A{cur_row}'].alignment = ALIGN_CENTER

    ws.merge_cells(f'D{cur_row}:F{cur_row}')
    ws[f'D{cur_row}'] = "O Director da Escola: ____________________"
    ws[f'D{cur_row}'].font = FONT_REGULAR
    ws[f'D{cur_row}'].alignment = ALIGN_CENTER

    auto_ajustar_colunas(ws, padding=3)
    ws.column_dimensions['A'].width = 28

    buffer = io.BytesIO()
    salvar_xlsx_padronizado(wb, buffer)
    buffer.seek(0)
    return buffer.getvalue()

# ==================== 3. DECLARAÇÃO COM NOTAS (VERTICAL) ====================

def gerar_declaracao_xlsx(aluno, escola, ano_letivo, notas_disciplinas, media_global=None, director_nome=None, orientacao='portrait') -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Declaração {aluno.matricula[:10]}"
    configurar_pagina_excel(ws, orientacao=orientacao)

    # Logótipo Oficial Escolhido pela Instituição
    inserir_logo_cabecalho_xlsx(ws, escola, cell='A1')

    ws.merge_cells('A1:B1')
    ws['A1'] = "REPÚBLICA DE MOÇAMBIQUE"
    ws['A1'].font = FONT_TITLE
    ws['A1'].alignment = ALIGN_CENTER

    prov = (getattr(escola, 'provincia', 'Inhambane') or 'Inhambane').upper()
    ws.merge_cells('A2:B2')
    esc_nome_decl = _obter_campo_escola(escola, 'nome', 'Escola Secundária').upper()
    ws['A2'] = f"GOVERNO DA PROVÍNCIA DE {prov} — {esc_nome_decl}"
    ws['A2'].font = FONT_SUBTITLE
    ws['A2'].alignment = ALIGN_CENTER

    ws.merge_cells('A4:B4')
    ws['A4'] = "DECLARAÇÃO OFICIAL COM NOTAS"
    ws['A4'].font = FONT_TITLE
    ws['A4'].alignment = ALIGN_CENTER

    aluno_nome = obter_nome_completo_aluno(aluno).upper()
    grau_classe = (aluno.turma.grau_ano if aluno.turma and aluno.turma.grau_ano else getattr(aluno, 'classe', None)) or '10ª Classe'

    ws['A6'] = "Nome Completo:"
    ws['A6'].font = FONT_REGULAR_BOLD
    ws['B6'] = aluno_nome
    ws['B6'].font = FONT_REGULAR_BOLD

    ws['A7'] = "Classe / Grau:"
    ws['A7'].font = FONT_REGULAR_BOLD
    ws['B7'] = grau_classe
    ws['B7'].font = FONT_REGULAR

    ws['A8'] = "Ano Lectivo:"
    ws['A8'].font = FONT_REGULAR_BOLD
    ws['B8'] = str(ano_letivo or 2026)
    ws['B8'].font = FONT_REGULAR

    # Tabela de notas
    ws['A10'] = "Disciplina Curricular"
    ws['A10'].font = FONT_HEADER
    ws['A10'].fill = FILL_NAVY
    ws['A10'].border = THIN_BORDER
    ws['A10'].alignment = ALIGN_LEFT

    ws['B10'] = "Classificação Final"
    ws['B10'].font = FONT_HEADER
    ws['B10'].fill = FILL_NAVY
    ws['B10'].border = THIN_BORDER
    ws['B10'].alignment = ALIGN_CENTER

    row_idx = 11
    for disc in notas_disciplinas:
        nome_d = disc.get('nome') or disc.get('disciplina') or 'Disciplina'
        nota = disc.get('media_anual', disc.get('mediaFinal', disc.get('media_final', disc.get('nota', '-'))))
        
        c1 = ws.cell(row=row_idx, column=1, value=str(nome_d))
        c1.font = FONT_REGULAR
        c1.border = THIN_BORDER
        c1.alignment = ALIGN_LEFT

        c2 = ws.cell(row=row_idx, column=2, value=str(nota if nota is not None else '-'))
        c2.font = FONT_REGULAR_BOLD
        c2.border = THIN_BORDER
        c2.alignment = ALIGN_CENTER

        row_idx += 1

    row_idx += 2
    dir_nome = director_nome or getattr(escola, 'director_nome', None) or 'Pero Chitofo Murrombe'
    ws.merge_cells(f'A{row_idx}:B{row_idx}')
    ws[f'A{row_idx}'] = f"O Director da Escola: {dir_nome}"
    ws[f'A{row_idx}'].font = FONT_REGULAR_BOLD
    ws[f'A{row_idx}'].alignment = ALIGN_CENTER

    auto_ajustar_colunas(ws, padding=4)
    ws.column_dimensions['A'].width = 36
    ws.column_dimensions['B'].width = 24

    buffer = io.BytesIO()
    salvar_xlsx_padronizado(wb, buffer)
    buffer.seek(0)
    return buffer.getvalue()

# ==================== 4. CERTIFICADO DE HABILITAÇÕES (VERTICAL) ====================

def gerar_certificado_xlsx(aluno, escola, ano_letivo, notas_disciplinas, media_global=None, codigo_autenticidade=None, orientacao='portrait') -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Certificado {aluno.matricula[:10]}"
    configurar_pagina_excel(ws, orientacao=orientacao)

    # Logótipo Oficial Escolhido pela Instituição
    inserir_logo_cabecalho_xlsx(ws, escola, cell='A1')

    ws.merge_cells('A1:B1')
    ws['A1'] = "REPÚBLICA DE MOÇAMBIQUE"
    ws['A1'].font = FONT_TITLE
    ws['A1'].alignment = ALIGN_CENTER

    ws.merge_cells('A2:B2')
    ws['A2'] = _obter_campo_escola(escola, 'nome', 'Escola Secundária').upper()
    ws['A2'].font = FONT_SUBTITLE
    ws['A2'].alignment = ALIGN_CENTER

    ws.merge_cells('A4:B4')
    ws['A4'] = "CERTIFICADO DE HABILITAÇÕES LITERÁRIAS"
    ws['A4'].font = FONT_TITLE
    ws['A4'].alignment = ALIGN_CENTER

    aluno_nome = obter_nome_completo_aluno(aluno).upper()
    grau_classe = (aluno.turma.grau_ano if aluno.turma and aluno.turma.grau_ano else getattr(aluno, 'classe', None)) or '12ª Classe'

    ws['A6'] = "Nome do Graduado:"
    ws['A6'].font = FONT_REGULAR_BOLD
    ws['B6'] = aluno_nome
    ws['B6'].font = FONT_REGULAR_BOLD

    ws['A7'] = "Grau / Nível Concluído:"
    ws['A7'].font = FONT_REGULAR_BOLD
    ws['B7'] = grau_classe
    ws['B7'].font = FONT_REGULAR

    cod_str = codigo_autenticidade or f"CERT-{aluno.matricula}-2026"
    ws['A8'] = "Código de Autenticidade:"
    ws['A8'].font = FONT_REGULAR_BOLD
    ws['B8'] = cod_str
    ws['B8'].font = FONT_REGULAR

    ws['A10'] = "Disciplina Concluída"
    ws['A10'].font = FONT_HEADER
    ws['A10'].fill = FILL_NAVY
    ws['A10'].border = THIN_BORDER

    ws['B10'] = "Classificação Final"
    ws['B10'].font = FONT_HEADER
    ws['B10'].fill = FILL_NAVY
    ws['B10'].border = THIN_BORDER
    ws['B10'].alignment = ALIGN_CENTER

    row_idx = 11
    for disc in notas_disciplinas:
        nome_d = disc.get('nome') or disc.get('disciplina') or 'Disciplina'
        nota = disc.get('media_anual', disc.get('mediaFinal', disc.get('media_final', disc.get('nota', '-'))))
        
        c1 = ws.cell(row=row_idx, column=1, value=str(nome_d))
        c1.font = FONT_REGULAR
        c1.border = THIN_BORDER

        c2 = ws.cell(row=row_idx, column=2, value=str(nota if nota is not None else '-'))
        c2.font = FONT_REGULAR_BOLD
        c2.border = THIN_BORDER
        c2.alignment = ALIGN_CENTER

        row_idx += 1

    auto_ajustar_colunas(ws, padding=4)
    ws.column_dimensions['A'].width = 36
    ws.column_dimensions['B'].width = 24

    buffer = io.BytesIO()
    salvar_xlsx_padronizado(wb, buffer)
    buffer.seek(0)
    return buffer.getvalue()

# ==================== 5. ACTA DE CONSELHO (HORIZONTAL) ====================

def gerar_acta_xlsx(turma, escola, periodo, ano_letivo, dados_alunos,
                    tabela_efectivo=None, tabela_aproveitamento=None,
                    disciplinas=None, trimestres_com_notas=None,
                    estatisticas=None, presidente=None, data_sessao=None,
                    orientacao='landscape', params_sessao=None, **kwargs) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Acta {turma.nome[:25]}"
    configurar_pagina_excel(ws, orientacao=orientacao, fit_to_height=1)
    ws.row_breaks = RowBreak()
    ws.col_breaks = ColBreak()

    # Obter ou calcular as tabelas se não foram passadas
    te = tabela_efectivo or {}
    ta = tabela_aproveitamento or {}
    tc = trimestres_com_notas or {'t1': True, 't2': False, 't3': False, 'fimAno': False}
    discs = disciplinas or []

    if not te or not ta:
        try:
            from apps.pautas.views import _calcular_tabelas_acta
            te, ta, discs, tc = _calcular_tabelas_acta(dados_alunos, discs)
        except Exception:
            pass

    # Extrair dados da Sessão e Montar Texto Protocolar Oficial
    ps = dict(params_sessao or {})
    p1 = ps.get('presidenteT1') or presidente or '____________________'
    p2 = ps.get('presidenteT2') or presidente or '____________________'
    p3 = ps.get('presidenteT3') or presidente or '____________________'

    dt1 = ps.get('dataT1') or data_sessao or f"___/___/{ano_letivo or 2026}"
    dt2 = ps.get('dataT2') or data_sessao or f"___/___/{ano_letivo or 2026}"
    dt3 = ps.get('dataT3') or data_sessao or f"___/___/{ano_letivo or 2026}"

    hIni1 = ps.get('horaInicioT1') or '____'
    mIni1 = ps.get('minInicioT1') or '____'
    hFim1 = ps.get('horaFimT1') or '____'
    mFim1 = ps.get('minFimT1') or '____'

    hIni2 = ps.get('horaInicioT2') or '____'
    mIni2 = ps.get('minInicioT2') or '____'
    hFim2 = ps.get('horaFimT2') or '____'
    mFim2 = ps.get('minFimT2') or '____'

    hIni3 = ps.get('horaInicioT3') or '____'
    mIni3 = ps.get('minInicioT3') or '____'
    hFim3 = ps.get('horaFimT3') or '____'
    mFim3 = ps.get('minFimT3') or '____'

    dt_turma = ps.get('directorTurma') or (turma.director_turma.nome if getattr(turma, 'director_turma', None) else '____________________')
    curso_txt = 'Nocturno' if (turma.turno or '').upper() == 'NOITE' else 'Diurno'

    texto_protocolar = (
        f"Sob presidência do senhor professor {p1} (Iº Trimestre); {p2} (IIº Trimestre); {p3} (IIIº Trimestre); "
        f"director/substituto do director de turma {dt_turma} da turma {turma.nome} do grupo da {turma.grau_ano}, "
        f"curso {curso_txt}, realizou-se o Conselho de Avaliação do Iº; IIº, IIIº, Trimestre no dia {dt1}; {dt2}; {dt3}, "
        f"com início às {hIni1} horas e {mIni1} minutos e com término às {hFim1} horas e {mFim1} minutos (Iº Trim); "
        f"{hIni2} horas e {mIni2} minutos e com término às {hFim2} horas e {mFim2} minutos (IIº Trim); "
        f"{hIni3} horas e {mIni3} minutos e com término às {hFim3} horas e {mFim3} minutos (IIIº Trim). "
        f"No final deste conselho colheram-se os resultados que abaixo vão discriminados de todos os membros que participaram:"
    )

    num_d = len(discs)
    max_cols_total = max(24, 1 + num_d * 3 if num_d > 0 else 24)

    # 1. Logótipo Oficial Escolhido pela Instituição & Cabeçalho MEC
    inserir_logo_cabecalho_xlsx(ws, escola, cell='A1')

    prov = (getattr(escola, 'provincia', 'Inhambane') or 'Inhambane').upper()
    dist = (getattr(escola, 'distrito', 'Massinga') or 'Massinga').upper()
    esc_nome = (getattr(escola, 'nome', '') or 'Escola Secundária').upper()

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_cols_total)
    ws.cell(row=1, column=1, value="REPÚBLICA DE MOÇAMBIQUE")
    aplicar_estilo_intervalo(ws, 1, 1, max_cols_total, 1, font=FONT_TITLE, border=None, alignment=ALIGN_CENTER)

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=max_cols_total)
    ws.cell(row=2, column=1, value="MINISTÉRIO DA EDUCAÇÃO E CULTURA")
    aplicar_estilo_intervalo(ws, 1, 2, max_cols_total, 2, font=FONT_SUBTITLE, border=None, alignment=ALIGN_CENTER)

    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=max_cols_total)
    ws.cell(row=3, column=1, value=f"DIRECÇÃO PROVINCIAL DA EDUCAÇÃO — {prov} | SERVIÇO DISTRITAL DE EDUCAÇÃO, JUVENTUDE E TECNOLOGIA DE {dist}")
    aplicar_estilo_intervalo(ws, 1, 3, max_cols_total, 3, font=FONT_REGULAR, border=None, alignment=ALIGN_CENTER)

    ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=max_cols_total)
    ws.cell(row=4, column=1, value=esc_nome)
    aplicar_estilo_intervalo(ws, 1, 4, max_cols_total, 4, font=FONT_TITLE, border=None, alignment=ALIGN_CENTER)

    ws.merge_cells(start_row=5, start_column=1, end_row=5, end_column=max_cols_total)
    ws.cell(row=5, column=1, value=f"ACTA DO CONSELHO DE AVALIAÇÃO DA TURMA {turma.nome} — {ano_letivo or 2026}")
    aplicar_estilo_intervalo(ws, 1, 5, max_cols_total, 5, font=FONT_TITLE, border=None, alignment=ALIGN_CENTER)

    ws.merge_cells(start_row=6, start_column=1, end_row=6, end_column=max_cols_total)
    ws.cell(row=6, column=1, value=f"SECTOR PEDAGÓGICO — {turma.grau_ano} | CURSO {curso_txt.upper()}")
    aplicar_estilo_intervalo(ws, 1, 6, max_cols_total, 6, font=FONT_REGULAR_BOLD, border=None, alignment=ALIGN_CENTER)

    # 2. Texto Protocolar Oficial em bloco de destaque
    ws.merge_cells(start_row=7, start_column=1, end_row=8, end_column=max_cols_total)
    ws.cell(row=7, column=1, value=texto_protocolar)
    aplicar_estilo_intervalo(ws, 1, 7, max_cols_total, 8, font=FONT_SMALL, fill=FILL_LIGHT, border=THIN_BORDER, alignment=ALIGN_LEFT)
    ws.row_dimensions[7].height = 25
    ws.row_dimensions[8].height = 25

    # 3. Título das Tabelas 1 e 2 Lado a Lado
    ws.merge_cells('A9:J9')
    ws['A9'] = "APROVEITAMENTO POR TRIMESTRES E FIM DO ANO (EFECTIVOS E MOVIMENTO)"
    aplicar_estilo_intervalo(ws, 1, 9, 10, 9, font=FONT_HEADER, fill=FILL_NAVY, border=THIN_BORDER, alignment=ALIGN_CENTER)

    ws.merge_cells('L9:X9')
    ws['L9'] = "APROVEITAMENTO PEDAGÓGICO POR FAIXAS E CRESCIMENTO"
    aplicar_estilo_intervalo(ws, 12, 9, 24, 9, font=FONT_HEADER, fill=FILL_NAVY, border=THIN_BORDER, alignment=ALIGN_CENTER)

    # Cabeçalhos Tabela 1 (Cols A:J, 1..10)
    ws.merge_cells('A10:A11')
    ws['A10'] = "CATEGORIA"
    ws.merge_cells('B10:B11')
    ws['B10'] = "GÉN"
    ws.merge_cells('C10:D10')
    ws['C10'] = "Iº TRIMESTRE"
    ws['C11'] = "Nº"
    ws['D11'] = "%"
    ws.merge_cells('E10:F10')
    ws['E10'] = "IIº TRIMESTRE"
    ws['E11'] = "Nº"
    ws['F11'] = "%"
    ws.merge_cells('G10:H10')
    ws['G10'] = "IIIº TRIMESTRE"
    ws['G11'] = "Nº"
    ws['H11'] = "%"
    ws.merge_cells('I10:J10')
    ws['I10'] = "FIM DO ANO"
    ws['I11'] = "Nº"
    ws['J11'] = "%"
    aplicar_estilo_intervalo(ws, 1, 10, 10, 11, font=FONT_HEADER_SM, fill=FILL_NAVY, border=THIN_BORDER, alignment=ALIGN_CENTER)

    # Cabeçalhos Tabela 2 (Cols L:X, 12..24)
    ws.merge_cells('L10:L11')
    ws['L10'] = "CLASSIFICAÇÃO"
    ws.merge_cells('M10:M11')
    ws['M10'] = "GÉN"
    ws.merge_cells('N10:O10')
    ws['N10'] = "Iº TRIMESTRE"
    ws['N11'] = "Nº"
    ws['O11'] = "%"
    ws.merge_cells('P10:Q10')
    ws['P10'] = "IIº TRIMESTRE"
    ws['P11'] = "Nº"
    ws['Q11'] = "%"
    ws.merge_cells('R10:S10')
    ws['R10'] = "IIIº TRIMESTRE"
    ws['R11'] = "Nº"
    ws['S11'] = "%"
    ws.merge_cells('T10:U10')
    ws['T10'] = "FIM DO ANO"
    ws['T11'] = "Nº"
    ws['U11'] = "%"
    ws.merge_cells('V10:X10')
    ws['V10'] = "CRESCIMENTO"
    ws['V11'] = "I-II"
    ws['W11'] = "II-III"
    ws['X11'] = "GLO"
    aplicar_estilo_intervalo(ws, 12, 10, 24, 11, font=FONT_HEADER_SM, fill=FILL_NAVY, border=THIN_BORDER, alignment=ALIGN_CENTER)

    # Dados Tabela 1
    cats_te = [
        ('Matrículas / Efectivo Inicial', 'inscritos'),
        ('Desistentes', 'desistentes'),
        ('Transferidos', 'transferidos'),
        ('Falecidos', 'falecidos'),
        ('Perdeu Ano por Faltas', 'perdeuFaltas'),
        ('Anulou Matrícula', 'anulouMatricula'),
        ('Alunos Avaliados', 'avaliados'),
    ]

    for cat_i, (label, chave) in enumerate(cats_te):
        r_start = 12 + cat_i * 3
        r_end = r_start + 2
        ws.merge_cells(start_row=r_start, start_column=1, end_row=r_end, end_column=1)
        ws.cell(row=r_start, column=1, value=label)
        aplicar_estilo_intervalo(ws, 1, r_start, 1, r_end, font=FONT_TINY_BOLD, border=THIN_BORDER, alignment=ALIGN_LEFT)

        is_inicial = (chave == 'inscritos')
        for gen_i, gen in enumerate(['H', 'M', 'HM']):
            row_idx = r_start + gen_i
            prop = 'h' if gen == 'H' else ('m' if gen == 'M' else 'hm')
            pct_prop = 'pctH' if gen == 'H' else ('pctM' if gen == 'M' else 'pct')

            tem_t1 = tc.get('t1') or is_inicial
            v_t1 = str(te.get('t1', {}).get(chave, {}).get(prop, '-')) if (tem_t1 and te.get('t1', {}).get(chave)) else ('-' if not is_inicial else str(te.get('t1', {}).get('inscritos', {}).get(prop, '-')))
            p_t1 = f"{te.get('t1', {}).get(chave, {}).get(pct_prop, 100 if is_inicial else 0)}%" if (tem_t1 and te.get('t1', {}).get(chave)) else ('100%' if is_inicial and v_t1 != '-' else '-')

            tem_t2 = tc.get('t2') or is_inicial
            v_t2 = str(te.get('t2', {}).get(chave, {}).get(prop, v_t1 if is_inicial else '-')) if (tem_t2 and (te.get('t2', {}).get(chave) or is_inicial)) else '-'
            p_t2 = f"{te.get('t2', {}).get(chave, {}).get(pct_prop, 100 if is_inicial else 0)}%" if (tem_t2 and (te.get('t2', {}).get(chave) or is_inicial)) else ('100%' if is_inicial and v_t2 != '-' else '-')

            tem_t3 = tc.get('t3') or is_inicial
            v_t3 = str(te.get('t3', {}).get(chave, {}).get(prop, v_t1 if is_inicial else '-')) if (tem_t3 and (te.get('t3', {}).get(chave) or is_inicial)) else '-'
            p_t3 = f"{te.get('t3', {}).get(chave, {}).get(pct_prop, 100 if is_inicial else 0)}%" if (tem_t3 and (te.get('t3', {}).get(chave) or is_inicial)) else ('100%' if is_inicial and v_t3 != '-' else '-')

            tem_fa = tc.get('fimAno') or is_inicial
            v_fa = str(te.get('fimAno', {}).get(chave, {}).get(prop, v_t1 if is_inicial else '-')) if (tem_fa and (te.get('fimAno', {}).get(chave) or is_inicial)) else '-'
            p_fa = f"{te.get('fimAno', {}).get(chave, {}).get(pct_prop, 100 if is_inicial else 0)}%" if (tem_fa and (te.get('fimAno', {}).get(chave) or is_inicial)) else ('100%' if is_inicial and v_fa != '-' else '-')

            vals_row = [gen, v_t1, p_t1, v_t2, p_t2, v_t3, p_t3, v_fa, p_fa]
            for col_offset, val in enumerate(vals_row, start=2):
                ws.cell(row=row_idx, column=col_offset, value=val)

            fill_r = FILL_ROW_HM if gen == 'HM' else None
            font_r = FONT_TINY_BOLD if gen == 'HM' else FONT_TINY
            aplicar_estilo_intervalo(ws, 2, row_idx, 10, row_idx, font=font_r, fill=fill_r, border=THIN_BORDER, alignment=ALIGN_CENTER)

    # Dados Tabela 2
    cats_ta = [
        ('Alunos Avaliados', 'avaliados', False),
        ('Não Satisfatório (0-9,4)', 'naoSatisfatorio', False),
        ('Satisfatório (9,5-13,4)', 'satisfatorio', False),
        ('Bom (13,5-16,4)', 'bom', False),
        ('Muito Bom (16,5-18,4)', 'muitoBom', False),
        ('Excelente (18,5-20)', 'excelente', False),
        ('TOTAL APROVADOS', 'aprovados', True),
        ('TOTAL REPROVADOS', 'reprovados', False),
    ]

    for cat_i, (label, chave, is_aprov) in enumerate(cats_ta):
        r_start = 12 + cat_i * 3
        r_end = r_start + 2
        ws.merge_cells(start_row=r_start, start_column=12, end_row=r_end, end_column=12)
        ws.cell(row=r_start, column=12, value=label)
        font_lbl = FONT_SUCCESS_SM if is_aprov else FONT_TINY_BOLD
        fill_lbl = FILL_SUCCESS if is_aprov else None
        aplicar_estilo_intervalo(ws, 12, r_start, 12, r_end, font=font_lbl, fill=fill_lbl, border=THIN_BORDER, alignment=ALIGN_LEFT)

        for gen_i, gen in enumerate(['H', 'M', 'HM']):
            row_idx = r_start + gen_i
            prop = 'h' if gen == 'H' else ('m' if gen == 'M' else 'hm')
            pct_prop = 'pctH' if gen == 'H' else ('pctM' if gen == 'M' else 'pct')

            tem_notas_t1 = tc.get('t1') and (ta.get('t1', {}).get('avaliados', {}).get('hm', 0) > 0)
            v_t1 = str(ta.get('t1', {}).get(chave, {}).get(prop, '-')) if (tem_notas_t1 and ta.get('t1', {}).get(chave)) else '-'
            p_t1 = f"{ta.get('t1', {}).get(chave, {}).get(pct_prop, 100 if chave == 'avaliados' else 0)}%" if (tem_notas_t1 and ta.get('t1', {}).get(chave)) else '-'

            tem_notas_t2 = tc.get('t2') and (ta.get('t2', {}).get('avaliados', {}).get('hm', 0) > 0)
            v_t2 = str(ta.get('t2', {}).get(chave, {}).get(prop, '-')) if (tem_notas_t2 and ta.get('t2', {}).get(chave)) else '-'
            p_t2 = f"{ta.get('t2', {}).get(chave, {}).get(pct_prop, 100 if chave == 'avaliados' else 0)}%" if (tem_notas_t2 and ta.get('t2', {}).get(chave)) else '-'

            tem_notas_t3 = tc.get('t3') and (ta.get('t3', {}).get('avaliados', {}).get('hm', 0) > 0)
            v_t3 = str(ta.get('t3', {}).get(chave, {}).get(prop, '-')) if (tem_notas_t3 and ta.get('t3', {}).get(chave)) else '-'
            p_t3 = f"{ta.get('t3', {}).get(chave, {}).get(pct_prop, 100 if chave == 'avaliados' else 0)}%" if (tem_notas_t3 and ta.get('t3', {}).get(chave)) else '-'

            tem_notas_fa = tc.get('fimAno') and (ta.get('fimAno', {}).get('avaliados', {}).get('hm', 0) > 0)
            v_fa = str(ta.get('fimAno', {}).get(chave, {}).get(prop, '-')) if (tem_notas_fa and ta.get('fimAno', {}).get(chave)) else '-'
            p_fa = f"{ta.get('fimAno', {}).get(chave, {}).get(pct_prop, 100 if chave == 'avaliados' else 0)}%" if (tem_notas_fa and ta.get('fimAno', {}).get(chave)) else '-'

            c1_2 = '-'
            if tem_notas_t1 and tem_notas_t2:
                try:
                    n1 = float(ta.get('t1', {}).get(chave, {}).get(pct_prop, 0))
                    n2 = float(ta.get('t2', {}).get(chave, {}).get(pct_prop, 0))
                    dif = round(n2 - n1, 1)
                    c1_2 = f"+{dif}%" if dif > 0 else f"{dif}%"
                except Exception:
                    pass

            c2_3 = '-'
            if tem_notas_t2 and tem_notas_t3:
                try:
                    n2 = float(ta.get('t2', {}).get(chave, {}).get(pct_prop, 0))
                    n3 = float(ta.get('t3', {}).get(chave, {}).get(pct_prop, 0))
                    dif = round(n3 - n2, 1)
                    c2_3 = f"+{dif}%" if dif > 0 else f"{dif}%"
                except Exception:
                    pass

            c_glo = '-'
            if tem_notas_t1 and tem_notas_fa:
                try:
                    n1 = float(ta.get('t1', {}).get(chave, {}).get(pct_prop, 0))
                    nfa = float(ta.get('fimAno', {}).get(chave, {}).get(pct_prop, 0))
                    dif = round(nfa - n1, 1)
                    c_glo = f"+{dif}%" if dif > 0 else f"{dif}%"
                except Exception:
                    pass

            vals_row = [gen, v_t1, p_t1, v_t2, p_t2, v_t3, p_t3, v_fa, p_fa, c1_2, c2_3, c_glo]
            for col_offset, val in enumerate(vals_row, start=13):
                ws.cell(row=row_idx, column=col_offset, value=val)

            fill_r = FILL_SUCCESS if is_aprov else (FILL_ROW_HM if gen == 'HM' else None)
            font_r = FONT_SUCCESS_SM if is_aprov else (FONT_TINY_BOLD if gen == 'HM' else FONT_TINY)
            aplicar_estilo_intervalo(ws, 13, row_idx, 24, row_idx, font=font_r, fill=fill_r, border=THIN_BORDER, alignment=ALIGN_CENTER)

    # 4. TABELA 3: Aproveitamento Pedagógico por Disciplina
    current_row = 37
    if discs:
        current_row += 1
        t3_end_col = 1 + num_d * 3
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=t3_end_col)
        ws.cell(row=current_row, column=1, value="ÁREA CURRICULAR & ESTATÍSTICA PEDAGÓGICA POR DISCIPLINA")
        aplicar_estilo_intervalo(ws, 1, current_row, t3_end_col, current_row, font=FONT_HEADER, fill=FILL_NAVY, border=THIN_BORDER, alignment=ALIGN_CENTER)

        current_row += 1
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row + 1, end_column=1)
        ws.cell(row=current_row, column=1, value="CLASSIFICAÇÃO")
        aplicar_estilo_intervalo(ws, 1, current_row, 1, current_row + 1, font=FONT_HEADER_SM, fill=FILL_NAVY, border=THIN_BORDER, alignment=ALIGN_CENTER)

        for d_i, d in enumerate(discs):
            c_start = 2 + d_i * 3
            c_end = c_start + 2
            ws.merge_cells(start_row=current_row, start_column=c_start, end_row=current_row, end_column=c_end)
            ws.cell(row=current_row, column=c_start, value=d.get('nome', '').upper())
            aplicar_estilo_intervalo(ws, c_start, current_row, c_end, current_row, font=FONT_HEADER_SM, fill=FILL_NAVY, border=THIN_BORDER, alignment=ALIGN_CENTER)

            ws.cell(row=current_row + 1, column=c_start, value='H')
            ws.cell(row=current_row + 1, column=c_start + 1, value='M')
            ws.cell(row=current_row + 1, column=c_start + 2, value='HM')
            aplicar_estilo_intervalo(ws, c_start, current_row + 1, c_end, current_row + 1, font=FONT_HEADER_SM, fill=FILL_NAVY, border=THIN_BORDER, alignment=ALIGN_CENTER)

        current_row += 2
        faixas_disc = [
            ('[0 - 9,4 valores]', 'faixa0_9', 'regular'),
            ('[9,5 - 13,4 valores]', 'faixa10_13', 'regular'),
            ('[13,5 - 16,4 valores]', 'faixa14_16', 'regular'),
            ('[16,5 - 18,4 valores]', 'faixa17_18', 'regular'),
            ('[18,5 - 20 valores]', 'faixa19_20', 'regular'),
            ('Alunos Avaliados', 'avaliados', 'neutral'),
            ('Notas Positivas', 'positivas', 'success'),
            ('% Positivas', 'positivas_pct', 'success'),
            ('Assinatura do Docente', 'assinatura', 'docente'),
        ]

        for f_label, f_key, f_type in faixas_disc:
            ws.cell(row=current_row, column=1, value=f_label)

            font_row = FONT_TINY
            fill_row = None
            if f_type == 'neutral':
                font_row = FONT_TINY_BOLD
                fill_row = FILL_ROW_HM
            elif f_type == 'success':
                font_row = FONT_SUCCESS_SM
                fill_row = FILL_SUCCESS

            aplicar_estilo_intervalo(ws, 1, current_row, 1, current_row, font=font_row, fill=fill_row, border=THIN_BORDER, alignment=ALIGN_LEFT)

            for d_i, d in enumerate(discs):
                c_start = 2 + d_i * 3
                c_end = c_start + 2

                if f_type == 'docente':
                    ws.merge_cells(start_row=current_row, start_column=c_start, end_row=current_row, end_column=c_end)
                    ws.cell(row=current_row, column=c_start, value="_________________")
                    aplicar_estilo_intervalo(ws, c_start, current_row, c_end, current_row, font=FONT_MUTED_ITALIC, fill=None, border=THIN_BORDER, alignment=ALIGN_CENTER)
                elif f_key == 'positivas_pct':
                    pos_h = d.get('positivas', {}).get('pctH', 0)
                    pos_m = d.get('positivas', {}).get('pctM', 0)
                    pos_hm = d.get('positivas', {}).get('pct', 0)
                    ws.cell(row=current_row, column=c_start, value=f"{pos_h}%")
                    ws.cell(row=current_row, column=c_start + 1, value=f"{pos_m}%")
                    ws.cell(row=current_row, column=c_start + 2, value=f"{pos_hm}%")
                    aplicar_estilo_intervalo(ws, c_start, current_row, c_end, current_row, font=font_row, fill=fill_row, border=THIN_BORDER, alignment=ALIGN_CENTER)
                else:
                    bloco = d.get(f_key, {})
                    ws.cell(row=current_row, column=c_start, value=bloco.get('h', 0))
                    ws.cell(row=current_row, column=c_start + 1, value=bloco.get('m', 0))
                    ws.cell(row=current_row, column=c_start + 2, value=bloco.get('hm', 0))
                    aplicar_estilo_intervalo(ws, c_start, current_row, c_end, current_row, font=font_row, fill=fill_row, border=THIN_BORDER, alignment=ALIGN_CENTER)

            current_row += 1

    # 5. TABELA 4: Relação Nominal dos Alunos e Deliberação do Conselho
    current_row += 2
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=10)
    ws.cell(row=current_row, column=1, value="RELAÇÃO NOMINAL DOS ALUNOS E DELIBERAÇÃO DO CONSELHO")
    aplicar_estilo_intervalo(ws, 1, current_row, 10, current_row, font=FONT_HEADER, fill=FILL_NAVY, border=THIN_BORDER, alignment=ALIGN_CENTER)

    current_row += 1
    ws.cell(row=current_row, column=1, value="Nº")
    ws.merge_cells(start_row=current_row, start_column=2, end_row=current_row, end_column=6)
    ws.cell(row=current_row, column=2, value="Nome Completo do Aluno")
    ws.cell(row=current_row, column=7, value="Média Final")
    ws.cell(row=current_row, column=8, value="Comportamento")
    ws.merge_cells(start_row=current_row, start_column=9, end_row=current_row, end_column=10)
    ws.cell(row=current_row, column=9, value="Decisão do Conselho")
    aplicar_estilo_intervalo(ws, 1, current_row, 10, current_row, font=FONT_HEADER_SM, fill=FILL_NAVY, border=THIN_BORDER, alignment=ALIGN_CENTER)

    current_row += 1
    for idx, aluno in enumerate(dados_alunos, start=1):
        num_aluno = aluno.get('numero') or idx
        nome_aluno = obter_nome_completo_aluno(aluno)
        med_aluno = str(aluno.get('media_geral', '-'))
        comp_aluno = str(aluno.get('comportamento', 'B') or 'B')
        res_val = str(aluno.get('resultado', 'Aprovado')).strip()

        ws.cell(row=current_row, column=1, value=num_aluno)
        ws.merge_cells(start_row=current_row, start_column=2, end_row=current_row, end_column=6)
        ws.cell(row=current_row, column=2, value=nome_aluno)
        ws.cell(row=current_row, column=7, value=med_aluno)
        ws.cell(row=current_row, column=8, value=comp_aluno)
        ws.merge_cells(start_row=current_row, start_column=9, end_row=current_row, end_column=10)
        ws.cell(row=current_row, column=9, value=res_val)

        aplicar_estilo_intervalo(ws, 1, current_row, 1, current_row, font=FONT_TINY, border=THIN_BORDER, alignment=ALIGN_CENTER)
        aplicar_estilo_intervalo(ws, 2, current_row, 6, current_row, font=FONT_TINY, border=THIN_BORDER, alignment=ALIGN_LEFT)
        aplicar_estilo_intervalo(ws, 7, current_row, 7, current_row, font=FONT_TINY_BOLD, border=THIN_BORDER, alignment=ALIGN_CENTER)
        aplicar_estilo_intervalo(ws, 8, current_row, 8, current_row, font=FONT_TINY, border=THIN_BORDER, alignment=ALIGN_CENTER)

        font_res = FONT_DANGER_SM if res_val in ('Reprovado', 'R', 'Excluído') else FONT_SUCCESS_SM
        aplicar_estilo_intervalo(ws, 9, current_row, 10, current_row, font=font_res, border=THIN_BORDER, alignment=ALIGN_CENTER)

        current_row += 1

    # 6. Assinaturas Oficiais dos Membros do Conselho
    current_row += 2
    pres_final = p1 if p1 != '____________________' else (presidente or 'Presidente da Sessão')
    dir_turma_final = dt_turma if dt_turma != '____________________' else 'Director de Turma'

    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=3)
    ws.cell(row=current_row, column=1, value="O Presidente do Conselho")

    ws.merge_cells(start_row=current_row, start_column=4, end_row=current_row, end_column=7)
    ws.cell(row=current_row, column=4, value="O Secretário do Conselho")

    ws.merge_cells(start_row=current_row, start_column=8, end_row=current_row, end_column=10)
    ws.cell(row=current_row, column=8, value="O Director de Turma")
    aplicar_estilo_intervalo(ws, 1, current_row, 10, current_row, font=FONT_SMALL_BOLD, border=None, alignment=ALIGN_CENTER)

    current_row += 2
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=3)
    ws.cell(row=current_row, column=1, value="__________________________________")

    ws.merge_cells(start_row=current_row, start_column=4, end_row=current_row, end_column=7)
    ws.cell(row=current_row, column=4, value="__________________________________")

    ws.merge_cells(start_row=current_row, start_column=8, end_row=current_row, end_column=10)
    ws.cell(row=current_row, column=8, value="__________________________________")
    aplicar_estilo_intervalo(ws, 1, current_row, 10, current_row, font=FONT_REGULAR, border=None, alignment=ALIGN_CENTER)

    current_row += 1
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=3)
    ws.cell(row=current_row, column=1, value=pres_final)

    ws.merge_cells(start_row=current_row, start_column=4, end_row=current_row, end_column=7)
    ws.cell(row=current_row, column=4, value="Secretário(a) Designado(a)")

    ws.merge_cells(start_row=current_row, start_column=8, end_row=current_row, end_column=10)
    ws.cell(row=current_row, column=8, value=dir_turma_final)
    aplicar_estilo_intervalo(ws, 1, current_row, 10, current_row, font=FONT_SMALL_BOLD, border=None, alignment=ALIGN_CENTER)

    # Rodapé informático
    current_row += 2
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=max_cols_total)
    ws.cell(row=current_row, column=1, value=f"Documento processado informaticamente pelo SIGE em {datetime.date.today().strftime('%d/%m/%Y')} — Sistema Integrado de Gestão Escolar")
    aplicar_estilo_intervalo(ws, 1, current_row, max_cols_total, current_row, font=FONT_SMALL, border=None, alignment=ALIGN_RIGHT)

    # Larguras das colunas
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 6
    for c_idx in range(3, 11):
        col_letter = get_column_letter(c_idx)
        ws.column_dimensions[col_letter].width = 7.5
    ws.column_dimensions['K'].width = 2.5
    ws.column_dimensions['L'].width = 25
    ws.column_dimensions['M'].width = 6
    for c_idx in range(14, 22):
        col_letter = get_column_letter(c_idx)
        ws.column_dimensions[col_letter].width = 7.5
    ws.column_dimensions['V'].width = 8.5
    ws.column_dimensions['W'].width = 8.5
    ws.column_dimensions['X'].width = 8.5

    if num_d > 0:
        for c_idx in range(25, 2 + num_d * 3):
            col_letter = get_column_letter(c_idx)
            ws.column_dimensions[col_letter].width = 7.5

    # Garantir eliminação absoluta de quebras de página para impressão contínua
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1
    ws.row_breaks = RowBreak()
    ws.col_breaks = ColBreak()

    buffer = io.BytesIO()
    salvar_xlsx_padronizado(wb, buffer)
    buffer.seek(0)
    return buffer.getvalue()

# ==================== 6. EMISSÃO EM LOTE (XLSX) ====================

def _adicionar_aba_aluno_lote(wb, idx, doc_item, tipo_documento, turma, escola, orientacao='portrait'):
    aluno_info = doc_item.get('aluno', {})
    nome = obter_nome_completo_aluno(aluno_info) or f"Aluno_{idx}"
    mat = aluno_info.get('matricula') or '-'
    
    safe_name = re.sub(r'[\:\/\?\*\[\]]', '', str(nome))[:20]
    tab_title = f"{idx:02d} - {safe_name}".strip()[:31]
    
    existing_titles = [s.title for s in wb.worksheets]
    if tab_title in existing_titles:
        tab_title = f"{tab_title[:27]}_{idx}"

    ws = wb.create_sheet(title=tab_title)
    configurar_pagina_excel(ws, orientacao=orientacao)

    tipo = tipo_documento.upper()
    ano_val = getattr(turma, 'ano_letivo', 2026) or 2026
    prov = (getattr(escola, 'provincia', 'Inhambane') or 'Inhambane').upper()
    dist = (getattr(escola, 'distrito', 'Massinga') or 'Massinga').upper()

    ws.merge_cells('A1:F1')
    ws['A1'] = "REPÚBLICA DE MOÇAMBIQUE"
    ws['A1'].font = FONT_TITLE
    ws['A1'].alignment = ALIGN_CENTER

    ws.merge_cells('A2:F2')
    ws['A2'] = f"GOVERNO DA PROVÍNCIA DE {prov} — SDEJT DE {dist}"
    ws['A2'].font = FONT_SUBTITLE
    ws['A2'].alignment = ALIGN_CENTER

    ws.merge_cells('A3:F3')
    ws['A3'] = _obter_campo_escola(escola, 'nome', 'Escola Secundária').upper()
    ws['A3'].font = FONT_TITLE
    ws['A3'].alignment = ALIGN_CENTER

    tipo_titulos = {
        'BOLETIM': f"BOLETIM DE APROVEITAMENTO ESCOLAR — ANO LECTIVO {ano_val}",
        'DECLARACAO': f"DECLARAÇÃO COM NOTAS — ANO LECTIVO {ano_val}",
        'CERTIFICADO': f"CERTIFICADO DE HABILITAÇÕES LITERÁRIAS — {ano_val}",
        'FICHA': "FICHA BIOGRÁFICA DO ALUNO",
        'RECIBO': "RECIBO DE PAGAMENTO OFICIAL"
    }
    ws.merge_cells('A4:F4')
    ws['A4'] = tipo_titulos.get(tipo, f"DOCUMENTO ESCOLAR ({tipo}) — {ano_val}")
    ws['A4'].font = FONT_SUBTITLE
    ws['A4'].alignment = ALIGN_CENTER

    ws['A6'] = "Nome do Aluno:"
    ws['A6'].font = FONT_REGULAR_BOLD
    ws.merge_cells('B6:D6')
    ws['B6'] = str(nome).upper()
    ws['B6'].font = FONT_REGULAR_BOLD

    ws['E6'] = "Classe/Turma:"
    ws['E6'].font = FONT_REGULAR_BOLD
    ws['F6'] = f"{getattr(turma, 'grau_ano', '')} - {turma.nome}"
    ws['F6'].font = FONT_REGULAR

    ws['A7'] = "Nº Matrícula:"
    ws['A7'].font = FONT_REGULAR_BOLD
    ws['B7'] = str(mat)
    ws['B7'].font = FONT_REGULAR

    ws['E7'] = "Turno / Ano:"
    ws['E7'].font = FONT_REGULAR_BOLD
    ws['F7'] = f"{getattr(turma, 'turno', 'Diurno')} | {ano_val}"
    ws['F7'].font = FONT_REGULAR

    for r in range(6, 8):
        for c in range(1, 7):
            ws.cell(row=r, column=c).border = THIN_BORDER

    if tipo in ('BOLETIM', 'DECLARACAO', 'CERTIFICADO'):
        headers = ['Disciplina Curricular', '1º Trimestre', '2º Trimestre', '3º Trimestre', 'Média Final', 'Situação']
        for c_idx, h in enumerate(headers, start=1):
            cell = ws.cell(row=9, column=c_idx, value=h)
            cell.font = FONT_HEADER
            cell.fill = FILL_NAVY
            cell.alignment = ALIGN_CENTER
            cell.border = THIN_BORDER

        discs = doc_item.get('disciplinas') or doc_item.get('_dados_disc') or []
        cur_r = 10
        for d in discs:
            d_nome = d.get('nome') or d.get('disciplina') or 'Disciplina'
            t1 = d.get('t1', d.get('trimestre1', '-'))
            t2 = d.get('t2', d.get('trimestre2', '-'))
            t3 = d.get('t3', d.get('trimestre3', '-'))
            mf = d.get('media_anual', d.get('mediaFinal', d.get('media_final', d.get('nota', '-'))))
            sit_d = 'Aprovado' if str(mf).replace(',', '.').replace('-', '0') != '-' and float(str(mf).replace(',', '.').replace('-', '0') or 0) >= 9.5 else 'Pendente'

            ws.cell(row=cur_r, column=1, value=str(d_nome)).alignment = ALIGN_LEFT
            ws.cell(row=cur_r, column=2, value=str(t1 if t1 is not None else '-')).alignment = ALIGN_CENTER
            ws.cell(row=cur_r, column=3, value=str(t2 if t2 is not None else '-')).alignment = ALIGN_CENTER
            ws.cell(row=cur_r, column=4, value=str(t3 if t3 is not None else '-')).alignment = ALIGN_CENTER
            ws.cell(row=cur_r, column=5, value=str(mf if mf is not None else '-')).alignment = ALIGN_CENTER
            ws.cell(row=cur_r, column=6, value=sit_d).alignment = ALIGN_CENTER

            for col_i in range(1, 7):
                c = ws.cell(row=cur_r, column=col_i)
                c.font = FONT_REGULAR
                c.border = THIN_BORDER
            cur_r += 1

        ws.cell(row=cur_r, column=1, value="MÉDIA GLOBAL & RESULTADO").font = FONT_HEADER
        ws.cell(row=cur_r, column=1).fill = FILL_LIGHT_GRAY
        med_raw = doc_item.get('mediaGlobal') or doc_item.get('mediaGeral') or '-'
        sit_raw = doc_item.get('situacaoGlobal') or doc_item.get('resultadoFinal') or 'Aprovado'
        med_glob = str(med_raw.get('mediaGeral') or med_raw.get('mediaGlobal') or '-') if isinstance(med_raw, dict) else str(med_raw)
        sit_glob = str(sit_raw.get('resultado') or sit_raw.get('situacao') or sit_raw.get('motivo') or 'Pendente') if isinstance(sit_raw, dict) else str(sit_raw)
        ws.cell(row=cur_r, column=5, value=str(med_glob)).font = FONT_HEADER
        ws.cell(row=cur_r, column=5).alignment = ALIGN_CENTER
        ws.cell(row=cur_r, column=6, value=str(sit_glob)).font = FONT_HEADER
        ws.cell(row=cur_r, column=6).alignment = ALIGN_CENTER
        for col_i in range(1, 7):
            ws.cell(row=cur_r, column=col_i).border = THIN_BORDER

        ass_r = cur_r + 3
        ws.cell(row=ass_r, column=1, value="O Director de Turma: __________________________________").font = FONT_REGULAR_BOLD
        ws.cell(row=ass_r, column=4, value="A Direcção da Escola: __________________________________").font = FONT_REGULAR_BOLD

    elif tipo == 'FICHA':
        campos = [
            ('Nome Completo:', str(nome).upper()),
            ('Número de Matrícula:', str(mat)),
            ('Data de Nascimento:', str(aluno_info.get('dataNascimento', '---'))),
            ('Filiação (Pai):', str(aluno_info.get('pai', '---'))),
            ('Filiação (Mãe):', str(aluno_info.get('mae', '---'))),
            ('Classe & Turma:', f"{getattr(turma, 'grau_ano', '')} - {turma.nome}"),
            ('Ano Lectivo:', str(ano_val)),
            ('Situação Escolar:', 'Matriculado e Regular')
        ]
        cur_r = 9
        for lbl, v in campos:
            ws.cell(row=cur_r, column=1, value=lbl).font = FONT_REGULAR_BOLD
            ws.cell(row=cur_r, column=1).fill = FILL_LIGHT_GRAY
            ws.cell(row=cur_r, column=1).border = THIN_BORDER
            ws.merge_cells(start_row=cur_r, start_column=2, end_row=cur_r, end_column=6)
            ws.cell(row=cur_r, column=2, value=v).font = FONT_REGULAR
            for col_i in range(1, 7):
                ws.cell(row=cur_r, column=col_i).border = THIN_BORDER
            cur_r += 1

        ass_r = cur_r + 2
        ws.cell(row=ass_r, column=1, value="A Secretaria Escolar: __________________________________").font = FONT_REGULAR_BOLD
        ws.cell(row=ass_r, column=4, value="O Encarregado: __________________________________").font = FONT_REGULAR_BOLD

    elif tipo == 'RECIBO':
        campos = [
            ('Nome do Aluno:', str(nome).upper()),
            ('Número de Matrícula:', str(mat)),
            ('Descrição:', 'Propina Escolar / Mensalidade Regular'),
            ('Mês de Referência:', 'Fevereiro / 2026'),
            ('Valor Cobrado:', '1.500,00 MT'),
            ('Valor Liquidado:', '1.500,00 MT'),
            ('Estado do Pagamento:', 'PAGO / LIQUIDADO COM SUCESSO'),
            ('Método de Pagamento:', 'MPESA / BANCÁRIO'),
            ('Data de Liquidação:', datetime.date.today().strftime('%d/%m/%Y'))
        ]
        cur_r = 9
        for lbl, v in campos:
            ws.cell(row=cur_r, column=1, value=lbl).font = FONT_REGULAR_BOLD
            ws.cell(row=cur_r, column=1).fill = FILL_LIGHT_GRAY
            ws.cell(row=cur_r, column=1).border = THIN_BORDER
            ws.merge_cells(start_row=cur_r, start_column=2, end_row=cur_r, end_column=6)
            c2 = ws.cell(row=cur_r, column=2, value=v)
            c2.font = FONT_REGULAR_BOLD if 'PAGO' in v else FONT_REGULAR
            for col_i in range(1, 7):
                ws.cell(row=cur_r, column=col_i).border = THIN_BORDER
            cur_r += 1

        ass_r = cur_r + 2
        ws.cell(row=ass_r, column=1, value="A Secretaria Financeira: __________________________________").font = FONT_REGULAR_BOLD

    auto_ajustar_colunas(ws, padding=3)
    ws.column_dimensions['A'].width = 28
    ws.column_dimensions['B'].width = 18


def gerar_lote_xlsx(turma, escola, tipo_documento, alunos_documentos, orientacao='portrait') -> bytes:
    wb = openpyxl.Workbook()
    # 1. Página 1: Mapa Oficial de Emissão em Lote
    ws = wb.active
    ws.title = "Mapa de Emissão"
    configurar_pagina_excel(ws, orientacao=orientacao)

    # Logótipo Oficial Escolhido pela Instituição
    inserir_logo_cabecalho_xlsx(ws, escola, cell='A1')

    ws.merge_cells('A1:F1')
    esc_nome_lote = _obter_campo_escola(escola, 'nome', 'Escola Secundária').upper()
    ws['A1'] = f"{esc_nome_lote} — MAPA OFICIAL DE EMISSÃO EM LOTE ({tipo_documento.upper()}S)"
    ws['A1'].font = FONT_TITLE
    ws['A1'].alignment = ALIGN_CENTER

    ws.merge_cells('A2:F2')
    ws['A2'] = f"Turma: {turma.nome} ({turma.grau_ano}) | Total de Alunos: {len(alunos_documentos)}"
    ws['A2'].font = FONT_SUBTITLE
    ws['A2'].alignment = ALIGN_CENTER

    headers = ['Nº', 'Nome Completo', 'Matrícula', 'Média Global', 'Resultado Pedagógico', 'Data de Emissão']
    for idx, h in enumerate(headers, start=1):
        c = ws.cell(row=4, column=idx, value=h)
        c.font = FONT_HEADER
        c.fill = FILL_NAVY
        c.alignment = ALIGN_CENTER
        c.border = THIN_BORDER

    cur_row = 5
    for idx, doc in enumerate(alunos_documentos, start=1):
        aluno_info = doc.get('aluno', {})
        nome = obter_nome_completo_aluno(aluno_info) or 'Aluno'
        mat = aluno_info.get('matricula') or '-'
        med_raw = doc.get('mediaGlobal') or doc.get('media_global') or '-'
        res_raw = doc.get('situacaoGlobal') or doc.get('resultadoFinal') or doc.get('avaliacao') or 'Aprovado'
        med = str(med_raw.get('mediaGeral') or med_raw.get('mediaGlobal') or '-') if isinstance(med_raw, dict) else str(med_raw)
        res = str(res_raw.get('resultado') or res_raw.get('situacao') or res_raw.get('motivo') or 'Pendente') if isinstance(res_raw, dict) else str(res_raw)

        ws.cell(row=cur_row, column=1, value=idx).alignment = ALIGN_CENTER
        ws.cell(row=cur_row, column=2, value=nome).alignment = ALIGN_LEFT
        ws.cell(row=cur_row, column=3, value=mat).alignment = ALIGN_CENTER
        ws.cell(row=cur_row, column=4, value=str(med)).alignment = ALIGN_CENTER
        ws.cell(row=cur_row, column=5, value=str(res)).alignment = ALIGN_CENTER
        ws.cell(row=cur_row, column=6, value=datetime.date.today().strftime('%d/%m/%Y')).alignment = ALIGN_CENTER

        for col_i in range(1, 7):
            c = ws.cell(row=cur_row, column=col_i)
            c.font = FONT_REGULAR
            c.border = THIN_BORDER

        cur_row += 1

    ass_row = cur_row + 2
    ws.cell(row=ass_row, column=2, value="O Director de Turma: _____________________________").font = FONT_REGULAR_BOLD
    ws.cell(row=ass_row, column=5, value="A Direcção da Escola: _____________________________").font = FONT_REGULAR_BOLD

    auto_ajustar_colunas(ws, padding=3)
    ws.column_dimensions['B'].width = 34

    # 2. Abas 2..N: Documentos Individuais de Cada Aluno
    for idx, doc_item in enumerate(alunos_documentos, start=1):
        _adicionar_aba_aluno_lote(wb, idx, doc_item, tipo_documento, turma, escola, orientacao=orientacao)

    buffer = io.BytesIO()
    salvar_xlsx_padronizado(wb, buffer)
    buffer.seek(0)
    return buffer.getvalue()


# ==================== 10. ESTATÍSTICAS GERAIS DO APROVEITAMENTO PEDAGÓGICO ====================

def gerar_estatisticas_gerais_xlsx(escola, ano_letivo, periodo, stats_data, orientacao='landscape') -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Estatísticas {ano_letivo}"
    configurar_pagina_excel(ws, orientacao=orientacao)

    nome_escola = _obter_campo_escola(escola, 'nome', 'Escola Secundária')
    periodo_rotulo = "MÉDIA ANUAL / MFD" if str(periodo).upper() in ('GLOBAL', 'ANUAL', 'MFD') else str(periodo)

    # Logótipo Oficial Escolhido pela Instituição
    inserir_logo_cabecalho_xlsx(ws, escola, cell='A1')

    # 1. Cabeçalho Oficial
    ws.merge_cells('A1:J1')
    ws['A1'] = "REPÚBLICA DE MOÇAMBIQUE — MINISTÉRIO DA EDUCAÇÃO E CULTURA"
    ws['A1'].font = FONT_SUBTITLE
    ws['A1'].alignment = ALIGN_CENTER
    ws.row_dimensions[1].height = 22

    ws.merge_cells('A2:J2')
    ws['A2'] = f"{nome_escola.upper()} — MAPA CONSOLIDADO DO RENDIMENTO E APROVEITAMENTO PEDAGÓGICO"
    ws['A2'].font = FONT_TITLE
    ws['A2'].alignment = ALIGN_CENTER
    ws.row_dimensions[2].height = 25

    ws.merge_cells('A3:J3')
    ws['A3'] = f"Ano Lectivo: {ano_letivo} | Período: {periodo_rotulo} | Data de Emissão: {datetime.date.today().strftime('%d/%m/%Y')}"
    ws['A3'].font = FONT_REGULAR
    ws['A3'].alignment = ALIGN_CENTER
    ws.row_dimensions[3].height = 20

    row = 5
    ge = stats_data.get('geralEscola', {})
    por_classe = stats_data.get('porClasse', [])
    por_turma = stats_data.get('porTurma', [])
    por_disc = stats_data.get('porDisciplina', [])

    # ----- SECÇÃO 1: RESUMO GLOBAL DA ESCOLA -----
    ws.cell(row=row, column=1, value="1. RESUMO GLOBAL DA ESCOLA").font = FONT_REGULAR_BOLD
    row += 1

    headers_ge_top = [
        ('A', 'C', 'Inscritos / Matriculados'),
        ('D', 'F', 'Efectivo Avaliado'),
        ('G', 'J', 'Aproveitamento Positivo (Aprovados)'),
        ('K', 'N', 'Não Aproveitamento (Reprovados)')
    ]
    # Usaremos colunas de 1 a 10
    ge_headers = [
        'Inscritos (HM)', 'Inscritos (M)', 'Inscritos Total',
        'Avaliados (HM)', 'Avaliados (M)', 'Avaliados Total',
        'Aprovados Total', '% Aproveitamento',
        'Reprovados Total', '% Reprovação'
    ]
    for col_idx, h in enumerate(ge_headers, start=1):
        c = ws.cell(row=row, column=col_idx, value=h)
        c.font = FONT_HEADER
        c.fill = FILL_NAVY
        c.alignment = ALIGN_CENTER
        c.border = THIN_BORDER

    row += 1
    insc = ge.get('inscritos', {})
    aval = ge.get('avaliados', {})
    aprov = ge.get('aprovados', {})
    reprov = ge.get('reprovados', {})

    ge_vals = [
        insc.get('h', 0), insc.get('m', 0), insc.get('total', 0),
        aval.get('h', 0), aval.get('m', 0), aval.get('total', 0),
        aprov.get('total', 0), f"{aprov.get('pct', 0)}%",
        reprov.get('total', 0), f"{reprov.get('pct', 0)}%"
    ]
    for col_idx, val in enumerate(ge_vals, start=1):
        c = ws.cell(row=row, column=col_idx, value=val)
        c.font = FONT_REGULAR_BOLD
        c.alignment = ALIGN_CENTER
        c.border = THIN_BORDER
        if col_idx in (7, 8):
            c.font = FONT_GREEN
        elif col_idx in (9, 10):
            c.font = FONT_RED

    row += 3

    # ----- SECÇÃO 2: RESUMO POR CLASSE -----
    ws.cell(row=row, column=1, value="2. RENDIMENTO POR CLASSE").font = FONT_REGULAR_BOLD
    row += 1

    classe_headers = [
        'Nível / Classe', 'Turmas',
        'Inscritos (HM)', 'Inscritos (M)', 'Inscritos Total',
        'Avaliados Total', 'Aprovados Total', '% Aproveitamento',
        'Reprovados Total', '% Reprovação'
    ]
    for col_idx, h in enumerate(classe_headers, start=1):
        c = ws.cell(row=row, column=col_idx, value=h)
        c.font = FONT_HEADER
        c.fill = FILL_NAVY
        c.alignment = ALIGN_CENTER
        c.border = THIN_BORDER

    row += 1
    if not por_classe:
        ws.cell(row=row, column=1, value="Sem classes registadas").font = FONT_REGULAR
        for ci in range(1, len(classe_headers) + 1):
            ws.cell(row=row, column=ci).border = THIN_BORDER
        row += 1
    else:
        for c_item in por_classe:
            c_insc = c_item.get('inscritos', {})
            c_aval = c_item.get('avaliados', {})
            c_ap = c_item.get('aprovados', {})
            c_rep = c_item.get('reprovados', {})
            c_vals = [
                f"{c_item.get('classe')} Classe",
                c_item.get('turmas', 0),
                c_insc.get('h', 0), c_insc.get('m', 0), c_insc.get('total', 0),
                c_aval.get('total', 0),
                c_ap.get('total', 0), f"{c_ap.get('pct', 0)}%",
                c_rep.get('total', 0), f"{c_rep.get('pct', 0)}%"
            ]
            for col_idx, val in enumerate(c_vals, start=1):
                c = ws.cell(row=row, column=col_idx, value=val)
                c.font = FONT_REGULAR
                c.alignment = ALIGN_LEFT if col_idx == 1 else ALIGN_CENTER
                c.border = THIN_BORDER
                if col_idx in (7, 8):
                    c.font = FONT_GREEN
                elif col_idx in (9, 10):
                    c.font = FONT_RED
            row += 1

    row += 2

    # ----- SECÇÃO 3: APROVEITAMENTO POR TURMA -----
    ws.cell(row=row, column=1, value="3. APROVEITAMENTO PEDAGÓGICO POR TURMA").font = FONT_REGULAR_BOLD
    row += 1

    turma_headers = [
        'Turma', 'Classe', 'Turno', 'Director de Turma',
        'Inscritos Total', 'Avaliados Total', 'Aprovados Total',
        '% Aproveitamento', 'Reprovados Total', '% Reprovação'
    ]
    for col_idx, h in enumerate(turma_headers, start=1):
        c = ws.cell(row=row, column=col_idx, value=h)
        c.font = FONT_HEADER
        c.fill = FILL_NAVY
        c.alignment = ALIGN_CENTER
        c.border = THIN_BORDER

    row += 1
    if not por_turma:
        ws.cell(row=row, column=1, value="Sem turmas activas").font = FONT_REGULAR
        for ci in range(1, len(turma_headers) + 1):
            ws.cell(row=row, column=ci).border = THIN_BORDER
        row += 1
    else:
        for t_item in por_turma:
            t_insc = t_item.get('inscritos', {})
            t_aval = t_item.get('avaliados', {})
            t_ap = t_item.get('aprovados', {})
            t_rep = t_item.get('reprovados', {})
            t_vals = [
                t_item.get('turmaNome', ''),
                t_item.get('grau_ano', ''),
                t_item.get('turno', ''),
                t_item.get('directorTurma', '-'),
                t_insc.get('total', 0),
                t_aval.get('total', 0),
                t_ap.get('total', 0), f"{t_ap.get('pct', 0)}%",
                t_rep.get('total', 0), f"{t_rep.get('pct', 0)}%"
            ]
            for col_idx, val in enumerate(t_vals, start=1):
                c = ws.cell(row=row, column=col_idx, value=val)
                c.font = FONT_REGULAR
                c.alignment = ALIGN_LEFT if col_idx in (1, 4) else ALIGN_CENTER
                c.border = THIN_BORDER
                if col_idx in (7, 8):
                    c.font = FONT_GREEN
                elif col_idx in (9, 10):
                    c.font = FONT_RED
            row += 1

    row += 2

    # ----- SECÇÃO 4: RENDIMENTO POR DISCIPLINA -----
    ws.cell(row=row, column=1, value="4. RENDIMENTO COMPARATIVO POR DISCIPLINA").font = FONT_REGULAR_BOLD
    row += 1

    disc_headers = [
        'Disciplina', 'Código',
        'Avaliados (HM)', 'Avaliados (M)', 'Avaliados Total',
        'Aprovados Total', '% Aproveitamento',
        'Reprovados Total', '% Reprovação', 'Média Final'
    ]
    for col_idx, h in enumerate(disc_headers, start=1):
        c = ws.cell(row=row, column=col_idx, value=h)
        c.font = FONT_HEADER
        c.fill = FILL_NAVY
        c.alignment = ALIGN_CENTER
        c.border = THIN_BORDER

    row += 1
    if not por_disc:
        ws.cell(row=row, column=1, value="Sem disciplinas registadas").font = FONT_REGULAR
        for ci in range(1, len(disc_headers) + 1):
            ws.cell(row=row, column=ci).border = THIN_BORDER
        row += 1
    else:
        for d_item in por_disc:
            d_aval = d_item.get('avaliados', {})
            d_ap = d_item.get('aprovados', {})
            d_rep = d_item.get('reprovados', {})
            d_med = d_item.get('mediaFinal')
            d_vals = [
                d_item.get('nome', ''),
                d_item.get('codigo', ''),
                d_aval.get('h', 0), d_aval.get('m', 0), d_aval.get('total', 0),
                d_ap.get('total', 0), f"{d_ap.get('pct', 0)}%",
                d_rep.get('total', 0), f"{d_rep.get('pct', 0)}%",
                d_med if d_med is not None else '-'
            ]
            for col_idx, val in enumerate(d_vals, start=1):
                c = ws.cell(row=row, column=col_idx, value=val)
                c.font = FONT_REGULAR
                c.alignment = ALIGN_LEFT if col_idx == 1 else ALIGN_CENTER
                c.border = THIN_BORDER
                if col_idx in (6, 7):
                    c.font = FONT_GREEN
                elif col_idx in (8, 9):
                    c.font = FONT_RED
                elif col_idx == 10 and isinstance(val, (int, float)):
                    c.font = FONT_GREEN if val >= 9.5 else FONT_RED
            row += 1

    row += 3

    # Rodapé de Validação
    ws.cell(row=row, column=2, value="O Director Pedagógico (DAP)").alignment = ALIGN_CENTER
    ws.cell(row=row, column=5, value="O Chefe da Secretaria").alignment = ALIGN_CENTER
    ws.cell(row=row, column=8, value="O Director da Escola").alignment = ALIGN_CENTER
    for ci in (2, 5, 8):
        ws.cell(row=row, column=ci).font = FONT_REGULAR_BOLD

    auto_ajustar_colunas(ws, padding=3)
    ws.column_dimensions['A'].width = 24
    ws.column_dimensions['D'].width = 26

    buffer = io.BytesIO()
    salvar_xlsx_padronizado(wb, buffer)
    buffer.seek(0)
    return buffer.getvalue()


# ==================== 11. CADERNETA DE AVALIAÇÃO CONTÍNUA DO PROFESSOR (XLSX) ====================

def gerar_caderneta_xlsx(caderneta_data: dict, orientacao='landscape') -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active

    escola_info = caderneta_data.get('escola') or {}
    turma_info = caderneta_data.get('turma') or {}
    disc_info = caderneta_data.get('disciplina') or {}
    prof_info = caderneta_data.get('professor') or {}
    dt_info = caderneta_data.get('directorTurma') or {}
    ef_info = caderneta_data.get('efectivo') or {}
    alunos = caderneta_data.get('alunos') or []
    estatisticas = caderneta_data.get('estatisticasColunas') or {}

    turma_nome = turma_info.get('nome') or 'Turma'
    ws.title = f"Caderneta {turma_nome}"[:31]
    configurar_pagina_excel(ws, orientacao=orientacao, fit_to_height=0)

    esc_nome = (escola_info.get('nome') or 'ESCOLA SECUNDÁRIA DE CAMBINE').upper()
    prov = escola_info.get('provincia') or 'Inhambane'
    dist = escola_info.get('distrito') or 'Morrumbene'
    disc_nome = (disc_info.get('nome') or 'MATEMÁTICA').upper()
    disc_cod = disc_info.get('codigo') or 'MAT-11CG'
    ano_letivo = turma_info.get('ano_letivo') or '2026'
    grau_ano = turma_info.get('grau_ano') or '11ª Classe'
    turno = turma_info.get('turno') or 'TARDE'
    sala = turma_info.get('sala') or '1'
    ef_h = ef_info.get('h', sum(1 for a in alunos if (a.get('genero') or '').upper() == 'M'))
    ef_m = ef_info.get('m', sum(1 for a in alunos if (a.get('genero') or '').upper().startswith('F')))
    ef_tot = ef_info.get('total', len(alunos))
    prof_nome = f"{prof_info.get('nome') or ''} {prof_info.get('apelido') or ''}".strip() or 'Fernando José Mandamule'
    prof_tel = prof_info.get('telefone') or '+258 842988844'
    dt_nome = dt_info.get('nome') or 'Bionisio'

    # 1. Logótipo Oficial Escolhido pela Instituição & Cabeçalho Institucional Oficial (28 colunas A a AB)
    inserir_logo_cabecalho_xlsx(ws, escola_info, cell='A1')
    ws.merge_cells('A1:AB1')
    ws['A1'] = "REPÚBLICA DE MOÇAMBIQUE"
    ws['A1'].font = FONT_SUBTITLE
    ws['A1'].alignment = ALIGN_CENTER
    ws.row_dimensions[1].height = 20

    ws.merge_cells('A2:AB2')
    ws['A2'] = "MINISTÉRIO DA EDUCAÇÃO E CULTURA"
    ws['A2'].font = FONT_SUBTITLE
    ws['A2'].alignment = ALIGN_CENTER
    ws.row_dimensions[2].height = 20

    ws.merge_cells('A3:AB3')
    ws['A3'] = f"DIRECÇÃO PROVINCIAL DA EDUCAÇÃO — {prov.upper()}"
    ws['A3'].font = FONT_REGULAR
    ws['A3'].alignment = ALIGN_CENTER
    ws.row_dimensions[3].height = 18

    ws.merge_cells('A4:AB4')
    ws['A4'] = f"SERVIÇO DISTRITAL DE EDUCAÇÃO, JUVENTUDE E TECNOLOGIA DE {dist.upper()}"
    ws['A4'].font = FONT_REGULAR
    ws['A4'].alignment = ALIGN_CENTER
    ws.row_dimensions[4].height = 18

    ws.merge_cells('A5:AB5')
    ws['A5'] = esc_nome
    ws['A5'].font = FONT_TITLE
    ws['A5'].alignment = ALIGN_CENTER
    ws.row_dimensions[5].height = 22

    ws.merge_cells('A6:AB6')
    ws['A6'] = f"CADERNETA DE AVALIAÇÃO CONTÍNUA DO PROFESSOR — DISCIPLINA: {disc_nome} ({disc_cod})"
    ws['A6'].font = FONT_TITLE
    ws['A6'].alignment = ALIGN_CENTER
    ws.row_dimensions[6].height = 24

    ws.merge_cells('A7:AB7')
    ws['A7'] = (
        f"Ano Lectivo: {ano_letivo} | Classe: {grau_ano} | Turma: {turma_nome} | Turno: {turno} | Sala: {sala} | "
        f"Efectivo: H={ef_h}, M={ef_m}, HM={ef_tot} | Docente: {prof_nome} ({prof_tel}) | Director de Turma: {dt_nome}"
    )
    ws['A7'].font = FONT_REGULAR
    ws['A7'].alignment = ALIGN_CENTER
    ws.row_dimensions[7].height = 20

    # 2. Cabeçalho Oficial da Tabela em 2 Linhas (Linhas 9 e 10 - Exatamente 28 colunas A a AB)
    ws.merge_cells('A9:A10')
    ws['A9'] = 'Nº'
    ws.merge_cells('B9:B10')
    ws['B9'] = 'Nome Completo do Aluno'
    ws.merge_cells('C9:C10')
    ws['C9'] = 'Gén'
    ws.merge_cells('D9:K9')
    ws['D9'] = 'Iº TRIMESTRE'
    ws.merge_cells('L9:S9')
    ws['L9'] = 'IIº TRIMESTRE'
    ws.merge_cells('T9:AA9')
    ws['T9'] = 'IIIº TRIMESTRE'
    ws.merge_cells('AB9:AB10')
    ws['AB9'] = 'MFD'

    # Linha 10 (subcabeçalhos de cada trimestre):
    subcols = ['1ªA', '2ªA', '3ªA', 'MAP', 'MAS', 'AT', 'MT', 'Cp']
    for idx_s, s_name in enumerate(subcols):
        ws.cell(row=10, column=4 + idx_s, value=s_name)
        ws.cell(row=10, column=12 + idx_s, value=s_name)
        ws.cell(row=10, column=20 + idx_s, value=s_name)

    ws.row_dimensions[9].height = 24
    ws.row_dimensions[10].height = 22
    aplicar_estilo_intervalo(ws, 1, 9, 28, 10, font=FONT_HEADER_SM, fill=FILL_NAVY, border=THIN_BORDER, alignment=ALIGN_CENTER)

    # 3. Linhas dos Alunos
    def fmt_n(val):
        if val is None or val == '' or val == '-':
            return '-'
        try:
            f = float(val)
            return round(f, 1) if f % 1 != 0 else int(f)
        except (ValueError, TypeError):
            return str(val)

    row = 10
    for idx, al in enumerate(alunos, start=1):
        row += 1
        ws.row_dimensions[row].height = 20
        t1 = al.get('t1') or {}
        t2 = al.get('t2') or {}
        t3 = al.get('t3') or {}
        nome_completo = al.get('nomeCompleto') or obter_nome_completo_aluno(al)
        vals = [
            al.get('numero') or idx,
            nome_completo,
            al.get('genero') or 'M',
            fmt_n(t1.get('t1')), fmt_n(t1.get('t2')), fmt_n(t1.get('t3')),
            fmt_n(t1.get('map')), fmt_n(t1.get('mas')), fmt_n(t1.get('at')), fmt_n(t1.get('mt')),
            str(t1.get('comportamento') or '-'),
            fmt_n(t2.get('t1')), fmt_n(t2.get('t2')), fmt_n(t2.get('t3')),
            fmt_n(t2.get('map')), fmt_n(t2.get('mas')), fmt_n(t2.get('at')), fmt_n(t2.get('mt')),
            str(t2.get('comportamento') or '-'),
            fmt_n(t3.get('t1')), fmt_n(t3.get('t2')), fmt_n(t3.get('t3')),
            fmt_n(t3.get('map')), fmt_n(t3.get('mas')), fmt_n(t3.get('at')), fmt_n(t3.get('mt')),
            str(t3.get('comportamento') or '-'),
            fmt_n(al.get('mfd'))
        ]
        for col_idx, val in enumerate(vals, start=1):
            c = ws.cell(row=row, column=col_idx, value=val)
            c.border = THIN_BORDER
            c.alignment = ALIGN_LEFT if col_idx == 2 else ALIGN_CENTER
            if col_idx in (10, 18, 26, 28):  # MT e MFD
                c.fill = FILL_LIGHT
                c.font = FONT_TINY_BOLD
            else:
                c.font = FONT_TINY

    # 4. Parâmetros Estatísticos Oficiais (Colunas 4 a 28)
    col_stat_map = {
        4: 't1_t1', 5: 't1_t2', 6: 't1_t3', 7: 't1_map', 8: 't1_mas', 9: 't1_at', 10: 't1_mt',
        12: 't2_t1', 13: 't2_t2', 14: 't2_t3', 15: 't2_map', 16: 't2_mas', 17: 't2_at', 18: 't2_mt',
        20: 't3_t1', 21: 't3_t2', 22: 't3_t3', 23: 't3_map', 24: 't3_mas', 25: 't3_at', 26: 't3_mt',
        28: 'mfd'
    }

    def _val_cel(s_k, getter, default='-'):
        if not s_k or s_k not in estatisticas:
            return default
        st_c = estatisticas[s_k]
        if (st_c.get('avaliados') or {}).get('total', 0) == 0:
            return default
        return getter(st_c)

    # 1. Linha: Parametro estatistico
    row += 1
    ws.row_dimensions[row].height = 20
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=28)
    ws.cell(row=row, column=1, value='Parametro estatistico')
    aplicar_estilo_intervalo(ws, 1, row, 28, row, font=FONT_REGULAR_BOLD, fill=FILL_GRAY, border=THIN_BORDER, alignment=ALIGN_LEFT)

    # 2. Avaliados (M, F, M+F)
    r_av_start = row + 1
    for gen_idx, (g_lbl, g_k) in enumerate([('M', 'h'), ('F', 'm'), ('M+F', 'total')]):
        row += 1
        ws.row_dimensions[row].height = 17
        if gen_idx == 0:
            ws.cell(row=row, column=1, value='Avaliados')
        ws.cell(row=row, column=3, value=g_lbl)
        is_mf = (g_lbl == 'M+F')
        fill_row = FILL_ROW_GRAY if is_mf else None
        font_row = FONT_TINY_BOLD if is_mf else FONT_TINY
        aplicar_estilo_intervalo(ws, 1, row, 2, row, font=FONT_TINY_BOLD, fill=fill_row, border=THIN_BORDER, alignment=ALIGN_LEFT)
        aplicar_estilo_intervalo(ws, 3, row, 3, row, font=font_row, fill=fill_row, border=THIN_BORDER, alignment=ALIGN_CENTER)
        for col_idx in range(4, 29):
            s_key = col_stat_map.get(col_idx)
            val = _val_cel(s_key, lambda st: (st.get('avaliados') or {}).get(g_k, 0))
            c = ws.cell(row=row, column=col_idx, value=val)
            c.font = font_row
            if fill_row:
                c.fill = fill_row
            c.border = THIN_BORDER
            c.alignment = ALIGN_CENTER
    ws.merge_cells(start_row=r_av_start, start_column=1, end_row=row, end_column=2)

    # 3. Positivos (M, F, M+F)
    r_pos_start = row + 1
    for gen_idx, (g_lbl, g_k) in enumerate([('M', 'h'), ('F', 'm'), ('M+F', 'total')]):
        row += 1
        ws.row_dimensions[row].height = 17
        if gen_idx == 0:
            ws.cell(row=row, column=1, value='Positivos')
        ws.cell(row=row, column=3, value=g_lbl)
        is_mf = (g_lbl == 'M+F')
        fill_row = FILL_ROW_SUCCESS if is_mf else None
        font_row = FONT_GREEN_SM
        aplicar_estilo_intervalo(ws, 1, row, 2, row, font=FONT_GREEN_SM, fill=fill_row, border=THIN_BORDER, alignment=ALIGN_LEFT)
        aplicar_estilo_intervalo(ws, 3, row, 3, row, font=font_row, fill=fill_row, border=THIN_BORDER, alignment=ALIGN_CENTER)
        for col_idx in range(4, 29):
            s_key = col_stat_map.get(col_idx)
            val = _val_cel(s_key, lambda st: (st.get('positivas') or {}).get(g_k, 0))
            c = ws.cell(row=row, column=col_idx, value=val)
            c.font = font_row
            if fill_row:
                c.fill = fill_row
            c.border = THIN_BORDER
            c.alignment = ALIGN_CENTER
    ws.merge_cells(start_row=r_pos_start, start_column=1, end_row=row, end_column=2)

    # 4. % Positivos (M, F, M+F)
    r_pct_pos_start = row + 1
    for gen_idx, (g_lbl, g_k) in enumerate([('M', 'pctH'), ('F', 'pctM'), ('M+F', 'pct')]):
        row += 1
        ws.row_dimensions[row].height = 17
        if gen_idx == 0:
            ws.cell(row=row, column=1, value='% Positivos')
        ws.cell(row=row, column=3, value=g_lbl)
        is_mf = (g_lbl == 'M+F')
        fill_row = FILL_ROW_SUCCESS if is_mf else None
        font_row = FONT_GREEN_SM
        aplicar_estilo_intervalo(ws, 1, row, 2, row, font=FONT_GREEN_SM, fill=fill_row, border=THIN_BORDER, alignment=ALIGN_LEFT)
        aplicar_estilo_intervalo(ws, 3, row, 3, row, font=font_row, fill=fill_row, border=THIN_BORDER, alignment=ALIGN_CENTER)
        for col_idx in range(4, 29):
            s_key = col_stat_map.get(col_idx)
            val = _val_cel(s_key, lambda st: f"{(st.get('positivas') or {}).get(g_k, 0)}%")
            c = ws.cell(row=row, column=col_idx, value=val)
            c.font = font_row
            if fill_row:
                c.fill = fill_row
            c.border = THIN_BORDER
            c.alignment = ALIGN_CENTER
    ws.merge_cells(start_row=r_pct_pos_start, start_column=1, end_row=row, end_column=2)

    # 5. Negativos (M, F, M+F)
    r_neg_start = row + 1
    for gen_idx, (g_lbl, g_k) in enumerate([('M', 'h'), ('F', 'm'), ('M+F', 'total')]):
        row += 1
        ws.row_dimensions[row].height = 17
        if gen_idx == 0:
            ws.cell(row=row, column=1, value='Negativos')
        ws.cell(row=row, column=3, value=g_lbl)
        is_mf = (g_lbl == 'M+F')
        fill_row = FILL_ROW_DANGER if is_mf else None
        font_row = FONT_RED_SM
        aplicar_estilo_intervalo(ws, 1, row, 2, row, font=FONT_RED_SM, fill=fill_row, border=THIN_BORDER, alignment=ALIGN_LEFT)
        aplicar_estilo_intervalo(ws, 3, row, 3, row, font=font_row, fill=fill_row, border=THIN_BORDER, alignment=ALIGN_CENTER)
        for col_idx in range(4, 29):
            s_key = col_stat_map.get(col_idx)
            val = _val_cel(s_key, lambda st: (st.get('negativas') or {}).get(g_k, 0))
            c = ws.cell(row=row, column=col_idx, value=val)
            c.font = font_row
            if fill_row:
                c.fill = fill_row
            c.border = THIN_BORDER
            c.alignment = ALIGN_CENTER
    ws.merge_cells(start_row=r_neg_start, start_column=1, end_row=row, end_column=2)

    # 6. % Negativos (M, F, M+F)
    r_pct_neg_start = row + 1
    for gen_idx, (g_lbl, g_k) in enumerate([('M', 'pctH'), ('F', 'pctM'), ('M+F', 'pct')]):
        row += 1
        ws.row_dimensions[row].height = 17
        if gen_idx == 0:
            ws.cell(row=row, column=1, value='% Negativos')
        ws.cell(row=row, column=3, value=g_lbl)
        is_mf = (g_lbl == 'M+F')
        fill_row = FILL_ROW_DANGER if is_mf else None
        font_row = FONT_RED_SM
        aplicar_estilo_intervalo(ws, 1, row, 2, row, font=FONT_RED_SM, fill=fill_row, border=THIN_BORDER, alignment=ALIGN_LEFT)
        aplicar_estilo_intervalo(ws, 3, row, 3, row, font=font_row, fill=fill_row, border=THIN_BORDER, alignment=ALIGN_CENTER)
        for col_idx in range(4, 29):
            s_key = col_stat_map.get(col_idx)
            val = _val_cel(s_key, lambda st: f"{(st.get('negativas') or {}).get(g_k, 0)}%")
            c = ws.cell(row=row, column=col_idx, value=val)
            c.font = font_row
            if fill_row:
                c.fill = fill_row
            c.border = THIN_BORDER
            c.alignment = ALIGN_CENTER
    ws.merge_cells(start_row=r_pct_neg_start, start_column=1, end_row=row, end_column=2)

    # 7. Faixas Oficiais (0 a 9,4 | 9,5 a 13,4 | 13,5 a 16,4 | 16,5 a 18,4 | 18,5 a 20)
    faixas_defs = [
        ('0 a 9,4', 'f0_94'),
        ('9,5 a 13,4', 'f95_134'),
        ('13,5 a 16,4', 'f135_164'),
        ('16,5 a 18,4', 'f165_184'),
        ('18,5 a 20', 'f185_20'),
    ]
    for f_lbl, f_prop in faixas_defs:
        row += 1
        ws.row_dimensions[row].height = 17
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
        ws.cell(row=row, column=1, value=f_lbl)
        aplicar_estilo_intervalo(ws, 1, row, 3, row, font=FONT_TINY_BOLD, border=THIN_BORDER, alignment=ALIGN_LEFT)
        for col_idx in range(4, 29):
            s_key = col_stat_map.get(col_idx)
            val = _val_cel(s_key, lambda st: ((st.get('faixas') or {}).get(f_prop) or {}).get('total', 0))
            c = ws.cell(row=row, column=col_idx, value=val)
            c.font = FONT_TINY_BOLD
            c.border = THIN_BORDER
            c.alignment = ALIGN_CENTER

    # 8. Linha final: Média da Coluna
    row += 1
    ws.row_dimensions[row].height = 18
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
    ws.cell(row=row, column=1, value='Média da Coluna')
    aplicar_estilo_intervalo(ws, 1, row, 3, row, font=FONT_TINY_BOLD, fill=FILL_ROW_BLUE, border=THIN_BORDER, alignment=ALIGN_LEFT)
    for col_idx in range(4, 29):
        s_key = col_stat_map.get(col_idx)
        val = _val_cel(s_key, lambda st: st.get('media', 0))
        c = ws.cell(row=row, column=col_idx, value=val)
        c.font = FONT_TINY_BOLD
        c.fill = FILL_ROW_BLUE
        c.border = THIN_BORDER
        c.alignment = ALIGN_CENTER

    # 9. Assinaturas Oficiais (Idênticas ao PDF e Foto)
    row += 2
    ws.row_dimensions[row].height = 20
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=8)
    ws.cell(row=row, column=1, value="O Docente da Disciplina").font = FONT_REGULAR_BOLD
    ws.cell(row=row, column=1).alignment = ALIGN_CENTER

    ws.merge_cells(start_row=row, start_column=10, end_row=row, end_column=17)
    ws.cell(row=row, column=10, value="O Director de Turma").font = FONT_REGULAR_BOLD
    ws.cell(row=row, column=10).alignment = ALIGN_CENTER

    ws.merge_cells(start_row=row, start_column=19, end_row=row, end_column=28)
    ws.cell(row=row, column=19, value="O Director Adjunto Pedagógico").font = FONT_REGULAR_BOLD
    ws.cell(row=row, column=19).alignment = ALIGN_CENTER

    row += 1
    ws.row_dimensions[row].height = 20
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=8)
    ws.cell(row=row, column=1, value="__________________________________").font = FONT_REGULAR
    ws.cell(row=row, column=1).alignment = ALIGN_CENTER

    ws.merge_cells(start_row=row, start_column=10, end_row=row, end_column=17)
    ws.cell(row=row, column=10, value="__________________________________").font = FONT_REGULAR
    ws.cell(row=row, column=10).alignment = ALIGN_CENTER

    ws.merge_cells(start_row=row, start_column=19, end_row=row, end_column=28)
    ws.cell(row=row, column=19, value="__________________________________").font = FONT_REGULAR
    ws.cell(row=row, column=19).alignment = ALIGN_CENTER

    row += 1
    ws.row_dimensions[row].height = 20
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=8)
    ws.cell(row=row, column=1, value=prof_nome).font = FONT_REGULAR
    ws.cell(row=row, column=1).alignment = ALIGN_CENTER

    ws.merge_cells(start_row=row, start_column=10, end_row=row, end_column=17)
    ws.cell(row=row, column=10, value=dt_nome).font = FONT_REGULAR
    ws.cell(row=row, column=10).alignment = ALIGN_CENTER

    ws.merge_cells(start_row=row, start_column=19, end_row=row, end_column=28)
    ws.cell(row=row, column=19, value="Assinatura e Carimbo").font = FONT_REGULAR
    ws.cell(row=row, column=19).alignment = ALIGN_CENTER

    # Ajuste Automático Milimétrico de Colunas em Função do Conteúdo
    max_nome_len = max((len(al.get('nomeCompleto') or obter_nome_completo_aluno(al) or '') for al in alunos), default=25)
    ws.column_dimensions['A'].width = 5.0
    ws.column_dimensions['B'].width = max(28.0, min(45.0, max_nome_len + 3.0))
    ws.column_dimensions['C'].width = 5.5
    for c_idx in range(4, 29):
        col_letter = get_column_letter(c_idx)
        ws.column_dimensions[col_letter].width = 7.0

    buffer = io.BytesIO()
    salvar_xlsx_padronizado(wb, buffer)
    buffer.seek(0)
    return buffer.getvalue()


