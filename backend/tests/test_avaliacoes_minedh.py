from common.utils.geografia_mocambique import (
    PROVINCIAS_MOCAMBIQUE,
    DISTRITOS_POR_PROVINCIA,
    CARREIRAS_DOCENTES,
    ANOTACOES_STATUS
)
from common.utils.avaliacoes_mocambique import (
    calcular_media_trimestral,
    avaliar_aprovacao_pauta
)

def test_geografia_mocambique():
    assert len(PROVINCIAS_MOCAMBIQUE) == 11
    assert 'Maputo' in DISTRITOS_POR_PROVINCIA or 'Província de Maputo' in DISTRITOS_POR_PROVINCIA
    assert 'DN1' in CARREIRAS_DOCENTES
    assert 'D' in ANOTACOES_STATUS
    assert 'PPF' in ANOTACOES_STATUS

def test_calculo_media_trimestral():
    # Teste 1: 14, Teste 2: 16, Trabalho: 15, AT: 17
    # MAC = (14 + 16 + 15) / 3 = 15.0
    # MT = (2 * 15 + 17) / 3 = 47 / 3 = 15.666... -> round(16)
    res = calcular_media_trimestral({
        'teste1': 14,
        'teste2': 16,
        'trabalho': 15,
        'avaliacao_trimestral': 17
    })
    assert res['mediaContinua'] == 15.0
    assert res['mediaFinal'] == 16
    assert res['resultado'] == 'Aprovado'
    assert res['comportamento'] == 'B'
    assert res['cor'] == 'preto'

def test_reprovacao_media_negativa():
    res = calcular_media_trimestral({
        'teste1': 8,
        'teste2': 7,
        'trabalho': 9,
        'avaliacao_trimestral': 8
    })
    assert res['mediaFinal'] == 8
    assert res['resultado'] == 'Reprovado'
    assert res['cor'] == 'vermelho'
    assert res['comportamento'] == 'NS'

def test_sem_notas_nao_preenche_comportamento():
    res = calcular_media_trimestral({})
    assert res['comportamento'] == ''
    assert res['mediaFinal'] == 0
    assert res['mt'] is None
    assert res['mtValida'] is False
    assert res['resultado'] == ''

def test_mt_so_mostra_com_minimo_2_acs_e_at():
    # Apenas 1ª ACS -> MT deve estar vazia (None / False)
    res1 = calcular_media_trimestral({'teste1': 14})
    assert res1['mt'] is None
    assert res1['mtValida'] is False
    assert res1['comportamento'] == ''

    # 1ª ACS e 2ª ACS sem AT -> MT deve estar vazia
    res2 = calcular_media_trimestral({'teste1': 14, 'teste2': 16})
    assert res2['mt'] is None
    assert res2['mtValida'] is False
    assert res2['comportamento'] == ''

    # 1ª ACS e AT sem 2ª ACS -> MT deve estar vazia
    res3 = calcular_media_trimestral({'teste1': 14, 'avaliacao_trimestral': 15})
    assert res3['mt'] is None
    assert res3['mtValida'] is False
    assert res3['comportamento'] == ''

    # 1ª ACS, 2ª ACS e AT -> MT calculada com sucesso
    res4 = calcular_media_trimestral({'teste1': 14, 'teste2': 16, 'avaliacao_trimestral': 15})
    assert res4['mtValida'] is True
    assert res4['mt'] == 15
    assert res4['comportamento'] == 'B'

def test_regra_geral_aprovacao_pauta_requer_zero_negativas():
    # 10ª Classe com 1 negativa -> REPROVADO
    notas = [
        {'disciplina': 'Matemática', 'notaFinal': 14},
        {'disciplina': 'Português', 'notaFinal': 12},
        {'disciplina': 'Física', 'notaFinal': 8}, # Negativa
    ]
    res = avaliar_aprovacao_pauta(notas, grau_ano='10ª Classe')
    assert res['aprovado'] is False
    assert res['resultado'] == 'Reprovado'
    assert res['totalNegativas'] == 1

def test_regra_12a_classe_permite_ate_duas_negativas_maior_ou_igual_a_8():
    # 12ª Classe com 2 negativas (notas 9 e 8), média geral >= 9.5 -> APROVADO
    notas = [
        {'disciplina': 'Matemática', 'notaFinal': 16},
        {'disciplina': 'Português', 'notaFinal': 14},
        {'disciplina': 'Física', 'notaFinal': 9},  # Negativa 1 >= 8
        {'disciplina': 'Química', 'notaFinal': 8}, # Negativa 2 >= 8
        {'disciplina': 'Biologia', 'notaFinal': 15},
    ]
    res = avaliar_aprovacao_pauta(notas, grau_ano='12ª Classe')
    assert res['aprovado'] is True
    assert res['resultado'] == 'Aprovado'
    assert res['totalNegativas'] == 2

def test_regra_12a_classe_reprova_se_tiver_nota_menor_que_8():
    notas = [
        {'disciplina': 'Matemática', 'notaFinal': 18},
        {'disciplina': 'Português', 'notaFinal': 16},
        {'disciplina': 'Física', 'notaFinal': 7}, # Reprova imediatamente
    ]
    res = avaliar_aprovacao_pauta(notas, grau_ano='12ª Classe')
    assert res['aprovado'] is False
    assert res['resultado'] == 'Reprovado'
    assert res['temNotaInferiorA8'] is True
