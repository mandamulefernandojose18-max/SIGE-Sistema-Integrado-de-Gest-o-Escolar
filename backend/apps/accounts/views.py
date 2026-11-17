from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenRefreshView
import hashlib

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import Usuario, LogAcesso
from .serializers import UsuarioSerializer, LoginSerializer, RedefinirSenhaSerializer
from common.permissions.rbac import IsEscolaAdmin

# Bloqueio temporário por tentativas falhadas (por identificador+IP e global por identificador).
# Usa a cache do Django (por processo; com 2 workers o limite efectivo pode chegar ao dobro).
LOGIN_MAX_FALHAS = 5            # por (identificador, IP)
LOGIN_MAX_FALHAS_GLOBAL = 30    # por identificador, de qualquer IP
LOGIN_JANELA_SEGUNDOS = 15 * 60


def _incrementar_falhas(chave):
    if cache.add(chave, 1, LOGIN_JANELA_SEGUNDOS):
        return 1
    try:
        return cache.incr(chave)
    except ValueError:
        cache.set(chave, 1, LOGIN_JANELA_SEGUNDOS)
        return 1


def _ip_cliente(request):
    return request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR', '127.0.0.1')


def _chaves_login(request):
    ident = (request.data.get('email') or request.data.get('usuario') or request.data.get('username')
             or request.data.get('codigo') or '')
    ident = str(ident).strip().lower()
    if not ident:
        return None, None
    h = hashlib.sha256(ident.encode('utf-8')).hexdigest()[:32]
    return f'login_falhas:{h}:{_ip_cliente(request)}', f'login_falhas_global:{h}'


class LogoutView(APIView):
    """Termina a sessão: coloca o refresh token na blacklist (deixa de poder gerar novos acessos).

    Aceita o refresh token no corpo; responde sempre 200 (idempotente, sem revelar se o token era válido)."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        refresh = (request.data.get('refresh') or request.data.get('refreshToken') or '').strip()
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except TokenError:
                pass
        return Response({'success': True, 'message': 'Sessão terminada.'})


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'login'

    def post(self, request):
        chave_ip, chave_global = _chaves_login(request)
        if chave_ip and (cache.get(chave_ip, 0) >= LOGIN_MAX_FALHAS or cache.get(chave_global, 0) >= LOGIN_MAX_FALHAS_GLOBAL):
            msg = 'Demasiadas tentativas falhadas. Tente novamente dentro de 15 minutos.'
            return Response({'success': False, 'message': msg, 'detail': msg},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            errors = serializer.errors
            msg = 'Credenciais invalidas.'
            if isinstance(errors, dict):
                first_val = next(iter(errors.values()), None)
                if isinstance(first_val, list) and len(first_val) > 0:
                    msg = str(first_val[0])
                elif isinstance(first_val, str):
                    msg = first_val
            elif isinstance(errors, list) and len(errors) > 0:
                msg = str(errors[0])
            if chave_ip and msg.lower().startswith('credenciais'):
                n_ip = _incrementar_falhas(chave_ip)
                _incrementar_falhas(chave_global)
                if n_ip == LOGIN_MAX_FALHAS:
                    try:
                        LogAcesso.objects.create(
                            ip=_ip_cliente(request),
                            user_agent=request.META.get('HTTP_USER_AGENT', ''),
                            tipo='LOGIN_BLOQUEADO'
                        )
                    except Exception:
                        pass
            return Response({
                'success': False,
                'message': msg,
                'detail': msg
            }, status=status.HTTP_401_UNAUTHORIZED)

        data = serializer.validated_data
        user = data['user']
        if chave_ip:
            cache.delete(chave_ip)

        # Registrar Log de Acesso
        LogAcesso.objects.create(
            escola=user.escola,
            usuario=user,
            ip=request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR', '127.0.0.1'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            tipo='LOGIN_SUCESSO'
        )

        from django.utils import timezone
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        user_data = UsuarioSerializer(user).data
        escola_data = None
        if user.escola_id:
            from apps.tenants.models import Escola
            from apps.tenants.serializers import EscolaListSerializer
            escola = Escola.objects.select_related('plano', 'pacote').prefetch_related('assinaturas__plano').filter(id=user.escola_id).first()
            if escola:
                escola_data = EscolaListSerializer(escola).data

        return Response({
            'success': True,
            'message': 'Autenticação realizada com sucesso',
            'data': {
                'user': user_data,
                'escola': escola_data,
                'tokens': {
                    'accessToken': data['access'],
                    'refreshToken': data['refresh'],
                }
            },
            'token': data['access'],
            'access': data['access'],
            'refresh': data['refresh'],
            'user': user_data
        }, status=status.HTTP_200_OK)

class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from common.utils.tenant import get_tenant_escola
        user_data = UsuarioSerializer(request.user).data
        escola_data = None
        escola = get_tenant_escola(request)
        if escola:
            from apps.tenants.serializers import EscolaListSerializer
            escola_data = EscolaListSerializer(escola).data

        return Response({
            'success': True,
            'user': user_data,
            'tenant': escola_data,
            'escola': escola_data,
            'data': {
                'user': user_data,
                'tenant': escola_data,
                'escola': escola_data
            }
        })

class UserStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from common.utils.tenant import get_tenant_escola
        escola = get_tenant_escola(request)
        qs = Usuario.objects.all()
        if escola:
            qs = qs.filter(escola=escola)
        elif getattr(request.user, 'role', '') != 'SUPERADMIN':
            qs = Usuario.objects.none()

        stats = qs.values('role').annotate(total=Count('id'))
        return Response({
            'success': True,
            'data': list(stats)
        })

class RedefinirSenhaView(APIView):
    permission_classes = [IsAuthenticated, IsEscolaAdmin]

    def _executar(self, request, user_id):
        serializer = RedefinirSenhaSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        user = Usuario.objects.filter(id=user_id).first()
        if not user:
            return Response({'success': False, 'message': 'Utilizador não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if getattr(request.user, 'role', '') != 'SUPERADMIN' and user.escola != request.user.escola:
            return Response({'success': False, 'message': 'Sem permissão para alterar utilizador de outra escola.'}, status=status.HTTP_403_FORBIDDEN)

        repor_codigo = serializer.validated_data.get('repor_codigo', False) or bool(request.data.get('reporCodigo'))
        nova_senha = (
            serializer.validated_data.get('nova_senha')
            or serializer.validated_data.get('novaSenha')
            or request.data.get('nova_senha')
            or request.data.get('novaSenha')
            or request.data.get('senha')
            or ''
        ).strip()

        if repor_codigo:
            cod_padrao = (user.codigo_acesso or '').strip()
            if not cod_padrao:
                return Response({'success': False, 'message': 'Este utilizador não possui código oficial atribuído.'}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(cod_padrao)
            user.senha_redefinida = False
            user.save(update_fields=['password', 'senha_redefinida'])
            return Response({
                'success': True,
                'message': f'Senha de {user.nome} reposta para o código oficial ({cod_padrao}) com sucesso!'
            })

        if not nova_senha or len(nova_senha) < settings.MIN_SENHA_UTILIZADOR:
            return Response({'success': False, 'message': f'Informe uma nova palavra-passe (mínimo {settings.MIN_SENHA_UTILIZADOR} caracteres).'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(nova_senha)
        user.senha_redefinida = (nova_senha.lower() != (user.codigo_acesso or '').strip().lower())
        user.save(update_fields=['password', 'senha_redefinida'])

        return Response({'success': True, 'message': f'Senha de {user.nome} redefinida com sucesso!'})

    def post(self, request, user_id):
        return self._executar(request, user_id)

    def put(self, request, user_id):
        return self._executar(request, user_id)


class AlterarMinhaSenhaView(APIView):
    """Permite que qualquer utilizador autenticado (GD, DP, SECR, Professor, DT, DC, Aluno) redefina a sua própria senha."""
    permission_classes = [IsAuthenticated]

    def _executar(self, request):
        user = request.user
        senha_atual = (request.data.get('senha_atual') or request.data.get('senhaAtual') or '').strip()
        nova_senha = (
            request.data.get('nova_senha')
            or request.data.get('novaSenha')
            or request.data.get('senha')
            or ''
        ).strip()

        if not nova_senha or len(nova_senha) < settings.MIN_SENHA_UTILIZADOR:
            return Response({
                'success': False,
                'message': f'A nova palavra-passe deve ter pelo menos {settings.MIN_SENHA_UTILIZADOR} caracteres.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # A senha actual é SEMPRE exigida: um token roubado não basta para tomar a conta.
        # No 1.º acesso (senha_redefinida=False) a senha actual é a repetição do código oficial.
        if not senha_atual:
            return Response({
                'success': False,
                'message': 'Informe a senha actual (no 1.º acesso é a repetição do seu código de acesso).'
            }, status=status.HTTP_400_BAD_REQUEST)

        chave_falhas = f'troca_senha_falhas:{user.pk}'
        if cache.get(chave_falhas, 0) >= LOGIN_MAX_FALHAS:
            return Response({
                'success': False,
                'message': 'Demasiadas tentativas falhadas. Tente novamente dentro de alguns minutos.'
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        from .serializers import _validar_senha_ou_codigo_inicial
        if not _validar_senha_ou_codigo_inicial(user, senha_atual):
            _incrementar_falhas(chave_falhas)
            return Response({
                'success': False,
                'message': 'A senha actual informada está incorrecta (se ainda não redefiniu, introduza o seu código de acesso).'
            }, status=status.HTTP_400_BAD_REQUEST)
        cache.delete(chave_falhas)

        user.set_password(nova_senha)
        user.senha_redefinida = (nova_senha.lower() != (user.codigo_acesso or '').strip().lower())
        user.save(update_fields=['password', 'senha_redefinida'])

        return Response({
            'success': True,
            'message': 'A sua palavra-passe foi redefinida com sucesso!',
            'data': UsuarioSerializer(user).data
        })

    def post(self, request):
        return self._executar(request)

    def put(self, request):
        return self._executar(request)




from .models import LogAuditoria
from .serializers import LogAuditoriaSerializer

class AuditoriaListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = getattr(request.user, 'role', '')
        if role not in ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA']:
            return Response({'success': False, 'message': 'Acesso restrito à Direcção e Administração.'}, status=403)

        qs = LogAuditoria.objects.all()
        if role != 'SUPERADMIN' or not request.GET.get('todas_escolas'):
            if request.user.escola:
                qs = qs.filter(escola=request.user.escola)
            elif role != 'SUPERADMIN':
                qs = qs.none()

        entidade = request.GET.get('entidade')
        if entidade:
            qs = qs.filter(entidade__iexact=entidade)
        acao = request.GET.get('acao')
        if acao:
            qs = qs.filter(acao__iexact=acao)
        objeto_id = request.GET.get('objeto_id')
        if objeto_id:
            qs = qs.filter(objeto_id=objeto_id)

        # Filtros por data (AAAA-MM-DD), inclusivos
        from django.utils.dateparse import parse_date
        data_inicio = parse_date(request.GET.get('data_inicio') or '')
        data_fim = parse_date(request.GET.get('data_fim') or '')
        if data_inicio:
            qs = qs.filter(created_at__date__gte=data_inicio)
        if data_fim:
            qs = qs.filter(created_at__date__lte=data_fim)

        try:
            limite = max(1, min(int(request.GET.get('limit', 100)), 500))
        except Exception:
            limite = 100
        try:
            offset = max(0, int(request.GET.get('offset', 0)))
        except Exception:
            offset = 0

        total = qs.count()
        logs = qs[offset:offset + limite]
        serializer = LogAuditoriaSerializer(logs, many=True)
        return Response({'success': True, 'data': serializer.data, 'total': total, 'offset': offset, 'limit': limite})
