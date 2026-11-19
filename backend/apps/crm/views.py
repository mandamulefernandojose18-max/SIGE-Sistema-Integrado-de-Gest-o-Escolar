from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.alunos.models import Aluno, PresencaAluno
from apps.pagamentos.models import Pagamento
from common.permissions.rbac import IsEscolaAdmin
from common.utils.tenant import get_tenant_escola
from .models import Atendimento, Comunicacao, VinculoEncarregado
from .serializers import AtendimentoSerializer, ComunicacaoSerializer, VinculoEncarregadoSerializer

LIMITE_MAX = 200


class AtendimentoViewSet(viewsets.ModelViewSet):
    serializer_class = AtendimentoSerializer
    permission_classes = [IsEscolaAdmin]

    def get_queryset(self):
        escola = get_tenant_escola(self.request)
        if not escola:
            return Atendimento.objects.none()
        qs = Atendimento.objects.filter(escola=escola).select_related('aluno')
        p = self.request.query_params
        for campo, filtro in (('estado', 'estado'), ('prioridade', 'prioridade'), ('aluno_id', 'aluno_id'),
                              ('responsavel_id', 'responsavel_id')):
            if p.get(campo):
                qs = qs.filter(**{filtro: p[campo]})
        return qs

    def perform_create(self, serializer):
        escola = get_tenant_escola(self.request)
        if not escola:
            raise ValidationError({'escola': 'Nenhuma escola identificada.'})
        serializer.save(escola=escola, criado_por=self.request.user)

    @action(detail=True, methods=['post'])
    def resolver(self, request, pk=None):
        at = self.get_object()
        resolucao = (request.data.get('resolucao') or '').strip()
        if at.estado == 'RESOLVIDO':
            raise ValidationError({'estado': 'Atendimento já resolvido.'})
        if not resolucao:
            raise ValidationError({'resolucao': 'Indique a resolução.'})
        at.estado, at.resolucao, at.resolvido_em = 'RESOLVIDO', resolucao, timezone.now()
        at.save()
        return Response(self.get_serializer(at).data)


class ComunicacaoViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                         viewsets.GenericViewSet):
    serializer_class = ComunicacaoSerializer
    permission_classes = [IsEscolaAdmin]

    def get_queryset(self):
        escola = get_tenant_escola(self.request)
        if not escola:
            return Comunicacao.objects.none()
        qs = Comunicacao.objects.filter(escola=escola).select_related('aluno')
        p = self.request.query_params
        if p.get('aluno_id'):
            qs = qs.filter(aluno_id=p['aluno_id'])
        if p.get('tipo'):
            qs = qs.filter(tipo=p['tipo'])
        return qs

    def perform_create(self, serializer):
        escola = get_tenant_escola(self.request)
        if not escola:
            raise ValidationError({'escola': 'Nenhuma escola identificada.'})
        aluno = serializer.validated_data['aluno']
        destinatario = serializer.validated_data.get('destinatario') or aluno.nome_responsavel or ''
        serializer.save(escola=escola, registado_por=self.request.user, destinatario=destinatario)


class VinculoEncarregadoViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Associa contas de Encarregado de Educação aos seus educandos (gestão da escola)."""
    serializer_class = VinculoEncarregadoSerializer
    permission_classes = [IsEscolaAdmin]

    def get_queryset(self):
        escola = get_tenant_escola(self.request)
        if not escola:
            return VinculoEncarregado.objects.none()
        qs = VinculoEncarregado.objects.filter(escola=escola).select_related('usuario', 'aluno')
        if self.request.query_params.get('aluno_id'):
            qs = qs.filter(aluno_id=self.request.query_params['aluno_id'])
        return qs

    def perform_create(self, serializer):
        escola = get_tenant_escola(self.request)
        if not escola:
            raise ValidationError({'escola': 'Nenhuma escola identificada.'})
        serializer.save(escola=escola, criado_por=self.request.user)


def _faltas_efectivas_por_aluno(escola, ano_letivo=None, turma_id=None, aluno_id=None):
    qs = PresencaAluno.objects.filter(escola=escola, status__in=('FALTA_JUSTIFICADA', 'FALTA_INJUSTIFICADA'))
    if ano_letivo:
        qs = qs.filter(turma__ano_letivo=ano_letivo)
    if turma_id:
        qs = qs.filter(turma_id=turma_id)
    if aluno_id:
        qs = qs.filter(aluno_id=aluno_id)
    linhas = qs.values('aluno_id').annotate(brutas=Sum('aulas'), just=Sum('aulas_justificadas'))
    return {l['aluno_id']: max((l['brutas'] or 0) - (l['just'] or 0), 0) for l in linhas}


def _propinas_em_atraso(escola, aluno_ids=None):
    qs = Pagamento.objects.filter(escola=escola, status__in=('PENDENTE', 'ATRASADO'),
                                  data_vencimento__lt=timezone.now())
    if aluno_ids is not None:
        qs = qs.filter(aluno_id__in=aluno_ids)
    return qs


class Encarregado360View(APIView):
    """Ficha 360º do educando e do seu encarregado: faltas, propinas, contactos e atendimentos reais."""
    permission_classes = [IsEscolaAdmin]

    def get(self, request, aluno_id):
        escola = get_tenant_escola(request)
        if not escola:
            raise ValidationError({'escola': 'Nenhuma escola identificada.'})
        aluno = get_object_or_404(Aluno.objects.select_related('turma'), id=aluno_id, escola=escola)
        faltas = _faltas_efectivas_por_aluno(escola, aluno_id=aluno.id).get(aluno.id, 0)
        atraso = _propinas_em_atraso(escola, [aluno.id])
        return Response({
            'aluno': {'id': str(aluno.id), 'nome': aluno.nome, 'matricula': aluno.matricula, 'classe': aluno.classe,
                      'turma': aluno.turma.nome if aluno.turma else None, 'status': aluno.status},
            'encarregado': {'nome': aluno.nome_responsavel, 'contacto': aluno.contato_responsavel,
                            'email': aluno.email_responsavel, 'pai': aluno.pai, 'mae': aluno.mae},
            'faltas_efectivas': faltas,
            'propinas_em_atraso': {'quantidade': atraso.count(),
                                   'valor': str(sum((p.valor - p.valor_pago for p in atraso), 0))},
            'atendimentos_abertos': Atendimento.objects.filter(escola=escola, aluno=aluno).exclude(estado='RESOLVIDO').count(),
            'contas_encarregado': [{'id': str(v.id), 'email': v.usuario.email}
                                   for v in VinculoEncarregado.objects.filter(escola=escola, aluno=aluno).select_related('usuario')],
            'comunicacoes_recentes': ComunicacaoSerializer(
                Comunicacao.objects.filter(escola=escola, aluno=aluno).select_related('aluno')[:10], many=True).data,
        })


class AlertasEvasaoView(APIView):
    """Alunos activos com faltas efectivas ou propinas em atraso acima dos limites (filtros em cascata, paginado)."""
    permission_classes = [IsEscolaAdmin]

    def get(self, request):
        escola = get_tenant_escola(request)
        if not escola:
            return Response({'total': 0, 'resultados': []})
        p = request.query_params
        try:
            min_faltas = max(int(p.get('min_faltas', 10)), 0)
            min_atrasos = max(int(p.get('min_propinas_atraso', 2)), 0)
            limite = min(max(int(p.get('limite', 50)), 1), LIMITE_MAX)
            offset = max(int(p.get('offset', 0)), 0)
        except ValueError:
            raise ValidationError('Parâmetros numéricos inválidos.')
        ano = p.get('ano_letivo') or getattr(escola, 'ano_letivo_ativo', None)

        alunos = Aluno.objects.filter(escola=escola, status='ATIVO')
        if p.get('classe'):
            alunos = alunos.filter(classe=p['classe'])
        if p.get('turma_id'):
            alunos = alunos.filter(turma_id=p['turma_id'])
        ids = list(alunos.values_list('id', flat=True))

        faltas = _faltas_efectivas_por_aluno(escola, ano_letivo=ano, turma_id=p.get('turma_id'))
        atrasos = {}
        for pg in _propinas_em_atraso(escola, ids):
            atrasos[pg.aluno_id] = atrasos.get(pg.aluno_id, 0) + 1

        sinalizados = []
        for a in alunos.select_related('turma').order_by('nome'):
            f, n = faltas.get(a.id, 0), atrasos.get(a.id, 0)
            motivos = []
            if min_faltas and f >= min_faltas:
                motivos.append('FALTAS')
            if min_atrasos and n >= min_atrasos:
                motivos.append('PROPINAS')
            if motivos:
                sinalizados.append({'aluno_id': str(a.id), 'nome': a.nome, 'matricula': a.matricula, 'classe': a.classe,
                                    'turma': a.turma.nome if a.turma else None, 'faltas_efectivas': f,
                                    'propinas_em_atraso': n, 'motivos': motivos})
        return Response({'total': len(sinalizados), 'ano_letivo': ano,
                         'resultados': sinalizados[offset:offset + limite]})
