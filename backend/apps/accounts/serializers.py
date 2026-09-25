from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import Usuario, LogAcesso

class UsuarioSerializer(serializers.ModelSerializer):
    escola_id = serializers.UUIDField(source='escola.id', read_only=True, allow_null=True)
    escola_nome = serializers.CharField(source='escola.nome', read_only=True, allow_null=True)

    class Meta:
        model = Usuario
        fields = [
            'id', 'nome', 'email', 'role', 'escola_id', 'escola_nome',
            'ativo', 'telefone', 'avatar_url', 'aluno_id', 'professor_id', 'date_joined'
        ]
        read_only_fields = ['id', 'date_joined']

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        # Permite autenticação tanto com username quanto com email
        user = authenticate(username=email, password=password)
        if not user:
            # Fallback para busca direta por email caso username difira
            u = Usuario.objects.filter(email=email).first()
            if u and u.check_password(password):
                user = u

        if not user:
            raise serializers.ValidationError('Credenciais inválidas. Verifique o email e a senha.')

        if not user.ativo or not user.is_active:
            raise serializers.ValidationError('Conta de utilizador inativa ou desativada.')

        refresh = RefreshToken.for_user(user)
        # Custom claims para conformidade com JWT do SIGE
        refresh['role'] = user.role
        refresh['nome'] = user.nome
        refresh['escola_id'] = str(user.escola_id) if user.escola_id else None

        return {
            'user': user,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }

class RedefinirSenhaSerializer(serializers.Serializer):
    nova_senha = serializers.CharField(min_length=6, write_only=True)
