"""Identificação do telefone de quem lê o código: validação do IMEI e imagem do modelo pesquisada na internet.

Os navegadores não deixam ler o IMEI por código (é uma protecção do Android/iOS), por isso ele é pedido à pessoa
(marcar *#06#) e validado aqui de forma rigorosa. Para a imagem só se envia à internet o nome do modelo, nada mais.
"""
import json
import re
import urllib.parse
import urllib.request

_API = 'https://commons.wikimedia.org/w/api.php'
_HOST_IMAGENS = 'upload.wikimedia.org'
_MAX_IMAGEM = 1024 * 1024
_TIMEOUT = 5


def limpar_imei(valor) -> str:
    """Só dígitos; aceita espaços, hífenes e barras que as pessoas copiam do ecrã."""
    return re.sub(r'[\s\-/.]', '', str(valor or ''))


def imei_valido(valor) -> bool:
    """15 dígitos com dígito de controlo de Luhn correcto e TAC que não seja só zeros."""
    imei = limpar_imei(valor)
    if not re.fullmatch(r'\d{15}', imei) or imei[:8] == '00000000' or len(set(imei)) == 1:
        return False
    total = 0
    for i, d in enumerate(reversed(imei)):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            n = n - 9 if n > 9 else n
        total += n
    return total % 10 == 0


_PREFIXOS_MARCA = (
    (r'SM-|GT-|SCH-', 'Samsung'), (r'Pixel', 'Google'), (r'iPhone', 'Apple'), (r'TECNO|Tecno', 'Tecno'),
    (r'itel|Itel', 'itel'), (r'Infinix|X6\d{3}', 'Infinix'), (r'Redmi|M\d{4}[A-Z]\d|POCO|Mi ', 'Xiaomi'),
    (r'CPH|RMX', 'Oppo/Realme'), (r'V\d{4}', 'vivo'), (r'HUAWEI|[A-Z]{3}-L\d\d', 'Huawei'), (r'moto|XT\d{4}', 'Motorola'),
)


def marca_do_modelo(modelo: str) -> str:
    for padrao, marca in _PREFIXOS_MARCA:
        if re.match(padrao, modelo):
            return marca
    return ''


def consulta_modelo(info: dict) -> str:
    """Texto de pesquisa a partir das referências do aparelho (marca + modelo), sem dados pessoais."""
    modelo = (info.get('modelo') or '').strip()
    if modelo.lower() in ('', 'telemóvel', 'telemovel'):
        return ''
    marca = (info.get('fabricante') or '').strip() or marca_do_modelo(modelo)
    return f'{marca} {modelo}'.strip() if marca and marca.lower() not in modelo.lower() else modelo


def pesquisar_imagem(consulta: str):
    """Procura na Wikimedia Commons a imagem do modelo. Devolve (bytes, url_da_fonte) ou (None, '')."""
    consulta = (consulta or '').strip()[:100]
    if not consulta:
        return None, ''
    try:
        params = urllib.parse.urlencode({
            'action': 'query', 'format': 'json', 'generator': 'search', 'gsrnamespace': 6, 'gsrlimit': 5,
            'gsrsearch': f'{consulta} smartphone', 'prop': 'imageinfo', 'iiprop': 'url|mime', 'iiurlwidth': 400})
        pedido = urllib.request.Request(f'{_API}?{params}', headers={'User-Agent': 'SIGE-Escudo/1.0'})
        with urllib.request.urlopen(pedido, timeout=_TIMEOUT) as r:  # noqa: S310 (URL fixo https)
            paginas = (json.loads(r.read(200000)).get('query') or {}).get('pages') or {}
        for pag in sorted(paginas.values(), key=lambda p: p.get('index', 99)):
            info = (pag.get('imageinfo') or [{}])[0]
            url = info.get('thumburl') or info.get('url') or ''
            if info.get('mime') not in ('image/jpeg', 'image/png') or urllib.parse.urlparse(url).hostname != _HOST_IMAGENS:
                continue
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'SIGE-Escudo/1.0'}), timeout=_TIMEOUT) as img:  # noqa: S310
                dados = img.read(_MAX_IMAGEM + 1)
            if dados[:3] == b'\xff\xd8\xff' or dados[:4] == b'\x89PNG':
                if len(dados) <= _MAX_IMAGEM:
                    return dados, (info.get('descriptionurl') or url)[:300]
    except Exception:  # sem internet ou serviço em baixo: o registo guarda-se na mesma, sem imagem
        pass
    return None, ''
