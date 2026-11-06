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
            # Times New Roman 12 (negrito) ocupa ~1,2 unidades de largura por carácter
            linhas = sum(max(1, math.ceil(len(t) * 1.25 / larg_chars)) for t in v.split('\n'))
            precisa = max(precisa, linhas * _ALTURA_LINHA_PT + 6)
        if precisa:
            atual = ws.row_dimensions[r].height or 0
            ws.row_dimensions[r].height = min(max(atual, precisa), 409)


_AZUL_CABECALHO = '1E3A8A'
_ZEBRA = 'F1F5F9'


def _cor_fundo(cell):
    f = cell.fill
    if f is None or getattr(f, 'fill_type', None) != 'solid':
        return None
    rgb = getattr(f.start_color, 'rgb', None)
    return rgb[-6:].upper() if isinstance(rgb, str) else None


def _tem_borda(cell):
    b = cell.border
    return bool(b and (b.left.style or b.right.style or b.top.style or b.bottom.style))


def _melhorar_tabela(ws, max_r, max_c):
    """Cabeçalho da tabela repetido em cada página impressa e linhas de dados com riscas alternadas."""
    from openpyxl.styles import PatternFill
    cab = []
    for r in range(1, max_r + 1):
        cel = [ws.cell(row=r, column=c) for c in range(1, max_c + 1)]
        cheias = [c for c in cel if c.value is not None or _cor_fundo(c)]
        if cheias and sum(1 for c in cheias if _cor_fundo(c) == _AZUL_CABECALHO) * 2 >= len(cheias) and len(cheias) >= 3:
            cab.append(r)
        elif cab:
            break
    if not cab:
        return
    ult_cab = cab[-1]
    ws.print_title_rows = f'{cab[0]}:{ult_cab}'
    zebra = PatternFill(start_color=_ZEBRA, end_color=_ZEBRA, fill_type='solid')
    n = 0
    for r in range(ult_cab + 1, max_r + 1):
        linha = [ws.cell(row=r, column=c) for c in range(1, max_c + 1)]
        if not _tem_borda(linha[0]) or all(c.value is None for c in linha):
            break
        n += 1
        if n % 2 == 0:
            for c in linha:
                if _cor_fundo(c) is None and _tem_borda(c):
                    c.fill = zebra


_NAVY = '1E3A8A'
_OURO = 'C9A227'
_CINZA_LINHA = '94A3B8'
_CINZA_VERT = 'CBD5E1'
_AZUL_CLARO = '5B74B8'


def _componentes_tabela(ws, max_r, max_c):
    """Agrupa as células com borda (fusões incluídas) em tabelas ligadas entre si."""
    com_borda = set()
    for row in ws.iter_rows(min_row=1, max_row=max_r, max_col=max_c):
        for c in row:
            if _tem_borda(c):
                com_borda.add((c.row, c.column))
    for rg in ws.merged_cells.ranges:
        if (rg.min_row, rg.min_col) in com_borda:
            for r in range(rg.min_row, rg.max_row + 1):
                for c in range(rg.min_col, rg.max_col + 1):
                    com_borda.add((r, c))
    vistos, comps = set(), []
    for ini in sorted(com_borda):
        if ini in vistos:
            continue
        pilha, comp = [ini], set()
        vistos.add(ini)
        while pilha:
            r, c = pilha.pop()
            comp.add((r, c))
            for viz in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if viz in com_borda and viz not in vistos:
                    vistos.add(viz)
                    pilha.append(viz)
        comps.append(comp)
    return comps


def aplicar_moldura_tabelas(ws, max_r, max_c):
    """
    Tabelas opacas e com linhas de nível profissional:
      * fundo branco sólido em toda a tabela (nunca transparente);
      * moldura exterior grossa (thick) azul institucional;
      * linha dupla dourada por baixo do cabeçalho;
      * separação média (medium) entre grupos de colunas (ex.: bloco de cada disciplina);
      * linhas finas verticais e tracejado pontilhado (dotted) entre linhas de dados.
    """
    from openpyxl.styles import Border, Side, PatternFill
    branco = PatternFill(start_color='FFFFFF', end_color='FFFFFF', fill_type='solid')
    for comp in _componentes_tabela(ws, max_r, max_c):
        navy = {p for p in comp if _cor_fundo(ws.cell(row=p[0], column=p[1])) == _AZUL_CABECALHO}
        grupos = set()  # colunas c: linha vertical entre c e c+1 é fronteira de grupo
        if navy:
            topo = min(r for r, _ in navy)
            for rg in ws.merged_cells.ranges:
                if rg.min_row == topo and rg.max_col > rg.min_col and (rg.min_row, rg.min_col) in comp:
                    grupos.update({rg.min_col - 1, rg.max_col})

        def lado(estilo, cor):
            return Side(style=estilo, color=cor)

        def aresta_h(a, b):  # a acima, b abaixo
            if a not in comp or b not in comp:
                return lado('thick', _NAVY)
            if a in navy and b not in navy:
                return lado('double', _OURO)
            if a in navy and b in navy:
                return lado('thin', _AZUL_CLARO)
            return lado('dotted', _CINZA_LINHA)

        def aresta_v(a, b):  # a à esquerda, b à direita
            if a not in comp or b not in comp:
                return lado('thick', _NAVY)
            if a[1] in grupos:
                return lado('medium', 'FFFFFF' if a in navy else _NAVY)
            return lado('thin', _AZUL_CLARO if a in navy else _CINZA_VERT)

        for (r, c) in comp:
            cel = ws.cell(row=r, column=c)
            if getattr(cel.fill, 'fill_type', None) is None:
                cel.fill = branco
            cel.border = Border(
                left=aresta_v((r, c - 1), (r, c)), right=aresta_v((r, c), (r, c + 1)),
                top=aresta_h((r - 1, c), (r, c)), bottom=aresta_h((r, c), (r + 1, c)))


_LARGURA_MAX_COLUNA = 60


def garantir_palavras_inteiras(ws, max_r, max_c):
    """
    Nenhuma palavra é partida a meio («Reprova/da», «Agro/pec/uária»): se a palavra mais comprida
    de uma célula com quebra de linha não cabe na largura das suas colunas, as colunas são alargadas.
    «do/da» e restantes palavras só mudam de linha nos espaços.
    """
    from openpyxl.utils import get_column_letter
    fundidas = {(rg.min_row, rg.min_col): rg for rg in ws.merged_cells.ranges}
    for r in range(1, max_r + 1):
        for c in range(1, max_c + 1):
            cel = ws.cell(row=r, column=c)
            v = cel.value
            if not isinstance(v, str) or not v.strip() or not (cel.alignment and cel.alignment.wrap_text):
                continue
            palavra = max(len(p) for p in v.split())
            fator = 1.3 if (cel.font and cel.font.bold) else 1.15
            necessario = palavra * fator + 2.5
            rg = fundidas.get((r, c))
            c_fim = rg.max_col if rg is not None else c
            letras = [get_column_letter(i) for i in range(c, c_fim + 1)]
            atuais = [ws.column_dimensions[l].width or 8.43 for l in letras]
            falta = min(necessario, _LARGURA_MAX_COLUNA * len(letras)) - sum(atuais)
            if falta > 0:
                for l, w in zip(letras, atuais):
                    ws.column_dimensions[l].width = min(w + falta / len(letras), _LARGURA_MAX_COLUNA)


def embelezar_workbook(wb):
    """
    Apresentação final de todos os documentos Excel do SIGE:
      * esconde todas as linhas e colunas sem conteúdo: só a área abrangida pelo conteúdo fica visível;
      * centra o logótipo sobre o cabeçalho e deixa-lhe espaço próprio;
      * ajusta a altura das linhas ao texto, sem grelha de fundo e com impressão centrada.
    """
    from openpyxl.utils import get_column_letter, column_index_from_string
    from openpyxl.worksheet.dimensions import ColumnDimension
    for ws in wb.worksheets:
        max_r, max_c = _limites_conteudo(ws)
        if max_r == 0 or max_c == 0:
            continue
        garantir_palavras_inteiras(ws, max_r, max_c)
        _centrar_logo(ws, max_c)
        _ajustar_alturas(ws, max_r, max_c)
        _melhorar_tabela(ws, max_r, max_c)
        aplicar_moldura_tabelas(ws, max_r, max_c)
        # Linhas: todas as do conteúdo têm altura explícita; as restantes ficam escondidas (zeroHeight)
        for r in range(1, max_r + 1):
            if ws.row_dimensions[r].height is None:
                ws.row_dimensions[r].height = 22
        ws.sheet_format.zeroHeight = True
        # Colunas: esconde da primeira vazia até ao fim da folha (XFD)
        if max_c < _ULTIMA_COLUNA:
            for chave in list(ws.column_dimensions.keys()):
                cd0 = ws.column_dimensions[chave]
                ini = cd0.min or column_index_from_string(chave)
                if ini > max_c:
                    del ws.column_dimensions[chave]  # evita <col> sobrepostos com o intervalo escondido
                elif cd0.max and cd0.max > max_c:
                    cd0.max = max_c
            letra = get_column_letter(max_c + 1)
            ws.column_dimensions[letra] = ColumnDimension(
                ws, index=letra, min=max_c + 1, max=_ULTIMA_COLUNA, hidden=True)
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
    # O openpyxl grava um <workbookProtection/> vazio; o Excel pode tratá-lo como livro protegido.
    wb.security = None
    if embelezar:
        embelezar_workbook(wb)
    tmp = io.BytesIO()
    wb.save(tmp)
    dados = tmp.getvalue()
    validar_xlsx_bytes(dados)
    if destino is not None:
        destino.write(dados)
    return dados
