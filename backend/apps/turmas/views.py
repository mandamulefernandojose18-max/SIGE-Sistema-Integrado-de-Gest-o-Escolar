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
        escola = self.request.tenant or getattr(self.request.user, 'escola', None)
        if not escola and getattr(self.request.user, 'role', '') == 'SUPERADMIN':
            qs = Turma.objects.all()
        elif escola:
            qs = Turma.objects.filter(escola=escola)
        else:
            qs = Turma.objects.none()

        ano = self.request.query_params.get('ano_letivo')
        if ano:
            qs = qs.filter(ano_letivo=ano)
        return qs.order_by('nome')

    def perform_create(self, serializer):
        escola = self.request.tenant or getattr(self.request.user, 'escola', None)
        if not escola and getattr(self.request.user, 'role', '') == 'SUPERADMIN':
            escola_id = (
                self.request.data.get('escola_id') or
                self.request.data.get('escola') or
                self.request.headers.get('X-Tenant-ID')
            )
            if escola_id:
                from apps.tenants.models import Escola
                escola = Escola.objects.filter(id=escola_id).first()
            if not escola:
                from apps.tenants.models import Escola
                escola = Escola.objects.filter(status='ATIVA').first() or Escola.objects.first()

        if not escola:
            from rest_framework import serializers as drf_serializers
            raise drf_serializers.ValidationError({
                'escola': 'Nenhuma escola seleccionada. Por favor, seleccione uma escola no topo antes de criar a turma.'
            })

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
        kwargs['partial'] = True
        response = super().update(request, *args, **kwargs)
        return Response({'success': True, 'data': response.data})

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return Response({'success': True, 'message': 'Turma excluída com sucesso.'})
