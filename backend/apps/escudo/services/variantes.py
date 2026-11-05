"""Provas com variantes: cada cópia recebe valores diferentes e tem gabarito próprio.

Modelo (JSON):
    {"titulo": "...", "escola": "...", "disciplina": "...", "classe": "...", "duracao": "45 minutos", "professor": "...",
     "variaveis": {"R1": [2, 3, 4], "U": {"min": 6, "max": 18, "passo": 3}},
     "restricoes": ["R1 != R2"],
     "perguntas": [{"cotacao": 4, "espaco": 110,
                    "texto": "Duas resistências de {R1} Ω e {R2} Ω em paralelo a {U} V. Calcule a corrente total.",
                    "resposta": "R_eq = {R1*R2/(R1+R2):.2f} Ω; I = {U*(R1+R2)/(R1*R2):.2f} A"}]}

Em texto e resposta, {expressão} ou {expressão:.2f} calcula-se com os valores da cópia; {{ e }} são chaves literais.
Os valores de cada cópia saem de (código da prova, n.º da cópia), por isso são sempre os mesmos e nunca se repetem
enquanto houver combinações por usar.
"""
import ast
import io
import json
import math
import operator
import random
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer

MAX_MODELO = 60_000
MAX_PERGUNTAS = 40
MAX_DOMINIO = 1000
MAX_EXPR = 200

OPERADORES = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
              ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}
COMPARACOES = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt, ast.LtE: operator.le,
               ast.Gt: operator.gt, ast.GtE: operator.ge}
FUNCOES = {"sqrt": math.sqrt, "abs": abs, "round": round, "min": min, "max": max, "sin": math.sin, "cos": math.cos,
           "tan": math.tan, "radians": math.radians, "degrees": math.degrees, "log10": math.log10, "ln": math.log}
CONSTANTES = {"pi": math.pi, "e": math.e}
RE_CAMPO = re.compile(r"\{\{|\}\}|\{([^{}]+)\}")
RE_FORMATO = re.compile(r"^(\d+)?(\.\d+)?[fgd]$")
TRANSLITERACAO = {"Ω": "ohm", "Δ": "Delta", "μ": "u", "λ": "lambda", "π": "pi", "α": "alfa", "β": "beta", "θ": "teta",
                  "ρ": "ro", "ε": "eps", "φ": "fi", "→": "->", "≈": "~", "≤": "<=", "≥": ">=", "−": "-", "×": "x"}


class ErroModelo(ValueError):
    """O modelo de variantes tem um erro que o professor pode corrigir."""


# ---------------------------------------------------------------- expressões seguras
def _avaliar(expr, ambiente):
    if len(expr) > MAX_EXPR:
        raise ErroModelo(f"Expressão demasiado longa: «{expr[:40]}…»")
    try:
        arvore = ast.parse(expr.strip(), mode="eval")
    except SyntaxError:
        raise ErroModelo(f"Expressão inválida: «{expr}»") from None

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
            return n.value
        if isinstance(n, ast.Name):
            if n.id in ambiente:
                return ambiente[n.id]
            if n.id in CONSTANTES:
                return CONSTANTES[n.id]
            raise ErroModelo(f"Variável desconhecida «{n.id}» em «{expr}». Declara-a em «variaveis».")
        if isinstance(n, ast.BinOp) and type(n.op) in OPERADORES:
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Pow) and (abs(b) > 12 or abs(a) > 1e6):
                raise ErroModelo(f"Potência demasiado grande em «{expr}».")
            try:
                return OPERADORES[type(n.op)](a, b)
            except ZeroDivisionError:
                raise ErroModelo(f"Divisão por zero em «{expr}» com {ambiente}.") from None
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd, ast.Not)):
            v = ev(n.operand)
            return -v if isinstance(n.op, ast.USub) else v if isinstance(n.op, ast.UAdd) else (not v)
        if isinstance(n, ast.Compare) and all(type(o) in COMPARACOES for o in n.ops):
            esquerda = ev(n.left)
            for op, direita in zip(n.ops, n.comparators):
                d = ev(direita)
                if not COMPARACOES[type(op)](esquerda, d):
                    return False
                esquerda = d
            return True
        if isinstance(n, ast.BoolOp):
            valores = [ev(v) for v in n.values]
            return all(valores) if isinstance(n.op, ast.And) else any(valores)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in FUNCOES \
                and not n.keywords and len(n.args) <= 3:
            try:
                return FUNCOES[n.func.id](*[ev(a) for a in n.args])
            except (ValueError, ZeroDivisionError, OverflowError):
                raise ErroModelo(f"Não foi possível calcular «{expr}» com {ambiente}.") from None
        raise ErroModelo(f"Expressão não permitida: «{expr}». Só há contas, comparações e "
                         f"{', '.join(sorted(FUNCOES))}.")
    return ev(arvore)


def formatar(valor, formato=None):
    """Número com vírgula decimal. Sem formato: inteiro se for inteiro, senão até 6 algarismos significativos."""
    if formato:
        texto = format(int(round(valor)), formato) if formato.endswith("d") else format(valor, formato)
    elif isinstance(valor, float) and valor.is_integer():
        texto = str(int(valor))
    elif isinstance(valor, float):
        texto = f"{valor:.6g}"
    else:
        texto = str(valor)
    return texto.replace(".", ",")


def preencher(texto, valores):
    """Substitui {expressão[:formato]} pelos valores da cópia."""
    def troca(m):
        if m.group(0) == "{{":
            return "{"
        if m.group(0) == "}}":
            return "}"
        campo = m.group(1)
        expr, _, formato = campo.rpartition(":")
        if not expr or not RE_FORMATO.match(formato):
            expr, formato = campo, None
        return formatar(_avaliar(expr, valores), formato)
    return RE_CAMPO.sub(troca, texto)


# ---------------------------------------------------------------- modelo
def _dominio(nome, spec):
    if isinstance(spec, list):
        valores = spec
    elif isinstance(spec, dict) and {"min", "max", "passo"} <= set(spec):
        try:
            minimo, maximo, passo = float(spec["min"]), float(spec["max"]), float(spec["passo"])
        except (TypeError, ValueError):
            raise ErroModelo(f"Variável «{nome}»: min, max e passo devem ser números.") from None
        if passo <= 0 or maximo < minimo or (maximo - minimo) / passo > MAX_DOMINIO:
            raise ErroModelo(f"Variável «{nome}»: intervalo inválido (passo > 0, máximo >= mínimo, até {MAX_DOMINIO} valores).")
        valores = [round(minimo + i * passo, 10) for i in range(int(round((maximo - minimo) / passo)) + 1)]
    else:
        raise ErroModelo(f"Variável «{nome}»: usa uma lista [2, 3, 4] ou {{\"min\": 1, \"max\": 9, \"passo\": 2}}.")
    if not valores or len(valores) > MAX_DOMINIO or not all(
            isinstance(v, (int, float)) and not isinstance(v, bool) for v in valores):
        raise ErroModelo(f"Variável «{nome}»: precisa de 1 a {MAX_DOMINIO} números.")
    return [int(v) if float(v).is_integer() else v for v in valores]


def validar_modelo(dados):
    """Valida o modelo e devolve-o normalizado. Ensaia o texto e as respostas com várias cópias para apanhar erros cedo."""
    if not isinstance(dados, dict):
        raise ErroModelo("O modelo deve ser um objeto JSON.")
    perguntas = dados.get("perguntas")
    if not isinstance(perguntas, list) or not 1 <= len(perguntas) <= MAX_PERGUNTAS:
        raise ErroModelo(f"O modelo precisa de 1 a {MAX_PERGUNTAS} perguntas.")
    variaveis = dados.get("variaveis") or {}
    if not isinstance(variaveis, dict):
        raise ErroModelo("«variaveis» deve ser um objeto.")
    modelo = {
        "titulo": str(dados.get("titulo") or "Prova")[:120],
        "escola": str(dados.get("escola") or "")[:120], "professor": str(dados.get("professor") or "")[:80],
        "disciplina": str(dados.get("disciplina") or "")[:60], "classe": str(dados.get("classe") or "")[:30],
        "duracao": str(dados.get("duracao") or "")[:30],
        "variaveis": {}, "restricoes": [], "perguntas": [],
    }
    for nome, spec in variaveis.items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,15}", nome) or nome in CONSTANTES or nome in FUNCOES:
            raise ErroModelo(f"Nome de variável inválido: «{nome}».")
        modelo["variaveis"][nome] = _dominio(nome, spec)
    restricoes = dados.get("restricoes") or []
    if not isinstance(restricoes, list) or not all(isinstance(r, str) for r in restricoes):
        raise ErroModelo("«restricoes» deve ser uma lista de expressões, ex.: [\"R1 != R2\"].")
    modelo["restricoes"] = restricoes
    for i, q in enumerate(perguntas, 1):
        if not isinstance(q, dict) or not str(q.get("texto") or "").strip():
            raise ErroModelo(f"A pergunta {i} precisa de «texto».")
        resposta = q.get("resposta") or ""
        if isinstance(resposta, list):
            resposta = "\n".join(map(str, resposta))
        try:
            espaco = min(max(float(q.get("espaco", 110)), 20), 300)
            cotacao = q.get("cotacao")
            cotacao = None if cotacao in (None, "") else float(cotacao)
        except (TypeError, ValueError):
            raise ErroModelo(f"A pergunta {i}: «espaco» e «cotacao» devem ser números.") from None
        modelo["perguntas"].append({"texto": str(q["texto"]), "resposta": str(resposta), "espaco": espaco, "cotacao": cotacao})
    # ensaio: 40 cópias; qualquer erro de nome, divisão por zero ou restrição impossível aparece já
    for serial in range(1, 41):
        valores = escolher_valores(modelo, "ENSAIO00", serial)
        for i, q in enumerate(modelo["perguntas"], 1):
            for campo in ("texto", "resposta"):
                try:
                    preencher(q[campo], valores)
                except ErroModelo as e:
                    raise ErroModelo(f"Pergunta {i} ({campo}): {e}") from None
    return modelo


def carregar_modelo(bruto):
    if len(bruto) > MAX_MODELO:
        raise ErroModelo(f"O modelo excede {MAX_MODELO // 1000} KB.")
    try:
        return validar_modelo(json.loads(bruto.decode("utf-8-sig")))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ErroModelo(f"O ficheiro não é um JSON válido ({e}).") from None


def combinacoes(modelo):
    return math.prod(len(d) for d in modelo["variaveis"].values()) if modelo["variaveis"] else 1


def escolher_valores(modelo, pid, serial):
    """Valores da cópia `serial`: determinísticos e, enquanto houver combinações livres, diferentes das cópias anteriores."""
    usados = set()
    valores = {}
    for k in range(1, serial + 1):
        rng = random.Random(f"{pid}:{k}")
        escolhido, alternativa = None, None
        for _ in range(300):
            cand = {nome: rng.choice(dominio) for nome, dominio in modelo["variaveis"].items()}
            if not all(_avaliar(r, cand) for r in modelo["restricoes"]):
                continue
            chave = tuple(cand.values())
            if chave not in usados:
                escolhido = cand
                break
            alternativa = alternativa or cand
        valores = escolhido if escolhido is not None else alternativa  # {} (sem variáveis) é um resultado válido
        if valores is None:
            raise ErroModelo("As restrições não deixam nenhuma combinação válida das variáveis.")
        usados.add(tuple(valores.values()))
    return valores


# ---------------------------------------------------------------- PDF
_FONTES = None


def _fontes():
    """(normal, negrito, ttf?): Arial/DejaVu se existirem (têm Ω, acentos...), senão Helvetica sem os símbolos gregos."""
    global _FONTES
    if _FONTES:
        return _FONTES
    for normal, negrito in (("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
                            ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
                            ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf")):
        if Path(normal).exists() and Path(negrito).exists():
            pdfmetrics.registerFont(TTFont("PV-Sans", normal))
            pdfmetrics.registerFont(TTFont("PV-Sans-Bold", negrito))
            _FONTES = ("PV-Sans", "PV-Sans-Bold", True)
            return _FONTES
    _FONTES = ("Helvetica", "Helvetica-Bold", False)
    return _FONTES


def _texto_pdf(texto, ttf):
    if not ttf:
        for k, v in TRANSLITERACAO.items():
            texto = texto.replace(k, v if k != "Ω" else " ohm")
        texto = texto.encode("cp1252", "replace").decode("cp1252")
    return escape(texto).replace("\n", "<br/>")


def _estilos():
    normal, negrito, ttf = _fontes()
    return {
        "ttf": ttf, "normal": normal, "negrito": negrito,
        "titulo": ParagraphStyle("t", fontName=negrito, fontSize=14, leading=18, spaceAfter=2),
        "sub": ParagraphStyle("s", fontName=normal, fontSize=10.5, leading=14, textColor="#333333"),
        "campo": ParagraphStyle("c", fontName=normal, fontSize=10, leading=14, spaceBefore=8, spaceAfter=16),
        "pergunta": ParagraphStyle("p", fontName=normal, fontSize=11.5, leading=16, leftIndent=0),
        "nota": ParagraphStyle("n", fontName=normal, fontSize=9, leading=12, textColor="#555555"),
        "gab": ParagraphStyle("g", fontName=normal, fontSize=10.5, leading=14),
        "gabt": ParagraphStyle("gt", fontName=negrito, fontSize=11, leading=15, spaceBefore=10, spaceAfter=3),
    }


def pdf_copia(modelo, pid, serial):
    """PDF A4 da cópia `serial`, com a margem direita livre para os QR das perguntas."""
    est = _estilos()
    valores = escolher_valores(modelo, pid, serial)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=60, rightMargin=88, topMargin=62, bottomMargin=52,
                            title=modelo["titulo"], author=modelo["professor"] or "Cofre de Provas")
    t = lambda s: _texto_pdf(s, est["ttf"])  # noqa: E731
    historia = []
    if modelo["escola"]:
        historia.append(Paragraph(t(modelo["escola"]), est["titulo"]))
    historia.append(Paragraph(t(modelo["titulo"]), est["sub"]))
    detalhes = " · ".join(x for x in (modelo["disciplina"], modelo["classe"], modelo["duracao"] and f"Duração: {modelo['duracao']}",
                                      modelo["professor"] and f"Professor: {modelo['professor']}") if x)
    if detalhes:
        historia.append(Paragraph(t(detalhes), est["sub"]))
    historia.append(Paragraph("Nome: ________________________ &nbsp; N.º: ____ &nbsp; Turma: ______ &nbsp; Data: __/__/____", est["campo"]))
    for i, q in enumerate(modelo["perguntas"], 1):
        cot = f" <font size=9 color='#555555'>({formatar(q['cotacao'])} valores)</font>" if q["cotacao"] else ""
        historia.append(KeepTogether([Paragraph(f"<b>{i}.</b> {t(preencher(q['texto'], valores))}{cot}", est["pergunta"]),
                                      Spacer(1, q["espaco"])]))
    doc.build(historia)
    return buf.getvalue()


def pdf_gabarito(modelo, pid, copias):
    """PDF para o professor: valores e respostas de cada cópia (1..copias)."""
    est = _estilos()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=50, rightMargin=50, topMargin=50, bottomMargin=45,
                            title=f"Gabarito das cópias: {modelo['titulo']}")
    t = lambda s: _texto_pdf(s, est["ttf"])  # noqa: E731
    historia = [Paragraph(t(f"Gabarito das cópias · {modelo['titulo']}"), est["titulo"]),
                Paragraph(t(f"Código da prova {pid} · {copias} cópia(s). Só para o professor."), est["nota"]), Spacer(1, 6)]
    for serial in range(1, copias + 1):
        valores = escolher_valores(modelo, pid, serial)
        vars_txt = ", ".join(f"{k} = {formatar(v)}" for k, v in valores.items()) or "sem variáveis"
        bloco = [Paragraph(t(f"Cópia {serial:03d}  ({pid}-{serial:03d})"), est["gabt"]), Paragraph(t(vars_txt), est["nota"])]
        for i, q in enumerate(modelo["perguntas"], 1):
            resposta = preencher(q["resposta"], valores) if q["resposta"].strip() else "(sem resposta no modelo)"
            bloco.append(Paragraph(f"<b>{q.get('rotulo') or i})</b> {t(resposta)}", est["gab"]))
        historia.append(KeepTogether(bloco))
    doc.build(historia)
    return buf.getvalue()
