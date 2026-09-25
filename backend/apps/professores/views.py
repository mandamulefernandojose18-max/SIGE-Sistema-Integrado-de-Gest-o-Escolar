from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from .models import Professor, AlocacaoDocente
from .serializers import ProfessorSerializer, AlocacaoDocenteSerializer, CriarAlocacaoSerializer
from apps.turmas.models import Turma
from apps.disciplinas.models import Disciplina
from apps.alunos.models import Aluno
from apps.notas.models import Nota
from common.permissions.rbac import IsEscolaAdmin, IsProfessor

class ProfessorViewSet(viewsets.ModelViewSet):
    serializer_class = ProfessorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        escola = self.request.tenant or self.request.user.escola
        return Professor.objects.filter(escola=escola).prefetch_related('alocacoes').order_by('nome')

    def perform_create(self, serializer):
        escola = self.request.tenant or self.request.user.escola
        serializer.save(escola=escola)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return Response({'success': True, 'data': ProfessorSerializer(qs, many=True).data})

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
        return Response({'success': True, 'message': 'Professor excluído com sucesso.'})

class AlocarProfessorView(APIView):
    permission_classes = [IsAuthenticated, IsEscolaAdmin]

    def post(self, request):
        serializer = CriarAlocacaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        escola = request.tenant or request.user.escola
        prof = get_object_or_404(Professor, id=serializer.validated_data['professor_id'], escola=escola)
        disc = get_object_or_404(Disciplina, id=serializer.validated_data['disciplina_id'], escola=escola)
        turma = get_object_or_404(Turma, id=serializer.validated_data['turma_id'], escola=escola)

        aloc, created = AlocacaoDocente.objects.get_or_create(
            escola=escola,
            professor=prof,
            disciplina=disc,
            turma=turma
        )

        return Response({
            'success': True,
            'message': 'Alocação docente criada com sucesso.',
            'data': AlocacaoDocenteSerializer(aloc).data
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def delete(self, request, alocacao_id):
        escola = request.tenant or request.user.escola
        aloc = get_object_or_404(AlocacaoDocente, id=alocacao_id, escola=escola)
        aloc.delete()
        return Response({'success': True, 'message': 'Alocação removida com sucesso.'})

class ProfessorStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        escola = request.tenant or request.user.escola
        total = Professor.objects.filter(escola=escola).count()
        ativos = Professor.objects.filter(escola=escola, ativo=True).count()
        alocacoes = AlocacaoDocente.objects.filter(escola=escola).count()
        return Response({
            'success': True,
            'data': {
                'totalProfessores': total,
                'professoresAtivos': ativos,
                'totalAlocacoes': alocacoes
            }
        })

class MinhasTurmasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        escola = request.tenant or request.user.escola
        prof_id = request.user.professor_id

        # Se for admin, lista todas as alocações da escola
        if getattr(request.user, 'role', '') in ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP']:
            alocs = AlocacaoDocente.objects.filter(escola=escola).select_related('professor', 'disciplina', 'turma')
        elif prof_id:
            alocs = AlocacaoDocente.objects.filter(escola=escola, professor_id=prof_id).select_related('disciplina', 'turma')
        else:
            alocs = AlocacaoDocente.objects.none()

        return Response({
            'success': True,
            'data': AlocacaoDocenteSerializer(alocs, many=True).data
        })

class MeuPerfilView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.professor_id:
            return Response({'success': False, 'message': 'Utilizador não é um professor cadastrado.'}, status=status.HTTP_404_NOT_FOUND)
        prof = Professor.objects.filter(id=request.user.professor_id).first()
        if not prof:
            return Response({'success': False, 'message': 'Professor não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'data': ProfessorSerializer(prof).data})

class CadernetaCompletaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, alocacao_id):
        escola = request.tenant or request.user.escola
        aloc = get_object_or_404(AlocacaoDocente, id=alocacao_id, escola=escola)
        alunos = Aluno.objects.filter(turma=aloc.turma, status='ATIVO').order_by('nome')
        notas = Nota.objects.filter(turma=aloc.turma, disciplina=aloc.disciplina)

        notas_dict = {}
        for n in notas:
            key = f"{n.aluno_id}_{n.periodo}"
            notas_dict[key] = {
                'id': str(n.id),
                'teste1': n.teste1,
                'teste2': n.teste2,
                'teste3': n.teste3,
                'teste4': n.teste4,
                'trabalho': n.trabalho,
                'avaliacao_trimestral': n.avaliacao_trimestral,
                'media_final': n.media_final,
                'anotacao': n.anotacao,
                'comportamento': n.comportamento,
                'resultado': n.resultado,
                'faltas': n.faltas
            }

        alunos_data = []
        for a in alunos:
            alunos_data.append({
                'id': str(a.id),
                'matricula': a.matricula,
                'nome': a.nome,
                'trimestres': {
                    '1_TRIMESTRE': notas_dict.get(f"{a.id}_1_TRIMESTRE"),
                    '2_TRIMESTRE': notas_dict.get(f"{a.id}_2_TRIMESTRE"),
                    '3_TRIMESTRE': notas_dict.get(f"{a.id}_3_TRIMESTRE"),
                }
            })

        return Response({
            'success': True,
            'alocacao': AlocacaoDocenteSerializer(aloc).data,
            'alunos': alunos_data
        })
