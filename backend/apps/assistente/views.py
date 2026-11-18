from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.utils.tenant import get_tenant_escola
from . import engine
from .models import ConsultaAssistente

TAMANHO_MAX = 500


class PerguntarView(APIView):
    """POST /assistente/perguntar/ {pergunta, aluno_id?} — assistente de nível 0, só leitura, isolado por escola."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        escola = get_tenant_escola(request)
        if not escola:
            raise ValidationError({'escola': 'Nenhuma escola identificada.'})
        pergunta = (request.data.get('pergunta') or '').strip()
        if not pergunta:
            raise ValidationError({'pergunta': 'Escreva a sua pergunta.'})
        if len(pergunta) > TAMANHO_MAX:
            raise ValidationError({'pergunta': f'A pergunta não pode exceder {TAMANHO_MAX} caracteres.'})
        aluno_id = request.data.get('aluno_id') or None
        try:
            intencao, aluno, resposta = engine.responder(request.user, escola, pergunta, aluno_id)
        except (ValueError, TypeError, DjangoValidationError):
            raise ValidationError({'aluno_id': 'Identificador de aluno inválido.'})
        ConsultaAssistente.objects.create(escola=escola, usuario=request.user, aluno=aluno,
                                          pergunta=pergunta, intencao=intencao)
        return Response(resposta)
