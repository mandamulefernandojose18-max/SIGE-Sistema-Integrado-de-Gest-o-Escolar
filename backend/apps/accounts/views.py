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

        return Response({
            'success': True,
            'token': data['access'],
            'access': data['access'],
            'refresh': data['refresh'],
            'user': UsuarioSerializer(user).data
        }, status=status.HTTP_200_OK)

class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'success': True,
            'user': UsuarioSerializer(request.user).data
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

    def post(self, request, user_id):
        serializer = RedefinirSenhaSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        user = Usuario.objects.filter(id=user_id).first()
        if not user:
            return Response({'success': False, 'message': 'Utilizador não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        # Verificar isolamento: se não for SuperAdmin, só pode redefinir da própria escola
        if getattr(request.user, 'role', '') != 'SUPERADMIN' and user.escola != request.user.escola:
            return Response({'success': False, 'message': 'Sem permissão para alterar utilizador de outra escola.'}, status=status.HTTP_403_FORBIDDEN)

        user.set_password(serializer.validated_data['nova_senha'])
        user.save()

        return Response({'success': True, 'message': f'Senha de {user.nome} redefinida com sucesso!'})
