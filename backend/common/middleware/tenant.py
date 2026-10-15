from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.authentication import JWTAuthentication

class TenantMiddleware(MiddlewareMixin):
    """
    Identifica e injeta o Tenant (Escola) seguro em `request.tenant`.
    - Suporta autenticação de sessão e autenticação de Token JWT (Bearer).
    - Para utilizadores normais vinculados a uma escola: utiliza `user.escola`.
    - Para SUPERADMIN: permite inspecionar uma escola via header `X-Tenant-ID` ou query param.
    """
    def process_request(self, request):
        request.tenant = None

        # 1. Se ainda não autenticado pela sessão, tenta autenticar via Bearer JWT ou query param ?token=
        if not (hasattr(request, 'user') and request.user.is_authenticated):
            auth_header = request.headers.get('Authorization') or request.META.get('HTTP_AUTHORIZATION')
            raw_token = None
            if auth_header and auth_header.startswith('Bearer '):
                raw_token = auth_header.split(' ', 1)[1].strip()
            elif request.GET.get('token'):
                raw_token = request.GET.get('token').strip()
            if raw_token:
                try:
                    jwt_auth = JWTAuthentication()
                    validated_token = jwt_auth.get_validated_token(raw_token)
                    user = jwt_auth.get_user(validated_token)
                    request.user = user
                except Exception:
                    pass

        # 2. Injeta o tenant a partir do usuário autenticado
        if hasattr(request, 'user') and request.user.is_authenticated:
            if getattr(request.user, 'role', '') == 'SUPERADMIN':
                tenant_id = request.headers.get('X-Tenant-ID') or request.GET.get('tenant_id') or request.GET.get('escola_id')
                if tenant_id:
                    from apps.tenants.models import Escola
                    request.tenant = Escola.objects.filter(id=tenant_id).first()
                else:
                    request.tenant = getattr(request.user, 'escola', None)
            elif hasattr(request.user, 'escola') and request.user.escola is not None:
                request.tenant = request.user.escola

                # SÓ E SÓ O SUPER ADMIN DEVE TER ACESSO SEMPRE INDEPENDENTEMENTE DE A ESCOLA ESTAR OU NÃO ACTIVA.
                # Para todos os utilizadores comuns: bloquear acesso à API se a escola não estiver ATIVA ou estiver bloqueada.
                st = str(getattr(request.tenant, 'status', '') or '').strip().upper()
                bloqueada = bool(getattr(request.tenant, 'bloqueada_manualmente', False))
                if st != 'ATIVA' or bloqueada:
                    from django.http import JsonResponse
                    is_exempt = (
                        request.path.startswith('/api/v1/auth/')
                        or request.path.startswith('/api/v1/health/')
                        or request.path in ['/health', '/health/']
                        or request.path.startswith('/api/v1/certificados/verificar/')
                        or request.path.startswith('/api/docs/')
                        or request.path.startswith('/api/schema/')
                        or request.path.startswith('/api/redoc/')
                    )
                    if request.path.startswith('/api/') and not is_exempt:
                        if bloqueada:
                            motivo = 'bloqueada manualmente'
                        elif 'PEND' in st:
                            motivo = 'com o registo pendente de activação'
                        else:
                            motivo = 'com a subscrição expirada'

                        return JsonResponse({
                            'success': False,
                            'message': (
                                f'Acesso bloqueado: A sua instituição de ensino ({request.tenant.nome}) encontra-se {motivo}. '
                                f'Por esse motivo, o acesso ao sistema está temporariamente vedado. '
                                f'Para restabelecer o acesso, contacte o Engenheiro do Sistema, responsável pela gestão das instituições e pela renovação das respectivas subscrições.'
                            )
                        }, status=403)
