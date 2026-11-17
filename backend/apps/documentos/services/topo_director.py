"""Topo de documento com o cabeçalho oficial à esquerda e a assinatura «O Director da Escola» à direita,
lado a lado, para que o carimbo (que fica sempre sobre essa assinatura) não deixe espaço vazio.

As dimensões ajustam-se sozinhas ao carimbo da escola: largura da coluna da direita = círculo (+ coluna do QR e
do código nos níveis Selo/Assinatura) e folgas acima e abaixo da linha = o que o círculo ocupa para lá do bloco.
Qualquer documento com este layout deve usar `topo_cabecalho_director` (nunca medidas fixas).
"""
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Image, Spacer, Table, TableStyle

from apps.certificados.carimbo import COLUNA_CM, DIAMETRO_CM
from apps.documentos.services.pdf_service import Paragraph, gerar_cabecalho_mec, getSampleStyleSheet

ESCALA_CARIMBO_ASSINATURA = 0.8   # a mesma de aplicar_carimbo_pdf ao carimbar sobre a assinatura
ALTURA_BLOCO_CM = 1.1             # linha + rótulo + nome (o círculo centra-se aqui)
LINHA = '________________________'


def _esc(t):
    return str(t or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def medidas_carimbo(escola):
    """(largura_direita_cm, folga_acima_cm, folga_abaixo_cm) necessárias para o carimbo da escola."""
    nivel = getattr(escola, 'carimbo_nivel', 'SELO') or 'SELO'
    d = DIAMETRO_CM * ESCALA_CARIMBO_ASSINATURA
    coluna = 0 if nivel == 'IMAGEM' else COLUNA_CM * ESCALA_CARIMBO_ASSINATURA  # QR e código só nos níveis B/C
    folga = max(0.2, d / 2 - ALTURA_BLOCO_CM / 2)
    return max(d + coluna + 0.3, 4.8), folga, folga   # no mínimo o que o nome do Director precisa numa linha


def assinatura_director_bloco(escola, largura_cm, folga_acima_cm, folga_abaixo_cm):
    st = ParagraphStyle('AsD', fontName='Times-Roman', fontSize=10, leading=12, alignment=1)
    stb = ParagraphStyle('AsDB', fontName='Times-Bold', fontSize=10, leading=12, alignment=1)
    bloco = Table([[Spacer(1, folga_acima_cm * cm)], [Paragraph(LINHA, st)], [Paragraph('O Director da Escola', stb)],
                   [Paragraph(_esc(getattr(escola, 'director_nome', '')), st)], [Spacer(1, folga_abaixo_cm * cm)]],
                  colWidths=[largura_cm * cm])
    bloco.setStyle(TableStyle([('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                               ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))
    return bloco


def topo_cabecalho_director(escola, largura_util_cm=17.0):
    """Tabela com o cabeçalho oficial (esquerda) e a assinatura do Director + espaço do carimbo (direita)."""
    dir_cm, acima, abaixo = medidas_carimbo(escola)
    esq = gerar_cabecalho_mec(getSampleStyleSheet(), escola.nome, escola.provincia, escola.distrito,
                              compacto=True, escola=escola)
    esq_w = (largura_util_cm - dir_cm) * cm
    for i, e in enumerate(esq):
        if isinstance(e, Image):  # dentro de uma célula o emblema não se centra sozinho
            c = Table([[e]], colWidths=[esq_w])
            c.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
                                   ('RIGHTPADDING', (0, 0), (-1, -1), 0), ('TOPPADDING', (0, 0), (-1, -1), 0),
                                   ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
            esq[i] = c
    topo = Table([[esq, assinatura_director_bloco(escola, dir_cm, acima, abaixo)]],
                 colWidths=[esq_w, dir_cm * cm])
    topo.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
                              ('RIGHTPADDING', (0, 0), (-1, -1), 0), ('TOPPADDING', (0, 0), (-1, -1), 0),
                              ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
    return topo
