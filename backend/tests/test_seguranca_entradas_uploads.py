"""Segurança: uploads validados por conteúdo, entrega segura, sanitização de HTML em JSON e SQL parametrizado."""
import io
import json
import re
import zipfile
from pathlib import Path

import pytest
from django.test import RequestFactory

from common.middleware.sanitizar_entrada import SanitizarEntradaMiddleware, _limpar
from common.utils.uploads import (
    FicheiroInvalido, nome_seguro, resposta_ficheiro_segura, tipo_seguro_por_conteudo,
)

RAIZ = Path(__file__).resolve().parents[1]


def _docx():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('[Content_Types].xml', '<x/>')
        z.writestr('word/document.xml', '<x/>')
    return buf.getvalue()


def test_pdf_valido_aceite_e_mime_decidido_pelo_servidor():
    assert tipo_seguro_por_conteudo(b'%PDF-1.7 abc', 'pdf') == 'application/pdf'


@pytest.mark.parametrize('dados,ext', [
    (b'<html><script>alert(1)</script></html>', 'pdf'),   # HTML disfarçado de PDF
    (b'<svg onload=alert(1)>', 'png'),
    (b'<html><body>x</body></html>', 'txt'),
    (b'<script>alert(1)</script>', 'csv'),
    (b'PK\x03\x04lixo', 'docx'),
    (b'x', 'html'), (b'x', 'svg'), (b'x', 'js'), (b'x', 'exe'),
])
def test_ficheiros_perigosos_rejeitados(dados, ext):
    with pytest.raises(FicheiroInvalido):
        tipo_seguro_por_conteudo(dados, ext)


def test_docx_real_aceite():
    assert tipo_seguro_por_conteudo(_docx(), 'docx').endswith('wordprocessingml.document')


def test_entrega_nunca_serve_html_nem_confia_no_mime_do_cliente():
    resp = resposta_ficheiro_segura(b'<html><script>alert(1)</script></html>', 'x.html', 'text/html')
    assert resp['Content-Type'] == 'application/octet-stream'
    assert resp['Content-Disposition'].startswith('attachment')
    assert resp['X-Content-Type-Options'] == 'nosniff'
    assert 'sandbox' in resp['Content-Security-Policy']


def test_nome_seguro_remove_aspas_e_quebras_de_linha():
    n = nome_seguro('a"; filename=x\r\nSet-Cookie: z.pdf')
    assert '"' not in n and '\r' not in n and '\n' not in n and ';' not in n


def test_json_html_e_neutralizado_mas_texto_normal_fica():
    sujo = {'nome': '<img src=x onerror=alert(1)>', 'obs': 'nota < 10', 'link': 'JavaScript:alert(1)',
            'conteudo_base64': 'PGh0bWw+', 'lista': ['<script>x</script>']}
    limpo = _limpar(sujo)
    assert '<' not in limpo['nome'] and '&lt;img' in limpo['nome']
    assert limpo['obs'] == 'nota < 10'
    assert 'javascript:' not in limpo['link'].lower()
    assert limpo['conteudo_base64'] == 'PGh0bWw+'
    assert '<' not in limpo['lista'][0]


def test_middleware_reescreve_corpo_json():
    capturado = {}

    def resposta(request):
        capturado['corpo'] = json.loads(request.body)
        from django.http import HttpResponse
        return HttpResponse('ok')

    req = RequestFactory().post('/api/v1/alunos/', data=json.dumps({'nome': '<b onmouseover=1>x</b>'}),
                                content_type='application/json')
    SanitizarEntradaMiddleware(resposta)(req)
    assert '<' not in capturado['corpo']['nome']


def test_middleware_json_invalido_da_400():
    from django.http import HttpResponse
    req = RequestFactory().post('/api/v1/alunos/', data='{mau', content_type='application/json')
    assert SanitizarEntradaMiddleware(lambda r: HttpResponse('ok'))(req).status_code == 400


def test_nginx_redirect_http_usa_dominio_fixo_e_ha_limites():
    conf = (RAIZ.parent / 'frontend' / 'nginx.conf').read_text(encoding='utf-8')
    assert 'return 301 https://$host' not in conf          # open redirect por Host
    assert 'limit_req_zone' in conf and 'limit_conn_zone' in conf


def test_sem_sql_por_concatenacao_nas_apps():
    """Todo cursor.execute / .raw / .extra deve usar parâmetros (%s) e nunca f-strings ou % / .format."""
    padrao = re.compile(r'(\.execute|\.raw|\.extra)\(\s*(f["\']|["\'][^"\']*["\']\s*(%|\.format\())')
    ofensas = []
    for ficheiro in (RAIZ / 'apps').rglob('*.py'):
        if 'migrations' in ficheiro.parts:
            continue
        for n, linha in enumerate(ficheiro.read_text(encoding='utf-8', errors='ignore').splitlines(), 1):
            if padrao.search(linha):
                ofensas.append(f'{ficheiro.name}:{n}')
    assert not ofensas, ofensas
