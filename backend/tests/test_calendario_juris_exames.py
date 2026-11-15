"""Calendário de Exames, formação automática de júris, PDFs e vista privada do aluno."""
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.alunos.models import Aluno
from apps.disciplinas.models import Disciplina
from apps.notas.models import CalendarioExame, JuriExame, Nota
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma

SENHA = 'ExamePass123!'


def _login(email):
    c = APIClient()
    r = c.post('/api/v1/auth/login/', {'email': email, 'password': SENHA}, format='json')
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['token']}")
    return c


def _escola(nome, nif, email):
    plano = Plano.objects.create(nome=f'PL_{nif}', preco=1500, duracao_dias=30)
    return Escola.objects.create(nome=nome, nif_cnpj=nif, email=email, status='ATIVA', plano=plano,
                                 ano_letivo_ativo='2026')


@pytest.mark.django_db
class TestCalendarioJurisExames:
    def setup_method(self):
        self.escola = _escola('Escola Exames', '70010001', 'ex@escola.mz')
        Usuario.objects.create_user(email='dir@ex.mz', password=SENHA, role='ADMIN_ESCOLA', escola=self.escola)
        Usuario.objects.create_user(email='prof@ex.mz', password=SENHA, role='PROFESSOR', escola=self.escola)
        self.turma = Turma.objects.create(escola=self.escola, nome='10ª A', grau_ano='10ª Classe', ano_letivo='2026')
        self.mat = Disciplina.objects.create(escola=self.escola, nome='Matemática', codigo='MAT-10', ano_letivo='2026', tem_exame=True)
        self.fis = Disciplina.objects.create(escola=self.escola, nome='Física', codigo='FIS-10', ano_letivo='2026', tem_exame=True)
        self.alunos = []
        # 7 admitidos (freq 12) e 2 excluídos (freq 8) a Matemática
        for i in range(9):
            a = Aluno.objects.create(escola=self.escola, turma=self.turma, matricula=f'20269{i:02d}',
                                     nome=f'Aluno{i:02d}', apelido='Teste', data_nascimento='2009-01-01', genero='M')
            self.alunos.append(a)
            freq = 12 if i < 7 else 8
            Nota.objects.create(escola=self.escola, aluno=a, turma=self.turma, disciplina=self.mat,
                                periodo='1_TRIMESTRE', media_final=freq, resultado='Aprovado')
            Nota.objects.create(escola=self.escola, aluno=a, turma=self.turma, disciplina=self.fis,
                                periodo='1_TRIMESTRE', media_final=13, resultado='Aprovado')
        self.c = _login('dir@ex.mz')

    def _calendario(self, **extra):
        itens = [
            {'disciplina': 'Matemática', 'epoca': 1, 'data': '2026-11-20', 'periodo': 'MANHA',
             'hora_inicio': '08:00', 'duracao_minutos': 120},
            {'disciplina': 'Física', 'epoca': 1, 'data': '2026-11-20', 'periodo': 'MANHA',
             'hora_inicio': '08:30', 'duracao_minutos': 90},
        ]
        itens[1].update(extra)
        return self.c.post('/api/v1/notas/calendario-exames/', {'ano_letivo': '2026', 'classe': '10ª Classe', 'itens': itens},
                           format='json')

    def test_hora_final_automatica_e_listagem(self):
        r = self._calendario(hora_inicio='10:30')
        assert r.status_code == 200, r.data
        c = CalendarioExame.objects.get(disciplina='Matemática', epoca=1)
        assert c.hora_fim.strftime('%H:%M') == '10:00'
        r = self.c.get('/api/v1/notas/calendario-exames/?ano=2026&classe=10ª Classe')
        linhas = {l['disciplina']: l for l in r.data['data']['linhas']}
        assert linhas['Matemática']['admitidos'] == 7 and linhas['Matemática']['excluidos'] == 2
        assert linhas['Matemática']['chamadas']['1']['hora_fim'] == '10:00'

    def test_conflito_de_horario_e_periodo_obrigatorio(self):
        r = self._calendario()  # Física 08:30 sobrepõe Matemática 08:00-10:00
        assert r.status_code == 400 and 'Conflito' in r.data['message']
        r = self._calendario(hora_inicio='10:00', periodo='')
        assert r.status_code == 400 and 'período' in r.data['message']

    def test_segunda_epoca_depois_da_primeira(self):
        assert self._calendario(hora_inicio='10:30').status_code == 200
        r = self.c.post('/api/v1/notas/calendario-exames/', {'ano_letivo': '2026', 'classe': '10ª Classe', 'itens': [
            {'disciplina': 'Matemática', 'epoca': 2, 'data': '2026-11-19', 'periodo': 'TARDE',
             'hora_inicio': '14:00', 'duracao_minutos': 120}]}, format='json')
        assert r.status_code == 400

    def test_formar_juris_equilibrados_com_salas_e_frequencia(self):
        self._calendario(hora_inicio='10:30')
        r = self.c.post('/api/v1/notas/juris-exame/formar/',
                        {'ano_letivo': '2026', 'epoca': 1, 'max_alunos': 4, 'num_salas': 2}, format='json')
        assert r.status_code == 200, r.data
        # Matemática: 7 admitidos -> 2 júris (4+3). Física: 9 -> 3 júris (3+3+3).
        assert r.data['data']['juris_formados'] == 5
        mat = list(JuriExame.objects.filter(disciplina='Matemática').order_by('numero'))
        assert [j.alunos_juri.count() for j in mat] == [4, 3]
        assert not any(ja.aluno in self.alunos[7:] for j in mat for ja in j.alunos_juri.all())  # excluídos fora
        r = self.c.get('/api/v1/notas/juris-exame/?ano=2026&epoca=1&classe=10ª Classe&disciplina=Matemática')
        j1 = r.data['data'][0]
        assert j1['alunos'][0]['freq'] == 12.0 and j1['data'] == '2026-11-20'
        assert j1['sala'].startswith('Sala ')
        # Matemática (08:00-10:00) e Física (10:30-12:00) não se sobrepõem: sala pode repetir; sem salas livres só ocorre com choque.
        assert r.data['data'][0]['sala'] != r.data['data'][1]['sala']

    def test_sala_em_falta_gera_aviso(self):
        itens = [{'disciplina': 'Matemática', 'epoca': 1, 'data': '2026-11-20', 'periodo': 'MANHA',
                  'hora_inicio': '08:00', 'duracao_minutos': 120}]
        self.c.post('/api/v1/notas/calendario-exames/', {'ano_letivo': '2026', 'classe': '10ª Classe', 'itens': itens}, format='json')
        r = self.c.post('/api/v1/notas/juris-exame/formar/', {'epoca': 1, 'max_alunos': 4, 'num_salas': 1}, format='json')
        assert r.status_code == 200
        assert any('sem sala' in a for a in r.data['data']['avisos'])

    def test_sala_opcional(self):
        self._calendario(hora_inicio='10:30')
        r = self.c.post('/api/v1/notas/juris-exame/formar/', {'epoca': 1, 'max_alunos': 50}, format='json')
        assert r.status_code == 200
        assert JuriExame.objects.filter(sala='').count() == JuriExame.objects.count()

    def test_pdfs_juris_e_excluidos(self):
        self._calendario(hora_inicio='10:30')
        self.c.post('/api/v1/notas/juris-exame/formar/', {'epoca': 1, 'max_alunos': 4}, format='json')
        r = self.c.get('/api/v1/notas/juris-exame/pdf/?ano=2026&epoca=1')
        assert r.status_code == 200 and r.content[:4] == b'%PDF'
        r = self.c.get('/api/v1/notas/juris-exame/excluidos/?ano=2026&classe=10ª Classe')
        mat = next(g for g in r.data['data'] if g['disciplina'] == 'Matemática')
        assert len(mat['alunos']) == 2 and all(a['freq'] == 8.0 for a in mat['alunos'])
        r = self.c.get('/api/v1/notas/juris-exame/excluidos/pdf/?ano=2026&classe=10ª Classe')
        assert r.status_code == 200 and r.content[:4] == b'%PDF'

    def test_professor_so_le_e_aluno_nao_acede(self):
        prof = _login('prof@ex.mz')
        assert prof.get('/api/v1/notas/calendario-exames/?ano=2026&classe=10ª Classe').status_code == 200
        assert prof.post('/api/v1/notas/juris-exame/formar/', {'epoca': 1, 'max_alunos': 4}, format='json').status_code == 403
        Usuario.objects.create_user(email='al@ex.mz', password=SENHA, role='ALUNO', escola=self.escola,
                                    aluno_id=self.alunos[0].id)
        assert _login('al@ex.mz').get('/api/v1/notas/juris-exame/?ano=2026&epoca=1').status_code == 403

    def test_isolamento_entre_escolas(self):
        self._calendario(hora_inicio='10:30')
        outra = _escola('Outra Escola', '70010002', 'outra@escola.mz')
        Usuario.objects.create_user(email='dir@outra.mz', password=SENHA, role='ADMIN_ESCOLA', escola=outra)
        c2 = _login('dir@outra.mz')
        r = c2.get('/api/v1/notas/calendario-exames/?ano=2026&classe=10ª Classe')
        assert r.data['data']['linhas'] == []
        assert c2.get('/api/v1/notas/juris-exame/?ano=2026&epoca=1').data['data'] == []

    def test_aluno_ve_so_os_seus_dados(self):
        self._calendario(hora_inicio='10:30')
        self.c.post('/api/v1/notas/juris-exame/formar/', {'epoca': 1, 'max_alunos': 4, 'num_salas': 3}, format='json')
        Usuario.objects.create_user(email='a0@ex.mz', password=SENHA, role='ALUNO', escola=self.escola,
                                    aluno_id=self.alunos[0].id)
        Usuario.objects.create_user(email='a8@ex.mz', password=SENHA, role='ALUNO', escola=self.escola,
                                    aluno_id=self.alunos[8].id)
        r = _login('a0@ex.mz').get('/api/v1/alunos/me/calendario-exames/?ano=2026')
        assert r.status_code == 200
        itens = {i['disciplina']: i for i in r.data['data']['itens']}
        m = itens['Matemática']
        assert m['estado'] == 'ADMITIDO' and m['nota_frequencia'] == 12.0
        ch = m['chamadas'][0]
        assert ch['juri'] == 1 and ch['sala'] and ch['data'] == '2026-11-20' and ch['hora_fim'] == '10:00'
        texto = str(r.data)
        assert 'Aluno01' not in texto and 'Teste' not in texto and 'matricula' not in texto  # sem colegas
        # excluído a Matemática: sem calendário nem júri, só a sua situação
        r8 = _login('a8@ex.mz').get('/api/v1/alunos/me/calendario-exames/?ano=2026')
        m8 = {i['disciplina']: i for i in r8.data['data']['itens']}['Matemática']
        assert m8['estado'] == 'EXCLUIDO' and m8['chamadas'] == []
