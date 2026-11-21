"""
SIGE — Correcção automática EM LOTE, super-rápida (orçamento: ≤ 60 s para o lote, qualquer que seja o nº de folhas).

Como se cumpre:
  * o ficheiro envia-se UMA vez e o servidor trata TODAS as páginas num só trabalho (sem vaivém página a página);
  * as páginas são lidas, corrigidas e DESENHADAS (vistos/círculos/nota/nome) em paralelo, em PROCESSOS (um por núcleo);
  * o processo principal só grava na base de dados e no disco (rápido);
  * o estado vai para um ficheiro JSON; o navegador só consulta o progresso (a cada ~0,7 s).

O lançamento nas cadernetas e o PDF das provas corrigidas são pedidos pelo navegador logo que o trabalho termina
(`/lancar/` e `/folhas-corrigidas/`), sem o professor carregar em mais nada.
"""
import json
import os
import threading
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context

ORCAMENTO_S = 60          # tempo máximo exigido para o lote
MAX_PROCESSOS = 8


def _iniciar_processo():
    import django
    django.setup()
    import cv2
    cv2.setNumThreads(1)      # um núcleo por processo: sem sobrecarga de threads do OpenCV a competir entre si
    cv2.ocl.setUseOpenCL(False)


_POOL = None
_POOL_LOCK = threading.Lock()


def _pool():
    """Pool de processos permanente (arranque pago UMA vez e já feito durante o envio do ficheiro: `aquecer`)."""
    global _POOL
    with _POOL_LOCK:
        if _POOL is None:
            n = max(1, min(os.cpu_count() or 2, MAX_PROCESSOS))
            _POOL = ProcessPoolExecutor(max_workers=n, mp_context=get_context('spawn'), initializer=_iniciar_processo)
        return _POOL


def aquecer():
    """Arranca os processos (importações pesadas) enquanto o ficheiro ainda está a ser enviado."""
    try:
        p = _pool()
        for _ in range(p._max_workers):
            p.submit(os.getpid)
    except Exception:
        pass


def trabalhar_pagina(caminho, idx, prova, n_mc, n_alt, versoes, professor):
    """Corre num processo à parte: lê a página, identifica o QR e já desenha a folha corrigida (sem base de dados)."""
    import warnings
    warnings.filterwarnings('ignore')
    from . import omr_servico as omr
    from .views_omr import _ler_cpu, anotar_resolvendo_duvidas
    with open(caminho, 'rb') as f:
        dados = f.read()
    img, orig, erro = omr.abrir_lote(dados, [idx])[0]
    if img is None:
        return {'idx': idx, 'cpu': {'erro': erro}, 'pre': None}
    cpu = _ler_cpu(img, orig, n_mc, n_alt, True)
    pre = None
    res = cpu.get('res')
    if res and res.get('alta'):
        qr = cpu.get('qr') or {}
        versao = (qr.get('v') or '').upper()
        if versao and versoes and versao not in versoes:
            versao = ''
        if (not versoes) or versao:
            try:
                from .views_omr import resolver_respostas
                r = anotar_resolvendo_duvidas(prova, res['alta'], res['respostas'], res['duvidas'], versao, professor)
                pre = {'jpg': r['jpg'], 'acertos': r['acertos'], 'nota': r['nota'], 'versao': versao}
            except Exception:
                pre = None
    return {'idx': idx, 'cpu': cpu, 'pre': pre}


# ---------------------------------------------------------------------------
# Estado do trabalho (ficheiro JSON: partilhado entre os processos do servidor)
# ---------------------------------------------------------------------------
def _pasta(escola):
    from django.conf import settings
    return os.path.join(settings.MEDIA_ROOT, 'tmp_omr', str(escola.id))


def caminho_estado(escola, job_id):
    try:
        j = uuid.UUID(str(job_id)).hex
    except (ValueError, TypeError):
        return None
    return os.path.join(_pasta(escola), f'job_{j}.json')


def _gravar_estado(caminho, estado):
    tmp = caminho + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(estado, f)
    os.replace(tmp, caminho)


def ler_estado(escola, job_id):
    c = caminho_estado(escola, job_id)
    if not c or not os.path.isfile(c):
        return None
    try:
        with open(c, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def iniciar(escola, prova, utilizador, caminho_upload, nome_origem, professor):
    """Cria o trabalho e lança-o numa thread; devolve o id (o navegador consulta o estado)."""
    from . import omr_servico as omr
    with open(caminho_upload, 'rb') as f:
        total = omr.contar_paginas(f.read())
    job_id = str(uuid.uuid4())
    caminho = caminho_estado(escola, job_id)
    estado = {'id': job_id, 'estado': 'A_CORRER', 'total': total, 'feitas': 0, 'corrigidas': 0, 'sem_aluno': 0,
              'erros': 0, 'inicio': time.time(), 'segundos': 0.0, 'itens': [], 'mensagem': ''}
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    _gravar_estado(caminho, estado)
    threading.Thread(target=_correr, daemon=True,
                     args=(caminho, estado, escola, prova, utilizador, caminho_upload, nome_origem, professor)).start()
    return job_id, total


def _correr(caminho, estado, escola, prova, utilizador, caminho_upload, nome_origem, professor):
    from django.db import connection

    from .views_omr import LeituraOmrView
    n_mc = sum(1 for p in prova.perguntas if p.get('tipo') == 'MC')
    n_alt = prova.n_alternativas
    versoes = [v for v in (prova.versoes or []) if v]
    ultimo = 0.0
    try:
        global _POOL
        try:
            ex = _pool()
            futuros = {ex.submit(trabalhar_pagina, caminho_upload, i, prova, n_mc, n_alt, versoes, professor): i
                       for i in range(estado['total'])}
        except Exception:                                   # pool avariado: recria-o e tenta uma vez
            with _POOL_LOCK:
                _POOL = None
            ex = _pool()
            futuros = {ex.submit(trabalhar_pagina, caminho_upload, i, prova, n_mc, n_alt, versoes, professor): i
                       for i in range(estado['total'])}
        for fut in as_completed(futuros):
            try:
                r = fut.result()
                pag = LeituraOmrView._pagina(escola, prova, r['cpu'], r['idx'], n_mc, n_alt, versoes, professor,
                                             utilizador, nome_origem, True, pre=r['pre'])
            except Exception as e:                                   # uma folha má não pára o lote
                pag = {'ok': False, 'pagina': futuros[fut] + 1, 'erro': str(e)}
            estado['feitas'] += 1
            if not pag.get('ok'):
                estado['erros'] += 1
                estado['itens'].append({'pagina': pag.get('pagina'), 'estado': 'ERRO', 'erro': pag.get('erro', '')})
            elif pag.get('guardada'):
                estado['corrigidas'] += 1
                estado['itens'].append({'pagina': pag['pagina'], 'estado': 'CORRIGIDA', 'nota': pag.get('nota'),
                                        'aluno': (pag.get('aluno') or {}).get('nome', '')})
            else:
                estado['sem_aluno'] += 1
                estado['itens'].append({'pagina': pag['pagina'], 'estado': 'SEM_ALUNO', 'nota': pag.get('nota'),
                                        'aviso': ' '.join(pag.get('avisos') or [])[:200]})
            estado['segundos'] = round(time.time() - estado['inicio'], 1)
            if time.time() - ultimo > 0.4 or estado['feitas'] == estado['total']:
                ultimo = time.time()
                _gravar_estado(caminho, estado)
        estado['estado'] = 'CONCLUIDO'
    except Exception as e:
        estado['estado'] = 'ERRO'
        estado['mensagem'] = str(e)[:300]
    finally:
        estado['segundos'] = round(time.time() - estado['inicio'], 1)
        estado['itens'].sort(key=lambda x: x.get('pagina') or 0)
        estado['dentro_orcamento'] = estado['segundos'] <= ORCAMENTO_S
        _gravar_estado(caminho, estado)
        try:
            os.remove(caminho_upload)
        except OSError:
            pass
        connection.close()
