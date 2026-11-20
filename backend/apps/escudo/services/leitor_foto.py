"""Leitura dos QR de uma fotografia de uma prova: diz de que cópia (e página ou pergunta) veio a foto.

Os QR são cinzentos e pequenos e a foto tem ruído; por isso lê-se a imagem inteira e depois por blocos que se sobrepõem,
com realce de contraste e ampliação, até se esgotarem as hipóteses (ou o tempo).
"""
import io
import re
import time

MAX_BYTES = 12 * 1024 * 1024
MAX_PIXELS = 60_000_000
LADO_MAX = 4200
TEMPO_MAX_S = 25
RE_QR = re.compile(r'/v/([A-Z0-9]{8})/(\d{1,5})(?:/([pq])(\d{1,3}))?(?![0-9A-Za-z])')


def _cv():
    try:
        import cv2
        import numpy as np
    except ImportError as e:  # pragma: no cover - o servidor tem a biblioteca instalada
        raise ValueError('O leitor de fotografias não está disponível neste servidor.') from e
    return cv2, np


def _abrir(dados: bytes):
    cv2, np = _cv()
    if not dados or len(dados) > MAX_BYTES:
        raise ValueError('Fotografia inválida ou demasiado grande (máximo 12 MB).')
    if dados[:3] != b'\xff\xd8\xff' and dados[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Envia a fotografia em JPEG ou PNG.')
    from PIL import Image
    try:
        with Image.open(io.BytesIO(dados)) as im:
            if im.width * im.height > MAX_PIXELS:
                raise ValueError('Fotografia demasiado grande.')
    except ValueError:
        raise
    except Exception as e:
        raise ValueError('Não foi possível abrir a fotografia.') from e
    img = cv2.imdecode(np.frombuffer(dados, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError('Não foi possível abrir a fotografia.')
    maior = max(img.shape[:2])
    if maior > LADO_MAX:
        k = LADO_MAX / maior
        img = cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    return img


def _variantes(cv2, rec):
    """O recorte como está, com contraste realçado (QR cinzentos) e ampliado quando é pequeno."""
    cinza = cv2.cvtColor(rec, cv2.COLOR_BGR2GRAY)
    yield rec
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4)).apply(cinza)
    yield clahe
    yield cv2.normalize(cinza, None, 0, 255, cv2.NORM_MINMAX)
    if max(rec.shape[:2]) < 1100:
        yield cv2.resize(clahe, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)


def ler_qrs(dados: bytes) -> list:
    """Textos dos QR encontrados na fotografia (sem repetições)."""
    cv2, _ = _cv()
    img = _abrir(dados)
    det = cv2.QRCodeDetector()
    achados = []
    fim = time.monotonic() + TEMPO_MAX_S

    def juntar(textos):
        for t in textos:
            if t and t not in achados:
                achados.append(t)

    try:
        ok, textos, _pts, _ = det.detectAndDecodeMulti(img)
        if ok:
            juntar(textos)
    except cv2.error:
        pass
    h, w = img.shape[:2]
    lado = max(500, int(max(h, w) / 3))
    passo = max(250, lado // 2)
    for y in range(0, max(1, h - lado // 2), passo):
        for x in range(0, max(1, w - lado // 2), passo):
            if time.monotonic() > fim:
                return achados
            rec = img[y:y + lado, x:x + lado]
            for v in _variantes(cv2, rec):
                try:
                    t, _p, _s = det.detectAndDecode(v)
                except cv2.error:
                    continue
                if t:
                    juntar([t])
                    break
    return achados


def interpretar(textos, pid: str) -> dict:
    """Agrupa as leituras desta prova por cópia (página e perguntas); `outras` conta QR de outras provas ou de fora do SIGE."""
    copias, outras = {}, 0
    for t in textos:
        m = RE_QR.search(t)
        if not m or m.group(1) != pid:
            outras += 1
            continue
        c = copias.setdefault(int(m.group(2)), {'paginas': set(), 'perguntas': set()})
        if m.group(3) == 'p':
            c['paginas'].add(int(m.group(4)))
        elif m.group(3) == 'q':
            c['perguntas'].add(int(m.group(4)))
    return {
        'copias': [{'serial': s, 'codigo': f'{pid}-{s:03d}', 'paginas': sorted(c['paginas']), 'perguntas': sorted(c['perguntas'])}
                   for s, c in sorted(copias.items())],
        'outras': outras,
    }
