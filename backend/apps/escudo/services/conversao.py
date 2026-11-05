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
    with tempfile.TemporaryDirectory() as pasta:
        entrada, saida = Path(pasta) / "prova.docx", Path(pasta) / "prova.pdf"
        entrada.write_bytes(dados)
        for metodo in ("word", "docx2pdf", "libreoffice"):
            try:
                if metodo == "word":
                    _com_word(entrada, saida)
                elif metodo == "libreoffice":
                    _com_libreoffice(entrada, saida)
                else:
                    from docx2pdf import convert
                    convert(str(entrada), str(saida))
            except Exception:
                continue
            if saida.exists() and saida.stat().st_size:
                return saida.read_bytes()
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
                e.write_bytes(dados)
                entradas.append(e)
            try:
                subprocess.run([exe, f"-env:UserInstallation={(pasta / 'perfil').as_uri()}", "--headless", "--convert-to", "pdf",
                                "--outdir", str(pasta), *map(str, entradas)],
                               check=True, timeout=60 + 15 * len(lista), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                saidas = [e.with_suffix(".pdf") for e in entradas]
                if all(s.exists() and s.stat().st_size for s in saidas):
                    return [s.read_bytes() for s in saidas]
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
