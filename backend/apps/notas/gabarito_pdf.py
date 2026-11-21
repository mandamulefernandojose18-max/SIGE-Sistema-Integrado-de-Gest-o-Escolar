"""PDF do gabarito / guião de correcção guardado (regras: docs/REGRAS_EXCEL_E_PDF.md, secção 2).

Times New Roman, cabeçalho de tabela azul e centrado, células com Paragraph (nada sobreposto), zebra, logótipo da escola.
Uma tabela por versão: pares «Pergunta | Resposta certa» em várias colunas e, por baixo, a chave em sequência.
"""
import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm

from apps.documentos.services.pdf_service import (
    KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, gerar_cabecalho_mec, getSampleStyleSheet,
)

AZUL = colors.HexColor('#1E3A8A')
ZEBRA = colors.HexColor('#F1F5F9')
CINZA = colors.HexColor('#94A3B8')
OURO = colors.HexColor('#C9A227')
PARES = 5                      # pares «Perg. | Resp.» por linha


def _esc(t):
    return str(t if t is not None else '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def nome_ficheiro(g):
    import re
    return re.sub(r'[\\/:*?"<>|\r\n]+', ' ', f'Gabarito - {g.nome}').strip() + '.pdf'


def _tabela_versao(chave):
    st_h = ParagraphStyle('GbH', fontName='Times-Bold', alignment=1, textColor=colors.white)
    st_n = ParagraphStyle('GbN', fontName='Times-Roman', alignment=1)
    st_r = ParagraphStyle('GbR', fontName='Times-Bold', alignment=1)
    cab = []
    for _ in range(PARES):
        cab += [Paragraph('Perg.', st_h), Paragraph('Resposta', st_h)]
    n = len(chave)
    linhas = -(-n // PARES)
    dados = [cab]
    for r in range(linhas):
        linha = []
        for c in range(PARES):
            q = r + c * linhas              # as perguntas descem por coluna, como na folha de resposta
            if q < n:
                linha += [Paragraph(str(q + 1), st_n), Paragraph(_esc(chave[q]), st_r)]
            else:
                linha += [Paragraph('', st_n), Paragraph('', st_n)]
        dados.append(linha)
    larg = [1.3 * cm, 2.2 * cm] * PARES            # 17,5 cm
    t = Table(dados, colWidths=larg, repeatRows=1)
    cmds = [('BACKGROUND', (0, 0), (-1, 0), AZUL), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1.2, AZUL), ('LINEBELOW', (0, 0), (-1, 0), 1.6, OURO),
            ('INNERGRID', (0, 1), (-1, -1), 0.4, CINZA)]
    for c in range(1, PARES):                       # linha mais grossa entre os grupos de colunas
        cmds.append(('LINEBEFORE', (c * 2, 0), (c * 2, -1), 1.0, AZUL))
    for i in range(2, len(dados), 2):
        cmds.append(('BACKGROUND', (0, i), (-1, i), ZEBRA))
    t.setStyle(TableStyle(cmds))
    return t


def pdf_gabarito(escola, g, professor_nome=''):
    buf = io.BytesIO()
    styles = getSampleStyleSheet()
    el = gerar_cabecalho_mec(styles, escola.nome, escola.provincia, escola.distrito, compacto=True, escola=escola)
    el.append(Paragraph('<b>GUIÃO DE CORRECÇÃO (GABARITO)</b>', ParagraphStyle('GbT', fontName='Times-Bold', alignment=1)))
    el.append(Spacer(1, 0.25 * cm))
    sb, sr = ParagraphStyle('GbB', fontName='Times-Bold'), ParagraphStyle('GbRr', fontName='Times-Roman')
    letras = 'ABCDEF'[:g.n_alternativas]
    info = [['Gabarito', g.nome, 'Nº de perguntas', str(g.n_perguntas)],
            ['Alternativas', f'{g.n_alternativas} ({letras[0]}–{letras[-1]})', 'Versões', ' / '.join(g.versoes) if g.versoes else 'única'],
            ['Professor(a)', professor_nome or '—', 'Emitido em', date.today().strftime('%d/%m/%Y')]]
    ti = Table([[Paragraph(_esc(c), sb if k % 2 == 0 else sr) for k, c in enumerate(r)] for r in info],
               colWidths=[2.6 * cm, 6.4 * cm, 3.2 * cm, 5.3 * cm])
    ti.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), 1.2, AZUL), ('INNERGRID', (0, 0), (-1, -1), 0.4, CINZA),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('BACKGROUND', (0, 0), (0, -1), ZEBRA), ('BACKGROUND', (2, 0), (2, -1), ZEBRA)]))
    el += [ti, Spacer(1, 0.4 * cm)]
    for versao in (g.versoes or ['-']):
        chave = (g.gabaritos or {}).get(versao) or ''
        titulo = 'Respostas certas' if versao == '-' else f'Versão {versao} — respostas certas'
        bloco = [Paragraph(f'<b>{_esc(titulo)}</b>', ParagraphStyle('GbV', fontName='Times-Bold')), Spacer(1, 0.15 * cm),
                 _tabela_versao(chave), Spacer(1, 0.2 * cm),
                 Paragraph('Em sequência: <font face="Courier-Bold">' + _esc(' '.join(chave[i:i + 10] for i in range(0, len(chave), 10))) + '</font>', sr),
                 Spacer(1, 0.5 * cm)]
        el.append(KeepTogether(bloco))
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.0 * cm,
                      bottomMargin=1.2 * cm).build(el)
    return buf.getvalue()
