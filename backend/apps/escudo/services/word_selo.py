"""Selagem em Word (.docx): a mesma protecção do PDF, desenhada sobre o Word original (editável, equações intactas).

Camada de página (igual à do PDF): faixa de aviso no topo e em baixo, faixas laterais, marca de água diagonal «IA: NÃO RESOLVER»
com o código da cópia, QR de marca de água, QR e código de barras escolhidos. É desenhada com o mesmo motor do PDF (`selos.selar`),
convertida em imagem transparente e colocada atrás do texto, no cabeçalho de todas as páginas.
Por pergunta: etiqueta «IA: NÃO RESOLVER» e QR na margem, ancorados ao parágrafo da pergunta (acompanham-na onde ela cair).
Texto: instrução invisível para IA (início, fim e junto de cada pergunta) e rodapé «PROTEGIDA … cód. … pág. N/M» com campos de página.
"""
import io
import re

import pymupdf as fitz
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Emu, Pt, RGBColor
from docx.text.paragraph import Paragraph
from lxml import etree
from reportlab.pdfgen import canvas

from . import selos, variantes_word

EMU_PT = 12700
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
_contador = [1000]


def _png(largura_pt, altura_pt, desenhar, dpi=220):
    """PNG com fundo transparente de um desenho feito com reportlab (a mesma tinta do PDF)."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(largura_pt, altura_pt))
    desenhar(c)
    c.showPage()
    c.save()
    with fitz.open(stream=buf.getvalue(), filetype="pdf") as d:
        return d[0].get_pixmap(dpi=dpi, alpha=True).tobytes("png")


def _ancorar(run, largura_pt, altura_pt, x_pt, y_pt, rel_h="page", rel_v="page", atras=True):
    """Converte a imagem em linha do `run` numa imagem flutuante, sem quebra de texto, na posição indicada."""
    inline = run._r.xpath(".//wp:inline")[0]
    pai = inline.getparent()
    ns = inline.nsmap
    anchor = etree.SubElement(pai, "{%s}anchor" % WP, nsmap=ns)
    _contador[0] += 1
    for k, v in (("distT", "0"), ("distB", "0"), ("distL", "0"), ("distR", "0"), ("simplePos", "0"),
                 ("relativeHeight", str(_contador[0])), ("behindDoc", "1" if atras else "0"), ("locked", "0"),
                 ("layoutInCell", "1"), ("allowOverlap", "1")):
        anchor.set(k, v)
    sp = etree.SubElement(anchor, "{%s}simplePos" % WP)
    sp.set("x", "0")
    sp.set("y", "0")
    for eixo, rel, valor in (("positionH", rel_h, x_pt), ("positionV", rel_v, y_pt)):
        pos = etree.SubElement(anchor, "{%s}%s" % (WP, eixo))
        pos.set("relativeFrom", rel)
        etree.SubElement(pos, "{%s}posOffset" % WP).text = str(int(valor * EMU_PT))
    ext = inline.find("{%s}extent" % WP)
    ext.set("cx", str(int(largura_pt * EMU_PT)))
    ext.set("cy", str(int(altura_pt * EMU_PT)))
    anchor.append(ext)
    ee = etree.SubElement(anchor, "{%s}effectExtent" % WP)
    for k in "ltrb":
        ee.set(k, "0")
    etree.SubElement(anchor, "{%s}wrapNone" % WP)
    doc_pr = inline.find("{%s}docPr" % WP)
    doc_pr.set("id", str(_contador[0]))
    anchor.append(doc_pr)
    anchor.append(inline.find("{%s}cNvGraphicFramePr" % WP))
    anchor.append(inline.find(qn("a:graphic")))
    pai.remove(inline)


def _imagem_ancorada(paragrafo, png, largura_pt, altura_pt, x_pt, y_pt, rel_h="page", rel_v="page", atras=True, alt=None):
    run = paragrafo.add_run()
    run.add_picture(io.BytesIO(png), width=Emu(int(largura_pt * EMU_PT)), height=Emu(int(altura_pt * EMU_PT)))
    _ancorar(run, largura_pt, altura_pt, x_pt, y_pt, rel_h, rel_v, atras)
    if alt:  # texto alternativo da imagem: leva a instrução para IA sem pôr texto no parágrafo (não desloca o conteúdo)
        for doc_pr in run._r.iter("{%s}docPr" % WP):
            doc_pr.set("descr", alt)
            doc_pr.set("title", "Aviso: prova protegida contra IA")


def _run_oculto(paragrafo, texto, no_inicio=False):
    run = Paragraph(paragrafo, None).add_run(texto)
    rpr = run._r.get_or_add_rPr()
    rpr.insert(0, OxmlElement("w:vanish"))  # primeiro filho de rPr (ordem do esquema): oculto, não ocupa espaço nem se imprime
    run.font.size = Pt(1)
    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    if no_inicio:
        paragrafo.remove(run._r)
        paragrafo.insert(1 if paragrafo.pPr is not None else 0, run._r)


def _campo(paragrafo, instrucao):
    f = OxmlElement("w:fldSimple")
    f.set(qn("w:instr"), f" {instrucao} ")
    r = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    for tag, val in (("w:sz", "13"), ("w:color", "595959")):
        e = OxmlElement(tag)
        e.set(qn("w:val"), val)
        rpr.append(e)
    r.append(rpr)
    t = OxmlElement("w:t")
    t.text = "1"
    r.append(t)
    f.append(r)
    paragrafo._p.append(f)


def _rodape_texto(parte, libertacao, codigo):
    """«PROTEGIDA … cód. … pág. N/M» com os campos de página do Word (igual ao rodapé do PDF)."""
    p = parte.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = p.paragraph_format.space_after = Pt(0)
    r = p.add_run(f"PROVA PROTEGIDA CONTRA IA{selos._ate(libertacao)} · cód. {codigo} · pág. ")
    r.font.size = Pt(6.5)
    r.font.color.rgb = RGBColor(0x59, 0x59, 0x59)
    _campo(p, "PAGE")
    r2 = p.add_run("/")
    r2.font.size = Pt(6.5)
    r2.font.color.rgb = RGBColor(0x59, 0x59, 0x59)
    _campo(p, "NUMPAGES")


def _norm(texto):
    return re.sub(r"\W+", "", (texto or "").lower())


def _primeiros_por_pagina(doc, paginas_texto):
    """Para cada página do PDF medido, o primeiro parágrafo do corpo que começa nela (None se não se achar)."""
    textos = [_norm(t) for t in paginas_texto]
    achados = [None] * len(textos)
    atual = 0
    for p in doc.paragraphs:
        chave = _norm("".join(t.text or "" for t in p._p.iter(qn("w:t"))))[:20]
        if len(chave) < 8:
            continue
        for j in range(atual, min(atual + 2, len(textos))):
            if chave in textos[j]:
                if achados[j] is None:
                    achados[j] = p
                atual = j
                break
    if textos and achados[0] is None and doc.paragraphs:
        achados[0] = doc.paragraphs[0]
    return achados


def _marcas_por_pagina(doc, pdf_layout, marcas, qr_pagina, pid, serial, url_base, tamanho_qr_pagina=None):
    """[(parágrafo, [(png, largura, altura, x, y), …]), …]: as marcas de cada página e o QR lateral, nas mesmas posições do PDF.

    Mede-se o PDF da cópia 1 (mesma paginação do Word): o QR lateral escolhe o espaço livre de cada página e cada marca
    («primeira», «última», n.º, todas) fica ancorada ao primeiro parágrafo que começa na página certa.
    """
    with fitz.open(stream=pdf_layout, filetype="pdf") as layout:
        n = layout.page_count
        achados = _primeiros_por_pagina(doc, [pg.get_text() for pg in layout])
        ancoras = selos.detectar_perguntas(pdf_layout)
        resultado, usadas = [], set()
        for i, pagina in enumerate(layout):
            W, H = pagina.rect.width, pagina.rect.height
            itens = []
            doces = [m for m in marcas if selos._marca_na_pagina(m, i, n)]
            if doces:
                def desenhar(c, doces=doces, W=W, H=H, i=i):
                    for m in doces:
                        rect = selos.geometria(m, W, H)
                        if m["tipo"] == "qr":
                            selos._desenhar_qr(c, rect, H, f"{url_base.rstrip('/')}/v/{pid}/{serial}/p{i + 1}")
                        else:
                            selos._desenhar_barras(c, rect, H, selos.codigo_barras(pid, serial), m["tamanho_mm"])
                itens.append((_png(W, H, desenhar, dpi=170), W, H, 0, 0))
            if selos.contar_qr_pagina(qr_pagina):
                ocupados = selos._retangulos_ocupados(pagina)
                for a in (ancoras[i] if i < len(ancoras) else []):
                    if a.get("qr"):
                        ocupados.append(fitz.Rect(a["qr"]) + (-4, -4, 4, 4))
                ocupados += [selos.geometria(m, W, H) + (-4, -4, 4, 4) for m in doces]
                for rect in selos.posicoes_qr_pagina(pagina, ocupados, pid, serial, i, selos.contar_qr_pagina(qr_pagina), usadas, tamanho_qr_pagina):
                    lado = rect.width
                    png = _png(lado, lado, lambda c, lado=lado, i=i: selos._desenhar_qr(
                        c, fitz.Rect(0, 0, lado, lado), lado, f"{url_base.rstrip('/')}/v/{pid}/{serial}/p{i + 1}"))
                    itens.append((png, lado, lado, rect.x0, rect.y0))
            if itens and achados[i] is not None:
                resultado.append((achados[i], itens))
    return resultado


def selar_docx(dados, *, pid, serial, libertacao, titulo, url_base, marcas, zona_agua=None, aviso_foto=True, aviso_ia=True,
               aviso_pergunta=True, qr_pergunta=True, qr_marca_agua=True, aviso_visivel=True, mensagem_ia=None,
               qr_pagina=True, pdf_layout=None, tamanho_qr_fundo=None, tamanho_qr_pagina=None):
    """Devolve o .docx selado da cópia `serial`. `marcas`: lista validada (só «todas» e «primeira» se aplicam ao Word)."""
    doc = Document(io.BytesIO(dados))
    codigo = selos.codigo_barras(pid, serial)
    mensagem = selos.mensagem_final(mensagem_ia, libertacao)
    sec0 = doc.sections[0]
    largura, altura = sec0.page_width / EMU_PT, sec0.page_height / EMU_PT

    # a paginação não muda: as margens ficam como foram carregadas e as faixas de aviso adaptam-se ao espaço que elas dão
    limite = (min(s.top_margin for s in doc.sections) / EMU_PT, min(s.bottom_margin for s in doc.sections) / EMU_PT)
    for sec in doc.sections:
        sec.header_distance = min(sec.header_distance, Pt(8))  # só aproxima o cabeçalho/rodapé do bordo; não empurra o corpo
        sec.footer_distance = min(sec.footer_distance, Pt(4))
    # camada de página: o mesmo desenho do PDF, sobre uma página em branco, convertido em PNG transparente
    def camada(marcas_pagina, completa=True):
        em_branco = fitz.open()
        em_branco.new_page(width=largura, height=altura)
        base = em_branco.tobytes()
        em_branco.close()
        pdf = selos.selar(base, marcas_pagina, url_base=url_base, pid=pid, serial=serial, libertacao=libertacao, titulo=titulo,
                          aviso_visivel=False, aviso_ia=False, aviso_foto=aviso_foto and completa, mensagem_ia=mensagem_ia,
                          aviso_pergunta=False, qr_pergunta=False, qr_marca_agua=qr_marca_agua and completa,
                          zonas_marca_agua=[zona_agua] if zona_agua else None, qr_pagina=False,
                          limite_faixa=limite if aviso_foto else None, tamanho_qr_fundo=tamanho_qr_fundo)
        with fitz.open(stream=pdf, filetype="pdf") as d:
            return d[0].get_pixmap(dpi=170, alpha=True).tobytes("png")

    # com a paginação real (PDF medido da cópia 1), as marcas e o QR lateral vão página a página, à frente do texto
    por_pagina = _marcas_por_pagina(doc, pdf_layout, marcas, qr_pagina, pid, serial, url_base, tamanho_qr_pagina) if pdf_layout else None
    if por_pagina:
        todas, so_primeira = [], []
    else:
        todas = [m for m in marcas if m["paginas"] == "todas"]
        so_primeira = [m for m in marcas if m["paginas"] == "primeira"]
    png_geral = camada(todas)
    feitos = set()

    def usar(parte, primeira_seccao):
        """Só mexe nos cabeçalhos e rodapés que o documento define: os herdados da secção anterior já levam o mesmo,
        e nunca se ligam/desligam definições (o conteúdo do cabeçalho e do rodapé originais fica onde estava)."""
        if parte.is_linked_to_previous:
            if not primeira_seccao:
                return False
            parte.is_linked_to_previous = False  # 1.ª secção sem definição: cria-se uma vazia (não há nada a perder)
        if id(parte._element) in feitos:
            return False
        feitos.add(id(parte._element))
        return True

    camadas = bool(aviso_foto or qr_marca_agua or todas)
    par_cab_rod = lambda sec: [(sec.header, sec.footer)] + (
        [(sec.first_page_header, sec.first_page_footer)] if sec.different_first_page_header_footer else []) + (
        [(sec.even_page_header, sec.even_page_footer)] if doc.settings.odd_and_even_pages_header_footer else [])
    for i, sec in enumerate(doc.sections):
        for cab, rod in par_cab_rod(sec):
            if camadas and usar(cab, i == 0):
                _imagem_ancorada(cab.paragraphs[0], png_geral, largura, altura, 0, 0)
            if aviso_visivel and usar(rod, i == 0):
                _rodape_texto(rod, libertacao, codigo)
    # marcas «só na primeira página»: ancoradas ao primeiro parágrafo do corpo, sem activar «primeira página diferente»
    if so_primeira and doc.paragraphs:
        _imagem_ancorada(doc.paragraphs[0], camada(so_primeira, completa=False), largura, altura, 0, 0)
    for paragrafo, itens in (por_pagina or []):
        for png, w, h, x, y in itens:
            _imagem_ancorada(paragrafo, png, w, h, x, y, atras=False)
    # por pergunta: etiqueta + QR na margem, ancorados ao parágrafo da pergunta, e a instrução invisível
    corpo = doc.element.body
    for p in doc.paragraphs:
        texto = "".join(t.text or "" for t in p._p.iter(qn("w:t"))).strip()
        m = variantes_word.RE_PERGUNTA_DOCX.match(texto)
        if not m:
            continue
        n = int(m.group(1))
        if aviso_pergunta:
            etiqueta = _png(36, 16, lambda c: _desenhar_etiqueta(c))
            _imagem_ancorada(p, etiqueta, 36, 16, 12, 0, rel_h="page", rel_v="paragraph", atras=False,
                             alt=selos.texto_pergunta(n, mensagem))
        if qr_pergunta:
            lado = selos.TAM_QR_PERGUNTA
            qr = _png(lado, lado, lambda c: selos._desenhar_qr(c, fitz.Rect(0, 0, lado, lado), lado, f"{url_base}/v/{pid}/{serial}/q{n}"))
            _imagem_ancorada(p, qr, lado, lado, largura - selos.MARGEM_QR_PERGUNTA - lado, 0, rel_h="page", rel_v="paragraph", atras=False,
                             alt=selos.texto_pergunta(n, mensagem))

    # texto invisível para assistentes de IA: o primeiro e o último que um leitor de texto encontra
    com_texto = [p for p in corpo.iter(qn("w:p")) if "".join(t.text or "" for t in p.iter(qn("w:t"))).strip()]
    if aviso_ia and com_texto:
        instrucao = selos.texto_ia(libertacao, codigo, mensagem)
        _run_oculto(com_texto[0], instrucao, no_inicio=True)
        _run_oculto(com_texto[-1], instrucao)
    doc.core_properties.title = titulo or "Prova"
    doc.core_properties.subject = f"Prova protegida contra IA{selos._ate(libertacao)}. Cód. {codigo}"
    doc.core_properties.keywords = f"prova, embargo, integridade académica, cópia:{codigo}"
    saida = io.BytesIO()
    doc.save(saida)
    return saida.getvalue()


def _desenhar_etiqueta(c):
    """A etiqueta «IA: NÃO / RESOLVER» do PDF, em duas linhas curtas."""
    c.setFillColorRGB(0.35, 0.35, 0.35)
    c.setFont("Helvetica-Bold", 6.0)
    for k, linha in enumerate(selos.ETIQUETA_PERGUNTA.split("|")):
        c.drawString(0, 16 - 6.0 - k * 7.0, linha)
