"""Carimbo digital/electrónico da escola (SIGE).

Três níveis, escolhidos pela escola em Configurações:
  A  IMAGEM      carimbo visual (imagem carregada pela escola ou carimbo gerado pelo sistema)
  B  SELO        carimbo + código único + QR que abre a verificação pública
  C  ASSINATURA  selo + assinatura digital Ed25519 com a chave própria da escola

Regra de negócio: o carimbo NUNCA é aplicado por omissão. Cada emissão tem de trazer `?carimbo=sim`
ou `?carimbo=nao` (o frontend pergunta ao utilizador antes de cada descarregamento); sem resposta a
API devolve 409 `requer_decisao_carimbo`.

Limite honesto do nível C: é uma assinatura do SIGE sobre o registo do documento (verificável na página
pública), não um certificado digital qualificado de uma entidade certificadora acreditada.
"""
import base64
import hashlib
import io
import math
import os
import uuid

from django.conf import settings
from rest_framework.exceptions import APIException

from .models import ChaveAssinaturaEscola, DocumentoCarimbado

NIVEIS = ('IMAGEM', 'SELO', 'ASSINATURA')
_RANK = {n: i for i, n in enumerate(NIVEIS)}
AZUL_CARIMBO = '#1e3a8a'
CM = 28.3464567  # pontos por centímetro
DIAMETRO_CM = 4.4
COLUNA_ALTURA_CM = 2.4
COLUNA_CM = 2.2   # coluna do QR e do código, à esquerda do círculo (níveis B/C)


# ----------------------------------------------------------------------------------------------
# Decisão obrigatória em cada emissão
# ----------------------------------------------------------------------------------------------
class DecisaoCarimboPendente(APIException):
    status_code = 409
    default_code = 'requer_decisao_carimbo'

    def __init__(self):
        super().__init__()
        # Corpo bruto: o DRF converteria os valores (ex.: True) em texto.
        self.detail = {
            'success': False,
            'requer_decisao_carimbo': True,
            'message': 'Indique se o documento sai com carimbo ou sem carimbo (parâmetro carimbo=sim|nao).',
        }


def decidir_carimbo(request):
    """True = com carimbo, False = sem carimbo. Sem resposta explícita levanta 409 (nunca assume).

    Aluno e encarregado só obtêm cópias de consulta: nunca saem com carimbo (nem pedindo `carimbo=sim`)
    e não são perguntados. O carimbo é um acto da escola."""
    if str(getattr(request.user, 'role', '') or '').upper() in ('ALUNO', 'ENCARREGADO'):
        return False
    parametros = getattr(request, 'query_params', None)
    if parametros is None:
        parametros = request.GET
    valor = (parametros.get('carimbo') or '').strip().lower()
    if valor in ('sim', 's', 'true', '1'):
        return True
    if valor in ('nao', 'não', 'n', 'false', '0'):
        return False
    raise DecisaoCarimboPendente()


# ----------------------------------------------------------------------------------------------
# Nome abreviado (a verificação pública não expõe o nome completo)
# ----------------------------------------------------------------------------------------------
def nome_abreviado(aluno):
    partes = f"{aluno.nome} {getattr(aluno, 'apelido', '') or ''}".split()
    if not partes:
        return ''
    return partes[0] + ''.join(f' {p[0].upper()}.' for p in partes[1:])


# ----------------------------------------------------------------------------------------------
# Chaves e assinatura (nível C)
# ----------------------------------------------------------------------------------------------
def _fernet():
    from cryptography.fernet import Fernet
    segredo = os.environ.get('SIGE_CARIMBO_KEY') or settings.SECRET_KEY
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(segredo.encode('utf-8')).digest()))


def obter_ou_criar_chave(escola):
    chave = ChaveAssinaturaEscola.objects.filter(escola=escola).first()
    if chave:
        return chave
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    privada = Ed25519PrivateKey.generate()
    priv_pem = privada.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    pub_pem = privada.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    return ChaveAssinaturaEscola.objects.create(
        escola=escola,
        chave_publica_pem=pub_pem.decode('ascii'),
        chave_privada_cifrada=_fernet().encrypt(priv_pem).decode('ascii'),
        impressao_digital=hashlib.sha256(pub_pem).hexdigest(),
    )


def _mensagem_assinada(doc):
    return '|'.join([
        str(doc.escola_id), doc.tipo, doc.referencia, doc.codigo, doc.nivel,
        doc.emitido_em.isoformat(),
    ]).encode('utf-8')


def _assinar(doc):
    from cryptography.hazmat.primitives import serialization
    chave = obter_ou_criar_chave(doc.escola)
    priv_pem = _fernet().decrypt(chave.chave_privada_cifrada.encode('ascii'))
    privada = serialization.load_pem_private_key(priv_pem, password=None)
    doc.assinatura = base64.b64encode(privada.sign(_mensagem_assinada(doc))).decode('ascii')
    doc.impressao_digital_chave = chave.impressao_digital
    doc.save(update_fields=['assinatura', 'impressao_digital_chave'])


def verificar_assinatura(doc):
    """None = documento sem assinatura (níveis A/B); True/False = assinatura válida/inválida."""
    if not doc.assinatura:
        return None
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import serialization
        chave = ChaveAssinaturaEscola.objects.get(escola_id=doc.escola_id)
        publica = serialization.load_pem_public_key(chave.chave_publica_pem.encode('ascii'))
        try:
            publica.verify(base64.b64decode(doc.assinatura), _mensagem_assinada(doc))
            return True
        except InvalidSignature:
            return False
    except Exception:
        return False


def registrar_documento(escola, tipo, referencia, descricao, emitido_por, nivel):
    """Regista (ou recupera) o documento carimbado. O mesmo documento mantém sempre o mesmo código."""
    doc = DocumentoCarimbado.objects.filter(escola=escola, tipo=tipo, referencia=referencia).first()
    if doc is None:
        doc = DocumentoCarimbado.objects.create(
            escola=escola, tipo=tipo, referencia=referencia, descricao=(descricao or '')[:255],
            codigo=f"SEL-{uuid.uuid4().hex[:12].upper()}", nivel=nivel, emitido_por=(emitido_por or '')[:255])
    elif _RANK.get(nivel, 0) > _RANK.get(doc.nivel, 0):
        doc.nivel = nivel
        doc.save(update_fields=['nivel'])
    if doc.nivel == 'ASSINATURA' and not doc.assinatura:
        _assinar(doc)
    return doc


# ----------------------------------------------------------------------------------------------
# Desenho vectorial do carimbo
# ----------------------------------------------------------------------------------------------
def _url_base():
    return os.environ.get('SIGE_PUBLIC_URL', 'https://sigesaas.duckdns.org').rstrip('/')


def dimensoes_carimbo_pt(nivel):
    """(largura, altura) do bloco em pontos."""
    d = DIAMETRO_CM * CM
    if nivel == 'IMAGEM':
        return d, d
    return d + COLUNA_CM * CM, d


def _texto_em_arco(c, texto, cx, cy, raio, centro_graus, fonte, tamanho, em_cima=True, limite_graus=200):
    from reportlab.pdfbase.pdfmetrics import stringWidth
    texto = (texto or '').strip()
    if not texto:
        return
    limite = math.radians(limite_graus)
    while stringWidth(texto, fonte, tamanho) / raio > limite and tamanho > 4.0:
        tamanho -= 0.3
    while len(texto) > 3 and stringWidth(texto, fonte, tamanho) / raio > limite:
        texto = texto[:-2].rstrip() + '…'
    total = stringWidth(texto, fonte, tamanho) / raio
    c.setFont(fonte, tamanho)
    if em_cima:
        ang = math.radians(centro_graus) + total / 2
        for ch in texto:
            w = stringWidth(ch, fonte, tamanho)
            a = ang - (w / 2) / raio
            c.saveState()
            c.translate(cx + raio * math.cos(a), cy + raio * math.sin(a))
            c.rotate(math.degrees(a) - 90)
            c.drawString(-w / 2, 0, ch)
            c.restoreState()
            ang -= w / raio
    else:
        ang = math.radians(centro_graus) - total / 2
        for ch in texto:
            w = stringWidth(ch, fonte, tamanho)
            a = ang + (w / 2) / raio
            c.saveState()
            c.translate(cx + raio * math.cos(a), cy + raio * math.sin(a))
            c.rotate(math.degrees(a) + 90)
            c.drawString(-w / 2, 0, ch)
            c.restoreState()
            ang += w / raio


_EMBLEMA_MONO = {}


def _emblema_cor_do_carimbo():
    """Emblema nacional em silhueta com a cor do carimbo (azul): tudo o que não é fundo passa a tinta azul,
    com a densidade do original, para o emblema parecer parte do mesmo carimbo."""
    if 'png' in _EMBLEMA_MONO:
        return _EMBLEMA_MONO['png']
    png = None
    try:
        from apps.documentos.services.pdf_service import EMBLEMA_PATH
        from PIL import Image, ImageChops
        if os.path.exists(EMBLEMA_PATH):
            im = Image.open(EMBLEMA_PATH).convert('RGBA')
            from PIL import ImageOps
            a = im.split()[3]
            # densidade = escuridão do original (contornos fortes, zonas claras mais leves), com contraste
            escuridao = ImageOps.invert(im.convert('L'))
            densidade = ImageOps.autocontrast(escuridao, cutoff=3).point(lambda v: min(255, int((v / 255.0) ** 0.7 * 255 * 1.15)))
            mascara = ImageChops.multiply(densidade, a)
            cor = tuple(int(AZUL_CARIMBO[i:i + 2], 16) for i in (1, 3, 5))
            mono = Image.new('RGBA', im.size, cor + (255,))
            mono.putalpha(mascara)
            saida = io.BytesIO()
            mono.save(saida, format='PNG')
            png = saida.getvalue()
    except Exception:
        png = None
    _EMBLEMA_MONO['png'] = png
    return png


def _desenhar_circulo(c, x, y, escola):
    """Carimbo circular gerado pelo sistema (ou imagem carregada pela escola) com canto inferior esquerdo em (x, y)."""
    from reportlab.lib import colors
    d = DIAMETRO_CM * CM
    origem = getattr(escola, 'carimbo_origem', 'GERADO')
    if origem == 'CARREGADO' and getattr(escola, 'carimbo_imagem_base64', None):
        from apps.documentos.services.pdf_service import obter_imagereader_para_reportlab
        img = obter_imagereader_para_reportlab(escola.carimbo_imagem_base64)
        if img:
            c.drawImage(img, x, y, width=d, height=d, mask='auto', preserveAspectRatio=True, anchor='c')
            return
    cx, cy, r = x + d / 2, y + d / 2, d / 2
    c.saveState()
    cor = colors.HexColor(AZUL_CARIMBO)
    c.setStrokeColor(cor)
    c.setFillColor(cor)
    c.setFillAlpha(0.78)
    c.setStrokeAlpha(0.78)
    c.setLineWidth(1.5)
    c.circle(cx, cy, r - 1, stroke=1, fill=0)
    c.setLineWidth(0.6)
    r2, r3, r4 = r - 0.16 * CM, r - 0.72 * CM, r - 1.28 * CM
    c.circle(cx, cy, r2, stroke=1, fill=0)   # só os dois círculos exteriores; sem linhas interiores
    provincia = (getattr(escola, 'provincia', '') or '').upper()
    distrito = (getattr(escola, 'distrito', '') or '').upper()
    nome = (getattr(escola, 'nome', '') or '').upper()
    # Faixa exterior: República e Província. Faixa interior: Governo do Distrito e nome da escola.
    # Em cima as letras crescem para fora (linha de base no interior da faixa); em baixo crescem para dentro.
    _texto_em_arco(c, 'REPÚBLICA DE MOÇAMBIQUE', cx, cy, r3 + 3.4, 90, 'Times-Bold', 6.2, em_cima=True)
    _texto_em_arco(c, nome, cx, cy, r2 - 3.4, 270, 'Times-Bold', 6.2, em_cima=False)
    _texto_em_arco(c, f'PROVÍNCIA DE {provincia}' if provincia else '', cx, cy, r4 + 5.6, 90,
                   'Times-Bold', 5.4, em_cima=True, limite_graus=168)
    _texto_em_arco(c, f'GOVERNO DO DISTRITO DE {distrito}' if distrito else '', cx, cy, r3 - 5.4, 270,
                   'Times-Bold', 5.4, em_cima=False, limite_graus=168)
    # Centro: emblema nacional
    try:
        from reportlab.lib.utils import ImageReader
        png = _emblema_cor_do_carimbo()
        if png:
            lado = 1.0 * CM
            c.drawImage(ImageReader(io.BytesIO(png)), cx - lado / 2, cy - lado / 2,
                        width=lado, height=lado, mask='auto', preserveAspectRatio=True)
    except Exception:
        pass
    c.restoreState()


def desenhar_carimbo(c, x, y, escola, nivel, doc=None, previa=False, escala=1.0):
    """Desenha o bloco do carimbo (tamanho nominal x `escala`) com canto inferior esquerdo em (x, y)."""
    c.saveState()
    c.translate(x, y)
    c.scale(escala, escala)
    _desenhar_bloco(c, 0, 0, escola, nivel, doc, previa)
    c.restoreState()


def _desenhar_bloco(c, x, y, escola, nivel, doc=None, previa=False):
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    d = DIAMETRO_CM * CM
    if nivel == 'IMAGEM' or doc is None:
        _desenhar_circulo(c, x, y, escola)
        return
    # B/C: coluna à esquerda (QR e, por baixo, código e endereço) e o carimbo à direita
    _desenhar_coluna(c, x, y, nivel, doc, previa)
    _desenhar_circulo(c, x + COLUNA_CM * CM, y, escola)


def _desenhar_coluna(c, x, y, nivel, doc, previa=False):
    """QR de verificação, código do selo e (nível C) «Assinado digitalmente»; (x, y) = canto inferior esquerdo."""
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    from apps.documentos.services.pdf_service import gerar_qr_code_image
    qr_lado = 1.5 * CM
    alvo = _url_base() if previa else f"{_url_base()}/verificar-certificado.html?codigo={doc.codigo}"
    meio = x + (COLUNA_CM * CM - 0.1 * CM) / 2
    c.drawImage(ImageReader(gerar_qr_code_image(alvo)), meio - qr_lado / 2, y + 0.85 * CM,
                width=qr_lado, height=qr_lado)
    c.saveState()
    c.setFillColor(colors.HexColor('#111111'))
    c.setFont('Times-Bold', 5.5)
    c.drawCentredString(meio, y + 0.62 * CM, doc.codigo)
    c.setFont('Times-Roman', 5)
    c.drawCentredString(meio, y + 0.38 * CM, _url_base().split('://')[-1])
    if nivel == 'ASSINATURA':
        c.drawCentredString(meio, y + 0.14 * CM, 'Assinado digitalmente')
    c.restoreState()


def _com_escala(c, x, y, escala, desenhar):
    c.saveState()
    c.translate(x, y)
    c.scale(escala, escala)
    desenhar()
    c.restoreState()


class _DocPrevia:
    """Cenário de pré-visualização: não existe no registo e nunca é gravado."""
    def __init__(self, nivel, escola):
        import datetime
        self.codigo = 'PRÉ-VISUALIZAÇÃO'
        self.nivel = nivel
        self.emitido_em = datetime.datetime.now()
        chave = ChaveAssinaturaEscola.objects.filter(escola=escola).first()
        self.impressao_digital_chave = chave.impressao_digital if chave else ''


def renderizar_carimbo_png(escola, nivel, doc=None, previa=False, escala=4):
    """Rasteriza o carimbo (PDF vectorial -> PNG) para Word e para a pré-visualização."""
    from reportlab.pdfgen import canvas
    import pypdfium2 as pdfium
    larg, alt = dimensoes_carimbo_pt(nivel if doc is not None else 'IMAGEM')
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(larg, alt))
    desenhar_carimbo(c, 0, 0, escola, nivel, doc, previa=previa)
    c.save()
    pdf = pdfium.PdfDocument(buf.getvalue())
    imagem = pdf[0].render(scale=escala).to_pil()
    saida = io.BytesIO()
    imagem.save(saida, format='PNG')
    return saida.getvalue(), larg / CM


def gerar_previa_base64(escola, nivel):
    doc = None if nivel == 'IMAGEM' else _DocPrevia(nivel, escola)
    png, _ = renderizar_carimbo_png(escola, nivel, doc, previa=True)
    return 'data:image/png;base64,' + base64.b64encode(png).decode('ascii')


# ----------------------------------------------------------------------------------------------
# Aplicação nos documentos já gerados
# ----------------------------------------------------------------------------------------------
ESCALAS_CARIMBO = (0.85, 0.7, 0.6)   # tamanho em relação ao nominal; reduz-se se não houver espaço livre
MARGEM_CARIMBO = 1.2 * CM            # o carimbo fica dentro da moldura da página
PALAVRAS_ASSINATURA = ('Director', 'Directora', 'Carimbo', 'Chefe')


def _posicao_livre(doc_fitz, indice, bw, bh, w, h, ancora=None, bloqueio=None, escalas=None):
    """Procura na página o sítio livre (sem texto nem imagens pequenas por baixo) mais próximo da assinatura do
    director. Devolve (x, y, escala) em coordenadas PDF (origem em baixo) ou None se não conseguir analisar.
    Usa uma grelha de ocupação + imagem integral (numpy) para avaliar todas as posições de uma só vez."""
    try:
        import numpy as np
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz
        pagina = doc_fitz[indice]
        g = 2.0  # pontos por célula da grelha
        nx, ny = int(math.ceil(w / g)) + 1, int(math.ceil(h / g)) + 1
        ocupado = np.zeros((ny, nx), dtype=np.int32)

        def marcar(x0, y0, x1, y1):
            ocupado[max(int(y0 // g), 0):min(int(math.ceil(y1 / g)), ny), max(int(x0 // g), 0):min(int(math.ceil(x1 / g)), nx)] = 1

        palavras = pagina.get_text('words')
        for p in palavras:
            if set(p[4]) <= set('_.-'):  # linhas de assinatura/preenchimento: o carimbo pode sobrepô-las
                continue
            marcar(p[0] - 2, p[1] - 2, p[2] + 2, p[3] + 2)
        area_pagina = pagina.rect.get_area()
        for info in pagina.get_image_info():
            r = fitz.Rect(info['bbox'])
            if 0 < r.get_area() < 0.25 * area_pagina:  # as marcas de água grandes não contam
                marcar(r.x0, r.y0, r.x1, r.y1)
        for desenho in pagina.get_drawings():  # linhas e quadros (grelhas de tabelas); a moldura da página não conta
            r = desenho['rect']
            if r.get_area() > 0.25 * area_pagina or (r.width > 0.9 * w and r.height > 0.9 * h):
                continue
            marcar(r.x0 - 1, r.y0 - 1, r.x1 + 1, r.y1 + 1)
        if bloqueio:  # área já ocupada (ex.: o círculo do carimbo)
            marcar(*bloqueio)
        integral = np.zeros((ny + 1, nx + 1), dtype=np.int64)
        integral[1:, 1:] = ocupado.cumsum(axis=0).cumsum(axis=1)

        # Âncora: a palavra de assinatura mais abaixo na página; por omissão, o canto inferior direito
        ancora_dada = ancora
        ancora = (w - MARGEM_CARIMBO - bw / 2, h - MARGEM_CARIMBO - bh / 2)
        achadas = [p for p in palavras if p[4].strip('.,:/') in PALAVRAS_ASSINATURA]
        if ancora_dada:
            ancora = ancora_dada
        elif achadas:
            a = max(achadas, key=lambda p: p[3])
            ancora = ((a[0] + a[2]) / 2, a[1] - bh / 2)

        melhor = None
        for escala in (escalas or ESCALAS_CARIMBO):
            cw, ch = int(math.ceil(bw * escala / g)), int(math.ceil(bh * escala / g))
            x_min, x_max = int(MARGEM_CARIMBO // g), int((w - MARGEM_CARIMBO) // g) - cw
            y_min, y_max = int(h * 0.4 // g), int((h - MARGEM_CARIMBO) // g) - ch
            if x_max < x_min or y_max < y_min:
                continue
            xs = np.arange(x_min, x_max + 1)
            ys = np.arange(y_min, y_max + 1)
            soma = (integral[np.ix_(ys + ch, xs + cw)] - integral[np.ix_(ys, xs + cw)]
                    - integral[np.ix_(ys + ch, xs)] + integral[np.ix_(ys, xs)])
            cx = (xs + cw / 2.0) * g
            cy = (ys + ch / 2.0)[:, None] * g
            dist = np.hypot(cx[None, :] - ancora[0], cy - ancora[1])
            pontuacao = soma * 1000.0 + dist
            iy, ix = np.unravel_index(int(np.argmin(pontuacao)), pontuacao.shape)
            candidato = (int(soma[iy, ix]), float(xs[ix] * g), float(ys[iy] * g), escala)
            if melhor is None or candidato[0] < melhor[0]:
                melhor = candidato
            if candidato[0] == 0:
                melhor = candidato
                break
        if melhor is None:
            return None
        _, x, y_topo, escala = melhor
        return x, h - y_topo - bh * escala, escala
    except Exception:
        return None


def _posicao_assinatura(doc_fitz, indice, bw, bh, w, h, escala):
    """Carimbo sobre a assinatura do director: o círculo fica centrado na linha de assinatura e apoiado
    acima do que for mais alto entre a linha e o rótulo «O Director da Escola» (nunca tapa o rótulo).
    Devolve (x, y, escala) em coordenadas PDF ou None se não encontrar a assinatura."""
    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz
        pagina = doc_fitz[indice]
        palavras = pagina.get_text('words')
        rotulos = []
        for e in palavras:  # «Director/Directora» … «da» … «Escola» na mesma linha, junto um do outro
            if e[4] != 'Escola':
                continue
            antes = [q for q in palavras if q[4] in ('Director', 'Directora') and abs(q[1] - e[1]) < 2
                     and 0 < e[0] - q[2] < 80]
            if antes:
                q = max(antes, key=lambda z: z[2])
                rotulos.append(fitz.Rect(q[0], min(q[1], e[1]), e[2], max(q[3], e[3])))
        if not rotulos:
            return None
        rotulo = max(rotulos, key=lambda r: r.y1)
        x0, x1, topo = rotulo.x0, rotulo.x1, rotulo.y0
        linhas = [p for p in palavras
                  if len(p[4]) > 5 and set(p[4]) <= set('_')
                  and rotulo.x0 - 20 <= (p[0] + p[2]) / 2 <= rotulo.x1 + 20 and abs(p[3] - rotulo.y0) < 3 * CM]
        if linhas:  # a linha de assinatura do director está centrada sobre o rótulo (não outras linhas da página)
            linha = min(linhas, key=lambda p: abs(p[3] - rotulo.y0))
            x0, x1, topo = linha[0], linha[2], min(topo, linha[1])
        # Bloco da assinatura: rótulo, linha e nome do director (o carimbo fica exactamente por cima de tudo isto)
        base = rotulo.y1
        for q in palavras:
            centro_x = (q[0] + q[2]) / 2
            if x0 - 10 <= centro_x <= x1 + 10 and topo - 1 <= q[1] <= topo + 3.2 * CM and not (set(q[4]) <= set('_.-')):
                base = max(base, q[3])
        cx, cy = (x0 + x1) / 2, (rotulo.y0 + base) / 2   # exactamente sobre o rótulo e o nome
        d = DIAMETRO_CM * CM * escala
        x = cx - d / 2 - COLUNA_CM * CM * escala
        x = max(MARGEM_CARIMBO, min(x, w - MARGEM_CARIMBO - bw * escala))
        y = h - (cy + d / 2)                      # base do círculo (coordenadas PDF)
        y = max(MARGEM_CARIMBO / 2, min(y, h - MARGEM_CARIMBO - bh * escala))
        return x, y, escala
    except Exception:
        return None


def _abrir_fitz(pdf_bytes):
    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz
        return fitz.open(stream=pdf_bytes, filetype='pdf')
    except Exception:
        return None


def _paginas_com_assinatura(doc_fitz):
    """Índices das páginas com a assinatura «O Director da Escola» (um lote tem uma por documento).
    Sem nenhuma, usa a última página que tenha outra palavra de assinatura; se também não houver, lista vazia."""
    if doc_fitz is None:
        return []
    diretor, outras = [], []
    for i, pagina in enumerate(doc_fitz):
        palavras = pagina.get_text('words')
        if any(e[4] == 'Escola' and any(q[4] in ('Director', 'Directora') and abs(q[1] - e[1]) < 2
                                        and 0 < e[0] - q[2] < 80 for q in palavras) for e in palavras):
            diretor.append(i)
        elif any(p[4].strip('.,:/') in PALAVRAS_ASSINATURA for p in palavras):
            outras.append(i)
    return diretor or outras[-1:]


def aplicar_carimbo_pdf(pdf_bytes, escola, nivel, doc=None, posicao='direita'):
    """Sobrepõe o carimbo exactamente sobre a assinatura do director de cada documento do PDF; se a assinatura
    não existir, no sítio livre mais próximo do fim da página (ou canto inferior direito / centro na declaração)."""
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    leitor = PdfReader(io.BytesIO(pdf_bytes))
    escritor = PdfWriter()
    doc_f = _abrir_fitz(pdf_bytes)
    alvos = set(_paginas_com_assinatura(doc_f)) or {len(leitor.pages) - 1}
    bw, bh = dimensoes_carimbo_pt(nivel if doc is not None else 'IMAGEM')
    tem_coluna = doc is not None and nivel != 'IMAGEM'
    for i, pagina in enumerate(leitor.pages):
        nova = escritor.add_page(pagina)
        if i not in alvos:
            continue
        w, h = float(nova.mediabox.width), float(nova.mediabox.height)
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(w, h))
        fixo = _posicao_assinatura(doc_f, i, bw, bh, w, h, 0.8) if doc_f is not None else None
        if fixo:
            # Círculo apoiado na assinatura do director; o QR procura a zona livre mais próxima do círculo
            x, y, escala = fixo
            d = DIAMETRO_CM * CM * escala
            # x já inclui a coluna do QR à esquerda do círculo; sem coluna (nível A) o círculo centra-se na mesma
            # sobre a assinatura (antes ficava deslocado para a esquerda)
            cx_circ = x + COLUNA_CM * CM * escala
            _com_escala(c, cx_circ, y, escala, lambda: _desenhar_circulo(c, 0, 0, escola))
            if tem_coluna:
                cw, ch = COLUNA_CM * CM, COLUNA_ALTURA_CM * CM
                coluna = _posicao_livre(
                    doc_f, i, cw, ch, w, h, ancora=(cx_circ - cw * escala / 2, h - y - d / 2),
                    bloqueio=(cx_circ, h - (y + d), cx_circ + d, h - y), escalas=(escala,))
                xc, yc, ec = coluna if coluna else (x, y, escala)
                _com_escala(c, xc, yc, ec, lambda: _desenhar_coluna(c, 0, 0, nivel, doc))
        else:
            livre = _posicao_livre(doc_f, i, bw, bh, w, h) if doc_f is not None else None
            if livre:
                x, y, escala = livre
            else:
                escala = 0.85
                x = (w - bw * escala) / 2 if posicao == 'centro' else w - MARGEM_CARIMBO - bw * escala
                y = 1.3 * CM
            desenhar_carimbo(c, x, y, escola, nivel, doc, escala=escala)
        c.save()
        nova.merge_page(PdfReader(io.BytesIO(buf.getvalue())).pages[0])
    saida = io.BytesIO()
    escritor.write(saida)
    return saida.getvalue()


def aplicar_carimbo_docx(docx_bytes, escola, nivel, doc=None, posicao='direita'):
    import docx
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm
    png, larg_cm = renderizar_carimbo_png(escola, nivel if doc is not None else 'IMAGEM', doc)
    documento = docx.Document(io.BytesIO(docx_bytes))
    par = documento.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER if posicao == 'centro' else WD_ALIGN_PARAGRAPH.RIGHT
    par.add_run().add_picture(io.BytesIO(png), width=Cm(larg_cm))
    saida = io.BytesIO()
    documento.save(saida)
    return saida.getvalue()


def aplicar_carimbo_xlsx(xlsx_bytes, escola, nivel, doc=None):
    """Excel: o carimbo (imagem) entra por baixo da tabela da primeira folha, com uma linha de texto com o selo.
    As linhas usadas ficam visíveis (as de baixo estão ocultas por regra) e o carimbo não altera o conteúdo."""
    import openpyxl
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.utils import get_column_letter
    png, larg_cm = renderizar_carimbo_png(escola, nivel if doc is not None else 'IMAGEM', doc)
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    ws = wb.worksheets[0]
    img = XLImage(io.BytesIO(png))
    escala_img = (larg_cm / 2.54 * 96 * 0.8) / img.width       # ~80 % do tamanho nominal, em pixéis
    img.width, img.height = int(img.width * escala_img), int(img.height * escala_img)
    primeira = (ws.max_row or 1) + 2
    linhas = int(math.ceil(img.height * 0.75 / 15.0)) + 1      # altura em pontos / 15
    for r in range(primeira, primeira + linhas + 1):
        ws.row_dimensions[r].height = 15
        ws.row_dimensions[r].hidden = False
    if doc is not None:
        ws.cell(row=primeira + linhas, column=1,
                value=f"Selo {doc.codigo} — verifique em {_url_base().split('://')[-1]}")
    coluna = max(1, (ws.max_column or 1) - 3)
    ws.add_image(img, f"{get_column_letter(coluna)}{primeira}")
    saida = io.BytesIO()
    wb.save(saida)
    return saida.getvalue()


def aplicar_carimbo_zip(zip_bytes, escola, nivel, doc=None, posicao='direita'):
    """ZIP (lote): carimba cada PDF, Excel e Word que o ZIP contém."""
    import zipfile
    entrada = zipfile.ZipFile(io.BytesIO(zip_bytes))
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, 'w', zipfile.ZIP_DEFLATED) as z:
        for info in entrada.infolist():
            dados = entrada.read(info.filename)
            ext = info.filename.lower().rsplit('.', 1)[-1]
            if ext == 'pdf':
                dados = aplicar_carimbo_pdf(dados, escola, nivel, doc, posicao)
            elif ext == 'xlsx':
                dados = aplicar_carimbo_xlsx(dados, escola, nivel, doc)
            elif ext == 'docx':
                dados = aplicar_carimbo_docx(dados, escola, nivel, doc, posicao)
            z.writestr(info.filename, dados)
    return saida.getvalue()


def carimbar_documento(com_carimbo, conteudo, formato, escola, tipo, referencia, descricao,
                       emitido_por, posicao='direita'):
    """Ponto único: se o utilizador escolheu «sem carimbo» devolve o documento intacto.
    `formato`: pdf, docx, xlsx ou zip."""
    if not com_carimbo:
        return conteudo
    nivel = getattr(escola, 'carimbo_nivel', 'SELO') or 'SELO'
    doc = None
    if nivel in ('SELO', 'ASSINATURA'):
        doc = registrar_documento(escola, tipo, referencia, descricao, emitido_por, nivel)
        nivel = doc.nivel
    if formato == 'pdf':
        return aplicar_carimbo_pdf(conteudo, escola, nivel, doc, posicao)
    if formato == 'xlsx':
        return aplicar_carimbo_xlsx(conteudo, escola, nivel, doc)
    if formato == 'zip':
        return aplicar_carimbo_zip(conteudo, escola, nivel, doc, posicao)
    return aplicar_carimbo_docx(conteudo, escola, nivel, doc, posicao)
