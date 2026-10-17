import time
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication

# Cache leve em memória com expiração (TTL de 45 segundos)
_ASSINATURA_CACHE = {}
_CACHE_TTL = 45


def obter_estado_assinatura_cached(instituicao_id):
    agora = time.time()
    cached = _ASSINATURA_CACHE.get(str(instituicao_id))
    if cached and (agora - cached['timestamp']) < _CACHE_TTL:
        return cached['estado'], cached['assinatura_id']

    from apps.tenants.models import SaasAssinatura
    ass = SaasAssinatura.objects.filter(instituicao_id=instituicao_id).order_by('-created_at').first()
    if ass:
        estado = ass.estado
        ass_id = ass.id
    else:
        # Se ainda não possui registo SaaS, consideramos activa (retrocompatibilidade)
        estado = 'activa'
        ass_id = None

    _ASSINATURA_CACHE[str(instituicao_id)] = {
        'estado': estado,
        'assinatura_id': ass_id,
        'timestamp': agora
    }
    return estado, ass_id


def limpar_cache_assinatura(instituicao_id=None):
    if instituicao_id:
        _ASSINATURA_CACHE.pop(str(instituicao_id), None)
    else:
        _ASSINATURA_CACHE.clear()


class VerificarAssinaturaMiddleware(MiddlewareMixin):
    """
    Middleware corporativo de Controlo de Acesso por Assinatura SaaS:
    - SUPERADMIN: Totalmente isento (acesso irrestrito e soberano).
    - teste / activa / fatura_pendente: Acesso total.
    - em_atraso: Acesso total + cabeçalho de aviso X-Assinatura-Alerta: em_atraso.
    - restrita: Leitura permitida (GET/HEAD/OPTIONS); mutações bloqueadas (POST/PUT/PATCH/DELETE)
      exceto envio de comprovativos de pagamento.
    - suspensa / cancelada: Apenas login, logout e rotas de regularização/pagamento da assinatura.
    """

    ROTAS_ISENTAS_SEMPRE = (
        '/api/v1/auth/',
        '/api/v1/health',
        '/api/v1/health/',
        '/health',
        '/health/',
        '/api/docs/',
        '/api/schema/',
        '/api/redoc/',
        '/api/v1/certificados/verificar/',
        '/api/v1/saas/minha-assinatura',
        '/api/v1/saas/minha-assinatura/',
        '/api/v1/saas/faturas',
        '/api/v1/saas/faturas/',
        '/api/v1/saas/pagamentos',
        '/api/v1/saas/pagamentos/',
    )

    def process_request(self, request):
        # 1. Garante identificação do utilizador via Bearer se ainda não autenticado
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
                    request.user = jwt_auth.get_user(validated_token)
                except Exception:
                    pass

        # SuperAdmin é sempre soberano e isento de bloqueios SaaS
        if hasattr(request, 'user') and getattr(request.user, 'role', '') == 'SUPERADMIN':
            return None

        # Verificar tenant associado
        instituicao = getattr(request, 'tenant', None)
        if not instituicao and hasattr(request, 'user') and getattr(request.user, 'escola', None):
            instituicao = request.user.escola

        if not instituicao:
            return None

        estado, assinatura_id = obter_estado_assinatura_cached(instituicao.id)
        request.assinatura_estado = estado
        request.assinatura_id = assinatura_id

        path = request.path

        # 2. Verificação para ESTADO SUSPENSA ou CANCELADA
        if estado in ('suspensa', 'cancelada'):
            is_isenta = any(path.startswith(prefix) for prefix in self.ROTAS_ISENTAS_SEMPRE)
            if not is_isenta:
                return JsonResponse({
                    'success': False,
                    'codigo': 'ASSINATURA_SUSPENSA',
                    'estado_assinatura': estado,
                    'message': (
                        f'Acesso suspenso: A sua instituição ({instituicao.nome}) encontra-se com a subscrição {estado.upper()}. '
                        f'O acesso às funcionalidades normais está temporariamente bloqueado até regularização da fatura. '
                        f'Aceda à página de regularização de pagamentos para submeter o comprovativo de liquidação.'
                    )
                }, status=403)

        # 3. Verificação para ESTADO RESTRITA (Somente Leitura)
        elif estado == 'restrita':
            if request.method not in ('GET', 'HEAD', 'OPTIONS'):
                is_rota_pagamento = any(path.startswith(p) for p in (
                    '/api/v1/saas/pagamentos',
                    '/api/v1/auth/logout',
                ))
                if not is_rota_pagamento:
                    return JsonResponse({
                        'success': False,
                        'codigo': 'ASSINATURA_RESTRITA',
                        'estado_assinatura': estado,
                        'message': (
                            f'Acesso em modo restrito (apenas consulta): O prazo de tolerância da subscrição da instituição ({instituicao.nome}) expirou. '
                            f'Não é permitido criar, editar ou eliminar dados até à regularização do pagamento.'
                        )
                    }, status=403)

        return None

    def process_response(self, request, response):
        # Injeta cabeçalho com alerta para o frontend quando em_atraso ou restrita
        estado = getattr(request, 'assinatura_estado', None)
        if estado in ('em_atraso', 'restrita'):
            response['X-Assinatura-Alerta'] = estado
        return response
