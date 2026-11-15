"""
SIGE — API do Calendário de Exames e Júris.

  GET    /api/v1/notas/calendario-exames/?ano=&classe=          linhas por disciplina com exame (1ª e 2ª chamada)
  POST   /api/v1/notas/calendario-exames/                       grava (upsert) {ano_letivo, classe, itens:[...]}
  DELETE /api/v1/notas/calendario-exames/<id>/
  GET    /api/v1/notas/juris-exame/?ano=&epoca=&classe=         júris formados (com nota de frequência)
  POST   /api/v1/notas/juris-exame/formar/                      forma os júris automaticamente
  GET    /api/v1/notas/juris-exame/pdf/?ano=&epoca=&classe=     PDF dos júris
  GET    /api/v1/notas/juris-exame/excluidos/?ano=&classe=      lista de excluídos (JSON)
  GET    /api/v1/notas/juris-exame/excluidos/pdf/?ano=&classe=  PDF dos excluídos

Tudo isolado por escola. Só leitura para o corpo docente; gravação para Direcção, Administração e DAP.
"""
import datetime as dt

from django.http import HttpResponse
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.audit import registrar_auditoria
from common.utils.tenant import get_tenant_escola

from . import exames_servico as svc
from .models import CalendarioExame

ROLES_ESCRITA = {'SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'}
ROLES_SEM_ACESSO = {'ALUNO', 'ENCARREGADO'}
PERIODOS = {'MANHA', 'TARDE', 'NOITE'}


class PodeVerExames(BasePermission):
    message = 'O seu perfil não pode consultar a gestão de exames.'

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and getattr(u, 'role', '') not in ROLES_SEM_ACESSO)


def _escola(request):
    escola = get_tenant_escola(request)
    if not escola:
        raise PermissionDenied('Nenhuma escola associada ao pedido.')
    return escola


def _exigir_escrita(request):
    if getattr(request.user, 'role', '') not in ROLES_ESCRITA and not getattr(request.user, 'is_superuser', False):
        raise PermissionDenied('Só a Direcção, a Administração ou o DAP podem alterar o calendário e os júris.')


def _ano(request, escola):
    return str(request.query_params.get('ano') or escola.ano_letivo_ativo)


def _epoca(valor, padrao=1):
    try:
        e = int(valor or padrao)
    except (TypeError, ValueError):
        e = 0
    if e not in (1, 2):
        raise svc.ErroCalendario('Época inválida: use 1 (1ª chamada) ou 2 (2ª chamada).')
    return e


def _erro(msg, status=400):
    return Response({'success': False, 'message': msg}, status=status)


def serializar_entrada(c):
    return {
        'id': str(c.id), 'data': c.data.isoformat(), 'periodo': c.periodo,
        'hora_inicio': c.hora_inicio.strftime('%H:%M'), 'hora_fim': c.hora_fim.strftime('%H:%M'),
        'duracao_minutos': c.duracao_minutos,
    }


class CalendarioExamesView(APIView):
    permission_classes = [IsAuthenticated, PodeVerExames]

    def get(self, request):
        escola = _escola(request)
        ano = _ano(request, escola)
        classe = request.query_params.get('classe')
        classes = svc.classes_da_escola(escola, ano)
        if not classe:
            return Response({'success': True, 'data': {'ano': ano, 'classes': classes, 'linhas': []}})
        grupos = svc.analisar_classe(escola, ano, classe)
        entradas = {}
        for c in CalendarioExame.objects.filter(escola=escola, ano_letivo=ano, classe=classe):
            entradas.setdefault(svc.chave_disciplina(c.disciplina), {})[c.epoca] = c
        linhas = []
        chaves = list(grupos) + [k for k in entradas if k not in grupos]
        for chave in chaves:
            g = grupos.get(chave)
            ents = entradas.get(chave, {})
            nome = g['nome'] if g else next(iter(ents.values())).disciplina
            linhas.append({
                'disciplina': nome,
                'admitidos': len(svc.candidatos_da_epoca(g, 1)) if g else 0,
                'excluidos': len(svc.excluidos(g)) if g else 0,
                'chamadas': {str(e): serializar_entrada(ents[e]) if e in ents else None for e in (1, 2)},
            })
        return Response({'success': True, 'data': {'ano': ano, 'classes': classes, 'linhas': linhas}})

    def post(self, request):
        _exigir_escrita(request)
        escola = _escola(request)
        corpo = request.data or {}
        ano = str(corpo.get('ano_letivo') or escola.ano_letivo_ativo)
        classe = str(corpo.get('classe') or '').strip()
        itens = corpo.get('itens')
        if not classe or not isinstance(itens, list):
            return _erro('Indique a classe e a lista de datas a gravar.')
        guardados = 0
        try:
            for it in itens:
                disciplina = str(it.get('disciplina') or '').strip()
                epoca = _epoca(it.get('epoca'))
                if not disciplina:
                    return _erro('Disciplina em falta.')
                existente = CalendarioExame.objects.filter(
                    escola=escola, ano_letivo=ano, classe=classe, disciplina=disciplina, epoca=epoca).first()
                if not it.get('data'):
                    if existente:
                        existente.delete()
                    continue
                periodo = str(it.get('periodo') or '').upper()
                if periodo not in PERIODOS:
                    return _erro(f'{disciplina} ({epoca}ª época): o período (Manhã, Tarde ou Noturno) é obrigatório.')
                try:
                    data = dt.date.fromisoformat(str(it['data']))
                    inicio = dt.time.fromisoformat(str(it.get('hora_inicio') or ''))
                    duracao = int(it.get('duracao_minutos'))
                except (ValueError, TypeError, KeyError):
                    return _erro(f'{disciplina} ({epoca}ª época): data, hora inicial e duração são obrigatórias.')
                if not 10 <= duracao <= 480:
                    return _erro(f'{disciplina} ({epoca}ª época): a duração deve ficar entre 10 e 480 minutos.')
                fim_dt = dt.datetime.combine(data, inicio) + dt.timedelta(minutes=duracao)
                if fim_dt.date() != data:
                    return _erro(f'{disciplina} ({epoca}ª época): o exame não pode passar da meia-noite.')
                svc.validar_conflitos(escola, ano, classe, disciplina, epoca, data, inicio, fim_dt.time())
                CalendarioExame.objects.update_or_create(
                    escola=escola, ano_letivo=ano, classe=classe, disciplina=disciplina, epoca=epoca,
                    defaults={'data': data, 'periodo': periodo, 'hora_inicio': inicio, 'duracao_minutos': duracao})
                guardados += 1
        except svc.ErroCalendario as e:
            return _erro(str(e))
        registrar_auditoria(request.user, escola, 'EXAME', 'CALENDARIO', '', f'Calendário de exames {classe} {ano}: {guardados} data(s) gravada(s)')
        return Response({'success': True, 'message': 'Calendário de exames guardado.', 'guardados': guardados})


class CalendarioExameDetalheView(APIView):
    permission_classes = [IsAuthenticated, PodeVerExames]

    def delete(self, request, pk):
        _exigir_escrita(request)
        escola = _escola(request)
        c = CalendarioExame.objects.filter(escola=escola, pk=pk).first()
        if not c:
            return _erro('Registo não encontrado.', 404)
        c.delete()
        return Response({'success': True})


class JurisExameView(APIView):
    permission_classes = [IsAuthenticated, PodeVerExames]

    def get(self, request):
        escola = _escola(request)
        try:
            epoca = _epoca(request.query_params.get('epoca'))
        except svc.ErroCalendario as e:
            return _erro(str(e))
        juris = svc.listar_juris(escola, _ano(request, escola), epoca, request.query_params.get('classe') or None,
                                 request.query_params.get('disciplina') or None)
        return Response({'success': True, 'data': juris})


class FormarJurisView(APIView):
    permission_classes = [IsAuthenticated, PodeVerExames]

    def post(self, request):
        _exigir_escrita(request)
        escola = _escola(request)
        corpo = request.data or {}
        try:
            epoca = _epoca(corpo.get('epoca'))
            maximo = int(corpo.get('max_alunos'))
            salas = corpo.get('num_salas')
            salas = int(salas) if salas not in (None, '', 0, '0') else None
        except (ValueError, TypeError, svc.ErroCalendario):
            return _erro('Indique a época e o número máximo de alunos por júri (número inteiro).')
        if not 1 <= maximo <= 500:
            return _erro('O número máximo de alunos por júri deve ficar entre 1 e 500.')
        if salas is not None and not 1 <= salas <= 500:
            return _erro('O número de salas deve ficar entre 1 e 500.')
        ano = str(corpo.get('ano_letivo') or escola.ano_letivo_ativo)
        try:
            res = svc.formar_juris(escola, ano, epoca, maximo, salas, (corpo.get('classe') or None))
        except svc.ErroCalendario as e:
            return _erro(str(e))
        registrar_auditoria(request.user, escola, 'EXAME', 'JURIS', '', f'Júris formados ({epoca}ª época, {ano}): {res["juris_formados"]} júri(s), {res["alunos_alocados"]} aluno(s)')
        return Response({'success': True, 'data': res})


def _pdf_resposta(conteudo, nome):
    r = HttpResponse(conteudo, content_type='application/pdf')
    r['Content-Disposition'] = f'attachment; filename="{nome}"'
    return r


class JurisExamePdfView(APIView):
    permission_classes = [IsAuthenticated, PodeVerExames]

    def get(self, request):
        from apps.documentos.services.pdf_service import DocumentoSemLogoError
        from .exames_pdf import pdf_juris
        escola = _escola(request)
        ano = _ano(request, escola)
        try:
            epoca = _epoca(request.query_params.get('epoca'))
        except svc.ErroCalendario as e:
            return _erro(str(e))
        juris = svc.listar_juris(escola, ano, epoca, request.query_params.get('classe') or None,
                                 request.query_params.get('disciplina') or None)
        try:
            pdf = pdf_juris(escola, ano, epoca, juris)
        except DocumentoSemLogoError as e:
            return Response({'detail': str(e), 'message': str(e)}, status=409)
        return _pdf_resposta(pdf, f'juris_exame_{epoca}a_epoca_{ano}.pdf')


def _grupos_excluidos(escola, ano, classe):
    return [(g['nome'], svc.excluidos(g)) for g in svc.analisar_classe(escola, ano, classe).values()]


class ExcluidosExameView(APIView):
    permission_classes = [IsAuthenticated, PodeVerExames]

    def get(self, request):
        escola = _escola(request)
        classe = request.query_params.get('classe')
        if not classe:
            return _erro('Escolha a classe.')
        dados = [{
            'disciplina': nome,
            'alunos': [{'nome': a['nome'], 'matricula': a['aluno'].matricula, 'turma': a['turma'], 'freq': a['freq']}
                       for a in lista],
        } for nome, lista in _grupos_excluidos(escola, _ano(request, escola), classe)]
        return Response({'success': True, 'data': dados})


class ExcluidosExamePdfView(APIView):
    permission_classes = [IsAuthenticated, PodeVerExames]

    def get(self, request):
        from apps.documentos.services.pdf_service import DocumentoSemLogoError
        from .exames_pdf import pdf_excluidos
        escola = _escola(request)
        classe = request.query_params.get('classe')
        if not classe:
            return _erro('Escolha a classe.')
        ano = _ano(request, escola)
        try:
            pdf = pdf_excluidos(escola, ano, classe, _grupos_excluidos(escola, ano, classe))
        except DocumentoSemLogoError as e:
            return Response({'detail': str(e), 'message': str(e)}, status=409)
        return _pdf_resposta(pdf, f'excluidos_exame_{ano}.pdf')


class CalendarioExamesPdfView(APIView):
    permission_classes = [IsAuthenticated, PodeVerExames]

    def get(self, request):
        from apps.documentos.services.pdf_service import DocumentoSemLogoError
        from .exames_pdf import pdf_calendario
        escola = _escola(request)
        ano = _ano(request, escola)
        qs = CalendarioExame.objects.filter(escola=escola, ano_letivo=ano)
        classe = request.query_params.get('classe')
        classes = [classe] if classe else svc.classes_da_escola(escola, ano)
        grupos = [(c, list(qs.filter(classe=c).order_by('data', 'hora_inicio', 'disciplina', 'epoca'))) for c in classes]
        try:
            pdf = pdf_calendario(escola, ano, grupos)
        except DocumentoSemLogoError as e:
            return Response({'detail': str(e), 'message': str(e)}, status=409)
        return _pdf_resposta(pdf, f'calendario_exames_{ano}.pdf')
