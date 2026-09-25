from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count

from .models import Aluno
from .serializers import AlunoSerializer, TransferirAlunoSerializer
from apps.turmas.models import Turma
from apps.notas.models import Nota
from apps.pagamentos.models import Pagamento

class AlunoViewSet(viewsets.ModelViewSet):
    serializer_class = AlunoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        escola = self.request.tenant or self.request.user.escola
        qs = Aluno.objects.filter(escola=escola)

        turma_id = self.request.query_params.get('turma_id')
        if turma_id:
            qs = qs.filter(turma_id=turma_id)

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(nome__icontains=search) |
                Q(apelido__icontains=search) |
                Q(matricula__icontains=search) |
                Q(numero_documento__icontains=search)
            )

        return qs.order_by('nome')

    def perform_create(self, serializer):
        escola = self.request.tenant or self.request.user.escola
        serializer.save(escola=escola)

    def list(self, request, *args, **kwargs):
        # Suporte a paginação e resposta compatível
        page = self.paginate_queryset(self.get_queryset())
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({'success': True, 'data': serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({'success': True, 'data': serializer.data}, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response({'success': True, 'data': response.data})

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return Response({'success': True, 'message': 'Aluno excluído com sucesso.'})

    @action(detail=True, methods=['post'], url_path='transferir')
    def transferir(self, request, pk=None):
        aluno = self.get_object()
        serializer = TransferirAlunoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        turma_destino = Turma.objects.filter(
            id=serializer.validated_data['turma_destino_id'],
            escola=aluno.escola
        ).first()

        if not turma_destino:
            return Response({'success': False, 'message': 'Turma de destino não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        aluno.turma = turma_destino
        aluno.save()

        return Response({
            'success': True,
            'message': f"Aluno {aluno.nome} transferido para {turma_destino.nome} com sucesso!",
            'data': AlunoSerializer(aluno).data
        })

class AlunoStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        escola = request.tenant or request.user.escola
        qs = Aluno.objects.filter(escola=escola)
        total = qs.count()
        ativos = qs.filter(status='ATIVO').count()
        genero = dict(qs.values_list('genero').annotate(total=Count('id')))

        return Response({
            'success': True,
            'data': {
                'totalAlunos': total,
                'alunosAtivos': ativos,
                'porGenero': genero
            }
        })

class AlunoPerfilMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.aluno_id:
            return Response({'success': False, 'message': 'Utilizador não é um aluno cadastrado.'}, status=status.HTTP_404_NOT_FOUND)
        aluno = Aluno.objects.filter(id=request.user.aluno_id).first()
        if not aluno:
            return Response({'success': False, 'message': 'Aluno não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'data': AlunoSerializer(aluno).data})

class AlunoMeNotasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.aluno_id:
            return Response({'success': False, 'message': 'Não autorizado.'}, status=status.HTTP_403_FORBIDDEN)
        notas = Nota.objects.filter(aluno_id=request.user.aluno_id).select_related('disciplina')
        data = [{
            'id': str(n.id),
            'disciplina': n.disciplina.nome,
            'periodo': n.periodo,
            'teste1': n.teste1,
            'teste2': n.teste2,
            'trabalho': n.trabalho,
            'avaliacao_trimestral': n.avaliacao_trimestral,
            'media_final': n.media_final,
            'resultado': n.resultado,
            'comportamento': n.comportamento
        } for n in notas]
        return Response({'success': True, 'data': data})

class AlunoMePagamentosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.aluno_id:
            return Response({'success': False, 'message': 'Não autorizado.'}, status=status.HTTP_403_FORBIDDEN)
        pagamentos = Pagamento.objects.filter(aluno_id=request.user.aluno_id).order_by('-data_vencimento')
        data = [{
            'id': str(p.id),
            'descricao': p.descricao,
            'mes_referencia': p.mes_referencia,
            'valor': str(p.valor),
            'valor_pago': str(p.valor_pago),
            'status': p.status,
            'data_vencimento': p.data_vencimento,
            'data_pagamento': p.data_pagamento,
            'recibo_numero': p.recibo_numero
        } for p in pagamentos]
        return Response({'success': True, 'data': data})
