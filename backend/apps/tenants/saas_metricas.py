"""Métricas do painel SuperAdmin, calculadas sobre o modelo de assinaturas SaaS (SaasAssinatura/SaasFatura),
o mesmo que alimenta as páginas de pagamentos e os alarmes. Substitui o cálculo antigo, feito sobre o
modelo legado `AssinaturaEscola`, que podia divergir dos restantes números.

Definições (uma assinatura por escola: a mais recente; escolas na lixeira ficam de fora):
* Contratadas (pagantes): estado activa, fatura_pendente, em_atraso ou restrita. O período de teste não conta para a receita.
* MRR: soma do valor mensal equivalente das contratadas = valor da fatura do período ÷ meses do período
  (já inclui o desconto da periodicidade e o preço do pacote, quando a escola é facturada por pacote).
* ARR: MRR × 12.
* Churn (30 dias): escolas que passaram a suspensa/cancelada nos últimos 30 dias e continuam assim,
  ÷ (contratadas hoje + essas escolas). Escolas reactivadas entretanto não contam.
"""
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from .models import Escola, SaasAssinatura, SaasLogAssinatura
from .pacotes import PERIODOS_MESES
from .saas_services import preco_mensal_contratado, valor_fatura_periodo

CONTRATADAS = ('activa', 'fatura_pendente', 'em_atraso', 'restrita')
PERDIDAS = ('suspensa', 'cancelada')
JANELA_CHURN_DIAS = 30


def valor_mensal_equivalente(ass):
    """Valor mensal efectivamente contratado (já com desconto de periodicidade)."""
    meses = PERIODOS_MESES.get(ass.periodicidade, 1) or 1
    try:
        return Decimal(valor_fatura_periodo(ass)) / Decimal(meses)
    except Exception:  # assinatura sem plano válido: usa o preço mensal base
        return Decimal(preco_mensal_contratado(ass) or 0)


def _ultima_assinatura_por_escola():
    ultimas = {}
    qs = (SaasAssinatura.objects.filter(instituicao__eliminada_em__isnull=True)
          .select_related('plano', 'instituicao', 'instituicao__pacote').order_by('-created_at'))
    for ass in qs:
        ultimas.setdefault(ass.instituicao_id, ass)
    return ultimas


def calcular_metricas_saas():
    from apps.alunos.models import Aluno
    from apps.professores.models import Professor

    ultimas = _ultima_assinatura_por_escola()
    contratadas = [a for a in ultimas.values() if a.estado in CONTRATADAS]
    mrr = sum((valor_mensal_equivalente(a) for a in contratadas), Decimal('0'))

    desde = timezone.now() - timedelta(days=JANELA_CHURN_DIAS)
    candidatas = set(
        SaasLogAssinatura.objects
        .filter(criado_em__gte=desde, estado_novo__in=PERDIDAS, instituicao__eliminada_em__isnull=True)
        .exclude(estado_anterior__in=PERDIDAS)
        .values_list('instituicao_id', flat=True))
    perdidas = [i for i in candidatas if i in ultimas and ultimas[i].estado in PERDIDAS]
    base = len(contratadas) + len(perdidas)
    churn = round(len(perdidas) / base * 100, 1) if base else 0.0

    total = Escola.objects.count()
    ativas = sum(1 for a in ultimas.values() if a.estado in CONTRATADAS or a.estado == 'teste')
    expiradas = sum(1 for a in ultimas.values() if a.estado in PERDIDAS)
    mrr_f = float(round(mrr, 2))

    return {
        'mrr': mrr_f,
        'arr': float(round(mrr * 12, 2)),
        'churn': churn,
        'churn_escolas': len(perdidas),
        'churn_janela_dias': JANELA_CHURN_DIAS,
        'pagantes': len(contratadas),
        'escolas': {'total': total, 'ativas': ativas, 'expiradas': expiradas},
        'totalEscolas': total,
        'escolasAtivas': ativas,
        'escolasExpiradas': expiradas,
        'totalAlunos': Aluno.objects.filter(escola__eliminada_em__isnull=True).count(),
        'totalProfessores': Professor.objects.filter(escola__eliminada_em__isnull=True).count(),
        'receitaMensalEstimada': mrr_f,
    }
