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
import datetime
import hashlib
import io
import math
import re

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
MAX_PERGUNTAS = 200
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

AZUL = colors.HexColor('#14325c')
CINZA_FUNDO = colors.HexColor('#f1f4f8')
CINZA_LINHA = colors.HexColor('#8a94a3')
CINZA_TEXTO = colors.HexColor('#4a5361')
PRETO = colors.HexColor('#111111')

FONTE = 'Times-Roman'
FONTE_B = 'Times-Bold'
FONTE_I = 'Times-Italic'

# Geometria (mm, medidos a partir do topo da página A4)
PAG_L, PAG_A = 210.0, 297.0
MARGEM = 12.0
LARG_UTIL = PAG_L - 2 * MARGEM
Y_GRELHA_1 = 156.0          # início da grelha na 1ª página
Y_GRELHA_CONT = 30.0        # início da grelha nas páginas de continuação
Y_FIM_GRELHA = 283.0
ALTURA_LINHA_MIN = 4.4
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
            ate = _num((s or {}).get('ate'), 'o limite da secção', inicio, n_perg, inteiro=True)
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
    total = round(sum(cotacoes), 2)

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
        'duracao_min': duracao,
        'data': _texto(dados.get('data'), 20),
        'hora_inicio': _texto(dados.get('hora_inicio'), 8),
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
    }


def montar_dados_escola(escola):
    """Dados reais da escola (modelo `Escola`) num dicionário simples."""
    return {
        'nome': escola.nome or '',
        'codigo': escola.codigo_escola or '',
        'provincia': escola.provincia or '',
        'distrito': escola.distrito or '',
        'ano_letivo': escola.ano_letivo_ativo or '',
        'trimestre': escola.trimestre_ativo or '',
        'obj': escola,
    }


def montar_dados_aluno(aluno, numero, classe=None, turma=None):
    return {
        'apelido': (aluno.apelido or '').strip(),
        'nome': (aluno.nome or '').strip(),
        'classe': classe or (aluno.turma.grau_ano if aluno.turma_id else (aluno.classe or '')),
        'turma': turma or (aluno.turma.nome if aluno.turma_id else ''),
        'numero': numero,
        'codigo': (aluno.matricula or '').strip(),
    }


def versao_do_aluno(config, indice):
    vs = config['versoes']
    return vs[indice % len(vs)] if vs and vs[0] else ''


def codigo_folha(escola, aluno, config, ano):
    """Código curto e estável da folha (rastreável, não secreto)."""
    base = f"{escola.get('codigo')}|{(aluno or {}).get('codigo','-')}|{config['tipo']}|{config['disciplina']}|{ano}"
    return 'FR-' + hashlib.sha1(base.encode('utf-8')).hexdigest()[:10].upper()


def _payload_qr(escola, aluno, config, ano, versao):
    partes = ['SIGE', 'FR', escola.get('codigo') or '-', (aluno or {}).get('codigo') or 'BRANCO',
              config['tipo'], config['disciplina'], ano, versao or '-', str(config['n_perguntas'])]
    return '|'.join(partes)


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


def paginas_grelha(n):
    """Lista de páginas da grelha: [(inicio0, fim0_exclusivo, colunas, linhas, y_inicio_mm)]."""
    cap1 = capacidade_linhas(Y_FIM_GRELHA - Y_GRELHA_1)
    cols, linhas = layout_grelha(n, cap1)
    paginas = []
    if cols * linhas >= n:
        return [(0, n, cols, linhas, Y_GRELHA_1)]
    # Não cabe numa página: 1ª página completa e continuação(ões) com mais espaço.
    cap_c = capacidade_linhas(Y_FIM_GRELHA - Y_GRELHA_CONT)
    pos = 0
    cap_pag = 4 * cap1
    paginas.append((0, min(n, cap_pag), 4, cap1, Y_GRELHA_1))
    pos = cap_pag
    while pos < n:
        restante = n - pos
        linhas_c = min(cap_c, math.ceil(math.ceil(restante / 4) / 5) * 5)
        fim = min(n, pos + 4 * linhas_c)
        paginas.append((pos, fim, 4, linhas_c, Y_GRELHA_CONT))
        pos = fim
    return paginas


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
    if alinh == 'c':
        c.drawCentredString((x_mm + larg_mm / 2) * mm, _y(y_mm), txt)
    elif alinh == 'r':
        c.drawRightString((x_mm + larg_mm) * mm, _y(y_mm), txt)
    else:
        c.drawString(x_mm * mm, _y(y_mm), txt)


def _barra_titulo(c, x, y, w, h, titulo, alinh='l', tam=8.5):
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


def _campo(c, x, y, w, rotulo, valor, tam=10.5):
    """Campo com rótulo pequeno e valor sobre linha (preenchido automaticamente)."""
    c.setFillColor(CINZA_TEXTO)
    c.setFont(FONTE_B, 5.8)
    c.drawString(x * mm, _y(y + 2.4), rotulo)
    c.setStrokeColor(CINZA_LINHA)
    c.setLineWidth(0.4)
    c.line(x * mm, _y(y + 7.4), (x + w) * mm, _y(y + 7.4))
    c.setFillColor(PRETO)
    if valor:
        _texto_ajustado(c, valor, x + 0.6, y + 6.4, w - 1.2, FONTE_B, tam, 6)


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


def _bolha(c, cx_mm, cy_mm, raio_mm, letra, preenchida=False, tam_letra=6.2):
    c.setLineWidth(0.55)
    c.setStrokeColor(PRETO)
    c.setFillColor(PRETO if preenchida else colors.white)
    c.circle(cx_mm * mm, _y(cy_mm), raio_mm * mm, stroke=1, fill=1)
    c.setFillColor(colors.white if preenchida else CINZA_TEXTO)
    c.setFont(FONTE, tam_letra)
    c.drawCentredString(cx_mm * mm, _y(cy_mm) - tam_letra * 0.32, letra)
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


def _cabecalho_institucional(c, escola, logo_reader, ano, compacto=False):
    y0 = 8.0
    if logo_reader is not None:
        try:
            c.drawImage(logo_reader, MARGEM * mm, _y(y0 + 21), 21 * mm, 21 * mm, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
    c.setFillColor(PRETO)
    # Esquerda: República / Província / Distrito
    _texto_ajustado(c, 'REPÚBLICA DE MOÇAMBIQUE', 36, y0 + 5, 68, FONTE_B, 10.5)
    if escola.get('provincia'):
        _texto_ajustado(c, f"Província de {escola['provincia']}", 36, y0 + 10.5, 68, FONTE, 9.5)
    if escola.get('distrito'):
        _texto_ajustado(c, f"Distrito de {escola['distrito']}", 36, y0 + 15.5, 68, FONTE, 9.5)
    _texto_ajustado(c, 'Sector Pedagógico', 36, y0 + 20.5, 68, FONTE_I, 9)
    # Direita: escola
    c.setStrokeColor(CINZA_LINHA)
    c.setLineWidth(0.4)
    c.line(107 * mm, _y(y0 + 1), 107 * mm, _y(y0 + 22))
    _texto_ajustado(c, escola.get('nome') or '', 110, y0 + 5, PAG_L - MARGEM - 110, FONTE_B, 11, 6.5)
    if escola.get('codigo'):
        _texto_ajustado(c, f"Código da escola: {escola['codigo']}", 110, y0 + 11, PAG_L - MARGEM - 110, FONTE, 9.5)
    _texto_ajustado(c, f'Ano lectivo: {ano}', 110, y0 + 16.5, PAG_L - MARGEM - 110, FONTE_B, 9.5)


def _bloco_marcas_exemplo(c, y):
    """Faixa de instruções de preenchimento com exemplos (correcto / incorrecto)."""
    c.setFillColor(CINZA_FUNDO)
    c.setStrokeColor(CINZA_LINHA)
    c.setLineWidth(0.4)
    c.rect(MARGEM * mm, _y(y + 9), LARG_UTIL * mm, 9 * mm, stroke=1, fill=1)
    c.setFillColor(PRETO)
    c.setFont(FONTE_B, 7)
    c.drawString((MARGEM + 2) * mm, _y(y + 3.6), 'COMO PREENCHER:')
    c.setFont(FONTE, 7)
    c.drawString((MARGEM + 2) * mm, _y(y + 7.4), 'Use esferográfica azul ou preta. Pinte a bolha completamente; não rasure.')
    x = 128
    _bolha(c, x, y + 4.5, 2.1, 'A', True)
    c.setFont(FONTE_B, 7)
    c.drawString((x + 3.2) * mm, _y(y + 5.2), 'Correcto')
    x += 20
    _bolha(c, x, y + 4.5, 2.1, 'B', False)
    c.setStrokeColor(PRETO)
    c.setLineWidth(0.7)
    c.line((x - 1.6) * mm, _y(y + 2.9), (x + 1.6) * mm, _y(y + 6.1))
    c.line((x - 1.6) * mm, _y(y + 6.1), (x + 1.6) * mm, _y(y + 2.9))
    c.setFont(FONTE, 7)
    c.drawString((x + 3.2) * mm, _y(y + 5.2), 'Incorrecto')
    x += 21
    _bolha(c, x, y + 4.5, 2.1, 'C', False)
    c.setLineWidth(0.9)
    c.line((x - 1.2) * mm, _y(y + 4.5), (x + 1.2) * mm, _y(y + 4.5))
    c.setFont(FONTE, 7)
    c.drawString((x + 3.2) * mm, _y(y + 5.2), 'Incompleto')
    c.setStrokeColor(PRETO)


def _descricao_cotacao(config):
    partes = []
    for s in config['seccoes']:
        intervalo = f"{s['de']}" if s['de'] == s['ate'] else f"{s['de']}–{s['ate']}"
        partes.append(f"{intervalo} × {formatar_valor(s['cotacao'])}")
    return '  |  '.join(partes[:6]) + f"   ·   Total: {formatar_valor(config['cotacao_total'])} val."


def _desenhar_grelha(c, config, inicio, fim, cols, linhas, y_ini, gabarito=None):
    """Desenha a grelha de bolhas das perguntas [inicio, fim) (índices a partir de 0)."""
    n_alt = config['n_alternativas']
    letras = LETRAS[:n_alt]
    largura_col = LARG_UTIL / cols
    altura_disp = Y_FIM_GRELHA - y_ini
    folgas = ((linhas - 1) // 5) * FOLGA_GRUPO
    altura_linha = min(6.4, (altura_disp - ALTURA_CABECALHO_GRELHA - folgas) / linhas)
    passo = min(7.4, (largura_col - 11.5) / n_alt)
    raio = min(2.25, passo * 0.34, altura_linha * 0.42)
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
        c.setFont(FONTE_B, 6.6)
        c.drawString((x0 + 1.6) * mm, _y(y_ini + 3.9), 'Perg.')
        for i, letra in enumerate(letras):
            cx = x0 + 10.2 + passo * i + passo / 2 - 0.6
            c.drawCentredString(cx * mm, _y(y_ini + 3.9), letra)
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
            c.setFont(FONTE_B, 7.6)
            c.drawCentredString((x0 + 4.9) * mm, _y(y_lin + altura_linha / 2 + 1.0), str(q + 1))
            cy = y_lin + altura_linha / 2
            for i, letra in enumerate(letras):
                cx = x0 + 10.2 + passo * i + passo / 2 - 0.6
                _bolha(c, cx, cy, raio, letra, preenchida=bool(gabarito and gabarito[q] == letra))
    c.setFillColor(PRETO)
    c.setStrokeColor(PRETO)


def _rodape(c, cod_folha, pagina, total_paginas, hoje):
    c.setFillColor(CINZA_TEXTO)
    c.setFont(FONTE, 6.8)
    c.drawString(MARGEM * mm, _y(288.8), f'SIGE · Folha de Respostas Personalizada · Cód. {cod_folha}')
    c.drawCentredString((PAG_L / 2) * mm, _y(288.8), f'Pág. {pagina}/{total_paginas}')
    c.drawRightString((PAG_L - MARGEM) * mm, _y(288.8), f'Emitida em {hoje}')
    c.setFillColor(PRETO)


def _titulo_prova(config):
    partes = ['FOLHA DE RESPOSTAS', config['tipo_rotulo']]
    if config['trimestre'] and config['tipo'] != 'EXAME':
        partes.append(config['trimestre'])
    partes.append(config['disciplina'])
    return '  ·  '.join(partes)


def _pagina_principal(c, escola, logo_reader, ano, aluno, config, versao, cod_folha, pag, total, hoje):
    if config['marcas_omr']:
        _desenhar_marcas_omr(c)
    _cabecalho_institucional(c, escola, logo_reader, ano)
    # barra de título
    _barra_titulo(c, MARGEM, 32, LARG_UTIL, 8, _titulo_prova(config), 'l', 10)
    if versao:
        c.setFillColor(colors.white)
        c.setFont(FONTE_B, 10)
        c.drawRightString((PAG_L - MARGEM - 2.5) * mm, _y(37.4), f'VERSÃO {versao}')
        c.setFillColor(PRETO)

    # I — Dados do aluno
    xi, yi, wi, hi = MARGEM, 43, 106, 51
    _caixa(c, xi, yi, wi, hi, 'I   DADOS DO ALUNO')
    al = aluno or {}
    _campo(c, xi + 3, yi + 7, 72, 'APELIDO', al.get('apelido'))
    _campo(c, xi + 3, yi + 15.5, 72, 'NOME', al.get('nome'))
    _campo(c, xi + 3, yi + 24, 31, 'CLASSE', al.get('classe'), 9.5)
    _campo(c, xi + 36, yi + 24, 25, 'TURMA', al.get('turma'), 9.5)
    _campo(c, xi + 63, yi + 24, 12, 'Nº', str(al['numero']) if al.get('numero') else '', 9.5)
    _campo(c, xi + 3, yi + 32.5, 72, 'CÓDIGO DO ALUNO', al.get('codigo'), 9.5)
    if config['codigo_barras'] and al.get('codigo'):
        _desenhar_codigo_barras(c, al['codigo'], xi + 3, yi + 41.2, 72, 6.2)
    # QR (verificação / leitura óptica)
    _desenhar_qr(c, _payload_qr(escola, aluno, config, ano, versao), xi + wi - 27.5, yi + 8.5, 24)
    c.setFont(FONTE, 5.8)
    c.setFillColor(CINZA_TEXTO)
    c.drawCentredString((xi + wi - 15.5) * mm, _y(yi + 35.5), 'Leitura óptica / QR')
    c.setFillColor(PRETO)

    # II — Informações da avaliação
    xii, wii = MARGEM + 109, LARG_UTIL - 109
    _caixa(c, xii, yi, wii, hi, 'II   INFORMAÇÕES DA AVALIAÇÃO')
    c.setFont(FONTE_B, 5.8)
    c.setFillColor(CINZA_TEXTO)
    c.drawString((xii + 3) * mm, _y(yi + 9.5), 'TIPO DE AVALIAÇÃO')
    c.setFillColor(PRETO)
    ops = TIPOS_AVALIACAO
    pos = [(xii + 3, yi + 11.5), (xii + 27, yi + 11.5), (xii + 51, yi + 11.5), (xii + 3, yi + 16.3), (xii + 27, yi + 16.3)]
    for (cod, rot), (px, py) in zip(ops, pos):
        _check(c, px, py, rot, cod == config['tipo'], tam=7.3, larg_txt=19)
    _campo(c, xii + 3, yi + 21.5, 31, 'Nº DE PERGUNTAS', str(config['n_perguntas']), 9.5)
    _campo(c, xii + 37, yi + 21.5, 34, 'Nº DE ALTERNATIVAS', f"{config['n_alternativas']} ({LETRAS[0]}–{LETRAS[config['n_alternativas'] - 1]})", 9.5)
    uniforme = len(config['seccoes']) == 1
    cot_txt = formatar_valor(config['seccoes'][0]['cotacao']) if uniforme else 'por secção'
    _campo(c, xii + 3, yi + 30, 31, 'COTAÇÃO / PERGUNTA', cot_txt, 9.5)
    _campo(c, xii + 37, yi + 30, 34, 'COTAÇÃO TOTAL', f"{formatar_valor(config['cotacao_total'])} valores", 9.5)
    dur = f"{config['duracao_min']} min" if config['duracao_min'] else ''
    _campo(c, xii + 3, yi + 38.5, 20, 'DURAÇÃO', dur, 9)
    _campo(c, xii + 25, yi + 38.5, 22, 'DATA', config['data'], 9)
    _campo(c, xii + 49, yi + 38.5, 22, 'HORA / SALA', ' · '.join(x for x in (config['hora_inicio'], config['sala']) if x), 9)

    # III — Disciplina
    yiii, hiii = 97, 36
    _caixa(c, MARGEM, yiii, 106, hiii, 'III   DISCIPLINA')
    nomes = list(config['disciplinas_classe'])
    if config['disciplina'] not in nomes:
        nomes.insert(0, config['disciplina'])
    nomes = nomes[:15]
    col_w = 34.0
    for k, nome in enumerate(nomes):
        cc, rr = divmod(k, 5)
        _check(c, MARGEM + 3 + cc * col_w, yiii + 8 + rr * 5.5, nome, nome == config['disciplina'], tam=7.2, larg_txt=col_w - 6)
    if config['professor']:
        c.setFont(FONTE_I, 6.8)
        c.setFillColor(CINZA_TEXTO)
        c.drawString((MARGEM + 3) * mm, _y(yiii + hiii - 1.6), f"Professor(a): {config['professor']}"[:70])
        c.setFillColor(PRETO)

    # IV — Classificação
    _caixa(c, xii, yiii, wii, hiii, 'IV   CLASSIFICAÇÃO')
    _campo(c, xii + 3, yiii + 6.5, 33, 'ACERTOS (n.º)', '')
    c.setFont(FONTE, 7.5)
    c.drawString((xii + 37) * mm, _y(yiii + 12.2), f"/ {config['n_perguntas']}")
    _campo(c, xii + 3, yiii + 15, 33, 'CORRECÇÃO NORMAL (valores)', '')
    _campo(c, xii + 38, yiii + 15, 33, 'RECORRECÇÃO (valores)', '')
    _campo(c, xii + 3, yiii + 23.5, 33, 'ASS. DO PROFESSOR', '')
    _campo(c, xii + 38, yiii + 23.5, 33, 'ASS. DO DIRECTOR DE TURMA', '')

    # Instruções + grelha
    _bloco_marcas_exemplo(c, 136)
    if config['instrucao_extra']:
        c.setFont(FONTE_I, 7)
        c.setFillColor(CINZA_TEXTO)
        c.drawString(MARGEM * mm, _y(147.2), config['instrucao_extra'])
        c.setFillColor(PRETO)
    _barra_titulo(c, MARGEM, 148.2, LARG_UTIL, 6.2, 'GRELHA DE RESPOSTAS', 'l', 8.5)
    c.setFillColor(colors.white)
    c.setFont(FONTE, 6.8)
    c.drawRightString((PAG_L - MARGEM - 2) * mm, _y(152.4), 'Cotação: ' + _descricao_cotacao(config))
    c.setFillColor(PRETO)


def _cabecalho_continuacao(c, escola, aluno, config, versao, ate_pergunta, inicio):
    if config['marcas_omr']:
        _desenhar_marcas_omr(c)
    _barra_titulo(c, MARGEM, 11, LARG_UTIL, 7, _titulo_prova(config) + '  (continuação)', 'l', 9)
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
    hoje = datetime.date.today().strftime('%d/%m/%Y')
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(PAG_L * mm, PAG_A * mm))
    c.setTitle(f"Folha de Respostas — {config['disciplina']} — {ROTULO_TIPO[config['tipo']]}")
    c.setAuthor('SIGE')
    c.setSubject('Folha de respostas personalizada')
    paginas = paginas_grelha(config['n_perguntas'])
    for idx, aluno in enumerate(alunos):
        versao = versao_do_aluno(config, idx)
        cod = codigo_folha(escola, aluno, config, ano)
        for p, (ini, fim, cols, linhas, y_ini) in enumerate(paginas):
            if p == 0:
                _pagina_principal(c, escola, logo_reader, ano, aluno, config, versao, cod, p + 1, len(paginas), hoje)
            else:
                _cabecalho_continuacao(c, escola, aluno, config, versao, fim, ini)
            _desenhar_grelha(c, config, ini, fim, cols, linhas, y_ini)
            _rodape(c, cod, p + 1, len(paginas), hoje)
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
    hoje = datetime.date.today().strftime('%d/%m/%Y')

    TNR = 'Times New Roman'
    f_norm = Font(name=TNR, size=10)
    f_bold = Font(name=TNR, size=10, bold=True)
    f_peq = Font(name=TNR, size=8, color='4A5361')
    f_titulo = Font(name=TNR, size=11, bold=True, color='FFFFFF')
    f_bolha = Font(name='Segoe UI Symbol', size=10)
    f_bolha_cheia = Font(name='Segoe UI Symbol', size=10, color='000000', bold=True)
    fundo_azul = PatternFill('solid', start_color='14325C')
    fundo_cinza = PatternFill('solid', start_color='F1F4F8')
    fino = Side(style='thin', color='8A94A3')
    borda = Border(left=fino, right=fino, top=fino, bottom=fino)
    sob = Border(bottom=fino)
    centro = Alignment(horizontal='center', vertical='center', wrap_text=True)
    esq = Alignment(horizontal='left', vertical='center', wrap_text=True)
    NCOL = 28
    ALT = 'ⒶⒷⒸⒹⒺⒻ'
    n = config['n_perguntas']
    n_alt = config['n_alternativas']

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    existentes = []

    def barra(ws, r, c1, c2, texto, alinh=centro):
        ws.merge_cells(start_row=r, start_column=c1, end_row=r, end_column=c2)
        cel = ws.cell(row=r, column=c1, value=texto)
        for cc in range(c1, c2 + 1):
            ws.cell(row=r, column=cc).fill = fundo_azul
        cel.font = f_titulo
        cel.alignment = alinh
        ws.row_dimensions[r].height = 18

    def par(ws, r, c1, c2, rotulo, valor, c_val_ini=None, c_val_fim=None):
        """Rótulo (fundo cinza) em c1..c2 e valor em c_val_ini..c_val_fim, com bordas."""
        ws.merge_cells(start_row=r, start_column=c1, end_row=r, end_column=c2)
        a = ws.cell(row=r, column=c1, value=rotulo)
        a.font = f_bold
        a.alignment = esq
        for cc in range(c1, c2 + 1):
            ws.cell(row=r, column=cc).fill = fundo_cinza
            ws.cell(row=r, column=cc).border = borda
        v1, v2 = c_val_ini or c2 + 1, c_val_fim or c2 + 1
        ws.merge_cells(start_row=r, start_column=v1, end_row=r, end_column=v2)
        b = ws.cell(row=r, column=v1, value=valor if valor not in (None, '') else None)
        b.font = f_bold
        b.alignment = esq
        for cc in range(v1, v2 + 1):
            ws.cell(row=r, column=cc).border = borda

    def preparar(ws):
        for i in range(1, NCOL + 1):
            ws.column_dimensions[col_l(i)].width = 4.6
        ws.sheet_view.showGridLines = False
        ws.page_setup.orientation = 'portrait'
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr = openpyxl.worksheet.properties.PageSetupProperties(fitToPage=True)
        ws.page_margins.left = ws.page_margins.right = 0.4
        ws.page_margins.top = ws.page_margins.bottom = 0.4
        ws.print_options.horizontalCentered = True

    def cabecalho(ws, titulo):
        if logo_png:
            img = XLImage(io.BytesIO(logo_png))
            img.width = img.height = 74
            ws.add_image(img, 'A1')
        for r in range(1, 5):
            ws.row_dimensions[r].height = 19
        linhas = [
            ('REPÚBLICA DE MOÇAMBIQUE', f_bold),
            (' · '.join(x for x in (f"Província de {escola['provincia']}" if escola.get('provincia') else '',
                                    f"Distrito de {escola['distrito']}" if escola.get('distrito') else '') if x), f_norm),
            (escola.get('nome') or '', Font(name=TNR, size=12, bold=True)),
            (' · '.join(x for x in ((f"Código da escola: {escola['codigo']}" if escola.get('codigo') else ''),
                                    f'Ano lectivo: {ano}', 'Sector Pedagógico') if x), f_norm),
        ]
        for i, (txt, fnt) in enumerate(linhas, start=1):
            ws.merge_cells(start_row=i, start_column=6, end_row=i, end_column=23)
            cel = ws.cell(row=i, column=6, value=txt)
            cel.font = fnt
            cel.alignment = Alignment(horizontal='center', vertical='center')
        barra(ws, 5, 1, NCOL, titulo, esq)

    # ---------------- folhas dos alunos ----------------
    for idx, aluno in enumerate(alunos):
        al = aluno or {}
        versao = versao_do_aluno(config, idx)
        rotulo_folha = f"{al.get('numero', idx + 1):02d} {al.get('apelido', '')} {al.get('nome', '')}".strip() if aluno else f'Branco {idx + 1:03d}'
        ws = wb.create_sheet(nome_folha(rotulo_folha, padrao=f'Folha {idx + 1}', existentes=existentes))
        existentes.append(ws.title)
        preparar(ws)
        cabecalho(ws, _titulo_prova(config) + (f'   ·   VERSÃO {versao}' if versao else ''))
        # QR no canto superior direito
        qr = XLImage(io.BytesIO(_png_qr(_payload_qr(escola, aluno, config, ano, versao))))
        qr.width = qr.height = 76
        ws.add_image(qr, 'X1')
        ws.row_dimensions[6].height = 5

        barra(ws, 7, 1, 15, 'I   DADOS DO ALUNO', esq)
        barra(ws, 7, 17, 28, 'II   INFORMAÇÕES DA AVALIAÇÃO', esq)
        par(ws, 8, 1, 3, 'APELIDO', al.get('apelido'), 4, 15)
        par(ws, 9, 1, 3, 'NOME', al.get('nome'), 4, 15)
        par(ws, 10, 1, 3, 'CLASSE', al.get('classe'), 4, 7)
        par(ws, 10, 8, 9, 'TURMA', al.get('turma'), 10, 12)
        par(ws, 10, 13, 13, 'Nº', al.get('numero'), 14, 15)
        par(ws, 11, 1, 3, 'CÓDIGO', al.get('codigo'), 4, 15)
        ws.merge_cells('A12:O13')
        if config['codigo_barras'] and al.get('codigo'):
            bar = XLImage(io.BytesIO(_png_codigo_barras(al['codigo'])))
            bar.width, bar.height = 280, 38
            ws.add_image(bar, 'D12')
        for r in (12, 13):
            ws.row_dimensions[r].height = 15

        ws.merge_cells('Q8:AB8')
        ws['Q8'] = 'TIPO DE AVALIAÇÃO'
        ws['Q8'].font = f_bold
        ws['Q8'].fill = fundo_cinza
        ws.merge_cells('Q9:AB9')
        ws['Q9'] = '   '.join(('●' if cod == config['tipo'] else '○') + ' ' + rot for cod, rot in TIPOS_AVALIACAO)
        ws['Q9'].font = Font(name='Segoe UI Symbol', size=9, bold=True)
        ws['Q9'].alignment = esq
        uniforme = len(config['seccoes']) == 1
        par(ws, 10, 17, 20, 'Nº PERGUNTAS', n, 21, 22)
        par(ws, 10, 23, 26, 'ALTERNATIVAS', n_alt, 27, 28)
        par(ws, 11, 17, 20, 'COTAÇÃO/PERG.', formatar_valor(config['seccoes'][0]['cotacao']) if uniforme else 'por secção', 21, 22)
        par(ws, 11, 23, 26, 'TOTAL (val.)', formatar_valor(config['cotacao_total']), 27, 28)
        par(ws, 12, 17, 20, 'DURAÇÃO (min)', config['duracao_min'] or None, 21, 22)
        par(ws, 12, 23, 26, 'DATA', config['data'], 27, 28)
        par(ws, 13, 17, 20, 'HORA / SALA', ' · '.join(x for x in (config['hora_inicio'], config['sala']) if x), 21, 28)

        ws.row_dimensions[14].height = 5
        barra(ws, 15, 1, 15, 'III   DISCIPLINA', esq)
        barra(ws, 15, 17, 28, 'IV   CLASSIFICAÇÃO', esq)
        nomes = list(config['disciplinas_classe'])
        if config['disciplina'] not in nomes:
            nomes.insert(0, config['disciplina'])
        nomes = nomes[:15]
        for k, nome in enumerate(nomes):
            cc, rr = divmod(k, 5)
            c1 = 1 + cc * 5
            ws.merge_cells(start_row=16 + rr, start_column=c1, end_row=16 + rr, end_column=c1 + 4)
            marcado = nome == config['disciplina']
            cel = ws.cell(row=16 + rr, column=c1, value=('☑ ' if marcado else '☐ ') + nome)
            cel.font = Font(name='Segoe UI Symbol', size=9, bold=marcado)
            cel.alignment = esq
        par(ws, 16, 17, 22, 'ACERTOS (n.º)', None, 23, 25)
        ws.cell(row=16, column=26, value=f'/ {n}').font = f_norm
        par(ws, 17, 17, 22, 'CORRECÇÃO NORMAL (val.)', None, 23, 28)
        par(ws, 18, 17, 22, 'RECORRECÇÃO (val.)', None, 23, 28)
        par(ws, 19, 17, 22, 'ASS. PROFESSOR', None, 23, 28)
        par(ws, 20, 17, 22, 'ASS. DIR. TURMA', None, 23, 28)
        ws.row_dimensions[21].height = 5

        ws.merge_cells('A22:AB22')
        ws['A22'] = ('COMO PREENCHER: use esferográfica azul ou preta e pinte a bolha completamente (●); não rasure. '
                     + config['instrucao_extra']).strip()
        ws['A22'].font = f_peq
        ws['A22'].alignment = esq
        ws['A22'].fill = fundo_cinza
        ws.row_dimensions[22].height = 24
        barra(ws, 23, 1, NCOL, 'GRELHA DE RESPOSTAS   —   Cotação: ' + _descricao_cotacao(config), esq)

        _grelha_excel(ws, config, 25, None, NCOL, f_norm, f_bold, f_bolha, f_bolha_cheia, fundo_azul, fundo_cinza, borda, centro, ALT)
        ws.print_area = f'A1:{col_l(NCOL)}{ws.max_row + 1}'

    # ---------------- Resumo (sem fórmulas) ----------------
    reais = [(i, a) for i, a in enumerate(alunos) if a]
    if len(reais) > 1:
        ws = wb.create_sheet('Resumo')
        ws.sheet_view.showGridLines = False
        cab = ['Nº', 'Código', 'Apelido', 'Nome', 'Classe', 'Turma', 'Versão', 'Pontos obtidos', 'Nota (0–20)', 'Observações']
        larg = [5, 24, 20, 30, 12, 12, 8, 14, 12, 28]
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
            vals = [a.get('numero'), a.get('codigo'), a.get('apelido'), a.get('nome'), a.get('classe'), a.get('turma'),
                    versao_do_aluno(config, i) or None, None, None, None]
            for cidx, v in enumerate(vals, start=1):
                cel = ws.cell(row=r, column=cidx, value=v)
                cel.font = f_norm
                cel.border = borda
                cel.alignment = centro if cidx in (1, 5, 6, 7, 8, 9) else esq
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
            barra(ws, 7, 1, NCOL, 'Cotação: ' + _descricao_cotacao(config), esq)
            _grelha_excel(ws, config, 9, g, NCOL, f_norm, f_bold, f_bolha, f_bolha_cheia, fundo_azul, fundo_cinza, borda, centro, ALT)
            ws.print_area = f'A1:{col_l(NCOL)}{ws.max_row + 1}'

    return guardar_xlsx_seguro(wb, embelezar=False), len(alunos)


def _grelha_excel(ws, config, linha_ini, gabarito, ncol, f_norm, f_bold, f_bolha, f_bolha_cheia,
                  fundo_azul, fundo_cinza, borda, centro, ALT):
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter as col_l
    n = config['n_perguntas']
    n_alt = config['n_alternativas']
    cols, linhas = layout_grelha(n, 999)
    cols = max(1, min(cols, 4))
    linhas = math.ceil(n / cols)
    linhas = math.ceil(linhas / 5) * 5
    bw = ncol // cols
    passo = max(1, (bw - 1) // n_alt)
    cols_usadas = math.ceil(n / linhas)
    # cabeçalho
    for b in range(cols_usadas):
        c0 = 1 + b * bw
        cel = ws.cell(row=linha_ini, column=c0, value='Perg.')
        cel.font = Font(name='Times New Roman', size=9, bold=True, color='FFFFFF')
        cel.fill = fundo_azul
        cel.alignment = centro
        ws.merge_cells(start_row=linha_ini, start_column=c0 + 1, end_row=linha_ini, end_column=c0 + bw - 1)
        h = ws.cell(row=linha_ini, column=c0 + 1, value='Alternativas')
        h.font = Font(name='Times New Roman', size=9, bold=True, color='FFFFFF')
        h.alignment = centro
        for cc in range(c0 + 1, c0 + bw):
            ws.cell(row=linha_ini, column=cc).fill = fundo_azul
    ws.row_dimensions[linha_ini].height = 16
    for r in range(linhas):
        pos = linha_ini + 1 + r + r // 5
        if r % 5 == 0 and r > 0:
            ws.row_dimensions[pos - 1].height = 5
        ws.row_dimensions[pos].height = 21
        for b in range(cols_usadas):
            q = b * linhas + r
            if q >= n:
                continue
            c0 = 1 + b * bw
            num = ws.cell(row=pos, column=c0, value=q + 1)
            num.font = f_bold
            num.alignment = centro
            num.border = borda
            if (r // 5) % 2 == 0:
                for cc in range(c0, c0 + bw):
                    ws.cell(row=pos, column=cc).fill = fundo_cinza
            for i in range(n_alt):
                cc = c0 + 1 + i * passo
                if passo > 1:
                    ws.merge_cells(start_row=pos, start_column=cc, end_row=pos, end_column=cc + passo - 1)
                marcada = bool(gabarito and gabarito[q] == LETRAS[i])
                cel = ws.cell(row=pos, column=cc, value='●' if marcada else ALT[i])
                cel.font = f_bolha_cheia if marcada else f_bolha
                cel.alignment = centro
