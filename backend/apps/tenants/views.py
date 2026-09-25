from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.db.models import Sum, Count

from .models import Plano, Escola, AssinaturaEscola
from .serializers import PlanoSerializer, EscolaSerializer, AssinaturaEscolaSerializer
from apps.accounts.models import Usuario
from apps.accounts.serializers import UsuarioSerializer
from apps.alunos.models import Aluno
from apps.professores.models import Professor
from common.permissions.rbac import IsSuperAdmin, IsEscolaAdmin
from common.utils.geografia_mocambique import (
    PROVINCIAS_MOCAMBIQUE,
    DISTRITOS_POR_PROVINCIA,
    CARREIRAS_DOCENTES,
    TIPOS_DOCUMENTO,
    ANOTACOES_STATUS,
    COMPORTAMENTOS
)

class GeografiaView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'success': True,
            'data': {
                'provincias': PROVINCIAS_MOCAMBIQUE,
                'distritos': DISTRITOS_POR_PROVINCIA,
                'carreiras': CARREIRAS_DOCENTES,
                'tiposDocumento': TIPOS_DOCUMENTO,
                'anotacoes': ANOTACOES_STATUS,
                'comportamentos': COMPORTAMENTOS
            }
        })

class SaaSMetricsView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        total_escolas = Escola.objects.count()
        escolas_ativas = Escola.objects.filter(status='ATIVA').count()
        escolas_expiradas = Escola.objects.filter(status='EXPIRADA').count()
        total_alunos = Aluno.objects.count()
        total_professores = Professor.objects.count()
        mrr = AssinaturaEscola.objects.filter(status='ATIVA').aggregate(total=Sum('valor'))['total'] or 0

        return Response({
            'success': True,
            'metrics': {
                'totalEscolas': total_escolas,
                'escolasAtivas': escolas_ativas,
                'escolasExpiradas': escolas_expiradas,
                'totalAlunos': total_alunos,
                'totalProfessores': total_professores,
                'receitaMensalEstimada': float(mrr),
                'mrr': float(mrr)
            }
        })

class PlanoViewSet(viewsets.ModelViewSet):
    queryset = Plano.objects.all()
    serializer_class = PlanoSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return Response({'success': True, 'data': PlanoSerializer(qs, many=True).data})

    @action(detail=True, methods=['put', 'patch'], url_path='preco')
    def preco(self, request, pk=None):
        plano = self.get_object()
        novo_preco = request.data.get('preco')
        if novo_preco is not None:
            plano.preco = novo_preco
            plano.save()
            return Response({'success': True, 'data': PlanoSerializer(plano).data})
        return Response({'success': False, 'message': 'Preço não fornecido.'}, status=status.HTTP_400_BAD_REQUEST)

class EscolaViewSet(viewsets.ModelViewSet):
    queryset = Escola.objects.all()
    serializer_class = EscolaSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return Response({'success': True, 'data': EscolaSerializer(qs, many=True).data})

    @action(detail=True, methods=['post'], url_path='toggle-status')
    def toggle_status(self, request, pk=None):
        escola = self.get_object()
        escola.status = 'SUSPENSA' if escola.status == 'ATIVA' else 'ATIVA'
        escola.save()
        return Response({
            'success': True,
            'message': f"Escola {escola.nome} alterada para status {escola.status}",
            'data': EscolaSerializer(escola).data
        })

class VerificarExpiracoesView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request):
        agora = timezone.now()
        # Escolas cuja assinatura mais recente venceu
        expiradas = 0
        for escola in Escola.objects.filter(status='ATIVA'):
            ultima_assinatura = escola.assinaturas.order_by('-data_fim').first()
            if ultima_assinatura and ultima_assinatura.data_fim < agora:
                escola.status = 'EXPIRADA'
                escola.save()
                ultima_assinatura.status = 'EXPIRADA'
                ultima_assinatura.save()
                expiradas += 1

        return Response({
            'success': True,
            'message': f"Verificação concluída. {expiradas} escolas marcadas como expiradas.",
            'totalExpiradas': expiradas
        })

class EscolaAdminInfoView(APIView):
    permission_classes = [IsAuthenticated, IsEscolaAdmin]

    def get(self, request):
        escola = request.tenant or request.user.escola
        if not escola:
            return Response({'success': False, 'message': 'Nenhuma escola associada.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'data': EscolaSerializer(escola).data})

    def put(self, request):
        escola = request.tenant or request.user.escola
        if not escola:
            return Response({'success': False, 'message': 'Nenhuma escola associada.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = EscolaSerializer(escola, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'success': True, 'data': serializer.data})
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class ToggleNotasView(APIView):
    permission_classes = [IsAuthenticated, IsEscolaAdmin]

    def post(self, request):
        escola = request.tenant or request.user.escola
        if not escola:
            return Response({'success': False, 'message': 'Escola não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        escola.permitir_visualizacao_notas = not escola.permitir_visualizacao_notas
        escola.save()
        return Response({
            'success': True,
            'permitir_visualizacao_notas': escola.permitir_visualizacao_notas,
            'message': f"Visualização de notas agora está {'ativada' if escola.permitir_visualizacao_notas else 'desativada'}."
        })

class UsuariosCredenciaisView(APIView):
    permission_classes = [IsAuthenticated, IsEscolaAdmin]

    def get(self, request):
        escola = request.tenant or request.user.escola
        usuarios = Usuario.objects.filter(escola=escola)
        return Response({
            'success': True,
            'data': UsuarioSerializer(usuarios, many=True).data
        })
