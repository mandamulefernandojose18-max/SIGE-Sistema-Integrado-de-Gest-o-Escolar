import io
import base64
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
import unicodedata, re
from django.http import HttpResponse
from django.db.models import Q, Count

from .models import MaterialEscolar
from .serializers import MaterialEscolarSerializer
from apps.tenants.models import Escola

def _safe_ascii_filename(nome: str) -> str:
    s = unicodedata.normalize('NFKD', str(nome or 'material.pdf')).encode('ascii', 'ignore').decode('ascii')
    s = re.sub(r'[^A-Za-z0-9._-]+', '_', s).strip('_')
    return s or 'material.pdf'

def get_tenant_escola_from_request(request):
    """
    Identifica a escola com isolamento estrito entre instituições:
    1. Se for SUPERADMIN:
       - Respeita o tenant ativo via header 'X-Tenant-ID' ou query/body 'escola_id'/'tenant_id'.
       - Fallback para request.tenant ou request.user.escola (se houver).
    2. Utilizadores de escola (ADMIN_ESCOLA, PROFESSOR, ALUNO, etc.):
       - Ficam estritamente restritos à sua própria escola (request.tenant ou request.user.escola).
       - NUNCA veem ou publicam dados de outras escolas.
    """
    user = getattr(request, 'user', None)
    is_super = getattr(user, 'role', '') == 'SUPERADMIN'

    if is_super:
        tenant_id = (
            request.headers.get('X-Tenant-ID')
            or (hasattr(request, 'query_params') and (request.query_params.get('escola_id') or request.query_params.get('tenant_id')))
            or (hasattr(request, 'GET') and (request.GET.get('escola_id') or request.GET.get('tenant_id')))
            or (isinstance(getattr(request, 'data', None), dict) and (request.data.get('escola_id') or request.data.get('escola')))
        )
        if tenant_id:
            return Escola.objects.filter(id=tenant_id).first()
        return getattr(request, 'tenant', None) or getattr(user, 'escola', None)

    escola = getattr(request, 'tenant', None)
    if not escola and user and getattr(user, 'is_authenticated', False):
        escola = getattr(user, 'escola', None)

    # Quem não é SUPERADMIN nunca escolhe a escola pelo pedido.
    return escola

CLASSES_MOCAMBIQUE = [
    '1ª Classe', '2ª Classe', '3ª Classe', '4ª Classe', '5ª Classe',
    '6ª Classe', '7ª Classe', '8ª Classe', '9ª Classe', '10ª Classe',
    '11ª Classe', '12ª Classe'
]

def _classes_reais_do_aluno(user):
    from apps.alunos.models import Aluno
    from apps.alunos.views_me import _turmas_do_aluno
    aluno = Aluno.objects.select_related('escola', 'turma').filter(id=getattr(user, 'aluno_id', None)).first()
    return {t.grau_ano for t in _turmas_do_aluno(aluno)} if aluno else set()


_AREAS_COMUNS = {'', 'geral', 'ensino geral', 'tronco comum'}


def _disciplinas_do_aluno(user, ano):
    """Disciplinas da classe e da área/secção em que o aluno estudou no ano indicado."""
    from apps.alunos.models import Aluno
    from apps.alunos.views_me import _turmas_do_aluno
    from apps.disciplinas.models import Disciplina
    aluno = Aluno.objects.select_related('escola', 'turma').filter(id=getattr(user, 'aluno_id', None)).first()
    if not aluno:
        return Disciplina.objects.none()
    turma = next((t for t in _turmas_do_aluno(aluno) if str(t.ano_letivo) == str(ano)), None)
    if not turma:
        return Disciplina.objects.none()
    from django.db.models import Q
    area = (turma.area or '').strip()
    if area.lower() in _AREAS_COMUNS:
        # Turma sem área própria: vale a área/secção registada no aluno (turma actual)
        area = (aluno.area or '').strip() if turma.id == aluno.turma_id else ''
    qs = Disciplina.objects.filter(escola=aluno.escola)
    num = re.search(r'\d+', turma.grau_ano or '')
    if num:
        # compara pelo número da classe, tolerando variações de escrita ("10ª Classe", "10 Classe")
        qs = qs.filter(classe__regex=rf'^\s*[^0-9]*{num.group()}\D*$')
    else:
        qs = qs.filter(classe=turma.grau_ano)
    comuns = Q(area__iregex=r'^\s*(|geral|ensino geral|tronco comum)\s*$')
    if area.lower() in _AREAS_COMUNS:
        qs = qs.filter(comuns)
    else:
        # Áreas são texto livre ("Ciências", "Ciências e Letras", "CB"...): compara por ramo/sub-área
        from apps.pautas.services import categorizar_area, normalizar_texto
        ramo_a, sub_a = categorizar_area(area)
        alvo = normalizar_texto(area)
        ids = []
        for d in qs.only('id', 'area'):
            da = (d.area or '').strip()
            if da.lower() in _AREAS_COMUNS:
                ids.append(d.id)
                continue
            ramo_d, sub_d = categorizar_area(da)
            nd = normalizar_texto(da)
            if nd == alvo or (nd and (nd in alvo or alvo in nd)):
                ids.append(d.id)
            elif ramo_d != 'GERAL' and ramo_d == ramo_a and (sub_d == sub_a or sub_d.endswith('_GERAL') or sub_a.endswith('_GERAL')):
                ids.append(d.id)
        qs = qs.filter(id__in=ids)
    do_ano = qs.filter(ano_letivo=str(ano))
    return (do_ano if do_ano.exists() else qs).order_by('nome')


def _chave_nome_disciplina(nome):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKD', str(nome or '')).encode('ascii', 'ignore').decode('ascii')).strip().lower()


def _disciplinas_unicas_do_aluno(user, ano):
    """Uma entrada por nome de disciplina (a da área própria prevalece sobre a geral); devolve [(disc, [ids])]."""
    grupos = {}
    for d in _disciplinas_do_aluno(user, ano):
        grupos.setdefault(_chave_nome_disciplina(d.nome), []).append(d)
    resultado = []
    for lista in grupos.values():
        lista.sort(key=lambda d: (d.area or '').strip().lower() in _AREAS_COMUNS)
        resultado.append((lista[0], [d.id for d in lista]))
    return sorted(resultado, key=lambda x: _chave_nome_disciplina(x[0].nome))


def _restringir_ao_aluno(request, qs):
    """Aluno: só material da disciplina escolhida, dentro das disciplinas da sua classe e área."""
    if getattr(request.user, 'role', '') != 'ALUNO':
        return qs
    ano = request.query_params.get('ano')
    disc_id = request.query_params.get('disciplina_id')
    if not disc_id:
        return qs.none()
    for _, ids in _disciplinas_unicas_do_aluno(request.user, ano):
        if any(str(i) == str(disc_id) for i in ids):
            return qs.filter(disciplina_id__in=ids)
    return qs.none()


class MaterialEscolarViewSet(viewsets.ModelViewSet):
    serializer_class = MaterialEscolarSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        escola = get_tenant_escola_from_request(self.request)

        # Regra Inquebrável de Isolamento Multi-Escola:
        # As publicações feitas numa escola NUNCA reflectem noutras escolas.
        # Se a escola não estiver identificada, retorna vazio (.none()) impedindo vazamento entre escolas.
        if escola:
            qs = MaterialEscolar.objects.filter(escola=escola)
        else:
            qs = MaterialEscolar.objects.none()

        qs = _restringir_ao_aluno(self.request, qs)

        classe = self.request.query_params.get('classe')
        if classe:
            qs = qs.filter(classe=classe)

        disciplina_id = self.request.query_params.get('disciplina_id')
        if disciplina_id and getattr(self.request.user, 'role', '') != 'ALUNO':
            qs = qs.filter(disciplina_id=disciplina_id)

        tipo = self.request.query_params.get('tipo')
        if tipo:
            qs = qs.filter(tipo=tipo)

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(Q(titulo__icontains=search) | Q(descricao__icontains=search))

        qs = qs.defer('conteudo_base64')

        return qs.select_related('disciplina', 'escola').order_by('-created_at')

    def perform_create(self, serializer):
        user = getattr(self.request, 'user', None)
        escola = get_tenant_escola_from_request(self.request)

        # Validação cruzada de integridade: a disciplina deve pertencer à mesma escola
        disc = serializer.validated_data.get('disciplina')
        if disc and getattr(disc, 'escola', None):
            if escola and disc.escola_id != escola.id:
                raise serializers.ValidationError({
                    'disciplina_id': 'A disciplina selecionada pertence a uma instituição de ensino diferente da escola ativa.'
                })
            if not escola:
                escola = disc.escola

        if not escola:
            raise serializers.ValidationError({
                'detail': 'Instituição de ensino não identificada. Não é possível publicar material escolar sem vincular à escola.'
            })

        publicador = getattr(user, 'nome', None) or getattr(user, 'username', 'Administração')
        serializer.save(escola=escola, publicado_por=publicador)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return Response({'success': True, 'data': MaterialEscolarSerializer(qs, many=True).data})

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
        return Response({'success': True, 'message': 'Material excluído com sucesso.'})

    @action(detail=True, methods=['get'], url_path='download', permission_classes=[IsAuthenticated])
    def download(self, request, pk=None):
        # get_object() aplica o filtro por escola de get_queryset(): material de outra escola dá 404.
        material = self.get_object()
        from django.db.models.functions import Length, Substr
        b64_chunks = []
        total_len = (
            MaterialEscolar.objects.filter(id=material.id)
            .annotate(blen=Length('conteudo_base64'))
            .values_list('blen', flat=True)
            .first()
        ) or 0
        if total_len > 0:
            chunk_size = 4_000_000
            offset = 1
            while offset <= total_len:
                part = (
                    MaterialEscolar.objects.filter(id=material.id)
                    .annotate(chunk=Substr('conteudo_base64', offset, chunk_size))
                    .values_list('chunk', flat=True)
                    .first()
                )
                if part:
                    b64_chunks.append(part)
                offset += chunk_size

        if b64_chunks:
            b64_str = "".join(b64_chunks)
            if ',' in b64_str[:128]:
                b64_str = b64_str.split(',', 1)[1]
            try:
                file_bytes = base64.b64decode(b64_str)
                fname = _safe_ascii_filename(material.nome_arquivo or 'material.pdf')
                response = HttpResponse(file_bytes, content_type=material.tipo_mime or 'application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename="{fname}"'
                return response
            except Exception:
                pass

        # Fallback oficial: gerar documento PDF com a ficha/conteúdo do material escolar
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm)
        styles = getSampleStyleSheet()
        s_tit = ParagraphStyle('MTit', parent=styles['Normal'], fontName='Times-Bold', fontSize=12, leading=18, alignment=1)
        s_sub = ParagraphStyle('MSub', parent=styles['Normal'], fontName='Times-Bold', fontSize=12, leading=18, alignment=1)
        s_body = ParagraphStyle('MBody', parent=styles['Normal'], fontName='Times-Roman', fontSize=12, leading=18)

        escola_nome = material.escola.nome if material.escola else 'SIGE — Repositório Escolar'
        disc_nome = material.disciplina.nome if material.disciplina else 'Geral'
        elems = [
            Paragraph("REPÚBLICA DE MOÇAMBIQUE — MINISTÉRIO DA EDUCAÇÃO E CULTURA", s_sub),
            Paragraph(escola_nome.upper(), s_sub),
            Spacer(1, 0.6 * cm),
            Paragraph(material.titulo.upper(), s_tit),
            Spacer(1, 0.5 * cm),
            Paragraph(f"<b>Classe:</b> {material.classe} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Disciplina:</b> {disc_nome} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Tipo:</b> {material.tipo}", s_body),
            Paragraph(f"<b>Publicado por:</b> {material.publicado_por or 'Administração'}", s_body),
            Spacer(1, 0.5 * cm),
            Paragraph(f"<b>Descrição / Conteúdo Didáctico:</b><br/>{material.descricao or 'Material didáctico oficial disponibilizado na biblioteca digital da escola.'}", s_body),
        ]
        if material.arquivo_url:
            elems.append(Spacer(1, 0.4 * cm))
            elems.append(Paragraph(f"<b>Endereço / Recurso Externo:</b> {material.arquivo_url}", s_body))

        doc.build(elems)
        buffer.seek(0)
        raw_pdf = material.nome_arquivo if str(material.nome_arquivo).lower().endswith('.pdf') else f"{material.nome_arquivo or 'material'}.pdf"
        nome_pdf = _safe_ascii_filename(raw_pdf)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{nome_pdf}"'
        return response

class DisciplinasAlunoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request.user, 'role', '') != 'ALUNO':
            return Response({'success': True, 'data': []})
        ano = request.query_params.get('ano')
        dados = [{'id': str(d.id), 'nome': d.nome} for d, _ in _disciplinas_unicas_do_aluno(request.user, ano)]
        return Response({'success': True, 'data': dados})


class ClassesMaterialView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        escola = get_tenant_escola_from_request(request)
        if escola:
            qs = MaterialEscolar.objects.filter(escola=escola)
        else:
            qs = MaterialEscolar.objects.none()

        qs = _restringir_ao_aluno(request, qs)
        contagens = dict(qs.values_list('classe').annotate(total=Count('id')))
        dados = [
            {'classe': c, 'totalMateriais': contagens.get(c, 0)}
            for c in CLASSES_MOCAMBIQUE
        ]
        if getattr(request.user, 'role', '') == 'ALUNO':
            # O aluno só vê as classes reais em que esteve matriculado
            dados = [d for d in dados if d['classe'] in _classes_reais_do_aluno(request.user)]
        return Response({'success': True, 'data': dados})

