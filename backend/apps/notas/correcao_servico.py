"""
SIGE — Correcção assistida de provas físicas.

O professor digitaliza/fotografa a prova, atribui pontos por pergunta numa grelha de cotações e o sistema
soma, converte para a escala 0–20 e (só depois da confirmação do professor) lança na caderneta pelo mesmo
caminho do lançamento normal (prazos, pauta fechada, cálculo MEC e auditoria).
"""
import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from common.utils.avaliacoes_mocambique import calcular_media_trimestral

from .models import CorrecaoImagem, CorrecaoProva, Nota, ProvaFisica

MAX_PERGUNTAS = 100
MAX_IMAGEM_BYTES = 8 * 1024 * 1024
MAX_IMAGENS_POR_CORRECAO = 6
PERIODOS_VALIDOS = ('1_TRIMESTRE', '2_TRIMESTRE', '3_TRIMESTRE')
INSTRUMENTOS = tuple(k for k, _ in ProvaFisica.INSTRUMENTOS)
_CAMPOS_NOTA = ('teste1', 'teste2', 'teste3', 'teste4', 'trabalho', 'avaliacao_trimestral')

# Assinaturas reais dos ficheiros aceites (não se confia na extensão enviada).
_ASSINATURAS = (
    (b'\x89PNG\r\n\x1a\n', '.png', 'image/png'),
    (b'\xff\xd8\xff', '.jpg', 'image/jpeg'),
    (b'%PDF-', '.pdf', 'application/pdf'),
)
TIPOS_POR_EXTENSAO = {ext: tipo for _, ext, tipo in _ASSINATURAS}


class ErroCorrecao(ValueError):
    """Erro de regra de negócio, mostrado tal e qual ao professor."""


def _numero(valor, nome):
    try:
        n = float(str(valor).replace(',', '.'))
    except (TypeError, ValueError):
        raise ErroCorrecao(f'{nome} inválido(a).')
    if n != n or n in (float('inf'), float('-inf')):
        raise ErroCorrecao(f'{nome} inválido(a).')
    return n


def normalizar_perguntas(brutas):
    """Valida a grelha de cotações e devolve (perguntas, cotacao_total)."""
    if not isinstance(brutas, list) or not brutas:
        raise ErroCorrecao('Indique pelo menos uma pergunta com a respectiva cotação.')
    if len(brutas) > MAX_PERGUNTAS:
        raise ErroCorrecao(f'Uma prova pode ter no máximo {MAX_PERGUNTAS} perguntas.')
    perguntas, total = [], 0.0
    for i, item in enumerate(brutas, start=1):
        cot = _numero(item.get('cotacao') if isinstance(item, dict) else item, f'Cotação da pergunta {i}')
        if not 0 < cot <= 20:
            raise ErroCorrecao(f'A cotação da pergunta {i} deve estar entre 0 (exclusivo) e 20.')
        cot = round(cot, 2)
        perguntas.append({'numero': i, 'cotacao': cot})
        total += cot
    return perguntas, round(total, 2)


# Folha de Resposta do sistema: tipo de avaliação da folha → instrumento da caderneta
INSTRUMENTO_POR_TIPO_FOLHA = {'ACS1': 'teste1', 'ACS2': 'teste2', 'ACS3': 'teste3', 'AT': 'avaliacao_trimestral'}


def perguntas_da_folha(config_folha, disciplina_nome):
    """Prova de escolha múltipla a partir da MESMA configuração da Folha de Resposta gerada.

    Reutiliza a validação da folha (nº de perguntas, 2–6 alternativas, cotação uniforme ou por secções,
    partes abertas, versões e gabaritos), para que prova impressa e correcção nunca divirjam.
    Devolve dict com perguntas, cotacao_total, n_alternativas, versoes, gabaritos e instrumento.
    """
    from apps.documentos.services import folha_resposta_service as fr

    cfg_in = dict(config_folha or {})
    cfg_in['disciplina'] = disciplina_nome
    try:
        cfg = fr.normalizar_config(cfg_in, None)
    except fr.ConfigFolhaInvalida as e:
        raise ErroCorrecao(str(e))
    instrumento = INSTRUMENTO_POR_TIPO_FOLHA.get(cfg['tipo'])
    if not instrumento:
        raise ErroCorrecao('O Exame Final não se lança na caderneta trimestral: escolha 1ª/2ª/3ª ACS ou AT.')
    if not cfg['gabaritos']:
        raise ErroCorrecao('Indique a chave de correcção (gabarito) para o sistema corrigir as respostas.')
    faltam = [v or '-' for v in cfg['versoes'] if (v or '-') not in cfg['gabaritos']]
    if faltam:
        raise ErroCorrecao('Falta a chave de correcção da(s) versão(ões): ' + ', '.join(faltam) + '.')
    perguntas = [{'numero': i, 'cotacao': round(float(c), 4), 'tipo': 'MC'} for i, c in enumerate(cfg['cotacoes'], start=1)]
    for parte in cfg['abertas']:
        for _ in range(parte['n']):
            perguntas.append({'numero': len(perguntas) + 1, 'cotacao': parte['cotacao'], 'tipo': 'ABERTA',
                              'parte': parte['rotulo']})
    if len(perguntas) > MAX_PERGUNTAS + 50:
        raise ErroCorrecao('A prova tem perguntas a mais.')
    return {'perguntas': perguntas, 'cotacao_total': round(float(cfg['cotacao_total']), 2),
            'n_alternativas': cfg['n_alternativas'], 'versoes': cfg['versoes'], 'gabaritos': cfg['gabaritos'],
            'instrumento': instrumento}


def _pontos_escolha_multipla(prova, pontos, respostas, versao):
    """Pontos por pergunta: as de escolha múltipla vêm do gabarito; as abertas, dos pontos do professor."""
    n_mc = sum(1 for p in prova.perguntas if p.get('tipo') == 'MC')
    versoes = [v for v in (prova.versoes or []) if v]
    versao = (versao or '').upper().strip()
    if versoes and versao not in versoes:
        raise ErroCorrecao('Escolha a versão da folha deste aluno: ' + ', '.join(versoes) + '.')
    chave = prova.gabaritos.get(versao or '-') or (next(iter(prova.gabaritos.values())) if len(prova.gabaritos) == 1 else None)
    if not chave:
        raise ErroCorrecao('Esta prova não tem chave de correcção para a versão indicada.')
    letras = 'ABCDEF'[:prova.n_alternativas]
    limpas = ''.join(ch for ch in str(respostas or '').upper() if not ch.isspace())
    saida = list(pontos) if isinstance(pontos, list) and len(pontos) == len(prova.perguntas) else [None] * len(prova.perguntas)
    if not limpas:
        return [None if p.get('tipo') == 'MC' else saida[i] for i, p in enumerate(prova.perguntas)], ''
    if len(limpas) != n_mc:
        raise ErroCorrecao(f'Envie as {n_mc} respostas assinaladas (use "-" para em branco).')
    invalidas = sorted({c for c in limpas if c not in letras and c not in '-N'})
    if invalidas:
        raise ErroCorrecao(f'Respostas inválidas ({", ".join(invalidas)}): use apenas {", ".join(letras)}, "-" (em branco) ou "N" (nula).')
    for i, p in enumerate(prova.perguntas):
        if p.get('tipo') == 'MC':
            saida[i] = p['cotacao'] if limpas[i] == chave[i] else 0
    return saida, limpas


def calcular(prova, pontos, respostas=None, versao=''):
    """Valida os pontos contra as cotações. Devolve (pontos, total, nota 0–20, completa, respostas)."""
    cotacoes = [p['cotacao'] for p in prova.perguntas]
    resp_limpas = ''
    if prova.tipo == 'MULTIPLA_ESCOLHA':
        pontos, resp_limpas = _pontos_escolha_multipla(prova, pontos, respostas, versao)
    if not isinstance(pontos, list) or len(pontos) != len(cotacoes):
        raise ErroCorrecao(f'Envie os pontos das {len(cotacoes)} perguntas da prova.')
    limpos, total, completa = [], 0.0, True
    for i, (bruto, cot) in enumerate(zip(pontos, cotacoes), start=1):
        if bruto is None or bruto == '':
            limpos.append(None)
            completa = False
            continue
        v = round(_numero(bruto, f'Pontos da pergunta {i}'), 2)
        if v < -1e-9 or v > cot + 0.006:  # tolerância do arredondamento a 2 casas (ex.: 20/3 por pergunta)
            raise ErroCorrecao(f'Pergunta {i}: os pontos devem estar entre 0 e {cot:g}.')
        v = max(0.0, min(v, cot))
        limpos.append(v)
        total += v
    total = round(total, 2)
    nota = round(min(20.0, total / prova.cotacao_total * 20.0), 2) if prova.cotacao_total else 0.0
    return limpos, total, nota, completa, resp_limpas


def gravar_correcao(prova, aluno, pontos, utilizador, respostas=None, versao=''):
    limpos, total, nota, completa, resp = calcular(prova, pontos, respostas, versao)
    versao = (versao or '').upper().strip()[:2] if prova.tipo == 'MULTIPLA_ESCOLHA' else ''
    corr, criada = CorrecaoProva.objects.get_or_create(
        escola=prova.escola, prova=prova, aluno=aluno,
        defaults={'pontos': limpos, 'total': total, 'nota': nota})
    mudou = criada or corr.pontos != limpos or corr.respostas != resp or corr.versao != versao
    corr.pontos, corr.total, corr.nota = limpos, total, nota
    corr.respostas, corr.versao = resp, versao
    corr.corrigido_por = utilizador if getattr(utilizador, 'pk', None) else None
    if completa:
        # Já lançada e sem alterações mantém-se lançada; qualquer alteração exige novo lançamento.
        corr.estado = 'LANCADA' if (corr.estado == 'LANCADA' and not mudou) else 'CORRIGIDA'
    else:
        corr.estado = 'RASCUNHO'
    corr.save()
    return corr


# ---------------------------------------------------------------------------
# Imagens (acesso sempre autenticado; nunca servidas como ficheiro estático)
# ---------------------------------------------------------------------------
def _pasta_escola(escola):
    return os.path.join('provas_fisicas', str(escola.id))


def raiz_imagens(escola):
    return os.path.realpath(os.path.join(settings.MEDIA_ROOT, _pasta_escola(escola)))


def detectar_tipo(conteudo):
    for assinatura, ext, tipo in _ASSINATURAS:
        if conteudo.startswith(assinatura):
            return ext, tipo
    return None, None


def guardar_imagem(correcao, ficheiro):
    if correcao.imagens.count() >= MAX_IMAGENS_POR_CORRECAO:
        raise ErroCorrecao(f'Cada prova admite no máximo {MAX_IMAGENS_POR_CORRECAO} páginas digitalizadas.')
    if ficheiro is None:
        raise ErroCorrecao('Envie o ficheiro da prova digitalizada (campo "ficheiro").')
    if ficheiro.size > MAX_IMAGEM_BYTES:
        raise ErroCorrecao('O ficheiro excede o limite de 8 MB.')
    conteudo = ficheiro.read()
    ext, tipo = detectar_tipo(conteudo)
    if not ext:
        raise ErroCorrecao('Formato não suportado: use PNG, JPG ou PDF.')
    pasta = raiz_imagens(correcao.escola)
    os.makedirs(pasta, exist_ok=True)
    nome = f'{uuid.uuid4().hex}{ext}'
    with open(os.path.join(pasta, nome), 'wb') as f:
        f.write(conteudo)
    ordem = (correcao.imagens.order_by('-ordem').values_list('ordem', flat=True).first() or 0) + 1
    return CorrecaoImagem.objects.create(
        escola=correcao.escola, correcao=correcao, caminho=f'{_pasta_escola(correcao.escola)}/{nome}'.replace('\\', '/'),
        tipo=tipo, tamanho=len(conteudo), ordem=ordem)


def caminho_seguro(imagem):
    """Caminho absoluto do ficheiro, só se estiver dentro da pasta da escola dona; senão None."""
    raiz = raiz_imagens(imagem.escola)
    caminho = os.path.realpath(os.path.join(settings.MEDIA_ROOT, imagem.caminho))
    ext = os.path.splitext(caminho)[1].lower()
    if caminho.startswith(raiz + os.sep) and ext in TIPOS_POR_EXTENSAO and os.path.isfile(caminho):
        return caminho
    return None


def apagar_imagem(imagem):
    caminho = caminho_seguro(imagem)
    imagem.delete()
    if caminho:
        try:
            os.remove(caminho)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Lançamento na caderneta (mesma regra do lançamento normal)
# ---------------------------------------------------------------------------
def lancar_na_caderneta(request, escola, correcao):
    """Grava a nota da correcção no instrumento da prova, sem alterar os restantes instrumentos."""
    from .prazos_service import verificar_prazo_lancamento_trimestre
    from .views import _auditar_nota, _instantaneo_nota

    prova = correcao.prova
    if correcao.estado == 'RASCUNHO' or any(p is None for p in correcao.pontos):
        raise ErroCorrecao(f'A correcção de {correcao.aluno.nome} ainda tem perguntas por corrigir.')
    if prova.periodo not in PERIODOS_VALIDOS:
        raise ErroCorrecao('Período da prova inválido para lançamento.')

    permitido, _motivo, msg, _info = verificar_prazo_lancamento_trimestre(
        escola=escola, periodo=prova.periodo, turma=prova.turma, disciplina=prova.disciplina, user=request.user)
    if not permitido:
        raise ErroCorrecao(msg)

    existente = Nota.objects.filter(escola=escola, aluno=correcao.aluno, disciplina=prova.disciplina,
                                    turma=prova.turma, periodo=prova.periodo).first()
    antes = _instantaneo_nota(existente)
    dados = {c: (getattr(existente, c) if existente else None) for c in _CAMPOS_NOTA}
    dados[prova.instrumento] = correcao.nota
    calc = calcular_media_trimestral(dados)
    defaults = {
        prova.instrumento: correcao.nota,
        'media_final': calc['mediaFinal'],
        'resultado': calc['resultado'],
    }
    if not (existente and existente.comportamento):
        defaults['comportamento'] = calc.get('comportamento') or ''
    try:
        nota, _ = Nota.objects.update_or_create(
            escola=escola, aluno=correcao.aluno, disciplina=prova.disciplina, turma=prova.turma,
            periodo=prova.periodo, defaults=defaults)
    except ValidationError as e:
        raise ErroCorrecao('; '.join(e.messages))
    nota.refresh_from_db()
    _auditar_nota(request, escola, correcao.aluno, prova.disciplina, prova.periodo, antes, nota)
    correcao.estado = 'LANCADA'
    correcao.lancada_em = timezone.now()
    correcao.save(update_fields=['estado', 'lancada_em', 'updated_at'])
    return nota
