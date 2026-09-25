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
    email = serializers.CharField(required=False)
    usuario = serializers.CharField(required=False)
    username = serializers.CharField(required=False)
    password = serializers.CharField(write_only=True, required=False)
    senha = serializers.CharField(write_only=True, required=False)

    def validate(self, attrs):
        login_id = (attrs.get('email') or attrs.get('usuario') or attrs.get('username') or '').strip()
        pwd = attrs.get('password') or attrs.get('senha')

        if not login_id:
            raise serializers.ValidationError('O e-mail ou nome de utilizador é obrigatório.')
        if not pwd:
            raise serializers.ValidationError('A palavra-passe é obrigatória.')

        # Permite autenticação tanto com username quanto com email
        user = authenticate(username=login_id, password=pwd)
        if not user:
            # Fallback para busca direta por email case-insensitive
            u = Usuario.objects.filter(email__iexact=login_id).first()
            if not u:
                u = Usuario.objects.filter(username__iexact=login_id).first()

            # Fallback para aliases de demonstração e variações comuns
            if not u:
                aliases = {
                    'mandamulefj@sige.com': 'mandamulefj.@sige.com',
                    'mandamulefj.@sige.com': 'mandamulefj.@sige.com',
                    'antonio.costa@escola.edu.mz': 'costa@sige.com',
                    'costa@sige.com': 'costa@sige.com',
                    'joao.baptista@escola.edu.mz': 'baptista@sige.com',
                    'baptista@sige.com': 'baptista@sige.com',
                    'manuel.silva@escola.edu.mz': 'silva@sige.com',
                    'silva@sige.com': 'silva@sige.com',
                    'carlos.mandamule@escola.edu.mz': 'mandamule@sige.com',
                    'mandamule@escola.edu.mz': 'mandamule@sige.com',
                    'mandamule@sige.com': 'mandamule@sige.com',
                }
                alias_target = aliases.get(login_id.lower())
                if alias_target:
                    u = Usuario.objects.filter(email__iexact=alias_target).first() or Usuario.objects.filter(username__iexact=alias_target).first()

            if u and u.check_password(pwd):
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
