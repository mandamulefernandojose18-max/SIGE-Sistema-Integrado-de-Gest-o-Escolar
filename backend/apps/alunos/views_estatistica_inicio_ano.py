"""Endpoints do Mapa Estatístico de Início do Ano (turma, classe, escola) em JSON, PDF e Excel."""
import re
import unicodedata

from django.http import HttpResponse
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.disciplinas import plano
from common.utils.tenant import get_tenant_escola

from . import estatistica_inicio_ano as est

PERFIS_GESTAO = ('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP')


def _nome_ficheiro(texto):
    ascii_ = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode()
    return re.sub(r'[^A-Za-z0-9_.-]+', '_', ascii_).strip('_') or 'Estatistica'


def _escola_ou_400(request):
    escola = get_tenant_escola(request)
    if not escola:
        raise ValidationError({'detail': 'Instituição não identificada.'})
    return escola


def _e_gestao(user):
    return getattr(user, 'role', '') in PERFIS_GESTAO


def _professor_id(user):
    return getattr(user, 'professor_id', None)


def _ano(request):
    ano = (request.query_params.get('anoLetivo') or request.query_params.get('ano') or '').strip()
    if not re.fullmatch(r'\d{4}', ano):
        raise ValidationError({'detail': 'Indique o ano lectivo (AAAA).'})
    return ano


def _turma_ou_404(escola, turma_id):
    from apps.turmas.models import Turma
    try:
        return Turma.objects.select_related('director_turma', 'director_classe').get(id=turma_id, escola=escola)
    except Turma.DoesNotExist as exc:  # inexistente ou de outra escola
        raise NotFound('Turma não encontrada.') from exc


def _pode_ver_turma(user, turma):
    if _e_gestao(user):
        return True
    pid = _professor_id(user)
    return bool(pid) and (turma.director_turma_id == pid or turma.director_classe_id == pid)


def _pode_ver_classe(user, escola, classe, ano):
    if _e_gestao(user):
        return True
    pid = _professor_id(user)
    if not pid:
        return False
    return any(t.director_classe_id == pid for t in est._turmas_do_ano(escola, ano, classe))


def _resposta(formato, escola, dados, nome_base):
    from apps.documentos.services import estatistica_inicio_ano_docs as docs
    from apps.documentos.services.pdf_service import DocumentoSemLogoError
    if formato not in ('pdf', 'xlsx'):
        # As mesmas tabelas que saem no PDF/Excel: o ecrã mostra exactamente o que será impresso.
        return Response({'success': True, 'data': dict(dados, paginas=docs.montar_paginas(dados))})
    try:
        if formato == 'pdf':
            conteudo = docs.gerar_estatistica_inicio_ano_pdf(escola, dados)
            tipo, ext = 'application/pdf', 'pdf'
        else:
            conteudo = docs.gerar_estatistica_inicio_ano_xlsx(escola, dados)
            tipo, ext = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'xlsx'
    except DocumentoSemLogoError as e:
        return Response({'detail': str(e), 'message': str(e)}, status=409)
    resp = HttpResponse(conteudo, content_type=tipo)
    resp['Content-Disposition'] = f'attachment; filename="{_nome_ficheiro(nome_base)}.{ext}"'
    return resp


class EstatisticaInicioAnoTurmaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, turma_id, formato=None):
        escola = _escola_ou_400(request)
        turma = _turma_ou_404(escola, turma_id)
        if not _pode_ver_turma(request.user, turma):
            raise PermissionDenied('Apenas o Director da Turma, o Director da Classe ou a gestão pedagógica podem ver este mapa.')
        dados = est.compilar_turma(escola, turma)
        return _resposta(formato, escola, dados, f'Estatistica_Inicio_Ano_{turma.nome}_{turma.ano_letivo}')


class EstatisticaInicioAnoClasseView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, formato=None):
        escola = _escola_ou_400(request)
        ano = _ano(request)
        classe = (request.query_params.get('classe') or '').strip()
        if not classe:
            raise ValidationError({'detail': 'Indique a classe.'})
        if not _pode_ver_classe(request.user, escola, classe, ano):
            raise PermissionDenied('Apenas o Director da Classe ou a gestão pedagógica podem ver este mapa.')
        dados = est.compilar_classe(escola, classe, ano)
        return _resposta(formato, escola, dados, f'Estatistica_Inicio_Ano_{dados["classe"]}_{ano}')


class EstatisticaInicioAnoEscolaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, formato=None):
        escola = _escola_ou_400(request)
        if not _e_gestao(request.user):
            raise PermissionDenied('O mapa geral da escola é reservado à gestão pedagógica.')
        ano = _ano(request)
        dados = est.compilar_escola(escola, ano)
        return _resposta(formato, escola, dados, f'Estatistica_Inicio_Ano_Escola_{ano}')


class EstatisticaInicioAnoMinhasView(APIView):
    """Turmas e classes que o professor autenticado dirige (para os painéis do Director de Turma/Classe)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.turmas.models import Turma
        escola = _escola_ou_400(request)
        ano = _ano(request)
        pid = _professor_id(request.user)
        turmas = Turma.objects.filter(escola=escola, ano_letivo=ano)
        dt = [t for t in turmas.filter(director_turma_id=pid)] if pid else []
        dc_turmas = [t for t in turmas.filter(director_classe_id=pid)] if pid else []
        classes = sorted({plano.nome_classe_oficial(escola, t.grau_ano) or t.grau_ano for t in dc_turmas},
                         key=est._chave_classe_ordenacao)
        return Response({'success': True, 'data': {
            'turmas_dt': [{'id': str(t.id), 'nome': t.nome, 'classe': t.grau_ano, 'area': t.area or 'Geral'} for t in dt],
            'classes_dc': classes,
        }})
