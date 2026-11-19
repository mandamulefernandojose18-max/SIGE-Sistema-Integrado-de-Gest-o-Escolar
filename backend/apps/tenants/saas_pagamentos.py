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


_RE_CONFIRMADO = re.compile(r'Confirmad[oa]\s*[.:\-]?\s*([A-Z0-9][A-Z0-9.\-]{5,})', re.I)


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
    # 1.º: código rotulado (Ref, ID, Transacção); 2.º: o código que segue "Confirmado" (formato habitual das SMS M-Pesa).
    m_ref = _RE_REF.search(texto) or _RE_CONFIRMADO.search(texto)
    referencia = m_ref.group(1).strip().rstrip('.,;:-') if m_ref else None
    return valor, referencia


# ---------------------------------------------------------------------------
# Reconciliação por SMS (partilhada pela janela do SuperAdmin e pelo webhook)
# ---------------------------------------------------------------------------
def reconciliar_sms_texto(texto, utilizador):
    """Lê a SMS e, se referência E valor coincidirem exactamente com um comprovativo `enviado`,
    confirma-o. Nunca cria pagamentos. Devolve (http_status, payload)."""
    from django.db import transaction
    from .models import SaasPagamento
    from .saas_middleware import limpar_cache_assinatura

    texto = str(texto or '').strip()
    if not texto:
        return 400, {'success': False, 'message': 'Texto da SMS não fornecido.'}
    if len(texto) > 1000:
        return 400, {'success': False, 'message': 'Texto demasiado longo para uma SMS.'}

    valor, referencia = analisar_sms(texto)
    if valor is None or not referencia:
        return 200, {'success': True, 'status': 'NAO_RECONHECIDA',
                     'message': 'Não foi possível ler o valor e a referência desta SMS.'}

    utilizador = str(utilizador)[:150]
    with transaction.atomic():
        candidatos = list(SaasPagamento.objects.select_for_update().select_related('fatura__assinatura', 'instituicao')
                          .filter(referencia__iexact=referencia, estado='enviado'))
        if not candidatos:
            ja = SaasPagamento.objects.filter(referencia__iexact=referencia, estado='confirmado').exists()
            return 200, {'success': True, 'status': 'DUPLICADO' if ja else 'SEM_CORRESPONDENCIA',
                         'referencia': referencia, 'valor': str(valor),
                         'message': 'Esta referência já foi confirmada.' if ja else
                                    'Nenhum comprovativo pendente com esta referência. Aguarde a submissão pela escola.'}
        exactos = [p for p in candidatos if p.valor == valor]
        if not exactos:
            return 200, {'success': True, 'status': 'VALOR_DIVERGENTE', 'referencia': referencia, 'valor': str(valor),
                         'message': f'A referência existe, mas o valor da SMS ({valor} MZN) difere do comprovativo '
                                    f'({candidatos[0].valor} MZN). Valide manualmente.'}
        if len(exactos) > 1:
            return 200, {'success': True, 'status': 'AMBIGUO', 'referencia': referencia, 'valor': str(valor),
                         'message': 'Mais de um comprovativo corresponde. Valide manualmente.'}

        pag = exactos[0]
        resultado = confirmar_pagamento_saas(
            pag, utilizador, accao='PAGAMENTO_CONFIRMADO_SMS', nota='Reconciliado automaticamente por SMS.')

    limpar_cache_assinatura(pag.instituicao_id)
    return 200, {'success': True, 'status': 'CONFIRMADO', 'referencia': referencia, 'valor': str(valor),
                 'instituicao': pag.instituicao.nome, 'message': 'Pagamento confirmado automaticamente.', 'data': resultado}
