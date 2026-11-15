"""
SIGE — Calendário de Exames e formação automática de Júris.

Regras (todas sobre dados reais, isoladas por escola):
  * Admitido ao exame: média de frequência (MT1..MT3) superior a 9,4 (regra oficial da pauta de exames).
  * Excluído: média de frequência <= 9,4 (sem direito ao exame).
  * 1ª época: todos os admitidos. 2ª época: admitidos com nota de 1ª época lançada abaixo da nota mínima.
  * Júris: distribuição equilibrada (sem júris quase vazios) por ordem alfabética, com o máximo de
    alunos por júri definido pela escola; sala opcional atribuída sem choques de data/hora.
"""
import math
from collections import OrderedDict, defaultdict

from django.db import transaction

LIMITE_EXCLUSAO = 9.4


def chave_disciplina(nome):
    return ' '.join(str(nome or '').strip().lower().split())


def _media_nota(n):
    """Média de frequência de um trimestre (mesmo critério da pauta oficial)."""
    for campo in ('media_final', 'media_trimestral'):
        v = getattr(n, campo, None)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    testes = []
    for c in ('teste1', 'teste2', 'teste3', 'teste4', 'trabalho', 'avaliacao_trimestral'):
        v = getattr(n, c, None)
        if v is not None:
            try:
                testes.append(float(v))
            except (TypeError, ValueError):
                pass
    return round(sum(testes) / len(testes), 1) if testes else None


def nota_minima_exame(escola):
    try:
        return float(escola.get_config_parametros_exames().get('nota_minima_exame', 10.0))
    except Exception:
        return 10.0


def analisar_turma(turma):
    """{chave_disciplina: {'nome': str, 'alunos': {aluno_id: dados}}} só para disciplinas COM exame."""
    from apps.alunos.models import Aluno
    from apps.notas.models import Nota, NotaExame
    from apps.pautas.services import (
        disciplina_tem_exame_na_turma, obter_disciplinas_pauta_turma, obter_nome_completo_aluno,
    )

    disciplinas = [d for d in obter_disciplinas_pauta_turma(turma) if disciplina_tem_exame_na_turma(d, turma)]
    if not disciplinas:
        return {}
    alunos = list(Aluno.objects.filter(turma=turma, status='ATIVO').order_by('nome', 'apelido'))
    notas = {}
    for n in Nota.objects.filter(turma=turma):
        notas.setdefault((n.aluno_id, n.disciplina_id), {})[n.periodo] = n
    exames = {(e.aluno_id, e.disciplina_id): e for e in NotaExame.objects.filter(turma=turma, ano_letivo=turma.ano_letivo)}
    minima = nota_minima_exame(turma.escola)

    resultado = OrderedDict()
    for d in disciplinas:
        grupo = resultado.setdefault(chave_disciplina(d.nome), {'nome': d.nome, 'alunos': OrderedDict()})
        for a in alunos:
            por_tri = notas.get((a.id, d.id), {})
            vals = [v for v in (_media_nota(n) for n in por_tri.values()) if v is not None]
            ne = exames.get((a.id, d.id))
            freq = round(sum(vals) / len(vals), 1) if vals else None
            if freq is None and ne is not None and ne.nota_frequencia is not None:
                freq = round(float(ne.nota_frequencia), 1)
            e1 = ne.exame_1epoca if ne else None
            e2 = ne.exame_2epoca if ne else None
            if freq is None:
                estado = 'SEM_NOTA'
            elif freq <= LIMITE_EXCLUSAO:
                estado = 'EXCLUIDO'
            else:
                estado = 'ADMITIDO'
            grupo['alunos'][a.id] = {
                'aluno': a, 'nome': obter_nome_completo_aluno(a), 'turma': turma.nome,
                'freq': freq, 'e1': e1, 'e2': e2, 'estado': estado,
                'vai_2epoca': estado == 'ADMITIDO' and e1 is not None and e1 < minima,
            }
    return resultado


def analisar_classe(escola, ano, classe):
    """Junta as turmas da classe: {chave: {'nome', 'alunos': [dados...]}} ordenado por nome do aluno."""
    from apps.turmas.models import Turma
    junto = OrderedDict()
    for turma in Turma.objects.filter(escola=escola, ano_letivo=str(ano), grau_ano=classe).order_by('nome'):
        for chave, g in analisar_turma(turma).items():
            alvo = junto.setdefault(chave, {'nome': g['nome'], 'alunos': []})
            alvo['alunos'].extend(g['alunos'].values())
    for g in junto.values():
        g['alunos'].sort(key=lambda x: x['nome'].lower())
    return junto


def candidatos_da_epoca(grupo, epoca):
    """Alunos que vão a exame nessa época (já ordenados alfabeticamente)."""
    if int(epoca) == 1:
        return [a for a in grupo['alunos'] if a['estado'] == 'ADMITIDO']
    return [a for a in grupo['alunos'] if a['vai_2epoca']]


def excluidos(grupo):
    return [a for a in grupo['alunos'] if a['estado'] == 'EXCLUIDO']


def classes_da_escola(escola, ano):
    from apps.turmas.models import Turma
    return sorted(
        set(Turma.objects.filter(escola=escola, ano_letivo=str(ano)).values_list('grau_ano', flat=True)),
        key=lambda c: (len(c), c),
    )


# ---------------------------------------------------------------- calendário
class ErroCalendario(ValueError):
    pass


def validar_conflitos(escola, ano, classe, disciplina, epoca, data, inicio, fim):
    """Uma turma não faz duas disciplinas ao mesmo tempo; a 2ª época vem depois da 1ª."""
    from apps.notas.models import CalendarioExame
    outros = CalendarioExame.objects.filter(escola=escola, ano_letivo=str(ano), classe=classe, data=data).exclude(
        disciplina=disciplina, epoca=epoca)
    for o in outros:
        if o.hora_inicio < fim and inicio < o.hora_fim:
            raise ErroCalendario(
                f'Conflito: {o.disciplina} ({o.epoca}ª época) já ocupa {o.hora_inicio:%H:%M}–{o.hora_fim:%H:%M} '
                f'nesse dia para a {classe}.')
    par = CalendarioExame.objects.filter(
        escola=escola, ano_letivo=str(ano), classe=classe, disciplina=disciplina, epoca=3 - int(epoca)).first()
    if par:
        if int(epoca) == 2 and data <= par.data:
            raise ErroCalendario(f'A 2ª época de {disciplina} tem de ser depois da 1ª ({par.data:%d/%m/%Y}).')
        if int(epoca) == 1 and data >= par.data:
            raise ErroCalendario(f'A 1ª época de {disciplina} tem de ser antes da 2ª ({par.data:%d/%m/%Y}).')


# --------------------------------------------------------------------- júris
def _distribuir(total, maximo):
    n = math.ceil(total / maximo)
    base, extra = divmod(total, n)
    return [base + (1 if i < extra else 0) for i in range(n)]


@transaction.atomic
def formar_juris(escola, ano, epoca, max_por_juri, num_salas=None, classe=None):
    """Recria os júris do âmbito (ano, época e, opcionalmente, classe) a partir do calendário de exames."""
    from apps.notas.models import CalendarioExame, JuriExame, JuriExameAluno
    ano = str(ano)
    epoca = int(epoca)
    entradas = CalendarioExame.objects.filter(escola=escola, ano_letivo=ano, epoca=epoca)
    if classe:
        entradas = entradas.filter(classe=classe)
    entradas = list(entradas.order_by('data', 'hora_inicio', 'classe', 'disciplina'))
    avisos = []
    if not entradas:
        raise ErroCalendario('Defina primeiro as datas no calendário de exames desta época.')

    JuriExame.objects.filter(
        escola=escola, ano_letivo=ano, epoca=epoca, **({'classe': classe} if classe else {})).delete()

    analise = {}
    novos = []  # (entrada, numero, [alunos])
    classes_no_ambito = {e.classe for e in entradas} if not classe else {classe}
    for c in sorted(classes_no_ambito):
        analise[c] = analisar_classe(escola, ano, c)
        com_data = {chave_disciplina(e.disciplina) for e in entradas if e.classe == c}
        for chave, g in analise[c].items():
            if chave not in com_data:
                avisos.append(f'{c} · {g["nome"]}: sem data no calendário — júris não formados.')

    for e in entradas:
        grupo = analise[e.classe].get(chave_disciplina(e.disciplina))
        if not grupo:
            avisos.append(f'{e.classe} · {e.disciplina}: não é disciplina com exame nesta classe.')
            continue
        cands = candidatos_da_epoca(grupo, epoca)
        if not cands:
            avisos.append(f'{e.classe} · {e.disciplina}: nenhum aluno admitido para a {epoca}ª época.')
            continue
        pos = 0
        for numero, tamanho in enumerate(_distribuir(len(cands), max_por_juri), start=1):
            novos.append((e, numero, cands[pos:pos + tamanho]))
            pos += tamanho

    # Salas: primeira sala livre no intervalo [início, fim) do dia (só se a escola indicou salas).
    ocupacao = defaultdict(list)
    criados = 0
    alunos_alocados = 0
    sem_sala = 0
    for e, numero, alunos in sorted(novos, key=lambda t: (t[0].data, t[0].hora_inicio, t[0].classe, t[0].disciplina, t[1])):
        sala = ''
        if num_salas:
            for s in range(1, int(num_salas) + 1):
                if all(not (e.hora_inicio < f and i < e.hora_fim)
                       for (d, i, f) in ocupacao[s] if d == e.data):
                    ocupacao[s].append((e.data, e.hora_inicio, e.hora_fim))
                    sala = f'Sala {s}'
                    break
            else:
                sem_sala += 1
        juri = JuriExame.objects.create(
            escola=escola, ano_letivo=ano, classe=e.classe, disciplina=e.disciplina, epoca=epoca,
            numero=numero, sala=sala, max_alunos=max_por_juri)
        JuriExameAluno.objects.bulk_create([
            JuriExameAluno(juri=juri, aluno=a['aluno'], ordem=i) for i, a in enumerate(alunos, start=1)])
        criados += 1
        alunos_alocados += len(alunos)
    if sem_sala:
        avisos.append(f'{sem_sala} júri(s) ficaram sem sala: todas as {num_salas} salas estão ocupadas à mesma hora. '
                      'Aumente o número de salas ou separe os horários.')
    return {'juris_formados': criados, 'alunos_alocados': alunos_alocados, 'avisos': avisos}


def listar_juris(escola, ano, epoca, classe=None, disciplina=None):
    """Júris com a lista de alunos e a nota de frequência da disciplina."""
    from apps.notas.models import CalendarioExame, JuriExame
    qs = JuriExame.objects.filter(escola=escola, ano_letivo=str(ano), epoca=int(epoca))
    if classe:
        qs = qs.filter(classe=classe)
    if disciplina:
        qs = qs.filter(disciplina=disciplina)
    cal = {(c.classe, chave_disciplina(c.disciplina)): c for c in CalendarioExame.objects.filter(
        escola=escola, ano_letivo=str(ano), epoca=int(epoca))}
    analise = {}
    saida = []
    for j in qs.prefetch_related('alunos_juri__aluno'):
        if j.classe not in analise:
            analise[j.classe] = analisar_classe(escola, ano, j.classe)
        grupo = analise[j.classe].get(chave_disciplina(j.disciplina), {'alunos': []})
        por_id = {a['aluno'].id: a for a in grupo['alunos']}
        c = cal.get((j.classe, chave_disciplina(j.disciplina)))
        alunos = []
        for ja in j.alunos_juri.all():
            d = por_id.get(ja.aluno_id)
            alunos.append({
                'ordem': ja.ordem,
                'nome': d['nome'] if d else ja.aluno.nome,
                'matricula': ja.aluno.matricula,
                'turma': d['turma'] if d else '',
                'freq': d['freq'] if d else None,
            })
        saida.append({
            'id': str(j.id), 'classe': j.classe, 'disciplina': j.disciplina, 'epoca': j.epoca,
            'numero': j.numero, 'sala': j.sala, 'max_alunos': j.max_alunos,
            'data': c.data.isoformat() if c else None,
            'periodo': c.periodo if c else None,
            'hora_inicio': c.hora_inicio.strftime('%H:%M') if c else None,
            'hora_fim': c.hora_fim.strftime('%H:%M') if c else None,
            'duracao_minutos': c.duracao_minutos if c else None,
            'alunos': sorted(alunos, key=lambda x: x['ordem']),
        })
    saida.sort(key=lambda x: (x['classe'], x['data'] or '', x['hora_inicio'] or '', x['disciplina'], x['numero']))
    return saida
