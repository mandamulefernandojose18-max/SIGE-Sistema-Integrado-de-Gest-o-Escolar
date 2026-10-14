from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

EXEMPT_PATHS = [
    '/health',
    '/health/',
    '/api/v1/auth/',
    '/api/v1/saas-admin/',
    '/api/v1/certificados/',
    '/api/v1/impressao/',
    '/api/v1/pautas/',
    '/api/v1/professores/',
    '/api/v1/material-escolar',
    '/api/v1/escolas/',
    '/api/v1/pagamentos/',
    '/api/schema/',
    '/api/docs/',
    '/api/redoc/',
    '/admin/',
    '/static/',
    '/media/',
]

MENSAGEM_EXPIRACAO = (
    "O acesso a este estabelecimento de ensino está temporariamente suspenso devido à expiração "
    "da assinatura do sistema. Por favor, regularize a sua subscrição para restaurar o acesso integral."
)

class TenantExpirationMiddleware(MiddlewareMixin):
    """
    Middleware desativado. O controlo de acesso por estado de escola é feito estritamente no LoginSerializer e no TenantMiddleware.
    """
    def process_request(self, request):
        return None

