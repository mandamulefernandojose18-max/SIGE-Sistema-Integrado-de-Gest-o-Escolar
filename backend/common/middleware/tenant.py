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

        # 1. Se ainda não autenticado pela sessão, tenta autenticar via Bearer JWT
        if not (hasattr(request, 'user') and request.user.is_authenticated):
            auth_header = request.headers.get('Authorization') or request.META.get('HTTP_AUTHORIZATION')
            if auth_header and auth_header.startswith('Bearer '):
                try:
                    raw_token = auth_header.split(' ', 1)[1].strip()
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
