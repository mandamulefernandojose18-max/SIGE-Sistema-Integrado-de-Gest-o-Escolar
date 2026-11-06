"""IA do SIGE: resolve provas passo a passo (Guião / Resolução detalhada).

Fornecedores (o primeiro que tiver chave, por esta ordem, ou o escolhido em SIGE_IA_PROVEDOR):
  gemini      GRATUITO  Google AI Studio (GEMINI_API_KEY), sem cartão. Modelo: SIGE_IA_MODELO (predefinido gemini-3.8-flash).
  groq        GRATUITO  Groq (GROQ_API_KEY), com limites pequenos por minuto.
  openrouter  GRATUITO* OpenRouter (OPENROUTER_API_KEY), com modelos «:free».
  openai      qualquer serviço compatível com a API OpenAI (SIGE_IA_URL + SIGE_IA_CHAVE), ex.: Ollama no próprio servidor.
  anthropic   PAGO      Claude (ANTHROPIC_API_KEY).
As chaves ficam só em variáveis de ambiente do servidor (nunca no navegador nem no repositório). A prova segue como imagens das
páginas, para a IA ver enunciados, fórmulas e figuras tal como o aluno as vê.
"""
import base64
import json
import os
import re
import time
import urllib.error
import urllib.request

MODELO_ANTHROPIC = "claude-opus-5-5"
# USD por milhão de tokens (entrada, saída) dos modelos pagos: só para mostrar o custo aproximado
PRECOS = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50),
          "claude-opus-5": (5.0, 25.0), "claude-fable-5-1": (10.0, 50.0)}
MAX_TOKENS = 64000

# nome -> (variável da chave, URL base da API tipo OpenAI, modelo predefinido, gratuito, páginas por pedido, aviso de privacidade)
FORNECEDORES = {
    "gemini": ("GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/openai", "gemini-3.8-flash", True, 8,
               "Serviço gratuito da Google: o texto e as imagens da prova são enviados à Google, que pode usá-los para melhorar os seus produtos."),
    "groq": ("GROQ_API_KEY", "https://api.groq.com/openai/v1", "meta-llama/llama-4-scout-17b-16e-instruct", True, 2,
             "Serviço gratuito da Groq: a prova é enviada à Groq para ser resolvida."),
    "openrouter": ("OPENROUTER_API_KEY", "https://openrouter.ai/api/v1", "google/gemini-2.0-flash-exp:free", True, 4,
                   "Serviço gratuito do OpenRouter: a prova é enviada ao OpenRouter e ao fornecedor do modelo."),
    "openai": ("SIGE_IA_CHAVE", "", "", False, 4, "A prova é enviada ao serviço configurado em SIGE_IA_URL."),
    "anthropic": ("ANTHROPIC_API_KEY", "", MODELO_ANTHROPIC, False, 0,
                  "Serviço pago da Anthropic: a prova é enviada à Anthropic para ser resolvida."),
}
ORDEM = ("gemini", "groq", "openrouter", "openai", "anthropic")

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
vai entre $…$. Cada `equacao` deve ser uma expressão completa (por exemplo «x=\\frac{1}{2}»), não deve começar por «=».
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

FORMATO_JSON = """
Responde APENAS com um objecto JSON válido (sem texto antes ou depois, sem ```), exactamente com esta estrutura:
{"questoes": [{"numero": "1", "enunciado": "...", "tipo": "escolha_multipla|aberta|verdadeiro_falso|calculo",
  "passos": [{"descricao": "...", "equacao": "LaTeX sem $ ou vazio"}], "resposta_final": "...", "opcao_correcta": "A|B|C|D|E ou vazio",
  "texto_opcao_correcta": "...", "justificacao_opcao": "...", "confianca": "alta|media|baixa", "observacao": "..."}],
 "observacoes_gerais": "..."}
No JSON, as barras invertidas do LaTeX têm de vir duplicadas (por exemplo \\\\frac), e todas as chaves são obrigatórias."""


class IAIndisponivel(Exception):
    """A IA não está configurada ou não respondeu: a mensagem é para mostrar ao professor."""


def _chave(nome):
    return (os.environ.get(FORNECEDORES[nome][0]) or "").strip()


def provedor():
    """Nome do fornecedor activo (o escolhido em SIGE_IA_PROVEDOR ou o primeiro com chave), ou None."""
    escolhido = (os.environ.get("SIGE_IA_PROVEDOR") or "").strip().lower()
    if escolhido in FORNECEDORES and (_chave(escolhido) or (escolhido == "anthropic" and os.environ.get("ANTHROPIC_AUTH_TOKEN"))):
        if escolhido != "openai" or (os.environ.get("SIGE_IA_URL") or "").strip():
            return escolhido
    for nome in ORDEM:
        if nome == "openai" and not (os.environ.get("SIGE_IA_URL") or "").strip():
            continue
        if _chave(nome) or (nome == "anthropic" and os.environ.get("ANTHROPIC_AUTH_TOKEN")):
            return nome
    return None


def disponivel():
    return provedor() is not None


def gratuito():
    p = provedor()
    return bool(p and FORNECEDORES[p][3])


def modelo():
    p = provedor() or "gemini"
    explicito = (os.environ.get("SIGE_IA_MODELO") or "").strip()
    if explicito:
        return explicito
    return FORNECEDORES[p][2] or "(defina SIGE_IA_MODELO)"


def aviso_privacidade():
    p = provedor()
    return FORNECEDORES[p][5] if p else ""


def custo_estimado(entrada, saida, nome=None):
    """USD aproximados: 0 nos serviços gratuitos, None se o modelo pago não está na tabela de preços."""
    if gratuito():
        return 0.0
    p = PRECOS.get(nome or modelo())
    return round(entrada / 1e6 * p[0] + saida / 1e6 * p[1], 4) if p else None


# ----------------------------------------------------------------------------- utilitários comuns
def _paginas_png(pdf, dpi=115, maximo=40):
    """Páginas do PDF como PNG (bytes), uma por elemento."""
    import pymupdf
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        if doc.page_count > maximo:
            raise IAIndisponivel(f"A prova tem {doc.page_count} páginas; o limite para o Guião é {maximo}. Divida-a em partes.")
        return [p.get_pixmap(dpi=dpi, alpha=False).tobytes("png") for p in doc]


def _extrair_json(texto):
    """O objecto JSON de uma resposta de IA (tolera ```json … ``` e texto à volta)."""
    t = (texto or "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.IGNORECASE)
    try:
        return json.loads(t)
    except ValueError:
        i, j = t.find("{"), t.rfind("}")
        if i >= 0 and j > i:
            try:
                return json.loads(t[i:j + 1])
            except ValueError:
                pass
    raise IAIndisponivel("A resposta da IA veio incompleta ou fora do formato. Tente de novo.")


def _normalizar(dados):
    """Garante todos os campos de cada questão (as IAs gratuitas falham por vezes alguns)."""
    questoes = []
    for q in (dados.get("questoes") if isinstance(dados, dict) else None) or []:
        if not isinstance(q, dict):
            continue
        passos = [{"descricao": str(p.get("descricao", "")), "equacao": str(p.get("equacao", "") or "")}
                  for p in (q.get("passos") or []) if isinstance(p, dict)]
        opcao = str(q.get("opcao_correcta", "") or "").strip().upper()[:1]
        questoes.append({
            "numero": str(q.get("numero", len(questoes) + 1)), "enunciado": str(q.get("enunciado", "")),
            "tipo": q.get("tipo") if q.get("tipo") in ("escolha_multipla", "aberta", "verdadeiro_falso", "calculo") else "aberta",
            "passos": passos, "resposta_final": str(q.get("resposta_final", "")),
            "opcao_correcta": opcao if opcao in list("ABCDE") else "",
            "texto_opcao_correcta": str(q.get("texto_opcao_correcta", "")), "justificacao_opcao": str(q.get("justificacao_opcao", "")),
            "confianca": q.get("confianca") if q.get("confianca") in ("alta", "media", "baixa") else "media",
            "observacao": str(q.get("observacao", "")),
        })
    if not questoes:
        raise IAIndisponivel("A IA não encontrou questões para resolver nesta prova.")
    return {"questoes": questoes, "observacoes_gerais": str(dados.get("observacoes_gerais", ""))}


# ----------------------------------------------------------------------------- serviços tipo OpenAI (Gemini, Groq, …)
def _pedido_openai(url_base, chave, corpo, tentativas=3):
    pedido = urllib.request.Request(url_base.rstrip("/") + "/chat/completions", json.dumps(corpo).encode("utf-8"),
                                    {"Content-Type": "application/json", "Authorization": f"Bearer {chave}"})
    for k in range(tentativas):
        try:
            with urllib.request.urlopen(pedido, timeout=600) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detalhe = ""
            try:
                detalhe = e.read().decode("utf-8", "ignore")[:300]
            except Exception:  # noqa: BLE001
                pass
            if e.code in (429, 500, 502, 503, 504) and k < tentativas - 1:
                time.sleep(25 * (k + 1))  # limites por minuto dos serviços gratuitos
                continue
            if e.code in (401, 403):
                raise IAIndisponivel("A chave da IA foi recusada. Peça ao administrador para a verificar.") from None
            if e.code == 429:
                raise IAIndisponivel("O serviço gratuito atingiu o limite de pedidos. Tente de novo dentro de alguns minutos.") from None
            if e.code == 404:
                raise IAIndisponivel("O modelo da IA não existe neste serviço. O administrador pode mudá-lo em SIGE_IA_MODELO.") from None
            raise IAIndisponivel(f"A IA devolveu um erro ({e.code}). {detalhe}".strip()) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            if k < tentativas - 1:
                time.sleep(10)
                continue
            raise IAIndisponivel("Sem ligação à IA. Tente de novo dentro de alguns minutos.") from None
    raise IAIndisponivel("A IA não respondeu. Tente de novo.")


def _lote_openai(nome, imagens, contexto, indice, total):
    _, url_predef, _, _, _, _ = FORNECEDORES[nome]
    url = (os.environ.get("SIGE_IA_URL") or "").strip() if nome == "openai" else url_predef
    chave = _chave(nome)
    nota = f" (parte {indice} de {total}: resolve só as questões que aparecem nestas páginas)" if total > 1 else ""
    conteudo = [{"type": "text", "text": f"Prova: {contexto or 'sem título'}{nota}. Produz o guião com a resolução detalhada de todas as questões."}]
    for png in imagens:
        conteudo.append({"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(png).decode("ascii")}})
    corpo = {"model": modelo(), "temperature": 0.2, "max_tokens": 32000,
             "messages": [{"role": "system", "content": SISTEMA + FORMATO_JSON}, {"role": "user", "content": conteudo}],
             "response_format": {"type": "json_object"}}
    try:
        r = _pedido_openai(url, chave, corpo)
    except IAIndisponivel as e:
        if "erro (400)" not in str(e):
            raise
        corpo.pop("response_format")  # nem todos os serviços aceitam response_format: tenta sem ele
        r = _pedido_openai(url, chave, corpo)
    escolha = (r.get("choices") or [{}])[0]
    if escolha.get("finish_reason") == "length":
        raise IAIndisponivel("A resposta da IA ficou cortada (prova longa). Divida a prova em duas e tente de novo.")
    texto = (escolha.get("message") or {}).get("content") or ""
    uso = r.get("usage") or {}
    return _extrair_json(texto), int(uso.get("prompt_tokens") or 0), int(uso.get("completion_tokens") or 0)


def _resolver_openai(nome, pdf, contexto):
    paginas = _paginas_png(pdf)
    por_pedido = max(1, FORNECEDORES[nome][4])
    grupos = [paginas[i:i + por_pedido] for i in range(0, len(paginas), por_pedido)]
    questoes, gerais, entrada, saida = [], [], 0, 0
    for i, grupo in enumerate(grupos, 1):
        dados, e, s = _lote_openai(nome, grupo, contexto, i, len(grupos))
        entrada, saida = entrada + e, saida + s
        for q in (dados.get("questoes") or []):
            if isinstance(q, dict) and not any(str(x.get("numero")) == str(q.get("numero")) for x in questoes):
                questoes.append(q)  # uma questão que atravessa duas partes só entra uma vez
        if dados.get("observacoes_gerais"):
            gerais.append(str(dados["observacoes_gerais"]))
    return {"questoes": questoes, "observacoes_gerais": " ".join(gerais)}, entrada, saida


# ----------------------------------------------------------------------------- Claude (pago)
def _resolver_anthropic(pdf, contexto):
    import anthropic

    cliente = anthropic.Anthropic(max_retries=2, timeout=900.0)
    pedido = [
        {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                        "data": base64.standard_b64encode(pdf).decode("ascii")}},
        {"type": "text", "text": f"Prova: {contexto or 'sem título'}. Produz o guião com a resolução detalhada de todas as questões."},
    ]
    try:
        with cliente.messages.stream(
            model=modelo(), max_tokens=MAX_TOKENS, system=SISTEMA, thinking={"type": "adaptive"},
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
    return (_extrair_json(texto), int(getattr(resposta.usage, "input_tokens", 0) or 0),
            int(getattr(resposta.usage, "output_tokens", 0) or 0))


# ----------------------------------------------------------------------------- ponto de entrada
def resolver_prova(pdf, titulo="", disciplina="", classe=""):
    """Envia a prova (PDF) à IA e devolve {'dados': guião (dict), 'uso': {...}}.

    Levanta IAIndisponivel com uma mensagem em português se não houver chave, se a IA recusar ou se a resposta vier cortada.
    """
    nome = provedor()
    if not nome:
        raise IAIndisponivel("A IA do SIGE ainda não está activada neste servidor (falta a chave da IA).")
    contexto = ", ".join(x for x in (titulo, disciplina, classe) if x)
    if nome == "anthropic":
        dados, entrada, saida = _resolver_anthropic(pdf, contexto)
    else:
        dados, entrada, saida = _resolver_openai(nome, pdf, contexto)
    return {"dados": _normalizar(dados),
            "uso": {"modelo": modelo(), "provedor": nome, "gratuito": gratuito(), "entrada": entrada, "saida": saida,
                    "custo_usd": custo_estimado(entrada, saida, modelo())}}
