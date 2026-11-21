# -*- coding: utf-8 -*-
"""Gera o guiao de resolucao em PDF e Word (.docx) a partir de um modulo de conteudo.

Uso:  python -I build_resolucao.py <conteudo.py> <pasta_saida>

O modulo de conteudo define:
  META    = {"cabecalho":[...linhas...], "titulo":"...", "subtitulo":"...", "rodape":"...", "base":"nome_ficheiro"}
  CHAVE   = {1:"B", 2:"A", ...}
  QUESTOES= [ {"n":1,"tipo":"Calculo","enun":[T(..),M(..)],"passos":[T(..),M(..)],"resp":"B","nota":"opcional"}, ...]
  MATRIZ  = [("Conteudo","1 a 4",4,2.0), ...]   (opcional)
  OBS     = ["observacao 1", ...]                  (opcional)
  GRELHA_PDF / GRELHA_PNG = caminhos da folha de respostas original ja sinalizada (opcional)
"""
import os, sys, importlib.util, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eqrender as E

CM = 28.3465
MAXW_PDF = 12.9 * CM


def load(path):
    spec = importlib.util.spec_from_file_location("conteudo", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def T(s):
    return ("t", s)


def M(*s):
    return ("m", list(s) if len(s) > 1 else s[0])


def opcoes(*ex):
    """Alineas A. B. C. D. em formato matematico; parte em duas linhas se nao couberem numa."""
    def linha(idx):
        out = []
        for k, i in enumerate(idx):
            if k:
                out.append(("sp", 50))
            out.append("\\mathbf{%s.}\\ %s" % ("ABCD"[i], ex[i]))
        return out
    one = linha(range(len(ex)))
    if E.render(one)[1] <= MAXW_PDF:
        return ("m", one)
    return ("mm", [linha([0, 1]), linha([2, 3])])


# ------------------------------------------------------------------ PDF
def build_pdf(c, outdir, imgdir):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
                                    Table, TableStyle, Image, KeepTogether, PageBreak)
    from reportlab.pdfgen import canvas as rl_canvas

    import matplotlib
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    fd = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
    pdfmetrics.registerFont(TTFont("STIX", os.path.join(fd, "STIXGeneral.ttf")))
    pdfmetrics.registerFont(TTFont("STIX-B", os.path.join(fd, "STIXGeneralBol.ttf")))
    pdfmetrics.registerFont(TTFont("STIX-I", os.path.join(fd, "STIXGeneralItalic.ttf")))
    pdfmetrics.registerFont(TTFont("STIX-BI", os.path.join(fd, "STIXGeneralBolIta.ttf")))
    pdfmetrics.registerFontFamily("STIX", normal="STIX", bold="STIX-B", italic="STIX-I", boldItalic="STIX-BI")
    base = ParagraphStyle("b", fontName="STIX", fontSize=10.5, leading=13.2)
    bold = ParagraphStyle("bold", parent=base, fontName="STIX-B")
    ital = ParagraphStyle("ital", parent=base, fontName="STIX-I", textColor=colors.HexColor("#333333"))
    cen = ParagraphStyle("cen", parent=base, alignment=1)
    cenb = ParagraphStyle("cenb", parent=cen, fontName="STIX-B", fontSize=12.5, leading=15)
    h1 = ParagraphStyle("h1", parent=base, fontName="STIX-B", fontSize=12.5, leading=15, spaceBefore=8, spaceAfter=5)
    passo = ParagraphStyle("p", parent=base, spaceBefore=3, spaceAfter=1)
    cell = ParagraphStyle("c", parent=base, alignment=1)
    cellb = ParagraphStyle("cb", parent=cell, fontName="STIX-B")

    def esc(s):
        s = s.replace("✓", "(confere)")
        s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"__(.+?)__", r"<i>\1</i>", s)
        return s

    def pic(spec, maxw=MAXW_PDF, align="CENTER"):
        path, w, h = E.render(spec)
        if w > maxw:
            h = h * maxw / w
            w = maxw
        im = Image(path, width=w, height=h)
        im.hAlign = align
        return im

    def flow(items, sty=passo):
        out = []
        for kind, val in items:
            if kind == "t":
                out.append(Paragraph(esc(val), sty))
            elif kind == "mm":
                out += [pic(v) for v in val]
            else:
                out.append(pic(val))
        return out

    story = []
    for ln in c.META["cabecalho"]:
        story.append(Paragraph(esc(ln), cenb if ln == c.META["cabecalho"][0] else cen))
    story.append(Spacer(1, 5))
    story.append(Paragraph(esc(c.META["titulo"]), cenb))
    story.append(Paragraph(esc(c.META.get("subtitulo", "")), cen))
    story.append(Spacer(1, 6))

    # 1. chave de respostas
    story.append(Paragraph("1. Chave de respostas", h1))
    rows = []
    for ini in range(1, 41, 10):
        rows.append([str(k) for k in range(ini, ini + 10)])
        rows.append([c.CHAVE[k] for k in range(ini, ini + 10)])
    t = Table([[Paragraph(x, cellb if (i % 2 == 0) else cell) for x in r] for i, r in enumerate(rows)],
              colWidths=[1.8 * cm] * 10)
    st = [("GRID", (0, 0), (-1, -1), 0.6, colors.black), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    for i in range(0, len(rows), 2):
        st.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#E3E7F0")))
    t.setStyle(TableStyle(st))
    story.append(t)

    # 2. matriz
    if getattr(c, "MATRIZ", None):
        story.append(Paragraph("2. Matriz de especificação", h1))
        data = [[Paragraph("Conteúdos", cellb), Paragraph("Questões", cellb), Paragraph("N.º", cellb), Paragraph("Valores", cellb)]]
        tn = 0.0; tv = 0.0
        for nome, q, n, v in c.MATRIZ:
            data.append([Paragraph(esc(nome), base), Paragraph(q, cell), Paragraph(str(n), cell), Paragraph(("%.1f" % v).replace(".", ","), cell)])
            tn += n; tv += v
        data.append([Paragraph("Total", bold), Paragraph("1 a %d" % int(tn), cellb), Paragraph(str(int(tn)), cellb), Paragraph(("%.1f" % tv).replace(".", ","), cellb)])
        mt = Table(data, colWidths=[10.2 * cm, 3 * cm, 2.2 * cm, 2.6 * cm], repeatRows=1)
        mt.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.6, colors.black), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E3E7F0")),
                                ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        story.append(mt)

    if getattr(c, "OBS", None):
        story.append(Paragraph("Observações sobre o enunciado", h1))
        for o in c.OBS:
            story.append(Paragraph("• " + esc(o), base))
            story.append(Spacer(1, 2))

    # 3. resolucao
    story.append(PageBreak())
    story.append(Paragraph("3. Resolução das questões", h1))
    head = [Paragraph("N.º", cellb), Paragraph("Resp.", cellb), Paragraph("Tipo", cellb), Paragraph("Resolução", cellb)]
    data = [head]
    for q in c.QUESTOES:
        res = [Paragraph(esc("__Enunciado.__"), ital)] + flow(q["enun"], base)
        res.append(Spacer(1, 3))
        res.append(Paragraph(esc("**Resolução passo a passo.**"), base))
        res += flow(q["passos"])
        if q.get("nota"):
            res.append(Spacer(1, 2))
            res.append(Paragraph(esc("__Nota:__ " + q["nota"]), ital))
        res.append(Spacer(1, 3))
        res.append(Paragraph(esc("**Resposta: alínea %s.**" % q["resp"]), base))
        data.append([Paragraph(str(q["n_label"] if "n_label" in q else q["n"]), cellb), Paragraph(q["resp"], cellb),
                     Paragraph(esc(q["tipo"]), cell), res])
    rt = Table(data, colWidths=[1.2 * cm, 1.3 * cm, 2.3 * cm, 13.2 * cm], repeatRows=1, splitInRow=1)
    rt.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.6, colors.black), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E3E7F0")),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("VALIGN", (0, 0), (2, -1), "MIDDLE"),
                            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story.append(rt)

    class NC(rl_canvas.Canvas):
        def __init__(s, *a, **k):
            super().__init__(*a, **k); s._p = []
        def showPage(s):
            s._p.append(dict(s.__dict__)); s._startPage()
        def save(s):
            n = len(s._p)
            for st_ in s._p:
                s.__dict__.update(st_)
                s.setFont("STIX", 8.5)
                s.drawString(1.5 * cm, 0.9 * cm, c.META["rodape"] + "  |  Pág. %d de %d" % (s._pageNumber, n))
                super().showPage()
            super().save()

    out = os.path.join(outdir, c.META["base"] + "_so_resolucao.pdf")
    doc = BaseDocTemplate(out, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.4 * cm, bottomMargin=1.5 * cm,
                          title=c.META["titulo"], author="SIGE")
    doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(1.5 * cm, 1.5 * cm, A4[0] - 3 * cm, A4[1] - 2.9 * cm, id="f")])])
    doc.build(story, canvasmaker=NC)

    final = os.path.join(outdir, c.META["base"] + ".pdf")
    import pymupdf
    res = pymupdf.open(out)
    if getattr(c, "GRELHA_PDF", None) and os.path.exists(c.GRELHA_PDF):
        g = pymupdf.open(c.GRELHA_PDF)
        res.insert_pdf(g, from_page=0, to_page=0, start_at=0)
    res.save(final)
    res.close()
    os.remove(out)
    return final


# ------------------------------------------------------------------ DOCX
def build_docx(c, outdir):
    from docx import Document
    from docx.shared import Pt, Cm, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    d = Document()
    sec = d.sections[0]
    sec.page_width = Cm(21); sec.page_height = Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(1.5); sec.top_margin = Cm(1.5); sec.bottom_margin = Cm(1.6)
    stn = d.styles["Normal"]
    stn.font.name = "Times New Roman"; stn.font.size = Pt(11)
    stn.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    stn.paragraph_format.space_after = Pt(2); stn.paragraph_format.space_before = Pt(0)

    def para(container, text="", bold=False, italic=False, size=None, align=None, after=None):
        p = container.add_paragraph()
        text = text.replace("✓", "(confere)")
        parts = re.split(r"(\*\*.+?\*\*|__.+?__)", text)
        for part in parts:
            if not part:
                continue
            b, i = bold, italic
            if part.startswith("**"):
                part = part[2:-2]; b = True
            elif part.startswith("__"):
                part = part[2:-2]; i = True
            r = p.add_run(part); r.bold = b; r.italic = i
            r.font.name = "Times New Roman"
            if size: r.font.size = Pt(size)
        if align == "c": p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if after is not None: p.paragraph_format.space_after = Pt(after)
        return p

    def shade(cell, hexcol):
        tcPr = cell._tc.get_or_add_tcPr()
        sh = OxmlElement("w:shd"); sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), hexcol)
        tcPr.append(sh)

    def setw(cell, cm):
        cell.width = Cm(cm)
        tcPr = cell._tc.get_or_add_tcPr()
        w = OxmlElement("w:tcW"); w.set(qn("w:w"), str(int(cm * 567))); w.set(qn("w:type"), "dxa")
        for old in tcPr.findall(qn("w:tcW")):
            tcPr.remove(old)
        tcPr.append(w)

    def addpic(container, spec, maxcm=12.9):
        path, w, h = E.render(spec)
        win = w / 72.0
        win = min(win, maxcm / 2.54)
        p = container.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(2); p.paragraph_format.space_after = Pt(2)
        p.add_run().add_picture(path, width=Inches(win))

    def flow(cell, items):
        for kind, val in items:
            if kind == "t":
                para(cell, val, size=10.5)
            elif kind == "mm":
                for v in val:
                    addpic(cell, v)
            else:
                addpic(cell, val)

    # folha de respostas sinalizada (original)
    if getattr(c, "GRELHA_PNG", None) and os.path.exists(c.GRELHA_PNG):
        para(d, "Folha de respostas original sinalizada", bold=True, size=12, align="c", after=4)
        p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(c.GRELHA_PNG, height=Cm(25.2))
        d.add_page_break()

    for i, ln in enumerate(c.META["cabecalho"]):
        para(d, ln, bold=(i == 0), size=12.5 if i == 0 else 11, align="c", after=0)
    para(d, "", after=2)
    para(d, c.META["titulo"], bold=True, size=13, align="c", after=0)
    para(d, c.META.get("subtitulo", ""), size=11, align="c", after=6)

    para(d, "1. Chave de respostas", bold=True, size=12.5, after=3)
    t = d.add_table(rows=8, cols=10); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for blk, ini in enumerate(range(1, 41, 10)):
        for j in range(10):
            a = t.cell(blk * 2, j); b = t.cell(blk * 2 + 1, j)
            for cc, txt, bd in ((a, str(ini + j), True), (b, c.CHAVE[ini + j], False)):
                cc.text = ""; pr = cc.paragraphs[0]; pr.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = pr.add_run(txt); r.bold = bd; r.font.name = "Times New Roman"
                setw(cc, 1.8)
            shade(a, "E3E7F0")

    if getattr(c, "MATRIZ", None):
        para(d, "", after=2)
        para(d, "2. Matriz de especificação", bold=True, size=12.5, after=3)
        t = d.add_table(rows=1, cols=4); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for j, (h, w) in enumerate(zip(["Conteúdos", "Questões", "N.º", "Valores"], [10.2, 3, 2.2, 2.6])):
            cc = t.rows[0].cells[j]; cc.text = ""; r = cc.paragraphs[0].add_run(h); r.bold = True
            cc.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER; shade(cc, "E3E7F0"); setw(cc, w)
        tn = 0; tv = 0.0
        for nome, q, n, v in c.MATRIZ:
            row = t.add_row().cells
            vals = [nome, q, str(n), ("%.1f" % v).replace(".", ",")]
            for j, (x, w) in enumerate(zip(vals, [10.2, 3, 2.2, 2.6])):
                row[j].text = ""; r = row[j].paragraphs[0].add_run(x)
                if j: row[j].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                setw(row[j], w)
            tn += n; tv += v
        row = t.add_row().cells
        for j, (x, w) in enumerate(zip(["Total", "1 a %d" % tn, str(tn), ("%.1f" % tv).replace(".", ",")], [10.2, 3, 2.2, 2.6])):
            row[j].text = ""; r = row[j].paragraphs[0].add_run(x); r.bold = True
            if j: row[j].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            setw(row[j], w)

    if getattr(c, "OBS", None):
        para(d, "", after=2)
        para(d, "Observações sobre o enunciado", bold=True, size=12.5, after=3)
        for o in c.OBS:
            para(d, "• " + o, size=10.5)

    d.add_page_break()
    para(d, "3. Resolução das questões", bold=True, size=12.5, after=3)
    t = d.add_table(rows=1, cols=4); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    widths = [1.2, 1.3, 2.3, 13.2]
    for j, h in enumerate(["N.º", "Resp.", "Tipo", "Resolução"]):
        cc = t.rows[0].cells[j]; cc.text = ""; r = cc.paragraphs[0].add_run(h); r.bold = True
        cc.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER; shade(cc, "E3E7F0"); setw(cc, widths[j])
    trPr = t.rows[0]._tr.get_or_add_trPr(); th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
    for q in c.QUESTOES:
        row = t.add_row().cells
        for j, txt in enumerate([str(q.get("n_label", q["n"])), q["resp"], q["tipo"]]):
            row[j].text = ""; r = row[j].paragraphs[0].add_run(txt); r.bold = j < 2
            row[j].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            row[j].vertical_alignment = WD_ALIGN_VERTICAL.CENTER; setw(row[j], widths[j])
        cell = row[3]; setw(cell, widths[3]); cell.text = ""
        first = cell.paragraphs[0]; r = first.add_run("Enunciado."); r.italic = True
        flow(cell, q["enun"])
        para(cell, "**Resolução passo a passo.**", size=10.5)
        flow(cell, q["passos"])
        if q.get("nota"):
            para(cell, "__Nota:__ " + q["nota"], size=10)
        para(cell, "**Resposta: alínea %s.**" % q["resp"], size=10.5)

    # rodape com numero de pagina
    fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = fp.add_run(c.META["rodape"] + "  |  Pág. "); r.font.size = Pt(8.5)
    r2 = fp.add_run(); r2.font.size = Pt(8.5)
    for typ, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        if typ:
            e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), typ)
        else:
            e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = txt
        r2._r.append(e)

    out = os.path.join(outdir, c.META["base"] + ".docx")
    d.save(out)
    return out


if __name__ == "__main__":
    outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    imgdir = os.path.join(outdir, "_eq")
    E.set_outdir(imgdir)
    c = load(sys.argv[1])
    p = build_pdf(c, outdir, imgdir)
    w = build_docx(c, outdir)
    print(p); print(w)
