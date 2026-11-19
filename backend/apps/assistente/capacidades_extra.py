"""
Capacidades adicionais do Assistente (por painel): perfil do aluno, resumo, turmas do professor, aproveitamento, resumo da escola,
devedores, contactos e datas dos trimestres, professores, e a ajuda personalizada ("o que posso perguntar?").
Todas só leitura, dentro da escola e filtradas pelo painel do perfil (ver `capacidades.permitido`).
"""
import datetime
import re
from collections import defaultdict
from decimal import Decimal

from django.db.models import Count, Q
from django.utils import timezone

from . import capacidades as cap
from .capacidades import (CAPACIDADES, DIRECCAO, GESTAO, POR_NOME, ROTULO_TRIM, TRIMESTRES, Capacidade, _data, _lista, _nome, _res, normalizar)

COBRANCA = DIRECCAO | {'FINANCEIRO', 'SECRETARIA', 'CHEFE_SECRETARIA'}


# ---------------------------------------------------------------- aluno
def h_perfil(ctx):
    a = ctx.aluno
    t = a.turma
    partes = [f'{_nome(a)} — matrícula {a.matricula}', a.classe or 'sem classe atribuída']
    partes.append(f'turma {t.nome}' if t else 'sem turma')
    if t and t.area and t.area.strip().lower() not in ('', 'geral'):
        partes.append(f'área {t.area}')
    if t and t.director_turma_id:
        partes.append(f'Director de Turma: {t.director_turma.nome}')
    if a.status and a.status != 'ATIVO':
        partes.append(f'situação: {a.status.lower()}')
    resp = ''
    if a.nome_responsavel:
        resp = f' Encarregado: {a.nome_responsavel}' + (f' ({a.contato_responsavel})' if a.contato_responsavel else '') + '.'
    return _res('; '.join(partes) + '.' + resp, {'matricula': a.matricula, 'classe': a.classe, 'turma': t.nome if t else None})


def h_resumo_aluno(ctx):
    """Junta faltas, notas e propinas — só as partes que pertencem ao painel do perfil."""
    partes = []
    for nome, h in (('faltas', cap.h_faltas), ('notas', cap.h_notas), ('propinas', cap.h_propinas)):
        c = POR_NOME[nome]
        if cap.permitido(c, ctx.role, ctx.modulos or set()):
            partes.append(h(ctx)['texto'])
    if not partes:
        return _res('Não há informação do aluno disponível para o seu perfil.', {})
    return _res(' '.join(partes), {'componentes': len(partes)}, 'aluno-perfil' if ctx.proprio else 'alunos', 'Abrir o perfil do aluno')


# ---------------------------------------------------------------- professor / pedagógico
def h_turmas_professor(ctx):
    from apps.alunos.models import Aluno
    from apps.professores.models import AlocacaoDocente
    qs = AlocacaoDocente.objects.filter(escola=ctx.escola, professor_id=getattr(ctx.user, 'professor_id', None)).select_related('turma', 'disciplina')
    if ctx.ano:
        qs = qs.filter(turma__ano_letivo=ctx.ano)
    por_turma = defaultdict(list)
    turmas = {}
    for a in qs:
        por_turma[a.turma_id].append(a.disciplina.nome)
        turmas[a.turma_id] = a.turma
    if not turmas:
        return _res('Ainda não tem turmas atribuídas neste ano lectivo.', {'turmas': 0}, 'caderneta', 'Abrir a Caderneta')
    contagem = dict(Aluno.objects.filter(turma_id__in=list(turmas), status='ATIVO').values_list('turma_id').annotate(n=Count('id')))
    linhas = [f'{t.grau_ano} {t.nome} ({_lista(sorted(set(por_turma[i])), 3)}; {contagem.get(i, 0)} aluno(s))' for i, t in turmas.items()]
    return _res(f'Tem {len(turmas)} turma(s): ' + _lista(linhas, 8) + '.', {'turmas': len(turmas)}, 'caderneta', 'Abrir a Caderneta')


def h_aproveitamento(ctx):
    from apps.notas.models import Nota
    qs = Nota.objects.filter(escola=ctx.escola, media_final__gt=0)
    if ctx.ano:
        qs = qs.filter(turma__ano_letivo=ctx.ano)
    if ctx.role == 'PROFESSOR':
        from apps.professores.models import AlocacaoDocente
        pares = Q(pk__in=[])
        for t_id, d_id in AlocacaoDocente.objects.filter(escola=ctx.escola, professor_id=getattr(ctx.user, 'professor_id', None)).values_list('turma_id', 'disciplina_id'):
            pares |= Q(turma_id=t_id, disciplina_id=d_id)
        qs = qs.filter(pares)
    periodo = next((p for p in reversed(TRIMESTRES) if qs.filter(periodo=p).exists()), None)
    if not periodo:
        return _res('Ainda não há notas lançadas para calcular o aproveitamento.', {'avaliacoes': 0}, 'estatisticas-aproveitamento', 'Abrir a Estatística')
    qs = qs.filter(periodo=periodo)
    total = qs.count()
    neg = qs.filter(media_final__lt=9.5).count()
    pct = lambda n, t: round(100 * n / t) if t else 0
    por_classe = qs.values('turma__grau_ano').annotate(t=Count('id'), n=Count('id', filter=Q(media_final__lt=9.5))).order_by('turma__grau_ano')
    classes = [f"{r['turma__grau_ano']} {pct(r['n'], r['t'])}%" for r in por_classe]
    por_disc = [(r['disciplina__nome'], pct(r['n'], r['t']), r['t']) for r in
                qs.values('disciplina__nome').annotate(t=Count('id'), n=Count('id', filter=Q(media_final__lt=9.5)))]
    piores = sorted((d for d in por_disc if d[2] >= 3 and d[1] > 0), key=lambda x: -x[1])[:3]
    txt = f'No {ROTULO_TRIM[periodo]}: {total} avaliação(ões), {neg} negativa(s) ({pct(neg, total)}%).'
    if classes:
        txt += ' Negativas por classe: ' + _lista(classes, 6) + '.'
    if piores:
        txt += ' Disciplinas com mais negativas: ' + ', '.join(f'{d} {p}%' for d, p, _ in piores) + '.'
    return _res(txt, {'periodo': periodo, 'avaliacoes': total, 'negativas': neg}, 'estatisticas-aproveitamento', 'Abrir a Estatística')


def h_professores_resumo(ctx):
    from apps.professores.models import AlocacaoDocente, Professor
    profs = Professor.objects.filter(escola=ctx.escola)
    total = profs.count()
    if not total:
        return _res('Ainda não há professores registados.', {'professores': 0}, 'professores', 'Abrir Atribuição & Docentes')
    aloc = AlocacaoDocente.objects.filter(escola=ctx.escola)
    if ctx.ano:
        aloc = aloc.filter(turma__ano_letivo=ctx.ano)
    com = set(aloc.values_list('professor_id', flat=True))
    sem = [p.nome for p in profs if p.id not in com]
    txt = f'Há {total} professor(es), {total - len(sem)} com turmas atribuídas'
    txt += f' e {len(sem)} sem atribuição' + (f' ({_lista(sem, 5)})' if sem else '') + '.'
    return _res(txt, {'professores': total, 'sem_atribuicao': len(sem)}, 'professores', 'Abrir Atribuição & Docentes')


# ---------------------------------------------------------------- direcção / finanças / secretaria
def h_resumo_escola(ctx):
    from apps.alunos.models import Aluno, TransferenciaAnulacao
    from apps.atribuicoes.models import AtribuicaoCargo
    from apps.crm.models import Atendimento
    from apps.pagamentos.models import Pagamento
    from apps.pautas.models import Pauta
    from apps.professores.models import Professor
    from apps.turmas.models import Turma
    e = ctx.escola
    alunos = Aluno.objects.filter(escola=e, status='ATIVO').count()
    turmas = Turma.objects.filter(escola=e, **({'ano_letivo': ctx.ano} if ctx.ano else {})).count()
    profs = Professor.objects.filter(escola=e).count()
    atraso = list(Pagamento.objects.filter(escola=e, status__in=('PENDENTE', 'ATRASADO'), data_vencimento__lt=timezone.now()))
    valor = sum((p.valor - p.valor_pago for p in atraso), Decimal('0'))
    pautas = Pauta.objects.filter(escola=e).exclude(status='FECHADA').count()
    atend = Atendimento.objects.filter(escola=e).exclude(estado='RESOLVIDO').count()
    transf = TransferenciaAnulacao.objects.filter(escola=e, status='PENDENTE').count()
    cargos = AtribuicaoCargo.objects.filter(escola=e, prazo__lt=ctx.hoje).exclude(estado='CONCLUIDA').count()
    partes = [f'{e.nome}: {alunos} aluno(s) activo(s), {turmas} turma(s), {profs} professor(es)',
              f'{len(atraso)} propina(s) em atraso ({valor} MZN)', f'{pautas} pauta(s) por fechar', f'{atend} atendimento(s) por resolver',
              f'{transf} transferência(s) pendente(s)', f'{cargos} actividade(s) de cargo em atraso']
    return _res('; '.join(partes) + '.', {'alunos': alunos, 'turmas': turmas, 'professores': profs, 'propinas_em_atraso': len(atraso)}, 'dashboard', 'Abrir o Painel')


def h_devedores(ctx):
    from apps.pagamentos.models import Pagamento
    qs = Pagamento.objects.filter(escola=ctx.escola, status__in=('PENDENTE', 'ATRASADO'), data_vencimento__lt=timezone.now()).select_related('aluno', 'aluno__turma')
    n_classe = ctx.classe_pedida()
    if n_classe:
        qs = qs.filter(aluno__turma__grau_ano__regex=rf'^{n_classe}[^0-9]')
    por_aluno = defaultdict(lambda: [None, Decimal('0'), 0])
    for p in qs:
        r = por_aluno[p.aluno_id]
        r[0], r[1], r[2] = p.aluno, r[1] + (p.valor - p.valor_pago), r[2] + 1
    if not por_aluno:
        return _res('Não há propinas em atraso' + (f' na {n_classe}.ª classe.' if n_classe else '.'), {'devedores': 0}, 'pagamentos', 'Abrir Propinas & Mensalidades')
    total = sum((r[1] for r in por_aluno.values()), Decimal('0'))
    if n_classe:
        top = sorted(por_aluno.values(), key=lambda r: -r[1])[:10]
        linhas = [f"{_nome(a)} ({a.turma.nome if a.turma else '-'}): {v} MZN, {n} mês(es)" for a, v, n in top]
        return _res(f'{len(por_aluno)} aluno(s) em dívida na {n_classe}.ª classe ({total} MZN). Maiores dívidas: ' + '; '.join(linhas) + '.',
                    {'devedores': len(por_aluno), 'valor': str(total)}, 'pagamentos', 'Abrir Propinas & Mensalidades')
    por_turma = defaultdict(lambda: [0, Decimal('0')])
    for a, v, _n in por_aluno.values():
        k = f"{a.turma.grau_ano} {a.turma.nome}" if a.turma else 'sem turma'
        por_turma[k][0] += 1
        por_turma[k][1] += v
    top = sorted(por_turma.items(), key=lambda kv: -kv[1][1])[:5]
    return _res(f'{len(por_aluno)} aluno(s) em dívida, {total} MZN no total. Por turma: ' + '; '.join(f'{k}: {n} aluno(s), {v} MZN' for k, (n, v) in top) +
                '. Diga a classe (por exemplo "devedores da 7.ª classe") para ver os nomes.', {'devedores': len(por_aluno), 'valor': str(total)},
                'pagamentos', 'Abrir Propinas & Mensalidades')


def h_contactos(ctx):
    e = ctx.escola
    partes = [e.nome]
    if e.telefone:
        partes.append(f'telefone {e.telefone}')
    if e.email:
        partes.append(f'e-mail {e.email}')
    if e.endereco:
        partes.append(f'endereço {e.endereco}')
    partes.append(f'{e.distrito}, {e.provincia}')
    return _res('Contactos: ' + '; '.join(partes) + '.', {'telefone': e.telefone, 'email': e.email})


def h_trimestres(ctx):
    e = ctx.escola
    linhas = []
    for i in (1, 2, 3):
        ini, fim = getattr(e, f'data_inicio_t{i}'), getattr(e, f'data_fim_t{i}')
        if ini and fim:
            linhas.append(f'{i}.º trimestre: {_data(ini)} a {_data(fim)}')
    atual = ROTULO_TRIM.get(e.trimestre_ativo, '')
    if not linhas:
        return _res(f'A escola ainda não definiu as datas dos trimestres. O trimestre activo é o {atual}.', {'definidas': 0})
    return _res('; '.join(linhas) + f'. Trimestre activo: {atual}.', {'definidas': len(linhas)})


# ---------------------------------------------------------------- ajuda personalizada
def h_ajuda(ctx):
    modulos = ctx.modulos or set()
    dados, guias_ex, regras = [], [], []
    for c in CAPACIDADES:
        if not c.exemplos or (c.plataforma and ctx.role != 'SUPERADMIN') or not cap.permitido(c, ctx.role, modulos):
            continue
        if c.tipo == 'dados' and (ctx.escola is not None or c.plataforma):
            dados.append(c.exemplos[0])
        elif c.tipo == 'guia' and c.nome != 'guia_assistente_guia':
            guias_ex.append(c.exemplos[0])
        elif c.tipo == 'regra' and c.nome in ('faq_mt', 'faq_aprovacao'):
            regras.append(c.exemplos[0])
    txt = 'Sou o assistente do SIGE e só respondo sobre o que pertence ao seu painel (só leitura). '
    if dados:
        txt += 'Consultas: ' + '; '.join(dados[:8]) + '. '
    if guias_ex:
        txt += 'Guias passo a passo: ' + '; '.join(guias_ex[:6]) + '. '
    if regras:
        txt += 'Regras do MEC: ' + '; '.join(regras) + '.'
    exemplos = (dados[:3] + guias_ex[:2] + regras[:1])[:6]
    return {'texto': txt.strip(), 'dados': None, 'destino': None, 'rotulo': None, 'sugestoes': exemplos}


EXTRA = [
    Capacidade('perfil_aluno', 'dados', [' qual a turma', ' em que turma', ' minha turma', ' turma do', ' qual a classe', ' em que classe', ' minha classe', ' classe do',
                                         ' meu codigo', ' minha matricula', ' numero de matricula', ' meu director de turma', ' quem e o director de turma',
                                         ' dados do aluno', ' ficha do aluno', ' contacto do encarregado', ' quem e o encarregado', ' dados pessoais'], h_perfil,
               aluno='obrigatorio', destino='alunos', destino_proprio='aluno-perfil', rotulo='Abrir o perfil do aluno', peso=2,
               exemplos=('Em que turma está o aluno?',)),
    Capacidade('resumo_aluno', 'dados', [' resumo do aluno', ' como esta o aluno', ' como esta a ir', ' como vai o', ' como estou', ' situacao do aluno', ' minha situacao',
                                         ' como esta o meu filho', ' como vai o meu filho', ' balanco', ' visao geral do aluno'], h_resumo_aluno,
               aluno='obrigatorio', destino='alunos', destino_proprio='aluno-perfil', rotulo='Abrir o perfil do aluno', peso=2,
               alt=('caderneta', 'presencas', 'pagamentos'), exemplos=('Como está o aluno?',)),
    Capacidade('turmas_professor', 'dados', [' minhas turmas', ' que turmas tenho', ' turmas que leciono', ' turmas que lecciono', ' quantos alunos tenho', ' minhas disciplinas',
                                             ' que disciplinas leciono', ' que disciplinas lecciono', ' onde leciono'], h_turmas_professor,
               perfis={'PROFESSOR'}, destino='caderneta', rotulo='Abrir a Caderneta', peso=2, exemplos=('Que turmas tenho?',)),
    Capacidade('aproveitamento', 'dados', [' aproveitamento', ' taxa de aprovacao', ' taxa de negativas', ' percentagem de negativas', ' quantas negativas', ' disciplinas com mais negativas',
                                           ' negativas por classe', ' resultado das notas', ' como estao as notas', ' alunos com negativa', ' quem tem negativa', ' negativas da turma', ' negativas nas minhas'], h_aproveitamento,
               perfis=DIRECCAO | {'DAP', 'PROFESSOR'}, destino='estatisticas-aproveitamento', rotulo='Abrir a Estatística', peso=2,
               exemplos=('Como está o aproveitamento?',)),
    Capacidade('professores_resumo', 'dados', [' quantos professores', ' professores sem turma', ' professores sem atribuicao', ' total de professores', ' docentes sem turma'],
               h_professores_resumo, perfis=DIRECCAO | {'DAP', 'SECRETARIA', 'CHEFE_SECRETARIA'}, destino='professores', rotulo='Abrir Atribuição & Docentes', peso=2,
               exemplos=('Quantos professores estão sem turma?',)),
    Capacidade('resumo_escola', 'dados', [' resumo da escola', ' como esta a escola', ' situacao da escola', ' visao geral da escola', ' panorama', ' estado da escola',
                                          ' resumo geral'], h_resumo_escola, perfis=DIRECCAO, destino='dashboard', rotulo='Abrir o Painel', peso=3,
               exemplos=('Dê-me um resumo da escola.',)),
    Capacidade('devedores', 'dados', [' devedores', ' quem deve', ' alunos devedores', ' em divida', ' dividas', ' quem nao pagou', ' nao pagaram', ' alunos em divida'],
               h_devedores, perfis=COBRANCA, destino='pagamentos', rotulo='Abrir Propinas & Mensalidades', peso=2, exemplos=('Quem tem propinas em atraso?',)),
    Capacidade('contactos_escola', 'dados', [' contacto da escola', ' contactos da escola', ' telefone da escola', ' email da escola', ' e mail da escola', ' endereco da escola',
                                             ' morada da escola', ' como contacto a escola', ' falar com a escola', ' numero da escola'], h_contactos, universal=True, peso=2,
               exemplos=('Qual o contacto da escola?',)),
    Capacidade('trimestres', 'dados', [' datas dos trimestres', ' datas do trimestre', ' quando comeca o trimestre', ' quando termina o trimestre', ' trimestre atual', ' trimestre ativo',
                                       ' em que trimestre', ' calendario dos trimestres', ' inicio do trimestre', ' fim do trimestre', ' 1o trimestre', ' 2o trimestre', ' 3o trimestre', ' 1 trimestre', ' 2 trimestre', ' 3 trimestre', ' primeiro trimestre', ' segundo trimestre', ' terceiro trimestre'], h_trimestres, universal=True, peso=2,
               exemplos=('Quais as datas dos trimestres?',)),
]


def registar():
    """Junta as capacidades extra ao registo geral (idempotente) e liga a ajuda personalizada."""
    if 'perfil_aluno' in POR_NOME:
        return
    CAPACIDADES.extend(EXTRA)
    POR_NOME.update({c.nome: c for c in EXTRA})
    ajuda = POR_NOME['guia_assistente_guia']
    ajuda.handler = h_ajuda
    ajuda.chaves = list(ajuda.chaves) + [' o que posso perguntar', ' que posso perguntar', ' que perguntas', ' ajuda', ' ajudas', ' o que podes fazer', ' como me ajudas',
                                         ' o que sabes fazer', ' o que consegues', ' para que serves']
    ajuda.peso = 2
    # permissões de dados do aluno para as novas capacidades
    cap.ACESSO_ALUNO['perfil_aluno'] = {'proprio', 'gestao', 'financeiro'}
    cap.ACESSO_ALUNO['resumo_aluno'] = {'proprio', 'gestao', 'professor', 'financeiro'}
    cap._VOCAB = None       # o vocabulário de correcção de escrita inclui as palavras novas
