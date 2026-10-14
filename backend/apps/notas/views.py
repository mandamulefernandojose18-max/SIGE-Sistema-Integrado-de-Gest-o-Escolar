from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from datetime import timedelta
from django.utils import timezone

from .models import Nota, PermissaoEdicaoNotas
from .serializers import NotaSerializer, SalvarNotasBulkSerializer, PermissaoEdicaoNotasSerializer
from .prazos_service import verificar_prazo_lancamento_trimestre, obter_configuracao_prazos
from apps.turmas.models import Turma
from apps.disciplinas.models import Disciplina
from apps.alunos.models import Aluno
from apps.professores.models import Professor
from common.utils.avaliacoes_mocambique import calcular_media_trimestral
from common.permissions.rbac import IsEscolaAdmin
from common.utils.tenant import get_tenant_escola

class NotaViewSet(viewsets.ModelViewSet):
    serializer_class = NotaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        escola = get_tenant_escola(self.request)
        if not escola:
            return Nota.objects.none()
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
        escola = get_tenant_escola(request)
        if not escola:
            return Response({'success': False, 'message': 'Instituição não identificada.'}, status=status.HTTP_400_BAD_REQUEST)

        # Lançamento em lote ou individual
        if 'notas' in request.data:
            serializer = SalvarNotasBulkSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            turma = get_object_or_404(Turma, id=data['turma_id'], escola=escola)
            disciplina = get_object_or_404(Disciplina, id=data['disciplina_id'], escola=escola)
            periodo = data['periodo']

            # Validação oficial de Prazos de Calendarização
            permitido, motivo, msg_prazo, _ = verificar_prazo_lancamento_trimestre(
                escola=escola,
                periodo=periodo,
                turma=turma,
                disciplina=disciplina,
                user=request.user
            )
            if not permitido:
                return Response({
                    'success': False,
                    'message': msg_prazo,
                    'bloqueado': True,
                    'motivo': motivo
                }, status=status.HTTP_403_FORBIDDEN)

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
            escola = get_tenant_escola(request)
            if not escola:
                return Response({'success': False, 'message': 'Instituição não identificada.'}, status=status.HTTP_400_BAD_REQUEST)
            turma = get_object_or_404(Turma, id=turma_id, escola=escola)
            disciplina = get_object_or_404(Disciplina, id=disciplina_id, escola=escola)
            aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)

            # Validação oficial de Prazos de Calendarização
            permitido, motivo, msg_prazo, _ = verificar_prazo_lancamento_trimestre(
                escola=escola,
                periodo=periodo,
                turma=turma,
                disciplina=disciplina,
                user=request.user
            )
            if not permitido:
                return Response({
                    'success': False,
                    'message': msg_prazo,
                    'bloqueado': True,
                    'motivo': motivo
                }, status=status.HTTP_403_FORBIDDEN)

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
        escola = get_tenant_escola(request)
        if not escola:
            return Response({'success': False, 'message': 'Instituição não identificada.'}, status=status.HTTP_400_BAD_REQUEST)
        trimestre_ativo = escola.trimestre_ativo if escola else '1_TRIMESTRE'
        cfg = obter_configuracao_prazos(escola)

        # Avaliar status de cada trimestre para resposta rica
        status_t1, motivo_t1, msg_t1, info_t1 = verificar_prazo_lancamento_trimestre(escola, '1_TRIMESTRE', user=request.user)
        status_t2, motivo_t2, msg_t2, info_t2 = verificar_prazo_lancamento_trimestre(escola, '2_TRIMESTRE', user=request.user)
        status_t3, motivo_t3, msg_t3, info_t3 = verificar_prazo_lancamento_trimestre(escola, '3_TRIMESTRE', user=request.user)

        data_dict = {
            'modo_calendarizacao': getattr(escola, 'modo_calendarizacao', 'MANUAL'),
            'tipo_duracao_automatica': getattr(escola, 'tipo_duracao_automatica', 'SEMANAS'),
            'valor_duracao_automatica': getattr(escola, 'valor_duracao_automatica', 4),
            'data_base_automatica': str(getattr(escola, 'data_base_automatica', '')) if getattr(escola, 'data_base_automatica', None) else '',
            'data_inicio_t1': str(cfg['1_TRIMESTRE']['inicio'] or '') if cfg['1_TRIMESTRE']['inicio'] else '',
            'data_fim_t1': str(cfg['1_TRIMESTRE']['fim'] or '') if cfg['1_TRIMESTRE']['fim'] else '',
            'data_inicio_t2': str(cfg['2_TRIMESTRE']['inicio'] or '') if cfg['2_TRIMESTRE']['inicio'] else '',
            'data_fim_t2': str(cfg['2_TRIMESTRE']['fim'] or '') if cfg['2_TRIMESTRE']['fim'] else '',
            'data_inicio_t3': str(cfg['3_TRIMESTRE']['inicio'] or '') if cfg['3_TRIMESTRE']['inicio'] else '',
            'data_fim_t3': str(cfg['3_TRIMESTRE']['fim'] or '') if cfg['3_TRIMESTRE']['fim'] else '',
            'permitir_sempre_t1': getattr(escola, 'permitir_sempre_t1', False),
            'permitir_sempre_t2': getattr(escola, 'permitir_sempre_t2', False),
            'permitir_sempre_t3': getattr(escola, 'permitir_sempre_t3', False),
        }

        return Response({
            'success': True,
            'trimestreAtivo': trimestre_ativo,
            'modoCalendarizacao': getattr(escola, 'modo_calendarizacao', 'MANUAL'),
            'data': data_dict,
            'prazos': {
                '1_TRIMESTRE': {
                    'aberto': status_t1,
                    'motivo': motivo_t1,
                    'mensagem': msg_t1,
                    'nome': '1º Trimestre',
                    'inicio': data_dict['data_inicio_t1'],
                    'fim': data_dict['data_fim_t1'],
                    'sempre': cfg['1_TRIMESTRE']['sempre'],
                },
                '2_TRIMESTRE': {
                    'aberto': status_t2,
                    'motivo': motivo_t2,
                    'mensagem': msg_t2,
                    'nome': '2º Trimestre',
                    'inicio': data_dict['data_inicio_t2'],
                    'fim': data_dict['data_fim_t2'],
                    'sempre': cfg['2_TRIMESTRE']['sempre'],
                },
                '3_TRIMESTRE': {
                    'aberto': status_t3,
                    'motivo': motivo_t3,
                    'mensagem': msg_t3,
                    'nome': '3º Trimestre',
                    'inicio': data_dict['data_inicio_t3'],
                    'fim': data_dict['data_fim_t3'],
                    'sempre': cfg['3_TRIMESTRE']['sempre'],
                },
            }
        })

    def post(self, request):
        return self._salvar_prazos(request)

    def put(self, request):
        return self._salvar_prazos(request)

    def _salvar_prazos(self, request):
        escola = get_tenant_escola(request)
        if not escola:
            return Response({'success': False, 'message': 'Instituição não identificada.'}, status=status.HTTP_400_BAD_REQUEST)

        d = request.data
        modo = d.get('modo_calendarizacao') or d.get('modo') or 'MANUAL'
        if modo in ('MANUAL', 'AUTOMATICO', 'SEMPRE'):
            escola.modo_calendarizacao = modo

        if 'tipo_duracao_automatica' in d:
            escola.tipo_duracao_automatica = d.get('tipo_duracao_automatica') or 'SEMANAS'
        if 'valor_duracao_automatica' in d and d.get('valor_duracao_automatica') is not None:
            try:
                escola.valor_duracao_automatica = max(1, int(d.get('valor_duracao_automatica')))
            except (ValueError, TypeError):
                pass

        def parse_date(v):
            if not v:
                return None
            try:
                from datetime import datetime
                return datetime.strptime(str(v)[:10], '%Y-%m-%d').date()
            except Exception:
                return None

        if 'data_base_automatica' in d:
            escola.data_base_automatica = parse_date(d.get('data_base_automatica'))

        if 'permitir_sempre_t1' in d:
            escola.permitir_sempre_t1 = bool(d.get('permitir_sempre_t1'))
        if 'permitir_sempre_t2' in d:
            escola.permitir_sempre_t2 = bool(d.get('permitir_sempre_t2'))
        if 'permitir_sempre_t3' in d:
            escola.permitir_sempre_t3 = bool(d.get('permitir_sempre_t3'))

        # Se for modo MANUAL ou datas explicitamente fornecidas
        if modo == 'MANUAL' or 'data_inicio_t1' in d:
            escola.data_inicio_t1 = parse_date(d.get('data_inicio_t1'))
            escola.data_fim_t1 = parse_date(d.get('data_fim_t1'))
            escola.data_inicio_t2 = parse_date(d.get('data_inicio_t2'))
            escola.data_fim_t2 = parse_date(d.get('data_fim_t2'))
            escola.data_inicio_t3 = parse_date(d.get('data_inicio_t3'))
            escola.data_fim_t3 = parse_date(d.get('data_fim_t3'))
        elif modo == 'AUTOMATICO':
            # Se for automático, sincronizar datas calculadas na escola
            escola.save()
            cfg = obter_configuracao_prazos(escola)
            escola.data_inicio_t1 = cfg['1_TRIMESTRE']['inicio']
            escola.data_fim_t1 = cfg['1_TRIMESTRE']['fim']
            escola.data_inicio_t2 = cfg['2_TRIMESTRE']['inicio']
            escola.data_fim_t2 = cfg['2_TRIMESTRE']['fim']
            escola.data_inicio_t3 = cfg['3_TRIMESTRE']['inicio']
            escola.data_fim_t3 = cfg['3_TRIMESTRE']['fim']

        escola.save()

        cfg_final = obter_configuracao_prazos(escola)
        return Response({
            'success': True,
            'message': 'Calendário oficial de prazos de lançamento guardado com sucesso!',
            'data': {
                'modo_calendarizacao': escola.modo_calendarizacao,
                'data_inicio_t1': str(escola.data_inicio_t1 or ''),
                'data_fim_t1': str(escola.data_fim_t1 or ''),
                'data_inicio_t2': str(escola.data_inicio_t2 or ''),
                'data_fim_t2': str(escola.data_fim_t2 or ''),
                'data_inicio_t3': str(escola.data_inicio_t3 or ''),
                'data_fim_t3': str(escola.data_fim_t3 or ''),
                'permitir_sempre_t1': escola.permitir_sempre_t1,
                'permitir_sempre_t2': escola.permitir_sempre_t2,
                'permitir_sempre_t3': escola.permitir_sempre_t3,
            }
        }, status=status.HTTP_200_OK)

class AutorizacaoEdicaoView(APIView):
    permission_classes = [IsAuthenticated, IsEscolaAdmin]

    def get(self, request):
        escola = get_tenant_escola(request)
        if not escola:
            return Response({'success': True, 'data': []})
        perms = PermissaoEdicaoNotas.objects.filter(escola=escola, ativa=True).select_related('turma', 'professor', 'disciplina').order_by('-created_at')
        return Response({'success': True, 'data': PermissaoEdicaoNotasSerializer(perms, many=True).data})

    def post(self, request):
        escola = get_tenant_escola(request)
        if not escola:
            return Response({'success': False, 'message': 'Instituição não identificada.'}, status=status.HTTP_400_BAD_REQUEST)
        turma = get_object_or_404(Turma, id=request.data.get('turma_id'), escola=escola)

        prof_id = request.data.get('professor_id')
        prof = None
        if prof_id:
            prof = Professor.objects.filter(id=prof_id, escola=escola).first()

        disc_id = request.data.get('disciplina_id')
        disc = None
        if disc_id:
            disc = Disciplina.objects.filter(id=disc_id, escola=escola).first()

        periodo = request.data.get('periodo', '1_TRIMESTRE')
        horas = int(request.data.get('duracao_horas') or 48)
        expira_em = timezone.now() + timedelta(hours=horas)
        motivo = request.data.get('motivo', 'Autorização Pedagógica de Lançamento')

        perm, _ = PermissaoEdicaoNotas.objects.update_or_create(
            escola=escola,
            turma=turma,
            professor=prof,
            disciplina=disc,
            periodo=periodo,
            defaults={
                'autorizado_por': getattr(request.user, 'nome', 'Direcção / Secretaria'),
                'motivo': motivo,
                'duracao_horas': horas,
                'data_expiracao': expira_em,
                'ativa': True
            }
        )
        return Response({
            'success': True,
            'message': 'Autorização de desbloqueio concedida com sucesso!',
            'data': PermissaoEdicaoNotasSerializer(perm).data
        }, status=status.HTTP_201_CREATED)

    def delete(self, request, perm_id=None):
        escola = get_tenant_escola(request)
        if not escola:
            return Response({'success': False, 'message': 'Instituição não identificada.'}, status=status.HTTP_400_BAD_REQUEST)
        target_id = perm_id or request.data.get('id') or request.query_params.get('id')
        perm = get_object_or_404(PermissaoEdicaoNotas, id=target_id, escola=escola)
        perm.ativa = False
        perm.save()
        return Response({'success': True, 'message': 'Autorização de desbloqueio revogada com sucesso.'})
