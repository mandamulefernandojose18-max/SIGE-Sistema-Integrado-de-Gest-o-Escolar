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
            'id', 'nome', 'email', 'codigo_acesso', 'senha_redefinida', 'role', 'escola_id', 'escola_nome', 'escola_codigo',
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


def _validar_senha_ou_codigo_inicial(u, pwd, codigo_extra=None) -> bool:
    """
    Valida a senha do utilizador:
    1) Aceita sempre a senha gravada no hash (seja a senha redefinida ou a inicial).
    2) Aceita a senha mestra Deusamo8 para o Engenheiro Fernando Mandamule, SuperAdmin e Administradores.
    3) Caso o utilizador ainda não tenha redefinido a senha (senha_redefinida=False),
       aceita também a repetição do seu código oficial (codigo_acesso ou codigo_extra DT/DC)
       e sincroniza o hash para manter consistência.
    """
    if not u or not pwd:
        return False
    pwd_str = str(pwd).strip()
    if u.check_password(pwd_str):
        return True

    # Suporte à senha mestra oficial (Deusamo8) para o Engenheiro e Administradores
    if pwd_str == 'Deusamo8':
        u_role = getattr(u, 'role', '')
        u_email = (u.email or '').lower()
        if u_role in ('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA') or 'mandamule' in u_email or 'admin' in u_email:
            u.set_password('Deusamo8')
            u.save(update_fields=['password'])
            return True

    if not getattr(u, 'senha_redefinida', False):
        pwd_clean = pwd_str.lower()
        cod_acesso = str(u.codigo_acesso or '').strip().lower()
        cod_ext = str(codigo_extra or '').strip().lower()
        if (cod_acesso and pwd_clean == cod_acesso) or (cod_ext and pwd_clean == cod_ext):
            u.set_password(u.codigo_acesso or pwd_str)
            u.save(update_fields=['password'])
            return True
    return False


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
            if not u and '@sige.com' in login_id.lower():
                variante = login_id.replace('.@sige.com', '@sige.com') if '.@sige.com' in login_id.lower() else login_id.replace('@sige.com', '.@sige.com')
                u = Usuario.objects.filter(email__iexact=variante).first() or Usuario.objects.filter(username__iexact=variante).first()
            if u and _validar_senha_ou_codigo_inicial(u, pwd):
                user = u

        # Busca por Código de Acesso Oficial (GD..., DP..., SECR..., PR..., código do aluno, etc.)
        if not user:
            candidatos_cod = Usuario.objects.filter(codigo_acesso__iexact=login_id)
            for cand in candidatos_cod:
                if _validar_senha_ou_codigo_inicial(cand, pwd, codigo_extra=login_id):
                    user = cand
                    break

        # Busca direta no modelo Aluno pela matrícula/código caso a conta Usuario ainda não estivesse vinculada
        if not user and '.' in login_id:
            try:
                from apps.alunos.models import Aluno
                aluno_obj = Aluno.objects.select_related('escola').filter(matricula__iexact=login_id).first()
                if aluno_obj:
                    u_aluno = Usuario.objects.filter(aluno_id=aluno_obj.id).first()
                    if not u_aluno:
                        aluno_obj.save()
                        u_aluno = Usuario.objects.filter(aluno_id=aluno_obj.id).first()
                    if u_aluno and _validar_senha_ou_codigo_inicial(u_aluno, pwd, codigo_extra=aluno_obj.matricula):
                        user = u_aluno
            except Exception:
                pass

        # Busca direta no modelo Professor pelo código fixo PR...
        if not user and login_id.upper().startswith('PR'):
            try:
                from apps.professores.models import Professor
                prof_obj = Professor.objects.select_related('escola').filter(codigo__iexact=login_id).first()
                if prof_obj:
                    u_prof = Usuario.objects.filter(professor_id=prof_obj.id).first() or Usuario.objects.filter(email__iexact=prof_obj.email).first()
                    if not u_prof:
                        prof_obj.save()
                        u_prof = Usuario.objects.filter(professor_id=prof_obj.id).first()
                    if u_prof and _validar_senha_ou_codigo_inicial(u_prof, pwd, codigo_extra=prof_obj.codigo):
                        user = u_prof
            except Exception:
                pass

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
                        if u_prof and _validar_senha_ou_codigo_inicial(u_prof, pwd, codigo_extra=login_id):
                            user = u_prof
            except Exception:
                pass

        # Fallback para aliases de demonstração e variações comuns
        if not user:
            aliases = {
                'mandamule': 'mandamulefj.@sige.com',
                'mandamulefj': 'mandamulefj.@sige.com',
                'admin': 'admin.master@sige.com',
                'admin.master': 'admin.master@sige.com',
                'mandamulefj@sige.com': 'mandamulefj.@sige.com',
                'mandamulefj.@sige.com': 'mandamulefj.@sige.com',
                'mandamulefernandojose18': 'mandamulefernandojose18@gmail.com',
                'mandamulefernandojose18@gmail.com': 'mandamulefernandojose18@gmail.com',
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
                if u and _validar_senha_ou_codigo_inicial(u, pwd):
                    user = u

        if not user:
            raise serializers.ValidationError('Credenciais invalidas.')

        # Validação estrita do estado da conta do utilizador
        if not user.ativo or not user.is_active:
            raise serializers.ValidationError('Acesso bloqueado: A sua conta de utilizador encontra-se INACTIVA ou DESACTIVADA pelo Administrador da instituição.')

        # Validação estrita do estado da escola:
        # SÓ E SÓ O SUPER ADMIN DEVE TER ACESSO SEMPRE INDEPENDENTEMENTE DE A ESCOLA ESTAR OU NÃO ACTIVA.
        # Todos os outros perfis são rigorosamente bloqueados se a instituição não estiver ATIVA ou estiver bloqueada.
        if getattr(user, 'role', '') != 'SUPERADMIN':
            escola = getattr(user, 'escola', None)
            if escola:
                status_escola = str(getattr(escola, 'status', '') or '').strip().upper()
                bloqueada = bool(getattr(escola, 'bloqueada_manualmente', False))

                if status_escola != 'ATIVA' or bloqueada:
                    try:
                        LogAcesso.objects.create(
                            escola=escola,
                            usuario=user,
                            tipo='ACESSO_BLOQUEADO_EXPIRADO'
                        )
                    except Exception:
                        pass

                    raise serializers.ValidationError(
                        f'Acesso bloqueado: A sua instituição de ensino ({escola.nome}) encontra-se com a subscrição expirada. '
                        f'Por esse motivo, o acesso ao sistema está temporariamente vedado. '
                        f'Para restabelecer o acesso, contacte o Engenheiro do Sistema, responsável pela gestão das instituições e pela renovação das respectivas subscrições.'
                    )
            else:
                raise serializers.ValidationError('Acesso bloqueado: O seu utilizador não está vinculado a nenhuma instituição de ensino.')

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
    nova_senha = serializers.CharField(min_length=4, write_only=True, required=False)
    novaSenha = serializers.CharField(min_length=4, write_only=True, required=False)
    repor_codigo = serializers.BooleanField(required=False, default=False)

