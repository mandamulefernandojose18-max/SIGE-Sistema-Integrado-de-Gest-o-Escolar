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
    CODIGOS_PROVINCIAS_MOCAMBIQUE,
    DISTRITOS_POR_PROVINCIA,
    CARREIRAS_DOCENTES,
    TIPOS_DOCUMENTO,
    ANOTACOES_STATUS,
    COMPORTAMENTOS,
    TIPOS_ESCOLA,
    obter_codigos_orgaos_escola,
)


def garantir_contas_institucionais_escola(escola, data=None):
    """
    Garante que a Escola possui o código único oficial (ex: 0101S0001) e que as
    3 contas institucionais da direcção existem e possuem os respectivos códigos:
      - Director da Escola (Admin Geral / Gabinete do Director): GD + codigo_escola (ex: GD0101S0001)
      - Director Pedagógico (Sub-Admin / Direcção Pedagógica): DP + codigo_escola (ex: DP0101S0001)
      - Chefe da Secretaria (Secretaria): SECR + codigo_escola (ex: SECR0101S0001)
    """
    if not escola:
        return None, None, None

    data = data or {}
    if not escola.codigo_escola:
        escola.save()

    cod_escola = (escola.codigo_escola or '').strip().upper()
    orgaos = obter_codigos_orgaos_escola(cod_escola)
    cod_gd = orgaos['gabinete_director']      # ex: GD0101S0001
    cod_dp = orgaos['direccao_pedagogica']    # ex: DP0101S0001
    cod_secr = orgaos['secretaria']           # ex: SECR0101S0001

    slug_cod = cod_escola.lower() or str(escola.id)[:8].lower()

    # 1. Director da Escola (Admin Geral) - GD + codigo_escola
    admin_nome = (
        data.get('adminNome')
        or data.get('director_nome')
        or escola.director_nome
        or f"Director da Escola ({escola.nome})"
    ).strip()
    admin_email_req = (data.get('adminEmail') or '').strip().lower()
    admin_senha = data.get('adminSenha')

    admin_user = (
        Usuario.objects.filter(escola=escola, role__in=['ADMIN_ESCOLA', 'DIRECTOR_ESCOLA']).first()
        or (Usuario.objects.filter(email__iexact=admin_email_req).first() if admin_email_req else None)
    )
    if not admin_user:
        email_cand = admin_email_req or f"gd.{slug_cod}@sige.edu.mz"
        if Usuario.objects.filter(email__iexact=email_cand).exists():
            email_cand = f"gd.{slug_cod}.{str(escola.id)[:4]}@sige.edu.mz"
        admin_user = Usuario.objects.create_user(
            email=email_cand,
            password=admin_senha or '123456',
            nome=admin_nome,
            role='ADMIN_ESCOLA',
            escola=escola,
            telefone=data.get('telefone') or escola.telefone or '',
            codigo_acesso=cod_gd,
        )
    else:
        changed = False
        if admin_user.escola_id != escola.id:
            admin_user.escola = escola
            changed = True
        if admin_user.codigo_acesso != cod_gd:
            admin_user.codigo_acesso = cod_gd
            changed = True
        if data.get('adminNome') or data.get('director_nome'):
            admin_user.nome = admin_nome
            changed = True
        if admin_senha:
            admin_user.set_password(admin_senha)
            changed = True
        if changed:
            admin_user.save()

    # 2. Direcção Pedagógica / Director Pedagógico (Sub-Admin) - DP + codigo_escola
    dp_nome = (
        data.get('dapNome')
        or data.get('dap_nome')
        or escola.dap_nome
        or f"Direcção Pedagógica ({escola.nome})"
    ).strip()
    dp_email_req = (data.get('dapEmail') or '').strip().lower()
    dp_senha = data.get('dapSenha')

    dp_user = (
        Usuario.objects.filter(escola=escola, role='DAP').first()
        or (Usuario.objects.filter(email__iexact=dp_email_req).first() if dp_email_req else None)
    )
    if not dp_user:
        email_cand = dp_email_req or f"dp.{slug_cod}@sige.edu.mz"
        if Usuario.objects.filter(email__iexact=email_cand).exists():
            email_cand = f"dp.{slug_cod}.{str(escola.id)[:4]}@sige.edu.mz"
        dp_user = Usuario.objects.create_user(
            email=email_cand,
            password=dp_senha or '123456',
            nome=dp_nome,
            role='DAP',
            escola=escola,
            telefone=escola.telefone or '',
            codigo_acesso=cod_dp,
        )
    else:
        changed = False
        if dp_user.escola_id != escola.id:
            dp_user.escola = escola
            changed = True
        if dp_user.codigo_acesso != cod_dp:
            dp_user.codigo_acesso = cod_dp
            changed = True
        if data.get('dapNome') or data.get('dap_nome'):
            dp_user.nome = dp_nome
            changed = True
        if dp_senha:
            dp_user.set_password(dp_senha)
            changed = True
        if changed:
            dp_user.save()

    # 3. Chefe da Secretaria (Secretaria) - SECR + codigo_escola
    secr_nome = (
        data.get('secretariaNome')
        or data.get('chefe_secretaria_nome')
        or escola.chefe_secretaria_nome
        or f"Chefe da Secretaria ({escola.nome})"
    ).strip()
    secr_email_req = (data.get('secretariaEmail') or '').strip().lower()
    secr_senha = data.get('secretariaSenha')

    secr_user = (
        Usuario.objects.filter(escola=escola, role='CHEFE_SECRETARIA').first()
        or (Usuario.objects.filter(email__iexact=secr_email_req).first() if secr_email_req else None)
    )
    if not secr_user:
        email_cand = secr_email_req or f"secr.{slug_cod}@sige.edu.mz"
        if Usuario.objects.filter(email__iexact=email_cand).exists():
            email_cand = f"secr.{slug_cod}.{str(escola.id)[:4]}@sige.edu.mz"
        secr_user = Usuario.objects.create_user(
            email=email_cand,
            password=secr_senha or '123456',
            nome=secr_nome,
            role='CHEFE_SECRETARIA',
            escola=escola,
            telefone=escola.telefone or '',
            codigo_acesso=cod_secr,
        )
    else:
        changed = False
        if secr_user.escola_id != escola.id:
            secr_user.escola = escola
            changed = True
        if secr_user.codigo_acesso != cod_secr:
            secr_user.codigo_acesso = cod_secr
            changed = True
        if data.get('secretariaNome') or data.get('chefe_secretaria_nome'):
            secr_user.nome = secr_nome
            changed = True
        if secr_senha:
            secr_user.set_password(secr_senha)
            changed = True
        if changed:
            secr_user.save()

    return admin_user, dp_user, secr_user


class GeografiaView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'success': True,
            'data': {
                'provincias': PROVINCIAS_MOCAMBIQUE,
                'codigosProvincias': CODIGOS_PROVINCIAS_MOCAMBIQUE,
                'distritos': DISTRITOS_POR_PROVINCIA,
                'tiposEscola': TIPOS_ESCOLA,
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
        raw_logo = data.get('logo_url') or None
        is_b64_logo = bool(raw_logo and str(raw_logo).startswith('data:'))
        tipo_escola_in = data.get('tipo_escola') or ''
        director_nome_in = (data.get('director_nome') or data.get('adminNome') or 'Prof. Dr. António Costa').strip()
        dap_nome_in = (data.get('dap_nome') or data.get('dapNome') or 'Prof. João Baptista').strip()
        secr_nome_in = (data.get('chefe_secretaria_nome') or data.get('secretariaNome') or 'Dra. Maria Eunice').strip()

        escola = Escola.objects.create(
            nome=nome,
            nif_cnpj=nif_cnpj,
            email=email,
            telefone=data.get('telefone', '+258 '),
            provincia=data.get('provincia', 'Maputo Cidade'),
            distrito=data.get('distrito', 'KaMpfumo'),
            tipo_escola=tipo_escola_in,
            director_nome=director_nome_in,
            dap_nome=dap_nome_in,
            chefe_secretaria_nome=secr_nome_in,
            codigo_escola=(data.get('codigo_escola') or '').strip().upper() or None,
            plano=plano,
            usar_emblema_nacional=data.get('usar_emblema_nacional', True),
            logo_url=None if is_b64_logo else raw_logo,
            logo_base64=raw_logo if is_b64_logo else (data.get('logo_base64') or None),
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

        # Garantir as 3 Contas Institucionais (GD, DP, SECR)
        admin_user, dp_user, secr_user = garantir_contas_institucionais_escola(escola, data)

        return Response({
            'success': True,
            'message': f'Instituição cadastrada com sucesso! Código Oficial: {escola.codigo_escola}',
            'data': {
                'escola': EscolaSerializer(escola).data,
                'adminUser': {
                    'id': str(admin_user.id),
                    'nome': admin_user.nome,
                    'email': admin_user.email,
                    'codigo_acesso': admin_user.codigo_acesso,
                    'role': admin_user.role,
                } if admin_user else None,
                'dpUser': {
                    'id': str(dp_user.id),
                    'nome': dp_user.nome,
                    'email': dp_user.email,
                    'codigo_acesso': dp_user.codigo_acesso,
                    'role': dp_user.role,
                } if dp_user else None,
                'secretariaUser': {
                    'id': str(secr_user.id),
                    'nome': secr_user.nome,
                    'email': secr_user.email,
                    'codigo_acesso': secr_user.codigo_acesso,
                    'role': secr_user.role,
                } if secr_user else None,
            }
        }, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        escola = self.get_object()
        data = request.data.copy()

        # Se mudou província, distrito ou tipo_escola e não enviou um novo codigo_escola manual diferente,
        # recalcular o prefixo do codigo_escola se necessário
        prov_nova = data.get('provincia', escola.provincia)
        dist_novo = data.get('distrito', escola.distrito)
        tipo_novo = data.get('tipo_escola', escola.tipo_escola)
        if (prov_nova != escola.provincia or dist_novo != escola.distrito or tipo_novo != escola.tipo_escola):
            from common.utils.geografia_mocambique import gerar_codigo_unico_escola
            data['codigo_escola'] = gerar_codigo_unico_escola(
                provincia=prov_nova,
                distrito=dist_novo,
                tipo_escola=tipo_novo,
                nome_escola=data.get('nome', escola.nome),
                exclude_escola_id=escola.id,
            )

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
        garantir_contas_institucionais_escola(escola, data)

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
        return Response({
            'success': True,
            'data': _montar_comprovativo_escola(escola)
        })


def _montar_comprovativo_escola(escola):
    from apps.turmas.models import Turma
    assinatura = escola.assinaturas.order_by('-data_fim').first()
    plano = escola.plano or (assinatura.plano if assinatura else None)
    val_pago = float(assinatura.valor) if assinatura else (float(plano.preco) if plano else 0.0)
    return {
        'comprovativo_numero': f"CONT-{str(escola.id)[:8].upper()}-{timezone.now().year}",
        'status_atual': escola.status,
        'escola': {
            'id': str(escola.id),
            'nome': escola.nome,
            'codigo_escola': escola.codigo_escola,
            'tipo_escola': escola.tipo_escola,
            'nif_cnpj': escola.nif_cnpj,
            'distrito': escola.distrito,
            'provincia': escola.provincia,
            'email': escola.email,
            'telefone': escola.telefone or '+258',
            'status': escola.status,
        },
        'plano': {
            'nome': plano.nome if plano else 'Plano Padrão',
            'preco': float(plano.preco) if plano else 0.0,
            'max_alunos': plano.max_alunos if plano else 1000,
            'max_professores': plano.max_professores if plano else 100,
        },
        'assinatura': {
            'data_inicio': assinatura.data_inicio if assinatura else escola.created_at,
            'data_fim': assinatura.data_fim if assinatura else timezone.now(),
            'valor': val_pago,
            'valor_pago': val_pago,
        },
        'estatisticas': {
            'total_alunos': Aluno.objects.filter(escola=escola).count(),
            'total_professores': Professor.objects.filter(escola=escola).count(),
            'total_turmas': Turma.objects.filter(escola=escola).count(),
        }
    }


class MinhaEscolaComprovativoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        escola = getattr(request, 'tenant', None) or getattr(request.user, 'escola', None)
        if not escola and getattr(request.user, 'role', '') == 'SUPERADMIN':
            escola = Escola.objects.filter(status='ATIVA').first() or Escola.objects.first()
        if not escola:
            return Response({'success': False, 'message': 'Nenhuma escola vinculada ao usuário.'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'success': True,
            'data': _montar_comprovativo_escola(escola)
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
        if not escola.codigo_escola:
            escola.save()
        garantir_contas_institucionais_escola(escola)
        return Response({'success': True, 'data': EscolaSerializer(escola).data})

    def put(self, request):
        escola = request.tenant or request.user.escola
        if not escola:
            return Response({'success': False, 'message': 'Nenhuma escola associada.'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        prov_nova = data.get('provincia', escola.provincia)
        dist_novo = data.get('distrito', escola.distrito)
        tipo_novo = data.get('tipo_escola', escola.tipo_escola)
        if (prov_nova != escola.provincia or dist_novo != escola.distrito or tipo_novo != escola.tipo_escola):
            from common.utils.geografia_mocambique import gerar_codigo_unico_escola
            if not data.get('codigo_escola') or data.get('codigo_escola') == escola.codigo_escola:
                data['codigo_escola'] = gerar_codigo_unico_escola(
                    provincia=prov_nova,
                    distrito=dist_novo,
                    tipo_escola=tipo_novo,
                    nome_escola=data.get('nome', escola.nome),
                    exclude_escola_id=escola.id,
                )

        serializer = EscolaSerializer(escola, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            escola.refresh_from_db()
            garantir_contas_institucionais_escola(escola, data)
            return Response({'success': True, 'data': EscolaSerializer(escola).data})
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
        if escola:
            garantir_contas_institucionais_escola(escola)
        usuarios = Usuario.objects.filter(escola=escola)
        return Response({
            'success': True,
            'data': UsuarioSerializer(usuarios, many=True).data
        })
