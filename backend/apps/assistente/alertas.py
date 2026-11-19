"""
Alertas proactivos do Assistente (custo zero, só leitura): o que merece atenção de cada perfil, calculado na hora a partir
de dados reais da escola. Sem nada a assinalar devolve lista vazia (nunca inventa alertas).

Cada alerta: {nivel: 'alta'|'media'|'info', titulo, detalhe, destino, rotulo}. O ecrã mostra um contador no menu e o painel
"Merece atenção" no assistente; o destino é um ecrã do menu do perfil.
"""
import datetime
from decimal import Decimal

from django.utils import timezone

from . import capacidades as cap
from .capacidades import DIRECCAO, GESTAO, PROPRIO, Ctx

MAX_ALERTAS = 12
ORDEM = {'alta': 0, 'media': 1, 'info': 2}


def _a(nivel, titulo, detalhe='', destino=None, rotulo=None):
    return {'nivel': nivel, 'titulo': titulo, 'detalhe': detalhe, 'destino': destino, 'rotulo': rotulo or ('Abrir' if destino else None)}


def _educandos(user, escola):
    from apps.alunos.models import Aluno
    from .engine import educandos_do_encarregado
    if user.role == 'ENCARREGADO':
        return educandos_do_encarregado(user, escola)
    if user.role == 'ALUNO' and getattr(user, 'aluno_id', None):
        return list(Aluno.objects.filter(id=user.aluno_id, escola=escola).select_related('turma'))
    return []


def _ctx(user, escola, aluno=None):
    return Ctx(user=user, escola=escola, pergunta='', texto='', aluno=aluno)


# ---------------------------------------------------------------- aluno / encarregado (por educando)
def alertas_familia(user, escola):
    from apps.notas.models import CalendarioExame
    from apps.pagamentos.models import Pagamento
    out, agora, hoje = [], timezone.now(), datetime.date.today()
    for aluno in _educandos(user, escola):
        ctx = _ctx(user, escola, aluno)
        nome = cap._nome(aluno) if user.role == 'ENCARREGADO' else 'Você'
        abertos = list(Pagamento.objects.filter(escola=escola, aluno=aluno, status__in=('PENDENTE', 'ATRASADO')))
        atraso = [p for p in abertos if p.data_vencimento < agora]
        if atraso:
            valor = sum((p.valor - p.valor_pago for p in atraso), Decimal('0'))
            meses = ', '.join(sorted(p.mes_referencia for p in atraso)[:4])
            out.append(_a('alta' if len(atraso) >= 2 else 'media', f'{nome}: {len(atraso)} propina(s) em atraso',
                          f'{valor} MZN ({meses})', 'aluno-pagamentos', 'Ver propinas'))
        a_vencer = [p for p in abertos if agora <= p.data_vencimento <= agora + datetime.timedelta(days=7)]
        if a_vencer:
            out.append(_a('info', f'{nome}: {len(a_vencer)} propina(s) a vencer nos próximos 7 dias', '', 'aluno-pagamentos', 'Ver propinas'))
        efectivas, injust = cap.faltas_do_aluno(escola, aluno, ctx.ano)
        if injust:
            out.append(_a('media' if efectivas >= 10 else 'info', f'{nome}: {injust} falta(s) por justificar',
                          f'{efectivas} falta(s) efectiva(s) no ano lectivo. Pode pedir a justificação.', 'aluno-faltas', 'Ver faltas'))
        periodos, permitido = cap._trimestres_visiveis(ctx)
        if permitido and periodos:
            mapa = cap._notas_por_disciplina(ctx, periodos)
            for p in reversed(periodos):
                neg = sorted(d for d, per in mapa.items() if p in per and per[p] < 9.5)
                if any(p in per for per in mapa.values()):
                    if neg:
                        out.append(_a('media', f'{nome}: {len(neg)} negativa(s) no {cap.ROTULO_TRIM[p]}', ', '.join(neg[:5]), 'aluno-notas', 'Ver notas'))
                    break
        if aluno.classe:
            exames = list(CalendarioExame.objects.filter(escola=escola, classe__iexact=aluno.classe, data__gte=hoje,
                                                         data__lte=hoje + datetime.timedelta(days=14)).order_by('data', 'hora_inicio')[:3])
            if exames:
                out.append(_a('info', f'{nome}: {len(exames)} exame(s) nos próximos 14 dias',
                              '; '.join(f'{e.data:%d/%m} {e.disciplina}' for e in exames), 'aluno-calendario', 'Ver calendário'))
    return out


# ---------------------------------------------------------------- professor
def alertas_professor(user, escola):
    from apps.atribuicoes.models import AtribuicaoCargo
    out, hoje = [], datetime.date.today()
    qs = AtribuicaoCargo.objects.filter(escola=escola, professor_id=getattr(user, 'professor_id', None)).exclude(estado='CONCLUIDA')
    atrasadas = qs.filter(prazo__lt=hoje).count()
    proximas = qs.filter(prazo__gte=hoje, prazo__lte=hoje + datetime.timedelta(days=7)).count()
    if atrasadas:
        out.append(_a('alta', f'{atrasadas} actividade(s) de cargo com o prazo ultrapassado', '', 'minhas-atividades', 'Ver actividades'))
    if proximas:
        out.append(_a('media', f'{proximas} actividade(s) de cargo a vencer nos próximos 7 dias', '', 'minhas-atividades', 'Ver actividades'))
    return out


# ---------------------------------------------------------------- escola (gestão)
def alertas_transferencias(user, escola):
    from apps.alunos.models import TransferenciaAnulacao
    pend = TransferenciaAnulacao.objects.filter(escola=escola, status='PENDENTE')
    n = pend.count()
    if not n:
        return []
    atraso = pend.filter(data_solicitacao__lte=datetime.date.today() - datetime.timedelta(days=7)).count()
    return [_a('alta' if atraso else 'media', f'{n} transferência(s)/anulação(ões) pendente(s)',
               f'{atraso} há mais de 7 dias' if atraso else '', 'transferencias', 'Ver transferências')]


def alertas_crm(user, escola):
    from apps.crm.models import Atendimento
    qs = Atendimento.objects.filter(escola=escola).exclude(estado='RESOLVIDO')
    antigos = qs.filter(created_at__lte=timezone.now() - datetime.timedelta(days=7)).count()
    altos = qs.filter(prioridade='ALTA').count()
    n = qs.count()
    if not n:
        return []
    return [_a('alta' if (antigos or altos) else 'info', f'{n} atendimento(s) por resolver',
               f'{antigos} com mais de 7 dias; {altos} de prioridade alta', 'crm', 'Abrir o CRM')]


def alertas_risco(user, escola):
    dados = cap.h_risco(_ctx(user, escola)).get('dados') or {}
    n = dados.get('em_risco', 0)
    if not n:
        return []
    return [_a('media', f'{n} aluno(s) em risco de evasão', f"{dados.get('por_faltas', 0)} por faltas; {dados.get('por_propinas', 0)} por propinas",
               'crm', 'Ver no CRM')]


def alertas_pautas(user, escola):
    from apps.pautas.models import Pauta
    ano = getattr(escola, 'ano_letivo_ativo', None)
    qs = Pauta.objects.filter(escola=escola).exclude(status='FECHADA')
    if ano:
        qs = qs.filter(ano_letivo=ano)
    n = qs.count()
    return [_a('media', f'{n} pauta(s) por fechar', '', 'pautas', 'Ver pautas')] if n else []


def alertas_cargos_gestao(user, escola):
    from apps.atribuicoes.models import AtribuicaoCargo
    qs = AtribuicaoCargo.objects.filter(escola=escola, prazo__lt=datetime.date.today()).exclude(estado='CONCLUIDA')
    n = qs.count()
    return [_a('media', f'{n} actividade(s) de cargo com o prazo ultrapassado', '', 'atribuicoes-cargos', 'Ver actividades')] if n else []


def alertas_assinatura(user, escola):
    from apps.tenants.models import AssinaturaEscola
    ass = AssinaturaEscola.objects.filter(escola=escola).order_by('-data_fim').first()
    if not ass:
        return []
    dias = (ass.data_fim.date() - datetime.date.today()).days
    if dias < 0:
        return [_a('alta', 'A assinatura do sistema terminou', f'Há {-dias} dia(s).', 'assinatura-escola', 'Regularizar')]
    if dias <= 15:
        return [_a('media', f'A assinatura do sistema termina em {dias} dia(s)', '', 'assinatura-escola', 'Ver assinatura')]
    return []


def alertas_pagamentos_saas(user, escola):
    """Decisões do SuperAdmin sobre os comprovativos da assinatura que a escola submeteu.

    Rejeitado: alta prioridade, com o motivo, até a fatura ser paga ou existir novo comprovativo para ela.
    Confirmado: informativo durante 7 dias. Desaparecem sozinhos (não é preciso "dispensar").
    """
    from apps.tenants.models import SaasPagamento
    desde = timezone.now() - datetime.timedelta(days=14)
    decididos = (SaasPagamento.objects.select_related('fatura')
                 .filter(instituicao=escola, estado__in=('confirmado', 'rejeitado'), confirmado_em__gte=desde)
                 .order_by('-confirmado_em')[:6])
    destino = 'assinatura-escola' if user.role in DIRECCAO else None
    out = []
    for p in decididos:
        if p.estado == 'rejeitado':
            if p.fatura.estado == 'paga':
                continue
            if SaasPagamento.objects.filter(fatura=p.fatura, estado__in=('enviado', 'confirmado'), criado_em__gt=p.criado_em).exists():
                continue
            motivo = (p.motivo_rejeicao or 'sem motivo indicado')[:160]
            out.append(_a('alta', f'Comprovativo {p.referencia} rejeitado ({p.valor} MZN)', f'Motivo: {motivo}. Submeta um novo comprovativo.', destino, 'Ver assinatura'))
        elif (timezone.now() - p.confirmado_em).days < 7:
            out.append(_a('info', f'Pagamento {p.referencia} confirmado ({p.valor} MZN)', f'Fatura {p.fatura.numero_fatura}.', destino, 'Ver assinatura'))
    return out[:3]

def alertas_despesas(user, escola):
    from apps.pagamentos.models import TransacaoFinanceira
    n = TransacaoFinanceira.objects.filter(escola=escola, status_aprovacao='PENDENTE').count()
    if not n:
        return []
    texto = f'{n} movimento(s) a aguardar a aprovação do Director'
    return [_a('media' if user.role in DIRECCAO else 'info', texto, '', 'despesas', 'Ver movimentos')]


def alertas_propinas_escola(user, escola):
    from apps.pagamentos.models import Pagamento
    atraso = list(Pagamento.objects.filter(escola=escola, status__in=('PENDENTE', 'ATRASADO'), data_vencimento__lt=timezone.now()))
    if not atraso:
        return []
    valor = sum((p.valor - p.valor_pago for p in atraso), Decimal('0'))
    alunos = len({p.aluno_id for p in atraso})
    return [_a('media', f'{len(atraso)} propina(s) em atraso de {alunos} aluno(s)', f'{valor} MZN por cobrar', 'pagamentos', 'Ver propinas')]


# ---------------------------------------------------------------- para todos
def alertas_comunicados(user, escola):
    from apps.documentos.models import ComunicadoEscolar
    qs = ComunicadoEscolar.objects.filter(escola=escola, status='PUBLICADO', aprovado_pelo_director=True,
                                          data_publicacao__gte=timezone.now() - datetime.timedelta(days=7))
    alvos = cap.ALVO_POR_PERFIL.get(user.role)
    if alvos:
        qs = qs.filter(publico_alvo__in=alvos)
    itens = list(qs.order_by('-data_publicacao')[:3])
    if not itens:
        return []
    urgente = any(c.prioridade == 'URGENTE' for c in itens)
    return [_a('media' if urgente else 'info', f'{len(itens)} comunicado(s) recente(s)', '; '.join(c.titulo for c in itens), 'comunicados', 'Ler comunicados')]


def alertas_calendario(user, escola):
    from apps.documentos.models import CalendarioEscolar
    hoje = datetime.date.today()
    qs = CalendarioEscolar.objects.filter(escola=escola, status_aprovacao='APROVADO_DIRECTOR', data_inicio__gte=hoje,
                                          data_inicio__lte=hoje + datetime.timedelta(days=7)).order_by('data_inicio')
    itens = list(qs[:3])
    if not itens:
        return []
    return [_a('info', f'{len(itens)} evento(s) no calendário nos próximos 7 dias', '; '.join(f'{e.data_inicio:%d/%m} {e.titulo}' for e in itens),
               'aluno-calendario' if user.role in PROPRIO else 'calendario', 'Ver calendário')]


# (função, perfis; None = todos)
ALERTAS = [
    (alertas_familia, PROPRIO),
    (alertas_professor, {'PROFESSOR'}),
    (alertas_assinatura, DIRECCAO),
    (alertas_pagamentos_saas, DIRECCAO | {'DAP', 'CHEFE_SECRETARIA', 'SECRETARIA', 'FINANCEIRO'}),
    (alertas_transferencias, GESTAO),
    (alertas_crm, GESTAO),
    (alertas_risco, GESTAO),
    (alertas_pautas, DIRECCAO | {'DAP'}),
    (alertas_cargos_gestao, DIRECCAO | {'DAP'}),
    (alertas_despesas, DIRECCAO | {'FINANCEIRO'}),
    (alertas_propinas_escola, DIRECCAO | {'FINANCEIRO', 'CHEFE_SECRETARIA'}),
    (alertas_comunicados, None),
    (alertas_calendario, None),
]


def alertas_plataforma(user):
    """Super Admin sem escola em inspecção: o que merece atenção na plataforma."""
    from apps.tenants.models import SaasAssinatura, SaasFatura, SaasPagamento
    out = []
    por_validar = SaasPagamento.objects.filter(instituicao__eliminada_em__isnull=True, estado='enviado').count()
    if por_validar:
        out.append(_a('alta', f'{por_validar} comprovativo(s) de pagamento por validar', '', 'pagamentos-saas', 'Validar'))
    em_atraso = SaasFatura.objects.filter(instituicao__eliminada_em__isnull=True, estado='em_atraso').count()
    if em_atraso:
        out.append(_a('alta', f'{em_atraso} fatura(s) SaaS em atraso', '', 'pagamentos-saas', 'Ver faturas'))
    criticas = SaasAssinatura.objects.filter(instituicao__eliminada_em__isnull=True, estado__in=('restrita', 'suspensa')).count()
    if criticas:
        out.append(_a('media', f'{criticas} assinatura(s) restrita(s) ou suspensa(s)', '', 'saas', 'Ver escolas'))
    return out


def alertas_do_utilizador(user, escola):
    """Lista ordenada por urgência (e limitada); cada função só corre para os perfis a que se destina."""
    role = getattr(user, 'role', '')
    if role == 'SUPERADMIN' and escola is None:
        return sorted(alertas_plataforma(user), key=lambda a: ORDEM[a['nivel']])[:MAX_ALERTAS]
    out = []
    for func, perfis in ALERTAS:
        if perfis is None or role in perfis:
            out.extend(func(user, escola))
    out.sort(key=lambda a: ORDEM[a['nivel']])
    return out[:MAX_ALERTAS]
