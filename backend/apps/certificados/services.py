"""Emissão de códigos de autenticidade de certificados.

O código impresso no documento tem de existir na tabela `Certificado` e ser aleatório
(nunca derivado da matrícula), porque a verificação pública só aceita códigos registados.
"""
import os
import uuid

from .models import Certificado


def obter_ou_criar_certificado_conclusao(escola, aluno, emitido_por='Secretaria'):
    """Devolve o `Certificado` de conclusão do aluno, criando-o (código aleatório) se ainda não existir."""
    cert = Certificado.objects.filter(escola=escola, aluno=aluno, tipo='CONCLUSAO').first()
    if cert:
        return cert
    codigo = f"CERT-{uuid.uuid4().hex[:10].upper()}"
    base = os.environ.get('SIGE_PUBLIC_URL', 'https://sigesaas.duckdns.org').rstrip('/')
    return Certificado.objects.create(
        escola=escola,
        aluno=aluno,
        tipo='CONCLUSAO',
        codigo_autenticidade=codigo,
        qrcode_data=f"{base}/verificar-certificado.html?codigo={codigo}",
        emitido_por=emitido_por,
    )


def codigo_certificado_conclusao(escola, aluno, emitido_por='Secretaria'):
    return obter_ou_criar_certificado_conclusao(escola, aluno, emitido_por).codigo_autenticidade
