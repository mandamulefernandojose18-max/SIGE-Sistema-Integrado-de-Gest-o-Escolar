# -*- coding: utf-8 -*-
"""Renderiza equacoes em formato de livro (fraccoes, radicais, expoentes, matrizes,
sistemas, tabelas) como imagens PNG de alta resolucao (300 dpi), em fonte STIX
(semelhante a Times New Roman). Nunca em forma linear.

Especificacoes (spec) aceites por render():
  "x^{2}+\\dfrac{a}{b}"          -> mathtext (LaTeX basico)
  "!texto simples"               -> texto em romano (com espacos)
  [spec, spec, ...]              -> composicao horizontal (centrada na vertical)
  ("sp", px)                     -> espaco horizontal
  ("mat", [[c11,c12],[c21,c22]], "[" | "|")   -> matriz / determinante
  ("sys", [linha1, linha2, ...])               -> sistema com chaveta a esquerda
  ("tab", [[...],[...]])                       -> tabela com linhas (1.a linha = cabecalho)
"""
import io
import hashlib
import os
import matplotlib

matplotlib.use("Agg")
from matplotlib import mathtext, font_manager
from PIL import Image, ImageDraw

matplotlib.rcParams["mathtext.fontset"] = "stix"
matplotlib.rcParams["font.family"] = "STIXGeneral"

DPI = 300
FS = 13
INK = (0, 0, 0)
_OUT = None
_cache = {}


def set_outdir(path):
    global _OUT
    _OUT = path
    os.makedirs(path, exist_ok=True)


def _math(s):
    if s.startswith("!"):
        t = s[1:].replace(" ", "\\ ")
        s = "\\mathrm{" + t + "}"
    if s.strip() == "":
        return Image.new("RGB", (4, 4), "white")
    buf = io.BytesIO()
    mathtext.math_to_image("$" + s + "$", buf, prop=font_manager.FontProperties(size=FS), dpi=DPI, format="png")
    im = Image.open(buf).convert("RGBA")
    bg = Image.new("RGB", im.size, "white")
    bg.paste(im, mask=im.split()[3])
    return bg


def _blank(w, h=4):
    return Image.new("RGB", (max(1, int(w)), h), "white")


def _hcompose(imgs, gap=14, pad=6):
    h = max(i.height for i in imgs) + 2 * pad
    w = sum(i.width for i in imgs) + gap * (len(imgs) - 1) + 2 * pad
    out = Image.new("RGB", (w, h), "white")
    x = pad
    for i in imgs:
        out.paste(i, (x, (h - i.height) // 2))
        x += i.width + gap
    return out


def _bezier(p0, p1, p2, n=18):
    pts = []
    for k in range(n + 1):
        t = k / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        pts.append((x, y))
    return pts


def _brace(h, w=26, lw=4):
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    m = h / 2.0
    r = min(w * 0.5, h * 0.12)
    pts = []
    pts += _bezier((w - 1, 1), (w / 2, 1), (w / 2, 1 + r))
    pts += [(w / 2, m - r)]
    pts += _bezier((w / 2, m - r), (w / 2, m), (1, m))
    pts += _bezier((1, m), (w / 2, m), (w / 2, m + r))
    pts += [(w / 2, h - 1 - r)]
    pts += _bezier((w / 2, h - 1 - r), (w / 2, h - 1), (w - 1, h - 1))
    d.line(pts, fill=INK, width=lw, joint="curve")
    return im


def _cells(rows):
    return [[(_render(c) if not isinstance(c, Image.Image) else c) for c in r] for r in rows]


def _grid(rows, delim=None, border=False, padx=26, pady=12):
    cells = _cells(rows)
    ncol = max(len(r) for r in cells)
    for r in cells:
        while len(r) < ncol:
            r.append(_blank(4))
    cw = [max(r[j].width for r in cells) + 2 * padx for j in range(ncol)]
    rh = [max(c.height for c in r) + 2 * pady for r in cells]
    W, H = sum(cw), sum(rh)
    m = 14
    out = Image.new("RGB", (W + 2 * m, H + 2 * m), "white")
    d = ImageDraw.Draw(out)
    y = m
    for i, r in enumerate(cells):
        x = m
        for j, c in enumerate(r):
            out.paste(c, (x + (cw[j] - c.width) // 2, y + (rh[i] - c.height) // 2))
            x += cw[j]
        y += rh[i]
    if border:
        x = m
        for j in range(ncol + 1):
            d.line([(x, m), (x, m + H)], fill=INK, width=3)
            if j < ncol:
                x += cw[j]
        y = m
        for i in range(len(cells) + 1):
            d.line([(m, y), (m + W, y)], fill=INK, width=3 if i not in (1,) else 5)
            if i < len(cells):
                y += rh[i]
    if delim in ("[", "|"):
        lw = 4
        d.line([(m - 2, m), (m - 2, m + H)], fill=INK, width=lw)
        d.line([(m + W + 2, m), (m + W + 2, m + H)], fill=INK, width=lw)
        if delim == "[":
            d.line([(m - 2, m), (m + 12, m)], fill=INK, width=lw)
            d.line([(m - 2, m + H), (m + 12, m + H)], fill=INK, width=lw)
            d.line([(m + W + 2, m), (m + W - 12, m)], fill=INK, width=lw)
            d.line([(m + W + 2, m + H), (m + W - 12, m + H)], fill=INK, width=lw)
    return out


def _render(spec):
    if isinstance(spec, Image.Image):
        return spec
    if isinstance(spec, str):
        return _math(spec)
    if isinstance(spec, list):
        return _hcompose([_render(s) for s in spec])
    kind = spec[0]
    if kind == "sp":
        return _blank(spec[1])
    if kind == "mat":
        return _grid(spec[1], delim=spec[2] if len(spec) > 2 else "[")
    if kind == "tab":
        return _grid(spec[1], border=True, padx=22, pady=10)
    if kind == "sys":
        lines = [_render(s) for s in spec[1]]
        g = _grid([[l] for l in lines], padx=8, pady=8)
        # alinhar linhas a esquerda
        w = max(l.width for l in lines) + 16
        hh = sum(l.height + 22 for l in lines) + 8
        body = Image.new("RGB", (w, hh), "white")
        y = 4
        for l in lines:
            body.paste(l, (8, y + 11))
            y += l.height + 22
        br = _brace(hh)
        out = Image.new("RGB", (br.width + body.width + 6, hh), "white")
        out.paste(br, (0, 0))
        out.paste(body, (br.width + 6, 0))
        return out
    raise ValueError("spec invalida: %r" % (spec,))


def render(spec):
    """Devolve (caminho_png, largura_pt, altura_pt). Escala natural: 300 dpi."""
    key = hashlib.md5(repr(spec).encode("utf-8")).hexdigest()
    if key in _cache:
        return _cache[key]
    im = _render(spec)
    path = os.path.join(_OUT, key + ".png")
    im.save(path, dpi=(DPI, DPI))
    res = (path, im.width * 72.0 / DPI, im.height * 72.0 / DPI)
    _cache[key] = res
    return res
