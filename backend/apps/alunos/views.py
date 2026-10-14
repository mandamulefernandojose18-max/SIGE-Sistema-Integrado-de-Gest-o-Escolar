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
        from common.utils.tenant import get_tenant_escola
        escola = get_tenant_escola(self.request)
        if escola:
            qs = Aluno.objects.filter(escola=escola)
        else:
            qs = Aluno.objects.none()

        turma_id = self.request.query_params.get('turma_id') or self.request.query_params.get('turmaId')
        if turma_id:
            qs = qs.filter(turma_id=turma_id)

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        classe_param = self.request.query_params.get('classe')
        if classe_param:
            if classe_param == 'SEM_TURMA':
                qs = qs.filter(turma__isnull=True)
            elif classe_param != 'TODAS':
                qs = qs.filter(Q(classe__iexact=classe_param) | Q(turma__grau_ano__iexact=classe_param))

        ano_param = (
            self.request.query_params.get('ano_ingresso') or 
            self.request.query_params.get('ano') or 
            self.request.query_params.get('ano_letivo')
        )
        if ano_param and str(ano_param).upper() != 'TODOS':
            qs = qs.filter(Q(ano_ingresso=ano_param) | Q(turma__ano_letivo=ano_param))

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
        from common.utils.tenant import get_tenant_escola
        from rest_framework import serializers as drf_serializers
        escola = get_tenant_escola(self.request)
        if not escola and serializer.validated_data.get('turma'):
            escola = serializer.validated_data['turma'].escola

        if not escola:
            raise drf_serializers.ValidationError({
                'escola': 'Nenhuma escola seleccionada. Por favor, seleccione uma escola no topo antes de matricular o aluno.'
            })

        turma = serializer.validated_data.get('turma')
        if turma and turma.escola_id != escola.id:
            raise drf_serializers.ValidationError({
                'turma': 'A turma selecionada pertence a uma instituição de ensino diferente da escola ativa.'
            })

        ano_ingresso = (
            serializer.validated_data.get('ano_ingresso') or 
            self.request.data.get('ano_ingresso') or 
            (escola.ano_letivo_ativo if escola else None) or 
            '2026'
        )

        from .models import gerar_proxima_matricula
        turma = serializer.validated_data.get('turma')
        classe = serializer.validated_data.get('classe') or (turma.grau_ano if turma else None)
        area = serializer.validated_data.get('area') or (turma.area if turma else None)
        matricula = gerar_proxima_matricula(
            escola=escola,
            ano_ingresso=ano_ingresso,
            classe=classe,
            turma=turma,
            area=area,
        )
        serializer.save(escola=escola, matricula=matricula, ano_ingresso=ano_ingresso)

    def list(self, request, *args, **kwargs):
        # Suporte a paginação e resposta compatível
        page = self.paginate_queryset(self.get_queryset())
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({'success': True, 'data': serializer.data})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({'success': True, 'data': serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({'success': True, 'data': serializer.data}, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        response = super().update(request, *args, **kwargs)
        return Response({'success': True, 'data': response.data})

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return Response({'success': True, 'message': 'Aluno excluído com sucesso.'})

    @action(detail=True, methods=['post', 'put'], url_path='transferir')
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
        escola = getattr(request, 'tenant', None) or getattr(request.user, 'escola', None)
        if not escola and getattr(request.user, 'role', '') == 'SUPERADMIN':
            qs = Aluno.objects.all()
        elif escola:
            qs = Aluno.objects.filter(escola=escola)
        else:
            qs = Aluno.objects.none()

        total = qs.count()
        ativos = qs.filter(status='ATIVO').count()
        genero_counts = dict(qs.values_list('genero').annotate(total=Count('id')))
        genero_m = genero_counts.get('M', 0)
        genero_f = genero_counts.get('F', 0)
        genero_dict = {'M': genero_m, 'F': genero_f}

        return Response({
            'success': True,
            'data': {
                'totalAlunos': total,
                'totalGeral': total,
                'alunosAtivos': ativos,
                'taxaRetencao': 0.0,
                'taxaEvasao': 0.0,
                'porGenero': genero_dict,
                'genero': genero_dict
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
            'comportamento': n.comportamento if ((n.media_final is not None and n.media_final > 0) or any(x is not None and x > 0 for x in [n.teste1, n.teste2, n.teste3, n.trabalho, n.avaliacao_trimestral])) else ''
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
