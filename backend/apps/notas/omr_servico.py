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
MAX_BYTES = 60 * 1024 * 1024    # PDF digitalizado com a turma inteira
MAX_PIXELS = 80_000_000
LADO_MAX_FOTO = 3200
MAX_PAGINAS_PDF = 200
LIMIAR_MARCA = 0.17             # tinta nova na alternativa para contar como marcada (riscos finos de caneta chegam a 0.17–0.3)
LIMIAR_FRACA = 0.13             # o ruído do papel/scanner numa alternativa em branco fica abaixo de 0.13
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
    fundo = cv2.morphologyEx(cinza, cv2.MORPH_CLOSE, np.ones((45, 45), np.uint8))
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
def abrir_lote(dados: bytes, indices):
    """Abre as páginas `indices` de uma só vez (o PDF abre-se UMA vez, não uma por página).

    Devolve [(img, original, erro)]: `img` é a página a ~200 dpi para ler a grelha; `original` é a imagem digitalizada
    completa (para o QR) ou None. Em digitalizações (uma imagem por página) usa-se a própria imagem, reduzida —
    muito mais rápido do que desenhar a página do PDF outra vez."""
    cv2, np = _cv()
    if dados[:5] != b'%PDF-':
        out = []
        for i in indices:
            try:
                out.append((abrir_pagina(dados, i), None, None))
            except ErroOMR as e:
                out.append((None, None, str(e)))
        return out
    import fitz
    try:
        doc = fitz.open(stream=dados, filetype='pdf')
    except Exception:
        return [(None, None, 'Não foi possível abrir o PDF.') for _ in indices]
    out = []
    try:
        for i in indices:
            try:
                if i < 0 or i >= min(doc.page_count, MAX_PAGINAS_PDF):
                    raise ErroOMR('Página inexistente no PDF.')
                pg = doc[i]
                imgs = pg.get_images(full=True)
                nat = None
                if len(imgs) == 1:
                    try:
                        x = doc.extract_image(imgs[0][0])
                        nat = cv2.imdecode(np.frombuffer(x['image'], np.uint8), cv2.IMREAD_COLOR)
                        if nat is not None and max(nat.shape[:2]) > 5000:
                            nat = None
                    except Exception:
                        nat = None
                if nat is not None:
                    k = min(1.0, 1654.0 / nat.shape[1])
                    img = cv2.resize(nat, None, fx=k, fy=k, interpolation=cv2.INTER_AREA) if k < 1.0 else nat
                    out.append((img, nat, None))
                    continue
                esc = min(200 / 72, 3400 / max(pg.rect.width, pg.rect.height))
                pix = pg.get_pixmap(matrix=fitz.Matrix(esc, esc), colorspace=fitz.csRGB, alpha=False)
                arr = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 3)
                out.append((cv2.cvtColor(arr, cv2.COLOR_RGB2BGR), None, None))
            except ErroOMR as e:
                out.append((None, None, str(e)))
            except Exception:
                out.append((None, None, 'Não foi possível ler esta página do PDF.'))
    finally:
        doc.close()
    return out


def imagem_original_pdf(dados: bytes, indice: int):
    """PDF digitalizado (uma imagem por página): devolve essa imagem original (ex.: 300 dpi), onde o QR ainda se lê;
    None se a página não for uma digitalização simples."""
    if dados[:5] != b'%PDF-':
        return None
    cv2, np = _cv()
    import fitz
    try:
        doc = fitz.open(stream=dados, filetype='pdf')
    except Exception:
        return None
    try:
        if indice < 0 or indice >= doc.page_count:
            return None
        imgs = doc[indice].get_images(full=True)
        if len(imgs) != 1:
            return None
        x = doc.extract_image(imgs[0][0])
        nat = cv2.imdecode(np.frombuffer(x['image'], np.uint8), cv2.IMREAD_COLOR)
        if nat is None or max(nat.shape[:2]) > 5000:
            return None
        return nat
    except Exception:
        return None
    finally:
        doc.close()


def ler_qr_original(img):
    """Lê o QR no canto superior direito da imagem original (digitalização): recortes ampliados 2–4× com várias
    binarizações e os dois detectores do OpenCV. Devolve o texto ou ''."""
    import time
    cv2, np = _cv()
    h, w = img.shape[:2]
    limite = time.time() + 0.6          # orçamento curto: uma folha sem QR legível não pode atrasar o lote
    # passagem rápida (≈ 0,2 s): o detector Aruco a 1,5× lê quase todos os QR bons logo à primeira
    g0 = cv2.cvtColor(img[0:int(h * 0.15), int(w * 0.66):w], cv2.COLOR_BGR2GRAY)
    det_a = getattr(cv2, 'QRCodeDetectorAruco', None)
    if det_a is not None:
        for k in (1.5, 2):
            try:
                t, _, _ = det_a().detectAndDecode(cv2.resize(g0, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC))
            except Exception:
                continue
            if t and 'verificar' in t:
                return t
    for fy, fx in ((0.19, 0.42),):
        recorte = img[0:int(h * fy), int(w * (1 - fx)):w]
        g = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
        for k in (2, 3):
            big = cv2.resize(g, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)
            suave = cv2.GaussianBlur(big, (0, 0), 1.5)
            variantes = [
                big, suave,
                cv2.adaptiveThreshold(big, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 10),
                cv2.adaptiveThreshold(suave, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 71, 8),
                cv2.threshold(cv2.GaussianBlur(big, (0, 0), 2), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
            ]
            for v in variantes:
                for det in (cv2.QRCodeDetector, getattr(cv2, 'QRCodeDetectorAruco', None)):
                    if det is None:
                        continue
                    try:
                        t, _, _ = det().detectAndDecode(v)
                    except Exception:
                        continue
                    if t and 'verificar' in t:
                        return t
                if time.time() > limite:
                    return ''
    return ''


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
        raise ErroOMR('Ficheiro inválido ou demasiado grande (máximo 60 MB).')
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


def _quatro_por_cantos(cv2, np, img):
    """Procura a marca preta em cada canto da imagem (digitalizações e fotos com a folha a ocupar a imagem toda).

    Usa o maior canal (B,G,R): o preto fica escuro em todos, a tinta azul/colorida do aluno não conta como marca."""
    h, w = img.shape[:2]
    jan = 0.22
    sw, sh = int(w * jan), int(h * jan)
    zonas = [(0, 0), (w - sw, 0), (w - sw, h - sh), (0, h - sh)]
    cantos = [(0, 0), (w, 0), (w, h), (0, h)]
    lado_min, lado_max = 0.010 * w, 0.045 * w
    res = []
    for (x0, y0), (cx, cy) in zip(zonas, cantos):
        z = cv2.GaussianBlur(img[y0:y0 + sh, x0:x0 + sw].max(axis=2), (3, 3), 0)     # só nas 4 janelas dos cantos (não na imagem toda)
        melhor = None
        for lim in (90, 120, 60):
            bw = (z < lim).astype(np.uint8) * 255
            # o fecho une a marca quando o scanner a corta com um risco branco fino
            bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
            bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
            contornos, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in contornos:
                area = cv2.contourArea(c)
                (px, py), (rw, rh), _a = cv2.minAreaRect(c)
                if min(rw, rh) < lado_min or max(rw, rh) > lado_max or min(rw, rh) / max(rw, rh) < 0.45:
                    continue
                if area / (rw * rh) < 0.75:     # quadrado cheio (0.55 deixava passar riscos de caneta e falhava folhas boas)
                    continue
                m = cv2.moments(c)
                if m['m00'] <= 0:
                    continue
                gx, gy = m['m10'] / m['m00'] + x0, m['m01'] / m['m00'] + y0
                lado = (rw + rh) / 2
                if min(rw, rh) / max(rw, rh) < 0.7:
                    # marca cortada pelo scanner/impressora (mais larga do que alta): o lado verdadeiro é o maior e
                    # o centro conta-se a partir da aresta que não foi cortada (a de dentro da folha)
                    bx, by, bw_, bh_ = cv2.boundingRect(c)
                    if bw_ <= bh_ * 1.3:
                        continue
                    lado = float(bw_)
                    gy = (by + bh_ - lado / 2 + y0) if cy == 0 else (by + lado / 2 + y0)
                d = (gx - cx) ** 2 + (gy - cy) ** 2
                if melhor is None or d < melhor[0]:
                    melhor = (d, gx, gy, lado)
            if melhor:
                break
        res.append((melhor[1], melhor[2], melhor[3]) if melhor else None)
    em_falta = [i for i, p in enumerate(res) if p is None]
    if len(em_falta) > 1:
        return None
    if em_falta:
        # um canto apagado/coberto: deduz-se dos outros três (paralelogramo: tl + br = tr + bl)
        k = em_falta[0]
        tl, tr, br, bl = res
        if k == 0:
            xy = (tr[0] + bl[0] - br[0], tr[1] + bl[1] - br[1])
        elif k == 1:
            xy = (tl[0] + br[0] - bl[0], tl[1] + br[1] - bl[1])
        elif k == 2:
            xy = (tr[0] + bl[0] - tl[0], tr[1] + bl[1] - tl[1])
        else:
            xy = (tl[0] + br[0] - tr[0], tl[1] + br[1] - tr[1])
        vizinho = next(p for p in res if p is not None)
        res[k] = (xy[0], xy[1], vizinho[2])
    lados = [p[2] for p in res]
    if max(lados) > 1.7 * min(lados):
        return None
    return res


def endireitar(img):
    """Devolve (bgr_endireitada LARGURA_PX×ALTURA_PX, info). Levanta ErroOMR se não achar as 4 marcas."""
    cv2, np = _cv()
    cinza = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    quatro = _quatro_por_cantos(cv2, np, img)
    if quatro and not _validar_proporcao(_ordenar_retrato(quatro)):
        quatro = None
    if not quatro:
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
    page = cv2.warpPerspective(img, M, (LARGURA_PX, ALTURA_PX), flags=cv2.INTER_LINEAR, borderValue=(255, 255, 255))
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


def _cinzas_por_cor(cv2, np, page):
    """Separa a tinta válida (preta ou azul) da inválida (vermelha, verde, laranja… — a do professor, por exemplo).

    Devolve (cinza só com a tinta válida, cinza só com a tinta inválida); o papel fica a 255 nos dois."""
    cinza = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(page, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    azul = (h >= 85) & (h <= 150)
    # o preto/azul muito escuro tem matiz instável (V baixo) e conta sempre como válido; vermelho/verde/laranja são vivos
    invalida = (s > 110) & (v >= 90) & (v < 240) & ~azul
    invalida = cv2.dilate(invalida.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    valida = cinza.copy()
    valida[invalida] = 255
    so_invalida = np.full_like(cinza, 255)
    so_invalida[invalida] = cinza[invalida]
    return valida, so_invalida


def _orientar_completo(cv2, np, page, n, n_alt, modelo):
    """Testa 0° (e só se a grelha não coincidir bem, também 180°). Devolve (page, tinta, rodada, cinza_tinta_invalida).

    Cada passo caro (separar as cores, normalizar a luz) faz-se uma só vez por orientação."""
    valida, inv = _cinzas_por_cor(cv2, np, page)
    t0 = _normalizar_ilumina(cv2, np, valida)
    c0, _ = _correlacao_grelha(cv2, np, t0, modelo, n, n_alt)
    if c0 >= 0.45:                      # folha na posição certa: não vale a pena testar de cabeça para baixo
        return page, t0, False, inv
    rot = cv2.rotate(page, cv2.ROTATE_180)
    valida1, inv1 = _cinzas_por_cor(cv2, np, rot)
    t1 = _normalizar_ilumina(cv2, np, valida1)
    c1, _ = _correlacao_grelha(cv2, np, t1, modelo, n, n_alt)
    return (page, t0, False, inv) if c0 >= c1 else (rot, t1, True, inv1)


def _orientar(cv2, np, page, n, n_alt, modelo):
    """Testa 0° e 180°: fica a orientação cuja grelha coincide melhor com o modelo."""
    return _orientar_completo(cv2, np, page, n, n_alt, modelo)[:3]


# ---------------------------------------------------------------------------
# Decisão das respostas
# ---------------------------------------------------------------------------
def _desloc_linha(cv2, np, tinta, modelo, linha, dx0, dy0, folga=20, minimo=0.22):
    """Alinha CADA linha (pergunta) pelo seu próprio desenho impresso (caixas + letras), numa janela de ±2,5 mm à volta do
    deslocamento da coluna. Corrige a deriva vertical/horizontal das digitalizações esticadas ou inclinadas, que fazia a
    tinta das últimas linhas (ex.: perguntas 19, 20, 39, 40) cair fora da janela e ler-se como «em branco»."""
    try:
        _q, _i, cx0, cy, lw, lh = linha[0]
        cx1 = linha[-1][2]
        x0, x1 = int(round((cx0 - lw / 2 - 0.8) * PPM)), int(round((cx1 + lw / 2 + 0.8) * PPM))
        y0, y1 = int(round((cy - lh / 2 - 1.6) * PPM)), int(round((cy + lh / 2 + 1.6) * PPM))
        mod = modelo[y0:y1, x0:x1]
        xa, ya = x0 + dx0 - folga, y0 + dy0 - folga
        xb, yb = x1 + dx0 + folga, y1 + dy0 + folga
        if mod.size == 0 or xa < 0 or ya < 0 or xb > tinta.shape[1] or yb > tinta.shape[0]:
            return dx0, dy0
        r = cv2.matchTemplate(tinta[ya:yb, xa:xb], mod, cv2.TM_CCOEFF_NORMED)
        _mn, mx, _l, loc = cv2.minMaxLoc(r)
        if mx < minimo:
            return dx0, dy0
        return dx0 - folga + loc[0], dy0 - folga + loc[1]
    except Exception:
        return dx0, dy0

def _pontuar(tinta, modelo, n, n_alt, deslocamentos):
    """Pontuação 0..1 por pergunta e alternativa (tinta nova / tinta que faltava)."""
    cels, cols, linhas, _ = celulas_grelha(n, n_alt)
    scores = [[0.0] * n_alt for _ in range(n)]
    cv2, np = _cv()
    por_linha = {}
    for c in cels:
        por_linha.setdefault(c[0], []).append(c)
    desl_linha = {}
    for q, lin in por_linha.items():
        bx, by = deslocamentos[min(q // linhas, len(deslocamentos) - 1)] if deslocamentos else (0, 0)
        desl_linha[q] = _desloc_linha(cv2, np, tinta, modelo, lin, bx, by)
    for q, i, cx, cy, lw, lh in cels:
        dx, dy = desl_linha[q]
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
        if a < LIMIAR_FRACA and a >= 0.09 and a >= 2.5 * b:   # uma só marca, mas fraca (caneta clara): conta como resposta, nunca como nula
            resp.append(letras[ordem[0]])
            duvidas.append({'n': q, 'motivo': 'FRACA', 'candidatas': [letras[ordem[0]]], 'sugerida': letras[ordem[0]]})
        elif a < LIMIAR_FRACA:
            resp.append('-')
        elif (a >= LIMIAR_MARCA and b < LIMIAR_FRACA) or b < 0.07:   # única alternativa com tinta, mesmo fraca
            resp.append(letras[ordem[0]])
        elif a >= LIMIAR_FRACA and b >= LIMIAR_FRACA and b >= RAZAO_DUPLA * a:
            resp.append('N')       # mais de uma alternativa assinalada: questão nula (vale 0), sem precisar de revisão
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
    fim = time.monotonic() + 1.5
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


# ---------------------------------------------------------------------------
# Identificação do aluno pelo Nº escrito à mão (folha não personalizada, sem QR)
# O nome em letra cursiva não se lê com fiabilidade; o Nº (dígitos) lê-se bem e coincide com o último segmento do código
# oficial do aluno (0101S0001.12.01.2026.cg.NN): é a chave usada para identificar o aluno dentro da turma da prova.
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=1)
def _motor_ocr():
    from rapidocr_onnxruntime import RapidOCR
    return RapidOCR()


def _memoria_livre_mb():
    try:
        with open('/proc/meminfo') as f:
            for linha in f:
                if linha.startswith('MemAvailable:'):
                    return int(linha.split()[1]) // 1024
    except OSError:
        pass
    return 10 ** 6          # sem /proc (Windows/desenvolvimento): sem limite


def ler_numero_manuscrito(jpeg_alta):
    """Lê o «Nº» escrito à mão no campo TURMA/Nº da folha endireitada. Devolve (numero, confianca) ou None.
    Só dígitos com confiança ≥ 0,9; o último número do campo é o Nº (o anterior é a turma)."""
    try:
        import re
        if _memoria_livre_mb() < 450:          # servidor pequeno: o OCR (~200 MB) só corre com memória sobrando (nunca derruba o site)
            return None
        cv2, np = _cv()
        im = cv2.imdecode(np.frombuffer(jpeg_alta, np.uint8), cv2.IMREAD_COLOR)
        ppm = im.shape[1] / 210.0
        rec = im[int(63 * ppm):int(77 * ppm), int(72 * ppm):int(104 * ppm)]
        res, _t = _motor_ocr()(rec)
        nums = [(int(r[1]), float(r[2])) for r in (res or []) if re.fullmatch(r'\d{1,3}', str(r[1]).strip()) and float(r[2]) >= 0.9]
        return nums[-1] if nums else None
    except Exception:
        return None


def numero_do_aluno(matricula):
    """Nº do aluno na turma = último segmento numérico do código oficial (…ano.area.NN)."""
    import re
    m = re.search(r'\.(\d{1,3})$', str(matricula or '').strip())
    return int(m.group(1)) if m else None

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


def _padroes_code128():
    """Tabela do Code 128: valor → 6 larguras (7 no stop), a partir da do ReportLab (maiúscula = barra, minúscula = espaço;
    a/A = 1, b/B = 2, c/C = 3, d/D = 4 módulos)."""
    from reportlab.graphics.barcode import code128
    larg = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    return {v: tuple(larg[ch.lower()] for ch in p) for v, p in code128._patterns.items()}


def _decodificar_code128(corridas):
    """Descodifica uma sequência de corridas (largura em pixéis, a começar por uma barra). Devolve texto ou ''."""
    pad = _padroes_code128()
    por_padrao = {p: v for v, p in pad.items() if len(p) == 6}
    n = len(corridas)

    def valor(grupo):
        soma = sum(grupo)
        mod = soma / 11.0
        if mod < 1.0:
            return None
        larg = tuple(max(1, min(4, int(round(g / mod)))) for g in grupo)
        if sum(larg) != 11:
            return None
        return por_padrao.get(larg)

    for i in range(0, max(0, n - 6)):
        v0 = valor(corridas[i:i + 6])
        if v0 not in (103, 104, 105):
            continue
        valores, j, ok = [v0], i + 6, True
        while j + 6 <= n:
            g = corridas[j:j + 6]
            v = valor(g)
            if v is None:
                # o stop (106) tem 7 elementos: 2331112
                ok = j + 7 <= n and abs(sum(corridas[j:j + 7]) / 13.0 - sum(corridas[i:i + 6]) / 11.0) < 0.6 * (sum(corridas[i:i + 6]) / 11.0)
                break
            valores.append(v)
            j += 6
        if not ok or len(valores) < 4:
            continue
        *dados, chk = valores[1:]
        soma = valores[0] + sum((k + 1) * v for k, v in enumerate(dados))
        if soma % 103 != chk:
            continue
        conj, saida = {103: 'A', 104: 'B', 105: 'C'}[valores[0]], []
        for v in dados:
            if v in (99, 100, 101):
                conj = {99: 'C', 100: 'B', 101: 'A'}[v]
            elif v >= 96 and conj != 'C':
                continue
            elif conj == 'C':
                saida.append(f'{v:02d}')
            elif conj == 'B':
                saida.append(chr(v + 32))
            else:
                saida.append(chr(v + 32) if v < 64 else chr(v - 64))
        return ''.join(saida)
    return ''


def ler_codigo_barras(page):
    """Código de barras (Code 128) do aluno impresso na secção «Dados do aluno» das folhas personalizadas.

    `page` é a folha já endireitada (8 px/mm). Devolve o texto (o código/matrícula do aluno) ou ''.
    (O detector de barras do OpenCV só lê EAN/UPC, por isso o Code 128 é descodificado aqui.)"""
    cv2, np = _cv()
    cinza = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
    recorte = cinza[int(40 * PPM):int(118 * PPM), int(8 * PPM):int(112 * PPM)]
    k = 3
    grande = cv2.resize(recorte, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)
    limiar = cv2.threshold(cv2.GaussianBlur(grande, (0, 0), 1.2), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[0]
    h, w = grande.shape
    for y in range(0, h, 4):
        linha = grande[y] < limiar
        # só linhas com muitas transições podem ser de um código de barras
        if np.count_nonzero(linha[1:] != linha[:-1]) < 80:
            continue
        mudancas = np.flatnonzero(linha[1:] != linha[:-1]) + 1
        if not len(mudancas):
            continue
        corridas = np.diff(np.concatenate(([0], mudancas, [w]))).tolist()
        if linha[0]:
            pass
        else:
            corridas = corridas[1:]          # a primeira corrida tem de ser uma barra
        texto = _decodificar_code128(corridas)
        if len(texto) >= 4:
            return texto
    return ''


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
# Folha corrigida (modelo do professor: visto nas certas, círculo na certa das erradas, acertos, nota e assinatura)
# ---------------------------------------------------------------------------
VERMELHO = (40, 40, 215)    # BGR


def _fonte_ttf(estilos):
    import os
    from PIL import ImageFont
    pastas = ['/usr/share/fonts/truetype/liberation', '/usr/share/fonts/truetype/dejavu', 'C:/Windows/Fonts']
    for nome in estilos:
        for pasta in pastas:
            p = os.path.join(pasta, nome)
            if os.path.isfile(p):
                return p
    return None


def _texto_pil(cv2, np, img, texto, x_mm, y_base_mm, larg_max_mm, altura_mm, estilos, cor=VERMELHO):
    """Escreve `texto` (com acentos) em Times/Liberation, ajustado à largura máxima; a base do texto fica em y_base_mm."""
    from PIL import Image, ImageDraw, ImageFont
    caminho = _fonte_ttf(estilos)
    tam = max(8, int(round(altura_mm * PPM)))
    while True:
        fonte = ImageFont.truetype(caminho, tam) if caminho else ImageFont.load_default()
        larg = fonte.getlength(texto) if hasattr(fonte, 'getlength') else len(texto) * tam * 0.5
        if larg <= larg_max_mm * PPM or tam <= 10:
            break
        tam -= 2
    im = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(im)
    d.text((int(x_mm * PPM), int(y_base_mm * PPM)), texto, font=fonte, fill=(cor[2], cor[1], cor[0]), anchor='ls')
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def _valor_pt(v):
    return f'{float(v):.1f}'.replace('.', ',')


def _circulo_a_mao(cv2, np, img, cx, cy, rx, ry, semente, esp):
    """Círculo CLÁSSICO e nítido (elipse perfeita, traço firme e contínuo) à volta da alternativa certa: vê-se logo que
    foi o sistema que corrigiu."""
    esp = max(3, int(round(esp * 1.6)))
    cv2.ellipse(img, (int(round(cx * 16)), int(round(cy * 16))), (int(round(rx * 16)), int(round(ry * 16))),
                0, 0, 360, VERMELHO, esp, cv2.LINE_AA, 4)

def _afinar_centro(cv2, np, cinza, cx, cy, lw, lh, ppm, folga_mm=1.8, minimo=0.30):
    """Corrige o centro (mm) da alternativa para o quadrinho realmente impresso nesta folha: procura, numa janela de
    ±1,8 mm, o contorno oco do quadrinho (correlação normalizada; a tinta do aluno dentro do quadrinho não atrapalha).
    Se a certeza for baixa mantém a posição do modelo."""
    try:
        w, h = max(6, int(round(lw * ppm))), max(4, int(round(lh * ppm)))
        esp = max(2, int(round(0.35 * ppm)))
        tpl = np.zeros((h, w), np.float32)
        cv2.rectangle(tpl, (0, 0), (w - 1, h - 1), 1.0, esp)
        pad = int(round(folga_mm * ppm))
        x0, y0 = int(round(cx * ppm - w / 2)) - pad, int(round(cy * ppm - h / 2)) - pad
        x1, y1 = x0 + w + 2 * pad, y0 + h + 2 * pad
        if x0 < 0 or y0 < 0 or y1 > cinza.shape[0] or x1 > cinza.shape[1]:
            return cx, cy
        escuro = (cinza[y0:y1, x0:x1] < 150).astype(np.float32)
        res = cv2.matchTemplate(escuro, tpl, cv2.TM_CCORR_NORMED)
        _mn, mx, _l, loc = cv2.minMaxLoc(res)
        if mx < minimo:
            return cx, cy
        return (x0 + loc[0] + w / 2) / ppm, (y0 + loc[1] + h / 2) / ppm
    except Exception:
        return cx, cy


def _visto_a_mao(cv2, np, img, x, y, ppm, semente, esp):
    """Certo CLÁSSICO (✓): traço curto para baixo e traço longo a subir à direita, firme e bem visível."""
    esp = max(3, int(round(esp * 1.7)))
    mm = [(0.0, -0.1), (1.1, 1.3), (4.7, -2.9)]       # compacto: cabe no espaço entre alternativas e na altura da linha
    pts = np.array([[(x + a * ppm) * 16, (y + b * ppm) * 16] for a, b in mm], np.int32)
    cv2.polylines(img, [pts], False, VERMELHO, esp, cv2.LINE_AA, 4)

def _textos_pil(cv2, np, img, itens, ppm=None):
    """Escreve vários textos (com acentos) numa só conversão da imagem. itens: (texto, x_mm, y_base_mm, larg_max_mm, altura_mm, estilos)."""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(im)
    cor = (VERMELHO[2], VERMELHO[1], VERMELHO[0])
    ppm = ppm or PPM
    for texto, x_mm, y_mm, larg_mm, alt_mm, estilos in itens:
        caminho = _fonte_ttf(estilos)
        tam = max(8, int(round(alt_mm * ppm)))
        while True:
            fonte = ImageFont.truetype(caminho, tam) if caminho else ImageFont.load_default()
            larg = fonte.getlength(texto) if hasattr(fonte, 'getlength') else len(texto) * tam * 0.5
            if larg <= larg_mm * ppm or tam <= 10:
                break
            tam -= 2
        d.text((int(x_mm * ppm), int(y_mm * ppm)), texto, font=fonte, fill=cor, anchor='ls')
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def anotar_folha(imagem_bgr, n_perguntas, n_alternativas, respostas, chave, acertos, nota, nome_professor, largura=None):
    """Desenha a correcção a vermelho, como no modelo do professor, na folha já endireitada; devolve JPEG (bytes).

    Modelo (docs/modelos/Modelo de correccao da prova.pdf; skill «modelo-correccao-prova»):
      * resposta certa  → visto fino de caneta à direita da alternativa assinalada;
      * resposta errada, em branco ou nula → círculo fino à volta da alternativa CERTA (nula: escreve também «Nula»);
      * «Acertos (n.º)» e «Correcção normal (valores)» escritos a vermelho (nota com uma casa decimal, ex.: 14,0);
      * «Ass. do Professor» com o NOME do professor (não rubrica).
    respostas: 'AB-C…' (uma por pergunta); chave: letras certas (mesma versão da folha)."""
    cv2, np = _cv()
    # Trabalha na resolução da própria imagem (folha endireitada em alta resolução, ~250 dpi): nada é reduzido nem deformado.
    page = imagem_bgr if imagem_bgr.shape[1] >= 1500 else cv2.resize(imagem_bgr, (LARGURA_PX, ALTURA_PX), interpolation=cv2.INTER_CUBIC)
    page = page.copy()
    ppm = page.shape[1] / 210.0
    letras = 'ABCDEF'[:n_alternativas]
    cels, _, _, _ = celulas_grelha(n_perguntas, n_alternativas)
    pos = {(q, i): (cx, cy, lw, lh) for q, i, cx, cy, lw, lh in cels}
    cinza = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
    esp = max(2, int(round(0.24 * ppm)))      # traço fino de caneta (≈ 0,25 mm), como no modelo
    textos = []
    # passo entre linhas (mm) e tamanho do círculo: NUNCA se cruzam círculos de linhas seguidas (folga ≥ 0,6 mm entre eles)
    passo_lin = min([pos[(q + 1, 0)][1] - pos[(q, 0)][1] for q in range(n_perguntas - 1) if (q + 1, 0) in pos and pos[(q + 1, 0)][1] > pos[(q, 0)][1]] or [6.0])
    traco_mm = max(3, int(round(esp * 1.6))) / ppm
    ry_mm = min(2.4, passo_lin / 2 - traco_mm / 2 - 0.3)
    rx_mm = None
    marcas = {}          # q -> [cx, cy, cx_modelo, cy_modelo, lw, lh, tipo]
    for q in range(n_perguntas):
        certa = chave[q] if q < len(chave) else ''
        dada = respostas[q] if q < len(respostas) else '-'
        if certa not in letras:
            continue
        cx0, cy0, lw, lh = pos[(q, letras.index(certa))]
        cx, cy = _afinar_centro(cv2, np, cinza, cx0, cy0, lw, lh, ppm)      # encaixa no quadrinho IMPRESSO desta folha
        if abs(cy - cy0) > 0.8:
            cy = cy0 + (0.8 if cy > cy0 else -0.8)                          # o ajuste é fino: nunca empurra a marca para a linha vizinha
        marcas[q] = [cx, cy, cx0, cy0, lw, lh, 'visto' if dada == certa else 'circulo', dada]
    # círculos em linhas consecutivas da mesma coluna: se ficarem a menos de 2·ry + 0,9 mm, voltam à posição do modelo
    for q, m in marcas.items():
        v = marcas.get(q + 1)
        if m[6] == 'circulo' and v and v[6] == 'circulo' and abs(v[0] - m[0]) < 12.0 and abs(v[1] - m[1]) < 2 * ry_mm + traco_mm + 0.9:
            m[0], m[1], v[0], v[1] = m[2], m[3], v[2], v[3]
    for q, (cx, cy, cx0, cy0, lw, lh, tipo, dada) in marcas.items():
        if tipo == 'visto':
            _visto_a_mao(cv2, np, page, (cx + lw / 2 + 0.6) * ppm, cy * ppm, ppm, q + 1, esp)
            continue
        # elipse que contém os 4 cantos do quadrinho e a letra, sem tocar nas linhas vizinhas nem nas alternativas ao lado
        rx_mm = (lw / 2) * 1.23
        _circulo_a_mao(cv2, np, page, cx * ppm, cy * ppm, rx_mm * ppm, ry_mm * ppm, q + 1, esp)
        if dada not in letras:   # mais de uma alternativa assinalada ('N') OU nenhuma ('-'): «Questão nula» na MESMA linha, à direita
            ux, uy, ulw, ulh = pos[(q, len(letras) - 1)]
            textos.append(('Questão nula', ux + ulw / 2 + 1.6, uy + 1.2, 24, 3.0,
                           ['timesbi.ttf', 'LiberationSerif-BoldItalic.ttf', 'DejaVuSerif-BoldItalic.ttf',
                            'timesi.ttf', 'LiberationSerif-Italic.ttf', 'DejaVuSerif-Italic.ttf']))
    from apps.documentos.services import folha_resposta_service as fr
    xii, yiii = fr.MARGEM + 109, 88.5
    estilo_i = ['timesi.ttf', 'LiberationSerif-Italic.ttf', 'DejaVuSerif-Italic.ttf']
    textos.append((str(int(acertos)), xii + 9, yiii + 12.6, 22, 6.2, estilo_i))
    textos.append((_valor_pt(nota), xii + 9, yiii + 20.3, 22, 7.4, estilo_i))
    if nome_professor:           # assinatura por extenso (nome), não rubrica
        textos.append((str(nome_professor)[:60], xii + 3.5, yiii + 27.2, 33, 4.2, estilo_i))
    page = _textos_pil(cv2, np, page, textos, ppm)
    if largura and largura < page.shape[1]:
        page = cv2.resize(page, (largura, int(page.shape[0] * largura / page.shape[1])), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode('.jpg', page, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    return buf.tobytes()

# ---------------------------------------------------------------------------
# API do módulo
# ---------------------------------------------------------------------------
def pagina_limpa_alta(fonte, M, rodada, k, ppm=10.0, qualidade=90, desloc=(0.0, 0.0)):
    """A folha ENDIREITADA em alta resolução (≈ 250 dpi) a partir da imagem ORIGINAL (sem passar pela versão reduzida),
    sem tocar na marcação do aluno: é a base limpa da prova corrigida (que pode ser impressa e entregue ao aluno).

    `M` leva a imagem reduzida de leitura ao espaço da página (PPM px/mm); `k` = largura reduzida / largura da fonte."""
    cv2, np = _cv()
    Mn = M.astype(np.float64) @ np.diag([k, k, 1.0])
    if rodada:
        Mn = np.array([[-1, 0, LARGURA_PX], [0, -1, ALTURA_PX], [0, 0, 1]], np.float64) @ Mn
    # `desloc` = desvio médio (px do espaço da página) medido entre a grelha impressa e o modelo: corrige-se aqui para que
    # os vistos e círculos caiam exactamente sobre as alternativas (marcas de canto cortadas deslocam a folha ~1 mm)
    Mn = np.array([[1, 0, -float(desloc[0])], [0, 1, -float(desloc[1])], [0, 0, 1]], np.float64) @ Mn
    H = np.diag([ppm / PPM, ppm / PPM, 1.0]) @ Mn
    page = cv2.warpPerspective(fonte, H, (int(round(210 * ppm)), int(round(297 * ppm))),
                               flags=cv2.INTER_LINEAR, borderValue=(255, 255, 255))   # linear: ~2× mais rápido, igual a 250 dpi
    ok, buf = cv2.imencode('.jpg', page, [int(cv2.IMWRITE_JPEG_QUALITY), qualidade])
    return buf.tobytes()


def ler_pagina(img, n_perguntas, n_alternativas, procurar_qr=True, fonte=None, com_imagens=True):
    """Lê uma página já carregada. Devolve dict com respostas ('ABC-*'), dúvidas, avisos, QR e imagens."""
    cv2, np = _cv()
    if not (2 <= n_alternativas <= 6) or not (1 <= n_perguntas <= 100):
        raise ErroOMR('Configuração de folha inválida.')
    letras = 'ABCDEF'[:n_alternativas]
    nitidez = float(cv2.Laplacian(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())
    page, M = endireitar(img)
    modelo = _modelo(n_perguntas, n_alternativas)
    page, tinta, rodada, cinza_inv = _orientar_completo(cv2, np, page, n_perguntas, n_alternativas, modelo)
    corr, desl = _correlacao_grelha(cv2, np, tinta, modelo, n_perguntas, n_alternativas)
    # (em PDF digitalizado o QR lê-se na imagem original, fora daqui: evita procurá-lo duas vezes)
    qr = identificar(_ler_qr(cv2, np, page, img, M, rodada)) if procurar_qr else None
    n_qr = int((qr or {}).get('n') or 0)
    # O QR da folha diz quantas perguntas tem: é o critério seguro. Sem QR, a grelha tem de coincidir bem com o modelo
    # (digitalizações reais certas dão 0.5–0.6: a tinta do aluno baixa a correlação; simulações de outra prova ≤ 0.47).
    if (n_qr and n_qr != n_perguntas) or corr < (0.30 if n_qr == n_perguntas else 0.50):
        raise ErroOMR(f'A grelha desta folha não coincide com a prova seleccionada, que tem {n_perguntas} perguntas e '
                      f'{n_alternativas} alternativas (a folha tem outro número de perguntas/alternativas, ou é de outra prova). '
                      'Corrija o nº de perguntas/alternativas da prova na «Folha de resposta» do Passo 1 e crie a prova de novo.')
    deslocamentos = [(dx, dy) for dx, dy, _c in desl]
    scores = _pontuar(tinta, modelo, n_perguntas, n_alternativas, deslocamentos)
    respostas, duvidas = decidir(scores, letras)
    avisos = []
    # Tinta que não é azul nem preta não conta como resposta: se numa pergunta sem marca válida houver tinta de
    # outra cor na alternativa, avisa o professor (não é lida como resposta).
    if int(np.count_nonzero(cinza_inv < 200)) > 400:       # só se houver tinta de outra cor na folha (senão, poupa-se o passo)
        tinta_inv = _normalizar_ilumina(cv2, np, cinza_inv)
        sc_inv = _pontuar(tinta_inv, modelo, n_perguntas, n_alternativas, deslocamentos)
        for q, linha in enumerate(sc_inv):
            if respostas[q] == '-' and max(linha) >= 0.25:
                duvidas.append({'n': q + 1, 'motivo': 'COR', 'candidatas': [letras[linha.index(max(linha))]]})
                if 'Tinta que não é azul nem preta' not in ' '.join(avisos):
                    avisos.append('Tinta que não é azul nem preta não conta como resposta (perguntas assinaladas na revisão).')
    if nitidez < LAPLACE_MIN:
        avisos.append('Fotografia desfocada: confirme as respostas com atenção ou volte a fotografar.')
    if corr < 0.45:
        avisos.append('Alinhamento da grelha pouco fiável: confirme as respostas.')
    codigo = '' if qr else ler_codigo_barras(page)     # folha personalizada sem QR legível: código de barras do aluno
    return {
        'respostas': ''.join(respostas),
        'duvidas': duvidas,
        'avisos': avisos,
        'qr': qr,
        'codigo_barras': codigo,
        'alinhamento': round(corr, 3),
        'nitidez': round(nitidez, 1),
        # (miniaturas só quando o navegador as vai usar; com guardar=1 o servidor guarda tudo e não as devolve)
        'pagina': _jpeg_b64(cv2, page, 1240, 74) if com_imagens else '',
        'previa': _jpeg_b64(cv2, _sobrepor(cv2, page, n_perguntas, n_alternativas, respostas, duvidas, letras), 900, 70) if com_imagens else '',
        # base limpa em alta resolução (a partir da imagem ORIGINAL), para a prova corrigida que se imprime
        'alta': pagina_limpa_alta(fonte if fonte is not None else img, M, rodada,
                                  img.shape[1] / float(fonte.shape[1]) if fonte is not None else 1.0,
                                  desloc=(sum(d[0] for d in desl) / len(desl), sum(d[1] for d in desl) / len(desl)) if desl else (0.0, 0.0)),
    }
