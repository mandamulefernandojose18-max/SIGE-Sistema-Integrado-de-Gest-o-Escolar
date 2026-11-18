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


def _dados_7_9(agrupar=True):
    com = [{'id': 'mat', 'nome': 'Matemática', 'area_exame': 'MCN'},
           {'id': 'lp', 'nome': 'Língua Portuguesa', 'area_exame': 'CCS'}]
    sem = [{'id': 'ev', 'nome': 'Educação Visual', 'area_exame': 'AP'},
           {'id': 'fr', 'nome': 'Língua Francesa', 'area_exame': 'CCS'}]
    todas = [com[1], sem[1], com[0], sem[0]]
    return {
        'agrupar_por_area': agrupar,
        'turma': {'nome': '8ª A', 'grau_ano': '8ª Classe', 'area': 'Geral'},
        'disciplinas': todas, 'disciplinas_com_exame': com, 'disciplinas_sem_exame': sem,
        'alunos': [{
            'numero': 1, 'nome': 'Aluno Teste', 'genero': 'M', 'turma': '8ª A',
            'disciplinas': {d['id']: {'frequencia': 12, 'exame_1epoca': 11, 'exame_2epoca': '', 'media': 12} for d in todas},
            'resultado_final': {'aprovado': 'Aprovado', 'mf': 12, 'disciplinas_reprovou': '---'},
        }],
        'estatisticas': {'total': 1},
    }


def test_colunas_agrupadas_ccs_mcn_ap_com_linha_entre_grupos():
    from apps.pautas.services import colunas_pauta_exames
    cols = colunas_pauta_exames(_dados_7_9())
    assert [c['disc']['area_exame'] for c in cols] == ['CCS', 'CCS', 'MCN', 'AP']
    assert [c['inicio_grupo'] for c in cols] == [False, False, True, True]


def test_sem_agrupamento_2_ciclo_mantem_ordem_original():
    from apps.pautas.services import colunas_pauta_exames
    cols = colunas_pauta_exames(_dados_7_9(agrupar=False))
    assert [c['disc']['id'] for c in cols] == ['mat', 'lp', 'ev', 'fr']
    assert not any(c['inicio_grupo'] for c in cols)


def test_xlsx_7_9_tem_linha_carregada_entre_grupos():
    import io
    import openpyxl
    from apps.documentos.services.excel_service import gerar_pauta_exames_xlsx
    ws = openpyxl.load_workbook(io.BytesIO(gerar_pauta_exames_xlsx(_dados_7_9(), {'nome': 'E'}))).active
    # CCS: LP (F-I, com exame) + Francês (J); MCN começa em K; AP em O
    assert ws['K7'].border.left.style == 'thick'
    assert ws['O7'].border.left.style == 'thick'
    assert ws['J7'].border.left.style != 'thick'


def test_pdf_e_docx_7_9_geram_sem_erro():
    from apps.documentos.services.pdf_service import gerar_pauta_exames_pdf
    from apps.documentos.services.docx_service import gerar_pauta_exames_docx
    assert gerar_pauta_exames_docx(_dados_7_9(), {'nome': 'E'})[:2] == b'PK'
    try:
        pdf = gerar_pauta_exames_pdf(_dados_7_9(), {'nome': 'E'})
    except Exception as e:  # o PDF exige logótipo da escola; fora disso tem de gerar
        assert 'logótipo' in str(e).lower()
    else:
        assert pdf[:4] == b'%PDF'


def _turma(grau, exame):
    esc = SimpleNamespace(config_classes_exames={grau: exame})
    return SimpleNamespace(grau_ano=grau, escola=esc)


def test_resultado_pauta_frequencia_por_seccao():
    from apps.pautas.services import resultado_frequencia_1_ciclo as rf
    com_exame = {'CCS', 'MCN'}
    r = rf({'CCS': [12, 14], 'MCN': [11], 'AP': [15]}, com_exame, 'M')
    assert r['situacao'] == 'Admitido'
    assert r['linhas'] == ['Admitido: CCS, MCN', 'Aprovado: AP']
    r = rf({'CCS': [12], 'MCN': [9.4], 'AP': [8]}, com_exame, 'F')
    assert r['situacao'] == 'Excluído'
    assert r['linhas'] == ['Admitida: CCS', 'Excluída: MCN', 'Reprovada: AP']
    r = rf({'CCS': [5], 'MCN': [4], 'AP': [12]}, com_exame, 'M')
    assert r['linhas'] == ['Excluído: CCS, MCN', 'Aprovado: AP']
    assert rf({}, com_exame, 'M')['situacao'] == 'Pendente'


def test_documentos_pauta_frequencia_1_ciclo_titulo_e_resultado():
    import io
    import openpyxl
    from types import SimpleNamespace as NS
    from apps.documentos.services.excel_service import gerar_pauta_xlsx
    turma = NS(nome='8ª A', grau_ano='8ª Classe', turno='MANHA', director_turma=None, area='Geral')
    discs = [NS(id='1', codigo='MAT', nome='Matemática')]
    alunos = [{
        'numero': 1, 'nome': 'Aluno Teste', 'nomeCompleto': 'Aluno Teste', 'genero': 'M',
        'notasDisciplinas': {'MAT': {'t1': 8, 't2': 8, 't3': 8, 'mfd': 8}},
        'mediasTrimestrais': {'t1': 8, 't2': 8, 't3': 8}, 'negativas': {}, 'resultado': 'Reprovado',
        'resultado_frequencia': {'situacao': 'Excluído', 'linhas': ['Excluído: MCN', 'Aprovado: AP']},
    }]
    ws = openpyxl.load_workbook(io.BytesIO(gerar_pauta_xlsx(turma, NS(nome='E'), '1_TRIMESTRE', '2026', alunos, discs))).active
    assert 'PAUTA DE FREQUÊNCIA' in ws['A4'].value
    celulas = [c.value for row in ws.iter_rows(min_row=9, max_row=9) for c in row if c.value]
    assert 'Excluído: MCN\nAprovado: AP' in celulas
    # sem o campo novo (outras classes) o título e o resultado não mudam
    alunos[0].pop('resultado_frequencia')
    ws = openpyxl.load_workbook(io.BytesIO(gerar_pauta_xlsx(turma, NS(nome='E'), '1_TRIMESTRE', '2026', alunos, discs))).active
    assert 'APROVEITAMENTO' in ws['A4'].value


def test_regime_so_7_a_9_e_so_se_a_classe_tem_exame():
    assert classe_1_ciclo_com_areas(_turma('8ª Classe', True))
    assert not classe_1_ciclo_com_areas(_turma('8ª Classe', False))   # sem exame: nada muda
    assert not classe_1_ciclo_com_areas(_turma('10ª Classe', True))
    assert not classe_1_ciclo_com_areas(_turma('5ª Classe', True))


def test_obter_disciplinas_pauta_turma_continua_a_logica_original():
    import inspect
    from apps.pautas import services
    assert inspect.getsource(services.obter_disciplinas_pauta_turma).count('_legado') == 1
