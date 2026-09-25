import io
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

def gerar_pauta_docx(turma, escola, periodo, ano_letivo, dados_alunos, disciplinas) -> bytes:
    doc = docx.Document()
    
    # Orientação e margens
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Cabeçalho
    p1 = doc.add_paragraph("REPÚBLICA DE MOÇAMBIQUE")
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.runs[0].font.bold = True
    p1.runs[0].font.size = Pt(11)

    p2 = doc.add_paragraph("MINISTÉRIO DA EDUCAÇÃO E DESENVOLVIMENTO HUMANO")
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.runs[0].font.bold = True
    p2.runs[0].font.size = Pt(10)

    p3 = doc.add_paragraph(f"{escola.nome.upper()}")
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p3.runs[0].font.bold = True
    p3.runs[0].font.size = Pt(12)

    doc.add_paragraph()

    # Título da Pauta
    p_title = doc.add_paragraph(f"PAUTA GERAL DE APROVEITAMENTO — {periodo.replace('_', ' ')} / {ano_letivo}")
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.runs[0].font.bold = True
    p_title.runs[0].font.size = Pt(11)

    p_sub = doc.add_paragraph(f"Turma: {turma.nome} | Grau: {turma.grau_ano} | Turno: {turma.turno}")
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.runs[0].font.size = Pt(9.5)

    doc.add_paragraph()

    # Tabela
    headers = ['Nº', 'Nome Completo'] + [d.codigo for d in disciplinas] + ['Média', 'Resultado']
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = 'Table Grid'

    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h
        hdr_cells[i].paragraphs[0].runs[0].font.bold = True
        hdr_cells[i].paragraphs[0].runs[0].font.size = Pt(8.5)

    for idx, aluno in enumerate(dados_alunos, start=1):
        row_cells = table.add_row().cells
        row_cells[0].text = str(idx)
        row_cells[1].text = aluno['nome']
        for d_idx, d in enumerate(disciplinas, start=2):
            nota = (aluno['notas'].get(str(d.id)) or aluno['notas'].get(d.id) or {}).get('media_final', '-')
            row_cells[d_idx].text = str(nota)
        row_cells[-2].text = str(aluno.get('media_geral', '-'))
        row_cells[-1].text = aluno.get('resultado', 'Aprovado')

        for cell in row_cells:
            cell.paragraphs[0].runs[0].font.size = Pt(8)

    doc.add_paragraph()
    doc.add_paragraph(f"Documento processado informaticamente pelo SIGE em nome de {escola.nome}.")

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
