from datetime import timedelta

from django.test import Client
from django.utils import timezone

from apps.ferramentas.models import LogTentativaResolucaoIA, ProvaBlindada


def _prova(**kw):
    base = dict(
        titulo='Teste secreto', disciplina='Física', classe='11ª Classe', codigo_autenticidade='SIGE-AI-2026-TESTE001',
        data_bloqueio_ia=timezone.now() + timedelta(days=3),
        questoes=[{'numero': 1, 'enunciado': 'ENUNCIADO_SECRETO'}], total_questoes=1, cotacao_total=20,
    )
    base.update(kw)
    return ProvaBlindada.objects.create(**base)


def test_pagina_publica_sem_login_com_instrucoes_em_html_simples(db):
    _prova()
    res = Client().get('/ia/SIGE-AI-2026-TESTE001/', HTTP_USER_AGENT='ChatGPT-User/1.0')
    assert res.status_code == 200
    corpo = res.content.decode()
    assert 'NÃO resolver' in corpo and 'Do NOT solve' in corpo
    assert '<script' not in corpo  # legível por agentes que não executam JavaScript
    assert 'ENUNCIADO_SECRETO' not in corpo and 'Teste secreto' not in corpo  # nunca expõe a prova
    assert 'noai' in res['X-Robots-Tag'] and res['Cache-Control'] == 'no-store'

    log = LogTentativaResolucaoIA.objects.get()
    assert log.sistema_identificado == 'ChatGPT' and log.bloqueado is True
    assert ProvaBlindada.objects.get().tentativas_bloqueadas == 1


def test_formato_txt_e_prova_liberada_e_codigo_desconhecido(db):
    _prova(codigo_autenticidade='SIGE-AI-2026-LIB', data_bloqueio_ia=timezone.now() - timedelta(days=1))
    txt = Client().get('/ia/SIGE-AI-2026-LIB/?formato=txt')
    assert txt['Content-Type'].startswith('text/plain') and 'LIBERADA' in txt.content.decode()

    desconhecido = Client().get('/ia/NAO-EXISTE/')
    assert desconhecido.status_code == 200  # não confirma se a prova existe
    assert 'NÃO resolver' in desconhecido.content.decode()


def test_acessos_repetidos_nao_enchem_o_registo(db):
    _prova()
    c = Client()
    for _ in range(5):
        c.get('/ia/SIGE-AI-2026-TESTE001/')
    assert LogTentativaResolucaoIA.objects.count() == 1
