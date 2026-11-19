"""
Assistente Virtual — nível 0 (custo zero, sem modelo de linguagem), só leitura.

Escolhe a capacidade (capacidades.py) por palavras-chave, aplica as permissões do perfil e da escola, e responde com dados reais,
regras do MEC ou guias dos módulos. Sem registos, diz que não há registos; nunca inventa valores.
"""
from . import capacidades as cap
from .capacidades import ACESSO_ALUNO, DIRECCAO, GESTAO, PROPRIO, Ctx, normalizar

SEM_PERMISSAO = 'O seu perfil não tem permissão para consultar essa informação.'
NAO_ENCONTRADO = 'Não encontrei esse aluno na sua escola.'
SEM_VINCULO = 'A sua conta ainda não está associada a um aluno. Peça à secretaria da escola para fazer essa associação.'
PEDE_ALUNO = 'Escolha primeiro o aluno a que a pergunta se refere.'
DESCONHECIDA = ('Ainda não sei responder a essa pergunta. Posso ajudar com dados da escola (faltas, notas, propinas, turmas, horários, calendário, exames, '
                'transferências, pautas, comunicados…), com as regras do MEC e com guias de cada módulo (por exemplo, "como lanço as notas?"). '
                'Escolha o aluno quando a pergunta for sobre dados dele.')


def classificar(pergunta, pagina=None):
    """Devolve (nome da capacidade ou 'desconhecida', texto normalizado)."""
    c, texto = cap.classificar(pergunta, pagina)
    return (c.nome if c else 'desconhecida'), texto


def _categoria(role):
    if role in GESTAO:
        return 'gestao'
    return {'FINANCEIRO': 'financeiro', 'PROFESSOR': 'professor'}.get(role)


def educandos_do_encarregado(user, escola):
    """Educandos de uma conta de Encarregado: os associados pela escola + o aluno_id antigo da conta (se houver)."""
    from apps.alunos.educando import educandos_ids
    from apps.alunos.models import Aluno
    ids = educandos_ids(user)
    if not ids:
        return []
    return list(Aluno.objects.filter(id__in=ids, escola=escola).select_related('turma').order_by('nome'))


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
    out = {'intencao': nome, 'resposta': resultado['texto'], 'sugestoes': cap.sugestoes(ctx.role, ctx.pagina)}
    if resultado.get('dados') is not None:
        out['dados'] = resultado['dados']
    if destino:
        out['acao'] = {'destino': destino, 'rotulo': rotulo or 'Abrir'}
    out.update(extra)
    return out


def _simples(nome, texto, ctx, **extra):
    return {'intencao': nome, 'resposta': texto, 'sugestoes': cap.sugestoes(ctx.role, ctx.pagina), **extra}


def responder(user, escola, pergunta, aluno_id=None, pagina=None):
    """Devolve (nome da capacidade, aluno|None, dict de resposta). Só leitura."""
    ctx = Ctx(user=user, escola=escola, pergunta=pergunta, texto=normalizar(pergunta), pagina=pagina)

    # "Onde fica X?" → atalho para o ecrã
    alvo = cap.navegar(ctx.texto)
    if alvo:
        destino, rotulo = alvo
        return 'navegacao', None, _simples('navegacao', f'Pode abrir {rotulo} a partir do menu lateral. Use o botão abaixo para ir directamente.', ctx,
                                           acao={'destino': destino, 'rotulo': f'Abrir {rotulo}'})

    capacidade, ctx.texto = cap.classificar(pergunta, pagina)
    if capacidade is None:
        return 'desconhecida', None, _simples('desconhecida', DESCONHECIDA, ctx)

    nome = capacidade.nome
    if capacidade.perfis is not None and ctx.role not in capacidade.perfis and not (capacidade.aluno == 'opcional' and (ctx.proprio or aluno_id)):
        return nome, None, _simples(nome, SEM_PERMISSAO, ctx)

    aluno = None
    if capacidade.aluno:
        # Pergunta de resumo ("quantas…", "pendentes…") numa capacidade opcional: responde pela escola, mesmo com um aluno escolhido
        resumo = capacidade.aluno == 'opcional' and any(w in ctx.texto for w in (' quantas ', ' quantos ', ' pendentes', ' este ano', ' no total'))
        quer_aluno = capacidade.aluno == 'obrigatorio' or ctx.proprio or (bool(aluno_id) and not resumo)
        if capacidade.aluno == 'proprio':      # só usa o educando do aluno/encarregado; os outros perfis ignoram o aluno escolhido
            quer_aluno = ctx.proprio
        if quer_aluno:
            aluno, erro = resolver_aluno(ctx, capacidade, aluno_id)
            if erro == 'precisa_aluno':
                if ctx.role == 'ENCARREGADO' and getattr(ctx, 'educandos', None):
                    nomes = ', '.join(a.nome for a in ctx.educandos[:6])
                    return nome, None, _simples(nome, f'De qual dos seus educandos quer saber? ({nomes}). Escolha-o na lista acima.', ctx,
                                                precisa_aluno=True, educandos=[{'id': str(a.id), 'nome': a.nome} for a in ctx.educandos])
                return nome, None, _simples(nome, PEDE_ALUNO, ctx, precisa_aluno=True)
            if erro:
                msg = {'nao_encontrado': NAO_ENCONTRADO, 'sem_vinculo': SEM_VINCULO}.get(erro, SEM_PERMISSAO)
                return nome, None, _simples(nome, msg, ctx)
            ctx.aluno = aluno

    resultado = capacidade.handler(ctx)
    return nome, aluno, _resposta(nome, resultado, ctx, capacidade)
