import base64
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.db.models import Q

from .models import MaterialEscolar
from .serializers import MaterialEscolarSerializer

CLASSES_MOCAMBIQUE = [
    '1ª Classe', '2ª Classe', '3ª Classe', '4ª Classe', '5ª Classe',
    '6ª Classe', '7ª Classe', '8ª Classe', '9ª Classe', '10ª Classe',
    '11ª Classe', '12ª Classe'
]

class MaterialEscolarViewSet(viewsets.ModelViewSet):
    serializer_class = MaterialEscolarSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        escola = self.request.tenant or self.request.user.escola
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

        return qs.select_related('disciplina').order_by('-created_at')

    def perform_create(self, serializer):
        escola = self.request.tenant or self.request.user.escola
        publicado = self.request.user.nome if self.request.user else 'Administração'
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

    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, pk=None):
        material = self.get_object()
        if material.conteudo_base64:
            b64_str = material.conteudo_base64
            if ',' in b64_str:
                b64_str = b64_str.split(',', 1)[1]
            try:
                file_bytes = base64.b64decode(b64_str)
                response = HttpResponse(file_bytes, content_type=material.tipo_mime or 'application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename="{material.nome_arquivo}"'
                return response
            except Exception:
                pass
        return Response({'success': False, 'message': 'Arquivo não disponível para download direto.'}, status=status.HTTP_404_NOT_FOUND)

class ClassesMaterialView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'success': True, 'data': CLASSES_MOCAMBIQUE})
