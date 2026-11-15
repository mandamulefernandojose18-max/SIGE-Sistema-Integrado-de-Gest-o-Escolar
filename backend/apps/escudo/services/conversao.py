"""Aceita DOCX além de PDF: converte para PDF com o Microsoft Word (Windows) ou o LibreOffice (Linux/VM)."""
import io
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

WD_FORMAT_PDF = 17
MSO_AUTOMATION_SECURITY_FORCE_DISABLE = 3  # desliga macros ao abrir o ficheiro


def eh_docx(dados):
    if not dados.startswith(b"PK\x03\x04"):
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(dados)) as z:
            return "word/document.xml" in z.namelist()
    except zipfile.BadZipFile:
        return False


_M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
_PARES = {("(", ")"), ("[", "]"), ("{", "}"), ("|", "|"), ("‖", "‖"), ("⟨", "⟩"), ("⌊", "⌋"), ("⌈", "⌉"), ("", ""), ("(", ""), ("", ")")}
_PROIBIDOS = ("¿", "�", "\\{", "\\}", "\\left", "\\right", "\\(", "\\)")  # símbolos/códigos que a conversão nunca pode introduzir


def _texto_nor(texto):
    from lxml import etree
    r = etree.Element(f"{{{_M}}}r")
    rpr = etree.SubElement(r, f"{{{_M}}}rPr")
    etree.SubElement(rpr, f"{{{_M}}}nor")
    t = etree.SubElement(r, f"{{{_M}}}t")
    t.text = texto
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return r


_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
# estruturas e caracteres em que o LibreOffice costuma falhar ao importar equações do Word
_ARRISCADAS = {"d", "eqArr", "m", "groupChr", "borderBox", "box", "phant", "limLow", "limUpp", "nary", "acc", "bar", "sPre", "rad"}
_CARS_ARRISCADOS = set("[]{}|‖⟨⟩⌊⌋⌈⌉")


def _loc(el):
    return el.tag.rsplit("}", 1)[-1] if isinstance(el.tag, str) else ""


def _val(el, nome, padrao=""):
    if el is None:
        return padrao
    return el.get(f"{{{_M}}}val", padrao)


def _linear(el):
    """Texto linear (Unicode) de um elemento de equação do Word: «(a)/(b)», «x^(2)», «√(x)», «∑_(i=1)^(n) …»."""
    def filhos(nome):
        e = el.find(f"{{{_M}}}{nome}")
        return _linear(e) if e is not None else ""

    t = _loc(el)
    if t == "t":
        return el.text or ""
    if t == "f":
        return f"({filhos('num')})/({filhos('den')})"
    if t == "rad":
        g = filhos("deg")
        return (f"({g})" if g else "") + f"√({filhos('e')})"
    if t in ("sSup", "sSub", "sSubSup", "sPre"):
        base, sub, sup = filhos("e"), filhos("sub"), filhos("sup")
        pre = f"_({sub})^({sup})" if t == "sPre" else ""
        return pre + base + (f"_({sub})" if sub and t != "sPre" else "") + (f"^({sup})" if sup and t != "sPre" else "")
    if t == "nary":
        pr = el.find(f"{{{_M}}}naryPr")
        chr_ = _val(pr.find(f"{{{_M}}}chr") if pr is not None else None, "val", "") or "∫"
        sub, sup = filhos("sub"), filhos("sup")
        return chr_ + (f"_({sub})" if sub else "") + (f"^({sup})" if sup else "") + " " + filhos("e")
    if t == "d":
        pr = el.find(f"{{{_M}}}dPr")
        beg = pr.find(f"{{{_M}}}begChr") if pr is not None else None
        end = pr.find(f"{{{_M}}}endChr") if pr is not None else None
        sepe = pr.find(f"{{{_M}}}sepChr") if pr is not None else None
        b = "(" if beg is None else _val(beg, "val", "")
        e = ")" if end is None else _val(end, "val", "")
        sep = "|" if sepe is None else (_val(sepe, "val", "") or "|")
        return b + sep.join(_linear(x) for x in el.findall(f"{{{_M}}}e")) + e
    if t == "func":
        return filhos("fName") + " " + filhos("e")
    if t == "eqArr":
        return "; ".join(_linear(x) for x in el.findall(f"{{{_M}}}e"))
    if t == "m":
        return "; ".join(", ".join(_linear(c) for c in r.findall(f"{{{_M}}}e")) for r in el.findall(f"{{{_M}}}mr"))
    if t == "limLow":
        return filhos("e") + f"_({filhos('lim')})"
    if t == "limUpp":
        return filhos("e") + f"^({filhos('lim')})"
    if t == "bar":
        return filhos("e") + "̅"
    return "".join(_linear(c) for c in el if _loc(c) and not _loc(c).endswith("Pr"))


def _linearizar(raiz, tudo):
    """Troca as equações (todas, ou só as de risco) por texto linear normal do Word: nunca mais «¿» nem «\\{»."""
    from lxml import etree
    mudou = False
    for eq in list(raiz.iter(f"{{{_M}}}oMathPara", f"{{{_M}}}oMath")):
        pai = eq.getparent()
        if pai is None or _loc(pai) == "oMathPara":
            continue
        if not tudo:
            textos = "".join(x.text or "" for x in eq.iter(f"{{{_M}}}t"))
            tags = {_loc(x) for x in eq.iter() if isinstance(x.tag, str)}
            if not (tags & _ARRISCADAS or set(textos) & _CARS_ARRISCADOS):
                continue
        texto = _linear(eq).replace("​", "")
        r = etree.Element(f"{{{_W}}}r")
        t = etree.SubElement(r, f"{{{_W}}}t")
        t.text = texto
        t.set(_XML_SPACE, "preserve")
        pos = pai.index(eq)
        cauda = eq.tail
        pai.remove(eq)
        r.tail = cauda
        pai.insert(pos, r)
        mudou = True
    return mudou


def sanear_docx(dados, nivel=1):
    """Prepara o DOCX para o LibreOffice: parênteses rectos soltos das equações (intervalos como ]-13; +∞[) viram texto
    normal e delimitadores desencontrados são desfeitos; sem isto o LibreOffice desenha «¿» no lugar deles.
    nivel 2: as equações de risco (delimitadores, sistemas, matrizes, somatórios…) passam a texto linear;
    nivel 3: todas as equações passam a texto linear. Se nada houver a corrigir devolve o ficheiro tal como veio."""
    from lxml import etree
    try:
        with zipfile.ZipFile(io.BytesIO(dados)) as z:
            nomes = [n for n in z.namelist() if n.startswith("word/") and n.endswith(".xml")
                     and n.split("/")[-1].startswith(("document", "header", "footer"))]
            novos = {}
            for nome in nomes:
                raiz = etree.fromstring(z.read(nome))
                mudou = _linearizar(raiz, nivel >= 3) if nivel >= 2 else False
                for d in list(raiz.iter(f"{{{_M}}}d")):  # delimitadores com par desencontrado: ]a;b[  [a;b[
                    pr = d.find(f"{{{_M}}}dPr")
                    beg = pr.find(f"{{{_M}}}begChr") if pr is not None else None
                    end = pr.find(f"{{{_M}}}endChr") if pr is not None else None
                    b = beg.get(f"{{{_M}}}val", "(") if beg is not None else "("
                    e = end.get(f"{{{_M}}}val", ")") if end is not None else ")"
                    # só mexe em pares desencontrados com parênteses rectos (]a;b[): chavetas e parênteses ficam como vieram
                    if (b, e) in _PARES or not (set(b + e) & set("[]")) or (set(b + e) & set("{}")):
                        continue
                    pai = d.getparent()
                    pos = pai.index(d)
                    novos_nos = [_texto_nor(b)] if b else []
                    for filho in d.findall(f"{{{_M}}}e"):
                        sep = len(novos_nos) > (1 if b else 0)
                        if sep:
                            novos_nos.append(_texto_nor(d.find(f"{{{_M}}}dPr/{{{_M}}}sepChr").get(f"{{{_M}}}val", "|")
                                                        if d.find(f"{{{_M}}}dPr/{{{_M}}}sepChr") is not None else "|"))
                        novos_nos.extend(list(filho))
                    if e:
                        novos_nos.append(_texto_nor(e))
                    pai.remove(d)
                    for k, no in enumerate(novos_nos):
                        pai.insert(pos + k, no)
                    mudou = True
                for r in raiz.iter(f"{{{_M}}}r"):  # parênteses rectos soltos dentro de equações (as chavetas não se tocam:
                    t = r.find(f"{{{_M}}}t")       # em texto normal o LibreOffice escreveria «\{» no PDF)
                    if t is None or not t.text or not (set(t.text) & set("[]")) or (set(t.text) & set("{}")):
                        continue
                    pr = r.find(f"{{{_M}}}rPr")
                    if pr is None:
                        pr = etree.Element(f"{{{_M}}}rPr")
                        r.insert(0, pr)
                    if pr.find(f"{{{_M}}}nor") is None:
                        etree.SubElement(pr, f"{{{_M}}}nor")
                        mudou = True
                if mudou:
                    novos[nome] = etree.tostring(raiz, xml_declaration=True, encoding="UTF-8", standalone=True)
            if not novos:
                return dados
            saida = io.BytesIO()
            with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as w:
                for item in z.infolist():
                    w.writestr(item, novos.get(item.filename, z.read(item.filename)))
            return saida.getvalue()
    except Exception:
        return dados


def conteudo_adulterado(pdf, docx=None):
    """Texto estranho no PDF convertido («¿», «�») que não existia no DOCX de origem: a prova não pode sair assim."""
    try:
        import pymupdf as fitz
        texto = "".join(p.get_text() for p in fitz.open(stream=pdf, filetype="pdf"))
    except Exception:
        return False
    origem = ""
    if docx:
        try:
            with zipfile.ZipFile(io.BytesIO(docx)) as z:
                origem = z.read("word/document.xml").decode("utf-8", "ignore")
        except Exception:
            origem = ""
    return any(c in texto and c not in origem for c in _PROIBIDOS)


def _com_word(entrada, saida):
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    try:
        word.Visible = False
        word.DisplayAlerts = 0
        word.AutomationSecurity = MSO_AUTOMATION_SECURITY_FORCE_DISABLE
        doc = word.Documents.Open(str(entrada), ReadOnly=True, AddToRecentFiles=False, Visible=False)
        try:
            doc.SaveAs2(str(saida), FileFormat=WD_FORMAT_PDF)
        finally:
            doc.Close(False)
    finally:
        word.Quit()
        pythoncom.CoUninitialize()


def _com_libreoffice(entrada, saida):
    exe = shutil.which("soffice") or shutil.which("libreoffice")
    if not exe:
        raise FileNotFoundError("LibreOffice não instalado")
    perfil = Path(entrada).parent / "perfil"  # perfil isolado: não depende de HOME nem de instâncias abertas
    subprocess.run([exe, f"-env:UserInstallation={perfil.as_uri()}", "--headless", "--convert-to", "pdf",
                    "--outdir", str(Path(saida).parent), str(entrada)],
                   check=True, timeout=120, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def docx_para_pdf(dados):
    defeito = False
    with tempfile.TemporaryDirectory() as pasta:
        entrada, saida = Path(pasta) / "prova.docx", Path(pasta) / "prova.pdf"
        # o Word converte o original; os outros motores recebem o DOCX saneado (sem «¿» nas equações); se ainda assim
        # sair símbolo trocado, tenta com as equações de risco e depois todas em texto linear (nunca sai adulterado);
        # o último recurso converte o original sem qualquer retoque
        for metodo, nivel in (("word", 0), ("docx2pdf", 1), ("libreoffice", 1), ("libreoffice", 2),
                              ("libreoffice", 3), ("libreoffice_original", 0)):
            entrada.write_bytes(dados if nivel == 0 else sanear_docx(dados, nivel))
            saida.unlink(missing_ok=True)
            try:
                if metodo == "word":
                    _com_word(entrada, saida)
                elif metodo.startswith("libreoffice"):
                    _com_libreoffice(entrada, saida)
                else:
                    from docx2pdf import convert
                    convert(str(entrada), str(saida))
            except Exception:
                continue
            if saida.exists() and saida.stat().st_size:
                pdf = saida.read_bytes()
                if conteudo_adulterado(pdf, dados):
                    defeito = True
                    continue
                return pdf
    if defeito:
        raise ValueError("A conversão do Word alterou o conteúdo (apareceu «¿» ou «�» no lugar de símbolos das equações). "
                         "A prova não foi gerada para não sair adulterada: exporta o Word para PDF e carrega o PDF.")
    raise ValueError("Não foi possível converter o DOCX (é preciso o Microsoft Word ou o LibreOffice). Exporta-o para PDF e tenta de novo.")

def docxs_para_pdfs(lista):
    """Converte vários DOCX de uma vez (um só arranque do LibreOffice); devolve os PDFs pela mesma ordem."""
    if not lista:
        return []
    exe = shutil.which("soffice") or shutil.which("libreoffice")
    if exe:
        with tempfile.TemporaryDirectory() as pasta:
            pasta = Path(pasta)
            entradas = []
            for i, dados in enumerate(lista):
                e = pasta / f"c{i:04d}.docx"
                e.write_bytes(sanear_docx(dados))
                entradas.append(e)
            try:
                subprocess.run([exe, f"-env:UserInstallation={(pasta / 'perfil').as_uri()}", "--headless", "--convert-to", "pdf",
                                "--outdir", str(pasta), *map(str, entradas)],
                               check=True, timeout=60 + 15 * len(lista), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                saidas = [e.with_suffix(".pdf") for e in entradas]
                if all(s.exists() and s.stat().st_size for s in saidas):
                    pdfs = [s.read_bytes() for s in saidas]
                    if not any(conteudo_adulterado(pdf, d) for pdf, d in zip(pdfs, lista)):
                        return pdfs
            except (subprocess.SubprocessError, OSError):
                pass
    return [docx_para_pdf(d) for d in lista]  # Word no Windows, ou recurso cópia a cópia


def garantir_pdf(dados):
    """Devolve PDF: o próprio ficheiro, ou o DOCX convertido. Outros formatos são recusados."""
    if dados.startswith(b"%PDF-"):
        return dados
    if eh_docx(dados):
        return docx_para_pdf(dados)
    raise ValueError("O ficheiro não é um PDF nem um DOCX.")
