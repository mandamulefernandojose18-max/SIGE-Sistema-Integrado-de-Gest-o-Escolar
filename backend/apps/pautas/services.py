from common.utils.avaliacoes_mocambique import obter_nome_completo_aluno
import re
import unicodedata
from collections import Counter
from apps.disciplinas.models import Disciplina
from apps.professores.models import AlocacaoDocente
from apps.notas.models import Nota

# Nomes oficiais completos das disciplinas (MEC - Moçambique)
# REGRA: Não abreviar os nomes das disciplinas nas pautas
MATERIA_NOMES_OFICIAIS = {
    'LP': 'Língua Portuguesa',
    'ING': 'Língua Inglesa',
    'FRAN': 'Língua Francesa',
    'FILO': 'Filosofia',
    'HIS': 'História',
    'GEO': 'Geografia',
    'MAT': 'Matemática',
    'MATA': 'Matemática Aplicada',
    'FIS': 'Física',
    'QUI': 'Química',
    'BIO': 'Biologia',
    'DGD': 'Desenho e Geometria Descritiva',
    'EV': 'Educação Visual',
    'EF': 'Educação Física',
    'AGRO': 'Agropecuária',
    'LIT': 'Introdução à Literatura',
    'TIC': 'TIC',
}

# Ordem curricular oficial do Sistema Nacional de Educação de Moçambique (ESG)
ORDEM_CURRICULAR_CANONICA = [
    'LP',    # Língua Portuguesa
    'ING',   # Língua Inglesa
    'FRAN',  # Língua Francesa
    'FILO',  # Filosofia
    'HIS',   # História
    'GEO',   # Geografia
    'MAT',   # Matemática
    'MATA',  # Matemática Aplicada
    'FIS',   # Física
    'QUI',   # Química
    'BIO',   # Biologia
    'DGD',   # Desenho e Geometria Descritiva
    'EV',    # Educação Visual
    'LIT',   # Introdução à Literatura
    'AGRO',  # Agropecuária
    'EF',    # Educação Física
    'TIC',   # Informática / TIC
]

# Matrizes curriculares oficiais do MEC por secção/área
CURRICULO_REGRAS_AREAS = {
    'CIENCIAS_GEOGRAFIA': {
        'permitidas': {'LP', 'ING', 'FILO', 'EF', 'MAT', 'GEO', 'FIS', 'QUI', 'AGRO'},
        'proibidas': {'HIS', 'FRAN', 'BIO', 'DGD', 'EV', 'LIT', 'MATA'},
        'sufixo_codigo': 'CG',
        'nome_oficial': 'Ciências com Geografia',
    },
    'CIENCIAS_BIOLOGIA': {
        'permitidas': {'LP', 'ING', 'FILO', 'EF', 'MAT', 'BIO', 'QUI', 'FIS'},
        'proibidas': {'GEO', 'HIS', 'FRAN', 'DGD', 'EV', 'LIT', 'MATA', 'AGRO'},
        'sufixo_codigo': 'CB',
        'nome_oficial': 'Ciências com Biologia',
    },
    'CIENCIAS_DESENHO': {
        'permitidas': {'LP', 'ING', 'FILO', 'EF', 'MAT', 'FIS', 'DGD', 'QUI'},
        'proibidas': {'BIO', 'GEO', 'HIS', 'FRAN', 'EV', 'LIT', 'MATA', 'AGRO'},
        'sufixo_codigo': 'CD',
        'nome_oficial': 'Ciências com Desenho',
    },
    'CIENCIAS_GERAL': {
        'permitidas': {'LP', 'ING', 'FILO', 'EF', 'MAT', 'FIS', 'QUI', 'BIO'},
        'proibidas': {'HIS', 'FRAN', 'DGD', 'EV', 'LIT', 'MATA', 'AGRO'},
        'sufixo_codigo': 'C',
        'nome_oficial': 'Ciências',
    },
    'LETRAS_GEOGRAFIA': {
        'permitidas': {'LP', 'ING', 'FRAN', 'FILO', 'HIS', 'GEO', 'MATA', 'EF'},
        'proibidas': {'MAT', 'FIS', 'QUI', 'BIO', 'DGD', 'EV', 'LIT', 'AGRO'},
        'sufixo_codigo': 'LG',
        'nome_oficial': 'Letras com Geografia',
    },
    'LETRAS_HISTORIA': {
        'permitidas': {'LP', 'ING', 'FRAN', 'FILO', 'HIS', 'GEO', 'LIT', 'EF'},
        'proibidas': {'MAT', 'MATA', 'FIS', 'QUI', 'BIO', 'DGD', 'EV', 'AGRO'},
        'sufixo_codigo': 'LH',
        'nome_oficial': 'Letras com História',
    },
    'LETRAS_GERAL': {
        'permitidas': {'LP', 'ING', 'FRAN', 'FILO', 'HIS', 'GEO', 'EF'},
        'proibidas': {'MAT', 'FIS', 'QUI', 'BIO', 'DGD', 'EV', 'LIT', 'MATA', 'AGRO'},
        'sufixo_codigo': 'L',
        'nome_oficial': 'Letras',
    },
    'GERAL': {
        'permitidas': {'LP', 'MAT', 'ING', 'FIS', 'QUI', 'BIO', 'GEO', 'HIS', 'EV', 'EF', 'AGRO', 'TIC', 'FILO'},
        'proibidas': {'FRAN', 'DGD', 'LIT', 'MATA'},
        'sufixo_codigo': '',
        'nome_oficial': 'Ensino Geral',
    }
}


def normalizar_texto(texto):
    """Normaliza texto removendo acentos e convertendo para minúsculas."""
    if not texto:
        return ''
    t = unicodedata.normalize('NFKD', str(texto))
    t = t.encode('ASCII', 'ignore').decode('utf-8')
    return t.strip().lower()


def extrair_numero_classe(classe_str):
    """Extrai o número inteiro da classe (ex: '11ª Classe' -> 11)."""
    if not classe_str:
        return None
    m = re.search(r'\d+', str(classe_str))
    return int(m.group(0)) if m else None


def identificar_materia_canonica(d):
    """
    Identifica o código canônico da matéria (ex: 'LP', 'GEO', 'QUI')
    a partir do código e do nome da disciplina.
    """
    cod = (d.codigo or '').strip().upper()
    nome_norm = normalizar_texto(d.nome or '')

    # 1. Análise por prefixo exato do código curricular
    if cod.startswith('MATA-') or cod.startswith('MATA') or 'MATA' in cod:
        return 'MATA'
    if cod.startswith('MAT-') or cod.startswith('MAT') or cod.startswith('Mat-') or cod == 'MAT':
        return 'MAT'
    if cod.startswith('FRAN-') or cod.startswith('FRAN') or cod.startswith('Fran-'):
        return 'FRAN'
    if cod.startswith('GEO-') or cod.startswith('GEO') or cod.startswith('Geo-'):
        return 'GEO'
    if cod.startswith('HIS-') or cod.startswith('HIS') or cod.startswith('His-'):
        return 'HIS'
    if cod.startswith('FILO-') or cod.startswith('FILO') or cod.startswith('Filo-'):
        return 'FILO'
    if cod.startswith('FIS-') or cod.startswith('FIS') or cod.startswith('Fis-'):
        return 'FIS'
    if cod.startswith('QUI-') or cod.startswith('QUI') or cod.startswith('Qui-'):
        return 'QUI'
    if cod.startswith('BIO-') or cod.startswith('BIO') or cod.startswith('Bio-'):
        return 'BIO'
    if cod.startswith('DGD-') or cod.startswith('DGD') or cod.startswith('Dgd-'):
        return 'DGD'
    if cod.startswith('EV-') or cod.startswith('EV') or cod.startswith('Ev-'):
        return 'EV'
    if cod.startswith('LIT-') or cod.startswith('LIT') or cod.startswith('Lit-'):
        return 'LIT'
    if cod.startswith('AGRO-') or cod.startswith('AGRO') or cod.startswith('Agro') or cod.startswith("Agro'"):
        return 'AGRO'
    if cod.startswith('EF-') or cod.startswith('EF') or cod.startswith('Ef-'):
        return 'EF'
    if cod.startswith('ING-') or cod.startswith('ING') or cod.startswith('Ing-'):
        return 'ING'
    if cod.startswith('LP-') or cod.startswith('LP') or cod.startswith('Port-') or cod.startswith('PORT-'):
        return 'LP'
    if cod.startswith('TIC-') or cod.startswith('TIC') or cod.startswith('INF-'):
        return 'TIC'

    # 2. Análise pelo nome por termos específicos (da expressão mais longa para a mais curta)
    if 'matematica aplicada' in nome_norm:
        return 'MATA'
    if 'matematica' in nome_norm:
        return 'MAT'
    if 'desenho e geometria' in nome_norm or nome_norm == 'dgd':
        return 'DGD'
    if 'educacao visual' in nome_norm or nome_norm == 'desenho':
        return 'EV'
    if 'educacao fisica' in nome_norm or 'ed. fisica' in nome_norm or 'ed fisica' in nome_norm:
        return 'EF'
    if 'introducao a literatura' in nome_norm or 'literatura' in nome_norm:
        return 'LIT'
    if 'introducao a filosofia' in nome_norm or 'filosofia' in nome_norm:
        return 'FILO'
    if 'lingua francesa' in nome_norm or 'frances' in nome_norm:
        return 'FRAN'
    if 'lingua inglesa' in nome_norm or 'ingles' in nome_norm:
        return 'ING'
    if 'lingua portuguesa' in nome_norm or 'portugues' in nome_norm:
        return 'LP'
    if 'agropecuaria' in nome_norm:
        return 'AGRO'
    if 'biologia' in nome_norm:
        return 'BIO'
    if 'quimica' in nome_norm:
        return 'QUI'
    if 'fisica' in nome_norm:
        return 'FIS'
    if 'geografia' in nome_norm:
        return 'GEO'
    if 'historia' in nome_norm:
        return 'HIS'
    if 'informatica' in nome_norm or 'tic' in nome_norm:
        return 'TIC'

    return None


def categorizar_area(area_str, nome_contexto=''):
    """
    Retorna uma tupla (ramo, sub_area):
    ramo: 'CIENCIAS', 'LETRAS', 'GERAL'
    sub_area: 'CIENCIAS_BIOLOGIA', 'CIENCIAS_DESENHO', 'CIENCIAS_GEOGRAFIA', 'CIENCIAS_GERAL',
              'LETRAS_GEOGRAFIA', 'LETRAS_HISTORIA', 'LETRAS_GERAL', 'GERAL'
    """
    combinado = f"{area_str or ''} {nome_contexto or ''}"
    norm = normalizar_texto(combinado)

    # 1. Sub-áreas específicas de Ciências
    # Suporte a abreviações como CG, CB, CD, C. Geografia, etc.
    if re.search(r'\b(cg)\b', norm) or (('cienc' in norm or 'cinc' in norm) and ('geo' in norm or 'geog' in norm)):
        return 'CIENCIAS', 'CIENCIAS_GEOGRAFIA'
    if re.search(r'\b(cb)\b', norm) or (('cienc' in norm or 'cinc' in norm) and ('bio' in norm or 'biol' in norm)):
        return 'CIENCIAS', 'CIENCIAS_BIOLOGIA'
    if re.search(r'\b(cd)\b', norm) or (('cienc' in norm or 'cinc' in norm) and ('desenh' in norm or 'dgd' in norm or 'geom' in norm)):
        return 'CIENCIAS', 'CIENCIAS_DESENHO'

    # 2. Sub-áreas específicas de Letras
    # Suporte a abreviações como LG, LH, L. Geografia, etc.
    if re.search(r'\b(lg)\b', norm) or ('letr' in norm and ('geo' in norm or 'geog' in norm)):
        return 'LETRAS', 'LETRAS_GEOGRAFIA'
    if re.search(r'\b(lh)\b', norm) or ('letr' in norm and ('hist' in norm or 'lit' in norm)):
        return 'LETRAS', 'LETRAS_HISTORIA'

    # Se contém Geografia mas não Letras, e há indicação de Ciências
    if 'geografia' in norm and ('cienc' in norm or 'cinc' in norm):
        return 'CIENCIAS', 'CIENCIAS_GEOGRAFIA'
    if 'biologia' in norm and ('cienc' in norm or 'cinc' in norm):
        return 'CIENCIAS', 'CIENCIAS_BIOLOGIA'
    if 'desenho' in norm and ('cienc' in norm or 'cinc' in norm):
        return 'CIENCIAS', 'CIENCIAS_DESENHO'

    # 3. Ramos gerais do 2º Ciclo
    if 'cienc' in norm or 'cinc' in norm:
        return 'CIENCIAS', 'CIENCIAS_GERAL'
    if 'letr' in norm:
        return 'LETRAS', 'LETRAS_GERAL'

    return 'GERAL', 'GERAL'


def categorizar_disciplina(d):
    """
    Determina o ramo e sub-área de uma disciplina a partir de seu código, área e nome.
    """
    cod_norm = (d.codigo or '').strip().upper()
    nome_norm = normalizar_texto(d.nome or '')
    area_norm = normalizar_texto(d.area or '')

    # 1. Códigos curriculares nacionais do MEC (ex: LP-11CB, FIS-11CD, FRAN-11LG)
    if 'CB' in cod_norm:
        return 'CIENCIAS', 'CIENCIAS_BIOLOGIA'
    if 'CD' in cod_norm:
        return 'CIENCIAS', 'CIENCIAS_DESENHO'
    if 'CG' in cod_norm:
        return 'CIENCIAS', 'CIENCIAS_GEOGRAFIA'
    if 'LG' in cod_norm:
        return 'LETRAS', 'LETRAS_GEOGRAFIA'
    if 'LH' in cod_norm:
        return 'LETRAS', 'LETRAS_HISTORIA'

    # 2. Campo área explicitamente cadastrado
    if area_norm and area_norm not in ('geral', 'ensino geral', 'tronco comum'):
        ramo, sub = categorizar_area(d.area)
        if sub != 'GERAL':
            return ramo, sub

    # 3. Matérias exclusivas de ramos
    materia = identificar_materia_canonica(d)
    if materia == 'DGD':
        return 'CIENCIAS', 'CIENCIAS_DESENHO'
    if materia == 'BIO':
        return 'CIENCIAS', 'CIENCIAS_BIOLOGIA'
    if materia == 'FRAN':
        return 'LETRAS', 'LETRAS_GERAL'
    if materia == 'LIT':
        return 'LETRAS', 'LETRAS_HISTORIA'
    if materia == 'MATA':
        return 'LETRAS', 'LETRAS_GEOGRAFIA'
    if materia == 'HIS':
        return 'LETRAS', 'LETRAS_GERAL'

    return 'GERAL', 'GERAL'


def disciplina_pertence_a_area_turma(d, turma, ramo_turma, sub_turma, num_classe_turma):
    """
    Verifica se a disciplina `d` pertence estrita e exclusivamente à área/secção da turma.
    Regra do usuário: "A(s) pauta(s) deve ter disciplinas so e so daquela seccao ou area...
    Por exemplo Ciencias com Geografia, nao tem Historia, Frances, Biologia, Desenho e Geometria Descritiva."
    """
    cod_d = (d.codigo or '').strip().upper()
    area_d = normalizar_texto(d.area or '')
    materia_key = identificar_materia_canonica(d)
    ramo_disc, sub_disc = categorizar_disciplina(d)

    # 1. Validação para turmas do Ensino Geral / Tronco Comum (7ª a 10ª classe)
    if ramo_turma == 'GERAL' and (num_classe_turma and num_classe_turma <= 10):
        if any(suf in cod_d for suf in ['-11', '-12', '11CB', '12CB', '11CD', '12CD', '11CG', '12CG', '11LG', '12LG', '11LH', '12LH']):
            return False
        if any(termo in area_d for termo in ['ciencias com', 'letras com', 'biologia e quimica', 'desenho e geometria']):
            return False
        if materia_key in {'FRAN', 'DGD', 'LIT', 'MATA'}:
            return False
        if materia_key == 'FILO' and num_classe_turma < 10:
            return False
        if materia_key == 'EV' and num_classe_turma >= 10:
            return False
        return True

    # 2. Turmas do 2º Ciclo (11ª e 12ª Classes) com área definida
    regras = CURRICULO_REGRAS_AREAS.get(sub_turma) or CURRICULO_REGRAS_AREAS.get(ramo_turma) or CURRICULO_REGRAS_AREAS.get('CIENCIAS_GEOGRAFIA')

    # A) REJEIÇÃO CATEGÓRICA: Se a matéria for proibida para esta área curricular
    if materia_key and materia_key in regras['proibidas']:
        return False

    # B) REJEIÇÃO CATEGÓRICA: Se a disciplina tiver área cadastrada de outra sub-área específica diferente
    if sub_disc not in ('GERAL', 'CIENCIAS_GERAL', 'LETRAS_GERAL') and sub_disc != sub_turma:
        return False

    # C) Rejeição por códigos curriculares cruzados de outras áreas
    if sub_turma == 'CIENCIAS_GEOGRAFIA':
        if any(s in cod_d for s in ['-11CB', '-12CB', '-11CD', '-12CD', '-11LG', '-12LG', '-11LH', '-12LH', '11CB', '12CB', '11CD', '12CD', '11LG', '12LG', '11LH', '12LH']):
            return False
        if ramo_disc == 'LETRAS' or 'letr' in area_d or 'bio' in area_d or 'desenh' in area_d:
            return False

    elif sub_turma == 'CIENCIAS_BIOLOGIA':
        if any(s in cod_d for s in ['-11CG', '-12CG', '-11CD', '-12CD', '-11LG', '-12LG', '-11LH', '-12LH', '11CG', '12CG', '11CD', '12CD', '11LG', '12LG', '11LH', '12LH']):
            return False
        if ramo_disc == 'LETRAS' or 'letr' in area_d or 'geo' in area_d or 'desenh' in area_d or 'agro' in area_d:
            return False

    elif sub_turma == 'CIENCIAS_DESENHO':
        if any(s in cod_d for s in ['-11CG', '-12CG', '-11CB', '-12CB', '-11LG', '-12LG', '-11LH', '-12LH', '11CG', '12CG', '11CB', '12CB', '11LG', '12LG', '11LH', '12LH']):
            return False
        if ramo_disc == 'LETRAS' or 'letr' in area_d or 'bio' in area_d or 'geo' in area_d or 'agro' in area_d:
            return False

    elif sub_turma == 'LETRAS_GEOGRAFIA':
        if any(s in cod_d for s in ['-11CB', '-12CB', '-11CD', '-12CD', '-11CG', '-12CG', '-11LH', '-12LH', '11CB', '12CB', '11CD', '12CD', '11CG', '12CG', '11LH', '12LH']):
            return False
        if ramo_disc == 'CIENCIAS' or 'cienc' in area_d or 'lit' in area_d or 'agro' in area_d:
            return False

    elif sub_turma == 'LETRAS_HISTORIA':
        if any(s in cod_d for s in ['-11CB', '-12CB', '-11CD', '-12CD', '-11CG', '-12CG', '-11LG', '-12LG', '11CB', '12CB', '11CD', '12CD', '11CG', '12CG', '11LG', '12LG']):
            return False
        if ramo_disc == 'CIENCIAS' or 'cienc' in area_d or 'mata' in area_d or 'agro' in area_d:
            return False

    # D) Pertinência às matérias oficiais permitidas
    if materia_key and materia_key in regras['permitidas']:
        return True

    # E) Se a disciplina estiver cadastrada com o nome exato da área da turma
    area_turma_norm = normalizar_texto(turma.area or '')
    if area_turma_norm and area_turma_norm not in ('geral', 'ensino geral', 'tronco comum'):
        if area_d == area_turma_norm:
            return True

    return False


def obter_disciplinas_pauta_turma(turma):
    """
    Retorna única e exclusivamente as disciplinas pertencentes ao plano curricular da secção/área da turma,
    carregando estritamente as disciplinas cadastradas e disponíveis para aquela escola, classe e área,
    com os nomes completos e oficiais (sem abreviações), deduplicadas e ordenadas
    rigorosamente conforme o currículo oficial do MEC.
    """
    escola = turma.escola
    grau_turma = (turma.grau_ano or '').strip()
    num_classe = extrair_numero_classe(grau_turma)

    # 1. Determinar área efetiva da turma
    area_turma = (turma.area or '').strip()
    ramo_turma, sub_turma = categorizar_area(area_turma, turma.nome)

    # Para 11ª e 12ª Classes: o 2º Ciclo é estritamente dividido em Áreas/Secções curriculares.
    # Se a turma constar como Geral ou ambígua, inferir rigorosamente a secção oficial real.
    if (num_classe and num_classe in (11, 12)) and sub_turma in ('GERAL', 'CIENCIAS_GERAL', 'LETRAS_GERAL'):
        # A) Pelos alunos matriculados ativos
        areas_alunos = list(turma.alunos.filter(status='ATIVO')
                            .exclude(area__in=['', 'Geral', 'Ensino Geral', 'Tronco Comum', None])
                            .values_list('area', flat=True))
        if areas_alunos:
            area_mais_comum = Counter(areas_alunos).most_common(1)[0][0]
            ramo_turma, sub_turma = categorizar_area(area_mais_comum)

        # B) Pelas alocações de professores já cadastradas para a turma
        if sub_turma in ('GERAL', 'CIENCIAS_GERAL', 'LETRAS_GERAL'):
            alocs_areas = list(Disciplina.objects.filter(alocacoes__turma=turma, escola=escola)
                               .exclude(area__in=['', 'Geral', 'Ensino Geral', 'Tronco Comum', None])
                               .values_list('area', flat=True))
            if alocs_areas:
                area_mais_comum = Counter(alocs_areas).most_common(1)[0][0]
                ramo_turma, sub_turma = categorizar_area(area_mais_comum)

        # C) Pelas notas já lançadas na turma
        if sub_turma in ('GERAL', 'CIENCIAS_GERAL', 'LETRAS_GERAL'):
            notas_areas = list(Disciplina.objects.filter(notas__turma=turma, escola=escola)
                               .exclude(area__in=['', 'Geral', 'Ensino Geral', 'Tronco Comum', None])
                               .values_list('area', flat=True))
            if notas_areas:
                area_mais_comum = Counter(notas_areas).most_common(1)[0][0]
                ramo_turma, sub_turma = categorizar_area(area_mais_comum)

        # D) Se mesmo assim for 11ª/12ª, verificar se o nome da turma tem indícios de Ciências ou Letras
        if sub_turma in ('GERAL', 'CIENCIAS_GERAL', 'LETRAS_GERAL'):
            r_nome, s_nome = categorizar_area(turma.nome)
            if s_nome not in ('GERAL', 'CIENCIAS_GERAL', 'LETRAS_GERAL'):
                ramo_turma, sub_turma = r_nome, s_nome

        # E) Consultar quais áreas oficiais estão cadastradas na escola para essa classe
        if sub_turma in ('GERAL', 'CIENCIAS_GERAL', 'LETRAS_GERAL'):
            areas_cadastradas = list(Disciplina.objects.filter(escola=escola, classe__icontains=str(num_classe))
                                     .exclude(area__in=['', 'Geral', 'Ensino Geral', 'Tronco Comum', None])
                                     .values_list('area', flat=True))
            if areas_cadastradas:
                contagens = Counter([categorizar_area(a)[1] for a in areas_cadastradas if categorizar_area(a)[1] not in ('GERAL', 'CIENCIAS_GERAL', 'LETRAS_GERAL')])
                if contagens:
                    sub_turma = contagens.most_common(1)[0][0]
                    ramo_turma = 'LETRAS' if 'LETRAS' in sub_turma else 'CIENCIAS'

        # F) Regra final de proteção: nunca deixar turma de 11ª/12ª em "Geral" para não criar pautas fictícias
        if sub_turma in ('GERAL', 'CIENCIAS_GERAL'):
            sub_turma = 'CIENCIAS_GEOGRAFIA'
            ramo_turma = 'CIENCIAS'
        elif sub_turma == 'LETRAS_GERAL':
            sub_turma = 'LETRAS_GEOGRAFIA'
            ramo_turma = 'LETRAS'

    # 2. Carregar IDs de disciplinas com notas e com docentes alocados (1 query cada, sem N+1)
    try:
        disc_ids_com_notas = set(Nota.objects.filter(turma=turma).values_list('disciplina_id', flat=True))
    except Exception:
        disc_ids_com_notas = set()

    try:
        disc_ids_alocadas = set(AlocacaoDocente.objects.filter(turma=turma).values_list('disciplina_id', flat=True))
    except Exception:
        disc_ids_alocadas = set()

    # 3. Buscar disciplinas candidatas da escola para a mesma classe
    qs = Disciplina.objects.filter(escola=escola)
    if num_classe:
        qs = qs.filter(classe__icontains=str(num_classe))
    elif grau_turma:
        qs = qs.filter(classe__iexact=grau_turma)

    disciplinas_candidatas = list(qs)

    # Incluir também quaisquer disciplinas que já tenham docentes alocados nesta turma
    if disc_ids_alocadas:
        for d_aloc in Disciplina.objects.filter(id__in=disc_ids_alocadas, escola=escola):
            if d_aloc not in disciplinas_candidatas:
                disciplinas_candidatas.append(d_aloc)

    # 4. Filtrar única e exclusivamente as disciplinas pertencentes à área da turma
    disciplinas_filtradas = []
    for d in disciplinas_candidatas:
        num_classe_d = extrair_numero_classe(d.classe)
        if num_classe and num_classe_d and num_classe != num_classe_d:
            continue

        if disciplina_pertence_a_area_turma(d, turma, ramo_turma, sub_turma, num_classe):
            disciplinas_filtradas.append(d)

    # 5. Agrupamento e Deduplicação por matéria canônica
    # Garante que "Língua Inglesa" e "Inglês" nunca apareçam duplicados na mesma pauta
    regras = CURRICULO_REGRAS_AREAS.get(sub_turma) or CURRICULO_REGRAS_AREAS.get(ramo_turma) or CURRICULO_REGRAS_AREAS.get('CIENCIAS_GEOGRAFIA')
    sufixo_esperado = regras.get('sufixo_codigo', '')

    grupos_por_materia = {}
    for d in disciplinas_filtradas:
        chave_mat = identificar_materia_canonica(d) or normalizar_texto(d.nome)
        if chave_mat not in grupos_por_materia:
            grupos_por_materia[chave_mat] = []
        grupos_por_materia[chave_mat].append(d)

    disciplinas_finais = []
    for chave_mat, lista in grupos_por_materia.items():
        if len(lista) == 1:
            escolhida = lista[0]
        else:
            # Pontuação para selecionar a melhor disciplina representante da turma
            def pontuar(d):
                pt = 0
                if d.id in disc_ids_com_notas:
                    pt += 25
                if d.id in disc_ids_alocadas:
                    pt += 15
                r_d, s_d = categorizar_disciplina(d)
                if s_d == sub_turma and sub_turma != 'GERAL':
                    pt += 10
                if normalizar_texto(d.area) == normalizar_texto(area_turma) and area_turma:
                    pt += 10
                cod_u = (d.codigo or '').upper()
                if sufixo_esperado and sufixo_esperado in cod_u:
                    pt += 5
                # Prefere disciplinas com o nome oficial já expandido
                if d.nome and d.nome.strip() == MATERIA_NOMES_OFICIAIS.get(chave_mat):
                    pt += 2
                return pt

            escolhida = max(lista, key=pontuar)

        # Atribuição estrita do nome completo oficial sem abreviação
        nome_completo_oficial = MATERIA_NOMES_OFICIAIS.get(chave_mat)
        if nome_completo_oficial:
            escolhida.nome = nome_completo_oficial
        elif escolhida.nome:
            escolhida.nome = escolhida.nome.strip()

        disciplinas_finais.append(escolhida)

    # 6. Ordenação curricular oficial estrita
    def ordem_sort_key(d):
        chave_mat = identificar_materia_canonica(d)
        if chave_mat and chave_mat in ORDEM_CURRICULAR_CANONICA:
            return (ORDEM_CURRICULAR_CANONICA.index(chave_mat), d.nome)
        return (999, d.nome)

    disciplinas_finais.sort(key=ordem_sort_key)
    return disciplinas_finais


# =====================================================================
# REGRAS E CONSOLIDAÇÃO DA PAUTA DE EXAMES OFICIAIS (MEC / MOÇAMBIQUE)
# =====================================================================

def obter_classes_com_exame_escola(escola):
    """
    Retorna a lista de nomes de classes/níveis que possuem regime de exame na escola.
    Garante que todas as classes com exame da instituição fiquem disponíveis automaticamente.
    """
    classes_exame = set()

    # 1. Da configuração explícita de classes/níveis da instituição
    cfg = getattr(escola, 'config_classes_exames', {}) or {}
    if isinstance(cfg, dict):
        for nome, tem_ex in cfg.items():
            if tem_ex:
                classes_exame.add(str(nome).strip())

    # 2. Das turmas ativas da instituição
    if escola:
        from apps.turmas.models import Turma
        turmas = Turma.objects.filter(escola=escola).exclude(grau_ano__isnull=True).exclude(grau_ano='')
        for t in turmas:
            if turma_tem_exame(t, escola):
                classes_exame.add(t.grau_ano.strip())

    # 3. Fallback nacional MEC se nenhuma configuração explícita existir
    if not classes_exame:
        regime = getattr(escola, 'regime_curricular', 'CLASSES') or 'CLASSES'
        if regime == 'CLASSES':
            classes_exame.update(['10ª Classe', '12ª Classe'])
        else:
            classes_exame.update(['Nível 3', 'Nível 5'])

    def sort_key(c):
        m = re.search(r'\d+', c)
        return int(m.group(0)) if m else 999

    return sorted(list(classes_exame), key=sort_key)


def turma_tem_exame(turma, escola=None):
    """
    Verifica se a turma pertence a uma classe ou nível com regime de exame oficial.
    Por padrão em Moçambique: 10ª Classe e 12ª Classe.
    Além disso, respeita qualquer classe configurada com tem_exame=True na escola.
    """
    if not turma:
        return False
    grau = str(getattr(turma, 'grau_ano', '') or '').strip()
    if re.search(r'(^|[^\d])(10|12)([ªaº\.\s]|$)', grau.lower()):
        return True

    esc = escola or getattr(turma, 'escola', None)
    if esc and hasattr(esc, 'config_classes_exames') and isinstance(esc.config_classes_exames, dict):
        for k, v in esc.config_classes_exames.items():
            if v and (k.lower() in grau.lower() or grau.lower() in k.lower()):
                return True
    return False


def disciplina_tem_exame_na_turma(disciplina, turma):
    """
    Determina se uma disciplina específica realiza exame oficial na respectiva turma/classe.
    Respeita a configuração explícita disciplina.tem_exame, classes configuradas pela instituição
    e a matriz curricular oficial MEC.
    """
    if getattr(disciplina, 'tem_exame', False):
        return True

    m_canon = identificar_materia_canonica(disciplina)
    grau = str(getattr(turma, 'grau_ano', '') or '').lower()
    tem_regime_exame = turma_tem_exame(turma)

    # 10ª Classe (ou turmas do 1º Ciclo com regime de exame):
    if re.search(r'(^|[^\d])10([ªaº\.\s]|$)', grau) or (tem_regime_exame and not re.search(r'(^|[^\d])(11|12)([ªaº\.\s]|$)', grau)):
        if m_canon in {'LP', 'ING', 'HIS', 'GEO', 'BIO', 'QUI', 'FIS', 'MAT'}:
            return True
        return False

    # 11ª e 12ª Classes (ou 2º Ciclo com regime de exame): Exames por secção/área
    if re.search(r'(^|[^\d])(11|12)([ªaº\.\s]|$)', grau) or tem_regime_exame:
        _, sub_area = categorizar_area(getattr(turma, 'area', ''), getattr(turma, 'nome', ''))
        if sub_area == 'CIENCIAS_BIOLOGIA' and m_canon in {'LP', 'MAT', 'BIO', 'QUI', 'ING', 'FILO'}:
            return True
        elif sub_area == 'CIENCIAS_DESENHO' and m_canon in {'LP', 'MAT', 'FIS', 'DGD', 'ING', 'FILO'}:
            return True
        elif sub_area == 'CIENCIAS_GEOGRAFIA' and m_canon in {'LP', 'MAT', 'GEO', 'FIS', 'QUI', 'ING', 'FILO'}:
            return True
        elif sub_area in ('LETRAS_GEOGRAFIA', 'LETRAS_HISTORIA', 'LETRAS_GERAL') and m_canon in {'LP', 'HIS', 'GEO', 'FRAN', 'ING', 'FILO'}:
            return True
        elif m_canon in {'LP', 'MAT', 'ING', 'FILO', 'QUI', 'GEO', 'FIS', 'BIO'}:
            return True
        return False

    return False




def obter_disciplinas_com_exame_escola(escola):
    """
    Retorna as disciplinas que realizam exame oficial na instituicao escolar,
    agrupadas por nome e identificando o grupo de professores associados
    (por especialidade e/ou alocacao docente).
    """
    if not escola:
        return []

    from apps.disciplinas.models import Disciplina
    from apps.professores.models import Professor, AlocacaoDocente
    from apps.turmas.models import Turma

    classes_exame = set(obter_classes_com_exame_escola(escola))
    turmas_exame = list(Turma.objects.filter(escola=escola).exclude(grau_ano__isnull=True))
    turmas_exame = [t for t in turmas_exame if turma_tem_exame(t, escola)]

    todas_discs = list(Disciplina.objects.filter(escola=escola))
    profs_ativos = list(Professor.objects.filter(escola=escola, ativo=True).order_by('nome'))
    alocacoes = list(AlocacaoDocente.objects.filter(escola=escola).select_related('professor', 'disciplina'))

    profs_por_disc_id = {}
    profs_por_disc_nome = {}
    for al in alocacoes:
        if not al.professor or not al.disciplina:
            continue
        p_id = str(al.professor.id)
        d_id = str(al.disciplina.id)
        d_nome_norm = al.disciplina.nome.strip().lower()

        if d_id not in profs_por_disc_id:
            profs_por_disc_id[d_id] = set()
        profs_por_disc_id[d_id].add(p_id)

        if d_nome_norm not in profs_por_disc_nome:
            profs_por_disc_nome[d_nome_norm] = set()
        profs_por_disc_nome[d_nome_norm].add(p_id)

    discs_exame_map = {}

    for d in todas_discs:
        nome_clean = d.nome.strip()
        nome_norm = nome_clean.lower()
        codigo_clean = (d.codigo or '').strip()

        tem_ex = getattr(d, 'tem_exame', False)
        classes_onde_tem_ex = set()

        if not tem_ex and turmas_exame:
            for t in turmas_exame:
                if disciplina_tem_exame_na_turma(d, t):
                    tem_ex = True
                    if t.grau_ano:
                        classes_onde_tem_ex.add(t.grau_ano.strip())
        elif tem_ex:
            if d.classe and any(c.lower() in d.classe.lower() for c in classes_exame):
                classes_onde_tem_ex.add(d.classe.strip())
            else:
                classes_onde_tem_ex.update(classes_exame)

        if not tem_ex:
            m_canon = identificar_materia_canonica(d)
            if m_canon in {'LP', 'MAT', 'ING', 'HIS', 'GEO', 'BIO', 'QUI', 'FIS', 'FILO', 'DGD', 'FRAN'}:
                tem_ex = True
                classes_onde_tem_ex.update(classes_exame)

        if tem_ex:
            if nome_norm not in discs_exame_map:
                discs_exame_map[nome_norm] = {
                    'nome': nome_clean,
                    'codigo': codigo_clean,
                    'ids': [str(d.id)],
                    'classes': set(classes_onde_tem_ex) if classes_onde_tem_ex else set(classes_exame),
                }
            else:
                discs_exame_map[nome_norm]['ids'].append(str(d.id))
                if classes_onde_tem_ex:
                    discs_exame_map[nome_norm]['classes'].update(classes_onde_tem_ex)

    resultado = []
    for nome_norm, info in sorted(discs_exame_map.items(), key=lambda x: x[1]['nome']):
        prof_ids_grupo = set()

        for d_id in info['ids']:
            prof_ids_grupo.update(profs_por_disc_id.get(d_id, set()))
        prof_ids_grupo.update(profs_por_disc_nome.get(nome_norm, set()))

        for p in profs_ativos:
            p_id = str(p.id)
            p_esp = (p.especialidade or '').strip().lower()
            if p_esp and (p_esp in nome_norm or nome_norm in p_esp or any(pal in p_esp for pal in nome_norm.split() if len(pal) > 3)):
                prof_ids_grupo.add(p_id)

        profs_grupo_detalhe = []
        for p in profs_ativos:
            p_id = str(p.id)
            if p_id in prof_ids_grupo:
                profs_grupo_detalhe.append({
                    'id': p_id,
                    'nome': p.nome,
                    'codigo': p.codigo or '',
                    'especialidade': p.especialidade or '',
                    'email': p.email or ''
                })

        resultado.append({
            'nome': info['nome'],
            'codigo': info['codigo'],
            'ids': info['ids'],
            'classes': sorted(list(info['classes'])),
            'professores_grupo': profs_grupo_detalhe,
            'professores_ids': sorted(list(prof_ids_grupo))
        })

    return resultado


def resolver_permissoes_exames_usuario(user, escola, turma=None, disciplinas_info=None):
    """
    Resolve as permissoes do utilizador para lancamento de notas de exame.
    Suporta:
    - APENAS_DAP: Exclusivo do DAP e gestao.
    - TODOS_PROFESSORES: Todos os professores ativos.
    - ALGUNS_PROFESSORES: Permissao delegada por classe e por grupo de disciplina (parcial).
    """
    user_role = getattr(user, 'role', '') if user else ''
    is_gestao = user_role in ('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP', '')

    if not user or not getattr(user, 'is_authenticated', False):
        return {
            'pode_editar': False,
            'is_gestao': False,
            'disciplinas_autorizadas_ids': [],
            'disciplinas_autorizadas_nomes': [],
            'is_permissao_parcial': False,
            'motivo_bloqueio': 'Autenticacao necessaria para lancar notas de exame.'
        }

    if is_gestao:
        return {
            'pode_editar': True,
            'is_gestao': True,
            'disciplinas_autorizadas_ids': None,
            'disciplinas_autorizadas_nomes': None,
            'is_permissao_parcial': False,
            'motivo_bloqueio': ''
        }

    if user_role != 'PROFESSOR':
        return {
            'pode_editar': False,
            'is_gestao': False,
            'disciplinas_autorizadas_ids': [],
            'disciplinas_autorizadas_nomes': [],
            'is_permissao_parcial': False,
            'motivo_bloqueio': 'Apenas o Director Pedagogico ou professores autorizados podem lancar notas de exame.'
        }

    esc = escola or (getattr(turma, 'escola', None) if turma else None)
    cfg_p = esc.get_config_parametros_exames() if (esc and hasattr(esc, 'get_config_parametros_exames')) else {}
    modo = cfg_p.get('modo_permissao_exames', 'ALGUNS_PROFESSORES')

    if modo == 'TODOS_PROFESSORES':
        return {
            'pode_editar': True,
            'is_gestao': False,
            'disciplinas_autorizadas_ids': None,
            'disciplinas_autorizadas_nomes': None,
            'is_permissao_parcial': False,
            'motivo_bloqueio': ''
        }

    if modo == 'APENAS_DAP':
        return {
            'pode_editar': False,
            'is_gestao': False,
            'disciplinas_autorizadas_ids': [],
            'disciplinas_autorizadas_nomes': [],
            'is_permissao_parcial': False,
            'motivo_bloqueio': 'O lancamento das notas de exame nesta instituicao e de competencia exclusiva do Director Pedagogico.'
        }

    prof_id = getattr(user, 'professor_id', None)
    if not prof_id and getattr(user, 'email', None) and esc:
        from apps.professores.models import Professor
        p_obj = Professor.objects.filter(escola=esc, email=user.email).first()
        if p_obj:
            prof_id = p_obj.id

    grau_turma = getattr(turma, 'grau_ano', '') or ''
    profs_aut = cfg_p.get('professores_autorizados_exame', [])

    autorizacao_prof = None
    for aut in profs_aut:
        if str(aut.get('professor_id')) == str(prof_id) and aut.get('ativo', True):
            autorizacao_prof = aut
            break

    if not autorizacao_prof:
        return {
            'pode_editar': False,
            'is_gestao': False,
            'disciplinas_autorizadas_ids': [],
            'disciplinas_autorizadas_nomes': [],
            'is_permissao_parcial': False,
            'motivo_bloqueio': f'O lancamento de notas de exame nesta classe esta reservado ao Director Pedagogico ou professores autorizados.'
        }

    classes_aut = autorizacao_prof.get('classes', [])
    if classes_aut and not any(c.lower() in grau_turma.lower() or grau_turma.lower() in c.lower() for c in classes_aut):
        return {
            'pode_editar': False,
            'is_gestao': False,
            'disciplinas_autorizadas_ids': [],
            'disciplinas_autorizadas_nomes': [],
            'is_permissao_parcial': False,
            'motivo_bloqueio': f'Nao possui autorizacao para lancar notas de exame na classe {grau_turma}.'
        }

    discs_aut = autorizacao_prof.get('disciplinas', [])
    if not discs_aut or '*' in discs_aut:
        return {
            'pode_editar': True,
            'is_gestao': False,
            'disciplinas_autorizadas_ids': None,
            'disciplinas_autorizadas_nomes': None,
            'is_permissao_parcial': False,
            'motivo_bloqueio': ''
        }

    discs_aut_norm = [str(d).strip().lower() for d in discs_aut if str(d).strip()]

    if disciplinas_info is None and turma:
        from apps.pautas.services import obter_disciplinas_pauta_turma, disciplina_tem_exame_na_turma
        discs_t = obter_disciplinas_pauta_turma(turma)
        disciplinas_info = [
            {'id': str(d.id), 'nome': d.nome, 'codigo': d.codigo or '', 'tem_exame': disciplina_tem_exame_na_turma(d, turma)}
            for d in discs_t
        ]

    disciplinas_com_exame = [d for d in (disciplinas_info or []) if d.get('tem_exame')]

    permitidas_ids = []
    permitidas_nomes = []
    for d in disciplinas_com_exame:
        d_id = str(d.get('id', ''))
        d_nome = str(d.get('nome', '')).strip().lower()
        d_cod = str(d.get('codigo', '')).strip().lower()

        match = False
        for alvo in discs_aut_norm:
            if alvo == d_id.lower() or alvo == d_cod or alvo == d_nome or alvo in d_nome or d_nome in alvo:
                match = True
                break
        if match:
            permitidas_ids.append(d['id'])
            permitidas_nomes.append(d.get('nome', ''))

    if not permitidas_ids:
        return {
            'pode_editar': False,
            'is_gestao': False,
            'disciplinas_autorizadas_ids': [],
            'disciplinas_autorizadas_nomes': [],
            'is_permissao_parcial': True,
            'motivo_bloqueio': f'Nao possui autorizacao para lancar notas de exame nas disciplinas com exame desta turma ({grau_turma}).'
        }

    is_parcial = (len(permitidas_ids) < len(disciplinas_com_exame))
    nomes_str = ', '.join(permitidas_nomes)
    motivo = f'Lancamento Parcial Activo: autorizado exclusivamente para: {nomes_str}.' if is_parcial else ''

    return {
        'pode_editar': True,
        'is_gestao': False,
        'disciplinas_autorizadas_ids': permitidas_ids,
        'disciplinas_autorizadas_nomes': permitidas_nomes,
        'is_permissao_parcial': is_parcial,
        'motivo_bloqueio': motivo
    }


def consolidar_pauta_exames(turma, ano_letivo='2026'):
    """
    Gera a Pauta Oficial de Exames do SIGE estruturada fielmente ao modelo do MEC:
    - Disciplinas e Médias de Proveniência (Frequência) extraídas diretamente das pautas de frequência (reais, não fictícias).
    - Sub-colunas para disciplinas com exame: Frequência (Proven.), Exame 1ª, Exame 2ª, Média da Disciplina.
    - Coluna única para disciplinas sem exame: Frequência.
    - RESULTADO FINAL: Aprovado(a), MF (Média Final), Disciplina(s) que Reprovou.
    """
    from apps.alunos.models import Aluno
    from apps.notas.models import Nota, NotaExame
    from common.utils.avaliacoes_mocambique import avaliar_aprovacao_pauta

    # 1. Carregar disciplinas da turma
    disciplinas = obter_disciplinas_pauta_turma(turma)

    # Identificar quais têm exame e quais não têm
    disciplinas_info = []
    disciplinas_objs_map = {}
    for d in disciplinas:
        tem_ex = disciplina_tem_exame_na_turma(d, turma)
        disciplinas_objs_map[str(d.id)] = d
        disciplinas_info.append({
            'id': str(d.id),
            'nome': d.nome,
            'codigo': d.codigo or '',
            'tem_exame': tem_ex
        })

    # 2. Carregar alunos ativos da turma
    alunos = list(Aluno.objects.filter(turma=turma, status='ATIVO').order_by('nome', 'apelido'))

    # 3. Carregar notas de frequência de todos os trimestres
    todas_notas = list(Nota.objects.filter(turma=turma).select_related('disciplina'))
    notas_freq_map = {}
    notas_freq_por_nome = {}
    for n in todas_notas:
        if n.disciplina_id:
            notas_freq_map[(n.aluno_id, n.disciplina_id, n.periodo)] = n
        if n.disciplina and n.disciplina.nome:
            notas_freq_por_nome[(n.aluno_id, n.disciplina.nome.strip().lower(), n.periodo)] = n

    # 4. Carregar notas de exame salvas
    notas_exame_objs = list(NotaExame.objects.filter(turma=turma, ano_letivo=ano_letivo))
    notas_exame_map = {}
    for ne in notas_exame_objs:
        notas_exame_map[(ne.aluno_id, ne.disciplina_id)] = ne

    # 0. Obter configurações de parâmetros de exame da escola
    escola = getattr(turma, 'escola', None)
    if escola and hasattr(escola, 'get_config_parametros_exames'):
        cfg_exames = escola.get_config_parametros_exames()
    elif escola and hasattr(escola, 'config_parametros_exames'):
        cfg_exames = escola.config_parametros_exames or {}
    else:
        cfg_exames = {}

    try:
        peso_freq = float(cfg_exames.get('peso_frequencia', 50.0))
    except (ValueError, TypeError):
        peso_freq = 50.0

    try:
        peso_exame = float(cfg_exames.get('peso_exame', 50.0))
    except (ValueError, TypeError):
        peso_exame = 50.0

    try:
        nota_minima = float(cfg_exames.get('nota_minima_exame', 10.0))
    except (ValueError, TypeError):
        nota_minima = 10.0

    grau_ano = getattr(turma, 'grau_ano', '') or '10ª Classe'
    is_12a = bool(re.search(r'(^|[^\d])12([ªaº\.\s]|$)', grau_ano.lower()))

    dados_alunos = []
    total_aprovados = 0
    total_reprovados = 0
    total_admitidos = 0
    total_excluidos = 0
    total_segunda_epoca = 0

    for idx, aluno in enumerate(alunos, start=1):
        aluno_nome_completo = obter_nome_completo_aluno(aluno)
        genero = (aluno.genero or 'M').upper()
        sufixo_genero = 'a' if genero.startswith('F') else 'o'

        disciplinas_aluno = {}
        notas_finais_calc = []
        disciplinas_reprovadas = []

        tem_algum_exame = False
        aluno_tem_2epoca_pendente = False

        for d_info in disciplinas_info:
            d_id = d_info['id']
            d_obj = disciplinas_objs_map.get(d_id)
            tem_ex = d_info['tem_exame']

            # Calcular média de frequência real a partir dos trimestres
            # Obter registo de exame antecipadamente para fallback de frequência
            ne_obj = notas_exame_map.get((aluno.id, d_obj.id))

            # Calcular média de frequência real a partir dos trimestres ou do registo oficial
            def extrair_val(per):
                n = (
                    notas_freq_map.get((aluno.id, d_obj.id, per))
                    or (notas_freq_por_nome.get((aluno.id, d_info['nome'].strip().lower(), per)) if d_info.get('nome') else None)
                )
                if not n:
                    return None
                if n.media_final is not None:
                    try:
                        return float(n.media_final)
                    except (ValueError, TypeError):
                        pass
                if hasattr(n, 'media_trimestral') and n.media_trimestral is not None:
                    try:
                        return float(n.media_trimestral)
                    except (ValueError, TypeError):
                        pass
                testes = [getattr(n, c) for c in ['teste1', 'teste2', 'teste3', 'teste4', 'trabalho', 'avaliacao_trimestral'] if getattr(n, c, None) is not None]
                if testes:
                    try:
                        valid_testes = [float(v) for v in testes]
                        return round(sum(valid_testes) / len(valid_testes), 1)
                    except (ValueError, TypeError):
                        pass
                return None

            t1 = extrair_val('1_TRIMESTRE')
            t2 = extrair_val('2_TRIMESTRE')
            t3 = extrair_val('3_TRIMESTRE')

            vals_tri = [v for v in [t1, t2, t3] if v is not None]
            if vals_tri:
                mfreq_val = round(sum(vals_tri) / len(vals_tri), 1)
                mfreq_int = int(round(mfreq_val))
            elif ne_obj and getattr(ne_obj, 'nota_frequencia', None) is not None:
                try:
                    mfreq_val = round(float(ne_obj.nota_frequencia), 1)
                    mfreq_int = int(round(mfreq_val))
                except (ValueError, TypeError):
                    mfreq_val = None
                    mfreq_int = None
            else:
                mfreq_val = None
                mfreq_int = None

            raw_e1 = getattr(ne_obj, 'exame_1epoca', None) if ne_obj else None
            raw_e2 = getattr(ne_obj, 'exame_2epoca', None) if ne_obj else None

            def format_num_exame(v):
                if v is None:
                    return None
                try:
                    num = float(v)
                    if num == int(num):
                        return int(num)
                    return round(num, 2)
                except (ValueError, TypeError):
                    return v

            e1 = format_num_exame(raw_e1)
            e2 = format_num_exame(raw_e2)

            if e1 is not None or e2 is not None:
                tem_algum_exame = True

            nota_exame_efetiva = None
            aprovado_1epoca = False
            pode_fazer_2epoca = False
            situacao_exame = 'Pendente'

            # REGRA OFICIAL DE ADMISSÃO AO EXAME:
            # Se na nota de frequência tiver uma nota <= 9.4 (negativa), então o aluno
            # NÃO TEM DIREITO AO EXAME, fica 'Excluído', e os campos de exame devem estar vazios.
            e_excluido = (mfreq_val is not None and mfreq_val <= 9.4)

            if e_excluido:
                e1 = None
                e2 = None
                nota_exame_efetiva = None
                aprovado_1epoca = False
                pode_fazer_2epoca = False
                situacao_exame = 'Excluído'
                media_disc_int = mfreq_int if mfreq_int is not None else int(round(mfreq_val))
                res_disc = 'Excluído'
                aprov_disc = False
                total_excluidos += 1
                disciplinas_reprovadas.append(f"{d_info['nome']} (Excluído)")
            elif tem_ex:
                e1_val = float(e1) if e1 is not None else None
                e2_val = float(e2) if e2 is not None else None

                if e1_val is not None and e1_val >= nota_minima:
                    # Aprovado diretamente na 1ª época!
                    nota_exame_efetiva = e1_val
                    aprovado_1epoca = True
                    pode_fazer_2epoca = False
                    situacao_exame = 'Aprovado 1ª época'
                elif e1_val is not None and e1_val < nota_minima:
                    # Não atingiu a nota mínima na 1ª época -> tem direito à 2ª época
                    if e2_val is not None:
                        nota_exame_efetiva = e2_val
                        pode_fazer_2epoca = False
                        if e2_val >= nota_minima:
                            situacao_exame = 'Aprovado 2ª época'
                        else:
                            situacao_exame = 'Reprovado 2ª época'
                    else:
                        # Ainda não realizou a 2ª época
                        nota_exame_efetiva = None
                        pode_fazer_2epoca = True
                        aluno_tem_2epoca_pendente = True
                        situacao_exame = '2ª época'
                elif e1_val is None and e2_val is not None:
                    # Realizou exame diretamente na 2ª época
                    nota_exame_efetiva = e2_val
                    pode_fazer_2epoca = False
                    if e2_val >= nota_minima:
                        situacao_exame = 'Aprovado 2ª época'
                    else:
                        situacao_exame = 'Reprovado 2ª época'
                else:
                    # Nenhum exame lançado ainda
                    nota_exame_efetiva = None
                    pode_fazer_2epoca = True
                    situacao_exame = 'Pendente'

                # Cálculo ponderado da Média Final da Disciplina
                if nota_exame_efetiva is not None:
                    if mfreq_val is not None:
                        media_disc_val = round((mfreq_val * (peso_freq / 100.0)) + (nota_exame_efetiva * (peso_exame / 100.0)), 1)
                        media_disc_int = int(round(media_disc_val))
                    else:
                        media_disc_int = int(round(nota_exame_efetiva))
                else:
                    # Se não tem nota num dos exames (1ª ou 2ª) então a Média nessa disciplina é 0
                    media_disc_int = 0

                aprov_disc = (media_disc_int is not None and media_disc_int >= 9.5)
                res_disc = f"Aprovad{sufixo_genero}" if aprov_disc else f"Reprovad{sufixo_genero}"
                if not aprov_disc:
                    disciplinas_reprovadas.append(d_info['nome'])
            else:
                # Disciplina sem exame (a nota final é a própria frequência)
                media_disc_int = mfreq_int if mfreq_int is not None else 0
                situacao_exame = 'Sem Exame'
                aprov_disc = (media_disc_int is not None and media_disc_int >= 9.5)
                res_disc = f"Aprovad{sufixo_genero}" if aprov_disc else f"Reprovad{sufixo_genero}"
                if not aprov_disc:
                    disciplinas_reprovadas.append(d_info['nome'])

            notas_finais_calc.append({'disciplina': d_info['nome'], 'notaFinal': media_disc_int if media_disc_int is not None else 0})

            disciplinas_aluno[d_id] = {
                'disciplina_id': d_id,
                'nome': d_info['nome'],
                'codigo': d_info['codigo'],
                'tem_exame': tem_ex,
                'frequencia': format_num_exame(mfreq_val) if mfreq_val is not None else '-',
                'frequencia_decimal': mfreq_val,
                'excluido': e_excluido,
                'exame_1epoca': e1 if not e_excluido else None,
                'exame_2epoca': e2 if not e_excluido else None,
                'aprovado_1epoca': aprovado_1epoca,
                'pode_fazer_2epoca': pode_fazer_2epoca,
                'situacao_exame': situacao_exame,
                'nota_exame_efetiva': nota_exame_efetiva,
                'media': media_disc_int,
                'resultado': res_disc,
                'aprovado': aprov_disc
            }

        # Avaliar Resultado Final do Aluno:
        # REGRA SOLICITADA: 'Aprovado' se tiver todas as disciplinas Positivas e com média igual ou superior a 9.5, e caso contrário 'Reprovado'.
        if notas_finais_calc:
            soma_finais = sum(n['notaFinal'] for n in notas_finais_calc)
            mf_global = int(round(soma_finais / len(notas_finais_calc)))
            total_negativas = len(disciplinas_reprovadas)

            aprovado_geral = (total_negativas == 0 and mf_global >= 9.5)
            resultado_final = f"Aprovad{sufixo_genero}" if aprovado_geral else f"Reprovad{sufixo_genero}"
            if aprovado_geral:
                total_aprovados += 1
            else:
                total_reprovados += 1
        else:
            mf_global = 0
            resultado_final = f"Reprovad{sufixo_genero}"
            total_reprovados += 1

        dados_alunos.append({
            'numero': idx,
            'id': str(aluno.id),
            'aluno_id': str(aluno.id),
            'candidato': aluno.matricula or f"CAND-{idx:03d}",
            'matricula': aluno.matricula or f"CAND-{idx:03d}",
            'nome': aluno_nome_completo,
            'genero': genero,
            'turma': turma.nome,
            'disciplinas': disciplinas_aluno,
            'resultado_final': {
                'aprovado': resultado_final,
                'resultado': resultado_final,
                'mf': mf_global,
                'media_final': mf_global,
                'disciplinas_reprovou': ", ".join(disciplinas_reprovadas) if disciplinas_reprovadas else "---",
                'total_negativas': len(disciplinas_reprovadas)
            }
        })

    total_alunos = len(dados_alunos)
    homens = sum(1 for a in dados_alunos if a['genero'] == 'M')
    mulheres = sum(1 for a in dados_alunos if a['genero'].startswith('F'))

    estatisticas = {
        'total': total_alunos,
        'homens': homens,
        'mulheres': mulheres,
        'aprovados': total_aprovados,
        'reprovados': total_reprovados,
        'admitidos': total_admitidos,
        'excluidos': total_excluidos,
        'segunda_epoca': total_segunda_epoca,
        'taxa_aprovacao': round((total_aprovados / (total_aprovados + total_reprovados) * 100), 1) if (total_aprovados + total_reprovados) > 0 else 0.0
    }

    return {
        'turma': {
            'id': str(turma.id),
            'nome': turma.nome,
            'grau_ano': turma.grau_ano,
            'area': turma.area,
            'turno': getattr(turma, 'turno', 'Diurno') or 'Diurno',
            'ano_letivo': ano_letivo,
            'tem_exame': turma_tem_exame(turma)
        },
        'parametros': {
            'peso_frequencia': peso_freq,
            'peso_exame': peso_exame,
            'nota_minima_exame': nota_minima,
            'nota_maxima_exame': 20.0
        },
        'escola': {
            'id': str(escola.id) if escola else '',
            'nome': getattr(escola, 'nome', '') or 'Escola Secundária de Massinga',
            'provincia': (getattr(escola, 'provincia', '') or 'Inhambane'),
            'distrito': (getattr(escola, 'distrito', '') or 'Massinga'),
            'codigo_escola': (getattr(escola, 'codigo_escola', '') or ''),
            'logo': getattr(escola, 'logo_url', None) or getattr(escola, 'logo_base64', '') or '',
            'usar_emblema_nacional': getattr(escola, 'usar_emblema_nacional', True) if escola else True,
            'logo_url': getattr(escola, 'logo_url', None) if escola else None,
            'logo_base64': getattr(escola, 'logo_base64', None) if escola else None,
            'modo_uso_logo': getattr(escola, 'modo_uso_logo', 'DOCUMENTOS') if escola else 'DOCUMENTOS',
            'marca_dagua_url': getattr(escola, 'marca_dagua_url', None) if escola else None,
            'marca_dagua_base64': getattr(escola, 'marca_dagua_base64', None) if escola else None,
            'marca_dagua_modo': getattr(escola, 'marca_dagua_modo', 'EMBLEMA_NACIONAL') if escola else 'EMBLEMA_NACIONAL',
        },
        'disciplinas': disciplinas_info,
        'disciplinas_com_exame': [d for d in disciplinas_info if d['tem_exame']],
        'disciplinas_sem_exame': [d for d in disciplinas_info if not d['tem_exame']],
        'alunos': dados_alunos,
        'estatisticas': estatisticas
    }

