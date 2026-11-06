"""IA do SIGE: resolve provas passo a passo (Guião / Resolução detalhada) com a API do Claude.

Fica no servidor: a chave vem da variável de ambiente ANTHROPIC_API_KEY (nunca vai para o navegador nem para o repositório).
A prova é enviada como PDF para a IA «ler» enunciados, fórmulas e figuras tal como o aluno as vê.
"""
import base64
import json
import os

MODELO_PADRAO = "claude-opus-5-5"
# USD por milhão de tokens (entrada, saída): só serve para mostrar ao professor o custo aproximado de cada Guião
PRECOS = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50),
          "claude-opus-5": (5.0, 25.0), "claude-fable-5-1": (10.0, 50.0)}
MAX_TOKENS = 64000

ESQUEMA = {
    "type": "object",
    "properties": {
        "questoes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "numero": {"type": "string"},
                    "enunciado": {"type": "string"},
                    "tipo": {"type": "string", "enum": ["escolha_multipla", "aberta", "verdadeiro_falso", "calculo"]},
                    "passos": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"descricao": {"type": "string"}, "equacao": {"type": "string"}},
                            "required": ["descricao", "equacao"],
                            "additionalProperties": False,
                        },
                    },
                    "resposta_final": {"type": "string"},
                    "opcao_correcta": {"type": "string"},
                    "texto_opcao_correcta": {"type": "string"},
                    "justificacao_opcao": {"type": "string"},
                    "confianca": {"type": "string", "enum": ["alta", "media", "baixa"]},
                    "observacao": {"type": "string"},
                },
                "required": ["numero", "enunciado", "tipo", "passos", "resposta_final", "opcao_correcta",
                             "texto_opcao_correcta", "justificacao_opcao", "confianca", "observacao"],
                "additionalProperties": False,
            },
        },
        "observacoes_gerais": {"type": "string"},
    },
    "required": ["questoes", "observacoes_gerais"],
    "additionalProperties": False,
}

SISTEMA = """És o assistente pedagógico do SIGE (Sistema Integrado de Gestão Escolar de Moçambique). Escreves em português de Moçambique, \
seguindo os programas do Ministério da Educação e Desenvolvimento Humano (MINEDH).
O professor carregou uma prova. A tua tarefa é produzir o GUIÃO: a resolução detalhada de TODAS as questões, para o professor corrigir.

Regras obrigatórias:
1. Resolve todas as questões, pela ordem da prova, sem saltar nenhuma e sem inventar questões que não existam.
2. Resolução SEM OMISSÃO de passos e de cálculos: cada passo algébrico ou numérico tem o seu próprio passo (substituição de valores, \
simplificação, passagem de membros, factorização, aplicação da fórmula, conversão de unidades, etc.). Nunca escrevas «é fácil ver» nem \
«pelo que se conclui» sem mostrar a conta.
3. Cada passo tem `descricao` (uma frase curta que diz o que se faz e porquê) e `equacao` (a expressão desse passo em LaTeX, SEM os \
delimitadores $…$; vazio se o passo é só texto). Usa LaTeX normal: \\frac{a}{b}, \\sqrt{x}, x^{2}, x_{1}, \\cdot, \\times, \\pm, \\leq, \\geq, \\neq, \\approx, \
\\sum, \\int, \\lim, \\sin, \\log, \\vec{v}, \\overline{AB}, \\begin{cases} … \\end{cases}, \\begin{pmatrix} … \\end{pmatrix}, \\text{unidade}. As equações são \
escritas na forma matemática (fracções, raízes, expoentes), nunca em linha tipo a/b ou x^2 sem LaTeX. Matemática dentro de uma frase da `descricao` \
vai entre $…$.
4. Em Física e Química: escreve os dados, a fórmula, a substituição com unidades, o cálculo e o resultado com unidades e algarismos significativos \
adequados; em Química inclui o balanceamento de equações e as contas de mol, massa e concentração passo a passo. Em Biologia, História, Geografia, \
Línguas e outras disciplinas, os passos são o raciocínio: critério, aplicação ao caso e conclusão.
5. `resposta_final` é o resultado final da questão (com $…$ para matemática).
6. Se a questão é de escolha múltipla: `tipo` = `escolha_multipla`, `opcao_correcta` é a letra (A, B, C, D ou E) — confirma-a resolvendo e \
comparando com TODAS as alternativas —, `texto_opcao_correcta` repete o texto da alternativa certa e `justificacao_opcao` explica em poucas linhas por \
que as outras estão erradas. Se não é de escolha múltipla, deixa `opcao_correcta`, `texto_opcao_correcta` e `justificacao_opcao` vazios.
7. Se um enunciado está ilegível, ambíguo, incompleto, precisa de uma figura que não consegues ler, ou admite mais de uma resposta, diz-o em \
`observacao` e põe `confianca` = `baixa`. Não adivinhes em silêncio. Se tens a certeza do resultado, `confianca` = `alta`.
8. `enunciado` repete a pergunta de forma fiel e sintética (com $…$ para fórmulas), para o guião se perceber sozinho.
9. Não acrescentes nada fora da estrutura pedida."""


class IAIndisponivel(Exception):
    """A IA não está configurada ou não respondeu: a mensagem é para mostrar ao professor."""


def disponivel():
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def modelo():
    return os.environ.get("SIGE_IA_MODELO") or MODELO_PADRAO


def custo_estimado(entrada, saida, nome=None):
    """USD aproximados (None se o modelo não está na tabela de preços)."""
    p = PRECOS.get(nome or modelo())
    return round(entrada / 1e6 * p[0] + saida / 1e6 * p[1], 4) if p else None


def resolver_prova(pdf, titulo="", disciplina="", classe=""):
    """Envia a prova (PDF) à IA e devolve {'dados': guião (dict), 'uso': {...}}.

    Levanta IAIndisponivel com uma mensagem em português se não houver chave, se a IA recusar ou se a resposta vier cortada.
    """
    if not disponivel():
        raise IAIndisponivel("A IA do SIGE ainda não está activada neste servidor (falta a chave ANTHROPIC_API_KEY).")
    import anthropic

    cliente = anthropic.Anthropic(max_retries=2, timeout=900.0)
    nome = modelo()
    contexto = ", ".join(x for x in (titulo, disciplina, classe) if x)
    pedido = [
        {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                        "data": base64.standard_b64encode(pdf).decode("ascii")}},
        {"type": "text", "text": f"Prova: {contexto or 'sem título'}. Produz o guião com a resolução detalhada de todas as questões."},
    ]
    try:
        with cliente.messages.stream(
            model=nome, max_tokens=MAX_TOKENS, system=SISTEMA,
            thinking={"type": "adaptive"},
            output_config={"effort": "high", "format": {"type": "json_schema", "schema": ESQUEMA}},
            messages=[{"role": "user", "content": pedido}],
        ) as fluxo:
            resposta = fluxo.get_final_message()
    except anthropic.AuthenticationError:
        raise IAIndisponivel("A chave da IA foi recusada. Peça ao administrador para a verificar.") from None
    except anthropic.RateLimitError:
        raise IAIndisponivel("A IA está com muitos pedidos neste momento. Tente de novo dentro de alguns minutos.") from None
    except anthropic.BadRequestError as e:
        raise IAIndisponivel(f"A IA não aceitou este ficheiro: {getattr(e, 'message', e)}") from None
    except (anthropic.APIConnectionError, anthropic.APITimeoutError):
        raise IAIndisponivel("Sem ligação à IA. Tente de novo dentro de alguns minutos.") from None
    except anthropic.APIStatusError as e:
        raise IAIndisponivel(f"A IA devolveu um erro ({e.status_code}). Tente de novo mais tarde.") from None
    if resposta.stop_reason == "refusal":
        raise IAIndisponivel("A IA recusou resolver este conteúdo. Reveja a prova ou resolva-a manualmente.")
    if resposta.stop_reason == "max_tokens":
        raise IAIndisponivel("A prova é demasiado longa para um só guião. Divida-a em duas e tente de novo.")
    texto = "".join(b.text for b in resposta.content if b.type == "text")
    try:
        dados = json.loads(texto)
    except ValueError:
        raise IAIndisponivel("A resposta da IA veio incompleta. Tente de novo.") from None
    if not isinstance(dados.get("questoes"), list) or not dados["questoes"]:
        raise IAIndisponivel("A IA não encontrou questões para resolver nesta prova.")
    entrada = int(getattr(resposta.usage, "input_tokens", 0) or 0)
    saida = int(getattr(resposta.usage, "output_tokens", 0) or 0)
    return {"dados": dados, "uso": {"modelo": nome, "entrada": entrada, "saida": saida, "custo_usd": custo_estimado(entrada, saida, nome)}}
