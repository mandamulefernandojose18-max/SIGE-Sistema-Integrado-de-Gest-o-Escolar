"""Variantes a partir do Word: o professor escreve {R1}, {U/R1:.2f}… no .docx e define as variáveis no ecrã.

Cada cópia sai com valores próprios (os mesmos de `variantes.escolher_valores`): o .docx é preenchido e convertido
para PDF, e o gabarito de cada cópia é calculado a partir das respostas indicadas.
"""
import io
import random
import re

from . import variantes
from .variantes import ErroModelo

MAX_VARIAVEIS = 20
RE_VARIAVEL = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]{0,15})\s*=\s*(.+?)\s*$")
RE_INTERVALO = re.compile(r"^(-?[\d.,]+)\s*(?:\.\.|a|até)\s*(-?[\d.,]+)(?:\s*(?::|passo)\s*([\d.,]+))?$", re.IGNORECASE)
RE_RESPOSTA = re.compile(r"^\s*(\d{1,3}(?:\.\d{1,2})?)\s*[:)\-–]\s*(.+?)\s*$")


def _numero(texto):
    try:
        return float(texto.strip().replace(",", "."))
    except ValueError:
        raise ErroModelo(f"«{texto.strip()}» não é um número.") from None


def ler_variaveis(texto):
    """Linhas «R1 = 2 a 10», «U = 6..24:6» (intervalo e passo) ou «k = 1,5; 2; 2,5» (lista com ponto e vírgula)."""
    variaveis = {}
    for n, linha in enumerate((texto or "").splitlines(), 1):
        if not linha.strip() or linha.strip().startswith("#"):
            continue
        m = RE_VARIAVEL.match(linha)
        if not m:
            raise ErroModelo(f"Variáveis, linha {n}: escreve «NOME = 2 a 10», «NOME = 2 a 10 passo 2» ou «NOME = 1; 2; 5».")
        nome, valor = m.groups()
        intervalo = RE_INTERVALO.match(valor)
        if intervalo:
            spec = {"min": _numero(intervalo.group(1)), "max": _numero(intervalo.group(2)),
                    "passo": _numero(intervalo.group(3)) if intervalo.group(3) else 1}
        else:
            spec = [_numero(v) for v in valor.split(";") if v.strip()]
        if nome in variaveis:
            raise ErroModelo(f"A variável «{nome}» está definida duas vezes.")
        variaveis[nome] = spec
    if len(variaveis) > MAX_VARIAVEIS:
        raise ErroModelo(f"No máximo {MAX_VARIAVEIS} variáveis.")
    return variaveis


def ler_respostas(texto):
    """Linhas «3: I = {U/R1:.2f} A» (número da questão e resposta com as mesmas expressões do Word)."""
    perguntas = []
    for n, linha in enumerate((texto or "").splitlines(), 1):
        if not linha.strip():
            continue
        m = RE_RESPOSTA.match(linha)
        if not m:
            raise ErroModelo(f"Respostas, linha {n}: escreve «número da questão: resposta», ex.: «3: I = {{U/R1:.2f}} A».")
        perguntas.append({"rotulo": m.group(1), "texto": f"Questão {m.group(1)}", "resposta": m.group(2),
                          "espaco": 0, "cotacao": None})
    return perguntas


# ---------------------------------------------------------------- .docx
def _paragrafos(doc):
    """Todos os parágrafos do documento: corpo, tabelas (incluindo aninhadas), cabeçalhos e rodapés."""
    def de(contentor):
        for p in contentor.paragraphs:
            yield p
        for tabela in getattr(contentor, "tables", []):
            for linha in tabela.rows:
                for celula in linha.cells:
                    yield from de(celula)
    yield from de(doc)
    for seccao in doc.sections:
        for parte in (seccao.header, seccao.footer, seccao.first_page_header, seccao.first_page_footer):
            yield from de(parte)


_M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"


def _nos_texto(p):
    """Nós de texto do parágrafo, por ordem: texto normal (w:t) e texto dentro de equações do Word (m:t)."""
    return [t for t in p._p.iter(_W_TEXTO, _M + "t")]


def _texto_campos(p):
    return "".join(t.text or "" for t in _nos_texto(p))


def campos_docx(dados):
    """Textos dos parágrafos que têm campos {…} (também dentro de equações)."""
    from docx import Document
    doc = Document(io.BytesIO(dados))
    return [t for t in (_texto_campos(p) for p in _paragrafos(doc)) if variantes.RE_CAMPO.search(t)]


def preencher_docx(dados, valores):
    """Devolve o .docx com os campos {…} substituídos pelos valores da cópia.

    O Word parte o texto em «runs» à vontade (um campo pode ficar dividido), por isso a troca trabalha sobre o texto
    do parágrafo todo, mas escreve só nos nós de texto: o valor vai para o nó onde o campo começa e o resto do campo
    é apagado dos nós seguintes. Equações (OMML, MathType, imagens) e a formatação ficam onde estavam.
    """
    from docx import Document
    doc = Document(io.BytesIO(dados))
    for p in _paragrafos(doc):
        nos = _nos_texto(p)
        texto = "".join(t.text or "" for t in nos)
        if not variantes.RE_CAMPO.search(texto):
            continue
        limites, ini = [], 0
        for t in nos:
            limites.append((ini, ini + len(t.text or "")))
            ini = limites[-1][1]
        novos = [t.text or "" for t in nos]
        for m in reversed(list(variantes.RE_CAMPO.finditer(texto))):
            valor = variantes.preencher(m.group(0), valores)
            primeiro = True
            for k, (a, b) in enumerate(limites):
                de, ate = max(a, m.start()), min(b, m.end())
                if de >= ate:
                    continue
                corte = novos[k]
                novos[k] = corte[:de - a] + (valor if primeiro else "") + corte[ate - a:]
                primeiro = False
        for t, novo in zip(nos, novos):
            if t.text != novo:
                t.text = novo
                t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def modelo_word(dados_docx, variaveis_txt, condicoes_txt="", respostas_txt="", titulo="Prova"):
    """Valida o Word com campos e as definições; devolve o modelo (sem o .docx) usado para escolher os valores."""
    campos = campos_docx(dados_docx) if (variaveis_txt or "").strip() else []
    if (variaveis_txt or "").strip() and not campos:
        raise ErroModelo("Definiste variáveis, mas o Word não tem campos como {R1}. Escreve-os no texto da prova.")
    modelo = variantes.validar_modelo({
        "titulo": titulo, "variaveis": ler_variaveis(variaveis_txt),
        "restricoes": [c.strip() for c in (condicoes_txt or "").splitlines() if c.strip()],
        "perguntas": [{"texto": "(Word)", "resposta": ""}],
    })
    modelo["perguntas"] = ler_respostas(respostas_txt)
    modelo["origem"] = "word"
    # ensaio: os campos do Word e as respostas com 40 cópias; erros de nome ou divisões por zero aparecem já
    for serial in range(1, 41):
        valores = variantes.escolher_valores(modelo, "ENSAIO00", serial)
        for texto in campos:
            try:
                variantes.preencher(texto, valores)
            except ErroModelo as e:
                raise ErroModelo(f"No Word, em «{texto[:60]}»: {e}") from None
        for q in modelo["perguntas"]:
            try:
                variantes.preencher(q["resposta"], valores)
            except ErroModelo as e:
                raise ErroModelo(f"Resposta da questão {q['rotulo']}: {e}") from None
    return modelo


# ---------------------------------------------------------------- baralhar perguntas e alternativas
RE_ALTERNATIVA = re.compile(r"^\s*\(?([A-Ea-e])\s*[).]\s*")
RE_LETRA = re.compile(r"^[A-Ea-e]$")
# «3.», «3)», «Questão 3:», seguido de espaço: «1.ª ACS» (um título) não é uma pergunta
RE_PERGUNTA_DOCX = re.compile(r"^(?:(?:quest[ãa]o|pergunta|exerc[íi]cio|problema)\s*)?(\d{1,2})\s*[.):\-–](?=\s)", re.IGNORECASE)
RE_FIM = re.compile(r"^\s*(fim|bom trabalho|boa sorte|bom teste)\b", re.IGNORECASE)
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_W_TEXTO = _W + "t"


def _texto_elemento(el):
    return "".join(t.text or "" for t in el.iter(_W + "t"))


def _trocar_inicio(paragrafo, padrao, novo):
    """Troca o rótulo no início do parágrafo («3.», «B)») sem mexer no resto, se o rótulo estiver no 1.º run."""
    textos = list(paragrafo.iter(_W + "t"))
    for t in textos:
        if (t.text or "").strip():
            m = padrao.match(t.text)
            if m:
                t.text = t.text[:m.start(1)] + novo + t.text[m.end(1):]
                return True
            break
    completo = "".join(x.text or "" for x in textos)  # rótulo partido entre runs: reescreve o texto todo no 1.º
    m = padrao.match(completo)
    if not m or not textos:
        return False
    textos[0].text = completo[:m.start(1)] + novo + completo[m.end(1):]
    for t in textos[1:]:
        t.text = ""
    return True


def _blocos(corpo):
    """Divide o corpo do documento em: cabeçalho, perguntas (cada uma com as suas alternativas e figuras) e final."""
    filhos = [el for el in corpo if el.tag != _W + "sectPr"]
    inicios = [i for i, el in enumerate(filhos) if el.tag == _W + "p" and RE_PERGUNTA_DOCX.match(_texto_elemento(el).strip())]
    if len(inicios) < 2:
        return filhos, [], []
    fim = len(filhos)
    for i in range(inicios[-1] + 1, len(filhos)):
        if filhos[i].tag == _W + "p" and RE_FIM.match(_texto_elemento(filhos[i])):
            fim = i
            break
    perguntas = [filhos[a:b] for a, b in zip(inicios, inicios[1:] + [fim])]
    return filhos[:inicios[0]], perguntas, filhos[fim:]


def _numero_bloco(bloco):
    return RE_PERGUNTA_DOCX.match(_texto_elemento(bloco[0]).strip()).group(1)


RE_EM_LINHA = re.compile(r"(?:(?<=\s)|^)\(?([A-Ea-e])[).]\s")
_M_MATEMATICA = "{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath"


def _em_linha(el):
    """Marcadores «A. », «B. »… de uma linha com várias alternativas (ou None se não for uma linha assim)."""
    marcas = list(RE_EM_LINHA.finditer(_texto_elemento(el)))
    letras = [m.group(1).upper() for m in marcas]
    return marcas if len(marcas) >= 2 and letras == list("ABCDE"[:len(marcas)]) else None


def _grupos_alternativas(bloco):
    """Grupos de parágrafos de alternativas seguidos e em sequência (A, B, C…), um por pergunta; linhas em linha ficam de fora."""
    grupos, atual, ultima = [], [], None

    def fechar():
        if len(atual) >= 2:
            grupos.append(list(atual))

    for el in bloco:
        m = RE_ALTERNATIVA.match(_texto_elemento(el)) if el.tag == _W + "p" and not _em_linha(el) else None
        letra = m.group(1).upper() if m else None
        if letra and atual and letra == chr(ord(ultima) + 1):
            atual.append(el)
            ultima = letra
        else:
            fechar()
            atual, ultima = ([el], letra) if letra == "A" else ([], None)
    fechar()
    return grupos


def _baralhar_em_linha(p, rng):
    """Alternativas na horizontal («A. x    B. y    C. z»): troca o texto das alternativas e mantém a linha, os espaços e a posição.

    Só mexe em parágrafos de texto simples (sem equações nem imagens): se houver, deixa a linha como está.
    """
    marcas = _em_linha(p)
    if not marcas or any(True for _ in p.iter(_M_MATEMATICA)) or any(True for _ in p.iter(_W + "drawing", _W + "object", _W + "pict")):
        return None
    if any(r.find(_W + "tab") is not None or r.find(_W + "br") is not None for r in p.iter(_W + "r")):
        return None  # alinhada com tabulações ou quebras: não se mexe
    nos = list(p.iter(_W_TEXTO))
    texto = "".join(t.text or "" for t in nos)
    itens = []
    for i, m in enumerate(marcas):
        fim = marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)
        corpo = texto[m.end():fim]
        conteudo = corpo.rstrip()
        itens.append((m.group(0), conteudo, corpo[len(conteudo):]))
    ordem = list(range(len(itens)))
    rng.shuffle(ordem)
    novo, letras = texto[:marcas[0].start()], {}
    for k, i in enumerate(ordem):
        marcador, _, espaco = itens[k]
        maiuscula = marcas[k].group(1).isupper()
        letra = "ABCDE"[k]
        novo += re.sub(r"[A-Ea-e]", letra if maiuscula else letra.lower(), marcador, count=1) + itens[i][1] + espaco
        letras["ABCDE"[i]] = letra
    nos[0].text = novo
    nos[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    for t in nos[1:]:
        t.text = ""
    return letras


def baralhar_docx(dados, pid, serial, perguntas=True, alternativas=True):
    """Devolve (docx, mapa) com a ordem das perguntas e das alternativas própria da cópia.

    A cópia 1 fica sempre na ordem original. As perguntas são renumeradas 1, 2, 3… pela nova ordem e as alternativas
    reetiquetadas A, B, C…; `mapa` diz, para cada pergunta original, o novo número e a nova letra de cada alternativa.
    """
    from docx import Document
    doc = Document(io.BytesIO(dados))
    corpo = doc.element.body
    _, blocos, _ = _blocos(corpo)
    mapa = {"perguntas": {}, "alternativas": {}}
    if not blocos:
        return dados, mapa
    rng = random.Random(f"{pid}:{serial}:ordem")
    ordem = list(range(len(blocos)))
    if perguntas and serial != 1:
        rng.shuffle(ordem)
    sect = corpo.find(_W + "sectPr")
    ancora = blocos[0][0].getprevious()
    for el in [el for b in blocos for el in b]:
        corpo.remove(el)
    pos = (list(corpo).index(ancora) + 1) if ancora is not None else 0
    for novo, i in enumerate(ordem, 1):
        bloco = blocos[i]
        original = _numero_bloco(bloco)
        mapa["perguntas"][original] = str(novo)
        _trocar_inicio(bloco[0], RE_PERGUNTA_DOCX, str(novo))
        # alternativas, sem desorganizar a prova: cada grupo de parágrafos seguidos «A. … B. … C. …» baralha-se só dentro de si
        # (nunca se misturam alternativas de perguntas diferentes) e as alternativas em linha («A. x   B. y   C. z») continuam
        # em linha, na mesma posição, só com o texto trocado.
        letras = {}
        if alternativas and serial != 1:
            for grupo in _grupos_alternativas(bloco):
                idx = [bloco.index(a) for a in grupo]
                nova = list(grupo)
                rng.shuffle(nova)
                for k, (lugar, el) in enumerate(zip(idx, nova)):
                    m = RE_ALTERNATIVA.match(_texto_elemento(el))
                    letra_nova = "ABCDE"[k]
                    _trocar_inicio(el, RE_ALTERNATIVA, letra_nova if m.group(1).isupper() else letra_nova.lower())
                    letras[m.group(1).upper()] = letra_nova
                    bloco[lugar] = el
            for el in bloco:
                if el.tag == _W + "p":
                    letras.update(_baralhar_em_linha(el, rng) or {})
        mapa["alternativas"][original] = letras
        for el in bloco:
            corpo.insert(pos, el)
            pos += 1
    if sect is not None:
        corpo.remove(sect)
        corpo.append(sect)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue(), mapa


# ---------------------------------------------------------------- chave por cópia e conferência
def chave_copia(modelo, pid, serial, mapa):
    """Respostas da cópia, na numeração da cópia: {n.º na cópia: (n.º original, resposta)}."""
    valores = variantes.escolher_valores(modelo, pid, serial) if modelo.get("variaveis") else {}
    chave = {}
    for q in modelo.get("perguntas", []):
        original = q.get("rotulo")
        resposta = variantes.preencher(q["resposta"], valores).strip()
        if RE_LETRA.match(resposta):
            resposta = mapa.get("alternativas", {}).get(original, {}).get(resposta.upper(), resposta.upper())
        chave[mapa.get("perguntas", {}).get(original, original)] = (original, resposta)
    return chave


def _numero_resposta(texto):
    m = re.search(r"-?\d+(?:[.,]\d+)?", texto or "")
    return float(m.group(0).replace(",", ".")) if m else None


def coincide(dada, certa):
    """Letra igual, ou o primeiro número da resposta igual com 1 % de tolerância."""
    dada, certa = (dada or "").strip(), (certa or "").strip()
    if not dada or not certa:
        return False
    if RE_LETRA.match(certa):
        return dada.upper() == certa.upper()
    a, b = _numero_resposta(dada), _numero_resposta(certa)
    if a is None or b is None:
        return dada.lower() == certa.lower()
    return abs(a - b) <= max(abs(b) * 0.01, 1e-9)


def ler_respostas_aluno(texto):
    """«1: C; 2: 2,5 A» ou uma por linha → {n.º: resposta}."""
    respostas = {}
    for parte in re.split(r"[;\n]", texto or ""):
        m = re.match(r"^\s*(\d{1,3})\s*[:).\-–]\s*(.+?)\s*$", parte)
        if m:
            respostas[m.group(1)] = m.group(2)
    if not respostas:
        raise ErroModelo("Escreve as respostas como «1: C; 2: 2,5 A» (número da questão: resposta).")
    return respostas


def pdf_gabarito_word(modelo, pid, copias, mapas):
    """PDF para o professor: valores e respostas de cada cópia, já na numeração e nas letras de cada cópia."""
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer
    est = variantes._estilos()
    t = lambda s: variantes._texto_pdf(s, est["ttf"])  # noqa: E731
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=50, rightMargin=50, topMargin=50, bottomMargin=45,
                            title=f"Gabarito das cópias: {modelo['titulo']}")
    historia = [Paragraph(t(f"Gabarito das cópias · {modelo['titulo']}"), est["titulo"]),
                Paragraph(t(f"Código da prova {pid} · {copias} cópia(s). Só para o professor."), est["nota"]), Spacer(1, 6)]
    for serial in range(1, copias + 1):
        valores = variantes.escolher_valores(modelo, pid, serial) if modelo.get("variaveis") else {}
        vars_txt = ", ".join(f"{k} = {variantes.formatar(v)}" for k, v in valores.items()) or "mesmos valores em todas as cópias"
        bloco = [Paragraph(t(f"Cópia {serial:03d}  ({pid}-{serial:03d})"), est["gabt"]), Paragraph(t(vars_txt), est["nota"])]
        chave = chave_copia(modelo, pid, serial, mapas.get(serial, {}))
        for n in sorted(chave, key=lambda x: float(x)):
            original, resposta = chave[n]
            origem = f" <i>(original {original})</i>" if original != n else ""
            bloco.append(Paragraph(f"<b>{n})</b> {t(resposta or '(sem resposta)')}{origem}", est["gab"]))
        historia.append(KeepTogether(bloco))
    doc.build(historia)
    return buf.getvalue()
