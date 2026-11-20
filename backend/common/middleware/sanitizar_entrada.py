"""Neutraliza HTML em corpos JSON recebidos pela API (defesa em profundidade contra XSS armazenado).

Nomes, títulos, descrições, etc. nunca precisam de etiquetas HTML. Em qualquer texto de um corpo JSON, uma sequência
que abre uma etiqueta (`<` seguido de letra, `/`, `!` ou `?`) passa a `&lt;`, e `javascript:` perde a eficácia.
Texto normal como «nota < 10» (com espaço) não é alterado. Caminhos que carregam conteúdo próprio (provas do Escudo,
ferramentas) ficam de fora.
"""
import json
import re

from django.http import JsonResponse

_ETIQUETA = re.compile(r'<(?=[A-Za-z/!?])')
_JS_URL = re.compile(r'(?i)\bj\s*a\s*v\s*a\s*s\s*c\s*r\s*i\s*p\s*t\s*:')
_CAMPOS_BINARIOS = {
    'conteudo_base64', 'documento_base64', 'comprovativo_base64', 'imagem_base64', 'ficheiro_base64',
    'logo_base64', 'foto_base64', 'password', 'senha', 'nova_senha', 'senha_atual', 'refresh', 'access',
}
_EXCLUIDOS = ('/api/v1/escudo', '/ferramentas/', '/ia/')
MAX_PROFUNDIDADE = 20


def _limpar_texto(texto):
    texto = _ETIQUETA.sub('&lt;', texto)
    return _JS_URL.sub('blocked:', texto)


def _limpar(valor, profundidade=0):
    if profundidade > MAX_PROFUNDIDADE:
        return valor
    if isinstance(valor, str):
        return _limpar_texto(valor) if '<' in valor or ':' in valor else valor
    if isinstance(valor, list):
        return [_limpar(v, profundidade + 1) for v in valor]
    if isinstance(valor, dict):
        return {k: (v if k in _CAMPOS_BINARIOS else _limpar(v, profundidade + 1)) for k, v in valor.items()}
    return valor


class SanitizarEntradaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (request.method in ('POST', 'PUT', 'PATCH')
                and 'application/json' in (request.content_type or '')
                and request.path.startswith('/api/')
                and not request.path.startswith(_EXCLUIDOS)):
            try:
                corpo = request.body
                if corpo:
                    limpo = _limpar(json.loads(corpo))
                    request._body = json.dumps(limpo, ensure_ascii=False).encode('utf-8')
                    request.META['CONTENT_LENGTH'] = str(len(request._body))
            except (ValueError, UnicodeDecodeError):
                return JsonResponse({'success': False, 'message': 'JSON inválido.'}, status=400)
            except Exception:
                pass
        return self.get_response(request)
