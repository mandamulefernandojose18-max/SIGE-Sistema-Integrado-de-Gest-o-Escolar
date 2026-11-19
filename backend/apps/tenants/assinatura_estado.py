"""Textos e estado de assinatura partilhados entre o login, o middleware e o assistente."""
import datetime


def mensagem_bloqueio(nome_escola, status):
    """Mensagem de acesso bloqueado, adequada ao motivo (escola na lixeira ou subscrição expirada)."""
    if str(status or '').strip().upper() == 'ELIMINADA':
        return (f'Acesso bloqueado: a instituição de ensino ({nome_escola}) foi removida da plataforma. '
                f'Para a restabelecer, contacte o Engenheiro do Sistema, responsável pela gestão das instituições.')
    return (f'Acesso bloqueado: A sua instituição de ensino ({nome_escola}) encontra-se com a subscrição expirada. '
            f'Por esse motivo, o acesso ao sistema está temporariamente vedado. '
            f'Para restabelecer o acesso, contacte o Engenheiro do Sistema, responsável pela gestão das instituições '
            f'e pela renovação das respectivas subscrições.')


def estado_assinatura_escola(escola, hoje=None):
    """Estado da assinatura da escola. Usa a assinatura SaaS (a que é facturada e validada pelo SuperAdmin) e,
    só se a escola não tiver nenhuma, a assinatura antiga. Devolve None se não houver nenhuma.

    {'origem': 'saas'|'legado', 'plano': str, 'estado': str, 'data': date, 'dias': int}
    `data` é o vencimento da próxima fatura (SaaS) ou o fim do contrato (legado)."""
    from .models import AssinaturaEscola, SaasAssinatura
    hoje = hoje or datetime.date.today()
    ass = SaasAssinatura.objects.filter(instituicao=escola).select_related('plano').order_by('-created_at').first()
    if ass and ass.proxima_fatura_em:
        return {'origem': 'saas', 'plano': ass.plano.nome if ass.plano else '-', 'estado': ass.estado,
                'data': ass.proxima_fatura_em, 'dias': (ass.proxima_fatura_em - hoje).days}
    leg = AssinaturaEscola.objects.filter(escola=escola).select_related('plano').order_by('-data_fim').first()
    if leg:
        fim = leg.data_fim.date()
        return {'origem': 'legado', 'plano': leg.plano.nome if leg.plano else '-', 'estado': str(leg.status).lower(),
                'data': fim, 'dias': (fim - hoje).days}
    return None