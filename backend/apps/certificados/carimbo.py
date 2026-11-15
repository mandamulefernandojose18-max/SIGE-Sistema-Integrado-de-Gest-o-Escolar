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
DIAMETRO_CM = 3.2


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
    """True = com carimbo, False = sem carimbo. Sem resposta explícita levanta 409 (nunca assume)."""
    valor = (request.query_params.get('carimbo') or '').strip().lower()
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
    return d + 1.7 * CM, d + 1.45 * CM


def _texto_em_arco(c, texto, cx, cy, raio, centro_graus, fonte, tamanho, em_cima=True):
    from reportlab.pdfbase.pdfmetrics import stringWidth
    texto = (texto or '').strip()
    if not texto:
        return
    limite = math.radians(200)
    while stringWidth(texto, fonte, tamanho) / raio > limite and tamanho > 5:
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
    c.setFillAlpha(0.9)
    c.setStrokeAlpha(0.9)
    c.setLineWidth(1.5)
    c.circle(cx, cy, r - 1, stroke=1, fill=0)
    c.setLineWidth(0.6)
    c.circle(cx, cy, r - 0.16 * CM, stroke=1, fill=0)   # limite exterior da faixa de texto
    c.circle(cx, cy, r - 0.75 * CM, stroke=1, fill=0)   # limite interior da faixa de texto
    nome = (getattr(escola, 'nome', '') or '').upper()
    local = ' · '.join(p for p in [(getattr(escola, 'distrito', '') or '').upper(),
                                   (getattr(escola, 'provincia', '') or '').upper()] if p)
    # Em cima as letras crescem para fora (linha de base no interior da faixa); em baixo crescem para dentro
    _texto_em_arco(c, nome, cx, cy, r - 0.75 * CM + 3.5, 90, 'Times-Bold', 6.5, em_cima=True)
    _texto_em_arco(c, local, cx, cy, r - 0.16 * CM - 3.5, 270, 'Times-Bold', 6, em_cima=False)
    # Centro: emblema nacional e código da escola
    try:
        from apps.documentos.services.pdf_service import EMBLEMA_PATH
        from reportlab.lib.utils import ImageReader
        if os.path.exists(EMBLEMA_PATH):
            lado = 0.72 * CM
            c.drawImage(ImageReader(EMBLEMA_PATH), cx - lado / 2, cy - lado / 2 + 3,
                        width=lado, height=lado, mask='auto', preserveAspectRatio=True)
    except Exception:
        pass
    c.setFont('Times-Bold', 5.5)
    c.drawCentredString(cx, cy - 15, getattr(escola, 'codigo_escola', '') or '')
    c.restoreState()


def desenhar_carimbo(c, x, y, escola, nivel, doc=None, previa=False):
    """Desenha o bloco do carimbo no canvas ReportLab com canto inferior esquerdo em (x, y)."""
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    d = DIAMETRO_CM * CM
    if nivel == 'IMAGEM' or doc is None:
        _desenhar_circulo(c, x, y, escola)
        return
    # B/C: QR à esquerda, carimbo à direita, linhas de texto por baixo
    topo_y = y + 1.45 * CM
    qr_lado = 1.5 * CM
    from apps.documentos.services.pdf_service import gerar_qr_code_image
    alvo = _url_base() if previa else f"{_url_base()}/verificar-certificado.html?codigo={doc.codigo}"
    c.drawImage(ImageReader(gerar_qr_code_image(alvo)), x, topo_y + (d - qr_lado) / 2,
                width=qr_lado, height=qr_lado)
    _desenhar_circulo(c, x + 1.7 * CM, topo_y, escola)
    c.saveState()
    c.setFillColor(colors.HexColor('#111111'))
    larg = d + 1.7 * CM
    meio = x + larg / 2
    c.setFont('Times-Bold', 6.5)
    c.drawCentredString(meio, y + 1.15 * CM, f"Selo {doc.codigo}")
    c.setFont('Times-Roman', 6)
    data = doc.emitido_em.strftime('%d/%m/%Y') if getattr(doc, 'emitido_em', None) else ''
    c.drawCentredString(meio, y + 0.85 * CM, f"Emitido em {data}")
    c.drawCentredString(meio, y + 0.55 * CM, f"Verifique: {_url_base().split('://')[-1]}")
    if nivel == 'ASSINATURA':
        fp = (getattr(doc, 'impressao_digital_chave', '') or '')[:8].upper()
        c.drawCentredString(meio, y + 0.25 * CM,
                            'Assinado digitalmente' + (f' · chave {fp}' if fp else ''))
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
def aplicar_carimbo_pdf(pdf_bytes, escola, nivel, doc=None, posicao='direita'):
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    leitor = PdfReader(io.BytesIO(pdf_bytes))
    escritor = PdfWriter()
    ultimo = len(leitor.pages) - 1
    for i, pagina in enumerate(leitor.pages):
        if i == ultimo:
            w, h = float(pagina.mediabox.width), float(pagina.mediabox.height)
            bw, _ = dimensoes_carimbo_pt(nivel if doc is not None else 'IMAGEM')
            x = (w - bw) / 2 if posicao == 'centro' else w - 1.5 * CM - bw - 0.6 * CM
            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=(w, h))
            desenhar_carimbo(c, x, 1.3 * CM, escola, nivel, doc)
            c.save()
            pagina.merge_page(PdfReader(io.BytesIO(buf.getvalue())).pages[0])
        escritor.add_page(pagina)
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


def carimbar_documento(com_carimbo, conteudo, formato, escola, tipo, referencia, descricao,
                       emitido_por, posicao='direita'):
    """Ponto único usado pelas views: se o utilizador escolheu «sem carimbo» devolve o documento intacto."""
    if not com_carimbo:
        return conteudo
    nivel = getattr(escola, 'carimbo_nivel', 'SELO') or 'SELO'
    doc = None
    if nivel in ('SELO', 'ASSINATURA'):
        doc = registrar_documento(escola, tipo, referencia, descricao, emitido_por, nivel)
        nivel = doc.nivel
    if formato == 'pdf':
        return aplicar_carimbo_pdf(conteudo, escola, nivel, doc, posicao)
    return aplicar_carimbo_docx(conteudo, escola, nivel, doc, posicao)
