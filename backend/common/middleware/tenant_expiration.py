from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

EXEMPT_PATHS = [
    '/health',
    '/health/',
    '/api/v1/auth/',
    '/api/v1/saas-admin/',
    '/api/v1/certificados/verificar/',
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
    Bloqueia o acesso com HTTP 402 (Payment Required) caso a escola esteja com status 'EXPIRADA'
    ou bloqueada manualmente, exceto para rotas públicas e de gestão do SaaS.
    """
    def process_request(self, request):
        path = request.path

        # Rotas isentas não são bloqueadas
        for exempt in EXEMPT_PATHS:
            if path.startswith(exempt):
                return None

        # SuperAdmin nunca é bloqueado
        if hasattr(request, 'user') and request.user.is_authenticated:
            if getattr(request.user, 'role', '') == 'SUPERADMIN':
                return None

        tenant = getattr(request, 'tenant', None)
        if tenant:
            if getattr(tenant, 'status', 'ATIVA') == 'EXPIRADA' or getattr(tenant, 'bloqueada_manualmente', False):
                return JsonResponse({
                    'success': False,
                    'message': MENSAGEM_EXPIRACAO,
                    'code': 'TENANT_EXPIRED',
                    'escola': {
                        'id': str(tenant.id),
                        'nome': tenant.nome,
                        'status': tenant.status
                    }
                }, status=402)

        return None
