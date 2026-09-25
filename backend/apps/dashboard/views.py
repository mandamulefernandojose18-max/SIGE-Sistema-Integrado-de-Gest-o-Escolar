from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum

from apps.alunos.models import Aluno
from apps.professores.models import Professor
from apps.turmas.models import Turma
from apps.disciplinas.models import Disciplina
from apps.pagamentos.models import Pagamento

class DashboardOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        escola = request.tenant or request.user.escola
        if not escola:
            return Response({'success': False, 'message': 'Nenhuma escola associada.'})

        total_alunos = Aluno.objects.filter(escola=escola, status='ATIVO').count()
        total_professores = Professor.objects.filter(escola=escola, ativo=True).count()
        total_turmas = Turma.objects.filter(escola=escola, ano_letivo=escola.ano_letivo_ativo).count()
        total_disciplinas = Disciplina.objects.filter(escola=escola).count()

        p_pagos = Pagamento.objects.filter(escola=escola, status='PAGO').aggregate(s=Sum('valor_pago'))['s'] or 0
        p_pendentes = Pagamento.objects.filter(escola=escola, status='PENDENTE').aggregate(s=Sum('valor'))['s'] or 0

        return Response({
            'success': True,
            'data': {
                'escola': {
                    'nome': escola.nome,
                    'anoLetivo': escola.ano_letivo_ativo,
                    'trimestre': escola.trimestre_ativo,
                    'status': escola.status
                },
                'totalAlunos': total_alunos,
                'totalProfessores': total_professores,
                'totalTurmas': total_turmas,
                'totalDisciplinas': total_disciplinas,
                'propinasRecebidas': float(p_pagos),
                'propinasPendentes': float(p_pendentes),
            }
        })
