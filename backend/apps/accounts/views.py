from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenRefreshView
from django.db.models import Count

from .models import Usuario, LogAcesso
from .serializers import UsuarioSerializer, LoginSerializer, RedefinirSenhaSerializer
from common.permissions.rbac import IsEscolaAdmin

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': serializer.errors.get('non_field_errors', ['Credenciais inválidas'])[0]
            }, status=status.HTTP_401_UNAUTHORIZED)

        data = serializer.validated_data
        user = data['user']

        # Registrar Log de Acesso
        LogAcesso.objects.create(
            escola=user.escola,
            usuario=user,
            ip=request.META.get('REMOTE_ADDR', '127.0.0.1'),
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
            from apps.tenants.serializers import EscolaSerializer
            escola = Escola.objects.select_related('plano').prefetch_related('assinaturas__plano').filter(id=user.escola_id).first()
            if escola:
                escola_data = EscolaSerializer(escola).data

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
        user_data = UsuarioSerializer(request.user).data
        escola_data = None
        escola = getattr(request, 'tenant', None) or getattr(request.user, 'escola', None)
        if escola:
            from apps.tenants.serializers import EscolaSerializer
            escola_data = EscolaSerializer(escola).data

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
        qs = Usuario.objects.all()
        if getattr(request.user, 'role', '') != 'SUPERADMIN' and request.user.escola:
            qs = qs.filter(escola=request.user.escola)

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

        if not nova_senha or len(nova_senha) < 4:
            return Response({'success': False, 'message': 'Informe uma nova palavra-passe (mínimo 4 caracteres).'}, status=status.HTTP_400_BAD_REQUEST)

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

        if not nova_senha or len(nova_senha) < 4:
            return Response({
                'success': False,
                'message': 'A nova palavra-passe deve ter pelo menos 4 caracteres.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if senha_atual:
            from .serializers import _validar_senha_ou_codigo_inicial
            if not _validar_senha_ou_codigo_inicial(user, senha_atual):
                return Response({
                    'success': False,
                    'message': 'A senha actual informada está incorrecta (se ainda não redefiniu, introduza o seu código de acesso).'
                }, status=status.HTTP_400_BAD_REQUEST)

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


