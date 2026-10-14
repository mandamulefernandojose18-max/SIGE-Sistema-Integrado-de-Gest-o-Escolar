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
        from common.utils.tenant import get_tenant_escola
        escola = get_tenant_escola(self.request)
        if escola:
            qs = Pagamento.objects.filter(escola=escola)
        else:
            qs = Pagamento.objects.none()

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        mes = self.request.query_params.get('mes') or self.request.query_params.get('mes_referencia')
        if mes:
            qs = qs.filter(mes_referencia=mes)

        aluno_id = self.request.query_params.get('aluno_id') or self.request.query_params.get('alunoId')
        if aluno_id:
            qs = qs.filter(aluno_id=aluno_id)

        ano_param = self.request.query_params.get('ano_letivo') or self.request.query_params.get('ano')
        if ano_param and str(ano_param).upper() != 'TODOS':
            from django.db.models import Q
            try:
                ano_int = int(ano_param)
                qs = qs.filter(Q(aluno__turma__ano_letivo=ano_param) | Q(aluno__ano_ingresso=ano_param) | Q(data_vencimento__year=ano_int))
            except ValueError:
                qs = qs.filter(Q(aluno__turma__ano_letivo=ano_param) | Q(aluno__ano_ingresso=ano_param))

        return qs.select_related('aluno', 'aluno__turma', 'escola').order_by('-data_vencimento')

    def perform_create(self, serializer):
        from common.utils.tenant import get_tenant_escola
        from rest_framework import serializers as drf_serializers
        aluno = serializer.validated_data.get('aluno')
        escola = get_tenant_escola(self.request) or (getattr(aluno, 'escola', None) if aluno else None)
        if not escola:
            raise drf_serializers.ValidationError({'escola': 'Nenhuma escola identificada para registar o pagamento.'})
        if aluno and aluno.escola_id != escola.id:
            raise drf_serializers.ValidationError({'aluno': 'O aluno selecionado pertence a outra instituição de ensino.'})
        serializer.save(escola=escola)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({'success': True, 'data': serializer.data}, status=status.HTTP_201_CREATED)

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
        pagamento.data_pagamento = timezone.now().date()
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

        escola = getattr(request, 'tenant', None) or getattr(request.user, 'escola', None)
        is_super = getattr(request.user, 'role', '') == 'SUPERADMIN'
        if escola and not is_super:
            turma = get_object_or_404(Turma, id=data['turma_id'], escola=escola)
        else:
            turma = get_object_or_404(Turma, id=data['turma_id'])
            escola = turma.escola or escola
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

        taxa_adimp = round((float(total_recebido) / float(total_geral) * 100), 1) if total_geral > 0 else 0
        taxa_inadimp = round(100.0 - taxa_adimp, 1) if total_geral > 0 else 0

        historico_meses = [
            {'mes': 'Jan', 'recebido': 0, 'pendente': 0},
            {'mes': 'Fev', 'recebido': 0, 'pendente': 0},
            {'mes': 'Mar', 'recebido': float(total_recebido), 'pendente': float(total_pendente)},
        ]

        return Response({
            'success': True,
            'data': {
                'totalFaturado': float(total_geral),
                'totalRecebido': float(total_recebido),
                'totalPendente': float(total_pendente),
                'totalAtrasado': float(total_atrasado),
                'taxaAdimplencia': taxa_adimp,
                'percentualAdimplentes': taxa_adimp,
                'taxaInadimplencia': taxa_inadimp,
                'historicoMeses': historico_meses
            }
        })


