"""
Assistente Virtual — nível 0 (custo zero, sem modelo de linguagem).

Classifica a pergunta por palavras-chave e responde com (a) dados reais lidos da base, só leitura e já
limitados pelo perfil e pela escola, ou (b) regras oficiais do MEC já documentadas no SIGE. Sem registos,
diz que não há registos; nunca inventa valores.
"""
import re
import unicodedata

from django.utils import timezone

from apps.alunos.models import PresencaAluno
from apps.pagamentos.models import Pagamento

ROLES_GESTAO = {'SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP', 'CHEFE_SECRETARIA', 'SECRETARIA'}
ROLES_PROPRIO = {'ALUNO', 'ENCARREGADO'}

SUGESTOES = [
    'Quantas faltas tem o aluno?',
    'Há propinas em atraso?',
    'Como se calcula a média trimestral (MT)?',
    'Como se calcula a média final da disciplina (MFD)?',
    'Quais são as regras de aprovação?',
    'Como funcionam as faltas em aula dupla?',
]


def normalizar(texto):
    t = unicodedata.normalize('NFKD', texto or '').encode('ascii', 'ignore').decode('ascii').lower()
    return ' ' + re.sub(r'[^a-z0-9 ]+', ' ', t).strip() + ' '


# (intenção, palavras-chave). Pontuação = nº de palavras-chave presentes; empate resolve pela ordem.
INTENCOES = [
    ('aula_dupla', [' aula dupla', ' dupla ', ' justific', ' anular justific']),
    ('faltas', [' falta', ' faltas', ' faltou', ' assiduidade', ' ausenc', ' presenc']),
    ('propinas', [' propina', ' mensalidade', ' pagamento', ' pagar', ' divida', ' em atraso', ' atrasad']),
    ('faq_mt', [' mt ', ' media trimestral', ' trimestral ']),
    ('faq_mfd', [' mfd ', ' media final', ' media anual']),
    ('faq_mac', [' mac ', ' acs ', ' avaliacao continua', ' avaliacoes continuas']),
    ('faq_aprovacao', [' aprov', ' reprov', ' transit', ' negativa', ' passar de classe', ' retid']),
    ('faq_exames', [' exame', ' epoca', ' nota minima']),
    ('faq_escala', [' escala', ' excelente', ' suficiente', ' qualitativ', ' muito bom']),
    ('faq_siglas', [' sigla', ' anotacao', ' ppf ', ' vt ']),
    ('ajuda', [' ajuda', ' ola ', ' bom dia', ' boa tarde', ' boa noite', ' o que sabes', ' o que podes']),
]


def classificar(pergunta):
    texto = normalizar(pergunta)
    melhor, pontos = 'desconhecida', 0
    for nome, chaves in INTENCOES:
        p = sum(1 for c in chaves if c in texto)
        if p > pontos:
            melhor, pontos = nome, p
    return melhor, texto


# ---------------------------------------------------------------- respostas de regras (MEC)
FAQ = {
    'faq_mt': (
        'A Média Trimestral (MT) combina com peso 2 a média das avaliações contínuas (MAC) e com peso 1 a '
        'Avaliação Trimestral (AT): MT = (2 × MAC + AT) / 3, arredondada ao inteiro mais próximo (9,5 → 10; 9,49 → 9). '
        'Só é apurada com pelo menos duas avaliações contínuas válidas (1.ª e 2.ª ACS) e a AT realizada; caso contrário a disciplina fica Pendente.'),
    'faq_mfd': (
        'A Média Final da Disciplina (MFD) é a média aritmética das três médias trimestrais, arredondada ao inteiro '
        'mais próximo: MFD = (MT1 + MT2 + MT3) / 3. Notas na escala de 0 a 20; abaixo de 10 é negativa.'),
    'faq_mac': (
        'A MAC é a média aritmética simples das avaliações contínuas efectivamente realizadas (1.ª e 2.ª ACS obrigatórias; '
        '3.ª ACS, MAP e MAS opcionais), arredondada a uma casa decimal. Testes opcionais não realizados não baixam a média.'),
    'faq_exames': (
        'Por padrão do MEC têm exame a 10.ª e a 12.ª classes, mas cada escola pode definir que classes têm exame. '
        'Nas disciplinas com exame: NF = (M. Frequência × peso freq. + Nota de exame × peso exame) / 100 (padrão 50% / 50%). '
        'Se a nota da 1.ª época for inferior à nota mínima (padrão 10), o aluno tem direito à 2.ª época, cuja nota passa a contar.'),
    'faq_escala': (
        'Escala qualitativa: 18,5 a 20 = Excelente (E); 16,5 a 18,4 = Muito Bom (MB); 13,5 a 16,4 = Bom (B); '
        '9,5 a 13,4 = Suficiente (S, positiva); 0 a 9,4 = Não Suficiente (NS, negativa, a vermelho).'),
    'faq_siglas': (
        'Siglas de anotação: D (Dispensado), T (Transferido), VT (Veio Transferido), F (Faleceu), AM (Anulou a Matrícula), '
        'PPF (Perdeu por Faltas), PDF (Perdeu por Disciplina).'),
    'aula_dupla': (
        'Numa aula dupla, cada ausência conta como 2 faltas; numa aula simples conta 1. A secretaria/direcção pode justificar '
        'faltas por quantidade: as faltas justificadas reduzem as faltas efectivas do aluno.'),
}

APROVACAO_GERAL = (
    'Da 7.ª à 11.ª classe o aluno só é aprovado se tiver MFD ≥ 10 em todas as disciplinas (zero negativas); '
    'uma única negativa determina a reprovação.')
APROVACAO_12 = (
    'Na 12.ª classe o aluno é aprovado se a média geral anual for ≥ 9,5, tiver no máximo 2 disciplinas negativas '
    'e nenhuma negativa inferior a 8 valores (notas 7, 6 ou 5 reprovam, mesmo com média alta).')

AJUDA = ('Posso responder, só em leitura, sobre: faltas e propinas de um aluno, fórmulas oficiais (MT, MFD, MAC), '
         'regras de aprovação, exames, escala qualitativa e siglas. Escolha o aluno quando a pergunta for sobre dados dele.')


# ---------------------------------------------------------------- permissões e dados reais
def aluno_permitido(user, escola, aluno_id, intencao):
    """Devolve (aluno, erro). Aplica o perfil: o aluno/encarregado só vê o seu; o professor só vê faltas das suas turmas."""
    from apps.alunos.models import Aluno
    role = getattr(user, 'role', '')
    alvo = getattr(user, 'aluno_id', None) if role in ROLES_PROPRIO else aluno_id
    if not alvo:
        return None, 'precisa_aluno'
    aluno = Aluno.objects.filter(id=alvo, escola=escola).select_related('turma').first()
    if not aluno:
        return None, 'nao_encontrado'
    if role in ROLES_PROPRIO or role in ROLES_GESTAO:
        return aluno, None
    if role == 'FINANCEIRO':
        return (aluno, None) if intencao == 'propinas' else (None, 'sem_permissao')
    if role == 'PROFESSOR' and intencao == 'faltas':
        from apps.professores.models import AlocacaoDocente
        ok = AlocacaoDocente.objects.filter(escola=escola, professor_id=getattr(user, 'professor_id', None),
                                            turma_id=aluno.turma_id).exists()
        return (aluno, None) if ok else (None, 'sem_permissao')
    return None, 'sem_permissao'


def resposta_faltas(escola, aluno):
    from apps.crm.views import _faltas_efectivas_por_aluno
    ano = getattr(escola, 'ano_letivo_ativo', None)
    efectivas = _faltas_efectivas_por_aluno(escola, ano_letivo=ano, aluno_id=aluno.id).get(aluno.id, 0)
    regs = PresencaAluno.objects.filter(escola=escola, aluno=aluno, status='FALTA_INJUSTIFICADA')
    if ano:
        regs = regs.filter(turma__ano_letivo=ano)
    injust = sum(max((r.aulas or 1) - (r.aulas_justificadas or 0), 0) for r in regs)
    if not efectivas:
        return f'{aluno.nome} não tem faltas efectivas registadas' + (f' no ano lectivo {ano}.' if ano else '.'), {'faltas_efectivas': 0}
    return (f'{aluno.nome} tem {efectivas} falta(s) efectiva(s)' + (f' no ano lectivo {ano}' if ano else '') +
            f', das quais {injust} ainda por justificar.'), {'faltas_efectivas': efectivas, 'por_justificar': injust}


def resposta_propinas(escola, aluno):
    agora = timezone.now()
    abertos = Pagamento.objects.filter(escola=escola, aluno=aluno, status__in=('PENDENTE', 'ATRASADO'))
    atraso = [p for p in abertos if p.data_vencimento < agora]
    futuros = [p for p in abertos if p.data_vencimento >= agora]
    if not atraso and not futuros:
        return f'{aluno.nome} não tem propinas pendentes registadas.', {'em_atraso': 0, 'a_vencer': 0}
    valor = sum((p.valor - p.valor_pago for p in atraso), 0)
    meses = ', '.join(p.mes_referencia for p in sorted(atraso, key=lambda x: x.mes_referencia))
    partes = []
    if atraso:
        partes.append(f'{len(atraso)} propina(s) em atraso ({meses}), no valor de {valor} MZN')
    if futuros:
        partes.append(f'{len(futuros)} a vencer')
    return f'{aluno.nome}: ' + '; '.join(partes) + '.', {'em_atraso': len(atraso), 'valor_em_atraso': str(valor), 'a_vencer': len(futuros)}


def responder(user, escola, pergunta, aluno_id=None):
    """Devolve (intencao, aluno|None, dict de resposta). Só leitura."""
    intencao, texto = classificar(pergunta)
    base = {'intencao': intencao, 'sugestoes': SUGESTOES}

    if intencao in ('faltas', 'propinas'):
        aluno, erro = aluno_permitido(user, escola, aluno_id, intencao)
        if erro == 'precisa_aluno':
            return intencao, None, {**base, 'resposta': 'Escolha primeiro o aluno a que a pergunta se refere.', 'precisa_aluno': True}
        if erro in ('nao_encontrado', 'sem_permissao'):
            msg = ('Não encontrei esse aluno na sua escola.' if erro == 'nao_encontrado'
                   else 'O seu perfil não tem permissão para consultar essa informação.')
            return intencao, None, {**base, 'resposta': msg}
        texto_resp, dados = (resposta_faltas if intencao == 'faltas' else resposta_propinas)(escola, aluno)
        return intencao, aluno, {**base, 'resposta': texto_resp, 'dados': dados}

    if intencao == 'faq_aprovacao':
        return intencao, None, {**base, 'resposta': APROVACAO_12 if re.search(r' (12|doze)', texto) else APROVACAO_GERAL + ' ' + APROVACAO_12}
    if intencao in FAQ:
        return intencao, None, {**base, 'resposta': FAQ[intencao]}
    if intencao == 'ajuda':
        return intencao, None, {**base, 'resposta': AJUDA}
    return 'desconhecida', None, {**base, 'resposta': 'Ainda não sei responder a essa pergunta. ' + AJUDA}
