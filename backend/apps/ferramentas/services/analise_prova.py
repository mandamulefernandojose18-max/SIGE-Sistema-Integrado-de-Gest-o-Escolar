# =====================================================================
# SIGE - ANÁLISE DE UMA PROVA ANTES DE A APLICAR (em memória; o texto nunca é guardado)
#  - dependência da turma: perguntas "genéricas" que uma IA resolve sem ter estado na aula
#  - originalidade: perguntas que já existem na internet (pesquisa web opcional)
# =====================================================================

import json
import os
import re
import urllib.parse
import urllib.request

# Palavras que indicam que a pergunta depende de material/dados da turma ou da aula.
_MARCAS_LOCAIS = (
    'aula', 'turma', 'experiência', 'experiencia', 'laboratório', 'laboratorio', 'medimos', 'medimos', 'nosso',
    'nossa', 'anexo', 'folha', 'texto dado', 'texto que', 'segunda-feira', 'terça-feira', 'quarta-feira',
    'quinta-feira', 'sexta-feira', 'escola', 'professor', 'caderno', 'ficha', 'tabela abaixo', 'dados abaixo',
)

_PALAVRAS = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)


def _limpar(enunciado: str) -> str:
    """Enunciado sem as alíneas A) B) C) D), para pesquisar só a pergunta."""
    primeira = re.split(r"\n\s*[A-E]\)|\s+[A-E]\)\s", enunciado, maxsplit=1)[0]
    return " ".join(primeira.split())


def dependencia_da_turma(questoes: list) -> dict:
    """Heurística simples: uma pergunta sem qualquer referência à aula/turma/anexo é considerada genérica."""
    genericas, locais = [], []
    for q in questoes:
        texto = (q.get('enunciado') or '').lower()
        (locais if any(m in texto for m in _MARCAS_LOCAIS) else genericas).append(q.get('numero'))
    total = len(questoes) or 1
    return {
        'total_questoes': len(questoes),
        'genericas': genericas,
        'dependentes_da_turma': locais,
        'percentagem_genericas': round(100 * len(genericas) / total),
        'sugestao': (
            "Torne as perguntas dependentes da turma: use dados medidos na aula, um texto ou ficha dados em papel, "
            "ou valores diferentes por turma. Perguntas de livro, uma IA resolve de memória."
            if genericas else "Todas as perguntas referem material ou dados da turma."
        ),
    }


def pesquisar_web(frase: str, chave: str, timeout: int = 8) -> list:
    """Pesquisa via Brave Search API (plano gratuito). Devolve [(título, trecho)]. Lança excepção em caso de falha."""
    url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode({'q': f'"{frase}"', 'count': 5})
    req = urllib.request.Request(url, headers={'Accept': 'application/json', 'X-Subscription-Token': chave})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        dados = json.loads(resp.read().decode('utf-8'))
    return [(r.get('title', ''), r.get('description', '')) for r in dados.get('web', {}).get('results', [])]


def _parecido(frase: str, trechos: list) -> bool:
    """A pergunta existe num resultado se pelo menos 70% das suas palavras aparecem no mesmo resultado."""
    palavras = {p.lower() for p in _PALAVRAS.findall(frase) if len(p) > 3}
    if len(palavras) < 4:
        return False
    for titulo, desc in trechos:
        alvo = {p.lower() for p in _PALAVRAS.findall(f"{titulo} {desc}")}
        if len(palavras & alvo) / len(palavras) >= 0.7:
            return True
    return False


def originalidade(questoes: list, pesquisar=pesquisar_web, maximo: int = 10) -> dict:
    """
    Verifica se as perguntas já existem na internet. Limita-se a `maximo` pedidos por análise (custo/quota).
    Sem BRAVE_SEARCH_API_KEY o serviço fica indisponível e a análise de dependência da turma continua a funcionar.
    """
    chave = os.environ.get('BRAVE_SEARCH_API_KEY', '')
    if not chave:
        return {'disponivel': False, 'motivo': 'Serviço de pesquisa na web não configurado (BRAVE_SEARCH_API_KEY).'}
    escolhidas = sorted(questoes, key=lambda q: len(_limpar(q.get('enunciado') or '')), reverse=True)[:maximo]
    encontradas, falhas = [], 0
    for q in escolhidas:
        frase = _limpar(q.get('enunciado') or '')[:200]
        if len(frase) < 25:
            continue
        try:
            if _parecido(frase, pesquisar(frase, chave)):
                encontradas.append(q.get('numero'))
        except Exception:
            falhas += 1
    return {
        'disponivel': True,
        'verificadas': len(escolhidas),
        'ja_existem_na_internet': sorted(n for n in encontradas if n is not None),
        'falhas_de_pesquisa': falhas,
        'sugestao': "Altere números, contexto ou palavras nas perguntas listadas." if encontradas
                    else "Nenhuma das perguntas verificadas foi encontrada na internet.",
    }


def analisar(texto: str, com_web: bool = True) -> dict:
    from apps.ferramentas.views import _extrair_questoes_de_texto  # evita importação circular
    questoes = _extrair_questoes_de_texto(texto)
    resultado = {'dependencia_da_turma': dependencia_da_turma(questoes)}
    resultado['originalidade'] = originalidade(questoes) if com_web else {'disponivel': False, 'motivo': 'Não pedida.'}
    return resultado
