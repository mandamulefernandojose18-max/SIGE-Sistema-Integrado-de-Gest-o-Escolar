"""
Utilitários de segurança para exportação XLSX — SIGE.

Centraliza o que impede o Excel de abrir (ou de "reparar") um ficheiro:
  * nomes de folha inválidos (``/ \\ ? * [ ] :``, mais de 31 caracteres, apóstrofo nas pontas, duplicados);
  * textos que o Excel interpretaria como fórmula (``=``, ``+``, ``-``, ``@``);
  * textos acima do limite de 32 767 caracteres por célula;
  * logótipos em formatos que o Excel não aceita (WebP, SVG, CMYK, paleta...);
  * validação final do ficheiro gerado antes de o entregar.
"""
import io
import re
import zipfile

LIMITE_NOME_FOLHA = 31
LIMITE_CELULA = 32767
_PROIBIDOS_FOLHA = re.compile(r'[\\/?*\[\]:]')
_CONTROLO_XML = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')


class XlsxInvalidoError(Exception):
    """O ficheiro gerado não passou na validação de integridade."""


def nome_folha(texto, padrao='Folha', existentes=()):
    """Devolve um nome de folha válido para o Excel (único e com no máximo 31 caracteres)."""
    base = _PROIBIDOS_FOLHA.sub('-', str(texto or ''))
    base = _CONTROLO_XML.sub('', base).strip().strip("'").strip()
    base = re.sub(r'\s+', ' ', base) or padrao
    base = base[:LIMITE_NOME_FOLHA].strip().strip("'").strip() or padrao
    if base.lower() == 'history':  # nome reservado pelo Excel
        base = 'Historico'
    usados = {str(e).lower() for e in existentes}
    nome, n = base, 2
    while nome.lower() in usados:
        sufixo = f' ({n})'
        nome = base[:LIMITE_NOME_FOLHA - len(sufixo)].rstrip() + sufixo
        n += 1
    return nome


def texto_seguro(valor):
    """Remove caracteres de controlo proibidos no XML e corta ao limite da célula."""
    if not isinstance(valor, str):
        return valor
    valor = _CONTROLO_XML.sub('', valor)
    return valor[:LIMITE_CELULA]


def sanear_workbook(wb):
    """
    Garante que todo o texto é gravado como texto (nunca como fórmula) e dentro dos limites.
    O SIGE não exporta fórmulas, por isso qualquer valor a começar por '=' é texto literal.
    """
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                v = cell.value
                if isinstance(v, str) and v:
                    v = texto_seguro(v)
                    cell.value = v
                    if v[:1] == '=' or cell.data_type == 'f':
                        cell.data_type = 's'
    return wb


def normalizar_logo_png(logo_bytes, lado_max=256):
    """Converte qualquer imagem aceite pelo Pillow para PNG RGB(A) seguro para o Excel. None se inválida."""
    if not logo_bytes:
        return None
    try:
        from PIL import Image
        with Image.open(io.BytesIO(logo_bytes)) as im:
            im.load()
            if im.mode not in ('RGB', 'RGBA'):
                im = im.convert('RGBA' if 'A' in im.mode or im.info.get('transparency') is not None else 'RGB')
            im.thumbnail((lado_max, lado_max))
            saida = io.BytesIO()
            im.save(saida, format='PNG')
            return saida.getvalue()
    except Exception:
        return None


def validar_xlsx_bytes(dados):
    """Reabre o ficheiro como o Excel faria. Levanta XlsxInvalidoError se estiver avariado."""
    if not dados or dados[:2] != b'PK':
        raise XlsxInvalidoError('O ficheiro gerado não é um XLSX válido (cabeçalho ZIP em falta).')
    try:
        with zipfile.ZipFile(io.BytesIO(dados)) as z:
            if z.testzip() is not None:
                raise XlsxInvalidoError('O ficheiro XLSX gerado tem partes corrompidas.')
            nomes = set(z.namelist())
            for obrigatorio in ('[Content_Types].xml', 'xl/workbook.xml'):
                if obrigatorio not in nomes:
                    raise XlsxInvalidoError(f'XLSX sem a parte obrigatória {obrigatorio}.')
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(dados))
        for ws in wb.worksheets:
            rs = list(ws.merged_cells.ranges)
            for i, a in enumerate(rs):
                for b in rs[i + 1:]:
                    if not (a.max_col < b.min_col or b.max_col < a.min_col
                            or a.max_row < b.min_row or b.max_row < a.min_row):
                        raise XlsxInvalidoError(f'Células fundidas sobrepostas na folha "{ws.title}" ({a} e {b}).')
    except XlsxInvalidoError:
        raise
    except Exception as exc:
        raise XlsxInvalidoError(f'O XLSX gerado não pôde ser reaberto: {exc}') from exc
    return True


def guardar_xlsx_seguro(wb, destino=None):
    """
    Sanea, grava e valida. Sem ``destino`` devolve os bytes; com ``destino`` (buffer) escreve nele
    e devolve também os bytes. Levanta XlsxInvalidoError se o resultado não abrir.
    """
    sanear_workbook(wb)
    tmp = io.BytesIO()
    wb.save(tmp)
    dados = tmp.getvalue()
    validar_xlsx_bytes(dados)
    if destino is not None:
        destino.write(dados)
    return dados
