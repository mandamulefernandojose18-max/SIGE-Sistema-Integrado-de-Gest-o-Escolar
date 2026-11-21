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
        imagem_json, aviso_imagem = None, ''
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
        return Response({'success': True, 'data': _correcao_json(corr), 'imagem': imagem_json,
                         'aviso_imagem': aviso_imagem, 'lancamento': lancamento})


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
            paginas.append(self._pagina(escola, prova, dados, idx, n_mc, n_alt, versoes))
        return Response({'success': True, 'data': {
            'total_paginas': total, 'paginas': paginas, 'proxima': fim if fim < total else None,
            'n_perguntas_mc': n_mc, 'n_alternativas': n_alt, 'versoes': versoes}})

    @staticmethod
    def _pagina(escola, prova, dados, idx, n_mc, n_alt, versoes):
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
