import io

import openpyxl
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.alunos.models import Aluno
from apps.disciplinas.models import Disciplina
from apps.documentos.services import folha_resposta_service as fr
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma

URL = '/api/v1/documentos/folha-resposta/'


@pytest.fixture
def cenario(db):
    plano = Plano.objects.create(nome='PLANO_FR', preco=2000, duracao_dias=30)
    a = Escola.objects.create(nome='Escola A', nif_cnpj='NIF_FRA', email='fra@sige.mz', status='ATIVA',
                              plano=plano, codigo_escola='03029924', provincia='Inhambane', distrito='Massinga')
    b = Escola.objects.create(nome='Escola B', nif_cnpj='NIF_FRB', email='frb@sige.mz', status='ATIVA', plano=plano)
    Usuario.objects.create_user(email='admin.fra@sige.mz', password='PassFr123!', role='ADMIN_ESCOLA', escola=a)
    Usuario.objects.create_user(email='aluno.fra@sige.mz', password='PassFr123!', role='ALUNO', escola=a)
    t = Turma.objects.create(escola=a, nome='Turma 1', grau_ano='10ª Classe', ano_letivo=a.ano_letivo_ativo)
    Disciplina.objects.create(escola=a, nome='Matemática', codigo='MAT', classe='10ª Classe', ano_letivo=a.ano_letivo_ativo)
    for i, nome in enumerate(('Ana', 'Bruno', 'Carla')):
        Aluno.objects.create(escola=a, turma=t, matricula=f'MAT_FR_{i}', nome=nome, apelido='Silva',
                             data_nascimento='2009-01-01', genero='F')
    tb = Turma.objects.create(escola=b, nome='Turma B', grau_ano='10ª Classe')
    ab = Aluno.objects.create(escola=b, turma=tb, matricula='MAT_FR_B', nome='Alheio',
                              data_nascimento='2009-01-01', genero='M')
    return a, t, ab


def _cliente(email):
    c = APIClient()
    r = c.post('/api/v1/auth/login/', {'email': email, 'password': 'PassFr123!'}, format='json')
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['token']}")
    return c


def _corpo(**extra):
    base = {'config': {'tipo_avaliacao': 'ACS1', 'disciplina': 'Matemática', 'n_perguntas': 30, 'n_alternativas': 4}}
    base.update(extra)
    return base


def test_config_cotacao_por_defeito_soma_20():
    cfg = fr.normalizar_config({'disciplina': 'X', 'n_perguntas': 40, 'n_alternativas': 4})
    assert cfg['cotacao_total'] == 20
    assert fr.formatar_valor(0.5) == '0,5'


def test_config_seccoes_e_gabarito():
    cfg = fr.normalizar_config({
        'disciplina': 'X', 'n_perguntas': 4, 'n_alternativas': 4,
        'seccoes': [{'ate': 2, 'cotacao': 2}, {'ate': 4, 'cotacao': 3}], 'gabarito': 'A,B,C,D',
    })
    assert cfg['cotacao_total'] == 10 and cfg['incluir_chave']
    with pytest.raises(fr.ConfigFolhaInvalida):
        fr.normalizar_config({'disciplina': 'X', 'n_perguntas': 4, 'gabarito': 'ABE'})
    with pytest.raises(fr.ConfigFolhaInvalida):
        fr.normalizar_config({'disciplina': 'X', 'n_perguntas': 500})


@pytest.mark.parametrize('n', [5, 40, 75, 100])
def test_layout_cobre_todas_as_perguntas(n):
    paginas = fr.paginas_grelha(n)
    assert len(paginas) == 1  # cabe sempre numa só página
    assert sum(fim - ini for ini, fim, *_ in paginas) == n
    for ini, fim, cols, linhas, _ in paginas:
        assert cols * linhas >= fim - ini


def test_sem_login_negado(cenario):
    assert APIClient().post(URL + 'gerar/', _corpo(escopo='branco', copias=1), format='json').status_code in (401, 403)


def test_aluno_nao_emite(cenario):
    c = _cliente('aluno.fra@sige.mz')
    assert c.get(URL + 'contexto/').status_code == 403


def test_contexto_tem_classes_e_disciplinas(cenario):
    r = _cliente('admin.fra@sige.mz').get(URL + 'contexto/')
    assert r.status_code == 200
    assert r.data['classes'][0]['total_alunos'] == 3
    assert {'nome': 'Matemática', 'area': 'Geral'} in r.data['disciplinas_por_classe']['10ª Classe']
    assert r.data['escola']['codigo'] == Escola.objects.get(email='fra@sige.mz').codigo_escola


def test_pdf_turma_gera_uma_folha_por_aluno(cenario):
    _, turma, _ = cenario
    r = _cliente('admin.fra@sige.mz').post(URL + 'gerar/', _corpo(escopo='turma', turma_id=str(turma.id)), format='json')
    assert r.status_code == 200, r.content[:200]
    assert r['X-Total-Folhas'] == '3'
    import zipfile
    z = zipfile.ZipFile(io.BytesIO(r.content))   # turma/classe: ZIP com as folhas + lista de quem teve folha (PDF e Excel)
    nomes = z.namelist()
    assert any(n.endswith('_LISTA_ALUNOS_gerados.pdf') for n in nomes) and any(n.endswith('_LISTA_ALUNOS_gerados.xlsx') for n in nomes)
    folhas = z.read([n for n in nomes if n.endswith('.pdf') and 'LISTA' not in n][0])
    assert folhas[:4] == b'%PDF'
    import pymupdf as fitz
    doc = fitz.open(stream=folhas, filetype='pdf')
    assert doc.page_count >= 3
    assert len(doc.get_toc()) == 3 and 'Silva' in doc.get_toc()[0][1]   # marcador com o nome de cada aluno
    lista = fitz.open(stream=z.read([n for n in nomes if n.endswith('.pdf') and 'LISTA' in n][0]), filetype='pdf')
    texto = ''.join(p.get_text() for p in lista)
    assert 'Ana' in texto and 'Bruno' in texto and 'Carla' in texto and 'Total de folhas/provas geradas: 3' in texto
    wb = openpyxl.load_workbook(io.BytesIO(z.read([n for n in nomes if n.endswith('.xlsx') and 'LISTA' in n][0])))
    assert wb.sheetnames == ['Alunos'] and wb['Alunos']['C10'].value == Aluno.objects.get(nome='Ana', turma=turma).matricula


def test_regra_automatica_e_exclusoes_na_folha_personalizada(cenario):
    a, turma, _ = cenario
    from apps.notas.models import Nota
    d = Disciplina.objects.get(escola=a, nome='Matemática')
    ana = Aluno.objects.get(nome='Ana', turma=turma)
    bruno = Aluno.objects.get(nome='Bruno', turma=turma)
    Nota.objects.create(escola=a, aluno=ana, disciplina=d, turma=turma, periodo='1_TRIMESTRE', faltas=14)
    Nota.objects.create(escola=a, aluno=bruno, disciplina=d, turma=turma, periodo='1_TRIMESTRE', anotacao='PPF')
    c = _cliente('admin.fra@sige.mz')
    r = c.post(URL + 'regra/', {'verificar_sempre': True, 'motivos': ['faltas'], 'faltas_minimo': 0}, format='json')
    assert r.status_code == 400   # faltas sem total definido: recusado
    r = c.post(URL + 'regra/', {'verificar_sempre': True, 'motivos': ['faltas', 'ppf', 'pdf', 'transferida', 'obito'], 'faltas_minimo': 10}, format='json')
    assert r.status_code == 200 and r.data['faltas_minimo'] == 10
    assert c.get(URL + 'contexto/').data['regra_exclusao']['verificar_sempre'] is True
    r = c.post(URL + 'gerar/', {**_corpo(escopo='turma', turma_id=str(turma.id)), 'cor_excluidos': '#a1b2c3'}, format='json')
    assert r.status_code == 200 and r['X-Total-Folhas'] == '1'   # só sobra a Carla
    import zipfile
    z = zipfile.ZipFile(io.BytesIO(r.content))
    import pymupdf as fitz
    lista = fitz.open(stream=z.read([n for n in z.namelist() if n.endswith('.pdf') and 'LISTA' in n][0]), filetype='pdf')
    texto = ''.join(p.get_text() for p in lista)
    assert 'Carla' in texto and 'Faltas: 14' in texto and 'PPF' in texto   # incluída + excluídos com o motivo
    wb = openpyxl.load_workbook(io.BytesIO(z.read([n for n in z.namelist() if n.endswith('.xlsx') and 'LISTA' in n][0])))
    assert wb.sheetnames == ['Alunos']
    ws = wb['Alunos']   # estatística H/M/HM dos dois grupos na mesma lista (as 3 alunas são do sexo feminino)
    assert [ws.cell(row=5, column=k).value for k in (3, 4, 5, 6)] == ['Folha gerada', 0, 1, 1]
    assert [ws.cell(row=6, column=k).value for k in (3, 4, 5, 6)] == ['Excluídos', 0, 2, 2]
    assert [ws.cell(row=7, column=k).value for k in (3, 4, 5, 6)] == ['Total do âmbito', 0, 3, 3]
    assert str(ws.cell(row=10, column=1).fill.start_color.rgb).upper().endswith('A1B2C3')   # excluído (Ana) na cor escolhida
    assert 'Excluído: Faltas: 14' in str(ws.cell(row=10, column=9).value)
    assert not str(ws.cell(row=12, column=1).fill.start_color.rgb).upper().endswith('A1B2C3')   # Carla gerada: sem a cor
    assert 'Estatística' in texto and 'Excluídos' in texto
    # um aluno excluído pela regra não recebe folha individual
    r = c.post(URL + 'gerar/', _corpo(escopo='aluno', aluno_id=str(ana.id)), format='json')
    assert r.status_code == 409


def test_pdf_classe_100_perguntas_com_chave_e_versoes(cenario):
    corpo = _corpo(escopo='classe', classe='10ª Classe')
    corpo['config'].update({'n_perguntas': 100, 'n_alternativas': 5, 'versoes': 'A,B', 'gabaritos': {'A': 'A' * 100, 'B': 'B' * 100}})
    r = _cliente('admin.fra@sige.mz').post(URL + 'gerar/', corpo, format='json')
    assert r.status_code == 200 and r['X-Total-Folhas'] == '3'


def test_xlsx_aluno_tem_grelha_sem_formulas(cenario):
    a, turma, _ = cenario
    aluno = Aluno.objects.filter(turma=turma).first()
    r = _cliente('admin.fra@sige.mz').post(URL + 'gerar/', _corpo(escopo='aluno', aluno_id=str(aluno.id), formato='xlsx'), format='json')
    assert r.status_code == 200, r.content[:200]
    wb = openpyxl.load_workbook(io.BytesIO(r.content))
    ws = wb.worksheets[0]
    texto = ' '.join(str(c.value) for row in ws.iter_rows() for c in row if c.value is not None)
    assert 'Escola A' in texto and aluno.matricula in texto and 'Matemática' in texto and a.codigo_escola in texto
    assert 'INSTRUÇÕES GERAIS' in texto and 'pintando o quadradinho' in texto


def test_xlsx_turma_tem_resumo(cenario):
    _, turma, _ = cenario
    r = _cliente('admin.fra@sige.mz').post(URL + 'gerar/', _corpo(escopo='turma', turma_id=str(turma.id), formato='xlsx'), format='json')
    import zipfile
    z = zipfile.ZipFile(io.BytesIO(r.content))
    principal = [n for n in z.namelist() if n.endswith('.xlsx') and 'LISTA' not in n][0]
    nomes = openpyxl.load_workbook(io.BytesIO(z.read(principal))).sheetnames
    assert 'Resumo' in nomes and len(nomes) == 4
    assert any('Silva' in n and 'Ana' in n for n in nomes)   # cada folha do Excel leva o nome do aluno


def test_aluno_de_outra_escola_negado(cenario):
    _, _, alheio = cenario
    r = _cliente('admin.fra@sige.mz').post(URL + 'gerar/', _corpo(escopo='aluno', aluno_id=str(alheio.id)), format='json')
    assert r.status_code == 403


def test_turma_sem_alunos_nao_inventa_dados(cenario):
    a, _, _ = cenario
    vazia = Turma.objects.create(escola=a, nome='Vazia', grau_ano='11ª Classe')
    r = _cliente('admin.fra@sige.mz').post(URL + 'gerar/', _corpo(escopo='turma', turma_id=str(vazia.id)), format='json')
    assert r.status_code == 404


def test_branco_e_validacao(cenario):
    c = _cliente('admin.fra@sige.mz')
    assert c.post(URL + 'gerar/', _corpo(escopo='branco', copias=2), format='json').status_code == 200
    assert c.post(URL + 'gerar/', _corpo(escopo='branco', copias=0), format='json').status_code == 400
    ruim = _corpo(escopo='branco', copias=1)
    ruim['config']['n_perguntas'] = 0
    assert c.post(URL + 'gerar/', ruim, format='json').status_code == 400


def test_classe_filtra_por_area(cenario):
    a, _, _ = cenario
    tc = Turma.objects.create(escola=a, nome='Turma 2', grau_ano='10ª Classe', area='Ciências', ano_letivo=a.ano_letivo_ativo)
    Aluno.objects.create(escola=a, turma=tc, matricula='MAT_FR_C', nome='Dina', data_nascimento='2009-01-01', genero='F')
    c = _cliente('admin.fra@sige.mz')
    r = c.post(URL + 'gerar/', _corpo(escopo='classe', classe='10ª Classe', area='Ciências'), format='json')
    assert r.status_code == 200 and r['X-Total-Folhas'] == '1'
    r = c.post(URL + 'gerar/', _corpo(escopo='classe', classe='10ª Classe'), format='json')
    assert r['X-Total-Folhas'] == '4'


def test_qr_abre_pagina_oficial_e_verificacao_publica(cenario):
    a, turma, _ = cenario
    esc = fr.montar_dados_escola(a)
    aluno = Aluno.objects.filter(turma=turma).first()
    cfg = fr.normalizar_config({'disciplina': 'Matemática', 'n_perguntas': 10, 'versoes': 'A'}, esc)
    url = fr._payload_qr(esc, fr.montar_dados_aluno(aluno, 1), cfg, '2026', 'A')
    assert url.startswith('https://sigesaas.duckdns.org/verificar-folha.html?d=')
    import urllib.parse as up
    q = dict(up.parse_qsl(up.urlparse(url).query))
    r = APIClient().get(URL + 'verificar/', q)  # público: sem login
    assert r.status_code == 200 and r.data['valida'] is True
    assert r.data['escola']['nome'] == 'Escola A' and r.data['disciplina'] == 'Matemática'
    assert aluno.nome not in str(r.data) and aluno.matricula not in str(r.data)  # sem dados pessoais
    assert r.data['aluno']['codigo_mascarado'].endswith(aluno.matricula[-4:])
    # adulterado
    q['s'] = '0' * 16
    assert APIClient().get(URL + 'verificar/', q).status_code == 404
    assert APIClient().get(URL + 'verificar/').status_code == 404


def test_folha_inclui_area_seccao_do_aluno(cenario):
    a, _, _ = cenario
    tc = Turma.objects.create(escola=a, nome='Turma 2', grau_ano='10ª Classe', area='Ciências', ano_letivo=a.ano_letivo_ativo)
    al = Aluno.objects.create(escola=a, turma=tc, matricula='MAT_FR_AREA', nome='Eva',
                              data_nascimento='2009-01-01', genero='F')
    d = fr.montar_dados_aluno(al, 1)
    assert d['area'] == 'Ciências'
    r = _cliente('admin.fra@sige.mz').post(URL + 'gerar/', _corpo(escopo='aluno', aluno_id=str(al.id), formato='xlsx'), format='json')
    ws = openpyxl.load_workbook(io.BytesIO(r.content)).worksheets[0]
    texto = ' '.join(str(c.value) for row in ws.iter_rows() for c in row if c.value is not None)
    assert 'ÁREA/SECÇÃO' in texto and 'Ciências' in texto


def test_area_seccao_especifica(cenario):
    a, turma, _ = cenario
    base = dict(escola=a, nome='X', data_nascimento='2009-01-01', genero='F')

    def novo(matricula, **kw):
        obj = Aluno.objects.create(turma=turma, matricula=matricula, **base, **kw)
        Aluno.objects.filter(pk=obj.pk).update(matricula=matricula)  # o modelo gera o código; fixa o valor oficial
        return Aluno.objects.select_related('turma').get(pk=obj.pk)

    # turma genérica «Ciências» + sigla no código → secção específica
    turma.area = 'Ciências'
    turma.save()
    al = novo('0411S0001.11.02.2026.cg.02')
    assert fr.nome_area_secao(al) == 'Ciências com Geografia'
    al2 = novo('0411S0001.11.02.2026.lh.03')
    assert fr.nome_area_secao(al2) == 'Letras com História'
    # área específica no próprio aluno tem prioridade
    al3 = novo('0411S0001.11.02.2026.cg.04', area='Ciências com Desenho')
    assert fr.nome_area_secao(al3) == 'Ciências com Desenho'
    # sem informação específica: valor genérico ou Ensino Geral
    turma.area = 'Geral'
    turma.save()
    al4 = novo('MAT_SEM_SIGLA')
    assert fr.nome_area_secao(al4) == 'Ensino Geral'


def test_hora_final_calculada_pela_duracao():
    assert fr.somar_minutos('07:30', 90) == '09:00'
    assert fr.somar_minutos('23:30', 60) == '00:30'
    assert fr.somar_minutos('25:00', 60) == ''
    cfg = fr.normalizar_config({'disciplina': 'X', 'n_perguntas': 10, 'hora_inicio': '8:15', 'duracao_min': 45})
    assert cfg['hora_inicio'] == '08:15' and cfg['hora_fim'] == '09:00'
    assert fr.texto_hora_sala({**cfg, 'sala': 'S3'}) == '08:15 – 09:00 · Sala: S3'
    cfg2 = fr.normalizar_config({'disciplina': 'X', 'n_perguntas': 10, 'hora_inicio': '08:00', 'hora_fim': '10:30'})
    assert cfg2['hora_fim'] == '10:30'


def test_rotulos_de_correccao_conforme_o_tipo():
    normal = fr.normalizar_config({'tipo_avaliacao': 'ACS1', 'disciplina': 'X', 'n_perguntas': 10})
    exame = fr.normalizar_config({'tipo_avaliacao': 'EXAME', 'disciplina': 'X', 'n_perguntas': 10})
    assert fr.rotulos_correccao(normal) == ('CORRECÇÃO NORMAL', 'RECORRECÇÃO')
    assert fr.rotulos_correccao(exame) == ('1ª CORRECÇÃO', '2ª CORRECÇÃO')


def test_logo_da_escola_opcional_e_nunca_no_exame():
    import base64, io
    from types import SimpleNamespace
    from PIL import Image
    b = io.BytesIO(); Image.new('RGB', (20, 20), (200, 30, 30)).save(b, 'PNG')
    escola = {'obj': SimpleNamespace(logo_url='', logo_base64='data:image/png;base64,' + base64.b64encode(b.getvalue()).decode())}
    assert fr.logo_proprio_escola(escola)
    assert fr.logo_proprio_escola({'obj': SimpleNamespace(logo_url='', logo_base64='', logo='')}) is None
    base = {'disciplina': 'Matemática', 'n_perguntas': 10, 'n_alternativas': 4, 'logo_escola': True}
    assert fr.normalizar_config(dict(base, tipo_avaliacao='ACS1'))['logo_escola'] is True
    assert fr.normalizar_config(dict(base, tipo_avaliacao='EXAME'))['logo_escola'] is False
    assert fr.normalizar_config({k: v for k, v in base.items() if k != 'logo_escola'})['logo_escola'] is False


def test_folha_a_partir_de_lista_importada_com_exclusoes_e_listas(cenario):
    import json
    import zipfile
    from django.core.files.uploadedfile import SimpleUploadedFile
    a, turma, _ = cenario
    ana = Aluno.objects.get(nome='Ana', turma=turma)
    csv_ = f'Nome;Apelido;Codigo;Situacao\nAna;Silva;{ana.matricula};\nZeca;Mondlane;;Transferida\nRita;Cossa;;\n'.encode('utf-8')
    corpo = _corpo(escopo='lista', excluir=True, motivos=['transferida'])
    c = _cliente('admin.fra@sige.mz')
    r = c.post(URL + 'gerar/', {'dados': json.dumps(corpo), 'lista': SimpleUploadedFile('alunos.csv', csv_)}, format='multipart')
    assert r.status_code == 200, r.content[:300]
    assert r['X-Total-Folhas'] == '2'   # Zeca (transferida) fica de fora
    z = zipfile.ZipFile(io.BytesIO(r.content))
    assert any(n.endswith('_LISTA_ALUNOS_gerados.pdf') for n in z.namelist())
    wb = openpyxl.load_workbook(io.BytesIO(z.read([n for n in z.namelist() if n.endswith('.xlsx') and 'LISTA' in n][0])))
    assert wb.sheetnames == ['Alunos']
    # sem ficheiro: recusado
    r = c.post(URL + 'gerar/', {'dados': json.dumps(corpo)}, format='multipart')
    assert r.status_code == 400