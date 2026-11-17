from types import SimpleNamespace

from apps.pautas.services import (
    area_exame_da_disciplina, areas_reprovadas, classe_1_ciclo_com_areas,
)


def _d(nome, codigo=''):
    return SimpleNamespace(nome=nome, codigo=codigo)


def test_areas_das_disciplinas():
    assert area_exame_da_disciplina(_d('Português')) == 'CCS'
    assert area_exame_da_disciplina(_d('Geografia')) == 'CCS'
    assert area_exame_da_disciplina(_d('Química')) == 'MCN'
    assert area_exame_da_disciplina(_d('Educação Visual')) == 'AP'
    assert area_exame_da_disciplina(_d('Noções de Empreendedorismo')) == 'AP'
    assert area_exame_da_disciplina(_d('Educação Física')) == 'AP'


def test_retencao_por_area():
    assert areas_reprovadas({'CCS': [12, 14], 'MCN': [9.4]}) == ['MCN']
    assert areas_reprovadas({'CCS': [9], 'MCN': [15], 'AP': [8]}) == ['CCS', 'AP']
    assert areas_reprovadas({'CCS': [9.5], 'MCN': [10], 'AP': [20]}) == []
    assert areas_reprovadas({'CCS': [5], 'MCN': [4], 'AP': [3]}) == ['CCS', 'MCN', 'AP']


def test_regime_so_7_a_9():
    assert classe_1_ciclo_com_areas(SimpleNamespace(grau_ano='8ª Classe'))
    assert not classe_1_ciclo_com_areas(SimpleNamespace(grau_ano='10ª Classe'))
    assert not classe_1_ciclo_com_areas(SimpleNamespace(grau_ano='5ª Classe'))
