import re

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.utils.tenant import get_tenant_escola
from . import capacidades, engine
from .models import ConsultaAssistente

TAMANHO_MAX = 500
PAGINA_VALIDA = re.compile(r'^[a-z0-9\-]{1,60}$')


def _pagina(request):
    p = (request.data.get('pagina') if hasattr(request, 'data') else None) or request.query_params.get('pagina') or ''
    p = str(p).strip().lower()
    return p if PAGINA_VALIDA.match(p) else ''


def _escola(request):
    escola = get_tenant_escola(request)
    if not escola:
        raise ValidationError({'escola': 'Nenhuma escola identificada.'})
    return escola


class PerguntarView(APIView):
    """POST /assistente/perguntar/ {pergunta, aluno_id?, pagina?} — nível 0, só leitura, isolado por escola."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        escola = _escola(request)
        pergunta = (request.data.get('pergunta') or '').strip()
        if not pergunta:
            raise ValidationError({'pergunta': 'Escreva a sua pergunta.'})
        if len(pergunta) > TAMANHO_MAX:
            raise ValidationError({'pergunta': f'A pergunta não pode exceder {TAMANHO_MAX} caracteres.'})
        aluno_id = request.data.get('aluno_id') or None
        pagina = _pagina(request)
        try:
            intencao, aluno, resposta = engine.responder(request.user, escola, pergunta, aluno_id, pagina or None)
        except (ValueError, TypeError, DjangoValidationError):
            raise ValidationError({'aluno_id': 'Identificador de aluno inválido.'})
        consulta = ConsultaAssistente.objects.create(escola=escola, usuario=request.user, aluno=aluno, pergunta=pergunta,
                                                     intencao=intencao, pagina=pagina)
        resposta['consulta_id'] = str(consulta.id)
        return Response(resposta)


class FeedbackView(APIView):
    """POST /assistente/feedback/ {consulta_id, util} — "foi útil?" (só o próprio utilizador, na sua escola)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        escola = _escola(request)
        util = request.data.get('util')
        if not isinstance(util, bool):
            raise ValidationError({'util': 'Indique true ou false.'})
        try:
            n = ConsultaAssistente.objects.filter(id=request.data.get('consulta_id'), escola=escola, usuario=request.user).update(util=util)
        except (ValueError, TypeError, DjangoValidationError):
            raise ValidationError({'consulta_id': 'Identificador inválido.'})
        if not n:
            raise ValidationError({'consulta_id': 'Consulta não encontrada.'})
        return Response({'success': True})


class SugestoesView(APIView):
    """GET /assistente/sugestoes/?pagina= — perguntas sugeridas para o perfil e a página actual."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'sugestoes': capacidades.sugestoes(getattr(request.user, 'role', ''), _pagina(request))})
