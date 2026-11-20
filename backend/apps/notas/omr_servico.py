"""
SIGE — Leitura óptica (OMR) da Folha de Resposta gerada pelo sistema.

A partir de uma fotografia (JPEG/PNG) ou de um PDF digitalizado:
  1. encontra as 4 marcas de registo dos cantos e endireita a página (perspectiva);
  2. decide se a página está de cabeça para baixo ou deitada e corrige;
  3. afina o alinhamento da grelha contra um modelo limpo da MESMA folha (mesma geometria da Folha de Resposta);
  4. mede, em cada alternativa, a tinta que o aluno acrescentou ao modelo em branco (por isso a letra impressa
     não conta) e decide a resposta; marcas duplas, rasuras e marcas fracas ficam como DÚVIDA para o professor;
  5. lê o QR da folha (assinado) e identifica o aluno e a versão.

Nada é gravado aqui: devolve uma proposta que o professor confirma antes de ir para a correcção.
"""
import base64
import functools
import io
import time
from urllib.parse import parse_qs, urlparse

PPM = 8.0                       # pixéis por mm da página endireitada (A4 ≈ 1680 × 2376)
LARGURA_PX = int(round(210.0 * PPM))
ALTURA_PX = int(round(297.0 * PPM))
CENTRO_MARCA_MM = 5.5 + 4.5 / 2   # centro das marcas de registo (mm a partir de cada canto)
MAX_BYTES = 15 * 1024 * 1024
MAX_PIXELS = 80_000_000
LADO_MAX_FOTO = 3200
MAX_PAGINAS_PDF = 200
LIMIAR_MARCA = 0.30             # fracção da área da alternativa preenchida para contar como marcada
LIMIAR_FRACA = 0.15
RAZAO_DUPLA = 0.60
LAPLACE_MIN = 40.0              # abaixo disto a fotografia está desfocada


class ErroOMR(ValueError):
    """Mensagem pronta a mostrar ao professor."""


def _cv():
    try:
        import cv2
        import numpy as np
    except ImportError as e:  # pragma: no cover - o servidor tem as bibliotecas instaladas
        raise ErroOMR('O leitor de folhas não está disponível neste servidor.') from e
    return cv2, np


# ---------------------------------------------------------------------------
# Geometria da grelha (espelha folha_resposta_service._desenhar_grelha)
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=64)
def celulas_grelha(n, n_alt):
    """[(pergunta0, indice_alternativa, x_mm, y_mm, larg_mm, alt_mm)] com o centro (x, y) de cada alternativa."""
    from apps.documentos.services import folha_resposta_service as fr
    (_, fim, cols, linhas, y_ini), = fr.paginas_grelha(n, 0.0)
    largura_col = fr.LARG_UTIL / cols
    altura_disp = fr.Y_FIM_GRELHA - y_ini
    folgas = ((linhas - 1) // 5) * fr.FOLGA_GRUPO
    altura_linha = min(6.4, (altura_disp - fr.ALTURA_CABECALHO_GRELHA - folgas) / linhas)
    passo = min(13.0, (largura_col - 11.5) / n_alt)
    larg_alt = min(9.6, passo * 0.84)
    alt_alt = min(1.9, altura_linha * 0.36)
    saida = []
    for q in range(fim):
        col, r = divmod(q, linhas)
        x0 = fr.MARGEM + col * largura_col
        y_lin = y_ini + fr.ALTURA_CABECALHO_GRELHA + r * altura_linha + (r // 5) * fr.FOLGA_GRUPO
        cy = y_lin + altura_linha / 2
        for i in range(n_alt):
            cx = x0 + 10.2 + passo * i + passo / 2 - 0.6
            saida.append((q, i, cx, cy, larg_alt, alt_alt))
    return tuple(saida), cols, linhas, y_ini


def _normalizar_ilumina(cv2, np, cinza):
    """Tinta 0..1 (1 = preto) com a iluminação uniformizada (sombras e papel acinzentado deixam de contar)."""
    fundo = cv2.morphologyEx(cinza, cv2.MORPH_CLOSE, np.ones((21, 21), np.uint8))
    fundo = cv2.GaussianBlur(fundo, (0, 0), 12)
    norm = cv2.divide(cinza, np.maximum(fundo, 1), scale=255)
    return 1.0 - np.clip(norm.astype(np.float32) / 255.0, 0, 1)


@functools.lru_cache(maxsize=16)
def _modelo(n, n_alt):
    """Tinta (0..1) da folha limpa (marcas + grelha) à mesma escala da página endireitada."""
    cv2, np = _cv()
    import fitz
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as rl_canvas
    from apps.documentos.services import folha_resposta_service as fr
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(fr.PAG_L * mm, fr.PAG_A * mm))
    fr._desenhar_marcas_omr(c)
    _, cols, linhas, y_ini = celulas_grelha(n, n_alt)
    fr._desenhar_grelha(c, {'n_alternativas': n_alt}, 0, n, cols, linhas, y_ini)
    c.showPage()
    c.save()
    doc = fitz.open(stream=buf.getvalue(), filetype='pdf')
    try:
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(PPM * 25.4 / 72, PPM * 25.4 / 72), colorspace=fitz.csGRAY, alpha=False)
        img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
    finally:
        doc.close()
    img = cv2.resize(img, (LARGURA_PX, ALTURA_PX), interpolation=cv2.INTER_AREA)
    return _normalizar_ilumina(cv2, np, img)


# ---------------------------------------------------------------------------
# Carregar páginas (foto ou PDF)
# ---------------------------------------------------------------------------
def contar_paginas(dados: bytes) -> int:
    if dados[:5] == b'%PDF-':
        import fitz
        try:
            doc = fitz.open(stream=dados, filetype='pdf')
            try:
                return min(doc.page_count, MAX_PAGINAS_PDF)
            finally:
                doc.close()
        except Exception as e:
            raise ErroOMR('Não foi possível abrir o PDF.') from e
    return 1


def abrir_pagina(dados: bytes, indice: int = 0):
    """Devolve a página `indice` como imagem BGR (numpy)."""
    cv2, np = _cv()
    if not dados or len(dados) > MAX_BYTES:
        raise ErroOMR('Ficheiro inválido ou demasiado grande (máximo 15 MB).')
    if dados[:5] == b'%PDF-':
        import fitz
        try:
            doc = fitz.open(stream=dados, filetype='pdf')
        except Exception as e:
            raise ErroOMR('Não foi possível abrir o PDF.') from e
        try:
            if indice < 0 or indice >= min(doc.page_count, MAX_PAGINAS_PDF):
                raise ErroOMR('Página inexistente no PDF.')
            pg = doc[indice]
            esc = min(200 / 72, 3400 / max(pg.rect.width, pg.rect.height))
            pix = pg.get_pixmap(matrix=fitz.Matrix(esc, esc), colorspace=fitz.csRGB, alpha=False)
            img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 3)
            return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        finally:
            doc.close()
    if indice != 0:
        raise ErroOMR('Página inexistente.')
    if dados[:3] != b'\xff\xd8\xff' and dados[:8] != b'\x89PNG\r\n\x1a\n':
        raise ErroOMR('Envie a fotografia em JPEG ou PNG (ou um PDF digitalizado).')
    from PIL import Image
    try:
        with Image.open(io.BytesIO(dados)) as im:
            if im.width * im.height > MAX_PIXELS:
                raise ErroOMR('Fotografia demasiado grande.')
    except ErroOMR:
        raise
    except Exception as e:
        raise ErroOMR('Não foi possível abrir a fotografia.') from e
    img = cv2.imdecode(np.frombuffer(dados, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ErroOMR('Não foi possível abrir a fotografia.')
    maior = max(img.shape[:2])
    if maior > LADO_MAX_FOTO:
        k = LADO_MAX_FOTO / maior
        img = cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    return img


# ---------------------------------------------------------------------------
# Marcas de registo e endireitamento
# ---------------------------------------------------------------------------
def _candidatas_marcas(cv2, np, cinza):
    h, w = cinza.shape
    k = 1600.0 / max(h, w) if max(h, w) > 1600 else 1.0
    pq = cv2.resize(cinza, None, fx=k, fy=k, interpolation=cv2.INTER_AREA) if k != 1.0 else cinza
    pq = cv2.GaussianBlur(pq, (5, 5), 0)
    ph, pw = pq.shape
    bloco = max(31, (int(min(ph, pw) * 0.06) // 2) * 2 + 1)
    bw = cv2.adaptiveThreshold(pq, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, bloco, 12)
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contornos, _ = cv2.findContours(bw, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    lado_min, lado_max = 0.008 * pw, 0.075 * pw
    achadas = []
    for c in contornos:
        area = cv2.contourArea(c)
        if area < lado_min ** 2 * 0.6 or area > lado_max ** 2:
            continue
        (cx, cy), (rw, rh), _ang = cv2.minAreaRect(c)
        if min(rw, rh) < lado_min or max(rw, rh) > lado_max:
            continue
        if min(rw, rh) / max(rw, rh) < 0.72:
            continue
        if area / (rw * rh) < 0.80:          # quadrado cheio (as bolhas/letras são vazadas ou finas)
            continue
        m = cv2.moments(c)
        if m['m00'] <= 0:
            continue
        achadas.append((m['m10'] / m['m00'] / k, m['m01'] / m['m00'] / k, (rw + rh) / 2 / k))
    return achadas


def _escolher_quatro(cands):
    """Os 4 cantos extremos (por soma/diferença das coordenadas) com tamanhos parecidos."""
    if len(cands) < 4:
        return None
    tl = min(cands, key=lambda p: p[0] + p[1])
    br = max(cands, key=lambda p: p[0] + p[1])
    tr = max(cands, key=lambda p: p[0] - p[1])
    bl = min(cands, key=lambda p: p[0] - p[1])
    quatro = [tl, tr, br, bl]
    if len({(round(p[0]), round(p[1])) for p in quatro}) < 4:
        return None
    lados = [p[2] for p in quatro]
    if max(lados) > 1.7 * min(lados):
        return None
    return quatro


def _ordenar_retrato(quatro):
    """Se a folha está deitada (lado tl→tr mais comprido que tl→bl) roda a ordem dos cantos."""
    import math
    tl, tr, br, bl = quatro
    e1 = math.dist(tl[:2], tr[:2])
    e2 = math.dist(tl[:2], bl[:2])
    if e1 > e2:
        return [bl, tl, tr, br]
    return quatro


def _validar_proporcao(quatro):
    import math
    tl, tr, br, bl = quatro
    larg = (math.dist(tl[:2], tr[:2]) + math.dist(bl[:2], br[:2])) / 2
    alt = (math.dist(tl[:2], bl[:2]) + math.dist(tr[:2], br[:2])) / 2
    esperada = (210.0 - 2 * CENTRO_MARCA_MM) / (297.0 - 2 * CENTRO_MARCA_MM)
    r = larg / alt if alt else 0
    return 0.65 * esperada <= r <= 1.4 * esperada


def endireitar(img):
    """Devolve (bgr_endireitada LARGURA_PX×ALTURA_PX, info). Levanta ErroOMR se não achar as 4 marcas."""
    cv2, np = _cv()
    cinza = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    quatro = _escolher_quatro(_candidatas_marcas(cv2, np, cinza))
    if not quatro:
        raise ErroOMR('Não foram encontradas as 4 marcas pretas dos cantos da folha. Fotografe a folha inteira, de cima, '
                      'sem cortar os cantos e com boa luz.')
    quatro = _ordenar_retrato(quatro)
    if not _validar_proporcao(quatro):
        raise ErroOMR('As marcas dos cantos não têm a forma de uma folha A4 (fotografia muito inclinada ou folha dobrada). '
                      'Fotografe de cima, com a folha bem esticada.')
    cm = CENTRO_MARCA_MM * PPM
    dst = np.float32([[cm, cm], [LARGURA_PX - cm, cm], [LARGURA_PX - cm, ALTURA_PX - cm], [cm, ALTURA_PX - cm]])
    src = np.float32([p[:2] for p in quatro])
    M = cv2.getPerspectiveTransform(src, dst)
    page = cv2.warpPerspective(img, M, (LARGURA_PX, ALTURA_PX), flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))
    return page, M


# ---------------------------------------------------------------------------
# Alinhamento fino contra o modelo
# ---------------------------------------------------------------------------
def _zona_grelha_px(n, n_alt):
    _, cols, linhas, y_ini = celulas_grelha(n, n_alt)
    from apps.documentos.services import folha_resposta_service as fr
    return cols, int(y_ini * PPM), int(fr.Y_FIM_GRELHA * PPM)


def _correlacao_grelha(cv2, np, tinta, modelo, n, n_alt, margem=14):
    """Melhor correlação (e deslocamento) por coluna da grelha. Devolve (media_corr, [(dx, dy, corr)] por coluna)."""
    cols, y0, y1 = _zona_grelha_px(n, n_alt)
    from apps.documentos.services import folha_resposta_service as fr
    larg_col = fr.LARG_UTIL / cols
    res = []
    for c in range(cols):
        x0 = int((fr.MARGEM + c * larg_col) * PPM)
        x1 = int((fr.MARGEM + (c + 1) * larg_col) * PPM)
        mod = modelo[y0:y1, x0:x1]
        if mod.shape[0] < 20 or mod.shape[1] < 20:
            continue
        ya, yb = max(0, y0 - margem), min(tinta.shape[0], y1 + margem)
        xa, xb = max(0, x0 - margem), min(tinta.shape[1], x1 + margem)
        zona = tinta[ya:yb, xa:xb]
        if zona.shape[0] < mod.shape[0] or zona.shape[1] < mod.shape[1]:
            continue
        r = cv2.matchTemplate(zona, mod, cv2.TM_CCOEFF_NORMED)
        _, mx, _, loc = cv2.minMaxLoc(r)
        res.append((loc[0] - (x0 - xa), loc[1] - (y0 - ya), float(mx)))
    if not res:
        return 0.0, []
    return sum(r[2] for r in res) / len(res), res


def _orientar(cv2, np, page, n, n_alt, modelo):
    """Testa 0° e 180°: fica a orientação cuja grelha coincide melhor com o modelo."""
    t0 = _normalizar_ilumina(cv2, np, cv2.cvtColor(page, cv2.COLOR_BGR2GRAY))
    c0, _ = _correlacao_grelha(cv2, np, t0, modelo, n, n_alt)
    rot = cv2.rotate(page, cv2.ROTATE_180)
    t1 = _normalizar_ilumina(cv2, np, cv2.cvtColor(rot, cv2.COLOR_BGR2GRAY))
    c1, _ = _correlacao_grelha(cv2, np, t1, modelo, n, n_alt)
    return (page, t0, False) if c0 >= c1 else (rot, t1, True)


# ---------------------------------------------------------------------------
# Decisão das respostas
# ---------------------------------------------------------------------------
def _pontuar(tinta, modelo, n, n_alt, deslocamentos):
    """Pontuação 0..1 por pergunta e alternativa (tinta nova / tinta que faltava)."""
    cels, cols, linhas, _ = celulas_grelha(n, n_alt)
    scores = [[0.0] * n_alt for _ in range(n)]
    for q, i, cx, cy, lw, lh in cels:
        dx, dy = deslocamentos[min(q // linhas, len(deslocamentos) - 1)] if deslocamentos else (0, 0)
        x0 = int(round((cx - lw / 2 + 0.25) * PPM)) + dx
        x1 = int(round((cx + lw / 2 - 0.25) * PPM)) + dx
        y0 = int(round((cy - lh / 2 - 0.15) * PPM)) + dy
        y1 = int(round((cy + lh / 2 + 0.15) * PPM)) + dy
        if x0 < 0 or y0 < 0 or x1 > tinta.shape[1] or y1 > tinta.shape[0] or x1 <= x0 or y1 <= y0:
            continue
        mod = modelo[int(round((cy - lh / 2 - 0.15) * PPM)):int(round((cy + lh / 2 + 0.15) * PPM)),
                     int(round((cx - lw / 2 + 0.25) * PPM)):int(round((cx + lw / 2 - 0.25) * PPM))]
        obs = tinta[y0:y1, x0:x1]
        ref = float(mod.mean()) if mod.size else 0.0
        v = float(obs.mean())
        scores[q][i] = max(0.0, min(1.0, (v - ref) / max(1e-6, 1.0 - ref)))
    return scores


def decidir(scores, letras):
    """Resposta por pergunta: letra, '-' (em branco) ou '*' (dúvida). Devolve (respostas, duvidas)."""
    resp, duvidas = [], []
    for q, linha in enumerate(scores, start=1):
        ordem = sorted(range(len(linha)), key=lambda i: linha[i], reverse=True)
        a, b = linha[ordem[0]], linha[ordem[1]] if len(ordem) > 1 else 0.0
        if a < LIMIAR_FRACA:
            resp.append('-')
        elif a >= LIMIAR_MARCA and b < LIMIAR_FRACA:
            resp.append(letras[ordem[0]])
        elif a >= LIMIAR_FRACA and b >= LIMIAR_FRACA and b >= RAZAO_DUPLA * a:
            resp.append('*')
            duvidas.append({'n': q, 'motivo': 'DUPLA', 'candidatas': [letras[ordem[0]], letras[ordem[1]]]})
        elif a >= LIMIAR_MARCA:
            resp.append(letras[ordem[0]])
            duvidas.append({'n': q, 'motivo': 'RASURA', 'candidatas': [letras[ordem[0]], letras[ordem[1]]], 'sugerida': letras[ordem[0]]})
        else:
            resp.append('*')
            duvidas.append({'n': q, 'motivo': 'FRACA', 'candidatas': [letras[ordem[0]]], 'sugerida': letras[ordem[0]]})
    return resp, duvidas


# ---------------------------------------------------------------------------
# QR (identificação)
# ---------------------------------------------------------------------------
def _recortes_qr(cv2, np, original, M, rodada):
    """Zona do QR (canto superior direito da folha) tirada da foto ORIGINAL, numa só reamostragem e com 2×/3× mais
    pixéis por mm que a página endireitada: o QR tem muitos módulos e a endireitada perderia detalhe."""
    x0, y0, x1, y1 = 168.0, 4.0, 208.0, 36.0
    base = M.astype(np.float64)
    if rodada:
        base = np.array([[-1, 0, LARGURA_PX], [0, -1, ALTURA_PX], [0, 0, 1]], np.float64) @ base
    for esc in (2.0, 3.0):
        A = np.array([[esc, 0, -esc * x0 * PPM], [0, esc, -esc * y0 * PPM], [0, 0, 1]], np.float64)
        yield cv2.warpPerspective(original, A @ base, (int((x1 - x0) * PPM * esc), int((y1 - y0) * PPM * esc)),
                                  flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))


def _ler_qr(cv2, np, page, original, M, rodada):
    detectores = [cv2.QRCodeDetector()]
    if hasattr(cv2, 'QRCodeDetectorAruco'):
        detectores.append(cv2.QRCodeDetectorAruco())
    fim = time.monotonic() + 6
    candidatos = list(_recortes_qr(cv2, np, original, M, rodada))[::-1]       # 3× primeiro: nas simulações é o mais fiável
    candidatos.append(page[int(4 * PPM):int(40 * PPM), int(110 * PPM):LARGURA_PX])
    for reg in candidatos:
        cinza = cv2.cvtColor(reg, cv2.COLOR_BGR2GRAY)
        variantes = (
            cv2.adaptiveThreshold(cinza, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 41, 8),
            reg,
            cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4)).apply(cinza),
        )
        for v in variantes:
            for det in detectores:
                if time.monotonic() > fim:
                    return ''
                try:
                    t = det.detectAndDecode(v)[0]
                except cv2.error:
                    continue
                if t:
                    return t
    return ''


def identificar(texto_qr):
    """Dados assinados da folha ({'e','a','t','d','y','v','n'}) ou None se ilegível/falsificado."""
    from apps.documentos.services import folha_resposta_service as fr
    if not texto_qr:
        return None
    try:
        q = parse_qs(urlparse(texto_qr).query)
        return fr.validar_token_verificacao((q.get('d') or [''])[0], (q.get('s') or [''])[0])
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Pré-visualização
# ---------------------------------------------------------------------------
def _jpeg_b64(cv2, img, largura, qualidade):
    h, w = img.shape[:2]
    k = largura / w
    pq = cv2.resize(img, (largura, int(h * k)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode('.jpg', pq, [int(cv2.IMWRITE_JPEG_QUALITY), qualidade])
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.tobytes()).decode('ascii')


def _sobrepor(cv2, page, n, n_alt, respostas, duvidas, letras):
    cels, _, _, _ = celulas_grelha(n, n_alt)
    sobre = page.copy()
    em_duvida = {d['n'] for d in duvidas}
    for q, i, cx, cy, lw, lh in cels:
        r = respostas[q]
        if r == letras[i] or (r == '*' and (q + 1) in em_duvida):
            cor = (0, 140, 255) if (q + 1) in em_duvida else (0, 170, 0)
            p1 = (int((cx - lw / 2 - 0.8) * PPM), int((cy - lh / 2 - 1.2) * PPM))
            p2 = (int((cx + lw / 2 + 0.8) * PPM), int((cy + lh / 2 + 1.2) * PPM))
            if r == letras[i] or (q + 1) in em_duvida:
                cv2.rectangle(sobre, p1, p2, cor, 3)
    return sobre


# ---------------------------------------------------------------------------
# API do módulo
# ---------------------------------------------------------------------------
def ler_pagina(img, n_perguntas, n_alternativas):
    """Lê uma página já carregada. Devolve dict com respostas ('ABC-*'), dúvidas, avisos, QR e imagens."""
    cv2, np = _cv()
    if not (2 <= n_alternativas <= 6) or not (1 <= n_perguntas <= 100):
        raise ErroOMR('Configuração de folha inválida.')
    letras = 'ABCDEF'[:n_alternativas]
    nitidez = float(cv2.Laplacian(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())
    page, M = endireitar(img)
    modelo = _modelo(n_perguntas, n_alternativas)
    page, tinta, rodada = _orientar(cv2, np, page, n_perguntas, n_alternativas, modelo)
    corr, desl = _correlacao_grelha(cv2, np, tinta, modelo, n_perguntas, n_alternativas)
    if corr < 0.5:       # folhas certas dão ≥ 0.85 nas simulações; de outra prova ≤ 0.47
        raise ErroOMR('A grelha de respostas não coincide com a folha desta prova (número de perguntas/alternativas diferente '
                      'ou folha de outra prova). Confirme se é a Folha de Resposta gerada para esta prova.')
    deslocamentos = [(dx, dy) for dx, dy, _c in desl]
    scores = _pontuar(tinta, modelo, n_perguntas, n_alternativas, deslocamentos)
    respostas, duvidas = decidir(scores, letras)
    avisos = []
    if nitidez < LAPLACE_MIN:
        avisos.append('Fotografia desfocada: confirme as respostas com atenção ou volte a fotografar.')
    if corr < 0.75:
        avisos.append('Alinhamento da grelha pouco fiável: confirme as respostas.')
    qr = identificar(_ler_qr(cv2, np, page, img, M, rodada))
    return {
        'respostas': ''.join(respostas),
        'duvidas': duvidas,
        'avisos': avisos,
        'qr': qr,
        'alinhamento': round(corr, 3),
        'nitidez': round(nitidez, 1),
        'pagina': _jpeg_b64(cv2, page, 1240, 74),
        'previa': _jpeg_b64(cv2, _sobrepor(cv2, page, n_perguntas, n_alternativas, respostas, duvidas, letras), 900, 70),
    }
