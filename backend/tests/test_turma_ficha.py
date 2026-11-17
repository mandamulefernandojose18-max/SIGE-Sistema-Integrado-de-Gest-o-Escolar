"""Ficha da turma (botão «Descarregar» em Turmas & Capacidade): PDF/Excel, carimbo obrigatório e isolamento."""
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.tenants.models import Escola, Plano
from apps.turmas.models import Turma

SENHA = 'FichaPass123!'


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
def test_ficha_turma_xlsx_sem_carimbo_e_isolamento():
    e1, e2 = _escola('71000001'), _escola('71000002')
    Usuario.objects.create_user(email='a@f.mz', password=SENHA, role='ADMIN_ESCOLA', escola=e1)
    t1 = Turma.objects.create(escola=e1, nome='Turma 1', grau_ano='11ª Classe', ano_letivo='2026')
    t2 = Turma.objects.create(escola=e2, nome='Turma 9', grau_ano='11ª Classe', ano_letivo='2026')
    c = _login('a@f.mz')
    base = '/api/v1/escola-admin/turmas/{}/ficha/'
    r = c.get(base.format(t1.id) + '?formato=xlsx&carimbo=nao')
    assert r.status_code == 200
    assert r.content[:2] == b'PK'
    assert c.get(base.format(t1.id) + '?formato=xlsx').status_code == 409  # sem decisão: nunca assume
    assert c.get(base.format(t2.id) + '?formato=xlsx&carimbo=nao').status_code == 404  # outra escola
