"""
Capacidades estatísticas e de calendário do Assistente (só leitura, dados reais, isoladas por escola).

* Calendário académico: para TODOS os painéis (alunos e encarregados incluídos).
* Estatísticas (pessoal, alunos, resultados, repetentes, faltosos, melhores alunos, exames, propinas, previsão, aproveitamento por
  professor/turma/classe/disciplina/escola e comparação entre anos lectivos): para os painéis que NÃO são de aluno/encarregado.
  O professor só vê as suas turmas/disciplinas; listas nominais só para os perfis que já têm esse ecrã no painel.
* Plataforma (Super Admin): calendário agregado, escolas por província, ranking, crescimento e limites do plano.

Nada é inventado: sem registos, devolve-se apenas o estado vazio explicativo.
"""
import datetime
import re
from collections import Counter, defaultdict

from django.db.models import Avg, Count, Q, Sum

from . import capacidades as cap
from .capacidades import DIRECCAO, ROTULO_TRIM, TRIMESTRES, Capacidade, _data, _lista, _res, normalizar

PROPRIO = cap.PROPRIO
NAO_PROPRIO = {'SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP', 'CHEFE_SECRETARIA', 'SECRETARIA', 'PROFESSOR', 'FINANCEIRO'}
PEDAGOGICO = DIRECCAO | {'DAP', 'PROFESSOR'}
SECRETARIA = {'CHEFE_SECRETARIA', 'SECRETARIA'}
COBRANCA = DIRECCAO | {'FINANCEIRO'} | SECRETARIA
NEGATIVA = 9.5
MESES = {'janeiro': 1, 'fevereiro': 2, 'marco': 3, 'abril': 4, 'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8, 'setembro': 9,
         'outubro': 10, 'novembro': 11, 'dezembro': 12}
MES_NOME = {v: k.capitalize().replace('Marco', 'Março') for k, v in MESES.items()}


def _pct(n, t):
    return round(100 * n / t, 1) if t else 0


def _fmt(p):
    return f'{p:g}'.replace('.', ',')


def _ano_pedido(ctx):
    """Ano lectivo escolhido na pergunta ("em 2025"); por omissão, o ano lectivo activo da escola."""
    m = re.search(r'\b(20\d{2})\b', ctx.texto)
    return m.group(1) if m else (ctx.ano or str(ctx.hoje.year))


def _ano_anterior(ano):
    return str(int(ano) - 1) if str(ano).isdigit() else None


def _num_classe(grau):
    m = re.search(r'\d+', grau or '')
    return int(m.group()) if m else None


def _turmas_do_professor(ctx):
    from apps.professores.models import AlocacaoDocente
    return list(AlocacaoDocente.objects.filter(escola=ctx.escola, professor_id=getattr(ctx.user, 'professor_id', None))
                .values_list('turma_id', 'disciplina_id'))


def _notas(ctx, ano):
    """Notas trimestrais do ano lectivo com valor lançado; o professor só vê as suas turmas/disciplinas."""
    from apps.notas.models import Nota
    qs = Nota.objects.filter(escola=ctx.escola, turma__ano_letivo=ano, periodo__in=TRIMESTRES, media_final__gt=0)
    if ctx.role == 'PROFESSOR':
        pares = Q(pk__in=[])
        for t_id, d_id in _turmas_do_professor(ctx):
            pares |= Q(turma_id=t_id, disciplina_id=d_id)
        qs = qs.filter(pares)
    return qs


def _alunos(ctx, ano):
    from apps.alunos.models import Aluno
    qs = Aluno.objects.filter(escola=ctx.escola, turma__ano_letivo=ano)
    if ctx.role == 'PROFESSOR':
        qs = qs.filter(turma_id__in=[t for t, _ in _turmas_do_professor(ctx)])
    return qs


def _hm(qs, campo='genero'):
    """(homens, mulheres, total) de um queryset com género M/F."""
    r = qs.aggregate(h=Count('id', filter=Q(**{f'{campo}__iexact': 'M'})), m=Count('id', filter=Q(**{f'{campo}__istartswith': 'F'})), t=Count('id'))
    return r['h'], r['m'], r['t']


def _sem_dados(ctx, texto, destino, rotulo):
    return _res(texto, {'vazio': True}, destino, rotulo)


# ------------------------------------------------------------------ calendário académico (todos os painéis)
def h_calendario_academico(ctx):
    from apps.documentos.models import CalendarioEscolar
    from apps.notas.models import CalendarioExame
    e = ctx.escola
    partes, dados = [], {}
    trims = [f'{i}.º trimestre: {_data(getattr(e, f"data_inicio_t{i}"))} a {_data(getattr(e, f"data_fim_t{i}"))}'
             for i in (1, 2, 3) if getattr(e, f'data_inicio_t{i}') and getattr(e, f'data_fim_t{i}')]
    cab = f'Ano lectivo {ctx.ano}'
    if e.trimestre_ativo in ROTULO_TRIM:
        cab += f' — {ROTULO_TRIM[e.trimestre_ativo]} em curso'
    partes.append(cab + '.')
    if trims:
        partes.append('Trimestres: ' + '; '.join(trims) + '.')
    mes = next((n for k, n in MESES.items() if f' {k} ' in ctx.texto), None)
    eventos = CalendarioEscolar.objects.filter(escola=e, status_aprovacao='APROVADO_DIRECTOR')
    rotulo_tipo = dict(CalendarioEscolar.TIPO_CHOICES)
    chaves_tipo = {'FERIADO_PAUSA': (' feriado', ' ferias', ' pausa'), 'REUNIAO_ENCARREGADOS': (' reuniao', ' reunioes'),
                   'CONSELHO_TURMA': (' conselho',), 'EXAME': (' exame', ' epoca'), 'AVALIACAO_TESTE': (' teste', ' avaliacao', ' avaliacoes')}
    tipo = next((t for t, ks in chaves_tipo.items() if any(k in ctx.texto for k in ks)), None)
    if tipo:
        eventos = eventos.filter(tipo=tipo)
    if mes:
        eventos = eventos.filter(Q(data_inicio__month=mes) | Q(data_fim__month=mes))
        eventos = eventos.filter(Q(data_inicio__year=ctx.hoje.year) | Q(data_inicio__year=int(ctx.ano) if str(ctx.ano).isdigit() else ctx.hoje.year))
    else:
        eventos = eventos.filter(Q(data_inicio__gte=ctx.hoje) | Q(data_fim__gte=ctx.hoje))
    lista = list(eventos.order_by('data_inicio')[:8])
    dados['eventos'] = len(lista)
    if lista:
        titulo = f'Eventos de {MES_NOME[mes]}' if mes else 'Próximos eventos'
        partes.append(titulo + ': ' + '; '.join(
            f'{_data(x.data_inicio)}' + (f' a {_data(x.data_fim)}' if x.data_fim and x.data_fim != x.data_inicio else '') +
            f' — {x.titulo} ({rotulo_tipo.get(x.tipo, x.tipo)})' for x in lista) + '.')
    else:
        partes.append('Não há eventos aprovados no calendário escolar' + (f' em {MES_NOME[mes]}.' if mes else ' a partir de hoje.'))
    if not tipo or tipo == 'EXAME':
        ex = CalendarioExame.objects.filter(escola=e, data__gte=ctx.hoje, **({'ano_letivo': ctx.ano} if ctx.ano else {}))
        if ctx.proprio and ctx.aluno is not None and ctx.aluno.classe:
            ex = ex.filter(classe__iexact=ctx.aluno.classe)
        ex = list(ex.order_by('data', 'hora_inicio')[:3])
        dados['exames'] = len(ex)
        if ex:
            partes.append('Exames: ' + '; '.join(f'{_data(i.data)} — {i.classe}, {i.disciplina} ({i.epoca}.ª época)' for i in ex) + '.')
    return _res(' '.join(partes), dados, 'calendario', 'Abrir o Calendário Escolar')


def h_plat_calendario(ctx):
    from apps.documentos.models import CalendarioEscolar
    qs = (CalendarioEscolar.objects.filter(status_aprovacao='APROVADO_DIRECTOR', escola__eliminada_em__isnull=True)
          .filter(Q(data_inicio__gte=ctx.hoje) | Q(data_fim__gte=ctx.hoje)).select_related('escola').order_by('data_inicio'))
    total = qs.count()
    if not total:
        return _res('Nenhuma escola tem eventos futuros aprovados no calendário escolar.', {'eventos': 0}, 'saas', 'Abrir o Painel Master')
    escolas = qs.values('escola').distinct().count()
    linhas = [f'{_data(x.data_inicio)} — {x.titulo} ({x.escola.nome})' for x in qs[:5]]
    return _res(f'{total} evento(s) futuros em {escolas} escola(s). Próximos: ' + '; '.join(linhas) + '. Para o calendário de uma escola, abra-a com "Inspecionar".',
                {'eventos': total, 'escolas': escolas}, 'saas', 'Abrir o Painel Master')


# ------------------------------------------------------------------ pessoal (docente e não docente)
def h_estat_pessoal(ctx):
    from apps.accounts.models import Usuario
    from apps.professores.models import AlocacaoDocente, Professor
    e = ctx.escola
    profs = Professor.objects.filter(escola=e)
    h, m, total = _hm(profs)
    ativos = profs.filter(ativo=True).count()
    inativos = total - ativos
    ROT = {'ADMIN_ESCOLA': 'Administração', 'DIRECTOR_ESCOLA': 'Direcção', 'DAP': 'Direcção pedagógica', 'CHEFE_SECRETARIA': 'Chefia da secretaria',
           'SECRETARIA': 'Secretaria', 'FINANCEIRO': 'Financeiro'}
    contas = Counter(Usuario.objects.filter(escola=e, role__in=list(ROT), ativo=True).values_list('role', flat=True))
    nao_doc = sum(contas.values())
    if not total and not nao_doc:
        return _sem_dados(ctx, 'Ainda não há funcionários registados na escola.', 'professores', 'Abrir Atribuição & Docentes')
    txt = f'Pessoal da escola: {total + nao_doc} funcionário(s) — {total} docente(s) e {nao_doc} não docente(s) com conta activa.'
    if total:
        txt += f' Docentes: {h} H, {m} M ({ativos} activo(s), {inativos} inactivo(s)/desligado(s)).'
        carr = Counter(profs.filter(ativo=True).values_list('carreira', flat=True))
        txt += ' Por carreira: ' + _lista([f'{c} {n}' for c, n in carr.most_common()], 5) + '.'
        com = set(AlocacaoDocente.objects.filter(escola=e, **({'turma__ano_letivo': ctx.ano} if ctx.ano else {})).values_list('professor_id', flat=True))
        txt += f' {sum(1 for i in profs.filter(ativo=True).values_list("id", flat=True) if i not in com)} docente(s) activo(s) sem turma atribuída.'
    if nao_doc:
        txt += ' Não docentes: ' + _lista([f'{ROT[r]} {n}' for r, n in contas.most_common()], 6) + '.'
    txt += ' (O sistema não guarda o género dos não docentes nem regista transferências de funcionários; inactivos/desligados são os docentes desactivados.)'
    return _res(txt, {'docentes': total, 'nao_docentes': nao_doc, 'inactivos': inativos}, 'professores', 'Abrir Atribuição & Docentes')


# ------------------------------------------------------------------ alunos
def h_estat_alunos(ctx):
    from apps.alunos.models import Aluno
    ano = _ano_pedido(ctx)
    qs = _alunos(ctx, ano)
    h, m, total = _hm(qs)
    if not total:
        return _sem_dados(ctx, f'Não há alunos em turmas do ano lectivo {ano}.', 'alunos', 'Abrir Alunos')
    ROT = {'ATIVO': 'activos', 'TRANSFERIDO': 'transferidos', 'EVADIDO': 'desistentes', 'INATIVO': 'inactivos'}
    estados = Counter(qs.values_list('status', flat=True))
    txt = f'Alunos do ano lectivo {ano}: {total} HM ({h} H, {m} M). Situação: ' + ', '.join(f'{n} {ROT.get(s, s.lower())}' for s, n in estados.most_common()) + '.'
    classes = defaultdict(lambda: [0, 0, 0])
    for g, cl in qs.values_list('genero', 'turma__grau_ano'):
        r = classes[cl]
        r[2] += 1
        r[0 if (g or '').upper() == 'M' else 1] += 1
    ordem = sorted(classes.items(), key=lambda kv: (_num_classe(kv[0]) or 99, kv[0]))
    txt += ' Por classe (H/M/HM): ' + _lista([f'{c} {a}/{b}/{t}' for c, (a, b, t) in ordem], 8) + '.'
    if ctx.role != 'PROFESSOR':
        antes = Aluno.objects.filter(escola=ctx.escola, status='TRANSFERIDO', turma__ano_letivo__lt=ano).count()
        if antes:
            txt += f' Transferidos em anos anteriores: {antes}.'
        if ano == ctx.ano:
            sem = Aluno.objects.filter(escola=ctx.escola, turma__isnull=True, status='ATIVO').count()
            if sem:
                txt += f' {sem} aluno(s) activo(s) ainda sem turma.'
    return _res(txt, {'ano': ano, 'hm': total, 'h': h, 'm': m}, 'alunos', 'Abrir Alunos')


def _resultados(ctx, ano):
    """{aluno_id: (classe, genero, estado)} com estado aprovado|reprovado|pendente — critério oficial (avaliar_aprovacao_pauta) sobre a MFD."""
    from common.utils.avaliacoes_mocambique import avaliar_aprovacao_pauta
    por_aluno = {}
    for aid, grau, g, disc, per, nota in _notas(ctx, ano).values_list('aluno_id', 'turma__grau_ano', 'aluno__genero', 'disciplina__nome', 'periodo', 'media_final'):
        r = por_aluno.setdefault(aid, [grau, g, defaultdict(dict)])
        r[2][disc][per] = nota
    saida = {}
    for aid, (grau, g, discs) in por_aluno.items():
        completas = [{'disciplina': d, 'notaFinal': int(round(sum(p.values()) / 3))} for d, p in discs.items() if len(p) == 3]
        if not completas:
            saida[aid] = (grau, g, 'pendente')
        else:
            saida[aid] = (grau, g, 'aprovado' if avaliar_aprovacao_pauta(completas, grau)['aprovado'] else 'reprovado')
    return saida


def h_estat_resultados(ctx):
    ano = _ano_pedido(ctx)
    res = _resultados(ctx, ano)
    if not res:
        return _sem_dados(ctx, f'Ainda não há notas trimestrais lançadas no ano lectivo {ano} para calcular aprovados e reprovados.', 'pautas', 'Abrir as Pautas')
    cont = Counter()
    por_classe = defaultdict(Counter)
    for grau, g, est in res.values():
        sx = 'H' if (g or '').upper() == 'M' else 'M'
        cont[est] += 1
        cont[(est, sx)] += 1
        por_classe[grau][est] += 1
    julg = cont['aprovado'] + cont['reprovado']
    txt = (f'Resultados do ano lectivo {ano} ({julg} aluno(s) com as 3 notas trimestrais): aprovados {cont["aprovado"]} '
           f'({cont[("aprovado", "H")]} H, {cont[("aprovado", "M")]} M), reprovados {cont["reprovado"]} ({cont[("reprovado", "H")]} H, {cont[("reprovado", "M")]} M); '
           f'taxa de aprovação {_fmt(_pct(cont["aprovado"], julg))}%.')
    if cont['pendente']:
        txt += f' {cont["pendente"]} aluno(s) ainda sem as 3 notas trimestrais (resultado pendente).'
    ordem = sorted(por_classe.items(), key=lambda kv: (_num_classe(kv[0]) or 99, kv[0]))
    txt += ' Por classe (aprovados/reprovados): ' + _lista([f'{c} {v["aprovado"]}/{v["reprovado"]}' for c, v in ordem], 8) + '.'
    # repetentes: frequentaram a mesma classe no ano anterior
    ant = _ano_anterior(ano)
    if ant and ctx.role != 'PROFESSOR':
        from apps.notas.models import Nota
        antes = defaultdict(set)
        for aid, grau in Nota.objects.filter(escola=ctx.escola, turma__ano_letivo=ant).values_list('aluno_id', 'turma__grau_ano').distinct():
            antes[aid].add(_num_classe(grau))
        rep = [(aid, g) for aid, (grau, g, _e) in res.items() if _num_classe(grau) in antes.get(aid, ())]
        if antes:
            txt += f' Repetentes (mesma classe do ano {ant}): {len(rep)} ({sum(1 for _a, g in rep if (g or "").upper() == "M")} H, {sum(1 for _a, g in rep if (g or "").upper() != "M")} M).'
    return _res(txt, {'ano': ano, 'aprovados': cont['aprovado'], 'reprovados': cont['reprovado'], 'pendentes': cont['pendente']}, 'pautas', 'Abrir as Pautas')


def h_faltosos(ctx):
    from apps.alunos.models import PresencaAluno
    ano = _ano_pedido(ctx)
    qs = PresencaAluno.objects.filter(escola=ctx.escola, turma__ano_letivo=ano, status='FALTA_INJUSTIFICADA')
    if ctx.role == 'PROFESSOR':
        qs = qs.filter(turma_id__in=[t for t, _ in _turmas_do_professor(ctx)])
    linhas = list(qs.values('aluno_id', 'aluno__nome', 'aluno__apelido', 'turma__grau_ano', 'turma__nome', 'aluno__genero')
                  .annotate(n=Sum('aulas'), j=Sum('aulas_justificadas')).order_by('-n')[:2000])
    efectivas = [(r, (r['n'] or 0) - (r['j'] or 0)) for r in linhas]
    efectivas = [(r, f) for r, f in efectivas if f > 0]
    if not efectivas:
        return _sem_dados(ctx, f'Não há faltas injustificadas registadas no ano lectivo {ano}.', 'presencas', 'Abrir as Presenças')
    h = sum(1 for r, _ in efectivas if (r['aluno__genero'] or '').upper() == 'M')
    top = sorted(efectivas, key=lambda x: -x[1])[:5]
    nomes = [f"{r['aluno__nome']} {r['aluno__apelido'] or ''}".strip() + f" ({r['turma__nome']}, {f} falta(s))" for r, f in top]
    return _res(f'Faltosos no ano lectivo {ano}: {len(efectivas)} aluno(s) com faltas injustificadas por justificar ({h} H, {len(efectivas) - h} M). '
                f'Mais faltas: ' + '; '.join(nomes) + '.', {'faltosos': len(efectivas)}, 'presencas', 'Abrir as Presenças')


def h_melhores_alunos(ctx):
    ano = _ano_pedido(ctx)
    qs = _notas(ctx, ano)
    periodo = next((p for p in reversed(TRIMESTRES) if qs.filter(periodo=p).exists()), None)
    if not periodo:
        return _sem_dados(ctx, f'Ainda não há notas lançadas no ano lectivo {ano} para classificar os melhores alunos.', 'estatisticas-aproveitamento', 'Abrir a Estatística')
    qs = qs.filter(periodo=periodo)
    n_classe = ctx.classe_pedida()
    if n_classe:
        qs = qs.filter(turma__grau_ano__regex=rf'^{n_classe}[^0-9]')
    top = list(qs.values('aluno_id', 'aluno__nome', 'aluno__apelido', 'turma__grau_ano', 'turma__nome').annotate(m=Avg('media_final'), n=Count('id'))
               .filter(n__gte=3).order_by('-m')[:5])
    if not top:
        return _sem_dados(ctx, 'Ainda não há alunos com pelo menos 3 disciplinas avaliadas para classificar.', 'estatisticas-aproveitamento', 'Abrir a Estatística')
    linhas = [f"{i}. {t['aluno__nome']} {t['aluno__apelido'] or ''}".strip() + f" — {t['turma__grau_ano']} {t['turma__nome']}, média {t['m']:.1f}" for i, t in enumerate(top, 1)]
    return _res(f'Melhores alunos do {ROTULO_TRIM[periodo]} de {ano}' + (f' ({n_classe}.ª classe)' if n_classe else '') + ': ' + '; '.join(linhas) + '.',
                {'periodo': periodo, 'alunos': len(top)}, 'estatisticas-aproveitamento', 'Abrir a Estatística')


def h_estat_exames(ctx):
    from apps.notas.models import JuriExameAluno, NotaExame
    ano = _ano_pedido(ctx)
    insc = JuriExameAluno.objects.filter(juri__escola=ctx.escola, juri__ano_letivo=ano)
    ids = set(insc.values_list('aluno_id', flat=True))
    res = Counter(NotaExame.objects.filter(escola=ctx.escola, ano_letivo=ano).values_list('resultado', flat=True))
    if not ids and not res:
        return _sem_dados(ctx, f'Ainda não há inscritos nem resultados de exames no ano lectivo {ano}.', 'exames', 'Abrir os Exames')
    from apps.alunos.models import Aluno
    h, m, t = _hm(Aluno.objects.filter(id__in=ids, escola=ctx.escola))
    txt = f'Exames do ano lectivo {ano}: {t} aluno(s) inscrito(s) nos júris ({h} H, {m} M).'
    if res:
        txt += ' Resultados lançados: ' + ', '.join(f'{n} {r.lower()}' for r, n in res.most_common()) + '.'
    return _res(txt, {'inscritos': t}, 'exames', 'Abrir os Exames')


# ------------------------------------------------------------------ propinas e previsão
def h_estat_pagamentos(ctx):
    from apps.pagamentos.models import Pagamento
    ano = _ano_pedido(ctx)
    qs = Pagamento.objects.filter(escola=ctx.escola, mes_referencia__startswith=str(ano)).exclude(status='CANCELADO')
    meses = list(qs.values('mes_referencia').annotate(f=Sum('valor'), r=Sum('valor_pago'), n=Count('id')).order_by('mes_referencia'))
    if not meses:
        return _sem_dados(ctx, f'Não há propinas/mensalidades registadas em {ano}.', 'pagamentos', 'Abrir Propinas & Mensalidades')
    fat = sum(x['f'] for x in meses)
    rec = sum(x['r'] for x in meses)
    atraso = qs.filter(status__in=('PENDENTE', 'ATRASADO'), data_vencimento__lt=datetime.datetime.combine(ctx.hoje, datetime.time.min, tzinfo=datetime.timezone.utc)).count()
    futuro = qs.filter(status__in=('PENDENTE', 'ATRASADO')).aggregate(s=Sum('valor'), p=Sum('valor_pago'))
    previsao = (futuro['s'] or 0) - (futuro['p'] or 0)
    txt = (f'Propinas de {ano}: facturado {fat:.2f} MZN, recebido {rec:.2f} MZN ({_fmt(_pct(float(rec), float(fat)))}%); {atraso} em atraso. '
           'Mês a mês (facturado/recebido): ' + _lista([f"{x['mes_referencia']} {x['f']:.0f}/{x['r']:.0f}" for x in meses], 12) + '.')
    txt += f' Previsão de entrada (valores ainda por receber): {previsao:.2f} MZN.'
    return _res(txt, {'facturado': str(fat), 'recebido': str(rec)}, 'pagamentos', 'Abrir Propinas & Mensalidades')


def h_previsao_alunos(ctx):
    from apps.alunos.models import Aluno
    anos = list(Aluno.objects.filter(escola=ctx.escola, turma__isnull=False).values('turma__ano_letivo').annotate(n=Count('id')).order_by('turma__ano_letivo'))
    if not anos:
        return _sem_dados(ctx, 'Ainda não há histórico de alunos por ano lectivo para fazer previsões.', 'alunos', 'Abrir Alunos')
    txt = 'Anos findos (alunos por ano lectivo): ' + ', '.join(f"{x['turma__ano_letivo']}: {x['n']}" for x in anos[-6:]) + '.'
    ativos = Aluno.objects.filter(escola=ctx.escola, status='ATIVO', turma__isnull=False, turma__ano_letivo=ctx.ano)
    continuam = sum(1 for g in ativos.values_list('turma__grau_ano', flat=True) if (_num_classe(g) or 0) < 12)
    concluintes = ativos.count() - continuam
    ingr = [n for _a, n in Counter(Aluno.objects.filter(escola=ctx.escola).exclude(ano_ingresso__in=[None, '']).values_list('ano_ingresso', flat=True)).items()
            if str(_a).isdigit() and int(_a) < int(ctx.ano or 0)][-3:]
    if ativos.exists() and ingr:
        novos = round(sum(ingr) / len(ingr))
        prox = int(ctx.ano) + 1 if str(ctx.ano).isdigit() else ''
        txt += (f' Previsão para {prox}: cerca de {continuam + novos} aluno(s) = {continuam} a continuar (todos os activos de {ctx.ano} fora da 12.ª classe, '
                f'aprovados a subir de classe e reprovados a repetir) + {novos} novo(s) ingressos (média dos últimos {len(ingr)} ano(s) com registo). '
                f'{concluintes} aluno(s) da 12.ª classe devem concluir o ciclo. É uma estimativa: não conta com transferências nem desistências.')
    else:
        txt += ' Ainda não há dados suficientes (alunos activos e ingressos de anos anteriores) para estimar o ano seguinte.'
    return _res(txt, {'anos': len(anos)}, 'alunos', 'Abrir Alunos')


# ------------------------------------------------------------------ aproveitamento pedagógico (escola, classe, turma, disciplina, professor, anos)
def _dimensao(texto):
    for chaves, dim in (((' por professor', ' do professor', ' dos professores', ' de cada professor', ' professor com'), 'professor'),
                        ((' por turma', ' da turma', ' das turmas', ' de cada turma'), 'turma'),
                        ((' por disciplina', ' da disciplina', ' das disciplinas', ' de cada disciplina'), 'disciplina'),
                        ((' por classe', ' da classe', ' das classes', ' de cada classe'), 'classe')):
        if any(k in texto for k in chaves):
            return dim
    return 'escola'


def h_aproveitamento_avancado(ctx):
    ano = _ano_pedido(ctx)
    comparar = any(k in ctx.texto for k in (' compar', ' evolucao', ' entre anos', ' anos anteriores', ' ano passado', ' ano anterior'))
    dim = _dimensao(ctx.texto)
    if comparar:
        linhas = []
        for a, pos, tot in _por_ano(ctx):
            linhas.append((a, pos, tot))
        if not linhas:
            return _sem_dados(ctx, 'Ainda não há notas lançadas para comparar o aproveitamento entre anos lectivos.', 'estatisticas-aproveitamento', 'Abrir a Estatística')
        txt = 'Aproveitamento pedagógico por ano lectivo (avaliações trimestrais positivas): ' + '; '.join(f'{a}: {_fmt(_pct(p, t))}% ({t} avaliações)' for a, p, t in linhas) + '.'
        if len(linhas) >= 2:
            (a0, p0, t0), (a1, p1, t1) = linhas[-2], linhas[-1]
            d = round(_pct(p1, t1) - _pct(p0, t0), 1)
            txt += f' De {a0} para {a1}: {"subida" if d > 0 else "descida" if d < 0 else "estável"} de {_fmt(abs(d))} pontos percentuais.'
        return _res(txt, {'anos': len(linhas)}, 'estatisticas-aproveitamento', 'Abrir a Estatística')
    qs = _notas(ctx, ano)
    total = qs.count()
    if not total:
        return _sem_dados(ctx, f'Ainda não há notas lançadas no ano lectivo {ano} para calcular o aproveitamento.', 'estatisticas-aproveitamento', 'Abrir a Estatística')
    pos_total = qs.filter(media_final__gte=NEGATIVA).count()
    rotulo = f'Aproveitamento pedagógico de {ano} — escola: {_fmt(_pct(pos_total, total))}% de positivas ({total} avaliações)'
    if dim == 'escola':
        return _res(rotulo + '. Peça "por classe", "por turma", "por disciplina" ou "por professor" para o detalhe, ou "compare com os anos anteriores".',
                    {'ano': ano, 'positivas_pct': _pct(pos_total, total)}, 'estatisticas-aproveitamento', 'Abrir a Estatística')
    grupos = defaultdict(lambda: [0, 0])
    if dim == 'professor':
        from apps.professores.models import AlocacaoDocente
        dono = {(t, d): f'{n} {a or ""}'.strip() for t, d, n, a in AlocacaoDocente.objects.filter(escola=ctx.escola, turma__ano_letivo=ano)
                .values_list('turma_id', 'disciplina_id', 'professor__nome', 'professor__apelido')}
        for t, d, nota in qs.values_list('turma_id', 'disciplina_id', 'media_final'):
            g = grupos[dono.get((t, d), 'sem professor atribuído')]
            g[1] += 1
            g[0] += nota >= NEGATIVA
    else:
        campo = {'turma': 'turma__nome', 'disciplina': 'disciplina__nome', 'classe': 'turma__grau_ano'}[dim]
        extra = 'turma__grau_ano' if dim == 'turma' else campo
        for k, e2, nota in qs.values_list(campo, extra, 'media_final'):
            g = grupos[f'{e2} {k}' if dim == 'turma' else k]
            g[1] += 1
            g[0] += nota >= NEGATIVA
    ordem = sorted(((k, p, t) for k, (p, t) in grupos.items() if t >= 3), key=lambda x: (-_pct(x[1], x[2]), x[0]))
    if not ordem:
        return _res(rotulo + '; ainda sem avaliações suficientes por ' + dim + '.', {'ano': ano}, 'estatisticas-aproveitamento', 'Abrir a Estatística')
    if dim == 'classe':
        ordem.sort(key=lambda x: (_num_classe(x[0]) or 99, x[0]))
    txt = rotulo + f'. Por {dim} (% de positivas): ' + _lista([f'{k} {_fmt(_pct(p, t))}%' for k, p, t in ordem], 10) + '.'
    return _res(txt, {'ano': ano, 'grupos': len(ordem)}, 'estatisticas-aproveitamento', 'Abrir a Estatística')


def _por_ano(ctx):
    from apps.notas.models import Nota
    qs = Nota.objects.filter(escola=ctx.escola, periodo__in=TRIMESTRES, media_final__gt=0)
    if ctx.role == 'PROFESSOR':
        pares = Q(pk__in=[])
        for t_id, d_id in _turmas_do_professor(ctx):
            pares |= Q(turma_id=t_id, disciplina_id=d_id)
        qs = qs.filter(pares)
    rows = qs.values('turma__ano_letivo').annotate(t=Count('id'), p=Count('id', filter=Q(media_final__gte=NEGATIVA))).order_by('turma__ano_letivo')
    return [(r['turma__ano_letivo'], r['p'], r['t']) for r in rows][-6:]


# ------------------------------------------------------------------ plataforma (Super Admin)
def h_plat_provincias(ctx):
    from apps.alunos.models import Aluno
    from apps.tenants.models import Escola
    escolas = Escola.objects.values('provincia').annotate(n=Count('id')).order_by('-n')
    if not escolas:
        return _res('Ainda não há escolas registadas na plataforma.', {'escolas': 0}, 'saas', 'Abrir o Painel Master')
    alunos = dict(Aluno.objects.values_list('escola__provincia').annotate(n=Count('id')))
    h, m, t = _hm(Aluno.objects.all())
    return _res(f'Alunos na plataforma: {t} ({h} H, {m} M). Escolas por província (escolas/alunos): ' +
                _lista([f"{e['provincia']} {e['n']}/{alunos.get(e['provincia'], 0)}" for e in escolas], 10) + '.', {'provincias': len(escolas)}, 'saas', 'Abrir o Painel Master')


def h_plat_ranking(ctx):
    from apps.tenants.models import Escola
    top = list(Escola.objects.annotate(n=Count('alunos')).filter(n__gt=0).order_by('-n')[:5])
    if not top:
        return _res('Ainda não há alunos registados nas escolas da plataforma.', {'escolas': 0}, 'saas', 'Abrir o Painel Master')
    sem = Escola.objects.annotate(n=Count('alunos')).filter(n=0).count()
    return _res('Escolas com mais alunos: ' + '; '.join(f'{e.nome} ({e.n})' for e in top) + f'. {sem} escola(s) sem alunos registados.', {'sem_alunos': sem}, 'saas', 'Abrir o Painel Master')


def h_plat_crescimento(ctx):
    from apps.tenants.models import Escola
    por_mes = Counter(d.strftime('%Y-%m') for d in Escola.objects.values_list('data_adesao', flat=True) if d)
    if not por_mes:
        return _res('Ainda não há escolas aderentes para medir o crescimento.', {'escolas': 0}, 'saas', 'Abrir o Painel Master')
    meses = sorted(por_mes)[-6:]
    return _res('Novas escolas por mês: ' + ', '.join(f'{k}: {por_mes[k]}' for k in meses) + f'. Total acumulado: {sum(por_mes.values())}.', {'meses': len(meses)}, 'saas', 'Abrir o Painel Master')


def h_plat_limites(ctx):
    from apps.tenants.models import Escola
    acima = [e for e in Escola.objects.filter(plano__isnull=False).select_related('plano').annotate(n=Count('alunos', distinct=True)) if e.n > e.plano.max_alunos]
    perto = [e for e in Escola.objects.filter(plano__isnull=False).select_related('plano').annotate(n=Count('alunos', distinct=True)) if 0.9 * e.plano.max_alunos <= e.n <= e.plano.max_alunos]
    if not acima and not perto:
        return _res('Nenhuma escola ultrapassou ou está perto do limite de alunos do seu plano.', {'acima': 0, 'perto': 0}, 'saas', 'Abrir o Painel Master')
    txt = ''
    if acima:
        txt += f'{len(acima)} escola(s) acima do limite de alunos: ' + _lista([f'{e.nome} ({e.n}/{e.plano.max_alunos})' for e in acima], 5) + '. '
    if perto:
        txt += f'{len(perto)} escola(s) a mais de 90% do limite: ' + _lista([f'{e.nome} ({e.n}/{e.plano.max_alunos})' for e in perto], 5) + '.'
    return _res(txt.strip(), {'acima': len(acima), 'perto': len(perto)}, 'saas', 'Abrir o Painel Master')


# ------------------------------------------------------------------ registo
EXTRA = [
    Capacidade('calendario_academico', 'dados', [' calendario academico', ' calendario letivo', ' calendario lectivo', ' calendario escolar', ' feriados', ' pausas letivas', ' ferias',
                                                 ' conselhos de turma', ' datas importantes', ' agenda do ano', ' quando comecam as aulas',
                                                 ' fim do ano letivo', ' eventos de', ' proximas avaliacoes', ' epoca de exames'], h_calendario_academico,
               universal=True, destino='calendario', destino_proprio='aluno-calendario', rotulo='Abrir o Calendário Escolar', peso=3,
               exemplos=('Mostre o calendário académico.', 'Que eventos há em março?', 'Quando são os feriados?')),
    Capacidade('estat_pessoal', 'dados', [' estatistica de docentes', ' estatistica do pessoal', ' quantos funcionarios', ' total de funcionarios', ' pessoal docente', ' pessoal nao docente',
                                          ' funcionarios da escola', ' docentes homens', ' docentes mulheres', ' quadro de pessoal', ' pessoal da escola', ' quantos docentes'], h_estat_pessoal,
               perfis=NAO_PROPRIO, universal=True, destino='professores', rotulo='Abrir Atribuição & Docentes', peso=3, exemplos=('Estatística do pessoal docente e não docente.',)),
    Capacidade('estat_alunos', 'dados', [' estatistica de alunos', ' estatistica dos alunos', ' alunos por genero', ' alunos homens e mulheres', ' alunos hm', ' quantos alunos e quantas alunas',
                                         ' desistencias', ' quantos desistentes', ' estatistica da escola', ' alunos do ano letivo'],
               h_estat_alunos, perfis=NAO_PROPRIO, universal=True, destino='alunos', rotulo='Abrir Alunos', peso=3, exemplos=('Estatística de alunos (H, M e HM) do ano lectivo.',)),
    Capacidade('estat_resultados', 'dados', [' alunos aprovados', ' alunos reprovados', ' quantos aprovados', ' quantos reprovados', ' repetentes', ' quantos repetentes', ' taxa de aprovacao do ano',
                                             ' resultados do ano', ' aprovados e reprovados', ' reprovacoes'], h_estat_resultados, perfis=PEDAGOGICO | SECRETARIA, destino='pautas',
               alt=('estatisticas-aproveitamento',), rotulo='Abrir as Pautas', peso=3, exemplos=('Quantos alunos aprovados, reprovados e repetentes?',)),
    Capacidade('faltosos', 'dados', [' alunos faltosos', ' faltosos', ' estatistica de faltas', ' quantos faltosos'],
               h_faltosos, perfis=PEDAGOGICO | SECRETARIA, destino='presencas', rotulo='Abrir as Presenças', peso=3, exemplos=('Quais os alunos faltosos?',)),
    Capacidade('melhores_alunos', 'dados', [' melhores alunos', ' melhor aluno', ' quadro de honra', ' alunos com melhor media', ' top alunos', ' alunos de excelencia', ' cinco melhores'],
               h_melhores_alunos, perfis=PEDAGOGICO, destino='estatisticas-aproveitamento', rotulo='Abrir a Estatística', peso=3, exemplos=('Quais são os melhores alunos?',)),
    Capacidade('estat_exames', 'dados', [' inscritos ao exame', ' inscritos nos exames', ' inscritos para exame', ' quantos inscritos', ' alunos inscritos', ' resultados dos exames',
                                         ' estatistica dos exames', ' candidatos ao exame'], h_estat_exames, perfis=PEDAGOGICO | SECRETARIA, destino='exames', alt=('pautas',),
               rotulo='Abrir os Exames', peso=3, exemplos=('Quantos alunos estão inscritos ao exame?',)),
    Capacidade('estat_pagamentos', 'dados', [' pagamentos mensais', ' propinas por mes', ' receita das propinas', ' estatistica de pagamentos', ' estatistica financeira', ' quanto foi pago',
                                             ' previsao de receitas', ' previsao de pagamentos', ' evolucao dos pagamentos', ' cobranca por mes'], h_estat_pagamentos, perfis=COBRANCA,
               destino='pagamentos', rotulo='Abrir Propinas & Mensalidades', peso=3, exemplos=('Estatística dos pagamentos mensais.',)),
    Capacidade('previsao_alunos', 'dados', [' previsao de alunos', ' previsao dos alunos', ' quantos alunos no proximo ano', ' alunos no proximo ano', ' alunos do proximo ano', ' alunos futuros',
                                            ' historico de alunos', ' alunos por ano letivo', ' anos findos', ' projecao de alunos', ' previsao para o proximo ano'],
               h_previsao_alunos, perfis=DIRECCAO | {'DAP'} | SECRETARIA, destino='alunos', rotulo='Abrir Alunos', peso=3, exemplos=('Previsão de alunos para o próximo ano.',)),
    Capacidade('aproveitamento_avancado', 'dados', [' aproveitamento pedagogico', ' aproveitamento por professor', ' aproveitamento por turma', ' aproveitamento por classe',
                                                    ' aproveitamento por disciplina', ' aproveitamento da escola', ' aproveitamento do professor', ' aproveitamento da turma',
                                                    ' aproveitamento da classe', ' aproveitamento da disciplina', ' comparar aproveitamento', ' comparacao do aproveitamento',
                                                    ' aproveitamento entre anos', ' evolucao do aproveitamento', ' aproveitamento dos anos'], h_aproveitamento_avancado, perfis=PEDAGOGICO,
               destino='estatisticas-aproveitamento', rotulo='Abrir a Estatística', peso=4, exemplos=('Compare o aproveitamento pedagógico entre os anos.', 'Aproveitamento por professor.')),
]
EXTRA_PLATAFORMA = [
    Capacidade('plat_calendario', 'dados', [' calendario academico', ' calendario escolar', ' feriados', ' eventos das escolas', ' calendarios das escolas'], h_plat_calendario,
               perfis={'SUPERADMIN'}, destino='saas', plataforma=True, peso=3, exemplos=('Que eventos têm as escolas no calendário?',)),
    Capacidade('plat_provincias', 'dados', [' escolas por provincia', ' alunos por provincia', ' por provincia', ' provincias', ' estatistica da plataforma', ' alunos hm da plataforma', ' alunos homens e mulheres'],
               h_plat_provincias, perfis={'SUPERADMIN'}, destino='saas', plataforma=True, peso=3, exemplos=('Quantas escolas e alunos há por província?',)),
    Capacidade('plat_ranking', 'dados', [' escolas com mais alunos', ' maiores escolas', ' ranking de escolas', ' escolas sem alunos', ' escolas inativas', ' escolas sem atividade'],
               h_plat_ranking, perfis={'SUPERADMIN'}, destino='saas', plataforma=True, peso=3, exemplos=('Quais as escolas com mais alunos?',)),
    Capacidade('plat_crescimento', 'dados', [' crescimento da plataforma', ' novas escolas', ' escolas novas', ' adesoes', ' escolas por mes', ' crescimento de escolas'],
               h_plat_crescimento, perfis={'SUPERADMIN'}, destino='saas', plataforma=True, peso=3, exemplos=('Quantas escolas aderiram nos últimos meses?',)),
    Capacidade('plat_limites', 'dados', [' limite de alunos', ' acima do limite', ' limite do plano', ' escolas acima do plano', ' escolas perto do limite', ' upgrade de plano'],
               h_plat_limites, perfis={'SUPERADMIN'}, destino='saas', plataforma=True, peso=3, exemplos=('Que escolas ultrapassaram o limite do plano?',)),
]

SUGESTOES_NOVAS = {
    'TODOS': ['Mostre o calendário académico.', 'Quais os feriados e pausas lectivas?'],
    'ESTATISTICA_GESTAO': ['Estatística de alunos (H, M e HM).', 'Quantos alunos aprovados, reprovados e repetentes?', 'Estatística do pessoal docente e não docente.',
                           'Quais os alunos faltosos?', 'Quais são os melhores alunos?', 'Compare o aproveitamento entre os anos.',
                           'Previsão de alunos para o próximo ano.', 'Estatística dos pagamentos mensais.'],
    'SUPERADMIN': ['Quantas escolas e alunos há por província?', 'Quais as escolas com mais alunos?', 'Que escolas ultrapassaram o limite do plano?',
                   'Quantas escolas aderiram nos últimos meses?', 'Que eventos têm as escolas no calendário?'],
}


def registar():
    """Junta as capacidades estatísticas ao registo geral (idempotente) e enriquece as sugestões por painel."""
    if 'estat_alunos' in cap.POR_NOME:
        return
    novas = EXTRA + EXTRA_PLATAFORMA
    for c in novas:
        c.prioritaria = c.nome not in ('estat_pessoal', 'calendario_academico')   # estas duas competem com perguntas genéricas de contagem/agenda
    cap.CAPACIDADES.extend(novas)
    cap.POR_NOME.update({c.nome: c for c in novas})
    S = SUGESTOES_NOVAS
    for role in list(cap.SUGESTOES_PERFIL):
        base = cap.SUGESTOES_PERFIL[role]
        if role == 'SUPERADMIN':
            extra = S['SUPERADMIN'] + S['TODOS'][:1]
        elif role in PROPRIO:
            extra = S['TODOS']
        elif role == 'PROFESSOR':
            extra = S['TODOS'][:1] + ['Aproveitamento por disciplina.', 'Quais são os melhores alunos?', 'Quais os alunos faltosos?']
        elif role == 'FINANCEIRO':
            extra = S['TODOS'][:1] + ['Estatística dos pagamentos mensais.', 'Estatística de alunos (H, M e HM).']
        else:
            extra = S['TODOS'][:1] + S['ESTATISTICA_GESTAO']
        cap.SUGESTOES_PERFIL[role] = base + [s for s in extra if s not in base]
    cap.SUGESTOES_PAGINA.setdefault('estatisticas-aproveitamento', ['Compare o aproveitamento entre os anos.', 'Aproveitamento por professor.', 'Quais são os melhores alunos?'])
    cap.SUGESTOES_PAGINA.setdefault('dashboard', ['Estatística de alunos (H, M e HM).', 'Previsão de alunos para o próximo ano.'])
    cap.SUGESTOES_PAGINA['calendario'] = ['Que eventos há este mês?', 'Quando são os feriados?', 'Quando são os exames?']
    cap.SUGESTOES_PAGINA['aluno-calendario'] = ['Mostre o calendário académico.', 'Quando são os exames?']
    cap._VOCAB = None
