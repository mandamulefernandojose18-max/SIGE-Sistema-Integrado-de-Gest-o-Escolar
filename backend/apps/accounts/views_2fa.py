"""Autenticação de dois factores (TOTP) — activação, desactivação, reposição e verificação no login."""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import totp
from .audit import registrar_auditoria
from .models import LogAcesso, Usuario


def _ip(request):
    return request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR', '127.0.0.1')


def _erro(msg, http=status.HTTP_400_BAD_REQUEST, **extra):
    return Response({'success': False, 'message': msg, 'detail': msg, **extra}, status=http)


def verificar_segundo_factor(request, user, chave_ip=None, chave_global=None, incrementar_falhas=None):
    """Chamado pelo login depois de a palavra-passe estar correcta.

    Devolve None se o segundo factor foi aceite, ou uma Response 401 (`requer_2fa=True`) caso contrário.
    Um código TOTP válido só pode ser usado uma vez; um código de recuperação é consumido ao ser usado.
    """
    codigo = str(request.data.get('codigo_2fa') or '').strip()
    if not codigo:
        msg = 'Introduza o código de verificação da sua aplicação autenticadora.'
        return _erro(msg, status.HTTP_401_UNAUTHORIZED, requer_2fa=True)

    passo = totp.verificar_codigo(user.totp_secret, codigo, user.totp_ultimo_passo)
    if passo is not None:
        user.totp_ultimo_passo = passo
        user.save(update_fields=['totp_ultimo_passo'])
        return None

    restantes = totp.consumir_codigo_recuperacao(user.totp_codigos_recuperacao, codigo)
    if restantes is not None:
        user.totp_codigos_recuperacao = restantes
        user.save(update_fields=['totp_codigos_recuperacao'])
        registrar_auditoria(user, user.escola, 'SEGURANCA', '2FA_CODIGO_RECUPERACAO', user.id,
                            f'Entrada com código de recuperação 2FA ({len(restantes)} restante(s))', ip=_ip(request))
        return None

    if incrementar_falhas and chave_ip:
        incrementar_falhas(chave_ip)
        incrementar_falhas(chave_global)
    try:
        LogAcesso.objects.create(escola=user.escola, usuario=user, ip=_ip(request),
                                 user_agent=request.META.get('HTTP_USER_AGENT', ''), tipo='LOGIN_2FA_FALHA')
    except Exception:
        pass
    return _erro('Código de verificação inválido.', status.HTTP_401_UNAUTHORIZED, requer_2fa=True)


def _perfil_elegivel(user):
    return getattr(user, 'role', '') in totp.PERFIS_2FA


class Estado2FAView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        return Response({'success': True, 'data': {
            'elegivel': _perfil_elegivel(u),
            'ativo': bool(u.totp_ativo),
            'codigos_recuperacao_restantes': len(u.totp_codigos_recuperacao or []),
        }})


class Configurar2FAView(APIView):
    """Gera um segredo novo (ainda não activo) e devolve o QR para a aplicação autenticadora."""
    permission_classes = [IsAuthenticated]
    throttle_scope = 'login'

    def post(self, request):
        u = request.user
        if not _perfil_elegivel(u):
            return _erro('O 2FA está disponível apenas para perfis de gestão.', status.HTTP_403_FORBIDDEN)
        if u.totp_ativo:
            return _erro('O 2FA já está activo. Desactive-o primeiro para o reconfigurar.')
        u.totp_secret = totp.gerar_segredo()
        u.save(update_fields=['totp_secret'])
        uri = totp.uri_otpauth(u.totp_secret, u.email)
        return Response({'success': True, 'data': {
            'segredo': u.totp_secret, 'uri': uri, 'qr': totp.qr_data_uri(uri),
        }})


class Activar2FAView(APIView):
    """Confirma o primeiro código da aplicação, activa o 2FA e devolve os códigos de recuperação (uma só vez)."""
    permission_classes = [IsAuthenticated]
    throttle_scope = 'login'

    def post(self, request):
        u = request.user
        if not _perfil_elegivel(u):
            return _erro('O 2FA está disponível apenas para perfis de gestão.', status.HTTP_403_FORBIDDEN)
        if u.totp_ativo:
            return _erro('O 2FA já está activo.')
        if not u.totp_secret:
            return _erro('Inicie primeiro a configuração do 2FA.')
        if not u.check_password(str(request.data.get('password') or '')):
            return _erro('Palavra-passe incorrecta.')
        passo = totp.verificar_codigo(u.totp_secret, request.data.get('codigo'))
        if passo is None:
            return _erro('Código inválido. Verifique a hora do telemóvel e tente de novo.')
        claros, hashes = totp.gerar_codigos_recuperacao()
        u.totp_ativo = True
        u.totp_ultimo_passo = passo
        u.totp_codigos_recuperacao = hashes
        u.save(update_fields=['totp_ativo', 'totp_ultimo_passo', 'totp_codigos_recuperacao'])
        registrar_auditoria(u, u.escola, 'SEGURANCA', '2FA_ATIVADO', u.id, 'Autenticação de dois factores activada', ip=_ip(request))
        return Response({'success': True, 'message': '2FA activado.', 'data': {'codigos_recuperacao': claros}})


class Desativar2FAView(APIView):
    """Desactiva o 2FA: exige a palavra-passe e um código válido (da aplicação ou de recuperação)."""
    permission_classes = [IsAuthenticated]
    throttle_scope = 'login'

    def post(self, request):
        u = request.user
        if not u.totp_ativo:
            return _erro('O 2FA não está activo.')
        if not u.check_password(str(request.data.get('password') or '')):
            return _erro('Palavra-passe incorrecta.')
        codigo = request.data.get('codigo')
        ok = totp.verificar_codigo(u.totp_secret, codigo, u.totp_ultimo_passo) is not None
        if not ok:
            ok = totp.consumir_codigo_recuperacao(u.totp_codigos_recuperacao, codigo) is not None
        if not ok:
            return _erro('Código inválido.')
        u.totp_ativo = False
        u.totp_secret = ''
        u.totp_ultimo_passo = None
        u.totp_codigos_recuperacao = []
        u.save(update_fields=['totp_ativo', 'totp_secret', 'totp_ultimo_passo', 'totp_codigos_recuperacao'])
        registrar_auditoria(u, u.escola, 'SEGURANCA', '2FA_DESATIVADO', u.id, 'Autenticação de dois factores desactivada', ip=_ip(request))
        return Response({'success': True, 'message': '2FA desactivado.'})


class Repor2FAView(APIView):
    """Reposição por um administrador (telemóvel perdido e sem códigos de recuperação).

    SUPERADMIN repõe qualquer conta; ADMIN_ESCOLA/DIRECTOR_ESCOLA repõem contas da sua escola (nunca de SUPERADMIN).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        actor = request.user
        alvo = Usuario.objects.filter(id=user_id).first()
        permitido = False
        if alvo and alvo.id != actor.id:
            if actor.role == 'SUPERADMIN':
                permitido = True
            elif actor.role in ('ADMIN_ESCOLA', 'DIRECTOR_ESCOLA') and actor.escola_id and alvo.escola_id == actor.escola_id \
                    and alvo.role != 'SUPERADMIN':
                permitido = True
        if not permitido:
            return _erro('Utilizador não encontrado.', status.HTTP_404_NOT_FOUND)
        alvo.totp_ativo = False
        alvo.totp_secret = ''
        alvo.totp_ultimo_passo = None
        alvo.totp_codigos_recuperacao = []
        alvo.save(update_fields=['totp_ativo', 'totp_secret', 'totp_ultimo_passo', 'totp_codigos_recuperacao'])
        registrar_auditoria(actor, alvo.escola or actor.escola, 'SEGURANCA', '2FA_REPOSTO', alvo.id,
                            f'2FA de {alvo.nome} reposto por {actor.nome}', ip=_ip(request))
        return Response({'success': True, 'message': f'2FA de {alvo.nome} reposto. O utilizador pode configurá-lo de novo.'})
