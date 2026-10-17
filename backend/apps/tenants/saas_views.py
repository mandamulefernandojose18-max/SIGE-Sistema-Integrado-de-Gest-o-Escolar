import os
import uuid
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.db import connection, transaction
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Escola, SaasPlano, SaasAssinatura, SaasFatura, SaasPagamento, SaasLogAssinatura, SaasCoordenadasPagamento
from .saas_serializers import (
    SaasPlanoSerializer,
    SaasAssinaturaSerializer,
    SaasFaturaSerializer,
    SaasPagamentoSerializer,
    SaasLogAssinaturaSerializer,
    SaasCoordenadasPagamentoSerializer
)
from .saas_middleware import limpar_cache_assinatura


def is_postgresql():
    return connection.vendor == 'postgresql'


def is_superadmin_user(user):
    return getattr(user, 'role', '') == 'SUPERADMIN' or getattr(user, 'is_superuser', False)


# =====================================================================
# 👑 VISÃO SUPER ADMIN (DONO DA PLATAFORMA)
# =====================================================================

class SaasResumoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_superadmin_user(request.user):
            return Response({'success': False, 'message': 'Acesso exclusivo ao Super Administrador.'}, status=status.HTTP_403_FORBIDDEN)

        # 1. Total de Instituições por Estado
        estados_contagem = {
            'activa': SaasAssinatura.objects.filter(estado='activa').count(),
            'fatura_pendente': SaasAssinatura.objects.filter(estado='fatura_pendente').count(),
            'em_atraso': SaasAssinatura.objects.filter(estado='em_atraso').count(),
            'restrita': SaasAssinatura.objects.filter(estado='restrita').count(),
            'suspensa': SaasAssinatura.objects.filter(estado='suspensa').count(),
            'cancelada': SaasAssinatura.objects.filter(estado='cancelada').count(),
            'teste': SaasAssinatura.objects.filter(estado='teste').count(),
        }
        total_instituicoes = Escola.objects.count()

        # 2. Valor total em dívida (faturas abertas ou em atraso)
        faturas_devedoras = SaasFatura.objects.filter(estado__in=['aberta', 'em_atraso', 'paga_parcial'])
        valor_em_divida = sum(float(f.valor + f.multa_aplicada - f.valor_pago) for f in faturas_devedoras)

        # 3. Pagamentos aguardando validação
        pagamentos_pendentes = SaasPagamento.objects.filter(estado='enviado').count()

        # 4. Receita do mês corrente
        hoje = timezone.localdate()
        mes_inicio = hoje.replace(day=1)
        pagamentos_mes = SaasPagamento.objects.filter(estado='confirmado', confirmado_em__date__gte=mes_inicio)
        receita_mes = sum(float(p.valor) for p in pagamentos_mes)

        return Response({
            'success': True,
            'data': {
                'total_instituicoes': total_instituicoes,
                'estados': estados_contagem,
                'valor_em_divida_mzn': round(valor_em_divida, 2),
                'pagamentos_pendentes_validacao': pagamentos_pendentes,
                'receita_mes_mzn': round(receita_mes, 2),
            }
        })


class SaasAssinaturasListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_superadmin_user(request.user):
            return Response({'success': False, 'message': 'Acesso exclusivo ao Super Administrador.'}, status=status.HTTP_403_FORBIDDEN)

        # Garante que todas as escolas tenham um registo de SaasAssinatura ativo
        plano_padrao = SaasPlano.objects.filter(activo=True).first()
        if not plano_padrao:
            plano_padrao = SaasPlano.objects.create(
                nome='Plano Básico',
                preco_mensal=Decimal('2500.00'),
                limite_alunos=500,
                limite_professores=50
            )

        hoje = timezone.localdate()
        for escola in Escola.objects.all():
            if not SaasAssinatura.objects.filter(instituicao=escola).exists():
                proxima = hoje + timedelta(days=30)
                SaasAssinatura.objects.create(
                    instituicao=escola,
                    plano=plano_padrao,
                    periodicidade='mensal',
                    modo_data_limite='automatico',
                    dias_tolerancia=5,
                    dias_ate_suspensao=15,
                    estado='activa' if escola.status == 'ATIVA' else 'suspensa',
                    proxima_fatura_em=proxima
                )

        qs = SaasAssinatura.objects.select_related('instituicao', 'plano').all().order_by('-created_at')

        # Filtros
        estado_filtro = request.GET.get('estado')
        if estado_filtro:
            qs = qs.filter(estado=estado_filtro)

        periodicidade_filtro = request.GET.get('periodicidade')
        if periodicidade_filtro:
            qs = qs.filter(periodicidade=periodicidade_filtro)

        busca = request.GET.get('busca')
        if busca:
            qs = qs.filter(instituicao__nome__icontains=busca) | qs.filter(instituicao__codigo_escola__icontains=busca) | qs.filter(instituicao__nif_cnpj__icontains=busca)

        serializer = SaasAssinaturaSerializer(qs, many=True)
        return Response({'success': True, 'data': serializer.data})


class SaasAssinaturaDetalheView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not is_superadmin_user(request.user):
            return Response({'success': False, 'message': 'Acesso exclusivo ao Super Administrador.'}, status=status.HTTP_403_FORBIDDEN)

        ass = SaasAssinatura.objects.select_related('instituicao', 'plano').filter(id=pk).first()
        if not ass:
            return Response({'success': False, 'message': 'Assinatura não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        faturas = SaasFatura.objects.filter(assinatura=ass).order_by('-periodo_inicio')
        pagamentos = SaasPagamento.objects.filter(instituicao=ass.instituicao).order_by('-criado_em')
        logs = SaasLogAssinatura.objects.filter(instituicao=ass.instituicao).order_by('-criado_em')[:50]

        return Response({
            'success': True,
            'data': {
                'assinatura': SaasAssinaturaSerializer(ass).data,
                'faturas': SaasFaturaSerializer(faturas, many=True).data,
                'pagamentos': SaasPagamentoSerializer(pagamentos, many=True).data,
                'auditoria': SaasLogAssinaturaSerializer(logs, many=True).data
            }
        })

    def patch(self, request, pk):
        """Configuração avançada dos parâmetros da assinatura pelo Super Admin"""
        if not is_superadmin_user(request.user):
            return Response({'success': False, 'message': 'Acesso exclusivo ao Super Administrador.'}, status=status.HTTP_403_FORBIDDEN)

        ass = SaasAssinatura.objects.filter(id=pk).first()
        if not ass:
            return Response({'success': False, 'message': 'Assinatura não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        if 'periodicidade' in data:
            ass.periodicidade = data['periodicidade']
        if 'modo_data_limite' in data:
            ass.modo_data_limite = data['modo_data_limite']
        if 'dia_limite' in data:
            ass.dia_limite = int(data['dia_limite']) if data['dia_limite'] else None
        if 'dias_tolerancia' in data:
            ass.dias_tolerancia = int(data['dias_tolerancia'])
        if 'dias_ate_suspensao' in data:
            ass.dias_ate_suspensao = int(data['dias_ate_suspensao'])
        if 'data_bloqueio_manual' in data:
            ass.data_bloqueio_manual = data['data_bloqueio_manual'] or None
        if 'multa_tipo' in data:
            ass.multa_tipo = data['multa_tipo']
        if 'multa_valor' in data:
            ass.multa_valor = Decimal(str(data['multa_valor']))

        ass.save()
        limpar_cache_assinatura(ass.instituicao_id)

        SaasLogAssinatura.objects.create(
            instituicao=ass.instituicao,
            assinatura=ass,
            accao='CONFIGURACAO_ASSINATURA',
            feito_por=request.user.nome or request.user.email,
            motivo='Actualização dos parâmetros e datas da assinatura pelo Super Admin.'
        )

        return Response({
            'success': True,
            'message': 'Parâmetros da assinatura actualizados com sucesso.',
            'data': SaasAssinaturaSerializer(ass).data
        })


class SaasPagamentosPendentesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_superadmin_user(request.user):
            return Response({'success': False, 'message': 'Acesso restrito ao Super Administrador.'}, status=status.HTTP_403_FORBIDDEN)

        qs = SaasPagamento.objects.select_related('instituicao', 'fatura').filter(estado='enviado').order_by('-criado_em')
        serializer = SaasPagamentoSerializer(qs, many=True)
        return Response({'success': True, 'data': serializer.data})


class SaasConfirmarPagamentoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not is_superadmin_user(request.user):
            return Response({'success': False, 'message': 'Acesso restrito ao Super Administrador.'}, status=status.HTTP_403_FORBIDDEN)

        pag = SaasPagamento.objects.filter(id=pk).first()
        if not pag:
            return Response({'success': False, 'message': 'Pagamento não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        utilizador = request.user.nome or request.user.email

        if is_postgresql():
            with connection.cursor() as cursor:
                cursor.execute("SELECT public.confirmar_pagamento(%s, %s)", [str(pk), utilizador])
                resultado = cursor.fetchone()[0]
        else:
            # Fallback Python para ambiente local SQLite / Testes
            with transaction.atomic():
                fat = pag.fatura
                ass = fat.assinatura
                total_devido = fat.valor + fat.multa_aplicada
                novo_pago = fat.valor_pago + pag.valor

                pag.estado = 'confirmado'
                pag.confirmado_por = utilizador
                pag.confirmado_em = timezone.now()
                pag.save()

                if novo_pago >= total_devido:
                    fat.valor_pago = novo_pago
                    fat.estado = 'paga'
                else:
                    fat.valor_pago = novo_pago
                    fat.estado = 'paga_parcial'
                fat.save()

                restantes = SaasFatura.objects.filter(instituicao=pag.instituicao, estado__in=['em_atraso', 'aberta']).count()
                if restantes == 0:
                    ass.estado = 'activa'
                    ass.save()
                    Escola.objects.filter(id=pag.instituicao_id).update(status='ATIVA', bloqueada_manualmente=False)

                SaasLogAssinatura.objects.create(
                    instituicao=pag.instituicao,
                    assinatura=ass,
                    fatura=fat,
                    accao='PAGAMENTO_CONFIRMADO',
                    estado_anterior=ass.estado,
                    estado_novo='activa' if restantes == 0 else ass.estado,
                    valor_novo=pag.valor,
                    feito_por=utilizador,
                    motivo=f'Confirmação manual de pagamento Ref: {pag.referencia}'
                )
                resultado = {'sucesso': True, 'mensagem': 'Pagamento confirmado com sucesso.', 'assinatura_reativada': restantes == 0}

        limpar_cache_assinatura(pag.instituicao_id)
        return Response({'success': True, 'data': resultado})


class SaasRejeitarPagamentoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not is_superadmin_user(request.user):
            return Response({'success': False, 'message': 'Acesso restrito ao Super Administrador.'}, status=status.HTTP_403_FORBIDDEN)

        motivo = request.data.get('motivo', '').strip()
        if not motivo:
            return Response({'success': False, 'message': 'O motivo de rejeição é estritamente obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)

        pag = SaasPagamento.objects.filter(id=pk).first()
        if not pag:
            return Response({'success': False, 'message': 'Pagamento não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        utilizador = request.user.nome or request.user.email

        if is_postgresql():
            with connection.cursor() as cursor:
                cursor.execute("SELECT public.rejeitar_pagamento(%s, %s, %s)", [str(pk), motivo, utilizador])
                resultado = cursor.fetchone()[0]
        else:
            pag.estado = 'rejeitado'
            pag.motivo_rejeicao = motivo
            pag.confirmado_por = utilizador
            pag.confirmado_em = timezone.now()
            pag.save()

            SaasLogAssinatura.objects.create(
                instituicao=pag.instituicao,
                fatura=pag.fatura,
                accao='PAGAMENTO_REJEITADO',
                estado_anterior='enviado',
                estado_novo='rejeitado',
                feito_por=utilizador,
                motivo=motivo
            )
            resultado = {'sucesso': True, 'mensagem': 'Pagamento rejeitado com sucesso.'}

        return Response({'success': True, 'data': resultado})


class SaasProrrogarDataLimiteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not is_superadmin_user(request.user):
            return Response({'success': False, 'message': 'Acesso restrito ao Super Administrador.'}, status=status.HTTP_403_FORBIDDEN)

        nova_data_str = request.data.get('nova_data')
        motivo = request.data.get('motivo', '').strip()

        if not nova_data_str or not motivo:
            return Response({'success': False, 'message': 'A nova data e a justificação são estritamente obrigatórias.'}, status=status.HTTP_400_BAD_REQUEST)

        fat = SaasFatura.objects.filter(id=pk).first()
        if not fat:
            return Response({'success': False, 'message': 'Fatura não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        utilizador = request.user.nome or request.user.email

        if is_postgresql():
            with connection.cursor() as cursor:
                cursor.execute("SELECT public.prorrogar_data_limite(%s, %s, %s, %s)", [str(pk), nova_data_str, motivo, utilizador])
                resultado = cursor.fetchone()[0]
        else:
            nova_data = date.fromisoformat(nova_data_str)
            fat.data_limite_manual = nova_data
            if nova_data >= timezone.localdate() and fat.estado == 'em_atraso':
                fat.estado = 'aberta'
            fat.save()

            ass = fat.assinatura
            if nova_data >= timezone.localdate() and ass.estado in ('em_atraso', 'restrita', 'suspensa'):
                ass.estado = 'fatura_pendente'
                ass.save()
                Escola.objects.filter(id=fat.instituicao_id).update(status='ATIVA')

            SaasLogAssinatura.objects.create(
                instituicao=fat.instituicao,
                assinatura=ass,
                fatura=fat,
                accao='PRORROGAR_DATA_LIMITE',
                feito_por=utilizador,
                motivo=f'Prorrogação para {nova_data}. Justificação: {motivo}'
            )
            resultado = {'sucesso': True, 'mensagem': 'Prazo prorrogado com sucesso.', 'nova_data': nova_data_str}

        limpar_cache_assinatura(fat.instituicao_id)
        return Response({'success': True, 'data': resultado})


class SaasSuspenderReactivarManualView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not is_superadmin_user(request.user):
            return Response({'success': False, 'message': 'Acesso restrito ao Super Administrador.'}, status=status.HTTP_403_FORBIDDEN)

        acao = request.data.get('acao')  # 'suspender' ou 'reactivar'
        motivo = request.data.get('motivo', '').strip()

        if not motivo:
            return Response({'success': False, 'message': 'A justificação é estritamente obrigatória.'}, status=status.HTTP_400_BAD_REQUEST)

        escola = Escola.objects.filter(id=pk).first()
        if not escola:
            return Response({'success': False, 'message': 'Instituição não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        utilizador = request.user.nome or request.user.email

        if acao == 'suspender':
            if is_postgresql():
                with connection.cursor() as cursor:
                    cursor.execute("SELECT public.suspender_manual(%s, %s, %s)", [str(pk), motivo, utilizador])
                    res = cursor.fetchone()[0]
            else:
                SaasAssinatura.objects.filter(instituicao=escola).update(estado='suspensa')
                Escola.objects.filter(id=pk).update(status='SUSPENSA', bloqueada_manualmente=True)
                SaasLogAssinatura.objects.create(
                    instituicao=escola,
                    accao='SUSPENSAO_MANUAL',
                    estado_novo='suspensa',
                    feito_por=utilizador,
                    motivo=motivo
                )
                res = {'sucesso': True, 'mensagem': 'Instituição suspensa manualmente.'}
        elif acao == 'reactivar':
            if is_postgresql():
                with connection.cursor() as cursor:
                    cursor.execute("SELECT public.reactivar_manual(%s, %s, %s)", [str(pk), motivo, utilizador])
                    res = cursor.fetchone()[0]
            else:
                SaasAssinatura.objects.filter(instituicao=escola).update(estado='activa')
                Escola.objects.filter(id=pk).update(status='ATIVA', bloqueada_manualmente=False)
                SaasLogAssinatura.objects.create(
                    instituicao=escola,
                    accao='REACTIVACAO_MANUAL',
                    estado_novo='activa',
                    feito_por=utilizador,
                    motivo=motivo
                )
                res = {'sucesso': True, 'mensagem': 'Instituição reactivada com sucesso.'}
        else:
            return Response({'success': False, 'message': 'Ação inválida.'}, status=status.HTTP_400_BAD_REQUEST)

        limpar_cache_assinatura(pk)
        return Response({'success': True, 'data': res})


class SaasRotinaDiariaManualView(APIView):
    """Execução da rotina diária de verificação e faturação SaaS"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not is_superadmin_user(request.user):
            return Response({'success': False, 'message': 'Acesso restrito ao Super Administrador.'}, status=status.HTTP_403_FORBIDDEN)

        if is_postgresql():
            with connection.cursor() as cursor:
                cursor.execute("SELECT public.gerar_faturas_do_dia()")
                faturas_geradas = cursor.fetchone()[0]
                cursor.execute("SELECT public.actualizar_estados_assinaturas()")
                estados_res = cursor.fetchone()[0]
            resultado = {
                'faturas_geradas': faturas_geradas,
                'estados_res': estados_res,
                'executado_em': str(timezone.now())
            }
        else:
            # Fallback Python para SQLite
            from .saas_services import executar_rotina_diaria_saas_python
            resultado = executar_rotina_diaria_saas_python()

        limpar_cache_assinatura()
        return Response({'success': True, 'data': resultado})


# =====================================================================
# 🏫 VISÃO ADMIN DA INSTITUIÇÃO (CLIENTE SAAS)
# =====================================================================

class MinhaAssinaturaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if getattr(user, 'role', '') in ['ALUNO', 'PROFESSOR']:
            return Response(
                {
                    'success': False,
                    'message': 'Acesso restrito. Os planos de subscrição do Super Admin aplicam-se apenas à gestão da instituição e não reflectem para os usuários escolares.'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        escola = getattr(user, 'escola', None)
        if not escola and is_superadmin_user(user):
            tenant_id = request.headers.get('X-Tenant-ID') or request.GET.get('tenant_id')
            if tenant_id:
                escola = Escola.objects.filter(id=tenant_id).first()

        if not escola:
            return Response({'success': False, 'message': 'Utilizador não associado a uma instituição.'}, status=status.HTTP_400_BAD_REQUEST)

        ass = SaasAssinatura.objects.select_related('plano').filter(instituicao=escola).order_by('-created_at').first()
        if not ass:
            plano = SaasPlano.objects.filter(activo=True).first()
            if not plano:
                plano = SaasPlano.objects.create(nome='Plano Básico', preco_mensal=Decimal('2500.00'))
            ass = SaasAssinatura.objects.create(
                instituicao=escola,
                plano=plano,
                proxima_fatura_em=timezone.localdate() + timedelta(days=30),
                estado='activa'
            )

        faturas = SaasFatura.objects.filter(instituicao=escola).order_by('-periodo_inicio')
        fatura_aberta = faturas.filter(estado__in=['aberta', 'em_atraso', 'paga_parcial']).first()

        # Alerta amigável
        alerta = None
        if ass.estado == 'em_atraso':
            alerta = {
                'tipo': 'warning',
                'titulo': 'Assinatura em Atraso',
                'mensagem': 'A sua subscrição ultrapassou a data limite. Encontra-se dentro do período de tolerância. Por favor regularize o pagamento para evitar restrição de escrita.'
            }
        elif ass.estado == 'restrita':
            alerta = {
                'tipo': 'danger',
                'titulo': 'Modo Restrito (Apenas Leitura)',
                'mensagem': 'O período de tolerância expirou. O sistema encontra-se bloqueado para alterações ou cadastros. Regularize a fatura para restabelecer o acesso total.'
            }
        elif ass.estado in ('suspensa', 'cancelada'):
            alerta = {
                'tipo': 'danger',
                'titulo': 'Acesso Suspenso',
                'mensagem': 'O acesso da instituição está suspenso. Apenas o registo de pagamentos e consulta de faturas está disponível.'
            }

        coord = SaasCoordenadasPagamento.get_singleton()
        return Response({
            'success': True,
            'data': {
                'assinatura': SaasAssinaturaSerializer(ass).data,
                'fatura_atual': SaasFaturaSerializer(fatura_aberta).data if fatura_aberta else None,
                'alerta': alerta,
                'faturas': SaasFaturaSerializer(faturas, many=True).data,
                'coordenadas': SaasCoordenadasPagamentoSerializer(coord).data,
            }
        })


class RegistarPagamentoInstituicaoView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        user = request.user
        if getattr(user, 'role', '') in ['ALUNO', 'PROFESSOR']:
            return Response(
                {
                    'success': False,
                    'message': 'Acesso restrito. Pagamentos SaaS são de competência exclusiva da administração da instituição.'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        escola = getattr(user, 'escola', None)
        if not escola and is_superadmin_user(user):
            tenant_id = request.headers.get('X-Tenant-ID') or request.data.get('instituicao_id')
            if tenant_id:
                escola = Escola.objects.filter(id=tenant_id).first()

        if not escola:
            return Response({'success': False, 'message': 'Instituição não identificada.'}, status=status.HTTP_400_BAD_REQUEST)

        fatura_id = request.data.get('fatura_id')
        metodo = request.data.get('metodo')
        referencia = request.data.get('referencia', '').strip()
        valor_raw = request.data.get('valor')
        comprovativo_file = request.FILES.get('comprovativo')
        comprovativo_base64 = request.data.get('comprovativo_base64')

        if not fatura_id or not metodo or not referencia or not valor_raw:
            return Response({'success': False, 'message': 'Fatura, método, referência e valor são obrigatórios.'}, status=status.HTTP_400_BAD_REQUEST)

        fat = SaasFatura.objects.filter(id=fatura_id, instituicao=escola).first()
        if not fat:
            return Response({'success': False, 'message': 'Fatura não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            valor = Decimal(str(valor_raw))
            if valor <= 0:
                raise ValueError()
        except Exception:
            return Response({'success': False, 'message': 'Valor de pagamento inválido.'}, status=status.HTTP_400_BAD_REQUEST)

        comprovativo_path = None
        comprovativo_url = None

        if comprovativo_file:
            ext = os.path.splitext(comprovativo_file.name)[1].lower()
            if ext not in ('.pdf', '.jpg', '.jpeg', '.png'):
                return Response({'success': False, 'message': 'Formato de ficheiro inválido. Envie PDF, JPG ou PNG.'}, status=status.HTTP_400_BAD_REQUEST)

            nome_seguro = f"comp_{uuid.uuid4().hex[:12]}{ext}"
            caminho_relativo = os.path.join('comprovativos', str(escola.id), str(fat.id), nome_seguro)
            caminho_completo = os.path.join(settings.MEDIA_ROOT, caminho_relativo)
            os.makedirs(os.path.dirname(caminho_completo), exist_ok=True)

            with open(caminho_completo, 'wb+') as dest:
                for chunk in comprovativo_file.chunks():
                    dest.write(chunk)

            comprovativo_path = caminho_relativo
            comprovativo_url = f"/media/{caminho_relativo.replace(os.sep, '/')}"

        elif comprovativo_base64:
            # Suporte para envio base64
            comprovativo_url = comprovativo_base64
            comprovativo_path = 'base64_encoded'

        pagamento = SaasPagamento.objects.create(
            fatura=fat,
            instituicao=escola,
            metodo=metodo,
            referencia=referencia,
            valor=valor,
            comprovativo_path=comprovativo_path,
            comprovativo_url=comprovativo_url,
            estado='enviado'
        )

        SaasLogAssinatura.objects.create(
            instituicao=escola,
            assinatura=fat.assinatura,
            fatura=fat,
            accao='REGISTO_PAGAMENTO_ENVIADO',
            valor_novo=valor,
            feito_por=user.nome or user.email,
            motivo=f'Comprovativo submetido pela instituição. Ref: {referencia}'
        )

        return Response({
            'success': True,
            'message': 'Comprovativo de pagamento submetido com sucesso! O Super Administrador irá validar a operação.',
            'data': SaasPagamentoSerializer(pagamento).data
        }, status=status.HTTP_201_CREATED)


class SaasCoordenadasPagamentoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        coord = SaasCoordenadasPagamento.get_singleton()
        return Response({
            'success': True,
            'data': SaasCoordenadasPagamentoSerializer(coord).data
        })

    def post(self, request):
        if not is_superadmin_user(request.user):
            return Response({'success': False, 'message': 'Acesso restrito ao Super Administrador.'}, status=status.HTTP_403_FORBIDDEN)

        coord = SaasCoordenadasPagamento.get_singleton()
        campos = [
            'mpesa_numero', 'mpesa_titular',
            'emola_numero', 'emola_titular',
            'bim_conta', 'bim_nib', 'bim_titular',
            'bci_conta', 'bci_nib', 'bci_titular',
            'nuit_entidade', 'instrucoes_adicionais'
        ]
        for c in campos:
            if c in request.data:
                setattr(coord, c, str(request.data.get(c, '')).strip())
        coord.save()

        return Response({
            'success': True,
            'message': 'Coordenadas de pagamento atualizadas com sucesso.',
            'data': SaasCoordenadasPagamentoSerializer(coord).data
        })
