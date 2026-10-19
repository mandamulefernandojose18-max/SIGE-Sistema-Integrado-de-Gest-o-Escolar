"""
Serviço de Exportação em Word (DOCX) — SIGE (Sistema Integrado de Gestão Escolar)
Gera documentos oficiais rigorosamente formatados em Times New Roman, tamanho 12,
com margens ajustadas, sem corte de conteúdo e controle preciso de orientação
(Horizontal/Landscape para Pautas e Vertical/Portrait para Boletins, Declarações e Certificados).
"""
import io
import datetime
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.enum.section import WD_ORIENTATION
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def aplicar_fonte_times(run, pt_size=12, bold=False, italic=False, color_rgb=None):
    """Aplica estritamente a fonte Times New Roman em run do Word."""
    run.font.name = 'Times New Roman'
    run.font.size = Pt(pt_size)
    run.bold = bold
    run.italic = italic
    if color_rgb:
        run.font.color.rgb = color_rgb
    else:
        run.font.color.rgb = RGBColor(0x11, 0x11, 0x11)
    
    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn('w:ascii'), 'Times New Roman')
    rFonts.set(qn('w:hAnsi'), 'Times New Roman')
    rFonts.set(qn('w:cs'), 'Times New Roman')

def configurar_secao_pagina(doc, orientacao='portrait', margem_pol=0.6):
    """Configura tamanho A4 e orientação de forma rigorosa."""
    section = doc.sections[0]
    section.top_margin = Inches(margem_pol)
    section.bottom_margin = Inches(margem_pol)
    section.left_margin = Inches(margem_pol)
    section.right_margin = Inches(margem_pol)
    
    if orientacao.lower() in ('landscape', 'horizontal'):
        section.orientation = WD_ORIENTATION.LANDSCAPE
        section.page_width = Inches(11.69)   # 297 mm
        section.page_height = Inches(8.27)   # 210 mm
    else:
        section.orientation = WD_ORIENTATION.PORTRAIT
        section.page_width = Inches(8.27)    # 210 mm
        section.page_height = Inches(11.69)  # 297 mm

def aplicar_cant_split_tabela(table):
    """Impede que linhas da tabela sejam cortadas de forma indesejada entre páginas."""
    for row in table.rows:
        trPr = row._tr.get_or_add_trPr()
        trPr.append(OxmlElement('w:cantSplit'))
    if len(table.rows) > 0:
        header_trPr = table.rows[0]._tr.get_or_add_trPr()
        header_trPr.append(OxmlElement('w:tblHeader'))

def set_cell_border(cell, **kwargs):
    """Define bordas finas sólidas para células."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        edge_data = kwargs.get(edge)
        if edge_data:
            tag = 'w:{}'.format(edge)
            element = OxmlElement(tag)
            element.set(qn('w:val'), edge_data.get('val', 'single'))
            element.set(qn('w:sz'), str(edge_data.get('sz', 4)))
            element.set(qn('w:space'), '0')
            element.set(qn('w:color'), edge_data.get('color', '555555'))
            tcBorders.append(element)
    tcPr.append(tcBorders)

def set_cell_shading(cell, color_hex):
    """Aplica cor de fundo em célula docx."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex.lstrip('#'))
    tcPr.append(shd)

# ==================== 1. PAUTA GERAL DA TURMA (HORIZONTAL) ====================

def gerar_pauta_docx(turma, escola, periodo, ano_letivo, dados_alunos, disciplinas, orientacao='landscape') -> bytes:
    doc = docx.Document()
    configurar_secao_pagina(doc, orientacao=orientacao, margem_pol=0.45)

    # Cabeçalho Oficial
    p1 = doc.add_paragraph()
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.paragraph_format.space_after = Pt(2)
    r1 = p1.add_run("REPÚBLICA DE MOÇAMBIQUE")
    aplicar_fonte_times(r1, pt_size=12, bold=True)

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.space_after = Pt(2)
    r2 = p2.add_run("MINISTÉRIO DA EDUCAÇÃO E DESENVOLVIMENTO HUMANO")
    aplicar_fonte_times(r2, pt_size=11, bold=True)

    prov = (getattr(escola, 'provincia', 'Inhambane') or 'Inhambane').upper()
    dist = (getattr(escola, 'distrito', 'Massinga') or 'Massinga').upper()
    p3 = doc.add_paragraph()
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p3.paragraph_format.space_after = Pt(2)
    r3 = p3.add_run(f"GOVERNO DA PROVÍNCIA DE {prov} — SDEJT DE {dist}")
    aplicar_fonte_times(r3, pt_size=10, bold=False)

    p_esc = doc.add_paragraph()
    p_esc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_esc.paragraph_format.space_after = Pt(6)
    r_esc = p_esc.add_run(f"{escola.nome.upper()}")
    aplicar_fonte_times(r_esc, pt_size=12, bold=True)

    # Título da Pauta
    periodo_str = periodo.replace('_', ' ').title() if periodo else 'Geral'
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_after = Pt(4)
    r_title = p_title.add_run(f"PAUTA OFICIAL DE APROVEITAMENTO — {periodo_str.upper()} / {ano_letivo}")
    aplicar_fonte_times(r_title, pt_size=12, bold=True)

    area_desc = f" | Área/Secção: {turma.area}" if getattr(turma, 'area', None) and str(turma.area).strip().lower() not in ('geral', 'ensino geral', 'tronco comum', '') else ""
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_after = Pt(10)
    r_sub = p_sub.add_run(f"Turma: {turma.nome} | Grau/Classe: {turma.grau_ano}{area_desc} | Turno: {turma.turno}")
    aplicar_fonte_times(r_sub, pt_size=10.5, italic=True)

    # Tabela de Pauta
    headers = ['Nº', 'Nome Completo do Aluno'] + [(getattr(d, 'codigo', None) or getattr(d, 'nome', str(d))) for d in disciplinas] + ['Média', 'Resultado']
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = 'Table Grid'
    aplicar_cant_split_tabela(table)

    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = ""
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(str(h))
        aplicar_fonte_times(r, pt_size=9, bold=True)

    if not dados_alunos:
        row_cells = table.add_row().cells
        row_cells[0].text = '-'
        row_cells[1].text = 'Nenhum aluno registado nesta turma'
        for i in range(2, len(headers)):
            row_cells[i].text = '-'
    else:
        for idx, aluno in enumerate(dados_alunos, start=1):
            row_cells = table.add_row().cells
            row_cells[0].text = str(aluno.get('numero') or idx)
            row_cells[1].text = aluno.get('nome', '')
            
            for d_idx, d in enumerate(disciplinas, start=2):
                d_id = str(getattr(d, 'id', d))
                d_nome = str(getattr(d, 'nome', d))
                d_cod = str(getattr(d, 'codigo', d))
                notas_dict = aluno.get('notas', {}) if isinstance(aluno.get('notas'), dict) else {}
                disc_dict = aluno.get('disciplinas', {}) if isinstance(aluno.get('disciplinas'), dict) else {}
                n_info = notas_dict.get(d_id) or notas_dict.get(d_nome) or disc_dict.get(d_nome) or disc_dict.get(d_id) or disc_dict.get(d_cod) or {}
                if isinstance(n_info, dict):
                    val = n_info.get('media_final', n_info.get('nota', '-'))
                else:
                    val = n_info
                row_cells[d_idx].text = str(val if val is not None else '-')

            row_cells[-2].text = str(aluno.get('media_geral', '-'))
            res_val = str(aluno.get('resultado', 'Aprovado')).strip()
            row_cells[-1].text = res_val

            for c_idx, cell in enumerate(row_cells):
                if cell.paragraphs:
                    p = cell.paragraphs[0]
                    if c_idx > 1:
                        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    for r in p.runs:
                        aplicar_fonte_times(r, pt_size=8.5)

            if row_cells[-1].paragraphs and row_cells[-1].paragraphs[0].runs:
                r_res = row_cells[-1].paragraphs[0].runs[0]
                if res_val in ('Reprovado', 'R', 'Excluído'):
                    aplicar_fonte_times(r_res, pt_size=8.5, bold=True, color_rgb=RGBColor(220, 38, 38))
                else:
                    aplicar_fonte_times(r_res, pt_size=8.5, bold=True)

    doc.add_paragraph()
    p_foot = doc.add_paragraph()
    p_foot.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_foot = p_foot.add_run(f"Documento processado informaticamente pelo SIGE • {datetime.date.today().strftime('%d/%m/%Y')}")
    aplicar_fonte_times(r_foot, pt_size=9, italic=True, color_rgb=RGBColor(100, 100, 100))

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

# ==================== 2. BOLETIM DE APROVEITAMENTO (VERTICAL) ====================

def gerar_boletim_docx(aluno, escola, ano_letivo, notas_disciplinas, orientacao='portrait') -> bytes:
    doc = docx.Document()
    configurar_secao_pagina(doc, orientacao=orientacao, margem_pol=0.6)

    # Cabeçalho da República
    p1 = doc.add_paragraph()
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.paragraph_format.space_after = Pt(2)
    r1 = p1.add_run("REPÚBLICA DE MOÇAMBIQUE")
    aplicar_fonte_times(r1, pt_size=13, bold=True)

    prov = (getattr(escola, 'provincia', 'Inhambane') or 'Inhambane').upper()
    dist = (getattr(escola, 'distrito', 'Massinga') or 'Massinga').upper()
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.space_after = Pt(2)
    r2 = p2.add_run(f"GOVERNO DA PROVÍNCIA DE {prov}")
    aplicar_fonte_times(r2, pt_size=11, bold=True)

    p3 = doc.add_paragraph()
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p3.paragraph_format.space_after = Pt(2)
    r3 = p3.add_run(f"SERVIÇO DISTRITAL DE EDUCAÇÃO, JUVENTUDE E TECNOLOGIA DE {dist}")
    aplicar_fonte_times(r3, pt_size=10, bold=False)

    escola_nome = escola.nome.upper()
    if not escola_nome.startswith('ESCOLA'):
        escola_nome = f"ESCOLA SECUNDÁRIA DE {escola_nome}"
    p4 = doc.add_paragraph()
    p4.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p4.paragraph_format.space_after = Pt(2)
    r4 = p4.add_run(escola_nome)
    aplicar_fonte_times(r4, pt_size=12, bold=True)

    codigo_inst = getattr(escola, 'codigo_escola', None) or f"ESC-{str(escola.id)[:4].upper()}"
    p_cod = doc.add_paragraph()
    p_cod.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cod.paragraph_format.space_after = Pt(8)
    r_cod = p_cod.add_run(f"Código da Instituição: {codigo_inst}")
    aplicar_fonte_times(r_cod, pt_size=9, italic=True)

    # Linha divisória
    p_div = doc.add_paragraph()
    p_div.paragraph_format.space_after = Pt(8)
    r_div = p_div.add_run("―" * 58)
    r_div.font.color.rgb = RGBColor(50, 50, 50)

    # Título do Boletim
    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_tit.paragraph_format.space_after = Pt(12)
    r_tit = p_tit.add_run(f"BOLETIM DE APROVEITAMENTO ESCOLAR — ANO LECTIVO {ano_letivo or 2026}")
    aplicar_fonte_times(r_tit, pt_size=12, bold=True)

    # Dados do Aluno (Tabela de identificação)
    t_aluno = doc.add_table(rows=2, cols=2)
    t_aluno.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_aluno.style = 'Table Grid'
    aplicar_cant_split_tabela(t_aluno)

    turma_obj = getattr(aluno, 'turma', None)
    turma_nome = turma_obj.nome if turma_obj else '10ª Classe A'
    grau_nome = getattr(turma_obj, 'grau_ano', None) or getattr(aluno, 'classe', None) or '10ª Classe'
    classe_turma = f"{grau_nome} - {turma_nome}" if grau_nome not in turma_nome else turma_nome
    turno = getattr(turma_obj, 'turno', 'Manhã') if turma_obj else 'Manhã'

    aluno_nome_str = f"{aluno.nome} {getattr(aluno, 'apelido', '') or ''}".strip().upper() if aluno else 'ALUNO'
    matricula_str = getattr(aluno, 'matricula', None) or getattr(aluno, 'codigo_matricula', '---')

    t_aluno.rows[0].cells[0].paragraphs[0].add_run("Nome do Aluno: ").bold = True
    r = t_aluno.rows[0].cells[0].paragraphs[0].add_run(aluno_nome_str)
    aplicar_fonte_times(r, pt_size=11, bold=True)

    t_aluno.rows[0].cells[1].paragraphs[0].add_run("Classe / Turma: ").bold = True
    r = t_aluno.rows[0].cells[1].paragraphs[0].add_run(classe_turma)
    aplicar_fonte_times(r, pt_size=11)

    t_aluno.rows[1].cells[0].paragraphs[0].add_run("Nº de Matrícula: ").bold = True
    r = t_aluno.rows[1].cells[0].paragraphs[0].add_run(matricula_str)
    aplicar_fonte_times(r, pt_size=11)

    t_aluno.rows[1].cells[1].paragraphs[0].add_run("Turno / Ano: ").bold = True
    r = t_aluno.rows[1].cells[1].paragraphs[0].add_run(f"{turno} | {ano_letivo or 2026}")
    aplicar_fonte_times(r, pt_size=11)

    for row in t_aluno.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                for run in p.runs:
                    aplicar_fonte_times(run, pt_size=11)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # Tabela de Disciplinas e Notas
    t_notas = doc.add_table(rows=1, cols=6)
    t_notas.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_notas.style = 'Table Grid'
    aplicar_cant_split_tabela(t_notas)

    cabecalhos = ['Disciplina Curricular', '1º Trim', '2º Trim', '3º Trim', 'Média Final', 'Situação']
    for idx, c in enumerate(cabecalhos):
        p = t_notas.rows[0].cells[idx].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(c)
        aplicar_fonte_times(r, pt_size=10, bold=True)

    total_media = 0
    qtd_media = 0

    for disc in notas_disciplinas:
        row = t_notas.add_row()
        nome_d = disc.get('nome') or disc.get('disciplina') or 'Disciplina'
        t1 = disc.get('t1', disc.get('trimestre1', '-'))
        t2 = disc.get('t2', disc.get('trimestre2', '-'))
        t3 = disc.get('t3', disc.get('trimestre3', '-'))
        med = disc.get('media_anual', disc.get('mediaFinal', disc.get('media_final', '-')))
        sit = disc.get('situacao', disc.get('resultado', ''))

        if med not in (None, '-', '', '---'):
            try:
                m_num = float(med)
                total_media += m_num
                qtd_media += 1
                if not sit:
                    sit = 'Aprovado' if m_num >= 9.5 else 'Reprovado'
            except (ValueError, TypeError):
                pass

        valores = [str(nome_d), str(t1 or '-'), str(t2 or '-'), str(t3 or '-'), str(med or '-'), str(sit or '-')]
        for c_idx, val in enumerate(valores):
            p = row.cells[c_idx].paragraphs[0]
            if c_idx > 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(val)
            aplicar_fonte_times(r, pt_size=12, bold=(c_idx == 4))

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # Resumo do Conselho
    media_global = round(total_media / qtd_media, 1) if qtd_media > 0 else '-'
    resultado_geral = 'Transita' if (isinstance(media_global, (int, float)) and media_global >= 9.5) else ('Não Transita' if isinstance(media_global, (int, float)) else 'Em Avaliação')

    p_res = doc.add_paragraph()
    p_res.paragraph_format.space_after = Pt(14)
    r_res1 = p_res.add_run("Decisão do Conselho de Avaliação: ")
    aplicar_fonte_times(r_res1, pt_size=12, bold=True)
    r_res2 = p_res.add_run(f"O aluno obteve o resultado de ")
    aplicar_fonte_times(r_res2, pt_size=12)
    r_res3 = p_res.add_run(f"{resultado_geral.upper()}")
    aplicar_fonte_times(r_res3, pt_size=12, bold=True)
    r_res4 = p_res.add_run(f" com Média Global de ")
    aplicar_fonte_times(r_res4, pt_size=12)
    r_res5 = p_res.add_run(f"{media_global} valores.")
    aplicar_fonte_times(r_res5, pt_size=12, bold=True)

    # Assinaturas
    doc.add_paragraph().paragraph_format.space_after = Pt(20)
    t_ass = doc.add_table(rows=1, cols=2)
    t_ass.alignment = WD_TABLE_ALIGNMENT.CENTER
    
    p_ass1 = t_ass.rows[0].cells[0].paragraphs[0]
    p_ass1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_ass1.add_run("O Director de Turma\n\n__________________________________")
    for r in p_ass1.runs:
        aplicar_fonte_times(r, pt_size=11)

    p_ass2 = t_ass.rows[0].cells[1].paragraphs[0]
    p_ass2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_ass2.add_run("O Director da Escola\n\n__________________________________")
    for r in p_ass2.runs:
        aplicar_fonte_times(r, pt_size=11)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

# ==================== 3. DECLARAÇÃO COM NOTAS (VERTICAL) ====================

def gerar_declaracao_docx(aluno, escola, ano_letivo, notas_disciplinas, media_global=None, director_nome=None, orientacao='portrait') -> bytes:
    doc = docx.Document()
    configurar_secao_pagina(doc, orientacao=orientacao, margem_pol=0.65)

    prov = (getattr(escola, 'provincia', 'Inhambane') or 'Inhambane').upper()
    dist = (getattr(escola, 'distrito', 'Massinga') or 'Massinga').title()
    escola_nome = escola.nome.upper()
    dir_nome = director_nome or getattr(escola, 'director_nome', None) or 'Pero Chitofo Murrombe'

    # Cabeçalho Oficial
    p1 = doc.add_paragraph()
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.paragraph_format.space_after = Pt(2)
    r1 = p1.add_run("REPÚBLICA DE MOÇAMBIQUE")
    aplicar_fonte_times(r1, pt_size=13, bold=True)

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.space_after = Pt(2)
    r2 = p2.add_run(f"GOVERNO DA PROVÍNCIA DE {prov}")
    aplicar_fonte_times(r2, pt_size=11, bold=True)

    p3 = doc.add_paragraph()
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p3.paragraph_format.space_after = Pt(2)
    r3 = p3.add_run(f"DIRECÇÃO PROVINCIAL DA EDUCAÇÃO E CULTURA DE {prov}")
    aplicar_fonte_times(r3, pt_size=10, bold=False)

    p4 = doc.add_paragraph()
    p4.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p4.paragraph_format.space_after = Pt(12)
    r4 = p4.add_run(escola_nome)
    aplicar_fonte_times(r4, pt_size=12, bold=True)

    # Título
    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_tit.paragraph_format.space_after = Pt(14)
    r_tit = p_tit.add_run("DECLARAÇÃO COM NOTAS")
    aplicar_fonte_times(r_tit, pt_size=14, bold=True)

    # Corpo da Declaração
    aluno_nome = f"{aluno.nome} {getattr(aluno, 'apelido', '') or ''}".strip().upper()
    pai = getattr(aluno, 'pai', None) or '...........................................'
    mae = getattr(aluno, 'mae', None) or '...........................................'
    doc_tipo = getattr(aluno, 'tipo_documento', 'B.I.') or 'B.I.'
    doc_num = getattr(aluno, 'numero_documento', None) or getattr(aluno, 'bi_numero', None) or aluno.matricula or '---'
    grau_classe = (aluno.turma.grau_ano if aluno.turma and aluno.turma.grau_ano else getattr(aluno, 'classe', None)) or '10ª Classe'

    p_corp = doc.add_paragraph()
    p_corp.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_corp.paragraph_format.space_after = Pt(12)
    p_corp.paragraph_format.line_spacing = 1.25

    texto_declaracao = (
        f"{dir_nome}, Director da {escola_nome}, declara que {aluno_nome}, "
        f"filho(a) de {pai} e de {mae}, portador(a) do {doc_tipo} nº {doc_num}, concluiu com aproveitamento "
        f"neste estabelecimento de ensino no ano lectivo de {ano_letivo or 2026} a {grau_classe}, "
        f"obtendo as seguintes classificações por disciplina:"
    )
    r_corp = p_corp.add_run(texto_declaracao)
    aplicar_fonte_times(r_corp, pt_size=12)

    # Tabela de Notas
    t_notas = doc.add_table(rows=1, cols=2)
    t_notas.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_notas.style = 'Table Grid'
    aplicar_cant_split_tabela(t_notas)

    p_h1 = t_notas.rows[0].cells[0].paragraphs[0]
    p_h1.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p_h1.add_run("Disciplina Curricular")
    aplicar_fonte_times(r, pt_size=12, bold=True)

    p_h2 = t_notas.rows[0].cells[1].paragraphs[0]
    p_h2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_h2.add_run("Classificação Final (Valores)")
    aplicar_fonte_times(r, pt_size=12, bold=True)

    for disc in notas_disciplinas:
        row = t_notas.add_row()
        nome_d = disc.get('nome') or disc.get('disciplina') or 'Disciplina'
        nota = disc.get('media_anual', disc.get('mediaFinal', disc.get('media_final', disc.get('nota', '-'))))
        
        p_d = row.cells[0].paragraphs[0]
        r_d = p_d.add_run(str(nome_d))
        aplicar_fonte_times(r_d, pt_size=12)

        p_n = row.cells[1].paragraphs[0]
        p_n.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_n = p_n.add_run(str(nota if nota is not None else '-'))
        aplicar_fonte_times(r_n, pt_size=12, bold=True)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # Fecho
    p_fim = doc.add_paragraph()
    p_fim.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_fim.paragraph_format.space_after = Pt(20)
    hoje = datetime.date.today().strftime('%d de %B de %Y')
    r_fim = p_fim.add_run(
        f"E por ser verdade e me ter sido solicitada, mandei passar a presente declaração que vai por mim assinada "
        f"e autenticada com o carimbo a óleo em uso nesta instituição. {dist}, aos {hoje}."
    )
    aplicar_fonte_times(r_fim, pt_size=12)

    # Assinatura
    p_ass = doc.add_paragraph()
    p_ass.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_ass = p_ass.add_run(f"O Director da Escola\n\n\n__________________________________\n{dir_nome}")
    aplicar_fonte_times(r_ass, pt_size=11, bold=True)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

# ==================== 4. CERTIFICADO DE HABILITAÇÕES (VERTICAL) ====================

def gerar_certificado_docx(aluno, escola, ano_letivo, notas_disciplinas, media_global=None, codigo_autenticidade=None, orientacao='portrait') -> bytes:
    doc = docx.Document()
    configurar_secao_pagina(doc, orientacao=orientacao, margem_pol=0.65)

    prov = (getattr(escola, 'provincia', 'Inhambane') or 'Inhambane').upper()
    dist = (getattr(escola, 'distrito', 'Massinga') or 'Massinga').title()
    escola_nome = escola.nome.upper()
    dir_nome = getattr(escola, 'director_nome', None) or 'Pero Chitofo Murrombe'

    p1 = doc.add_paragraph()
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.paragraph_format.space_after = Pt(2)
    r1 = p1.add_run("REPÚBLICA DE MOÇAMBIQUE")
    aplicar_fonte_times(r1, pt_size=13, bold=True)

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.space_after = Pt(2)
    r2 = p2.add_run(f"GOVERNO DA PROVÍNCIA DE {prov}")
    aplicar_fonte_times(r2, pt_size=11, bold=True)

    p3 = doc.add_paragraph()
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p3.paragraph_format.space_after = Pt(14)
    r3 = p3.add_run(escola_nome)
    aplicar_fonte_times(r3, pt_size=12, bold=True)

    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_tit.paragraph_format.space_after = Pt(14)
    r_tit = p_tit.add_run("CERTIFICADO DE HABILITAÇÕES LITERÁRIAS")
    aplicar_fonte_times(r_tit, pt_size=14, bold=True)

    aluno_nome = f"{aluno.nome} {getattr(aluno, 'apelido', '') or ''}".strip().upper()
    grau_classe = (aluno.turma.grau_ano if aluno.turma and aluno.turma.grau_ano else getattr(aluno, 'classe', None)) or '12ª Classe'
    area = (aluno.turma.area if aluno.turma and aluno.turma.area else getattr(aluno, 'area', 'Ciências e Letras')) or 'Ciências e Letras'
    nasc = str(aluno.data_nascimento) if getattr(aluno, 'data_nascimento', None) else '---'

    p_corp = doc.add_paragraph()
    p_corp.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_corp.paragraph_format.space_after = Pt(12)
    p_corp.paragraph_format.line_spacing = 1.25

    corpo = (
        f"Certifica-se que {aluno_nome}, nascido(a) a {nasc}, natural de {dist}, província de {prov}, "
        f"concluiu com aproveitamento neste estabelecimento de ensino no ano lectivo de {ano_letivo or 2026} "
        f"a {grau_classe} (Área de {area}), com as seguintes classificações:"
    )
    r_corp = p_corp.add_run(corpo)
    aplicar_fonte_times(r_corp, pt_size=12)

    # Tabela com as notas
    t_notas = doc.add_table(rows=1, cols=2)
    t_notas.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_notas.style = 'Table Grid'
    aplicar_cant_split_tabela(t_notas)

    t_notas.rows[0].cells[0].paragraphs[0].add_run("Disciplina Curricular").bold = True
    t_notas.rows[0].cells[1].paragraphs[0].add_run("Nota Final (Valores)").bold = True

    for disc in notas_disciplinas:
        row = t_notas.add_row()
        nome_d = disc.get('nome') or disc.get('disciplina') or 'Disciplina'
        nota = disc.get('media_anual', disc.get('mediaFinal', disc.get('media_final', disc.get('nota', '-'))))
        
        row.cells[0].paragraphs[0].add_run(str(nome_d))
        p = row.cells[1].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run(str(nota if nota is not None else '-')).bold = True

    for row in t_notas.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                for r in p.runs:
                    aplicar_fonte_times(r, pt_size=12)

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    p_cod = doc.add_paragraph()
    p_cod.paragraph_format.space_after = Pt(16)
    cod_str = codigo_autenticidade or f"CERT-{aluno.matricula}-2026"
    r_cod = p_cod.add_run(f"Código de Autenticação Digital: {cod_str}")
    aplicar_fonte_times(r_cod, pt_size=10, italic=True)

    # Assinatura
    p_ass = doc.add_paragraph()
    p_ass.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_ass = p_ass.add_run(f"O Director da Escola\n\n\n__________________________________\n{dir_nome}")
    aplicar_fonte_times(r_ass, pt_size=11, bold=True)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

# ==================== 5. ACTA DE CONSELHO (HORIZONTAL) ====================

def gerar_acta_docx(turma, escola, periodo, ano_letivo, dados_alunos,
                    tabela_efectivo=None, tabela_aproveitamento=None,
                    disciplinas=None, trimestres_com_notas=None,
                    estatisticas=None, presidente=None, data_sessao=None,
                    orientacao='landscape', params_sessao=None, **kwargs) -> bytes:
    doc = docx.Document()
    configurar_secao_pagina(doc, orientacao=orientacao, margem_pol=0.4)

    # Cabeçalho Oficial
    p1 = doc.add_paragraph()
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.paragraph_format.space_after = Pt(2)
    r1 = p1.add_run("REPÚBLICA DE MOÇAMBIQUE")
    aplicar_fonte_times(r1, pt_size=12, bold=True)

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.space_after = Pt(2)
    r2 = p2.add_run("MINISTÉRIO DA EDUCAÇÃO E DESENVOLVIMENTO HUMANO")
    aplicar_fonte_times(r2, pt_size=11, bold=True)

    prov_str = (getattr(escola, 'provincia', '') or 'Inhambane').upper()
    dist_str = (getattr(escola, 'distrito', '') or 'Massinga').upper()

    p_dpe = doc.add_paragraph()
    p_dpe.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_dpe.paragraph_format.space_after = Pt(2)
    r_dpe = p_dpe.add_run(f"DIRECÇÃO PROVINCIAL DA EDUCAÇÃO — {prov_str}\nSERVIÇO DISTRITAL DE EDUCAÇÃO, JUVENTUDE E TECNOLOGIA DE {dist_str}")
    aplicar_fonte_times(r_dpe, pt_size=9.5, bold=False)

    p3 = doc.add_paragraph()
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p3.paragraph_format.space_after = Pt(3)
    r3 = p3.add_run(f"{escola.nome.upper()}")
    aplicar_fonte_times(r3, pt_size=11, bold=True)

    # Título da Acta e Subtítulo
    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_tit.paragraph_format.space_after = Pt(1)
    r_tit = p_tit.add_run(f"ACTA DO CONSELHO DE AVALIAÇÃO DA TURMA {turma.nome} — {ano_letivo or 2026}")
    aplicar_fonte_times(r_tit, pt_size=11, bold=True)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_after = Pt(4)
    r_sub = p_sub.add_run(f"SECTOR PEDAGÓGICO — {turma.grau_ano} | CURSO {'NOCTURNO' if (turma.turno or '').upper() == 'NOITE' else 'DIURNO'}")
    aplicar_fonte_times(r_sub, pt_size=9.5, bold=True, color_rgb=RGBColor(0x1e, 0x3a, 0x8a))

    # Sessão e Texto Protocolar
    ps = dict(params_sessao or {})
    p1_s = ps.get('presidenteT1') or presidente or '____________________'
    p2_s = ps.get('presidenteT2') or presidente or '____________________'
    p3_s = ps.get('presidenteT3') or presidente or '____________________'

    def _formatar_data_br(val):
        if not val:
            return f"___/___/{ano_letivo or 2026}"
        val = str(val).strip()
        if re.match(r'^\d{4}-\d{2}-\d{2}$', val):
            parts = val.split('-')
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
        return val

    dt1 = _formatar_data_br(ps.get('dataT1') or data_sessao)
    dt2 = _formatar_data_br(ps.get('dataT2') or data_sessao)
    dt3 = _formatar_data_br(ps.get('dataT3') or data_sessao)

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
        f"Sob presidência do senhor professor {p1_s} (Iº Trimestre); {p2_s} (IIº Trimestre); {p3_s} (IIIº Trimestre); "
        f"director/substituto do director de turma {dt_turma} da turma {turma.nome} do grupo da {turma.grau_ano}, "
        f"curso {curso_txt}, realizou-se o Conselho de Avaliação do Iº; IIº, IIIº, Trimestre no dia {dt1}; {dt2}; {dt3}, "
        f"com início às {hIni1} horas e {mIni1} minutos e com término às {hFim1} horas e {mFim1} minutos (Iº Trim); "
        f"{hIni2} horas e {mIni2} minutos e com término às {hFim2} horas e {mFim2} minutos (IIº Trim); "
        f"{hIni3} horas e {mIni3} minutos e com término às {hFim3} horas e {mFim3} minutos (IIIº Trim). "
        f"No final deste conselho colheram-se os resultados que abaixo vão discriminados de todos os membros que participaram:"
    )
    p_proto = doc.add_paragraph()
    p_proto.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_proto.paragraph_format.space_after = Pt(4)
    r_proto = p_proto.add_run(texto_protocolar)
    aplicar_fonte_times(r_proto, pt_size=8.5)

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

    # TABELA 1: Efectivos e Movimento (Fluxo contínuo imediatamente após a informação)
    p_t1_tit = doc.add_paragraph()
    p_t1_tit.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_t1_tit.paragraph_format.space_before = Pt(2)
    p_t1_tit.paragraph_format.space_after = Pt(2)
    p_t1_tit.paragraph_format.keep_with_next = True
    r_t1_tit = p_t1_tit.add_run("1. APROVEITAMENTO POR TRIMESTRES E FIM DO ANO (EFECTIVOS E MOVIMENTO)")
    aplicar_fonte_times(r_t1_tit, pt_size=9.5, bold=True, color_rgb=RGBColor(0x1e, 0x3a, 0x8a))

    t1_doc = doc.add_table(rows=2, cols=10)
    t1_doc.alignment = WD_TABLE_ALIGNMENT.CENTER
    t1_doc.style = 'Table Grid'
    aplicar_cant_split_tabela(t1_doc)

    hdr1 = ['CATEGORIA', 'GÉN', 'Iº TRIMESTRE', '', 'IIº TRIMESTRE', '', 'IIIº TRIMESTRE', '', 'FIM DO ANO', '']
    hdr2 = ['', '', 'Nº', '%', 'Nº', '%', 'Nº', '%', 'Nº', '%']
    for idx, c in enumerate(hdr1):
        if c:
            p = t1_doc.rows[0].cells[idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(c)
            aplicar_fonte_times(r, pt_size=8, bold=True)
            set_cell_shading(t1_doc.rows[0].cells[idx], '1E3A8A')
            r.font.color.rgb = RGBColor(0xff, 0xff, 0xff)
    for idx, c in enumerate(hdr2):
        if c:
            p = t1_doc.rows[1].cells[idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(c)
            aplicar_fonte_times(r, pt_size=7.5, bold=True)
            set_cell_shading(t1_doc.rows[1].cells[idx], '1E3A8A')
            r.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

    # Mesclar cabeçalhos
    t1_doc.rows[0].cells[0].merge(t1_doc.rows[1].cells[0])
    t1_doc.rows[0].cells[1].merge(t1_doc.rows[1].cells[1])
    t1_doc.rows[0].cells[2].merge(t1_doc.rows[0].cells[3])
    t1_doc.rows[0].cells[4].merge(t1_doc.rows[0].cells[5])
    t1_doc.rows[0].cells[6].merge(t1_doc.rows[0].cells[7])
    t1_doc.rows[0].cells[8].merge(t1_doc.rows[0].cells[9])

    cats_te = [
        ('Matrículas / Efectivo Inicial', 'inscritos'),
        ('Desistentes', 'desistentes'),
        ('Transferidos', 'transferidos'),
        ('Falecidos', 'falecidos'),
        ('Perdeu Ano por Faltas', 'perdeuFaltas'),
        ('Anulou Matrícula', 'anulouMatricula'),
        ('Alunos Avaliados', 'avaliados'),
    ]

    for label, chave in cats_te:
        is_inicial = (chave == 'inscritos')
        for gen in ['H', 'M', 'HM']:
            row = t1_doc.add_row()
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

            vals = [label if gen == 'H' else '', gen, v_t1, p_t1, v_t2, p_t2, v_t3, p_t3, v_fa, p_fa]
            for c_i, v in enumerate(vals):
                p = row.cells[c_i].paragraphs[0]
                if c_i == 0:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                else:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = p.add_run(v)
                aplicar_fonte_times(r, pt_size=7.5, bold=(gen == 'HM'))
            if gen == 'HM':
                for cell in row.cells[1:]:
                    set_cell_shading(cell, 'F1F5F9')

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # TABELA 2: Aproveitamento Pedagógico
    p_t2_tit = doc.add_paragraph()
    p_t2_tit.paragraph_format.space_after = Pt(4)
    r_t2_tit = p_t2_tit.add_run("2. APROVEITAMENTO PEDAGÓGICO POR FAIXAS E CRESCIMENTO")
    aplicar_fonte_times(r_t2_tit, pt_size=10, bold=True, color_rgb=RGBColor(0x1e, 0x3a, 0x8a))

    t2_doc = doc.add_table(rows=2, cols=13)
    t2_doc.alignment = WD_TABLE_ALIGNMENT.CENTER
    t2_doc.style = 'Table Grid'
    aplicar_cant_split_tabela(t2_doc)

    hdr2_1 = ['CLASSIFICAÇÃO', 'GÉN', 'Iº TRIMESTRE', '', 'IIº TRIMESTRE', '', 'IIIº TRIMESTRE', '', 'FIM DO ANO', '', 'CRESCIMENTO', '', '']
    hdr2_2 = ['', '', 'Nº', '%', 'Nº', '%', 'Nº', '%', 'Nº', '%', 'I-II', 'II-III', 'GLO']
    for idx, c in enumerate(hdr2_1):
        if c:
            p = t2_doc.rows[0].cells[idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(c)
            aplicar_fonte_times(r, pt_size=8, bold=True)
            set_cell_shading(t2_doc.rows[0].cells[idx], '1E3A8A')
            r.font.color.rgb = RGBColor(0xff, 0xff, 0xff)
    for idx, c in enumerate(hdr2_2):
        if c:
            p = t2_doc.rows[1].cells[idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(c)
            aplicar_fonte_times(r, pt_size=7.5, bold=True)
            set_cell_shading(t2_doc.rows[1].cells[idx], '1E3A8A')
            r.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

    t2_doc.rows[0].cells[0].merge(t2_doc.rows[1].cells[0])
    t2_doc.rows[0].cells[1].merge(t2_doc.rows[1].cells[1])
    t2_doc.rows[0].cells[2].merge(t2_doc.rows[0].cells[3])
    t2_doc.rows[0].cells[4].merge(t2_doc.rows[0].cells[5])
    t2_doc.rows[0].cells[6].merge(t2_doc.rows[0].cells[7])
    t2_doc.rows[0].cells[8].merge(t2_doc.rows[0].cells[9])
    t2_doc.rows[0].cells[10].merge(t2_doc.rows[0].cells[12])

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

    for label, chave, is_aprov in cats_ta:
        for gen in ['H', 'M', 'HM']:
            row = t2_doc.add_row()
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
                n1 = float(ta.get('t1', {}).get(chave, {}).get(pct_prop, 0))
                n2 = float(ta.get('t2', {}).get(chave, {}).get(pct_prop, 0))
                dif = round(n2 - n1, 1)
                c1_2 = f"+{dif}%" if dif > 0 else f"{dif}%"

            c2_3 = '-'
            if tem_notas_t2 and tem_notas_t3:
                n2 = float(ta.get('t2', {}).get(chave, {}).get(pct_prop, 0))
                n3 = float(ta.get('t3', {}).get(chave, {}).get(pct_prop, 0))
                dif = round(n3 - n2, 1)
                c2_3 = f"+{dif}%" if dif > 0 else f"{dif}%"

            c_glo = '-'
            if tem_notas_t1 and tem_notas_fa:
                n1 = float(ta.get('t1', {}).get(chave, {}).get(pct_prop, 0))
                nfa = float(ta.get('fimAno', {}).get(chave, {}).get(pct_prop, 0))
                dif = round(nfa - n1, 1)
                c_glo = f"+{dif}%" if dif > 0 else f"{dif}%"

            vals = [label if gen == 'H' else '', gen, v_t1, p_t1, v_t2, p_t2, v_t3, p_t3, v_fa, p_fa, c1_2, c2_3, c_glo]
            for c_i, v in enumerate(vals):
                p = row.cells[c_i].paragraphs[0]
                if c_i == 0:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                else:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = p.add_run(v)
                aplicar_fonte_times(r, pt_size=7.5, bold=(gen == 'HM' or is_aprov))
            if is_aprov:
                for cell in row.cells:
                    set_cell_shading(cell, 'DCFCE7')
            elif gen == 'HM':
                for cell in row.cells[1:]:
                    set_cell_shading(cell, 'F1F5F9')

    # Fluxo contínuo para Tabela 3 e Lista de Alunos (sem quebra de página manual)
    p_sep = doc.add_paragraph()
    p_sep.paragraph_format.space_before = Pt(6)
    p_sep.paragraph_format.space_after = Pt(4)

    # TABELA 3: Aproveitamento por Disciplina
    if discs:
        p_t3_tit = doc.add_paragraph()
        p_t3_tit.paragraph_format.space_after = Pt(4)
        r_t3_tit = p_t3_tit.add_run("3. ÁREA CURRICULAR & ESTATÍSTICA PEDAGÓGICA POR DISCIPLINA")
        aplicar_fonte_times(r_t3_tit, pt_size=10, bold=True, color_rgb=RGBColor(0x1e, 0x3a, 0x8a))

        num_d = len(discs)
        t3_doc = doc.add_table(rows=2, cols=1 + num_d * 3)
        t3_doc.alignment = WD_TABLE_ALIGNMENT.CENTER
        t3_doc.style = 'Table Grid'
        aplicar_cant_split_tabela(t3_doc)

        p = t3_doc.rows[0].cells[0].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run("CLASSIFICAÇÃO")
        aplicar_fonte_times(r, pt_size=8, bold=True)
        set_cell_shading(t3_doc.rows[0].cells[0], '1E3A8A')
        r.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

        for i, d in enumerate(discs):
            c_idx = 1 + i * 3
            p_d = t3_doc.rows[0].cells[c_idx].paragraphs[0]
            p_d.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r_d = p_d.add_run(d.get('nome', '').upper())
            aplicar_fonte_times(r_d, pt_size=7.5, bold=True)
            set_cell_shading(t3_doc.rows[0].cells[c_idx], '1E3A8A')
            r_d.font.color.rgb = RGBColor(0xff, 0xff, 0xff)
            t3_doc.rows[0].cells[c_idx].merge(t3_doc.rows[0].cells[c_idx + 2])

            for sub_i, gen in enumerate(['H', 'M', 'HM']):
                p_g = t3_doc.rows[1].cells[c_idx + sub_i].paragraphs[0]
                p_g.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r_g = p_g.add_run(gen)
                aplicar_fonte_times(r_g, pt_size=7, bold=True)
                set_cell_shading(t3_doc.rows[1].cells[c_idx + sub_i], '1E3A8A')
                r_g.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

        t3_doc.rows[0].cells[0].merge(t3_doc.rows[1].cells[0])

        faixas_disc = [
            ('[0 - 9,4 valores]', 'faixa0_9', False),
            ('[9,5 - 13,4 valores]', 'faixa10_13', False),
            ('[13,5 - 16,4 valores]', 'faixa14_16', False),
            ('[16,5 - 18,4 valores]', 'faixa17_18', False),
            ('[18,5 - 20 valores]', 'faixa19_20', False),
            ('Alunos Avaliados', 'avaliados', 'neutral'),
            ('Notas Positivas', 'positivas', 'success'),
            ('% Positivas', 'positivas_pct', 'success'),
            ('Assinatura do Docente', 'assinatura', 'docente'),
        ]

        for f_label, f_key, f_type in faixas_disc:
            row = t3_doc.add_row()
            p_l = row.cells[0].paragraphs[0]
            r_l = p_l.add_run(f_label)
            aplicar_fonte_times(r_l, pt_size=7.5, bold=(f_type in ('neutral', 'success')))

            for i, d in enumerate(discs):
                c_idx = 1 + i * 3
                if f_type == 'docente':
                    p_sig = row.cells[c_idx].paragraphs[0]
                    p_sig.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    r_sig = p_sig.add_run("_________________")
                    aplicar_fonte_times(r_sig, pt_size=6.5)
                    row.cells[c_idx].merge(row.cells[c_idx + 2])
                elif f_key == 'positivas_pct':
                    vals = [
                        f"{d.get('positivas', {}).get('pctH', 0)}%",
                        f"{d.get('positivas', {}).get('pctM', 0)}%",
                        f"{d.get('positivas', {}).get('pct', 0)}%"
                    ]
                    for sub_i, val in enumerate(vals):
                        p_v = row.cells[c_idx + sub_i].paragraphs[0]
                        p_v.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        r_v = p_v.add_run(val)
                        aplicar_fonte_times(r_v, pt_size=7, bold=True)
                else:
                    bloco = d.get(f_key, {})
                    vals = [str(bloco.get('h', 0)), str(bloco.get('m', 0)), str(bloco.get('hm', 0))]
                    for sub_i, val in enumerate(vals):
                        p_v = row.cells[c_idx + sub_i].paragraphs[0]
                        p_v.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        r_v = p_v.add_run(val)
                        aplicar_fonte_times(r_v, pt_size=7, bold=(sub_i == 2 or f_type == 'neutral'))

            if f_type == 'neutral':
                for cell in row.cells:
                    set_cell_shading(cell, 'F1F5F9')
            elif f_type == 'success':
                for cell in row.cells:
                    set_cell_shading(cell, 'DCFCE7')

        doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # TABELA 4: Relação Nominal dos Alunos e Deliberação do Conselho
    p_t4_tit = doc.add_paragraph()
    p_t4_tit.paragraph_format.space_after = Pt(4)
    r_t4_tit = p_t4_tit.add_run("4. RELAÇÃO NOMINAL DOS ALUNOS E DELIBERAÇÃO DO CONSELHO")
    aplicar_fonte_times(r_t4_tit, pt_size=10, bold=True, color_rgb=RGBColor(0x1e, 0x3a, 0x8a))

    t_acta = doc.add_table(rows=1, cols=5)
    t_acta.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_acta.style = 'Table Grid'
    aplicar_cant_split_tabela(t_acta)

    cab = ['Nº', 'Nome Completo do Aluno', 'Média Final', 'Comportamento', 'Decisão do Conselho']
    for idx, c in enumerate(cab):
        p = t_acta.rows[0].cells[idx].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(c)
        aplicar_fonte_times(r, pt_size=8.5, bold=True)
        set_cell_shading(t_acta.rows[0].cells[idx], '1E3A8A')
        r.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

    for idx, aluno in enumerate(dados_alunos, start=1):
        row = t_acta.add_row()
        row.cells[0].paragraphs[0].add_run(str(aluno.get('numero') or idx))
        row.cells[1].paragraphs[0].add_run(aluno.get('nome', ''))
        row.cells[2].paragraphs[0].add_run(str(aluno.get('media_geral', '-')))
        row.cells[3].paragraphs[0].add_run(str(aluno.get('comportamento', 'B') or 'B'))
        row.cells[4].paragraphs[0].add_run(str(aluno.get('resultado', 'Aprovado')))

        for c_idx, cell in enumerate(row.cells):
            p = cell.paragraphs[0]
            if c_idx != 1:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs:
                aplicar_fonte_times(r, pt_size=8)

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # Assinaturas Oficiais dos Membros do Conselho
    pres_final = p1_s if p1_s != '____________________' else (presidente or 'Presidente da Sessão')
    dir_turma_final = dt_turma if dt_turma != '____________________' else 'Director de Turma'

    t_sig = doc.add_table(rows=2, cols=3)
    t_sig.alignment = WD_TABLE_ALIGNMENT.CENTER
    aplicar_cant_split_tabela(t_sig)

    cabs_sig = ["O Presidente do Conselho", "O Secretário do Conselho", "O Director de Turma"]
    for c_i, c_txt in enumerate(cabs_sig):
        p = t_sig.rows[0].cells[c_i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(c_txt)
        aplicar_fonte_times(r, pt_size=8.5, bold=True)

    vals_sig = [f"\n_____________________________\n{pres_final}", "\n_____________________________\nSecretário(a) Designado(a)", f"\n_____________________________\n{dir_turma_final}"]
    for c_i, v_txt in enumerate(vals_sig):
        p = t_sig.rows[1].cells[c_i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(v_txt)
        aplicar_fonte_times(r, pt_size=8.5)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

# ==================== 6. FICHA DO ALUNO (VERTICAL) ====================

def gerar_ficha_docx(aluno, escola, orientacao='portrait') -> bytes:
    from common.utils.avaliacoes_mocambique import obter_disciplinas_plano_curricular

    doc = docx.Document()
    configurar_secao_pagina(doc, orientacao=orientacao, margem_pol=0.55)

    p1 = doc.add_paragraph()
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.paragraph_format.space_after = Pt(2)
    r1 = p1.add_run("REPÚBLICA DE MOÇAMBIQUE")
    aplicar_fonte_times(r1, pt_size=12, bold=True)

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.space_after = Pt(2)
    r2 = p2.add_run(f"{escola.nome.upper()}")
    aplicar_fonte_times(r2, pt_size=11, bold=True)

    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_tit.paragraph_format.space_after = Pt(10)
    r_tit = p_tit.add_run("FICHA BIOGRÁFICA DO ALUNO")
    aplicar_fonte_times(r_tit, pt_size=12, bold=True)

    # Obter dados acadêmicos (Classe, Área/Secção, Turma, Turno, Ano Lectivo)
    classe_str = getattr(aluno, 'classe', None) or (aluno.turma.grau_ano if getattr(aluno, 'turma', None) else None) or '10ª Classe'
    area_str = getattr(aluno, 'area', None) or (aluno.turma.area if getattr(aluno, 'turma', None) else None) or 'Ensino Geral'
    turma_str = aluno.turma.nome if getattr(aluno, 'turma', None) else '---'
    turno_str = (getattr(aluno.turma, 'turno', '') or 'Diurno').capitalize() if getattr(aluno, 'turma', None) else 'Diurno'
    ano_letivo_str = getattr(aluno.turma, 'ano_letivo', None) if getattr(aluno, 'turma', None) else (getattr(aluno, 'ano_ingresso', None) or '2026')
    nome_completo = f"{aluno.nome} {getattr(aluno, 'apelido', '') or ''}".strip().upper()
    doc_ident = f"{getattr(aluno, 'tipo_documento', 'BI') or 'BI'} nº {getattr(aluno, 'numero_documento', None) or getattr(aluno, 'bi_numero', '---')}"
    naturalidade = f"{getattr(aluno, 'distrito', '---')} / {getattr(aluno, 'provincia', '---')}"
    resp_nome = getattr(aluno, 'nome_responsavel', '---') or '---'
    resp_cont = getattr(aluno, 'contato_responsavel', '---') or '---'

    # 1. Tabela com campos biográficos
    table = doc.add_table(rows=0, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = 'Table Grid'
    aplicar_cant_split_tabela(table)

    campos = [
        ('Nome Completo:', nome_completo),
        ('Número de Matrícula:', str(aluno.matricula)),
        ('Data de Nascimento:', str(aluno.data_nascimento or '---')),
        ('Género:', 'Masculino' if getattr(aluno, 'genero', 'M') == 'M' else 'Feminino'),
        ('Documento de Identificação:', doc_ident),
        ('Filiação (Pai):', getattr(aluno, 'pai', '---') or '---'),
        ('Filiação (Mãe):', getattr(aluno, 'mae', '---') or '---'),
        ('Naturalidade / Província:', naturalidade),
        ('Classe Actual:', str(classe_str)),
        ('Área / Secção de Estudos:', str(area_str)),
        ('Turma Actual / Turno:', f"{turma_str} ({turno_str}) | Ano Lectivo: {ano_letivo_str}"),
        ('Encarregado de Educação:', f"{resp_nome} (Contacto: {resp_cont})")
    ]

    for label, val in campos:
        row = table.add_row()
        p0 = row.cells[0].paragraphs[0]
        r0 = p0.add_run(label)
        aplicar_fonte_times(r0, pt_size=9.5, bold=True)
        set_cell_shading(row.cells[0], 'F8FAFC')

        p1 = row.cells[1].paragraphs[0]
        r1 = p1.add_run(str(val))
        aplicar_fonte_times(r1, pt_size=9.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 2. Tabela de Disciplinas do Plano Curricular
    p_sec = doc.add_paragraph()
    p_sec.paragraph_format.space_after = Pt(4)
    r_sec = p_sec.add_run(f"PLANO CURRICULAR & DISCIPLINAS ({str(classe_str).upper()} — {str(area_str).upper()})")
    aplicar_fonte_times(r_sec, pt_size=10, bold=True, color_rgb=RGBColor(0x1e, 0x3a, 0x8a))

    disciplinas = obter_disciplinas_plano_curricular(aluno, escola)
    t_disc = doc.add_table(rows=1, cols=4)
    t_disc.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_disc.style = 'Table Grid'
    aplicar_cant_split_tabela(t_disc)

    cab_disc = ['Nº', 'Código', 'Disciplina Curricular', 'Carga Horária']
    for idx, c in enumerate(cab_disc):
        p = t_disc.rows[0].cells[idx].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(c)
        aplicar_fonte_times(r, pt_size=8.5, bold=True)
        set_cell_shading(t_disc.rows[0].cells[idx], '1E3A8A')
        r.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

    for d in disciplinas:
        row = t_disc.add_row()
        row.cells[0].paragraphs[0].add_run(str(d.get('numero', '-')))
        row.cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        row.cells[1].paragraphs[0].add_run(str(d.get('codigo', '-')))
        row.cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        row.cells[2].paragraphs[0].add_run(str(d.get('nome', '-')))
        row.cells[3].paragraphs[0].add_run(str(d.get('carga', '-')))
        row.cells[3].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        for c_idx, cell in enumerate(row.cells):
            for r in cell.paragraphs[0].runs:
                aplicar_fonte_times(r, pt_size=8)

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # 3. Assinaturas Oficiais
    t_sig = doc.add_table(rows=2, cols=2)
    t_sig.alignment = WD_TABLE_ALIGNMENT.CENTER
    aplicar_cant_split_tabela(t_sig)

    p_s0 = t_sig.rows[0].cells[0].paragraphs[0]
    p_s0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_s0 = p_s0.add_run("A Secretaria Escolar")
    aplicar_fonte_times(r_s0, pt_size=9, bold=True)

    p_s1 = t_sig.rows[0].cells[1].paragraphs[0]
    p_s1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_s1 = p_s1.add_run("O Aluno / Encarregado de Educação")
    aplicar_fonte_times(r_s1, pt_size=9, bold=True)

    p_v0 = t_sig.rows[1].cells[0].paragraphs[0]
    p_v0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_v0 = p_v0.add_run("\n__________________________________")
    aplicar_fonte_times(r_v0, pt_size=9)

    p_v1 = t_sig.rows[1].cells[1].paragraphs[0]
    p_v1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_v1 = p_v1.add_run("\n__________________________________")
    aplicar_fonte_times(r_v1, pt_size=9)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

# ==================== 7. RECIBO DE PAGAMENTO (VERTICAL) ====================

def gerar_recibo_docx(pagamento, escola, orientacao='portrait') -> bytes:
    doc = docx.Document()
    configurar_secao_pagina(doc, orientacao=orientacao, margem_pol=0.65)

    # Determinação estrita do estado de liquidação e conformidade de pagamento
    status_raw = str(getattr(pagamento, 'status', '')).upper().strip()
    valor_pago_val = float(getattr(pagamento, 'valor_pago', 0) or 0)
    tem_data_pag = bool(getattr(pagamento, 'data_pagamento', None))
    is_pago = (status_raw == 'PAGO') and (tem_data_pag or valor_pago_val > 0)

    # Dados sincronizados da Instituição
    nome_escola = getattr(escola, 'nome', 'Instituição de Ensino')
    provincia = getattr(escola, 'provincia', '') or 'Inhambane'
    distrito = getattr(escola, 'distrito', '') or 'Massinga'
    nuit = getattr(escola, 'nuit', None) or getattr(escola, 'nif_cnpj', None) or '---'
    telefone = getattr(escola, 'telefone', '---')

    p_rep = doc.add_paragraph()
    p_rep.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_rep.paragraph_format.space_after = Pt(1)
    r_rep = p_rep.add_run("REPÚBLICA DE MOÇAMBIQUE\nMINISTÉRIO DA EDUCAÇÃO E DESENVOLVIMENTO HUMANO")
    aplicar_fonte_times(r_rep, pt_size=10, bold=True)

    p1 = doc.add_paragraph()
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.paragraph_format.space_after = Pt(2)
    r1 = p1.add_run(f"{nome_escola.upper()}")
    aplicar_fonte_times(r1, pt_size=12, bold=True)

    p_info = doc.add_paragraph()
    p_info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_info.paragraph_format.space_after = Pt(8)
    r_info = p_info.add_run(f"NUIT: {nuit} | Província: {provincia} | Distrito: {distrito} | Tel: {telefone}")
    aplicar_fonte_times(r_info, pt_size=9, italic=True)

    num_rec = getattr(pagamento, 'recibo_numero', None) or f"REC-{pagamento.id}"
    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_tit.paragraph_format.space_after = Pt(4)
    if is_pago:
        r_tit = p_tit.add_run(f"RECIBO DE PAGAMENTO OFICIAL — {num_rec}")
    else:
        r_tit = p_tit.add_run(f"RECIBO / GUIA DE PAGAMENTO (NÃO PAGO) — {num_rec}")
    aplicar_fonte_times(r_tit, pt_size=12, bold=True)

    # Banner de Estado
    p_ban = doc.add_paragraph()
    p_ban.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_ban.paragraph_format.space_after = Pt(10)
    if is_pago:
        r_ban = p_ban.add_run("[ SITUAÇÃO: PAGO / LIQUIDADO COM SUCESSO ]")
        aplicar_fonte_times(r_ban, pt_size=11, bold=True, color_rgb=(21, 128, 61))
    else:
        r_ban = p_ban.add_run("[ ATENÇÃO: NÃO PAGO — PENDENTE DE LIQUIDAÇÃO ]")
        aplicar_fonte_times(r_ban, pt_size=11, bold=True, color_rgb=(185, 28, 28))

    table = doc.add_table(rows=0, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = 'Table Grid'
    aplicar_cant_split_tabela(table)

    aluno = getattr(pagamento, 'aluno', None)
    nome_aluno = f"{aluno.nome} {getattr(aluno, 'apelido', '') or ''}".strip().upper() if aluno else '---'
    matricula = aluno.matricula if aluno else '---'
    turma_nome = aluno.turma.nome if aluno and aluno.turma else '---'
    grau_ano = getattr(aluno.turma, 'grau_ano', '') if aluno and aluno.turma else ''
    turma_completa = f"{turma_nome} ({grau_ano})" if grau_ano else turma_nome
    turno_sala = f"{getattr(aluno.turma, 'turno', '---')} / Sala: {getattr(aluno.turma, 'sala', '---')}" if aluno and aluno.turma else '---'
    encarregado = getattr(aluno, 'encarregado_nome', '') or getattr(aluno, 'nome_pai', '') or getattr(aluno, 'nome_mae', '') or '---' if aluno else '---'

    if is_pago:
        valor_liq = f"{getattr(pagamento, 'valor_pago', None) or pagamento.valor} MT"
        estado_txt = "PAGO"
        metodo_txt = str(getattr(pagamento, 'metodo_pagamento', 'MPESA') or 'MPESA')
        data_conf_txt = str(getattr(pagamento, 'data_pagamento', None) or pagamento.created_at)[:10]
    else:
        valor_liq = "0,00 MT (Aguardando Liquidação)"
        estado_txt = "NÃO PAGO"
        metodo_txt = "Pendente de Liquidação"
        data_conf_txt = "Aguardando Confirmação"

    campos = [
        ('Instituição de Ensino:', nome_escola.upper()),
        ('Localização / Província:', f"{distrito}, {provincia}"),
        ('Nome do Aluno:', nome_aluno),
        ('Matrícula do Aluno:', matricula),
        ('Turma / Classe:', turma_completa),
        ('Turno / Instalações:', turno_sala),
        ('Encarregado de Educação:', encarregado),
        ('Descrição do Serviço:', getattr(pagamento, 'descricao', 'Mensalidade / Propina') or 'Mensalidade / Propina'),
        ('Mês de Referência:', str(getattr(pagamento, 'mes_referencia', '---') or '---')),
        ('Valor Total Cobrado:', f"{pagamento.valor} MT"),
        ('Valor Liquidado:', valor_liq),
        ('Situação / Estado:', estado_txt),
        ('Forma de Pagamento:', metodo_txt),
        ('Data de Vencimento:', str(getattr(pagamento, 'data_vencimento', '---') or '---')[:10]),
        ('Data de Liquidação / Confirmação:', data_conf_txt)
    ]

    for label, val in campos:
        row = table.add_row()
        p0 = row.cells[0].paragraphs[0]
        r0 = p0.add_run(label)
        aplicar_fonte_times(r0, pt_size=10, bold=True)

        p1 = row.cells[1].paragraphs[0]
        r1 = p1.add_run(str(val))
        if label == 'Situação / Estado:':
            if is_pago:
                aplicar_fonte_times(r1, pt_size=10, bold=True, color_rgb=(21, 128, 61))
            else:
                aplicar_fonte_times(r1, pt_size=10, bold=True, color_rgb=(185, 28, 28))
        elif label == 'Valor Liquidado:' and not is_pago:
            aplicar_fonte_times(r1, pt_size=10, bold=True, color_rgb=(185, 28, 28))
        else:
            aplicar_fonte_times(r1, pt_size=10)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # Aviso no rodapé
    p_av = doc.add_paragraph()
    p_av.paragraph_format.space_after = Pt(8)
    if not is_pago:
        r_av = p_av.add_run("AVISO: Este recibo possui a indicação expressa de NÃO PAGO. Não confere quitação de dívida até a respectiva liquidação e confirmação de pagamento no sistema.")
        aplicar_fonte_times(r_av, pt_size=8.5, italic=True, color_rgb=(185, 28, 28))
    else:
        r_av = p_av.add_run("COMPROVATIVO DE QUITAÇÃO: Certifica-se que o valor indicado foi devidamente liquidado e confirmado no sistema oficial SIGE.")
        aplicar_fonte_times(r_av, pt_size=8.5, italic=True, color_rgb=(21, 128, 61))

    # Carimbo temporal
    carimbo_dt = datetime.datetime.now().strftime('%d/%m/%Y às %H:%M:%S')
    p_auth = doc.add_paragraph()
    p_auth.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_auth.paragraph_format.space_after = Pt(14)
    r_auth = p_auth.add_run(f"Processado por Computador aos {carimbo_dt} | Autenticação Digital SIGE")
    aplicar_fonte_times(r_auth, pt_size=8, italic=True)

    p_ass = doc.add_paragraph()
    p_ass.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_ass = p_ass.add_run("A Secretaria Escolar\n\n__________________________________\nAssinatura e Carimbo Oficial")
    aplicar_fonte_times(r_ass, pt_size=9.5)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


# ==================== 8. CADERNETA DO PROFESSOR (DOCX HORIZONTAL) ====================

def gerar_caderneta_docx(caderneta_data: dict, orientacao='landscape') -> bytes:
    doc = docx.Document()
    configurar_secao_pagina(doc, orientacao=orientacao, margem_pol=0.35)

    escola_info = caderneta_data.get('escola') or {}
    turma_info = caderneta_data.get('turma') or {}
    disc_info = caderneta_data.get('disciplina') or {}
    prof_info = caderneta_data.get('professor') or {}
    dt_info = caderneta_data.get('directorTurma') or {}
    ef_info = caderneta_data.get('efectivo') or {}
    alunos = caderneta_data.get('alunos') or []
    estatisticas = caderneta_data.get('estatisticasColunas') or {}

    esc_nome = (escola_info.get('nome') or 'ESCOLA SECUNDÁRIA').upper()
    prov = escola_info.get('provincia') or 'Inhambane'
    dist = escola_info.get('distrito') or 'Massinga'
    disc_nome = (disc_info.get('nome') or 'Disciplina').upper()
    disc_cod = disc_info.get('codigo') or disc_nome[:3]
    ano_letivo = turma_info.get('ano_letivo') or '2026'
    turma_nome = turma_info.get('nome') or 'Turma'
    grau_ano = turma_info.get('grau_ano') or ''
    turno = turma_info.get('turno') or 'MANHÃ'
    sala = turma_info.get('sala') or '-'
    ef_h = ef_info.get('h', 0)
    ef_m = ef_info.get('m', 0)
    ef_tot = ef_info.get('total', len(alunos))
    prof_nome = f"{prof_info.get('nome') or ''} {prof_info.get('apelido') or ''}".strip() or 'Professor'
    prof_tel = prof_info.get('telefone') or '-'
    dt_nome = dt_info.get('nome') or '-'

    # Cabeçalho Institucional Oficial
    p1 = doc.add_paragraph()
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.paragraph_format.space_after = Pt(1)
    r1 = p1.add_run("REPÚBLICA DE MOÇAMBIQUE — MINISTÉRIO DA EDUCAÇÃO E DESENVOLVIMENTO HUMANO")
    aplicar_fonte_times(r1, pt_size=10.5, bold=True)

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.space_after = Pt(1)
    r2 = p2.add_run(f"DIRECÇÃO PROVINCIAL DA EDUCAÇÃO — {prov.upper()} | SDEJT DE {dist.upper()} — {esc_nome}")
    aplicar_fonte_times(r2, pt_size=9.5, bold=True)

    p3 = doc.add_paragraph()
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p3.paragraph_format.space_after = Pt(1)
    r3 = p3.add_run(f"CADERNETA DE AVALIAÇÃO CONTÍNUA DO PROFESSOR — DISCIPLINA: {disc_nome} ({disc_cod})")
    aplicar_fonte_times(r3, pt_size=10, bold=True)

    p4 = doc.add_paragraph()
    p4.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p4.paragraph_format.space_after = Pt(4)
    r4 = p4.add_run(
        f"Ano Lectivo: {ano_letivo} | Classe: {grau_ano} | Turma: {turma_nome} | Turno: {turno} | Sala: {sala} | "
        f"Efectivo: H={ef_h}, M={ef_m}, HM={ef_tot} | Docente: {prof_nome} ({prof_tel}) | DT: {dt_nome}"
    )
    aplicar_fonte_times(r4, pt_size=8.0)

    # 28 colunas
    headers = [
        'Nº', 'Nome Completo do Aluno', 'Gén',
        '1º 1ªA', '1º 2ªA', '1º 3ªA', '1º MAP', '1º MAS', '1º AT', '1º MT', '1º Cp',
        '2º 1ªA', '2º 2ªA', '2º 3ªA', '2º MAP', '2º MAS', '2º AT', '2º MT', '2º Cp',
        '3º 1ªA', '3º 2ªA', '3º 3ªA', '3º MAP', '3º MAS', '3º AT', '3º MT', '3º Cp',
        'MFD'
    ]
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.style = 'Table Grid'
    aplicar_cant_split_tabela(t)

    for c_i, h in enumerate(headers):
        p = t.rows[0].cells[c_i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        aplicar_fonte_times(r, pt_size=6.0, bold=True)
        set_cell_shading(t.rows[0].cells[c_i], '1E3A8A')
        r.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

    def fmt_n(val):
        if val is None or val == '' or val == '-':
            return '-'
        try:
            f = float(val)
            return str(round(f, 1) if f % 1 != 0 else int(f))
        except (ValueError, TypeError):
            return str(val)

    for idx, al in enumerate(alunos, start=1):
        row = t.add_row()
        t1 = al.get('t1') or {}
        t2 = al.get('t2') or {}
        t3 = al.get('t3') or {}
        nome_c = f"{al.get('nome') or ''} {al.get('apelido') or ''}".strip()
        vals = [
            str(al.get('numero') or idx),
            nome_c,
            str(al.get('genero') or 'M'),
            fmt_n(t1.get('t1')), fmt_n(t1.get('t2')), fmt_n(t1.get('t3')), fmt_n(t1.get('map')), fmt_n(t1.get('mas')), fmt_n(t1.get('at')), fmt_n(t1.get('mt')), str(t1.get('comportamento') or '-'),
            fmt_n(t2.get('t1')), fmt_n(t2.get('t2')), fmt_n(t2.get('t3')), fmt_n(t2.get('map')), fmt_n(t2.get('mas')), fmt_n(t2.get('at')), fmt_n(t2.get('mt')), str(t2.get('comportamento') or '-'),
            fmt_n(t3.get('t1')), fmt_n(t3.get('t2')), fmt_n(t3.get('t3')), fmt_n(t3.get('map')), fmt_n(t3.get('mas')), fmt_n(t3.get('at')), fmt_n(t3.get('mt')), str(t3.get('comportamento') or '-'),
            fmt_n(al.get('mfd'))
        ]
        for c_i, v in enumerate(vals):
            p = row.cells[c_i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if c_i == 1 else WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(v)
            is_bold = (c_i in (9, 17, 25, 27))
            aplicar_fonte_times(r, pt_size=6.0, bold=is_bold)
            if c_i in (9, 17, 25, 27):
                set_cell_shading(row.cells[c_i], 'F8FAFC')

    stat_cols = [
        't1_t1', 't1_t2', 't1_t3', 't1_map', 't1_mas', 't1_at', 't1_mt', None,
        't2_t1', 't2_t2', 't2_t3', 't2_map', 't2_mas', 't2_at', 't2_mt', None,
        't3_t1', 't3_t2', 't3_t3', 't3_map', 't3_mas', 't3_at', 't3_mt', None,
        'mfd'
    ]

    def _v_doc(col_k, getter, default='-'):
        if not col_k or col_k not in estatisticas:
            return default
        col_st = estatisticas[col_k]
        if (col_st.get('avaliados') or {}).get('total', 0) == 0:
            return default
        return getter(col_st)

    # 1. Linha: Parametro estatistico
    r_hdr = t.add_row()
    r_hdr.cells[0].merge(r_hdr.cells[27])
    p_hdr = r_hdr.cells[0].paragraphs[0]
    p_hdr.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r_run = p_hdr.add_run("Parametro estatistico")
    aplicar_fonte_times(r_run, pt_size=6.5, bold=True)
    set_cell_shading(r_hdr.cells[0], 'E2E8F0')

    # Helper para adicionar linhas estatísticas
    def add_stat_block(lbl, sub_gen, data_vals, text_color=None, bg_color=None, bold=False):
        row = t.add_row()
        row.cells[0].merge(row.cells[1])
        p0 = row.cells[0].paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r0 = p0.add_run(lbl)
        aplicar_fonte_times(r0, pt_size=6.0, bold=True)
        if text_color:
            r0.font.color.rgb = text_color

        p2 = row.cells[2].paragraphs[0]
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r2 = p2.add_run(sub_gen)
        aplicar_fonte_times(r2, pt_size=6.0, bold=bold)
        if text_color:
            r2.font.color.rgb = text_color

        for c_idx, val in enumerate(data_vals, start=3):
            p = row.cells[c_idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(str(val))
            aplicar_fonte_times(r, pt_size=6.0, bold=bold)
            if text_color:
                r.font.color.rgb = text_color

        if bg_color:
            for c_i in range(len(row.cells)):
                set_cell_shading(row.cells[c_i], bg_color)

    COLOR_GREEN = RGBColor(0x05, 0x96, 0x69)
    COLOR_RED = RGBColor(0xDC, 0x26, 0x26)

    # 2. Avaliados (M, F, M+F)
    add_stat_block("Avaliados", "M", [_v_doc(k, lambda s: (s.get('avaliados') or {}).get('h', 0)) for k in stat_cols])
    add_stat_block("", "F", [_v_doc(k, lambda s: (s.get('avaliados') or {}).get('m', 0)) for k in stat_cols])
    add_stat_block("", "M+F", [_v_doc(k, lambda s: (s.get('avaliados') or {}).get('total', 0)) for k in stat_cols], bg_color='E5E7EB', bold=True)

    # 3. Positivos (M, F, M+F)
    add_stat_block("Positivos", "M", [_v_doc(k, lambda s: (s.get('positivas') or {}).get('h', 0)) for k in stat_cols], text_color=COLOR_GREEN)
    add_stat_block("", "F", [_v_doc(k, lambda s: (s.get('positivas') or {}).get('m', 0)) for k in stat_cols], text_color=COLOR_GREEN)
    add_stat_block("", "M+F", [_v_doc(k, lambda s: (s.get('positivas') or {}).get('total', 0)) for k in stat_cols], text_color=COLOR_GREEN, bg_color='D1FAE5', bold=True)

    # 4. % Positivos (M, F, M+F)
    add_stat_block("% Positivos", "M", [_v_doc(k, lambda s: f"{(s.get('positivas') or {}).get('pctH', 0)}%") for k in stat_cols], text_color=COLOR_GREEN)
    add_stat_block("", "F", [_v_doc(k, lambda s: f"{(s.get('positivas') or {}).get('pctM', 0)}%") for k in stat_cols], text_color=COLOR_GREEN)
    add_stat_block("", "M+F", [_v_doc(k, lambda s: f"{(s.get('positivas') or {}).get('pct', 0)}%") for k in stat_cols], text_color=COLOR_GREEN, bg_color='D1FAE5', bold=True)

    # 5. Negativos (M, F, M+F)
    add_stat_block("Negativos", "M", [_v_doc(k, lambda s: (s.get('negativas') or {}).get('h', 0)) for k in stat_cols], text_color=COLOR_RED)
    add_stat_block("", "F", [_v_doc(k, lambda s: (s.get('negativas') or {}).get('m', 0)) for k in stat_cols], text_color=COLOR_RED)
    add_stat_block("", "M+F", [_v_doc(k, lambda s: (s.get('negativas') or {}).get('total', 0)) for k in stat_cols], text_color=COLOR_RED, bg_color='FEE2E2', bold=True)

    # 6. % Negativos (M, F, M+F)
    add_stat_block("% Negativos", "M", [_v_doc(k, lambda s: f"{(s.get('negativas') or {}).get('pctH', 0)}%") for k in stat_cols], text_color=COLOR_RED)
    add_stat_block("", "F", [_v_doc(k, lambda s: f"{(s.get('negativas') or {}).get('pctM', 0)}%") for k in stat_cols], text_color=COLOR_RED)
    add_stat_block("", "M+F", [_v_doc(k, lambda s: f"{(s.get('negativas') or {}).get('pct', 0)}%") for k in stat_cols], text_color=COLOR_RED, bg_color='FEE2E2', bold=True)

    # 7. Faixas
    def add_single_row_stat(lbl, data_vals, bg_color=None, bold=True):
        row = t.add_row()
        row.cells[0].merge(row.cells[2])
        p0 = row.cells[0].paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r0 = p0.add_run(lbl)
        aplicar_fonte_times(r0, pt_size=6.0, bold=bold)

        for c_idx, val in enumerate(data_vals, start=3):
            p = row.cells[c_idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(str(val))
            aplicar_fonte_times(r, pt_size=6.0, bold=bold)

        if bg_color:
            for c_i in range(len(row.cells)):
                set_cell_shading(row.cells[c_i], bg_color)

    faixas_defs = [
        ('0 a 9,4', 'f0_94'),
        ('9,5 a 13,4', 'f95_134'),
        ('13,5 a 16,4', 'f135_164'),
        ('16,5 a 18,4', 'f165_184'),
        ('18,5 a 20', 'f185_20'),
    ]
    for f_lbl, f_prop in faixas_defs:
        add_single_row_stat(f_lbl, [_v_doc(k, lambda s: ((s.get('faixas') or {}).get(f_prop) or {}).get('total', 0)) for k in stat_cols])

    # 8. Média da Coluna
    add_single_row_stat("Média da Coluna", [_v_doc(k, lambda s: s.get('media', 0)) for k in stat_cols], bg_color='DBEAFE', bold=True)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


# ==================== 9. EMISSÃO EM LOTE DA TURMA (DOCX) ====================

def gerar_lote_docx(turma, escola, tipo_documento, alunos_documentos, orientacao='portrait') -> bytes:
    doc = docx.Document()
    configurar_secao_pagina(doc, orientacao=orientacao, margem_pol=0.55)

    p1 = doc.add_paragraph()
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.paragraph_format.space_after = Pt(2)
    r1 = p1.add_run(f"REPÚBLICA DE MOÇAMBIQUE — {escola.nome.upper()}")
    aplicar_fonte_times(r1, pt_size=12, bold=True)

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.space_after = Pt(8)
    r2 = p2.add_run(f"MAPA DE EMISSÃO EM LOTE ({tipo_documento.upper()}) — TURMA {turma.nome} ({turma.grau_ano})")
    aplicar_fonte_times(r2, pt_size=11, bold=True)

    headers = ['Nº', 'Nome Completo do Aluno', 'Matrícula', 'Média Global', 'Situação Pedagógica']
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.style = 'Table Grid'
    aplicar_cant_split_tabela(t)

    for c_i, h in enumerate(headers):
        p = t.rows[0].cells[c_i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        aplicar_fonte_times(r, pt_size=9.5, bold=True)
        set_cell_shading(t.rows[0].cells[c_i], '1E3A8A')
        r.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

    for idx, doc_item in enumerate(alunos_documentos, start=1):
        row = t.add_row()
        al_info = doc_item.get('aluno') or {}
        nome = al_info.get('nomeCompleto') or al_info.get('nome') or 'Aluno'
        mat = al_info.get('matricula') or '-'
        med = doc_item.get('mediaGlobal') or doc_item.get('mediaGeral') or '-'
        sit = doc_item.get('situacaoGlobal') or doc_item.get('resultadoFinal') or 'Aprovado'
        vals = [str(idx), str(nome), str(mat), str(med), str(sit)]
        for c_i, v in enumerate(vals):
            p = row.cells[c_i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if c_i == 1 else WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(v)
            aplicar_fonte_times(r, pt_size=9.0, bold=(c_i in (3, 4)))

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

