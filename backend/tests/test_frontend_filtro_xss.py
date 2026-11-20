"""Regressão: o filtro anti-XSS do frontend nunca pode entrar em recursão (bloqueou o login na v2.9.81)."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

JS = Path(__file__).resolve().parents[2] / 'frontend' / 'js' / 'seguranca-xss.js'


def test_parser_inerte_usa_o_setter_original_e_tem_trava_de_reentrada():
    codigo = JS.read_text(encoding='utf-8')
    assert 'setterOriginal.call(t, html)' in codigo          # nunca `t.innerHTML = html` (recursão infinita)
    assert not re.search(r"\bt\.innerHTML\s*=", codigo)
    assert 'emCurso' in codigo and 'catch' in codigo        # trava + fallback seguro


@pytest.mark.skipif(not shutil.which('node'), reason='node indisponível')
def test_filtro_executa_sem_estourar_a_pilha_e_limpa_html_perigoso():
    jsdom = Path(__file__).resolve().parents[2] / 'frontend' / 'node_modules' / 'jsdom'
    if not jsdom.exists():
        pytest.skip('jsdom indisponível')
    script = f"""
    const {{ JSDOM }} = require({str(jsdom).replace(chr(92), '/')!r});
    const dom = new JSDOM('<div id=a></div>', {{ runScripts: 'outside-only' }});
    dom.window.eval(require('fs').readFileSync({str(JS).replace(chr(92), '/')!r}, 'utf8'));
    const a = dom.window.document.getElementById('a');
    a.innerHTML = '<img src=x onerror=alert(1)><button onclick="f()">ok</button><script>1</script>';
    console.log(a.innerHTML);
    """
    r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert 'onerror' not in r.stdout and '<script' not in r.stdout and 'onclick' in r.stdout
