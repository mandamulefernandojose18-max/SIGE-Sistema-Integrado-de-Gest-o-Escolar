"""
SIGE — Folha de Resposta Personalizada (grelha de respostas de escolha múltipla).

Gera, em PDF (ReportLab, vectorial) ou Excel (openpyxl), folhas de resposta já preenchidas com os dados
reais do sistema: escola, logótipo/emblema, código da escola, ano lectivo, aluno (apelido, nome, classe,
turma, número, código de matrícula + código de barras Code128 + QR), disciplina e tipo de avaliação.

Parâmetros configuráveis: nº de perguntas, nº de alternativas, cotação (uniforme ou por secções),
duração, data, versões A/B/C… rotativas por aluno (anti-cópia), chave de correcção (gabarito) e marcas
de registo (OMR) nos quatro cantos para digitalização/leitura óptica.

O módulo não toca na base de dados: recebe dicionários simples (ver `montar_dados_escola` / `montar_dados_aluno`).
Nunca inventa alunos: sem alunos reais não há folha personalizada (apenas folhas em branco explícitas).
"""
import base64
import datetime
import hashlib
import hmac
import io
import json
import math
import re

from django.conf import settings
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import code128
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as rl_canvas

from .pdf_service import resolver_logo_documento_escola

# --------------------------------------------------------------------------------------
# Constantes e configuração
# --------------------------------------------------------------------------------------
LETRAS = 'ABCDEF'
MAX_PERGUNTAS = 100   # a folha cabe sempre numa única página A4
MAX_FOLHAS = 2000
MAX_FOLHAS_BRANCO = 500

TIPOS_AVALIACAO = [
    ('ACS1', '1ª ACS'),
    ('ACS2', '2ª ACS'),
    ('ACS3', '3ª ACS'),
    ('AT', 'AT'),
    ('EXAME', 'Exame Final'),
]
ROTULO_TIPO = dict(TIPOS_AVALIACAO)
ROTULO_TIPO_COMPLETO = {
    'ACS1': '1ª Avaliação de Carácter Sumativo (1ª ACS)',
    'ACS2': '2ª Avaliação de Carácter Sumativo (2ª ACS)',
    'ACS3': '3ª Avaliação de Carácter Sumativo (3ª ACS)',
    'AT': 'Avaliação Trimestral (AT)',
    'EXAME': 'Exame Final',
}

# Cores de alto contraste para impressão (letras bem visíveis e carregadas,
# mesmo em impressoras laser/jato de tinta em modo económico ou monocromático).
AZUL = colors.HexColor('#0a1f40')
CINZA_FUNDO = colors.HexColor('#e6e9ee')
CINZA_LINHA = colors.HexColor('#3a4250')
CINZA_TEXTO = colors.HexColor('#000000')
PRETO = colors.HexColor('#000000')

FONTE = 'Times-Roman'
FONTE_B = 'Times-Bold'
FONTE_I = 'Times-Italic'

# Geometria (mm, medidos a partir do topo da página A4)
PAG_L, PAG_A = 210.0, 297.0
MARGEM = 12.0
LARG_UTIL = PAG_L - 2 * MARGEM
Y_GRELHA_1 = 152.8          # início da grelha (página única)
Y_GRELHA_CONT = 30.0        # início da grelha nas páginas de continuação
Y_FIM_GRELHA = 283.0
ALTURA_LINHA_MIN = 4.2
DESLOC_VIGILANTES = 10.0    # altura extra (mm) para os Professores Vigilantes, só no Exame Final
FOLGA_GRUPO = 1.4
ALTURA_CABECALHO_GRELHA = 6.0


class ConfigFolhaInvalida(ValueError):
    """Parâmetros da folha de resposta inválidos (mensagem pronta a mostrar ao utilizador)."""


def _num(valor, nome, minimo, maximo, padrao=None, inteiro=False):
    if valor in (None, ''):
        if padrao is None:
            raise ConfigFolhaInvalida(f'Indique {nome}.')
        return padrao
    try:
        n = float(str(valor).replace(',', '.'))
    except (TypeError, ValueError):
        raise ConfigFolhaInvalida(f'{nome.capitalize()} inválido(a).')
    if math.isnan(n) or math.isinf(n) or n < minimo or n > maximo:
        raise ConfigFolhaInvalida(f'{nome.capitalize()} deve estar entre {minimo:g} e {maximo:g}.')
    return int(n) if inteiro else n


def _texto(valor, limite=120):
    return re.sub(r'\s+', ' ', str(valor or '')).strip()[:limite]


def _normalizar_gabarito(bruto, n_perguntas, n_alternativas, versao):
    letras_ok = LETRAS[:n_alternativas]
    limpo = re.sub(r'[\s,;.\-|/]+', '', str(bruto or '')).upper()
    if not limpo:
        return None
    invalidas = sorted({ch for ch in limpo if ch not in letras_ok})
    if invalidas:
        raise ConfigFolhaInvalida(
            f"Chave da versão {versao}: letras inválidas ({', '.join(invalidas)}); use apenas {', '.join(letras_ok)}."
        )
    if len(limpo) != n_perguntas:
        raise ConfigFolhaInvalida(
            f'Chave da versão {versao}: tem {len(limpo)} respostas mas a prova tem {n_perguntas} perguntas.'
        )
    return limpo


def formatar_valor(v):
    """Formata cotações/notas à portuguesa (vírgula decimal, sem zeros inúteis)."""
    v = round(float(v) + 1e-9, 2)
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return f'{v:.2f}'.rstrip('0').rstrip('.').replace('.', ',')


def _hora_valida(valor):
    m = re.fullmatch(r'\s*(\d{1,2}):(\d{2})\s*', str(valor or ''))
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        return ''
    return f'{int(m.group(1)):02d}:{m.group(2)}'


def somar_minutos(hora, minutos):
    """«07:30» + 90 → «09:00» (volta às 00:00 depois da meia-noite)."""
    h = _hora_valida(hora)
    if not h or not minutos:
        return ''
    total = (int(h[:2]) * 60 + int(h[3:]) + int(minutos)) % (24 * 60)
    return f'{total // 60:02d}:{total % 60:02d}'


def normalizar_config(dados, escola=None):
    """Valida e completa a configuração vinda do frontend. Levanta ConfigFolhaInvalida."""
    dados = dados or {}
    tipo = str(dados.get('tipo_avaliacao') or 'ACS1').upper()
    if tipo not in ROTULO_TIPO:
        raise ConfigFolhaInvalida('Tipo de avaliação inválido.')
    disciplina = _texto(dados.get('disciplina'), 80)
    if not disciplina:
        raise ConfigFolhaInvalida('Escolha a disciplina.')

    n_perg = _num(dados.get('n_perguntas'), 'o número de perguntas', 1, MAX_PERGUNTAS, inteiro=True, padrao=None)
    n_alt = _num(dados.get('n_alternativas'), 'o número de alternativas', 2, 6, padrao=4, inteiro=True)

    # Cotação: uniforme (cotacao_pergunta) ou por secções [{"ate": 20, "cotacao": 0.5}, ...]
    seccoes_in = dados.get('seccoes') or []
    cotacoes = []
    seccoes = []
    if seccoes_in:
        if not isinstance(seccoes_in, list) or len(seccoes_in) > 12:
            raise ConfigFolhaInvalida('Secções de cotação inválidas (máximo 12).')
        inicio = 1
        for s in seccoes_in:
            if inicio > n_perg:  # secção a mais (sobrou de um nº de perguntas maior): já está tudo coberto, ignora-se
                break
            ate =_num((s or {}).get('ate'), 'o limite da secção', inicio, n_perg, inteiro=True)
            cot = _num((s or {}).get('cotacao'), 'a cotação da secção', 0, 100)
            seccoes.append({'de': inicio, 'ate': ate, 'cotacao': cot})
            cotacoes.extend([cot] * (ate - inicio + 1))
            inicio = ate + 1
        if inicio <= n_perg:
            raise ConfigFolhaInvalida(f'As secções de cotação terminam na pergunta {inicio - 1}; faltam até à {n_perg}.')
    else:
        cot = dados.get('cotacao_pergunta')
        cot = 20 / n_perg if cot in (None, '') else _num(cot, 'a cotação por pergunta', 0, 100)
        cotacoes = [cot] * n_perg
        seccoes = [{'de': 1, 'ate': n_perg, 'cotacao': cot}]
    cotacao_mc = round(sum(cotacoes), 2)

    # Partes de resolução livre (perguntas abertas / demonstração): não têm alternativas na grelha,
    # mas a sua cotação conta no total e aparece na folha. [{"rotulo": "Parte B", "n": 2, "cotacao": 3}]
    abertas = []
    ab_in = dados.get('abertas') or []
    if ab_in:
        if not isinstance(ab_in, list) or len(ab_in) > 6:
            raise ConfigFolhaInvalida('Partes de perguntas abertas inválidas (máximo 6).')
        for k, a in enumerate(ab_in, start=1):
            a = a or {}
            n_ab = _num(a.get('n'), 'o número de perguntas abertas', 1, 50, inteiro=True)
            cot_ab = _num(a.get('cotacao'), 'a cotação das perguntas abertas', 0, 100)
            abertas.append({'rotulo': _texto(a.get('rotulo'), 40) or f'Parte {k} (perguntas abertas)',
                            'n': n_ab, 'cotacao': cot_ab, 'total': round(n_ab * cot_ab, 2)})
    total = round(cotacao_mc + sum(a['total'] for a in abertas), 2)

    duracao = _num(dados.get('duracao_min'), 'a duração', 0, 600, padrao=0, inteiro=True)

    versoes = [v for v in re.split(r'[\s,;]+', str(dados.get('versoes') or '').upper()) if v]
    versoes = [v[:2] for v in versoes if re.fullmatch(r'[A-Z0-9]{1,2}', v[:2])][:6]
    versoes = list(dict.fromkeys(versoes)) or ['']
    if not versoes[0] and dados.get('versao'):
        versoes = [_texto(dados.get('versao'), 2).upper()]

    gabaritos = {}
    gb_in = dados.get('gabaritos') if isinstance(dados.get('gabaritos'), dict) else {}
    if dados.get('gabarito'):
        gb_in = {**gb_in, (versoes[0] or '-'): dados.get('gabarito')}
    for v, bruto in gb_in.items():
        chave_v = str(v).upper() or '-'
        if versoes != [''] and chave_v != '-' and chave_v not in versoes:
            continue
        g = _normalizar_gabarito(bruto, n_perg, n_alt, chave_v)
        if g:
            gabaritos[chave_v] = g

    trimestre = _texto(dados.get('trimestre'), 12)
    if not trimestre and escola and tipo != 'EXAME':
        t = str(escola.get('trimestre') or '')
        trimestre = {'1_TRIMESTRE': '1.º Trimestre', '2_TRIMESTRE': '2.º Trimestre',
                     '3_TRIMESTRE': '3.º Trimestre'}.get(t, '')

    return {
        'tipo': tipo,
        'tipo_rotulo': ROTULO_TIPO[tipo],
        'disciplina': disciplina,
        'n_perguntas': n_perg,
        'n_alternativas': n_alt,
        'cotacoes': cotacoes,
        'seccoes': seccoes,
        'cotacao_total': total,
        'cotacao_mc': cotacao_mc,
        'abertas': abertas,
        'duracao_min': duracao,
        'data': _texto(dados.get('data'), 20),
        'hora_inicio': _hora_valida(dados.get('hora_inicio')),
        'hora_fim': _hora_valida(dados.get('hora_fim')) or somar_minutos(dados.get('hora_inicio'), duracao),
        'sala': _texto(dados.get('sala'), 20),
        'professor': _texto(dados.get('professor'), 80),
        'trimestre': trimestre,
        'versoes': versoes,
        'gabaritos': gabaritos,
        'incluir_chave': bool(dados.get('incluir_chave', True)) and bool(gabaritos),
        'disciplinas_classe': [_texto(d, 40) for d in (dados.get('disciplinas_classe') or []) if _texto(d, 40)][:15],
        'marcas_omr': bool(dados.get('marcas_omr', True)),
        'codigo_barras': bool(dados.get('codigo_barras', True)),
        'instrucao_extra': _texto(dados.get('instrucao_extra'), 140),
        # logotipo próprio da escola (opcional); nunca no Exame Final
        'logo_escola': bool(dados.get('logo_escola', False)) and tipo != 'EXAME',
    }


def montar_dados_escola(escola):
    """Dados reais da escola (modelo `Escola`) num dicionário simples."""
    return {
        'id': str(escola.id),
        'nome': escola.nome or '',
        'codigo': escola.codigo_escola or '',
        'provincia': escola.provincia or '',
        'distrito': escola.distrito or '',
        'ano_letivo': escola.ano_letivo_ativo or '',
        'trimestre': escola.trimestre_ativo or '',
        'obj': escola,
    }


def logo_proprio_escola(escola):
    """Bytes do logotipo próprio da escola (o carregado nas Configurações), ou None se não existir."""
    from .pdf_service import extrair_bytes_de_imagem
    obj = escola.get('obj') if isinstance(escola, dict) else escola
    for campo in ('logo_url', 'logo_base64', 'logo'):
        ref = getattr(obj, campo, None) if obj is not None else None
        if ref:
            try:
                dados = extrair_bytes_de_imagem(ref)
            except Exception:
                dados = None
            if dados:
                return dados
    return None


SECCOES_ESPECIFICAS = {
    'cg': 'Ciências com Geografia', 'cb': 'Ciências com Biologia', 'cd': 'Ciências com Desenho',
    'lg': 'Letras com Geografia', 'lh': 'Letras com História',
}
_GENERICAS = {'', 'geral', 'ensino geral', 'tronco comum', 'eg', 'none', 'null', 'ciências', 'ciencias', 'letras',
              'ciências e letras', 'ciencias e letras'}


def nome_area_secao(aluno):
    """
    Nome específico da Área/Secção do aluno («Ciências com Geografia», «Letras com História»…).
    Prioridade: área específica do aluno → da turma → sigla no código do aluno (…2026.cg.02) → valor genérico.
    """
    candidatos = [getattr(aluno, 'area', None) or '']
    turma = getattr(aluno, 'turma', None) if getattr(aluno, 'turma_id', None) else None
    if turma is not None:
        candidatos.append(getattr(turma, 'area', None) or '')
    for c in candidatos:
        v = str(c).strip()
        if v and v.lower() not in _GENERICAS:
            return v
    for parte in str(getattr(aluno, 'matricula', '') or '').lower().split('.'):
        if parte in SECCOES_ESPECIFICAS:
            return SECCOES_ESPECIFICAS[parte]
    for c in candidatos:
        v = str(c).strip()
        if v and v.lower() not in ('geral', 'ensino geral', 'tronco comum', 'eg', 'none', 'null'):
            return v
    return 'Ensino Geral'


def montar_dados_aluno(aluno, numero, classe=None, turma=None):
    return {
        'apelido': (aluno.apelido or '').strip(),
        'nome': (aluno.nome or '').strip(),
        'classe': classe or (aluno.turma.grau_ano if aluno.turma_id else (aluno.classe or '')),
        'turma': turma or (aluno.turma.nome if aluno.turma_id else ''),
        'area': nome_area_secao(aluno),
        'numero': numero,
        'codigo': (aluno.matricula or '').strip(),
        'genero': (getattr(aluno, 'genero', '') or '').strip(),
    }


def rotulos_correccao(config):
    """«CORRECÇÃO NORMAL»/«RECORRECÇÃO»; no Exame Final: «1ª CORRECÇÃO»/«2ª CORRECÇÃO» (tudo em maiúsculas)."""
    if config.get('tipo') == 'EXAME':
        return '1ª CORRECÇÃO', '2ª CORRECÇÃO'
    return 'CORRECÇÃO NORMAL', 'RECORRECÇÃO'


def texto_hora_sala(config):
    intervalo = ' – '.join(x for x in (config['hora_inicio'], config['hora_fim']) if x)
    sala = config['sala']
    if sala and not re.match(r'(?i)^\s*sala\b', sala):
        sala = f'Sala: {sala}'
    return ' · '.join(x for x in (intervalo, sala) if x)


def versao_do_aluno(config, indice):
    vs = config['versoes']
    return vs[indice % len(vs)] if vs and vs[0] else ''


def codigo_folha(escola, aluno, config, ano):
    """Código curto e estável da folha (rastreável, não secreto)."""
    base = f"{escola.get('codigo')}|{(aluno or {}).get('codigo','-')}|{config['tipo']}|{config['disciplina']}|{ano}"
    return 'FR-' + hashlib.sha1(base.encode('utf-8')).hexdigest()[:10].upper()


DOMINIO_OFICIAL = 'https://sigesaas.duckdns.org'


def _b64(raw):
    return base64.urlsafe_b64encode(raw).decode('ascii').rstrip('=')


def _unb64(txt):
    return base64.urlsafe_b64decode(txt + '=' * (-len(txt) % 4))


def _assinatura(token):
    return hmac.new(settings.SECRET_KEY.encode('utf-8'), token.encode('ascii'), hashlib.sha256).hexdigest()[:16]


def gerar_token_verificacao(escola, aluno, config, ano, versao):
    """Token assinado (HMAC) com os dados mínimos da folha; não exige guardar nada na base de dados."""
    al = aluno or {}
    dados = {'e': str(escola.get('id') or ''), 'a': al.get('codigo') or '', 't': config['tipo'],
             'd': config['disciplina'], 'y': str(ano), 'v': versao or '', 'n': config['n_perguntas']}
    token = _b64(json.dumps(dados, separators=(',', ':'), ensure_ascii=False).encode('utf-8'))
    return token, _assinatura(token)


def validar_token_verificacao(token, assinatura):
    """Devolve os dados da folha se a assinatura for autêntica; caso contrário None."""
    try:
        if not token or not assinatura or len(token) > 2000:
            return None
        if not hmac.compare_digest(_assinatura(token), str(assinatura)):
            return None
        dados = json.loads(_unb64(token).decode('utf-8'))
        return dados if isinstance(dados, dict) else None
    except Exception:
        return None


def _payload_qr(escola, aluno, config, ano, versao):
    """O QR abre a página oficial de verificação da folha (domínio do SIGE)."""
    token, sig = gerar_token_verificacao(escola, aluno, config, ano, versao)
    return f'{DOMINIO_OFICIAL}/verificar-folha.html?d={token}&s={sig}'


# --------------------------------------------------------------------------------------
# Layout da grelha (comum a PDF e Excel)
# --------------------------------------------------------------------------------------
def capacidade_linhas(altura_disponivel_mm):
    """Máximo de linhas que cabem numa coluna da grelha com a altura disponível."""
    r = 0
    while ALTURA_CABECALHO_GRELHA + (r + 1) * ALTURA_LINHA_MIN + (r // 5) * FOLGA_GRUPO <= altura_disponivel_mm:
        r += 1
    return max(r, 5)


def layout_grelha(n, capacidade):
    """Devolve (colunas, linhas_por_coluna) para n perguntas dado o máximo de linhas por coluna."""
    cols = 2 if n <= 40 else 3 if n <= 75 else 4
    linhas = math.ceil(n / cols)
    linhas = math.ceil(linhas / 5) * 5
    if linhas > capacidade:
        cols, linhas = 4, capacidade
    return cols, linhas


def paginas_grelha(n, desloc=0.0):
    """A folha cabe SEMPRE numa só página: [(inicio0, fim0_exclusivo, colunas, linhas, y_inicio_mm)]."""
    cap = capacidade_linhas(Y_FIM_GRELHA - Y_GRELHA_1 - desloc)
    cols, linhas = layout_grelha(n, cap)
    return [(0, n, cols, linhas, Y_GRELHA_1 + desloc)]


def _agora_texto():
    """Data e hora da emissão: dd/mm/aaaa HH:MM:SS (hora local configurada)."""
    from django.utils import timezone
    return timezone.localtime().strftime('%d/%m/%Y %H:%M:%S')


# --------------------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------------------
def _y(v_mm):
    return (PAG_A - v_mm) * mm


def _texto_ajustado(c, txt, x_mm, y_mm, larg_mm, fonte=FONTE, tam=9.0, tam_min=5.5, alinh='l'):
    txt = str(txt or '')
    t = tam
    while t > tam_min and stringWidth(txt, fonte, t) > larg_mm * mm:
        t -= 0.25
    while len(txt) > 1 and stringWidth(txt, fonte, t) > larg_mm * mm:
        txt = txt[:-1]
    c.setFont(fonte, t)
    # Letras "carregadas": contorno fino da mesma cor do preenchimento (impressão bem visível)
    c.saveState()
    try:
        c.setStrokeColor(c._fillColorObj)
        c.setLineWidth(0.22)
        txo = c.beginText()
        txo.setTextRenderMode(2)
        txo.setFont(fonte, t)
        if alinh == 'c':
            xx = (x_mm + larg_mm / 2) * mm - stringWidth(txt, fonte, t) / 2
        elif alinh == 'r':
            xx = (x_mm + larg_mm) * mm - stringWidth(txt, fonte, t)
        else:
            xx = x_mm * mm
        txo.setTextOrigin(xx, _y(y_mm))
        txo.textOut(txt)
        c.drawText(txo)
    finally:
        c.restoreState()


def _barra_titulo(c, x, y, w, h, titulo, alinh='l', tam=10.5):
    c.setFillColor(AZUL)
    c.rect(x * mm, _y(y + h), w * mm, h * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    _texto_ajustado(c, titulo, x + 2, y + h - 1.5, w - 4, FONTE_B, tam, 5.5, alinh)
    c.setFillColor(PRETO)


def _caixa(c, x, y, w, h, titulo=None, barra=5.2):
    c.setStrokeColor(AZUL)
    c.setLineWidth(0.9)
    c.rect(x * mm, _y(y + h), w * mm, h * mm, stroke=1, fill=0)
    if titulo:
        _barra_titulo(c, x, y, w, barra, titulo)
    c.setStrokeColor(PRETO)


def _campo(c, x, y, w, rotulo, valor, tam=13.0, tam_rot=8.2):
    """Campo com rótulo pequeno e valor sobre linha (preenchido automaticamente)."""
    c.setFillColor(CINZA_TEXTO)
    t_r = tam_rot
    while t_r > 6.0 and c.stringWidth(rotulo, FONTE_B, t_r) > (w + 1.5) * mm:
        t_r -= 0.2
    c.setFont(FONTE_B, t_r)
    c.drawString(x * mm, _y(y + 2.4), rotulo)
    c.setStrokeColor(CINZA_LINHA)
    c.setLineWidth(0.4)
    c.line(x * mm, _y(y + 7.4), (x + w) * mm, _y(y + 7.4))
    c.setFillColor(PRETO)
    if valor:
        _texto_ajustado(c, valor, x + 0.6, y + 6.4, w - 1.2, FONTE_B, tam, 7.5)


def _check(c, x, y, rotulo, marcado, tam=7.5, lado=3.0, larg_txt=None):
    c.setStrokeColor(PRETO)
    c.setLineWidth(0.6)
    c.rect(x * mm, _y(y + lado), lado * mm, lado * mm, stroke=1, fill=1 if marcado else 0)
    if marcado:
        c.setFillColor(AZUL)
        c.rect(x * mm, _y(y + lado), lado * mm, lado * mm, stroke=1, fill=1)
        c.setFillColor(colors.white)
        c.setStrokeColor(colors.white)
        c.setLineWidth(0.9)
        c.line((x + 0.6) * mm, _y(y + 1.6), (x + 1.3) * mm, _y(y + 2.3))
        c.line((x + 1.3) * mm, _y(y + 2.3), (x + 2.4) * mm, _y(y + 0.7))
        c.setStrokeColor(PRETO)
    c.setFillColor(PRETO)
    if larg_txt:
        _texto_ajustado(c, rotulo, x + lado + 1.2, y + lado - 0.4, larg_txt, FONTE_B if marcado else FONTE, tam, 5)
    else:
        c.setFont(FONTE_B if marcado else FONTE, tam)
        c.drawString((x + lado + 1.2) * mm, _y(y + lado - 0.4), rotulo)


def _bolha(c, cx_mm, cy_mm, larg_mm, alt_mm, letra, preenchida=False, tam_letra=10.5, riscada=False):
    """
    Alternativa: a letra com o «quadradinho» (rectângulo achatado) a cortá-la ao meio.
    A resposta marca-se pintando/riscando o quadradinho (preenchida/riscada = quadradinho a preto).
    """
    c.setFillColor(PRETO)
    c.setFont(FONTE, tam_letra)
    c.drawCentredString(cx_mm * mm, _y(cy_mm) - tam_letra * 0.37, letra)
    cheio = bool(preenchida or riscada)
    c.setLineWidth(0.6)
    c.setStrokeColor(PRETO)
    c.setFillColor(PRETO)
    c.rect((cx_mm - larg_mm / 2) * mm, _y(cy_mm + alt_mm / 2), larg_mm * mm, alt_mm * mm,
           stroke=1, fill=1 if cheio else 0)
    c.setFillColor(PRETO)


def _desenhar_marcas_omr(c):
    c.setFillColor(PRETO)
    lado = 4.5
    for x, y in ((5.5, 5.5), (PAG_L - 5.5 - lado, 5.5), (5.5, PAG_A - 5.5 - lado), (PAG_L - 5.5 - lado, PAG_A - 5.5 - lado)):
        c.rect(x * mm, _y(y + lado), lado * mm, lado * mm, stroke=0, fill=1)


def _desenhar_codigo_barras(c, valor, x, y, larg, alt):
    if not valor:
        return
    b = code128.Code128(valor, barWidth=0.5, barHeight=alt * mm, humanReadable=False, quiet=False)
    modulos = b.width / 0.5
    bw = (larg * mm) / modulos
    b = code128.Code128(valor, barWidth=bw, barHeight=alt * mm, humanReadable=False, quiet=False)
    b.drawOn(c, x * mm, _y(y + alt))
    c.setFont('Courier', 6.2)
    c.setFillColor(PRETO)
    c.drawCentredString((x + larg / 2) * mm, _y(y + alt + 2.6), valor)


def _desenhar_qr(c, dados, x, y, lado):
    w = QrCodeWidget(dados, barLevel='M')
    x0, y0, x1, y1 = w.getBounds()
    d = Drawing(lado * mm, lado * mm, transform=[lado * mm / (x1 - x0), 0, 0, lado * mm / (y1 - y0), 0, 0])
    d.add(w)
    renderPDF.draw(d, c, x * mm, _y(y + lado))


def _cabecalho_institucional(c, escola, logo_reader, ano, compacto=False, qr=None):
    y0 = 8.0
    if logo_reader is not None:
        try:
            c.drawImage(logo_reader, (MARGEM + 3) * mm, _y(y0 + 18), 15 * mm, 15 * mm, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
    c.setFillColor(PRETO)
    # Esquerda: República / Província / Distrito
    _texto_ajustado(c, 'REPÚBLICA DE MOÇAMBIQUE', 36, y0 + 5, 68, FONTE_B, 12)
    if escola.get('provincia'):
        _texto_ajustado(c, f"Província de {escola['provincia']}", 36, y0 + 10.5, 68, FONTE, 11)
    if escola.get('distrito'):
        _texto_ajustado(c, f"Distrito de {escola['distrito']}", 36, y0 + 15.5, 68, FONTE, 11)
    _texto_ajustado(c, 'Sector Pedagógico', 36, y0 + 20.5, 68, FONTE_I, 11)
    # Direita: escola
    c.setStrokeColor(CINZA_LINHA)
    c.setLineWidth(0.4)
    c.line(107 * mm, _y(y0 + 1), 107 * mm, _y(y0 + 22))
    x_esc = 110
    logo_esc = escola.get('_logo_proprio')
    if logo_esc is not None:
        try:
            c.drawImage(logo_esc, 110 * mm, _y(y0 + 18), 15 * mm, 15 * mm, preserveAspectRatio=True, mask='auto')
            x_esc = 127
        except Exception:
            pass
    larg_esc = PAG_L - MARGEM - x_esc - (23 if qr else 0)   # com QR: o texto da escola pára antes dele
    _texto_ajustado(c, escola.get('nome') or '', x_esc, y0 + 5, larg_esc, FONTE_B, 13, 8)
    if escola.get('codigo'):
        _texto_ajustado(c, f"Código da escola: {escola['codigo']}", x_esc, y0 + 11, larg_esc, FONTE, 11)
    _texto_ajustado(c, f'Ano lectivo: {ano}', x_esc, y0 + 16.5, larg_esc, FONTE_B, 11)
    if qr:
        _desenhar_qr(c, qr, PAG_L - MARGEM - 21, y0 + 1, 20)


def _bloco_instrucoes(c, y, extra=''):
    """Caixa «INSTRUÇÕES GERAIS» com o exemplo de marcação (letra D na questão 1)."""
    h = 23.8
    c.setFillColor(colors.white)
    c.setStrokeColor(AZUL)
    c.setLineWidth(0.9)
    c.rect(MARGEM * mm, _y(y + h), LARG_UTIL * mm, h * mm, stroke=1, fill=1)
    c.setFillColor(PRETO)
    c.setFont(FONTE_B, 10.5)
    c.drawCentredString((PAG_L / 2) * mm, _y(y + 4.2), 'INSTRUÇÕES GERAIS')
    itens = [
        '1. Não dobre nem rasure esta folha de respostas.',
        '2. Todas as questões devem ser respondidas com caneta azul ou preta.',
        '3. Responda apenas a quantidade de questões relativa à sua prova.',
        '4. Marque apenas uma resposta por pergunta, pintando o quadradinho da alternativa escolhida, conforme o modelo abaixo.',
    ]
    for i, txt in enumerate(itens):
        _texto_ajustado(c, txt, MARGEM + 3, y + 8.3 + i * 3.45, LARG_UTIL - 6, FONTE_B if i == 3 else FONTE, 10.2, 6)
    # exemplo: marcação da letra D na questão número 1
    ex_y = y + 21.0
    c.setFont(FONTE_B, 9)
    c.drawString((MARGEM + 3) * mm, _y(ex_y + 1.0), 'Exemplo:')
    for i, letra in enumerate('ABCD'):
        _bolha(c, MARGEM + 22 + i * 11, ex_y, 7.6, 1.6, letra, riscada=(letra == 'D'), tam_letra=10.5)
    c.setFont(FONTE, 9)
    c.drawString((MARGEM + 63) * mm, _y(ex_y + 1.0), extra or '')
    c.setStrokeColor(PRETO)


def _descricao_cotacao(config):
    partes = []
    for s in config['seccoes']:
        intervalo = f"{s['de']}" if s['de'] == s['ate'] else f"{s['de']}–{s['ate']}"
        partes.append(f"{intervalo} × {formatar_valor(s['cotacao'])}")
    partes = partes[:6]
    for a in config.get('abertas') or []:
        partes.append(f"{a['rotulo']}: {a['n']} × {formatar_valor(a['cotacao'])}")
    return '  |  '.join(partes) + f"   ·   Total: {formatar_valor(config['cotacao_total'])} val."


def _desenhar_grelha(c, config, inicio, fim, cols, linhas, y_ini, gabarito=None):
    """Desenha a grelha de bolhas das perguntas [inicio, fim) (índices a partir de 0)."""
    n_alt = config['n_alternativas']
    letras = LETRAS[:n_alt]
    largura_col = LARG_UTIL / cols
    altura_disp = Y_FIM_GRELHA - y_ini
    folgas = ((linhas - 1) // 5) * FOLGA_GRUPO
    altura_linha = min(6.4, (altura_disp - ALTURA_CABECALHO_GRELHA - folgas) / linhas)
    passo = min(13.0, (largura_col - 11.5) / n_alt)
    larg_alt = min(9.6, passo * 0.84)
    alt_alt = min(1.9, altura_linha * 0.36)
    tam_letra = max(10.0, min(13.0, altura_linha * 2.4))
    total_q = fim - inicio
    cols_usadas = math.ceil(total_q / linhas)
    for col in range(cols_usadas):
        x0 = MARGEM + col * largura_col
        if col > 0:
            x0 += 0  # colunas contíguas; a separação é feita pelo fundo e por traços finos
        # cabeçalho da coluna
        c.setFillColor(AZUL)
        c.rect((x0 + 0.5) * mm, _y(y_ini + ALTURA_CABECALHO_GRELHA - 0.8), (largura_col - 1) * mm,
               (ALTURA_CABECALHO_GRELHA - 1.2) * mm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont(FONTE_B, 11)
        c.drawString((x0 + 1.6) * mm, _y(y_ini + 4.2), 'Perg.')
        for i, letra in enumerate(letras):
            cx = x0 + 10.2 + passo * i + passo / 2 - 0.6
            c.drawCentredString(cx * mm, _y(y_ini + 4.2), letra)
        c.setFillColor(PRETO)
        for r in range(linhas):
            q = inicio + col * linhas + r
            if q >= fim:
                break
            y_lin = y_ini + ALTURA_CABECALHO_GRELHA + r * altura_linha + (r // 5) * FOLGA_GRUPO
            if (r // 5) % 2 == 0:
                c.setFillColor(CINZA_FUNDO)
                c.rect((x0 + 0.5) * mm, _y(y_lin + altura_linha), (largura_col - 1) * mm, altura_linha * mm, stroke=0, fill=1)
                c.setFillColor(PRETO)
            # número da pergunta
            c.setFillColor(colors.white)
            c.setStrokeColor(PRETO)
            c.setLineWidth(0.5)
            c.roundRect((x0 + 1.4) * mm, _y(y_lin + altura_linha - 0.55), 7 * mm, (altura_linha - 1.1) * mm, 0.8 * mm,
                        stroke=1, fill=1)
            c.setFillColor(PRETO)
            c.setFont(FONTE_B, 10)
            c.drawCentredString((x0 + 4.9) * mm, _y(y_lin + altura_linha / 2 + 1.0), str(q + 1))
            cy = y_lin + altura_linha / 2
            for i, letra in enumerate(letras):
                cx = x0 + 10.2 + passo * i + passo / 2 - 0.6
                _bolha(c, cx, cy, larg_alt, alt_alt, letra, preenchida=bool(gabarito and gabarito[q] == letra), tam_letra=tam_letra)
    c.setFillColor(PRETO)
    c.setStrokeColor(PRETO)


def _rodape(c, cod_folha, pagina, total_paginas, hoje, ident=''):
    c.setFillColor(CINZA_TEXTO)
    c.setFont(FONTE, 8.2)
    # «Folha» + natureza da emissão (Turma X / Toda a Classe X · Disciplina · Ano)
    _texto_ajustado(c, f'SIGE · Folha de Respostas{" · " + ident if ident else ""} · Cód. {cod_folha}', MARGEM, 288.8, 112, FONTE, 8.2, 5.5)
    c.drawCentredString((PAG_L / 2) * mm, _y(288.8), f'Pág. {pagina}/{total_paginas}')
    c.drawRightString((PAG_L - MARGEM) * mm, _y(288.8), f'Emitida em {hoje}')
    c.setFillColor(PRETO)


def _classe_turma(aluno):
    """«10ª Classe · Turma A» do aluno (só o que existir)."""
    al = aluno or {}
    p = []
    if al.get('classe'):
        p.append(str(al['classe']))
    if al.get('turma'):
        p.append(f"Turma {al['turma']}")
    return ' · '.join(p)


def _titulo_prova(config, aluno=None):
    partes = ['FOLHA DE RESPOSTAS', config['tipo_rotulo']]
    if config['trimestre'] and config['tipo'] != 'EXAME':
        partes.append(config['trimestre'])
    partes.append(config['disciplina'])
    ct = _classe_turma(aluno)
    if ct:
        partes.append(ct)
    return '  ·  '.join(partes)


def _pagina_principal(c, escola, logo_reader, ano, aluno, config, versao, cod_folha, pag, total, hoje):
    if config['marcas_omr']:
        _desenhar_marcas_omr(c)
    _cabecalho_institucional(c, escola, logo_reader, ano, qr=_payload_qr(escola, aluno, config, ano, versao))
    vig = config['tipo'] == 'EXAME'
    d = DESLOC_VIGILANTES if vig else 0.0
    # barra de título
    _barra_titulo(c, MARGEM, 31, LARG_UTIL, 7, _titulo_prova(config, aluno), 'l', 12)
    if versao:
        c.setFillColor(colors.white)
        c.setFont(FONTE_B, 10)
        c.drawRightString((PAG_L - MARGEM - 2.5) * mm, _y(36), f'VERSÃO {versao}')
        c.setFillColor(PRETO)

    # I — Dados do aluno
    xi, yi, wi, hi = MARGEM, 40, 106, 46
    _caixa(c, xi, yi, wi, hi, 'I   DADOS DO ALUNO')
    al = aluno or {}
    _campo(c, xi + 3, yi + 6.3, 72, 'APELIDO', al.get('apelido'))
    _campo(c, xi + 3, yi + 13.8, 72, 'NOME', al.get('nome'))
    _campo(c, xi + 3, yi + 21.3, 17, 'CLASSE', al.get('classe'), 12)
    _campo(c, xi + 22, yi + 21.3, 34, 'ÁREA / SECÇÃO', al.get('area'), 12)
    _campo(c, xi + 58, yi + 21.3, 12, 'TURMA', al.get('turma'), 12)
    _campo(c, xi + 72, yi + 21.3, 5, 'Nº', str(al['numero']) if al.get('numero') else '', 12)
    _campo(c, xi + 3, yi + 28.8, 72, 'CÓDIGO DO ALUNO', al.get('codigo'), 13)
    if config['codigo_barras'] and al.get('codigo'):
        _desenhar_codigo_barras(c, al['codigo'], xi + 3, yi + 37.6, 72, 4.6)

    # II — Informações da avaliação
    xii, wii = MARGEM + 109, LARG_UTIL - 109
    _caixa(c, xii, yi, wii, hi, 'II   INFORMAÇÕES DA AVALIAÇÃO')
    c.setFont(FONTE_B, 9)
    c.setFillColor(CINZA_TEXTO)
    c.drawString((xii + 3) * mm, _y(yi + 8.8), 'TIPO DE AVALIAÇÃO')
    c.setFillColor(PRETO)
    pos = [(xii + 3, yi + 10), (xii + 27, yi + 10), (xii + 51, yi + 10), (xii + 3, yi + 14.6), (xii + 27, yi + 14.6)]
    # Só aparece o tipo de avaliação seleccionado; os restantes ficam ocultos.
    for cod, rot in TIPOS_AVALIACAO:
        if cod == config['tipo']:
            _check(c, pos[0][0], pos[0][1] + 1.5, rot, True, tam=12, lado=3.8, larg_txt=60)
            break
    _campo(c, xii + 3, yi + 19, 31, 'Nº DE PERGUNTAS', str(config['n_perguntas']), 12, 8.2)
    _campo(c, xii + 37, yi + 19, 34, 'Nº DE ALTERNATIVAS', f"{config['n_alternativas']} ({LETRAS[0]}–{LETRAS[config['n_alternativas'] - 1]})", 12, 8.2)
    uniforme = len(config['seccoes']) == 1
    cot_txt = formatar_valor(config['seccoes'][0]['cotacao']) if uniforme else 'por secção'
    _campo(c, xii + 3, yi + 26.6, 31, 'COTAÇÃO / PERGUNTA', cot_txt, 12, 8.2)
    _campo(c, xii + 37, yi + 26.6, 34, 'COTAÇÃO TOTAL', f"{formatar_valor(config['cotacao_total'])} valores", 12, 8.2)
    dur = f"{config['duracao_min']} min" if config['duracao_min'] else ''
    _campo(c, xii + 3, yi + 34.2, 15, 'DURAÇÃO', dur, 12, 8.2)
    _campo(c, xii + 20, yi + 34.2, 19, 'DATA', config['data'], 12, 8.2)
    _campo(c, xii + 41, yi + 34.2, 31, 'HORA (INÍCIO – FIM) / SALA', texto_hora_sala(config), 12, 7.4)

    # III — Disciplina
    yiii, hiii = 88.5, 31 + d
    _caixa(c, MARGEM, yiii, 106, hiii, 'III   DISCIPLINA')
    # Só aparece a disciplina seleccionada; as restantes ficam ocultas.
    _check(c, MARGEM + 3, yiii + 6.6, config['disciplina'], True, tam=12, lado=3.8, larg_txt=96)
    if config['professor']:
        c.setFont(FONTE_I, 10.5)
        c.setFillColor(CINZA_TEXTO)
        c.drawString((MARGEM + 3) * mm, _y(yiii + 30.1), f"Professor(a): {config['professor']}"[:70])
        c.setFillColor(PRETO)
    if vig:  # só no Exame Final: espaço para a assinatura de cada vigilante
        c.setFillColor(PRETO)
        c.setFont(FONTE_B, 10.5)
        c.drawString((MARGEM + 3) * mm, _y(yiii + 35.0), 'Professores Vigilantes:')
        c.setLineWidth(0.5)
        c.setStrokeColor(PRETO)
        for k, rot in enumerate(('1º Vigilante:', '2º Vigilante:')):
            x0 = MARGEM + 3 + k * 51
            c.setFont(FONTE, 10)
            c.drawString(x0 * mm, _y(yiii + 39.6), rot)
            c.line((x0 + 21) * mm, _y(yiii + 39.8), (x0 + 48) * mm, _y(yiii + 39.8))

    # IV — Classificação
    _caixa(c, xii, yiii, wii, hiii, 'IV   CLASSIFICAÇÃO')
    _campo(c, xii + 3, yiii + 6, 33, 'Acertos (n.º)', '', tam_rot=9)
    c.setFont(FONTE_B, 12)
    c.drawString((xii + 37) * mm, _y(yiii + 11.6), f"/ {config['n_perguntas']}")
    rot1, rot2 = rotulos_correccao(config)
    _campo(c, xii + 3, yiii + 13.6, 33, f'{rot1} (valores)', '', tam_rot=7.4)
    _campo(c, xii + 38, yiii + 13.6, 33, f'{rot2} (valores)', '', tam_rot=7.4)
    _campo(c, xii + 3, yiii + 21.2, 33, 'Ass. do Professor', '', tam_rot=9)
    _campo(c, xii + 38, yiii + 21.2, 33, 'Ass. do Professor', '', tam_rot=9)

    # Instruções gerais + grelha
    _bloco_instrucoes(c, 121.5 + d, config['instrucao_extra'])
    _barra_titulo(c, MARGEM, 146.2 + d, LARG_UTIL, 6, 'GRELHA DE RESPOSTAS', 'l', 10.5)
    c.setFillColor(colors.white)
    c.setFont(FONTE, 9.6)
    _texto_ajustado(c, 'Cotação: ' + _descricao_cotacao(config), MARGEM + 52, 150.5 + d, LARG_UTIL - 54, FONTE, 9.6, 6.0, 'r')
    c.setFillColor(PRETO)


def _cabecalho_continuacao(c, escola, aluno, config, versao, ate_pergunta, inicio):
    if config['marcas_omr']:
        _desenhar_marcas_omr(c)
    _barra_titulo(c, MARGEM, 11, LARG_UTIL, 7, _titulo_prova(config, aluno) + '  (continuação)', 'l', 9)
    al = aluno or {}
    c.setFont(FONTE_B, 8.5)
    c.setFillColor(PRETO)
    ident = ' '.join(x for x in (al.get('apelido'), al.get('nome')) if x)
    _texto_ajustado(c, f"Aluno: {ident}" if ident else 'Aluno: ______________________________', MARGEM, 23.5, 110, FONTE_B, 9)
    _texto_ajustado(c, f"Código: {al.get('codigo', '')}   Turma: {al.get('turma', '')}   Nº: {al.get('numero', '')}", MARGEM, 27.6, 110, FONTE, 8.2)
    if versao:
        c.setFont(FONTE_B, 9)
        c.drawRightString((PAG_L - MARGEM) * mm, _y(24), f'Versão {versao}')
    c.setFont(FONTE, 7.5)
    c.drawRightString((PAG_L - MARGEM) * mm, _y(27.8), f'Perguntas {inicio + 1} a {ate_pergunta}')


def gerar_folhas_pdf(escola, alunos, config, ano_letivo=None):
    """
    Gera o PDF com uma folha (1+ páginas) por aluno. `alunos` = lista de dicts (montar_dados_aluno);
    `None` na lista gera uma folha em branco (campos do aluno por preencher).
    Devolve (bytes_pdf, numero_de_folhas). Levanta ConfigFolhaInvalida / ValueError.
    """
    if not alunos:
        raise ConfigFolhaInvalida('Não há alunos para gerar folhas de resposta.')
    if len(alunos) > MAX_FOLHAS:
        raise ConfigFolhaInvalida(f'Máximo de {MAX_FOLHAS} folhas por ficheiro; reduza o âmbito (use a turma).')
    ano = ano_letivo or escola.get('ano_letivo') or ''
    logo_bytes, logo_reader, _, _ = resolver_logo_documento_escola(escola.get('obj') or escola)
    if logo_reader is None:
        from .pdf_service import DocumentoSemLogoError
        raise DocumentoSemLogoError('A escola não tem o logótipo oficial escolhido para documentos.')
    if config.get('logo_escola'):
        _lb = logo_proprio_escola(escola)
        if _lb:
            from reportlab.lib.utils import ImageReader as _IR
            escola = dict(escola, _logo_proprio=_IR(io.BytesIO(_lb)))
    hoje = _agora_texto()
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(PAG_L * mm, PAG_A * mm))
    c.setTitle(f"Folha de Respostas — {config.get('identificacao') or config['disciplina']} — {ROTULO_TIPO[config['tipo']]}")
    c.setAuthor('SIGE')
    c.setSubject('Folha de respostas personalizada')
    paginas = paginas_grelha(config['n_perguntas'], DESLOC_VIGILANTES if config['tipo'] == 'EXAME' else 0.0)
    for idx, aluno in enumerate(alunos):
        versao = versao_do_aluno(config, idx)
        cod = codigo_folha(escola, aluno, config, ano)
        if aluno:  # marcador com o nome do aluno: localiza-se a folha pelo painel de marcadores do PDF
            nome_marc = f"{aluno.get('numero') or idx + 1:02d} {aluno.get('apelido') or ''} {aluno.get('nome') or ''}".replace('  ', ' ').strip()
            c.bookmarkPage(f'aluno{idx}')
            c.addOutlineEntry(nome_marc, f'aluno{idx}', 0)
        for p, (ini, fim, cols, linhas, y_ini) in enumerate(paginas):
            if p == 0:
                _pagina_principal(c, escola, logo_reader, ano, aluno, config, versao, cod, p + 1, len(paginas), hoje)
            else:
                _cabecalho_continuacao(c, escola, aluno, config, versao, fim, ini)
            _desenhar_grelha(c, config, ini, fim, cols, linhas, y_ini)
            ct = _classe_turma(aluno)   # a identificação de cada folha leva a classe e a turma do próprio aluno
            ident_folha = f"{ct} · {config['disciplina']} · {ano}" if ct else config.get('identificacao', '')
            _rodape(c, cod, p + 1, len(paginas), hoje, ident_folha)
            c.showPage()
    if config['incluir_chave']:
        for v, g in config['gabaritos'].items():
            c.setFont(FONTE, 10)
            _pagina_chave_completa(c, escola, logo_reader, ano, config, '' if v == '-' else v, g, hoje)
            c.showPage()
    c.save()
    return buf.getvalue(), len(alunos)


def _pagina_chave_completa(c, escola, logo_reader, ano, config, versao, gabarito, hoje):
    if config['marcas_omr']:
        _desenhar_marcas_omr(c)
    _cabecalho_institucional(c, escola, logo_reader, ano)
    _barra_titulo(c, MARGEM, 32, LARG_UTIL, 8, 'CHAVE DE CORRECÇÃO — USO EXCLUSIVO DO PROFESSOR', 'l', 10)
    c.setFillColor(PRETO)
    desc = f"{config['tipo_rotulo']} · {config['disciplina']}" + (f' · Versão {versao}' if versao else '')
    c.setFont(FONTE_B, 9.5)
    c.drawString(MARGEM * mm, _y(46), desc)
    c.setFont(FONTE, 8.2)
    c.drawString(MARGEM * mm, _y(50.8), f"{config['n_perguntas']} perguntas · {config['n_alternativas']} alternativas · Cotação: {_descricao_cotacao(config)}")
    n = config['n_perguntas']
    y_ini = 56.0
    cap = capacidade_linhas(Y_FIM_GRELHA - y_ini)
    cols, linhas = layout_grelha(n, cap)
    if cols * linhas < n:
        cols, linhas = 4, math.ceil(math.ceil(n / 4) / 5) * 5
    _desenhar_grelha(c, config, 0, n, cols, linhas, y_ini, gabarito)
    _rodape(c, 'CHAVE', 1, 1, hoje)


# --------------------------------------------------------------------------------------
# Excel
# --------------------------------------------------------------------------------------
def _png_codigo_barras(valor, altura_px=46):
    """PNG do Code128 (via decomposição do ReportLab) para inserir no Excel."""
    from PIL import Image, ImageDraw
    b = code128.Code128(valor, barWidth=1, humanReadable=False)
    b._calculate()
    b.decompose()
    larguras = [(ord(ch.lower()) - 96, ch.isupper()) for ch in b.decomposed]
    modulo = 2
    total = sum(w for w, _ in larguras) * modulo + 20
    im = Image.new('RGB', (total, altura_px), 'white')
    d = ImageDraw.Draw(im)
    x = 10
    for w, barra in larguras:
        if barra:
            d.rectangle([x, 0, x + w * modulo - 1, altura_px - 1], fill='black')
        x += w * modulo
    out = io.BytesIO()
    im.save(out, format='PNG')
    return out.getvalue()


def _png_qr(dados, lado=110):
    import qrcode
    qr = qrcode.QRCode(box_size=4, border=1, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(dados)
    qr.make(fit=True)
    im = qr.make_image(fill_color='black', back_color='white').convert('RGB').resize((lado, lado))
    out = io.BytesIO()
    im.save(out, format='PNG')
    return out.getvalue()


def _dimensoes_excel(config):
    """(blocos, linhas por bloco, colunas de grelha G, sub-colunas por coluna K, total de colunas NCOL).
    Todas as colunas da folha têm a mesma largura e a grelha ocupa-as TODAS (sem colunas em branco)."""
    n, n_alt = config['n_perguntas'], config['n_alternativas']
    cols, _ = layout_grelha(n, 999)
    cols = max(1, min(cols, 4))
    linhas = math.ceil(math.ceil(n / cols) / 5) * 5
    blocos = math.ceil(n / linhas)
    G = blocos * (1 + n_alt)
    K = max(2, math.ceil(56 / G))
    return blocos, linhas, G, K, G * K


def _contorno_xl(ws, r1, c1, r2, c2, estilo='thick', cor='1E3A8A'):
    """Moldura exterior de um bloco (preserva as linhas interiores já definidas)."""
    from openpyxl.styles import Border, Side
    lado = Side(style=estilo, color=cor)
    for r in range(r1, r2 + 1):
        for c in range(c1, c2 + 1):
            cel = ws.cell(row=r, column=c)
            b = cel.border
            cel.border = Border(left=lado if c == c1 else b.left, right=lado if c == c2 else b.right,
                                top=lado if r == r1 else b.top, bottom=lado if r == r2 else b.bottom)


def gerar_folhas_xlsx(escola, alunos, config, ano_letivo=None):
    """Excel com uma folha por aluno (réplica da grelha), mais 'Resumo' e 'Chave' quando aplicável."""
    import openpyxl
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter as col_l
    from .xlsx_seguro import guardar_xlsx_seguro, nome_folha, normalizar_logo_png

    if not alunos:
        raise ConfigFolhaInvalida('Não há alunos para gerar folhas de resposta.')
    if len(alunos) > MAX_FOLHAS:
        raise ConfigFolhaInvalida(f'Máximo de {MAX_FOLHAS} folhas por ficheiro; reduza o âmbito (use a turma).')
    ano = ano_letivo or escola.get('ano_letivo') or ''
    logo_bytes, _, _, _ = resolver_logo_documento_escola(escola.get('obj') or escola)
    if not logo_bytes:
        from .pdf_service import DocumentoSemLogoError
        raise DocumentoSemLogoError('A escola não tem o logótipo oficial escolhido para documentos.')
    logo_png = normalizar_logo_png(logo_bytes)
    logo_esc_png = None
    if config.get('logo_escola'):
        _lb = logo_proprio_escola(escola)
        logo_esc_png = normalizar_logo_png(_lb) if _lb else None
    hoje = _agora_texto()

    TNR = 'Times New Roman'
    f_norm = Font(name=TNR, size=12)
    f_bold = Font(name=TNR, size=12, bold=True)
    f_peq = Font(name=TNR, size=12, color='4A5361')
    f_titulo = Font(name=TNR, size=12, bold=True, color='FFFFFF')
    f_bolha = Font(name='Times New Roman', size=12)
    f_bolha_cheia = Font(name='Times New Roman', size=12, color='000000', bold=True)
    fundo_azul = PatternFill('solid', start_color='1E3A8A')
    fundo_cinza = PatternFill('solid', start_color='F1F4F8')
    fino = Side(style='thin', color='8A94A3')
    borda = Border(left=fino, right=fino, top=fino, bottom=fino)
    sob = Border(bottom=fino)
    centro = Alignment(horizontal='center', vertical='center', wrap_text=True)
    esq = Alignment(horizontal='left', vertical='center', wrap_text=True)
    BLOCOS, LINHAS_B, G_GRELHA, K_SUB, NCOL = _dimensoes_excel(config)
    S = NCOL / 28.0  # o desenho do cabeçalho usa 28 colunas «de projecto»

    def C1(u):
        return int(round((u - 1) * S)) + 1

    def C2(u):
        return int(round(u * S))
    ALT = 'ⒶⒷⒸⒹⒺⒻ'
    n = config['n_perguntas']
    n_alt = config['n_alternativas']

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    existentes = []

    AZUL_X = '1E3A8A'
    fino_i = Side(style='thin', color='B8C2D0')
    borda_i = Border(left=fino_i, right=fino_i, top=fino_i, bottom=fino_i)

    def contorno(ws, r1, u1, r2, u2, estilo='thick', cor=AZUL_X):
        _contorno_xl(ws, r1, C1(u1), r2, C2(u2), estilo, cor)

    def garantir_altura(ws, r, texto, c1, c2, negrito=False, minimo=24):
        """Altura da linha suficiente para o texto quebrar nos espaços sem ser cortado (Times New Roman 12)."""
        largura = max((c2 - c1 + 1) * (140.0 / NCOL) - 2.0, 3.0)
        fator = 1.32 if negrito else 1.18
        linhas = 0
        for parte in str(texto).split('\n'):
            palavras = parte.split()
            atual, n_lin = 0.0, 1
            for pal in palavras:
                w = len(pal) * fator
                if atual and atual + 1 + w > largura:
                    n_lin += 1
                    atual = w
                else:
                    atual = atual + (1 if atual else 0) + w
            linhas += n_lin
        precisa = max(minimo, linhas * 17 + 8)
        ws.row_dimensions[r].height = max(ws.row_dimensions[r].height or 0, precisa)

    def barra(ws, r, u1, u2, texto, alinh=centro):
        ws.merge_cells(start_row=r, start_column=C1(u1), end_row=r, end_column=C2(u2))
        cel = ws.cell(row=r, column=C1(u1), value=texto)
        for cc in range(C1(u1), C2(u2) + 1):
            ws.cell(row=r, column=cc).fill = fundo_azul
        cel.font = f_titulo
        cel.alignment = centro
        ws.row_dimensions[r].height = max(ws.row_dimensions[r].height or 0, 24)
        garantir_altura(ws, r, texto, C1(u1), C2(u2), True)

    def juntar(ws, r, u1, u2, valor=None, fonte=None, alinh=None, borda_=None, fundo=None):
        ws.merge_cells(start_row=r, start_column=C1(u1), end_row=r, end_column=C2(u2))
        cel = ws.cell(row=r, column=C1(u1), value=valor)
        if fonte:
            cel.font = fonte
        if alinh:
            cel.alignment = alinh
        for cc in range(C1(u1), C2(u2) + 1):
            if borda_:
                ws.cell(row=r, column=cc).border = borda_
            if fundo:
                ws.cell(row=r, column=cc).fill = fundo
        if isinstance(valor, str) and valor:
            if alinh is not None and not alinh.wrap_text:
                cel.alignment = Alignment(horizontal=alinh.horizontal, vertical=alinh.vertical or 'center',
                                          indent=alinh.indent, wrap_text=True)
            garantir_altura(ws, r, valor, C1(u1), C2(u2), bool(fonte and fonte.bold))
        return cel

    def par(ws, r, u1, u2, rotulo, valor, v1=None, v2=None):
        """Rótulo (fundo cinza) em u1..u2 e valor (fundo branco) em v1..v2 (colunas de projecto)."""
        juntar(ws, r, u1, u2, rotulo, f_bold, esq, borda_i, fundo_cinza)
        v1, v2 = v1 or u2 + 1, v2 or u2 + 1
        juntar(ws, r, v1, v2, valor if valor not in (None, '') else None, f_bold, esq, borda_i,
               PatternFill('solid', start_color='FFFFFF'))
        ws.row_dimensions[r].height = max(ws.row_dimensions[r].height or 0, 24)

    def preparar(ws):
        ws.sige_layout_fixo = True
        for i in range(1, NCOL + 1):
            ws.column_dimensions[col_l(i)].width = 140.0 / NCOL
        ws.sheet_view.showGridLines = False
        ws.page_setup.orientation = 'portrait'
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 1   # a folha cabe sempre numa só página
        ws.sheet_properties.pageSetUpPr = openpyxl.worksheet.properties.PageSetupProperties(fitToPage=True)
        ws.page_margins.left = ws.page_margins.right = 0.4
        ws.page_margins.top = ws.page_margins.bottom = 0.4
        ws.print_options.horizontalCentered = True

    def cabecalho(ws, titulo):
        """Cabeçalho idêntico ao do PDF: emblema à esquerda, República/Província/Distrito, escola à direita."""
        if logo_png:
            img = XLImage(io.BytesIO(logo_png))
            img.width = img.height = 88
            ws.add_image(img, 'A1')
        for r in range(1, 5):
            ws.row_dimensions[r].height = max(ws.row_dimensions[r].height or 0, 24)
        esquerda = [
            ('REPÚBLICA DE MOÇAMBIQUE', Font(name=TNR, size=12, bold=True)),
            (f"Província de {escola['provincia']}" if escola.get('provincia') else '', f_norm),
            (f"Distrito de {escola['distrito']}" if escola.get('distrito') else '', f_norm),
            ('Sector Pedagógico', Font(name=TNR, size=12, italic=True)),
        ]
        direita = [
            (escola.get('nome') or '', Font(name=TNR, size=12, bold=True)),
            (f"Código da escola: {escola['codigo']}" if escola.get('codigo') else '', f_norm),
            (f'Ano lectivo: {ano}', Font(name=TNR, size=12, bold=True)),
            ('', f_norm),
        ]
        u_dir = 16
        if logo_esc_png:
            im2 = XLImage(io.BytesIO(logo_esc_png))
            im2.width = im2.height = 72
            ws.add_image(im2, f'{col_l(C1(16))}1')
            u_dir = 19
        for i in range(4):
            for (txt, fnt), u1, u2 in ((esquerda[i], 5, 14), (direita[i], u_dir, 28)):
                juntar(ws, i + 1, u1, u2, txt or None, fnt, Alignment(horizontal='left', vertical='center'))
        barra(ws, 5, 1, 28, titulo, esq)
        ws.row_dimensions[5].height = max(ws.row_dimensions[5].height or 0, 26)
        ws.row_dimensions[6].height = 6

    # ---------------- folhas dos alunos ----------------
    for idx, aluno in enumerate(alunos):
        al = aluno or {}
        versao = versao_do_aluno(config, idx)
        rotulo_folha = f"{al.get('numero', idx + 1):02d} {al.get('apelido', '')} {al.get('nome', '')}".strip() if aluno else f'Branco {idx + 1:03d}'
        ws = wb.create_sheet(nome_folha(rotulo_folha, padrao=f'Folha {idx + 1}', existentes=existentes))
        existentes.append(ws.title)
        preparar(ws)
        cabecalho(ws, _titulo_prova(config, aluno) + (f'   ·   VERSÃO {versao}' if versao else ''))

        # ---- I DADOS DO ALUNO / II INFORMAÇÕES DA AVALIAÇÃO ----
        barra(ws, 7, 1, 15, 'I   DADOS DO ALUNO', esq)
        barra(ws, 7, 17, 28, 'II   INFORMAÇÕES DA AVALIAÇÃO', esq)
        par(ws, 8, 1, 3, 'APELIDO', al.get('apelido'), 4, 12)
        par(ws, 9, 1, 3, 'NOME', al.get('nome'), 4, 12)
        par(ws, 10, 1, 3, 'CLASSE', al.get('classe'), 4, 6)
        par(ws, 10, 7, 8, 'TURMA', al.get('turma'), 9, 10)
        par(ws, 10, 11, 11, 'Nº', al.get('numero'), 12, 12)
        par(ws, 11, 1, 3, 'CÓDIGO', al.get('codigo'), 4, 12)
        par(ws, 12, 1, 3, 'ÁREA/SECÇÃO', al.get('area'), 4, 12)
        juntar(ws, 13, 1, 15)
        ws.row_dimensions[13].height = max(ws.row_dimensions[13].height or 0, 62)  # linha alta só para o código de barras
        qr = XLImage(io.BytesIO(_png_qr(_payload_qr(escola, aluno, config, ano, versao))))
        qr.width = qr.height = 108
        ws.add_image(qr, f'{col_l(C1(13))}8')
        if config['codigo_barras'] and al.get('codigo'):
            from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
            from openpyxl.drawing.xdr import XDRPositiveSize2D
            bar = XLImage(io.BytesIO(_png_codigo_barras(al['codigo'], altura_px=60)))
            bar.width, bar.height = 330, 54
            emu = 9525
            # bem visível: a meio da linha, longe das molduras (zona de silêncio branca à volta das barras)
            bar.anchor = OneCellAnchor(_from=AnchorMarker(col=C1(3) - 1, colOff=12 * emu, row=12, rowOff=12 * emu),
                                       ext=XDRPositiveSize2D(bar.width * emu, bar.height * emu))
            ws.add_image(bar)
        contorno(ws, 7, 1, 13, 15)

        juntar(ws, 8, 17, 28, 'TIPO DE AVALIAÇÃO', f_bold, esq, borda_i, fundo_cinza)
        juntar(ws, 9, 17, 28, '   '.join(('☒' if cod == config['tipo'] else '☐') + ' ' + rot for cod, rot in TIPOS_AVALIACAO),
               Font(name='Times New Roman', size=12, bold=True), esq, borda_i)
        uniforme = len(config['seccoes']) == 1
        par(ws, 10, 17, 20, 'Nº PERGUNTAS', n, 21, 22)
        par(ws, 10, 23, 26, 'ALTERNATIVAS', n_alt, 27, 28)
        par(ws, 11, 17, 20, 'COTAÇÃO/PERG.', formatar_valor(config['seccoes'][0]['cotacao']) if uniforme else 'por secção', 21, 22)
        par(ws, 11, 23, 26, 'TOTAL (val.)', formatar_valor(config['cotacao_total']), 27, 28)
        par(ws, 12, 17, 20, 'DURAÇÃO (min)', config['duracao_min'] or None, 21, 22)
        par(ws, 12, 23, 26, 'DATA', config['data'], 27, 28)
        par(ws, 13, 17, 20, 'HORA / SALA', texto_hora_sala(config), 21, 28)
        contorno(ws, 7, 17, 13, 28)

        ws.row_dimensions[14].height = 6
        # ---- III DISCIPLINA / IV CLASSIFICAÇÃO ----
        barra(ws, 15, 1, 15, 'III   DISCIPLINA', esq)
        barra(ws, 15, 17, 28, 'IV   CLASSIFICAÇÃO', esq)
        nomes = [config['disciplina']]   # só a disciplina seleccionada
        for r in range(16, 21):
            ws.row_dimensions[r].height = max(ws.row_dimensions[r].height or 0, 24)
        for k, nome in enumerate(nomes):
            cc, rr = divmod(k, 5)
            u1 = 1 + cc * 5
            marcado = nome == config['disciplina']
            juntar(ws, 16 + rr, u1, u1 + 4, ('☒ ' if marcado else '☐ ') + nome,
                   Font(name='Times New Roman', size=12, bold=marcado), esq)
        contorno(ws, 15, 1, 20, 15)
        rot1, rot2 = rotulos_correccao(config)
        par(ws, 16, 17, 22, 'Acertos (n.º)', None, 23, 25)
        juntar(ws, 16, 26, 28, f'/ {n}', f_norm, esq)
        par(ws, 17, 17, 22, f'{rot1} (valores)', None, 23, 28)
        par(ws, 18, 17, 22, 'Ass. do Professor', None, 23, 28)
        par(ws, 19, 17, 22, f'{rot2} (valores)', None, 23, 28)
        par(ws, 20, 17, 22, 'Ass. do Professor', None, 23, 28)
        # etiquetas longas quebram em duas linhas: altura folgada para nenhuma ficar cortada
        for r in range(16, 21):
            ws.row_dimensions[r].height = max(ws.row_dimensions[r].height or 0, 40)
        for r in (10, 11, 12):
            ws.row_dimensions[r].height = max(ws.row_dimensions[r].height or 0, 32)
        contorno(ws, 15, 17, 20, 28)
        ws.row_dimensions[21].height = 6

        # ---- INSTRUÇÕES GERAIS ----
        barra(ws, 22, 1, 28, 'INSTRUÇÕES GERAIS', centro)
        instrucoes = [
            '1. Não dobre nem rasure esta folha de respostas.',
            '2. Todas as questões devem ser respondidas com caneta azul ou preta.',
            '3. Responda apenas a quantidade de questões relativa à sua prova.',
            '4. Marque apenas uma resposta por pergunta, pintando o quadradinho da alternativa escolhida, conforme o modelo abaixo.',
        ]
        for k, txt in enumerate(instrucoes):
            juntar(ws, 23 + k, 1, 28, txt, f_bold if k == 3 else f_norm, Alignment(horizontal='left', vertical='center', indent=1))
            ws.row_dimensions[23 + k].height = max(ws.row_dimensions[23 + k].height or 0, 22)
        juntar(ws, 27, 1, 4, 'Exemplo:', f_bold, Alignment(horizontal='left', vertical='center', indent=1))
        for k, letra in enumerate('ABCD'):
            u1 = 6 + k * 4
            marcada = letra == 'D'
            juntar(ws, 27, u1, u1 + 2, letra,
                   Font(name='Times New Roman', size=12, bold=True, color='FFFFFF' if marcada else '000000'), centro, borda,
                   PatternFill('solid', start_color='000000' if marcada else 'FFFFFF'))
        if config['instrucao_extra']:
            juntar(ws, 27, 23, 28, config['instrucao_extra'], f_norm, esq)
        ws.row_dimensions[27].height = max(ws.row_dimensions[27].height or 0, 26)
        contorno(ws, 22, 1, 27, 28)
        ws.row_dimensions[28].height = 6

        # ---- GRELHA ----
        barra(ws, 29, 1, 28, 'GRELHA DE RESPOSTAS   —   Cotação: ' + _descricao_cotacao(config), centro)
        _grelha_excel(ws, config, 30, None)
        ws.print_area = f'A1:{col_l(NCOL)}{ws.max_row + 1}'

    # ---------------- Resumo (sem fórmulas) ----------------
    reais = [(i, a) for i, a in enumerate(alunos) if a]
    if len(reais) > 1:
        ws = wb.create_sheet('Resumo')
        ws.sheet_view.showGridLines = False
        cab = ['Nº', 'Código', 'Apelido', 'Nome', 'Classe', 'Área/Secção', 'Turma', 'Versão', 'Pontos obtidos', 'Nota (0–20)', 'Observações']
        larg = [5, 24, 20, 30, 12, 14, 12, 8, 14, 12, 28]
        for i, (t, w) in enumerate(zip(cab, larg), start=1):
            ws.column_dimensions[col_l(i)].width = w
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(cab))
        t = ws.cell(row=1, column=1, value=f"Resumo — {_titulo_prova(config)} · {escola.get('nome', '')} · {ano}")
        t.font = Font(name=TNR, size=12, bold=True)
        ws.cell(row=2, column=1, value=f"Cotação total: {formatar_valor(config['cotacao_total'])} valores · {n} perguntas · Emitido em {hoje}").font = f_peq
        for i, h in enumerate(cab, start=1):
            cel = ws.cell(row=4, column=i, value=h)
            cel.font = f_titulo
            cel.fill = fundo_azul
            cel.alignment = centro
            cel.border = borda
        for r, (i, a) in enumerate(reais, start=5):
            vals = [a.get('numero'), a.get('codigo'), a.get('apelido'), a.get('nome'), a.get('classe'), a.get('area'), a.get('turma'),
                    versao_do_aluno(config, i) or None, None, None, None]
            for cidx, v in enumerate(vals, start=1):
                cel = ws.cell(row=r, column=cidx, value=v)
                cel.font = f_norm
                cel.border = borda
                cel.alignment = centro if cidx in (1, 5, 6, 7, 8, 9, 10) else esq
        ws.freeze_panes = 'A5'
        ws.page_setup.orientation = 'portrait'
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr = openpyxl.worksheet.properties.PageSetupProperties(fitToPage=True)

    # ---------------- Chave de correcção ----------------
    if config['incluir_chave']:
        for v, g in config['gabaritos'].items():
            ws = wb.create_sheet(nome_folha(f"Chave {v if v != '-' else ''}".strip(), existentes=[s.title for s in wb.worksheets]))
            preparar(ws)
            cabecalho(ws, 'CHAVE DE CORRECÇÃO — USO EXCLUSIVO DO PROFESSOR   ·   ' + config['disciplina']
                      + (f'   ·   VERSÃO {v}' if v != '-' else ''))
            barra(ws, 7, 1, 28, 'Cotação: ' + _descricao_cotacao(config), esq)
            _grelha_excel(ws, config, 9, g)
            ws.print_area = f'A1:{col_l(NCOL)}{ws.max_row + 1}'

    return guardar_xlsx_seguro(wb), len(alunos)


def _grelha_excel(ws, config, linha_ini, gabarito):
    """
    Grelha no estilo das tabelas do SIGE: cabeçalho azul («Perg.» | «Alternativas»), uma letra por célula,
    todas as colunas com a mesma largura e SEM colunas em branco; moldura grossa azul, linha dupla dourada
    sob o cabeçalho, linhas ponteadas entre perguntas. Cada célula da letra é o quadradinho a pintar.
    """
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    n, n_alt = config['n_perguntas'], config['n_alternativas']
    blocos, linhas, G, K, NCOL = _dimensoes_excel(config)
    azul, ouro = '1E3A8A', 'C9A227'
    vert = Side(style='thin', color='CBD5E1')
    pont = Side(style='dotted', color='94A3B8')
    dupla = Side(style='double', color=ouro)
    centro_c = Alignment(horizontal='centerContinuous', vertical='center')
    branco = PatternFill('solid', start_color='FFFFFF')
    zebra = PatternFill('solid', start_color='F1F5F9')
    fundo_azul = PatternFill('solid', start_color=azul)
    preto = PatternFill('solid', start_color='000000')

    def celula(r, c0, ncols, valor, fonte, fundo, topo, base):
        """Preenche ncols sub-colunas a partir de c0 (valor centrado ao longo de todas) com bordas verticais finas."""
        for k in range(ncols):
            cel = ws.cell(row=r, column=c0 + k)
            if k == 0:
                cel.value = valor
            cel.font = fonte
            cel.fill = fundo
            cel.alignment = centro_c
            cel.border = Border(left=vert if k == 0 else None, right=vert if k == ncols - 1 else None, top=topo, bottom=base)

    f_cab = Font(name='Times New Roman', size=12, bold=True, color='FFFFFF')
    for b in range(blocos):
        c0 = 1 + b * (1 + n_alt) * K
        celula(linha_ini, c0, K, 'Perg.', f_cab, fundo_azul, None, dupla)
        celula(linha_ini, c0 + K, n_alt * K, 'Alternativas', f_cab, fundo_azul, None, dupla)
    ws.row_dimensions[linha_ini].height = 24
    usadas = [0] * blocos
    for r in range(linhas):
        pos = linha_ini + 1 + r
        ws.row_dimensions[pos].height = 25
        fundo = zebra if r % 2 == 1 else branco
        for b in range(blocos):
            q = b * linhas + r
            if q >= n:
                continue
            usadas[b] = r + 1
            c0 = 1 + b * (1 + n_alt) * K
            topo = dupla if r == 0 else pont
            celula(pos, c0, K, q + 1, Font(name='Times New Roman', size=12, bold=True), fundo, topo, pont)
            for i in range(n_alt):
                marcada = bool(gabarito and gabarito[q] == LETRAS[i])
                celula(pos, c0 + (1 + i) * K, K, LETRAS[i],
                       Font(name='Times New Roman', size=12, bold=True, color='FFFFFF' if marcada else '000000'),
                       preto if marcada else fundo, topo, pont)
    for b in range(blocos):
        c0 = 1 + b * (1 + n_alt) * K
        _contorno_xl(ws, linha_ini, c0, linha_ini + usadas[b], c0 + (1 + n_alt) * K - 1)
