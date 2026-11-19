"""
Capacidades da PLATAFORMA (painel do Super Admin): dados agregados de todas as escolas, só leitura.
Só o SuperAdmin as vê (`perfis={'SUPERADMIN'}`); nunca são oferecidas a perfis de uma escola.
"""
import datetime
from collections import Counter
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from . import capacidades as cap
from .capacidades import Capacidade, _data, _lista, _res

SUPER = {'SUPERADMIN'}
ESTADO_ROTULO = {'teste': 'em teste', 'activa': 'activas', 'fatura_pendente': 'com fatura pendente', 'em_atraso': 'em atraso',
                 'restrita': 'restritas', 'suspensa': 'suspensas'}


def h_plat_resumo(ctx):
    from apps.alunos.models import Aluno
    from apps.professores.models import Professor
    from apps.tenants.models import Escola
    por_estado = Counter(Escola.objects.values_list('status', flat=True))
    total = sum(por_estado.values())
    if not total:
        return _res('Ainda não há escolas registadas na plataforma.', {'escolas': 0}, 'saas', 'Abrir o Painel Master')
    partes = ', '.join(f'{n} {s.lower()}' for s, n in sorted(por_estado.items()))
    return _res(f'A plataforma tem {total} escola(s): {partes}. No total, {Aluno.objects.count()} aluno(s) e {Professor.objects.count()} professor(es).',
                {'escolas': total, 'por_estado': dict(por_estado)}, 'saas', 'Abrir o Painel Master')


def h_plat_assinaturas(ctx):
    from apps.tenants.models import SaasAssinatura
    por_estado = Counter(SaasAssinatura.objects.values_list('estado', flat=True))
    if not por_estado:
        return _res('Ainda não há assinaturas SaaS registadas.', {'assinaturas': 0}, 'saas', 'Abrir o Painel Master')
    partes = '; '.join(f'{n} {ESTADO_ROTULO.get(e, e)}' for e, n in por_estado.items())
    criticas = [a.instituicao.nome for a in SaasAssinatura.objects.filter(estado__in=('em_atraso', 'restrita', 'suspensa')).select_related('instituicao')[:20]]
    txt = f'Assinaturas SaaS: {partes}.'
    if criticas:
        txt += ' A pedir atenção: ' + _lista(criticas, 5) + '.'
    return _res(txt, dict(por_estado), 'saas', 'Abrir o Painel Master')


def h_plat_faturas(ctx):
    from apps.tenants.models import SaasFatura
    abertas = SaasFatura.objects.filter(estado__in=('aberta', 'paga_parcial', 'em_atraso'))
    n, atraso = abertas.count(), abertas.filter(estado='em_atraso').count()
    if not n:
        return _res('Não há faturas SaaS em aberto.', {'em_aberto': 0}, 'pagamentos-saas', 'Abrir Assinaturas & Pagamentos SaaS')
    em_aberto = sum((f.valor + f.multa_aplicada - f.valor_pago for f in abertas), Decimal('0'))
    return _res(f'Há {n} fatura(s) SaaS em aberto, {atraso} em atraso, num total de {em_aberto:.2f} MZN por receber.',
                {'em_aberto': n, 'em_atraso': atraso, 'valor': str(em_aberto)}, 'pagamentos-saas', 'Abrir Assinaturas & Pagamentos SaaS')


def h_plat_pagamentos(ctx):
    from apps.tenants.models import SaasPagamento
    por_validar = SaasPagamento.objects.filter(estado='enviado').select_related('instituicao')
    n = por_validar.count()
    if not n:
        return _res('Não há comprovativos de pagamento por validar.', {'por_validar': 0}, 'pagamentos-saas', 'Abrir Assinaturas & Pagamentos SaaS')
    valor = por_validar.aggregate(s=Sum('valor'))['s'] or Decimal('0')
    escolas = sorted({p.instituicao.nome for p in por_validar[:50]})
    return _res(f'Há {n} comprovativo(s) por validar, no valor de {valor:.2f} MZN (escolas: {_lista(escolas, 5)}).',
                {'por_validar': n, 'valor': str(valor)}, 'pagamentos-saas', 'Abrir Assinaturas & Pagamentos SaaS')


def h_plat_planos(ctx):
    from apps.tenants.models import SaasPlano
    planos = list(SaasPlano.objects.filter(activo=True).annotate(n=Count('assinaturas')).order_by('preco_mensal'))
    if not planos:
        return _res('Ainda não há planos SaaS activos.', {'planos': 0}, 'saas', 'Abrir o Painel Master')
    return _res('Planos activos: ' + '; '.join(f'{p.nome} ({p.preco_mensal} MZN/mês, {p.n} escola(s))' for p in planos) + '.',
                {'planos': len(planos)}, 'saas', 'Abrir o Painel Master')


def h_plat_mrr(ctx):
    from apps.tenants.models import SaasAssinatura
    activas = SaasAssinatura.objects.filter(estado__in=('activa', 'fatura_pendente')).select_related('plano')
    mrr = sum((a.plano.preco_mensal for a in activas), Decimal('0'))
    n = activas.count()
    if not n:
        return _res('Ainda não há assinaturas activas para calcular a receita mensal.', {'mrr': '0'}, 'saas', 'Abrir o Painel Master')
    return _res(f'Receita mensal contratada (assinaturas activas e com fatura pendente): {mrr:.2f} MZN, de {n} escola(s) (anual: {mrr * 12:.2f} MZN).',
                {'mrr': str(mrr), 'assinaturas': n}, 'saas', 'Abrir o Painel Master')


def h_plat_assistente(ctx):
    from .models import ConsultaAssistente
    desde = timezone.now() - datetime.timedelta(days=30)
    qs = ConsultaAssistente.objects.filter(created_at__gte=desde)
    total = qs.count()
    if not total:
        return _res('Ainda não houve perguntas ao assistente nos últimos 30 dias.', {'perguntas': 0}, 'assistente-relatorio', 'Abrir o Relatório do Assistente')
    desc = qs.filter(intencao__in=('desconhecida', 'fora_do_painel')).count()
    nao_uteis = qs.filter(util=False).count()
    return _res(f'Nos últimos 30 dias: {total} pergunta(s); {desc} sem resposta ou fora do painel ({100 * desc // total}%) e {nao_uteis} marcada(s) como não útil. '
                'O relatório mostra as perguntas a melhorar.', {'perguntas': total, 'sem_resposta': desc, 'nao_uteis': nao_uteis},
                'assistente-relatorio', 'Abrir o Relatório do Assistente')


CAPACIDADES_PLATAFORMA = [
    Capacidade('plat_resumo', 'dados', [' quantas escolas', ' escolas registadas', ' total de escolas', ' escolas na plataforma', ' escolas ativas', ' escolas activas',
                                        ' alunos na plataforma', ' alunos na nuvem', ' professores na plataforma'], h_plat_resumo, perfis=SUPER, destino='saas', plataforma=True,
               exemplos=('Quantas escolas temos?',), peso=2),
    Capacidade('plat_assinaturas', 'dados', [' assinaturas', ' escolas em atraso', ' suspensas', ' restritas', ' escolas suspensas', ' estado das assinaturas'],
               h_plat_assinaturas, perfis=SUPER, destino='saas', plataforma=True, exemplos=('Quantas assinaturas estão em atraso?',), peso=2),
    Capacidade('plat_faturas', 'dados', [' faturas', ' faturas em aberto', ' por receber', ' faturas em atraso', ' faturacao'], h_plat_faturas,
               perfis=SUPER, destino='pagamentos-saas', plataforma=True, exemplos=('Há faturas em atraso?',), peso=2),
    Capacidade('plat_pagamentos', 'dados', [' comprovativos por validar', ' pagamentos por validar', ' comprovativos', ' pagamentos pendentes', ' por validar'],
               h_plat_pagamentos, perfis=SUPER, destino='pagamentos-saas', plataforma=True, exemplos=('Há comprovativos por validar?',), peso=2),
    Capacidade('plat_planos', 'dados', [' planos', ' planos saas', ' planos activos', ' planos ativos'], h_plat_planos, perfis=SUPER, destino='saas',
               plataforma=True, exemplos=('Que planos temos?',)),
    Capacidade('plat_mrr', 'dados', [' mrr', ' arr', ' receita mensal', ' receita anual', ' quanto faturamos', ' quanto faturamos por mes'], h_plat_mrr,
               perfis=SUPER, destino='saas', plataforma=True, exemplos=('Qual a receita mensal (MRR)?',), peso=2),
    Capacidade('plat_assistente', 'dados', [' perguntas sem resposta', ' relatorio do assistente', ' uso do assistente', ' o assistente falha', ' perguntas nao uteis', ' correr o assistente', ' como esta o assistente', ' qualidade do assistente', ' assistente falha'],
               h_plat_assistente, perfis=SUPER, destino='assistente-relatorio', plataforma=True, exemplos=('Como está a correr o assistente?',), peso=2),
]


def registar():
    """Junta as capacidades da plataforma ao registo geral (idempotente)."""
    if not any(c.plataforma for c in cap.CAPACIDADES):
        cap.CAPACIDADES.extend(CAPACIDADES_PLATAFORMA)
        cap.POR_NOME.update({c.nome: c for c in CAPACIDADES_PLATAFORMA})
