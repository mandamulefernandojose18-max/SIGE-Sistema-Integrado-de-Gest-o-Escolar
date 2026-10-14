from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Disciplina
from .serializers import DisciplinaSerializer

class DisciplinaViewSet(viewsets.ModelViewSet):
    serializer_class = DisciplinaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        escola = getattr(self.request, 'tenant', None) or getattr(self.request.user, 'escola', None)
        if not escola and getattr(self.request.user, 'role', '') == 'SUPERADMIN':
            escola_id = self.request.query_params.get('escola_id') or self.request.headers.get('X-Tenant-ID')
            if escola_id:
                from apps.tenants.models import Escola
                escola = Escola.objects.filter(id=escola_id).first()

        if escola:
            qs = Disciplina.objects.filter(escola=escola)
        elif getattr(self.request.user, 'role', '') == 'SUPERADMIN':
            qs = Disciplina.objects.all()
        else:
            qs = Disciplina.objects.none()

        classe = self.request.query_params.get('classe')
        if classe:
            import re
            m = re.search(r'\d+', classe)
            if m:
                qs = qs.filter(classe__icontains=m.group(0))
            else:
                qs = qs.filter(classe__iexact=classe)

        area = self.request.query_params.get('area')
        if area:
            from django.db.models import Q
            a_clean = area.strip()
            if 'geral' in a_clean.lower():
                qs = qs.filter(Q(area__icontains='geral') | Q(area__isnull=True) | Q(area=''))
            else:
                qs = qs.filter(area__icontains=a_clean)

        busca = self.request.query_params.get('search') or self.request.query_params.get('q')
        if busca:
            from django.db.models import Q
            b = busca.strip()
            qs = qs.filter(Q(nome__icontains=b) | Q(codigo__icontains=b))

        return qs.order_by('nome')

    def perform_create(self, serializer):
        escola = self.request.tenant or self.request.user.escola
        serializer.save(escola=escola)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return Response({'success': True, 'data': DisciplinaSerializer(qs, many=True).data})

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
        return Response({'success': True, 'message': 'Disciplina excluída com sucesso.'})

class DisciplinaStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        escola = getattr(request, 'tenant', None) or getattr(request.user, 'escola', None)
        if not escola:
            from apps.tenants.models import Escola
            escola = Escola.objects.filter(status='ATIVA').first() or Escola.objects.first()
        total = Disciplina.objects.filter(escola=escola).count() if escola else 0
        return Response({'success': True, 'data': {'totalDisciplinas': total}})
