"""Registo das correcções automáticas: modelo, rotas e isolamento básico (sem dados fictícios de alunos/notas)."""
from django.urls import resolve, reverse


def test_rotas_registos_existem():
    assert resolve('/api/v1/notas/provas-fisicas/registos/').url_name == 'correcao_registos'
    rid = '11111111-1111-1111-1111-111111111111'
    assert resolve(f'/api/v1/notas/provas-fisicas/registos/{rid}/ficheiro/').url_name == 'correcao_registo_ficheiro'
    assert resolve(f'/api/v1/notas/provas-fisicas/{rid}/registos/').url_name == 'correcao_registo_criar'


def test_registos_exigem_autenticacao(client):
    r = client.get('/api/v1/notas/provas-fisicas/registos/')
    assert r.status_code in (401, 403)
