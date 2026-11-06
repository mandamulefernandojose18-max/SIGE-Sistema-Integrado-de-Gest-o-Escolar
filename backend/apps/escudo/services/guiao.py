"""Guião (resolução detalhada) em Word e PDF: passos numerados, equações em duas dimensões e a opção correcta no fim.

O Word usa equações nativas (OMML); o PDF sai da conversão desse Word, por isso as fórmulas são iguais nos dois formatos.
"""
import io
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from lxml import etree

from . import conversao
from .latex_omml import M_NS, latex_para_omml

FONTE = "Times New Roman"
RE_MATEMATICA = re.compile(r"(\$[^$]+\$)")


def _fonte(run, tamanho=12, negrito=None, italico=None, cor=None):
    run.font.name = FONTE
    run._r.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), FONTE)
    run.font.size = Pt(tamanho)
    if negrito is not None:
        run.bold = negrito
    if italico is not None:
        run.italic = italico
    if cor:
        run.font.color.rgb = RGBColor(*cor)


def _texto(p, texto, tamanho=12, negrito=None, italico=None, cor=None):
    """Texto com matemática: o que está entre $…$ vira equação nativa, o resto texto normal."""
    for parte in RE_MATEMATICA.split(texto or ""):
        if len(parte) > 2 and parte.startswith("$") and parte.endswith("$"):
            omml = latex_para_omml(parte[1:-1])
            if omml:
                p._p.append(etree.fromstring(omml))
                continue
            parte = parte[1:-1]
        if parte:
            _fonte(p.add_run(parte), tamanho, negrito, italico, cor)


def _equacao(doc, latex):
    """Equação sozinha numa linha, centrada, na forma matemática (não linear)."""
    omml = latex_para_omml(latex)
    if not omml:
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(4)
    par = etree.SubElement(p._p, "{%s}oMathPara" % M_NS, nsmap={"m": M_NS})
    par.append(etree.fromstring(omml))


def _par(doc, antes=0, depois=4, esquerda=0.0):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(antes)
    p.paragraph_format.space_after = Pt(depois)
    p.paragraph_format.left_indent = Pt(esquerda)
    return p


def _campo(p, instrucao):
    f = OxmlElement("w:fldSimple")
    f.set(qn("w:instr"), f" {instrucao} ")
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = "1"
    r.append(t)
    f.append(r)
    p._p.append(f)


def construir_docx(guiao, titulo="", disciplina="", classe="", codigo=""):
    """Devolve o .docx do Guião. `guiao` é o dicionário devolvido pela IA (ver `ia_sige.ESQUEMA`)."""
    doc = Document()
    estilo = doc.styles["Normal"]
    estilo.font.name = FONTE
    estilo.font.size = Pt(12)
    estilo.element.rPr.rFonts.set(qn("w:eastAsia"), FONTE)
    sec = doc.sections[0]
    for lado in ("left_margin", "right_margin"):
        setattr(sec, lado, Pt(62))
    sec.top_margin = sec.bottom_margin = Pt(56)

    p = _par(doc, 0, 2)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _fonte(p.add_run("GUIÃO DE CORRECÇÃO E RESOLUÇÃO DETALHADA"), 15, negrito=True)
    p = _par(doc, 0, 2)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _fonte(p.add_run(titulo or "Prova"), 13, negrito=True)
    linha = " · ".join(x for x in (disciplina, classe, f"cód. {codigo}" if codigo else "") if x)
    if linha:
        p = _par(doc, 0, 2)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _fonte(p.add_run(linha), 11)
    p = _par(doc, 4, 10)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _fonte(p.add_run("Documento reservado ao professor. Não distribuir aos alunos. Gerado pela IA do SIGE: confira antes de usar."),
           9.5, italico=True, cor=(0x8A, 0x1C, 0x1C))

    for q in guiao.get("questoes", []):
        p = _par(doc, 12, 3)
        p.paragraph_format.keep_with_next = True
        _fonte(p.add_run(f"Questão {q.get('numero', '')}"), 13, negrito=True)
        if q.get("enunciado"):
            p = _par(doc, 0, 4)
            _fonte(p.add_run("Enunciado: "), 12, negrito=True)
            _texto(p, q["enunciado"], 12, italico=True)
        if q.get("confianca") == "baixa" and q.get("observacao"):
            p = _par(doc, 0, 4)
            _texto(p, "Atenção: " + q["observacao"], 11, negrito=True, cor=(0xB0, 0x1E, 0x1E))
        p = _par(doc, 2, 2)
        p.paragraph_format.keep_with_next = True
        _fonte(p.add_run("Resolução:"), 12, negrito=True)
        for k, passo in enumerate(q.get("passos", []), 1):
            p = _par(doc, 0, 1, esquerda=10)
            p.paragraph_format.keep_with_next = bool(passo.get("equacao"))
            _fonte(p.add_run(f"{k}. "), 12, negrito=True)
            _texto(p, passo.get("descricao", ""), 12)
            if passo.get("equacao"):
                _equacao(doc, passo["equacao"])
        if q.get("resposta_final"):
            p = _par(doc, 4, 3)
            _fonte(p.add_run("Resposta: "), 12, negrito=True)
            _texto(p, q["resposta_final"], 12, negrito=True)
        if q.get("opcao_correcta"):
            p = _par(doc, 2, 3)
            _fonte(p.add_run("Opção correcta: "), 12, negrito=True, cor=(0x0B, 0x5D, 0x2E))
            _fonte(p.add_run(f"{q['opcao_correcta']}"), 13, negrito=True, cor=(0x0B, 0x5D, 0x2E))
            if q.get("texto_opcao_correcta"):
                _fonte(p.add_run(") "), 12, negrito=True, cor=(0x0B, 0x5D, 0x2E))
                _texto(p, q["texto_opcao_correcta"], 12)
            if q.get("justificacao_opcao"):
                p = _par(doc, 0, 6, esquerda=10)
                _texto(p, q["justificacao_opcao"], 10.5, italico=True)
        if q.get("confianca") == "media" and q.get("observacao"):
            p = _par(doc, 0, 4)
            _texto(p, "Nota: " + q["observacao"], 10.5, italico=True)

    if guiao.get("observacoes_gerais"):
        p = _par(doc, 14, 3)
        _fonte(p.add_run("Observações gerais"), 12, negrito=True)
        p = _par(doc, 0, 4)
        _texto(p, guiao["observacoes_gerais"], 11)

    rodape = sec.footer.paragraphs[0]
    rodape.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _fonte(rodape.add_run(f"Guião · {titulo} · cód. {codigo} · pág. ".strip()), 8.5)
    _campo(rodape, "PAGE")
    _fonte(rodape.add_run("/"), 8.5)
    _campo(rodape, "NUMPAGES")
    doc.core_properties.title = f"Guião · {titulo}"
    doc.core_properties.subject = "Resolução detalhada (reservado ao professor)"
    saida = io.BytesIO()
    doc.save(saida)
    return saida.getvalue()


def construir_pdf(docx_bytes):
    """O mesmo Guião em PDF (LibreOffice converte as equações nativas do Word)."""
    return conversao.docx_para_pdf(docx_bytes)
