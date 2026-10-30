from rest_framework import permissions
import uuid
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum, Count
from django.shortcuts import get_object_or_404

from .models import Pagamento, PlanoPagamentoEscola
from .serializers import (
    PagamentoSerializer,
    LiquidarPagamentoSerializer,
    GerarPagamentosTurmaSerializer,
    PlanoPagamentoEscolaSerializer
)
from apps.alunos.models import Aluno
from apps.turmas.models import Turma
from common.permissions.rbac import IsEscolaAdmin


class PlanoPagamentoEscolaViewSet(viewsets.ModelViewSet):
    """
    Gestão de Planos de Pagamento e Tabelas de Propinas Próprias de cada Escola.
    Garante isolamento absoluto:
    - Cada escola cria, altera e aplica os seus próprios planos aos seus alunos.
    - O plano do Super Admin é estritamente B2B (Super Admin -> Instituição) e não reflete para os usuários da escola.
    - Nada do que uma escola configura reflecte ou compromete outra escola.
    """
    serializer_class = PlanoPagamentoEscolaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from common.utils.tenant import get_tenant_escola
        escola = get_tenant_escola(self.request)
        if not escola:
            return PlanoPagamentoEscola.objects.none()
        qs = PlanoPagamentoEscola.objects.filter(escola=escola)

        ativo = self.request.query_params.get('ativo')
        if ativo is not None:
            qs = qs.filter(ativo=str(ativo).lower() in ['true', '1'])

        periodicidade = self.request.query_params.get('periodicidade')
        if periodicidade:
            qs = qs.filter(periodicidade=periodicidade)

        busca = self.request.query_params.get('busca') or self.request.query_params.get('q')
        if busca:
            qs = qs.filter(nome__icontains=busca)

        return qs.order_by('nome')

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        serializer = self.get_serializer(qs, many=True)
        return Response({'success': True, 'data': serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({'success': True, 'data': serializer.data}, status=status.HTTP_201_CREATED)

    def _verificar_permissao_gestao(self, request):
        from rest_framework.exceptions import PermissionDenied
        role = getattr(request.user, 'role', '')
        if role not in ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'CHEFE_SECRETARIA', 'FINANCEIRO']:
            raise PermissionDenied('Apenas a direcção e gestão financeira da instituição podem gerir os planos de pagamento da escola.')

    def perform_create(self, serializer):
        from common.utils.tenant import get_tenant_escola
        from rest_framework import serializers as drf_serializers
        self._verificar_permissao_gestao(self.request)
        escola = get_tenant_escola(self.request)
        if not escola:
            raise drf_serializers.ValidationError({'escola': 'Nenhuma escola identificada para registar o plano.'})
        serializer.save(escola=escola)

    def perform_update(self, serializer):
        self._verificar_permissao_gestao(self.request)
        serializer.save()

    def perform_destroy(self, instance):
        self._verificar_permissao_gestao(self.request)
        if instance.pagamentos.exists():
            instance.ativo = False
            instance.save()
        else:
            instance.delete()


class PagamentoViewSet(viewsets.ModelViewSet):
    serializer_class = PagamentoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from common.utils.tenant import get_tenant_escola
        escola = get_tenant_escola(self.request)
        if escola:
            qs = Pagamento.objects.filter(escola=escola)
            if getattr(self.request.user, 'role', '') == 'ALUNO':
                target_aluno_id = getattr(self.request.user, 'aluno_id', None)
                qs = qs.filter(aluno_id=target_aluno_id) if target_aluno_id else qs.none()
        else:
            qs = Pagamento.objects.none()

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        mes = self.request.query_params.get('mes') or self.request.query_params.get('mes_referencia')
        if mes:
            qs = qs.filter(mes_referencia=mes)

        aluno_id = self.request.query_params.get('aluno_id') or self.request.query_params.get('alunoId')
        if aluno_id:
            qs = qs.filter(aluno_id=aluno_id)

        ano_param = self.request.query_params.get('ano_letivo') or self.request.query_params.get('ano')
        if ano_param and str(ano_param).upper() != 'TODOS':
            from django.db.models import Q
            try:
                ano_int = int(ano_param)
                qs = qs.filter(Q(aluno__turma__ano_letivo=ano_param) | Q(aluno__ano_ingresso=ano_param) | Q(data_vencimento__year=ano_int))
            except ValueError:
                qs = qs.filter(Q(aluno__turma__ano_letivo=ano_param) | Q(aluno__ano_ingresso=ano_param))

        return qs.select_related('aluno', 'aluno__turma', 'escola').order_by('-data_vencimento')

    def perform_create(self, serializer):
        from common.utils.tenant import get_tenant_escola
        from rest_framework import serializers as drf_serializers
        aluno = serializer.validated_data.get('aluno')
        mes_referencia = serializer.validated_data.get('mes_referencia')
        escola = get_tenant_escola(self.request) or (getattr(aluno, 'escola', None) if aluno else None)
        if not escola:
            raise drf_serializers.ValidationError({'escola': 'Nenhuma escola identificada para registar o pagamento.'})
        if aluno and aluno.escola_id != escola.id:
            raise drf_serializers.ValidationError({'aluno': 'O aluno selecionado pertence a outra instituição de ensino.'})

        plano = serializer.validated_data.get('plano_pagamento')
        if plano and plano.escola_id != escola.id:
            raise drf_serializers.ValidationError({'plano_pagamento': 'O plano de pagamento pertence a outra instituição de ensino.'})

        # Evita duplicação de faturas do mesmo mês
        if aluno and mes_referencia:
            ja_existe = Pagamento.objects.filter(
                escola=escola,
                aluno=aluno,
                mes_referencia=mes_referencia
            ).exclude(status='CANCELADO').exists()
            if ja_existe:
                raise drf_serializers.ValidationError({'mes_referencia': 'A factura já foi gerada no sistema.'})

        serializer.save(escola=escola)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            erros = serializer.errors
            msg = 'Erro ao processar factura.'
            if any('já foi gerada' in str(v).lower() for v in erros.values()):
                msg = 'A factura já foi gerada no sistema.'
            elif isinstance(erros, dict):
                first_val = next(iter(erros.values()))
                if isinstance(first_val, list) and first_val:
                    msg = str(first_val[0])
                elif isinstance(first_val, str):
                    msg = first_val
            return Response({'success': False, 'message': msg, 'errors': erros}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_create(serializer)
        except Exception as e:
            msg = str(e)
            if 'já foi gerada' in msg.lower():
                msg = 'A factura já foi gerada no sistema.'
            return Response({'success': False, 'message': msg}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'success': True, 'data': serializer.data}, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return Response({'success': True, 'data': PagamentoSerializer(qs, many=True).data})

    @action(detail=True, methods=['post'], url_path='liquidar')
    def liquidar(self, request, pk=None):
        pagamento = self.get_object()

        # Restrição de segurança: Se for aluno, só pode liquidar a sua própria propina
        if getattr(request.user, 'role', '') == 'ALUNO':
            aluno_id = getattr(request.user, 'aluno_id', None)
            if not aluno_id or str(pagamento.aluno_id) != str(aluno_id):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('Apenas o próprio aluno ou a direcção da escola podem liquidar esta propina.')

        serializer = LiquidarPagamentoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        valor_pago = serializer.validated_data.get('valor_pago') or pagamento.valor
        metodo_raw = serializer.validated_data.get('metodo_pagamento', 'MPESA')
        telefone = serializer.validated_data.get('telefone', '').strip()
        referencia = serializer.validated_data.get('referencia', '').strip()

        # Normalização canónica de método para o sistema e telecomunicações de Moçambique
        metodo_upper = str(metodo_raw).upper().replace(' ', '').replace('-', '')
        if 'MPESA' in metodo_upper:
            metodo_oficial = 'MPESA'
            nome_metodo = 'M-Pesa (Vodacom)'
        elif 'EMOLA' in metodo_upper:
            metodo_oficial = 'EMOLA'
            nome_metodo = 'e-Mola (Movitel)'
        elif 'POS' in metodo_upper or 'CARTAO' in metodo_upper:
            metodo_oficial = 'POS'
            nome_metodo = 'POS / Cartão Bancário'
        elif 'TRANSFERENCIA' in metodo_upper or 'BANCO' in metodo_upper:
            metodo_oficial = 'TRANSFERENCIA'
            nome_metodo = 'Transferência Bancária'
        else:
            metodo_oficial = 'NUMERARIO'
            nome_metodo = 'Numerário'

        pagamento.valor_pago = valor_pago
        pagamento.status = 'PAGO'
        pagamento.data_pagamento = timezone.now().date()
        pagamento.metodo_pagamento = metodo_oficial
        if not pagamento.recibo_numero:
            ano = timezone.now().year
            num_seq = Pagamento.objects.filter(escola=pagamento.escola, status='PAGO').count() + 1
            pagamento.recibo_numero = f"REC-{ano}-{num_seq:05d}"
        pagamento.save()

        msg_detalhes = f"Pagamento de saldo liquidado com sucesso via {nome_metodo}."
        if referencia:
            msg_detalhes += f" Ref: {referencia}."

        return Response({
            'success': True,
            'message': f"{msg_detalhes} Recibo Oficial: {pagamento.recibo_numero}",
            'data': PagamentoSerializer(pagamento).data,
            'recibo_numero': pagamento.recibo_numero,
            'metodo_pagamento': metodo_oficial,
            'metodo_nome': nome_metodo,
            'telefone': telefone,
            'referencia': referencia
        })

    @action(detail=False, methods=['post'], url_path='gerar-turma')
    def gerar_turma(self, request):
        serializer = GerarPagamentosTurmaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        escola = getattr(request, 'tenant', None) or getattr(request.user, 'escola', None)
        is_super = getattr(request.user, 'role', '') == 'SUPERADMIN'
        if escola and not is_super:
            turma = get_object_or_404(Turma, id=data['turma_id'], escola=escola)
        else:
            turma = get_object_or_404(Turma, id=data['turma_id'])
            escola = turma.escola or escola
        alunos = Aluno.objects.filter(turma=turma, status='ATIVO')
        plano_id = data.get('plano_id')
        plano = None
        if plano_id:
            plano = get_object_or_404(PlanoPagamentoEscola, id=plano_id, escola=escola)

        criados = 0
        ja_existentes = 0
        for aluno in alunos:
            # Impede duplicação de facturas do mesmo mês para o aluno
            ja_tem = Pagamento.objects.filter(
                escola=escola,
                aluno=aluno,
                mes_referencia=data['mes_referencia']
            ).exclude(status='CANCELADO').exists()

            if ja_tem:
                ja_existentes += 1
                continue

            Pagamento.objects.create(
                escola=escola,
                aluno=aluno,
                plano_pagamento=plano,
                descricao=data['descricao'],
                mes_referencia=data['mes_referencia'],
                valor=data['valor'],
                data_vencimento=data['data_vencimento'],
                status='PENDENTE'
            )
            criados += 1

        if criados == 0 and ja_existentes > 0:
            return Response({
                'success': False,
                'message': 'A factura já foi gerada no sistema.',
                'totalGerados': 0,
                'totalExistentes': ja_existentes
            }, status=status.HTTP_400_BAD_REQUEST)

        msg = f"Gerados {criados} pagamentos para os alunos da turma {turma.nome}."
        if ja_existentes > 0:
            msg += f" ({ja_existentes} já haviam sido gerados anteriormente)."

        return Response({
            'success': True,
            'message': msg,
            'totalGerados': criados,
            'totalExistentes': ja_existentes
        })

class PagamentoStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        escola = getattr(request, 'tenant', None) or getattr(request.user, 'escola', None)
        if not escola and getattr(request.user, 'role', '') == 'SUPERADMIN':
            qs = Pagamento.objects.all()
        elif escola:
            qs = Pagamento.objects.filter(escola=escola)
        else:
            qs = Pagamento.objects.none()

        total_recebido = qs.filter(status='PAGO').aggregate(total=Sum('valor_pago'))['total'] or 0
        total_pendente = qs.filter(status='PENDENTE').aggregate(total=Sum('valor'))['total'] or 0
        total_atrasado = qs.filter(status='ATRASADO').aggregate(total=Sum('valor'))['total'] or 0
        total_geral = total_recebido + total_pendente + total_atrasado

        taxa_adimp = round((float(total_recebido) / float(total_geral) * 100), 1) if total_geral > 0 else 0
        taxa_inadimp = round(100.0 - taxa_adimp, 1) if total_geral > 0 else 0

        historico_meses = [
            {'mes': 'Jan', 'recebido': 0, 'pendente': 0},
            {'mes': 'Fev', 'recebido': 0, 'pendente': 0},
            {'mes': 'Mar', 'recebido': float(total_recebido), 'pendente': float(total_pendente)},
        ]

        return Response({
            'success': True,
            'data': {
                'totalFaturado': float(total_geral),
                'totalRecebido': float(total_recebido),
                'totalPendente': float(total_pendente),
                'totalAtrasado': float(total_atrasado),
                'taxaAdimplencia': taxa_adimp,
                'percentualAdimplentes': taxa_adimp,
                'taxaInadimplencia': taxa_inadimp,
                'historicoMeses': historico_meses
            }
        })




from .models import TransacaoFinanceira, FolhaSalario, ItemPatrimonio
from .serializers import TransacaoFinanceiraSerializer, FolhaSalarioSerializer, ItemPatrimonioSerializer
from apps.accounts.audit import registrar_auditoria

class TransacaoFinanceiraViewSet(viewsets.ModelViewSet):
    queryset = TransacaoFinanceira.objects.all()
    serializer_class = TransacaoFinanceiraSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, 'role', '')
        escola = getattr(self.request, 'tenant', None) or getattr(user, 'escola', None)
        qs = TransacaoFinanceira.objects.all()
        if escola:
            qs = qs.filter(escola=escola)
        elif role != 'SUPERADMIN' and user.escola:
            qs = qs.filter(escola=user.escola)
        elif role != 'SUPERADMIN':
            return TransacaoFinanceira.objects.none()

        tipo = self.request.query_params.get('tipo')
        if tipo:
            qs = qs.filter(tipo=tipo)
        categoria = self.request.query_params.get('categoria')
        if categoria:
            qs = qs.filter(categoria__icontains=categoria)
        status_aprov = self.request.query_params.get('status_aprovacao')
        if status_aprov:
            qs = qs.filter(status_aprovacao=status_aprov)
        return qs.order_by('-data', '-created_at')

    def perform_create(self, serializer):
        escola = getattr(self.request, 'tenant', None) or getattr(self.request.user, 'escola', None)
        obj = serializer.save(escola=escola, registado_por=self.request.user)
        registrar_auditoria(self.request.user, escola, 'DESPESA', 'CRIACAO', obj.id, f'Registo de {obj.tipo} no valor de {obj.valor} MT ({obj.descricao})')

    @action(detail=True, methods=['post'], url_path='aprovar')
    def aprovar(self, request, pk=None):
        role = getattr(request.user, 'role', '')
        if role == 'FINANCEIRO':
            return Response({
                'success': False,
                'message': 'Regra mandatória de separação de funções: quem regista no Finanças NÃO pode aprovar a despesa. A aprovação é exclusiva da Direcção da Escola.'
            }, status=403)
        if role not in ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA'] and not getattr(request.user, 'is_superuser', False):
            return Response({'success': False, 'message': 'Competência exclusiva do Director da Escola.'}, status=403)
        obj = self.get_object()
        obj.status_aprovacao = 'APROVADO_DIRECTOR'
        obj.aprovado_por = request.user
        obj.data_aprovacao = timezone.now()
        obj.save()
        registrar_auditoria(request.user, obj.escola, 'DESPESA', 'APROVACAO', obj.id, f'Aprovação de {obj.tipo} de {obj.valor} MT pelo Director')
        return Response({'success': True, 'message': 'Transacção aprovada oficialmente com sucesso!', 'data': self.get_serializer(obj).data})

class FolhaSalarioViewSet(viewsets.ModelViewSet):
    queryset = FolhaSalario.objects.all()
    serializer_class = FolhaSalarioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, 'role', '')
        escola = getattr(self.request, 'tenant', None) or getattr(user, 'escola', None)
        qs = FolhaSalario.objects.all()
        if escola:
            qs = qs.filter(escola=escola)
        elif role != 'SUPERADMIN' and user.escola:
            qs = qs.filter(escola=user.escola)
        elif role != 'SUPERADMIN':
            return FolhaSalario.objects.none()

        mes = self.request.query_params.get('mes')
        if mes:
            qs = qs.filter(mes=mes)
        ano = self.request.query_params.get('ano')
        if ano:
            qs = qs.filter(ano=ano)
        status_folha = self.request.query_params.get('status')
        if status_folha:
            qs = qs.filter(status=status_folha)
        return qs.order_by('-ano', '-mes', 'funcionario_nome')

    def perform_create(self, serializer):
        escola = getattr(self.request, 'tenant', None) or getattr(self.request.user, 'escola', None)
        obj = serializer.save(escola=escola, processado_por=self.request.user)
        registrar_auditoria(self.request.user, escola, 'PAGAMENTO', 'CRIACAO', obj.id, f'Processamento de vencimento para {obj.funcionario_nome} ({obj.salario_liquido} MT)')

    @action(detail=True, methods=['post'], url_path='aprovar')
    def aprovar(self, request, pk=None):
        role = getattr(request.user, 'role', '')
        if role not in ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA'] and not getattr(request.user, 'is_superuser', False):
            return Response({'success': False, 'message': 'Competência exclusiva do Director da Escola.'}, status=403)
        obj = self.get_object()
        obj.status = 'APROVADO_DIRECTOR'
        obj.aprovado_por = request.user
        obj.save()
        registrar_auditoria(request.user, obj.escola, 'PAGAMENTO', 'APROVACAO', obj.id, f'Aprovação de vencimento de {obj.funcionario_nome} pelo Director')
        return Response({'success': True, 'message': 'Folha salarial aprovada com sucesso!', 'data': self.get_serializer(obj).data})

class ItemPatrimonioViewSet(viewsets.ModelViewSet):
    queryset = ItemPatrimonio.objects.all()
    serializer_class = ItemPatrimonioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, 'role', '')
        escola = getattr(self.request, 'tenant', None) or getattr(user, 'escola', None)
        qs = ItemPatrimonio.objects.all()
        if escola:
            qs = qs.filter(escola=escola)
        elif role != 'SUPERADMIN' and user.escola:
            qs = qs.filter(escola=user.escola)
        elif role != 'SUPERADMIN':
            return ItemPatrimonio.objects.none()

        categoria = self.request.query_params.get('categoria')
        if categoria:
            qs = qs.filter(categoria=categoria)
        estado = self.request.query_params.get('estado')
        if estado:
            qs = qs.filter(estado_conservacao=estado)
        return qs.order_by('codigo')

    def perform_create(self, serializer):
        escola = getattr(self.request, 'tenant', None) or getattr(self.request.user, 'escola', None)
        obj = serializer.save(escola=escola, registado_por=self.request.user)
        registrar_auditoria(self.request.user, escola, 'PATRIMONIO', 'CRIACAO', obj.id, f'Registo de bem patrimonial {obj.codigo} - {obj.nome}')

    @action(detail=True, methods=['post'], url_path='homologar')
    def homologar(self, request, pk=None):
        role = getattr(request.user, 'role', '')
        if role not in ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA'] and not getattr(request.user, 'is_superuser', False):
            return Response({'success': False, 'message': 'Competência exclusiva do Director da Escola.'}, status=403)
        obj = self.get_object()
        obj.status_validacao = 'HOMOLOGADO_DIRECTOR'
        obj.homologado_por = request.user
        obj.save()
        registrar_auditoria(request.user, obj.escola, 'PATRIMONIO', 'HOMOLOGACAO', obj.id, f'Homologação de bem {obj.codigo} pelo Director')
        return Response({'success': True, 'message': 'Bem patrimonial homologado com sucesso!', 'data': self.get_serializer(obj).data})
