"""
Folha de resposta opcional junto das cópias da prova (Escudo Anti-IA).

A folha, quando pedida, é SEMPRE a primeira página da cópia. Duas variantes:
  · não personalizada: só os dados do aluno ficam em branco (uma folha igual em todas as cópias);
  · personalizada: uma folha por aluno real (classe → secção/área → turma); a cópia n leva a folha do aluno n.
Só se usam alunos activos reais da escola da prova: sem alunos não há folhas personalizadas.
"""
import csv
import io
import re
import unicodedata

import pymupdf as fitz
from django.db.models import Count

from apps.alunos.models import Aluno
from apps.disciplinas.models import Disciplina
from apps.notas.models import Nota
from apps.documentos.services import folha_resposta_service as fr
from apps.documentos.views_folha_resposta import _alunos_da_turma
from apps.tenants.models import Escola
from apps.turmas.models import Turma

from .servico import MAX_COPIAS


def _data_br(iso):
    """«2026-11-09» -> «09/11/2026»; vazio ou inválido fica em branco."""
    m = re.fullmatch(r'(\d{4})-(\d{2})-(\d{2})', (iso or '').strip())
    return f'{m.group(3)}/{m.group(2)}/{m.group(1)}' if m else ''


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



# ----------------------------------------------------------------- lista importada e exclusões
COR_EXCLUIDOS_PADRAO = '#FDE2E2'
MOTIVOS_EXCLUSAO = ('faltas', 'ppf', 'pdf', 'transferida', 'obito', 'outros')
MAX_LISTA_BYTES = 2 * 1024 * 1024
MAX_LINHAS_LISTA = 2000
_ALIAS = {
    'apelido': {'apelido', 'apelidos', 'sobrenome'},
    'nome': {'nome', 'nomes', 'nomedoaluno', 'nomecompleto', 'aluno'},
    'classe': {'classe', 'ano', 'grau'},
    'turma': {'turma'},
    'area': {'area', 'seccao', 'areaseccao', 'seccaoarea', 'curso'},
    'numero': {'n', 'no', 'numero', 'nordem', 'ordem', 'nodeordem'},
    'codigo': {'codigo', 'matricula', 'processo', 'nprocesso', 'noprocesso', 'codigodoaluno', 'nmatricula'},
    'situacao': {'situacao', 'estado', 'observacao', 'observacoes', 'motivo'},
    'genero': {'sexo', 'genero', 'hm', 'mf'},
    'faltas': {'faltas', 'totaldefaltas', 'totalfaltas', 'nfaltas', 'nodefaltas', 'numerodefaltas', 'faltasacumuladas',
               'totaldefaltasacumuladas', 'tfaltas', 'totfaltas'},
}


def _num_faltas(v):
    """Faltas indicadas na lista importada («12», «12 faltas», «12,0»); 0 se vazio ou ilegível."""
    m = re.search(r'\d+', str(v or '').replace(',', '.'))
    return int(m.group()) if m else 0


def _sem_acentos(t):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(t or '')) if not unicodedata.combining(c)).lower()


def _chave(t):
    return re.sub(r'[^a-z0-9]', '', _sem_acentos(t))


def _nome_norm(t):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', _sem_acentos(t))).strip()


def _linhas_do_ficheiro(ficheiro):
    nome = (getattr(ficheiro, 'name', '') or '').lower()
    dados = ficheiro.read(MAX_LISTA_BYTES + 1)
    if len(dados) > MAX_LISTA_BYTES:
        raise ValueError('A lista é demasiado grande (máximo 2 MB).')
    if nome.endswith('.xlsx'):
        import openpyxl
        try:
            wb = openpyxl.load_workbook(io.BytesIO(dados), read_only=True, data_only=True)
        except Exception:
            raise ValueError('Não foi possível ler o Excel da lista.') from None
        ws = wb.worksheets[0]
        return [[('' if c is None else str(c).strip()) for c in linha] for linha in ws.iter_rows(values_only=True, max_row=MAX_LINHAS_LISTA)]
    if nome.endswith(('.csv', '.txt')):
        try:
            texto = dados.decode('utf-8-sig')
        except UnicodeDecodeError:
            texto = dados.decode('latin-1')
        amostra = texto[:2000]
        sep = max(';,\t', key=amostra.count) if any(s in amostra for s in ';,\t') else ';'
        return [[c.strip() for c in linha] for linha in csv.reader(io.StringIO(texto), delimiter=sep)][:MAX_LINHAS_LISTA]
    raise ValueError('Formato da lista não suportado: use Excel (.xlsx) ou CSV.')


def _candidatos_da_lista(ficheiro, escola):
    """Alunos de uma lista importada (nunca guardada). Cabeçalho obrigatório; basta a coluna Nome."""
    linhas = [l for l in _linhas_do_ficheiro(ficheiro) if any(l)]
    cab, mapa = None, {}
    for idx, linha in enumerate(linhas[:10]):
        m = {}
        for col, cel in enumerate(linha):
            for campo, alias in _ALIAS.items():
                if _chave(cel) in alias and campo not in m:
                    m[campo] = col
        if 'nome' in m:
            cab, mapa = idx, m
            break
    if cab is None:
        raise ValueError('A lista precisa de cabeçalho com a coluna «Nome» (opcionais: Apelido, Classe, Turma, '
                         'Secção/Área, Nº, Código, Situação).')
    brutos = []
    for linha in linhas[cab + 1:]:
        def val(campo):
            c = mapa.get(campo)
            return re.sub(r'\s+', ' ', linha[c]).strip() if c is not None and c < len(linha) else ''
        if val('nome') or val('apelido'):
            brutos.append({k: val(k) for k in _ALIAS})
    codigos = [b['codigo'] for b in brutos if b['codigo']]
    do_sistema = {a.matricula: a for a in Aluno.objects.filter(escola=escola, matricula__in=codigos).select_related('turma')} if codigos else {}
    cands = []
    for b in brutos:
        a = do_sistema.get(b['codigo']) if b['codigo'] else None
        base = fr.montar_dados_aluno(a, None) if a else {}
        try:
            numero = int(re.sub(r'\D', '', b['numero'])) if b['numero'] else base.get('numero')
        except ValueError:
            numero = None
        dados = {
            'apelido': b['apelido'] or base.get('apelido', ''), 'nome': b['nome'] or base.get('nome', ''),
            'classe': b['classe'] or base.get('classe', ''), 'turma': b['turma'] or base.get('turma', ''),
            'area': b['area'] or base.get('area', ''), 'numero': numero, 'codigo': b['codigo'],
            'genero': b['genero'] or base.get('genero', ''),
            'faltas_lista': _num_faltas(b['faltas']),   # coluna «Total de Faltas» do ficheiro (conta para a exclusão)
        }
        cands.append({'dados': dados, 'aluno': a, 'situacao': b['situacao']})
    return cands


def _lista(form, nome):
    if hasattr(form, 'getlist'):
        return form.getlist(nome)
    v = form.get(nome)
    return list(v) if isinstance(v, (list, tuple)) else ([v] if v else [])


def regra_da_escola(escola):
    """Regra guardada da escola: {verificar_sempre, motivos[], faltas_minimo}."""
    from ..models import RegraExclusaoEscudo
    r = RegraExclusaoEscudo.objects.filter(escola=escola).first() if escola else None
    return {'verificar_sempre': bool(r and r.verificar_sempre),
            'motivos': [m for m in (r.motivos if r else []) if m in MOTIVOS_EXCLUSAO],
            'faltas_minimo': r.faltas_minimo if r else 0,
            'cor_excluidos': (r.cor_excluidos if r else '') or COR_EXCLUIDOS_PADRAO}


def guardar_regra(escola, form):
    """Guarda a regra («verificar automaticamente e sempre», motivos e total de faltas) da escola."""
    from ..models import RegraExclusaoEscudo
    motivos = [m for m in _lista(form, 'motivos') if m in MOTIVOS_EXCLUSAO and m != 'outros']
    try:
        minimo = int(form.get('faltas_minimo') or 0)
    except (TypeError, ValueError):
        raise ValueError('O total de faltas tem de ser um número inteiro.') from None
    if minimo < 0 or minimo > 999:
        raise ValueError('O total de faltas deve estar entre 1 e 999.')
    sempre = _on(form, 'verificar_sempre')
    if sempre and 'faltas' in motivos and minimo < 1:
        raise ValueError('Defina o total de faltas acumuladas (1 ou mais) a partir do qual o aluno não faz a prova.')
    if sempre and not motivos:
        raise ValueError('Marque pelo menos um motivo para a verificação automática.')
    defaults = {'verificar_sempre': sempre, 'motivos': motivos, 'faltas_minimo': minimo}
    if form.get('cor_excluidos'):
        defaults['cor_excluidos'] = cor_valida(form.get('cor_excluidos'))
    RegraExclusaoEscudo.objects.update_or_create(escola=escola, defaults=defaults)
    return regra_da_escola(escola)


def _aplicar_exclusoes(form, p, escola, ano, cands):
    """Devolve (incluídos, excluídos[(dados, motivo)]). Aplica o que se marcou («Sim») e, se a escola o pediu,
    a regra «verificar automaticamente e sempre» (com o total de faltas definido no sistema)."""
    regra = regra_da_escola(escola)
    manual = _on(form, 'folha_excluir')
    motivos = {m for m in _lista(form, 'folha_excluir_motivo') if m in MOTIVOS_EXCLUSAO} if manual else set()
    if manual and not motivos and not regra['verificar_sempre']:
        raise ValueError('Indique o motivo da exclusão (Faltas, PPF, PDF, Transferida, Óbito ou Outros).')
    minimo = 0
    if manual:
        try:
            minimo = int(form.get('folha_excluir_faltas') or 0)
        except ValueError:
            minimo = 0
    if regra['verificar_sempre']:
        motivos |= set(regra['motivos'])
        if 'faltas' in regra['motivos'] and regra['faltas_minimo'] >= 1:
            minimo = min(minimo, regra['faltas_minimo']) if minimo >= 1 else regra['faltas_minimo']
    if not motivos:
        return cands, []
    if 'faltas' in motivos and minimo < 1:
        raise ValueError('Indique o número mínimo de faltas (1 ou mais) ou defina o total de faltas na verificação automática.')
    outros = {_nome_norm(l) for l in re.split(r'[\r\n;]+', form.get('folha_excluir_outros') or '') if _nome_norm(l)}
    if 'outros' in motivos and not outros and len(motivos) == 1:
        raise ValueError('Em «Outros», indique os alunos a excluir (código ou nome, um por linha).')
    faltas, anot = {}, {}
    ids = [c['aluno'].id for c in cands if c['aluno']]
    if ids and motivos & {'faltas', 'ppf', 'pdf'}:
        for aid, f, an in Nota.objects.filter(escola=escola, aluno_id__in=ids, turma__ano_letivo=ano,
                                              disciplina__nome__iexact=p.get('disciplina') or '').values_list('aluno_id', 'faltas', 'anotacao'):
            faltas[aid] = faltas.get(aid, 0) + (f or 0)
            anot.setdefault(aid, set()).add((an or '').strip().upper())
        if 'faltas' in motivos:
            # faltas reais registadas nas presenças (justificadas + injustificadas) neste ano e disciplina;
            # vale o maior entre o lançado na caderneta e o contado nas presenças
            from apps.alunos.models import PresencaAluno
            reais = PresencaAluno.objects.filter(
                escola=escola, aluno_id__in=ids, turma__ano_letivo=ano, disciplina__nome__iexact=p.get('disciplina') or '',
                status__in=('FALTA_JUSTIFICADA', 'FALTA_INJUSTIFICADA')).values('aluno_id').annotate(n=Count('id'))
            for r in reais:
                faltas[r['aluno_id']] = max(faltas.get(r['aluno_id'], 0), r['n'])

    incluidos, excluidos = [], []
    for c in cands:
        a, sit, d = c['aluno'], _sem_acentos(c['situacao']), c['dados']
        aid = a.id if a else None
        razao = []
        if 'faltas' in motivos:
            # vale o maior entre as faltas do sistema e o «Total de Faltas» da lista importada
            total_f = max(faltas.get(aid, 0) if aid else 0, d.get('faltas_lista') or 0)
            if total_f >= minimo:
                razao.append(f'Faltas: {total_f} (mínimo {minimo})')
        for cod, rot in (('ppf', 'PPF'), ('pdf', 'PDF')):
            if cod in motivos and ((aid and rot in anot.get(aid, ())) or re.search(rf'\b{cod}\b', sit)):
                razao.append(rot)
        if 'transferida' in motivos and ((a and (a.status or '').upper() == 'TRANSFERIDO') or 'transfer' in sit):
            razao.append('Transferida')
        if 'obito' in motivos and ((a and (a.status or '').upper() in ('FALECIDO', 'OBITO', 'ÓBITO')) or re.search(r'obito|falecid', sit)):
            razao.append('Óbito')
        if 'outros' in motivos:
            chaves = {_nome_norm(d['codigo']), _nome_norm(f"{d['apelido']} {d['nome']}"),
                      _nome_norm(f"{d['nome']} {d['apelido']}"), _nome_norm(d['nome'])} - {''}
            if chaves & outros:
                razao.append('Outros (indicado na lista de exclusão)')
        if razao:
            excluidos.append((d, '; '.join(razao)))
        else:
            incluidos.append(c)
    return incluidos, excluidos


def _relatorio_excluidos(excluidos):
    """CSV (só para o professor) com os alunos que ficaram de fora e porquê."""
    if not excluidos:
        return b''
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=';')
    w.writerow(['Nº', 'Código', 'Apelido', 'Nome', 'Classe', 'Turma', 'Motivo da exclusão'])
    for d, motivo in excluidos:
        w.writerow([d.get('numero') or '', d.get('codigo') or '', d.get('apelido') or '', d.get('nome') or '',
                    d.get('classe') or '', d.get('turma') or '', motivo])
    return buf.getvalue().encode('utf-8-sig')

def cor_valida(valor, padrao=None):
    from apps.documentos.services.lista_alunos_service import COR_EXCLUIDOS_PADRAO as P, cor_valida as cv
    return cv(valor, padrao or P)


def cor_dos_excluidos(escola, pedida=None):
    """Cor pedida neste pedido; senão a guardada na regra da escola; senão a cor por omissão."""
    return cor_valida(pedida, regra_da_escola(escola)['cor_excluidos'])


def listas_geradas(escola, dados_alunos, excluidos, titulo, referencia='', todos=None, cor=None):
    """(pdf, xlsx) com quem teve a folha/prova gerada (e quantos) e, se houver, quem ficou de fora e porquê."""
    from apps.documentos.services import lista_alunos_service as la
    cor = cor_dos_excluidos(escola, cor)
    return (la.lista_pdf(escola, titulo, dados_alunos, excluidos, referencia, todos, cor),
            la.lista_xlsx(escola, titulo, dados_alunos, excluidos, referencia, todos, cor))


def excluir_alunos(escola, ano, disciplina, cands, form):
    """Aplica as exclusões (marcadas no ecrã e/ou a regra automática da escola). `cands`: [{dados, aluno, situacao}].
    Devolve (incluídos, excluídos). `form` usa os mesmos nomes de campo do Escudo (folha_excluir…)."""
    return _aplicar_exclusoes(form, {'disciplina': disciplina}, escola, ano, cands)


def _escola_da_prova(p, alternativa=None):
    """A escola da prova; se a prova não tiver (Super Admin sem escola), a escola seleccionada ou da conta."""
    escola = Escola.objects.filter(id=p.get('escola_id')).first() if p.get('escola_id') else None
    return escola or alternativa


def preparar(p, form, ficheiros=None, escola_alt=None, previa=False):
    """None se a prova não leva folha; senão dicionário com `personalizada`, `total` e `para(n)` (bytes PDF da folha da cópia n)."""
    if not _on(form, 'folha_resposta'):
        return None
    escola = _escola_da_prova(p, escola_alt)
    if not escola:
        raise ValueError('Para a folha de resposta, seleccione primeiro a escola (Super Admin) ou use uma conta de escola.')
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
        # dados da avaliação impressos na folha: só o que o utilizador indicar (nada é inventado)
        'duracao_min': form.get('folha_duracao') or 0,
        'data': _data_br(form.get('folha_data')),
        'hora_inicio': (form.get('folha_hora_inicio') or '').strip(),
        'hora_fim': (form.get('folha_hora_fim') or '').strip(),
        'sala': (form.get('folha_sala') or '').strip(),
        'professor': (form.get('folha_professor') or '').strip(),
        'versoes': (form.get('folha_versoes') or '').strip(),
        'instrucao_extra': (form.get('folha_instrucao') or '').strip(),
    }
    ab_n = re.sub(r'\D', '', str(form.get('folha_abertas_n') or ''))
    if ab_n and int(ab_n) > 0:  # parte de perguntas abertas / demonstração: a cotação entra no total e é impressa
        cfg_in['abertas'] = [{'rotulo': (form.get('folha_abertas_rotulo') or '').strip(), 'n': int(ab_n),
                              'cotacao': str(form.get('folha_abertas_cot') or '0').replace(',', '.')}]
    if classe:
        discs = Disciplina.objects.filter(escola=escola, ano_letivo=ano, classe=classe)
        cfg_in['disciplinas_classe'] = list(discs.order_by('nome').values_list('nome', flat=True).distinct())
    config = fr.normalizar_config(cfg_in, esc)

    if not personalizada:
        pdf, _ = fr.gerar_folhas_pdf(esc, [None], config, ano)
        return {'personalizada': False, 'total': 0, 'alunos': [], 'excluidos': [], 'relatorio': b'', 'listas': None, 'para': lambda n: pdf}

    if (form.get('folha_fonte') or 'sistema') == 'lista':
        ficheiro = (ficheiros or {}).get('folha_lista')
        if not ficheiro:
            raise ValueError('Escolha o ficheiro da lista de alunos (Excel .xlsx ou CSV).')
        cands = _candidatos_da_lista(ficheiro, escola)
    else:
        if not classe:
            raise ValueError('Escolha a classe das folhas personalizadas.')
        area = (form.get('folha_area') or '').strip()
        turma_id = (form.get('folha_turma_id') or '').strip()
        try:
            trio = _alunos_do_ambito(escola, ano, classe, area, turma_id)
        except Exception:  # id de turma mal formado
            raise ValueError('Turma inválida.') from None
        cands = [{'dados': fr.montar_dados_aluno(a, i), 'aluno': a, 'situacao': ''} for _, a, i in trio]
    if not cands:
        raise ValueError('Não existem alunos activos neste âmbito: não há folhas personalizadas a gerar.')

    incluidos, excluidos = _aplicar_exclusoes(form, p, escola, ano, cands)
    if not incluidos:
        raise ValueError('Todos os alunos ficaram excluídos: não há folhas personalizadas a gerar.')
    if previa:  # só a folha do primeiro aluno, para ser rápida
        incluidos = incluidos[:1]
    if len(incluidos) > MAX_COPIAS:
        raise ValueError(f'Há {len(incluidos)} alunos neste âmbito; o máximo é {MAX_COPIAS} cópias por vez. '
                         'Escolha uma secção ou uma turma, ou exclua alunos.')
    dados = [c['dados'] for c in incluidos]
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
            'excluidos': excluidos, 'relatorio': _relatorio_excluidos(excluidos),
            'listas': lambda: listas_geradas(escola, dados, excluidos, 'Lista de alunos com prova gerada',
                                             f"{p.get('titulo') or ''} · {p.get('disciplina') or ''}".strip(' ·'),
                                             [c['dados'] for c in cands], form.get('folha_cor_excluidos')),
            'para': lambda n: folhas[(n - 1) % len(folhas)]}

def contexto(p, escola_alt=None):
    """Dados reais para os filtros em cascata: classes → turmas (com secção/área e nº de alunos activos)."""
    escola = _escola_da_prova(p, escola_alt)
    if not escola:
        return {'sem_escola': True, 'classes': [], 'tipos_avaliacao': [{'codigo': c, 'rotulo': r} for c, r in fr.TIPOS_AVALIACAO],
                'logo_proprio_disponivel': False}
    ano = escola.ano_letivo_ativo
    turmas = list(Turma.objects.filter(escola=escola, ano_letivo=ano).order_by('grau_ano', 'nome'))
    contagem = {}
    for t_id in Aluno.objects.filter(escola=escola, status='ATIVO', turma__in=turmas).values_list('turma_id', flat=True):
        contagem[t_id] = contagem.get(t_id, 0) + 1
    classes = {}
    for t in turmas:
        classes.setdefault(t.grau_ano, []).append({'id': str(t.id), 'nome': t.nome, 'area': t.area or '',
                                                   'alunos': contagem.get(t.id, 0)})
    return {
        'ano_letivo': ano,
        'classes': [{'classe': k, 'turmas': v, 'total_alunos': sum(x['alunos'] for x in v)} for k, v in classes.items()],
        'tipos_avaliacao': [{'codigo': c, 'rotulo': r} for c, r in fr.TIPOS_AVALIACAO],
        'logo_proprio_disponivel': bool(fr.logo_proprio_escola(escola)),
        'regra_exclusao': regra_da_escola(escola),
    }


def prefixar_word(folha_pdf, docx_bytes, dpi=170):
    """Word final: a(s) página(s) da folha de resposta (como imagem a página inteira) antes do conteúdo da prova."""
    import io
    from docx import Document
    from docx.enum.text import WD_BREAK
    from docx.shared import Emu
    doc = Document(io.BytesIO(docx_bytes))
    corpo = doc.element.body
    sec = doc.sections[0]
    larg = sec.page_width - sec.left_margin - sec.right_margin
    alt = sec.page_height - sec.top_margin - sec.bottom_margin - Emu(91440)  # folga para o salto de página
    novos = []
    with fitz.open(stream=folha_pdf, filetype='pdf') as fp:
        for pagina in fp:
            png = pagina.get_pixmap(dpi=dpi).tobytes('png')
            p = doc.add_paragraph()
            p.paragraph_format.space_before = p.paragraph_format.space_after = 0
            run = p.add_run()
            razao = pagina.rect.width / pagina.rect.height
            w = min(larg, int(alt * razao))
            run.add_picture(io.BytesIO(png), width=Emu(w))
            run.add_break(WD_BREAK.PAGE)
            novos.append(p._p)
    for el in novos:  # add_paragraph acrescenta no fim: mover para o início, mantendo a ordem
        corpo.remove(el)
    for i, el in enumerate(novos):
        corpo.insert(i, el)
    saida = io.BytesIO()
    doc.save(saida)
    return saida.getvalue()


def prefixar(folha_pdf, copia_pdf, aluno=None):
    """PDF final: páginas da folha de resposta primeiro, depois a cópia selada da prova."""
    saida = fitz.open()
    for dados in (folha_pdf, copia_pdf):
        with fitz.open(stream=dados, filetype='pdf') as doc:
            saida.insert_pdf(doc)
    if aluno:
        saida.set_toc([[1, aluno, 1]])
        saida.set_metadata({'title': f'Prova — {aluno}'})
    resultado = saida.tobytes(garbage=3, deflate=True)
    saida.close()
    return resultado
