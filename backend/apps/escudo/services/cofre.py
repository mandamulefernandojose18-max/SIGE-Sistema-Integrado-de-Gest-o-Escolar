"""Cifra AES-256-GCM. A chave de cada ficheiro deriva da chave-mestra + código da prova + tipo."""
import hashlib
import secrets

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings

MAGIA = b'PV1'


def _mestra():
    """ESCUDO_MASTER_KEY (ambiente), ou derivada da SECRET_KEY do Django. Quem a perder não recupera as provas."""
    bruto = getattr(settings, 'ESCUDO_MASTER_KEY', '') or settings.SECRET_KEY
    return hashlib.sha256(('escudo:' + bruto).encode()).digest()


def _chave(pid, tipo):
    return HKDF(hashes.SHA256(), 32, None, f'cofre:{pid}:{tipo}'.encode()).derive(_mestra())


def cifrar(pid, tipo, dados):
    nonce = secrets.token_bytes(12)
    return MAGIA + nonce + AESGCM(_chave(pid, tipo)).encrypt(nonce, dados, f'{pid}:{tipo}'.encode())


def decifrar(pid, tipo, bruto):
    bruto = bytes(bruto)
    if bruto[:3] != MAGIA:
        raise ValueError('ficheiro do cofre corrompido')
    return AESGCM(_chave(pid, tipo)).decrypt(bruto[3:15], bruto[15:], f'{pid}:{tipo}'.encode())


class Cofre:
    """Mesma interface do cofre do Escudo (cifrar/decifrar), sobre a chave-mestra do SIGE."""
    cifrar = staticmethod(cifrar)
    decifrar = staticmethod(decifrar)
