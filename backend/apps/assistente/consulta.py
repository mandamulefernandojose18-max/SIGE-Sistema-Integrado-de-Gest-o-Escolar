"""
Motor de consulta por PARÂMETROS do Assistente (nível 0, só leitura).

Perguntas novas, que não estão na lista das já previstas mas cabem nos dados que o perfil pode ver, são respondidas assim:
  1. ENTIDADE  — de que dados se fala (alunos, faltas, notas, propinas, transferências…);
  2. OPERAÇÃO  — o que fazer (contar, listar, somar, média, maior/menor, ranking, agrupar);
  3. FILTROS   — classe, turma, género, disciplina, trimestre, mês/ano/período, estado, tipo, limites ("mais de 10", "abaixo de 10");
  4. ÂMBITO    — cada entidade só existe no painel/perfil a que pertence, sempre dentro da escola; aluno/encarregado só o seu;
                 professor só as suas turmas e disciplinas. O resultado repete como a pergunta foi entendida.

Nada é inventado: sem registos diz que não há. Nada é escrito: só leitura.
"""
import datetime
import re
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Optional

from django.db.models import Avg, Count, F, Max, Min, Q, Sum
from django.utils import timezone

from . import capacidades as cap
from .capacidades import DIRECCAO, GESTAO, PROPRIO, ROTULO_TRIM, TRIMESTRES, _data, _lista, _nome, normalizar

LIMITE = 10
# Palavras da linguagem de consulta: nunca fazem parte do nome de um aluno (março, feminino, atraso, maior…).
PALAVRAS_PLANO = {'sexo', 'feminino', 'feminina', 'masculino', 'masculina', 'raparigas', 'rapazes', 'meninas', 'meninos', 'mulheres', 'homens', 'trimestre', 'primeiro',
                  'segundo', 'terceiro', 'maior', 'menor', 'melhor', 'pior', 'abaixo', 'acima', 'superior', 'inferior', 'media', 'total', 'valor', 'soma', 'lista', 'listar',
                  'atraso', 'atrasadas', 'atrasados', 'pendentes', 'pendente', 'pagas', 'pagos', 'pago', 'paga', 'justificadas', 'injustificadas', 'justificada', 'injustificada',
                  'resolvidos', 'abertos', 'resolvido', 'aberto', 'aprovadas', 'aprovados', 'rejeitadas', 'canceladas', 'semana', 'passado', 'passada', 'ultimo', 'janeiro',
                  'fevereiro', 'marco', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro', 'negativas', 'positivas', 'negativa',
                  'positiva', 'lotadas', 'lotada', 'ativos', 'activos', 'inativos', 'transferidos', 'evadidos', 'urgentes', 'urgente', 'saida', 'entrada', 'anulacoes',
                  'receitas', 'despesas', 'gastamos', 'recebemos', 'estudantes', 'matriculados', 'docentes', 'professores', 'turmas', 'disciplina', 'disciplinas'}
MESES = {'janeiro': 1, 'fevereiro': 2, 'marco': 3, 'abril': 4, 'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10,
         'novembro': 11, 'dezembro': 12}
NOME_MES = {v: k.capitalize() if k != 'marco' else 'Março' for k, v in MESES.items()}


# ---------------------------------------------------------------- extracção de parâmetros
def _num(txt):
    return float(txt.replace(',', '.'))


def _slots(ctx):
    t = ctx.texto
    s = {}
    m = re.search(r'\b(\d{1,2})\s*a?\s*classe', t)
    if m:
        s['classe'] = int(m.group(1))
    else:
        m = re.search(r'\b(\d{1,2})\s*a\s+([a-d])\b', t)        # "7ª A" = 7.ª classe, turma A
        if m:
            s['classe'] = int(m.group(1))
    m = (re.search(r'\bclasse\s+(?:turma\s+)?([a-d])\b', t) or re.search(r'\bturma\s+([a-d0-9])\b', t) or re.search(r'\b\d{1,2}\s*a\s+([a-d])\b', t))
    if m:
        s['turma'] = m.group(1)
    if re.search(r'\b(femin\w*|raparig\w*|menina\w*|mulher\w*|femea\w*|aluna\w*)', t):
        s['genero'] = 'F'
    elif re.search(r'\b(mascul\w*|rapaz\w*|menino\w*|homem|homens)\b', t):
        s['genero'] = 'M'
    m = re.search(r'\b([123])\s*o?\s*trimestre', t) or re.search(r'\b(primeiro|segundo|terceiro)\s+trimestre', t)
    if m:
        s['trimestre'] = {'primeiro': 1, 'segundo': 2, 'terceiro': 3}.get(m.group(1)) or int(m.group(1))
    for nome, n in MESES.items():
        if re.search(rf'\b{nome}\b', t):
            s['mes'] = n
    m = re.search(r'\b(20\d{2})\b', t)
    if m:
        s['ano'] = int(m.group(1))
    for chave, rel in ((' hoje', 'hoje'), (' ontem', 'ontem'), (' esta semana', 'semana'), (' desta semana', 'semana'), (' nesta semana', 'semana'), (' semana passada', 'semana_passada'), (' este mes', 'mes'), (' deste mes', 'mes'), (' neste mes', 'mes'),
                       (' mes passado', 'mes_passado'), (' ultimo mes', 'mes_passado'), (' este ano', 'ano'), (' deste ano', 'ano'), (' neste ano', 'ano'), (' ano passado', 'ano_passado')):
        if chave in t:
            s['relativo'] = rel
    m = re.search(r'\b(?:mais de|acima de|superior a|maior que|mais que|pelo menos|no minimo)\s+(\d+(?:[.,]\d+)?)', t)
    if m:
        s['limiar'] = ('>=' if 'pelo menos' in m.group(0) or 'no minimo' in m.group(0) else '>', _num(m.group(1)))
    m = re.search(r'\b(?:menos de|abaixo de|inferior a|menor que|menos que|no maximo)\s+(\d+(?:[.,]\d+)?)', t)
    if m:
        s['limiar'] = ('<=' if 'no maximo' in m.group(0) else '<', _num(m.group(1)))
    m = re.search(r'\bpor\s+(classe|turma|genero|sexo|disciplina|mes|estado|tipo|prioridade|canal|trimestre|aluno)\b', t)
    if m:
        s['agrupar'] = {'sexo': 'genero'}.get(m.group(1), m.group(1))
    return s


def _intervalo(s, hoje):
    """(inicio, fim, descrição) a partir de mês/ano/relativo; None se a pergunta não fala de tempo."""
    rel = s.get('relativo')
    if rel == 'hoje':
        return hoje, hoje, 'hoje'
    if rel == 'ontem':
        d = hoje - datetime.timedelta(days=1)
        return d, d, 'ontem'
    if rel == 'semana':
        ini = hoje - datetime.timedelta(days=hoje.weekday())
        return ini, ini + datetime.timedelta(days=6), 'esta semana'
    if rel == 'semana_passada':
        ini = hoje - datetime.timedelta(days=hoje.weekday() + 7)
        return ini, ini + datetime.timedelta(days=6), 'semana passada'
    if rel in ('mes', 'mes_passado') or s.get('mes'):
        if s.get('mes'):
            ano, mes = s.get('ano') or hoje.year, s['mes']
            desc = f'{NOME_MES[mes]} de {ano}'
        else:
            ano, mes = (hoje.year, hoje.month) if rel == 'mes' else ((hoje.year, hoje.month - 1) if hoje.month > 1 else (hoje.year - 1, 12))
            desc = 'este mês' if rel == 'mes' else 'mês passado'
        ini = datetime.date(ano, mes, 1)
        fim = (datetime.date(ano + (mes == 12), (mes % 12) + 1, 1)) - datetime.timedelta(days=1)
        return ini, fim, desc
    if rel in ('ano', 'ano_passado') or s.get('ano'):
        ano = s.get('ano') or (hoje.year if rel == 'ano' else hoje.year - 1)
        return datetime.date(ano, 1, 1), datetime.date(ano, 12, 31), f'{ano}' if s.get('ano') else ('este ano' if rel == 'ano' else 'ano passado')
    return None


CUES_DADOS = re.compile(r'\b(quantos|quantas|quanto|numero de|total de|valor total|soma|media|maior|menor|melhor|pior|quais|quem tem|lista|listar|ha quantos|de prioridade \w+|urgentes|que (alunos?|alunas?|professores?|disciplinas?|encarregados?|exames?|certificados?)|que turmas? \w+ d[aoe] \d+\w*|(mais|menos|abaixo|acima|inferior|superior) (de|a|que) \d+|sem turma|deste mes|este mes|do mes|este ano|neste ano|total das?)\b|\bpor (classe|turma|genero|sexo|disciplina|mes|estado|tipo|prioridade|canal|trimestre)\b')


QUANTIFICADOR = re.compile(r'\b(quantos|quantas|quanto|numero de|total de|ha quantos|media d\w+|que (exames?|alunos?|alunas?|professores?|certificados?))\b')


def tem_quantificador(texto):
    """Pede uma quantidade/soma/média (nunca um guia 'como faço…')."""
    return bool(QUANTIFICADOR.search(texto))


def tem_cue(texto):
    """A pergunta pede dados agregados (quantidade, soma, média, máximo, lista…)?"""
    return bool(CUES_DADOS.search(texto))


def _operacao(t):
    """contar | listar | somar | media | maximo | minimo | ranking | existe | None (sem sinal de operação)"""
    if re.search(r'\b(valor total|valor|soma|somado|montante|total em|quanto (?:foi|e|sao|temos|tem|recebemos|recebeu|gastamos|gastou|pagaram|pagou|devem|deve|devo|devemos|rendeu))\b', t):
        return 'somar'
    if ' media' in t:
        return 'media'
    if re.search(r'\b(maior|melhor|mais alta|mais alto|maxima|maximo)\b', t) and ' mais faltas' not in t:
        return 'maximo'
    if re.search(r'\b(menor|pior|mais baixa|mais baixo|minima|minimo)\b', t):
        return 'minimo'
    if re.search(r'\bquem tem (mais|menos)|\bque alunos? tem (mais|menos)|\bmais (faltas|negativas|propinas)\b', t):
        return 'ranking'
    if re.search(r'\b(quantos|quantas|numero de|total de|ha quantos|existem quantos)\b', t):
        return 'contar'
    if re.search(r'\b(quais|qual|que alunos?|que professores?|que turmas?|que exames?|que certificados?|que atendimentos?|que transferencias?|lista|listar|quem|nomes|mostra|mostrar|diga me os)\b', t):
        return 'listar'
    if re.search(r'\b(ha|existe|existem|tem algum|temos algum)\b', t):
        return 'existe'
    return None


def _disciplina(ctx):
    from apps.disciplinas.models import Disciplina
    nomes = {}
    for n in Disciplina.objects.filter(escola=ctx.escola).values_list('nome', flat=True).distinct():
        nn = normalizar(n).strip()
        if nn:
            nomes[nn] = n
    for nn in sorted(nomes, key=len, reverse=True):
        if f' {nn} ' in ctx.texto:
            return nomes[nn]
    toks = set(ctx.texto.split())
    candidatos = [n for nn, n in nomes.items() if any(len(p) >= 6 and p in toks for p in nn.split())]
    return candidatos[0] if len(candidatos) == 1 else None


def _regex_classe(n):
    return rf'^{n}[^0-9]'


def _desc(partes):
    return ', '.join(p for p in partes if p)


def _m(v):
    return f'{Decimal(v):.2f}'


def _numero(x):
    return f'{x:g}' if isinstance(x, (int, float)) else str(x)


def _ate_limite(itens, limite=LIMITE):
    itens = list(itens)
    return itens[:limite], max(len(itens) - limite, 0)


def _turmas_professor(ctx):
    from apps.professores.models import AlocacaoDocente
    qs = AlocacaoDocente.objects.filter(escola=ctx.escola, professor_id=getattr(ctx.user, 'professor_id', None))
    return list(qs.values_list('turma_id', 'disciplina_id'))


def _pares_professor(pares, campo_turma='turma_id', campo_disc='disciplina_id'):
    q = Q(pk__in=[])
    for t_id, d_id in pares:
        q |= Q(**{campo_turma: t_id, campo_disc: d_id})
    return q


# ---------------------------------------------------------------- entidades
def _resultado(texto, dados, destino, rotulo, especifico):
    return {'texto': texto, 'dados': dados, 'destino': destino, 'rotulo': rotulo, 'especifico': especifico}


def _agrupar_contagens(qs, campos, rotulo_fn, titulo):
    linhas = list(qs.values(*campos).annotate(n=Count('id')).order_by('-n')[:LIMITE])
    if not linhas:
        return None
    return titulo + ': ' + '; '.join(f'{rotulo_fn(r)}: {r["n"]}' for r in linhas) + '.', {'grupos': len(linhas)}


def e_alunos(ctx, op, s, aluno_obj):
    from apps.alunos.models import Aluno
    qs = Aluno.objects.filter(escola=ctx.escola)
    if ctx.role == 'PROFESSOR':
        qs = qs.filter(turma_id__in=[t for t, _d in _turmas_professor(ctx)])
    est = 'ATIVO'
    for palavra, valor in ((' transferid', 'TRANSFERIDO'), (' inativ', 'INATIVO'), (' evadid', 'EVADIDO'), (' desist', 'EVADIDO')):
        if palavra in ctx.texto:
            est = valor
    qs = qs.filter(status=est)
    desc = [f'alunos {est.lower() if est != "ATIVO" else "activos"}'] + (['nas suas turmas'] if ctx.role == 'PROFESSOR' else [])
    n_filtros = 0
    if s.get('classe'):
        qs = qs.filter(turma__grau_ano__regex=_regex_classe(s['classe']))
        desc.append(f'{s["classe"]}.ª classe')
        n_filtros += 1
    if s.get('turma'):
        qs = qs.filter(turma__nome__iexact=s['turma'])
        desc.append(f'turma {s["turma"].upper()}')
        n_filtros += 1
    if s.get('genero'):
        qs = qs.filter(genero=s['genero'])
        desc.append('género feminino' if s['genero'] == 'F' else 'género masculino')
        n_filtros += 1
    if est != 'ATIVO':
        n_filtros += 1
    entendi = f'({_desc(desc)})'
    if s.get('agrupar') in ('classe', 'turma', 'genero', 'estado'):
        campos, rot, tit = {'classe': (['turma__grau_ano'], lambda r: r['turma__grau_ano'] or 'sem turma', 'Por classe'),
                            'turma': (['turma__grau_ano', 'turma__nome'], lambda r: f"{r['turma__grau_ano']} {r['turma__nome']}" if r['turma__nome'] else 'sem turma', 'Por turma'),
                            'genero': (['genero'], lambda r: 'Feminino' if r['genero'] == 'F' else 'Masculino', 'Por género'),
                            'estado': (['status'], lambda r: r['status'].lower(), 'Por estado')}[s['agrupar']]
        g = _agrupar_contagens(qs, campos, rot, tit)
        if g:
            return _resultado(f'{g[0]} {entendi}', g[1], 'alunos', 'Abrir Alunos & Matrículas', True)
    total = qs.count()
    if op in ('listar', 'ranking') and total:
        itens, resto = _ate_limite(qs.select_related('turma').order_by('nome'))
        linhas = [f'{_nome(a)}' + (f' ({a.turma.grau_ano} {a.turma.nome})' if a.turma else '') for a in itens]
        return _resultado(f'{total} aluno(s) {entendi}: ' + '; '.join(linhas) + (f' e mais {resto}' if resto else '') + '.', {'total': total}, 'alunos',
                          'Abrir Alunos & Matrículas', True)
    if op == 'existe':
        return _resultado(('Sim' if total else 'Não') + f': {total} aluno(s) {entendi}.', {'total': total}, 'alunos', 'Abrir Alunos & Matrículas', True)
    return _resultado(f'{total} aluno(s) {entendi}.' if total else f'Não há alunos {entendi}.', {'total': total}, 'alunos', 'Abrir Alunos & Matrículas', n_filtros > 0)


def e_professores(ctx, op, s, aluno_obj):
    from apps.professores.models import AlocacaoDocente, Professor
    qs = Professor.objects.filter(escola=ctx.escola)
    desc, n_filtros = ['professores'], 0
    if s.get('genero'):
        qs = qs.filter(genero=s['genero'])
        desc.append('género feminino' if s['genero'] == 'F' else 'género masculino')
        n_filtros += 1
    aloc = AlocacaoDocente.objects.filter(escola=ctx.escola)
    if ' sem turma' in ctx.texto or ' sem atribuicao' in ctx.texto or ' sem alocacao' in ctx.texto:
        qs = qs.exclude(id__in=aloc.values_list('professor_id', flat=True))
        desc.append('sem turmas atribuídas')
        n_filtros += 1
    elif ' com turma' in ctx.texto or ' com atribuicao' in ctx.texto:
        qs = qs.filter(id__in=aloc.values_list('professor_id', flat=True))
        desc.append('com turmas atribuídas')
        n_filtros += 1
    total = qs.count()
    entendi = f'({_desc(desc)})'
    if op in ('listar', 'ranking') and total:
        itens, resto = _ate_limite(qs.order_by('nome'))
        return _resultado(f'{total} professor(es) {entendi}: ' + _lista([p.nome for p in itens], LIMITE) + (f' e mais {resto}' if resto else '') + '.', {'total': total},
                          'professores', 'Abrir Atribuição & Docentes', True)
    return _resultado(f'{total} professor(es) {entendi}.' if total else f'Não há professores {entendi}.', {'total': total}, 'professores', 'Abrir Atribuição & Docentes', n_filtros > 0)


def e_turmas(ctx, op, s, aluno_obj):
    from apps.turmas.models import Turma
    qs = Turma.objects.filter(escola=ctx.escola)
    if ctx.ano:
        qs = qs.filter(ano_letivo=ctx.ano)
    desc, n_filtros = ['turmas'], 0
    if s.get('classe'):
        qs = qs.filter(grau_ano__regex=_regex_classe(s['classe']))
        desc.append(f'{s["classe"]}.ª classe')
        n_filtros += 1
    turmas = list(qs.annotate(n=Count('alunos', filter=Q(alunos__status='ATIVO'))))
    if ' lotada' in ctx.texto or ' cheia' in ctx.texto:
        turmas = [t for t in turmas if t.n >= t.capacidade_maxima]
        desc.append('lotadas')
        n_filtros += 1
    if ' sem director' in ctx.texto or ' sem diretor' in ctx.texto:
        turmas = [t for t in turmas if not t.director_turma_id]
        desc.append('sem Director de Turma')
        n_filtros += 1
    entendi = f'({_desc(desc)})'
    if s.get('agrupar') == 'classe' and turmas:
        por = defaultdict(int)
        for t in turmas:
            por[t.grau_ano] += 1
        return _resultado('Turmas por classe: ' + '; '.join(f'{k}: {v}' for k, v in sorted(por.items())) + f' {entendi}.', {'turmas': len(turmas)}, 'turmas', 'Abrir Turmas', True)
    if op in ('listar', 'ranking') and turmas:
        itens, resto = _ate_limite(sorted(turmas, key=lambda t: (t.grau_ano, t.nome)))
        return _resultado(f'{len(turmas)} turma(s) {entendi}: ' + '; '.join(f'{t.grau_ano} {t.nome} ({t.n}/{t.capacidade_maxima})' for t in itens) + (f' e mais {resto}' if resto else '') + '.',
                          {'turmas': len(turmas)}, 'turmas', 'Abrir Turmas', True)
    return _resultado(f'{len(turmas)} turma(s) {entendi}.' if turmas else f'Não há turmas {entendi}.', {'turmas': len(turmas)}, 'turmas', 'Abrir Turmas', n_filtros > 0)


def e_pagamentos(ctx, op, s, aluno_obj):
    from apps.pagamentos.models import Pagamento
    qs = Pagamento.objects.filter(escola=ctx.escola).select_related('aluno', 'aluno__turma')
    if ctx.proprio:
        qs = qs.filter(aluno=aluno_obj)
    elif aluno_obj is not None:
        qs = qs.filter(aluno=aluno_obj)
    t = ctx.texto
    agora = timezone.now()
    desc, n_filtros, modo = ['propinas'], 0, 'valor'
    if re.search(r'\b(pag[oa]s?|liquidad\w*|recebid\w*|pagaram|pagou)\b', t) and ' nao pag' not in t and ' por pagar' not in t:
        qs = qs.filter(status='PAGO')
        desc.append('pagas')
        modo = 'valor_pago'
        n_filtros += 1
    elif re.search(r'\b(atras\w*|vencid\w*|divida\w*|devo|devemos|devem|deve|devia|devedor\w*|nao pag\w*)\b', t):
        qs = qs.filter(status__in=('PENDENTE', 'ATRASADO'), data_vencimento__lt=agora)
        desc.append('em atraso')
        modo = 'atraso'
        n_filtros += 1
    elif re.search(r'\bpendente\w*|\bpor pagar\b|\bem aberto\b', t):
        qs = qs.filter(status__in=('PENDENTE', 'ATRASADO'))
        desc.append('pendentes')
        modo = 'atraso'
        n_filtros += 1
    iv = _intervalo(s, ctx.hoje)
    if iv:
        meses = set()
        d = datetime.date(iv[0].year, iv[0].month, 1)
        while d <= iv[1]:
            meses.add(f'{d.year}-{d.month:02d}')
            d = datetime.date(d.year + (d.month == 12), (d.month % 12) + 1, 1)
        qs = qs.filter(mes_referencia__in=meses)
        desc.append(f'referentes a {iv[2]}')
        n_filtros += 1
    if s.get('classe'):
        qs = qs.filter(aluno__turma__grau_ano__regex=_regex_classe(s['classe']))
        desc.append(f'{s["classe"]}.ª classe')
        n_filtros += 1
    if s.get('turma'):
        qs = qs.filter(aluno__turma__nome__iexact=s['turma'])
        desc.append(f'turma {s["turma"].upper()}')
        n_filtros += 1
    if aluno_obj is not None and not ctx.proprio:
        desc.append(_nome(aluno_obj))
    entendi = f'({_desc(desc)})'
    linhas = list(qs)

    def valor_de(p):
        return p.valor_pago if modo == 'valor_pago' else ((p.valor - p.valor_pago) if modo == 'atraso' else p.valor)

    if s.get('agrupar') in ('turma', 'classe', 'mes', 'estado') and linhas:
        por = defaultdict(lambda: [0, Decimal('0')])
        for p in linhas:
            chave = {'turma': f'{p.aluno.turma.grau_ano} {p.aluno.turma.nome}' if p.aluno.turma else 'sem turma', 'classe': p.aluno.turma.grau_ano if p.aluno.turma else 'sem turma',
                     'mes': p.mes_referencia, 'estado': p.status.lower()}[s['agrupar']]
            por[chave][0] += 1
            por[chave][1] += valor_de(p)
        topo = sorted(por.items(), key=lambda kv: -kv[1][1])[:LIMITE]
        return _resultado(f'Propinas por {s["agrupar"]} {entendi}: ' + '; '.join(f'{k}: {n} ({v} MZN)' for k, (n, v) in topo) + '.', {'grupos': len(topo)},
                          'aluno-pagamentos' if ctx.proprio else 'pagamentos', 'Abrir as Propinas', True)
    destino, rotulo = ('aluno-pagamentos' if ctx.proprio else 'pagamentos'), 'Abrir as Propinas'
    if not linhas:
        return _resultado(f'Não há propinas {entendi}.', {'total': 0}, destino, rotulo, n_filtros > 0)
    total_valor = sum((valor_de(p) for p in linhas), Decimal('0'))
    if op == 'somar':
        return _resultado(f'Valor total: {total_valor} MZN em {len(linhas)} propina(s) {entendi}.', {'total': len(linhas), 'valor': str(total_valor)}, destino, rotulo, True)
    if op in ('listar', 'ranking') and not ctx.proprio:
        por_aluno = defaultdict(lambda: [None, Decimal('0'), 0])
        for p in linhas:
            r = por_aluno[p.aluno_id]
            r[0], r[1], r[2] = p.aluno, r[1] + valor_de(p), r[2] + 1
        topo, resto = _ate_limite(sorted(por_aluno.values(), key=lambda r: -r[1]))
        return _resultado(f'{len(por_aluno)} aluno(s) {entendi}: ' + '; '.join(f'{_nome(a)}: {v} MZN ({n} mês(es))' for a, v, n in topo) + (f' e mais {resto}' if resto else '') + '.',
                          {'alunos': len(por_aluno), 'valor': str(total_valor)}, destino, rotulo, True)
    if ' aluno' in t and not ctx.proprio and op in ('contar', 'existe'):
        n = len({p.aluno_id for p in linhas})
        return _resultado(f'{n} aluno(s) {entendi}.', {'alunos': n}, destino, rotulo, n_filtros > 0)
    if op == 'existe':
        return _resultado(f'Sim: {len(linhas)} propina(s) {entendi}.', {'total': len(linhas)}, destino, rotulo, True)
    return _resultado(f'{len(linhas)} propina(s) {entendi}, no valor de {total_valor} MZN.', {'total': len(linhas), 'valor': str(total_valor)}, destino, rotulo, n_filtros > 0)


def e_faltas(ctx, op, s, aluno_obj):
    from apps.alunos.models import PresencaAluno
    qs = PresencaAluno.objects.filter(escola=ctx.escola, status__in=('FALTA_JUSTIFICADA', 'FALTA_INJUSTIFICADA')).select_related('aluno', 'aluno__turma')
    if ctx.proprio or aluno_obj is not None:
        qs = qs.filter(aluno=aluno_obj)
    if ctx.role == 'PROFESSOR':
        qs = qs.filter(_pares_professor(_turmas_professor(ctx)))
    desc, n_filtros = ['faltas efectivas'] + (['nas suas turmas'] if ctx.role == 'PROFESSOR' else []), 0
    if ' injustificad' in ctx.texto or ' por justificar' in ctx.texto or ' nao justificad' in ctx.texto:
        qs = qs.filter(status='FALTA_INJUSTIFICADA')
        desc = ['faltas injustificadas']
        n_filtros += 1
    elif ' justificad' in ctx.texto:
        qs = qs.filter(aulas_justificadas__gt=0)
        desc = ['faltas com justificação']
        n_filtros += 1
    if ctx.ano:
        qs = qs.filter(turma__ano_letivo=ctx.ano)
    iv = _intervalo(s, ctx.hoje)
    if iv:
        qs = qs.filter(data__gte=iv[0], data__lte=iv[1])
        desc.append(iv[2])
        n_filtros += 1
    if s.get('classe'):
        qs = qs.filter(turma__grau_ano__regex=_regex_classe(s['classe']))
        desc.append(f'{s["classe"]}.ª classe')
        n_filtros += 1
    if s.get('turma'):
        qs = qs.filter(turma__nome__iexact=s['turma'])
        desc.append(f'turma {s["turma"].upper()}')
        n_filtros += 1
    disc = _disciplina(ctx)
    if disc:
        qs = qs.filter(disciplina__nome__iexact=disc)
        desc.append(disc)
        n_filtros += 1
    if s.get('genero'):
        qs = qs.filter(aluno__genero=s['genero'])
        desc.append('género feminino' if s['genero'] == 'F' else 'género masculino')
        n_filtros += 1
    if aluno_obj is not None and not ctx.proprio:
        desc.append(_nome(aluno_obj))
    entendi = f'({_desc(desc)})'
    destino = 'aluno-faltas' if ctx.proprio else 'presencas'
    por_aluno = defaultdict(lambda: [None, 0])
    for p in qs:
        r = por_aluno[p.aluno_id]
        r[0] = p.aluno
        r[1] += (p.aulas_justificadas if ' justificad' in ctx.texto and ' injustificad' not in ctx.texto and ' nao justificad' not in ctx.texto and ' por justificar' not in ctx.texto
                 else max(p.aulas - p.aulas_justificadas, 0))
    total = sum(v for _a, v in por_aluno.values())
    if not total:
        return _resultado(f'Não há faltas {entendi}.', {'faltas': 0}, destino, 'Abrir as Faltas', n_filtros > 0)
    lim = s.get('limiar')
    if lim and not ctx.proprio:
        ops = {'>': lambda x, v: x > v, '>=': lambda x, v: x >= v, '<': lambda x, v: x < v, '<=': lambda x, v: x <= v}
        sel = [(a, v) for a, v in por_aluno.values() if ops[lim[0]](v, lim[1])]
        topo, resto = _ate_limite(sorted(sel, key=lambda r: -r[1]))
        txt = f'{len(sel)} aluno(s) com {"mais" if lim[0] in (">", ">=") else "menos"} de {_numero(lim[1])} faltas {entendi}'
        if topo:
            txt += ': ' + '; '.join(f'{_nome(a)}: {v}' for a, v in topo) + (f' e mais {resto}' if resto else '')
        return _resultado(txt + '.', {'alunos': len(sel)}, destino, 'Abrir as Faltas', True)
    if op in ('ranking', 'listar') and not ctx.proprio:
        crescente = ' menos ' in ctx.texto and ' mais ' not in ctx.texto
        topo, _ = _ate_limite(sorted(por_aluno.values(), key=lambda r: r[1] if crescente else -r[1]), 5)
        return _resultado(f'Alunos com {"menos" if crescente else "mais"} faltas {entendi}: ' + '; '.join(f'{_nome(a)}: {v}' for a, v in topo) + '.',
                          {'alunos': len(por_aluno), 'faltas': total}, destino, 'Abrir as Faltas', True)
    if s.get('agrupar') in ('turma', 'classe', 'disciplina', 'genero') and not ctx.proprio:
        por = defaultdict(int)
        for p in qs:
            chave = {'turma': f'{p.turma.grau_ano} {p.turma.nome}', 'classe': p.turma.grau_ano, 'disciplina': p.disciplina.nome if p.disciplina else 'sem disciplina',
                     'genero': 'Feminino' if p.aluno.genero == 'F' else 'Masculino'}[s['agrupar']]
            por[chave] += max(p.aulas - p.aulas_justificadas, 0)
        topo = sorted(por.items(), key=lambda kv: -kv[1])[:LIMITE]
        return _resultado(f'Faltas por {s["agrupar"]} {entendi}: ' + '; '.join(f'{k}: {v}' for k, v in topo) + '.', {'faltas': total}, destino, 'Abrir as Faltas', True)
    if ' aluno' in ctx.texto and not ctx.proprio and op in ('contar', 'existe'):
        return _resultado(f'{len(por_aluno)} aluno(s) com faltas {entendi} ({total} faltas no total).', {'alunos': len(por_aluno), 'faltas': total}, destino, 'Abrir as Faltas', n_filtros > 0)
    return _resultado(f'{total} falta(s) {entendi}.', {'faltas': total}, destino, 'Abrir as Faltas', n_filtros > 0)


def e_notas(ctx, op, s, aluno_obj):
    from apps.notas.models import Nota
    qs = Nota.objects.filter(escola=ctx.escola, media_final__gt=0).select_related('aluno', 'disciplina', 'turma')
    if ctx.ano:
        qs = qs.filter(turma__ano_letivo=ctx.ano)
    if ctx.proprio:
        periodos, permitido = cap._trimestres_visiveis(ctx)
        if not permitido or not periodos:
            return _resultado('A visualização de notas está suspensa pela Direcção da escola neste momento.', {'publicado': False}, 'aluno-notas', 'Abrir as Notas', True)
        qs = qs.filter(aluno=aluno_obj, periodo__in=periodos)
    elif aluno_obj is not None:
        qs = qs.filter(aluno=aluno_obj)
    if ctx.role == 'PROFESSOR':
        qs = qs.filter(_pares_professor(_turmas_professor(ctx)))
    desc, n_filtros = ['notas'] + (['nas suas turmas'] if ctx.role == 'PROFESSOR' else []), 0
    if s.get('trimestre'):
        qs = qs.filter(periodo=TRIMESTRES[s['trimestre'] - 1])
        desc.append(f'{s["trimestre"]}.º trimestre')
        n_filtros += 1
    else:
        ultimo = next((p for p in reversed(TRIMESTRES) if qs.filter(periodo=p).exists()), None)
        if ultimo:
            qs = qs.filter(periodo=ultimo)
            desc.append(f'último trimestre com notas ({ROTULO_TRIM[ultimo]})')
    disc = _disciplina(ctx)
    if disc:
        qs = qs.filter(disciplina__nome__iexact=disc)
        desc.append(disc)
        n_filtros += 1
    if s.get('classe'):
        qs = qs.filter(turma__grau_ano__regex=_regex_classe(s['classe']))
        desc.append(f'{s["classe"]}.ª classe')
        n_filtros += 1
    if s.get('turma'):
        qs = qs.filter(turma__nome__iexact=s['turma'])
        desc.append(f'turma {s["turma"].upper()}')
        n_filtros += 1
    if s.get('genero'):
        qs = qs.filter(aluno__genero=s['genero'])
        desc.append('género feminino' if s['genero'] == 'F' else 'género masculino')
        n_filtros += 1
    if aluno_obj is not None and not ctx.proprio:
        desc.append(_nome(aluno_obj))
    lim = s.get('limiar')
    t = ctx.texto
    if lim:
        campo = {'>': 'media_final__gt', '>=': 'media_final__gte', '<': 'media_final__lt', '<=': 'media_final__lte'}[lim[0]]
        qs = qs.filter(**{campo: lim[1]})
        desc.append(f'{"acima" if lim[0] in (">", ">=") else "abaixo"} de {_numero(lim[1])}')
        n_filtros += 1
    elif re.search(r'\bnegativ\w*|\breprov\w*|\bchumb\w*', t):
        qs = qs.filter(media_final__lt=9.5)
        desc.append('negativas')
        n_filtros += 1
    elif re.search(r'\bpositiv\w*|\baprov\w*', t):
        qs = qs.filter(media_final__gte=9.5)
        desc.append('positivas')
        n_filtros += 1
    entendi = f'({_desc(desc)})'
    destino = 'aluno-notas' if ctx.proprio else 'caderneta'
    n = qs.count()
    if not n:
        return _resultado(f'Não há notas {entendi}.', {'notas': 0}, destino, 'Abrir as Notas', n_filtros > 0)
    if s.get('agrupar') in ('disciplina', 'turma', 'classe'):
        campos = {'disciplina': ['disciplina__nome'], 'turma': ['turma__grau_ano', 'turma__nome'], 'classe': ['turma__grau_ano']}[s['agrupar']]
        linhas = list(qs.values(*campos).annotate(n=Count('id'), m=Avg('media_final')).order_by('m')[:LIMITE])
        rot = lambda r: ' '.join(str(r[c]) for c in campos)
        return _resultado(f'Média por {s["agrupar"]} {entendi}: ' + '; '.join(f'{rot(r)}: {r["m"]:.1f} ({r["n"]})' for r in linhas) + '.', {'grupos': len(linhas)}, destino, 'Abrir as Notas', True)
    if op == 'media':
        m = qs.aggregate(v=Avg('media_final'))['v']
        return _resultado(f'Média: {m:.1f} em {n} nota(s) {entendi}.', {'media': round(m, 1), 'notas': n}, destino, 'Abrir as Notas', True)
    if op in ('maximo', 'minimo'):
        ordem = '-media_final' if op == 'maximo' else 'media_final'
        extremo = qs.order_by(ordem).first()
        quem = '' if ctx.proprio else f' ({_nome(extremo.aluno)}, {extremo.disciplina.nome})' if aluno_obj is None else f' ({extremo.disciplina.nome})'
        return _resultado(f'{"Maior" if op == "maximo" else "Menor"} nota {entendi}: {extremo.media_final:g}{quem}.', {'nota': extremo.media_final}, destino, 'Abrir as Notas', True)
    if op in ('listar', 'ranking') and not ctx.proprio:
        crescente = bool(lim and lim[0] in ('<', '<=')) or bool(re.search(r'\bnegativ\w*|\bpior\w*', t))
        topo, resto = _ate_limite(qs.order_by('media_final' if crescente else '-media_final'))
        linhas = [f'{_nome(r.aluno)}: {r.media_final:g}' + (f' ({r.disciplina.nome})' if not disc else '') for r in topo]
        return _resultado(f'{n} nota(s) {entendi}: ' + '; '.join(linhas) + (f' e mais {resto}' if resto else '') + '.', {'notas': n}, destino, 'Abrir as Notas', True)
    if ' aluno' in t and not ctx.proprio and op in ('contar', 'existe'):
        na = qs.values('aluno').distinct().count()
        return _resultado(f'{na} aluno(s) {entendi}.', {'alunos': na}, destino, 'Abrir as Notas', n_filtros > 0)
    if op == 'existe':
        return _resultado(f'Sim: {n} nota(s) {entendi}.', {'notas': n}, destino, 'Abrir as Notas', True)
    if ctx.proprio and not lim and not disc and n_filtros == 0:
        itens = sorted((r.disciplina.nome, r.media_final) for r in qs)
        return _resultado('Notas ' + entendi + ': ' + _lista([f'{d} {m:g}' for d, m in itens], 12) + '.', {'notas': n}, destino, 'Abrir as Notas', False)
    return _resultado(f'{n} nota(s) {entendi}.', {'notas': n}, destino, 'Abrir as Notas', n_filtros > 0)


def e_transferencias(ctx, op, s, aluno_obj):
    from apps.alunos.models import TransferenciaAnulacao
    qs = TransferenciaAnulacao.objects.filter(escola=ctx.escola).select_related('aluno')
    t = ctx.texto
    desc, n_filtros = ['transferências e anulações'], 0
    for palavra, tipo, rot in ((' saida', 'TRANSFERENCIA_SAIDA', 'de saída'), (' entrada', 'TRANSFERENCIA_ENTRADA', 'de entrada'), (' anulac', 'ANULACAO_MATRICULA', 'anulações de matrícula')):
        if palavra in t:
            qs = qs.filter(tipo=tipo)
            desc = [f'transferências {rot}' if tipo != 'ANULACAO_MATRICULA' else rot]
            n_filtros += 1
            break
    for palavra, est, rot in ((' pendente', 'PENDENTE', 'pendentes'), (' aprovad', 'APROVADO', 'aprovadas'), (' rejeitad', 'REJEITADO', 'rejeitadas'), (' cancelad', 'CANCELADO', 'canceladas')):
        if palavra in t:
            qs = qs.filter(status=est)
            desc.append(rot)
            n_filtros += 1
            break
    iv = _intervalo(s, ctx.hoje)
    if iv:
        qs = qs.filter(data_solicitacao__gte=iv[0], data_solicitacao__lte=iv[1])
        desc.append(iv[2])
        n_filtros += 1
    if aluno_obj is not None:
        qs = qs.filter(aluno=aluno_obj)
        desc.append(_nome(aluno_obj))
    entendi = f'({_desc(desc)})'
    n = qs.count()
    if op in ('listar', 'ranking') and n:
        itens, resto = _ate_limite(qs.order_by('-data_solicitacao'))
        return _resultado(f'{n} processo(s) {entendi}: ' + '; '.join(f'{_nome(r.aluno)} — {r.get_tipo_display()} ({r.get_status_display()}) a {_data(r.data_solicitacao)}' for r in itens) + (f' e mais {resto}' if resto else '') + '.',
                          {'total': n}, 'transferencias', 'Abrir Transferências & Anulações', True)
    if s.get('agrupar') in ('tipo', 'estado') and n:
        campo = 'tipo' if s['agrupar'] == 'tipo' else 'status'
        linhas = list(qs.values(campo).annotate(c=Count('id')).order_by('-c'))
        return _resultado(f'Por {s["agrupar"]} {entendi}: ' + '; '.join(f'{r[campo]}: {r["c"]}' for r in linhas) + '.', {'total': n}, 'transferencias', 'Abrir Transferências & Anulações', True)
    return _resultado(f'{n} processo(s) {entendi}.' if n else f'Não há processos {entendi}.', {'total': n}, 'transferencias', 'Abrir Transferências & Anulações', n_filtros > 0)


def e_atendimentos(ctx, op, s, aluno_obj):
    from apps.crm.models import Atendimento
    qs = Atendimento.objects.filter(escola=ctx.escola).select_related('aluno')
    t = ctx.texto
    desc, n_filtros = ['atendimentos'], 0
    for palavra, est, rot in ((' resolvid', 'RESOLVIDO', 'resolvidos'), (' em curso', 'EM_CURSO', 'em curso'), (' abert', 'ABERTO', 'abertos')):
        if palavra in t:
            qs = qs.filter(estado=est)
            desc.append(rot)
            n_filtros += 1
            break
    for palavra, pri in ((' prioridade alta', 'ALTA'), (' urgente', 'ALTA'), (' prioridade baixa', 'BAIXA'), (' prioridade normal', 'NORMAL')):
        if palavra in t:
            qs = qs.filter(prioridade=pri)
            desc.append(f'prioridade {pri.lower()}')
            n_filtros += 1
            break
    for palavra, canal in ((' telefone', 'TELEFONE'), (' presencial', 'PRESENCIAL'), (' email', 'EMAIL'), (' aplicacao', 'APP')):
        if palavra in t:
            qs = qs.filter(canal=canal)
            desc.append(f'canal {canal.lower()}')
            n_filtros += 1
            break
    iv = _intervalo(s, ctx.hoje)
    if iv:
        qs = qs.filter(created_at__date__gte=iv[0], created_at__date__lte=iv[1])
        desc.append(iv[2])
        n_filtros += 1
    entendi = f'({_desc(desc)})'
    n = qs.count()
    if op in ('listar', 'ranking') and n:
        itens, resto = _ate_limite(qs.order_by('-created_at'))
        return _resultado(f'{n} atendimento(s) {entendi}: ' + '; '.join(f'{a.assunto} ({a.get_estado_display()})' for a in itens) + (f' e mais {resto}' if resto else '') + '.', {'total': n}, 'crm', 'Abrir o CRM Escolar', True)
    if s.get('agrupar') in ('estado', 'prioridade', 'canal') and n:
        campo = {'estado': 'estado', 'prioridade': 'prioridade', 'canal': 'canal'}[s['agrupar']]
        linhas = list(qs.values(campo).annotate(c=Count('id')).order_by('-c'))
        return _resultado(f'Por {s["agrupar"]} {entendi}: ' + '; '.join(f'{r[campo].lower()}: {r["c"]}' for r in linhas) + '.', {'total': n}, 'crm', 'Abrir o CRM Escolar', True)
    return _resultado(f'{n} atendimento(s) {entendi}.' if n else f'Não há atendimentos {entendi}.', {'total': n}, 'crm', 'Abrir o CRM Escolar', n_filtros > 0)


def e_pautas(ctx, op, s, aluno_obj):
    from apps.pautas.models import Pauta
    qs = Pauta.objects.filter(escola=ctx.escola).select_related('turma')
    if ctx.ano:
        qs = qs.filter(ano_letivo=ctx.ano)
    t = ctx.texto
    desc, n_filtros = ['pautas'], 0
    for palavra, st, rot in ((' fechad', 'FECHADA', 'fechadas'), (' consolid', 'EM_CONSOLIDACAO', 'em consolidação'), (' abert', 'ABERTA', 'abertas'), (' por fechar', None, 'por fechar')):
        if palavra in t:
            qs = qs.filter(status=st) if st else qs.exclude(status='FECHADA')
            desc.append(rot)
            n_filtros += 1
            break
    if s.get('classe'):
        qs = qs.filter(turma__grau_ano__regex=_regex_classe(s['classe']))
        desc.append(f'{s["classe"]}.ª classe')
        n_filtros += 1
    if s.get('turma'):
        qs = qs.filter(turma__nome__iexact=s['turma'])
        desc.append(f'turma {s["turma"].upper()}')
        n_filtros += 1
    entendi = f'({_desc(desc)})'
    n = qs.count()
    if op in ('listar', 'ranking') and n:
        itens, resto = _ate_limite(qs.order_by('turma__grau_ano', 'turma__nome'))
        return _resultado(f'{n} pauta(s) {entendi}: ' + '; '.join(f'{p.turma.grau_ano} {p.turma.nome} ({p.get_periodo_display() if hasattr(p, "get_periodo_display") else p.periodo}, {p.status.lower()})' for p in itens) + (f' e mais {resto}' if resto else '') + '.',
                          {'total': n}, 'pautas', 'Abrir Pautas & Actas', True)
    return _resultado(f'{n} pauta(s) {entendi}.' if n else f'Não há pautas {entendi}.', {'total': n}, 'pautas', 'Abrir Pautas & Actas', n_filtros > 0)


def e_movimentos(ctx, op, s, aluno_obj):
    from apps.pagamentos.models import TransacaoFinanceira
    qs = TransacaoFinanceira.objects.filter(escola=ctx.escola)
    t = ctx.texto
    desc, n_filtros = ['movimentos'], 0
    if re.search(r'\b(receita\w*|entrada\w*|recebemos|recebeu)\b', t):
        qs = qs.filter(tipo='RECEITA')
        desc = ['receitas']
        n_filtros += 1
    elif re.search(r'\b(despesa\w*|saida\w*|gasto\w*|gastamos|gastou)\b', t):
        qs = qs.filter(tipo='DESPESA')
        desc = ['despesas']
        n_filtros += 1
    if ' pendente' in t or ' por aprovar' in t:
        qs = qs.filter(status_aprovacao='PENDENTE')
        desc.append('pendentes de aprovação')
        n_filtros += 1
    elif ' rejeitad' in t:
        qs = qs.filter(status_aprovacao='REJEITADO')
        desc.append('rejeitados')
        n_filtros += 1
    else:
        qs = qs.filter(status_aprovacao='APROVADO_DIRECTOR')
        desc.append('aprovados')
    iv = _intervalo(s, ctx.hoje)
    if iv:
        qs = qs.filter(data__gte=iv[0], data__lte=iv[1])
        desc.append(iv[2])
        n_filtros += 1
    entendi = f'({_desc(desc)})'
    n = qs.count()
    if not n:
        return _resultado(f'Não há movimentos {entendi}.', {'total': 0}, 'despesas', 'Abrir Receitas & Despesas', n_filtros > 0)
    total = qs.aggregate(v=Sum('valor'))['v'] or Decimal('0')
    if op in ('listar', 'ranking'):
        itens, resto = _ate_limite(qs.order_by('-valor'))
        return _resultado(f'{n} movimento(s) {entendi}, {total:.2f} MZN: ' + '; '.join(f'{m.descricao} {m.valor} MZN' for m in itens) + (f' e mais {resto}' if resto else '') + '.',
                          {'total': n, 'valor': _m(total)}, 'despesas', 'Abrir Receitas & Despesas', True)
    if s.get('agrupar') in ('mes', 'tipo'):
        por = defaultdict(Decimal)
        for m in qs:
            por[f'{m.data.year}-{m.data.month:02d}' if s['agrupar'] == 'mes' else m.tipo.lower()] += m.valor
        return _resultado(f'Por {s["agrupar"]} {entendi}: ' + '; '.join(f'{k}: {v:.2f} MZN' for k, v in sorted(por.items())) + '.', {'total': n}, 'despesas', 'Abrir Receitas & Despesas', True)
    return _resultado(f'{n} movimento(s) {entendi}: {total:.2f} MZN.', {'total': n, 'valor': _m(total)}, 'despesas', 'Abrir Receitas & Despesas', n_filtros > 0)


def e_certificados(ctx, op, s, aluno_obj):
    from apps.certificados.models import Certificado
    qs = Certificado.objects.filter(escola=ctx.escola)
    desc, n_filtros = ['certificados e declarações emitidos'], 0
    iv = _intervalo(s, ctx.hoje)
    if iv:
        qs = qs.filter(emitido_em__date__gte=iv[0], emitido_em__date__lte=iv[1])
        desc.append(iv[2])
        n_filtros += 1
    if aluno_obj is not None:
        qs = qs.filter(aluno=aluno_obj)
        desc.append(_nome(aluno_obj))
    n = qs.count()
    return _resultado(f'{n} {_desc(desc)}.' if n else f'Não há {_desc(desc)}.', {'total': n}, 'certificados', 'Abrir Certificados & Declarações', n_filtros > 0)


def e_exames(ctx, op, s, aluno_obj):
    from apps.notas.models import CalendarioExame
    qs = CalendarioExame.objects.filter(escola=ctx.escola)
    if ctx.ano:
        qs = qs.filter(ano_letivo=ctx.ano)
    desc, n_filtros = ['exames'], 0
    iv = _intervalo(s, ctx.hoje)
    if iv:
        qs = qs.filter(data__gte=iv[0], data__lte=iv[1])
        desc.append(iv[2])
        n_filtros += 1
    else:
        qs = qs.filter(data__gte=ctx.hoje)
        desc.append('a partir de hoje')
    classe = s.get('classe')
    if ctx.proprio and aluno_obj is not None and aluno_obj.classe:
        m = re.search(r'\d+', aluno_obj.classe)
        classe = int(m.group()) if m else classe
    if classe:
        qs = qs.filter(classe__regex=_regex_classe(classe))
        desc.append(f'{classe}.ª classe')
        n_filtros += 1
    disc = _disciplina(ctx)
    if disc:
        qs = qs.filter(disciplina__iexact=disc)
        desc.append(disc)
        n_filtros += 1
    entendi = f'({_desc(desc)})'
    destino = 'aluno-calendario' if ctx.proprio else 'calendario-exames'
    n = qs.count()
    if not n:
        return _resultado(f'Não há exames {entendi}.', {'total': 0}, destino, 'Abrir o Calendário dos Exames', n_filtros > 0)
    itens, resto = _ate_limite(qs.order_by('data', 'hora_inicio'))
    return _resultado(f'{n} exame(s) {entendi}: ' + '; '.join(f'{_data(e.data)} {e.hora_inicio:%H:%M} — {e.classe}, {e.disciplina} ({e.epoca}.ª época)' for e in itens) + (f' e mais {resto}' if resto else '') + '.',
                      {'total': n}, destino, 'Abrir o Calendário dos Exames', True)


@dataclass
class Entidade:
    nome: str
    chaves: tuple
    modulos: tuple
    perfis: Optional[set]
    executar: Callable
    modulo_proprio: Optional[str] = None
    proprio_cap: Optional[str] = None     # capacidade usada para validar o aluno/educando de perfis próprios
    aceita_aluno: bool = False            # a pergunta pode referir um aluno pelo nome (perfis de gestão/professor)


ENTIDADES = [
    Entidade('faltas', ('falta', 'faltou', 'faltaram', 'faltar', 'ausencia', 'ausente', 'assiduidade'), ('presencas',), GESTAO | {'PROFESSOR'} | PROPRIO, e_faltas,
             'aluno-faltas', 'faltas', True),
    Entidade('notas', ('nota', 'negativa', 'positiva', 'media', 'classificacao', 'avaliacao', 'reprovado', 'aprovado', 'chumbado', 'teste'), ('caderneta',),
             DIRECCAO | {'DAP', 'PROFESSOR'} | PROPRIO, e_notas, 'aluno-notas', 'notas', True),
    Entidade('pagamentos', ('propina', 'mensalidade', 'pagamento', 'devedor', 'divida', 'devo', 'devem', 'deve', 'cobranca', 'liquidado', 'recebido', 'pago', 'pagaram', 'paga'), ('pagamentos',),
             DIRECCAO | {'FINANCEIRO', 'SECRETARIA', 'CHEFE_SECRETARIA'} | PROPRIO, e_pagamentos, 'aluno-pagamentos', 'propinas', True),
    Entidade('transferencias', ('transferencia', 'anulacao'), ('transferencias',), GESTAO | {'FINANCEIRO'}, e_transferencias, None, None, True),
    Entidade('atendimentos', ('atendimento', 'reclamacao'), ('crm',), GESTAO, e_atendimentos),
    Entidade('pautas', ('pauta', 'acta'), ('pautas',), GESTAO, e_pautas),
    Entidade('movimentos', ('receita', 'despesa', 'movimento', 'gasto', 'gastamos', 'recebemos', 'saldo', 'caixa'), ('despesas',), DIRECCAO | {'FINANCEIRO'}, e_movimentos),
    Entidade('certificados', ('certificado', 'declaracao'), ('certificados',), GESTAO, e_certificados, None, None, True),
    Entidade('exames', ('exame', 'epoca', 'juri'), ('calendario-exames', 'exames'), GESTAO | {'PROFESSOR'} | PROPRIO, e_exames, 'aluno-calendario', None),
    Entidade('professores', ('professor', 'docente'), ('professores',), DIRECCAO | {'DAP', 'SECRETARIA', 'CHEFE_SECRETARIA'}, e_professores),
    Entidade('alunos', ('aluno', 'aluna', 'estudante', 'matriculado', 'rapaz', 'raparig', 'menino', 'menina', 'educando'), ('alunos', 'caderneta'), GESTAO | {'FINANCEIRO', 'PROFESSOR'}, e_alunos),
    Entidade('turmas', ('turmas',), ('turmas',), GESTAO, e_turmas),
]


def entidade_permitida(ent, role, modulos):
    if ent.perfis is not None and role not in ent.perfis:
        return False
    if role in PROPRIO:
        return bool(ent.modulo_proprio) and ent.modulo_proprio in modulos
    return any(m in modulos for m in ent.modulos)


def _entidades_da_pergunta(ctx):
    """Entidades mencionadas, da mais para a menos provável (nº de palavras-chave; empate: ordem de prioridade)."""
    toks = set(cap.canon(ctx.texto).split()) | set(ctx.texto.split())
    out = []
    for ordem, ent in enumerate(ENTIDADES):
        if ent.nome == 'turmas':
            n = 1 if (' turmas ' in ctx.texto or ' que turma' in ctx.texto or ' qual turma' in ctx.texto) else 0
        else:
            n = sum(1 for c in ent.chaves if c in toks)
        if n:
            out.append((-n, ordem, ent))
    out.sort(key=lambda x: (x[0], x[1]))
    return [e for _n, _o, e in out]


def tentar(ctx, modulos, aluno_id, em_plataforma=False):
    """Interpreta a pergunta como consulta paramétrica.

    Devolve None (não é uma consulta), {'tipo': 'bloqueado'} (fala de dados que não pertencem ao painel),
    {'tipo': 'pede_aluno', ...}, {'tipo': 'resposta', 'nome', 'resultado', 'aluno', 'especifico'}.
    """
    if em_plataforma or ctx.escola is None:
        return None
    candidatas = _entidades_da_pergunta(ctx)
    if not candidatas:
        return None
    permitidas = [e for e in candidatas if entidade_permitida(e, ctx.role, modulos)]
    if not permitidas:
        return {'tipo': 'bloqueado'}
    ent = permitidas[0]
    if candidatas[0] is not ent and candidatas[0] not in permitidas:
        # a entidade mais provável não é deste painel: não "adivinha" outra (por segurança, recusa)
        return {'tipo': 'bloqueado'}
    s = _slots(ctx)
    op_explicita = _operacao(ctx.texto)
    op = op_explicita or 'contar'
    if ctx.role in PROPRIO and ent.nome != 'exames' and (s.get('classe') or s.get('turma') or s.get('genero') or s.get('agrupar')
                                                          or any(w in ctx.texto for w in (' colega', ' turma ', ' escola ', ' todos os alunos', ' outros alunos', ' da classe', ' toda a', ' alunos em ', ' alunos com ', ' quem tem ', ' quem e o ', ' quem sao ', ' que alunos')) or op_explicita in ('ranking',)):
        return {'tipo': 'bloqueado'}      # estatísticas de turma/escola não são do painel do aluno nem do encarregado
    if ctx.role == 'PROFESSOR' and ent.nome == 'alunos' and not (s.get('classe') or s.get('turma')) and any(w in ctx.texto for w in (' temos', ' escola', ' todos')):
        return {'tipo': 'bloqueado'}      # o professor só vê os alunos das suas turmas, não o total da escola
    aluno_obj = None
    from . import engine
    if ctx.role in PROPRIO and ent.proprio_cap:
        if ctx.role == 'ENCARREGADO' and not aluno_id:
            achado, ambiguos = engine.aluno_pelo_nome(ctx, None)
            if ambiguos:
                return {'tipo': 'ambiguo', 'nome': f'consulta_{ent.nome}', 'candidatos': ambiguos}
            if achado is not None:
                aluno_id = str(achado.id)
        aluno_obj, erro = engine.resolver_aluno(ctx, cap.POR_NOME[ent.proprio_cap], aluno_id)
        if erro == 'precisa_aluno':
            return {'tipo': 'pede_aluno', 'nome': f'consulta_{ent.nome}'}
        if erro:
            return {'tipo': 'erro', 'nome': f'consulta_{ent.nome}', 'erro': erro}
    elif ctx.role in PROPRIO:
        if ent.nome == 'exames':
            aluno_obj, _erro = engine.resolver_aluno(ctx, cap.POR_NOME['faltas'], aluno_id)
            if _erro == 'precisa_aluno':
                return {'tipo': 'pede_aluno', 'nome': 'consulta_exames'}
    elif ent.aceita_aluno:
        achado, ambiguos = engine.aluno_pelo_nome(ctx, None)
        if ambiguos:
            return {'tipo': 'ambiguo', 'nome': f'consulta_{ent.nome}', 'candidatos': ambiguos}
        if achado is not None:
            if ent.proprio_cap:
                aluno_obj, erro = engine.resolver_aluno(ctx, cap.POR_NOME[ent.proprio_cap], str(achado.id))   # revalida o âmbito do perfil
                if erro:
                    return {'tipo': 'erro', 'nome': f'consulta_{ent.nome}', 'erro': erro}
            else:
                aluno_obj = achado
        elif aluno_id and ent.proprio_cap:
            aluno_obj, erro = engine.resolver_aluno(ctx, cap.POR_NOME[ent.proprio_cap], aluno_id)
            if erro:
                return {'tipo': 'erro', 'nome': f'consulta_{ent.nome}', 'erro': erro}
    if aluno_obj is not None and ctx.role not in PROPRIO and not s and not op_explicita:
        return None      # pergunta sobre um aluno concreto sem filtros: a capacidade com o detalhe do aluno responde melhor
    if aluno_id and ctx.role not in PROPRIO and not s and ent.nome in ('notas', 'faltas', 'pagamentos'):
        return None
    resultado = ent.executar(ctx, op, s, aluno_obj)
    if ent.nome in ('turmas',) and not s and not resultado.get('especifico'):
        return None      # panorama das turmas: a capacidade dedicada já o apresenta
    if not (op_explicita or s or (resultado.get('especifico') and ent.nome == 'atendimentos')):
        return None      # sem operação, sem filtros e sem pistas: só tinha uma palavra solta ("receita de bolo"), não é uma consulta
    return {'tipo': 'resposta', 'nome': f'consulta_{ent.nome}', 'resultado': resultado, 'aluno': aluno_obj, 'especifico': resultado.get('especifico', False),
            'avancada': bool(s) or op_explicita in ('ranking', 'maximo', 'minimo', 'media', 'somar')}
