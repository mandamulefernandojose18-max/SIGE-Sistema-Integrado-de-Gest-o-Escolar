import uuid
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum, Count
from django.shortcuts import get_object_or_404

from .models import Pagamento
from .serializers import (
    PagamentoSerializer,
    LiquidarPagamentoSerializer,
    GerarPagamentosTurmaSerializer
)
from apps.alunos.models import Aluno
from apps.turmas.models import Turma
from common.permissions.rbac import IsEscolaAdmin

class PagamentoViewSet(viewsets.ModelViewSet):
    serializer_class = PagamentoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        escola = self.request.tenant or self.request.user.escola
        qs = Pagamento.objects.filter(escola=escola)

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        mes = self.request.query_params.get('mes') or self.request.query_params.get('mes_referencia')
        if mes:
            qs = qs.filter(mes_referencia=mes)

        aluno_id = self.request.query_params.get('aluno_id')
        if aluno_id:
            qs = qs.filter(aluno_id=aluno_id)

        return qs.select_related('aluno', 'aluno__turma').order_by('-data_vencimento')

    def perform_create(self, serializer):
        escola = self.request.tenant or self.request.user.escola
        serializer.save(escola=escola)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return Response({'success': True, 'data': PagamentoSerializer(qs, many=True).data})

    @action(detail=True, methods=['post'], url_path='liquidar')
    def liquidar(self, request, pk=None):
        pagamento = self.get_object()
        serializer = LiquidarPagamentoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        valor_pago = serializer.validated_data.get('valor_pago') or pagamento.valor
        metodo = serializer.validated_data.get('metodo_pagamento', 'MPESA')

        pagamento.valor_pago = valor_pago
        pagamento.status = 'PAGO'
        pagamento.data_pagamento = timezone.now()
        pagamento.metodo_pagamento = metodo
        if not pagamento.recibo_numero:
            ano = timezone.now().year
            num_seq = Pagamento.objects.filter(escola=pagamento.escola, status='PAGO').count() + 1
            pagamento.recibo_numero = f"REC-{ano}-{num_seq:05d}"
        pagamento.save()

        return Response({
            'success': True,
            'message': f"Pagamento liquidado com sucesso! Recibo: {pagamento.recibo_numero}",
            'data': PagamentoSerializer(pagamento).data
        })

    @action(detail=False, methods=['post'], url_path='gerar-turma')
    def gerar_turma(self, request):
        serializer = GerarPagamentosTurmaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        escola = request.tenant or request.user.escola
        turma = get_object_or_404(Turma, id=data['turma_id'], escola=escola)
        alunos = Aluno.objects.filter(turma=turma, status='ATIVO')

        criados = 0
        for aluno in alunos:
            # Evita duplicatas para a mesma descrição e mês
            obj, created = Pagamento.objects.get_or_create(
                escola=escola,
                aluno=aluno,
                descricao=data['descricao'],
                mes_referencia=data['mes_referencia'],
                defaults={
                    'valor': data['valor'],
                    'data_vencimento': data['data_vencimento'],
                    'status': 'PENDENTE'
                }
            )
            if created:
                criados += 1

        return Response({
            'success': True,
            'message': f"Gerados {criados} pagamentos para os alunos da turma {turma.nome}.",
            'totalGerados': criados
        })

class PagamentoStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        escola = getattr(request, 'tenant', None) or getattr(request.user, 'escola', None)
        if not escola and getattr(request.user, 'role', '') == 'SUPERADMIN':
            qs = Pagamento.objects.all()
        elif escola:
            qs = Pagamento.objects.filter(escola=escola)
        else:
            qs = Pagamento.objects.none()

        total_recebido = qs.filter(status='PAGO').aggregate(total=Sum('valor_pago'))['total'] or 0
        total_pendente = qs.filter(status='PENDENTE').aggregate(total=Sum('valor'))['total'] or 0
        total_atrasado = qs.filter(status='ATRASADO').aggregate(total=Sum('valor'))['total'] or 0
        total_geral = total_recebido + total_pendente + total_atrasado

        taxa = round((float(total_recebido) / float(total_geral) * 100), 1) if total_geral > 0 else 0

        historico_meses = [
            {'mes': 'Jan', 'recebido': 0, 'pendente': 0},
            {'mes': 'Fev', 'recebido': 0, 'pendente': 0},
            {'mes': 'Mar', 'recebido': float(total_recebido), 'pendente': float(total_pendente)},
        ]

        return Response({
            'success': True,
            'data': {
                'totalRecebido': float(total_recebido),
                'totalPendente': float(total_pendente),
                'totalAtrasado': float(total_atrasado),
                'taxaAdimplencia': taxa,
                'historicoMeses': historico_meses
            }
        })

