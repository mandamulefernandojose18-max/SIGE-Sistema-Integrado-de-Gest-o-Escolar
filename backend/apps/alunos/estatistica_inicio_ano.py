"""Mapa Estatístico de Início do Ano Lectivo (levantamento de 03/03).

Três níveis, encadeados automaticamente (nada é digitado à mão):
  * turma  -> a partir dos alunos matriculados na turma (dados da ficha de matrícula);
  * classe -> soma dos mapas das turmas da classe;
  * escola -> soma dos mapas das classes, em três grupos: 1º Ciclo, 2º Ciclo e 1º + 2º Ciclos.

Para o 2º Ciclo (10ª a 12ª) acresce a parte das disciplinas (por secção/área), pois nestas classes
o plano é organizado por área e por disciplina.
Só contam alunos com estado ATIVO matriculados em turmas do ano lectivo pedido (isolamento por escola).
"""
from collections import defaultdict

from apps.disciplinas import plano

ROTULO_ORFANDADE = [('PAI', 'Órfãos de pai'), ('MAE', 'Órfãos de mãe'), ('AMBOS', 'Órfãos de pai e mãe')]
ROTULO_NEE = [
    ('DV', 'Deficiência visual'), ('DAU', 'Deficiência auditiva'), ('DFM', 'Deficiência física/motora'),
    ('DAP', 'Dificuldades de aprendizagem'), ('ALB', 'Albinismo'), ('PC', 'Problemas comportamentais'),
    ('OUTRA', 'Outras necessidades'),
]
ROTULO_TRANSPORTE = [
    ('A_PE', 'A pé'), ('BICICLETA', 'Bicicleta'), ('MOTORIZADA', 'Motorizada'),
    ('TRANSPORTE_PUBLICO', 'Transporte público'), ('CARRO', 'Carro particular'), ('OUTRO', 'Outro'),
]
ROTULO_TEMPO = [
    ('ATE_30', 'Até 30 minutos'), ('DE_30_A_60', 'De 30 a 60 minutos'),
    ('DE_60_A_90', 'De 60 a 90 minutos'), ('MAIS_90', 'Mais de 90 minutos'),
]
IDADE_MIN, IDADE_MAX = 11, 25  # idades fora deste intervalo agrupam-se em «≤11» e «≥25»

TITULO_CICLO = {
    'CICLO1': '1º Ciclo (7ª a 9ª Classes)',
    'CICLO2': '2º Ciclo (10ª a 12ª Classes)',
    'GERAL': '1º + 2º Ciclos (Total da Escola)',
}


def ciclo_da_classe(nome):
    """1 para classes até à 9ª, 2 para a 10ª em diante."""
    tipo, num = plano.chave_classe(nome)
    if tipo == 'C' and num.isdigit() and int(num) >= 10:
        return 2
    return 1


def _chave_classe_ordenacao(nome):
    tipo, num = plano.chave_classe(nome)
    return (0, int(num), '') if num.isdigit() else (1, 0, str(nome))


# ---------------------------------------------------------------------------
# Mapa bruto (somável) -> mapa final (lista de linhas para as tabelas)
# ---------------------------------------------------------------------------
def _hm():
    return {'h': 0, 'm': 0}


def _novo():
    return {
        'mat': _hm(), 'idades': defaultdict(_hm), 'nee': defaultdict(_hm), 'orfaos': defaultdict(_hm),
        'transporte': defaultdict(_hm), 'tempo': defaultdict(_hm), 'locais': defaultdict(lambda: defaultdict(int)),
    }


def _somar_hm(dest, orig):
    dest['h'] += orig['h']
    dest['m'] += orig['m']


def _somar(dest, orig):
    _somar_hm(dest['mat'], orig['mat'])
    for sec in ('idades', 'nee', 'orfaos', 'transporte', 'tempo'):
        for k, v in orig[sec].items():
            _somar_hm(dest[sec][k], v)
    for k, bairros in orig['locais'].items():
        for b, n in bairros.items():
            dest['locais'][k][b] += n
    return dest


def _sexo(aluno):
    return 'm' if str(aluno.genero or '').strip().upper().startswith('F') else 'h'


def _idade(aluno, ano):
    try:
        return int(ano) - aluno.data_nascimento.year
    except (TypeError, ValueError, AttributeError):
        return None


def _bruto_de_alunos(alunos, ano):
    b = _novo()
    for a in alunos:
        s = _sexo(a)
        b['mat'][s] += 1
        idade = _idade(a, ano)
        if idade is not None:
            chave = min(max(idade, IDADE_MIN), IDADE_MAX)
            b['idades'][chave][s] += 1
        if a.necessidade_especial:
            b['nee'][a.necessidade_especial][s] += 1
        if a.orfandade and a.orfandade != 'NENHUMA':
            b['orfaos'][a.orfandade][s] += 1
        if a.meio_transporte:
            b['transporte'][a.meio_transporte][s] += 1
        if a.tempo_casa_escola:
            b['tempo'][a.tempo_casa_escola][s] += 1
            local = ' '.join((a.local_residencia or '').split())
            if local:
                b['locais'][a.tempo_casa_escola][local] += 1
    return b


def _linha(rotulo, hm, **extra):
    d = {'rotulo': rotulo, 'h': hm['h'], 'm': hm['m'], 't': hm['h'] + hm['m']}
    d.update(extra)
    return d


def _rotulo_idade(chave):
    if chave <= IDADE_MIN:
        return f'≤{IDADE_MIN}'
    if chave >= IDADE_MAX:
        return f'≥{IDADE_MAX}'
    return str(chave)


def _finalizar(b):
    mat = b['mat']
    locais = {
        k: ', '.join(f'{nome} ({n})' for nome, n in sorted(v.items(), key=lambda x: (-x[1], x[0])))
        for k, v in b['locais'].items()
    }
    return {
        'matriculados': {'h': mat['h'], 'm': mat['m'], 't': mat['h'] + mat['m']},
        'idades': [_linha(_rotulo_idade(k), v) for k, v in sorted(b['idades'].items())],
        'nee': [_linha(r, b['nee'].get(c, _hm()), codigo=c) for c, r in ROTULO_NEE],
        'orfaos': [_linha(r, b['orfaos'].get(c, _hm()), codigo=c) for c, r in ROTULO_ORFANDADE],
        'transporte': [_linha(r, b['transporte'].get(c, _hm()), codigo=c) for c, r in ROTULO_TRANSPORTE],
        'tempo': [_linha(r, b['tempo'].get(c, _hm()), codigo=c, locais=locais.get(c, '')) for c, r in ROTULO_TEMPO],
    }


# ---------------------------------------------------------------------------
# Dados da escola
# ---------------------------------------------------------------------------
def _escola_info(escola):
    return {
        'nome': getattr(escola, 'nome', '') or '',
        'provincia': getattr(escola, 'provincia', '') or '',
        'distrito': getattr(escola, 'distrito', '') or '',
    }


def _alunos_por_turma(escola, turmas):
    from apps.alunos.models import Aluno
    ids = [t.id for t in turmas]
    por_turma = defaultdict(list)
    for a in Aluno.objects.filter(escola=escola, status='ATIVO', turma_id__in=ids):
        por_turma[a.turma_id].append(a)
    return por_turma


def _turmas_do_ano(escola, ano, classe=None):
    from apps.turmas.models import Turma
    qs = Turma.objects.filter(escola=escola, ano_letivo=str(ano)).select_related('director_turma', 'director_classe')
    turmas = list(qs)
    if classe is not None:
        turmas = [t for t in turmas if plano.mesma_classe(t.grau_ano, classe)]
    turmas.sort(key=lambda t: (_chave_classe_ordenacao(t.grau_ano), t.nome))
    return turmas


def _alocacoes(escola, turmas):
    """{(turma_id, disciplina_id): [nomes dos professores]} — dados reais da atribuição de disciplinas."""
    from apps.professores.models import AlocacaoDocente
    mapa = defaultdict(list)
    for al in AlocacaoDocente.objects.filter(escola=escola, turma_id__in=[t.id for t in turmas]).select_related('professor'):
        nome = getattr(al.professor, 'nome', '') or ''
        if nome and nome not in mapa[(al.turma_id, al.disciplina_id)]:
            mapa[(al.turma_id, al.disciplina_id)].append(nome)
    return mapa


def _disciplinas_da_turma(escola, turma):
    """Disciplinas do Plano Curricular aplicáveis à turma (tronco comum + as da sua secção/área)."""
    from apps.disciplinas.models import AreaSeccaoDisciplina
    area = ' '.join(str(turma.area or '').split()).lower()
    todas = plano.disciplinas_da_classe(escola, turma.grau_ano)
    if area in plano.SEM_AREA:
        return [d for d in todas if ' '.join(str(d.area or '').split()).lower() in plano.SEM_AREA] or todas
    ids_area = set(
        AreaSeccaoDisciplina.objects.filter(escola=escola, area__nome__iexact=turma.area)
        .values_list('disciplina_id', flat=True)
    )
    resultado = []
    for d in todas:
        da = ' '.join(str(d.area or '').split()).lower()
        if da in plano.SEM_AREA or da == area or d.id in ids_area:
            resultado.append(d)
    return resultado


def _linhas_disciplinas(escola, turma, mat, alocs):
    return [
        {
            'classe': turma.grau_ano, 'area': turma.area or 'Geral', 'nome': d.nome, 'codigo': d.codigo,
            'professor': ', '.join(alocs.get((turma.id, d.id), [])),
            'turmas': 1, 'h': mat['h'], 'm': mat['m'], 't': mat['h'] + mat['m'],
        }
        for d in sorted(_disciplinas_da_turma(escola, turma), key=lambda x: x.nome)
    ]


def _agrupar_disciplinas(linhas, por_area=True):
    agg = {}
    for ln in linhas:
        chave = (ln['classe'], ln['area'] if por_area else '', ln['nome'])
        if chave not in agg:
            agg[chave] = dict(ln, professor=set(filter(None, ln['professor'].split(', '))), turmas=0, h=0, m=0, t=0)
        r = agg[chave]
        r['professor'].update(filter(None, ln['professor'].split(', ')))
        r['turmas'] += ln['turmas']
        r['h'] += ln['h']
        r['m'] += ln['m']
        r['t'] += ln['t']
    saida = []
    for (_, _, _), r in sorted(agg.items(), key=lambda x: (_chave_classe_ordenacao(x[0][0]), x[0][1], x[0][2])):
        r['professor'] = ', '.join(sorted(r['professor']))
        saida.append(r)
    return saida


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
def _nome_prof(p):
    return getattr(p, 'nome', '') if p else ''


def compilar_turma(escola, turma):
    ano = turma.ano_letivo
    alunos = _alunos_por_turma(escola, [turma]).get(turma.id, [])
    bruto = _bruto_de_alunos(alunos, ano)
    ciclo = ciclo_da_classe(turma.grau_ano)
    disciplinas = []
    if ciclo == 2:
        disciplinas = _linhas_disciplinas(escola, turma, bruto['mat'], _alocacoes(escola, [turma]))
    return {
        'tipo': 'turma', 'ano': str(ano), 'ciclo': ciclo, 'escola': _escola_info(escola),
        'turma': {
            'id': str(turma.id), 'nome': turma.nome, 'classe': turma.grau_ano, 'area': turma.area or 'Geral',
            'turno': turma.turno, 'director_turma': _nome_prof(turma.director_turma),
        },
        'mapa': _finalizar(bruto), 'disciplinas': disciplinas,
    }


def _brutos_turmas(escola, turmas, ano):
    por_turma = _alunos_por_turma(escola, turmas)
    return {t.id: _bruto_de_alunos(por_turma.get(t.id, []), ano) for t in turmas}


def compilar_classe(escola, classe, ano):
    turmas = _turmas_do_ano(escola, ano, classe)
    brutos = _brutos_turmas(escola, turmas, ano)
    total = _novo()
    linhas_turmas = []
    for t in turmas:
        _somar(total, brutos[t.id])
        mat = brutos[t.id]['mat']
        linhas_turmas.append({
            'rotulo': t.nome, 'area': t.area or 'Geral', 'turno': t.turno, 'director_turma': _nome_prof(t.director_turma),
            'h': mat['h'], 'm': mat['m'], 't': mat['h'] + mat['m'],
        })
    nome = (turmas[0].grau_ano if turmas else None) or plano.nome_classe_oficial(escola, classe) or classe
    ciclo = ciclo_da_classe(nome)
    disciplinas = []
    if ciclo == 2 and turmas:
        alocs = _alocacoes(escola, turmas)
        linhas = []
        for t in turmas:
            linhas += _linhas_disciplinas(escola, t, brutos[t.id]['mat'], alocs)
        disciplinas = _agrupar_disciplinas(linhas, por_area=True)
    dc = next((t.director_classe for t in turmas if t.director_classe_id), None)
    return {
        'tipo': 'classe', 'ano': str(ano), 'classe': nome, 'ciclo': ciclo, 'escola': _escola_info(escola),
        'director_classe': _nome_prof(dc), 'turmas': linhas_turmas, 'mapa': _finalizar(total), 'disciplinas': disciplinas,
    }


def compilar_escola(escola, ano):
    turmas = _turmas_do_ano(escola, ano)
    brutos = _brutos_turmas(escola, turmas, ano)
    alocs = _alocacoes(escola, [t for t in turmas if ciclo_da_classe(t.grau_ano) == 2])

    por_classe = defaultdict(list)
    for t in turmas:
        chave = plano.nome_classe_oficial(escola, t.grau_ano) or t.grau_ano
        por_classe[chave].append(t)

    grupos = {k: {'chave': k, 'titulo': TITULO_CICLO[k], 'classes': [], 'bruto': _novo(), 'linhas_disc': []}
              for k in ('CICLO1', 'CICLO2', 'GERAL')}
    for nome in sorted(por_classe, key=_chave_classe_ordenacao):
        ts = por_classe[nome]
        bruto_classe = _novo()
        for t in ts:
            _somar(bruto_classe, brutos[t.id])
        ciclo = ciclo_da_classe(nome)
        alvo = grupos['CICLO2' if ciclo == 2 else 'CICLO1']
        mat = bruto_classe['mat']
        linha = {'rotulo': nome, 'turmas': len(ts), 'h': mat['h'], 'm': mat['m'], 't': mat['h'] + mat['m']}
        alvo['classes'].append(linha)
        grupos['GERAL']['classes'].append(dict(linha))
        _somar(alvo['bruto'], bruto_classe)
        _somar(grupos['GERAL']['bruto'], bruto_classe)
        if ciclo == 2:
            for t in ts:
                alvo['linhas_disc'] += _linhas_disciplinas(escola, t, brutos[t.id]['mat'], alocs)

    saida = []
    for k in ('CICLO1', 'CICLO2', 'GERAL'):
        g = grupos[k]
        saida.append({
            'chave': k, 'titulo': g['titulo'], 'classes': g['classes'], 'mapa': _finalizar(g['bruto']),
            'disciplinas': _agrupar_disciplinas(g['linhas_disc'], por_area=False) if k == 'CICLO2' else [],
        })
    return {'tipo': 'escola', 'ano': str(ano), 'escola': _escola_info(escola), 'grupos': saida}
