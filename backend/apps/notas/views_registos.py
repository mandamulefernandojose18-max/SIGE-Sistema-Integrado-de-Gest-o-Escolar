"""
SIGE — Registo das correcções automáticas concluídas («Provas corrigidas»).

  GET    /api/v1/notas/provas-fisicas/registos/?turma_id=&disciplina_id=&periodo=   lista (data, duração, nº de folhas)
  POST   /api/v1/notas/provas-fisicas/<id>/registos/      {duracao_seg, n_folhas} → guarda o registo + listas PDF/Excel
  GET    /api/v1/notas/provas-fisicas/registos/<rid>/ficheiro/?t=pdf|xlsx|folhas|zip   descarrega / exporta
  DELETE /api/v1/notas/provas-fisicas/registos/<rid>/    elimina só o registo e as listas guardadas

Eliminar um registo nunca altera notas, correcções nem cadernetas. Isolamento por escola e permissões iguais às
da correcção (professor alocado e SUPERADMIN escrevem; Direcção, Administração e DAP só consultam).
"""
import io
import os
import re
import zipfile
from urllib.parse import quote

from django.conf import settings
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import correcao_servico as svc
from . import lista_avaliacao as la
from .models import CorrecaoRegisto
from .views_correcao import (FolhasCorrigidasPdfView, ROLES_LEITURA, _e_super, _erro, _escola, _pode, _prova, _uuid)

MIME_XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def _json(r):
    p = r.prova
    return {
        'id': str(r.id), 'prova_id': str(p.id), 'titulo': p.titulo, 'disciplina_nome': p.disciplina.nome,
        'turma_nome': p.turma.nome, 'periodo': p.periodo, 'instrumento_nome': p.get_instrumento_display(),
        'ano_letivo': p.turma.ano_letivo, 'duracao_seg': r.duracao_seg, 'n_folhas': r.n_folhas,
        'created_at': r.created_at.isoformat(), 'tem_listas': bool(r.caminho_pdf and r.caminho_xlsx),
    }


def _abs(escola, caminho):
    """Caminho absoluto, só se estiver dentro da pasta da escola dona."""
    if not caminho:
        return None
    raiz = svc.raiz_imagens(escola)
    p = os.path.realpath(os.path.join(settings.MEDIA_ROOT, caminho))
    return p if p.startswith(raiz + os.sep) and os.path.isfile(p) else None


def _guardar(escola, rid, ext, dados):
    rel = os.path.join('provas_fisicas', str(escola.id), 'registos', f'{rid}.{ext}')
    ab = os.path.join(settings.MEDIA_ROOT, rel)
    os.makedirs(os.path.dirname(ab), exist_ok=True)
    with open(ab, 'wb') as fh:
        fh.write(dados)
    return rel


def _nome(base):
    return re.sub(r'[\\/:*?"<>|\r\n]+', ' ', base).strip()


def _resposta(dados, tipo, nome):
    resp = HttpResponse(dados, content_type=tipo)
    ascii_ = re.sub(r'[^A-Za-z0-9._ -]+', '', nome.encode('ascii', 'ignore').decode()) or 'ficheiro'
    resp['Content-Disposition'] = f'attachment; filename="{ascii_}"; filename*=UTF-8\'\'{quote(nome)}'
    resp['Cache-Control'] = 'private, no-store'
    resp['X-Content-Type-Options'] = 'nosniff'
    return resp


class RegistosListaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        escola = _escola(request)
        if not escola:
            return _erro('Instituição não identificada.')
        role = getattr(request.user, 'role', '')
        if not (_e_super(request.user) or role in ROLES_LEITURA or role == 'PROFESSOR'):
            return _erro('O seu perfil não tem acesso à correcção de provas.', 403)
        qs = CorrecaoRegisto.objects.filter(escola=escola).select_related('prova', 'prova__turma', 'prova__disciplina')
        for param, campo in (('turma_id', 'prova__turma_id'), ('disciplina_id', 'prova__disciplina_id')):
            val = request.query_params.get(param)
            if val:
                u = _uuid(val)
                if not u:
                    return Response({'success': True, 'data': []})
                qs = qs.filter(**{campo: u})
        if request.query_params.get('periodo'):
            qs = qs.filter(prova__periodo=request.query_params['periodo'])
        dados = [_json(r) for r in qs[:500] if _pode(request.user, (r.prova.turma_id, r.prova.disciplina_id), escola, False)]
        return Response({'success': True, 'data': dados})


class RegistoCriarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        escola, prova, erro = _prova(request, pk, escrita=True)
        if erro:
            return erro
        try:
            dur = max(0, int(float(request.data.get('duracao_seg') or 0)))
            n = max(0, int(float(request.data.get('n_folhas') or 0)))
        except (TypeError, ValueError):
            return _erro('Duração ou número de folhas inválido.')
        reg = CorrecaoRegisto(escola=escola, prova=prova, criado_por=request.user, duracao_seg=dur, n_folhas=n)
        try:
            cab, linhas = la.montar(prova, getattr(request.user, 'nome', '') or request.user.get_username())
            reg.caminho_pdf = _guardar(escola, reg.id, 'pdf', la.pdf_lista(cab, linhas))
            reg.caminho_xlsx = _guardar(escola, reg.id, 'xlsx', la.xlsx_lista(cab, linhas))
        except Exception:   # o registo da correcção não se perde se a lista falhar; descarrega-se depois a partir da prova
            pass
        reg.save()
        reg = CorrecaoRegisto.objects.select_related('prova', 'prova__turma', 'prova__disciplina').get(pk=reg.pk)
        return Response({'success': True, 'data': _json(reg), 'message': 'Correcção guardada em «Provas corrigidas».'}, status=201)


class RegistoDetalheView(APIView):
    permission_classes = [IsAuthenticated]

    def _registo(self, request, rid, escrita):
        escola = _escola(request)
        if not escola:
            return None, None, _erro('Instituição não identificada.')
        reg = CorrecaoRegisto.objects.filter(pk=rid, escola=escola).select_related(
            'prova', 'prova__turma', 'prova__disciplina').first()
        if not reg or not _pode(request.user, (reg.prova.turma_id, reg.prova.disciplina_id), escola, escrita):
            return None, None, _erro('Registo não encontrado.', 404)
        return escola, reg, None

    def get(self, request, rid, ficheiro=None):
        escola, reg, erro = self._registo(request, rid, False)
        if erro:
            return erro
        t = (request.query_params.get('t') or 'zip').lower()
        base = _nome(f'{reg.prova.disciplina.nome} - {reg.prova.get_instrumento_display()} - {reg.prova.turma.ano_letivo}')
        if t in ('pdf', 'xlsx'):
            ab = _abs(escola, reg.caminho_pdf if t == 'pdf' else reg.caminho_xlsx)
            if not ab:
                return _erro('A lista guardada já não está disponível.', 404)
            with open(ab, 'rb') as fh:
                return _resposta(fh.read(), 'application/pdf' if t == 'pdf' else MIME_XLSX, f'Lista de notas - {base}.{t}')
        folhas = FolhasCorrigidasPdfView().get(request, reg.prova_id)
        if t == 'folhas':
            if folhas.status_code != 200:
                return folhas
            return _resposta(folhas.content, 'application/pdf', f'Avaliacao corrigida - {base}.pdf')
        if t != 'zip':
            return _erro('Tipo inválido: use pdf, xlsx, folhas ou zip.')
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
            for ext, rel in (('pdf', reg.caminho_pdf), ('xlsx', reg.caminho_xlsx)):
                ab = _abs(escola, rel)
                if ab:
                    z.write(ab, f'Lista de notas - {base}.{ext}')
            if folhas.status_code == 200:
                z.writestr(f'Avaliacao corrigida - {base}.pdf', folhas.content)
        if not buf.getbuffer().nbytes or not zipfile.ZipFile(io.BytesIO(buf.getvalue())).namelist():
            return _erro('Não há ficheiros para exportar.', 404)
        return _resposta(buf.getvalue(), 'application/zip', f'Correccao - {base}.zip')

    def delete(self, request, rid, ficheiro=None):
        escola, reg, erro = self._registo(request, rid, True)
        if erro:
            return erro
        for rel in (reg.caminho_pdf, reg.caminho_xlsx):
            ab = _abs(escola, rel)
            if ab:
                try:
                    os.remove(ab)
                except OSError:
                    pass
        reg.delete()
        return Response({'success': True, 'message': 'Registo eliminado. As notas e as cadernetas não foram alteradas.'})
