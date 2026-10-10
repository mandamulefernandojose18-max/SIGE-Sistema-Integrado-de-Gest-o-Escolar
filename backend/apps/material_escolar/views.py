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

CLASSES_MOCAMBIQUE = [
    '1ª Classe', '2ª Classe', '3ª Classe', '4ª Classe', '5ª Classe',
    '6ª Classe', '7ª Classe', '8ª Classe', '9ª Classe', '10ª Classe',
    '11ª Classe', '12ª Classe'
]

class MaterialEscolarViewSet(viewsets.ModelViewSet):
    serializer_class = MaterialEscolarSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if getattr(self, 'action', None) in ['download', 'list', 'retrieve']:
            return [AllowAny()]
        return super().get_permissions()

    def get_queryset(self):
        escola = getattr(self.request, 'tenant', None) or getattr(getattr(self.request, 'user', None), 'escola', None)
        is_super = getattr(getattr(self.request, 'user', None), 'role', '') == 'SUPERADMIN'

        if is_super or not escola or self.action in ['retrieve', 'update', 'partial_update', 'destroy', 'download']:
            qs = MaterialEscolar.objects.all()
        else:
            qs = MaterialEscolar.objects.filter(escola=escola)

        classe = self.request.query_params.get('classe')
        if classe:
            qs = qs.filter(classe=classe)

        disciplina_id = self.request.query_params.get('disciplina_id')
        if disciplina_id:
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
        escola = getattr(self.request, 'tenant', None) or getattr(self.request.user, 'escola', None)
        disc = serializer.validated_data.get('disciplina')
        if disc and getattr(disc, 'escola', None):
            escola = disc.escola
        if not escola:
            escola = Escola.objects.filter(status='ATIVA').first() or Escola.objects.first()
        publicado = getattr(self.request.user, 'nome', None) or 'Administração'
        serializer.save(escola=escola, publicado_por=publicado)

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

    @action(detail=True, methods=['get'], url_path='download', permission_classes=[AllowAny])
    def download(self, request, pk=None):
        material = MaterialEscolar.objects.defer('conteudo_base64').select_related('escola', 'disciplina').filter(id=pk).first()
        if not material:
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
        s_tit = ParagraphStyle('MTit', parent=styles['Normal'], fontName='Times-Bold', fontSize=14, leading=18, alignment=1)
        s_sub = ParagraphStyle('MSub', parent=styles['Normal'], fontName='Times-Bold', fontSize=11, leading=15, alignment=1)
        s_body = ParagraphStyle('MBody', parent=styles['Normal'], fontName='Times-Roman', fontSize=11, leading=16)

        escola_nome = material.escola.nome if material.escola else 'SIGE — Repositório Escolar'
        disc_nome = material.disciplina.nome if material.disciplina else 'Geral'
        elems = [
            Paragraph("REPÚBLICA DE MOÇAMBIQUE — MINISTÉRIO DA EDUCAÇÃO E DESENVOLVIMENTO HUMANO", s_sub),
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

class ClassesMaterialView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        escola = getattr(request, 'tenant', None) or getattr(request.user, 'escola', None)
        is_super = getattr(request.user, 'role', '') == 'SUPERADMIN'
        if escola and not is_super:
            qs = MaterialEscolar.objects.filter(escola=escola)
        else:
            qs = MaterialEscolar.objects.all()

        contagens = dict(qs.values_list('classe').annotate(total=Count('id')))
        dados = [
            {'classe': c, 'totalMateriais': contagens.get(c, 0)}
            for c in CLASSES_MOCAMBIQUE
        ]
        return Response({'success': True, 'data': dados})

