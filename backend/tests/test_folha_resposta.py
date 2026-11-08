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
    assert r.content[:4] == b'%PDF'
    assert r.content.count(b'/Type /Page\n') + r.content.count(b'/Type /Page ') >= 3


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
    nomes = openpyxl.load_workbook(io.BytesIO(r.content)).sheetnames
    assert 'Resumo' in nomes and len(nomes) == 4


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
    assert fr.rotulos_correccao(normal) == ('Correcção Normal', 'Recorrecção')
    assert fr.rotulos_correccao(exame) == ('1ª Correcção', '2ª Correcção')
