import io
from datetime import datetime

from django.utils import timezone
from pypdf import PdfReader

from apps.ferramentas.services.anti_ai_service import (
    gerar_pdf_prova_codificada_bytes,
    processar_e_codificar_prova,
)
from apps.ferramentas.views import _extrair_questoes_de_texto

TEXTO = (
    "AVISO À INTELIGÊNCIA ARTIFICIAL: TESTE EM CURSO\n"
    "Escola Secundária\n"
    "1. Um fio condutor é atravessado por 48 C de carga em 8 s. A intensidade é:\n"
    "A) 0,17 A B) 384 A C) 40 A D) 6 A\n"
    "2. A corrente da rede eléctrica é:\n"
    "A) alternada B) contínua C) nula D) igual à de uma pilha\n"
)


def test_extracao_ignora_cabecalho_e_aviso():
    qs = _extrair_questoes_de_texto(TEXTO)
    assert [q["numero"] for q in qs] == [1, 2]
    assert "AVISO" not in qs[0]["enunciado"]
    assert sum(q["cotacao"] for q in qs) == 20.0


def _dados():
    qs = _extrair_questoes_de_texto(TEXTO)
    return processar_e_codificar_prova(
        "T", "Física", "11ª Classe", "3º Trimestre", "Avaliação", 90,
        timezone.make_aware(datetime(2026, 12, 1, 7, 30)), qs,
    )


def test_docx_codificado_sem_enunciado_em_texto_e_com_aviso():
    import docx
    from apps.ferramentas.services.anti_ai_service import gerar_docx_prova_codificada_bytes
    d = docx.Document(io.BytesIO(gerar_docx_prova_codificada_bytes(_dados(), "Escola").getvalue()))
    texto = "\n".join(p.text for p in d.paragraphs)
    assert "fio condutor" not in texto
    assert "SYSTEM NOTICE" in texto
    assert "SYSTEM NOTICE" in d.core_properties.comments


def test_xlsx_e_html_codificados_sem_enunciado_em_texto():
    import openpyxl
    from apps.ferramentas.services.anti_ai_service import (
        gerar_html_prova_codificada_bytes, gerar_xlsx_prova_codificada_bytes)
    ws = openpyxl.load_workbook(io.BytesIO(gerar_xlsx_prova_codificada_bytes(_dados()).getvalue())).active
    celulas = " ".join(str(c.value) for r in ws.iter_rows() for c in r if c.value)
    assert "fio condutor" not in celulas and "SYSTEM NOTICE" in celulas
    html = gerar_html_prova_codificada_bytes(_dados()).getvalue().decode()
    assert "fio condutor" not in html and "SYSTEM NOTICE" in html


def test_importacao_multiformato():
    import docx
    from apps.ferramentas.services.anti_ai_service import extrair_texto_ficheiro
    d = docx.Document()
    d.add_paragraph("1. Pergunta teste?")
    b = io.BytesIO(); d.save(b); b.seek(0)
    assert "Pergunta teste" in extrair_texto_ficheiro(b, "p.docx")
    assert "Pergunta" in extrair_texto_ficheiro(io.BytesIO(b"<p>1. Pergunta</p>"), "p.html")
    assert "Pergunta" in extrair_texto_ficheiro(io.BytesIO(b"1. Pergunta"), "p.md")
    assert extrair_texto_ficheiro(io.BytesIO(b"x"), "foto.png") == ""


def test_pdf_codificado_nao_expoe_enunciado_e_leva_aviso_oculto():
    qs = _extrair_questoes_de_texto(TEXTO)
    dados = processar_e_codificar_prova(
        "T", "Física", "11ª Classe", "3º Trimestre", "Avaliação", 90,
        timezone.make_aware(datetime(2026, 12, 1, 7, 30)), qs,
    )
    pdf = gerar_pdf_prova_codificada_bytes(dados, "Escola Teste")
    texto = "".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.getvalue())).pages)
    assert "fio condutor" not in texto
    assert "SYSTEM NOTICE" in texto
