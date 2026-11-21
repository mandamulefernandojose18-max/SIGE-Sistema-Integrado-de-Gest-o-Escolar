"""
SIGE — API da Correcção Assistida de Provas Físicas.

  GET/POST /api/v1/notas/provas-fisicas/                                      lista / cria prova (grelha de cotações)
  GET/DELETE /api/v1/notas/provas-fisicas/<id>/                               detalhe (alunos + estado) / elimina
  GET/PUT  /api/v1/notas/provas-fisicas/<id>/correcoes/<aluno_id>/            pontos por pergunta de um aluno
  POST     /api/v1/notas/provas-fisicas/<id>/correcoes/<aluno_id>/imagens/    página digitalizada (PNG/JPG/PDF)
  GET/DELETE /api/v1/notas/provas-fisicas/imagens/<img_id>/                   ficheiro autenticado / remove
  POST     /api/v1/notas/provas-fisicas/<id>/lancar/                          lança na caderneta (confirmação do professor)

Escolha múltipla: a prova é criada com a MESMA configuração da Folha de Resposta gerada (corpo {"tipo":
"MULTIPLA_ESCOLHA", "folha": {tipo_avaliacao, n_perguntas, n_alternativas, cotacao_pergunta|seccoes, abertas,
versoes, gabaritos}}); a correcção recebe as respostas assinaladas ({"respostas": "ABCD-A", "versao": "A"}) e
o sistema corrige contra o gabarito. Perguntas abertas da folha recebem pontos do professor em "pontos".

Tudo isolado por escola. Corrige quem é o professor alocado à turma e disciplina (ou SUPERADMIN);
Direcção, Administração e DAP só consultam. Nada chega à caderneta sem o pedido explícito de lançamento.
"""
import os
import uuid

from django.db.models import Exists, OuterRef
from django.http import FileResponse
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.audit import registrar_auditoria
from apps.alunos.models import Aluno
from apps.disciplinas.models import Disciplina
from apps.professores.models import AlocacaoDocente
from apps.turmas.models import Turma
from common.utils.tenant import get_tenant_escola

from . import correcao_servico as svc
from .models import CorrecaoImagem, CorrecaoProva, ProvaFisica
from .views import _ip_do_pedido

ROLES_LEITURA = {'SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'}


def _erro(msg, codigo=400):
    return Response({'success': False, 'message': msg}, status=codigo)


def _uuid(valor):
    try:
        return uuid.UUID(str(valor))
    except (ValueError, TypeError, AttributeError):
        return None


def _e_super(user):
    return getattr(user, 'role', '') == 'SUPERADMIN' or bool(getattr(user, 'is_superuser', False))


def _alocado(user, turma_id, disciplina_id, escola):
    prof_id = getattr(user, 'professor_id', None)
    return bool(prof_id) and AlocacaoDocente.objects.filter(
        escola=escola, professor_id=prof_id, turma_id=turma_id, disciplina_id=disciplina_id).exists()


def _pode(user, prova_ou_par, escola, escrita):
    """Professor alocado: lê e escreve. SUPERADMIN: lê e escreve. Direcção/Admin/DAP: só lê."""
    role = getattr(user, 'role', '')
    if _e_super(user):
        return True
    if role == 'PROFESSOR':
        turma_id, disc_id = prova_ou_par
        return _alocado(user, turma_id, disc_id, escola)
    return role in ROLES_LEITURA and not escrita


def _escola(request):
    return get_tenant_escola(request)


def _prova(request, pk, escrita=False):
    """Devolve (escola, prova, None) ou (None, None, Response de erro). 404 igual para inexistente e alheia."""
    escola = _escola(request)
    if not escola:
        return None, None, _erro('Instituição não identificada.')
    prova = ProvaFisica.objects.filter(pk=pk, escola=escola).select_related('turma', 'disciplina').first()
    if not prova or not _pode(request.user, (prova.turma_id, prova.disciplina_id), escola, escrita):
        if prova and getattr(request.user, 'role', '') in ROLES_LEITURA and escrita:
            return None, None, _erro('O seu perfil só pode consultar correcções; a correcção é do professor da disciplina.', 403)
        return None, None, _erro('Prova não encontrada.', 404)
    return escola, prova, None


def _imagem_json(i):
    return {'id': str(i.id), 'tipo': i.tipo, 'ordem': i.ordem, 'tamanho': i.tamanho}


def _correcao_json(c):
    return {
        'id': str(c.id), 'aluno_id': str(c.aluno_id), 'pontos': c.pontos, 'total': c.total, 'nota': c.nota,
        'estado': c.estado, 'versao': c.versao, 'respostas': c.respostas, 'lancada_em': c.lancada_em.isoformat() if c.lancada_em else None,
        'imagens': [_imagem_json(i) for i in c.imagens.all()],
    }


def _prova_json(p):
    return {
        'id': str(p.id), 'titulo': p.titulo, 'turma_id': str(p.turma_id), 'turma_nome': p.turma.nome,
        'disciplina_id': str(p.disciplina_id), 'disciplina_nome': p.disciplina.nome, 'periodo': p.periodo,
        'instrumento': p.instrumento, 'perguntas': p.perguntas, 'cotacao_total': p.cotacao_total,
        'instrumento_nome': p.get_instrumento_display(), 'ano_letivo': p.turma.ano_letivo,
        'tipo': p.tipo, 'n_alternativas': p.n_alternativas, 'versoes': [v for v in (p.versoes or []) if v],
        'created_at': p.created_at.isoformat(),  # o gabarito nunca sai da API
    }


class ProvasFisicasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        escola = _escola(request)
        if not escola:
            return _erro('Instituição não identificada.')
        role = getattr(request.user, 'role', '')
        if not (_e_super(request.user) or role in ROLES_LEITURA or role == 'PROFESSOR'):
            return _erro('O seu perfil não tem acesso à correcção de provas.', 403)
        qs = ProvaFisica.objects.filter(escola=escola).select_related('turma', 'disciplina')
        if role == 'PROFESSOR' and not _e_super(request.user):
            prof_id = getattr(request.user, 'professor_id', None)
            if not prof_id:
                return Response({'success': True, 'data': []})
            qs = qs.filter(Exists(AlocacaoDocente.objects.filter(
                escola=escola, professor_id=prof_id, turma_id=OuterRef('turma_id'), disciplina_id=OuterRef('disciplina_id'))))
        for param, campo in (('turma_id', 'turma_id'), ('disciplina_id', 'disciplina_id')):
            val = request.query_params.get(param)
            if val:
                u = _uuid(val)
                if not u:
                    return _erro(f'Parâmetro {param} inválido.')
                qs = qs.filter(**{campo: u})
        periodo = request.query_params.get('periodo')
        if periodo and periodo != 'TODOS':
            qs = qs.filter(periodo=periodo)
        return Response({'success': True, 'data': [_prova_json(p) for p in qs[:200]]})

    def post(self, request):
        escola = _escola(request)
        if not escola:
            return _erro('Instituição não identificada.')
        turma = Turma.objects.filter(id=_uuid(request.data.get('turma_id')), escola=escola).first()
        disciplina = Disciplina.objects.filter(id=_uuid(request.data.get('disciplina_id')), escola=escola).first()
        if not turma or not disciplina:
            return _erro('Turma ou disciplina não encontrada nesta instituição.', 404)
        if not _pode(request.user, (turma.id, disciplina.id), escola, True):
            return _erro('Apenas o professor atribuído a esta turma e disciplina pode criar provas para correcção.', 403)
        periodo = request.data.get('periodo')
        if periodo not in svc.PERIODOS_VALIDOS:
            return _erro('Seleccione um trimestre válido (1º, 2º ou 3º).')
        titulo = str(request.data.get('titulo') or '').strip()[:255]
        if not titulo:
            return _erro('Indique o título da prova.')
        tipo = request.data.get('tipo') or 'DISCURSIVA'
        extra = {}
        try:
            if tipo == 'MULTIPLA_ESCOLHA':
                # Mesma configuração da Folha de Resposta gerada pelo sistema (chave "folha").
                f = svc.perguntas_da_folha(request.data.get('folha'), disciplina.nome)
                perguntas, total, instrumento = f['perguntas'], f['cotacao_total'], f['instrumento']
                extra = {'n_alternativas': f['n_alternativas'], 'versoes': f['versoes'], 'gabaritos': f['gabaritos']}
            elif tipo == 'DISCURSIVA':
                instrumento = request.data.get('instrumento')
                if instrumento not in svc.INSTRUMENTOS:
                    return _erro('Instrumento de avaliação inválido.')
                perguntas, total = svc.normalizar_perguntas(request.data.get('perguntas'))
            else:
                return _erro('Tipo de prova inválido.')
        except svc.ErroCorrecao as e:
            return _erro(str(e))
        prova = ProvaFisica.objects.create(
            escola=escola, turma=turma, disciplina=disciplina, periodo=periodo, instrumento=instrumento,
            titulo=titulo, tipo=tipo, perguntas=perguntas, cotacao_total=total, **extra,
            criado_por=request.user if getattr(request.user, 'pk', None) else None)
        registrar_auditoria(request.user, escola, 'PROVA_FISICA', 'CRIACAO', prova.id,
                            f'Prova física "{titulo}" criada para correcção ({disciplina.nome}, {turma.nome}, {periodo})',
                            ip=_ip_do_pedido(request))
        return Response({'success': True, 'data': _prova_json(prova)}, status=status.HTTP_201_CREATED)


class ProvaFisicaDetalheView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        escola, prova, erro = _prova(request, pk)
        if erro:
            return erro
        correcoes = {c.aluno_id: c for c in CorrecaoProva.objects.filter(prova=prova).prefetch_related('imagens')}
        alunos = Aluno.objects.filter(escola=escola, turma=prova.turma, status='ATIVO').order_by('nome')
        itens = []
        for a in alunos:
            c = correcoes.get(a.id)
            itens.append({'aluno_id': str(a.id), 'nome': a.nome, 'matricula': a.matricula,
                          'correcao': _correcao_json(c) if c else None})
        resumo = {
            'total_alunos': len(itens),
            'corrigidas': sum(1 for i in itens if i['correcao'] and i['correcao']['estado'] in ('CORRIGIDA', 'LANCADA')),
            'lancadas': sum(1 for i in itens if i['correcao'] and i['correcao']['estado'] == 'LANCADA'),
        }
        return Response({'success': True, 'data': {**_prova_json(prova), 'alunos': itens, 'resumo': resumo}})

    def delete(self, request, pk):
        escola, prova, erro = _prova(request, pk, escrita=True)
        if erro:
            return erro
        # O professor pode eliminar a prova quando quiser. As notas já lançadas ficam na caderneta (não dependem da prova).
        lancadas = prova.correcoes.filter(estado='LANCADA').count()
        for img in CorrecaoImagem.objects.filter(correcao__prova=prova):
            svc.apagar_imagem(img)
        from .views_omr import _apagar_ficheiro_pendente
        for pend in prova.folhas_pendentes.all():
            _apagar_ficheiro_pendente(pend)
        registrar_auditoria(request.user, escola, 'PROVA_FISICA', 'ELIMINACAO', prova.id,
                            f'Prova física "{prova.titulo}" eliminada' + (f' ({lancadas} nota(s) já lançada(s) mantida(s) na caderneta)' if lancadas else ''),
                            ip=_ip_do_pedido(request))
        prova.delete()
        return Response({'success': True, 'lancadas_mantidas': lancadas,
                         'message': 'Prova eliminada.' + (f' As {lancadas} nota(s) já lançada(s) mantêm-se na caderneta.' if lancadas else '')})


class CorrecaoAlunoView(APIView):
    permission_classes = [IsAuthenticated]

    def _aluno(self, escola, prova, aluno_id):
        return Aluno.objects.filter(id=aluno_id, escola=escola, turma=prova.turma).first()

    def get(self, request, pk, aluno_id):
        escola, prova, erro = _prova(request, pk)
        if erro:
            return erro
        aluno = self._aluno(escola, prova, aluno_id)
        if not aluno:
            return _erro('Aluno não encontrado nesta turma.', 404)
        corr = CorrecaoProva.objects.filter(prova=prova, aluno=aluno).prefetch_related('imagens').first()
        return Response({'success': True, 'data': _correcao_json(corr) if corr else None})

    def put(self, request, pk, aluno_id):
        escola, prova, erro = _prova(request, pk, escrita=True)
        if erro:
            return erro
        aluno = self._aluno(escola, prova, aluno_id)
        if not aluno:
            return _erro('Aluno não encontrado nesta turma.', 404)
        try:
            corr = svc.gravar_correcao(prova, aluno, request.data.get('pontos'), request.user,
                                       respostas=request.data.get('respostas'), versao=request.data.get('versao') or '')
        except svc.ErroCorrecao as e:
            return _erro(str(e))
        return Response({'success': True, 'data': _correcao_json(corr)})

    def delete(self, request, pk, aluno_id):
        """Elimina a prova corrigida (o PDF/folha corrigida) do aluno. A correcção e a nota na caderneta NÃO se alteram."""
        escola, prova, erro = _prova(request, pk, escrita=True)
        if erro:
            return erro
        aluno = self._aluno(escola, prova, aluno_id)
        if not aluno:
            return _erro('Aluno não encontrado nesta turma.', 404)
        corr = CorrecaoProva.objects.filter(prova=prova, aluno=aluno).prefetch_related('imagens').first()
        imagens = list(corr.imagens.all()) if corr else []
        if not imagens:
            return _erro('Este aluno não tem prova corrigida para eliminar.', 404)
        for img in imagens:
            svc.apagar_imagem(img)
        return Response({'success': True, 'message': 'Prova corrigida eliminada. A nota e a caderneta não foram alteradas.'})


class FolhasCorrigidasPdfView(APIView):
    """PDF com as folhas corrigidas (uma por página A4): de um aluno (?aluno_id=) ou de toda a turma da prova."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        import re

        import fitz
        from django.http import HttpResponse

        escola, prova, erro = _prova(request, pk)
        if erro:
            return erro
        qs = CorrecaoProva.objects.filter(prova=prova).select_related('aluno').prefetch_related('imagens')
        aluno_id = request.query_params.get('aluno_id')
        if aluno_id:
            qs = qs.filter(aluno_id=_uuid(aluno_id))
        qs = qs.order_by('aluno__nome')
        doc = fitz.open()
        for corr in qs:
            for img in corr.imagens.order_by('ordem'):
                caminho = svc.caminho_seguro(img)
                if not caminho or img.tipo not in ('image/jpeg', 'image/png'):
                    continue
                pagina = doc.new_page(width=595.28, height=841.89)
                pagina.insert_image(pagina.rect, filename=caminho, keep_proportion=True)
        if not aluno_id:
            # folhas já corrigidas mas ainda sem aluno atribuído também entram no PDF (no fim, por ficheiro e página)
            from concurrent.futures import ThreadPoolExecutor

            from .models import FolhaPendente
            from .views_omr import anotar_resolvendo_duvidas
            nome_prof = getattr(request.user, 'nome', '') or request.user.get_username()
            pend = []
            for f in FolhaPendente.objects.filter(prova=prova).order_by('origem', 'pagina'):
                caminho = svc.caminho_seguro(f)
                if caminho:
                    with open(caminho, 'rb') as fh:
                        pend.append((f.respostas, f.duvidas, f.versao, fh.read()))

            def _corrigir(item):
                respostas, duvidas, versao, limpo = item
                try:
                    return anotar_resolvendo_duvidas(prova, limpo, respostas, duvidas, versao, nome_prof, largura=None)['jpg']
                except Exception:
                    return limpo               # sem versão/chave: a folha segue como foi lida
            if pend:
                with ThreadPoolExecutor(max_workers=max(1, min(4, os.cpu_count() or 2))) as ex:
                    for jpg in ex.map(_corrigir, pend):
                        pagina = doc.new_page(width=595.28, height=841.89)
                        pagina.insert_image(pagina.rect, stream=jpg, keep_proportion=True)
        if doc.page_count == 0:
            doc.close()
            return _erro('Ainda não há folhas corrigidas para descarregar.', 404)
        dados = doc.tobytes(deflate=True)
        doc.close()
        # Nome: Avaliacao corrigida - Disciplina - Tipo de avaliação - Ano
        nome = f'Avaliacao corrigida - {prova.disciplina.nome} - {prova.get_instrumento_display()} - {prova.turma.ano_letivo}'
        nome = re.sub(r'[\\/:*?"<>|\r\n]+', ' ', nome).strip()
        from urllib.parse import quote
        ascii_ = re.sub(r'[^A-Za-z0-9._ -]+', '', nome.encode('ascii', 'ignore').decode()) or 'Avaliacao corrigida'
        resp = HttpResponse(dados, content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="{ascii_}.pdf"; filename*=UTF-8\'\'{quote(nome)}.pdf\''
        resp['Cache-Control'] = 'private, no-store'
        resp['X-Content-Type-Options'] = 'nosniff'
        return resp


class ListaNotasAvaliacaoView(APIView):
    """Lista de resultados da avaliação corrigida (PDF ou Excel): ?formato=pdf|xlsx (por omissão pdf)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from django.http import HttpResponse
        from urllib.parse import quote

        from . import lista_avaliacao as la

        escola, prova, erro = _prova(request, pk)
        if erro:
            return erro
        formato = (request.query_params.get('formato') or 'pdf').lower()
        if formato not in ('pdf', 'xlsx'):
            return _erro('Formato inválido: use pdf ou xlsx.')
        cab, linhas = la.montar(prova, getattr(request.user, 'nome', '') or request.user.get_username())
        if formato == 'pdf':
            dados, tipo = la.pdf_lista(cab, linhas), 'application/pdf'
        else:
            dados, tipo = la.xlsx_lista(cab, linhas), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        nome = la.nome_ficheiro(cab, formato)
        resp = HttpResponse(dados, content_type=tipo)
        resp['Content-Disposition'] = f'attachment; filename="Lista_de_notas.{formato}"; filename*=UTF-8\'\'{quote(nome)}'
        resp['Cache-Control'] = 'private, no-store'
        resp['X-Content-Type-Options'] = 'nosniff'
        return resp


class CorrecaoImagemUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, pk, aluno_id):
        escola, prova, erro = _prova(request, pk, escrita=True)
        if erro:
            return erro
        aluno = Aluno.objects.filter(id=aluno_id, escola=escola, turma=prova.turma).first()
        if not aluno:
            return _erro('Aluno não encontrado nesta turma.', 404)
        corr, _ = CorrecaoProva.objects.get_or_create(
            escola=escola, prova=prova, aluno=aluno,
            defaults={'pontos': [None] * len(prova.perguntas), 'total': 0, 'nota': 0})
        try:
            img = svc.guardar_imagem(corr, request.FILES.get('ficheiro'))
        except svc.ErroCorrecao as e:
            return _erro(str(e))
        return Response({'success': True, 'data': _imagem_json(img)}, status=status.HTTP_201_CREATED)


class CorrecaoImagemFicheiroView(APIView):
    permission_classes = [IsAuthenticated]

    def _imagem(self, request, img_id, escrita):
        escola = _escola(request)
        if not escola:
            return None, _erro('Instituição não identificada.')
        img = CorrecaoImagem.objects.filter(pk=img_id, escola=escola).select_related(
            'escola', 'correcao__prova').first()
        prova = img.correcao.prova if img else None
        if not img or not _pode(request.user, (prova.turma_id, prova.disciplina_id), escola, escrita):
            return None, _erro('Ficheiro não encontrado.', 404)  # mesma resposta para inexistente e alheio
        return img, None

    def get(self, request, img_id):
        img, erro = self._imagem(request, img_id, False)
        if erro:
            return erro
        caminho = svc.caminho_seguro(img)
        if not caminho:
            return _erro('Ficheiro não encontrado.', 404)
        resp = FileResponse(open(caminho, 'rb'), content_type=img.tipo)
        resp['Content-Disposition'] = 'inline; filename="prova"'
        resp['X-Content-Type-Options'] = 'nosniff'
        resp['Cache-Control'] = 'private, no-store'
        resp['Content-Security-Policy'] = "default-src 'none'; sandbox"
        return resp

    def delete(self, request, img_id):
        img, erro = self._imagem(request, img_id, True)
        if erro:
            return erro
        svc.apagar_imagem(img)
        return Response({'success': True, 'message': 'Página removida.'})


class LancarCorrecoesView(APIView):
    """Lança na caderneta as correcções completas. É o ponto de confirmação do professor."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        escola, prova, erro = _prova(request, pk, escrita=True)
        if erro:
            return erro
        qs = CorrecaoProva.objects.filter(prova=prova, estado__in=['CORRIGIDA']).select_related('aluno')
        ids = request.data.get('aluno_ids')
        if ids is not None:
            if not isinstance(ids, list):
                return _erro('aluno_ids deve ser uma lista.')
            qs = qs.filter(aluno_id__in=[u for u in (_uuid(i) for i in ids) if u])
        lancadas, falhas = 0, []
        for corr in qs:
            try:
                svc.lancar_na_caderneta(request, escola, corr)
                lancadas += 1
            except svc.ErroCorrecao as e:
                falhas.append({'aluno_id': str(corr.aluno_id), 'nome': corr.aluno.nome, 'message': str(e)})
        if lancadas == 0 and not falhas:
            return _erro('Não há correcções completas por lançar.', 409)
        return Response({'success': lancadas > 0 or not falhas, 'lancadas': lancadas, 'falhas': falhas,
                         'message': f'{lancadas} nota(s) lançada(s) na caderneta.'
                                    + (f' {len(falhas)} não lançada(s).' if falhas else '')})
