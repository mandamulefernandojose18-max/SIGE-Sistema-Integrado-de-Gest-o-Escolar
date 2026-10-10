import re
import unicodedata
from collections import Counter
from apps.disciplinas.models import Disciplina
from apps.professores.models import AlocacaoDocente
from apps.notas.models import Nota

# Nomes oficiais completos das disciplinas (MINEDH - Moçambique)
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

# Matrizes curriculares oficiais do MINEDH por secção/área
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

    # 1. Códigos curriculares nacionais do MINEDH (ex: LP-11CB, FIS-11CD, FRAN-11LG)
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
    rigorosamente conforme o currículo oficial do MINEDH.
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
