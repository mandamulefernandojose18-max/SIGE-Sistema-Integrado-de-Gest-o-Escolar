"""Carimbo em todos os PDF, Excel, Word e ZIP gerados pelo sistema (excepto o painel do aluno).

Para qualquer descarregamento destes tipos exige-se `?carimbo=sim|nao` (409 `requer_decisao_carimbo` sem resposta)
e, com «sim», aplica-se o carimbo da escola. Um só ponto cobre todos os endpoints, actuais e futuros.
"""
import hashlib
import logging
import re

from django.http import JsonResponse

from common.utils.tenant import get_tenant_escola
from .carimbo import DecisaoCarimboPendente, carimbar_documento, decidir_carimbo

logger = logging.getLogger(__name__)

FORMATOS = {
    'application/pdf': 'pdf',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
    'application/zip': 'zip',
}
# Ficheiros que não são documentos emitidos pela escola: painel do aluno, ficheiros carregados por terceiros
# (anexos, calendário oficial) e a Blindagem Anti-IA (a integridade dos ficheiros protegidos não pode ser alterada).
EXCLUIDOS = ('/alunos/me/', '/provas-anti-ia', '/escudo/', '/ferramentas/', 'download_anexo',
             'download_documento_oficial', 'modelo_csv', '/material-escolar', '/comprovativo', '/cofre', '/auth/', '/saas', '/superadmin', '/certificados/carimbar', '/folha-resposta')


def _tipo_do_pedido(request):
    func = getattr(getattr(request, 'resolver_match', None), 'func', None)
    cls = getattr(func, 'cls', None)
    nome = cls.__name__ if cls else getattr(func, '__name__', 'documento')
    nome = re.sub(r'(PDF|XLSX|DOCX|ZIP)?View$', '', nome) or nome
    return nome.upper()[:50]


def _referencia_do_pedido(request):
    """Mesmo documento (endereço + filtros) = mesma referência = mesmo código de selo."""
    consulta = '&'.join(f"{k}={v}" for k, v in sorted(request.GET.items()) if k not in ('carimbo', 'token'))
    ref = f"{request.path}?{consulta}"
    return ref if len(ref) <= 190 else 'h:' + hashlib.sha1(ref.encode('utf-8')).hexdigest()


class CarimboDownloadsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            return self._tratar(request, response)
        except DecisaoCarimboPendente as exc:
            return JsonResponse(exc.detail, status=409)
        except Exception:
            logger.exception('Falha ao aplicar o carimbo em %s', request.path)
            # O utilizador pediu «com carimbo»: nunca se entrega o documento sem ele sem avisar.
            return JsonResponse({'success': False, 'message': 'Não foi possível aplicar o carimbo ao documento. Tente novamente.'},
                                status=500)

    def _tratar(self, request, response):
        if request.method != 'GET' or response.status_code != 200 or getattr(response, 'streaming', False):
            return response
        formato = FORMATOS.get((response.get('Content-Type') or '').split(';')[0].strip().lower())
        if not formato or any(x in request.path for x in EXCLUIDOS):
            return response
        utilizador = getattr(request, 'user', None)
        if not (utilizador and getattr(utilizador, 'is_authenticated', False)):
            return response
        if getattr(request, '_carimbo_aplicado', False):   # as vistas que já carimbam por conta própria
            return response
        escola = get_tenant_escola(request)
        if not escola:                                      # ex.: superadmin sem escola: não há carimbo
            return response
        if not decidir_carimbo(request):                    # pergunta obrigatória; aluno/encarregado: nunca
            return response
        tipo = _tipo_do_pedido(request)
        response.content = carimbar_documento(
            True, response.content, formato, escola, tipo, _referencia_do_pedido(request),
            tipo.capitalize(), getattr(utilizador, 'nome', None) or 'Secretaria')
        if response.has_header('Content-Length'):
            response['Content-Length'] = str(len(response.content))
        return response
