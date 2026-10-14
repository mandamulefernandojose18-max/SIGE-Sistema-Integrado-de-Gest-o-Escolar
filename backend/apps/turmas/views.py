from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from .models import Turma
from .serializers import TurmaSerializer
from common.permissions.rbac import IsEscolaAdmin

class TurmaViewSet(viewsets.ModelViewSet):
    serializer_class = TurmaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from common.utils.tenant import get_tenant_escola
        escola = get_tenant_escola(self.request)
        if escola:
            qs = Turma.objects.filter(escola=escola)
        else:
            qs = Turma.objects.none()

        ano = self.request.query_params.get('ano_letivo')
        if ano:
            qs = qs.filter(ano_letivo=ano)
        return qs.order_by('nome')

    def perform_create(self, serializer):
        from django.utils import timezone
        from common.utils.tenant import get_tenant_escola
        from rest_framework import serializers as drf_serializers
        escola = get_tenant_escola(self.request)

        if not escola:
            raise drf_serializers.ValidationError({
                'escola': 'Nenhuma escola seleccionada. Por favor, seleccione uma escola no topo antes de criar a turma.'
            })

        extra_kwargs = {'escola': escola}
        user_role = getattr(self.request.user, 'role', '')
        pode_homologar = user_role in ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA']
        homologar_imediato = bool(self.request.data.get('homologar_directores')) and pode_homologar

        nome_dap = getattr(escola, 'dap_nome', None) or (self.request.user.nome if user_role == 'DAP' else 'Direcção Pedagógica')
        nome_director = getattr(escola, 'director_nome', None) or (self.request.user.nome if pode_homologar else 'Director da Escola')

        if serializer.validated_data.get('director_turma'):
            extra_kwargs['dt_nomeado_por'] = nome_dap
            extra_kwargs['dt_data_nomeacao'] = timezone.now()
            if homologar_imediato:
                extra_kwargs['dt_status_homologacao'] = 'HOMOLOGADO'
                extra_kwargs['dt_homologado_por'] = nome_director
                extra_kwargs['dt_data_homologacao'] = timezone.now()
            else:
                extra_kwargs['dt_status_homologacao'] = 'PENDENTE_HOMOLOGACAO'

        if serializer.validated_data.get('director_classe'):
            extra_kwargs['dc_nomeado_por'] = nome_dap
            extra_kwargs['dc_data_nomeacao'] = timezone.now()
            if homologar_imediato:
                extra_kwargs['dc_status_homologacao'] = 'HOMOLOGADO'
                extra_kwargs['dc_homologado_por'] = nome_director
                extra_kwargs['dc_data_homologacao'] = timezone.now()
            else:
                extra_kwargs['dc_status_homologacao'] = 'PENDENTE_HOMOLOGACAO'

        serializer.save(**extra_kwargs)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return Response({'success': True, 'data': TurmaSerializer(qs, many=True).data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({'success': True, 'data': serializer.data}, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        from django.utils import timezone
        kwargs['partial'] = True
        turma = self.get_object()
        old_dt_id = turma.director_turma_id
        old_dc_id = turma.director_classe_id

        serializer = self.get_serializer(turma, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        escola = turma.escola
        user_role = getattr(request.user, 'role', '')
        pode_homologar = user_role in ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA']
        homologar_imediato = bool(request.data.get('homologar_directores')) and pode_homologar

        nome_dap = getattr(escola, 'dap_nome', None) or (request.user.nome if user_role == 'DAP' else 'Direcção Pedagógica')
        nome_director = getattr(escola, 'director_nome', None) or (request.user.nome if pode_homologar else 'Director da Escola')

        extra_kwargs = {}
        new_dt = serializer.validated_data.get('director_turma', turma.director_turma)
        new_dc = serializer.validated_data.get('director_classe', turma.director_classe)

        if 'director_turma' in serializer.validated_data:
            if new_dt and new_dt.id != old_dt_id:
                extra_kwargs['dt_nomeado_por'] = nome_dap
                extra_kwargs['dt_data_nomeacao'] = timezone.now()
                if homologar_imediato:
                    extra_kwargs['dt_status_homologacao'] = 'HOMOLOGADO'
                    extra_kwargs['dt_homologado_por'] = nome_director
                    extra_kwargs['dt_data_homologacao'] = timezone.now()
                else:
                    extra_kwargs['dt_status_homologacao'] = 'PENDENTE_HOMOLOGACAO'
            elif new_dt and homologar_imediato:
                extra_kwargs['dt_status_homologacao'] = 'HOMOLOGADO'
                extra_kwargs['dt_homologado_por'] = nome_director
                extra_kwargs['dt_data_homologacao'] = timezone.now()

        if 'director_classe' in serializer.validated_data:
            if new_dc and new_dc.id != old_dc_id:
                extra_kwargs['dc_nomeado_por'] = nome_dap
                extra_kwargs['dc_data_nomeacao'] = timezone.now()
                if homologar_imediato:
                    extra_kwargs['dc_status_homologacao'] = 'HOMOLOGADO'
                    extra_kwargs['dc_homologado_por'] = nome_director
                    extra_kwargs['dc_data_homologacao'] = timezone.now()
                else:
                    extra_kwargs['dc_status_homologacao'] = 'PENDENTE_HOMOLOGACAO'
            elif new_dc and homologar_imediato:
                extra_kwargs['dc_status_homologacao'] = 'HOMOLOGADO'
                extra_kwargs['dc_homologado_por'] = nome_director
                extra_kwargs['dc_data_homologacao'] = timezone.now()

        turma_salva = serializer.save(**extra_kwargs)

        # Actualizar os códigos dos alunos da turma caso classe, turma, ano ou área tenham sido alterados
        for aluno in turma_salva.alunos.all():
            aluno.classe = turma_salva.grau_ano
            aluno.area = turma_salva.area
            aluno.save()

        return Response({'success': True, 'data': TurmaSerializer(turma_salva).data})

    @action(detail=True, methods=['post'], url_path='nomear-directores')
    def nomear_directores(self, request, pk=None):
        """
        Acção oficial do Director Pedagógico (DAP/DP) para nomear o Director de Turma (DT)
        e/ou o Director de Classe (DC). Após a nomeação, fica pendente de homologação pelo
        Director da Escola (GD) para emissão definitiva do código oficial.
        """
        from django.utils import timezone
        from apps.professores.models import Professor

        turma = self.get_object()
        escola = turma.escola
        user_role = getattr(request.user, 'role', '')
        if user_role not in ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP']:
            return Response({
                'success': False,
                'message': 'Apenas a Direcção Pedagógica (DP) ou Direcção da Escola pode nomear Directores de Turma e de Classe.'
            }, status=status.HTTP_403_FORBIDDEN)

        dt_id = request.data.get('director_turma_id')
        dc_id = request.data.get('director_classe_id')
        aplicar_classe = request.data.get('aplicar_toda_classe', True)

        nome_dap = (
            request.data.get('nomeado_por')
            or (request.user.nome if user_role == 'DAP' else None)
            or getattr(escola, 'dap_nome', None)
            or 'Direcção Pedagógica'
        )

        if 'director_turma_id' in request.data:
            if dt_id:
                prof_dt = Professor.objects.filter(id=dt_id, escola=escola).first()
                if not prof_dt:
                    return Response({'success': False, 'message': 'Professor indicado para Director de Turma não encontrado nesta escola.'}, status=status.HTTP_404_NOT_FOUND)
                turma.director_turma = prof_dt
                turma.dt_status_homologacao = 'PENDENTE_HOMOLOGACAO'
                turma.dt_nomeado_por = nome_dap
                turma.dt_data_nomeacao = timezone.now()
                turma.codigo_director_turma = None
            else:
                turma.director_turma = None
                turma.dt_status_homologacao = 'NAO_DEFINIDO'
                turma.codigo_director_turma = None

        if 'director_classe_id' in request.data:
            if dc_id:
                prof_dc = Professor.objects.filter(id=dc_id, escola=escola).first()
                if not prof_dc:
                    return Response({'success': False, 'message': 'Professor indicado para Director de Classe não encontrado nesta escola.'}, status=status.HTTP_404_NOT_FOUND)
                turma.director_classe = prof_dc
                turma.dc_status_homologacao = 'PENDENTE_HOMOLOGACAO'
                turma.dc_nomeado_por = nome_dap
                turma.dc_data_nomeacao = timezone.now()
                turma.codigo_director_classe = None

                if aplicar_classe:
                    outras_turmas = Turma.objects.filter(
                        escola=escola,
                        grau_ano__iexact=turma.grau_ano,
                        ano_letivo=turma.ano_letivo
                    ).exclude(id=turma.id)
                    for t_outra in outras_turmas:
                        t_outra.director_classe = prof_dc
                        t_outra.dc_status_homologacao = 'PENDENTE_HOMOLOGACAO'
                        t_outra.dc_nomeado_por = nome_dap
                        t_outra.dc_data_nomeacao = timezone.now()
                        t_outra.codigo_director_classe = None
                        t_outra.save()
            else:
                turma.director_classe = None
                turma.dc_status_homologacao = 'NAO_DEFINIDO'
                turma.codigo_director_classe = None

        turma.save()
        return Response({
            'success': True,
            'message': f'Nomeação registada pela Direcção Pedagógica ({nome_dap}). Aguarda homologação do Director da Escola.',
            'data': TurmaSerializer(turma).data
        })

    @action(detail=True, methods=['post'], url_path='homologar-directores')
    def homologar_directores(self, request, pk=None):
        """
        Acção exclusiva do Director da Escola (Gabinete do Director - GD / Admin Geral)
        para homologar a nomeação feita pelo Director Pedagógico e emitir os códigos oficiais:
          - Código do Director de Turma (ex: DT0101S0001.12.01.2026.cg)
          - Código do Director de Classe (ex: DC0101S0001.12.2026)
        """
        from django.utils import timezone

        turma = self.get_object()
        escola = turma.escola
        user_role = getattr(request.user, 'role', '')
        if user_role not in ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA']:
            return Response({
                'success': False,
                'message': 'Apenas o Director da Escola (Gabinete do Director) tem competência para homologar a nomeação do Director de Turma e do Director de Classe.'
            }, status=status.HTTP_403_FORBIDDEN)

        tipo = (request.data.get('tipo') or 'AMBOS').upper()  # 'DT', 'DC', 'AMBOS'
        acao = (request.data.get('acao') or 'HOMOLOGAR').upper()  # 'HOMOLOGAR', 'REJEITAR'
        nome_director = (
            request.data.get('homologado_por')
            or getattr(escola, 'director_nome', None)
            or request.user.nome
            or 'Director da Escola'
        )

        codigos_gerados = []

        if tipo in ['DT', 'AMBOS'] and turma.director_turma_id:
            if acao == 'REJEITAR':
                turma.dt_status_homologacao = 'REJEITADO'
                turma.codigo_director_turma = None
            else:
                turma.dt_status_homologacao = 'HOMOLOGADO'
                turma.dt_homologado_por = nome_director
                turma.dt_data_homologacao = timezone.now()

        if tipo in ['DC', 'AMBOS'] and turma.director_classe_id:
            if acao == 'REJEITAR':
                turma.dc_status_homologacao = 'REJEITADO'
                turma.codigo_director_classe = None
            else:
                turma.dc_status_homologacao = 'HOMOLOGADO'
                turma.dc_homologado_por = nome_director
                turma.dc_data_homologacao = timezone.now()

                # Homologar o mesmo Director de Classe em todas as turmas da mesma classe/ano
                outras_turmas = Turma.objects.filter(
                    escola=escola,
                    grau_ano__iexact=turma.grau_ano,
                    ano_letivo=turma.ano_letivo,
                    director_classe_id=turma.director_classe_id
                ).exclude(id=turma.id)
                for t_outra in outras_turmas:
                    t_outra.dc_status_homologacao = 'HOMOLOGADO'
                    t_outra.dc_homologado_por = nome_director
                    t_outra.dc_data_homologacao = timezone.now()
                    t_outra.save()

        turma.save()
        if turma.codigo_director_turma:
            codigos_gerados.append(f"DT: {turma.codigo_director_turma}")
        if turma.codigo_director_classe:
            codigos_gerados.append(f"DC: {turma.codigo_director_classe}")

        resumo_codigos = f" ({', '.join(codigos_gerados)})" if codigos_gerados else ""
        msg = (
            f"Nomeação homologada pelo Director da Escola ({nome_director}) com sucesso{resumo_codigos}!"
            if acao != 'REJEITAR'
            else f"Nomeação rejeitada pelo Gabinete do Director ({nome_director})."
        )
        return Response({
            'success': True,
            'message': msg,
            'data': TurmaSerializer(turma).data
        })

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return Response({'success': True, 'message': 'Turma excluída com sucesso.'})

    @action(detail=False, methods=['post'], url_path='criar-lote')
    def criar_lote(self, request):
        escola = self.request.tenant or getattr(self.request.user, 'escola', None)
        if not escola and getattr(self.request.user, 'role', '') == 'SUPERADMIN':
            escola_id = (
                request.data.get('escola_id') or
                request.headers.get('X-Tenant-ID')
            )
            if escola_id:
                from apps.tenants.models import Escola
                escola = Escola.objects.filter(id=escola_id).first()
            if not escola:
                from apps.tenants.models import Escola
                escola = Escola.objects.filter(status='ATIVA').first() or Escola.objects.first()

        if not escola:
            return Response({'success': False, 'message': 'Nenhuma escola seleccionada.'}, status=status.HTTP_400_BAD_REQUEST)

        grau_ano = request.data.get('grau_ano', '').strip()
        quantidade = int(request.data.get('quantidade') or 1)
        turno = request.data.get('turno', 'MANHA')
        capacidade_maxima = int(request.data.get('capacidade_maxima') or 50)
        ano_letivo = request.data.get('ano_letivo', '2026')
        tipo_sufixo = request.data.get('tipo_sufixo', 'NUMERO') # 'NUMERO' (1, 2, 3...) ou 'LETRA' (A, B, C...)

        if not grau_ano:
            return Response({'success': False, 'message': 'Classe / Grau é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)

        area = request.data.get('area', 'Geral')
        distribuir_auto = request.data.get('distribuir_automaticamente', False)
        criterio = request.data.get('criterio', 'IDADE_ASC')

        import re as _re

        from .utils import extrair_identificador_turma, obter_proximo_numero_turma_classe

        criadas = []
        letras = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

        if tipo_sufixo == 'NUMERO':
            proximo_num = obter_proximo_numero_turma_classe(escola, grau_ano, ano_letivo, 'NUMERO')
        else:
            proxima_letra = obter_proximo_numero_turma_classe(escola, grau_ano, ano_letivo, 'LETRA')
            proximo_letra_idx = letras.index(proxima_letra) if proxima_letra in letras else 0

        for i in range(quantidade):
            if tipo_sufixo == 'LETRA':
                sufixo = letras[(proximo_letra_idx + i) % len(letras)]
                nome_cand = f"Turma {sufixo}"
            else:
                num = proximo_num + i
                nome_cand = f"Turma {num}"

            # Garantia final de unicidade no banco dentro da classe
            tentativa = nome_cand
            extra = 0
            while Turma.objects.filter(escola=escola, grau_ano__iexact=grau_ano, nome=tentativa, ano_letivo=ano_letivo).exists() or \
                  Turma.objects.filter(escola=escola, grau_ano__iexact=grau_ano, nome=f"{grau_ano} {tentativa}", ano_letivo=ano_letivo).exists():
                extra += 1
                if tipo_sufixo == 'NUMERO':
                    tentativa = f"Turma {proximo_num + i + extra}"
                else:
                    tentativa = f"Turma {letras[(proximo_letra_idx + i + extra) % len(letras)]}"

            turma = Turma.objects.create(
                escola=escola,
                nome=tentativa,
                grau_ano=grau_ano,
                area=area,
                turno=turno,
                capacidade_maxima=capacidade_maxima,
                ano_letivo=ano_letivo
            )
            criadas.append(turma)

        alocados_count = 0
        if distribuir_auto and criadas:
            alocados_count, _ = executar_distribuicao_alunos(
                escola=escola,
                turmas=criadas,
                grau_ano=grau_ano,
                area=area,
                criterio=criterio,
                apenas_sem_turma=True,
                capacidade_maxima=capacidade_maxima
            )

        msg = f'{len(criadas)} turmas criadas com sucesso para a {grau_ano} ({area})!'
        if alocados_count > 0:
            msg += f' {alocados_count} alunos pendentes foram distribuídos automaticamente com base no critério selecionado.'

        return Response({
            'success': True,
            'message': msg,
            'alocados_count': alocados_count,
            'data': TurmaSerializer(criadas, many=True).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='distribuir-automaticamente')
    def distribuir_automaticamente(self, request):
        escola = self.request.tenant or getattr(self.request.user, 'escola', None)
        if not escola and getattr(self.request.user, 'role', '') == 'SUPERADMIN':
            escola_id = (
                request.data.get('escola_id') or
                request.headers.get('X-Tenant-ID')
            )
            if escola_id:
                from apps.tenants.models import Escola
                escola = Escola.objects.filter(id=escola_id).first()
            if not escola:
                from apps.tenants.models import Escola
                escola = Escola.objects.filter(status='ATIVA').first() or Escola.objects.first()

        if not escola:
            return Response({'success': False, 'message': 'Nenhuma escola seleccionada.'}, status=status.HTTP_400_BAD_REQUEST)

        grau_ano = request.data.get('grau_ano')
        area = request.data.get('area')
        criterio = request.data.get('criterio', 'IDADE_ASC') # IDADE_ASC, IDADE_DESC, GENERO_EQUILIBRADO, EQUILIBRIO_IDADE_GENERO, ALFABETICO, ALEATORIO
        apenas_sem_turma = request.data.get('apenas_sem_turma', True)
        capacidade_maxima_param = request.data.get('capacidade_maxima')
        turmas_ids = request.data.get('turmas_ids', [])

        if turmas_ids:
            turmas = list(Turma.objects.filter(id__in=turmas_ids, escola=escola).order_by('nome'))
        elif grau_ano and grau_ano != 'TODAS':
            turmas = list(Turma.objects.filter(grau_ano__iexact=grau_ano, escola=escola).order_by('nome'))
        else:
            turmas = list(Turma.objects.filter(escola=escola).order_by('grau_ano', 'nome'))

        if area and area != 'TODAS':
            def match_area_filtro(t_area, a_filtro):
                t_low = (t_area or 'Geral').strip().lower()
                a_low = (a_filtro or '').strip().lower()
                if t_low == a_low:
                    return True
                if a_low in ['geral', 'ensino geral', 'tronco comum'] and t_low in ['geral', 'ensino geral', 'tronco comum']:
                    return True
                return False
            turmas = [t for t in turmas if match_area_filtro(t.area, area)]

        if not turmas:
            return Response({
                'success': False,
                'message': 'Nenhuma turma de destino encontrada para a selecção. Por favor, crie as turmas da classe/área antes de distribuir os alunos.'
            }, status=status.HTTP_400_BAD_REQUEST)

        alocados_count, resumo = executar_distribuicao_alunos(
            escola=escola,
            turmas=turmas,
            grau_ano=grau_ano,
            area=area,
            criterio=criterio,
            apenas_sem_turma=apenas_sem_turma,
            capacidade_maxima=capacidade_maxima_param
        )

        if alocados_count == 0:
            return Response({
                'success': False,
                'message': 'Nenhum aluno elegível encontrado para distribuição nesta escola/classe/área.'
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'success': True,
            'message': f'{alocados_count} alunos distribuídos com sucesso por {len(turmas)} turma(s)!',
            'total_alocados': alocados_count,
            'turmas_resumo': resumo
        })

    @action(detail=False, methods=['get'], url_path='previa-formacao-automatica')
    def previa_formacao_automatica(self, request):
        import datetime
        import math
        from apps.alunos.models import Aluno
        from django.db.models import Q

        escola = self.request.tenant or getattr(self.request.user, 'escola', None)
        if not escola and getattr(self.request.user, 'role', '') == 'SUPERADMIN':
            escola_id = request.query_params.get('escola_id') or request.headers.get('X-Tenant-ID')
            if escola_id:
                from apps.tenants.models import Escola
                escola = Escola.objects.filter(id=escola_id).first()
            if not escola:
                from apps.tenants.models import Escola
                escola = Escola.objects.filter(status='ATIVA').first() or Escola.objects.first()

        if not escola:
            return Response({'success': False, 'message': 'Nenhuma escola seleccionada.'}, status=status.HTTP_400_BAD_REQUEST)

        ano_letivo = request.query_params.get('ano_letivo') or getattr(escola, 'ano_letivo_ativo', '2026') or '2026'
        capacidade_padrao = int(request.query_params.get('capacidade_maxima') or 50)

        # Buscar alunos activos sem turma na escola
        alunos_qs = Aluno.objects.filter(escola=escola, status='ATIVO', turma__isnull=True)
        if ano_letivo and ano_letivo != 'TODOS':
            alunos_qs = alunos_qs.filter(Q(ano_ingresso=ano_letivo) | Q(ano_ingresso__isnull=True) | Q(ano_ingresso=''))

        grau_filtro = request.query_params.get('grau_ano')
        if grau_filtro and grau_filtro != 'TODAS':
            alunos_qs = alunos_qs.filter(classe__iexact=grau_filtro)

        area_filtro = request.query_params.get('area')
        if area_filtro and area_filtro != 'TODAS':
            a_low = area_filtro.strip().lower()
            if a_low in ['geral', 'ensino geral', 'tronco comum']:
                alunos_qs = alunos_qs.filter(
                    Q(area__iexact='Geral') | Q(area__iexact='Ensino Geral') | Q(area__iexact='Tronco Comum') | Q(area__isnull=True) | Q(area='')
                )
            else:
                alunos_qs = alunos_qs.filter(Q(area__iexact=area_filtro) | Q(area__isnull=True) | Q(area=''))

        grupos_dict = {}
        hoje = datetime.date.today()

        for a in alunos_qs:
            cls = (a.classe or '10ª Classe').strip()
            ar = (a.area or 'Geral').strip()
            if ar.lower() in ['geral', 'ensino geral', 'tronco comum']:
                ar = 'Ensino Geral'
            chave = (cls, ar)
            if chave not in grupos_dict:
                grupos_dict[chave] = []
            grupos_dict[chave].append(a)

        from .utils import obter_proximo_numero_turma_classe
        proximo_num_por_classe = {}
        for (cls_k, _) in grupos_dict.keys():
            if cls_k not in proximo_num_por_classe:
                proximo_num_por_classe[cls_k] = obter_proximo_numero_turma_classe(escola, cls_k, ano_letivo, 'NUMERO')

        grupos_res = []
        for (cls, ar), alunos in sorted(grupos_dict.items(), key=lambda x: x[0][0]):
            total = len(alunos)
            f_count = sum(1 for al in alunos if al.genero == 'F')
            m_count = sum(1 for al in alunos if al.genero == 'M')

            idades = []
            for al in alunos:
                if al.data_nascimento:
                    idade = hoje.year - al.data_nascimento.year - ((hoje.month, hoje.day) < (al.data_nascimento.month, al.data_nascimento.day))
                    idades.append(idade)

            min_idade = min(idades) if idades else '-'
            max_idade = max(idades) if idades else '-'
            media_idade = round(sum(idades) / len(idades), 1) if idades else '-'

            # Turmas existentes para esta classe e área no ano
            turmas_existentes = Turma.objects.filter(escola=escola, grau_ano__iexact=cls, ano_letivo=ano_letivo)
            def match_area(t_area, a_area):
                t_l = (t_area or 'Geral').strip().lower()
                a_l = a_area.strip().lower()
                if t_l == a_l: return True
                if a_l in ['geral', 'ensino geral', 'tronco comum'] and t_l in ['geral', 'ensino geral', 'tronco comum']: return True
                return False

            existentes = [t for t in turmas_existentes if match_area(t.area, ar)]
            cap_livre = sum(max(0, (t.capacidade_maxima or 50) - t.alunos.filter(status='ATIVO').count()) for t in existentes)

            turmas_necessarias = max(1, math.ceil(total / capacidade_padrao))
            novas_a_criar = max(0, math.ceil((total - cap_livre) / capacidade_padrao)) if total > cap_livre else 0

            # Proposta de turmas automáticas contínuas para a classe (sem repetição entre secções)
            propostas = []
            num_atual = proximo_num_por_classe.get(cls, 1)

            for i in range(1, turmas_necessarias + 1):
                num_turma = num_atual
                num_atual += 1
                turno = 'MANHA' if i <= math.ceil(turmas_necessarias / 2) else 'TARDE'
                propostas.append({
                    'nome': f"Turma {num_turma}",
                    'turno': turno,
                    'capacidade': capacidade_padrao
                })
            proximo_num_por_classe[cls] = num_atual

            grupos_res.append({
                'grau_ano': cls,
                'area': ar,
                'total_alunos': total,
                'total_feminino': f_count,
                'total_masculino': m_count,
                'idade_minima': min_idade,
                'idade_maxima': max_idade,
                'idade_media': media_idade,
                'turmas_existentes': len(existentes),
                'turmas_necessarias': turmas_necessarias,
                'novas_a_criar': novas_a_criar,
                'propostas': propostas
            })

        return Response({
            'success': True,
            'ano_letivo': ano_letivo,
            'total_alunos_pendentes': alunos_qs.count(),
            'grupos': grupos_res
        })

    @action(detail=False, methods=['post'], url_path='gerar-e-enturmar-automatico')
    def gerar_e_enturmar_automatico(self, request):
        import datetime
        import math
        import re
        from apps.alunos.models import Aluno
        from django.db.models import Q

        escola = self.request.tenant or getattr(self.request.user, 'escola', None)
        if not escola and getattr(self.request.user, 'role', '') == 'SUPERADMIN':
            escola_id = request.data.get('escola_id') or request.headers.get('X-Tenant-ID')
            if escola_id:
                from apps.tenants.models import Escola
                escola = Escola.objects.filter(id=escola_id).first()
            if not escola:
                from apps.tenants.models import Escola
                escola = Escola.objects.filter(status='ATIVA').first() or Escola.objects.first()

        if not escola:
            return Response({'success': False, 'message': 'Nenhuma escola seleccionada.'}, status=status.HTTP_400_BAD_REQUEST)

        grau_ano_filtro = request.data.get('grau_ano')
        area_filtro = request.data.get('area')
        capacidade_maxima = int(request.data.get('capacidade_maxima') or 50)
        criterio = request.data.get('criterio', 'EQUILIBRIO_IDADE_GENERO')
        ano_letivo = request.data.get('ano_letivo') or getattr(escola, 'ano_letivo_ativo', '2026') or '2026'
        turno_modo = request.data.get('turno', 'AUTO_IDADE') # 'AUTO_IDADE', 'MANHA', 'TARDE', 'NOITE'
        apenas_sem_turma = request.data.get('apenas_sem_turma', True)

        # Buscar alunos
        alunos_qs = Aluno.objects.filter(escola=escola, status='ATIVO')
        if apenas_sem_turma:
            alunos_qs = alunos_qs.filter(turma__isnull=True)

        if ano_letivo and ano_letivo != 'TODOS':
            alunos_qs = alunos_qs.filter(Q(ano_ingresso=ano_letivo) | Q(ano_ingresso__isnull=True) | Q(ano_ingresso=''))

        if grau_ano_filtro and grau_ano_filtro != 'TODAS':
            alunos_qs = alunos_qs.filter(Q(classe__iexact=grau_ano_filtro) | Q(turma__grau_ano__iexact=grau_ano_filtro))

        if area_filtro and area_filtro != 'TODAS':
            a_low = area_filtro.strip().lower()
            if a_low in ['geral', 'ensino geral', 'tronco comum']:
                alunos_qs = alunos_qs.filter(
                    Q(area__iexact='Geral') | Q(area__iexact='Ensino Geral') | Q(area__iexact='Tronco Comum') | Q(area__isnull=True) | Q(area='')
                )
            else:
                alunos_qs = alunos_qs.filter(Q(area__iexact=area_filtro) | Q(area__isnull=True) | Q(area=''))

        if not alunos_qs.exists():
            return Response({
                'success': False,
                'message': 'Não foram encontrados alunos elegíveis para formação automática de turmas nesta selecção.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Agrupar alunos por (Classe, Área)
        grupos = {}
        for al in alunos_qs:
            cls = (al.classe or '10ª Classe').strip()
            ar = (al.area or 'Geral').strip()
            if ar.lower() in ['geral', 'ensino geral', 'tronco comum']:
                ar = 'Ensino Geral'
            chave = (cls, ar)
            if chave not in grupos:
                grupos[chave] = []
            grupos[chave].append(al)

        total_turmas_novas = 0
        total_alunos_alocados = 0
        detalhes_grupos = []

        def match_area_str(t_area, a_area):
            t_l = (t_area or 'Geral').strip().lower()
            a_l = a_area.strip().lower()
            if t_l == a_l: return True
            if a_l in ['geral', 'ensino geral', 'tronco comum'] and t_l in ['geral', 'ensino geral', 'tronco comum']: return True
            return False

        from .utils import obter_proximo_numero_turma_classe
        proximo_num_por_classe = {}
        for (cls_k, _) in grupos.keys():
            if cls_k not in proximo_num_por_classe:
                proximo_num_por_classe[cls_k] = obter_proximo_numero_turma_classe(escola, cls_k, ano_letivo, 'NUMERO')

        for (cls, ar), alunos_grupo in grupos.items():
            N = len(alunos_grupo)
            if N == 0:
                continue

            # Buscar turmas existentes para a classe e área
            turmas_existentes = list(Turma.objects.filter(escola=escola, grau_ano__iexact=cls, ano_letivo=ano_letivo))
            existentes_area = [t for t in turmas_existentes if match_area_str(t.area, ar)]

            # Calcular capacidade livre nas turmas existentes
            cap_livre = sum(max(0, (t.capacidade_maxima or capacidade_maxima) - t.alunos.filter(status='ATIVO').count()) for t in existentes_area)

            # Quantas turmas novas precisam ser criadas
            if N > cap_livre:
                turmas_a_criar = math.ceil((N - cap_livre) / capacidade_maxima)
            else:
                turmas_a_criar = 0

            turmas_novas = []
            for i in range(1, turmas_a_criar + 1):
                num_turma = proximo_num_por_classe.get(cls, 1)
                proximo_num_por_classe[cls] = num_turma + 1

                # Atribuição pedagógica de turno
                if turno_modo == 'AUTO_IDADE':
                    # Metade inicial manhã (alunos mais novos), metade final tarde (alunos mais velhos)
                    t_turno = 'MANHA' if i <= math.ceil(turmas_a_criar / 2) else 'TARDE'
                else:
                    t_turno = turno_modo if turno_modo in ['MANHA', 'TARDE', 'NOITE'] else 'MANHA'

                nome_cand = f"Turma {num_turma}"
                while Turma.objects.filter(escola=escola, grau_ano__iexact=cls, nome=nome_cand, ano_letivo=ano_letivo).exists() or \
                      Turma.objects.filter(escola=escola, grau_ano__iexact=cls, nome=f"{cls} {nome_cand}", ano_letivo=ano_letivo).exists():
                    num_turma = proximo_num_por_classe[cls]
                    proximo_num_por_classe[cls] = num_turma + 1
                    nome_cand = f"Turma {num_turma}"

                t_nova = Turma.objects.create(
                    escola=escola,
                    nome=nome_cand,
                    grau_ano=cls,
                    area=ar,
                    turno=t_turno,
                    capacidade_maxima=capacidade_maxima,
                    ano_letivo=ano_letivo
                )
                turmas_novas.append(t_nova)
                total_turmas_novas += 1

            # Todas as turmas utilizáveis para este grupo (com prioridade MANHA primeiro)
            todas_turmas_grupo = existentes_area + turmas_novas
            todas_turmas_grupo.sort(key=lambda t: (0 if t.turno == 'MANHA' else (1 if t.turno == 'TARDE' else 2), t.nome))

            # Ordenar alunos conforme critério de idade e género
            if criterio == 'IDADE_ASC':
                # Jovens primeiro
                alunos_ordenados = sorted(alunos_grupo, key=lambda a: (a.data_nascimento or datetime.date(1900, 1, 1)), reverse=True)
            elif criterio == 'IDADE_DESC':
                # Mais velhos primeiro
                alunos_ordenados = sorted(alunos_grupo, key=lambda a: (a.data_nascimento or datetime.date(2099, 1, 1)))
            elif criterio == 'GENERO_EQUILIBRADO':
                fem = [a for a in alunos_grupo if a.genero == 'F']
                masc = [a for a in alunos_grupo if a.genero == 'M']
                alunos_ordenados = []
                max_l = max(len(fem), len(masc))
                for idx in range(max_l):
                    if idx < len(fem): alunos_ordenados.append(fem[idx])
                    if idx < len(masc): alunos_ordenados.append(masc[idx])
            elif criterio == 'ALFABETICO':
                alunos_ordenados = sorted(alunos_grupo, key=lambda a: (a.nome or '').lower())
            else: # EQUILIBRIO_IDADE_GENERO (Padrão MINEDH)
                fem = sorted([a for a in alunos_grupo if a.genero == 'F'], key=lambda a: (a.data_nascimento or datetime.date(1900, 1, 1)), reverse=True)
                masc = sorted([a for a in alunos_grupo if a.genero == 'M'], key=lambda a: (a.data_nascimento or datetime.date(1900, 1, 1)), reverse=True)
                alunos_ordenados = []
                max_l = max(len(fem), len(masc))
                for idx in range(max_l):
                    if idx < len(fem): alunos_ordenados.append(fem[idx])
                    if idx < len(masc): alunos_ordenados.append(masc[idx])

            # Enturmação dos alunos
            ocupacao = {t.id: t.alunos.filter(status='ATIVO').count() for t in todas_turmas_grupo}
            turma_idx = 0
            num_turmas = len(todas_turmas_grupo)

            for aluno in alunos_ordenados:
                alocado = False
                tentativas = 0
                while tentativas < num_turmas:
                    turma_alvo = todas_turmas_grupo[turma_idx % num_turmas]
                    cap_limite = turma_alvo.capacidade_maxima or capacidade_maxima
                    if ocupacao[turma_alvo.id] < cap_limite:
                        aluno.turma = turma_alvo
                        aluno.classe = turma_alvo.grau_ano
                        aluno.area = turma_alvo.area
                        aluno.save()
                        ocupacao[turma_alvo.id] += 1
                        total_alunos_alocados += 1
                        alocado = True
                        turma_idx += 1
                        break
                    else:
                        turma_idx += 1
                        tentativas += 1

                if not alocado and todas_turmas_grupo:
                    menor_t = min(todas_turmas_grupo, key=lambda t: ocupacao[t.id])
                    aluno.turma = menor_t
                    aluno.classe = menor_t.grau_ano
                    aluno.area = menor_t.area
                    aluno.save()
                    ocupacao[menor_t.id] += 1
                    total_alunos_alocados += 1

            detalhes_grupos.append({
                'grau_ano': cls,
                'area': ar,
                'alunos_processados': N,
                'turmas_criadas': len(turmas_novas),
                'turmas': [
                    {
                        'id': str(t.id),
                        'nome': t.nome,
                        'turno': t.turno,
                        'total_alunos': ocupacao[t.id],
                        'capacidade_maxima': t.capacidade_maxima
                    }
                    for t in todas_turmas_grupo
                ]
            })

        return Response({
            'success': True,
            'message': f'Formação Automática Concluída! Foram criadas {total_turmas_novas} turmas (Turma 1, 2, 3...) e enturmados {total_alunos_alocados} alunos na base da idade, género e secção.',
            'total_turmas_novas': total_turmas_novas,
            'total_alunos_alocados': total_alunos_alocados,
            'detalhes': detalhes_grupos
        })

    @action(detail=False, methods=['post'], url_path='renumerar-turmas')
    def renumerar_turmas(self, request):
        """
        Corrige turmas com numeração duplicada ou inconsistente dentro de uma classe.
        Renumera todas as turmas de cada classe de forma contínua e global (1, 2, 3...),
        sem repetições entre secções/áreas.
        """
        import re as _re
        from django.db import transaction

        escola = self.request.tenant or getattr(self.request.user, 'escola', None)
        if not escola:
            return Response({'success': False, 'message': 'Nenhuma escola seleccionada.'}, status=status.HTTP_400_BAD_REQUEST)

        ano_letivo = request.data.get('ano_letivo', '2026')
        grau_filtro = request.data.get('grau_ano')  # Opcional: só renumerar uma classe específica

        qs = Turma.objects.filter(escola=escola, ano_letivo=ano_letivo)
        if grau_filtro:
            qs = qs.filter(grau_ano__iexact=grau_filtro)

        # Agrupar turmas por grau_ano
        por_classe = {}
        for t in qs:
            cls = (t.grau_ano or '').strip()
            if cls not in por_classe:
                por_classe[cls] = []
            por_classe[cls].append(t)

        renomeadas = 0
        detalhes = []

        with transaction.atomic():
            from .utils import extrair_identificador_turma
            for cls, turmas in por_classe.items():
                def chave_ordenacao(t):
                    tipo, val, _ = extrair_identificador_turma(t.nome, t.grau_ano)
                    tem_colisao = 1 if '(' in (t.nome or '') else 0
                    num_val = val if tipo == 'NUMERO' else (ord(val) if tipo == 'LETRA' else 999)
                    return (num_val, tem_colisao, t.created_at)

                turmas_ordenadas = sorted(turmas, key=chave_ordenacao)

                # Fase 1: Atribuir nomes temporários únicos para evitar conflitos de UniqueConstraint
                for t in turmas_ordenadas:
                    t.nome = f"__TMP_RENUM_{t.id}__"
                    t.save(update_fields=['nome'])

                # Fase 2: Atribuir numeração contínua definitiva: Turma 1, Turma 2, Turma 3...
                for novo_num, turma in enumerate(turmas_ordenadas, start=1):
                    nome_final = f"Turma {novo_num}"
                    turma.nome = nome_final
                    turma.save()
                    for al in turma.alunos.all():
                        al.save()
                    renomeadas += 1
                    detalhes.append({'id': str(turma.id), 'para': nome_final, 'grau': cls, 'area': turma.area})

        return Response({
            'success': True,
            'message': f'{renomeadas} turma(s) renumerada(s) com sucesso de forma contínua (Turma 1, Turma 2, Turma 3...).',
            'renomeadas': renomeadas,
            'detalhes': detalhes
        })


def executar_distribuicao_alunos(escola, turmas, grau_ano=None, area=None, criterio='IDADE_ASC', apenas_sem_turma=True, capacidade_maxima=None):
    import random
    from apps.alunos.models import Aluno
    from django.db.models import Q

    if not turmas:
        return 0, []

    # Se foi definida uma nova capacidade máxima pelo utilizador, atualizar nas turmas
    if capacidade_maxima:
        try:
            cap_int = int(capacidade_maxima)
            if cap_int > 0:
                for t in turmas:
                    t.capacidade_maxima = cap_int
                    t.save(update_fields=['capacidade_maxima'])
        except (ValueError, TypeError):
            pass

    # Selecionar alunos elegíveis respeitando a Classe/Grau e Área de Estudo
    alunos_qs = Aluno.objects.filter(escola=escola, status='ATIVO')
    if apenas_sem_turma:
        alunos_qs = alunos_qs.filter(turma__isnull=True)
        if grau_ano and grau_ano != 'TODAS':
            alunos_qs = alunos_qs.filter(
                Q(classe__iexact=grau_ano) | Q(classe__isnull=True) | Q(classe='')
            )
    elif grau_ano and grau_ano != 'TODAS':
        alunos_qs = alunos_qs.filter(
            Q(turma__grau_ano__iexact=grau_ano) |
            (Q(turma__isnull=True) & (Q(classe__iexact=grau_ano) | Q(classe__isnull=True) | Q(classe='')))
        )

    if area and area != 'TODAS':
        a_low = area.strip().lower()
        if a_low in ['geral', 'ensino geral', 'tronco comum']:
            alunos_qs = alunos_qs.filter(
                Q(area__iexact='Geral') | Q(area__iexact='Ensino Geral') | Q(area__iexact='Tronco Comum') | Q(area__isnull=True) | Q(area='')
            )
        else:
            alunos_qs = alunos_qs.filter(Q(area__iexact=area) | Q(area__isnull=True) | Q(area=''))

    if not alunos_qs.exists():
        return 0, []

    # Ordenação conforme o critério pedagógico (Idade, Género, Ordem Alfabética, etc.)
    if criterio == 'IDADE_ASC':
        # Mais jovens primeiro (idade ascendente -> data de nascimento descendente)
        alunos = list(alunos_qs.order_by('-data_nascimento', 'nome'))
    elif criterio == 'IDADE_DESC':
        # Mais velhos primeiro (idade descendente -> data de nascimento ascendente)
        alunos = list(alunos_qs.order_by('data_nascimento', 'nome'))
    elif criterio == 'ALFABETICO':
        # Ordem alfabética
        alunos = list(alunos_qs.order_by('nome', 'apelido'))
    elif criterio == 'GENERO_EQUILIBRADO':
        # 50% Feminino / 50% Masculino balanceados uniformemente
        fem = list(alunos_qs.filter(genero='F').order_by('nome'))
        masc = list(alunos_qs.filter(genero='M').order_by('nome'))
        alunos = []
        max_len = max(len(fem), len(masc))
        for i in range(max_len):
            if i < len(fem): alunos.append(fem[i])
            if i < len(masc): alunos.append(masc[i])
    elif criterio == 'EQUILIBRIO_IDADE_GENERO':
        # Equilibrio duplo: alterna genero e ordena por idade
        fem = list(alunos_qs.filter(genero='F').order_by('-data_nascimento', 'nome'))
        masc = list(alunos_qs.filter(genero='M').order_by('-data_nascimento', 'nome'))
        alunos = []
        max_len = max(len(fem), len(masc))
        for i in range(max_len):
            if i < len(fem): alunos.append(fem[i])
            if i < len(masc): alunos.append(masc[i])
    elif criterio == 'ALEATORIO':
        alunos = list(alunos_qs)
        random.shuffle(alunos)
    else:
        alunos = list(alunos_qs.order_by('nome'))

    # Contagem de ocupação inicial por turma
    ocupacao = {}
    for t in turmas:
        ja_alocados = t.alunos.filter(status='ATIVO').exclude(id__in=[a.id for a in alunos]).count()
        ocupacao[t.id] = ja_alocados

    alocados_count = 0
    indices_por_area = {}

    for aluno in alunos:
        aluno_area = (aluno.area or 'Geral').strip()

        def area_corresponde(turma_area_str, al_norm):
            t_norm = (turma_area_str or 'Geral').strip().lower()
            if t_norm == al_norm:
                return True
            if al_norm in ['geral', 'ensino geral', 'tronco comum'] and t_norm in ['geral', 'ensino geral', 'tronco comum']:
                return True
            return False

        # Filtrar turmas que correspondem à área de estudo do aluno
        candidatas = [t for t in turmas if area_corresponde(t.area, aluno_area.lower())]
        if not candidatas:
            # Fallback para turmas 'Geral' / 'Ensino Geral' ou todas se a escola não separou por área
            candidatas = [t for t in turmas if (t.area or 'Geral').strip().lower() in ['geral', 'ensino geral', 'tronco comum']] or turmas

        total_cands = len(candidatas)
        if total_cands == 0:
            continue

        chave_area = aluno_area.lower()
        idx = indices_por_area.get(chave_area, 0)

        tentativas = 0
        alocado = False
        while tentativas < total_cands:
            turma_alvo = candidatas[idx % total_cands]
            limite = turma_alvo.capacidade_maxima or 50
            if ocupacao[turma_alvo.id] < limite:
                aluno.turma = turma_alvo
                aluno.classe = turma_alvo.grau_ano
                if not aluno.area or str(aluno.area).strip().lower() in ['', 'geral', 'ensino geral', 'tronco comum']:
                    aluno.area = turma_alvo.area
                aluno.save()
                ocupacao[turma_alvo.id] += 1
                alocados_count += 1
                alocado = True
                indices_por_area[chave_area] = idx + 1
                break
            else:
                idx += 1
                tentativas += 1

        if not alocado:
            # Se todas as turmas da área atingiram capacidade, aloca na de menor ocupação da área
            menor_turma = min(candidatas, key=lambda t: ocupacao[t.id])
            aluno.turma = menor_turma
            aluno.classe = menor_turma.grau_ano
            if not aluno.area or str(aluno.area).strip().lower() in ['', 'geral', 'ensino geral', 'tronco comum']:
                aluno.area = menor_turma.area
            aluno.save()
            ocupacao[menor_turma.id] += 1
            alocados_count += 1
            indices_por_area[chave_area] = idx + 1

    resumo = [
        {
            'turma_id': str(t.id),
            'turma_nome': t.nome,
            'grau_ano': t.grau_ano,
            'area': t.area,
            'capacidade_maxima': t.capacidade_maxima or 50,
            'total_alunos': ocupacao[t.id]
        }
        for t in turmas
    ]
    return alocados_count, resumo
