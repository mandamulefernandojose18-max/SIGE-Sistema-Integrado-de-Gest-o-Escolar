"""
SIGE — Importação do gabarito (chave de correcção) de uma prova de escolha múltipla.

Aceita o guião do professor em PDF (com texto), Word (.docx), Excel (.xlsx), CSV/TXT ou texto colado, e devolve uma
PROPOSTA ({versão: 'ABCD…'}) que o professor revê e corrige numa tabela antes de a prova ser criada.
Não usa IA nem OCR: PDF digitalizado (só imagem) não tem texto para ler e é recusado com instrução clara.

Formatos de chave reconhecidos (letras A–F):  «1-A  2-C»,  «1. B»,  «1) c»,  «1 | D»,  tabelas número/letra
(em colunas ou em duas linhas) e a sequência compacta «ABCDDABC…». Várias versões: «Versão A», «Tema B», «Grupo C».
"""
import io
import re
import zipfile

MAX_BYTES = 5 * 1024 * 1024
MAX_PERGUNTAS = 100
LETRAS = 'ABCDEF'
_RE_PAR = re.compile(r'(?<![\dA-Za-z])(\d{1,3})[ \t]*[\.\)\-–—:=|/]*[ \t]*\(?([A-Fa-f])\)?(?![A-Za-z0-9ÀÿÇç])')
_RE_VERSAO = re.compile(r'(?im)^\W*(?:vers[aã]o|tema|grupo|variante)\s*[:\-]?\s*([A-D])\b')
_RE_SEQ = re.compile(r'^[\s,;.\-|/ABCDEFabcdef]{5,}$')


class ErroImportacao(ValueError):
    """Mensagem pronta a mostrar ao professor."""


def _texto_pdf(dados):
    import fitz
    try:
        doc = fitz.open(stream=dados, filetype='pdf')
    except Exception as e:
        raise ErroImportacao('Não foi possível abrir o PDF.') from e
    try:
        partes = [p.get_text('text') for p in doc if doc.page_count <= 60]
    finally:
        doc.close()
    texto = '\n'.join(partes).strip()
    if len(re.sub(r'\s+', '', texto)) < 8:
        raise ErroImportacao('Este PDF não tem texto (é uma imagem digitalizada). Ainda não é possível ler fotografias ou '
                             'digitalizações do gabarito: cole a chave no campo de texto ou preencha a tabela.')
    return texto


def _texto_docx(dados):
    try:
        import docx
        d = docx.Document(io.BytesIO(dados))
    except (zipfile.BadZipFile, KeyError, ValueError) as e:
        raise ErroImportacao('Não foi possível abrir o ficheiro Word.') from e
    linhas = [p.text for p in d.paragraphs]
    for t in d.tables:
        for r in t.rows:
            linhas.append(' | '.join(c.text.strip() for c in r.cells))
    return '\n'.join(linhas)


def _linhas_xlsx(dados):
    try:
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(dados), read_only=True, data_only=True)
    except Exception as e:
        raise ErroImportacao('Não foi possível abrir o ficheiro Excel.') from e
    linhas = []
    try:
        for ws in wb.worksheets[:3]:
            for row in ws.iter_rows(values_only=True, max_row=400, max_col=120):
                celulas = ['' if v is None else str(v).strip() for v in row]
                if any(celulas):
                    linhas.append(celulas)
    finally:
        wb.close()
    return linhas


def _texto_de_linhas(linhas):
    """Linha a linha («1 | A»); e, se for uma tabela em duas linhas (números por cima, letras por baixo), emparelha-as."""
    saida = [' | '.join(c for c in r if c) for r in linhas]
    for a, b in zip(linhas, linhas[1:]):
        nums = [c for c in a if c.isdigit()]
        letras = [c for c in b if re.fullmatch(r'[A-Fa-f]', c)]
        if len(nums) >= 3 and len(nums) == len(letras):
            saida.append(' '.join(f'{n}-{l}' for n, l in zip(nums, letras)))
    return '\n'.join(saida)


def _ler_texto(dados, nome):
    ext = (nome or '').rsplit('.', 1)[-1].lower() if '.' in (nome or '') else ''
    if dados[:5] == b'%PDF-' or ext == 'pdf':
        return _texto_pdf(dados)
    if dados[:2] == b'PK':
        if ext in ('xlsx', 'xlsm') or b'xl/' in dados[:4096] + dados[-2048:]:
            return _texto_de_linhas(_linhas_xlsx(dados))
        return _texto_docx(dados)
    if dados[:3] in (b'\xff\xd8\xff', b'\x89PN') or ext in ('jpg', 'jpeg', 'png', 'heic', 'webp'):
        raise ErroImportacao('Ainda não é possível ler o gabarito a partir de fotografias. Envie PDF com texto, Word, Excel, '
                             'CSV/TXT, ou cole a chave no campo de texto.')
    for cod in ('utf-8-sig', 'cp1252'):
        try:
            txt = dados.decode(cod)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ErroImportacao('Formato de ficheiro não reconhecido.')
    if ext == 'csv' or (';' in txt[:400] and '\n' in txt):
        linhas = [[c.strip() for c in re.split(r'[;,\t]', l)] for l in txt.splitlines() if l.strip()]
        return _texto_de_linhas(linhas)
    return txt


def _extrair_sequencia(texto):
    """{numero: letra} por pares «n + letra»; escolhe a cadeia 1..N (a 1ª ocorrência ganha)."""
    achados = {}
    for m in _RE_PAR.finditer(texto):
        n = int(m.group(1))
        if 1 <= n <= MAX_PERGUNTAS and n not in achados:
            achados[n] = m.group(2).upper()
    if not achados:
        return [], []
    maximo = 0
    while (maximo + 1) in achados:
        maximo += 1
    topo = max(achados)
    if topo > maximo and len(achados) / topo >= 0.8:   # quase contínua: mantém tudo e assinala as lacunas
        maximo = topo
    elif maximo < 2:
        maximo = topo
    letras = [achados.get(i, '') for i in range(1, maximo + 1)]
    lacunas = [i for i, l in enumerate(letras, start=1) if not l]
    return letras, lacunas


def _compacta(texto):
    """Sequência sem números («ABCDABCD…»): só quando o texto inteiro é feito de letras de resposta."""
    limpo = re.sub(r'\s+', ' ', texto).strip()
    if _RE_SEQ.match(limpo):
        letras = re.sub(r'[^A-Fa-f]', '', limpo).upper()
        if 5 <= len(letras) <= MAX_PERGUNTAS:
            return list(letras)
    return []


def _por_versao(texto):
    marcas = list(_RE_VERSAO.finditer(texto))
    if len({m.group(1).upper() for m in marcas}) < 2:
        return {'-': texto}
    partes = {}
    for k, m in enumerate(marcas):
        fim = marcas[k + 1].start() if k + 1 < len(marcas) else len(texto)
        partes.setdefault(m.group(1).upper(), texto[m.end():fim])
    return partes


def extrair_gabarito(dados=None, nome='', texto=None):
    """Devolve {'versoes': {v: [letra|''…]}, 'n_perguntas', 'n_alternativas', 'lacunas': {v: [n…]}, 'avisos': [..]}."""
    if texto is None:
        if not dados or len(dados) > MAX_BYTES:
            raise ErroImportacao('Ficheiro vazio ou demasiado grande (máximo 5 MB).')
        texto = _ler_texto(dados, nome)
    texto = str(texto or '')[:200_000]
    if not texto.strip():
        raise ErroImportacao('Não foi encontrado texto para ler.')
    versoes, lacunas, avisos = {}, {}, []
    for v, parte in _por_versao(texto).items():
        letras, lac = _extrair_sequencia(parte)
        if len(letras) < 2 or len(lac) > len(letras) // 5:
            letras, lac = _compacta(parte), []
        if len(letras) < 2:
            continue
        versoes[v] = letras
        if lac:
            lacunas[v] = lac
    if not versoes:
        raise ErroImportacao('Não foi possível reconhecer uma chave de correcção (esperado algo como «1-A, 2-C, 3-B…»). '
                             'Pode escrevê-la directamente na tabela.')
    tamanhos = {len(l) for l in versoes.values()}
    n = max(tamanhos)
    if len(tamanhos) > 1:
        avisos.append('As versões têm números de perguntas diferentes; confirme a tabela antes de criar a prova.')
    for v, lac in lacunas.items():
        avisos.append(f'Versão {v if v != "-" else "única"}: sem resposta lida nas perguntas {", ".join(map(str, lac))}.')
    usadas = {c for l in versoes.values() for c in l if c}
    n_alt = max(2, max((LETRAS.index(c) + 1 for c in usadas), default=2))
    if n_alt == 2 and usadas <= {'A', 'B'}:
        avisos.append('Só apareceram as letras A e B; confirme o número de alternativas da prova.')
    avisos.append('Reveja a chave: o sistema leu o texto sem inteligência artificial e não distingue erros de digitação.')
    return {'versoes': versoes, 'n_perguntas': n, 'n_alternativas': n_alt, 'lacunas': lacunas, 'avisos': avisos}
