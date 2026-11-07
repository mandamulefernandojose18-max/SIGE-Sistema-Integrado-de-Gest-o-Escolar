"""
Alarmes de supervisão de pagamentos SaaS (só SuperAdmin).

Cada alarme tem código, título, severidade (critica | aviso | info), total e até MAX_ITENS exemplos,
para que a interface tenha altura constante, qualquer que seja o número de escolas.
"""
from datetime import timedelta
from django.db.models import Count
from django.utils import timezone

from .models import SaasAssinatura, SaasFatura, SaasLogAssinatura, SaasPagamento, SaasRotinaExecucao
from .saas_services import calcular_data_limite_efectiva_python

MAX_ITENS = 5
HORAS_COMPROVATIVO_CRITICO = 24
DIAS_AVISO_VENCIMENTO = 7
DIAS_AVISO_SUSPENSAO = 7
HORAS_ROTINA_ATRASADA = 36


def _alarme(codigo, titulo, severidade, itens, total=None, descricao=''):
    total = len(itens) if total is None else total
    return {
        'codigo': codigo, 'titulo': titulo, 'severidade': severidade,
        'descricao': descricao, 'total': total, 'itens': itens[:MAX_ITENS],
    }


def calcular_alarmes():
    agora = timezone.now()
    hoje = timezone.localdate()
    alarmes = []

    # 1. Comprovativos por confirmar (críticos se esperam mais de 24 h)
    pendentes = list(SaasPagamento.objects.select_related('instituicao', 'fatura').filter(estado='enviado').order_by('criado_em'))
    itens = []
    for p in pendentes:
        horas = int((agora - p.criado_em).total_seconds() // 3600)
        itens.append({
            'instituicao_id': str(p.instituicao_id), 'instituicao': p.instituicao.nome,
            'detalhe': f'{p.valor} MZN · ref. {p.referencia} · há {horas} h', 'horas': horas,
        })
    if itens:
        critico = any(i['horas'] >= HORAS_COMPROVATIVO_CRITICO for i in itens)
        alarmes.append(_alarme('comprovativos_pendentes', 'Comprovativos por confirmar',
                               'critica' if critico else 'aviso', itens,
                               descricao=f'Críticos a partir de {HORAS_COMPROVATIVO_CRITICO} h de espera.'))

    # 2. Faturas a vencer nos próximos dias / faturas em atraso / a entrar em suspensão
    a_vencer, em_atraso, quase_suspensas = [], [], []
    faturas = SaasFatura.objects.select_related('instituicao', 'assinatura').filter(
        estado__in=['aberta', 'paga_parcial', 'em_atraso'])
    for f in faturas:
        ass = f.assinatura
        limite = calcular_data_limite_efectiva_python(f)
        lim_tol = limite + timedelta(days=ass.dias_tolerancia)
        lim_sus = lim_tol + timedelta(days=ass.dias_ate_suspensao)
        divida = f.valor + f.multa_aplicada - f.valor_pago
        base = {'instituicao_id': str(f.instituicao_id), 'instituicao': f.instituicao.nome}
        if hoje <= limite and (limite - hoje).days <= DIAS_AVISO_VENCIMENTO:
            dias = (limite - hoje).days
            a_vencer.append({**base, 'dias': dias, 'detalhe': f'{divida} MZN · vence em {dias} dia(s)'})
        elif hoje > limite:
            atraso = (hoje - limite).days
            em_atraso.append({**base, 'dias': atraso, 'detalhe': f'{divida} MZN · {atraso} dia(s) de atraso'})
            if hoje < lim_sus and (lim_sus - hoje).days <= DIAS_AVISO_SUSPENSAO:
                quase_suspensas.append({**base, 'dias': (lim_sus - hoje).days,
                                        'detalhe': f'{divida} MZN · suspensão em {(lim_sus - hoje).days} dia(s)'})
    a_vencer.sort(key=lambda i: i['dias'])
    em_atraso.sort(key=lambda i: -i['dias'])
    quase_suspensas.sort(key=lambda i: i['dias'])
    if a_vencer:
        alarmes.append(_alarme('faturas_a_vencer', f'Faturas a vencer em {DIAS_AVISO_VENCIMENTO} dias', 'aviso', a_vencer))
    if em_atraso:
        alarmes.append(_alarme('faturas_em_atraso', 'Faturas em atraso', 'critica', em_atraso))
    if quase_suspensas:
        alarmes.append(_alarme('a_entrar_em_suspensao', f'A entrar em suspensão em {DIAS_AVISO_SUSPENSAO} dias', 'critica', quase_suspensas))

    # 3. Suspensões automáticas nas últimas 24 h
    desde = agora - timedelta(hours=24)
    logs = SaasLogAssinatura.objects.select_related('instituicao').filter(
        accao='SUSPENSAO_AUTOMATICA', criado_em__gte=desde).order_by('-criado_em')
    itens = [{'instituicao_id': str(l.instituicao_id), 'instituicao': l.instituicao.nome,
              'detalhe': (l.motivo or '')[:90]} for l in logs]
    if itens:
        alarmes.append(_alarme('suspensas_24h', 'Suspensas automaticamente nas últimas 24 h', 'critica', itens))

    # 4. Anomalias: referência duplicada e comprovativo com valor diferente do devido
    duplicadas = (SaasPagamento.objects.exclude(estado='rejeitado').values('referencia')
                  .annotate(n=Count('id')).filter(n__gt=1))
    refs = [d['referencia'] for d in duplicadas]
    itens = []
    if refs:
        for p in SaasPagamento.objects.select_related('instituicao').filter(referencia__in=refs).exclude(estado='rejeitado').order_by('referencia'):
            itens.append({'instituicao_id': str(p.instituicao_id), 'instituicao': p.instituicao.nome,
                          'detalhe': f'Referência duplicada: {p.referencia} ({p.valor} MZN)'})
    for p in pendentes:
        devido = p.fatura.valor + p.fatura.multa_aplicada - p.fatura.valor_pago
        if devido > 0 and p.valor != devido:
            itens.append({'instituicao_id': str(p.instituicao_id), 'instituicao': p.instituicao.nome,
                          'detalhe': f'Valor {p.valor} MZN difere do devido ({devido} MZN)'})
    if itens:
        alarmes.append(_alarme('anomalias', 'Anomalias em pagamentos', 'aviso', itens,
                               descricao='Referências repetidas ou valores diferentes do devido.'))

    # 4b. Excepções activas "não suspender até <data>" (informativo)
    adiadas = SaasAssinatura.objects.select_related('instituicao').filter(
        suspensao_adiada_ate__gte=hoje).order_by('suspensao_adiada_ate')
    itens = [{'instituicao_id': str(a.instituicao_id), 'instituicao': a.instituicao.nome,
              'detalhe': f'até {a.suspensao_adiada_ate.strftime("%d/%m/%Y")} · {(a.suspensao_adiada_motivo or "")[:70]}'}
             for a in adiadas]
    if itens:
        alarmes.append(_alarme('suspensao_adiada', 'Excepções: suspensão adiada', 'info', itens,
                               descricao='Escolas com acordo para não serem suspensas automaticamente até à data indicada.'))

    # 5. Rotina diária (faturação/suspensão/reactivação): falhou ou não corre há muito tempo
    ultima = SaasRotinaExecucao.objects.order_by('-executada_em').first()
    if ultima is None:
        alarmes.append(_alarme('rotina_diaria', 'Rotina diária nunca executada', 'aviso',
                               [{'instituicao_id': None, 'instituicao': 'Sistema',
                                 'detalhe': 'Sem registo de execuções. Confirme o agendamento diário.'}]))
    elif not ultima.sucesso:
        alarmes.append(_alarme('rotina_diaria', 'Rotina diária falhou', 'critica',
                               [{'instituicao_id': None, 'instituicao': 'Sistema', 'detalhe': (ultima.erro or 'erro')[:120]}]))
    elif (agora - ultima.executada_em) > timedelta(hours=HORAS_ROTINA_ATRASADA):
        horas = int((agora - ultima.executada_em).total_seconds() // 3600)
        alarmes.append(_alarme('rotina_diaria', 'Rotina diária em atraso', 'critica',
                               [{'instituicao_id': None, 'instituicao': 'Sistema',
                                 'detalhe': f'Última execução há {horas} h (esperado: diária).'}]))

    ordem = {'critica': 0, 'aviso': 1, 'info': 2}
    alarmes.sort(key=lambda a: ordem[a['severidade']])
    return {
        'gerado_em': agora.isoformat(),
        'total_alertas': sum(a['total'] for a in alarmes),
        'criticos': sum(a['total'] for a in alarmes if a['severidade'] == 'critica'),
        'nivel': ('critica' if any(a['severidade'] == 'critica' for a in alarmes)
                  else 'aviso' if alarmes else 'ok'),
        'ultima_rotina': (ultima.executada_em.isoformat() if ultima else None),
        'alarmes': alarmes,
    }
