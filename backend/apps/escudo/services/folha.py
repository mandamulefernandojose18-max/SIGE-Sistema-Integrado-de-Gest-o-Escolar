"""
Folha de resposta opcional junto das cópias da prova (Escudo Anti-IA).

A folha, quando pedida, é SEMPRE a primeira página da cópia. Duas variantes:
  · não personalizada: só os dados do aluno ficam em branco (uma folha igual em todas as cópias);
  · personalizada: uma folha por aluno real (classe → secção/área → turma); a cópia n leva a folha do aluno n.
Só se usam alunos activos reais da escola da prova: sem alunos não há folhas personalizadas.
"""
import pymupdf as fitz

from apps.alunos.models import Aluno  # noqa: F401  (usado via _alunos_da_turma)
from apps.disciplinas.models import Disciplina
from apps.documentos.services import folha_resposta_service as fr
from apps.documentos.views_folha_resposta import _alunos_da_turma
from apps.tenants.models import Escola
from apps.turmas.models import Turma

from .servico import MAX_COPIAS


def _on(form, nome, padrao=False):
    v = form.get(nome)
    return padrao if v is None else str(v).lower() in ('on', '1', 'true', 'sim')


def _alunos_do_ambito(escola, ano, classe, area, turma_id):
    """Lista de (turma, aluno) por ordem de turma e alfabética. `area`/`turma_id` vazios = todas."""
    turmas = Turma.objects.filter(escola=escola, ano_letivo=ano, grau_ano=classe)
    if area:
        turmas = turmas.filter(area=area)
    if turma_id:
        turmas = turmas.filter(id=turma_id)
    saida = []
    for t in turmas.order_by('area', 'nome'):
        saida += [(t, a, i) for i, a in enumerate(_alunos_da_turma(t), start=1)]
    return saida


def preparar(p, form):
    """None se a prova não leva folha; senão dicionário com `personalizada`, `total` e `para(n)` (bytes PDF da folha da cópia n)."""
    if not _on(form, 'folha_resposta'):
        return None
    escola = Escola.objects.filter(id=p.get('escola_id')).first() if p.get('escola_id') else None
    if not escola:
        raise ValueError('A folha de resposta precisa de uma prova associada a uma escola.')
    esc = fr.montar_dados_escola(escola)
    ano = escola.ano_letivo_ativo
    personalizada = _on(form, 'folha_personalizada')
    classe = (form.get('folha_classe') or '').strip() or (p.get('classe') or '').strip()

    cfg_in = {
        'tipo_avaliacao': form.get('folha_tipo') or 'ACS1',
        'disciplina': p.get('disciplina') or '',
        'n_perguntas': form.get('folha_n_perguntas'),
        'n_alternativas': form.get('folha_n_alternativas') or 4,
        'codigo_barras': _on(form, 'folha_codificada', True),  # «codificada»: leva código e QR de verificação
        'logo_escola': _on(form, 'folha_logo'),
        'incluir_chave': False,
    }
    if classe:
        discs = Disciplina.objects.filter(escola=escola, ano_letivo=ano, classe=classe)
        cfg_in['disciplinas_classe'] = list(discs.order_by('nome').values_list('nome', flat=True).distinct())
    config = fr.normalizar_config(cfg_in, esc)

    if not personalizada:
        pdf, _ = fr.gerar_folhas_pdf(esc, [None], config, ano)
        return {'personalizada': False, 'total': 0, 'alunos': [], 'para': lambda n: pdf}

    if not classe:
        raise ValueError('Escolha a classe das folhas personalizadas.')
    area = (form.get('folha_area') or '').strip()
    turma_id = (form.get('folha_turma_id') or '').strip()
    try:
        trio = _alunos_do_ambito(escola, ano, classe, area, turma_id)
    except Exception:  # id de turma mal formado
        raise ValueError('Turma inválida.') from None
    if not trio:
        raise ValueError('Não existem alunos activos neste âmbito: não há folhas personalizadas a gerar.')
    if len(trio) > MAX_COPIAS:
        raise ValueError(f'Há {len(trio)} alunos neste âmbito; o máximo é {MAX_COPIAS} cópias por vez. '
                         'Escolha uma secção ou uma turma.')
    dados = [fr.montar_dados_aluno(a, i) for _, a, i in trio]
    pdf, _ = fr.gerar_folhas_pdf(esc, dados, config, ano)
    por_aluno = len(fr.paginas_grelha(config['n_perguntas']))
    origem = fitz.open(stream=pdf, filetype='pdf')
    folhas = []
    for k in range(len(dados)):
        doc = fitz.open()
        doc.insert_pdf(origem, from_page=k * por_aluno, to_page=(k + 1) * por_aluno - 1)
        folhas.append(doc.tobytes(garbage=3, deflate=True))
        doc.close()
    origem.close()
    nomes = [f"{d['apelido']} {d['nome']}".strip() for d in dados]
    return {'personalizada': True, 'total': len(dados), 'alunos': nomes,
            'para': lambda n: folhas[(n - 1) % len(folhas)]}


def prefixar(folha_pdf, copia_pdf):
    """PDF final: páginas da folha de resposta primeiro, depois a cópia selada da prova."""
    saida = fitz.open()
    for dados in (folha_pdf, copia_pdf):
        with fitz.open(stream=dados, filetype='pdf') as doc:
            saida.insert_pdf(doc)
    resultado = saida.tobytes(garbage=3, deflate=True)
    saida.close()
    return resultado
