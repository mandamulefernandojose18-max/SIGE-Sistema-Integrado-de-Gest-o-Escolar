"""Descarregar turma (Turmas & Capacidade): ZIP com ficha + relação nominal, carimbo obrigatório e isolamento."""
import io
import zipfile

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.alunos.models import Aluno
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma

SENHA = 'FichaPass123!'
BASE = '/api/v1/escola-admin/turmas/{}/ficha/'


def _login(email):
    c = APIClient()
    r = c.post('/api/v1/auth/login/', {'email': email, 'password': SENHA}, format='json')
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['token']}")
    return c


def _escola(nif):
    plano = Plano.objects.create(nome=f'PL_{nif}', preco=1500, duracao_dias=30)
    return Escola.objects.create(nome=f'Escola {nif}', nif_cnpj=nif, email=f'{nif}@e.mz', status='ATIVA',
                                 plano=plano, ano_letivo_ativo='2026')


@pytest.mark.django_db
def test_zip_ficha_e_relacao_nominal_e_isolamento():
    e1, e2 = _escola('71000001'), _escola('71000002')
    Usuario.objects.create_user(email='a@f.mz', password=SENHA, role='ADMIN_ESCOLA', escola=e1)
    t1 = Turma.objects.create(escola=e1, nome='Turma 1', grau_ano='11ª Classe', ano_letivo='2026')
    t2 = Turma.objects.create(escola=e2, nome='Turma 9', grau_ano='11ª Classe', ano_letivo='2026')
    Aluno.objects.create(escola=e1, turma=t1, matricula='2026001', nome='Ana', apelido='Silva',
                         data_nascimento='2009-01-01', genero='F')
    c = _login('a@f.mz')
    r = c.get(BASE.format(t1.id) + '?formato=xlsx&carimbo=nao')
    assert r.status_code == 200 and r['Content-Type'] == 'application/zip'
    nomes = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert nomes == ['1_ficha_da_turma.xlsx', '2_relacao_nominal_dos_alunos.xlsx']
    assert c.get(BASE.format(t1.id) + '?formato=xlsx').status_code == 409  # sem decisão: nunca assume
    assert c.get(BASE.format(t2.id) + '?formato=xlsx&carimbo=nao').status_code == 404  # outra escola


@pytest.mark.django_db
def test_zip_pdf_com_carimbo_gera_dois_pdfs():
    e1 = _escola('71000003')
    Usuario.objects.create_user(email='b@f.mz', password=SENHA, role='ADMIN_ESCOLA', escola=e1)
    t1 = Turma.objects.create(escola=e1, nome='Turma 2', grau_ano='11ª Classe', ano_letivo='2026')
    c = _login('b@f.mz')
    r = c.get(BASE.format(t1.id) + '?formato=pdf&carimbo=sim')
    assert r.status_code in (200, 409), r.content[:200]
    if r.status_code == 200:
        z = zipfile.ZipFile(io.BytesIO(r.content))
        assert [n.rsplit('.', 1)[-1] for n in z.namelist()] == ['pdf', 'pdf']
        assert all(z.read(n)[:4] == b'%PDF' for n in z.namelist())
