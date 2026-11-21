"""Leitura óptica da Folha de Resposta (OMR) com fotografias SIMULADAS: perspectiva, rotação, sombra, desfoque e ruído.

As folhas são desenhadas com a MESMA função que gera a folha oficial (marcas dos cantos + grelha + QR assinado);
o «aluno» pinta os quadradinhos com riscos de caneta azul (cobertura parcial) e a imagem é depois deformada.
Nenhum dado de aluno real é usado: só strings de teste.
"""
import io
import random

import numpy as np
import pytest

cv2 = pytest.importorskip('cv2')
fitz = pytest.importorskip('fitz')

from apps.documentos.services import folha_resposta_service as fr  # noqa: E402
from apps.notas import omr_servico as omr  # noqa: E402


def _desenhar_folha_pdf(n, n_alt, com_qr=True, versao='', escola_id='escola-teste', codigo='MAT-0001'):
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as rl_canvas
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(fr.PAG_L * mm, fr.PAG_A * mm))
    fr._desenhar_marcas_omr(c)
    # cabeçalho assimétrico (o da folha real também o é): ajuda a distinguir a folha de cabeça para baixo
    c.setFont('Times-Bold', 16)
    c.drawString(20 * mm, (fr.PAG_A - 20) * mm, 'FOLHA DE RESPOSTAS  ·  TESTE')
    c.rect(12 * mm, (fr.PAG_A - 80) * mm, 106 * mm, 40 * mm, stroke=1, fill=0)
    if com_qr:
        config = {'tipo': 'ACS1', 'disciplina': 'Matemática', 'n_perguntas': n}
        escola = {'id': str(escola_id)}
        aluno = {'codigo': codigo}
        token, sig = fr.gerar_token_verificacao(escola, aluno, config, 2026, versao)
        fr._desenhar_qr(c, f'{fr.DOMINIO_OFICIAL}/verificar-folha.html?d={token}&s={sig}', fr.PAG_L - fr.MARGEM - 21, 9, 20)
    _, cols, linhas, y_ini = omr.celulas_grelha(n, n_alt)
    fr._desenhar_grelha(c, {'n_alternativas': n_alt}, 0, n, cols, linhas, y_ini)
    c.showPage()
    c.save()
    return buf.getvalue()


DPI = 220   # ≈ uma fotografia de telemóvel de 8 MP a apanhar a folha inteira (as de 12 MP têm mais)


def _renderizar(pdf, dpi=DPI):
    doc = fitz.open(stream=pdf, filetype='pdf')
    pix = doc[0].get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), colorspace=fitz.csRGB, alpha=False)
    img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 3).copy()
    doc.close()
    return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)


def _pintar(img, n, n_alt, marcas, dpi=DPI, cobertura=0.7, semente=1):
    """marcas: {pergunta(1..n): 'A' | 'AB' (duas marcadas)}; riscos azuis sobre o quadradinho."""
    rnd = random.Random(semente)
    px = dpi / 25.4
    for q, i, cx, cy, lw, lh in omr.celulas_grelha(n, n_alt)[0]:
        letra = 'ABCDEF'[i]
        if letra not in marcas.get(q + 1, ''):
            continue
        x0, x1 = (cx - lw / 2) * px, (cx + lw / 2) * px
        y0, y1 = (cy - lh / 2) * px, (cy + lh / 2) * px
        passos = max(3, int(((x1 - x0) / 3) * cobertura))
        for k in range(passos):
            xa = x0 + (x1 - x0) * k / passos + rnd.uniform(-1, 1)
            cv2.line(img, (int(xa), int(y0 - 0.3 * px)), (int(xa + 4), int(y1 + 0.3 * px)), (170, 60, 20), 2)
    return img


def _fotografar(img, graus=0.0, perspectiva=0.04, escala=0.82, sombra=0.25, ruido=6, desfoque=0, semente=3):
    """Coloca a folha numa «mesa» com perspectiva, rotação, sombra, ruído e JPEG."""
    rnd = np.random.RandomState(semente)
    h, w = img.shape[:2]
    H, W = int(h * 1.25), int(w * 1.25)
    cx, cy = W / 2, H / 2
    quad = np.float32([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]]) * escala
    quad += np.float32([[rnd.uniform(-1, 1) * perspectiva * w, rnd.uniform(-1, 1) * perspectiva * h] for _ in range(4)])
    a = np.deg2rad(graus)
    rot = np.float32([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    quad = quad @ rot.T + np.float32([cx, cy])
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    M = cv2.getPerspectiveTransform(src, quad.astype(np.float32))
    mesa = np.full((H, W, 3), (70, 90, 110), np.uint8)
    foto = cv2.warpPerspective(img, M, (W, H), dst=mesa, borderMode=cv2.BORDER_TRANSPARENT)
    grad = np.linspace(1 - sombra, 1.0, W, dtype=np.float32)[None, :, None]
    foto = np.clip(foto.astype(np.float32) * grad, 0, 255)
    foto = np.clip(foto + rnd.normal(0, ruido, foto.shape), 0, 255).astype(np.uint8)
    if desfoque:
        foto = cv2.GaussianBlur(foto, (0, 0), desfoque)
    ok, buf = cv2.imencode('.jpg', foto, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    assert ok
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


GABARITO = 'ABCDABCDDCBAABCDABCD'


def _ler(foto, n=20, n_alt=4):
    return omr.ler_pagina(foto, n, n_alt)


def test_geometria_coincide_com_a_folha_impressa():
    """A bolha pintada pelo gabarito da folha oficial é lida exactamente como o gabarito (sem foto, sem ruído)."""
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as rl_canvas
    n, n_alt = 20, 4
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(fr.PAG_L * mm, fr.PAG_A * mm))
    fr._desenhar_marcas_omr(c)
    _, cols, linhas, y_ini = omr.celulas_grelha(n, n_alt)
    fr._desenhar_grelha(c, {'n_alternativas': n_alt}, 0, n, cols, linhas, y_ini, GABARITO)
    c.showPage()
    c.save()
    res = _ler(_renderizar(buf.getvalue()))
    assert res['respostas'] == GABARITO
    assert res['duvidas'] == []


@pytest.mark.parametrize('n,n_alt', [(10, 4), (20, 4), (40, 5), (60, 4), (100, 4), (25, 3), (30, 6)])
def test_varios_tamanhos_de_folha(n, n_alt):
    rnd = random.Random(n)
    gab = ''.join(rnd.choice('ABCDEF'[:n_alt]) for _ in range(n))
    img = _renderizar(_desenhar_folha_pdf(n, n_alt))
    img = _pintar(img, n, n_alt, {i + 1: ch for i, ch in enumerate(gab)})
    res = omr.ler_pagina(_fotografar(img, graus=2.0), n, n_alt)
    assert res['respostas'] == gab
    assert res['duvidas'] == []


def test_foto_com_perspectiva_sombra_e_rotacao():
    marcas = {i + 1: ch for i, ch in enumerate(GABARITO)}
    img = _pintar(_renderizar(_desenhar_folha_pdf(20, 4)), 20, 4, marcas)
    for graus, persp in ((-7.0, 0.05), (9.0, 0.06), (0.0, 0.03)):
        res = _ler(_fotografar(img, graus=graus, perspectiva=persp, sombra=0.35, ruido=9))
        assert res['respostas'] == GABARITO, (graus, persp)


def test_folha_de_cabeca_para_baixo_e_deitada():
    marcas = {i + 1: ch for i, ch in enumerate(GABARITO)}
    img = _pintar(_renderizar(_desenhar_folha_pdf(20, 4)), 20, 4, marcas)
    base = _fotografar(img, graus=1.5)
    assert _ler(cv2.rotate(base, cv2.ROTATE_180))['respostas'] == GABARITO
    assert _ler(cv2.rotate(base, cv2.ROTATE_90_CLOCKWISE))['respostas'] == GABARITO
    assert _ler(cv2.rotate(base, cv2.ROTATE_90_COUNTERCLOCKWISE))['respostas'] == GABARITO


def test_em_branco_dupla_e_marca_fraca():
    marcas = {1: 'A', 2: 'BC', 4: 'D'}          # 3 fica em branco, 2 tem duas marcas
    img = _pintar(_renderizar(_desenhar_folha_pdf(10, 4)), 10, 4, marcas)
    res = _ler(_fotografar(img), n=10)
    assert res['respostas'][0] == 'A'
    assert res['respostas'][1] == 'N'          # mais de uma alternativa: questão nula, sem dúvida
    assert res['respostas'][2] == '-'
    assert res['respostas'][3] == 'D'
    d = {x['n']: x for x in res['duvidas']}
    assert 2 not in d and 3 not in d and 1 not in d


def test_folha_personalizada_identifica_o_aluno_pelo_codigo_de_barras():
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as rl_canvas
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(fr.PAG_L * mm, fr.PAG_A * mm))
    fr._desenhar_marcas_omr(c)
    c.setFont('Times-Bold', 16)
    c.drawString(20 * mm, (fr.PAG_A - 20) * mm, 'FOLHA DE RESPOSTAS  ·  TESTE')
    fr._desenhar_codigo_barras(c, '0101S0001.12.01.2026.cg', 15, 80, 72, 4.6)     # como a folha personalizada
    _, cols, linhas, y_ini = omr.celulas_grelha(10, 4)
    fr._desenhar_grelha(c, {'n_alternativas': 4}, 0, 10, cols, linhas, y_ini)
    c.showPage()
    c.save()
    img = _pintar(_renderizar(buf.getvalue()), 10, 4, {1: 'A'})
    res = _ler(_fotografar(img), n=10)
    assert res['qr'] is None
    assert res['codigo_barras'] == '0101S0001.12.01.2026.cg'


def test_tinta_vermelha_nao_conta_como_resposta():
    import numpy as np
    img = _pintar(_renderizar(_desenhar_folha_pdf(10, 4)), 10, 4, {1: 'B'})
    cels, _, _, _ = omr.celulas_grelha(10, 4)
    # pinta a alternativa B da pergunta 1 a vermelho (tinta do professor): não é resposta válida
    q, i, cx, cy, lw, lh = [c for c in cels if c[0] == 0 and c[1] == 1][0]
    esc = img.shape[1] / 210.0
    x0, x1, y0, y1 = int((cx - lw / 2) * esc), int((cx + lw / 2) * esc), int((cy - lh / 2) * esc), int((cy + lh / 2) * esc)
    img[y0:y1, x0:x1] = (30, 30, 220)
    res = _ler(_fotografar(img), n=10)
    assert res['respostas'][0] == '-'
    assert any(x['motivo'] == 'COR' and x['n'] == 1 for x in res['duvidas'])


def test_folha_corrigida_desenha_a_vermelho():
    import numpy as np
    img = _renderizar(_desenhar_folha_pdf(10, 4))
    jpg = omr.anotar_folha(img, 10, 4, 'ABN-CDABCD', 'ABCDABCDAB', 3, 1.5, 'Prof. Teste')
    out = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
    b, g, r = out[..., 0].astype(int), out[..., 1].astype(int), out[..., 2].astype(int)
    vermelho = ((r - b) > 90) & ((r - g) > 90)
    assert vermelho.sum() > 2000                # vistos, círculos, acertos, nota, "Nula" e nome


def test_marca_leve_pede_confirmacao():
    img = _pintar(_renderizar(_desenhar_folha_pdf(10, 4)), 10, 4, {1: 'C'}, cobertura=0.2)
    res = _ler(_fotografar(img), n=10)
    assert res['respostas'][0] in ('*', 'C', '-')
    if res['respostas'][0] == '*':
        assert res['duvidas'][0]['motivo'] == 'FRACA'


def test_identifica_o_aluno_pelo_qr_assinado():
    img = _pintar(_renderizar(_desenhar_folha_pdf(20, 4, versao='B')), 20, 4, {1: 'A'})
    res = _ler(_fotografar(img, graus=2))
    assert res['qr'] and res['qr']['a'] == 'MAT-0001' and res['qr']['v'] == 'B' and res['qr']['n'] == 20


def test_qr_falsificado_e_ignorado():
    assert omr.identificar('https://sigesaas.duckdns.org/verificar-folha.html?d=eyJhIjoiWCJ9&s=0000000000000000') is None
    assert omr.identificar('texto qualquer') is None
    assert omr.identificar('') is None


def test_sem_marcas_nos_cantos_da_erro_claro():
    branco = np.full((1600, 1200, 3), 255, np.uint8)
    with pytest.raises(omr.ErroOMR) as e:
        omr.ler_pagina(branco, 20, 4)
    assert '4 marcas' in str(e.value)


def test_folha_de_outra_prova_e_recusada():
    img = _renderizar(_desenhar_folha_pdf(60, 4))
    with pytest.raises(omr.ErroOMR) as e:
        omr.ler_pagina(_fotografar(img), 10, 4)   # a prova tem 10 perguntas, a folha tem 60
    assert 'não coincide' in str(e.value)


def test_pdf_com_varias_paginas_e_formato_invalido():
    pdf = _desenhar_folha_pdf(20, 4)
    assert omr.contar_paginas(pdf) == 1
    img = omr.abrir_pagina(pdf, 0)
    assert img.shape[0] > 1000
    with pytest.raises(omr.ErroOMR):
        omr.abrir_pagina(pdf, 3)
    with pytest.raises(omr.ErroOMR):
        omr.abrir_pagina(b'GIF89a-not-supported', 0)
    with pytest.raises(omr.ErroOMR):
        omr.abrir_pagina(b'', 0)
