import io
import qrcode
from PIL import Image
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def gerar_qr_code_image(dados_url: str) -> io.BytesIO:
    qr = qrcode.QRCode(box_size=3, border=1)
    qr.add_data(dados_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

def gerar_cabecalho_minedh(styles, escola_nome, provincia, distrito):
    elements = []
    style_center_bold = ParagraphStyle('CenterBold', parent=styles['Normal'], alignment=1, fontSize=10, leading=13, fontName='Helvetica-Bold')
    style_center = ParagraphStyle('Center', parent=styles['Normal'], alignment=1, fontSize=8.5, leading=11)

    elements.append(Paragraph("REPÚBLICA DE MOÇAMBIQUE", style_center_bold))
    elements.append(Paragraph("MINISTÉRIO DA EDUCAÇÃO E DESENVOLVIMENTO HUMANO", style_center_bold))
    elements.append(Paragraph(f"DIRECÇÃO PROVINCIAL DA EDUCAÇÃO — {provincia.upper()}", style_center))
    elements.append(Paragraph(f"SERVIÇO DISTRITAL DE EDUCAÇÃO, JUVENTUDE E TECNOLOGIA DE {distrito.upper()}", style_center))
    elements.append(Paragraph(escola_nome.upper(), style_center_bold))
    elements.append(Spacer(1, 0.4 * cm))
    return elements

def gerar_pauta_pdf(turma, escola, periodo, ano_letivo, dados_alunos, disciplinas) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm
    )
    styles = getSampleStyleSheet()
    elements = []

    # Cabeçalho Oficial
    elements.extend(gerar_cabecalho_minedh(styles, escola.nome, escola.provincia, escola.distrito))

    style_title = ParagraphStyle('Title', parent=styles['Heading2'], alignment=1, fontSize=12, leading=15, fontName='Helvetica-Bold')
    elements.append(Paragraph(f"PAUTA DE APROVEITAMENTO PEDAGÓGICO — {periodo.replace('_', ' ')} / {ano_letivo}", style_title))
    elements.append(Paragraph(f"Turma: <b>{turma.nome}</b> | Grau: <b>{turma.grau_ano}</b> | Turno: <b>{turma.turno}</b>", ParagraphStyle('Sub', alignment=1, fontSize=9)))
    elements.append(Spacer(1, 0.4 * cm))

    # Tabela da Pauta
    header_row = ['Nº', 'Nome Completo'] + [d.codigo for d in disciplinas] + ['Média', 'Neg.', 'Resultado']
    table_data = [header_row]

    for idx, aluno in enumerate(dados_alunos, start=1):
        row = [str(idx), aluno['nome']]
        for d in disciplinas:
            nota = (aluno['notas'].get(str(d.id)) or aluno['notas'].get(d.id) or {}).get('media_final', '-')
            row.append(str(nota))
        row.append(str(aluno.get('media_geral', '-')))
        row.append(str(aluno.get('total_negativas', 0)))
        row.append(aluno.get('resultado', 'Aprovado'))
        table_data.append(row)

    col_widths = [0.8 * cm, 5.5 * cm] + [1.8 * cm] * len(disciplinas) + [1.5 * cm, 1.2 * cm, 2.2 * cm]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.8 * cm))

    # Assinaturas
    sig_data = [
        ["O Director da Turma", "O Director Adjunto Pedagógico (DAP)", "O Director da Escola"],
        ["\n_______________________", "\n_______________________", "\n_______________________"],
        [turma.director_turma.nome if turma.director_turma else "Prof. Responsável", escola.dap_nome, escola.director_nome]
    ]
    t_sig = Table(sig_data, colWidths=[9 * cm, 9 * cm, 9 * cm])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t_sig)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

def gerar_boletim_pdf(aluno, escola, ano_letivo, notas_disciplinas) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    elements = []

    elements.extend(gerar_cabecalho_minedh(styles, escola.nome, escola.provincia, escola.distrito))

    style_title = ParagraphStyle('Title', alignment=1, fontSize=12, leading=15, fontName='Helvetica-Bold')
    elements.append(Paragraph("BOLETIM DE APROVEITAMENTO TRIMESTRAL", style_title))
    elements.append(Spacer(1, 0.3 * cm))

    # Dados do Aluno
    info_data = [
        [f"Aluno: <b>{aluno.nome}</b>", f"Matrícula: <b>{aluno.matricula}</b>"],
        [f"Turma: <b>{aluno.turma.nome if aluno.turma else 'N/A'}</b>", f"Ano Lectivo: <b>{ano_letivo}</b>"]
    ]
    t_info = Table(info_data, colWidths=[10 * cm, 7 * cm])
    t_info.setStyle(TableStyle([('FONTSIZE', (0, 0), (-1, -1), 9)]))
    elements.append(t_info)
    elements.append(Spacer(1, 0.4 * cm))

    # Tabela de Notas por Disciplina
    header = ['Disciplina', '1º Trim', '2º Trim', '3º Trim', 'Média Anual', 'Situação']
    rows = [header]
    for d in notas_disciplinas:
        rows.append([
            d['nome'],
            str(d.get('t1', '-')),
            str(d.get('t2', '-')),
            str(d.get('t3', '-')),
            str(d.get('media_anual', '-')),
            d.get('situacao', 'Aprovado')
        ])

    t_notas = Table(rows, colWidths=[6.5 * cm, 2.2 * cm, 2.2 * cm, 2.2 * cm, 2.2 * cm, 2.7 * cm])
    t_notas.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16a085')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(t_notas)
    elements.append(Spacer(1, 1 * cm))

    # QR Code e Autenticidade
    qr_buf = gerar_qr_code_image(f"https://sige.co.mz/verificar?aluno={aluno.matricula}")
    qr_img = RLImage(qr_buf, width=2.2*cm, height=2.2*cm)
    sig_table = Table([
        [qr_img, "O Director da Escola\n\n_______________________\n" + escola.director_nome]
    ], colWidths=[5 * cm, 12 * cm])
    sig_table.setStyle(TableStyle([('ALIGN', (1, 0), (1, 0), 'CENTER')]))
    elements.append(sig_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
