from common.utils.avaliacoes_mocambique import obter_nome_completo_aluno
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
        from common.utils.tenant import get_tenant_escola
        escola = get_tenant_escola(self.request)
        if escola:
            return Professor.objects.filter(escola=escola).prefetch_related('alocacoes__disciplina', 'alocacoes__turma').order_by('nome')
        return Professor.objects.none()

    def perform_create(self, serializer):
        from common.utils.tenant import get_tenant_escola
        from rest_framework import serializers as drf_serializers
        escola = get_tenant_escola(self.request)

        if not escola:
            raise drf_serializers.ValidationError({
                'escola': 'Nenhuma escola seleccionada. Por favor, seleccione uma escola no topo antes de cadastrar o professor.'
            })

        serializer.save(escola=escola)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return Response({'success': True, 'data': ProfessorSerializer(qs, many=True).data})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response({'success': True, 'data': ProfessorSerializer(instance).data})

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
        return Response({'success': True, 'message': 'Professor excluído com sucesso.'})

class AlocarProfessorView(APIView):
    permission_classes = [IsAuthenticated, IsEscolaAdmin]

    def post(self, request):
        serializer = CriarAlocacaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from common.utils.tenant import get_tenant_escola
        escola = get_tenant_escola(request)
        if not escola:
            return Response({'success': False, 'message': 'Nenhuma instituição seleccionada.'}, status=status.HTTP_400_BAD_REQUEST)

        prof = get_object_or_404(Professor, id=serializer.validated_data['professor_id'], escola=escola)
        disc = get_object_or_404(Disciplina, id=serializer.validated_data['disciplina_id'], escola=escola)
        turma = get_object_or_404(Turma, id=serializer.validated_data['turma_id'], escola=escola)

        aloc = AlocacaoDocente.objects.filter(professor=prof, disciplina=disc, turma=turma).first()
        created = False
        if not aloc:
            try:
                aloc = AlocacaoDocente.objects.create(
                    escola=escola,
                    professor=prof,
                    disciplina=disc,
                    turma=turma
                )
                created = True
            except Exception:
                aloc = AlocacaoDocente.objects.filter(professor=prof, disciplina=disc, turma=turma).first()
                if not aloc:
                    raise

        carga_max_classe = serializer.validated_data.get('carga_maxima_classe')
        if carga_max_classe is not None and turma.grau_ano:
            c_dict = dict(prof.carga_maxima_por_classe or {})
            c_dict[turma.grau_ano.strip()] = int(carga_max_classe)
            prof.carga_maxima_por_classe = c_dict
            prof.save(update_fields=['carga_maxima_por_classe'])

        return Response({
            'success': True,
            'message': 'Alocação docente criada com sucesso.',
            'data': AlocacaoDocenteSerializer(aloc).data
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def delete(self, request, alocacao_id):
        aloc = get_object_or_404(AlocacaoDocente, id=alocacao_id)
        aloc.delete()
        return Response({'success': True, 'message': 'Alocação removida com sucesso.'})

class ProfessorStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from common.utils.tenant import get_tenant_escola
        escola = get_tenant_escola(request)

        qs = Professor.objects.filter(escola=escola) if escola else Professor.objects.none()
        aloc_qs = AlocacaoDocente.objects.filter(escola=escola) if escola else AlocacaoDocente.objects.none()
        alunos_qs = Aluno.objects.filter(escola=escola, status='ATIVO') if escola else Aluno.objects.none()

        total = qs.count()
        ativos = qs.filter(ativo=True).count()
        alocacoes = aloc_qs.count()
        total_alunos = alunos_qs.count()
        ratio = round(total_alunos / total, 1) if total > 0 else 0
        return Response({
            'success': True,
            'data': {
                'totalProfessores': total,
                'professoresAtivos': ativos,
                'totalAlocacoes': alocacoes,
                'proporcaoAlunoProfessor': ratio,
                'totalAulasMes': alocacoes * 16
            }
        })

class MinhasTurmasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        escola = getattr(request, 'tenant', None) or getattr(request.user, 'escola', None)
        prof_id = getattr(request.user, 'professor_id', None)

        qs = AlocacaoDocente.objects.all()
        if escola:
            qs = qs.filter(escola=escola)

        # Se for admin, lista todas as alocações da escola ou filtra por professor_id se fornecido
        if getattr(request.user, 'role', '') in ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP']:
            req_prof_id = request.query_params.get('professor_id')
            if req_prof_id and req_prof_id != 'TODOS':
                alocs = qs.filter(professor_id=req_prof_id).select_related('professor', 'disciplina', 'turma')
            else:
                alocs = qs.select_related('professor', 'disciplina', 'turma')
        elif prof_id:
            # Professor estritamente isolado às suas alocações
            alocs = qs.filter(professor_id=prof_id).select_related('professor', 'disciplina', 'turma')
        else:
            alocs = AlocacaoDocente.objects.none()

        return Response({
            'success': True,
            'data': AlocacaoDocenteSerializer(alocs, many=True).data
        })

class MeuPerfilView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        prof_id = getattr(request.user, 'professor_id', None)
        if not prof_id:
            return Response({'success': False, 'message': 'Utilizador não é um professor cadastrado.'}, status=status.HTTP_404_NOT_FOUND)
        prof = Professor.objects.filter(id=prof_id).first()
        if not prof:
            return Response({'success': False, 'message': 'Professor não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'data': ProfessorSerializer(prof).data})

def _safe_ascii_filename(nome: str) -> str:
    import unicodedata, re
    s = unicodedata.normalize('NFKD', str(nome or 'documento')).encode('ascii', 'ignore').decode('ascii')
    s = re.sub(r'[^A-Za-z0-9._-]+', '_', s).strip('_')
    return s or 'documento'

def compilar_dados_caderneta(request, alocacao_id, ignorar_restricao=False):
    escola = getattr(request, 'tenant', None) or getattr(getattr(request, 'user', None), 'escola', None)
    aloc = AlocacaoDocente.objects.select_related('turma', 'disciplina', 'professor', 'escola').filter(id=alocacao_id).first()
    if not aloc:
        aloc = get_object_or_404(AlocacaoDocente, id=alocacao_id)
    escola = aloc.escola or escola

    turma = aloc.turma
    prof = aloc.professor
    disc = aloc.disciplina

    alunos = Aluno.objects.filter(turma=turma, status='ATIVO').order_by('nome', 'apelido')
    notas = Nota.objects.filter(turma=turma, disciplina=disc)

    notas_dict = {}
    for n in notas:
        key = f"{n.aluno_id}_{n.periodo}"
        notas_dict[key] = {
            'id': str(n.id),
            't1': n.teste1,
            't2': n.teste2,
            't3': n.teste3,
            'map': n.trabalho or n.teste4,
            'mas': n.teste4,
            'at': n.avaliacao_trimestral,
            'mt': n.media_final,
            'anotacao': n.anotacao,
            'comportamento': n.comportamento or '',
            'resultado': n.resultado,
            'faltas': n.faltas
        }

    total_h = alunos.filter(genero='M').count()
    total_m = alunos.filter(genero='F').count()

    alunos_caderneta = []
    for idx, a in enumerate(alunos, start=1):
        def extrair_trimestre(per):
            nd = notas_dict.get(f"{a.id}_{per}")
            if not nd:
                return {
                    't1': None, 't2': None, 't3': None, 'map': None, 'mas': None,
                    'at': None, 'mt': None, 'comportamento': '', 'anotacao': '', 'faltas': 0
                }
            def nota_valida(val):
                if val is None or val == '' or val == '-':
                    return False
                try:
                    n = float(val)
                    return 0.0 <= n <= 20.0
                except (ValueError, TypeError):
                    return False

            # Regra estrita: Na caderneta só deve mostrar a "MT" quando o aluno tiver no mínimo 2 ACS sendo (1ª, 2ª) e AT
            tem_requisitos_mt = nota_valida(nd.get('t1')) and nota_valida(nd.get('t2')) and nota_valida(nd.get('at'))
            mt_val = nd.get('mt') if tem_requisitos_mt else None

            tem_nota = any(
                nd.get(k) is not None and nd.get(k) != ''
                for k in ['t1', 't2', 't3', 'map', 'mas', 'at']
            ) or (mt_val is not None)
            comp = (nd.get('comportamento') or '') if (tem_nota and tem_requisitos_mt) else ''
            return {
                't1': nd.get('t1'),
                't2': nd.get('t2'),
                't3': nd.get('t3'),
                'map': nd.get('map'),
                'mas': nd.get('mas'),
                'at': nd.get('at'),
                'mt': mt_val,
                'comportamento': comp,
                'anotacao': nd.get('anotacao') or '',
                'faltas': nd.get('faltas') or 0
            }

        t1_data = extrair_trimestre('1_TRIMESTRE')
        t2_data = extrair_trimestre('2_TRIMESTRE')
        t3_data = extrair_trimestre('3_TRIMESTRE')

        def tem_mt_valido(trim_data):
            if not trim_data:
                return False
            val = trim_data.get('mt')
            if val is None or val == '' or val == '-':
                return False
            try:
                num = float(val)
                if num > 0:
                    return True
                tem_aval = any(
                    trim_data.get(k) is not None and trim_data.get(k) != '' and trim_data.get(k) != '-' and float(trim_data.get(k)) > 0
                    for k in ['t1', 't2', 't3', 'map', 'mas', 'at']
                )
                return tem_aval or bool(trim_data.get('anotacao'))
            except (ValueError, TypeError):
                return False

        # MFD oficial: só deve ser calculado e exibido quando as médias dos 3 trimestres estiverem disponíveis
        if tem_mt_valido(t1_data) and tem_mt_valido(t2_data) and tem_mt_valido(t3_data):
            mfd = round((float(t1_data['mt']) + float(t2_data['mt']) + float(t3_data['mt'])) / 3, 1)
        else:
            mfd = None

        alunos_caderneta.append({
            'numero': idx,
            'alunoId': str(a.id),
            'matricula': a.matricula or '',
            'nome': obter_nome_completo_aluno(a),
            'nomeCompleto': obter_nome_completo_aluno(a),
            'apelido': a.apelido or '',
            'genero': a.genero or 'M',
            't1': t1_data,
            't2': t2_data,
            't3': t3_data,
            'mfd': mfd
        })

    chaves = [
        ('t1_t1', 't1', 't1'), ('t1_t2', 't1', 't2'), ('t1_t3', 't1', 't3'),
        ('t1_map', 't1', 'map'), ('t1_mas', 't1', 'mas'), ('t1_at', 't1', 'at'), ('t1_mt', 't1', 'mt'),
        ('t2_t1', 't2', 't1'), ('t2_t2', 't2', 't2'), ('t2_t3', 't2', 't3'),
        ('t2_map', 't2', 'map'), ('t2_mas', 't2', 'mas'), ('t2_at', 't2', 'at'), ('t2_mt', 't2', 'mt'),
        ('t3_t1', 't3', 't1'), ('t3_t2', 't3', 't2'), ('t3_t3', 't3', 't3'),
        ('t3_map', 't3', 'map'), ('t3_mas', 't3', 'mas'), ('t3_at', 't3', 'at'), ('t3_mt', 't3', 'mt'),
        ('mfd', None, 'mfd')
    ]

    estatisticas = {}
    for chave, sub, campo in chaves:
        m_notas = []
        f_notas = []
        for al in alunos_caderneta:
            val = al[campo] if sub is None else al[sub][campo]
            if val is not None and val != '' and not (isinstance(val, (int, float)) and val <= 0):
                try:
                    n_val = float(val)
                    if al['genero'] == 'F':
                        f_notas.append(n_val)
                    else:
                        m_notas.append(n_val)
                except (ValueError, TypeError):
                    pass

        av_h = len(m_notas)
        av_f = len(f_notas)
        av_tot = av_h + av_f

        pos_h = sum(1 for n in m_notas if n >= 9.5)
        pos_f = sum(1 for n in f_notas if n >= 9.5)
        pos_tot = pos_h + pos_f

        neg_h = av_h - pos_h
        neg_f = av_f - pos_f
        neg_tot = av_tot - pos_tot

        pct_pos_h = round((pos_h / av_h) * 100) if av_h > 0 else 0
        pct_pos_f = round((pos_f / av_f) * 100) if av_f > 0 else 0
        pct_pos_tot = round((pos_tot / av_tot) * 100) if av_tot > 0 else 0

        pct_neg_h = round((neg_h / av_h) * 100) if av_h > 0 else 0
        pct_neg_f = round((neg_f / av_f) * 100) if av_f > 0 else 0
        pct_neg_tot = round((neg_tot / av_tot) * 100) if av_tot > 0 else 0

        todas_notas = m_notas + f_notas
        media_coluna = round(sum(todas_notas) / len(todas_notas), 1) if todas_notas else 0

        # Faixas oficiais de aproveitamento
        f0_94_h = sum(1 for n in m_notas if n < 9.5)
        f0_94_f = sum(1 for n in f_notas if n < 9.5)
        f0_94_tot = f0_94_h + f0_94_f

        f95_134_h = sum(1 for n in m_notas if 9.5 <= n < 13.5)
        f95_134_f = sum(1 for n in f_notas if 9.5 <= n < 13.5)
        f95_134_tot = f95_134_h + f95_134_f

        f135_164_h = sum(1 for n in m_notas if 13.5 <= n < 16.5)
        f135_164_f = sum(1 for n in f_notas if 13.5 <= n < 16.5)
        f135_164_tot = f135_164_h + f135_164_f

        f165_184_h = sum(1 for n in m_notas if 16.5 <= n < 18.5)
        f165_184_f = sum(1 for n in f_notas if 16.5 <= n < 18.5)
        f165_184_tot = f165_184_h + f165_184_f

        f185_20_h = sum(1 for n in m_notas if n >= 18.5)
        f185_20_f = sum(1 for n in f_notas if n >= 18.5)
        f185_20_tot = f185_20_h + f185_20_f

        estatisticas[chave] = {
            'avaliados': {'h': av_h, 'm': av_f, 'total': av_tot},
            'positivas': {'h': pos_h, 'm': pos_f, 'total': pos_tot, 'pctH': pct_pos_h, 'pctM': pct_pos_f, 'pct': pct_pos_tot},
            'negativas': {'h': neg_h, 'm': neg_f, 'total': neg_tot, 'pctH': pct_neg_h, 'pctM': pct_neg_f, 'pct': pct_neg_tot},
            'faixas': {
                'f0_94': {'h': f0_94_h, 'm': f0_94_f, 'total': f0_94_tot},
                'f95_134': {'h': f95_134_h, 'm': f95_134_f, 'total': f95_134_tot},
                'f135_164': {'h': f135_164_h, 'm': f135_164_f, 'total': f135_164_tot},
                'f165_184': {'h': f165_184_h, 'm': f165_184_f, 'total': f165_184_tot},
                'f185_20': {'h': f185_20_h, 'm': f185_20_f, 'total': f185_20_tot},
            },
            'media': media_coluna
        }

    caderneta_data = {
        'escola': {
            'id': str(escola.id) if escola else '',
            'nome': escola.nome if escola else 'Escola Secundária',
            'provincia': escola.provincia if escola else 'Maputo',
            'distrito': escola.distrito if escola else 'Cidade de Maputo',
            'usar_emblema_nacional': getattr(escola, 'usar_emblema_nacional', True) if escola else True,
            'logo_url': getattr(escola, 'logo_url', None) if escola else None,
            'logo_base64': getattr(escola, 'logo_base64', None) if escola else None,
            'modo_uso_logo': getattr(escola, 'modo_uso_logo', 'DOCUMENTOS') if escola else 'DOCUMENTOS',
            'marca_dagua_url': getattr(escola, 'marca_dagua_url', None) if escola else None,
            'marca_dagua_base64': getattr(escola, 'marca_dagua_base64', None) if escola else None,
            'marca_dagua_modo': getattr(escola, 'marca_dagua_modo', 'EMBLEMA_NACIONAL') if escola else 'EMBLEMA_NACIONAL',
        },
        'turma': {
            'id': str(turma.id),
            'nome': turma.nome,
            'grau_ano': turma.grau_ano,
            'area': turma.area or 'Ensino Geral',
            'turno': turma.turno or 'MANHA',
            'sala': turma.sala or '',
            'ano_letivo': turma.ano_letivo or '2026',
        },
        'disciplina': {
            'id': str(disc.id),
            'nome': disc.nome,
            'codigo': disc.codigo or disc.abreviatura or '',
        },
        'professor': {
            'id': str(prof.id) if prof else '',
            'nome': prof.nome if prof else (aloc.professor_nome or 'Professor'),
            'apelido': prof.apelido if prof else '',
            'telefone': prof.telefone if prof else '',
            'especialidade': prof.especialidade or prof.carreira or 'Ensino Geral',
        },
        'directorTurma': {
            'nome': turma.director_turma.nome if turma.director_turma else '-'
        },
        'efectivo': {
            'h': total_h,
            'm': total_m,
            'total': total_h + total_m
        },
        'alocacao': AlocacaoDocenteSerializer(aloc).data,
        'alunos': alunos_caderneta,
        'estatisticasColunas': estatisticas
    }
    return aloc, caderneta_data, alunos_caderneta


class CadernetaCompletaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, alocacao_id):
        aloc, caderneta_data, alunos_caderneta = compilar_dados_caderneta(request, alocacao_id)
        return Response({
            'success': True,
            'data': caderneta_data,
            'alocacao': AlocacaoDocenteSerializer(aloc).data,
            'alunos': alunos_caderneta
        })


from rest_framework.permissions import AllowAny

class CadernetaPDFView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, alocacao_id):
        from apps.documentos.services.pdf_service import gerar_caderneta_pdf
        aloc, caderneta_data, _ = compilar_dados_caderneta(request, alocacao_id)
        orientacao = request.query_params.get('orientacao', 'landscape')
        pdf_bytes = gerar_caderneta_pdf(caderneta_data, orientacao=orientacao)
        fname = _safe_ascii_filename(f"Caderneta_{aloc.turma.nome}_{aloc.disciplina.nome}.pdf")
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response


class CadernetaXLSXView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, alocacao_id):
        from apps.documentos.services.excel_service import gerar_caderneta_xlsx
        aloc, caderneta_data, _ = compilar_dados_caderneta(request, alocacao_id)
        orientacao = request.query_params.get('orientacao', 'landscape')
        xlsx_bytes = gerar_caderneta_xlsx(caderneta_data, orientacao=orientacao)
        fname = _safe_ascii_filename(f"Caderneta_{aloc.turma.nome}_{aloc.disciplina.nome}.xlsx")
        response = HttpResponse(xlsx_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response


class CadernetaDOCXView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, alocacao_id):
        from apps.documentos.services.docx_service import gerar_caderneta_docx
        aloc, caderneta_data, _ = compilar_dados_caderneta(request, alocacao_id)
        orientacao = request.query_params.get('orientacao', 'landscape')
        docx_bytes = gerar_caderneta_docx(caderneta_data, orientacao=orientacao)
        fname = _safe_ascii_filename(f"Caderneta_{aloc.turma.nome}_{aloc.disciplina.nome}.docx")
        response = HttpResponse(docx_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response

