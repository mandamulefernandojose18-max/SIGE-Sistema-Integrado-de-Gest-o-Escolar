"""TOTP (RFC 6238) sem dependências externas + códigos de recuperação.

Compatível com Google Authenticator, Microsoft Authenticator, Authy, etc.
O segredo é base32; o código tem 6 dígitos e muda a cada 30 segundos.
"""
import base64
import hashlib
import hmac
import io
import secrets
import struct
import time
from urllib.parse import quote

PERIODO = 30
DIGITOS = 6
JANELA = 1  # aceita o passo anterior e o seguinte (tolerância a relógios desajustados)
EMISSOR = 'SIGE'
N_CODIGOS_RECUPERACAO = 8

# Perfis para os quais o 2FA está disponível.
PERFIS_2FA = ('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP')


def gerar_segredo() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode('ascii').rstrip('=')


def _hotp(segredo: str, contador: int) -> str:
    chave = base64.b32decode(segredo + '=' * (-len(segredo) % 8), casefold=True)
    mac = hmac.new(chave, struct.pack('>Q', contador), hashlib.sha1).digest()
    desloc = mac[-1] & 0x0F
    num = (struct.unpack('>I', mac[desloc:desloc + 4])[0] & 0x7FFFFFFF) % (10 ** DIGITOS)
    return str(num).zfill(DIGITOS)


def passo_actual(agora: float = None) -> int:
    return int((time.time() if agora is None else agora) // PERIODO)


def codigo_para(segredo: str, passo: int) -> str:
    return _hotp(segredo, passo)


def verificar_codigo(segredo: str, codigo: str, ultimo_passo=None, agora: float = None):
    """Devolve o passo validado (int) ou None. Rejeita passos já usados (anti-reutilização)."""
    codigo = ''.join(ch for ch in str(codigo or '') if ch.isdigit())
    if len(codigo) != DIGITOS or not segredo:
        return None
    base = passo_actual(agora)
    for passo in range(base - JANELA, base + JANELA + 1):
        if ultimo_passo is not None and passo <= ultimo_passo:
            continue
        if hmac.compare_digest(_hotp(segredo, passo), codigo):
            return passo
    return None


def uri_otpauth(segredo: str, conta: str) -> str:
    rotulo = quote(f'{EMISSOR}:{conta}')
    return f'otpauth://totp/{rotulo}?secret={segredo}&issuer={quote(EMISSOR)}&algorithm=SHA1&digits={DIGITOS}&period={PERIODO}'


def qr_data_uri(texto: str) -> str:
    """QR em PNG (data URI), gerado no servidor para o segredo nunca passar por serviços externos."""
    import qrcode
    img = qrcode.make(texto, box_size=6, border=2)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


# ---- Códigos de recuperação (guardados apenas como hash) ----------------------------------------
def _normalizar(codigo: str) -> str:
    return ''.join(ch for ch in str(codigo or '').lower() if ch.isalnum())


def _hash(codigo: str) -> str:
    return hashlib.sha256(_normalizar(codigo).encode('utf-8')).hexdigest()


def gerar_codigos_recuperacao():
    """Devolve (codigos_em_claro, hashes). Os códigos em claro só são mostrados uma vez."""
    alfabeto = 'abcdefghjkmnpqrstuvwxyz23456789'
    claros = []
    for _ in range(N_CODIGOS_RECUPERACAO):
        bruto = ''.join(secrets.choice(alfabeto) for _ in range(10))
        claros.append(f'{bruto[:5]}-{bruto[5:]}')
    return claros, [_hash(c) for c in claros]


def consumir_codigo_recuperacao(hashes, codigo):
    """Se o código existir, devolve a nova lista de hashes sem ele; caso contrário None."""
    h = _hash(codigo)
    if len(_normalizar(codigo)) != 10:
        return None
    for existente in hashes or []:
        if hmac.compare_digest(existente, h):
            return [x for x in hashes if x != existente]
    return None
