"""
Registo de capacidades do Assistente (nível 0, custo zero, só leitura).

Cada capacidade responde a um tipo de pergunta sobre um módulo:
  - 'dados': lê registos reais (já limitados pela escola e pelo perfil); sem registos diz que não há;
  - 'regra': regras oficiais do MEC (docs/REGRAS_PEDAGOGICAS_MEC.md);
  - 'guia' : "como se faz" por módulo (guias.py).
Acrescentar um módulo = acrescentar uma entrada em CAPACIDADES (palavras-chave + função + perfis).
"""
import datetime
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from math import ceil
from typing import Callable, Optional

from django.db.models import Count, Q, Sum
from django.utils import timezone

from . import guias

GESTAO = {'SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP', 'CHEFE_SECRETARIA', 'SECRETARIA'}
PROPRIO = {'ALUNO', 'ENCARREGADO'}
DIRECCAO = {'SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA'}
TRIMESTRES = ['1_TRIMESTRE', '2_TRIMESTRE', '3_TRIMESTRE']
ROTULO_TRIM = {'1_TRIMESTRE': '1.º trimestre', '2_TRIMESTRE': '2.º trimestre', '3_TRIMESTRE': '3.º trimestre'}
DIAS = {1: 'segunda-feira', 2: 'terça-feira', 3: 'quarta-feira', 4: 'quinta-feira', 5: 'sexta-feira', 6: 'sábado'}
LIMITE_LISTA = 6


def normalizar(texto):
    t = unicodedata.normalize('NFKD', texto or '').encode('ascii', 'ignore').decode('ascii').lower()
    return ' ' + re.sub(r'[^a-z0-9 ]+', ' ', t).strip() + ' '


@dataclass
class Ctx:
    user: object
    escola: object
    pergunta: str
    texto: str
    pagina: Optional[str] = None
    aluno: object = None
    educandos: object = None
    modulos: object = None          # módulos do painel do perfil (as capacidades compostas só juntam o que o perfil pode ver)
    hoje: datetime.date = field(default_factory=datetime.date.today)

    @property
    def role(self):
        return getattr(self.user, 'role', '')

    @property
    def proprio(self):
        return self.role in PROPRIO

    @property
    def ano(self):
        return getattr(self.escola, 'ano_letivo_ativo', None)

    def classe_pedida(self):
        m = re.search(r'\b(\d{1,2})\s*a?\s*classe', self.texto)
        if m:
            return int(m.group(1))
        if self.aluno is not None and self.aluno.classe:
            m = re.search(r'\d+', self.aluno.classe)
            return int(m.group()) if m else None
        return None


@dataclass
class Capacidade:
    nome: str
    tipo: str                       # 'dados' | 'regra' | 'guia'
    chaves: list
    handler: Callable
    perfis: Optional[set] = None    # None = todos
    aluno: Optional[str] = None     # None | 'obrigatorio' | 'opcional'
    destino: Optional[str] = None
    rotulo: Optional[str] = None
    destino_proprio: Optional[str] = None
    peso: float = 1                 # multiplica os acertos de palavras-chave (frases específicas vencem as genéricas)
    alt: tuple = ()                 # módulos alternativos que também dão acesso (ex.: o professor vê 'minhas-atividades')
    universal: bool = False         # informação comum a todos os perfis da escola (calendário, comunicados)
    plataforma: bool = False        # dados da plataforma (só SuperAdmin, sem escola)
    exemplos: tuple = ()            # perguntas de exemplo (sugestões e ajuda por perfil)


# Quem pode ver dados de um aluno, por capacidade
ACESSO_ALUNO = {
    'faltas': {'proprio', 'gestao', 'professor'},
    'notas': {'proprio', 'gestao', 'professor'},
    'quanto_preciso': {'proprio', 'gestao', 'professor'},
    'propinas': {'proprio', 'gestao', 'financeiro'},
    'transferencias': {'gestao', 'financeiro'},
    'certificados': {'proprio', 'gestao'},
}


def _nome(a):
    """Nome completo do aluno (nome + apelido)."""
    return f'{a.nome} {a.apelido}'.strip() if getattr(a, 'apelido', None) else a.nome


def _res(texto, dados=None, destino=None, rotulo=None):
    return {'texto': texto, 'dados': dados, 'destino': destino, 'rotulo': rotulo}


def _data(d):
    return d.strftime('%d/%m/%Y')


def _lista(itens, limite=LIMITE_LISTA):
    itens = list(itens)
    extra = len(itens) - limite
    texto = ', '.join(itens[:limite])
    return texto + (f' e mais {extra}' if extra > 0 else '')


# ---------------------------------------------------------------- dados do aluno
def faltas_do_aluno(escola, aluno, ano):
    """(faltas efectivas, faltas injustificadas ainda por justificar) no ano lectivo."""
    from apps.alunos.models import PresencaAluno
    from apps.crm.views import _faltas_efectivas_por_aluno
    efectivas = _faltas_efectivas_por_aluno(escola, ano_letivo=ano, aluno_id=aluno.id).get(aluno.id, 0)
    regs = PresencaAluno.objects.filter(escola=escola, aluno=aluno, status='FALTA_INJUSTIFICADA')
    if ano:
        regs = regs.filter(turma__ano_letivo=ano)
    return efectivas, sum(max((r.aulas or 1) - (r.aulas_justificadas or 0), 0) for r in regs)


def h_faltas(ctx):
    escola, aluno, ano = ctx.escola, ctx.aluno, ctx.ano
    efectivas, injust = faltas_do_aluno(escola, aluno, ano)
    sufixo = f' no ano lectivo {ano}' if ano else ''
    if not efectivas:
        return _res(f'{_nome(aluno)} não tem faltas efectivas registadas{sufixo}.', {'faltas_efectivas': 0})
    return _res(f'{_nome(aluno)} tem {efectivas} falta(s) efectiva(s){sufixo}, das quais {injust} ainda por justificar.',
                {'faltas_efectivas': efectivas, 'por_justificar': injust})


def h_propinas(ctx):
    from apps.pagamentos.models import Pagamento
    escola, aluno = ctx.escola, ctx.aluno
    agora = timezone.now()
    abertos = Pagamento.objects.filter(escola=escola, aluno=aluno, status__in=('PENDENTE', 'ATRASADO'))
    atraso = [p for p in abertos if p.data_vencimento < agora]
    futuros = [p for p in abertos if p.data_vencimento >= agora]
    if not atraso and not futuros:
        return _res(f'{_nome(aluno)} não tem propinas pendentes registadas.', {'em_atraso': 0, 'a_vencer': 0})
    valor = sum((p.valor - p.valor_pago for p in atraso), Decimal('0'))
    meses = ', '.join(p.mes_referencia for p in sorted(atraso, key=lambda x: x.mes_referencia))
    partes = []
    if atraso:
        partes.append(f'{len(atraso)} propina(s) em atraso ({meses}), no valor de {valor} MZN')
    if futuros:
        partes.append(f'{len(futuros)} a vencer')
    return _res(f'{_nome(aluno)}: ' + '; '.join(partes) + '.',
                {'em_atraso': len(atraso), 'valor_em_atraso': str(valor), 'a_vencer': len(futuros)})


def _trimestres_visiveis(ctx):
    """Alunos/encarregados só veem os trimestres que a escola publicou; os outros perfis veem todos."""
    if not ctx.proprio:
        return list(TRIMESTRES), True
    pub, permitir, _modo, _info = ctx.escola.resolver_publicacao_notas()
    if not permitir or pub == 'NENHUM':
        return [], False
    return {'1_TRIMESTRE': TRIMESTRES[:1], '2_TRIMESTRE': TRIMESTRES[:2]}.get(pub, list(TRIMESTRES)), True


def _notas_por_disciplina(ctx, periodos):
    from apps.notas.models import Nota
    qs = Nota.objects.filter(escola=ctx.escola, aluno=ctx.aluno, periodo__in=periodos).select_related('disciplina')
    if ctx.ano:
        qs = qs.filter(turma__ano_letivo=ctx.ano)
    mapa = defaultdict(dict)
    for n in qs:
        if (n.media_final or 0) > 0:
            mapa[n.disciplina.nome][n.periodo] = n.media_final
    return mapa


def h_notas(ctx):
    periodos, permitido = _trimestres_visiveis(ctx)
    if not permitido:
        return _res('A visualização de notas está suspensa pela Direcção da escola neste momento.', {'publicado': False})
    mapa = _notas_por_disciplina(ctx, periodos)
    partes, dados = [], {}
    for p in periodos:
        itens = [(d, per[p]) for d, per in mapa.items() if p in per]
        if not itens:
            continue
        neg = sorted((d, m) for d, m in itens if m < 9.5)
        txt = f'{ROTULO_TRIM[p]}: {len(itens)} disciplina(s) avaliada(s), {len(neg)} negativa(s)'
        if neg:
            txt += ' (' + _lista([f'{d} {m:g}' for d, m in neg], 8) + ')'
        partes.append(txt)
        dados[p] = {'avaliadas': len(itens), 'negativas': len(neg)}
    if not partes:
        return _res(f'{_nome(ctx.aluno)} ainda não tem notas{" publicadas" if ctx.proprio else ""} registadas.', {})
    # pergunta sobre uma disciplina concreta ("notas de Matemática"): as médias dessa disciplina em cada trimestre
    pedida = [(d, per) for d, per in mapa.items() if normalizar(d).strip() and normalizar(d) in ctx.texto]
    if pedida:
        linhas = []
        for d, per in pedida:
            valores = [f'{ROTULO_TRIM[p]} {per[p]:g}' for p in periodos if p in per]
            mfd = ''
            if all(p in per for p in TRIMESTRES):
                mfd = f'; MFD {int(sum(per[p] for p in TRIMESTRES) / 3 + 0.5)}'
            linhas.append(f'{d}: ' + '; '.join(valores) + mfd)
        return _res(f'{_nome(ctx.aluno)} — ' + ' | '.join(linhas) + '.', dados)
    ultimo = next((p for p in reversed(periodos) if any(p in per for per in mapa.values())), None)
    detalhe = ''
    if ultimo:
        itens = sorted((d, per[ultimo]) for d, per in mapa.items() if ultimo in per)
        detalhe = f' Notas do {ROTULO_TRIM[ultimo]}: ' + _lista([f'{d} {m:g}' for d, m in itens], 12) + '.'
    return _res(f'{_nome(ctx.aluno)} — ' + '; '.join(partes) + '.' + detalhe, dados)


def h_quanto_preciso(ctx):
    periodos, permitido = _trimestres_visiveis(ctx)
    if not permitido:
        return _res('A visualização de notas está suspensa pela Direcção da escola neste momento.', {'publicado': False})
    if ctx.proprio and not {'1_TRIMESTRE', '2_TRIMESTRE'} <= set(periodos):
        return _res('A escola ainda não publicou o 1.º e o 2.º trimestre, por isso não consigo calcular o que falta.', {})
    mapa = _notas_por_disciplina(ctx, TRIMESTRES)
    precisa, garantidas, impossiveis = [], 0, []
    for disc, per in mapa.items():
        m1, m2 = per.get('1_TRIMESTRE'), per.get('2_TRIMESTRE')
        if not (m1 and m2) or per.get('3_TRIMESTRE'):
            continue
        # MFD = round((MT1+MT2+MT3)/3) >= 10  <=>  MT3 >= 28,5 - (MT1+MT2)  (MT inteiras)
        necessaria = ceil(28.5 - (m1 + m2))
        if necessaria <= 0:
            garantidas += 1
        elif necessaria > 20:
            impossiveis.append(disc)
        else:
            precisa.append((disc, necessaria))
    if not (precisa or garantidas or impossiveis):
        return _res('Não há disciplinas com MT1 e MT2 apuradas e a MT3 ainda por lançar.', {})
    precisa.sort(key=lambda x: -x[1])
    partes = []
    if precisa:
        partes.append('Para MFD ≥ 10 precisa de MT3 de pelo menos: ' + _lista([f'{d} {n}' for d, n in precisa], 8))
    if garantidas:
        partes.append(f'{garantidas} disciplina(s) já com a positiva garantida')
    if impossiveis:
        partes.append('não é possível chegar a 10 em: ' + _lista(impossiveis, 8))
    aviso = ' (MFD = média das 3 MT arredondada; a aprovação final também depende das regras da classe).'
    return _res(f'{_nome(ctx.aluno)}: ' + '; '.join(partes) + aviso,
                {'precisa': dict(precisa), 'garantidas': garantidas, 'impossiveis': impossiveis})


def h_transferencias(ctx):
    from apps.alunos.models import TransferenciaAnulacao
    qs = TransferenciaAnulacao.objects.filter(escola=ctx.escola)
    if ctx.aluno is not None:
        proc = list(qs.filter(aluno=ctx.aluno).order_by('-created_at')[:5])
        if not proc:
            return _res(f'{_nome(ctx.aluno)} não tem processos de transferência ou anulação.', {'processos': 0},
                        'transferencias', 'Abrir Transferências & Anulações')
        linhas = [f'{p.get_tipo_display()} ({p.get_status_display()}) a {_data(p.data_solicitacao)}' for p in proc]
        return _res(f'{_nome(ctx.aluno)}: ' + '; '.join(linhas) + '.', {'processos': len(proc)},
                    'transferencias', 'Abrir Transferências & Anulações')
    limite = ctx.hoje - datetime.timedelta(days=7)
    pend = qs.filter(status='PENDENTE')
    n_pend, n_atraso = pend.count(), pend.filter(data_solicitacao__lte=limite).count()
    aprovados = qs.filter(status='APROVADO', created_at__year=ctx.hoje.year).count()
    if not (n_pend or aprovados):
        return _res('Não há processos de transferência ou anulação pendentes nem aprovados este ano.', {'pendentes': 0},
                    'transferencias', 'Abrir Transferências & Anulações')
    return _res(f'Há {n_pend} processo(s) pendente(s), {n_atraso} há mais de 7 dias, e {aprovados} aprovado(s) este ano.',
                {'pendentes': n_pend, 'em_atraso': n_atraso, 'aprovados_ano': aprovados},
                'transferencias', 'Abrir Transferências & Anulações')


def h_certificados(ctx):
    from apps.certificados.models import Certificado
    qs = Certificado.objects.filter(escola=ctx.escola)
    if ctx.aluno is not None:
        n = qs.filter(aluno=ctx.aluno).count()
        ultimo = qs.filter(aluno=ctx.aluno).order_by('-emitido_em').first()
        if not n:
            return _res(f'{_nome(ctx.aluno)} não tem certificados emitidos.', {'emitidos': 0})
        return _res(f'{_nome(ctx.aluno)} tem {n} certificado(s) emitido(s); o último a {_data(ultimo.emitido_em.date())}.', {'emitidos': n})
    n = qs.filter(emitido_em__year=ctx.hoje.year).count()
    return _res(f'Foram emitidos {n} certificado(s) este ano.' if n else 'Ainda não foram emitidos certificados este ano.', {'emitidos_ano': n})


# ---------------------------------------------------------------- dados da escola
def h_alunos_resumo(ctx):
    from apps.alunos.models import Aluno
    qs = Aluno.objects.filter(escola=ctx.escola)
    por_estado = dict(qs.values_list('status').annotate(n=Count('id')))
    total = sum(por_estado.values())
    if not total:
        return _res('Ainda não há alunos registados nesta escola.', {'total': 0})
    activos = qs.filter(status='ATIVO')
    h, m = activos.filter(genero__iexact='M').count(), activos.filter(genero__iexact='F').count()
    outros = ', '.join(f'{n} {s.lower()}' for s, n in por_estado.items() if s != 'ATIVO' and n)
    return _res(f'A escola tem {por_estado.get("ATIVO", 0)} aluno(s) activo(s) ({h} H / {m} M)' + (f' e ainda {outros}' if outros else '') + '.',
                {'por_estado': por_estado, 'activos_homens': h, 'activos_mulheres': m})


def h_turmas(ctx):
    from apps.turmas.models import Turma
    qs = Turma.objects.filter(escola=ctx.escola)
    if ctx.ano:
        qs = qs.filter(ano_letivo=ctx.ano)
    n_classe = ctx.classe_pedida()
    if n_classe:
        qs = qs.filter(grau_ano__regex=rf'^{n_classe}[^0-9]')
    qs = qs.annotate(n_alunos=Count('alunos', filter=Q(alunos__status='ATIVO')))
    turmas = list(qs)
    if not turmas:
        return _res('Não há turmas registadas' + (f' para a {n_classe}.ª classe' if n_classe else '') + '.', {'turmas': 0})
    lotadas = [t for t in turmas if t.n_alunos >= t.capacidade_maxima]
    vagas = sum(max(t.capacidade_maxima - t.n_alunos, 0) for t in turmas)
    sem_dt = sum(1 for t in turmas if not t.director_turma_id)
    txt = (f'{len(turmas)} turma(s)' + (f' da {n_classe}.ª classe' if n_classe else '') +
           f': {sum(t.n_alunos for t in turmas)} aluno(s) activo(s) e {vagas} vaga(s) livre(s)')
    txt += f'; {len(lotadas)} lotada(s)' + (' (' + _lista([f'{t.grau_ano} {t.nome}' for t in lotadas], 5) + ')' if lotadas else '')
    txt += f'; {sem_dt} sem Director de Turma.'
    return _res(txt, {'turmas': len(turmas), 'vagas': vagas, 'lotadas': len(lotadas), 'sem_director_turma': sem_dt},
                'turmas', 'Abrir Turmas')


_DIAS_NOMES = {' segunda': 1, ' terca': 2, ' quarta': 3, ' quinta': 4, ' sexta': 5, ' sabado': 6}


def _turma_pedida(ctx):
    """Turma escrita na pergunta: "7.ª classe turma A" / "7ª A" (só da escola e do ano lectivo activo)."""
    from apps.turmas.models import Turma
    m = re.search(r'\b(\d{1,2})\s*a?\s*classe\s+(?:turma\s+)?([a-z0-9]{1,3})\b', ctx.texto) or re.search(r'\b(\d{1,2})\s*a\s+([a-z])\b', ctx.texto)
    if not m:
        return None
    qs = Turma.objects.filter(escola=ctx.escola, grau_ano__regex=rf'^{int(m.group(1))}[^0-9]', nome__iexact=m.group(2))
    if ctx.ano:
        qs = qs.filter(ano_letivo=ctx.ano)
    return qs.first()


def h_horario(ctx):
    from apps.alunos.models import Aluno
    from apps.turmas.models import HorarioEscolar
    dia = ctx.hoje.isoweekday() + (1 if ' amanha ' in ctx.texto else 0)
    dia = 1 if dia > 7 else dia
    for nome_dia_pedido, n_dia in _DIAS_NOMES.items():      # "horário de segunda-feira"
        if nome_dia_pedido in ctx.texto:
            dia = n_dia
    if dia == 7:
        return _res('No domingo não há aulas no horário lectivo.', {})
    qs = HorarioEscolar.objects.filter(escola=ctx.escola, dia_semana=dia, status_aprovacao='APROVADO').select_related('disciplina', 'turma')
    if ctx.ano:
        qs = qs.filter(turma__ano_letivo=ctx.ano)
    if ctx.proprio:
        aluno = ctx.aluno
        if not aluno or not aluno.turma_id:
            return _res('Ainda não tem turma atribuída, por isso não há horário para mostrar.', {})
        qs, quem = qs.filter(turma=aluno.turma), False
    elif ctx.role == 'PROFESSOR':
        qs, quem = qs.filter(professor_id=getattr(ctx.user, 'professor_id', None)), True
    else:
        turma = _turma_pedida(ctx)
        if not turma:
            return _res('Indique a turma (por exemplo "horário da 7.ª classe turma A") ou abra a página Horários e escolha a turma.', {}, 'horarios', 'Abrir Horários')
        qs, quem = qs.filter(turma=turma), False
    aulas = list(qs.order_by('hora_inicio'))
    nome_dia = DIAS.get(dia, '')
    if not aulas:
        return _res(f'Não há aulas registadas no horário para {nome_dia}.', {'aulas': 0}, 'horarios', 'Abrir Horários')
    linhas = [f'{a.hora_inicio:%H:%M}–{a.hora_fim:%H:%M} {a.disciplina.nome}' + (f' ({a.turma.nome})' if quem else '') +
              (f' sala {a.sala}' if a.sala else '') for a in aulas]
    return _res(f'Horário de {nome_dia}: ' + '; '.join(linhas[:10]) + '.', {'aulas': len(aulas)}, 'horarios', 'Abrir Horários')


def h_calendario(ctx):
    from apps.documentos.models import CalendarioEscolar
    qs = (CalendarioEscolar.objects.filter(escola=ctx.escola, status_aprovacao='APROVADO_DIRECTOR')
          .filter(Q(data_inicio__gte=ctx.hoje) | Q(data_fim__gte=ctx.hoje)).order_by('data_inicio'))[:5]
    eventos = list(qs)
    if not eventos:
        return _res('Não há eventos futuros no calendário escolar.', {'eventos': 0}, 'calendario', 'Abrir o Calendário Escolar')
    linhas = [f'{_data(e.data_inicio)}' + (f' a {_data(e.data_fim)}' if e.data_fim and e.data_fim != e.data_inicio else '') + f' — {e.titulo}'
              for e in eventos]
    return _res('Próximos eventos: ' + '; '.join(linhas) + '.', {'eventos': len(eventos)}, 'calendario', 'Abrir o Calendário Escolar')


def h_exames_calendario(ctx):
    from apps.alunos.models import Aluno
    from apps.notas.models import CalendarioExame
    qs = CalendarioExame.objects.filter(escola=ctx.escola, data__gte=ctx.hoje)
    if ctx.ano:
        qs = qs.filter(ano_letivo=ctx.ano)
    if ctx.proprio:
        aluno = ctx.aluno
        if aluno and aluno.classe:
            qs = qs.filter(classe__iexact=aluno.classe)
    itens = list(qs.order_by('data', 'hora_inicio')[:60])
    mencionados = [i for i in itens if normalizar(i.disciplina).strip() and normalizar(i.disciplina) in ctx.texto]
    itens = (mencionados or itens)[:LIMITE_LISTA]
    if not itens:
        return _res('Não há exames agendados a partir de hoje.', {'exames': 0}, 'calendario-exames', 'Abrir o Calendário dos Exames')
    linhas = [f'{_data(i.data)} {i.hora_inicio:%H:%M} — {i.classe}, {i.disciplina} ({i.epoca}.ª época)' for i in itens]
    return _res('Próximos exames: ' + '; '.join(linhas) + '.', {'exames': len(itens)}, 'calendario-exames', 'Abrir o Calendário dos Exames')


def h_crm(ctx):
    from apps.crm.models import Atendimento
    qs = Atendimento.objects.filter(escola=ctx.escola).exclude(estado='RESOLVIDO')
    abertos = qs.filter(estado='ABERTO').count()
    em_curso = qs.filter(estado='EM_CURSO').count()
    if not (abertos or em_curso):
        return _res('Não há atendimentos por resolver.', {'abertos': 0, 'em_curso': 0}, 'crm', 'Abrir o CRM Escolar')
    antigos = qs.filter(created_at__lte=timezone.now() - datetime.timedelta(days=7)).count()
    altos = qs.filter(prioridade='ALTA').count()
    return _res(f'Há {abertos} atendimento(s) aberto(s) e {em_curso} em curso; {antigos} com mais de 7 dias e {altos} de prioridade alta.',
                {'abertos': abertos, 'em_curso': em_curso, 'antigos': antigos, 'prioridade_alta': altos}, 'crm', 'Abrir o CRM Escolar')


def h_risco(ctx):
    from apps.alunos.models import Aluno
    from apps.crm.views import _faltas_efectivas_por_aluno, _propinas_em_atraso
    ativos = set(Aluno.objects.filter(escola=ctx.escola, status='ATIVO').values_list('id', flat=True))
    faltas = _faltas_efectivas_por_aluno(ctx.escola, ano_letivo=ctx.ano)
    com_faltas = {a for a, n in faltas.items() if n >= 10 and a in ativos}
    atrasos = defaultdict(int)
    for p in _propinas_em_atraso(ctx.escola):
        atrasos[p.aluno_id] += 1
    com_propinas = {a for a, n in atrasos.items() if n >= 2 and a in ativos}
    total = com_faltas | com_propinas
    if not total:
        return _res('Nenhum aluno activo atinge os limites de risco (10 faltas efectivas ou 2 propinas em atraso).', {'em_risco': 0}, 'crm', 'Abrir o CRM Escolar')
    return _res(f'{len(total)} aluno(s) em risco: {len(com_faltas)} com 10 ou mais faltas efectivas e {len(com_propinas)} com 2 ou mais propinas em atraso. '
                'Veja a lista, por classe e turma, no CRM Escolar.', {'em_risco': len(total), 'por_faltas': len(com_faltas), 'por_propinas': len(com_propinas)},
                'crm', 'Abrir o CRM Escolar')


def h_assinatura(ctx):
    from apps.tenants.models import AssinaturaEscola
    ass = AssinaturaEscola.objects.filter(escola=ctx.escola).select_related('plano').order_by('-data_fim').first()
    if not ass:
        return _res('Não há assinatura registada para esta escola.', {}, 'assinatura-escola', 'Abrir Assinatura do Sistema')
    dias = (ass.data_fim.date() - ctx.hoje).days
    prazo = f'termina em {_data(ass.data_fim)} (faltam {dias} dia(s))' if dias >= 0 else f'terminou a {_data(ass.data_fim)} (há {-dias} dia(s))'
    return _res(f'A assinatura ({ass.plano.nome}) está {ass.status.lower()} e {prazo}.', {'status': ass.status, 'dias': dias},
                'assinatura-escola', 'Abrir Assinatura do Sistema')


def h_caixa(ctx):
    from apps.pagamentos.models import Pagamento, TransacaoFinanceira
    h = ctx.hoje
    tr = TransacaoFinanceira.objects.filter(escola=ctx.escola, data__year=h.year, data__month=h.month, status_aprovacao='APROVADO_DIRECTOR')
    receitas = tr.filter(tipo='RECEITA').aggregate(s=Sum('valor'))['s'] or Decimal('0')
    despesas = tr.filter(tipo='DESPESA').aggregate(s=Sum('valor'))['s'] or Decimal('0')
    propinas = (Pagamento.objects.filter(escola=ctx.escola, status='PAGO', data_pagamento__year=h.year, data_pagamento__month=h.month)
                .aggregate(s=Sum('valor_pago'))['s'] or Decimal('0'))
    pend = TransacaoFinanceira.objects.filter(escola=ctx.escola, status_aprovacao='PENDENTE').count()
    if not (receitas or despesas or propinas or pend):
        return _res('Ainda não há movimentos aprovados neste mês.', {}, 'despesas', 'Abrir Receitas & Despesas')
    txt = (f'Neste mês (movimentos aprovados): receitas {receitas:.2f} MZN, despesas {despesas:.2f} MZN, saldo {receitas - despesas:.2f} MZN; '
           f'propinas recebidas {propinas:.2f} MZN.')
    if pend:
        txt += f' Há {pend} movimento(s) a aguardar a aprovação do Director.'
    return _res(txt, {'receitas': str(receitas), 'despesas': str(despesas), 'propinas': str(propinas), 'pendentes_aprovacao': pend},
                'despesas', 'Abrir Receitas & Despesas')


def h_plano_curricular(ctx):
    from apps.disciplinas.models import Disciplina
    n = ctx.classe_pedida()
    if not n:
        return _res('Indique a classe, por exemplo "disciplinas da 11.ª classe".', {}, 'plano-curricular', 'Abrir o Plano Curricular')
    qs = Disciplina.objects.filter(escola=ctx.escola, classe__regex=rf'^{n}[^0-9]')
    if ctx.ano:
        qs = qs.filter(ano_letivo=ctx.ano)
    por_area = defaultdict(list)
    for d in qs.order_by('area', 'nome'):
        por_area[d.area or 'Geral'].append(f'{d.nome} ({d.carga_horaria}h)' if d.carga_horaria else d.nome)
    if not por_area:
        return _res(f'Não há disciplinas registadas para a {n}.ª classe no Plano Curricular.', {'disciplinas': 0}, 'plano-curricular', 'Abrir o Plano Curricular')
    blocos = [f'{a}: ' + _lista(ds, 12) for a, ds in list(por_area.items())[:3]]
    extra = len(por_area) - 3
    texto = f'{n}.ª classe — ' + ' | '.join(blocos) + (f' | e mais {extra} área(s)' if extra > 0 else '') + '.'
    return _res(texto, {'areas': len(por_area), 'disciplinas': sum(len(v) for v in por_area.values())}, 'plano-curricular', 'Abrir o Plano Curricular')


def h_material(ctx):
    from apps.material_escolar.models import MaterialEscolar
    n = ctx.classe_pedida()
    qs = MaterialEscolar.objects.filter(escola=ctx.escola)
    if n:
        qs = qs.filter(disciplina__classe__regex=rf'^{n}[^0-9]')
    total = qs.count()
    if not total:
        return _res('Ainda não há material escolar publicado' + (f' para a {n}.ª classe.' if n else '.'), {'materiais': 0},
                    'material-escolar', 'Abrir o Material Escolar')
    titulos = list(qs.order_by('-created_at').values_list('titulo', flat=True)[:LIMITE_LISTA])
    return _res(f'Há {total} material(is)' + (f' para a {n}.ª classe' if n else '') + ': ' + _lista(titulos) + '.', {'materiais': total},
                'material-escolar', 'Abrir o Material Escolar')


def h_cargos(ctx):
    from apps.atribuicoes.models import AtribuicaoCargo
    qs = AtribuicaoCargo.objects.filter(escola=ctx.escola).exclude(estado='CONCLUIDA')
    if ctx.ano:
        qs = qs.filter(ano_letivo=ctx.ano)
    if ctx.role == 'PROFESSOR':
        qs = qs.filter(professor_id=getattr(ctx.user, 'professor_id', None))
        destino, rotulo = 'minhas-atividades', 'Abrir As Minhas Actividades'
    else:
        destino, rotulo = 'atribuicoes-cargos', 'Abrir Actividades dos Cargos'
    total = qs.count()
    if not total:
        return _res('Não há actividades de cargo por concluir.', {'por_concluir': 0}, destino, rotulo)
    atrasadas = qs.filter(prazo__lt=ctx.hoje).count()
    proximas = list(qs.filter(prazo__gte=ctx.hoje).order_by('prazo')[:3])
    txt = f'Há {total} actividade(s) de cargo por concluir, {atrasadas} com o prazo ultrapassado.'
    if proximas:
        txt += ' Próximas: ' + '; '.join(f'{a.titulo} ({_data(a.prazo)})' for a in proximas) + '.'
    return _res(txt, {'por_concluir': total, 'em_atraso': atrasadas}, destino, rotulo)


def h_pautas(ctx):
    from apps.pautas.models import Pauta
    qs = Pauta.objects.filter(escola=ctx.escola).select_related('turma')
    if ctx.ano:
        qs = qs.filter(ano_letivo=ctx.ano)
    if ctx.role == 'PROFESSOR':
        return _res('As pautas gerais são geridas pelo Director de Turma, pelo DAP e pela Direcção; consulte-as em Pautas & Actas.', {},
                    'pautas', 'Abrir Pautas & Actas')
    contagem = dict(qs.values_list('status').annotate(n=Count('id')))
    if not contagem:
        return _res('Ainda não há pautas registadas para o ano lectivo.', {'pautas': 0}, 'pautas', 'Abrir Pautas & Actas')
    abertas = [f'{p.turma.nome}' for p in qs.exclude(status='FECHADA')[:50]]
    txt = (f'Pautas do ano lectivo: {contagem.get("FECHADA", 0)} fechada(s), {contagem.get("EM_CONSOLIDACAO", 0)} em consolidação '
           f'e {contagem.get("ABERTA", 0)} aberta(s).')
    if abertas:
        txt += ' Por fechar: ' + _lista(abertas, 5) + '.'
    return _res(txt, contagem, 'pautas', 'Abrir Pautas & Actas')


ALVO_POR_PERFIL = {'ALUNO': ['TODOS', 'ALUNOS'], 'ENCARREGADO': ['TODOS', 'ENCARREGADOS'], 'PROFESSOR': ['TODOS', 'PROFESSORES'],
                   'SECRETARIA': ['TODOS', 'SECRETARIA'], 'CHEFE_SECRETARIA': ['TODOS', 'SECRETARIA']}


def h_comunicados(ctx):
    from apps.documentos.models import ComunicadoEscolar
    qs = ComunicadoEscolar.objects.filter(escola=ctx.escola, status='PUBLICADO', aprovado_pelo_director=True)
    alvos = ALVO_POR_PERFIL.get(ctx.role)
    if alvos:
        qs = qs.filter(publico_alvo__in=alvos)
    itens = list(qs.order_by('-data_publicacao')[:3])
    if not itens:
        return _res('Não há comunicados publicados para si.', {'comunicados': 0}, 'comunicados', 'Abrir Comunicados')
    linhas = [f'{_data(c.data_publicacao.date())} — {c.titulo}' for c in itens]
    return _res('Últimos comunicados: ' + '; '.join(linhas) + '.', {'comunicados': len(itens)}, 'comunicados', 'Abrir Comunicados')


# ---------------------------------------------------------------- regras do MEC
REGRAS = {
    'faq_mt': (' mt ', ' media trimestral', ' trimestral '),
    'faq_mfd': (' mfd ', ' media final', ' media anual'),
    'faq_mac': (' mac ', ' acs ', ' avaliacao continua', ' avaliacoes continuas'),
    'faq_exames': (' exame', ' epoca', ' nota minima'),
    'faq_escala': (' escala', ' excelente', ' suficiente', ' qualitativ', ' muito bom'),
    'faq_siglas': (' sigla', ' anotacao', ' ppf ', ' vt '),
    'aula_dupla': (' aula dupla', ' dupla '),
}
TEXTO_REGRA = {
    'faq_mt': ('A Média Trimestral (MT) combina com peso 2 a média das avaliações contínuas (MAC) e com peso 1 a Avaliação Trimestral (AT): '
               'MT = (2 × MAC + AT) / 3, arredondada ao inteiro mais próximo (9,5 → 10; 9,49 → 9). Só é apurada com pelo menos duas avaliações '
               'contínuas válidas (1.ª e 2.ª ACS) e a AT realizada; caso contrário a disciplina fica Pendente.'),
    'faq_mfd': ('A Média Final da Disciplina (MFD) é a média aritmética das três médias trimestrais, arredondada ao inteiro mais próximo: '
                'MFD = (MT1 + MT2 + MT3) / 3. Notas na escala de 0 a 20; abaixo de 10 é negativa.'),
    'faq_mac': ('A MAC é a média aritmética simples das avaliações contínuas efectivamente realizadas (1.ª e 2.ª ACS obrigatórias; 3.ª ACS, MAP e MAS opcionais), '
                'arredondada a uma casa decimal. Testes opcionais não realizados não baixam a média.'),
    'faq_exames': ('Por padrão do MEC têm exame a 10.ª e a 12.ª classes, mas cada escola pode definir que classes têm exame. Nas disciplinas com exame: '
                   'NF = (M. Frequência × peso freq. + Nota de exame × peso exame) / 100 (padrão 50% / 50%). Se a nota da 1.ª época for inferior à nota mínima '
                   '(padrão 10), o aluno tem direito à 2.ª época, cuja nota passa a contar.'),
    'faq_escala': ('Escala qualitativa: 18,5 a 20 = Excelente (E); 16,5 a 18,4 = Muito Bom (MB); 13,5 a 16,4 = Bom (B); 9,5 a 13,4 = Suficiente (S, positiva); '
                   '0 a 9,4 = Não Suficiente (NS, negativa, a vermelho).'),
    'faq_siglas': ('Siglas de anotação: D (Dispensado), T (Transferido), VT (Veio Transferido), F (Faleceu), AM (Anulou a Matrícula), '
                   'PPF (Perdeu por Faltas), PDF (Perdeu por Disciplina).'),
    'aula_dupla': ('Numa aula dupla, cada ausência conta como 2 faltas; numa aula simples conta 1. A secretaria/direcção pode justificar faltas por quantidade: '
                   'as faltas justificadas reduzem as faltas efectivas do aluno.'),
}
APROVACAO_GERAL = ('Da 7.ª à 11.ª classe o aluno só é aprovado se tiver MFD ≥ 10 em todas as disciplinas (zero negativas); '
                   'uma única negativa determina a reprovação.')
APROVACAO_12 = ('Na 12.ª classe o aluno é aprovado se a média geral anual for ≥ 9,5, tiver no máximo 2 disciplinas negativas e nenhuma negativa '
                'inferior a 8 valores (notas 7, 6 ou 5 reprovam, mesmo com média alta).')


def h_aprovacao(ctx):
    if re.search(r'\b(12|doze)\b', ctx.texto):
        return _res(APROVACAO_12)
    return _res(APROVACAO_GERAL + ' ' + APROVACAO_12)


def _regra(nome):
    return lambda ctx: _res(TEXTO_REGRA[nome])


def _guia(g):
    return lambda ctx: _res(g['texto'], None, g.get('destino'), g.get('rotulo'))


# ---------------------------------------------------------------- registo
CAPACIDADES = [
    # dados do aluno
    Capacidade('faltas', 'dados', [' falta', ' faltas', ' faltou', ' assiduidade', ' ausencia', ' presenca'], h_faltas, aluno='obrigatorio',
               destino='presencas', rotulo='Abrir Presenças dos Alunos', destino_proprio='aluno-faltas'),
    Capacidade('propinas', 'dados', [' propina', ' mensalidade', ' pagamento', ' pagar', ' divida', ' em atraso', ' atrasad', ' devo', ' quanto devo', ' tenho dividas', ' estou em divida'], h_propinas,
               aluno='obrigatorio', destino='pagamentos', rotulo='Abrir Propinas & Mensalidades', destino_proprio='aluno-pagamentos'),
    Capacidade('notas', 'dados', [' nota', ' notas', ' media', ' medias', ' negativa', ' negativas', ' classificacao', ' boletim', ' resultados'], h_notas,
               aluno='obrigatorio', destino='caderneta', rotulo='Abrir a Caderneta', destino_proprio='aluno-notas'),
    Capacidade('quanto_preciso', 'dados', [' quanto preciso', ' preciso para passar', ' para passar', ' quanto falta para', ' minimo para', ' esta a passar', ' estou a passar', ' vai passar', ' vou passar', ' consegue passar', ' consigo passar', ' vai reprovar', ' vou reprovar'], h_quanto_preciso,
               aluno='obrigatorio', destino='caderneta', rotulo='Abrir a Caderneta', destino_proprio='aluno-notas', peso=1.5),
    Capacidade('transferencias', 'dados', [' transferencia', ' transferencias', ' anulacao', ' processo de transferencia', ' em que estado', ' em que fase',
                                           ' estado do processo', ' pendentes'], h_transferencias,
               perfis=GESTAO | {'FINANCEIRO'}, aluno='opcional', destino='transferencias', rotulo='Abrir Transferências & Anulações'),
    Capacidade('certificados', 'dados', [' certificado', ' certificados', ' declaracao emitida', ' emitidos'], h_certificados,
               perfis=GESTAO, aluno='opcional', destino='certificados', rotulo='Abrir Certificados & Declarações', destino_proprio='aluno-perfil'),
    # dados da escola
    Capacidade('alunos_resumo', 'dados', [' quantos alunos', ' total de alunos', ' alunos matriculados', ' numero de alunos', ' alunos activos', ' alunos ativos'],
               h_alunos_resumo, perfis=GESTAO | {'FINANCEIRO'}, destino='alunos', rotulo='Abrir Alunos & Matrículas'),
    Capacidade('turmas', 'dados', [' turmas', ' vagas', ' lotada', ' lotadas', ' capacidade', ' sem director de turma', ' sem diretor de turma'], h_turmas,
               perfis=GESTAO | {'PROFESSOR'}, destino='turmas', rotulo='Abrir Turmas'),
    Capacidade('horario', 'dados', [' horario', ' aulas hoje', ' aulas amanha', ' tenho aula', ' que aula'], h_horario, aluno='proprio',
               destino='horarios', rotulo='Abrir Horários', peso=2),
    Capacidade('calendario', 'dados', [' calendario', ' prazo', ' prazos', ' feriado', ' proximo evento', ' proximos eventos', ' quando termina', ' quando comeca', ' datas', ' proximo teste', ' proximos testes', ' quando e o teste', ' quando sao os testes', ' reuniao', ' reunioes', ' ferias'],
               h_calendario, destino='calendario', rotulo='Abrir o Calendário Escolar', destino_proprio='aluno-calendario'),
    Capacidade('exames_calendario', 'dados', [' quando e o exame', ' quando sao os exames', ' quando ha exame', ' quando e a prova', ' data do exame', ' datas dos exames',
                                              ' proximo exame', ' proximos exames', ' calendario de exame', ' calendario dos exames', ' ha exame', ' exames este mes', ' exames esta semana', ' exame amanha', ' exame hoje', ' exames hoje'], h_exames_calendario,
               aluno='proprio', destino='calendario-exames', rotulo='Abrir o Calendário dos Exames', destino_proprio='aluno-calendario', peso=2),
    Capacidade('crm', 'dados', [' atendimento', ' atendimentos', ' reclamacao', ' reclamacoes', ' pedidos abertos', ' pedidos por resolver'], h_crm,
               perfis=GESTAO, destino='crm', rotulo='Abrir o CRM Escolar'),
    Capacidade('risco', 'dados', [' em risco', ' risco de evasao', ' evasao', ' alunos em risco'], h_risco,
               perfis=GESTAO, destino='crm', rotulo='Abrir o CRM Escolar', peso=2),
    Capacidade('assinatura', 'dados', [' assinatura', ' subscricao', ' plano contratado', ' expira', ' termina a assinatura', ' quando termina a assinatura'], h_assinatura,
               perfis=DIRECCAO, destino='assinatura-escola', rotulo='Abrir Assinatura do Sistema'),
    Capacidade('caixa', 'dados', [' caixa', ' saldo', ' receitas', ' despesas', ' quanto recebemos', ' faturacao', ' adimplencia', ' tesouraria'], h_caixa,
               perfis=DIRECCAO | {'FINANCEIRO'}, destino='despesas', rotulo='Abrir Receitas & Despesas'),
    Capacidade('plano_curricular', 'dados', [' disciplinas', ' que disciplinas', ' carga horaria', ' materias', ' grelha curricular'], h_plano_curricular,
               destino='plano-curricular', rotulo='Abrir o Plano Curricular'),
    Capacidade('material', 'dados', [' material escolar', ' material didatico', ' manuais', ' livros', ' fichas didaticas', ' material', ' materiais'], h_material,
               destino='material-escolar', rotulo='Abrir o Material Escolar'),
    Capacidade('cargos', 'dados', [' cargo', ' cargos', ' actividades', ' atividades', ' tarefas'], h_cargos,
               perfis=GESTAO | {'PROFESSOR'}, destino='atribuicoes-cargos', rotulo='Abrir Actividades dos Cargos'),
    Capacidade('pautas', 'dados', [' pauta', ' pautas', ' acta', ' actas', ' pautas fechadas', ' por fechar'], h_pautas,
               perfis=GESTAO | {'PROFESSOR'}, destino='pautas', rotulo='Abrir Pautas & Actas'),
    Capacidade('comunicados', 'dados', [' comunicado', ' comunicados', ' circular', ' circulares', ' avisos', ' novidades'], h_comunicados,
               destino='comunicados', rotulo='Abrir Comunicados'),
    # regras do MEC
    *[Capacidade(n, 'regra', list(ch), _regra(n)) for n, ch in REGRAS.items()],
    Capacidade('faq_aprovacao', 'regra', [' aprov', ' reprov', ' transit', ' passar de classe', ' retid', ' regras de aprovacao', ' regras para passar', ' regra para passar', ' condicoes para passar'], h_aprovacao),
    # guias por módulo
    *[Capacidade('guia_' + g['id'], 'guia', g['chaves'], _guia(g), destino=g.get('destino'), rotulo=g.get('rotulo')) for g in guias.GUIAS],
]

# Ajustes de segurança e de apresentação por capacidade (a regra geral está em `permitido`).
_AJUSTES = {
    'calendario': dict(universal=True),
    'comunicados': dict(universal=True),
    'certificados': dict(perfis=None),                       # aluno/encarregado (o seu) e gestão; o módulo decide quem
    'turmas': dict(perfis=GESTAO),
    'exames_calendario': dict(alt=('exames',)),
    'cargos': dict(alt=('minhas-atividades',)),
    'plano_curricular': dict(destino_proprio='aluno-notas', alt=('caderneta',)),
}
_GUIA_PERFIS = {
    'pedir_documentos': PROPRIO,
    'matricula': GESTAO, 'turmas': DIRECCAO | {'DAP'}, 'alocacao_docente': DIRECCAO | {'DAP'}, 'comunicados': GESTAO | {'FINANCEIRO'},
    'material': GESTAO | {'PROFESSOR'}, 'registar_presencas': DIRECCAO | {'DAP', 'PROFESSOR'}, 'horarios': DIRECCAO | {'DAP'},
    'calendario_guia': DIRECCAO | {'DAP'},
}
_GUIA_ALT = {'cargos_guia': ('atribuicoes-cargos',), 'juris': ('exames',)}
_GUIA_DESTINO_PROPRIO = {'justificar_falta': 'aluno-faltas'}
_EXEMPLOS = {
    'faltas': 'Quantas faltas tem o aluno?', 'propinas': 'Há propinas em atraso?', 'notas': 'Quais as notas do aluno?',
    'quanto_preciso': 'Quanto preciso para passar?', 'transferencias': 'Há transferências pendentes?', 'certificados': 'Quantos certificados foram emitidos?',
    'alunos_resumo': 'Quantos alunos temos?', 'turmas': 'Que turmas estão lotadas?', 'horario': 'Que aulas tenho hoje?',
    'calendario': 'Quais os próximos eventos?', 'exames_calendario': 'Quando são os exames?', 'crm': 'Há atendimentos abertos?',
    'risco': 'Há alunos em risco por faltas?', 'assinatura': 'Quando termina a assinatura?', 'caixa': 'Qual o saldo de caixa deste mês?',
    'plano_curricular': 'Que disciplinas tem a 11.ª classe?', 'material': 'Que material escolar existe?', 'cargos': 'Quais as actividades de cargo por concluir?',
    'pautas': 'Que pautas estão por fechar?', 'comunicados': 'Quais os últimos comunicados?', 'faq_mt': 'Como se calcula a média trimestral (MT)?',
    'faq_mfd': 'Como se calcula a MFD?', 'faq_mac': 'O que é a MAC?', 'faq_exames': 'Qual a nota mínima do exame?', 'faq_escala': 'Qual a escala qualitativa?',
    'faq_siglas': 'O que significam as siglas PPF e VT?', 'aula_dupla': 'Como funcionam as faltas em aula dupla?', 'faq_aprovacao': 'Quais são as regras de aprovação?',
    'guia_matricula': 'Como faço uma matrícula?', 'guia_turmas': 'Como crio turmas em lote?', 'guia_plano_curricular': 'Como funciona o plano curricular?',
    'guia_alocacao_docente': 'Como atribuo disciplinas a um professor?', 'guia_lancar_notas': 'Como lanço as notas?', 'guia_desbloqueio': 'Como desbloqueio um trimestre?',
    'guia_pautas': 'Como emito a pauta e a acta?', 'guia_exames': 'Como lanço as notas de exame?', 'guia_juris': 'Onde vejo os júris dos exames?',
    'guia_estatistica': 'Como vejo a estatística de aproveitamento?', 'guia_certificados': 'Como emito um certificado?', 'guia_pagar_propina': 'Como pago a propina?',
    'guia_cobrar_propina': 'Como gero as cobranças?', 'guia_despesas': 'Como registo e aprovo uma despesa?', 'guia_impressao': 'Como imprimo um boletim?',
    'guia_portal_aluno': 'O que posso ver no portal do aluno?', 'guia_senhas': 'Como redefino uma senha?', 'guia_auditoria': 'Como vejo quem alterou uma nota?',
    'guia_assinatura_guia': 'Como pago a assinatura do sistema?', 'guia_gateway': 'Como envio SMS aos encarregados?', 'guia_material': 'Como carrego material escolar?',
    'guia_justificar_falta': 'Como justifico uma falta?', 'guia_registar_presencas': 'Como registo as presenças?', 'guia_transferencia': 'Como faço uma transferência?',
    'guia_comunicados': 'Como publico um comunicado?', 'guia_horarios': 'Como elaboro o horário?', 'guia_sumarios': 'Como registo o sumário da aula?',
    'guia_ocorrencias': 'Como registo uma ocorrência disciplinar?', 'guia_antiia': 'Como protejo uma prova contra IA?', 'guia_folha_resposta': 'Como gero a folha de resposta?',
    'guia_cargos_guia': 'O que faz o Director de Turma?', 'guia_crm_guia': 'Como registo um contacto com o encarregado?', 'guia_calendario_guia': 'Como adiciono eventos ao calendário?',
    'guia_assistente_guia': 'O que sabes fazer?', 'guia_pedir_documentos': 'Como peço uma declaração?', 'guia_recuperar_acesso': 'Esqueci a minha senha.', 'guia_ano_lectivo': 'Porque a página está vazia?',
    'guia_saas_painel': 'O que mostra o painel master?', 'guia_saas_cadastrar': 'Como cadastro uma escola?', 'guia_saas_inspeccionar': 'Como inspeciono uma escola?',
    'guia_saas_renovar': 'Como renovo a assinatura de uma escola?', 'guia_pagamentos_saas': 'Como valido um comprovativo de pagamento?',
    'guia_acessos_guia': 'Onde vejo os registos de acessos?',
}


def _ajustar_registo():
    for c in CAPACIDADES:
        for k, v in _AJUSTES.get(c.nome, {}).items():
            setattr(c, k, v)
        if c.tipo == 'guia':
            gid = c.nome[len('guia_'):]
            if gid in _GUIA_PERFIS:
                c.perfis = _GUIA_PERFIS[gid]
            if gid in _GUIA_ALT:
                c.alt = _GUIA_ALT[gid]
            if gid in _GUIA_DESTINO_PROPRIO:
                c.destino_proprio = _GUIA_DESTINO_PROPRIO[gid]
            if c.destino is None:
                c.universal = True
        if c.nome in _EXEMPLOS:
            c.exemplos = (_EXEMPLOS[c.nome],)


_ajustar_registo()
POR_NOME = {c.nome: c for c in CAPACIDADES}


def permitido(cap, role, modulos):
    """Regra de segurança: o assistente só responde sobre o que pertence ao painel do perfil.

    1. o perfil tem de estar na lista da capacidade (se houver);
    2. regras do MEC e informação comum (calendário, comunicados, ajuda) são para todos;
    3. caso contrário, o módulo da capacidade tem de existir no painel do perfil (ou num módulo alternativo).
    """
    if cap.perfis is not None and role not in cap.perfis:
        return False
    if cap.universal or cap.tipo == 'regra':
        return True
    destino = cap.destino_proprio if (role in PROPRIO and cap.destino_proprio) else cap.destino
    if destino is None:
        return True
    return destino in modulos or any(a in modulos for a in cap.alt)

# Em que página o utilizador está → capacidade favorecida (desempate)
PAGINA_CAPACIDADE = {
    'presencas': 'faltas', 'aluno-faltas': 'faltas', 'caderneta': 'notas', 'aluno-notas': 'notas', 'pagamentos': 'propinas',
    'aluno-pagamentos': 'propinas', 'turmas': 'turmas', 'calendario': 'calendario', 'aluno-calendario': 'calendario', 'horarios': 'horario',
    'transferencias': 'transferencias', 'crm': 'crm', 'pautas': 'pautas', 'comunicados': 'comunicados', 'exames': 'exames_calendario',
    'calendario-exames': 'exames_calendario', 'material-escolar': 'material', 'despesas': 'caixa', 'assinatura-escola': 'assinatura',
    'minhas-atividades': 'cargos', 'atribuicoes-cargos': 'cargos', 'plano-curricular': 'plano_curricular', 'certificados': 'certificados',
    'alunos': 'alunos_resumo',
}
SUGESTOES_PAGINA = {
    'presencas': ['Quantas faltas tem o aluno?', 'Como justifico uma falta?', 'Como funcionam as faltas em aula dupla?'],
    'caderneta': ['Como lanço as notas?', 'Quais as negativas do aluno?', 'Como se calcula a média trimestral (MT)?'],
    'aluno-notas': ['Quais as minhas negativas?', 'Quanto preciso para passar?', 'Como se calcula a MFD?'],
    'pagamentos': ['Há propinas em atraso?', 'Como gero as cobranças?', 'Qual o saldo de caixa deste mês?'],
    'aluno-pagamentos': ['Que propinas tenho em atraso?', 'Como pago por M-Pesa?'],
    'turmas': ['Que turmas estão lotadas?', 'Quantas vagas livres temos?', 'Como crio turmas em lote?'],
    'pautas': ['Que pautas estão por fechar?', 'Como emito a acta do conselho?'],
    'exames': ['Quando são os exames?', 'Qual a nota mínima do exame?', 'Como funciona a 2.ª época?'],
    'transferencias': ['Quantas transferências estão pendentes?', 'Como faço uma transferência?'],
    'crm': ['Há atendimentos abertos?', 'Como registo um contacto com o encarregado?'],
    'calendario': ['Quais os próximos eventos?', 'Quando são os exames?'],
    'horarios': ['Que aulas tenho hoje?', 'Que aulas tenho amanhã?'],
    'plano-curricular': ['Que disciplinas tem a 11.ª classe?'],
    'comunicados': ['Quais os últimos comunicados?', 'Como publico um comunicado?'],
}
SUGESTOES_PERFIL = {
    'SUPERADMIN': ['Quantas escolas temos?', 'Há comprovativos por validar?', 'Há faturas em atraso?', 'Qual a receita mensal (MRR)?',
                   'Como cadastro uma escola?', 'Como inspeciono uma escola?'],
    'ALUNO': ['Quais as minhas negativas?', 'Quanto preciso para passar?', 'Que propinas tenho em atraso?', 'Que aulas tenho hoje?', 'Quando são os exames?'],
    'ENCARREGADO': ['Quantas faltas tem o meu educando?', 'Há propinas em atraso?', 'Quais as notas publicadas?', 'Quais os últimos comunicados?'],
    'PROFESSOR': ['Que aulas tenho hoje?', 'Quais as actividades de cargo por concluir?', 'Como lanço as notas?', 'Como registo presenças?'],
    'FINANCEIRO': ['Qual o saldo de caixa deste mês?', 'Há propinas em atraso?', 'Como gero as cobranças?'],
    'DAP': ['Que pautas estão por fechar?', 'Que turmas estão sem Director de Turma?', 'Quais as actividades de cargo em atraso?', 'Há alunos em risco por faltas?'],
    'DIRECTOR_ESCOLA': ['Quantos alunos temos?', 'Quando termina a assinatura?', 'Há atendimentos abertos?', 'Que pautas estão por fechar?'],
    'ADMIN_ESCOLA': ['Quantos alunos temos?', 'Quando termina a assinatura?', 'Há atendimentos abertos?', 'Como redefino uma senha?'],
    'CHEFE_SECRETARIA': ['Há transferências pendentes?', 'Há atendimentos abertos?', 'Como emito um certificado?', 'Quantos alunos temos?'],
    'SECRETARIA': ['Há transferências pendentes?', 'Há atendimentos abertos?', 'Como faço uma matrícula?', 'Quantos alunos temos?'],
}
SUGESTOES_BASE = ['Como se calcula a média trimestral (MT)?', 'Quais são as regras de aprovação?', 'Quando são os exames?']


def sugestoes(role, pagina=None):
    itens = list(SUGESTOES_PAGINA.get(pagina or '', []))
    for s in SUGESTOES_PERFIL.get(role, SUGESTOES_BASE):
        if s not in itens:
            itens.append(s)
    return itens[:6]


# ---------------------------------------------------------------- compreensão (forma canónica)
# Aplicada ao texto E às palavras-chave: tira artigos/preposições, passa o plural ao singular, leva "cadastro/crio/lanço…" ao infinitivo
# e corrige erros de escrita comuns ("propinaa", "lansar"). Assim "como registo as presenças" encontra "registar presença".
_ARTIGOS = {'a', 'o', 'as', 'os', 'um', 'uma', 'uns', 'umas', 'de', 'da', 'do', 'das', 'dos', 'no', 'na', 'nos', 'nas'}
_VERBOS = {
    'cadastro': 'cadastrar', 'crio': 'criar', 'lanco': 'lancar', 'registo': 'registar', 'emito': 'emitir', 'faco': 'fazer', 'pago': 'pagar',
    'gero': 'gerar', 'redefino': 'redefinir', 'imprimo': 'imprimir', 'publico': 'publicar', 'justifico': 'justificar', 'desbloqueio': 'desbloquear',
    'carrego': 'carregar', 'vejo': 'ver', 'envio': 'enviar', 'protejo': 'proteger', 'elaboro': 'elaborar', 'adiciono': 'adicionar',
    'inspeciono': 'inspecionar', 'inspeccionar': 'inspecionar', 'valido': 'validar', 'confirmo': 'confirmar', 'consulto': 'consultar', 'abro': 'abrir',
    'marco': 'marcar', 'aprovo': 'aprovar', 'apago': 'apagar', 'altero': 'alterar', 'corrijo': 'corrigir', 'exporto': 'exportar', 'descarrego': 'descarregar',
    'encontro': 'encontrar', 'atribuo': 'atribuir', 'renovo': 'renovar', 'liquido': 'liquidar', 'cobro': 'cobrar', 'recebo': 'receber', 'anulo': 'anular',
    'cancelo': 'cancelar', 'rejeito': 'rejeitar', 'importo': 'importar', 'procuro': 'procurar', 'pesquiso': 'pesquisar', 'actividades': 'atividades', 'actividade': 'atividade', 'actas': 'acta', 'activa': 'ativa', 'activo': 'ativo', 'activas': 'ativa',
    'activos': 'ativo', 'diretor': 'director', 'diretora': 'directora', 'directo': 'direto', 'subscricao': 'assinatura', 'senhas': 'senha',
}


def _singular(t):
    return t[:-1] if len(t) > 3 and t.endswith('s') and not t.endswith('ss') else t


def _canon_tokens(texto):
    out = []
    for t in texto.split():
        if t in _ARTIGOS:
            continue
        t = _VERBOS.get(t, t)
        out.append(_singular(t))
    return out


def canon(texto):
    return ' ' + ' '.join(_canon_tokens(texto)) + ' '


_VOCAB = None
_CK_CACHE = {}


def _vocabulario():
    global _VOCAB
    if _VOCAB is None:
        _VOCAB = {t for c in CAPACIDADES for k in c.chaves for t in _canon_tokens(k.strip()) if len(t) >= 5}
    return _VOCAB


def _e_erro_de_escrita(t, m):
    """Erro de escrita (troca, falta ou repetição de letra) e não uma flexão da palavra (funcionam ≠ funciona, aluno ≠ alunos)."""
    if t.startswith(m) or m.startswith(t):
        curto, longo = sorted((t, m), key=len)
        extra = longo[len(curto):]
        return len(set(extra)) == 1 and extra[0] == curto[-1]      # só se for a última letra repetida ("propinaa")
    return True


def _corrigir_escrita(tc):
    """Troca palavras quase iguais às do vocabulário do assistente (erros de escrita), só em palavras longas e sem ambiguidade."""
    import difflib
    vocab = _vocabulario()
    out = []
    for t in tc.split():
        if len(t) >= 6 and t not in vocab:
            m = difflib.get_close_matches(t, vocab, n=1, cutoff=0.88)
            if m and _e_erro_de_escrita(t, m[0]):
                t = m[0]
        out.append(t)
    return ' ' + ' '.join(out) + ' '


def _grupos(cap):
    """Grupos de chaves equivalentes (singular/plural, artigos…). Cada grupo conta UMA vez; frases maiores valem mais que palavras soltas."""
    k = (cap.nome, len(cap.chaves))
    g = _CK_CACHE.get(k)
    if g is None:
        mapa = {}
        for c in cap.chaves:
            cc = canon(c)
            # uma chave de várias palavras que fica reduzida a uma só (ex.: " classe do" → " classe ") ficaria genérica demais:
            # essa só vale na forma original
            if len(c.split()) >= 2 and len(cc.split()) < 2:
                cc = None
            chave = cc if cc is not None else ('raw', c)
            entrada = mapa.setdefault(chave, {'canon': cc, 'raws': [], 'ntok': len((cc or c).split())})
            entrada['raws'].append(c)
        g = [(e['canon'], e['raws'], 1 + 0.5 * min(e['ntok'] - 1, 2)) for e in mapa.values()]
        _CK_CACHE[k] = g
    return g


def pontuar(cap, texto, pagina, tc=None):
    """Pontos = palavras-chave presentes (no texto e na sua forma canónica); "como/onde" favorece guias; a página actual desempata."""
    pontos = 0.0
    for cc, raws, peso in _grupos(cap):
        if (cc is not None and tc and cc in tc) or any(r in texto for r in raws):
            pontos += peso
    pontos *= cap.peso
    if not pontos:
        return 0
    pergunta_de_ajuda = any(p in texto for p in (' como ', ' onde ', ' passo a passo', ' tutorial', ' o que faz', ' o que e '))
    # "como está / como vai…" pergunta pelo ESTADO de algo (dados), não por um procedimento (guia)
    if any(p in texto for p in (' como esta', ' como estao', ' como vai', ' como vao', ' como anda', ' como andam')):
        pergunta_de_ajuda = False
    if pergunta_de_ajuda:
        pontos += 2 if cap.tipo == 'guia' else (-1 if cap.tipo == 'dados' else 0)
    if PAGINA_CAPACIDADE.get(pagina or '') == cap.nome:
        pontos += 0.5
    return pontos


PRIORIDADE = {'regra': 2, 'guia': 1, 'dados': 0}   # em empate, regras e guias antes de dados


def pontuacoes(texto, pagina=None):
    """Todas as capacidades com pontos > 0, da melhor para a pior: [(pontos, prioridade, capacidade)]."""
    out = []
    tc = _corrigir_escrita(canon(texto))
    for cap in CAPACIDADES:
        p = pontuar(cap, texto, pagina, tc)
        if p > 0:
            out.append((p, PRIORIDADE[cap.tipo], cap))
    out.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return out


def classificar(pergunta, pagina=None):
    """Melhor capacidade (sem filtrar por perfil; o filtro de segurança está em `permitido`)."""
    texto = normalizar(pergunta)
    ordem = pontuacoes(texto, pagina)
    return (ordem[0][2] if ordem else None), texto


FRASES_NAVEGACAO = (' onde fica', ' onde esta', ' onde vejo', ' onde encontro', ' onde abro', ' abrir ', ' leva me', ' ir para', ' mostra me onde')


def navegar(texto):
    """"Onde fica X?" → (destino, rótulo) do melhor módulo, ou None. O filtro por painel é feito pelo motor."""
    if not any(f in texto for f in FRASES_NAVEGACAO):
        return None
    melhor, pontos = None, 0
    for destino, (rotulo, chaves) in guias.NAVEGACAO.items():
        p = sum(1 for c in chaves if c in texto)
        if p > pontos:
            melhor, pontos = (destino, rotulo), p
    return melhor
