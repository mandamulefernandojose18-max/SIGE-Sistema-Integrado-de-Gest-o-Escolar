from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import Usuario, LogAcesso

class UsuarioSerializer(serializers.ModelSerializer):
    escola_id = serializers.UUIDField(source='escola.id', read_only=True, allow_null=True)
    escola_nome = serializers.CharField(source='escola.nome', read_only=True, allow_null=True)
    escola_codigo = serializers.CharField(source='escola.codigo_escola', read_only=True, allow_null=True)
    ultimo_acesso = serializers.SerializerMethodField()
    ultimo_acesso_quem = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            'id', 'nome', 'email', 'codigo_acesso', 'role', 'escola_id', 'escola_nome', 'escola_codigo',
            'ativo', 'telefone', 'avatar_url', 'aluno_id', 'professor_id', 'date_joined',
            'last_login', 'ultimo_acesso', 'ultimo_acesso_quem'
        ]
        read_only_fields = ['id', 'date_joined']

    def get_ultimo_acesso(self, obj):
        if obj.last_login:
            return obj.last_login.isoformat()
        log = LogAcesso.objects.filter(usuario=obj, tipo='LOGIN_SUCESSO').order_by('-created_at').first()
        return log.created_at.isoformat() if log else None

    def get_ultimo_acesso_quem(self, obj):
        return obj.nome or obj.codigo_acesso or obj.username or obj.email

class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(required=False)
    usuario = serializers.CharField(required=False)
    username = serializers.CharField(required=False)
    codigo = serializers.CharField(required=False)
    password = serializers.CharField(write_only=True, required=False)
    senha = serializers.CharField(write_only=True, required=False)

    def validate(self, attrs):
        login_id = (
            attrs.get('email')
            or attrs.get('usuario')
            or attrs.get('username')
            or attrs.get('codigo')
            or ''
        ).strip()
        pwd = attrs.get('password') or attrs.get('senha')

        if not login_id:
            raise serializers.ValidationError('O código de acesso, e-mail ou nome de utilizador é obrigatório.')
        if not pwd:
            raise serializers.ValidationError('A palavra-passe é obrigatória.')

        # Permite autenticação tanto com username quanto com email
        user = authenticate(username=login_id, password=pwd)
        if not user:
            # Fallback para busca direta por email ou username case-insensitive
            u = Usuario.objects.filter(email__iexact=login_id).first()
            if not u:
                u = Usuario.objects.filter(username__iexact=login_id).first()
            if u and u.check_password(pwd):
                user = u

        # Busca por Código de Acesso Oficial (GD..., DP..., SECR..., PR..., código do aluno, etc.)
        if not user:
            candidatos_cod = Usuario.objects.filter(codigo_acesso__iexact=login_id)
            for cand in candidatos_cod:
                if cand.check_password(pwd):
                    user = cand
                    break

        # Busca por Código de Director de Turma (DT...) ou Director de Classe (DC...) homologado
        if not user and (login_id.upper().startswith('DT') or login_id.upper().startswith('DC')):
            try:
                from apps.turmas.models import Turma
                from django.db.models import Q
                turma_dir = Turma.objects.filter(
                    Q(codigo_director_turma__iexact=login_id, dt_status_homologacao='HOMOLOGADO') |
                    Q(codigo_director_classe__iexact=login_id, dc_status_homologacao='HOMOLOGADO')
                ).first()
                if turma_dir:
                    prof_alvo = (
                        turma_dir.director_turma
                        if (turma_dir.codigo_director_turma or '').upper() == login_id.upper()
                        else turma_dir.director_classe
                    )
                    if prof_alvo:
                        u_prof = Usuario.objects.filter(professor_id=prof_alvo.id).first() or Usuario.objects.filter(email__iexact=prof_alvo.email).first()
                        if u_prof and u_prof.check_password(pwd):
                            user = u_prof
            except Exception:
                pass

        # Fallback para aliases de demonstração e variações comuns
        if not user:
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
            raise serializers.ValidationError('Credenciais inválidas. Verifique o código/email e a senha.')

        if not user.ativo or not user.is_active:
            raise serializers.ValidationError('Conta de utilizador inativa ou desativada.')

        refresh = RefreshToken.for_user(user)
        # Custom claims para conformidade com JWT do SIGE
        refresh['role'] = user.role
        refresh['nome'] = user.nome
        refresh['codigo_acesso'] = user.codigo_acesso
        refresh['escola_id'] = str(user.escola_id) if user.escola_id else None

        return {
            'user': user,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }

class RedefinirSenhaSerializer(serializers.Serializer):
    nova_senha = serializers.CharField(min_length=6, write_only=True)
