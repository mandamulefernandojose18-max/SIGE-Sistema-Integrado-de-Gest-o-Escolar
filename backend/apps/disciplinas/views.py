from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Disciplina
from .serializers import DisciplinaSerializer

class DisciplinaViewSet(viewsets.ModelViewSet):
    serializer_class = DisciplinaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from common.utils.tenant import get_tenant_escola
        escola = get_tenant_escola(self.request)

        if escola:
            qs = Disciplina.objects.filter(escola=escola)
        else:
            qs = Disciplina.objects.none()

        classe = self.request.query_params.get('classe')
        if classe:
            from django.db.models import Q
            c_clean = classe.strip()
            c_alt = c_clean.replace('ª', 'a') if 'ª' in c_clean else c_clean.replace('a', 'ª')
            qs = qs.filter(Q(classe__iexact=c_clean) | Q(classe__iexact=c_alt))

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
        from common.utils.tenant import get_tenant_escola
        from rest_framework import serializers as drf_serializers
        escola = get_tenant_escola(self.request)
        if not escola:
            raise drf_serializers.ValidationError({
                'escola': 'Nenhuma escola seleccionada. Por favor, seleccione uma escola no topo antes de cadastrar a disciplina.'
            })
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

    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)
        return Response({'success': True, 'data': response.data})

    @action(detail=True, methods=['post', 'patch'], url_path='toggle-exame')
    def toggle_exame(self, request, pk=None):
        disciplina = self.get_object()
        tem_exame = request.data.get('tem_exame')
        if tem_exame is None:
            disciplina.tem_exame = not disciplina.tem_exame
        else:
            disciplina.tem_exame = bool(tem_exame)
        disciplina.save(update_fields=['tem_exame', 'updated_at'])
        return Response({
            'success': True,
            'data': DisciplinaSerializer(disciplina).data,
            'message': f"Regime de exame de '{disciplina.nome}' atualizado para: {'Com Exame (Sim)' if disciplina.tem_exame else 'Sem Exame (Não)'}."
        })

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return Response({'success': True, 'message': 'Disciplina excluída com sucesso.'})

class DisciplinaStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from common.utils.tenant import get_tenant_escola
        escola = get_tenant_escola(request)
        total = Disciplina.objects.filter(escola=escola).count() if escola else 0
        return Response({'success': True, 'data': {'totalDisciplinas': total}})
