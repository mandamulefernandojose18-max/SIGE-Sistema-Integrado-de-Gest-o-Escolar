from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from django.utils import timezone

from apps.alunos.models import Aluno
from apps.professores.models import Professor
from apps.turmas.models import Turma
from apps.disciplinas.models import Disciplina
from apps.pagamentos.models import Pagamento
from apps.tenants.models import Escola

class DashboardOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        escola = getattr(request, 'tenant', None) or getattr(request.user, 'escola', None)
        is_super = getattr(request.user, 'role', '') == 'SUPERADMIN'

        if not escola and is_super:
            total_alunos_todos = Aluno.objects.count()
            total_alunos_ativos = Aluno.objects.filter(status='ATIVO').count()
            total_professores = Professor.objects.filter(ativo=True).count()
            total_turmas = Turma.objects.count()
            total_disciplinas = Disciplina.objects.count()

            p_pagos = Pagamento.objects.filter(status='PAGO').aggregate(s=Sum('valor_pago'))['s'] or 0
            p_pendentes = Pagamento.objects.filter(status='PENDENTE').aggregate(s=Sum('valor'))['s'] or 0

            indicadores = {
                'totalAlunos': total_alunos_todos,
                'alunosAtivos': total_alunos_ativos,
                'totalProfessores': total_professores,
                'totalRecebido': float(p_pagos),
                'totalPendente': float(p_pendentes),
            }

            return Response({
                'success': True,
                'data': {
                    'escola': {
                        'nome': 'Visão Master SaaS (Todas as Escolas)',
                        'anoLetivo': '2026',
                        'trimestre': '1_TRIMESTRE',
                        'status': 'ATIVA',
                        'diasRestantesAssinatura': 365
                    },
                    'indicadores': indicadores,
                    'totalAlunos': total_alunos_todos,
                    'alunosAtivos': total_alunos_ativos,
                    'totalProfessores': total_professores,
                    'totalTurmas': total_turmas,
                    'totalDisciplinas': total_disciplinas,
                    'propinasRecebidas': float(p_pagos),
                    'propinasPendentes': float(p_pendentes),
                }
            })

        if not escola:
            return Response({'success': False, 'message': 'Nenhuma escola associada.'})

        total_alunos_todos = Aluno.objects.filter(escola=escola).count()
        total_alunos_ativos = Aluno.objects.filter(escola=escola, status='ATIVO').count()
        total_professores = Professor.objects.filter(escola=escola, ativo=True).count()
        total_turmas = Turma.objects.filter(escola=escola, ano_letivo=escola.ano_letivo_ativo).count()
        total_disciplinas = Disciplina.objects.filter(escola=escola).count()

        p_pagos = Pagamento.objects.filter(escola=escola, status='PAGO').aggregate(s=Sum('valor_pago'))['s'] or 0
        p_pendentes = Pagamento.objects.filter(escola=escola, status='PENDENTE').aggregate(s=Sum('valor'))['s'] or 0

        dias_restantes = 0
        ass_ativa = escola.assinaturas.order_by('-data_fim').first()
        if ass_ativa and ass_ativa.data_fim:
            diff = (ass_ativa.data_fim - timezone.now()).days
            dias_restantes = max(0, diff)

        indicadores = {
            'totalAlunos': total_alunos_todos,
            'alunosAtivos': total_alunos_ativos,
            'totalProfessores': total_professores,
            'totalRecebido': float(p_pagos),
            'totalPendente': float(p_pendentes),
        }

        return Response({
            'success': True,
            'data': {
                'escola': {
                    'nome': escola.nome,
                    'anoLetivo': escola.ano_letivo_ativo,
                    'trimestre': escola.trimestre_ativo,
                    'status': escola.status,
                    'diasRestantesAssinatura': dias_restantes
                },
                'indicadores': indicadores,
                'totalAlunos': total_alunos_todos,
                'alunosAtivos': total_alunos_ativos,
                'totalProfessores': total_professores,
                'totalTurmas': total_turmas,
                'totalDisciplinas': total_disciplinas,
                'propinasRecebidas': float(p_pagos),
                'propinasPendentes': float(p_pendentes),
            }
        })

