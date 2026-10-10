from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Nota, PermissaoEdicaoNotas
from .serializers import NotaSerializer, SalvarNotasBulkSerializer, PermissaoEdicaoNotasSerializer
from apps.turmas.models import Turma
from apps.disciplinas.models import Disciplina
from apps.alunos.models import Aluno
from apps.professores.models import Professor
from common.utils.avaliacoes_mocambique import calcular_media_trimestral
from common.permissions.rbac import IsEscolaAdmin

class NotaViewSet(viewsets.ModelViewSet):
    serializer_class = NotaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        escola = self.request.tenant or self.request.user.escola
        qs = Nota.objects.filter(escola=escola)

        turma_id = self.request.query_params.get('turma_id')
        if turma_id:
            qs = qs.filter(turma_id=turma_id)

        disciplina_id = self.request.query_params.get('disciplina_id')
        if disciplina_id:
            qs = qs.filter(disciplina_id=disciplina_id)

        periodo = self.request.query_params.get('periodo')
        if periodo:
            qs = qs.filter(periodo=periodo)

        aluno_id = self.request.query_params.get('aluno_id')
        if aluno_id:
            qs = qs.filter(aluno_id=aluno_id)

        return qs.select_related('aluno', 'disciplina', 'turma').order_by('aluno__nome')

    def create(self, request, *args, **kwargs):
        # Lançamento em lote ou individual
        if 'notas' in request.data:
            serializer = SalvarNotasBulkSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            escola = request.tenant or request.user.escola
            turma = get_object_or_404(Turma, id=data['turma_id'], escola=escola)
            disciplina = get_object_or_404(Disciplina, id=data['disciplina_id'], escola=escola)
            periodo = data['periodo']

            salvos = 0
            for item in data['notas']:
                aluno_id = item.get('aluno_id')
                if not aluno_id:
                    continue

                aluno = Aluno.objects.filter(id=aluno_id, escola=escola).first()
                if not aluno:
                    continue

                # Cálculo oficial de avaliação de Moçambique
                calc = calcular_media_trimestral(item)

                Nota.objects.update_or_create(
                    escola=escola,
                    aluno=aluno,
                    disciplina=disciplina,
                    turma=turma,
                    periodo=periodo,
                    defaults={
                        'teste1': item.get('teste1') if item.get('teste1') != '' else 0,
                        'teste2': item.get('teste2') if item.get('teste2') != '' else 0,
                        'teste3': item.get('teste3') if item.get('teste3') != '' else None,
                        'teste4': item.get('teste4') if item.get('teste4') != '' else None,
                        'trabalho': item.get('trabalho') if item.get('trabalho') != '' else 0,
                        'avaliacao_trimestral': item.get('avaliacao_trimestral') if item.get('avaliacao_trimestral') != '' else 0,
                        'media_final': calc['mediaFinal'],
                        'resultado': calc['resultado'],
                        'comportamento': item.get('comportamento') or calc.get('comportamento') or '',
                        'anotacao': item.get('anotacao') or None,
                        'faltas': int(item.get('faltas') or 0),
                    }
                )
                salvos += 1

            return Response({
                'success': True,
                'message': f"Lançamento concluído com sucesso para {salvos} aluno(s).",
                'totalSalvos': salvos
            }, status=status.HTTP_200_OK)

        # Lançamento individual (modal caderneta)
        aluno_id = request.data.get('aluno_id')
        turma_id = request.data.get('turma_id')
        disciplina_id = request.data.get('disciplina_id')
        periodo = request.data.get('periodo')

        if periodo in ('TODOS', '', None) or periodo not in ('1_TRIMESTRE', '2_TRIMESTRE', '3_TRIMESTRE', 'ANUAL'):
            return Response({
                'success': False,
                'message': 'Selecione um trimestre válido (1º, 2º ou 3º Trimestre) para gravar a avaliação.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if aluno_id and turma_id and disciplina_id and periodo:
            escola = request.tenant or request.user.escola
            turma = get_object_or_404(Turma, id=turma_id, escola=escola)
            disciplina = get_object_or_404(Disciplina, id=disciplina_id, escola=escola)
            aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)

            calc = calcular_media_trimestral(request.data)

            def parse_num(val):
                if val is None or val == '':
                    return None
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return None

            try:
                nota_obj, created = Nota.objects.update_or_create(
                    escola=escola,
                    aluno=aluno,
                    disciplina=disciplina,
                    turma=turma,
                    periodo=periodo,
                    defaults={
                        'teste1': parse_num(request.data.get('teste1')),
                        'teste2': parse_num(request.data.get('teste2')),
                        'teste3': parse_num(request.data.get('teste3')),
                        'teste4': parse_num(request.data.get('teste4')),
                        'trabalho': parse_num(request.data.get('trabalho')),
                        'avaliacao_trimestral': parse_num(request.data.get('avaliacao_trimestral')),
                        'media_final': calc['mediaFinal'],
                        'resultado': calc['resultado'],
                        'comportamento': request.data.get('comportamento') or calc.get('comportamento') or '',
                        'anotacao': request.data.get('anotacao') or None,
                        'faltas': int(request.data.get('faltas') or 0),
                    }
                )
            except Exception as e:
                return Response({
                    'success': False,
                    'message': f'Erro de integridade ao gravar avaliação: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)

            return Response({
                'success': True,
                'message': 'Avaliação gravada com sucesso.',
                'data': NotaSerializer(nota_obj).data
            }, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)

        return Response({
            'success': False,
            'message': 'Campos obrigatórios em falta: aluno_id, turma_id, disciplina_id e periodo são todos necessários.'
        }, status=status.HTTP_400_BAD_REQUEST)

class PrazosTrimestresView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        escola = request.tenant or request.user.escola
        trimestre_ativo = escola.trimestre_ativo if escola else '1_TRIMESTRE'

        return Response({
            'success': True,
            'trimestreAtivo': trimestre_ativo,
            'prazos': {
                '1_TRIMESTRE': {'aberto': trimestre_ativo == '1_TRIMESTRE', 'nome': '1º Trimestre'},
                '2_TRIMESTRE': {'aberto': trimestre_ativo == '2_TRIMESTRE', 'nome': '2º Trimestre'},
                '3_TRIMESTRE': {'aberto': trimestre_ativo == '3_TRIMESTRE', 'nome': '3º Trimestre'},
            }
        })

class AutorizacaoEdicaoView(APIView):
    permission_classes = [IsAuthenticated, IsEscolaAdmin]

    def get(self, request):
        escola = request.tenant or request.user.escola
        perms = PermissaoEdicaoNotas.objects.filter(escola=escola, ativa=True)
        return Response({'success': True, 'data': PermissaoEdicaoNotasSerializer(perms, many=True).data})

    def post(self, request):
        escola = request.tenant or request.user.escola
        prof = get_object_or_404(Professor, id=request.data.get('professor_id'), escola=escola)
        turma = get_object_or_404(Turma, id=request.data.get('turma_id'), escola=escola)
        disc = get_object_or_404(Disciplina, id=request.data.get('disciplina_id'), escola=escola)

        perm, _ = PermissaoEdicaoNotas.objects.update_or_create(
            escola=escola,
            professor=prof,
            turma=turma,
            disciplina=disc,
            periodo=request.data.get('periodo', '1_TRIMESTRE'),
            defaults={
                'autorizado_por': request.user.nome,
                'motivo': request.data.get('motivo', 'Autorização Pedagógica'),
                'ativa': True
            }
        )
        return Response({'success': True, 'message': 'Desbloqueio autorizado.', 'data': PermissaoEdicaoNotasSerializer(perm).data})

    def delete(self, request, perm_id):
        escola = request.tenant or request.user.escola
        perm = get_object_or_404(PermissaoEdicaoNotas, id=perm_id, escola=escola)
        perm.ativa = False
        perm.save()
        return Response({'success': True, 'message': 'Autorização revogada.'})
