import io
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.ferramentas.models import LogTentativaResolucaoIA, ProvaBlindada
from apps.ferramentas.services import analise_prova
from tests.test_ferramentas_autenticacao import _token, duas_escolas  # noqa: F401

TEXTO = (
    "1. Um fio condutor é atravessado por 48 C de carga eléctrica em 8 s. A intensidade da corrente é:\n"
    "A) 6 A B) 384 A C) 40 A D) 0,17 A\n"
    "2. Com os valores que medimos na aula de segunda-feira, calcule a resistência do circuito da nossa turma.\n"
)


def test_dependencia_da_turma_separa_genericas_de_locais():
    from apps.ferramentas.views import _extrair_questoes_de_texto
    r = analise_prova.dependencia_da_turma(_extrair_questoes_de_texto(TEXTO))
    assert r['genericas'] == [1] and r['dependentes_da_turma'] == [2] and r['percentagem_genericas'] == 50


def test_originalidade_sem_chave_fica_indisponivel_e_com_chave_usa_pesquisa(monkeypatch):
    from apps.ferramentas.views import _extrair_questoes_de_texto
    qs = _extrair_questoes_de_texto(TEXTO)
    monkeypatch.delenv('BRAVE_SEARCH_API_KEY', raising=False)
    assert analise_prova.originalidade(qs)['disponivel'] is False

    monkeypatch.setenv('BRAVE_SEARCH_API_KEY', 'chave-de-teste')
    pedidos = []

    def falsa(frase, chave):
        pedidos.append(chave)
        return [("Exercícios", "Um fio condutor é atravessado por 48 C de carga eléctrica em 8 s. A intensidade da corrente é")]

    r = analise_prova.originalidade(qs, pesquisar=falsa)
    assert r['disponivel'] and 1 in r['ja_existem_na_internet'] and 2 not in r['ja_existem_na_internet']
    assert len(pedidos) <= 10


def test_importar_com_analise_devolve_relatorio_sem_guardar_texto(duas_escolas):
    import docx
    d = docx.Document()
    for linha in TEXTO.split("\n"):
        d.add_paragraph(linha)
    b = io.BytesIO(); d.save(b)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(c, 'admin.fa@sige.mz', 'PassFa123!')}")
    res = c.post('/api/v1/ferramentas/provas-anti-ia/codificar/', {
        'titulo': 'T', 'disciplina': 'Física', 'classe': '11ª', 'data_bloqueio_ia': '2026-11-30T23:59:00',
        'analisar': '1', 'ficheiro': SimpleUploadedFile('t.docx', b.getvalue())}, format='multipart')
    dados = res.json()['data']
    assert dados['analise']['dependencia_da_turma']['genericas'] == [1]
    assert ProvaBlindada.objects.get(id=dados['id']).questoes == []


def _prova(escola, criador=None, codigo='SIGE-AI-2026-ALERTA'):
    return ProvaBlindada.objects.create(
        escola=escola, criado_por=criador, titulo='P', disciplina='F', classe='11ª', codigo_autenticidade=codigo,
        data_bloqueio_ia=timezone.now() + timedelta(days=3), questoes=[], total_questoes=0, cotacao_total=20)


def test_alertas_entregues_uma_vez_e_so_a_quem_pertence(duas_escolas):
    a, b = duas_escolas
    admin = Usuario.objects.get(email='admin.fa@sige.mz')
    pa, pb = _prova(a, admin, 'PROVA-A'), _prova(b, None, 'PROVA-B')
    for p in (pa, pb):
        LogTentativaResolucaoIA.objects.create(prova=p, sistema_identificado='ChatGPT', bloqueado=True)

    c = APIClient()
    assert c.get('/api/v1/ferramentas/provas-anti-ia/alertas/').status_code == 401
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(c, 'admin.fa@sige.mz', 'PassFa123!')}")
    r1 = c.get('/api/v1/ferramentas/provas-anti-ia/alertas/').json()
    assert r1['total'] == 1 and r1['alertas'][0]['prova'] == 'PROVA-A' and r1['alertas'][0]['agente_ia'] is True
    assert c.get('/api/v1/ferramentas/provas-anti-ia/alertas/').json()['total'] == 0  # já foi entregue
