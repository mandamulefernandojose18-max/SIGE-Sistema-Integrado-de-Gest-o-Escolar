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


_PX_POR_CHAR = 7
_PX_DEFAULT_COL = 64
_ALTURA_LINHA_PT = 16.0
_ALTURA_LOGO_LINHA1 = 62.0
_ULTIMA_COLUNA = 16384


def _largura_coluna_px(ws, idx):
    from openpyxl.utils import get_column_letter
    cd = ws.column_dimensions.get(get_column_letter(idx))
    if cd is not None and cd.width:
        return int(cd.width * _PX_POR_CHAR + 5)
    return _PX_DEFAULT_COL


def _limites_conteudo(ws):
    """Última linha/coluna com valor, formatação visível (fundo/borda) ou fusão."""
    max_r = max_c = 0
    for row in ws.iter_rows():
        for c in row:
            visivel = c.value is not None or getattr(c.fill, 'fill_type', None) or (
                c.border and (c.border.left.style or c.border.right.style or c.border.top.style or c.border.bottom.style))
            if visivel:
                max_r = max(max_r, c.row)
                max_c = max(max_c, c.column)
    for rg in ws.merged_cells.ranges:
        max_r = max(max_r, rg.max_row)
        max_c = max(max_c, rg.max_col)
    return max_r, max_c


def _centrar_logo(ws, max_c):
    """Centra o logótipo sobre o cabeçalho (intervalo fundido da linha 1, ou toda a largura útil)."""
    imagens = list(getattr(ws, '_images', []) or [])
    if not imagens or max_c < 1:
        return
    from openpyxl.drawing.spreadsheet_drawing import OneCellAnchor, AnchorMarker
    from openpyxl.drawing.xdr import XDRPositiveSize2D
    c1, c2 = 1, max_c
    topo = [rg for rg in ws.merged_cells.ranges if rg.min_row == 1 and rg.max_row == 1]
    if topo:
        melhor = max(topo, key=lambda rg: rg.max_col - rg.min_col)
        c1, c2 = melhor.min_col, melhor.max_col
    larguras = [_largura_coluna_px(ws, i) for i in range(c1, c2 + 1)]
    total = sum(larguras)
    emu = 9525
    for img in imagens:
        w_px, h_px = int(img.width or 46), int(img.height or 46)
        alvo = max((total - w_px) // 2, 0)
        acc = 0
        col_idx, off = c1, 0
        for i, lw in zip(range(c1, c2 + 1), larguras):
            if acc + lw > alvo:
                col_idx, off = i, alvo - acc
                break
            acc += lw
        img.anchor = OneCellAnchor(
            _from=AnchorMarker(col=col_idx - 1, colOff=off * emu, row=0, rowOff=3 * emu),
            ext=XDRPositiveSize2D(w_px * emu, h_px * emu),
        )
    # Linha 1: espaço para o logótipo e texto do cabeçalho encostado em baixo
    ws.row_dimensions[1].height = max(ws.row_dimensions[1].height or 0, _ALTURA_LOGO_LINHA1)
    from copy import copy
    for c in ws[1]:
        if c.value is not None:
            al = copy(c.alignment)
            al.vertical = 'bottom'
            c.alignment = al


def _ajustar_alturas(ws, max_r, max_c):
    """Altura de cada linha suficiente para o texto com quebra (nada cortado)."""
    from openpyxl.utils import get_column_letter
    import math
    fundidas = {}
    for rg in ws.merged_cells.ranges:
        fundidas[(rg.min_row, rg.min_col)] = rg
    for r in range(1, max_r + 1):
        precisa = 0.0
        for c in range(1, max_c + 1):
            cell = ws.cell(row=r, column=c)
            v = cell.value
            if not isinstance(v, str) or not v or not (cell.alignment and cell.alignment.wrap_text):
                continue
            rg = fundidas.get((r, c))
            if rg is not None and rg.max_row > rg.min_row:
                continue  # fusões verticais: altura vem das várias linhas
            c_fim = rg.max_col if rg is not None else c
            larg_chars = sum((_largura_coluna_px(ws, i) - 5) / _PX_POR_CHAR for i in range(c, c_fim + 1))
            larg_chars = max(larg_chars - 1, 3)
            linhas = sum(max(1, math.ceil(len(t) * 1.08 / larg_chars)) for t in v.split('\n'))
            precisa = max(precisa, linhas * _ALTURA_LINHA_PT + 4)
        if precisa:
            atual = ws.row_dimensions[r].height or 0
            ws.row_dimensions[r].height = min(max(atual, precisa), 409)


def embelezar_workbook(wb):
    """
    Apresentação final de todos os documentos Excel do SIGE:
      * não esconde nada (linhas e colunas ficam como no ecrã do sistema);
      * centra o logótipo sobre o cabeçalho e deixa-lhe espaço próprio;
      * ajusta a altura das linhas ao texto, sem grelha de fundo e com impressão centrada.
    """
    for ws in wb.worksheets:
        max_r, max_c = _limites_conteudo(ws)
        if max_r == 0 or max_c == 0:
            continue
        _centrar_logo(ws, max_c)
        _ajustar_alturas(ws, max_r, max_c)
        # Nada é escondido: o documento mostra-se como no ecrã do sistema.
        for r in range(1, max_r + 1):
            if ws.row_dimensions[r].height is None:
                ws.row_dimensions[r].height = 22
        ws.sheet_view.showGridLines = False
        ws.sheet_view.zoomScale = 100
        ws.print_options.horizontalCentered = True
        ws.sheet_properties.tabColor = '1E3A8A'
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


def guardar_xlsx_seguro(wb, destino=None, embelezar=True):
    """
    Sanea, embeleza, grava e valida. Sem ``destino`` devolve os bytes; com ``destino`` (buffer)
    escreve nele e devolve também os bytes. Levanta XlsxInvalidoError se o resultado não abrir.
    ``embelezar=False`` preserva a folha como está (ficheiros de terceiros, p. ex. provas).
    """
    sanear_workbook(wb)
    if embelezar:
        embelezar_workbook(wb)
    tmp = io.BytesIO()
    wb.save(tmp)
    dados = tmp.getvalue()
    validar_xlsx_bytes(dados)
    if destino is not None:
        destino.write(dados)
    return dados
