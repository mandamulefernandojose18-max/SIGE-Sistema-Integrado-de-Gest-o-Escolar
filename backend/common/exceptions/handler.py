from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    # Tratar erro mandatório de documento sem logótipo escolhido pela instituição
    from apps.documentos.services.pdf_service import DocumentoSemLogoError
    if isinstance(exc, DocumentoSemLogoError) or (isinstance(exc, ValueError) and 'logótipo' in str(exc).lower()):
        return Response({
            'success': False,
            'error': str(exc),
            'detail': str(exc)
        }, status=status.HTTP_400_BAD_REQUEST)

    # Chamar handler padrão do DRF para os demais erros
    response = exception_handler(exc, context)
    return response
