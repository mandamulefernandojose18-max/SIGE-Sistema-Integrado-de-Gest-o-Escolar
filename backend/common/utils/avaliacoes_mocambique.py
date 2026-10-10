"""
Regras Oficiais de Avaliação e Aprovação - Sistema Nacional de Educação de Moçambique (MINEDH)
"""
from typing import Dict, Any, List, Optional
import math
import re

def calcular_media_trimestral(dados: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcula a média trimestral conforme normas do MINEDH:
    MAC = média aritmética das avaliações contínuas (testes e trabalhos)
    MT = (2 * MAC + AT) / 3 arredondado para número inteiro (escala 0-20)
    """
    def extrair_nota_campo(chave: str) -> Optional[float]:
        val = dados.get(chave)
        if val is None or val == '' or val == '-':
            return None
        try:
            num = float(val)
            if 0.0 <= num <= 20.0:
                return num
        except (ValueError, TypeError):
            pass
        return None

    t1 = extrair_nota_campo('teste1')
    t2 = extrair_nota_campo('teste2')
    t3 = extrair_nota_campo('teste3')
    t4 = extrair_nota_campo('teste4')
    trab = extrair_nota_campo('trabalho')
    at = extrair_nota_campo('avaliacao_trimestral')

    # Regra Oficial: Só deve formar e mostrar MT quando o aluno tiver no mínimo 2 ACS sendo (1ª, 2ª) e AT
    tem_requisitos_mt = (t1 is not None and t2 is not None and at is not None)

    # Coletar todas as avaliações contínuas válidas para a MAC.
    # Se houver avaliações maiores que 0, campos com default 0 não lançados explicitamente (ex: trabalho=0, teste4=0)
    # não devem diluir a média a menos que sejam os únicos valores existentes.
    todas_acs: List[float] = [n for n in [t1, t2, t3, t4, trab] if n is not None]
    acs_positivas: List[float] = [n for n in todas_acs if n > 0]
    
    # Se existirem notas > 0, consideramos t1, t2 (mesmo se zero se foram lançados) e apenas os opcionais > 0
    if acs_positivas:
        acs_validas: List[float] = []
        if t1 is not None: acs_validas.append(t1)
        if t2 is not None: acs_validas.append(t2)
        for opc in [t3, t4, trab]:
            if opc is not None and opc > 0:
                acs_validas.append(opc)
    else:
        acs_validas = todas_acs

    mac = 0.0
    if acs_validas:
        mac = round(sum(acs_validas) / len(acs_validas), 1)

    if not tem_requisitos_mt:
        return {
            'mediaContinua': mac,
            'mediaFinal': 0,
            'mt': None,
            'mtValida': False,
            'resultado': 'Pendente' if (acs_validas or at is not None) else '',
            'comportamento': '',
            'cor': 'preto'
        }

    media_final = int(round((2 * mac + at) / 3))
    # Limitar escala de 0 a 20
    media_final = max(0, min(20, media_final))

    aprovado = media_final >= 9.5
    resultado = 'Aprovado' if aprovado else 'Reprovado'
    cor = 'preto' if aprovado else 'vermelho'

    if media_final >= 18.5:
        comportamento = 'E'   # Excelente
    elif media_final >= 16.5:
        comportamento = 'MB'  # Muito Bom
    elif media_final >= 13.5:
        comportamento = 'B'   # Bom
    elif media_final >= 9.5:
        comportamento = 'S'   # Suficiente
    else:
        comportamento = 'NS'  # Não Suficiente

    return {
        'mediaContinua': mac,
        'mediaFinal': media_final,
        'mt': media_final,
        'mtValida': True,
        'resultado': resultado,
        'comportamento': comportamento,
        'cor': cor
    }

def avaliar_aprovacao_pauta(
    notas_disciplinas: List[Dict[str, Any]],
    grau_ano: Optional[str] = None
) -> Dict[str, Any]:
    """
    Critério Oficial de Aprovação na Pauta Anual do Aluno (MINEDH):
    - Excepto a 12ª classe: O aluno SÓ APROVA se tiver em TODAS as disciplinas notas positivas (zero negativas).
    - Na 12ª classe: O aluno aprova se tiver Média geral >= 9.5 valores, no máximo 2 negativas e nenhuma negativa < 8.
    """
    grau_normalizado = (grau_ano or '').lower()
    is_12a_classe = bool(re.search(r'(^|[^\d])12([ªaº\.\s]|$)', grau_normalizado))
    is_classe_exame = bool(re.search(r'(^|[^\d])(9|12)([ªaº\.\s]|$)', grau_normalizado))

    notas_validas = []
    for item in (notas_disciplinas or []):
        val = item.get('notaFinal') if item.get('notaFinal') is not None else item.get('mediaFinal')
        if val is not None and val != '-' and val != '---':
            try:
                num = float(val)
                notas_validas.append((item.get('disciplina') or '', num))
            except (ValueError, TypeError):
                pass

    if not notas_validas:
        return {
            'aprovado': False,
            'resultado': 'Pendente',
            'siglaResultado': '-',
            'mediaGeral': '-',
            'totalNegativas': 0,
            'temNotaInferiorA8': False,
            'is12aClasse': is_12a_classe,
            'isClasseExame': is_classe_exame,
            'motivo': 'Sem notas lançadas na caderneta'
        }

    soma = sum(n[1] for n in notas_validas)
    total_negativas = sum(1 for n in notas_validas if n[1] < 9.5)
    tem_nota_inferior_a_8 = any(n[1] < 8.0 for n in notas_validas)
    media_geral = int(round(soma / len(notas_validas)))

    # 1. Regra Geral (Excepto 12ª classe): 100% de positivas
    if not is_12a_classe:
        if total_negativas > 0:
            return {
                'aprovado': False,
                'resultado': 'Reprovado',
                'siglaResultado': 'R',
                'mediaGeral': media_geral,
                'totalNegativas': total_negativas,
                'temNotaInferiorA8': tem_nota_inferior_a_8,
                'is12aClasse': False,
                'isClasseExame': is_classe_exame,
                'motivo': f'Reprovado: Excepto na 12ª classe, o aluno só aprova se tiver 100% de positivas (0 negativas). Possui {total_negativas} negativa(s).'
            }

        if media_geral < 9.5:
            return {
                'aprovado': False,
                'resultado': 'Reprovado',
                'siglaResultado': 'R',
                'mediaGeral': media_geral,
                'totalNegativas': total_negativas,
                'temNotaInferiorA8': tem_nota_inferior_a_8,
                'is12aClasse': False,
                'isClasseExame': is_classe_exame,
                'motivo': f'Reprovado: Média geral {media_geral} inferior a 9.5 valores.'
            }

        return {
            'aprovado': True,
            'resultado': 'Aprovado',
            'siglaResultado': 'A',
            'mediaGeral': media_geral,
            'totalNegativas': 0,
            'temNotaInferiorA8': False,
            'is12aClasse': False,
            'isClasseExame': is_classe_exame,
            'motivo': 'Aprovado com 100% de positivas (0 negativas).'
        }

    # 2. Regra da 12ª Classe: Média >= 9.5, máx 2 negativas e NENHUMA < 8
    if tem_nota_inferior_a_8:
        return {
            'aprovado': False,
            'resultado': 'Reprovado',
            'siglaResultado': 'R',
            'mediaGeral': media_geral,
            'totalNegativas': total_negativas,
            'temNotaInferiorA8': True,
            'is12aClasse': True,
            'isClasseExame': True,
            'motivo': 'Reprovado na 12ª classe: possui nota inferior a 8 valores.'
        }

    if total_negativas > 2:
        return {
            'aprovado': False,
            'resultado': 'Reprovado',
            'siglaResultado': 'R',
            'mediaGeral': media_geral,
            'totalNegativas': total_negativas,
            'temNotaInferiorA8': False,
            'is12aClasse': True,
            'isClasseExame': True,
            'motivo': f'Reprovado na 12ª classe: possui {total_negativas} negativas (máximo permitido é 2).'
        }

    if media_geral < 9.5:
        return {
            'aprovado': False,
            'resultado': 'Reprovado',
            'siglaResultado': 'R',
            'mediaGeral': media_geral,
            'totalNegativas': total_negativas,
            'temNotaInferiorA8': False,
            'is12aClasse': True,
            'isClasseExame': True,
            'motivo': f'Reprovado na 12ª classe: média geral {media_geral} inferior a 9.5 valores.'
        }

    return {
        'aprovado': True,
        'resultado': 'Aprovado',
        'siglaResultado': 'A',
        'mediaGeral': media_geral,
        'totalNegativas': total_negativas,
        'temNotaInferiorA8': False,
        'is12aClasse': True,
        'isClasseExame': True,
        'motivo': f'Aprovado na 12ª classe com {total_negativas} negativa(s) tolerada(s) (>= 8 valores) e média {media_geral}.' if total_negativas > 0 else f'Aprovado na 12ª classe com aproveitamento pleno e média {media_geral}.'
    }

# ==================== PLANO CURRICULAR OFICIAL MINEDH ====================

PLANO_CURRICULAR_NACIONAL_MINEDH: Dict[str, Any] = {
    '7ª Classe': [
        ('Língua Portuguesa', 'LP-07', '5h'),
        ('Matemática', 'MAT-07', '5h'),
        ('Língua Inglesa', 'ING-07', '3h'),
        ('Física', 'FIS-07', '3h'),
        ('Química', 'QUI-07', '3h'),
        ('Biologia', 'BIO-07', '3h'),
        ('Geografia', 'GEO-07', '3h'),
        ('História', 'HIS-07', '3h'),
        ('Educação Visual', 'EV-07', '2h'),
        ('Educação Física', 'EF-07', '2h'),
        ('Agropecuária', 'AGRO-07', '2h'),
    ],
    '8ª Classe': [
        ('Língua Portuguesa', 'LP-08', '5h'),
        ('Matemática', 'MAT-08', '5h'),
        ('Língua Inglesa', 'ING-08', '3h'),
        ('Física', 'FIS-08', '3h'),
        ('Química', 'QUI-08', '3h'),
        ('Biologia', 'BIO-08', '3h'),
        ('Geografia', 'GEO-08', '3h'),
        ('História', 'HIS-08', '3h'),
        ('Educação Visual', 'EV-08', '2h'),
        ('Educação Física', 'EF-08', '2h'),
        ('Agropecuária', 'AGRO-08', '2h'),
    ],
    '9ª Classe': [
        ('Língua Portuguesa', 'LP-09', '5h'),
        ('Matemática', 'MAT-09', '5h'),
        ('Língua Inglesa', 'ING-09', '3h'),
        ('Física', 'FIS-09', '3h'),
        ('Química', 'QUI-09', '3h'),
        ('Biologia', 'BIO-09', '3h'),
        ('Geografia', 'GEO-09', '3h'),
        ('História', 'HIS-09', '3h'),
        ('Educação Visual', 'EV-09', '2h'),
        ('Educação Física', 'EF-09', '2h'),
        ('Agropecuária', 'AGRO-09', '2h'),
    ],
    '10ª Classe': [
        ('Língua Portuguesa', 'LP-10', '5h'),
        ('Matemática', 'MAT-10', '5h'),
        ('Língua Inglesa', 'ING-10', '3h'),
        ('Física', 'FIS-10', '3h'),
        ('Química', 'QUI-10', '3h'),
        ('Biologia', 'BIO-10', '3h'),
        ('Geografia', 'GEO-10', '3h'),
        ('História', 'HIS-10', '3h'),
        ('Filosofia', 'FILO-10', '2h'),
        ('Educação Física', 'EF-10', '2h'),
        ('Agropecuária', 'AGRO-10', '2h'),
        ("TIC's", 'TIC-10', '2h'),
    ],
    '11ª Classe': {
        'Ciências com Biologia': [
            ('Língua Portuguesa', 'LP-11CB', '4h'),
            ('Língua Inglesa', 'ING-11CB', '3h'),
            ('Filosofia', 'FILO-11CB', '3h'),
            ('Educação Física', 'EF-11CB', '2h'),
            ('Matemática', 'MAT-11CB', '5h'),
            ('Biologia', 'BIO-11CB', '5h'),
            ('Química', 'QUI-11CB', '4h'),
            ('Física', 'FIS-11CB', '4h'),
            ("TIC's", 'TIC-11CB', '2h'),
        ],
        'Ciências com Desenho': [
            ('Língua Portuguesa', 'LP-11CD', '4h'),
            ('Língua Inglesa', 'ING-11CD', '3h'),
            ('Filosofia', 'FILO-11CD', '3h'),
            ('Educação Física', 'EF-11CD', '2h'),
            ('Matemática', 'MAT-11CD', '5h'),
            ('Física', 'FIS-11CD', '5h'),
            ('Desenho e Geometria Descritiva', 'DGD-11CD', '5h'),
            ('Química', 'QUI-11CD', '3h'),
            ("TIC's", 'TIC-11CD', '2h'),
        ],
        'Ciências com Geografia': [
            ('Língua Portuguesa', 'LP-11CG', '4h'),
            ('Língua Inglesa', 'ING-11CG', '4h'),
            ('Filosofia', 'FILO-11CG', '3h'),
            ('Educação Física', 'EF-11CG', '2h'),
            ('Matemática', 'MAT-11CG', '5h'),
            ('Geografia', 'GEO-11CG', '5h'),
            ('Física', 'FIS-11CG', '4h'),
            ('Química', 'QUI-11CG', '3h'),
            ('Agropecuária', 'AGRO-11CG', '3h'),
            ("TIC's", 'TIC-11CG', '2h'),
        ],
        'Letras com Geografia': [
            ('Língua Portuguesa', 'LP-11LG', '5h'),
            ('Língua Inglesa', 'ING-11LG', '4h'),
            ('Língua Francesa', 'FRAN-11LG', '3h'),
            ('Filosofia', 'FILO-11LG', '3h'),
            ('História', 'HIS-11LG', '4h'),
            ('Geografia', 'GEO-11LG', '5h'),
            ('Matemática Aplicada', 'MATA-11LG', '3h'),
            ('Educação Física', 'EF-11LG', '2h'),
            ("TIC's", 'TIC-11LG', '2h'),
        ],
        'Letras com História': [
            ('Língua Portuguesa', 'LP-11LH', '5h'),
            ('Língua Inglesa', 'ING-11LH', '4h'),
            ('Língua Francesa', 'FRAN-11LH', '3h'),
            ('Filosofia', 'FILO-11LH', '3h'),
            ('História', 'HIS-11LH', '5h'),
            ('Geografia', 'GEO-11LH', '4h'),
            ('Introdução à Literatura', 'LIT-11LH', '3h'),
            ('Educação Física', 'EF-11LH', '2h'),
            ("TIC's", 'TIC-11LH', '2h'),
        ],
        '_default': [
            ('Língua Portuguesa', 'LP-11', '4h'),
            ('Língua Inglesa', 'ING-11', '3h'),
            ('Filosofia', 'FILO-11', '3h'),
            ('Educação Física', 'EF-11', '2h'),
            ('Matemática', 'MAT-11', '5h'),
            ('Biologia', 'BIO-11', '4h'),
            ('Física', 'FIS-11', '4h'),
            ('Química', 'QUI-11', '3h'),
            ('Geografia', 'GEO-11', '4h'),
            ('História', 'HIS-11', '4h'),
        ]
    },
    '12ª Classe': {
        'Ciências com Biologia': [
            ('Língua Portuguesa', 'LP-12CB', '4h'),
            ('Língua Inglesa', 'ING-12CB', '3h'),
            ('Filosofia', 'FILO-12CB', '3h'),
            ('Educação Física', 'EF-12CB', '2h'),
            ('Matemática', 'MAT-12CB', '5h'),
            ('Biologia', 'BIO-12CB', '5h'),
            ('Química', 'QUI-12CB', '4h'),
            ('Física', 'FIS-12CB', '4h'),
            ("TIC's", 'TIC-12CB', '2h'),
        ],
        'Ciências com Desenho': [
            ('Língua Portuguesa', 'LP-12CD', '4h'),
            ('Língua Inglesa', 'ING-12CD', '3h'),
            ('Filosofia', 'FILO-12CD', '3h'),
            ('Educação Física', 'EF-12CD', '2h'),
            ('Matemática', 'MAT-12CD', '5h'),
            ('Física', 'FIS-12CD', '5h'),
            ('Desenho e Geometria Descritiva', 'DGD-12CD', '5h'),
            ('Química', 'QUI-12CD', '3h'),
            ("TIC's", 'TIC-12CD', '2h'),
        ],
        'Ciências com Geografia': [
            ('Língua Portuguesa', 'LP-12CG', '4h'),
            ('Língua Inglesa', 'ING-12CG', '4h'),
            ('Filosofia', 'FILO-12CG', '3h'),
            ('Educação Física', 'EF-12CG', '2h'),
            ('Matemática', 'MAT-12CG', '5h'),
            ('Geografia', 'GEO-12CG', '5h'),
            ('Física', 'FIS-12CG', '4h'),
            ('Química', 'QUI-12CG', '3h'),
            ('Agropecuária', 'AGRO-12CG', '3h'),
            ("TIC's", 'TIC-12CG', '2h'),
        ],
        'Letras com Geografia': [
            ('Língua Portuguesa', 'LP-12LG', '5h'),
            ('Língua Inglesa', 'ING-12LG', '4h'),
            ('Língua Francesa', 'FRAN-12LG', '3h'),
            ('Filosofia', 'FILO-12LG', '3h'),
            ('História', 'HIS-12LG', '4h'),
            ('Geografia', 'GEO-12LG', '5h'),
            ('Matemática Aplicada', 'MATA-12LG', '3h'),
            ('Educação Física', 'EF-12LG', '2h'),
            ("TIC's", 'TIC-12LG', '2h'),
        ],
        'Letras com História': [
            ('Língua Portuguesa', 'LP-12LH', '5h'),
            ('Língua Inglesa', 'ING-12LH', '4h'),
            ('Língua Francesa', 'FRAN-12LH', '3h'),
            ('Filosofia', 'FILO-12LH', '3h'),
            ('História', 'HIS-12LH', '5h'),
            ('Geografia', 'GEO-12LH', '4h'),
            ('Introdução à Literatura', 'LIT-12LH', '3h'),
            ('Educação Física', 'EF-12LH', '2h'),
            ("TIC's", 'TIC-12LH', '2h'),
        ],
        '_default': [
            ('Língua Portuguesa', 'LP-12', '4h'),
            ('Língua Inglesa', 'ING-12', '3h'),
            ('Filosofia', 'FILO-12', '3h'),
            ('Educação Física', 'EF-12', '2h'),
            ('Matemática', 'MAT-12', '5h'),
            ('Biologia', 'BIO-12', '4h'),
            ('Física', 'FIS-12', '4h'),
            ('Química', 'QUI-12', '3h'),
            ('Geografia', 'GEO-12', '4h'),
            ('História', 'HIS-12', '4h'),
        ]
    }
}

def obter_disciplinas_plano_curricular(aluno: Any, escola: Any = None) -> List[Dict[str, Any]]:
    """
    Retorna estritamente as disciplinas do plano curricular oficial correspondente à classe e área/secção que o aluno estuda.
    Retorna: [{'numero': 1, 'codigo': 'LP-10', 'nome': 'Língua Portuguesa', 'carga': '5h'}, ...]
    """
    turma_obj = getattr(aluno, 'turma', None)

    classe = getattr(aluno, 'classe', None) or ''
    if not classe and turma_obj:
        classe = getattr(turma_obj, 'grau_ano', '') or ''
    classe = str(classe or '10ª Classe').strip()

    # Normalizar classe (ex: '10' -> '10ª Classe')
    m_cls = re.search(r'(\d+)', classe)
    num_classe = m_cls.group(1) if m_cls else '10'
    chave_classe = f"{num_classe}ª Classe"

    # Determinar a área/secção do aluno com prioridade para área específica
    def _is_especifica(val: Any) -> bool:
        if not val:
            return False
        v = str(val).strip().lower()
        return v not in ('', 'geral', 'ensino geral', 'tronco comum', 'none', 'null', 'ciências e letras')

    area_aluno = getattr(aluno, 'area', None) or ''
    area_turma = getattr(turma_obj, 'area', None) or '' if turma_obj else ''
    if _is_especifica(area_aluno):
        area = str(area_aluno).strip()
    elif _is_especifica(area_turma):
        area = str(area_turma).strip()
    else:
        area = str(area_aluno or area_turma or 'Geral').strip()

    # Se for 11ª ou 12ª classe e a área ainda estiver genérica, inferir pela turma ou pelas notas do aluno
    if num_classe in ('11', '12') and not _is_especifica(area):
        try:
            from apps.pautas.services import categorizar_area, CURRICULO_REGRAS_AREAS
            if turma_obj:
                _, sub_t = categorizar_area(area_turma, getattr(turma_obj, 'nome', ''))
                if sub_t in CURRICULO_REGRAS_AREAS and sub_t != 'GERAL':
                    area = CURRICULO_REGRAS_AREAS[sub_t]['nome_oficial']
        except Exception:
            pass
        if not _is_especifica(area):
            area = 'Ciências com Biologia'

    # Obter o plano curricular oficial do MINEDH para esta Classe e Área/Secção
    plano_bloco = PLANO_CURRICULAR_NACIONAL_MINEDH.get(chave_classe, PLANO_CURRICULAR_NACIONAL_MINEDH.get('10ª Classe', []))
    lista_padrao = []

    if isinstance(plano_bloco, dict):
        sub_lista = None
        area_low = area.lower()
        # 1. Correspondência exata ou inclusão direta
        for k_area, dis_items in plano_bloco.items():
            if k_area != '_default' and (k_area.lower() in area_low or area_low in k_area.lower()):
                sub_lista = dis_items
                break
        # 2. Correspondência por combinação de ramo + especialidade
        if not sub_lista:
            if 'letr' in area_low and ('hist' in area_low or 'lh' in area_low):
                sub_lista = plano_bloco.get('Letras com História')
            elif 'letr' in area_low:
                sub_lista = plano_bloco.get('Letras com Geografia')
            elif 'desenh' in area_low or 'dgd' in area_low or 'cd' in area_low:
                sub_lista = plano_bloco.get('Ciências com Desenho')
            elif 'geo' in area_low or 'cg' in area_low:
                sub_lista = plano_bloco.get('Ciências com Geografia')
            elif 'bio' in area_low or 'cb' in area_low or 'cienc' in area_low or 'ciênc' in area_low:
                sub_lista = plano_bloco.get('Ciências com Biologia')
        if not sub_lista:
            sub_lista = plano_bloco.get('Ciências com Biologia') or plano_bloco.get('_default', [])
        lista_padrao = sub_lista
    elif isinstance(plano_bloco, list):
        lista_padrao = plano_bloco

    # Mapear disciplinas cadastradas na escola (para preservar códigos/cargas customizadas que pertençam estritamente ao plano da área)
    esc = escola or getattr(aluno, 'escola', None)
    db_por_materia = {}
    if esc and hasattr(esc, 'id'):
        try:
            from apps.disciplinas.models import Disciplina
            from apps.pautas.services import identificar_materia_canonica
            qs = Disciplina.objects.filter(escola=esc, classe__icontains=num_classe)
            for d in qs:
                mat_key = identificar_materia_canonica(d)
                if mat_key and mat_key not in db_por_materia:
                    db_por_materia[mat_key] = d
        except Exception:
            pass

    lista_final: List[Dict[str, Any]] = []
    nomes_vistos = set()
    try:
        from apps.pautas.services import identificar_materia_canonica as _id_mat, MATERIA_NOMES_OFICIAIS
    except Exception:
        _id_mat = None
        MATERIA_NOMES_OFICIAIS = {}

    for item in lista_padrao:
        nome_d, cod_d, carga_d = item
        # Nome oficial completo (ex: TIC's -> Tecnologias de Informação e Comunicação)
        if nome_d in ("TIC's", "TIC"):
            nome_d = "Tecnologias de Informação e Comunicação"
        elif nome_d == "Filosofia":
            nome_d = "Introdução à Filosofia"

        if nome_d.lower() not in nomes_vistos:
            nomes_vistos.add(nome_d.lower())
            lista_final.append({
                'numero': len(lista_final) + 1,
                'codigo': cod_d,
                'nome': nome_d,
                'disciplina': nome_d,
                'carga': carga_d,
                'carga_horaria': carga_d
            })

    return lista_final


