"""
O mapa de módulos por perfil do Assistente (apps/assistente/modulos.py) tem de acompanhar os menus reais do frontend
(MENUS_POR_PAINEL em frontend/js/app.js). Se um módulo for acrescentado a um painel e este mapa não for actualizado, o teste falha.
"""
import re
from pathlib import Path
import pytest
from apps.assistente.modulos import MODULOS_POR_PERFIL

APP_JS = Path(__file__).resolve().parents[2] / 'frontend' / 'js' / 'app.js'
# acrescentados por código depois da declaração dos menus (forEach em app.js)
EXTRAS_DINAMICOS = {'assistente', 'crm', 'assistente-relatorio'}


def _bloco(texto, inicio):
    i = texto.index(inicio)
    return texto[i:texto.index('\n};', i)]


@pytest.mark.skipif(not APP_JS.exists(), reason='frontend não está disponível neste ambiente')
def test_modulos_por_perfil_acompanham_os_menus_do_frontend():
    js = APP_JS.read_text(encoding='utf-8', errors='replace')
    menus_txt = _bloco(js, 'const MENUS_POR_PAINEL = {')
    paineis = {}
    for m in re.finditer(r"'(painel-[a-z]+)': \[(.*?)\n  \]", menus_txt, re.S):
        paineis[m.group(1)] = set(re.findall(r"\{ id: '([a-z0-9\-]+)'", m.group(2)))
    mapa_txt = _bloco(js, 'const MAPA_PAINEIS = {')
    mapa = dict(re.findall(r"(\w+): '(painel-[a-z]+)'", mapa_txt))
    assert set(mapa) == set(MODULOS_POR_PERFIL), 'perfis do frontend e do assistente diferem'
    for role, painel in mapa.items():
        estaticos = paineis[painel]
        assert estaticos, painel
        backend = MODULOS_POR_PERFIL[role]
        em_falta = estaticos - backend
        a_mais = backend - estaticos - EXTRAS_DINAMICOS
        assert not em_falta, f'{role}: módulos do menu em falta em modulos.py: {sorted(em_falta)}'
        assert not a_mais, f'{role}: modulos.py dá acesso a módulos que não estão no painel: {sorted(a_mais)}'
