"""
SIGE — API da Correcção Automática (gabarito importado + leitura óptica das folhas).

  POST /api/v1/notas/provas-fisicas/gabarito/importar/     {ficheiro | texto} → proposta de chave (nada é gravado)
  POST /api/v1/notas/provas-fisicas/<id>/leitura-omr/      {ficheiro, pagina_ini} → respostas lidas, dúvidas e aluno

A leitura só PROPÕE: o professor revê as dúvidas e confirma; só então se grava a correcção (PUT da correcção do
aluno) e, mais tarde, se lança na caderneta. Isolamento por escola e permissões iguais às da correcção manual.
"""
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.alunos.models import Aluno

from . import gabarito_importacao as gab
from . import omr_servico as omr
from .models import CorrecaoProva
from .views_correcao import ROLES_LEITURA, _e_super, _erro, _escola, _prova

PAGINAS_POR_PEDIDO = 2   # ~2–3 s por página: um pedido nunca passa do tempo limite do servidor


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
        if bruto.startswith('data:image/jpeg;base64,') and corr.respostas:
            try:
                cv2, np = omr._cv()
                dados = base64.b64decode(bruto.split(',', 1)[1], validate=False)
                if len(dados) > 6 * 1024 * 1024:
                    raise omr.ErroOMR('Imagem demasiado grande.')
                img = cv2.imdecode(np.frombuffer(dados, np.uint8), cv2.IMREAD_COLOR)
                if img is None:
                    raise omr.ErroOMR('Imagem inválida.')
                chave = prova.gabaritos.get(corr.versao or '-') or next(iter(prova.gabaritos.values()))
                n_mc = sum(1 for p in prova.perguntas if p.get('tipo') == 'MC')
                acertos = sum(1 for a, b in zip(corr.respostas, chave) if a == b)
                nome_prof = getattr(request.user, 'nome', '') or request.user.get_username()
                jpg = omr.anotar_folha(img, n_mc, prova.n_alternativas, corr.respostas, chave, acertos, corr.nota, nome_prof)
                for antiga in list(corr.imagens.all()):     # a folha corrigida substitui a leitura anterior
                    svc.apagar_imagem(antiga)
                pasta = svc.raiz_imagens(escola)
                os.makedirs(pasta, exist_ok=True)
                nome = f'{uuid.uuid4().hex}.jpg'
                with open(os.path.join(pasta, nome), 'wb') as f:
                    f.write(jpg)
                im = CorrecaoImagem.objects.create(
                    escola=escola, correcao=corr, caminho=f'{svc._pasta_escola(escola)}/{nome}'.replace('\\', '/'),
                    tipo='image/jpeg', tamanho=len(jpg), ordem=1)
                from .views_correcao import _imagem_json
                imagem_json = _imagem_json(im)
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
        folha = ''
        if imagem_json and jpg:
            folha = 'data:image/jpeg;base64,' + base64.b64encode(jpg).decode('ascii')
        return Response({'success': True, 'data': _correcao_json(corr), 'imagem': imagem_json,
                         'aviso_imagem': aviso_imagem, 'lancamento': lancamento, 'folha': folha})


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
        paginas = []
        fim = min(total, ini + PAGINAS_POR_PEDIDO)
        for idx in range(ini, fim):
            paginas.append(self._pagina(escola, prova, dados, idx, n_mc, n_alt, versoes,
                                        getattr(request.user, 'nome', '') or request.user.get_username()))
        return Response({'success': True, 'data': {
            'total_paginas': total, 'paginas': paginas, 'proxima': fim if fim < total else None,
            'n_perguntas_mc': n_mc, 'n_alternativas': n_alt, 'versoes': versoes}})

    @staticmethod
    def _pagina(escola, prova, dados, idx, n_mc, n_alt, versoes, professor=''):
        """Lê a página e já a corrige: junta `acertos`, `nota` e `corrigida` (folha corrigida a vermelho, JPEG em data-URL).

        A folha corrige-se mesmo sem aluno identificado (precisa só da versão, se a prova tiver várias)."""
        import base64
        out = LeituraOmrView._ler(escola, prova, dados, idx, n_mc, n_alt, versoes)
        if not out.get('ok'):
            return out
        out.update({'acertos': None, 'nota': None, 'corrigida': None})
        try:
            sugestoes = {d['n']: d.get('sugerida') or '-' for d in out['duvidas']}
            resp = ''.join(sugestoes.get(i + 1, '-') if c == '*' else c for i, c in enumerate(out['respostas']))
            from . import correcao_servico as svc
            _, _total, nota, _completa, limpas = svc.calcular(prova, None, resp, out['versao'])
            chave = prova.gabaritos.get(out['versao'] or '-') or next(iter(prova.gabaritos.values()))
            acertos = sum(1 for a, b in zip(limpas, chave) if a == b)
            cv2, np = omr._cv()
            bruto = base64.b64decode(out['imagem'].split(',', 1)[1])
            img = cv2.imdecode(np.frombuffer(bruto, np.uint8), cv2.IMREAD_COLOR)
            jpg = omr.anotar_folha(img, n_mc, n_alt, limpas, chave, acertos, nota, professor, largura=1240)
            out.update({'acertos': acertos, 'nota': nota,
                        'corrigida': 'data:image/jpeg;base64,' + base64.b64encode(jpg).decode('ascii')})
        except Exception:
            pass     # sem versão (ou chave) a folha fica só lida; o professor escolhe a versão e corrige
        return out

    @staticmethod
    def _ler(escola, prova, dados, idx, n_mc, n_alt, versoes):
        base = {'pagina': idx + 1, 'ok': False}
        try:
            img = omr.abrir_pagina(dados, idx)
            res = omr.ler_pagina(img, n_mc, n_alt)
        except omr.ErroOMR as e:
            return {**base, 'erro': str(e)}
        avisos = list(res['avisos'])
        qr = res['qr']
        if not qr:   # digitalização em PDF: o QR lê-se melhor na imagem original (300 dpi)
            try:
                orig = omr.imagem_original_pdf(dados, idx)
                qr = omr.identificar(omr.ler_qr_original(orig)) if orig is not None else None
            except Exception:
                qr = None
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
                        'previa': res['previa'], 'imagem': res['pagina']}
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
                'previa': res['previa'], 'imagem': res['pagina']}
