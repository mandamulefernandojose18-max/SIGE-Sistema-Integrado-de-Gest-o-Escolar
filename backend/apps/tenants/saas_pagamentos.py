"""Núcleo dos pagamentos de assinatura SaaS: confirmação única e leitura de SMS M-Pesa / e-Mola.

Todas as vias (confirmação manual de comprovativo, registo directo pelo SuperAdmin e reconciliação
automática por SMS) terminam em `confirmar_pagamento_saas`, para haver uma única regra de negócio.
"""
import re
from decimal import Decimal, InvalidOperation

from django.utils import timezone

from .models import SaasLogAssinatura
from .saas_services import aplicar_pagamento_adiantado_python


def confirmar_pagamento_saas(pag, utilizador, accao='PAGAMENTO_CONFIRMADO', nota=''):
    """Confirma um pagamento `enviado` e aplica-o à fatura/assinatura.

    O chamador tem de estar dentro de `transaction.atomic()` e ter bloqueado a linha do pagamento
    (`select_for_update`) e verificado que o estado é `enviado`.
    """
    fat = pag.fatura
    ass = fat.assinatura

    pag.estado = 'confirmado'
    pag.confirmado_por = utilizador
    pag.confirmado_em = timezone.now()
    pag.save()

    res_app = aplicar_pagamento_adiantado_python(
        ass=ass, fatura_principal=fat, valor_pago_total=pag.valor, utilizador=utilizador)

    motivo = f"Pagamento Ref: {pag.referencia} ({pag.valor} MZN). {res_app['info_adiantado']['descricao']}"
    if nota:
        motivo = f"{nota} {motivo}"
    SaasLogAssinatura.objects.create(
        instituicao=pag.instituicao, assinatura=ass, fatura=fat, accao=accao,
        estado_anterior=ass.estado, estado_novo='activa' if res_app['assinatura_reativada'] else ass.estado,
        valor_novo=pag.valor, feito_por=utilizador, motivo=motivo[:1000])

    return {
        'sucesso': True,
        'mensagem': 'Pagamento confirmado e processado com sucesso.',
        'assinatura_reativada': res_app['assinatura_reativada'],
        'fatura_liquidada': res_app['fatura_liquidada'],
        'info_adiantado': res_app['info_adiantado'],
    }


# ---------------------------------------------------------------------------
# Leitura de SMS M-Pesa / e-Mola
# ---------------------------------------------------------------------------
_RE_VALOR = re.compile(r'(?<![\d.,])(\d[\d.,]*\d|\d)\s*(?:MT|MZN|MZM)\b', re.I)
_RE_REF = re.compile(r'(?:Ref(?:er[eê]ncia)?|Transa[cç][aã]o(?:\s*ID)?|ID(?:\s*da\s*transa[cç][aã]o)?)\s*[.:\-]?\s*([A-Z0-9][A-Z0-9.\-]{3,})', re.I)


def normalizar_valor(texto):
    """'1,500.00' e '1.500,00' e '1500' → Decimal. O último separador seguido de 1-2 dígitos é a vírgula decimal."""
    t = re.sub(r'\s', '', str(texto))
    m = re.search(r'[.,](\d{1,2})$', t)
    if m:
        inteira = re.sub(r'[.,]', '', t[:m.start()])
        t = f'{inteira}.{m.group(1)}'
    else:
        t = re.sub(r'[.,]', '', t)
    try:
        return Decimal(t)
    except InvalidOperation:
        return None


def analisar_sms(texto):
    """Extrai (valor, referência) de uma SMS de recebimento. Devolve None nos campos que não encontrar."""
    texto = str(texto or '')
    valor = None
    for m in _RE_VALOR.finditer(texto):
        v = normalizar_valor(m.group(1))
        if v is not None and v > 0:
            valor = v
            break
    m_ref = _RE_REF.search(texto)
    referencia = m_ref.group(1).strip().rstrip('.,;:-') if m_ref else None
    return valor, referencia
