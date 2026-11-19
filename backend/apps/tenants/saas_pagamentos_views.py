"""Vias adicionais de pagamento da assinatura SaaS:

* registo directo pelo SuperAdmin (numerário, depósito, extracto) sem comprovativo da escola;
* reconciliação por SMS M-Pesa / e-Mola: confirma sozinha, mas só quando a referência E o valor
  coincidem exactamente com um comprovativo já submetido pela escola;
* webhook de SMS com token próprio e revogável (reencaminhamento automático a partir do telemóvel);
* anexo do comprovativo servido só a quem tem direito (SuperAdmin ou pessoal da escola dona).
Todas auditadas em `SaasLogAssinatura`; a confirmação usa o mesmo núcleo da via manual.
"""
import base64
import hashlib
import mimetypes
import os
import re
import secrets
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from .models import Escola, SaasFatura, SaasPagamento, SaasWebhookToken
from .saas_middleware import limpar_cache_assinatura
from .saas_pagamentos import confirmar_pagamento_saas, reconciliar_sms_texto
from .saas_views import (METODOS_PAGAMENTO_VALIDOS, PERFIS_PAGAMENTO_ESCOLA, VALOR_MAXIMO_PAGAMENTO,
                         is_superadmin_user)


def _so_superadmin(request):
    if not is_superadmin_user(request.user):
        return Response({'success': False, 'message': 'Acesso restrito ao Super Administrador.'}, status=status.HTTP_403_FORBIDDEN)
    return None


class SaasRegistarPagamentoDirectoView(APIView):
    """O SuperAdmin lança e confirma, num só passo, um pagamento recebido por outro meio."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        negado = _so_superadmin(request)
        if negado:
            return negado

        d = request.data
        metodo = d.get('metodo')
        referencia = str(d.get('referencia') or '').strip()
        observacao = str(d.get('observacao') or '').strip()
        if metodo not in METODOS_PAGAMENTO_VALIDOS:
            return Response({'success': False, 'message': 'Método de pagamento inválido.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(observacao) < 5:
            return Response({'success': False, 'message': 'A observação é obrigatória (mínimo 5 caracteres): indique como o pagamento foi recebido.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(referencia) > 100:
            return Response({'success': False, 'message': 'A referência não pode exceder 100 caracteres.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            valor = Decimal(str(d.get('valor')).strip().replace(',', '.'))
            if not valor.is_finite() or valor <= 0 or valor > VALOR_MAXIMO_PAGAMENTO:
                raise ValueError()
            valor = valor.quantize(Decimal('0.01'))
        except Exception:
            return Response({'success': False, 'message': 'Valor de pagamento inválido.'}, status=status.HTTP_400_BAD_REQUEST)

        utilizador = (request.user.nome or request.user.email)[:150]
        with transaction.atomic():
            try:
                escola = Escola.objects.filter(id=d.get('instituicao_id')).first()
                fat = SaasFatura.objects.select_for_update().filter(id=d.get('fatura_id'), instituicao=escola).first() if escola else None
            except (ValueError, DjangoValidationError):
                escola = fat = None
            if not escola or not fat:
                return Response({'success': False, 'message': 'Instituição ou fatura não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
            if fat.estado not in ('aberta', 'em_atraso', 'paga_parcial'):
                return Response({'success': False, 'message': f'A fatura está no estado "{fat.estado}" e não aceita pagamentos.'}, status=status.HTTP_400_BAD_REQUEST)

            if not referencia:
                referencia = f"DIRECTO-{uuid.uuid4().hex[:8].upper()}"
            if SaasPagamento.objects.filter(instituicao=escola, referencia__iexact=referencia, estado__in=['enviado', 'confirmado']).exists():
                return Response({'success': False, 'message': 'Esta referência já foi utilizada num pagamento desta instituição.'}, status=status.HTTP_400_BAD_REQUEST)

            pag = SaasPagamento.objects.create(
                fatura=fat, instituicao=escola, metodo=metodo, referencia=referencia, valor=valor, estado='enviado')
            resultado = confirmar_pagamento_saas(
                pag, utilizador, accao='PAGAMENTO_REGISTADO_DIRECTO', nota=f'Registo directo pelo SuperAdmin ({observacao[:300]}).')

        limpar_cache_assinatura(escola.id)
        return Response({'success': True, 'data': resultado}, status=status.HTTP_201_CREATED)


class SaasReconciliarSmsView(APIView):
    """Janela do SuperAdmin: cola o texto de uma SMS de recebimento."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        negado = _so_superadmin(request)
        if negado:
            return negado
        texto = request.data.get('message') or request.data.get('text') or request.data.get('sms')
        codigo, payload = reconciliar_sms_texto(texto, f"Automático (SMS) — {request.user.nome or request.user.email}")
        return Response(payload, status=codigo)


# ---------------------------------------------------------------------------
# Webhook de SMS com token próprio
# ---------------------------------------------------------------------------
def _hash_token(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


class WebhookSmsThrottle(SimpleRateThrottle):
    """Limita tentativas por origem (o Nginx sobrescreve X-Forwarded-For com o IP real)."""
    scope = 'saas_webhook_sms'
    rate = '60/min'

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


class SaasWebhookSmsView(APIView):
    """Recebe SMS reencaminhadas pelo telemóvel. Autenticação só por token de webhook (cabeçalho
    `X-Webhook-Token` ou `Authorization: Bearer <token>`), guardado como hash e revogável."""
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [WebhookSmsThrottle]

    def post(self, request):
        bruto = request.headers.get('X-Webhook-Token') or ''
        if not bruto:
            auth = request.headers.get('Authorization') or ''
            if auth.startswith('Bearer '):
                bruto = auth.split(' ', 1)[1]
        bruto = bruto.strip()
        tok = SaasWebhookToken.objects.filter(token_hash=_hash_token(bruto), revogado_em__isnull=True).first() if bruto else None
        if not tok:
            return Response({'success': False, 'message': 'Token inválido ou revogado.'}, status=status.HTTP_401_UNAUTHORIZED)

        texto = request.data.get('message') or request.data.get('text') or request.data.get('content') or request.data.get('sms')
        SaasWebhookToken.objects.filter(pk=tok.pk).update(ultimo_uso_em=timezone.now(), usos=tok.usos + 1)
        codigo, payload = reconciliar_sms_texto(texto, f"Automático (SMS) — {tok.nome}")
        return Response(payload, status=codigo)


class SaasWebhookTokensView(APIView):
    """Gestão dos tokens (SuperAdmin): listar e criar. O valor em claro só aparece na criação."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        negado = _so_superadmin(request)
        if negado:
            return negado
        return Response({'success': True, 'data': [{
            'id': str(t.id), 'nome': t.nome, 'prefixo': t.prefixo, 'activo': t.activo,
            'criado_em': t.criado_em.isoformat(), 'ultimo_uso_em': t.ultimo_uso_em.isoformat() if t.ultimo_uso_em else None,
            'usos': t.usos, 'criado_por': t.criado_por,
        } for t in SaasWebhookToken.objects.all()[:50]]})

    def post(self, request):
        negado = _so_superadmin(request)
        if negado:
            return negado
        nome = str(request.data.get('nome') or '').strip()
        if not (3 <= len(nome) <= 100):
            return Response({'success': False, 'message': 'Indique um nome para o token (3 a 100 caracteres), por exemplo o telemóvel que o usa.'}, status=status.HTTP_400_BAD_REQUEST)
        if SaasWebhookToken.objects.filter(revogado_em__isnull=True).count() >= 10:
            return Response({'success': False, 'message': 'Limite de 10 tokens activos. Revogue algum antes de criar outro.'}, status=status.HTTP_400_BAD_REQUEST)
        token = 'sige_' + secrets.token_urlsafe(32)
        obj = SaasWebhookToken.objects.create(
            nome=nome, prefixo=token[:9], token_hash=_hash_token(token),
            criado_por=(request.user.nome or request.user.email)[:150])
        return Response({'success': True, 'data': {'id': str(obj.id), 'nome': obj.nome, 'prefixo': obj.prefixo, 'token': token}},
                        status=status.HTTP_201_CREATED)


class SaasWebhookTokenRevogarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        negado = _so_superadmin(request)
        if negado:
            return negado
        tok = SaasWebhookToken.objects.filter(pk=pk).first()
        if not tok:
            return Response({'success': False, 'message': 'Token não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if tok.revogado_em is None:
            tok.revogado_em = timezone.now()
            tok.save(update_fields=['revogado_em'])
        return Response({'success': True, 'message': 'Token revogado. Deixa de aceitar SMS imediatamente.'})


# ---------------------------------------------------------------------------
# Anexo do comprovativo (acesso autenticado)
# ---------------------------------------------------------------------------
_DATA_URL = re.compile(r'^data:(image/(?:png|jpeg)|application/pdf);base64,(.+)$', re.S)
_TIPOS_PERMITIDOS = {'.pdf': 'application/pdf', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}


class SaasComprovativoView(APIView):
    """Serve o anexo só ao SuperAdmin ou ao pessoal da escola dona do pagamento."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        pag = SaasPagamento.objects.filter(pk=pk).first()
        autorizado = bool(pag) and (
            is_superadmin_user(user)
            or (getattr(user, 'role', '') in PERFIS_PAGAMENTO_ESCOLA and getattr(user, 'escola_id', None) == pag.instituicao_id))
        if not autorizado:
            # Mesma resposta para "não existe" e "não é seu": não revela a existência de pagamentos alheios.
            return Response({'success': False, 'message': 'Comprovativo não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        cabecalhos = {'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'private, no-store',
                      'Content-Security-Policy': "default-src 'none'; sandbox"}

        if pag.comprovativo_path == 'base64_encoded' and pag.comprovativo_url:
            m = _DATA_URL.match(pag.comprovativo_url)
            if m:
                try:
                    conteudo = base64.b64decode(m.group(2), validate=False)
                except Exception:
                    conteudo = b''
                if conteudo:
                    resp = HttpResponse(conteudo, content_type=m.group(1))
                    for k, v in cabecalhos.items():
                        resp[k] = v
                    return resp
        elif pag.comprovativo_path:
            raiz = os.path.realpath(os.path.join(settings.MEDIA_ROOT, 'comprovativos'))
            caminho = os.path.realpath(os.path.join(settings.MEDIA_ROOT, pag.comprovativo_path))
            ext = os.path.splitext(caminho)[1].lower()
            if caminho.startswith(raiz + os.sep) and ext in _TIPOS_PERMITIDOS and os.path.isfile(caminho):
                resp = FileResponse(open(caminho, 'rb'), content_type=_TIPOS_PERMITIDOS[ext])
                resp['Content-Disposition'] = f'inline; filename="comprovativo{ext}"'
                for k, v in cabecalhos.items():
                    resp[k] = v
                return resp
        return Response({'success': False, 'message': 'Este pagamento não tem anexo disponível.'}, status=status.HTTP_404_NOT_FOUND)
