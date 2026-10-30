from rest_framework import permissions
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count
from django.utils import timezone

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
        from common.utils.tenant import get_tenant_escola
        escola = get_tenant_escola(request)
        if escola:
            qs = Aluno.objects.filter(escola=escola)
        elif getattr(request.user, 'role', '') == 'SUPERADMIN':
            qs = Aluno.objects.all()
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
        target_aluno_id = getattr(request.user, 'aluno_id', None)
        if not target_aluno_id:
            # Permitir que utilizadores da escola / professores / superadmin consultem notas de aluno
            target_aluno_id = request.query_params.get('aluno_id') or request.query_params.get('alunoId')
            if not target_aluno_id:
                return Response({'success': False, 'message': 'Não autorizado ou nenhum aluno especificado.'}, status=status.HTTP_403_FORBIDDEN)

        aluno = Aluno.objects.select_related('escola', 'turma').filter(id=target_aluno_id).first()
        if not aluno:
            return Response({'success': False, 'message': 'Aluno não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        escola = aluno.escola
        if escola and hasattr(escola, 'resolver_publicacao_notas'):
            pub_trimestre, permitir_vis, modo_pub, info_periodo = escola.resolver_publicacao_notas()
        else:
            permitir_vis = getattr(escola, 'permitir_visualizacao_notas', True) if escola else True
            pub_trimestre = getattr(escola, 'publicacao_notas_trimestre', 'TODOS') if escola else 'TODOS'
            modo_pub = 'MANUAL'
            info_periodo = None

        # Período selecionado na consulta pelo utilizador:
        periodo_param = request.query_params.get('periodo')
        if not periodo_param or str(periodo_param).upper() in ('TODOS', 'ALL', 'ANUAL', 'GERAL'):
            periodo_solicitado = 'TODOS'
        elif str(periodo_param).upper() in ('1', 'T1', '1_TRIMESTRE', 'I'):
            periodo_solicitado = '1_TRIMESTRE'
        elif str(periodo_param).upper() in ('2', 'T2', '2_TRIMESTRE', 'II', '1_E_2', '1_E_2_TRIMESTRE'):
            periodo_solicitado = '2_TRIMESTRE'
        elif str(periodo_param).upper() in ('3', 'T3', '3_TRIMESTRE', 'III'):
            periodo_solicitado = '3_TRIMESTRE'
        else:
            periodo_solicitado = 'TODOS'

        if not permitir_vis or pub_trimestre == 'NENHUM':
            msg_suspensao = (
                'A visualização de notas está fora do período programado pela Direcção da Escola.'
                if modo_pub == 'DATAS'
                else 'A visualização de notas está temporariamente suspensa pela Direcção da Escola.'
            )
            return Response({
                'success': True,
                'data': {
                    'permitirVisualizacaoNotas': False,
                    'publicacaoNotasTrimestre': 'NENHUM',
                    'modoPublicacaoNotas': modo_pub,
                    'infoPeriodo': info_periodo,
                    'periodoVisualizacao': periodo_solicitado,
                    'mensagem': msg_suspensao,
                    'disciplinas': [],
                    'mediaGeral': None,
                    'situacao': 'Suspenso'
                }
            })

        # Trimestres publicados oficialmente pela escola:
        # 1. I Trimestre -> ['1_TRIMESTRE']
        # 2. I e II Trimestre -> ['1_TRIMESTRE', '2_TRIMESTRE']
        # 4. Todos os Trimestres -> ['1_TRIMESTRE', '2_TRIMESTRE', '3_TRIMESTRE']
        if pub_trimestre == '1_TRIMESTRE':
            trimestres_publicados = ['1_TRIMESTRE']
        elif pub_trimestre == '2_TRIMESTRE':
            trimestres_publicados = ['1_TRIMESTRE', '2_TRIMESTRE']
        elif pub_trimestre == '3_TRIMESTRE':
            trimestres_publicados = ['1_TRIMESTRE', '2_TRIMESTRE', '3_TRIMESTRE']
        elif pub_trimestre == 'TODOS':
            trimestres_publicados = ['1_TRIMESTRE', '2_TRIMESTRE', '3_TRIMESTRE']
        else:
            trimestres_publicados = ['1_TRIMESTRE', '2_TRIMESTRE', '3_TRIMESTRE']

        # Disciplinas aplicáveis
        from apps.disciplinas.models import Disciplina
        from apps.pautas.services import obter_disciplinas_pauta_turma

        if aluno.turma:
            disciplinas = list(obter_disciplinas_pauta_turma(aluno.turma))
        else:
            disciplinas = []

        # Se a turma não tiver disciplinas pré-definidas, buscar disciplinas com notas cadastradas
        notas_qs = list(Nota.objects.filter(aluno=aluno).select_related('disciplina'))
        if not disciplinas:
            disciplinas_vistas = {}
            for n in notas_qs:
                if n.disciplina and n.disciplina_id not in disciplinas_vistas:
                    disciplinas_vistas[n.disciplina_id] = n.disciplina
            disciplinas = list(disciplinas_vistas.values())

        notas_map = {(n.disciplina_id, n.periodo): n for n in notas_qs}

        disciplinas_data = []
        t1_valores = []
        t2_valores = []
        t3_valores = []
        mfd_valores = []

        def extrair_nota(n_obj):
            if not n_obj:
                return None
            tem_av = any(
                getattr(n_obj, c, None) is not None and getattr(n_obj, c, 0) > 0
                for c in ['teste1', 'teste2', 'teste3', 'teste4', 'trabalho', 'avaliacao_trimestral']
            )
            if tem_av or (n_obj.media_final is not None and n_obj.media_final > 0) or n_obj.anotacao:
                return n_obj.media_final
            return None

        for d in disciplinas:
            n_t1 = notas_map.get((d.id, '1_TRIMESTRE'))
            n_t2 = notas_map.get((d.id, '2_TRIMESTRE'))
            n_t3 = notas_map.get((d.id, '3_TRIMESTRE'))

            pub_t1 = '1_TRIMESTRE' in trimestres_publicados
            pub_t2 = '2_TRIMESTRE' in trimestres_publicados
            pub_t3 = '3_TRIMESTRE' in trimestres_publicados

            v_t1 = extrair_nota(n_t1) if pub_t1 else None
            v_t2 = extrair_nota(n_t2) if pub_t2 else None
            v_t3 = extrair_nota(n_t3) if pub_t3 else None

            if v_t1 is not None: t1_valores.append(v_t1)
            if v_t2 is not None: t2_valores.append(v_t2)
            if v_t3 is not None: t3_valores.append(v_t3)

            # MFD calculada
            if v_t1 is not None and v_t2 is not None and v_t3 is not None:
                mfd = round((v_t1 + v_t2 + v_t3) / 3, 1)
                mfd_final = int(round(mfd))
                mfd_valores.append(mfd)
            else:
                mfd_final = None

            # Determinar a nota em exibição de acordo com o período solicitado
            if periodo_solicitado == '1_TRIMESTRE':
                nota_exibicao = v_t1
                faltas_exibicao = n_t1.faltas if n_t1 else 0
                res_exibicao = n_t1.resultado if (n_t1 and v_t1 is not None) else ('Aguardando' if pub_t1 else 'Não Publicado')
            elif periodo_solicitado == '2_TRIMESTRE':
                nota_exibicao = v_t2
                faltas_exibicao = n_t2.faltas if n_t2 else 0
                res_exibicao = n_t2.resultado if (n_t2 and v_t2 is not None) else ('Aguardando' if pub_t2 else 'Não Publicado')
            elif periodo_solicitado == '3_TRIMESTRE':
                nota_exibicao = v_t3
                faltas_exibicao = n_t3.faltas if n_t3 else 0
                res_exibicao = n_t3.resultado if (n_t3 and v_t3 is not None) else ('Aguardando' if pub_t3 else 'Não Publicado')
            else:  # TODOS
                nota_exibicao = mfd_final
                faltas_exibicao = (n_t1.faltas if (n_t1 and pub_t1) else 0) + (n_t2.faltas if (n_t2 and pub_t2) else 0) + (n_t3.faltas if (n_t3 and pub_t3) else 0)
                if mfd_final is not None:
                    res_exibicao = 'Aprovado' if mfd_final >= 9.5 else 'Reprovado'
                else:
                    res_exibicao = 'Em Curso'

            def criar_detalhe(n_obj, pub):
                if not pub:
                    return {'publicado': False, 'mensagem': 'Não publicado'}
                if not n_obj:
                    return {
                        'publicado': True, 'teste1': None, 'teste2': None, 'teste3': None, 'teste4': None,
                        'trabalho': None, 'avaliacao_trimestral': None, 'media_final': None, 'faltas': 0,
                        'comportamento': '', 'anotacao': None, 'resultado': 'Sem Nota'
                    }
                return {
                    'publicado': True,
                    'teste1': n_obj.teste1,
                    'teste2': n_obj.teste2,
                    'teste3': n_obj.teste3,
                    'teste4': n_obj.teste4,
                    'trabalho': n_obj.trabalho,
                    'avaliacao_trimestral': n_obj.avaliacao_trimestral,
                    'media_final': n_obj.media_final,
                    'faltas': n_obj.faltas,
                    'comportamento': n_obj.comportamento or '',
                    'anotacao': n_obj.anotacao or '',
                    'resultado': n_obj.resultado or ('Aprovado' if (n_obj.media_final or 0) >= 9.5 else 'Reprovado')
                }

            disciplinas_data.append({
                'id': str(d.id),
                'nome': d.nome,
                'codigo': d.codigo or '',
                't1': v_t1,
                't2': v_t2,
                't3': v_t3,
                'mfd': mfd_final,
                'mediaFinal': nota_exibicao,
                'faltas': faltas_exibicao,
                'resultado': res_exibicao,
                'publicadoT1': pub_t1,
                'publicadoT2': pub_t2,
                'publicadoT3': pub_t3,
                'detalhes': {
                    '1_TRIMESTRE': criar_detalhe(n_t1, pub_t1),
                    '2_TRIMESTRE': criar_detalhe(n_t2, pub_t2),
                    '3_TRIMESTRE': criar_detalhe(n_t3, pub_t3),
                }
            })

        # Média Geral e Situação Conforme Período Selecionado
        if periodo_solicitado == '1_TRIMESTRE':
            med_geral = round(sum(t1_valores) / len(t1_valores), 1) if t1_valores else None
            sit_geral = ('APROVADO' if med_geral >= 9.5 else 'REPROVADO') if med_geral is not None else 'Pendente'
        elif periodo_solicitado == '2_TRIMESTRE':
            med_geral = round(sum(t2_valores) / len(t2_valores), 1) if t2_valores else None
            sit_geral = ('APROVADO' if med_geral >= 9.5 else 'REPROVADO') if med_geral is not None else 'Pendente'
        elif periodo_solicitado == '3_TRIMESTRE':
            med_geral = round(sum(t3_valores) / len(t3_valores), 1) if t3_valores else None
            sit_geral = ('APROVADO' if med_geral >= 9.5 else 'REPROVADO') if med_geral is not None else 'Pendente'
        else:  # TODOS
            if mfd_valores:
                med_geral = round(sum(mfd_valores) / len(mfd_valores), 1)
                sit_geral = 'APROVADO' if med_geral >= 9.5 else 'REPROVADO'
            elif t1_valores or t2_valores or t3_valores:
                todos_pts = t1_valores + t2_valores + t3_valores
                med_geral = round(sum(todos_pts) / len(todos_pts), 1)
                sit_geral = 'EM_CURSO'
            else:
                med_geral = None
                sit_geral = 'Pendente'

        med_t1_geral = round(sum(t1_valores) / len(t1_valores), 1) if t1_valores else None
        med_t2_geral = round(sum(t2_valores) / len(t2_valores), 1) if t2_valores else None
        med_t3_geral = round(sum(t3_valores) / len(t3_valores), 1) if t3_valores else None
        med_anual_geral = round(sum(mfd_valores) / len(mfd_valores), 1) if mfd_valores else None

        resumo_trimestres = {
            '1_TRIMESTRE': {'media': med_t1_geral, 'publicado': '1_TRIMESTRE' in trimestres_publicados, 'nome': 'I Trimestre'},
            '2_TRIMESTRE': {'media': med_t2_geral, 'publicado': '2_TRIMESTRE' in trimestres_publicados, 'nome': 'II Trimestre'},
            '3_TRIMESTRE': {'media': med_t3_geral, 'publicado': '3_TRIMESTRE' in trimestres_publicados, 'nome': 'III Trimestre'},
            'TODOS': {'media': med_anual_geral or med_geral, 'publicado': True, 'nome': 'Todos os Trimestres'}
        }

        retorno_payload = {
            'permitirVisualizacaoNotas': True,
            'publicacaoNotasTrimestre': pub_trimestre,
            'modoPublicacaoNotas': modo_pub,
            'infoPeriodo': info_periodo,
            'trimestresPublicados': trimestres_publicados,
            'periodoVisualizacao': periodo_solicitado,
            'mediaGeral': med_geral,
            'situacao': sit_geral,
            'disciplinas': disciplinas_data,
            'resumoTrimestres': resumo_trimestres,
            'aluno': {
                'id': str(aluno.id),
                'nome': aluno.nome,
                'apelido': aluno.apelido or '',
                'matricula': aluno.matricula,
                'turma': aluno.turma.nome if aluno.turma else '-',
                'classe': aluno.classe or (aluno.turma.grau_ano if aluno.turma else '-')
            }
        }

        return Response({
            'success': True,
            'data': retorno_payload
        })

class AlunoMePagamentosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.aluno_id:
            return Response({'success': False, 'message': 'Não autorizado.'}, status=status.HTTP_403_FORBIDDEN)
        pagamentos = Pagamento.objects.filter(aluno_id=request.user.aluno_id)
        ano = request.query_params.get('ano')
        if ano:
            filtro_ano = Q(mes_referencia__startswith=str(ano))
            if str(ano).isdigit():
                filtro_ano |= Q(data_vencimento__year=int(ano))
            pagamentos = pagamentos.filter(filtro_ano)
        pagamentos = pagamentos.order_by('-data_vencimento')
        data = [{
            'id': str(p.id),
            'descricao': p.descricao,
            'mes_referencia': p.mes_referencia,
            'valor': str(p.valor),
            'valor_pago': str(p.valor_pago),
            'status': p.status,
            'data_vencimento': p.data_vencimento,
            'data_pagamento': p.data_pagamento,
            'metodo_pagamento': p.metodo_pagamento,
            'recibo_numero': p.recibo_numero
        } for p in pagamentos]
        return Response({'success': True, 'data': data})

    def post(self, request):
        aluno_id = getattr(request.user, 'aluno_id', None)
        if not aluno_id:
            return Response({'success': False, 'message': 'Acesso exclusivo para alunos autenticados.'}, status=status.HTTP_403_FORBIDDEN)

        pagamento_id = request.data.get('pagamento_id') or request.data.get('id')
        if not pagamento_id:
            return Response({'success': False, 'message': 'O ID do pagamento é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)

        pagamento = Pagamento.objects.filter(id=pagamento_id, aluno_id=aluno_id).first()
        if not pagamento:
            return Response({'success': False, 'message': 'Mensalidade não encontrada para este aluno.'}, status=status.HTTP_404_NOT_FOUND)

        metodo_raw = request.data.get('metodo_pagamento', 'MPESA')
        telefone = str(request.data.get('telefone', '')).strip()
        referencia = str(request.data.get('referencia', '')).strip()
        valor_pago = request.data.get('valor_pago') or pagamento.valor

        metodo_upper = str(metodo_raw).upper().replace(' ', '').replace('-', '')
        if 'MPESA' in metodo_upper:
            metodo_oficial = 'MPESA'
            nome_metodo = 'M-Pesa (Vodacom)'
        elif 'EMOLA' in metodo_upper:
            metodo_oficial = 'EMOLA'
            nome_metodo = 'e-Mola (Movitel)'
        else:
            metodo_oficial = 'MPESA'
            nome_metodo = 'Carteira Móvel'

        pagamento.valor_pago = valor_pago
        pagamento.status = 'PAGO'
        pagamento.data_pagamento = timezone.now().date()
        pagamento.metodo_pagamento = metodo_oficial
        if not pagamento.recibo_numero:
            ano = timezone.now().year
            num_seq = Pagamento.objects.filter(escola=pagamento.escola, status='PAGO').count() + 1
            pagamento.recibo_numero = f"REC-{ano}-{num_seq:05d}"
        pagamento.save()

        msg = f"Saldo liquidado com sucesso via {nome_metodo}! Recibo Oficial: {pagamento.recibo_numero}"
        return Response({
            'success': True,
            'message': msg,
            'recibo_numero': pagamento.recibo_numero,
            'metodo_pagamento': metodo_oficial,
            'metodo_nome': nome_metodo,
            'referencia': referencia,
            'telefone': telefone
        })


from .models import PresencaAluno, TransferenciaAnulacao
from .serializers import PresencaAlunoSerializer, TransferenciaAnulacaoSerializer
from apps.accounts.audit import registrar_auditoria

class PresencaAlunoViewSet(viewsets.ModelViewSet):
    queryset = PresencaAluno.objects.all()
    serializer_class = PresencaAlunoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, 'role', '')
        escola = get_tenant_escola(self.request)
        qs = PresencaAluno.objects.all()
        if escola:
            qs = qs.filter(escola=escola)
        elif role != 'SUPERADMIN' and user.escola:
            qs = qs.filter(escola=user.escola)
        elif role != 'SUPERADMIN':
            return PresencaAluno.objects.none()

        if role == 'ALUNO':
            qs = qs.filter(aluno__id=user.aluno_id)
        elif role == 'PROFESSOR' and getattr(user, 'professor_id', None):
            turma_ids = user.professor.alocacoes.values_list('turma_id', flat=True) if hasattr(user, 'professor') else []
            if turma_ids:
                qs = qs.filter(turma_id__in=turma_ids)

        turma_id = self.request.query_params.get('turma_id')
        if turma_id:
            qs = qs.filter(turma_id=turma_id)
        aluno_id = self.request.query_params.get('aluno_id')
        if aluno_id:
            qs = qs.filter(aluno_id=aluno_id)
        data = self.request.query_params.get('data')
        if data:
            qs = qs.filter(data=data)
        return qs.order_by('-data', 'aluno__nome')

    def perform_create(self, serializer):
        escola = get_tenant_escola(self.request) or getattr(self.request.user, 'escola', None)
        prof = getattr(self.request.user, 'professor', None) if hasattr(self.request.user, 'professor') else None
        serializer.save(escola=escola, professor=prof, registado_por=self.request.user)

class TransferenciaAnulacaoViewSet(viewsets.ModelViewSet):
    queryset = TransferenciaAnulacao.objects.all()
    serializer_class = TransferenciaAnulacaoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, 'role', '')
        escola = get_tenant_escola(self.request)
        qs = TransferenciaAnulacao.objects.all()
        if escola:
            qs = qs.filter(escola=escola)
        elif role != 'SUPERADMIN' and user.escola:
            qs = qs.filter(escola=user.escola)
        elif role != 'SUPERADMIN':
            return TransferenciaAnulacao.objects.none()

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        escola = get_tenant_escola(self.request) or getattr(self.request.user, 'escola', None)
        item = serializer.save(escola=escola, solicitado_por=self.request.user)
        registrar_auditoria(self.request.user, escola, 'TRANSFERENCIA', 'CRIACAO', item.id, f'Solicitação de {item.tipo} para aluno {item.aluno.nome_completo}')

    @action(detail=True, methods=['post'], url_path='aprovar')
    def aprovar(self, request, pk=None):
        role = getattr(request.user, 'role', '')
        if role not in ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA'] and not getattr(request.user, 'is_superuser', False):
            return Response({'success': False, 'message': 'Competência exclusiva do Director da Escola.'}, status=403)
        obj = self.get_object()
        obj.status = 'APROVADO'
        obj.aprovado_por = request.user
        obj.data_aprovacao = timezone.now()
        obj.save()

        if obj.tipo == 'TRANSFERENCIA_SAIDA':
            obj.aluno.status = 'TRANSFERIDO'
            obj.aluno.save(update_fields=['status'])
        elif obj.tipo == 'ANULACAO_MATRICULA':
            obj.aluno.status = 'INATIVO'
            obj.aluno.save(update_fields=['status'])

        registrar_auditoria(request.user, obj.escola, 'TRANSFERENCIA', 'APROVACAO', obj.id, f'Aprovação de {obj.tipo} pelo Director da Escola')
        return Response({'success': True, 'message': f'{obj.tipo} aprovada com sucesso!', 'data': self.get_serializer(obj).data})
