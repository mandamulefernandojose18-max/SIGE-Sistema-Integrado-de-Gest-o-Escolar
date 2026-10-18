"""
Serviço de Geração de PDFs Oficiais com ReportLab — SIGE
Gera PDFs com fidelidade absoluta às normas oficiais do MEC (Moçambique)
e ao layout padrão oficial (Certificados, Declarações, Boletins e Pautas).
Tipografia estritamente em Times-Roman, Times-Bold e Times-Italic,
molduras oficiais da página (dupla para certificados, simples para declarações/boletins),
marca d'água semi-transparente do Emblema da República de Moçambique,
pontilhado de preenchimento milimétrico e suporte dinâmico a Portrait/Landscape.
"""
import io
import os
import datetime
import re
import unicodedata
import qrcode
from PIL import Image

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Localização do Emblema Oficial da República de Moçambique
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.abspath(os.path.join(_BASE_DIR, '..', 'assets'))
EMBLEMA_PATH = os.path.join(ASSETS_DIR, 'emblema-mocambique.png')
if not os.path.exists(EMBLEMA_PATH):
    ALT_PATH = os.path.abspath(os.path.join(_BASE_DIR, '../../../../frontend/img/emblema-mocambique.png'))
    if os.path.exists(ALT_PATH):
        EMBLEMA_PATH = ALT_PATH

def obter_id_canonico_disciplina(txt):
    if not txt:
        return ''
    s = unicodedata.normalize('NFKD', str(txt)).encode('ASCII', 'ignore').decode('utf-8').lower().strip()
    words = re.findall(r'[a-z0-9]+', s)
    compact = ''.join(words)

    if (
        'tic' in words or 'tics' in words or compact in ('tic', 'tics') or
        'informatica' in words or 'tecnologiadeinformacao' in compact or
        'tecnologiasdeinformacao' in compact or 'tecnologiasdainformacao' in compact
    ):
        return 'tic'

    if 'matematica' in words or compact.startswith('matematica'):
        if 'aplicada' in words or 'aplicada' in compact:
            return 'matematica_aplicada'
        return 'matematica'

    if ('educacao' in words or 'ed' in words) and ('fisica' in words or 'fis' in words):
        return 'educacao_fisica'

    if 'fisica' in words or compact == 'fisica':
        return 'fisica'

    if (
        (('educacao' in words or 'ed' in words) and ('visual' in words or 'vis' in words)) or
        'desenho' in words or 'geometriadescritiva' in compact or
        compact in ('edvisual', 'ev', 'dgd')
    ):
        return 'educacao_visual'

    if 'filosofia' in words or 'filosofia' in compact:
        return 'filosofia'

    if 'quimica' in words or compact == 'quimica':
        return 'quimica'

    if 'biologia' in words or compact == 'biologia':
        return 'biologia'

    if 'geografia' in words or compact == 'geografia':
        return 'geografia'

    if 'historia' in words or compact == 'historia':
        return 'historia'

    if 'portugues' in words or compact == 'portugues' or compact == 'linguaportuguesa':
        return 'portugues'

    if 'ingles' in words or compact == 'ingles' or compact == 'linguainglesa':
        return 'ingles'

    if 'frances' in words or compact == 'frances' or compact == 'linguafrancesa':
        return 'frances'

    if 'empreendedorismo' in words or 'empreendedorismo' in compact:
        return 'empreendedorismo'

    if 'agropecuaria' in words or 'agropecuaria' in compact or 'agro' in words:
        return 'agropecuaria'

    if 'psicopedagogia' in words or 'psicopedagogia' in compact:
        return 'psicopedagogia'

    return compact

def obter_nome_completo_disciplina(txt):
    if not txt:
        return ''
    id_c = obter_id_canonico_disciplina(txt)
    mapa = {
        'portugues': 'Português',
        'ingles': 'Inglês',
        'frances': 'Francês',
        'historia': 'História',
        'geografia': 'Geografia',
        'biologia': 'Biologia',
        'fisica': 'Física',
        'quimica': 'Química',
        'matematica': 'Matemática',
        'matematica_aplicada': 'Matemática Aplicada',
        'filosofia': 'Introdução à Filosofia',
        'educacao_visual': 'Educação Visual',
        'educacao_fisica': 'Educação Física',
        'tic': 'Tecnologias de Informação e Comunicação',
        'empreendedorismo': 'Noções de Empreendedorismo',
        'agropecuaria': 'Agropecuária',
        'psicopedagogia': 'Psicopedagogia',
        'desenho': 'Desenho e Geometria Descritiva',
    }
    return mapa.get(id_c, str(txt).strip())

def match_disciplina(alvo, candidato):
    id_a = obter_id_canonico_disciplina(alvo)
    id_c = obter_id_canonico_disciplina(candidato)
    if not id_a or not id_c:
        return False
    return id_a == id_c

def gerar_qr_code_image(dados_url: str) -> io.BytesIO:
    qr = qrcode.QRCode(box_size=3, border=1)
    qr.add_data(dados_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

def obter_tamanho_pagina(orientacao='portrait', padrao='portrait'):
    """Retorna o pagesize do ReportLab considerando orientacao explícita ou padrão."""
    ori = (orientacao or padrao).lower()
    if ori in ('landscape', 'horizontal'):
        return landscape(A4)
    return A4

def desenhar_moldura_e_marca_dagua(canvas, doc, moldura='simples', marca_dagua=True):
    """
    Desenha no canvas do ReportLab a moldura periférica oficial e a marca d'água central.
    - moldura='dupla': Borda dupla ornamental oficial para Certificado de Habilitações.
    - moldura='simples': Borda retangular única oficial para Declarações e Boletins.
    """
    canvas.saveState()
    width, height = doc.pagesize

    if moldura == 'dupla':
        # Linha externa mais espessa
        canvas.setStrokeColor(colors.HexColor('#111111'))
        canvas.setLineWidth(2.2)
        canvas.rect(0.8 * cm, 0.8 * cm, width - 1.6 * cm, height - 1.6 * cm)
        # Linha interna mais fina
        canvas.setLineWidth(0.7)
        canvas.rect(0.96 * cm, 0.96 * cm, width - 1.92 * cm, height - 1.92 * cm)
    elif moldura == 'simples':
        canvas.setStrokeColor(colors.HexColor('#222222'))
        canvas.setLineWidth(1.2)
        canvas.rect(0.8 * cm, 0.8 * cm, width - 1.6 * cm, height - 1.6 * cm)

    # Marca d'água suave no centro
    if marca_dagua and os.path.exists(EMBLEMA_PATH):
        try:
            canvas.setFillAlpha(0.08)
            wm_size = 9.5 * cm
            canvas.drawImage(
                EMBLEMA_PATH,
                (width - wm_size) / 2.0,
                (height - wm_size) / 2.0,
                width=wm_size,
                height=wm_size,
                mask='auto',
                preserveAspectRatio=True
            )
        except Exception:
            pass

    canvas.restoreState()

def gerar_cabecalho_minedh(styles, escola_nome, provincia, distrito, compacto=False):
    """Gera o cabeçalho padrão com emblema no topo."""
    elements = []
    img_sz = 1.0 * cm if compacto else 1.3 * cm
    if os.path.exists(EMBLEMA_PATH):
        try:
            elements.append(RLImage(EMBLEMA_PATH, width=img_sz, height=img_sz))
            elements.append(Spacer(1, 0.08 * cm if compacto else 0.15 * cm))
        except Exception:
            pass

    style_center_bold = ParagraphStyle(
        'CenterBold', parent=styles['Normal'], alignment=1,
        fontSize=9.5 if compacto else 11, leading=11.5 if compacto else 14, fontName='Times-Bold'
    )
    style_center = ParagraphStyle(
        'Center', parent=styles['Normal'], alignment=1,
        fontSize=8.5 if compacto else 9.5, leading=10.5 if compacto else 12, fontName='Times-Roman'
    )

    prov_str = (provincia or 'Inhambane').upper()
    dist_str = (distrito or 'Massinga').upper()

    elements.append(Paragraph("REPÚBLICA DE MOÇAMBIQUE", style_center_bold))
    elements.append(Paragraph("MINISTÉRIO DA EDUCAÇÃO E DESENVOLVIMENTO HUMANO", style_center_bold))
    elements.append(Paragraph(f"DIRECÇÃO PROVINCIAL DA EDUCAÇÃO — {prov_str}", style_center))
    elements.append(Paragraph(f"SERVIÇO DISTRITAL DE EDUCAÇÃO, JUVENTUDE E TECNOLOGIA DE {dist_str}", style_center))
    elements.append(Paragraph(escola_nome.upper(), style_center_bold))
    elements.append(Spacer(1, 0.12 * cm if compacto else 0.25 * cm))
    return elements

# ==================== 1. PAUTA OFICIAL DA TURMA (HORIZONTAL / LANDSCAPE) ====================

def gerar_pauta_pdf(turma, escola, periodo, ano_letivo, dados_alunos, disciplinas, orientacao='landscape') -> bytes:
    buffer = io.BytesIO()
    page_size = obter_tamanho_pagina(orientacao, padrao='landscape')
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        rightMargin=0.8 * cm,
        leftMargin=0.8 * cm,
        topMargin=0.7 * cm,
        bottomMargin=1.0 * cm
    )
    styles = getSampleStyleSheet()
    elements = []

    # 1. Emblema e Cabeçalho Oficial no Topo
    if os.path.exists(EMBLEMA_PATH):
        try:
            elements.append(RLImage(EMBLEMA_PATH, width=1.3 * cm, height=1.3 * cm))
            elements.append(Spacer(1, 0.1 * cm))
        except Exception:
            pass

    style_hdr_rep = ParagraphStyle('PHdrRep', alignment=1, fontSize=11, leading=13, fontName='Times-Bold')
    style_hdr_gov = ParagraphStyle('PHdrGov', alignment=1, fontSize=8.5, leading=11, fontName='Times-Roman')
    style_hdr_esc = ParagraphStyle('PHdrEsc', alignment=1, fontSize=11, leading=13, fontName='Times-Bold')

    prov_str = (getattr(escola, 'provincia', '') or 'Inhambane').upper()
    dist_str = (getattr(escola, 'distrito', '') or 'Morrumbene').upper()
    esc_nome = (getattr(escola, 'nome', '') or 'Escola Secundária').upper()

    elements.append(Paragraph("REPÚBLICA DE MOÇAMBIQUE", style_hdr_rep))
    elements.append(Paragraph(f"GOVERNO DA PROVÍNCIA DE {prov_str} | DISTRITO DE {dist_str}", style_hdr_gov))
    elements.append(Paragraph(esc_nome, style_hdr_esc))
    elements.append(Spacer(1, 0.15 * cm))

    # Título da Pauta a Roxo/Índigo (#4338ca)
    style_pauta_title = ParagraphStyle(
        'PPautaTitle', alignment=1, fontSize=11.5, leading=14, fontName='Times-Bold',
        textColor=colors.HexColor('#4338ca')
    )
    elements.append(Paragraph(f"PAUTA OFICIAL DE APROVEITAMENTO PEDAGÓGICO — ANO LECTIVO {ano_letivo or 2026}", style_pauta_title))

    # Subtítulo com dados da Turma
    dt_nome = turma.director_turma.nome if getattr(turma, 'director_turma', None) else "Manuel"
    turma_nome = turma.nome if getattr(turma, 'nome', None) else '10ª Classe A'
    grau_ano = turma.grau_ano if getattr(turma, 'grau_ano', None) else '10ª Classe'
    turno = turma.turno if getattr(turma, 'turno', None) else 'MANHA'

    style_pauta_sub = ParagraphStyle('PPautaSub', alignment=1, fontSize=8.5, leading=11, fontName='Times-Roman')
    elements.append(Paragraph(f"Turma: <b>{turma_nome}</b> | Classe: <b>{grau_ano}</b> | Turno: <b>{turno}</b> | Director de Turma: <b>{dt_nome}</b>", style_pauta_sub))
    # Cabeçalho deve estar a 2cm antes do conteúdo
    elements.append(Spacer(1, 2.0 * cm))

    # 2. Tabela Oficial da Pauta em Múltiplos Níveis
    sh_nome = ParagraphStyle('HN', fontName='Times-Bold', fontSize=8, leading=9.5, alignment=0)
    sh_gen = ParagraphStyle('HG', fontName='Times-Bold', fontSize=7.5, leading=9, alignment=1)
    # Aumentar tamanho das letras na parte das disciplinas (sem abreviar)
    sh_disc = ParagraphStyle('HD', fontName='Times-Bold', fontSize=8.5, leading=10, alignment=1, textColor=colors.HexColor('#4338ca'))
    sh_meds = ParagraphStyle('HM', fontName='Times-Bold', fontSize=8, leading=9.5, alignment=1)
    sh_white = ParagraphStyle('HW', fontName='Times-Bold', fontSize=8, leading=9.5, alignment=1, textColor=colors.white)
    sh_sub = ParagraphStyle('HS', fontName='Times-Roman', fontSize=7, leading=8.5, alignment=1)

    st_nome = ParagraphStyle('TN', fontName='Times-Bold', fontSize=7.5, leading=9, alignment=0)
    st_c = ParagraphStyle('TC', fontName='Times-Roman', fontSize=8, leading=9.5, alignment=1)
    st_red = ParagraphStyle('TR', fontName='Times-Bold', fontSize=8, leading=9.5, alignment=1, textColor=colors.HexColor('#dc2626'))
    st_bold = ParagraphStyle('TB', fontName='Times-Bold', fontSize=8, leading=9.5, alignment=1)
    st_res_rep = ParagraphStyle('TRRep', fontName='Times-Bold', fontSize=8, leading=9.5, alignment=1, textColor=colors.HexColor('#dc2626'))
    st_res_apr = ParagraphStyle('TRApr', fontName='Times-Bold', fontSize=8, leading=9.5, alignment=1, textColor=colors.HexColor('#111827'))

    # Header Row 1
    row1 = [
        Paragraph('Nome Completo do Aluno', sh_nome),
        Paragraph('Gén', sh_gen)
    ]
    for d in disciplinas:
        # Disciplinas sem abreviar
        raw_disc = getattr(d, 'nome', None) or getattr(d, 'codigo', None) or str(d)
        nome_disc_completo = obter_nome_completo_disciplina(raw_disc)
        row1.extend([Paragraph(nome_disc_completo, sh_disc), '', '', ''])

    row1.extend([
        Paragraph('Médias Trimestrais', sh_meds), '', '',
        Paragraph('Disciplinas Negativas', sh_meds), '', '', '',
        Paragraph('Média Geral', sh_white),
        Paragraph('Resultado', sh_white)
    ])

    # Header Row 2
    row2 = ['', '']
    for _ in disciplinas:
        row2.extend([
            Paragraph('1º', sh_sub), Paragraph('2º', sh_sub), Paragraph('3º', sh_sub), Paragraph('MFD', sh_sub)
        ])
    row2.extend([
        Paragraph('1º', sh_sub), Paragraph('2º', sh_sub), Paragraph('3º', sh_sub),
        Paragraph('1º', sh_sub), Paragraph('2º', sh_sub), Paragraph('3º', sh_sub), Paragraph('Total', sh_sub),
        '', ''
    ])

    table_data = [row1, row2]

    # Style do Table
    table_styles = [
        ('SPAN', (0, 0), (0, 1)),
        ('SPAN', (1, 0), (1, 1)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#94a3b8')),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]

    col_idx = 2
    for _ in disciplinas:
        table_styles.append(('SPAN', (col_idx, 0), (col_idx + 3, 0)))
        table_styles.append(('BACKGROUND', (col_idx, 0), (col_idx + 3, 0), colors.HexColor('#eef2ff')))
        table_styles.append(('BACKGROUND', (col_idx + 3, 1), (col_idx + 3, -1), colors.HexColor('#f8fafc')))
        col_idx += 4

    # Médias Trimestrais SPAN
    table_styles.append(('SPAN', (col_idx, 0), (col_idx + 2, 0)))
    table_styles.append(('BACKGROUND', (col_idx, 0), (col_idx + 2, 0), colors.HexColor('#f1f5f9')))
    col_idx += 3

    # Disciplinas Negativas SPAN
    table_styles.append(('SPAN', (col_idx, 0), (col_idx + 3, 0)))
    table_styles.append(('BACKGROUND', (col_idx, 0), (col_idx + 3, 0), colors.HexColor('#f1f5f9')))
    col_idx += 4

    # Média Geral SPAN
    med_col = col_idx
    table_styles.append(('SPAN', (med_col, 0), (med_col, 1)))
    table_styles.append(('BACKGROUND', (med_col, 0), (med_col, 1), colors.HexColor('#4f46e5')))

    # Resultado SPAN
    res_col = col_idx + 1
    table_styles.append(('SPAN', (res_col, 0), (res_col, 1)))
    table_styles.append(('BACKGROUND', (res_col, 0), (res_col, 1), colors.HexColor('#1e293b')))

    # Linhas de Alunos
    for a in dados_alunos:
        nome_completo = a.get('nomeCompleto') or a.get('nome', '')
        gen = (a.get('genero') or 'M').upper()
        # Badges para Gênero: M (escuro #334155) / F (ciano #0ea5e9)
        gen_color = '#0284c7' if gen.startswith('F') else '#334155'
        gen_html = f'<font color="{gen_color}"><b>{gen[:1]}</b></font>'

        row = [
            Paragraph(nome_completo, st_nome),
            Paragraph(gen_html, st_c)
        ]

        nd_dict = a.get('notasDisciplinas', {})
        for d in disciplinas:
            d_id = str(getattr(d, 'id', d))
            d_cod = str(getattr(d, 'codigo', d))
            d_nome = str(getattr(d, 'nome', d))
            nd = nd_dict.get(d_cod) or nd_dict.get(d_id) or nd_dict.get(d_nome) or {}

            for chave in ['t1', 't2', 't3', 'mfd']:
                val = nd.get(chave)
                if val is not None and str(val) not in ('-', '---', ''):
                    try:
                        num = round(float(val))
                        val_style = st_red if num < 10 else st_c
                        row.append(Paragraph(str(num), val_style))
                    except Exception:
                        row.append(Paragraph(str(val), st_c))
                else:
                    row.append(Paragraph('-', st_c))

        meds = a.get('mediasTrimestrais', {})
        for m_k in ['t1', 't2', 't3']:
            mv = meds.get(m_k)
            if mv is not None and str(mv) not in ('-', '---', ''):
                try:
                    num = round(float(mv))
                    m_style = st_red if num < 10 else st_c
                    row.append(Paragraph(str(num), m_style))
                except Exception:
                    row.append(Paragraph(str(mv), st_c))
            else:
                row.append(Paragraph('-', st_c))

        negs = a.get('negativas', {})
        for n_k in ['t1', 't2', 't3', 'fimDoAno']:
            nv = negs.get(n_k, 0)
            if nv is not None and str(nv) not in ('-', '---', ''):
                try:
                    num = int(nv)
                    n_style = st_red if num > 0 else st_c
                    row.append(Paragraph(str(num), n_style))
                except Exception:
                    row.append(Paragraph(str(nv), st_c))
            else:
                row.append(Paragraph('0', st_c))

        mg = a.get('media_geral') if a.get('media_geral') is not None else a.get('mediaFinalGeral')
        if mg is not None and str(mg) not in ('-', '---', ''):
            try:
                num = round(float(mg))
                mg_style = st_red if num < 10 else st_bold
                row.append(Paragraph(str(num), mg_style))
            except Exception:
                row.append(Paragraph(str(mg), st_bold))
        else:
            row.append(Paragraph('-', st_bold))

        res_str = str(a.get('resultado') or a.get('resultadoFinal', 'Aprovado')).strip()
        if res_str in ('Reprovado', 'R', 'Excluído'):
            row.append(Paragraph('Reprovado', st_res_rep))
        elif res_str in ('Aprovado', 'A'):
            row.append(Paragraph('Aprovado', st_res_apr))
        else:
            row.append(Paragraph(res_str, st_c))

        table_data.append(row)

    # Cálculo dinâmico das colunas para A4 Landscape (28.1cm total útil)
    util_cm = 28.1
    w_nome = 5.2 * cm
    w_gen = 0.8 * cm
    w_med_trim = 0.8 * cm  # 3 cols = 2.4cm
    w_neg = 0.7 * cm       # 4 cols = 2.8cm
    w_med_geral = 1.1 * cm
    w_res = 1.8 * cm

    espaco_fixo = w_nome + w_gen + (w_med_trim * 3) + (w_neg * 4) + w_med_geral + w_res
    resto_discs = util_cm * cm - espaco_fixo
    n_discs = max(len(disciplinas), 1)
    w_subdisc = max(0.65 * cm, resto_discs / (n_discs * 4))

    col_widths = [w_nome, w_gen]
    for _ in disciplinas:
        col_widths.extend([w_subdisc, w_subdisc, w_subdisc, w_subdisc])
    col_widths.extend([w_med_trim, w_med_trim, w_med_trim])
    col_widths.extend([w_neg, w_neg, w_neg, w_neg])
    col_widths.extend([w_med_geral, w_res])

    t = Table(table_data, colWidths=col_widths, repeatRows=2)
    t.setStyle(TableStyle(table_styles))
    elements.append(t)
    elements.append(Spacer(1, 0.5 * cm))

    # Assinaturas da Pauta (3 colunas: DT, DAP, Diretor)
    dap_nome = getattr(escola, 'dap_nome', 'O Director Pedagógico (DAP)') or 'O Director Pedagógico (DAP)'
    dir_nome = getattr(escola, 'director_nome', 'O Director da Escola') or 'O Director da Escola'

    sig_data = [
        ["______________________________", "______________________________", "______________________________"],
        ["O Director de Turma", "O Director Pedagógico (DAP)", "O Director da Escola"],
        [dt_nome, dap_nome, dir_nome]
    ]
    w_sig = (util_cm / 3.0) * cm
    t_sig = Table(sig_data, colWidths=[w_sig, w_sig, w_sig])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
    ]))
    elements.append(KeepTogether(t_sig))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


# ==================== 1.1 PAUTA DE EXAMES OFICIAIS (LANDSCAPE) ====================

def gerar_pauta_exames_pdf(dados_pauta, escola, ano_letivo='2026', orientacao='landscape') -> bytes:
    """
    Gera o PDF oficial da Pauta de Exames no formato A4 Paisagem (Landscape)
    respeitando integralmente a estrutura curricular e o modelo oficial do MEC.
    """
    buffer = io.BytesIO()
    page_size = obter_tamanho_pagina(orientacao, padrao='landscape')
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        rightMargin=0.6 * cm,
        leftMargin=0.6 * cm,
        topMargin=0.6 * cm,
        bottomMargin=0.8 * cm
    )
    elements = []

    # Emblema e Cabeçalho Oficial
    if os.path.exists(EMBLEMA_PATH):
        try:
            elements.append(RLImage(EMBLEMA_PATH, width=1.1 * cm, height=1.1 * cm))
            elements.append(Spacer(1, 0.1 * cm))
        except Exception:
            pass

    style_hdr_rep = ParagraphStyle('PEHdrRep', alignment=1, fontSize=10, leading=12, fontName='Times-Bold')
    style_hdr_esc = ParagraphStyle('PEHdrEsc', alignment=1, fontSize=11, leading=13, fontName='Times-Bold')
    style_pauta_title = ParagraphStyle('PEPautaTitle', alignment=1, fontSize=11, leading=13, fontName='Times-Bold', textColor=colors.HexColor('#1e3a8a'))
    style_pauta_sub = ParagraphStyle('PEPautaSub', alignment=1, fontSize=8, leading=10, fontName='Times-Roman')

    esc_nome = (getattr(escola, 'nome', '') or 'ESCOLA SECUNDÁRIA').upper()
    turma_info = dados_pauta.get('turma', {})
    turma_nome = turma_info.get('nome', 'Turma')
    grau_ano = turma_info.get('grau_ano', '10ª Classe')
    area_nome = turma_info.get('area', '')

    elements.append(Paragraph("REPÚBLICA DE MOÇAMBIQUE", style_hdr_rep))
    elements.append(Paragraph(f"ESCOLA {esc_nome}", style_hdr_esc))
    elements.append(Spacer(1, 0.1 * cm))

    sub_info = f"Classe/Área ou Secção: <b>{grau_ano} {('/ ' + area_nome) if area_nome else ''}</b> &nbsp;&nbsp;|&nbsp;&nbsp; <b>PAUTA DE EXAMES / Ano {ano_letivo}</b> &nbsp;&nbsp;|&nbsp;&nbsp; Turma: <b>{turma_nome}</b>"
    elements.append(Paragraph(sub_info, style_pauta_title))
    elements.append(Spacer(1, 0.3 * cm))

    # Tabela da Pauta
    disciplinas_com_exame = dados_pauta.get('disciplinas_com_exame', [])
    disciplinas_sem_exame = dados_pauta.get('disciplinas_sem_exame', [])
    alunos = dados_pauta.get('alunos', [])

    sh_bold_w = ParagraphStyle('SHBW', fontName='Times-Bold', fontSize=6.5, leading=7.5, alignment=1, textColor=colors.white)
    sh_sub = ParagraphStyle('SHSub', fontName='Times-Bold', fontSize=6, leading=7, alignment=1, textColor=colors.HexColor('#1e293b'))
    st_c = ParagraphStyle('STC', fontName='Times-Roman', fontSize=6.5, leading=7.5, alignment=1)
    st_c_bold = ParagraphStyle('STCB', fontName='Times-Bold', fontSize=6.5, leading=7.5, alignment=1)
    st_red = ParagraphStyle('STR', fontName='Times-Bold', fontSize=6.5, leading=7.5, alignment=1, textColor=colors.HexColor('#dc2626'))
    st_green = ParagraphStyle('STG', fontName='Times-Bold', fontSize=6.5, leading=7.5, alignment=1, textColor=colors.HexColor('#166534'))
    st_nome = ParagraphStyle('STN', fontName='Times-Roman', fontSize=6.5, leading=7.5, alignment=0)

    # Linhas de cabeçalho (3 linhas)
    row_hdr1 = [
        Paragraph("Nº Ordem", sh_bold_w),
        Paragraph("Nº Candidato", sh_bold_w),
        Paragraph("Nome do Aluno", sh_bold_w),
        Paragraph("Gén.", sh_bold_w),
        Paragraph("Turma", sh_bold_w),
    ]
    row_hdr2 = ["", "", "", "", ""]
    row_hdr3 = ["", "", "", "", ""]

    table_styles = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('BACKGROUND', (0, 1), (-1, 2), colors.HexColor('#f1f5f9')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (-1, -1), 1),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        # Merge colunas fixas 0 a 4 através das linhas 0 a 2
        ('SPAN', (0, 0), (0, 2)),
        ('SPAN', (1, 0), (1, 2)),
        ('SPAN', (2, 0), (2, 2)),
        ('SPAN', (3, 0), (3, 2)),
        ('SPAN', (4, 0), (4, 2)),
    ]

    curr_col = 5
    # Disciplinas com Exame
    for d in disciplinas_com_exame:
        d_nome_curto = d['nome'].replace('Língua ', '').replace('Educação ', 'Ed. ')
        row_hdr1.extend([Paragraph(d_nome_curto, sh_bold_w), "", "", ""])
        table_styles.append(('SPAN', (curr_col, 0), (curr_col + 3, 0)))

        row_hdr2.extend([
            Paragraph("de", sh_sub),
            Paragraph("Frequência", sh_sub),
            Paragraph("Exame", sh_sub),
            Paragraph("Média", sh_sub),
        ])
        row_hdr3.extend([
            Paragraph("Proven.", sh_sub),
            Paragraph("", sh_sub),
            Paragraph("1ª / 2ª", sh_sub),
            Paragraph("", sh_sub),
        ])
        curr_col += 4

    # Disciplinas sem Exame
    for d in disciplinas_sem_exame:
        d_nome_curto = d['nome'].replace('Língua ', '').replace('Educação ', 'Ed. ')
        row_hdr1.append(Paragraph(d_nome_curto, sh_bold_w))
        row_hdr2.append(Paragraph("Frequência", sh_sub))
        row_hdr3.append(Paragraph("Proven.", sh_sub))
        curr_col += 1

    # Resultado Final
    row_hdr1.extend([Paragraph("RESULTADO FINAL", sh_bold_w), "", ""])
    table_styles.append(('SPAN', (curr_col, 0), (curr_col + 2, 0)))

    row_hdr2.extend([
        Paragraph("Aprovado(a)", sh_sub),
        Paragraph("MF", sh_sub),
        Paragraph("Disciplina(s) que Reprovou", sh_sub),
    ])
    row_hdr3.extend(["", "", ""])
    table_styles.append(('SPAN', (curr_col, 1), (curr_col, 2)))
    table_styles.append(('SPAN', (curr_col + 1, 1), (curr_col + 1, 2)))
    table_styles.append(('SPAN', (curr_col + 2, 1), (curr_col + 2, 2)))

    table_data = [row_hdr1, row_hdr2, row_hdr3]

    # Inserir alunos
    for r_idx, aluno in enumerate(alunos, start=3):
        row = [
            Paragraph(str(aluno.get('numero', '')), st_c),
            Paragraph(str(aluno.get('candidato', '')), st_c),
            Paragraph(str(aluno.get('nome', '')), st_nome),
            Paragraph(str(aluno.get('genero', '')), st_c),
            Paragraph(str(aluno.get('turma', '')), st_c),
        ]

        disc_map = aluno.get('disciplinas', {})
        for d in disciplinas_com_exame:
            d_data = disc_map.get(d['id']) or {}
            v_freq = d_data.get('frequencia', '-')
            v_e1 = d_data.get('exame_1epoca')
            v_e2 = d_data.get('exame_2epoca')
            v_med = d_data.get('media', '-')

            e_str = f"{v_e2}" if v_e2 is not None else (f"{v_e1}" if v_e1 is not None else "-")

            row.append(Paragraph(str(v_freq), st_c))
            row.append(Paragraph(str(v_freq), st_c))
            row.append(Paragraph(e_str, st_c))

            if isinstance(v_med, (int, float)):
                m_st = st_green if v_med >= 9.5 else st_red
                row.append(Paragraph(str(v_med), m_st))
            else:
                row.append(Paragraph(str(v_med), st_c_bold))

        for d in disciplinas_sem_exame:
            d_data = disc_map.get(d['id']) or {}
            v_freq = d_data.get('frequencia', '-')
            if isinstance(v_freq, (int, float)):
                f_st = st_green if v_freq >= 9.5 else st_red
                row.append(Paragraph(str(v_freq), f_st))
            else:
                row.append(Paragraph(str(v_freq), st_c))

        res_info = aluno.get('resultado_final', {})
        res_aprov = str(res_info.get('aprovado', '') or 'Pendente').strip()
        res_mf = res_info.get('mf', '-')
        res_rep = str(res_info.get('disciplinas_reprovou', '---') or '---')

        ap_st = st_green if 'Aprovad' in res_aprov else (st_red if 'Reprovad' in res_aprov or 'Excluíd' in res_aprov else st_c_bold)
        row.append(Paragraph(res_aprov, ap_st))
        row.append(Paragraph(str(res_mf), st_c_bold))
        row.append(Paragraph(res_rep, ParagraphStyle('SRep', fontName='Times-Roman', fontSize=5.5, leading=6.5, alignment=0)))

        # Zebra striping
        if (r_idx % 2) == 0:
            table_styles.append(('BACKGROUND', (0, r_idx), (-1, r_idx), colors.HexColor('#f8fafc')))

        table_data.append(row)

    # Larguras das colunas
    total_cols = len(row_hdr1)
    w_fixed = [0.8 * cm, 1.3 * cm, 4.0 * cm, 0.6 * cm, 1.1 * cm]
    w_res = [1.5 * cm, 0.7 * cm, 2.5 * cm]
    espaco_discs = 28.5 * cm - sum(w_fixed) - sum(w_res)
    n_cols_discs = (len(disciplinas_com_exame) * 4) + len(disciplinas_sem_exame)
    w_col_disc = max(0.42 * cm, espaco_discs / max(n_cols_discs, 1))

    col_widths = list(w_fixed)
    for _ in range(n_cols_discs):
        col_widths.append(w_col_disc)
    col_widths.extend(w_res)

    t = Table(table_data, colWidths=col_widths, repeatRows=3)
    t.setStyle(TableStyle(table_styles))
    elements.append(t)
    elements.append(Spacer(1, 0.4 * cm))

    # Assinaturas
    dap_nome = getattr(escola, 'dap_nome', 'O Director Pedagógico (DAP)') or 'O Director Pedagógico (DAP)'
    dir_nome = getattr(escola, 'director_nome', 'O Director da Escola') or 'O Director da Escola'
    dt_nome = turma_info.get('director_turma', 'O Director de Turma') or 'O Director de Turma'

    sig_data = [
        ["______________________________", "______________________________", "______________________________"],
        ["O Director de Turma", "O Director Pedagógico (DAP)", "O Director da Escola"],
        [dt_nome, dap_nome, dir_nome]
    ]
    w_sig = (28.5 / 3.0) * cm
    t_sig = Table(sig_data, colWidths=[w_sig, w_sig, w_sig])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    elements.append(KeepTogether(t_sig))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


# ==================== 2. BOLETIM DE APROVEITAMENTO (VERTICAL / PORTRAIT) ====================

def gerar_boletim_pdf(aluno, escola, ano_letivo, notas_disciplinas, orientacao='portrait') -> bytes:
    buffer = io.BytesIO()
    page_size = obter_tamanho_pagina(orientacao, padrao='portrait')
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm
    )
    styles = getSampleStyleSheet()
    elements = []

    # Emblema no Topo Centralizado
    if os.path.exists(EMBLEMA_PATH):
        try:
            elements.append(RLImage(EMBLEMA_PATH, width=1.3 * cm, height=1.3 * cm))
            elements.append(Spacer(1, 0.1 * cm))
        except Exception:
            pass

    style_country = ParagraphStyle('Country', parent=styles['Normal'], alignment=1, fontSize=11.5, leading=13.5, fontName='Times-Bold')
    style_gov = ParagraphStyle('Gov', parent=styles['Normal'], alignment=1, fontSize=9.5, leading=11.5, fontName='Times-Bold')
    style_sdejt = ParagraphStyle('Sdejt', parent=styles['Normal'], alignment=1, fontSize=8.5, leading=11, fontName='Times-Roman')
    style_school = ParagraphStyle('School', parent=styles['Normal'], alignment=1, fontSize=10.5, leading=13, fontName='Times-Bold')
    style_code = ParagraphStyle('Code', parent=styles['Normal'], alignment=1, fontSize=8.5, leading=10.5, fontName='Times-Roman')

    prov = (getattr(escola, 'provincia', 'Inhambane') or 'Inhambane').upper()
    dist = (getattr(escola, 'distrito', 'Morrumbene') or 'Morrumbene').upper()
    escola_nome = escola.nome.upper()
    if not escola_nome.startswith('ESCOLA'):
        escola_nome = f"ESCOLA SECUNDÁRIA DE {escola_nome}"
    codigo_inst = getattr(escola, 'codigo_escola', None) or f"ESC-1001"

    elements.append(Paragraph("REPÚBLICA DE MOÇAMBIQUE", style_country))
    elements.append(Paragraph(f"GOVERNO DA PROVÍNCIA DE {prov}", style_gov))
    elements.append(Paragraph(f"SERVIÇO DISTRITAL DE EDUCAÇÃO, JUVENTUDE E TECNOLOGIA DE {dist}", style_sdejt))
    elements.append(Paragraph(escola_nome, style_school))
    elements.append(Paragraph(f"Código da Instituição: {codigo_inst}", style_code))
    elements.append(Spacer(1, 0.12 * cm))

    # Linha divisória (contida na largura útil de 18.0 cm)
    line_table = Table([[""]], colWidths=[18.0 * cm], rowHeights=[1])
    line_table.setStyle(TableStyle([('LINEBELOW', (0, 0), (-1, -1), 1.5, colors.HexColor('#1e3a8a'))]))
    elements.append(line_table)
    elements.append(Spacer(1, 0.18 * cm))

    # Título do Boletim
    style_title = ParagraphStyle('DocTitle', alignment=1, fontSize=11, leading=13.5, fontName='Times-Bold')
    elements.append(Paragraph(f"BOLETIM DE APROVEITAMENTO ESCOLAR — ANO LECTIVO {ano_letivo or 2026}", style_title))
    elements.append(Spacer(1, 0.45 * cm))

    # Caixa de Dados do Aluno
    turma_nome = aluno.turma.nome if aluno.turma else '10ª Classe A'
    grau_nome = aluno.turma.grau_ano if (aluno.turma and aluno.turma.grau_ano) else '10ª Classe'
    classe_turma = f"{grau_nome} - {turma_nome}" if grau_nome not in turma_nome else turma_nome
    turno_aluno = getattr(aluno.turma, 'turno', 'Manhã') if aluno.turma else 'Manhã'
    if str(turno_aluno).upper() == 'MANHA':
        turno_aluno = 'Manhã'

    style_info = ParagraphStyle('PInfo', fontName='Times-Roman', fontSize=9.5, leading=12)
    info_data = [
        [
            Paragraph(f"<b>Nome do Aluno:</b> {aluno.nome.upper()} {getattr(aluno, 'apelido', '') or ''}", style_info),
            Paragraph(f"<b>Classe / Turma:</b> {classe_turma}", style_info)
        ],
        [
            Paragraph(f"<b>Nº Matrícula:</b> {aluno.matricula}", style_info),
            Paragraph(f"<b>Turno:</b> {turno_aluno}", style_info)
        ]
    ]
    t_info = Table(info_data, colWidths=[10.2 * cm, 7.8 * cm])
    t_info.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#777777')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 0.25 * cm))

    # Tabela de Avaliações contida em 18.0 cm
    style_th = ParagraphStyle('TH', fontName='Times-Bold', fontSize=9, leading=11.5, alignment=1, textColor=colors.HexColor('#0f172a'))
    style_th_disc = ParagraphStyle('THD', fontName='Times-Bold', fontSize=9.5, leading=12, alignment=0, textColor=colors.HexColor('#0f172a'))
    headers = [
        Paragraph('<b>DISCIPLINA</b>', style_th_disc),
        Paragraph('<b>1º TRIM</b>', style_th),
        Paragraph('<b>2º TRIM</b>', style_th),
        Paragraph('<b>3º TRIM</b>', style_th),
        Paragraph('<b>MÉD. ANUAL</b>', style_th),
        Paragraph('<b>SITUAÇÃO</b>', style_th)
    ]
    tabela_data = [headers]

    style_td_disc = ParagraphStyle('TDisc', fontName='Times-Roman', fontSize=10.5, leading=13, alignment=0)
    style_td_nota = ParagraphStyle('TNota', fontName='Times-Roman', fontSize=10, leading=12.5, alignment=1)
    style_td_med = ParagraphStyle('TMed', fontName='Times-Bold', fontSize=10.5, leading=13, alignment=1)

    total_media = 0
    count_disciplinas = 0

    for item in notas_disciplinas:
        nome_d = item.get('nome') or item.get('disciplina') or 'Disciplina'
        t1 = item.get('t1', item.get('trimestre1', '---'))
        t2 = item.get('t2', item.get('trimestre2', '---'))
        t3 = item.get('t3', item.get('trimestre3', '---'))
        med = item.get('media_anual', item.get('mediaFinal', item.get('media_final', '---')))
        sit = item.get('situacao', item.get('resultado', ''))

        if med not in (None, '---', '-', ''):
            try:
                med_val = float(med)
                total_media += med_val
                count_disciplinas += 1
                if not sit:
                    sit = 'Aprovado' if med_val >= 9.5 else 'Reprovado'
            except (ValueError, TypeError):
                pass

        sit_color = colors.HexColor('#dc2626') if (sit in ('Reprovado', 'R')) else colors.HexColor('#111827')
        style_sit = ParagraphStyle('Sit', fontName='Times-Bold', fontSize=10, leading=12.5, alignment=1, textColor=sit_color)

        tabela_data.append([
            Paragraph(nome_d, style_td_disc),
            Paragraph(str(t1 if t1 is not None else '---'), style_td_nota),
            Paragraph(str(t2 if t2 is not None else '---'), style_td_nota),
            Paragraph(str(t3 if t3 is not None else '---'), style_td_nota),
            Paragraph(str(med if med is not None else '---'), style_td_med),
            Paragraph(str(sit if sit else '---'), style_sit)
        ])

    # Rodapé da Tabela: Linha da MÉDIA GLOBAL DO PERÍODO
    if count_disciplinas > 0:
        media_global_num = round(total_media / count_disciplinas)
        sit_global_txt = 'Aprovado' if media_global_num >= 9.5 else 'Reprovado'
    else:
        media_global_num = '---'
        sit_global_txt = '---'

    style_foot_lbl = ParagraphStyle('FLbl', fontName='Times-Bold', fontSize=9.5, leading=12, alignment=0)
    style_foot_val = ParagraphStyle('FVal', fontName='Times-Bold', fontSize=10, leading=12, alignment=1)
    style_foot_sit = ParagraphStyle('FSit', fontName='Times-Bold', fontSize=9.5, leading=12, alignment=1, textColor=colors.HexColor('#111827') if sit_global_txt == 'Aprovado' else colors.HexColor('#dc2626'))

    tabela_data.append([
        Paragraph('MÉDIA GLOBAL DO PERÍODO', style_foot_lbl),
        Paragraph('---', style_td_nota),
        Paragraph('---', style_td_nota),
        Paragraph('---', style_td_nota),
        Paragraph(str(media_global_num), style_foot_val),
        Paragraph(sit_global_txt, style_foot_sit)
    ])

    t_notas = Table(tabela_data, colWidths=[6.5 * cm, 2.3 * cm, 2.3 * cm, 2.3 * cm, 2.3 * cm, 2.3 * cm])
    t_notas.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#cbd5e1')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#64748b')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(t_notas)
    elements.append(Spacer(1, 0.25 * cm))

    # Decisão do Conselho
    if count_disciplinas > 0:
        decisao_texto = f"<b>Decisão do Conselho:</b> Resultado pedagógico do aluno: <b>{sit_global_txt}</b> com média global de <b>{media_global_num}</b> valores."
    else:
        decisao_texto = "<b>Decisão do Conselho:</b> O aluno ainda não possui avaliações concluídas na caderneta."

    style_dec = ParagraphStyle('Dec', fontName='Times-Roman', fontSize=9.5, leading=13)
    elements.append(Paragraph(decisao_texto, style_dec))
    elements.append(Spacer(1, 0.6 * cm))

    # Assinaturas Oficiais (O Director de Turma | O Director da Escola)
    sig_data = [
        ["__________________________________", "__________________________________"],
        ["O Director de Turma", "O Director da Escola"],
        ["", getattr(escola, 'director_nome', 'A Direcção')]
    ]
    t_sig = Table(sig_data, colWidths=[9.0 * cm, 9.0 * cm])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(KeepTogether(t_sig))

    # Compilação com moldura simples e marca d'água
    doc.build(
        elements,
        onFirstPage=lambda c, d: desenhar_moldura_e_marca_dagua(c, d, 'simples', True),
        onLaterPages=lambda c, d: desenhar_moldura_e_marca_dagua(c, d, 'simples', True)
    )
    buffer.seek(0)
    return buffer.getvalue()

# ==================== 3. DECLARAÇÃO COM NOTAS (VERTICAL / PORTRAIT) ====================

def gerar_declaracao_pdf(aluno, escola, ano_letivo, notas_disciplinas, media_global=None, director_nome=None, director_carreira=None, orientacao='portrait') -> bytes:
    buffer = io.BytesIO()
    page_size = obter_tamanho_pagina(orientacao, padrao='portrait')
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm
    )
    styles = getSampleStyleSheet()
    elements = []

    # Emblema no Topo Centralizado
    if os.path.exists(EMBLEMA_PATH):
        try:
            elements.append(RLImage(EMBLEMA_PATH, width=1.3 * cm, height=1.3 * cm))
            elements.append(Spacer(1, 0.1 * cm))
        except Exception:
            pass

    prov = (getattr(escola, 'provincia', 'Maputo') or 'Maputo').upper()
    escola_nome = escola.nome.upper()
    if not escola_nome.startswith('ESCOLA'):
        escola_nome = f"ESCOLA SECUNDÁRIA DE {escola_nome}"
    dir_nome = director_nome or getattr(escola, 'director_nome', None) or 'Prof. Dr. António Costa'
    dir_carreira = director_carreira or getattr(escola, 'director_carreira', 'Especialista de Educação')

    style_country = ParagraphStyle('Country', parent=styles['Normal'], alignment=1, fontSize=11, leading=13, fontName='Times-Bold')
    style_gov = ParagraphStyle('Gov', parent=styles['Normal'], alignment=1, fontSize=10, leading=12, fontName='Times-Bold')
    style_dpe = ParagraphStyle('Dpe', parent=styles['Normal'], alignment=1, fontSize=9, leading=11, fontName='Times-Roman')
    style_school = ParagraphStyle('School', parent=styles['Normal'], alignment=1, fontSize=10.5, leading=12.5, fontName='Times-Bold')
    style_title = ParagraphStyle('DocTitle', alignment=1, fontSize=13, leading=15.5, fontName='Times-Bold')

    elements.append(Paragraph("REPÚBLICA DE MOÇAMBIQUE", style_country))
    elements.append(Paragraph(f"GOVERNO DA PROVÍNCIA DE {prov}", style_gov))
    elements.append(Paragraph(f"DIRECÇÃO PROVINCIAL DA EDUCAÇÃO E CULTURA DE {prov}", style_dpe))
    elements.append(Paragraph(escola_nome, style_school))
    elements.append(Spacer(1, 0.12 * cm))
    elements.append(Paragraph("<u>Declaração</u>", style_title))
    elements.append(Spacer(1, 0.5 * cm))

    aluno_nome = f"{aluno.nome} {getattr(aluno, 'apelido', '') or ''}".strip().upper()
    pai = getattr(aluno, 'pai', None) or 'Eduardo Mondlane Jr.'
    mae = getattr(aluno, 'mae', None) or 'Janet Mondlane'
    doc_tipo = getattr(aluno, 'tipo_documento', 'Bilhete de Identidade') or 'Bilhete de Identidade'
    doc_num = getattr(aluno, 'numero_documento', None) or getattr(aluno, 'bi_numero', None) or '110293847591F'
    grau_classe = (aluno.turma.grau_ano if aluno.turma and aluno.turma.grau_ano else getattr(aluno, 'classe', None)) or '10ª Classe'

    corpo_texto = (
        f"Para os devidos efeitos se declara que <b>{aluno_nome}</b>, filho(a) de <b>{pai}</b> e de <b>{mae}</b>, "
        f"portador(a) do <b>{doc_tipo}</b> número <b>{doc_num}</b>, concluiu com aproveitamento a <b>{grau_classe}</b> "
        f"neste estabelecimento de ensino, no ano lectivo de <b>{ano_letivo or 2026}</b>, com as seguintes classificações:"
    )
    style_body = ParagraphStyle('BodyDecl', parent=styles['Normal'], fontSize=10.5, leading=15, alignment=4, fontName='Times-Roman')
    elements.append(Paragraph(corpo_texto, style_body))
    elements.append(Spacer(1, 0.25 * cm))

    # Tabela com as disciplinas do plano curricular da classe/secção do aluno em 2 Colunas estritamente dentro de 18.0 cm
    notas_map = {}
    lista_disc_nomes = []
    for d in (notas_disciplinas or []):
        n = (d.get('disciplina') or d.get('nome') or '').strip()
        if n and n not in lista_disc_nomes:
            lista_disc_nomes.append(n)
        v = d.get('media_anual') if d.get('media_anual') is not None else (d.get('mediaFinal') if d.get('mediaFinal') is not None else d.get('notaFinal'))
        if n and v not in (None, '-', '---'):
            try:
                notas_map[n] = str(round(float(v)))
            except Exception:
                pass

    if not lista_disc_nomes:
        plano = obter_disciplinas_plano_curricular(aluno, escola)
        lista_disc_nomes = [p.get('nome') for p in plano if p.get('nome')]

    def obter_nota_decl(alvo):
        for ch, vl in notas_map.items():
            if match_disciplina(alvo, ch):
                return vl
        return '---'

    meio_decl = (len(lista_disc_nomes) + 1) // 2
    col_esq = lista_disc_nomes[:meio_decl]
    col_dir = lista_disc_nomes[meio_decl:]

    s_name = ParagraphStyle('SN', fontName='Times-Roman', fontSize=11, leading=13.5)
    s_dots = ParagraphStyle('SD', fontName='Times-Roman', fontSize=10.5, leading=13.5, alignment=1, textColor=colors.HexColor('#666666'))
    s_val = ParagraphStyle('SV', fontName='Times-Bold', fontSize=11, leading=13.5, alignment=2)

    def criar_subitem_2col(disc, w_col=8.7 * cm):
        nota = obter_nota_decl(disc)
        nota_str = f'( {nota} ) valores' if nota != '---' else '( --- )'
        w1 = 5.6 * cm
        w3 = 2.4 * cm
        w2 = w_col - w1 - w3
        t = Table([[
            Paragraph(disc, s_name),
            Paragraph('....', s_dots),
            Paragraph(nota_str, s_val)
        ]], colWidths=[w1, w2, w3])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 1.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
        ]))
        return t

    rows_2col = []
    for i in range(max(len(col_esq), len(col_dir))):
        d1 = col_esq[i] if i < len(col_esq) else ''
        d2 = col_dir[i] if i < len(col_dir) else ''
        it1 = criar_subitem_2col(d1, 8.7 * cm) if d1 else Paragraph('', s_name)
        it2 = criar_subitem_2col(d2, 8.7 * cm) if d2 else Paragraph('', s_name)
        rows_2col.append([it1, '', it2])

    t_grid = Table(rows_2col, colWidths=[8.8 * cm, 0.4 * cm, 8.8 * cm])
    t_grid.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 1),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    elements.append(t_grid)
    elements.append(Spacer(1, 0.25 * cm))

    # Média global da Classe
    med_val_str = f"( {round(float(media_global))} ) valores." if (media_global not in (None, '-', '---')) else "( --- )"
    style_med = ParagraphStyle('MedDecl', fontName='Times-Bold', fontSize=10.5, leading=13)
    elements.append(Paragraph(f"Média global da Classe: {med_val_str}", style_med))
    elements.append(Spacer(1, 0.2 * cm))

    # Parágrafo do livro do termo de exames
    resultado_str = "Reprovado" if (media_global not in (None, '-', '---') and float(media_global) < 9.5) else "Aprovado"
    fecho_texto = (
        f"Consta no livro do termo de exames sob o número <b>124</b>, folha <b>32</b>, do ano lectivo de <b>{ano_letivo or 2026}</b>, "
        f"que o estudante obteve o resultado de <b>{resultado_str}</b>.<br/>"
        f"Por ser verdade e me haver sido solicitada, mandei passar a presente declaração que vai por mim assinada "
        f"e autenticada com o carimbo a tinta de óleo em uso nesta instituição."
    )
    elements.append(Paragraph(fecho_texto, style_body))
    elements.append(Spacer(1, 0.25 * cm))

    # Datação à direita
    hoje = datetime.date.today().strftime('%d de %B de %Y')
    elements.append(Paragraph(f"Maputo, aos {hoje}", ParagraphStyle('PData', fontName='Times-Roman', fontSize=10, alignment=2)))
    elements.append(Spacer(1, 0.25 * cm))

    # Campos de conferência
    conf_data = [
        [
            Paragraph("Extraído por: ____________________________<br/>Data: _____ / _____ / 2026", ParagraphStyle('C1', fontName='Times-Roman', fontSize=9, leading=12)),
            Paragraph("Conferido por: ____________________________<br/>Data: _____ / _____ / 2026", ParagraphStyle('C2', fontName='Times-Roman', fontSize=9, leading=12))
        ]
    ]
    t_conf = Table(conf_data, colWidths=[9.0 * cm, 9.0 * cm])
    t_conf.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    elements.append(t_conf)
    elements.append(Spacer(1, 0.25 * cm))

    # Assinatura Centralizada do Diretor da Escola
    sig_data = [
        ["O Director da Escola"],
        ["___________________________________"],
        [dir_nome],
        [f"/{dir_carreira}/"]
    ]
    t_sig = Table(sig_data, colWidths=[18.0 * cm])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('FONTNAME', (0, 2), (-1, 2), 'Times-Bold'),
        ('FONTNAME', (0, 3), (-1, 3), 'Times-Italic'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    elements.append(KeepTogether(t_sig))

    # Compilação com moldura simples e marca d'água
    doc.build(
        elements,
        onFirstPage=lambda c, d: desenhar_moldura_e_marca_dagua(c, d, 'simples', True),
        onLaterPages=lambda c, d: desenhar_moldura_e_marca_dagua(c, d, 'simples', True)
    )
    buffer.seek(0)
    return buffer.getvalue()

# ==================== 4. CERTIFICADO DE HABILITAÇÕES (VERTICAL / PORTRAIT) ====================

def gerar_certificado_pdf(aluno, escola, ano_letivo, notas_disciplinas, media_global=None, codigo_autenticidade=None, orientacao='portrait', **kwargs) -> bytes:
    buffer = io.BytesIO()
    page_size = obter_tamanho_pagina(orientacao, padrao='portrait')
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm
    )
    styles = getSampleStyleSheet()
    elements = []

    # Emblema no Topo Centralizado
    if os.path.exists(EMBLEMA_PATH):
        try:
            elements.append(RLImage(EMBLEMA_PATH, width=1.3 * cm, height=1.3 * cm))
            elements.append(Spacer(1, 0.08 * cm))
        except Exception:
            pass

    prov = (getattr(escola, 'provincia', 'Inhambane') or 'Inhambane')
    dist = (getattr(escola, 'distrito', 'Massinga') or 'Massinga')
    escola_nome = escola.nome.upper()
    if not escola_nome.startswith('ESCOLA'):
        escola_nome = f"ESCOLA SECUNDÁRIA DE {escola_nome}"
    dir_nome = kwargs.get('director_nome') or getattr(escola, 'director_nome', None) or 'Prof. Dr. António Costa'
    dir_carreira = kwargs.get('director_carreira') or getattr(escola, 'director_carreira', 'Especialista de Educação')
    chefe_nome = kwargs.get('chefe_secretaria_nome') or getattr(escola, 'chefe_secretaria_nome', 'Dra. Maria Eunice')
    chefe_carreira = kwargs.get('chefe_secretaria_carreira') or getattr(escola, 'chefe_secretaria_carreira', 'Técnica Profissional')

    style_country = ParagraphStyle('Country', parent=styles['Normal'], alignment=1, fontSize=11, leading=13, fontName='Times-Bold')
    style_mec = ParagraphStyle('Mec', parent=styles['Normal'], alignment=1, fontSize=10, leading=12, fontName='Times-Bold')
    style_inece = ParagraphStyle('Inece', parent=styles['Normal'], alignment=1, fontSize=8.5, leading=10.5, fontName='Times-Bold')
    style_school = ParagraphStyle('School', parent=styles['Normal'], alignment=1, fontSize=9.5, leading=11.5, fontName='Times-Roman')
    style_title = ParagraphStyle('DocTitle', alignment=1, fontSize=13, leading=15.5, fontName='Times-Bold')

    elements.append(Paragraph("REPÚBLICA DE MOÇAMBIQUE", style_country))
    elements.append(Paragraph("MINISTÉRIO DA EDUCAÇÃO E CULTURA", style_mec))
    elements.append(Paragraph("INSTITUTO NACIONAL DE EXAMES, CERTIFICAÇÃO E EQUIVALÊNCIA", style_inece))
    elements.append(Paragraph(f"<u>a) {escola_nome}</u>", style_school))
    elements.append(Spacer(1, 0.1 * cm))
    elements.append(Paragraph("<u><b>CERTIFICADO DE HABILITAÇÕES</b></u>", style_title))
    elements.append(Spacer(1, 0.4 * cm))

    aluno_nome = f"{aluno.nome} {getattr(aluno, 'apelido', '') or ''}".strip().upper()
    sexo = 'Feminino' if (getattr(aluno, 'genero', 'M') or '').upper().startswith('F') else 'Masculino'
    nat_dist = getattr(aluno, 'distrito', 'Cidade de Maputo') or 'Cidade de Maputo'
    nat_prov = getattr(aluno, 'provincia', 'Maputo') or 'Maputo'
    pai = getattr(aluno, 'pai', 'Eduardo Mondlane Jr.') or 'Eduardo Mondlane Jr.'
    mae = getattr(aluno, 'mae', 'Janet Mondlane') or 'Janet Mondlane'
    grau_classe = (aluno.turma.grau_ano if aluno.turma and aluno.turma.grau_ano else getattr(aluno, 'classe', None)) or '10ª Classe'
    area = (aluno.turma.area if aluno.turma and aluno.turma.area else getattr(aluno, 'area', 'Geral')) or 'Geral'

    # Formatação de Data de Nascimento
    dia_nasc = '09'
    mes_nasc = 'Julho'
    ano_nasc = '2008'
    if getattr(aluno, 'data_nascimento', None):
        try:
            dn = str(aluno.data_nascimento)
            partes = dn.split('-')
            if len(partes) == 3:
                ano_nasc = partes[0]
                meses_pt = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
                mes_idx = int(partes[1]) - 1
                mes_nasc = meses_pt[mes_idx] if 0 <= mes_idx < 12 else partes[1]
                dia_nasc = str(int(partes[2])).zfill(2)
        except Exception:
            pass

    corpo = (
        f"b) <b>{chefe_nome}</b>, <i>/{chefe_carreira}/</i>, Chefe da secretaria da <b>{escola_nome}</b>, "
        f"distrito de <b>{dist}</b>, província de <b>{prov}</b>, CERTIFICO em cumprimento do despacho exarado em requerimento "
        f"que fica arquivado nesta secretaria que <b>{aluno_nome}</b>, do Sexo <b>{sexo}</b>, natural de <b>{nat_dist}</b>, "
        f"distrito de <b>{nat_dist}</b>, província de <b>{nat_prov}</b>, nascido no dia <b>{dia_nasc} de {mes_nasc} de {ano_nasc}</b>, "
        f"filho/a de <b>{pai}</b> e de <b>{mae}</b>, concluiu nesta escola como aluno c) <b>Interno</b>, "
        f"em <b>Dezembro de {ano_letivo or 2026}</b>, a <b>{grau_classe}</b> na área de <b>{area}</b>, tendo obtido os seguintes resultados:"
    )
    style_body = ParagraphStyle('BodyCert', parent=styles['Normal'], fontSize=10, leading=14.5, alignment=4, fontName='Times-Roman')
    elements.append(Paragraph(corpo, style_body))
    elements.append(Spacer(1, 0.2 * cm))

    # Tabela de disciplinas do plano curricular da classe/secção do aluno em 2 Colunas equilibradas (18.0 cm total)
    notas_map = {}
    lista_disc_cert = []
    for d in (notas_disciplinas or []):
        nome_d = (d.get('nome') or d.get('disciplina') or '').strip()
        if nome_d and nome_d not in lista_disc_cert:
            lista_disc_cert.append(nome_d)
        v = d.get('media_anual') if d.get('media_anual') is not None else (d.get('mediaFinal') if d.get('mediaFinal') is not None else d.get('notaFinal'))
        if nome_d and v not in (None, '-', '---'):
            try:
                notas_map[nome_d] = str(round(float(v)))
            except Exception:
                pass

    if not lista_disc_cert:
        plano = obter_disciplinas_plano_curricular(aluno, escola)
        lista_disc_cert = [p.get('nome') for p in plano if p.get('nome')]

    def obter_nota_cert(nome):
        for ch, vl in notas_map.items():
            if match_disciplina(nome, ch):
                return vl
        return '---'

    meio_cert = (len(lista_disc_cert) + 1) // 2
    col_esq = lista_disc_cert[:meio_cert]
    col_dir = lista_disc_cert[meio_cert:]

    s_name = ParagraphStyle('SN', fontName='Times-Roman', fontSize=11, leading=13.5)
    s_dots = ParagraphStyle('SD', fontName='Times-Roman', fontSize=10.5, leading=13.5, alignment=1, textColor=colors.HexColor('#666666'))
    s_val = ParagraphStyle('SV', fontName='Times-Bold', fontSize=11, leading=13.5, alignment=2)

    def criar_subitem_cert(disc, w_col=8.7 * cm):
        nota = obter_nota_cert(disc)
        nota_str = f'( {nota} ) valores' if nota != '---' else '( --- )'
        w1 = 5.6 * cm
        w3 = 2.4 * cm
        w2 = w_col - w1 - w3
        t = Table([[
            Paragraph(disc, s_name),
            Paragraph('....', s_dots),
            Paragraph(nota_str, s_val)
        ]], colWidths=[w1, w2, w3])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]))
        return t

    rows_cert = []
    max_len = max(len(col_esq), len(col_dir))
    for i in range(max_len):
        d1 = col_esq[i] if i < len(col_esq) else ''
        d2 = col_dir[i] if i < len(col_dir) else ''

        it1 = criar_subitem_cert(d1, 8.7 * cm) if d1 else Paragraph('', s_name)
        it2 = criar_subitem_cert(d2, 8.7 * cm) if d2 else Paragraph('', s_name)

        rows_cert.append([it1, '', it2])

    t_grid = Table(rows_cert, colWidths=[8.8 * cm, 0.4 * cm, 8.8 * cm])
    t_grid.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 1),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    elements.append(t_grid)
    elements.append(Spacer(1, 0.2 * cm))

    # Média Global (Destacada e Centralizada)
    if media_global is not None and str(media_global) not in ('-', '---'):
        try:
            med_int = round(float(media_global))
            texto_med = f'<font color="#b91c1c"><b>Média Global: ( {med_int} ) Valores</b></font>'
        except Exception:
            texto_med = '<b>Média Global: ( --- ) Valores</b>'
    else:
        texto_med = '<b>Média Global: ( --- ) Valores</b>'

    style_med = ParagraphStyle('MedGlobal', parent=styles['Normal'], fontSize=11, leading=14, fontName='Times-Bold', alignment=1)
    elements.append(Paragraph(texto_med, style_med))
    elements.append(Spacer(1, 0.18 * cm))

    # Texto de Encerramento Oficial
    pauta_num = kwargs.get('pauta_num', '01')
    termo_num = kwargs.get('livro_termo', '124')
    matricula = getattr(aluno, 'matricula', 'MAT-2026-1006')

    fecho = (
        f"Os resultados constam da pauta nº <b>{pauta_num}</b> e do livro de Termo de Exames nº <b>{termo_num}</b>, código do aluno <b>{matricula}</b>.<br/>"
        f"E, por ser verdade passo o presente certificado que assino e autentico a tinta de óleo/selo branco em uso neste Estabelecimento de Ensino."
    )
    elements.append(Paragraph(fecho, style_body))
    elements.append(Spacer(1, 0.2 * cm))

    # Datação
    hoje = datetime.date.today().strftime('%d de %B de %Y')
    elements.append(Paragraph(f"{dist}, aos {hoje}", ParagraphStyle('PCertData', fontName='Times-Roman', fontSize=9.5, alignment=1)))
    elements.append(Spacer(1, 0.22 * cm))

    # QR Code e Autenticidade Digital
    cod = codigo_autenticidade or f"CERT-MZ-5001234567-{matricula}-{ano_letivo or 2026}"
    domain_base = os.environ.get('SIGE_PUBLIC_URL', 'https://sigesaas.duckdns.org').rstrip('/')
    qr_url = f"{domain_base}/verificar-certificado.html?codigo={cod}"
    qr_img = gerar_qr_code_image(qr_url)
    rl_qr = RLImage(qr_img, width=1.5 * cm, height=1.5 * cm)

    # Assinaturas Oficiais (3 Colunas estritamente em 18.0 cm)
    col_esq_content = [
        Paragraph("Extrai: _______&nbsp;&nbsp;&nbsp;Conferi: _______", ParagraphStyle('AExtrai', fontName='Times-Roman', fontSize=8, leading=10.5)),
        Spacer(1, 0.12 * cm),
        Paragraph("<b>O Chefe da Secretaria</b>", ParagraphStyle('AChefe', fontName='Times-Bold', fontSize=9, leading=11, alignment=1)),
        Paragraph("_____________________________", ParagraphStyle('ALinha1', fontName='Times-Roman', fontSize=9, alignment=1)),
        Paragraph(f"<b>{chefe_nome}</b>", ParagraphStyle('AChefeN', fontName='Times-Bold', fontSize=8.5, leading=11, alignment=1)),
        Paragraph(f"<i>/{chefe_carreira}/</i>", ParagraphStyle('AChefeC', fontName='Times-Italic', fontSize=8, leading=10, alignment=1)),
    ]

    col_meio_content = [
        rl_qr,
        Spacer(1, 0.05 * cm),
        Paragraph(f"<font size=6.5 color='#333333'>{cod}</font>", ParagraphStyle('AQrCod', fontName='Times-Roman', fontSize=6.5, leading=8, alignment=1))
    ]

    col_dir_content = [
        Paragraph("&nbsp;", ParagraphStyle('ASpace', fontSize=8, leading=10.5)),
        Spacer(1, 0.12 * cm),
        Paragraph("<b>O Director da Escola</b>", ParagraphStyle('ADir', fontName='Times-Bold', fontSize=9, leading=11, alignment=1)),
        Paragraph("_____________________________", ParagraphStyle('ALinha2', fontName='Times-Roman', fontSize=9, alignment=1)),
        Paragraph(f"<b>{dir_nome}</b>", ParagraphStyle('ADirN', fontName='Times-Bold', fontSize=8.5, leading=11, alignment=1)),
        Paragraph(f"<i>/{dir_carreira}/</i>", ParagraphStyle('ADirC', fontName='Times-Italic', fontSize=8, leading=10, alignment=1)),
    ]

    t_sigs = Table([[col_esq_content, col_meio_content, col_dir_content]], colWidths=[6.5 * cm, 5.0 * cm, 6.5 * cm])
    t_sigs.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(KeepTogether(t_sigs))

    # Compilação com moldura dupla ornamental e marca d'água
    doc.build(
        elements,
        onFirstPage=lambda c, d: desenhar_moldura_e_marca_dagua(c, d, 'dupla', True),
        onLaterPages=lambda c, d: desenhar_moldura_e_marca_dagua(c, d, 'dupla', True)
    )
    buffer.seek(0)
    return buffer.getvalue()

# ==================== 5. ACTA DO CONSELHO (HORIZONTAL / LANDSCAPE) ====================

def gerar_acta_pdf(turma, escola, periodo, ano_letivo, dados_alunos,
                    tabela_efectivo=None, tabela_aproveitamento=None,
                    disciplinas=None, trimestres_com_notas=None,
                    estatisticas=None, presidente=None, data_sessao=None,
                    orientacao='landscape', params_sessao=None, **kwargs) -> bytes:
    buffer = io.BytesIO()
    page_size = obter_tamanho_pagina(orientacao, padrao='landscape')
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        rightMargin=1.0 * cm,
        leftMargin=1.0 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm
    )
    styles = getSampleStyleSheet()
    elements = []

    # 1. Cabeçalho Oficial MEC (Compacto para permitir fluxo contínuo das tabelas na Página 1)
    if os.path.exists(EMBLEMA_PATH):
        try:
            elements.append(RLImage(EMBLEMA_PATH, width=0.9 * cm, height=0.9 * cm))
            elements.append(Spacer(1, 0.08 * cm))
        except Exception:
            pass

    prov_str = (getattr(escola, 'provincia', '') or 'Inhambane').upper()
    dist_str = (getattr(escola, 'distrito', '') or 'Massinga').upper()
    esc_nome = (getattr(escola, 'nome', '') or 'Escola Secundária').upper()

    style_rep = ParagraphStyle('ActaHdrRep', alignment=1, fontSize=9.5, leading=11, fontName='Times-Bold')
    style_min = ParagraphStyle('ActaHdrMin', alignment=1, fontSize=9.0, leading=10.5, fontName='Times-Bold')
    style_gov = ParagraphStyle('ActaHdrGov', alignment=1, fontSize=8.0, leading=9.5, fontName='Times-Roman')
    style_esc = ParagraphStyle('ActaHdrEsc', alignment=1, fontSize=9.5, leading=11, fontName='Times-Bold')

    elements.append(Paragraph("REPÚBLICA DE MOÇAMBIQUE", style_rep))
    elements.append(Paragraph("MINISTÉRIO DA EDUCAÇÃO E DESENVOLVIMENTO HUMANO", style_min))
    elements.append(Paragraph(f"DIRECÇÃO PROVINCIAL DA EDUCAÇÃO — {prov_str} | SERVIÇO DISTRITAL DE EDUCAÇÃO, JUVENTUDE E TECNOLOGIA DE {dist_str}", style_gov))
    elements.append(Paragraph(esc_nome, style_esc))
    elements.append(Spacer(1, 0.1 * cm))

    # 2. Título da Acta e Subtítulo Oficial
    style_title = ParagraphStyle('ActaTitle', parent=styles['Normal'], alignment=1, fontSize=10.0, leading=12, fontName='Times-Bold')
    style_sub = ParagraphStyle('ActaSub', parent=styles['Normal'], alignment=1, fontSize=8.0, leading=9.5, fontName='Times-Bold', textColor=colors.HexColor('#1e3a8a'))
    elements.append(Paragraph(f"ACTA DO CONSELHO DE AVALIAÇÃO DA TURMA {turma.nome} — {ano_letivo or 2026}", style_title))
    elements.append(Paragraph(f"SECTOR PEDAGÓGICO — {turma.grau_ano} | CURSO {'NOCTURNO' if (turma.turno or '').upper() == 'NOITE' else 'DIURNO'}", style_sub))
    elements.append(Spacer(1, 0.1 * cm))

    # 3. Extrair dados da Sessão e Montar Texto Protocolar Oficial
    ps = dict(params_sessao or {})
    p1 = ps.get('presidenteT1') or presidente or '____________________'
    p2 = ps.get('presidenteT2') or presidente or '____________________'
    p3 = ps.get('presidenteT3') or presidente or '____________________'

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
        f"Sob presidência do senhor professor <b>{p1}</b> (Iº Trimestre); <b>{p2}</b> (IIº Trimestre); <b>{p3}</b> (IIIº Trimestre); "
        f"director/substituto do director de turma <b>{dt_turma}</b> da turma <b>{turma.nome}</b> do grupo da <b>{turma.grau_ano}</b>, "
        f"curso <b>{curso_txt}</b>, realizou-se o Conselho de Avaliação do Iº; IIº, IIIº, Trimestre no dia <b>{dt1}</b>; <b>{dt2}</b>; <b>{dt3}</b>, "
        f"com início às <b>{hIni1}</b> horas e <b>{mIni1}</b> minutos e com término às <b>{hFim1}</b> horas e <b>{mFim1}</b> minutos (Iº Trim); "
        f"<b>{hIni2}</b> horas e <b>{mIni2}</b> minutos e com término às <b>{hFim2}</b> horas e <b>{mFim2}</b> minutos (IIº Trim); "
        f"<b>{hIni3}</b> horas e <b>{mIni3}</b> minutos e com término às <b>{hFim3}</b> horas e <b>{mFim3}</b> minutos (IIIº Trim). "
        f"No final deste conselho colheram-se os resultados que abaixo vão discriminados de todos os membros que participaram:"
    )
    style_proto = ParagraphStyle('ActaProto', parent=styles['Normal'], alignment=4, fontSize=6.8, leading=8.5, fontName='Times-Roman')
    elements.append(Paragraph(texto_protocolar, style_proto))
    elements.append(Spacer(1, 0.12 * cm))

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

    # 4. TABELA 1: Aproveitamento por Trimestres e Fim do Ano (Efectivos e Movimento por Género)
    hdr_t1_rows = [
        ['CATEGORIA', 'GÉN', 'Iº TRIMESTRE', '', 'IIº TRIMESTRE', '', 'IIIº TRIMESTRE', '', 'FIM DO ANO', ''],
        ['', '', 'Nº', '%', 'Nº', '%', 'Nº', '%', 'Nº', '%']
    ]
    data_t1 = list(hdr_t1_rows)
    cats_te = [
        ('Matrículas / Efectivo Inicial', 'inscritos'),
        ('Desistentes', 'desistentes'),
        ('Transferidos', 'transferidos'),
        ('Falecidos', 'falecidos'),
        ('Perdeu Ano por Faltas', 'perdeuFaltas'),
        ('Anulou Matrícula', 'anulouMatricula'),
        ('Alunos Avaliados', 'avaliados'),
    ]

    t1_styles = [
        ('BACKGROUND', (0, 0), (-1, 1), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 1), colors.white),
        ('FONTNAME', (0, 0), (-1, 1), 'Times-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 5.5),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#94a3b8')),
        ('TOPPADDING', (0, 0), (-1, -1), 0.6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0.6),
        ('LEFTPADDING', (0, 0), (-1, -1), 1),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ('SPAN', (0, 0), (0, 1)),
        ('SPAN', (1, 0), (1, 1)),
        ('SPAN', (2, 0), (3, 0)),
        ('SPAN', (4, 0), (5, 0)),
        ('SPAN', (6, 0), (7, 0)),
        ('SPAN', (8, 0), (9, 0)),
    ]

    curr_row_t1 = 2
    for label, chave in cats_te:
        t1_styles.append(('SPAN', (0, curr_row_t1), (0, curr_row_t1 + 2)))
        t1_styles.append(('ALIGN', (0, curr_row_t1), (0, curr_row_t1 + 2), 'LEFT'))
        t1_styles.append(('LEFTPADDING', (0, curr_row_t1), (0, curr_row_t1 + 2), 2))
        is_inicial = (chave == 'inscritos')

        for gen in ['H', 'M', 'HM']:
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

            if gen == 'HM':
                t1_styles.append(('BACKGROUND', (1, curr_row_t1), (-1, curr_row_t1), colors.HexColor('#f1f5f9')))
                t1_styles.append(('FONTNAME', (1, curr_row_t1), (-1, curr_row_t1), 'Times-Bold'))

            data_t1.append([label if gen == 'H' else '', gen, v_t1, p_t1, v_t2, p_t2, v_t3, p_t3, v_fa, p_fa])
            curr_row_t1 += 1

    t1_col_widths = [3.2 * cm, 0.65 * cm, 1.2 * cm, 1.1 * cm, 1.2 * cm, 1.1 * cm, 1.2 * cm, 1.1 * cm, 1.2 * cm, 1.1 * cm]
    t1_table = Table(data_t1, colWidths=t1_col_widths, rowHeights=[10.5, 9.5] + [8.5] * 21)
    t1_table.setStyle(TableStyle(t1_styles))

    # 5. TABELA 2: Aproveitamento Pedagógico por Faixas e Crescimento
    hdr_t2_rows = [
        ['CLASSIFICAÇÃO', 'GÉN', 'Iº TRIMESTRE', '', 'IIº TRIMESTRE', '', 'IIIº TRIMESTRE', '', 'FIM DO ANO', '', 'CRESCIMENTO', '', ''],
        ['', '', 'Nº', '%', 'Nº', '%', 'Nº', '%', 'Nº', '%', 'I-II', 'II-III', 'GLO']
    ]
    data_t2 = list(hdr_t2_rows)
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

    t2_styles = [
        ('BACKGROUND', (0, 0), (-1, 1), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 1), colors.white),
        ('FONTNAME', (0, 0), (-1, 1), 'Times-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 5.5),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#94a3b8')),
        ('TOPPADDING', (0, 0), (-1, -1), 0.6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0.6),
        ('LEFTPADDING', (0, 0), (-1, -1), 1),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ('SPAN', (0, 0), (0, 1)),
        ('SPAN', (1, 0), (1, 1)),
        ('SPAN', (2, 0), (3, 0)),
        ('SPAN', (4, 0), (5, 0)),
        ('SPAN', (6, 0), (7, 0)),
        ('SPAN', (8, 0), (9, 0)),
        ('SPAN', (10, 0), (12, 0)),
    ]

    curr_row_t2 = 2
    for label, chave, is_aprov in cats_ta:
        t2_styles.append(('SPAN', (0, curr_row_t2), (0, curr_row_t2 + 2)))
        t2_styles.append(('ALIGN', (0, curr_row_t2), (0, curr_row_t2 + 2), 'LEFT'))
        t2_styles.append(('LEFTPADDING', (0, curr_row_t2), (0, curr_row_t2 + 2), 2))

        for gen in ['H', 'M', 'HM']:
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

            if is_aprov:
                t2_styles.append(('BACKGROUND', (0, curr_row_t2), (-1, curr_row_t2), colors.HexColor('#dcfce7')))
                t2_styles.append(('TEXTCOLOR', (0, curr_row_t2), (-1, curr_row_t2), colors.HexColor('#166534')))
                t2_styles.append(('FONTNAME', (0, curr_row_t2), (-1, curr_row_t2), 'Times-Bold'))
            elif gen == 'HM':
                t2_styles.append(('BACKGROUND', (1, curr_row_t2), (-1, curr_row_t2), colors.HexColor('#f1f5f9')))
                t2_styles.append(('FONTNAME', (1, curr_row_t2), (-1, curr_row_t2), 'Times-Bold'))

            data_t2.append([label if gen == 'H' else '', gen, v_t1, p_t1, v_t2, p_t2, v_t3, p_t3, v_fa, p_fa, c1_2, c2_3, c_glo])
            curr_row_t2 += 1

    t2_col_widths = [2.8 * cm, 0.6 * cm, 0.95 * cm, 0.95 * cm, 0.95 * cm, 0.95 * cm, 0.95 * cm, 0.95 * cm, 0.95 * cm, 0.95 * cm, 1.0 * cm, 1.0 * cm, 1.0 * cm]
    t2_table = Table(data_t2, colWidths=t2_col_widths, rowHeights=[10.5, 9.5] + [8.5] * 24)
    t2_table.setStyle(TableStyle(t2_styles))

    # Título das tabelas lado a lado e inclusão imediata na Página 1 após a informação
    style_th_block = ParagraphStyle('THB', fontName='Times-Bold', fontSize=6.5, leading=8, alignment=1, textColor=colors.HexColor('#1e3a8a'))
    col_t1 = [Paragraph("<b>APROVEITAMENTO POR TRIMESTRES E FIM DO ANO (EFECTIVOS E MOVIMENTO)</b>", style_th_block), Spacer(1, 0.06 * cm), t1_table]
    col_t2 = [Paragraph("<b>APROVEITAMENTO PEDAGÓGICO POR FAIXAS E CRESCIMENTO</b>", style_th_block), Spacer(1, 0.06 * cm), t2_table]

    t_side_by_side = Table([[col_t1, col_t2]], colWidths=[13.2 * cm, 14.3 * cm])
    t_side_by_side.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(t_side_by_side)

    # 6. TABELA 3: Aproveitamento Pedagógico por Disciplina (Fluxo Contínuo)
    if discs:
        elements.append(Spacer(1, 0.3 * cm))
        style_sec = ParagraphStyle('SecHdr', fontName='Times-Bold', fontSize=9.5, leading=12, alignment=1, textColor=colors.HexColor('#1e3a8a'))
        elements.append(Paragraph("<b>ÁREA CURRICULAR & ESTATÍSTICA PEDAGÓGICA POR DISCIPLINA</b>", style_sec))
        elements.append(Spacer(1, 0.2 * cm))

        num_d = len(discs)
        col_w_class = 3.5 * cm
        disp_w = 24.0 * cm
        d_width = disp_w / max(num_d, 1)
        sub_w = d_width / 3.0

        t3_widths = [col_w_class] + [sub_w] * (num_d * 3)

        row0 = ['CLASSIFICAÇÃO']
        row1 = ['']
        for d in discs:
            row0.extend([d.get('nome', '').upper(), '', ''])
            row1.extend(['H', 'M', 'HM'])

        data_t3 = [row0, row1]

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

        t3_styles = [
            ('BACKGROUND', (0, 0), (-1, 1), colors.HexColor('#1e3a8a')),
            ('TEXTCOLOR', (0, 0), (-1, 1), colors.white),
            ('FONTNAME', (0, 0), (-1, 1), 'Times-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 5.5),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#94a3b8')),
            ('TOPPADDING', (0, 0), (-1, -1), 1.2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1.2),
            ('LEFTPADDING', (0, 0), (-1, -1), 1),
            ('RIGHTPADDING', (0, 0), (-1, -1), 1),
            ('SPAN', (0, 0), (0, 1)),
            ('ALIGN', (0, 2), (0, -1), 'LEFT'),
            ('LEFTPADDING', (0, 2), (0, -1), 3),
        ]

        for i in range(num_d):
            c_start = 1 + i * 3
            t3_styles.append(('SPAN', (c_start, 0), (c_start + 2, 0)))

        for f_label, f_key, f_type in faixas_disc:
            r = [f_label]
            for d in discs:
                if f_type == 'docente':
                    r.extend(['_________________', '', ''])
                elif f_key == 'positivas_pct':
                    pos_h = d.get('positivas', {}).get('pctH', 0)
                    pos_m = d.get('positivas', {}).get('pctM', 0)
                    pos_hm = d.get('positivas', {}).get('pct', 0)
                    r.extend([f"{pos_h}%", f"{pos_m}%", f"{pos_hm}%"])
                else:
                    bloco = d.get(f_key, {})
                    r.extend([str(bloco.get('h', 0)), str(bloco.get('m', 0)), str(bloco.get('hm', 0))])
            data_t3.append(r)

        r_idx = 2
        for _, _, f_type in faixas_disc:
            if f_type == 'neutral':
                t3_styles.append(('BACKGROUND', (0, r_idx), (-1, r_idx), colors.HexColor('#f1f5f9')))
                t3_styles.append(('FONTNAME', (0, r_idx), (-1, r_idx), 'Times-Bold'))
            elif f_type == 'success':
                t3_styles.append(('BACKGROUND', (0, r_idx), (-1, r_idx), colors.HexColor('#dcfce7')))
                t3_styles.append(('TEXTCOLOR', (0, r_idx), (-1, r_idx), colors.HexColor('#166534')))
                t3_styles.append(('FONTNAME', (0, r_idx), (-1, r_idx), 'Times-Bold'))
            elif f_type == 'docente':
                for i in range(num_d):
                    c_start = 1 + i * 3
                    t3_styles.append(('SPAN', (c_start, r_idx), (c_start + 2, r_idx)))
                t3_styles.append(('FONTNAME', (0, r_idx), (-1, r_idx), 'Times-Italic'))
                t3_styles.append(('TEXTCOLOR', (0, r_idx), (-1, r_idx), colors.HexColor('#64748b')))
            r_idx += 1

        t3_table = Table(data_t3, colWidths=t3_widths)
        t3_table.setStyle(TableStyle(t3_styles))
        elements.append(t3_table)
        elements.append(Spacer(1, 0.4 * cm))

    # 7. TABELA 4: Relação Nominal dos Alunos e Deliberação do Conselho
    style_sec_nom = ParagraphStyle('SecNomHdr', fontName='Times-Bold', fontSize=9.5, leading=12, alignment=1, textColor=colors.HexColor('#1e3a8a'))
    elements.append(Paragraph("<b>RELAÇÃO NOMINAL DOS ALUNOS E DELIBERAÇÃO DO CONSELHO</b>", style_sec_nom))
    elements.append(Spacer(1, 0.2 * cm))

    headers_alunos = [
        Paragraph('<b>Nº</b>', ParagraphStyle('H1', fontName='Times-Bold', fontSize=8, alignment=1, textColor=colors.whitesmoke)),
        Paragraph('<b>Nome Completo do Aluno</b>', ParagraphStyle('H2', fontName='Times-Bold', fontSize=8, textColor=colors.whitesmoke)),
        Paragraph('<b>Média Final</b>', ParagraphStyle('H3', fontName='Times-Bold', fontSize=8, alignment=1, textColor=colors.whitesmoke)),
        Paragraph('<b>Comportamento</b>', ParagraphStyle('H4', fontName='Times-Bold', fontSize=8, alignment=1, textColor=colors.whitesmoke)),
        Paragraph('<b>Decisão do Conselho</b>', ParagraphStyle('H5', fontName='Times-Bold', fontSize=8, alignment=1, textColor=colors.whitesmoke)),
    ]
    tabela_alunos_data = [headers_alunos]

    style_td_num = ParagraphStyle('TDNum', fontName='Times-Roman', fontSize=8, alignment=1)
    style_td_nome = ParagraphStyle('TDNome', fontName='Times-Roman', fontSize=8, alignment=0)
    style_td_med = ParagraphStyle('TDMed', fontName='Times-Bold', fontSize=8, alignment=1)
    style_td_comp = ParagraphStyle('TDComp', fontName='Times-Roman', fontSize=8, alignment=1)

    for idx, aluno in enumerate(dados_alunos, start=1):
        res_val = str(aluno.get('resultado', 'Aprovado')).strip()
        cor = colors.HexColor('#dc2626') if res_val in ('Reprovado', 'R') else colors.HexColor('#15803d')
        style_res = ParagraphStyle('TDRes', fontName='Times-Bold', fontSize=8, alignment=1, textColor=cor)

        tabela_alunos_data.append([
            Paragraph(str(aluno.get('numero') or idx), style_td_num),
            Paragraph(aluno.get('nome', ''), style_td_nome),
            Paragraph(str(aluno.get('media_geral', '-')), style_td_med),
            Paragraph(str(aluno.get('comportamento', 'B') or 'B'), style_td_comp),
            Paragraph(res_val, style_res)
        ])

    t_alunos = Table(tabela_alunos_data, colWidths=[1.2 * cm, 12.6 * cm, 3.2 * cm, 3.5 * cm, 7.0 * cm], repeatRows=1)
    t_alunos.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#94a3b8')),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(t_alunos)
    elements.append(Spacer(1, 0.5 * cm))

    # 8. Assinaturas Oficiais dos Membros do Conselho
    pres_final = p1 if p1 != '____________________' else (presidente or 'Presidente da Sessão')
    dir_turma_final = dt_turma if dt_turma != '____________________' else 'Director de Turma'
    sig_data = [
        ["O Presidente do Conselho", "O Secretário do Conselho", "O Director de Turma"],
        ["\n__________________________________", "\n__________________________________", "\n__________________________________"],
        [pres_final, "Secretário(a) Designado(a)", dir_turma_final]
    ]
    t_sig = Table(sig_data, colWidths=[9.1 * cm, 9.1 * cm, 9.1 * cm])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
    ]))
    elements.append(KeepTogether(t_sig))

    # Construção do PDF com moldura simples e marca d'água oficial
    doc.build(
        elements,
        onFirstPage=lambda c, d: desenhar_moldura_e_marca_dagua(c, d, 'simples', True),
        onLaterPages=lambda c, d: desenhar_moldura_e_marca_dagua(c, d, 'simples', True)
    )
    buffer.seek(0)
    return buffer.getvalue()

# ==================== 6. FICHA DO ALUNO (VERTICAL) ====================

def gerar_ficha_pdf(aluno, escola, orientacao='portrait') -> bytes:
    from common.utils.avaliacoes_mocambique import obter_disciplinas_plano_curricular

    buffer = io.BytesIO()
    page_size = obter_tamanho_pagina(orientacao, padrao='portrait')
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=0.9 * cm,
        bottomMargin=0.9 * cm
    )
    styles = getSampleStyleSheet()
    elements = []

    # 1. Cabeçalho Oficial MEC
    elements.extend(gerar_cabecalho_minedh(styles, escola.nome, escola.provincia, escola.distrito))

    style_title = ParagraphStyle('FichaTitle', parent=styles['Normal'], alignment=1, fontSize=12, leading=15, fontName='Times-Bold')
    elements.append(Paragraph("FICHA BIOGRÁFICA DO ALUNO", style_title))
    elements.append(Spacer(1, 0.25 * cm))

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

    # Tabela 1: Dados Biográficos e Identificação
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

    tabela_data = []
    style_l = ParagraphStyle('FL', fontName='Times-Bold', fontSize=8.5, leading=11)
    style_v = ParagraphStyle('FV', fontName='Times-Roman', fontSize=8.5, leading=11)

    for label, val in campos:
        tabela_data.append([Paragraph(label, style_l), Paragraph(str(val), style_v)])

    t_bio = Table(tabela_data, colWidths=[5.5 * cm, 12.5 * cm])
    t_bio.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#94a3b8')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc')),
        ('TOPPADDING', (0, 0), (-1, -1), 2.0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.0),
    ]))
    elements.append(t_bio)
    elements.append(Spacer(1, 0.3 * cm))

    # Tabela 2: Plano Curricular & Disciplinas que Estuda
    style_sec = ParagraphStyle('SecFicha', parent=styles['Normal'], alignment=0, fontSize=9.0, leading=11, fontName='Times-Bold', textColor=colors.HexColor('#1e3a8a'))
    elements.append(Paragraph(f"<b>PLANO CURRICULAR & DISCIPLINAS ({str(classe_str).upper()} — {str(area_str).upper()})</b>", style_sec))
    elements.append(Spacer(1, 0.12 * cm))

    disciplinas = obter_disciplinas_plano_curricular(aluno, escola)
    headers_disc = [
        Paragraph('<b>Nº</b>', ParagraphStyle('DH1', fontName='Times-Bold', fontSize=8, alignment=1, textColor=colors.whitesmoke)),
        Paragraph('<b>Código</b>', ParagraphStyle('DH2', fontName='Times-Bold', fontSize=8, alignment=1, textColor=colors.whitesmoke)),
        Paragraph('<b>Disciplina Curricular</b>', ParagraphStyle('DH3', fontName='Times-Bold', fontSize=8, textColor=colors.whitesmoke)),
        Paragraph('<b>Carga Horária</b>', ParagraphStyle('DH4', fontName='Times-Bold', fontSize=8, alignment=1, textColor=colors.whitesmoke)),
    ]
    data_disc = [headers_disc]
    style_td_c = ParagraphStyle('DC', fontName='Times-Roman', fontSize=7.5, leading=9.5, alignment=1)
    style_td_l = ParagraphStyle('DL', fontName='Times-Roman', fontSize=7.5, leading=9.5, alignment=0)

    for d in disciplinas:
        data_disc.append([
            Paragraph(str(d.get('numero', '-')), style_td_c),
            Paragraph(str(d.get('codigo', '-')), style_td_c),
            Paragraph(str(d.get('nome', '-')), style_td_l),
            Paragraph(str(d.get('carga', '-')), style_td_c),
        ])

    t_disc = Table(data_disc, colWidths=[1.2 * cm, 2.8 * cm, 11.2 * cm, 2.8 * cm])
    disc_styles = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#94a3b8')),
        ('TOPPADDING', (0, 0), (-1, -1), 1.6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.6),
    ]
    for r_i in range(1, len(data_disc)):
        if r_i % 2 == 0:
            disc_styles.append(('BACKGROUND', (0, r_i), (-1, r_i), colors.HexColor('#f8fafc')))

    t_disc.setStyle(TableStyle(disc_styles))
    elements.append(t_disc)
    elements.append(Spacer(1, 0.45 * cm))

    # Assinaturas Oficiais
    sig_data = [
        ["A Secretaria Escolar", "O Aluno / Encarregado de Educação"],
        ["\n__________________________________", "\n__________________________________"],
        ["", ""]
    ]
    t_sig = Table(sig_data, colWidths=[9.0 * cm, 9.0 * cm])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
    ]))
    elements.append(KeepTogether(t_sig))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# ==================== 7. RECIBO DE PAGAMENTO (VERTICAL) ====================

def gerar_recibo_pdf(pagamento, escola, orientacao='portrait') -> bytes:
    buffer = io.BytesIO()
    page_size = obter_tamanho_pagina(orientacao, padrao='portrait')
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm
    )
    styles = getSampleStyleSheet()
    elements = []

    elements.extend(gerar_cabecalho_minedh(styles, escola.nome, escola.provincia, escola.distrito))

    num_rec = getattr(pagamento, 'recibo_numero', None) or f"REC-{pagamento.id}"
    style_title = ParagraphStyle('RecTitle', parent=styles['Normal'], alignment=1, fontSize=13, leading=16, fontName='Times-Bold')
    elements.append(Paragraph(f"RECIBO DE PAGAMENTO OFICIAL — {num_rec}", style_title))
    elements.append(Spacer(1, 0.4 * cm))

    aluno = pagamento.aluno
    campos = [
        ('Nome do Aluno:', f"{aluno.nome} {getattr(aluno, 'apelido', '') or ''}".strip().upper() if aluno else '---'),
        ('Nº de Matrícula:', aluno.matricula if aluno else '---'),
        ('Turma:', aluno.turma.nome if aluno and aluno.turma else '---'),
        ('Descrição do Serviço:', pagamento.descricao or 'Mensalidade / Propina'),
        ('Mês de Referência:', str(pagamento.mes_referencia or '---')),
        ('Valor Total Pago:', f"<b>{pagamento.valor_pago or pagamento.valor} MT</b>"),
        ('Forma de Pagamento:', str(pagamento.metodo_pagamento or 'MPESA')),
        ('Data de Confirmação:', str(pagamento.data_pagamento or pagamento.created_at)[:10])
    ]

    tabela_data = []
    style_l = ParagraphStyle('RL', fontName='Times-Bold', fontSize=10.5, leading=14)
    style_v = ParagraphStyle('RV', fontName='Times-Roman', fontSize=10.5, leading=14)

    for label, val in campos:
        tabela_data.append([Paragraph(label, style_l), Paragraph(str(val), style_v)])

    t = Table(tabela_data, colWidths=[6.5 * cm, 11.5 * cm])
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#94a3b8')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 1.2 * cm))

    sig_data = [
        ["A Secretaria Escolar", "O Utente / Pagador"],
        ["\n__________________________________", "\n__________________________________"],
        ["Assinatura e Carimbo", "Assinatura"]
    ]
    t_sig = Table(sig_data, colWidths=[9.0 * cm, 9.0 * cm])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
    ]))
    elements.append(KeepTogether(t_sig))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


# ==================== 8. CADERNETA DE AVALIAÇÃO CONTÍNUA DO PROFESSOR (PDF HORIZONTAL) ====================

def gerar_caderneta_pdf(caderneta_data: dict, orientacao='landscape') -> bytes:
    buffer = io.BytesIO()
    page_size = obter_tamanho_pagina(orientacao, padrao='landscape')
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        rightMargin=1.0 * cm,
        leftMargin=1.0 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm
    )
    styles = getSampleStyleSheet()
    elements = []

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

    # 1. Cabeçalho Institucional Oficial
    elements.extend(gerar_cabecalho_minedh(styles, esc_nome, prov, dist, compacto=True))

    style_title = ParagraphStyle('CadTitle', parent=styles['Normal'], alignment=1, fontSize=10.5, leading=13, fontName='Times-Bold')
    style_meta = ParagraphStyle('CadMeta', parent=styles['Normal'], alignment=1, fontSize=8.0, leading=10, fontName='Times-Roman')
    elements.append(Paragraph(f"CADERNETA DE AVALIAÇÃO CONTÍNUA DO PROFESSOR — DISCIPLINA: {disc_nome} ({disc_cod})", style_title))
    elements.append(Paragraph(
        f"<b>Ano Lectivo:</b> {ano_letivo} | <b>Classe:</b> {grau_ano} | <b>Turma:</b> {turma_nome} | <b>Turno:</b> {turno} | <b>Sala:</b> {sala} | "
        f"<b>Efectivo:</b> H={ef_h}, M={ef_m}, HM={ef_tot} | <b>Docente:</b> {prof_nome} ({prof_tel}) | <b>Director de Turma:</b> {dt_nome}",
        style_meta
    ))
    elements.append(Spacer(1, 0.18 * cm))

    # 2. Tabela da Caderneta (28 colunas: Nº, Nome Completo, Gén, 3x8 colunas trimestrais, MFD)
    row_top = [
        'Nº', 'Nome Completo do Aluno', 'Gén',
        'Iº TRIMESTRE', '', '', '', '', '', '', '',
        'IIº TRIMESTRE', '', '', '', '', '', '', '',
        'IIIº TRIMESTRE', '', '', '', '', '', '', '',
        'MFD'
    ]
    row_sub = [
        '', '', '',
        '1ªA', '2ªA', '3ªA', 'MAP', 'MAS', 'AT', 'MT', 'Cp',
        '1ªA', '2ªA', '3ªA', 'MAP', 'MAS', 'AT', 'MT', 'Cp',
        '1ªA', '2ªA', '3ªA', 'MAP', 'MAS', 'AT', 'MT', 'Cp',
        ''
    ]
    data_table = [row_top, row_sub]

    def fmt_n(val):
        if val is None or val == '' or val == '-':
            return '-'
        try:
            f = float(val)
            return str(round(f, 1) if f % 1 != 0 else int(f))
        except (ValueError, TypeError):
            return str(val)

    style_nome = ParagraphStyle('CadAlNome', fontName='Times-Roman', fontSize=6.5, leading=7.5, alignment=0)
    for idx, al in enumerate(alunos, start=1):
        t1 = al.get('t1') or {}
        t2 = al.get('t2') or {}
        t3 = al.get('t3') or {}
        nome_c = f"{al.get('nome') or ''} {al.get('apelido') or ''}".strip()
        r = [
            str(al.get('numero') or idx),
            Paragraph(nome_c[:38], style_nome),
            str(al.get('genero') or 'M'),
            fmt_n(t1.get('t1')), fmt_n(t1.get('t2')), fmt_n(t1.get('t3')), fmt_n(t1.get('map')), fmt_n(t1.get('mas')), fmt_n(t1.get('at')), fmt_n(t1.get('mt')), str(t1.get('comportamento') or '-'),
            fmt_n(t2.get('t1')), fmt_n(t2.get('t2')), fmt_n(t2.get('t3')), fmt_n(t2.get('map')), fmt_n(t2.get('mas')), fmt_n(t2.get('at')), fmt_n(t2.get('mt')), str(t2.get('comportamento') or '-'),
            fmt_n(t3.get('t1')), fmt_n(t3.get('t2')), fmt_n(t3.get('t3')), fmt_n(t3.get('map')), fmt_n(t3.get('mas')), fmt_n(t3.get('at')), fmt_n(t3.get('mt')), str(t3.get('comportamento') or '-'),
            fmt_n(al.get('mfd'))
        ]
        data_table.append(r)

    # Linhas de Parâmetros Estatísticos Oficiais Conforme Modelo Padronizado (Foto Oficial)
    stat_cols = [
        't1_t1', 't1_t2', 't1_t3', 't1_map', 't1_mas', 't1_at', 't1_mt', None,
        't2_t1', 't2_t2', 't2_t3', 't2_map', 't2_mas', 't2_at', 't2_mt', None,
        't3_t1', 't3_t2', 't3_t3', 't3_map', 't3_mas', 't3_at', 't3_mt', None,
        'mfd'
    ]

    stat_rows_start = len(data_table)

    st_param_title = ParagraphStyle('StatParamTitle', fontName='Times-Bold', fontSize=6.5, leading=7.5, alignment=0, textColor=colors.HexColor('#0f172a'))
    st_stat_lbl_dark = ParagraphStyle('StatLblDark', fontName='Times-Bold', fontSize=6.0, leading=7.0, alignment=0, textColor=colors.HexColor('#0f172a'))
    st_stat_lbl_green = ParagraphStyle('StatLblGreen', fontName='Times-Bold', fontSize=6.0, leading=7.0, alignment=0, textColor=colors.HexColor('#059669'))
    st_stat_lbl_red = ParagraphStyle('StatLblRed', fontName='Times-Bold', fontSize=6.0, leading=7.0, alignment=0, textColor=colors.HexColor('#dc2626'))

    st_stat_gen_dark = ParagraphStyle('StatGenDark', fontName='Times-Roman', fontSize=6.0, leading=7.0, alignment=1, textColor=colors.HexColor('#0f172a'))
    st_stat_gen_dark_bold = ParagraphStyle('StatGenDarkB', fontName='Times-Bold', fontSize=6.0, leading=7.0, alignment=1, textColor=colors.HexColor('#0f172a'))
    st_stat_gen_green = ParagraphStyle('StatGenGreen', fontName='Times-Roman', fontSize=6.0, leading=7.0, alignment=1, textColor=colors.HexColor('#059669'))
    st_stat_gen_green_bold = ParagraphStyle('StatGenGreenB', fontName='Times-Bold', fontSize=6.0, leading=7.0, alignment=1, textColor=colors.HexColor('#059669'))
    st_stat_gen_red = ParagraphStyle('StatGenRed', fontName='Times-Roman', fontSize=6.0, leading=7.0, alignment=1, textColor=colors.HexColor('#dc2626'))
    st_stat_gen_red_bold = ParagraphStyle('StatGenRedB', fontName='Times-Bold', fontSize=6.0, leading=7.0, alignment=1, textColor=colors.HexColor('#dc2626'))

    st_val_dark = ParagraphStyle('StatValDark', fontName='Times-Roman', fontSize=6.0, leading=7.0, alignment=1, textColor=colors.HexColor('#0f172a'))
    st_val_dark_bold = ParagraphStyle('StatValDarkB', fontName='Times-Bold', fontSize=6.0, leading=7.0, alignment=1, textColor=colors.HexColor('#0f172a'))
    st_val_green = ParagraphStyle('StatValGreen', fontName='Times-Roman', fontSize=6.0, leading=7.0, alignment=1, textColor=colors.HexColor('#059669'))
    st_val_green_bold = ParagraphStyle('StatValGreenB', fontName='Times-Bold', fontSize=6.0, leading=7.0, alignment=1, textColor=colors.HexColor('#059669'))
    st_val_red = ParagraphStyle('StatValRed', fontName='Times-Roman', fontSize=6.0, leading=7.0, alignment=1, textColor=colors.HexColor('#dc2626'))
    st_val_red_bold = ParagraphStyle('StatValRedB', fontName='Times-Bold', fontSize=6.0, leading=7.0, alignment=1, textColor=colors.HexColor('#dc2626'))

    def _val_cad(col_k, getter, default='-'):
        if not col_k or col_k not in estatisticas:
            return default
        col_st = estatisticas[col_k]
        if (col_st.get('avaliados') or {}).get('total', 0) == 0:
            return default
        return getter(col_st)

    # 1. Linha: Parametro estatistico
    row_param = [Paragraph('Parametro estatistico', st_param_title)] + [''] * 27
    r_param_idx = len(data_table)
    data_table.append(row_param)

    # 2. Avaliados (M, F, M+F)
    r_av_idx = len(data_table)
    row_av_m = [Paragraph('Avaliados', st_stat_lbl_dark), '', Paragraph('M', st_stat_gen_dark)] + [
        Paragraph(str(_val_cad(k, lambda s: (s.get('avaliados') or {}).get('h', 0))), st_val_dark) for k in stat_cols
    ]
    row_av_f = ['', '', Paragraph('F', st_stat_gen_dark)] + [
        Paragraph(str(_val_cad(k, lambda s: (s.get('avaliados') or {}).get('m', 0))), st_val_dark) for k in stat_cols
    ]
    row_av_mf = ['', '', Paragraph('M+F', st_stat_gen_dark_bold)] + [
        Paragraph(str(_val_cad(k, lambda s: (s.get('avaliados') or {}).get('total', 0))), st_val_dark_bold) for k in stat_cols
    ]
    data_table.extend([row_av_m, row_av_f, row_av_mf])

    # 3. Positivos (M, F, M+F)
    r_pos_idx = len(data_table)
    row_pos_m = [Paragraph('Positivos', st_stat_lbl_green), '', Paragraph('M', st_stat_gen_green)] + [
        Paragraph(str(_val_cad(k, lambda s: (s.get('positivas') or {}).get('h', 0))), st_val_green) for k in stat_cols
    ]
    row_pos_f = ['', '', Paragraph('F', st_stat_gen_green)] + [
        Paragraph(str(_val_cad(k, lambda s: (s.get('positivas') or {}).get('m', 0))), st_val_green) for k in stat_cols
    ]
    row_pos_mf = ['', '', Paragraph('M+F', st_stat_gen_green_bold)] + [
        Paragraph(str(_val_cad(k, lambda s: (s.get('positivas') or {}).get('total', 0))), st_val_green_bold) for k in stat_cols
    ]
    data_table.extend([row_pos_m, row_pos_f, row_pos_mf])

    # 4. % Positivos (M, F, M+F)
    r_pct_pos_idx = len(data_table)
    row_pct_pos_m = [Paragraph('% Positivos', st_stat_lbl_green), '', Paragraph('M', st_stat_gen_green)] + [
        Paragraph(str(_val_cad(k, lambda s: f"{(s.get('positivas') or {}).get('pctH', 0)}%")), st_val_green) for k in stat_cols
    ]
    row_pct_pos_f = ['', '', Paragraph('F', st_stat_gen_green)] + [
        Paragraph(str(_val_cad(k, lambda s: f"{(s.get('positivas') or {}).get('pctM', 0)}%")), st_val_green) for k in stat_cols
    ]
    row_pct_pos_mf = ['', '', Paragraph('M+F', st_stat_gen_green_bold)] + [
        Paragraph(str(_val_cad(k, lambda s: f"{(s.get('positivas') or {}).get('pct', 0)}%")), st_val_green_bold) for k in stat_cols
    ]
    data_table.extend([row_pct_pos_m, row_pct_pos_f, row_pct_pos_mf])

    # 5. Negativos (M, F, M+F)
    r_neg_idx = len(data_table)
    row_neg_m = [Paragraph('Negativos', st_stat_lbl_red), '', Paragraph('M', st_stat_gen_red)] + [
        Paragraph(str(_val_cad(k, lambda s: (s.get('negativas') or {}).get('h', 0))), st_val_red) for k in stat_cols
    ]
    row_neg_f = ['', '', Paragraph('F', st_stat_gen_red)] + [
        Paragraph(str(_val_cad(k, lambda s: (s.get('negativas') or {}).get('m', 0))), st_val_red) for k in stat_cols
    ]
    row_neg_mf = ['', '', Paragraph('M+F', st_stat_gen_red_bold)] + [
        Paragraph(str(_val_cad(k, lambda s: (s.get('negativas') or {}).get('total', 0))), st_val_red_bold) for k in stat_cols
    ]
    data_table.extend([row_neg_m, row_neg_f, row_neg_mf])

    # 6. % Negativos (M, F, M+F)
    r_pct_neg_idx = len(data_table)
    row_pct_neg_m = [Paragraph('% Negativos', st_stat_lbl_red), '', Paragraph('M', st_stat_gen_red)] + [
        Paragraph(str(_val_cad(k, lambda s: f"{(s.get('negativas') or {}).get('pctH', 0)}%")), st_val_red) for k in stat_cols
    ]
    row_pct_neg_f = ['', '', Paragraph('F', st_stat_gen_red)] + [
        Paragraph(str(_val_cad(k, lambda s: f"{(s.get('negativas') or {}).get('pctM', 0)}%")), st_val_red) for k in stat_cols
    ]
    row_pct_neg_mf = ['', '', Paragraph('M+F', st_stat_gen_red_bold)] + [
        Paragraph(str(_val_cad(k, lambda s: f"{(s.get('negativas') or {}).get('pct', 0)}%")), st_val_red_bold) for k in stat_cols
    ]
    data_table.extend([row_pct_neg_m, row_pct_neg_f, row_pct_neg_mf])

    # 7. Faixas Oficiais (0 a 9,4 | 9,5 a 13,4 | 13,5 a 16,4 | 16,5 a 18,4 | 18,5 a 20)
    faixas_defs = [
        ('0 a 9,4', 'f0_94'),
        ('9,5 a 13,4', 'f95_134'),
        ('13,5 a 16,4', 'f135_164'),
        ('16,5 a 18,4', 'f165_184'),
        ('18,5 a 20', 'f185_20'),
    ]
    r_faixas_start = len(data_table)
    for f_lbl, f_prop in faixas_defs:
        r_f = [Paragraph(f_lbl, st_stat_lbl_dark), '', ''] + [
            Paragraph(str(_val_cad(k, lambda s: ((s.get('faixas') or {}).get(f_prop) or {}).get('total', 0))), st_val_dark_bold) for k in stat_cols
        ]
        data_table.append(r_f)

    # 8. Média da Coluna
    r_media_idx = len(data_table)
    row_med = [Paragraph('Média da Coluna', st_stat_lbl_dark), '', ''] + [
        Paragraph(str(_val_cad(k, lambda s: s.get('media', 0))), st_val_dark_bold) for k in stat_cols
    ]
    data_table.append(row_med)

    col_widths = [0.65 * cm, 4.35 * cm, 0.65 * cm] + ([0.86 * cm] * 24) + [0.95 * cm]
    t_cad = Table(data_table, colWidths=col_widths, repeatRows=2)
    t_styles = [
        ('BACKGROUND', (0, 0), (-1, 1), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 1), colors.white),
        ('FONTNAME', (0, 0), (-1, 1), 'Times-Bold'),
        ('FONTNAME', (0, 2), (-1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 6.0),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 2), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#94a3b8')),
        ('TOPPADDING', (0, 0), (-1, -1), 1.4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.4),
        ('LEFTPADDING', (0, 0), (-1, -1), 1.2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1.2),
        ('SPAN', (0, 0), (0, 1)),
        ('SPAN', (1, 0), (1, 1)),
        ('SPAN', (2, 0), (2, 1)),
        ('SPAN', (3, 0), (10, 0)),
        ('SPAN', (11, 0), (18, 0)),
        ('SPAN', (19, 0), (26, 0)),
        ('SPAN', (27, 0), (27, 1)),
    ]
    # Destacar colunas MT (9, 17, 25) e MFD (27) nas linhas de alunos
    for col_mt in (9, 17, 25, 27):
        t_styles.append(('BACKGROUND', (col_mt, 2), (col_mt, stat_rows_start - 1), colors.HexColor('#f8fafc')))
        t_styles.append(('FONTNAME', (col_mt, 2), (col_mt, stat_rows_start - 1), 'Times-Bold'))

    # Estilização das Linhas Estatísticas Oficiais
    t_styles.extend([
        # Linha Parametro estatistico
        ('SPAN', (0, r_param_idx), (-1, r_param_idx)),
        ('BACKGROUND', (0, r_param_idx), (-1, r_param_idx), colors.HexColor('#e2e8f0')),
        ('ALIGN', (0, r_param_idx), (-1, r_param_idx), 'LEFT'),
        ('LEFTPADDING', (0, r_param_idx), (-1, r_param_idx), 4),
        ('FONTNAME', (0, r_param_idx), (-1, r_param_idx), 'Times-Bold'),

        # Spans dos Blocos
        ('SPAN', (0, r_av_idx), (1, r_av_idx + 2)),
        ('BACKGROUND', (0, r_av_idx + 2), (-1, r_av_idx + 2), colors.HexColor('#e5e7eb')),

        ('SPAN', (0, r_pos_idx), (1, r_pos_idx + 2)),
        ('BACKGROUND', (0, r_pos_idx + 2), (-1, r_pos_idx + 2), colors.HexColor('#d1fae5')),

        ('SPAN', (0, r_pct_pos_idx), (1, r_pct_pos_idx + 2)),
        ('BACKGROUND', (0, r_pct_pos_idx + 2), (-1, r_pct_pos_idx + 2), colors.HexColor('#d1fae5')),

        ('SPAN', (0, r_neg_idx), (1, r_neg_idx + 2)),
        ('BACKGROUND', (0, r_neg_idx + 2), (-1, r_neg_idx + 2), colors.HexColor('#fee2e2')),

        ('SPAN', (0, r_pct_neg_idx), (1, r_pct_neg_idx + 2)),
        ('BACKGROUND', (0, r_pct_neg_idx + 2), (-1, r_pct_neg_idx + 2), colors.HexColor('#fee2e2')),

        # Média da Coluna
        ('SPAN', (0, r_media_idx), (2, r_media_idx)),
        ('BACKGROUND', (0, r_media_idx), (-1, r_media_idx), colors.HexColor('#dbeafe')),
    ])

    for r_f_idx in range(r_faixas_start, r_media_idx):
        t_styles.append(('SPAN', (0, r_f_idx), (2, r_f_idx)))
        t_styles.append(('ALIGN', (0, r_f_idx), (0, r_f_idx), 'LEFT'))
        t_styles.append(('LEFTPADDING', (0, r_f_idx), (0, r_f_idx), 4))

    t_styles.append(('ALIGN', (0, r_media_idx), (0, r_media_idx), 'LEFT'))
    t_styles.append(('LEFTPADDING', (0, r_media_idx), (0, r_media_idx), 4))

    # Padding compacto e grid para todas as linhas estatísticas
    t_styles.append(('VALIGN', (0, stat_rows_start), (-1, len(data_table) - 1), 'MIDDLE'))
    t_styles.append(('TOPPADDING', (0, stat_rows_start), (-1, len(data_table) - 1), 0.7))
    t_styles.append(('BOTTOMPADDING', (0, stat_rows_start), (-1, len(data_table) - 1), 0.7))
    t_styles.append(('GRID', (0, stat_rows_start), (-1, len(data_table) - 1), 0.4, colors.HexColor('#94a3b8')))

    t_cad.setStyle(TableStyle(t_styles))
    elements.append(t_cad)
    elements.append(Spacer(1, 0.4 * cm))

    # Assinaturas
    sig_data = [
        ["O Docente da Disciplina", "O Director de Turma", "O Director Adjunto Pedagógico"],
        ["\n__________________________________", "\n__________________________________", "\n__________________________________"],
        [prof_nome, dt_nome, "Assinatura e Carimbo"]
    ]
    t_sig = Table(sig_data, colWidths=[9.1 * cm, 9.1 * cm, 9.1 * cm])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.0),
    ]))
    elements.append(KeepTogether(t_sig))

    doc.build(
        elements,
        onFirstPage=lambda c, d: desenhar_moldura_e_marca_dagua(c, d, 'simples', True),
        onLaterPages=lambda c, d: desenhar_moldura_e_marca_dagua(c, d, 'simples', True)
    )
    buffer.seek(0)
    return buffer.getvalue()


# ==================== 9. EMISSÃO EM LOTE DA TURMA (PDF) ====================

def gerar_lote_pdf(turma, escola, tipo_documento, alunos_documentos, orientacao='portrait') -> bytes:
    buffer = io.BytesIO()
    page_size = obter_tamanho_pagina(orientacao, padrao='portrait')
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        rightMargin=1.2 * cm,
        leftMargin=1.2 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm
    )
    styles = getSampleStyleSheet()
    elements = []

    elements.extend(gerar_cabecalho_minedh(styles, escola.nome, escola.provincia, escola.distrito))

    style_title = ParagraphStyle('LoteTitle', parent=styles['Normal'], alignment=1, fontSize=12, leading=15, fontName='Times-Bold')
    style_sub = ParagraphStyle('LoteSub', parent=styles['Normal'], alignment=1, fontSize=9.5, leading=12, fontName='Times-Roman')
    elements.append(Paragraph(f"MAPA DE EMISSÃO EM LOTE — {tipo_documento.upper()}", style_title))
    elements.append(Paragraph(
        f"<b>Turma:</b> {turma.nome} ({turma.grau_ano}) | <b>Ano Lectivo:</b> {turma.ano_letivo or getattr(escola, 'ano_letivo_ativo', '2026')} | "
        f"<b>Total de Alunos:</b> {len(alunos_documentos)}",
        style_sub
    ))
    elements.append(Spacer(1, 0.35 * cm))

    headers = [
        Paragraph('<b>Nº</b>', ParagraphStyle('LH1', fontName='Times-Bold', fontSize=8.5, alignment=1, textColor=colors.white)),
        Paragraph('<b>Nome Completo do Aluno</b>', ParagraphStyle('LH2', fontName='Times-Bold', fontSize=8.5, textColor=colors.white)),
        Paragraph('<b>Matrícula</b>', ParagraphStyle('LH3', fontName='Times-Bold', fontSize=8.5, alignment=1, textColor=colors.white)),
        Paragraph('<b>Média Global</b>', ParagraphStyle('LH4', fontName='Times-Bold', fontSize=8.5, alignment=1, textColor=colors.white)),
        Paragraph('<b>Situação Pedagógica</b>', ParagraphStyle('LH5', fontName='Times-Bold', fontSize=8.5, alignment=1, textColor=colors.white)),
    ]
    data_rows = [headers]
    s_c = ParagraphStyle('LC', fontName='Times-Roman', fontSize=8.5, alignment=1)
    s_l = ParagraphStyle('LL', fontName='Times-Roman', fontSize=8.5, alignment=0)
    s_b = ParagraphStyle('LB', fontName='Times-Bold', fontSize=8.5, alignment=1)

    for idx, doc_item in enumerate(alunos_documentos, start=1):
        al_info = doc_item.get('aluno') or {}
        nome = al_info.get('nomeCompleto') or al_info.get('nome') or 'Aluno'
        mat = al_info.get('matricula') or '-'
        med = doc_item.get('mediaGlobal') or doc_item.get('mediaGeral') or '-'
        sit = doc_item.get('situacaoGlobal') or doc_item.get('resultadoFinal') or 'Aprovado'
        data_rows.append([
            Paragraph(str(idx), s_c),
            Paragraph(str(nome), s_l),
            Paragraph(str(mat), s_c),
            Paragraph(str(med), s_b),
            Paragraph(str(sit), s_b),
        ])

    t = Table(data_rows, colWidths=[1.2 * cm, 7.6 * cm, 3.4 * cm, 2.8 * cm, 3.6 * cm], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#94a3b8')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(t)

    doc.build(
        elements,
        onFirstPage=lambda c, d: desenhar_moldura_e_marca_dagua(c, d, 'simples', True),
        onLaterPages=lambda c, d: desenhar_moldura_e_marca_dagua(c, d, 'simples', True)
    )
    buffer.seek(0)
    return buffer.getvalue()

