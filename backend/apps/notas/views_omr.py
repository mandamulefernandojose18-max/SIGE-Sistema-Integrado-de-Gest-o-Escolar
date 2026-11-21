"""
SIGE — API da Correcção Automática (gabarito importado + leitura óptica das folhas).

  POST /api/v1/notas/provas-fisicas/gabarito/importar/     {ficheiro | texto} → proposta de chave (nada é gravado)
  POST /api/v1/notas/provas-fisicas/<id>/leitura-omr/      {ficheiro, pagina_ini} → respostas lidas, dúvidas e aluno

A leitura só PROPÕE: o professor revê as dúvidas e confirma; só então se grava a correcção (PUT da correcção do
aluno) e, mais tarde, se lança na caderneta. Isolamento por escola e permissões iguais às da correcção manual.
"""
import os

from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.alunos.models import Aluno

from . import gabarito_importacao as gab
from . import omr_servico as omr
from .models import CorrecaoProva
from .views_correcao import ROLES_LEITURA, _e_super, _erro, _escola, _prova

PAGINAS_POR_PEDIDO = 4   # lidas em paralelo (~1–2 s por página): um pedido leva poucos segundos


def _ler_cpu(img, orig, n_mc, n_alt, guardar=False):
    """Parte pesada da leitura de uma página (só OpenCV/numpy, sem base de dados): corre em paralelo."""
    try:
        res = omr.ler_pagina(img, n_mc, n_alt, procurar_qr=orig is None, fonte=orig, com_imagens=not guardar)
    except omr.ErroOMR as e:
        return {'erro': str(e)}
    qr = res['qr']
    if not qr and orig is not None:   # digitalização em PDF: o QR lê-se melhor na imagem original (300 dpi)
        try:
            qr = omr.identificar(omr.ler_qr_original(orig))
        except Exception:
            qr = None
    return {'res': res, 'qr': qr}


def anotar_resolvendo_duvidas(prova, jpeg_limpo, respostas, duvidas, versao, professor, largura=1240):
    """Corrige a folha (imagem limpa em JPEG) contra o gabarito da prova: dúvidas resolvidas pela leitura
    (marca fraca/rasura = letra mais provável; o resto em branco). Devolve {acertos, nota, jpg}; levanta se faltar a versão."""
    from . import correcao_servico as svc
    cv2, np = omr._cv()
    resp = resolver_respostas(respostas, duvidas)
    _, _total, nota, _completa, limpas = svc.calcular(prova, None, resp, versao)
    chave = prova.gabaritos.get(versao or '-') or next(iter(prova.gabaritos.values()))
    acertos = sum(1 for a, b in zip(limpas, chave) if a == b)
    img = cv2.imdecode(np.frombuffer(jpeg_limpo, np.uint8), cv2.IMREAD_COLOR)
    n_mc = sum(1 for p in prova.perguntas if p.get('tipo') == 'MC')
    jpg = omr.anotar_folha(img, n_mc, prova.n_alternativas, limpas, chave, acertos, nota, professor, largura=largura)
    return {'acertos': acertos, 'nota': nota, 'jpg': jpg}


def guardar_pendente(escola, prova, utilizador, origem, out, alta):
    """Guarda (ou actualiza) a folha lida sem aluno atribuído. Devolve o id."""
    import os
    import uuid

    from . import correcao_servico as svc
    from .models import FolhaPendente
    bruto = alta
    pasta = svc.raiz_imagens(escola)
    os.makedirs(pasta, exist_ok=True)
    nome = f'pend_{uuid.uuid4().hex}.jpg'
    with open(os.path.join(pasta, nome), 'wb') as f:
        f.write(bruto)
    caminho = f'{svc._pasta_escola(escola)}/{nome}'.replace('\\', '/')
    anterior = FolhaPendente.objects.filter(prova=prova, origem=origem, pagina=out['pagina']).first()
    if anterior:
        _apagar_ficheiro_pendente(anterior)
    f, _ = FolhaPendente.objects.update_or_create(
        prova=prova, origem=origem, pagina=out['pagina'],
        defaults={'escola': escola, 'criado_por': utilizador if getattr(utilizador, 'pk', None) else None,
                  'respostas': out['respostas'], 'versao': out.get('versao') or '', 'duvidas': out.get('duvidas') or [],
                  'avisos': out.get('avisos') or [], 'acertos': out.get('acertos'), 'nota': out.get('nota'),
                  'caminho': caminho})
    return str(f.id)


def _apagar_ficheiro_pendente(f):
    import os

    from . import correcao_servico as svc
    caminho = svc.caminho_seguro(f)
    if caminho:
        try:
            os.remove(caminho)
        except OSError:
            pass


def _pendente_json(f):
    return {'id': str(f.id), 'origem': f.origem, 'pagina': f.pagina, 'respostas': f.respostas, 'versao': f.versao,
            'duvidas': f.duvidas, 'avisos': f.avisos, 'acertos': f.acertos, 'nota': f.nota}


class FolhasPendentesView(APIView):
    """Folhas lidas e corrigidas pelo sistema que ainda não têm aluno atribuído (guardadas até o professor as atribuir
    ou eliminar).

      GET    /api/v1/notas/provas-fisicas/<id>/folhas-pendentes/                 lista
      GET    /api/v1/notas/provas-fisicas/<id>/folhas-pendentes/<fid>/imagem/    a folha corrigida a vermelho (JPEG)
      DELETE /api/v1/notas/provas-fisicas/<id>/folhas-pendentes/<fid>/           elimina a folha (e o ficheiro)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, fid=None):
        from django.http import HttpResponse

        from . import correcao_servico as svc
        from .models import FolhaPendente
        escola, prova, erro = _prova(request, pk)
        if erro:
            return erro
        if fid is None:
            qs = FolhaPendente.objects.filter(prova=prova)
            return Response({'success': True, 'data': [_pendente_json(f) for f in qs]})
        f = FolhaPendente.objects.filter(pk=fid, prova=prova).first()
        caminho = svc.caminho_seguro(f) if f else None
        if not caminho:
            return _erro('Folha não encontrada.', 404)
        with open(caminho, 'rb') as fh:
            limpo = fh.read()
        try:
            dados = anotar_resolvendo_duvidas(prova, limpo, f.respostas, f.duvidas, f.versao,
                                              getattr(request.user, 'nome', '') or request.user.get_username())['jpg']
        except Exception:
            dados = limpo
        resp = HttpResponse(dados, content_type='image/jpeg')
        resp['Cache-Control'] = 'private, no-store'
        resp['X-Content-Type-Options'] = 'nosniff'
        return resp

    def delete(self, request, pk, fid):
        from .models import FolhaPendente
        escola, prova, erro = _prova(request, pk, escrita=True)
        if erro:
            return erro
        f = FolhaPendente.objects.filter(pk=fid, prova=prova).first()
        if not f:
            return _erro('Folha não encontrada.', 404)
        _apagar_ficheiro_pendente(f)
        f.delete()
        return Response({'success': True, 'message': 'Folha eliminada.'})


class GabaritoImportarView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        escola = _escola(request)
        if not escola:
            return _erro('Instituição não identificada.')
        role = getattr(request.user, 'role', '')
        if not (_e_super(request.user) or role == 'PROFESSOR'):
            msg = ('O seu perfil só pode consultar correcções.' if role in ROLES_LEITURA
                   else 'O seu perfil não tem acesso à correcção de provas.')
            return _erro(msg, 403)
        ficheiro = request.FILES.get('ficheiro')
        try:
            if ficheiro:
                if ficheiro.size > gab.MAX_BYTES:
                    return _erro('Ficheiro demasiado grande (máximo 5 MB).')
                dados = gab.extrair_gabarito(dados=ficheiro.read(gab.MAX_BYTES + 1), nome=ficheiro.name or '')
            elif request.data.get('texto'):
                dados = gab.extrair_gabarito(texto=request.data.get('texto'))
            else:
                return _erro('Envie um ficheiro (PDF, Word, Excel, CSV/TXT) ou cole a chave de correcção.')
        except gab.ErroImportacao as e:
            return _erro(str(e))
        return Response({'success': True, 'data': dados})


class GabaritosGuardadosView(APIView):
    """Gabaritos / guiões guardados pelo professor, para reutilizar sem recomeçar.

      GET    /api/v1/notas/provas-fisicas/gabaritos-guardados/        os do utilizador na escola
      POST   /api/v1/notas/provas-fisicas/gabaritos-guardados/        {nome, n_perguntas, n_alternativas, versoes, gabaritos}
                                                                      (guarda ou substitui o do mesmo nome)
      DELETE /api/v1/notas/provas-fisicas/gabaritos-guardados/<id>/   elimina
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    @staticmethod
    def _json(g):
        return {'id': str(g.id), 'nome': g.nome, 'n_perguntas': g.n_perguntas, 'n_alternativas': g.n_alternativas,
                'versoes': g.versoes, 'gabaritos': g.gabaritos, 'atualizado_em': g.updated_at.isoformat()}

    def _contexto(self, request):
        escola = _escola(request)
        if not escola:
            return None, _erro('Instituição não identificada.')
        role = getattr(request.user, 'role', '')
        if not (_e_super(request.user) or role == 'PROFESSOR'):
            return None, _erro('Só o professor pode guardar gabaritos.', 403)
        return escola, None

    def get(self, request):
        from .models import GabaritoGuardado
        escola, erro = self._contexto(request)
        if erro:
            return erro
        qs = GabaritoGuardado.objects.filter(escola=escola, criado_por=request.user)
        return Response({'success': True, 'data': [self._json(g) for g in qs]})

    def post(self, request):
        from .models import GabaritoGuardado
        escola, erro = self._contexto(request)
        if erro:
            return erro
        d = request.data
        nome = str(d.get('nome') or '').strip()[:120]
        try:
            n, n_alt = int(d.get('n_perguntas')), int(d.get('n_alternativas') or 4)
        except (TypeError, ValueError):
            return _erro('Indique o nº de perguntas e de alternativas.')
        if not nome:
            return _erro('Dê um nome ao gabarito (ex.: «Física 11ª · AT 1.º trimestre»).')
        if not (1 <= n <= 100 and 2 <= n_alt <= 6):
            return _erro('O nº de perguntas deve estar entre 1 e 100 e o de alternativas entre 2 e 6.')
        versoes = [str(v).upper()[:2] for v in (d.get('versoes') or []) if str(v).strip()][:6]
        brutos = d.get('gabaritos') if isinstance(d.get('gabaritos'), dict) else {}
        letras = 'ABCDEF'[:n_alt]
        gabaritos = {}
        for chave in (versoes or ['-']):
            texto = ''.join(str(brutos.get(chave) or '').upper().split())
            if len(texto) != n or any(c not in letras for c in texto):
                return _erro(f'A chave{" da versão " + chave if chave != "-" else ""} tem de ter exactamente {n} respostas '
                             f'certas ({", ".join(letras)}): falta indicar alguma pergunta.')
            gabaritos[chave] = texto
        g, criado = GabaritoGuardado.objects.update_or_create(
            escola=escola, criado_por=request.user, nome=nome,
            defaults={'n_perguntas': n, 'n_alternativas': n_alt, 'versoes': versoes, 'gabaritos': gabaritos})
        return Response({'success': True, 'data': self._json(g),
                         'message': 'Gabarito guardado.' if criado else 'Gabarito actualizado.'},
                        status=201 if criado else 200)

    def delete(self, request, pk):
        from .models import GabaritoGuardado
        escola, erro = self._contexto(request)
        if erro:
            return erro
        g = GabaritoGuardado.objects.filter(pk=pk, escola=escola, criado_por=request.user).first()
        if not g:
            return _erro('Gabarito não encontrado.', 404)
        g.delete()
        return Response({'success': True, 'message': 'Gabarito eliminado.'})


def gravar_folha_corrigida(escola, prova, corr, jpeg_limpo, nome_professor):
    """Desenha a folha corrigida (modelo do professor) a partir da imagem limpa e ALTA resolução (JPEG), guarda-a como
    imagem da correcção (substitui a anterior) e devolve (imagem_json, jpg). A folha sai nítida e direita (pode imprimir-se
    e devolver-se ao aluno)."""
    import uuid

    from . import correcao_servico as svc
    from .models import CorrecaoImagem
    from .views_correcao import _imagem_json
    cv2, np = omr._cv()
    img = cv2.imdecode(np.frombuffer(jpeg_limpo, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise omr.ErroOMR('Imagem inválida.')
    chave = prova.gabaritos.get(corr.versao or '-') or next(iter(prova.gabaritos.values()))
    n_mc = sum(1 for p in prova.perguntas if p.get('tipo') == 'MC')
    acertos = sum(1 for a, b in zip(corr.respostas, chave) if a == b)
    jpg = omr.anotar_folha(img, n_mc, prova.n_alternativas, corr.respostas, chave, acertos, corr.nota, nome_professor)
    for antiga in list(corr.imagens.all()):          # a folha corrigida substitui a leitura anterior
        svc.apagar_imagem(antiga)
    pasta = svc.raiz_imagens(escola)
    os.makedirs(pasta, exist_ok=True)
    nome = f'{uuid.uuid4().hex}.jpg'
    with open(os.path.join(pasta, nome), 'wb') as f:
        f.write(jpg)
    im = CorrecaoImagem.objects.create(
        escola=escola, correcao=corr, caminho=f'{svc._pasta_escola(escola)}/{nome}'.replace('\\', '/'),
        tipo='image/jpeg', tamanho=len(jpg), ordem=1)
    return _imagem_json(im), jpg


def resolver_respostas(respostas, duvidas):
    """'ABC*-' → dúvidas resolvidas pela leitura (marca fraca/rasura = letra mais provável; o resto em branco)."""
    sugestoes = {d['n']: d.get('sugerida') or '-' for d in duvidas}
    return ''.join(sugestoes.get(i + 1, '-') if c == '*' else c for i, c in enumerate(respostas))


class GabaritoGuardadoPdfView(APIView):
    """PDF do gabarito / guião de correcção guardado: GET /api/v1/notas/provas-fisicas/gabaritos-guardados/<id>/pdf/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        import re
        from urllib.parse import quote

        from django.http import HttpResponse

        from . import gabarito_pdf
        from .models import GabaritoGuardado
        escola = _escola(request)
        if not escola:
            return _erro('Instituição não identificada.')
        role = getattr(request.user, 'role', '')
        if not (_e_super(request.user) or role == 'PROFESSOR'):
            return _erro('Só o professor pode exportar os seus gabaritos.', 403)
        g = GabaritoGuardado.objects.filter(pk=pk, escola=escola, criado_por=request.user).first()
        if not g:
            return _erro('Gabarito não encontrado.', 404)
        dados = gabarito_pdf.pdf_gabarito(escola, g, getattr(request.user, 'nome', '') or request.user.get_username())
        nome = gabarito_pdf.nome_ficheiro(g)
        ascii_ = re.sub(r'[^A-Za-z0-9._ -]+', '', nome.encode('ascii', 'ignore').decode()) or 'Gabarito.pdf'
        resp = HttpResponse(dados, content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="{ascii_}"; filename*=UTF-8\'\'{quote(nome)}'
        resp['Cache-Control'] = 'private, no-store'
        resp['X-Content-Type-Options'] = 'nosniff'
        return resp


class ConfirmarOmrView(APIView):
    """Confirma a leitura de uma folha: grava a correcção, desenha a folha corrigida (modelo do professor) e lança na caderneta.

    POST /api/v1/notas/provas-fisicas/<id>/correcoes/<aluno_id>/confirmar-omr/
         {respostas, versao, imagem (JPEG data-URL da folha endireitada, opcional), lancar (bool, por omissão true)}
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request, pk, aluno_id):
        import base64
        import os
        import uuid

        from django.conf import settings

        from . import correcao_servico as svc
        from .models import CorrecaoImagem
        from .views_correcao import _correcao_json

        escola, prova, erro = _prova(request, pk, escrita=True)
        if erro:
            return erro
        if prova.tipo != 'MULTIPLA_ESCOLHA':
            return _erro('A confirmação automática só serve para provas de escolha múltipla.')
        aluno = Aluno.objects.filter(id=aluno_id, escola=escola, turma=prova.turma).first()
        if not aluno:
            return _erro('Aluno não encontrado nesta turma.', 404)
        try:
            corr = svc.gravar_correcao(prova, aluno, None, request.user, respostas=request.data.get('respostas'),
                                       versao=request.data.get('versao') or '')
        except svc.ErroCorrecao as e:
            return _erro(str(e))

        # ---- folha corrigida (vistos, círculos, acertos, nota e nome do professor, a vermelho) ----
        imagem_json, aviso_imagem, jpg = None, '', b''
        bruto = request.data.get('imagem') or ''
        pend = None
        if request.data.get('pendente_id'):
            from .models import FolhaPendente
            try:
                pend = FolhaPendente.objects.filter(pk=request.data.get('pendente_id'), prova=prova).first()
            except Exception:
                pend = None
            if pend:   # a folha guardada no servidor (alta resolução) tem prioridade sobre qualquer imagem reduzida
                caminho = svc.caminho_seguro(pend)
                if caminho:
                    with open(caminho, 'rb') as fh:
                        bruto = 'data:image/jpeg;base64,' + base64.b64encode(fh.read()).decode('ascii')
        if bruto.startswith('data:image/jpeg;base64,') and corr.respostas:
            try:
                dados = base64.b64decode(bruto.split(',', 1)[1], validate=False)
                if len(dados) > 6 * 1024 * 1024:
                    raise omr.ErroOMR('Imagem demasiado grande.')
                imagem_json, jpg = gravar_folha_corrigida(
                    escola, prova, corr, dados, getattr(request.user, 'nome', '') or request.user.get_username())
            except Exception as e:                     # a correcção já está gravada; a imagem é um extra
                aviso_imagem = f'Não foi possível desenhar a folha corrigida: {e}'
        # ---- lançamento automático na caderneta ----
        lancamento = None
        if request.data.get('lancar', True) is not False and corr.estado == 'CORRIGIDA':
            try:
                svc.lancar_na_caderneta(request, escola, corr)
                lancamento = {'ok': True}
            except svc.ErroCorrecao as e:
                lancamento = {'ok': False, 'message': str(e)}
        corr.refresh_from_db()
        if pend:                       # a folha ficou atribuída a um aluno: já não está pendente
            _apagar_ficheiro_pendente(pend)
            pend.delete()
        folha = ''
        if imagem_json and jpg:
            folha = 'data:image/jpeg;base64,' + base64.b64encode(jpg).decode('ascii')
        return Response({'success': True, 'data': _correcao_json(corr), 'imagem': imagem_json,
                         'aviso_imagem': aviso_imagem, 'lancamento': lancamento, 'folha': folha})


def _pasta_temporaria(escola):
    from django.conf import settings
    return os.path.join(settings.MEDIA_ROOT, 'tmp_omr', str(escola.id))


def _caminho_upload(escola, uid):
    import uuid
    try:
        u = uuid.UUID(str(uid))
    except (ValueError, TypeError):
        return None
    pasta = os.path.realpath(_pasta_temporaria(escola))
    caminho = os.path.realpath(os.path.join(pasta, f'{u.hex}.bin'))
    return caminho if caminho.startswith(pasta + os.sep) and os.path.isfile(caminho) else None


class LeituraUploadView(APIView):
    """O ficheiro das folhas envia-se UMA vez (e não em cada pedido de leitura): fica numa pasta temporária da escola
    até a leitura acabar (ou 6 horas). POST devolve {upload_id, total_paginas}; DELETE apaga-o."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        import time
        import uuid
        escola, prova, erro = _prova(request, pk, escrita=True)
        if erro:
            return erro
        ficheiro = request.FILES.get('ficheiro')
        if not ficheiro:
            return _erro('Envie a fotografia ou o PDF digitalizado das folhas.')
        if ficheiro.size > omr.MAX_BYTES:
            return _erro('Ficheiro demasiado grande (máximo 60 MB).')
        dados = ficheiro.read(omr.MAX_BYTES + 1)
        try:
            total = omr.contar_paginas(dados)
        except omr.ErroOMR as e:
            return _erro(str(e))
        pasta = _pasta_temporaria(escola)
        os.makedirs(pasta, exist_ok=True)
        agora = time.time()
        for nome in os.listdir(pasta):                       # limpeza dos temporários com mais de 6 h
            p = os.path.join(pasta, nome)
            try:
                if agora - os.path.getmtime(p) > 6 * 3600:
                    os.remove(p)
            except OSError:
                pass
        uid = uuid.uuid4()
        with open(os.path.join(pasta, f'{uid.hex}.bin'), 'wb') as f:
            f.write(dados)
        return Response({'success': True, 'data': {'upload_id': str(uid), 'total_paginas': total}})

    def delete(self, request, pk, uid):
        escola, prova, erro = _prova(request, pk, escrita=True)
        if erro:
            return erro
        caminho = _caminho_upload(escola, uid)
        if caminho:
            try:
                os.remove(caminho)
            except OSError:
                pass
        return Response({'success': True})


class LeituraOmrView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        escola, prova, erro = _prova(request, pk, escrita=True)
        if erro:
            return erro
        if prova.tipo != 'MULTIPLA_ESCOLHA':
            return _erro('A leitura automática só serve para provas de escolha múltipla com Folha de Resposta.')
        ficheiro = request.FILES.get('ficheiro')
        nome_origem = (ficheiro.name if ficheiro else str(request.data.get('nome') or 'folhas'))[:255]
        if request.data.get('upload_id'):          # ficheiro já enviado uma vez (ver LeituraUploadView)
            caminho = _caminho_upload(escola, request.data.get('upload_id'))
            if not caminho:
                return _erro('O ficheiro enviado já não está disponível: volte a carregá-lo.', 410)
            with open(caminho, 'rb') as f:
                dados = f.read()
        else:
            if not ficheiro:
                return _erro('Envie a fotografia ou o PDF digitalizado das folhas.')
            if ficheiro.size > omr.MAX_BYTES:
                return _erro('Ficheiro demasiado grande (máximo 60 MB).')
            dados = ficheiro.read(omr.MAX_BYTES + 1)
        try:
            ini = max(0, int(request.data.get('pagina_ini') or 0))
        except (TypeError, ValueError):
            return _erro('Página inicial inválida.')
        try:
            total = omr.contar_paginas(dados)
        except omr.ErroOMR as e:
            return _erro(str(e))
        n_mc = sum(1 for p in prova.perguntas if p.get('tipo') == 'MC')
        n_alt = prova.n_alternativas
        versoes = [v for v in (prova.versoes or []) if v]
        guardar = str(request.data.get('guardar') or '').lower() in ('1', 'true', 'sim')
        paginas = []
        fim = min(total, ini + PAGINAS_POR_PEDIDO)
        # Rápido: abrir as páginas é sequencial (PyMuPDF não é seguro em threads); a leitura (OpenCV, que larga o GIL)
        # faz-se em paralelo pelas páginas do pedido; depois, sequencialmente, a base de dados e a folha corrigida.
        from concurrent.futures import ThreadPoolExecutor
        abertas = [(idx, img, orig, erro) for idx, (img, orig, erro)
                   in zip(range(ini, fim), omr.abrir_lote(dados, list(range(ini, fim))))]
        with ThreadPoolExecutor(max_workers=max(1, min(len(abertas) or 1, os.cpu_count() or 2))) as ex:
            futuros = [ex.submit(_ler_cpu, img, orig, n_mc, n_alt, guardar) if img is not None else None for _i, img, orig, _e in abertas]
        for (idx, _img, _orig, erro_abrir), fut in zip(abertas, futuros):
            cpu = fut.result() if fut is not None else {'erro': erro_abrir}
            paginas.append(self._pagina(escola, prova, cpu, idx, n_mc, n_alt, versoes,
                                        getattr(request.user, 'nome', '') or request.user.get_username(),
                                        request.user, nome_origem, guardar))
        return Response({'success': True, 'data': {
            'total_paginas': total, 'paginas': paginas, 'proxima': fim if fim < total else None,
            'n_perguntas_mc': n_mc, 'n_alternativas': n_alt, 'versoes': versoes}})

    @staticmethod
    def _pagina(escola, prova, cpu, idx, n_mc, n_alt, versoes, professor='', utilizador=None, origem='', guardar=False):
        """Lê a página e já a corrige. Com `guardar` e o aluno identificado, grava logo a correcção e a prova corrigida
        (sem devolver imagens ao navegador). Sem aluno, guarda a folha como pendente (não se perde)."""
        import base64

        from . import correcao_servico as svc
        out = LeituraOmrView._ler(escola, prova, cpu, idx, n_mc, n_alt, versoes)
        if not out.get('ok'):
            return out
        alta = out.pop('alta', b'')
        out.update({'acertos': None, 'nota': None, 'corrigida': None, 'pendente_id': None, 'guardada': False})
        versao_ok = (not versoes) or bool(out['versao'])
        if out.get('aluno') and guardar and versao_ok and alta:
            try:
                from apps.alunos.models import Aluno as _Aluno
                aluno = _Aluno.objects.get(id=out['aluno']['id'])
                corr = svc.gravar_correcao(prova, aluno, None, utilizador, respostas=resolver_respostas(out['respostas'], out['duvidas']),
                                           versao=out['versao'])
                gravar_folha_corrigida(escola, prova, corr, alta, professor)
                chave = prova.gabaritos.get(corr.versao or '-') or next(iter(prova.gabaritos.values()))
                out.update({'guardada': True, 'nota': corr.nota, 'acertos': sum(1 for a, b in zip(corr.respostas, chave) if a == b),
                            'imagem': '', 'previa': ''})
                if out['aluno'].get('estado_actual'):
                    out['avisos'].append('Este aluno já tinha correcção; foi substituída.')
                return out
            except Exception as e:     # não conseguiu guardar: segue o caminho normal (o professor revê)
                out['avisos'].append(f'Não foi possível guardar automaticamente: {e}')
        try:
            if guardar:      # o navegador vai buscar a folha ao servidor quando a quiser ver: só se calcula a nota
                _, _t, nota, _c, limpas = svc.calcular(prova, None, resolver_respostas(out['respostas'], out['duvidas']), out['versao'])
                chave = prova.gabaritos.get(out['versao'] or '-') or next(iter(prova.gabaritos.values()))
                out.update({'acertos': sum(1 for a, b in zip(limpas, chave) if a == b), 'nota': nota})
            else:
                r = anotar_resolvendo_duvidas(prova, alta, out['respostas'], out['duvidas'], out['versao'], professor)
                out.update({'acertos': r['acertos'], 'nota': r['nota'],
                            'corrigida': 'data:image/jpeg;base64,' + base64.b64encode(r['jpg']).decode('ascii')})
        except Exception:
            pass     # sem versão (ou chave) a folha fica só lida; o professor escolhe a versão e corrige
        if not out.get('aluno') and alta:
            # sem aluno identificado: guarda a folha no sistema (para não se perder ao recarregar); o professor
            # atribui o aluno quando quiser, ou elimina-a
            try:
                out['pendente_id'] = guardar_pendente(escola, prova, utilizador, origem, out, alta)
                if guardar:
                    out['imagem'] = out['previa'] = out['corrigida'] = ''
            except Exception:
                out['pendente_id'] = None
        return out

    @staticmethod
    def _ler(escola, prova, cpu, idx, n_mc, n_alt, versoes):
        base = {'pagina': idx + 1, 'ok': False}
        if cpu.get('erro'):
            return {**base, 'erro': cpu['erro']}
        res = cpu['res']
        avisos = list(res['avisos'])
        qr = cpu['qr']
        aluno_json, versao = None, ''
        codigo = res.get('codigo_barras') or ''
        if not qr and codigo:
            # folha personalizada: o código de barras traz o código do aluno
            aluno = Aluno.objects.filter(escola=escola, turma=prova.turma, matricula=codigo).first()
            if aluno:
                corr = CorrecaoProva.objects.filter(prova=prova, aluno=aluno).first()
                aluno_json = {'id': str(aluno.id), 'nome': aluno.nome, 'matricula': aluno.matricula,
                              'estado_actual': corr.estado if corr else None}
                if versoes:
                    avisos.append('Escolha a versão da folha deste aluno.')
                return {**base, 'ok': True, 'aluno': aluno_json, 'versao': '', 'respostas': res['respostas'],
                        'duvidas': res['duvidas'], 'avisos': avisos, 'alinhamento': res['alinhamento'],
                        'previa': res['previa'], 'imagem': res['pagina'], 'alta': res.get('alta', b'')}
        if not qr:
            avisos.append('O QR da folha não foi lido: escolha o aluno manualmente.')
        elif str(qr.get('e')) != str(escola.id):
            return {**base, 'erro': 'Esta folha pertence a outra instituição e não pode ser corrigida aqui.'}
        elif int(qr.get('n') or 0) != n_mc:
            return {**base, 'erro': f'Esta folha é de uma prova com {qr.get("n")} perguntas de escolha múltipla; '
                                    f'a prova seleccionada tem {n_mc}.'}
        else:
            versao = (qr.get('v') or '').upper()
            if versao and versoes and versao not in versoes:
                avisos.append(f'A folha diz versão {versao}, que não existe nesta prova: escolha a versão.')
                versao = ''
            aluno = Aluno.objects.filter(escola=escola, turma=prova.turma, matricula=qr.get('a') or '\0').first()
            if aluno:
                corr = CorrecaoProva.objects.filter(prova=prova, aluno=aluno).first()
                aluno_json = {'id': str(aluno.id), 'nome': aluno.nome, 'matricula': aluno.matricula,
                              'estado_actual': corr.estado if corr else None}
                if corr and corr.estado == 'LANCADA':
                    avisos.append('Este aluno já tem a nota lançada; confirmar de novo exige novo lançamento.')
            else:
                avisos.append('O aluno desta folha não está nesta turma: escolha o aluno manualmente.')
        if not versao and versoes:
            avisos.append('Escolha a versão da folha deste aluno.')
        return {**base, 'ok': True, 'aluno': aluno_json, 'versao': versao, 'respostas': res['respostas'],
                'duvidas': res['duvidas'], 'avisos': avisos, 'alinhamento': res['alinhamento'],
                'previa': res['previa'], 'imagem': res['pagina'], 'alta': res.get('alta', b'')}
