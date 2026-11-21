# -*- coding: utf-8 -*-
"""Pinta, na folha de respostas ORIGINAL (pagina 1 do PDF da prova), o quadradinho da
alinea escolhida de cada pergunta.
Uso: python -I marcar_grelha.py <prova.pdf> <saida.pdf> "B A D A ..."   (uma letra por pergunta, em ordem)
Gera tambem <saida>.png a 200 dpi.
Modelo de folha SIGE: duas colunas (perguntas 1-20 a esquerda, 21-40 a direita)."""
import sys, pymupdf

SRC, OUT, CH = sys.argv[1], sys.argv[2], sys.argv[3].split()
CHAVE = dict(enumerate(CH, 1))
d = pymupdf.open(SRC)
pg = d[0]
words = pg.get_text("words")
rects = [dr["rect"] for dr in pg.get_drawings() if 20 < dr["rect"].width < 36 and 5 < dr["rect"].height < 14]
meio = pg.rect.width / 2
nums = {}
for w in words:
    t = w[4]
    if t.isdigit() and 1 <= int(t) <= len(CHAVE) and w[1] > 420 and (w[0] < 60 or meio - 20 < w[0] < meio + 40):
        nums[int(t)] = w
feitas = 0
for n in sorted(CHAVE):
    if n not in nums:
        print("falta numero", n); continue
    nw = nums[n]; cy = (nw[1] + nw[3]) / 2
    esq = nw[0] < 100
    letras = sorted([w for w in words if w[4] in ("A", "B", "C", "D") and abs((w[1] + w[3]) / 2 - cy) < 6
                     and ((esq and w[0] < meio) or (not esq and w[0] > meio))], key=lambda w: w[0])
    if len(letras) != 4:
        print("letras", n, len(letras)); continue
    L = letras["ABCD".index(CHAVE[n])]
    cx = (L[0] + L[2]) / 2; cyl = (L[1] + L[3]) / 2
    cand = sorted([r for r in rects if r.x0 - 1 <= cx <= r.x1 + 1 and r.y0 - 2 <= cyl <= r.y1 + 2], key=lambda r: r.width * r.height)
    r = cand[0] if cand else pymupdf.Rect(cx - 14, cyl - 5, cx + 14, cyl + 5)
    sh = pg.new_shape(); sh.draw_rect(r)
    sh.finish(color=(0.04, 0.10, 0.45), fill=(0.04, 0.10, 0.45), width=0.6); sh.commit()
    feitas += 1
print("marcadas", feitas, "de", len(CHAVE))
pg.get_pixmap(dpi=200).save(OUT.replace(".pdf", ".png"))
d.save(OUT)
