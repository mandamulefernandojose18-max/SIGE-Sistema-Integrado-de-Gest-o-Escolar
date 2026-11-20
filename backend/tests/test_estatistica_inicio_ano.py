"""Mapa Estatístico de Início do Ano: turma -> classe -> escola, PDF/Excel e permissões."""
import datetime
import io

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.alunos import estatistica_inicio_ano as est
from apps.alunos.models import Aluno
from apps.disciplinas.models import Disciplina
from apps.professores.models import AlocacaoDocente, Professor
from apps.tenants.models import Escola
from apps.turmas.models import Turma

pytestmark = pytest.mark.django_db
ANO = '2026'
API = '/api/v1/alunos/estatistica-inicio-ano/'


def _logo_png():
    import base64
    from PIL import Image
    b = io.BytesIO()
    Image.new('RGB', (20, 20), (30, 58, 138)).save(b, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()


def _escola(nome, nuit):
    return Escola.objects.create(nome=nome, nif_cnpj=nuit, email=f'{nuit.lower()}@sige.mz', status='ATIVA',
                                 usar_emblema_nacional=False, logo_base64=_logo_png())


def _prof(escola, nome):
    return Professor.objects.create(escola=escola, nome=nome, email=f'{nome.lower()}@sige.mz', especialidade='Geral')


def _turma(escola, nome, classe, area='Geral', **kw):
    return Turma.objects.create(escola=escola, nome=nome, grau_ano=classe, area=area, ano_letivo=ANO, **kw)


_seq = {'n': 0}


def _aluno(escola, turma, genero, nasc, **kw):
    _seq['n'] += 1
    return Aluno.objects.create(escola=escola, turma=turma, classe=turma.grau_ano, nome=f'Aluno {_seq["n"]}',
                                matricula=f'M{_seq["n"]:05d}', data_nascimento=nasc, genero=genero, **kw)


def _cliente(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.fixture
def cenario():
    esc = _escola('Escola Alfa', 'NUIT_A')
    outra = _escola('Escola Beta', 'NUIT_B')
    t1 = _turma(esc, 'A', '8ª Classe')
    t2 = _turma(esc, 'B', '8ª Classe')
    t10 = _turma(esc, 'A', '10ª Classe', area='Ciências')
    _aluno(esc, t1, 'M', datetime.date(2012, 5, 1), orfandade='PAI', meio_transporte='A_PE',
           tempo_casa_escola='ATE_30', local_residencia='Bairro Central')
    _aluno(esc, t1, 'F', datetime.date(2012, 8, 1), necessidade_especial='DV', meio_transporte='BICICLETA',
           tempo_casa_escola='ATE_30', local_residencia='Bairro Central')
    _aluno(esc, t2, 'F', datetime.date(2011, 1, 1), orfandade='AMBOS', tempo_casa_escola='DE_30_A_60', local_residencia='Mafalala')
    _aluno(esc, t10, 'M', datetime.date(2009, 3, 3))
    _aluno(esc, t10, 'F', datetime.date(2009, 3, 3), status='TRANSFERIDO')  # não conta
    _aluno(outra, _turma(outra, 'A', '8ª Classe'), 'M', datetime.date(2012, 1, 1))  # outra escola
    return {'esc': esc, 'outra': outra, 't1': t1, 't2': t2, 't10': t10}


def test_turma_conta_so_ativos_com_idades_e_dados_da_matricula(cenario):
    d = est.compilar_turma(cenario['esc'], cenario['t1'])
    m = d['mapa']
    assert m['matriculados'] == {'h': 1, 'm': 1, 't': 2}
    assert [i['rotulo'] for i in m['idades']] == ['14']  # 2026 - 2012
    assert next(i for i in m['nee'] if i['codigo'] == 'DV')['m'] == 1
    assert next(i for i in m['orfaos'] if i['codigo'] == 'PAI')['h'] == 1
    assert next(i for i in m['transporte'] if i['codigo'] == 'BICICLETA')['t'] == 1
    ate30 = next(i for i in m['tempo'] if i['codigo'] == 'ATE_30')
    assert ate30['t'] == 2 and 'Bairro Central (2)' in ate30['locais']
    assert d['disciplinas'] == [] and d['ciclo'] == 1  # 1º ciclo: sem parte das disciplinas


def test_classe_soma_os_mapas_das_turmas_e_escola_agrega_por_ciclo(cenario):
    c = est.compilar_classe(cenario['esc'], '8ª Classe', ANO)
    assert c['mapa']['matriculados']['t'] == 3
    assert [t['rotulo'] for t in c['turmas']] == ['A', 'B']
    assert [i['rotulo'] for i in c['mapa']['idades']] == ['14', '15']
    e = est.compilar_escola(cenario['esc'], ANO)
    g = {x['chave']: x for x in e['grupos']}
    assert g['CICLO1']['mapa']['matriculados']['t'] == 3
    assert g['CICLO2']['mapa']['matriculados']['t'] == 1  # o transferido não conta
    assert g['GERAL']['mapa']['matriculados']['t'] == 4
    assert [c['rotulo'] for c in g['GERAL']['classes']] == ['8ª Classe', '10ª Classe']


def test_segundo_ciclo_traz_disciplinas_com_professor_e_matriculados(cenario):
    esc, t10 = cenario['esc'], cenario['t10']
    disc = Disciplina.objects.create(escola=esc, nome='Biologia', codigo='BIO10', classe='10ª Classe', area='Ciências', ano_letivo=ANO)
    AlocacaoDocente.objects.create(escola=esc, professor=_prof(esc, 'Ana'), disciplina=disc, turma=t10)
    d = est.compilar_turma(esc, t10)
    assert d['ciclo'] == 2
    assert [(x['nome'], x['professor'], x['t']) for x in d['disciplinas']] == [('Biologia', 'Ana', 1)]
    c = est.compilar_classe(esc, '10ª Classe', ANO)
    assert c['disciplinas'][0]['area'] == 'Ciências' and c['disciplinas'][0]['t'] == 1


def test_sem_alunos_nao_inventa_dados(cenario):
    vazia = _turma(cenario['esc'], 'Z', '9ª Classe')
    d = est.compilar_turma(cenario['esc'], vazia)
    assert d['mapa']['matriculados']['t'] == 0 and d['mapa']['idades'] == []


def test_pdf_e_xlsx_da_turma_classe_e_escola(cenario):
    from openpyxl import load_workbook
    admin = Usuario.objects.create_user(email='dir@a.mz', password='SchoolPass2026!', role='ADMIN_ESCOLA', nome='Dir', escola=cenario['esc'])
    c = _cliente(admin)
    t1 = cenario['t1'].id
    for url in (f'{API}turma/{t1}/pdf?carimbo=nao', f'{API}classe/pdf?classe=8ª Classe&ano={ANO}&carimbo=nao', f'{API}escola/pdf?ano={ANO}&carimbo=nao'):
        r = c.get(url)
        assert r.status_code == 200 and r.content[:4] == b'%PDF', url
    r = c.get(f'{API}escola/xlsx?ano={ANO}&carimbo=nao')
    assert r.status_code == 200
    wb = load_workbook(io.BytesIO(r.content))
    assert len(wb.worksheets) == 3  # 1º Ciclo, 2º Ciclo, 1º + 2º Ciclos
    assert c.get(f'{API}turma/{t1}/xlsx?carimbo=nao').status_code == 200
    assert c.get(f'{API}classe/xlsx?classe=10ª Classe&ano={ANO}&carimbo=nao').status_code == 200


def test_permissoes_e_isolamento(cenario):
    esc, outra = cenario['esc'], cenario['outra']
    dt, dc, estranho = _prof(esc, 'Dt'), _prof(esc, 'Dc'), _prof(esc, 'Estranho')
    Turma.objects.filter(id=cenario['t1'].id).update(director_turma=dt)
    Turma.objects.filter(grau_ano='8ª Classe', escola=esc).update(director_classe=dc)

    def prof_user(p, mail):
        u = Usuario.objects.create_user(email=mail, password='SchoolPass2026!', role='PROFESSOR', nome=p.nome, escola=esc)
        Usuario.objects.filter(pk=u.pk).update(professor_id=p.id)
        u.refresh_from_db()
        return _cliente(u)

    t1 = cenario['t1'].id
    assert prof_user(dt, 'dt@a.mz').get(f'{API}turma/{t1}').status_code == 200
    assert prof_user(dc, 'dc@a.mz').get(f'{API}turma/{t1}').status_code == 200
    assert prof_user(estranho, 'x@a.mz').get(f'{API}turma/{t1}').status_code == 403
    assert prof_user(dc, 'dc2@a.mz').get(f'{API}classe?classe=8ª Classe&ano={ANO}').status_code == 200
    assert prof_user(dt, 'dt2@a.mz').get(f'{API}classe?classe=8ª Classe&ano={ANO}').status_code == 403
    assert prof_user(dc, 'dc3@a.mz').get(f'{API}escola?ano={ANO}').status_code == 403
    minhas = prof_user(dt, 'dt3@a.mz').get(f'{API}minhas?ano={ANO}').json()['data']
    assert [t['nome'] for t in minhas['turmas_dt']] == ['A'] and minhas['classes_dc'] == []
    # outra escola não vê turmas desta
    admin_b = Usuario.objects.create_user(email='dir@b.mz', password='SchoolPass2026!', role='ADMIN_ESCOLA', nome='DirB', escola=outra)
    assert _cliente(admin_b).get(f'{API}turma/{t1}').status_code == 404
    assert _cliente(admin_b).get(f'{API}escola?ano={ANO}').json()['data']['grupos'][2]['mapa']['matriculados']['t'] == 1


def test_matricula_guarda_os_novos_campos_pela_api(cenario):
    admin = Usuario.objects.create_user(email='dir2@a.mz', password='SchoolPass2026!', role='ADMIN_ESCOLA', nome='Dir', escola=cenario['esc'])
    r = _cliente(admin).post('/api/v1/alunos', {
        'nome': 'Novo', 'data_nascimento': '2012-02-02', 'genero': 'F', 'turma_id': str(cenario['t1'].id),
        'orfandade': 'MAE', 'necessidade_especial': 'ALB', 'meio_transporte': 'A_PE',
        'tempo_casa_escola': 'DE_60_A_90', 'local_residencia': 'Liberdade',
    }, format='json')
    assert r.status_code in (200, 201), r.content
    a = Aluno.objects.get(nome='Novo')
    assert (a.orfandade, a.necessidade_especial, a.tempo_casa_escola, a.local_residencia) == ('MAE', 'ALB', 'DE_60_A_90', 'Liberdade')

