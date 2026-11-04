"""Transferências & Anulações de Matrícula: processo completo (pedido → quitação → parecer do Director → guia oficial).

Isolamento por escola em todas as consultas; permissões pela Matriz Oficial (V/C/E/A).
"""
import os
from datetime import timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from rest_framework import mixins, permissions, status as http, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.audit import registrar_auditoria
from apps.accounts.models import LogAuditoria
from common.permissions.matriz import checar_permissao_matriz
from common.utils.tenant import get_tenant_escola

from . import services_transferencias as svc
from .models import Aluno, AnexoTransferencia, TransferenciaAnulacao
from .serializers import TransferenciaAnulacaoSerializer

MODULO = 'transferencias_anulacoes'
ACOES_VER = {'list', 'retrieve', 'resumo', 'exportar', 'documento', 'historico', 'anexo'}
ACOES_CRIAR = {'create', 'buscar_alunos'}
ACOES_EDITAR = {'quitacao', 'cancelar', 'anexos'}
ACOES_APROVAR = {'aprovar', 'aprovar_lote', 'rejeitar'}
EXT_ANEXO = {'.pdf': 'application/pdf', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png'}
MAX_ANEXO_BYTES = 5 * 1024 * 1024
MAX_ANEXOS = 5
PAGE_SIZE_MAX = 100
URL_BASE_PUBLICA = os.environ.get('SIGE_PUBLIC_URL', 'https://sigesaas.duckdns.org')


class PermissaoTransferencias(permissions.BasePermission):
    """V/C/E/A da matriz, conforme a acção; sem acção conhecida, nega."""

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        role = getattr(u, 'role', '')
        acao = getattr(view, 'action', None)
        if acao in ACOES_VER:
            letras = ['V']
        elif acao in ACOES_CRIAR:
            letras = ['C']
        elif acao in ACOES_APROVAR:
            letras = ['A']
        elif acao == 'anexos':
            letras = ['C', 'E'] if request.method != 'GET' else ['V']
        elif acao in ACOES_EDITAR:
            letras = ['E', 'A'] if acao == 'cancelar' else ['E']
        else:
            return False
        return any(checar_permissao_matriz(role, MODULO, l) for l in letras)


class QuitacaoIncompleta(Exception):
    def __init__(self, info):
        super().__init__('Quitação incompleta')
        self.info = info


def _em_inspeccao(user):
    return getattr(user, 'role', '') == 'SUPERADMIN'


def _sufixo_auditoria(user):
    return ' (SuperAdmin em inspecção)' if _em_inspeccao(user) else ''


class TransferenciaAnulacaoViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                                   viewsets.GenericViewSet):
    serializer_class = TransferenciaAnulacaoSerializer
    permission_classes = [PermissaoTransferencias]
    queryset = TransferenciaAnulacao.objects.none()
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    # ---------- consultas ----------
    def _base_qs(self):
        user = self.request.user
        escola = get_tenant_escola(self.request)
        qs = TransferenciaAnulacao.objects.select_related('aluno', 'aluno__turma', 'escola', 'solicitado_por',
                                                          'aprovado_por', 'rejeitado_por').prefetch_related('anexos')
        if escola:
            return qs.filter(escola=escola)
        if getattr(user, 'role', '') == 'SUPERADMIN':
            return qs
        return qs.none()

    def _filtrar(self, qs):
        p = self.request.query_params
        if p.get('tipo'):
            qs = qs.filter(tipo=p['tipo'])
        if p.get('status'):
            qs = qs.filter(status=p['status'])
        if p.get('motivo_categoria'):
            qs = qs.filter(motivo_categoria=p['motivo_categoria'])
        if p.get('classe'):
            qs = qs.filter(classe_snapshot__iexact=p['classe'])
        if p.get('turma_id'):
            qs = qs.filter(aluno__turma_id=p['turma_id'])
        if p.get('area'):
            qs = qs.filter(aluno__turma__area__iexact=p['area'])
        if p.get('ano_letivo') and p['ano_letivo'].upper() != 'TODOS':
            ano = p['ano_letivo']
            # Processos anteriores ao retrato do aluno (campo vazio) contam pelo ano do pedido.
            qs = qs.filter(Q(ano_letivo_snapshot=ano) | Q(ano_letivo_snapshot='', data_solicitacao__year=ano if ano.isdigit() else 0))
        if p.get('search'):
            s = p['search'].strip()
            qs = qs.filter(Q(aluno__nome__icontains=s) | Q(aluno__apelido__icontains=s) | Q(aluno__matricula__icontains=s)
                           | Q(guia_numero__icontains=s))
        if p.get('atrasados') in ('1', 'true'):
            limite = timezone.localdate() - timedelta(days=svc.PRAZO_ALERTA_DIAS)
            qs = qs.filter(status='PENDENTE', data_solicitacao__lt=limite)
        return qs

    def get_queryset(self):
        return self._filtrar(self._base_qs()).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        try:
            page = max(1, int(request.query_params.get('page', 1)))
            size = min(PAGE_SIZE_MAX, max(1, int(request.query_params.get('page_size', 20))))
        except ValueError:
            raise ValidationError({'page': 'Paginação inválida.'})
        total = qs.count()
        itens = list(qs[(page - 1) * size: page * size])
        dados = self.get_serializer(itens, many=True).data
        return Response({'success': True, 'data': dados, 'count': total, 'page': page,
                         'pages': max(1, -(-total // size)), 'page_size': size})

    def retrieve(self, request, *args, **kwargs):
        return Response({'success': True, 'data': self.get_serializer(self.get_object()).data})

    # ---------- criação ----------
    def create(self, request, *args, **kwargs):
        escola = get_tenant_escola(request)
        if not escola:
            raise ValidationError({'escola': 'Nenhuma instituição identificada.'})
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        tipo = d['tipo']
        cat = d.get('motivo_categoria') or 'OUTRO'
        motivo = (d.get('motivo') or '').strip()
        if cat == 'OUTRO' and not motivo:
            raise ValidationError({'motivo': 'Indique o motivo quando a categoria é "Outro".'})
        origem = (d.get('escola_origem_destino') or '').strip()
        if tipo in ('TRANSFERENCIA_SAIDA', 'TRANSFERENCIA_ENTRADA') and not origem:
            raise ValidationError({'escola_origem_destino': 'Indique a escola de destino (saída) ou de origem (entrada).'})

        with transaction.atomic():
            novo = False
            if tipo == 'TRANSFERENCIA_ENTRADA':
                aluno = self._criar_aluno_entrada(escola, request.data.get('novo_aluno') or {})
                novo = True
            else:
                aluno = d.get('aluno')
                if not aluno:
                    raise ValidationError({'aluno': 'Seleccione o aluno.'})
                if aluno.escola_id != escola.id:
                    raise ValidationError({'aluno': 'O aluno não pertence a esta escola.'})
                if aluno.status != 'ATIVO':
                    raise ValidationError({'aluno': f'O aluno está "{aluno.status}" e não pode iniciar este processo.'})
                if TransferenciaAnulacao.objects.filter(aluno=aluno, status='PENDENTE').exists():
                    raise ValidationError({'aluno': 'Já existe um processo pendente para este aluno.'})

            t = TransferenciaAnulacao.objects.create(
                escola=escola, aluno=aluno, tipo=tipo, escola_origem_destino=origem, motivo=motivo,
                motivo_categoria=cat, observacoes=d.get('observacoes') or '', solicitado_por=request.user,
                classe_snapshot=(aluno.turma.grau_ano if aluno.turma else aluno.classe) or '',
                turma_snapshot=aluno.turma.nome if aluno.turma else '',
                ano_letivo_snapshot=(aluno.turma.ano_letivo if aluno.turma else aluno.ano_ingresso) or '',
                estado_anterior_aluno='' if novo else aluno.status,
            )
        registrar_auditoria(request.user, escola, 'TRANSFERENCIA', 'CRIACAO', t.id,
                            f'Solicitação de {t.get_tipo_display()} para o aluno {aluno.nome_completo}{_sufixo_auditoria(request.user)}')
        return Response({'success': True, 'data': self.get_serializer(t).data}, status=http.HTTP_201_CREATED)

    def _criar_aluno_entrada(self, escola, dados):
        obrig = ['nome', 'data_nascimento', 'genero', 'classe']
        faltam = {k: 'Obrigatório.' for k in obrig if not str(dados.get(k) or '').strip()}
        if faltam:
            raise ValidationError({'novo_aluno': faltam})
        genero = str(dados['genero']).strip().upper()[:1]
        if genero not in ('M', 'F'):
            raise ValidationError({'novo_aluno': {'genero': 'Use M ou F.'}})
        try:
            aluno = Aluno(
                escola=escola, nome=str(dados['nome']).strip(), apelido=str(dados.get('apelido') or '').strip() or None,
                data_nascimento=dados['data_nascimento'], genero=genero, classe=str(dados['classe']).strip(),
                nome_responsavel=str(dados.get('nome_responsavel') or '').strip() or None,
                contato_responsavel=str(dados.get('contato_responsavel') or '').strip() or None,
                status='PENDENTE',
            )
            aluno.save()
        except DjangoValidationError as e:
            raise ValidationError({'novo_aluno': e.message_dict if hasattr(e, 'error_dict') else e.messages})
        return aluno

    @action(detail=False, methods=['get'], url_path='buscar-alunos')
    def buscar_alunos(self, request):
        escola = get_tenant_escola(request)
        q = (request.query_params.get('q') or '').strip()
        if not escola or len(q) < 2:
            return Response({'success': True, 'data': []})
        qs = (Aluno.objects.filter(escola=escola, status='ATIVO')
              .filter(Q(nome__icontains=q) | Q(apelido__icontains=q) | Q(matricula__icontains=q))
              .select_related('turma').order_by('nome')[:15])
        return Response({'success': True, 'data': [{
            'id': str(a.id), 'nome': a.nome_completo, 'matricula': a.matricula,
            'classe': (a.turma.grau_ano if a.turma else a.classe) or '', 'turma': a.turma.nome if a.turma else '',
        } for a in qs]})

    # ---------- parecer do Director ----------
    def _aprovar_um(self, t, user, ignorar=False, justificacao=''):
        if t.status != 'PENDENTE':
            raise ValidationError({'status': 'Só processos pendentes podem ser homologados.'})
        if t.tipo != 'TRANSFERENCIA_ENTRADA':
            info = svc.quitacao_info(t)
            if not info['completa']:
                if not ignorar:
                    raise QuitacaoIncompleta(info)
                if len((justificacao or '').strip()) < 10:
                    raise ValidationError({'justificacao': 'Justifique a dispensa da quitação (mínimo 10 caracteres).'})
                t.quitacao_dispensada = True
                t.quitacao_justificacao = justificacao.strip()
        with transaction.atomic():
            svc.atribuir_numero_oficial(t)
            t.status = 'APROVADO'
            t.aprovado_por = user
            t.data_aprovacao = timezone.now()
            t.save()
            aluno = t.aluno
            novo_estado = {'TRANSFERENCIA_SAIDA': 'TRANSFERIDO', 'ANULACAO_MATRICULA': 'INATIVO',
                           'TRANSFERENCIA_ENTRADA': 'ATIVO'}[t.tipo]
            aluno.status = novo_estado
            aluno.save(update_fields=['status'])
        extra = ' com dispensa de quitação: ' + t.quitacao_justificacao if t.quitacao_dispensada else ''
        registrar_auditoria(user, t.escola, 'TRANSFERENCIA', 'APROVACAO', t.id,
                            f'Homologação de {t.get_tipo_display()} ({t.numero_guia_oficial}) pelo Director{extra}{_sufixo_auditoria(user)}')
        return t

    @action(detail=True, methods=['post'], url_path='aprovar')
    def aprovar(self, request, pk=None):
        t = self.get_object()
        try:
            self._aprovar_um(t, request.user, bool(request.data.get('ignorar_quitacao')), str(request.data.get('justificacao') or ''))
        except QuitacaoIncompleta as e:
            return Response({'success': False, 'codigo': 'QUITACAO_INCOMPLETA', 'quitacao_info': e.info,
                             'message': 'Quitação incompleta: propinas em dívida ou itens por confirmar. '
                                        'O Director pode dispensar com justificação.'}, status=http.HTTP_400_BAD_REQUEST)
        return Response({'success': True, 'message': f'{t.get_tipo_display()} aprovada com sucesso!',
                         'data': self.get_serializer(t).data})

    @action(detail=False, methods=['post'], url_path='aprovar-lote')
    def aprovar_lote(self, request):
        ids = request.data.get('ids') or []
        if not isinstance(ids, list) or not ids or len(ids) > 100:
            raise ValidationError({'ids': 'Indique entre 1 e 100 processos.'})
        aprovados, falhas = [], []
        for t in self._base_qs().filter(id__in=ids):
            try:
                self._aprovar_um(t, request.user)
                aprovados.append(str(t.id))
            except QuitacaoIncompleta:
                falhas.append({'id': str(t.id), 'aluno': t.aluno.nome_completo, 'motivo': 'Quitação incompleta'})
            except ValidationError:
                falhas.append({'id': str(t.id), 'aluno': t.aluno.nome_completo, 'motivo': 'Não elegível'})
        return Response({'success': True, 'aprovados': aprovados, 'falhas': falhas})

    @action(detail=True, methods=['post'], url_path='rejeitar')
    def rejeitar(self, request, pk=None):
        t = self.get_object()
        motivo = str(request.data.get('motivo') or '').strip()
        if len(motivo) < 5:
            raise ValidationError({'motivo': 'Indique o motivo da rejeição (mínimo 5 caracteres).'})
        self._encerrar(t, 'REJEITADO', request.user, motivo)
        registrar_auditoria(request.user, t.escola, 'TRANSFERENCIA', 'REJEICAO', t.id,
                            f'Rejeição de {t.get_tipo_display()}: {motivo}{_sufixo_auditoria(request.user)}')
        return Response({'success': True, 'data': self.get_serializer(t).data})

    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar(self, request, pk=None):
        t = self.get_object()
        motivo = str(request.data.get('motivo') or '').strip() or 'Cancelado pelo solicitante'
        self._encerrar(t, 'CANCELADO', request.user, motivo)
        registrar_auditoria(request.user, t.escola, 'TRANSFERENCIA', 'CANCELAMENTO', t.id,
                            f'Cancelamento de {t.get_tipo_display()}: {motivo}{_sufixo_auditoria(request.user)}')
        return Response({'success': True, 'data': self.get_serializer(t).data})

    def _encerrar(self, t, novo_status, user, motivo):
        if t.status != 'PENDENTE':
            raise ValidationError({'status': 'Só processos pendentes podem ser encerrados.'})
        with transaction.atomic():
            t.status = novo_status
            t.motivo_rejeicao = motivo
            t.rejeitado_por = user
            t.data_rejeicao = timezone.now()
            t.save()
            if t.tipo == 'TRANSFERENCIA_ENTRADA' and t.aluno.status == 'PENDENTE':
                t.aluno.status = 'INATIVO'
                t.aluno.save(update_fields=['status'])

    # ---------- quitação ----------
    @action(detail=True, methods=['post'], url_path='quitacao')
    def quitacao(self, request, pk=None):
        t = self.get_object()
        if t.status != 'PENDENTE':
            raise ValidationError({'status': 'A quitação só se altera em processos pendentes.'})
        q = dict(t.quitacao or {})
        for k in svc.ITENS_QUITACAO_MANUAIS:
            if k in request.data:
                q[k] = bool(request.data.get(k))
        t.quitacao = q
        t.save(update_fields=['quitacao', 'updated_at'])
        registrar_auditoria(request.user, t.escola, 'TRANSFERENCIA', 'QUITACAO', t.id,
                            f'Quitação actualizada: {q}{_sufixo_auditoria(request.user)}')
        return Response({'success': True, 'data': self.get_serializer(t).data})

    # ---------- anexos ----------
    @action(detail=True, methods=['get', 'post'], url_path='anexos')
    def anexos(self, request, pk=None):
        t = self.get_object()
        if request.method == 'GET':
            return Response({'success': True, 'data': self.get_serializer(t).data['anexos']})
        f = request.FILES.get('ficheiro')
        if not f:
            raise ValidationError({'ficheiro': 'Envie um ficheiro.'})
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in EXT_ANEXO:
            raise ValidationError({'ficheiro': 'Formato não permitido (use PDF, JPG ou PNG).'})
        if f.size > MAX_ANEXO_BYTES:
            raise ValidationError({'ficheiro': 'Ficheiro acima de 5 MB.'})
        if t.anexos.count() >= MAX_ANEXOS:
            raise ValidationError({'ficheiro': f'Máximo de {MAX_ANEXOS} anexos por processo.'})
        a = AnexoTransferencia.objects.create(transferencia=t, ficheiro=f, nome_original=os.path.basename(f.name)[:255],
                                              content_type=EXT_ANEXO[ext], tamanho=f.size, carregado_por=request.user)
        registrar_auditoria(request.user, t.escola, 'TRANSFERENCIA', 'ANEXO', t.id, f'Anexo adicionado: {a.nome_original}')
        t = self._base_qs().get(id=t.id)
        return Response({'success': True, 'data': self.get_serializer(t).data['anexos']}, status=http.HTTP_201_CREATED)

    @action(detail=True, methods=['get', 'delete'], url_path=r'anexos/(?P<anexo_id>[0-9a-f-]+)')
    def anexo(self, request, pk=None, anexo_id=None):
        t = self.get_object()
        a = t.anexos.filter(id=anexo_id).first()
        if not a:
            return Response({'success': False, 'message': 'Anexo não encontrado.'}, status=http.HTTP_404_NOT_FOUND)
        if request.method == 'DELETE':
            if not checar_permissao_matriz(getattr(request.user, 'role', ''), MODULO, 'E'):
                return Response({'success': False, 'message': 'Sem permissão.'}, status=http.HTTP_403_FORBIDDEN)
            a.ficheiro.delete(save=False)
            a.delete()
            return Response({'success': True})
        resp = FileResponse(a.ficheiro.open('rb'), content_type=a.content_type or 'application/octet-stream')
        resp['Content-Disposition'] = f'attachment; filename="{a.nome_original}"'
        return resp

    # ---------- documento oficial ----------
    @action(detail=True, methods=['get'], url_path='documento')
    def documento(self, request, pk=None):
        t = self.get_object()
        if t.status != 'APROVADO' or not t.numero_sequencial:
            raise ValidationError({'status': 'O documento só é emitido após a aprovação do Director.'})
        pdf = svc.gerar_pdf_documento(t, URL_BASE_PUBLICA)
        resp = HttpResponse(pdf, content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="{t.numero_guia_oficial}.pdf"'
        return resp

    # ---------- linha do tempo ----------
    @action(detail=True, methods=['get'], url_path='historico')
    def historico(self, request, pk=None):
        t = self.get_object()
        logs = LogAuditoria.objects.filter(entidade='TRANSFERENCIA', objeto_id=str(t.id)).order_by('created_at')
        return Response({'success': True, 'data': [{
            'acao': l.acao, 'descricao': l.descricao, 'usuario': l.usuario_nome, 'perfil': l.usuario_role,
            'data': l.created_at.isoformat(),
        } for l in logs]})

    # ---------- resumo e exportação ----------
    @action(detail=False, methods=['get'], url_path='resumo')
    def resumo(self, request):
        qs = self._base_qs()
        ano = str(timezone.now().year)
        limite = timezone.localdate() - timedelta(days=svc.PRAZO_ALERTA_DIAS)
        aprov_ano = qs.filter(status='APROVADO', data_aprovacao__year=ano)
        motivos = {m['motivo_categoria']: m['n'] for m in aprov_ano.values('motivo_categoria').annotate(n=Count('id'))}
        return Response({'success': True, 'data': {
            'pendentes': qs.filter(status='PENDENTE').count(),
            'atrasados': qs.filter(status='PENDENTE', data_solicitacao__lt=limite).count(),
            'prazo_alerta_dias': svc.PRAZO_ALERTA_DIAS,
            'aprovados_ano': aprov_ano.count(),
            'saidas_ano': aprov_ano.filter(tipo='TRANSFERENCIA_SAIDA').count(),
            'entradas_ano': aprov_ano.filter(tipo='TRANSFERENCIA_ENTRADA').count(),
            'anulacoes_ano': aprov_ano.filter(tipo='ANULACAO_MATRICULA').count(),
            'motivos_ano': motivos,
            'ano': ano,
        }})

    @action(detail=False, methods=['get'], url_path='exportar')
    def exportar(self, request):
        formato = (request.query_params.get('formato') or 'xlsx').lower()
        if formato not in ('xlsx', 'pdf'):
            raise ValidationError({'formato': 'Use xlsx ou pdf.'})
        itens = list(self.get_queryset()[:5000])
        if formato == 'xlsx':
            resp = HttpResponse(svc.gerar_xlsx_lista(itens),
                                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        else:
            resp = HttpResponse(svc.gerar_pdf_lista(itens, get_tenant_escola(request)), content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="transferencias.{formato}"'
        return resp


class VerificarTransferenciaView(APIView):
    """Verificação pública (QR da guia): só dados mínimos, com o nome do aluno abreviado."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_scope = 'verificacao'

    def get(self, request, codigo):
        t = (TransferenciaAnulacao.objects.select_related('aluno', 'escola')
             .filter(codigo_verificacao__iexact=(codigo or '').strip(), status='APROVADO').first())
        if not t:
            return Response({'success': False, 'autentico': False,
                             'message': 'Documento não encontrado ou código inválido.'}, status=http.HTTP_404_NOT_FOUND)
        partes = t.aluno.nome_completo.split()
        abreviado = partes[0] + ''.join(f' {p[0].upper()}.' for p in partes[1:])
        return Response({'success': True, 'autentico': True, 'data': {
            'tipo': t.get_tipo_display(), 'numero': t.numero_guia_oficial, 'escola': t.escola.nome,
            'aluno': abreviado, 'data_aprovacao': t.data_aprovacao.date().isoformat() if t.data_aprovacao else None,
        }})
