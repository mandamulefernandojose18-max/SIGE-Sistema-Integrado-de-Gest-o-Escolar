"""Vias adicionais de pagamento da assinatura SaaS (só SuperAdmin):

* registo directo (numerário, depósito, extracto) sem comprovativo submetido pela escola;
* reconciliação por SMS M-Pesa / e-Mola: confirma sozinha, mas só quando a referência E o valor
  coincidem exactamente com um comprovativo já submetido pela escola.
Todas auditadas em `SaasLogAssinatura`; a confirmação usa o mesmo núcleo da via manual.
"""
import uuid
from decimal import Decimal

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Escola, SaasFatura, SaasPagamento
from .saas_middleware import limpar_cache_assinatura
from .saas_pagamentos import analisar_sms, confirmar_pagamento_saas
from .saas_views import (METODOS_PAGAMENTO_VALIDOS, VALOR_MAXIMO_PAGAMENTO, is_superadmin_user)
from django.core.exceptions import ValidationError as DjangoValidationError


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
    """Recebe o texto de uma SMS de recebimento e confirma o comprovativo correspondente, se existir.

    Segurança: nunca cria pagamentos; só confirma um pagamento `enviado` cuja referência coincide
    (sem distinguir maiúsculas) e cujo valor é exactamente igual ao da SMS. Em qualquer dúvida
    (sem correspondência, valor divergente, ambíguo) não confirma e devolve o motivo.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        negado = _so_superadmin(request)
        if negado:
            return negado

        texto = str(request.data.get('message') or request.data.get('text') or request.data.get('sms') or '').strip()
        if not texto:
            return Response({'success': False, 'message': 'Texto da SMS não fornecido.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(texto) > 1000:
            return Response({'success': False, 'message': 'Texto demasiado longo para uma SMS.'}, status=status.HTTP_400_BAD_REQUEST)

        valor, referencia = analisar_sms(texto)
        if valor is None or not referencia:
            return Response({'success': True, 'status': 'NAO_RECONHECIDA', 'message': 'Não foi possível ler o valor e a referência desta SMS.'})

        utilizador = f"Automático (SMS) — {request.user.nome or request.user.email}"[:150]
        with transaction.atomic():
            candidatos = list(SaasPagamento.objects.select_for_update().select_related('fatura__assinatura', 'instituicao')
                              .filter(referencia__iexact=referencia, estado='enviado'))
            if not candidatos:
                ja = SaasPagamento.objects.filter(referencia__iexact=referencia, estado='confirmado').exists()
                return Response({'success': True, 'status': 'DUPLICADO' if ja else 'SEM_CORRESPONDENCIA',
                                 'referencia': referencia, 'valor': str(valor),
                                 'message': 'Esta referência já foi confirmada.' if ja else
                                            'Nenhum comprovativo pendente com esta referência. Aguarde a submissão pela escola.'})
            exactos = [p for p in candidatos if p.valor == valor]
            if len(exactos) == 0:
                return Response({'success': True, 'status': 'VALOR_DIVERGENTE', 'referencia': referencia, 'valor': str(valor),
                                 'message': f'A referência existe, mas o valor da SMS ({valor} MZN) difere do comprovativo ({candidatos[0].valor} MZN). Valide manualmente.'})
            if len(exactos) > 1:
                return Response({'success': True, 'status': 'AMBIGUO', 'referencia': referencia, 'valor': str(valor),
                                 'message': 'Mais de um comprovativo corresponde. Valide manualmente.'})

            pag = exactos[0]
            resultado = confirmar_pagamento_saas(
                pag, utilizador, accao='PAGAMENTO_CONFIRMADO_SMS', nota='Reconciliado automaticamente por SMS.')

        limpar_cache_assinatura(pag.instituicao_id)
        return Response({'success': True, 'status': 'CONFIRMADO', 'referencia': referencia, 'valor': str(valor),
                         'instituicao': pag.instituicao.nome, 'message': 'Pagamento confirmado automaticamente.', 'data': resultado})
