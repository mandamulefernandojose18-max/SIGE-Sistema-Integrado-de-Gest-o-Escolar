"""LaTeX -> OMML (equações do Word, em duas dimensões: fracções empilhadas, raízes, expoentes, somatórios, sistemas…).

Cobre o subconjunto usado em provas de Matemática, Física e Química. O OMML resultante é lido pelo Word e pelo LibreOffice
(que o desenha no PDF). Nada de texto «linear» tipo a/b ou x^2: cada construção vira o objecto de equação correspondente.
"""
import re
from xml.sax.saxutils import escape

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"

GREGAS = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε", "varepsilon": "ε", "zeta": "ζ", "eta": "η",
    "theta": "θ", "vartheta": "ϑ", "iota": "ι", "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "pi": "π",
    "rho": "ρ", "sigma": "σ", "tau": "τ", "upsilon": "υ", "phi": "φ", "varphi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω",
    "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ", "Pi": "Π", "Sigma": "Σ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω",
}
SIMBOLOS = {
    "cdot": "⋅", "times": "×", "div": "÷", "pm": "±", "mp": "∓", "leq": "≤", "le": "≤", "geq": "≥", "ge": "≥", "neq": "≠",
    "ne": "≠", "approx": "≈", "equiv": "≡", "infty": "∞", "to": "→", "rightarrow": "→", "leftarrow": "←", "Rightarrow": "⇒",
    "Leftarrow": "⇐", "Leftrightarrow": "⇔", "leftrightarrow": "↔", "implies": "⇒", "iff": "⇔", "in": "∈", "notin": "∉",
    "subset": "⊂", "subseteq": "⊆", "cup": "∪", "cap": "∩", "forall": "∀", "exists": "∃", "degree": "°", "circ": "∘",
    "partial": "∂", "nabla": "∇", "angle": "∠", "perp": "⊥", "parallel": "∥", "propto": "∝", "ldots": "…", "dots": "…",
    "cdots": "⋯", "sim": "∼", "cong": "≅", "triangle": "△", "emptyset": "∅", "therefore": "∴", "because": "∵",
    "ll": "≪", "gg": "≫", "mid": "∣", "setminus": "∖", "oplus": "⊕", "otimes": "⊗", "uparrow": "↑", "downarrow": "↓",
    "langle": "⟨", "rangle": "⟩", "ast": "∗", "star": "⋆", "bullet": "•", "prime": "′",
}
ESPACOS = {",": " ", ";": " ", ":": " ", "!": "", " ": " ", "quad": "  ", "qquad": "    "}
FUNCOES = {"sin", "cos", "tan", "cot", "sec", "csc", "arcsin", "arccos", "arctan", "sinh", "cosh", "tanh", "log", "ln", "lg",
           "exp", "max", "min", "det", "gcd", "lim", "sup", "inf", "mod", "arg", "dim", "ker"}
NARIOS = {"sum": "∑", "prod": "∏", "int": "∫", "iint": "∬", "iiint": "∭", "oint": "∮", "bigcup": "⋃", "bigcap": "⋂"}
ACENTOS = {"vec": "⃗", "hat": "^", "bar": "¯", "tilde": "~", "dot": "˙", "ddot": "¨", "overrightarrow": "⃗", "widehat": "^", "widetilde": "~"}
RELACOES = set("=<>") | {"≤", "≥", "≠", "≈", "≡", "→", "⇒", "⇔", "∈", "∼", "≅", "∝", "⊂", "⊆"}
DELIMITADORES = {"(": "(", ")": ")", "[": "[", "]": "]", "|": "|", ".": "", "\\{": "{", "\\}": "}", "\\|": "‖", "\\langle": "⟨",
                 "\\rangle": "⟩", "\\lfloor": "⌊", "\\rfloor": "⌋", "\\lceil": "⌈", "\\rceil": "⌉", "{": "{", "}": "}"}
CONJUNTOS = {"R": "ℝ", "N": "ℕ", "Z": "ℤ", "Q": "ℚ", "C": "ℂ"}
AMBIENTES_MATRIZ = {"pmatrix": ("(", ")"), "bmatrix": ("[", "]"), "vmatrix": ("|", "|"), "Vmatrix": ("‖", "‖"),
                    "matrix": ("", ""), "Bmatrix": ("{", "}")}
AMBIENTES_LINHAS = {"aligned", "align", "align*", "gather", "gathered", "eqnarray", "split", "array"}


class ErroLatex(ValueError):
    pass


def _tokens(texto):
    t, i, n = [], 0, len(texto)
    while i < n:
        c = texto[i]
        if c.isspace():
            i += 1
        elif c == "\\":
            j = i + 1
            if j < n and texto[j].isalpha():
                while j < n and texto[j].isalpha():
                    j += 1
                t.append(texto[i:j])
            else:
                j = min(i + 2, n)
                t.append(texto[i:j])
            i = j
        else:
            t.append(c)
            i += 1
    return t


def _r(texto, vertical=False, normal=False):
    """Um «run» matemático. `vertical` = letra direita (funções, unidades); `normal` = texto corrido."""
    if not texto:
        return ""
    props = ""
    if normal:
        props = "<m:rPr><m:nor/></m:rPr>"
    elif vertical:
        props = '<m:rPr><m:sty m:val="p"/></m:rPr>'
    return f'<m:r>{props}<m:t xml:space="preserve">{escape(texto)}</m:t></m:r>'


def _e(conteudo):
    return f"<m:e>{conteudo}</m:e>"


class _Analisador:
    def __init__(self, texto):
        self.t = _tokens(texto)
        self.i = 0

    # --- utilitários ---
    def ver(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def tomar(self):
        v = self.ver()
        self.i += 1
        return v

    def grupo(self):
        """O argumento de um comando: {…} ou um único símbolo."""
        v = self.ver()
        if v is None:
            return ""
        if v == "{":
            self.tomar()
            return self.sequencia(fim="}")
        return self.atomo()

    def texto_grupo(self):
        """Argumento como texto simples (para \\text{…}, \\mathrm{…})."""
        v = self.ver()
        if v == "{":
            self.tomar()
            nivel, partes = 1, []
            while self.i < len(self.t):
                x = self.tomar()
                if x == "{":
                    nivel += 1
                elif x == "}":
                    nivel -= 1
                    if nivel == 0:
                        break
                partes.append(x)
            return self._juntar(partes)
        return self.tomar() or ""

    @staticmethod
    def _juntar(partes):
        s = ""
        for p in partes:
            s += SIMBOLOS.get(p[1:], GREGAS.get(p[1:], p)) if p.startswith("\\") and len(p) > 1 else p
        return s

    # --- gramática ---
    def sequencia(self, fim=None, parar_em_relacao=False):
        partes = []
        while self.i < len(self.t):
            v = self.ver()
            if fim is not None and v == fim:
                self.tomar()
                break
            if fim is None and v == "}":
                break
            if v in ("&", "\\\\") or v == "\\end" or v == "\\right":
                break
            if parar_em_relacao and v in RELACOES:
                break
            partes.append(self.com_indices(self.atomo()))
        return "".join(partes)

    def com_indices(self, base):
        sub = sup = None
        while self.ver() in ("^", "_"):
            op = self.tomar()
            arg = self.grupo()
            if op == "^":
                sup = arg
            else:
                sub = arg
        return self._aplicar_indices(base, sub, sup)

    @staticmethod
    def _aplicar_indices(base, sub, sup):
        if sub is not None and sup is not None:
            return f"<m:sSubSup><m:e>{base or _r(' ')}</m:e><m:sub>{sub}</m:sub><m:sup>{sup}</m:sup></m:sSubSup>"
        if sup is not None:
            return f"<m:sSup><m:e>{base or _r(' ')}</m:e><m:sup>{sup}</m:sup></m:sSup>"
        if sub is not None:
            return f"<m:sSub><m:e>{base or _r(' ')}</m:e><m:sub>{sub}</m:sub></m:sSub>"
        return base

    def atomo(self):
        v = self.tomar()
        if v is None:
            return ""
        if v == "{":
            return self.sequencia(fim="}")
        if v in ("^", "_"):  # índice sem base: base vazia
            self.i -= 1
            return ""
        if not v.startswith("\\"):
            return self._literal(v)
        nome = v[1:]
        if nome in ("frac", "dfrac", "tfrac"):
            n, d = self.grupo(), self.grupo()
            return f"<m:f><m:num>{n}</m:num><m:den>{d}</m:den></m:f>"
        if nome in ("binom",):
            n, d = self.grupo(), self.grupo()
            return (f'<m:d><m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/></m:dPr><m:e><m:f><m:fPr><m:type m:val="noBar"/></m:fPr>'
                    f"<m:num>{n}</m:num><m:den>{d}</m:den></m:f></m:e></m:d>")
        if nome == "sqrt":
            grau = None
            if self.ver() == "[":
                self.tomar()
                partes = []
                while self.i < len(self.t) and self.ver() != "]":
                    partes.append(self.atomo())
                self.tomar()
                grau = "".join(partes)
            corpo = self.grupo()
            if grau:
                return f"<m:rad><m:deg>{grau}</m:deg><m:e>{corpo}</m:e></m:rad>"
            return f'<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>{corpo}</m:e></m:rad>'
        if nome in ("text", "textbf", "textit", "mbox", "mathrm", "operatorname", "mathbf", "mathit", "unit", "ce"):
            s = self.texto_grupo()
            return _r(s, normal=nome in ("text", "textbf", "textit", "mbox")) if nome in ("text", "textbf", "textit", "mbox") else _r(s, vertical=True)
        if nome == "mathbb":
            s = self.texto_grupo()
            return _r(CONJUNTOS.get(s, s))
        if nome in ("overline", "underline"):
            corpo = self.grupo()
            pos = "top" if nome == "overline" else "bot"
            return f'<m:bar><m:barPr><m:pos m:val="{pos}"/></m:barPr><m:e>{corpo}</m:e></m:bar>'
        if nome in ACENTOS:
            corpo = self.grupo()
            return f'<m:acc><m:accPr><m:chr m:val="{ACENTOS[nome]}"/></m:accPr><m:e>{corpo}</m:e></m:acc>'
        if nome == "overbrace" or nome == "underbrace":
            corpo = self.grupo()
            return corpo
        if nome in NARIOS:
            return self._nario(NARIOS[nome], nome)
        if nome in FUNCOES:
            if nome == "lim":
                inferior = None
                if self.ver() == "_":
                    self.tomar()
                    inferior = self.grupo()
                nome_fn = _r("lim", vertical=True)
                if inferior is not None:
                    return f"<m:limLow><m:e>{nome_fn}</m:e><m:lim>{inferior}</m:lim></m:limLow>"
                return nome_fn
            fn = _r(nome, vertical=True)
            if self.ver() in ("^", "_"):
                return self.com_indices(fn)
            return fn
        if nome in ("left", "bigl", "Bigl", "biggl"):
            return self._delimitado()
        if nome in ("begin",):
            return self._ambiente()
        if nome in GREGAS:
            return _r(GREGAS[nome])
        if nome in SIMBOLOS:
            return _r(SIMBOLOS[nome])
        if nome in ESPACOS:
            return _r(ESPACOS[nome]) if ESPACOS[nome] else ""
        if nome in ("right", "bigr", "Bigr", "biggr"):
            return ""
        if nome in ("%", "$", "&", "#", "_", "{", "}"):
            return _r(nome)
        if v in ("\\,", "\\;", "\\:", "\\!", "\\ "):
            return _r(ESPACOS.get(v[1:], " "))
        return _r(nome)  # comando desconhecido: mostra o nome em vez de falhar

    def _literal(self, c):
        if c.isdigit():  # agrupa algarismos e vírgula/ponto decimal
            s = c
            while self.ver() is not None and (self.ver().isdigit() or (self.ver() in (".", ",") and self.i + 1 < len(self.t) and self.t[self.i + 1].isdigit())):
                s += self.tomar()
            return _r(s)
        if c == "'":
            return _r("′")
        if c == "~":
            return _r(" ")
        if c == "-":
            return _r("−")
        if c == "*":
            return _r("∗")
        return _r(c)

    def _nario(self, simbolo, nome):
        sub = sup = None
        while self.ver() in ("^", "_"):
            op = self.tomar()
            arg = self.grupo()
            if op == "^":
                sup = arg
            else:
                sub = arg
        corpo = self.sequencia(parar_em_relacao=True)
        limites = ""
        if nome not in ("int", "iint", "iiint", "oint"):
            limites = '<m:limLoc m:val="undOvr"/>'
        ocultar = (f'<m:subHide m:val="{0 if sub is not None else 1}"/>' f'<m:supHide m:val="{0 if sup is not None else 1}"/>')
        return (f'<m:nary><m:naryPr><m:chr m:val="{simbolo}"/>{limites}{ocultar}</m:naryPr>'
                f"<m:sub>{sub or ''}</m:sub><m:sup>{sup or ''}</m:sup><m:e>{corpo}</m:e></m:nary>")

    def _delimitado(self):
        abre = self.tomar() or "."
        corpo = self.sequencia()
        fecha = "."
        if self.ver() in ("\\right", "\\bigr", "\\Bigr", "\\biggr"):
            self.tomar()
            fecha = self.tomar() or "."
        cb = DELIMITADORES.get(abre, abre.lstrip("\\"))
        ce = DELIMITADORES.get(fecha, fecha.lstrip("\\"))
        return (f'<m:d><m:dPr><m:begChr m:val="{escape(cb)}"/><m:endChr m:val="{escape(ce)}"/></m:dPr><m:e>{corpo}</m:e></m:d>')

    def _ambiente(self):
        nome = self.texto_grupo()
        if nome == "array" and self.ver() == "{":
            self.texto_grupo()  # especificação de colunas
        linhas, atual = [], []
        while self.i < len(self.t):
            celula = self.sequencia()
            atual.append(celula)
            v = self.ver()
            if v == "&":
                self.tomar()
                continue
            if v == "\\\\":
                self.tomar()
                linhas.append(atual)
                atual = []
                continue
            if v == "\\end":
                self.tomar()
                self.texto_grupo()
                break
            break
        if atual and any(c for c in atual):
            linhas.append(atual)
        if nome in AMBIENTES_MATRIZ:
            abre, fecha = AMBIENTES_MATRIZ[nome]
            mat = "<m:m>" + "".join("<m:mr>" + "".join(_e(c) for c in l) + "</m:mr>" for l in linhas) + "</m:m>"
            if not abre and not fecha:
                return mat
            return f'<m:d><m:dPr><m:begChr m:val="{escape(abre)}"/><m:endChr m:val="{escape(fecha)}"/></m:dPr><m:e>{mat}</m:e></m:d>'
        arr = "<m:eqArr>" + "".join(_e(self._linha_eq(l)) for l in linhas) + "</m:eqArr>"
        if nome == "cases":
            return f'<m:d><m:dPr><m:begChr m:val="{{"/><m:endChr m:val=""/></m:dPr><m:e>{arr}</m:e></m:d>'
        return arr

    @staticmethod
    def _linha_eq(celulas):
        # «a & b»: nas linhas de um sistema/alinhamento junta-se a condição à expressão com um espaço
        return (_r("  ")).join(c for c in celulas if c)


def latex_para_omml(latex):
    """Fórmula LaTeX (sem $…$) -> elemento <m:oMath> pronto a pôr num parágrafo do Word."""
    texto = (latex or "").strip()
    texto = re.sub(r"^\$+|\$+$", "", texto).strip()
    texto = re.sub(r"^\\\[|\\\]$|^\\\(|\\\)$", "", texto).strip()
    if not texto:
        return ""
    a = _Analisador(texto)
    corpo = []
    while a.i < len(a.t):
        if a.ver() == "}":
            a.tomar()
            continue
        corpo.append(a.sequencia())
        if a.ver() in ("&", "\\\\"):
            a.tomar()
    return f'<m:oMath xmlns:m="{M_NS}">{"".join(corpo)}</m:oMath>'
