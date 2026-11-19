"""
Assistente Virtual — nível 0 (custo zero, sem modelo de linguagem), só leitura.

Escolhe a capacidade (capacidades.py) por palavras-chave, aplica a REGRA DE SEGURANÇA (só responde sobre o que pertence ao painel
do perfil: modulos.py) e as permissões de dados (aluno/encarregado só o seu; professor só as suas turmas…), e responde com dados reais,
regras do MEC ou guias dos módulos. Sem registos, diz que não há registos; nunca inventa valores. O que não pertence ao painel é
recusado sem revelar nada.
"""
import difflib

from . import capacidades as cap
from . import capacidades_extra, plataforma
from .capacidades import ACESSO_ALUNO, GESTAO, PROPRIO, Ctx, normalizar
from .modulos import modulos_do_perfil

# Palavras que nunca são parte de um nome de aluno (perguntas, tempos, relações…)
_NAO_NOME = {'tem', 'quantas', 'quantos', 'qual', 'quais', 'como', 'esta', 'estao', 'aluno', 'aluna', 'educando', 'filho', 'filha', 'meu', 'minha', 'dele', 'dela',
             'para', 'por', 'com', 'sem', 'foi', 'hoje', 'agora', 'este', 'esse', 'nao', 'sim', 'mais', 'menos', 'quero', 'saber', 'ver', 'diga', 'dizer',
             'mostra', 'mostre', 'existe', 'existem', 'houve', 'sobre', 'cada', 'todos', 'todas', 'ainda', 'tambem', 'onde', 'quando', 'porque', 'que', 'seu', 'sua',
             'turma', 'classe', 'escola', 'ano', 'mes', 'trimestre', 'faz', 'fazer', 'ter', 'tenho', 'tinha', 'esta', 'estou', 'sou', 'ele', 'ela'}

SEM_PERMISSAO = 'O seu perfil não tem permissão para consultar essa informação.'
NAO_ENCONTRADO = 'Não encontrei esse aluno na sua escola.'
SEM_VINCULO = 'A sua conta ainda não está associada a um aluno. Peça à secretaria da escola para fazer essa associação.'
PEDE_ALUNO = 'Escolha primeiro o aluno a que a pergunta se refere.'
FORA_DO_PAINEL = ('Essa informação não faz parte do seu painel, por isso não posso responder. '
                  'Posso ajudar com o que está disponível para o seu perfil — pergunte "o que posso perguntar?".')
ESCOLHA_ESCOLA = ('Isso são dados de uma escola. Abra primeiro a escola com "Inspecionar" no Painel Master e volte a perguntar; '
                  'aqui posso responder sobre a plataforma (escolas, assinaturas, faturas, planos).')
DESCONHECIDA = ('Ainda não sei responder a essa pergunta. Posso ajudar com dados do seu painel, com as regras do MEC e com guias dos módulos. '
                'Pergunte "o que posso perguntar?" para ver exemplos para o seu perfil.')


def _registar():
    plataforma.registar()
    capacidades_extra.registar()


_CONHECIDAS = None


def _palavras_conhecidas():
    """Palavras do assistente (das palavras-chave) — o que sobra numa pergunta é candidato a nome de aluno."""
    global _CONHECIDAS
    if _CONHECIDAS is None or len(_CONHECIDAS[0]) != len(cap.CAPACIDADES):
        palavras = {t for c in cap.CAPACIDADES for k in c.chaves for t in k.split()}
        palavras |= {cap._singular(t) for t in palavras} | _NAO_NOME | cap._ARTIGOS
        _CONHECIDAS = (list(cap.CAPACIDADES), palavras)
    return _CONHECIDAS[1]


def aluno_pelo_nome(ctx, capacidade):
    """Procura, DENTRO do âmbito do perfil, o aluno cujo nome aparece na pergunta. Devolve (aluno|None, nomes_ambiguos)."""
    from apps.alunos.models import Aluno
    conhecidas = _palavras_conhecidas()
    candidatos = [t for t in ctx.texto.split() if len(t) >= 3 and t not in conhecidas and cap._singular(t) not in conhecidas and not t.isdigit()]
    if not candidatos:
        return None, []
    if ctx.role == 'ENCARREGADO':
        pool = [(a.id, a.nome, a.apelido) for a in (ctx.educandos or educandos_do_encarregado(ctx.user, ctx.escola))]
    else:
        qs = Aluno.objects.filter(escola=ctx.escola, status='ATIVO')
        if ctx.role == 'PROFESSOR':
            from apps.professores.models import AlocacaoDocente
            qs = qs.filter(turma_id__in=list(AlocacaoDocente.objects.filter(escola=ctx.escola, professor_id=getattr(ctx.user, 'professor_id', None))
                                             .values_list('turma_id', flat=True)))
        pool = list(qs.values_list('id', 'nome', 'apelido')[:20000])
    melhores, melhor = [], 0
    for aid, nome, apelido in pool:
        nomes = normalizar(f'{nome} {apelido or ""}').split()
        n = sum(1 for c in candidatos if any(p == c or (len(c) >= 4 and p.startswith(c)) for p in nomes))
        completo = f'{nome} {apelido or ""}'.strip()
        if n > melhor:
            melhores, melhor = [(aid, completo)], n
        elif n == melhor and n > 0:
            melhores.append((aid, completo))
    if not melhor:
        return None, []
    if len(melhores) == 1:
        return Aluno.objects.filter(id=melhores[0][0], escola=ctx.escola).select_related('turma').first(), []
    return None, [{'id': str(i), 'nome': n} for i, n in melhores[:6]]


def proximas(texto, role, modulos, tem_escola, k=4):
    """Perguntas de exemplo, permitidas ao perfil, mais parecidas com o que o utilizador escreveu (para "quis dizer…?")."""
    tc = set(cap.canon(texto).split())
    pontuadas = []
    for c in cap.CAPACIDADES:
        if not c.exemplos or (c.plataforma and role != 'SUPERADMIN') or not cap.permitido(c, role, modulos):
            continue
        if c.tipo == 'dados' and not tem_escola and not c.plataforma:
            continue
        ex = c.exemplos[0]
        te = set(cap.canon(normalizar(ex)).split())
        comum = len(tc & te) / max(len(te), 1)
        ratio = difflib.SequenceMatcher(None, normalizar(texto), normalizar(ex)).ratio()
        pontuadas.append((comum + 0.5 * ratio, ex))
    pontuadas.sort(reverse=True)
    return [ex for s, ex in pontuadas[:k] if s > 0.2]


def classificar(pergunta, pagina=None, role='DIRECTOR_ESCOLA'):
    """Devolve (nome da melhor capacidade PERMITIDA ao perfil ou 'desconhecida', texto normalizado). Usado nos testes de classificação."""
    _registar()
    modulos = modulos_do_perfil(role, inspeccionando=False)
    texto = normalizar(pergunta)
    for _pontos, _prio, c in cap.pontuacoes(texto, pagina):
        if c.plataforma and role != 'SUPERADMIN':
            continue
        if cap.permitido(c, role, modulos):
            return c.nome, texto
    return 'desconhecida', texto


def educandos_do_encarregado(user, escola):
    """Educandos de uma conta de Encarregado: os associados pela escola + o aluno_id antigo da conta (se houver)."""
    from apps.alunos.educando import educandos_ids
    from apps.alunos.models import Aluno
    ids = educandos_ids(user)
    if not ids:
        return []
    return list(Aluno.objects.filter(id__in=ids, escola=escola).select_related('turma').order_by('nome'))


def _categoria(role):
    if role in GESTAO:
        return 'gestao'
    return {'FINANCEIRO': 'financeiro', 'PROFESSOR': 'professor'}.get(role)


def resolver_aluno(ctx, capacidade, aluno_id):
    """Devolve (aluno, erro). O aluno/encarregado só vê o seu educando; o professor só alunos das suas turmas."""
    from apps.alunos.models import Aluno
    cats = ACESSO_ALUNO.get(capacidade.nome, {'proprio', 'gestao'})
    role = ctx.role
    if role == 'ENCARREGADO':
        if 'proprio' not in cats:
            return None, 'sem_permissao'
        educandos = educandos_do_encarregado(ctx.user, ctx.escola)
        if not educandos:
            return None, 'sem_vinculo'
        ctx.educandos = educandos
        if aluno_id:
            escolhido = next((a for a in educandos if str(a.id) == str(aluno_id)), None)
            return (escolhido, None) if escolhido else (None, 'sem_permissao')   # nunca outro aluno que não seja um dos seus
        if len(educandos) == 1:
            return educandos[0], None
        return None, 'precisa_aluno'
    if role in PROPRIO:
        if 'proprio' not in cats:
            return None, 'sem_permissao'
        alvo = getattr(ctx.user, 'aluno_id', None)
        if not alvo:
            return None, 'sem_vinculo'
        categoria = 'proprio'
    else:
        categoria = _categoria(role)
        if categoria not in cats:
            return None, 'sem_permissao'
        alvo = aluno_id
        if not alvo:
            return None, 'precisa_aluno'
    aluno = Aluno.objects.filter(id=alvo, escola=ctx.escola).select_related('turma').first()
    if not aluno:
        return None, 'nao_encontrado'
    if categoria == 'professor':
        from apps.professores.models import AlocacaoDocente
        if not AlocacaoDocente.objects.filter(escola=ctx.escola, professor_id=getattr(ctx.user, 'professor_id', None), turma_id=aluno.turma_id).exists():
            return None, 'sem_permissao'
    return aluno, None


def _resposta(nome, resultado, ctx, capacidade=None, **extra):
    destino, rotulo = resultado.get('destino'), resultado.get('rotulo')
    if capacidade is not None and not destino:
        destino = capacidade.destino_proprio if (ctx.proprio and capacidade.destino_proprio) else capacidade.destino
        rotulo = rotulo or capacidade.rotulo
    elif capacidade is not None and ctx.proprio and capacidade.destino_proprio and destino == capacidade.destino:
        destino = capacidade.destino_proprio
    out = {'intencao': nome, 'resposta': resultado['texto'], 'sugestoes': resultado.get('sugestoes') or cap.sugestoes(ctx.role, ctx.pagina)}
    if resultado.get('dados') is not None:
        out['dados'] = resultado['dados']
    if destino:
        out['acao'] = {'destino': destino, 'rotulo': rotulo or 'Abrir'}
    out.update(extra)
    return out


def _simples(nome, texto, ctx, **extra):
    return {'intencao': nome, 'resposta': texto, 'sugestoes': cap.sugestoes(ctx.role, ctx.pagina), **extra}


def _escolher(ordem, ctx, modulos, em_plataforma):
    """Separa a melhor capacidade PERMITIDA da melhor BLOQUEADA (fora do painel). Devolve (permitida, bloqueada) como (pontos, cap)."""
    melhor_ok = melhor_bloq = None
    for pontos, _prio, c in ordem:
        if c.plataforma and ctx.role != 'SUPERADMIN':
            continue    # dados da plataforma nem sequer são considerados para os perfis de uma escola
        permitida = cap.permitido(c, ctx.role, modulos) and (not em_plataforma or c.plataforma or c.tipo != 'dados')
        if permitida and melhor_ok is None:
            melhor_ok = (pontos, c)
        elif not permitida and melhor_bloq is None:
            melhor_bloq = (pontos, c)
        if melhor_ok and melhor_bloq:
            break
    return melhor_ok, melhor_bloq


def _responder_nome_ambiguo(nome, ambiguos, ctx):
    lista = '; '.join(c['nome'] for c in ambiguos)
    return nome, None, _simples(nome, f'Encontrei vários alunos com esse nome: {lista}. Escolha um deles abaixo ou indique o nome completo.', ctx,
                                precisa_aluno=True, candidatos=ambiguos)


def responder(user, escola, pergunta, aluno_id=None, pagina=None, anterior=None):
    """Devolve (nome da capacidade, aluno|None, dict de resposta). Só leitura. `anterior` = capacidade da pergunta anterior (seguimento)."""
    _registar()
    role = getattr(user, 'role', '')
    em_plataforma = role == 'SUPERADMIN' and escola is None
    modulos = modulos_do_perfil(role, inspeccionando=(role == 'SUPERADMIN' and escola is not None))
    ctx = Ctx(user=user, escola=escola, pergunta=pergunta, texto=normalizar(pergunta), pagina=pagina, modulos=modulos)

    def prox():
        return {'sugestoes': proximas(ctx.texto, role, modulos, escola is not None) or cap.sugestoes(role, pagina)}

    # "Onde fica X?" → atalho para o ecrã (só módulos do painel do perfil)
    alvo = cap.navegar(ctx.texto)
    if alvo:
        destino, rotulo = alvo
        if destino not in modulos:
            return 'fora_do_painel', None, _simples('fora_do_painel', FORA_DO_PAINEL, ctx, **prox())
        return 'navegacao', None, _simples('navegacao', f'Pode abrir {rotulo} a partir do menu lateral. Use o botão abaixo para ir directamente.', ctx,
                                           acao={'destino': destino, 'rotulo': f'Abrir {rotulo}'})

    ordem = cap.pontuacoes(ctx.texto, pagina)
    permitida, bloqueada = _escolher(ordem, ctx, modulos, em_plataforma)
    if bloqueada and bloqueada[0] > (permitida[0] if permitida else 0):
        # a melhor correspondência não pertence ao painel deste perfil: recusa sem revelar nada
        c = bloqueada[1]
        if em_plataforma and c.tipo == 'dados' and not c.plataforma:
            return 'escolher_escola', None, _simples('escolher_escola', ESCOLHA_ESCOLA, ctx, **prox())
        return 'fora_do_painel', None, _simples('fora_do_painel', FORA_DO_PAINEL, ctx, **prox())
    # "Como está o João Silva?" (com um nome de aluno na pergunta) → resumo do aluno; sem nome, "como está…" continua a ser a pergunta que já foi percebida
    if any(p in ctx.texto for p in (' como esta', ' como vai', ' como anda', ' como estao', ' como vao')) and not (permitida and permitida[0] >= 3):
        c_resumo = cap.POR_NOME.get('resumo_aluno')
        if c_resumo and cap.permitido(c_resumo, role, modulos) and role not in PROPRIO and escola is not None:
            achado, ambiguos = aluno_pelo_nome(ctx, c_resumo)
            if achado is not None or ambiguos:
                permitida = (3, c_resumo)
    if not permitida and anterior and anterior in cap.POR_NOME and len(ctx.texto.split()) <= 8:
        # pergunta de seguimento ("e do João?", "João Silva"): continua a capacidade anterior, se o perfil a pode usar
        c = cap.POR_NOME[anterior]
        if cap.permitido(c, role, modulos) and not (em_plataforma and c.tipo == 'dados' and not c.plataforma):
            # só é seguimento se houver um sinal verdadeiro: um marcador ("e o…", "também", "agora") ou um nome de aluno;
            # texto sem sentido NUNCA herda a capacidade anterior
            marcador = ctx.texto.startswith(' e ') or any(m in ctx.texto for m in (' tambem ', ' agora ', ' e se ', ' e para ', ' e do ', ' e da ', ' e de ', ' mesmo '))
            tem_nome = False
            if c.aluno in ('obrigatorio', 'opcional') and role != 'ALUNO':
                achado, ambiguos = aluno_pelo_nome(ctx, c)
                tem_nome = achado is not None or bool(ambiguos)
            if marcador or tem_nome:
                permitida = (0.5, c)
    # Correspondência fraca (uma só palavra-chave) numa frase cheia de palavras desconhecidas ("receita de bolo de chocolate") não é uma pergunta
    # que o assistente perceba: em vez de responder lixo, diz que não sabe. (Perguntas com nome de aluno estão isentas.)
    if permitida and 1 <= permitida[0] < 2 and permitida[1].tipo == 'dados' and not permitida[1].aluno:
        conhecidas = _palavras_conhecidas()
        toks = [t for t in ctx.texto.split() if t not in cap._ARTIGOS and len(t) > 2]
        conhecidos = [t for t in toks if t in conhecidas or cap._singular(t) in conhecidas]
        if len(toks) >= 3 and len(conhecidos) / len(toks) < 0.5:
            permitida = None
    if not permitida:
        return 'desconhecida', None, _simples('desconhecida', DESCONHECIDA, ctx, **prox())

    capacidade = permitida[1]
    nome = capacidade.nome

    aluno = None
    if capacidade.aluno:
        # Pergunta de resumo ("quantas…", "pendentes…") numa capacidade opcional: responde pela escola, mesmo com um aluno escolhido
        resumo = capacidade.aluno == 'opcional' and any(w in ctx.texto for w in (' quantas ', ' quantos ', ' pendentes', ' este ano', ' no total'))
        quer_aluno = capacidade.aluno == 'obrigatorio' or ctx.proprio or (bool(aluno_id) and not resumo)
        if capacidade.aluno == 'proprio':      # só usa o educando do aluno/encarregado; os outros perfis ignoram o aluno escolhido
            quer_aluno = ctx.proprio
        erro = None
        if quer_aluno:
            aluno, erro = resolver_aluno(ctx, capacidade, aluno_id)
        # O aluno pode vir escrito na pergunta ("faltas do João Silva"): procura-o, sempre dentro do âmbito do perfil
        if capacidade.aluno in ('obrigatorio', 'opcional') and not aluno_id and role != 'ALUNO' and not resumo and (not quer_aluno or erro == 'precisa_aluno'):
            achado, ambiguos = aluno_pelo_nome(ctx, capacidade)
            if achado is not None:
                aluno, erro = resolver_aluno(ctx, capacidade, achado.id)    # revalida permissões e âmbito (professor: só as suas turmas)
                quer_aluno = True
            elif ambiguos:
                return _responder_nome_ambiguo(nome, ambiguos, ctx)
        if quer_aluno:
            if erro == 'precisa_aluno':
                if ctx.role == 'ENCARREGADO' and getattr(ctx, 'educandos', None):
                    nomes = ', '.join(a.nome for a in ctx.educandos[:6])
                    return nome, None, _simples(nome, f'De qual dos seus educandos quer saber? ({nomes}). Escolha-o na lista acima.', ctx,
                                                precisa_aluno=True, educandos=[{'id': str(a.id), 'nome': a.nome} for a in ctx.educandos])
                return nome, None, _simples(nome, PEDE_ALUNO + ' Pode também escrever o nome do aluno.', ctx, precisa_aluno=True)
            if erro:
                msg = {'nao_encontrado': NAO_ENCONTRADO, 'sem_vinculo': SEM_VINCULO}.get(erro, SEM_PERMISSAO)
                return nome, None, _simples(nome, msg, ctx)
            ctx.aluno = aluno

    resultado = capacidade.handler(ctx)
    return nome, aluno, _resposta(nome, resultado, ctx, capacidade)