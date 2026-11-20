"""Validação e entrega segura de ficheiros enviados por utilizadores.

Regras:
- a extensão e o tipo MIME declarados pelo cliente NUNCA são confiáveis: o tipo é decidido pelos
  primeiros bytes do conteúdo (magic bytes) contra uma lista fechada;
- HTML, SVG, JS e outros formatos activos são rejeitados (evita XSS armazenado na mesma origem);
- a entrega é sempre `attachment`, com `nosniff` e CSP `sandbox`, e o tipo vem da lista fechada.
"""
import re
import unicodedata
import zipfile
import io

from django.http import HttpResponse

# extensão -> (tipo MIME seguro, verificador de conteúdo)
_OOXML = ('docx', 'xlsx', 'pptx')

TIPOS_PERMITIDOS = {
    'pdf': 'application/pdf',
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'gif': 'image/gif',
    'webp': 'image/webp',
    'doc': 'application/msword',
    'xls': 'application/vnd.ms-excel',
    'ppt': 'application/vnd.ms-powerpoint',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'csv': 'text/csv',
    'txt': 'text/plain',
}

_OLE = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
_ASSINATURAS = {
    'pdf': (b'%PDF-',),
    'png': (b'\x89PNG\r\n\x1a\n',),
    'jpg': (b'\xff\xd8\xff',),
    'jpeg': (b'\xff\xd8\xff',),
    'gif': (b'GIF87a', b'GIF89a'),
    'doc': (_OLE,), 'xls': (_OLE,), 'ppt': (_OLE,),
}
_MARCAS_ACTIVAS = re.compile(rb'<\s*(script|html|svg|iframe|object|embed|body|meta|link)\b|javascript:', re.I)


class FicheiroInvalido(ValueError):
    pass


def extensao_de(nome):
    nome = (nome or '').rsplit('\\', 1)[-1].rsplit('/', 1)[-1]
    return nome.rsplit('.', 1)[-1].lower() if '.' in nome else ''


def _ooxml_valido(dados, ext):
    pasta = {'docx': 'word/', 'xlsx': 'xl/', 'pptx': 'ppt/'}[ext]
    try:
        with zipfile.ZipFile(io.BytesIO(dados)) as z:
            nomes = z.namelist()
            return '[Content_Types].xml' in nomes and any(n.startswith(pasta) for n in nomes)
    except zipfile.BadZipFile:
        return False


def tipo_seguro_por_conteudo(dados, ext):
    """Devolve o MIME seguro se o conteúdo bate com a extensão permitida; senão levanta FicheiroInvalido."""
    ext = (ext or '').lower().lstrip('.')
    if ext not in TIPOS_PERMITIDOS:
        raise FicheiroInvalido('Formato de ficheiro não permitido.')
    if not dados:
        raise FicheiroInvalido('Ficheiro vazio.')
    if ext in _OOXML:
        if not _ooxml_valido(dados, ext):
            raise FicheiroInvalido('O conteúdo não corresponde ao formato indicado.')
    elif ext in ('csv', 'txt'):
        amostra = dados[:65536]
        if b'\x00' in amostra or _MARCAS_ACTIVAS.search(amostra):
            raise FicheiroInvalido('O conteúdo não corresponde a texto simples.')
    elif not any(dados.startswith(a) for a in _ASSINATURAS[ext]):
        raise FicheiroInvalido('O conteúdo não corresponde ao formato indicado.')
    return TIPOS_PERMITIDOS[ext]


def tipo_seguro_para_entrega(dados, nome_ou_ext, mime_declarado=''):
    """Para ficheiros já guardados: decide o MIME só por conteúdo/extensão. Desconhecido → octet-stream."""
    ext = extensao_de(nome_ou_ext) if '.' in (nome_ou_ext or '') else (nome_ou_ext or '').lower()
    candidatos = ([ext] if ext in TIPOS_PERMITIDOS else []) + ['pdf', 'png', 'jpg', 'gif', 'docx', 'xlsx', 'pptx']
    for candidato in candidatos:
        try:
            return tipo_seguro_por_conteudo(dados, candidato)
        except FicheiroInvalido:
            continue
    return 'application/octet-stream'


def nome_seguro(texto, padrao='ficheiro'):
    s = unicodedata.normalize('NFKD', str(texto or '')).encode('ascii', 'ignore').decode('ascii')
    s = re.sub(r'[^A-Za-z0-9 ._\-]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip(' .-_')
    return s[:120] or padrao


def resposta_ficheiro_segura(dados, nome, mime_declarado=''):
    """HttpResponse de descarga: sempre attachment, nosniff e CSP sandbox; MIME nunca vem do cliente."""
    mime = tipo_seguro_para_entrega(dados, nome, mime_declarado)
    resp = HttpResponse(dados, content_type=mime)
    resp['Content-Disposition'] = f'attachment; filename="{nome_seguro(nome)}"'
    resp['X-Content-Type-Options'] = 'nosniff'
    resp['Content-Security-Policy'] = "default-src 'none'; sandbox"
    resp['Cache-Control'] = 'private, no-store'
    return resp
