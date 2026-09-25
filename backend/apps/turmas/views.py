from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Turma
from .serializers import TurmaSerializer
from common.permissions.rbac import IsEscolaAdmin

class TurmaViewSet(viewsets.ModelViewSet):
    serializer_class = TurmaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        escola = self.request.tenant or self.request.user.escola
        qs = Turma.objects.filter(escola=escola)
        ano = self.request.query_params.get('ano_letivo')
        if ano:
            qs = qs.filter(ano_letivo=ano)
        return qs.order_by('nome')

    def perform_create(self, serializer):
        escola = self.request.tenant or self.request.user.escola
        serializer.save(escola=escola)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return Response({'success': True, 'data': TurmaSerializer(qs, many=True).data})

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
        return Response({'success': True, 'message': 'Turma excluída com sucesso.'})
