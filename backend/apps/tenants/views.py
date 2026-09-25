from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.db.models import Sum, Count

from .models import Plano, Escola, AssinaturaEscola
from .serializers import PlanoSerializer, EscolaSerializer, AssinaturaEscolaSerializer
from apps.accounts.models import Usuario
from apps.accounts.serializers import UsuarioSerializer
from apps.alunos.models import Aluno
from apps.professores.models import Professor
from common.permissions.rbac import IsSuperAdmin, IsEscolaAdmin
from common.utils.geografia_mocambique import (
    PROVINCIAS_MOCAMBIQUE,
    DISTRITOS_POR_PROVINCIA,
    CARREIRAS_DOCENTES,
    TIPOS_DOCUMENTO,
    ANOTACOES_STATUS,
    COMPORTAMENTOS
)

class GeografiaView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'success': True,
            'data': {
                'provincias': PROVINCIAS_MOCAMBIQUE,
                'distritos': DISTRITOS_POR_PROVINCIA,
                'carreiras': CARREIRAS_DOCENTES,
                'tiposDocumento': TIPOS_DOCUMENTO,
                'anotacoes': ANOTACOES_STATUS,
                'comportamentos': COMPORTAMENTOS
            }
        })

class SaaSMetricsView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        total_escolas = Escola.objects.count()
        escolas_ativas = Escola.objects.filter(status='ATIVA').count()
        escolas_expiradas = Escola.objects.filter(status='EXPIRADA').count()
        total_alunos = Aluno.objects.count()
        total_professores = Professor.objects.count()
        mrr = AssinaturaEscola.objects.filter(status='ATIVA').aggregate(total=Sum('valor'))['total'] or 0

        mrr_val = float(mrr)
        arr_val = mrr_val * 12.0
        churn_val = round((escolas_expiradas / total_escolas * 100), 1) if total_escolas else 0.0

        payload = {
            'mrr': mrr_val,
            'arr': arr_val,
            'churn': churn_val,
            'escolas': {
                'total': total_escolas,
                'ativas': escolas_ativas,
                'expiradas': escolas_expiradas,
            },
            'totalEscolas': total_escolas,
            'escolasAtivas': escolas_ativas,
            'escolasExpiradas': escolas_expiradas,
            'totalAlunos': total_alunos,
            'totalProfessores': total_professores,
            'receitaMensalEstimada': mrr_val,
        }

        return Response({
            'success': True,
            'data': payload,
            'metrics': payload
        })

class PlanoViewSet(viewsets.ModelViewSet):
    queryset = Plano.objects.all()
    serializer_class = PlanoSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return Response({'success': True, 'data': PlanoSerializer(qs, many=True).data})

    @action(detail=True, methods=['put', 'patch'], url_path='preco')
    def preco(self, request, pk=None):
        plano = self.get_object()
        novo_preco = request.data.get('preco')
        if novo_preco is not None:
            plano.preco = novo_preco
            plano.save()
            return Response({'success': True, 'data': PlanoSerializer(plano).data})
        return Response({'success': False, 'message': 'Preço não fornecido.'}, status=status.HTTP_400_BAD_REQUEST)

class EscolaViewSet(viewsets.ModelViewSet):
    queryset = Escola.objects.all()
    serializer_class = EscolaSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return Response({'success': True, 'data': EscolaSerializer(qs, many=True).data})

    def retrieve(self, request, *args, **kwargs):
        escola = self.get_object()
        return Response({'success': True, 'data': EscolaSerializer(escola).data})

    def create(self, request, *args, **kwargs):
        data = request.data
        nome = (data.get('nome') or '').strip()
        nif_cnpj = (data.get('nif_cnpj') or data.get('nuit') or '').strip()
        email = (data.get('email') or '').strip().lower()

        if not nome or not nif_cnpj or not email:
            return Response({
                'success': False,
                'message': 'Campos obrigatórios: Nome da Instituição, NUIT e E-mail.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if Escola.objects.filter(nif_cnpj__iexact=nif_cnpj).exists():
            return Response({
                'success': False,
                'message': f'Já existe uma instituição cadastrada com o NUIT {nif_cnpj}.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if Escola.objects.filter(email__iexact=email).exists():
            return Response({
                'success': False,
                'message': f'Já existe uma instituição cadastrada com o E-mail {email}.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Obter plano
        plano = None
        plano_id = data.get('plano_id') or data.get('plano')
        if plano_id:
            try:
                plano = Plano.objects.get(id=plano_id)
            except (Plano.DoesNotExist, ValueError):
                plano = None
        if not plano:
            plano = Plano.objects.filter(ativo=True).first()

        # Criar a Escola
        escola = Escola.objects.create(
            nome=nome,
            nif_cnpj=nif_cnpj,
            email=email,
            telefone=data.get('telefone', '+258 '),
            provincia=data.get('provincia', 'Maputo Cidade'),
            distrito=data.get('distrito', 'KaMpfumo'),
            plano=plano,
            usar_emblema_nacional=data.get('usar_emblema_nacional', True),
            logo_url=data.get('logo_url') or None,
            status='ATIVA'
        )

        # Criar a Assinatura inicial
        valor_contrato = data.get('valor_contrato')
        if valor_contrato is None and plano:
            valor_contrato = plano.preco
        elif valor_contrato is None:
            valor_contrato = 0

        duracao_dias = plano.duracao_dias if plano else 30
        data_fim = timezone.now() + timezone.timedelta(days=duracao_dias)

        assinatura = AssinaturaEscola.objects.create(
            escola=escola,
            plano=plano or Plano.objects.first(),
            data_inicio=timezone.now(),
            data_fim=data_fim,
            valor=valor_contrato,
            status='ATIVA',
            metodo_pagamento='TRANSFERENCIA'
        )

        # Criar o Administrador da Escola
        admin_nome = (data.get('adminNome') or f"Administrador {escola.nome}").strip()
        admin_email = (data.get('adminEmail') or f"admin.{escola.nif_cnpj}@sige.edu.mz").strip().lower()
        admin_senha = data.get('adminSenha') or '123456'

        admin_user = Usuario.objects.filter(email__iexact=admin_email).first()
        if not admin_user:
            admin_user = Usuario.objects.create_user(
                email=admin_email,
                password=admin_senha,
                nome=admin_nome,
                role='ADMIN_ESCOLA',
                escola=escola,
                telefone=data.get('telefone', '')
            )
        else:
            admin_user.escola = escola
            admin_user.role = 'ADMIN_ESCOLA'
            if admin_senha:
                admin_user.set_password(admin_senha)
            admin_user.save()

        return Response({
            'success': True,
            'message': 'Instituição e Administrador cadastrados com sucesso!',
            'data': {
                'escola': EscolaSerializer(escola).data,
                'adminUser': {
                    'id': str(admin_user.id),
                    'nome': admin_user.nome,
                    'email': admin_user.email,
                    'role': admin_user.role,
                }
            }
        }, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        escola = self.get_object()
        data = request.data.copy()

        # Atualizar assinatura se data_fim ou dias_adicionais enviados
        data_fim = data.pop('data_fim', None) or data.pop('data_fim_assinatura', None)
        dias_adicionais = data.pop('dias_adicionais', None)

        ass = escola.assinaturas.order_by('-data_fim').first()
        if ass:
            if dias_adicionais:
                try:
                    ass.data_fim = ass.data_fim + timezone.timedelta(days=int(dias_adicionais))
                    ass.status = 'ATIVA'
                    escola.status = 'ATIVA'
                    ass.save()
                except Exception:
                    pass
            elif data_fim:
                try:
                    from datetime import datetime
                    if isinstance(data_fim, str) and len(data_fim) == 10:
                        ass.data_fim = timezone.make_aware(datetime.strptime(data_fim, '%Y-%m-%d'))
                    ass.status = 'ATIVA'
                    escola.status = 'ATIVA'
                    ass.save()
                except Exception:
                    pass

        serializer = self.get_serializer(escola, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        escola.refresh_from_db()

        return Response({
            'success': True,
            'message': 'Dados da escola e contrato actualizados com sucesso.',
            'data': EscolaSerializer(escola).data
        })

    def destroy(self, request, *args, **kwargs):
        escola = self.get_object()
        nome = escola.nome
        escola.delete()
        return Response({
            'success': True,
            'message': f'Instituição {nome} removida com sucesso.'
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post', 'patch'], url_path='toggle-status')
    def toggle_status(self, request, pk=None):
        escola = self.get_object()
        escola.status = 'SUSPENSA' if escola.status == 'ATIVA' else 'ATIVA'
        escola.save()
        return Response({
            'success': True,
            'message': f"Escola {escola.nome} alterada para status {escola.status}",
            'data': EscolaSerializer(escola).data
        })

    @action(detail=True, methods=['get'], url_path='comprovativo-contrato')
    def comprovativo_contrato(self, request, pk=None):
        escola = self.get_object()
        assinatura = escola.assinaturas.order_by('-data_fim').first()
        plano = escola.plano or (assinatura.plano if assinatura else None)
        return Response({
            'success': True,
            'data': {
                'escola': {
                    'nome': escola.nome,
                    'nif_cnpj': escola.nif_cnpj,
                    'distrito': escola.distrito,
                    'provincia': escola.provincia,
                    'email': escola.email,
                    'status': escola.status,
                },
                'plano': {
                    'nome': plano.nome if plano else 'Plano Padrão',
                    'preco': float(plano.preco) if plano else 0.0,
                },
                'assinatura': {
                    'data_inicio': assinatura.data_inicio if assinatura else escola.created_at,
                    'data_fim': assinatura.data_fim if assinatura else timezone.now(),
                    'valor_pago': float(assinatura.valor) if assinatura else (float(plano.preco) if plano else 0.0),
                }
            }
        })

class MinhaEscolaComprovativoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        escola = getattr(request, 'tenant', None) or getattr(request.user, 'escola', None)
        if not escola:
            return Response({'success': False, 'message': 'Nenhuma escola vinculada ao usuário.'}, status=status.HTTP_404_NOT_FOUND)
        
        assinatura = escola.assinaturas.order_by('-data_fim').first()
        plano = escola.plano or (assinatura.plano if assinatura else None)
        return Response({
            'success': True,
            'data': {
                'escola': {
                    'nome': escola.nome,
                    'nif_cnpj': escola.nif_cnpj,
                    'distrito': escola.distrito,
                    'provincia': escola.provincia,
                    'email': escola.email,
                    'status': escola.status,
                },
                'plano': {
                    'nome': plano.nome if plano else 'Plano Padrão',
                    'preco': float(plano.preco) if plano else 0.0,
                },
                'assinatura': {
                    'data_inicio': assinatura.data_inicio if assinatura else escola.created_at,
                    'data_fim': assinatura.data_fim if assinatura else timezone.now(),
                    'valor_pago': float(assinatura.valor) if assinatura else (float(plano.preco) if plano else 0.0),
                }
            }
        })


class VerificarExpiracoesView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request):
        agora = timezone.now()
        # Escolas cuja assinatura mais recente venceu
        expiradas = 0
        for escola in Escola.objects.filter(status='ATIVA'):
            ultima_assinatura = escola.assinaturas.order_by('-data_fim').first()
            if ultima_assinatura and ultima_assinatura.data_fim < agora:
                escola.status = 'EXPIRADA'
                escola.save()
                ultima_assinatura.status = 'EXPIRADA'
                ultima_assinatura.save()
                expiradas += 1

        return Response({
            'success': True,
            'message': f"Verificação concluída. {expiradas} escolas marcadas como expiradas.",
            'totalExpiradas': expiradas
        })

class EscolaAdminInfoView(APIView):
    permission_classes = [IsAuthenticated, IsEscolaAdmin]

    def get(self, request):
        escola = request.tenant or request.user.escola
        if not escola:
            return Response({'success': False, 'message': 'Nenhuma escola associada.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'data': EscolaSerializer(escola).data})

    def put(self, request):
        escola = request.tenant or request.user.escola
        if not escola:
            return Response({'success': False, 'message': 'Nenhuma escola associada.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = EscolaSerializer(escola, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'success': True, 'data': serializer.data})
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class ToggleNotasView(APIView):
    permission_classes = [IsAuthenticated, IsEscolaAdmin]

    def post(self, request):
        escola = request.tenant or request.user.escola
        if not escola:
            return Response({'success': False, 'message': 'Escola não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        escola.permitir_visualizacao_notas = not escola.permitir_visualizacao_notas
        escola.save()
        return Response({
            'success': True,
            'permitir_visualizacao_notas': escola.permitir_visualizacao_notas,
            'message': f"Visualização de notas agora está {'ativada' if escola.permitir_visualizacao_notas else 'desativada'}."
        })

class UsuariosCredenciaisView(APIView):
    permission_classes = [IsAuthenticated, IsEscolaAdmin]

    def get(self, request):
        escola = request.tenant or request.user.escola
        usuarios = Usuario.objects.filter(escola=escola)
        return Response({
            'success': True,
            'data': UsuarioSerializer(usuarios, many=True).data
        })
