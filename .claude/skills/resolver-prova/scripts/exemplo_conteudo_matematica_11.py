# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"D:\SIGE\.claude\skills\resolver-prova\scripts")
from build_resolucao import T, M, opcoes

OUT = r"C:\Users\FERNAN~1\AppData\Local\Temp\claude\dfd663b723ca2c67\274f611a-7af3-4248-b6a6-8d3f9e2c9ba9\scratchpad\out"
GRELHA_PDF = OUT + r"\grelha.pdf"
GRELHA_PNG = OUT + r"\grelha.png"

META = {
    "cabecalho": ["REPÚBLICA DE MOÇAMBIQUE", "Província de Inhambane — Distrito de Massinga", "Escola Secundária de Massinga"],
    "titulo": "Resolução detalhada da Avaliação Trimestral (AT) de Matemática Ciências — 11.ª Classe — IIIº Trimestre/2026",
    "subtitulo": "Duração: 120 minutos  |  40 questões de escolha múltipla  |  0,5 valores cada  |  Total: 20 valores",
    "rodape": "Resolução da AT de Matemática Ciências – 11.ª Classe – IIIº Trimestre/2026",
    "base": "Resolucao_AT_Matematica_Ciencias_11a_Classe_III_Trimestre_2026",
}

CHAVE = dict(enumerate("B A D A B D D C B C D D B B C B D C A C D D D D D B B A B C A A A B C D A B B B".split(), 1))

MATRIZ = [
    ("Lógica matemática: equivalências, tabelas de verdade e quantificadores", "1 a 4", 4, 2.0),
    ("Domínio de expressões e potências de expoente inteiro; simplificação de radicais", "5, 6 e 13", 3, 1.5),
    ("Polinómios: operações, divisão, Briot-Ruffini e equações redutíveis", "7, 8, 14, 15 e 16", 5, 2.5),
    ("Fracções algébricas e equações fraccionárias", "9 a 12", 4, 2.0),
    ("Equação irracional e inequação fraccionária", "17 e 18", 2, 1.0),
    ("Determinantes e sistemas de equações lineares (regra de Cramer)", "19 a 23", 5, 2.5),
    ("Equações e inequações exponenciais", "24 a 27", 4, 2.0),
    ("Equações e inequações logarítmicas", "28 a 30", 3, 1.5),
    ("Vectores e geometria analítica da recta", "31 a 40", 10, 5.0),
]

OBS = [
    "Numeração: na prova impressa a questão do determinante com k aparece numerada «22» (repetida) e não existe a «23»; "
    "tratou-se esta como a questão 23, de acordo com a grelha de 40 respostas.",
    "Questão 2: pela tabela, x = 1 e y = 1. Nenhuma alínea tem exactamente estes valores; a alínea A (x = 2 e y = 1) é a única com y correcto, "
    "pelo que se assinalou A (provável gralha: x = 1). Sugere-se confirmar com o professor.",
    "Questão 14: o resto impresso na tabela é 1, mas os cálculos dão 9 (5 + 4 = 9). Os valores pedidos (x, y, z) não dependem do resto: B.",
    "Questão 16: com a equação tal como está impressa (7x³ = 1 − x⁶) as raízes não coincidem com nenhuma alínea. "
    "Com 7x³ = 1 − 8x⁶ (coeficiente 8 em falta) obtém-se {−1; 1/2}, alínea B, que foi a assinalada. Sugere-se confirmar com o professor.",
    "Questão 31: «direcção» = a recta onde o vector está (onde vai), «comprimento» = tamanho (módulo) e «sentido» = para que lado da recta aponta. A alínea A é a que melhor encaixa.",
]

Q = []


def q(n, tipo, enun, passos, resp, nota=None, n_label=None):
    d = {"n": n, "tipo": tipo, "enun": enun, "passos": passos, "resp": resp}
    if nota: d["nota"] = nota
    if n_label: d["n_label"] = n_label
    Q.append(d)


# ---------------------------------------------------------------- 1
q(1, "Cálculo",
  [T("Qual das expressões é equivalente a:"), M(r"p\vee(\sim p\wedge q)"),
   opcoes(r"\sim p\wedge q", r"p\vee q", r"\sim p\wedge\sim q", r"\sim p\vee\sim q")],
  [T("**Passo 1.** Aplica-se a propriedade distributiva da disjunção (ou) em relação à conjunção (e):"),
   M(r"p\vee(\sim p\wedge q)\ \equiv\ (p\vee\sim p)\wedge(p\vee q)"),
   T("**Passo 2.** A proposição p ∨ ∼p é uma tautologia (é sempre verdadeira, V):"),
   M(r"(p\vee\sim p)\wedge(p\vee q)\ \equiv\ \mathrm{V}\wedge(p\vee q)"),
   T("**Passo 3.** O valor lógico V é o elemento neutro da conjunção (V e X tem o mesmo valor que X):"),
   M(r"\mathrm{V}\wedge(p\vee q)\ \equiv\ p\vee q"),
   T("**Verificação pela tabela de verdade** (1 = verdadeiro, 0 = falso):"),
   M(("tab", [["p", "q", r"\sim p", r"\sim p\wedge q", r"p\vee(\sim p\wedge q)", r"p\vee q"],
              ["1", "1", "0", "0", "1", "1"], ["1", "0", "0", "0", "1", "1"],
              ["0", "1", "1", "1", "1", "1"], ["0", "0", "1", "0", "0", "0"]])),
   T("As duas últimas colunas são iguais em todas as linhas, logo as proposições são equivalentes: p ∨ (∼p ∧ q) ≡ p ∨ q.")],
  "B")

# ---------------------------------------------------------------- 2
q(2, "Tabela",
  [T("A tabela refere-se à equivalência material. Quais são os valores de x e y?"),
   M(("tab", [["p", "q", r"p\Leftrightarrow q"], ["1", "1", "x"], ["1", "0", "0"], ["0", "1", "0"], ["0", "0", "y"]])),
   opcoes(r"x=2\ \mathrm{e}\ y=1", r"x=0\ \mathrm{e}\ y=1", r"x=1\ \mathrm{e}\ y=0", r"x=0\ \mathrm{e}\ y=0")],
  [T("**Passo 1.** A equivalência p ⇔ q é verdadeira (1) quando p e q têm o mesmo valor lógico, e falsa (0) quando têm valores diferentes."),
   T("**Passo 2.** Linha 1: p = 1 e q = 1 (valores iguais), logo:"), M(r"x=1\Leftrightarrow 1=1"),
   T("**Passo 3.** Linha 4: p = 0 e q = 0 (valores iguais), logo:"), M(r"y=0\Leftrightarrow 0=1"),
   T("**Passo 4.** Confirmação das linhas 2 e 3: p = 1, q = 0 e p = 0, q = 1 têm valores diferentes, logo o resultado é 0 (já dado na tabela)."),
   T("Tabela completa:"),
   M(("tab", [["p", "q", r"p\Leftrightarrow q"], ["1", "1", "1"], ["1", "0", "0"], ["0", "1", "0"], ["0", "0", "1"]])),
   T("Logo x = 1 e y = 1. Das alíneas dadas, só A tem y = 1; o valor x = 2 não é um valor lógico (só pode ser 0 ou 1), pelo que é provável gralha de x = 1.")],
  "A", nota="Nenhuma alínea tem exactamente x = 1 e y = 1; assinalou-se A por ser a única com y = 1 (ver Observações).")

# ---------------------------------------------------------------- 3
q(3, "Conceptual",
  [T("A soma de quaisquer dois números naturais é sempre maior do que zero. Qual é a quantificação correcta?"),
   opcoes(r"\exists x;y\in\mathbb{N}:\ x+y>0", r"\exists x;y\in\mathbb{N}:\ x+y\geq 0",
          r"\forall x;y\in\mathbb{N}:\ x+y\geq 0", r"\forall x;y\in\mathbb{N}:\ x+y>0")],
  [T("**Passo 1.** A palavra «quaisquer» (e «sempre») indica o quantificador universal ∀ («para todo»), e não o existencial ∃ («existe»). Ficam excluídas A e B."),
   T("**Passo 2.** «Maior do que zero» significa estritamente maior: usa-se o sinal >, e não ≥ (que significa «maior ou igual»). Fica excluída C."),
   T("**Passo 3.** A proposição correcta é:"),
   M(r"\forall x;y\in\mathbb{N}:\ x+y>0")],
  "D")

# ---------------------------------------------------------------- 4
q(4, "Cálculo",
  [T("Qual das proposições é equivalente a:"), M(r"p\wedge(p\wedge\sim q)"),
   opcoes(r"p\wedge\sim q", r"\sim p\wedge q", r"p\wedge q", r"p\vee\sim q")],
  [T("**Passo 1.** Aplica-se a propriedade associativa da conjunção:"),
   M(r"p\wedge(p\wedge\sim q)\ \equiv\ (p\wedge p)\wedge\sim q"),
   T("**Passo 2.** Aplica-se a idempotência (p ∧ p ≡ p):"),
   M(r"(p\wedge p)\wedge\sim q\ \equiv\ p\wedge\sim q"),
   T("**Verificação pela tabela de verdade:**"),
   M(("tab", [["p", "q", r"\sim q", r"p\wedge\sim q", r"p\wedge(p\wedge\sim q)"],
              ["1", "1", "0", "0", "0"], ["1", "0", "1", "1", "1"], ["0", "1", "0", "0", "0"], ["0", "0", "1", "0", "0"]])),
   T("As duas últimas colunas coincidem, logo p ∧ (p ∧ ∼q) ≡ p ∧ ∼q.")],
  "A")

# ---------------------------------------------------------------- 5
q(5, "Cálculo",
  [T("Qual é o domínio de existência da expressão:"), M(r"\dfrac{x+2}{\sqrt[3]{x}-1}"),
   opcoes(r"\mathbb{R}", r"x\in\mathbb{R}\setminus\{1\}", r"x\in\ ]0;-\infty[", r"x\in\ ]0;-\infty[\setminus\{1\}")],
  [T("**Passo 1.** O numerador x + 2 existe para qualquer x real."),
   T("**Passo 2.** O radical tem índice 3 (ímpar): a raiz cúbica existe para qualquer número real (positivo, nulo ou negativo), pelo que não há restrição vinda do radical."),
   T("**Passo 3.** O denominador não pode ser nulo:"),
   M(r"\sqrt[3]{x}-1\neq 0"),
   M(r"\sqrt[3]{x}\neq 1"),
   T("**Passo 4.** Elevando ambos os membros ao cubo:"),
   M(r"\left(\sqrt[3]{x}\right)^{3}\neq 1^{3}\ \Rightarrow\ x\neq 1"),
   T("**Passo 5.** Domínio:"), M(r"D=\mathbb{R}\setminus\{1\}")],
  "B")

# ---------------------------------------------------------------- 6
q(6, "Cálculo",
  [T("Qual é o valor de"), M(r"\dfrac{x^{2}\left(y\,x^{-2}-x\,y^{-2}\right)}{x^{2}-\left(-x^{-3}\right)}\quad\mathrm{se}\quad x=-2\ \ \mathrm{e}\ \ y=-1\,?"),
   opcoes(r"-\dfrac{31}{56}", r"-\dfrac{56}{31}", r"\dfrac{31}{56}", r"\dfrac{56}{31}")],
  [T("**Passo 1.** Substituem-se x = −2 e y = −1 e calculam-se as potências:"),
   M(r"x^{2}=(-2)^{2}=4"),
   M(r"x^{-2}=\dfrac{1}{x^{2}}=\dfrac{1}{4}"),
   M(r"y^{-2}=\dfrac{1}{y^{2}}=\dfrac{1}{(-1)^{2}}=\dfrac{1}{1}=1"),
   M(r"x^{-3}=\dfrac{1}{x^{3}}=\dfrac{1}{(-2)^{3}}=\dfrac{1}{-8}=-\dfrac{1}{8}"),
   T("**Passo 2.** Parêntesis do numerador:"),
   M(r"y\,x^{-2}=(-1)\cdot\dfrac{1}{4}=-\dfrac{1}{4}\qquad x\,y^{-2}=(-2)\cdot 1=-2"),
   M(r"y\,x^{-2}-x\,y^{-2}=-\dfrac{1}{4}-(-2)=-\dfrac{1}{4}+2=-\dfrac{1}{4}+\dfrac{8}{4}=\dfrac{7}{4}"),
   T("**Passo 3.** Numerador:"), M(r"x^{2}\cdot\dfrac{7}{4}=4\cdot\dfrac{7}{4}=7"),
   T("**Passo 4.** Denominador:"),
   M(r"x^{2}-\left(-x^{-3}\right)=4-\left(-\left(-\dfrac{1}{8}\right)\right)=4-\dfrac{1}{8}=\dfrac{32}{8}-\dfrac{1}{8}=\dfrac{31}{8}"),
   T("**Passo 5.** Divisão final (multiplica-se pelo inverso):"),
   M(r"\dfrac{7}{\dfrac{31}{8}}=7\cdot\dfrac{8}{31}=\dfrac{56}{31}")],
  "D")

# ---------------------------------------------------------------- 7
q(7, "Cálculo",
  [T("Dados P(x) = 5x⁴ + 3x³ + 2x − 1 e Q(x) = −5x⁴ − 3x³ + 2x + 5, qual é o grau de P(x) + Q(x)?"),
   M(r"P(x)=5x^{4}+3x^{3}+2x-1\qquad Q(x)=-5x^{4}-3x^{3}+2x+5"),
   opcoes("4", "3", "2", "1")],
  [T("**Passo 1.** Somam-se os termos semelhantes (do mesmo grau):"),
   M(r"P(x)+Q(x)=(5-5)x^{4}+(3-3)x^{3}+(2+2)x+(-1+5)"),
   M(r"P(x)+Q(x)=0\cdot x^{4}+0\cdot x^{3}+4x+4"),
   M(r"P(x)+Q(x)=4x+4"),
   T("**Passo 2.** O maior expoente de x com coeficiente não nulo é 1, logo o grau é 1.")],
  "D")

# ---------------------------------------------------------------- 8
q(8, "Cálculo",
  [T("O quociente e o resto da divisão de P(x) por Q(x) são, respectivamente:"),
   M(r"P(x)=x^{4}+x^{2}+1\qquad Q(x)=x^{2}-x+1"),
   opcoes(r"x^{2}+x\ \mathrm{e}\ x", r"-x^{2}-x-1\ \mathrm{e}\ -x+1", r"x^{2}+x+1\ \mathrm{e}\ 0", r"x^{2}-x-1\ \mathrm{e}\ x-1")],
  [T("**Passo 1.** Completa-se o dividendo com os termos de coeficiente zero:"),
   M(r"P(x)=x^{4}+0x^{3}+x^{2}+0x+1"),
   T("**Passo 2.** Divide-se o termo de maior grau do dividendo pelo do divisor: x⁴ ÷ x² = x². Multiplica-se pelo divisor e subtrai-se:"),
   M(r"x^{2}\left(x^{2}-x+1\right)=x^{4}-x^{3}+x^{2}"),
   M(r"\left(x^{4}+0x^{3}+x^{2}\right)-\left(x^{4}-x^{3}+x^{2}\right)=x^{3}+0x^{2}"),
   T("Desce-se o termo seguinte (0x): fica x³ + 0x² + 0x."),
   T("**Passo 3.** x³ ÷ x² = x. Multiplica-se pelo divisor e subtrai-se:"),
   M(r"x\left(x^{2}-x+1\right)=x^{3}-x^{2}+x"),
   M(r"\left(x^{3}+0x^{2}+0x\right)-\left(x^{3}-x^{2}+x\right)=x^{2}-x"),
   T("Desce-se o último termo (+1): fica x² − x + 1."),
   T("**Passo 4.** x² ÷ x² = 1. Multiplica-se pelo divisor e subtrai-se:"),
   M(r"1\cdot\left(x^{2}-x+1\right)=x^{2}-x+1"),
   M(r"\left(x^{2}-x+1\right)-\left(x^{2}-x+1\right)=0"),
   T("**Passo 5.** Quociente: x² + x + 1; resto: 0."),
   T("**Verificação** (dividendo = divisor × quociente + resto):"),
   M(r"\left(x^{2}-x+1\right)\left(x^{2}+x+1\right)=\left(x^{2}+1\right)^{2}-x^{2}=x^{4}+2x^{2}+1-x^{2}=x^{4}+x^{2}+1\ \checkmark")],
  "C")

# ---------------------------------------------------------------- 9
q(9, "Cálculo",
  [T("Simplificando a expressão obtém-se:"), M(r"\dfrac{x^{2}+2x}{(x+1)(x-1)+(x+1)}"),
   opcoes(r"\dfrac{x+2}{x(x+1)}", r"\dfrac{x+2}{x+1}", r"\dfrac{x}{(x+1)(x-1)}", r"\dfrac{x(x+2)}{(x+1)(x-2)}")],
  [T("**Passo 1.** Factoriza-se o numerador (factor comum x):"), M(r"x^{2}+2x=x(x+2)"),
   T("**Passo 2.** No denominador põe-se em evidência o factor comum (x + 1):"),
   M(r"(x+1)(x-1)+(x+1)=(x+1)\left[(x-1)+1\right]=(x+1)\cdot x"),
   T("**Passo 3.** Substitui-se e simplifica-se o factor comum x (com x ≠ 0 e x ≠ −1):"),
   M(r"\dfrac{x(x+2)}{x(x+1)}=\dfrac{x+2}{x+1}")],
  "B")

# ---------------------------------------------------------------- 10
q(10, "Cálculo",
  [T("A expressão, com x ≠ ±1, é equivalente a:"), M(r"\dfrac{3x}{x^{2}-1}+\dfrac{2}{x-1}-\dfrac{x+3}{x-1}"),
   opcoes(r"-\dfrac{x^{2}+x+1}{x^{2}-1}", r"-\dfrac{x^{2}-x-1}{x^{2}-1}", r"-\dfrac{x^{2}-x+1}{x^{2}-1}", r"-\dfrac{x^{2}+x-1}{x^{2}-1}")],
  [T("**Passo 1.** Factoriza-se o denominador: x² − 1 = (x − 1)(x + 1). O denominador comum é x² − 1."),
   T("**Passo 2.** Reduzem-se as fracções ao denominador comum (multiplicando numerador e denominador por x + 1 nas fracções de denominador x − 1):"),
   M(r"\dfrac{3x}{x^{2}-1}+\dfrac{2(x+1)}{(x-1)(x+1)}-\dfrac{(x+3)(x+1)}{(x-1)(x+1)}=\dfrac{3x+2(x+1)-(x+3)(x+1)}{x^{2}-1}"),
   T("**Passo 3.** Desenvolvem-se os produtos:"),
   M(r"2(x+1)=2x+2"),
   M(r"(x+3)(x+1)=x^{2}+x+3x+3=x^{2}+4x+3"),
   T("**Passo 4.** Calcula-se o numerador (atenção ao sinal menos antes do parêntesis):"),
   M(r"3x+2x+2-\left(x^{2}+4x+3\right)=3x+2x+2-x^{2}-4x-3"),
   M(r"=-x^{2}+(3x+2x-4x)+(2-3)=-x^{2}+x-1"),
   T("**Passo 5.** Coloca-se o sinal menos em evidência:"),
   M(r"\dfrac{-x^{2}+x-1}{x^{2}-1}=-\dfrac{x^{2}-x+1}{x^{2}-1}")],
  "C")

# ---------------------------------------------------------------- 11
q(11, "Cálculo",
  [T("A expressão equivalente a"), M(r"\dfrac{x^{3}-5x^{2}+6x}{x^{3}-8}\div\dfrac{x^{2}-9}{x^{2}+2x+4}\quad\mathrm{é:}"),
   opcoes(r"\dfrac{x+3}{x-2}", r"\dfrac{x-2}{x+3}", r"\dfrac{x+3}{x}", r"\dfrac{x}{x+3}")],
  [T("**Passo 1.** Factoriza-se o numerador da 1.ª fracção. Factor comum x e depois trinómio (soma das raízes 5, produto 6, raízes 2 e 3):"),
   M(r"x^{3}-5x^{2}+6x=x\left(x^{2}-5x+6\right)=x(x-2)(x-3)"),
   T("**Passo 2.** Denominador da 1.ª fracção, diferença de cubos a³ − b³ = (a − b)(a² + ab + b²):"),
   M(r"x^{3}-8=x^{3}-2^{3}=(x-2)\left(x^{2}+2x+4\right)"),
   T("**Passo 3.** Numerador da 2.ª fracção, diferença de quadrados:"), M(r"x^{2}-9=(x-3)(x+3)"),
   T("**Passo 4.** Dividir por uma fracção é multiplicar pelo seu inverso:"),
   M(r"\dfrac{x(x-2)(x-3)}{(x-2)\left(x^{2}+2x+4\right)}\cdot\dfrac{x^{2}+2x+4}{(x-3)(x+3)}"),
   T("**Passo 5.** Simplificam-se os factores comuns (x − 2), (x − 3) e (x² + 2x + 4):"),
   M(r"\dfrac{x}{x+3}")],
  "D")

# ---------------------------------------------------------------- 12
q(12, "Cálculo",
  [T("Qual é a solução da equação:"), M(r"\dfrac{2x+1}{3x-3}=\dfrac{7}{x^{2}-x}"),
   opcoes(r"\left\{-\dfrac{7}{2};-3\right\}", r"\left\{-3;\dfrac{7}{2}\right\}", r"\left\{3;\dfrac{7}{2}\right\}", r"\left\{-\dfrac{7}{2};3\right\}")],
  [T("**Passo 1.** Factorizam-se os denominadores:"),
   M(r"3x-3=3(x-1)\qquad x^{2}-x=x(x-1)"),
   T("**Passo 2.** Condições de existência: 3(x − 1) ≠ 0 e x(x − 1) ≠ 0, logo x ≠ 0 e x ≠ 1."),
   T("**Passo 3.** Equação com os denominadores factorizados:"),
   M(r"\dfrac{2x+1}{3(x-1)}=\dfrac{7}{x(x-1)}"),
   T("**Passo 4.** Multiplicam-se os dois membros pelo denominador comum 3x(x − 1) (≠ 0):"),
   M(r"(2x+1)\cdot x=7\cdot 3"),
   M(r"2x^{2}+x=21\ \Rightarrow\ 2x^{2}+x-21=0"),
   T("**Passo 5.** Fórmula resolvente com a = 2, b = 1, c = −21:"),
   M(r"\Delta=b^{2}-4ac=1^{2}-4\cdot2\cdot(-21)=1+168=169\qquad\sqrt{\Delta}=13"),
   M(r"x=\dfrac{-b\pm\sqrt{\Delta}}{2a}=\dfrac{-1\pm 13}{4}"),
   M(r"x_{1}=\dfrac{-1+13}{4}=\dfrac{12}{4}=3\qquad x_{2}=\dfrac{-1-13}{4}=\dfrac{-14}{4}=-\dfrac{7}{2}"),
   T("**Passo 6.** Ambos são diferentes de 0 e de 1, logo são aceitáveis."),
   T("**Verificação** para x = 3:"), M(r"\dfrac{2\cdot3+1}{3\cdot3-3}=\dfrac{7}{6}\qquad\dfrac{7}{3^{2}-3}=\dfrac{7}{6}\ \checkmark"),
   T("**Verificação** para x = −7/2:"),
   M(r"\dfrac{-7+1}{-\dfrac{21}{2}-3}=\dfrac{-6}{-\dfrac{27}{2}}=\dfrac{12}{27}=\dfrac{4}{9}\qquad\dfrac{7}{\dfrac{49}{4}+\dfrac{7}{2}}=\dfrac{7}{\dfrac{63}{4}}=\dfrac{28}{63}=\dfrac{4}{9}\ \checkmark"),
   M(r"S=\left\{-\dfrac{7}{2};\,3\right\}")],
  "D")

# ---------------------------------------------------------------- 13
q(13, "Cálculo",
  [T("Qual é a expressão equivalente a:"), M(r"\dfrac{x+1}{\sqrt{x+1}}\ ?"),
   opcoes(r"\dfrac{1}{x+1}", r"\sqrt{x+1}", r"\dfrac{\sqrt{x+1}}{X+1}", r"x+1")],
  [T("**Passo 1.** A expressão existe para x + 1 > 0 (radicando positivo e denominador não nulo). Nestas condições:"),
   M(r"x+1=\left(\sqrt{x+1}\right)^{2}"),
   T("**Passo 2.** Substitui-se no numerador:"),
   M(r"\dfrac{x+1}{\sqrt{x+1}}=\dfrac{\left(\sqrt{x+1}\right)^{2}}{\sqrt{x+1}}=\dfrac{\sqrt{x+1}\cdot\sqrt{x+1}}{\sqrt{x+1}}=\sqrt{x+1}"),
   T("**Alternativa** (racionalizando o denominador):"),
   M(r"\dfrac{x+1}{\sqrt{x+1}}\cdot\dfrac{\sqrt{x+1}}{\sqrt{x+1}}=\dfrac{(x+1)\sqrt{x+1}}{x+1}=\sqrt{x+1}")],
  "B")

# ---------------------------------------------------------------- 14
q(14, "Tabela",
  [T("Na divisão de P(x) por (x + a) usou-se o dispositivo prático de Briot-Ruffini. Quais são x, y e z?"),
   M(("tab", [["", "2", "y", "-5", "4", "5"], ["-2", "", "", "", "", ""], ["", "x", "-4", "3", "z", "1"]])),
   opcoes("2,\\,-2,\\,0", "2,\\,0,\\,-2", "-2,\\,2,\\,0", "-2,\\,0,\\,-2")],
  [T("**Passo 1.** O divisor é x + 2 = x − (−2); logo a raiz usada no dispositivo é −2."),
   T("**Passo 2.** Regra: baixa-se o 1.º coeficiente; cada valor da linha de baixo multiplica-se por −2, o resultado escreve-se por baixo do coeficiente seguinte e somam-se."),
   T("1.º coeficiente: baixa-se o 2, logo:"), M(r"x=2"),
   T("**Passo 3.** 2 × (−2) = −4. Soma com y dá o valor −4 da linha de baixo:"),
   M(r"y+(-4)=-4\ \Rightarrow\ y=-4+4=0"),
   T("**Passo 4.** (−4) × (−2) = 8. Soma com −5:"), M(r"-5+8=3\ \checkmark\ (\mathrm{valor\ dado})"),
   T("**Passo 5.** 3 × (−2) = −6. Soma com 4:"), M(r"z=4+(-6)=-2"),
   T("**Passo 6.** (−2) × (−2) = 4. Soma com 5: 5 + 4 = 9 (resto). Dispositivo completo:"),
   M(("tab", [["", "2", "0", "-5", "4", "5"], ["-2", "", "-4", "8", "-6", "4"], ["", "2", "-4", "3", "-2", "9"]])),
   M(r"x=2,\qquad y=0,\qquad z=-2")],
  "B", nota="O resto impresso na prova (1) é inconsistente com os cálculos (9); não afecta x, y e z.")

# ---------------------------------------------------------------- 15
q(15, "Cálculo",
  [T("O conjunto solução da equação é:"), M(r"9x^{4}=10x^{2}-1"),
   opcoes(r"\left\{-\dfrac{1}{3};0;\dfrac{1}{3};3\right\}", r"\{-3;-1;1;3\}", r"\left\{-1;-\dfrac{1}{3};\dfrac{1}{3};1\right\}", r"\left\{-3;-1;\dfrac{1}{3};3\right\}")],
  [T("**Passo 1.** Passa-se tudo para o 1.º membro (equação biquadrada):"), M(r"9x^{4}-10x^{2}+1=0"),
   T("**Passo 2.** Mudança de variável t = x² (com t ≥ 0):"), M(r"9t^{2}-10t+1=0"),
   T("**Passo 3.** Fórmula resolvente com a = 9, b = −10, c = 1:"),
   M(r"\Delta=(-10)^{2}-4\cdot9\cdot1=100-36=64\qquad\sqrt{\Delta}=8"),
   M(r"t=\dfrac{10\pm8}{18}\ \Rightarrow\ t_{1}=\dfrac{18}{18}=1\qquad t_{2}=\dfrac{2}{18}=\dfrac{1}{9}"),
   T("**Passo 4.** Volta-se à variável x:"),
   M(r"x^{2}=1\ \Rightarrow\ x=\pm1\qquad x^{2}=\dfrac{1}{9}\ \Rightarrow\ x=\pm\dfrac{1}{3}"),
   T("**Verificação** para x = 1/3:"), M(r"9\cdot\dfrac{1}{81}=\dfrac{1}{9}\qquad 10\cdot\dfrac{1}{9}-1=\dfrac{1}{9}\ \checkmark"),
   M(r"S=\left\{-1;-\dfrac{1}{3};\dfrac{1}{3};1\right\}")],
  "C")

# ---------------------------------------------------------------- 16
q(16, "Cálculo",
  [T("Quais são as raízes da equação:"), M(r"7x^{3}=1-x^{6}\ ?"),
   opcoes(r"\left\{-1;\dfrac{1}{8}\right\}", r"\left\{-1;\dfrac{1}{2}\right\}", r"\{-1;1\}", r"\{2;-1\}")],
  [T("**Passo 1.** Equação como está impressa; passando tudo para o 1.º membro e pondo t = x³:"),
   M(r"x^{6}+7x^{3}-1=0\ \Rightarrow\ t^{2}+7t-1=0"),
   M(r"\Delta=7^{2}-4\cdot1\cdot(-1)=49+4=53\qquad t=\dfrac{-7\pm\sqrt{53}}{2}"),
   T("Estes valores não conduzem a nenhuma das alíneas (por exemplo x = −1 dá 7·(−1) = −7 ≠ 1 − 1 = 0). A equação tem uma gralha: o coeficiente 8 de x⁶ está em falta."),
   T("**Passo 2.** Equação que a prova pretendia (com 8x⁶):"), M(r"7x^{3}=1-8x^{6}\ \Rightarrow\ 8x^{6}+7x^{3}-1=0"),
   T("**Passo 3.** Mudança de variável t = x³:"), M(r"8t^{2}+7t-1=0"),
   M(r"\Delta=7^{2}-4\cdot8\cdot(-1)=49+32=81\qquad\sqrt{\Delta}=9"),
   M(r"t=\dfrac{-7\pm9}{16}\ \Rightarrow\ t_{1}=\dfrac{2}{16}=\dfrac{1}{8}\qquad t_{2}=\dfrac{-16}{16}=-1"),
   T("**Passo 4.** Volta-se à variável x (raiz cúbica):"),
   M(r"x^{3}=\dfrac{1}{8}\ \Rightarrow\ x=\sqrt[3]{\dfrac{1}{8}}=\dfrac{1}{2}\qquad x^{3}=-1\ \Rightarrow\ x=-1"),
   T("**Verificação:**"),
   M(r"x=\dfrac{1}{2}:\ \ 7\cdot\dfrac{1}{8}=\dfrac{7}{8}\quad 1-8\cdot\dfrac{1}{64}=1-\dfrac{1}{8}=\dfrac{7}{8}\ \checkmark\qquad x=-1:\ \ -7\quad 1-8=-7\ \checkmark"),
   M(r"S=\left\{-1;\dfrac{1}{2}\right\}")],
  "B", nota="Resposta assinalada com base na equação corrigida (ver Observações); a equação impressa não tem alínea correspondente.")

# ---------------------------------------------------------------- 17
q(17, "Cálculo",
  [T("Qual é a solução da equação:"), M(r"\left(x^{2}+4\right)^{\frac{1}{2}}=x+1"),
   opcoes(r"-\dfrac{3}{2}", r"-\dfrac{2}{3}", r"\dfrac{2}{3}", r"\dfrac{3}{2}")],
  [T("**Passo 1.** O expoente 1/2 equivale à raiz quadrada:"), M(r"\sqrt{x^{2}+4}=x+1"),
   T("**Passo 2.** Condição: a raiz é ≥ 0, logo x + 1 ≥ 0, isto é, x ≥ −1."),
   T("**Passo 3.** Elevam-se ambos os membros ao quadrado:"), M(r"x^{2}+4=(x+1)^{2}=x^{2}+2x+1"),
   T("**Passo 4.** Cancelam-se os termos x² e resolve-se:"),
   M(r"4=2x+1\ \Rightarrow\ 2x=3\ \Rightarrow\ x=\dfrac{3}{2}"),
   T("**Passo 5.** Verifica-se a condição x ≥ −1: 3/2 ≥ −1 ✓. Verificação na equação:"),
   M(r"\sqrt{\left(\dfrac{3}{2}\right)^{2}+4}=\sqrt{\dfrac{9}{4}+\dfrac{16}{4}}=\sqrt{\dfrac{25}{4}}=\dfrac{5}{2}\qquad\dfrac{3}{2}+1=\dfrac{5}{2}\ \checkmark")],
  "D")

# ---------------------------------------------------------------- 18
q(18, "Tabela",
  [T("Qual é a solução da inequação:"), M(r"\dfrac{2x+6}{2-x}<0\ ?"),
   opcoes(r"]-3;2[", r"]-\infty;-2[\,\cup\,]3;+\infty[", r"]-\infty;-3[\,\cup\,]2;+\infty[", r"\mathrm{IR}")],
  [T("**Passo 1.** Zero do numerador:"), M(r"2x+6=0\ \Rightarrow\ 2x=-6\ \Rightarrow\ x=-3"),
   T("**Passo 2.** Zero do denominador (valor excluído):"), M(r"2-x=0\ \Rightarrow\ x=2"),
   T("**Passo 3.** Quadro de sinais:"),
   M(("tab", [["x", r"]-\infty;-3[", "-3", r"]-3;2[", "2", r"]2;+\infty["],
              ["2x+6", "-", "0", "+", "+", "+"], ["2-x", "+", "+", "+", "0", "-"],
              [r"\dfrac{2x+6}{2-x}", "-", "0", "+", r"\mathrm{n.d.}", "-"]])),
   T("**Passo 4.** Pretende-se o quociente negativo (< 0): intervalos onde o sinal é «−». O 0 de −3 não serve (a desigualdade é estrita) e x = 2 não existe."),
   M(r"S=\ ]-\infty;-3[\ \cup\ ]2;+\infty[")],
  "C")

# ---------------------------------------------------------------- 19
q(19, "Cálculo",
  [T("De um sistema linear de três equações e três incógnitas (x; y; z) sabe-se que:"),
   M(r"\Delta=-7;\quad\Delta_{x}=-7;\quad\Delta_{y}=28;\quad\Delta_{z}=14"),
   T("Qual é o valor de x + y − z?"),
   opcoes("-1", "0", "1", "2")],
  [T("**Passo 1.** Regra de Cramer: cada incógnita é o quociente do respectivo determinante pelo determinante do sistema (Δ ≠ 0)."),
   M(r"x=\dfrac{\Delta_{x}}{\Delta}=\dfrac{-7}{-7}=1"),
   M(r"y=\dfrac{\Delta_{y}}{\Delta}=\dfrac{28}{-7}=-4"),
   M(r"z=\dfrac{\Delta_{z}}{\Delta}=\dfrac{14}{-7}=-2"),
   T("**Passo 2.** Calcula-se a expressão pedida:"),
   M(r"x+y-z=1+(-4)-(-2)=1-4+2=-1")],
  "A")

# ---------------------------------------------------------------- 20
q(20, "Cálculo",
  [T("Qual é o valor numérico do determinante:"), M(("mat", [["1", "1", "1"], ["1", "1", "0"], ["0", "1", "1"]], "[")),
   opcoes("-1", "0", "1", "2")],
  [T("**Passo 1.** Regra de Sarrus: repetem-se as duas primeiras colunas à direita do determinante."),
   M(("mat", [["1", "1", "1", "1", "1"], ["1", "1", "0", "1", "1"], ["0", "1", "1", "0", "1"]], "|")),
   T("**Passo 2.** Soma dos produtos das diagonais principais (da esquerda para a direita, para baixo):"),
   M(r"1\cdot1\cdot1+1\cdot0\cdot0+1\cdot1\cdot1=1+0+1=2"),
   T("**Passo 3.** Soma dos produtos das diagonais secundárias (da direita para a esquerda, para baixo):"),
   M(r"1\cdot1\cdot0+1\cdot0\cdot1+1\cdot1\cdot1=0+0+1=1"),
   T("**Passo 4.** O determinante é a diferença:"), M(r"\det=2-1=1"),
   T("**Verificação** (desenvolvimento pela 1.ª linha):"),
   M(r"1\cdot(1\cdot1-0\cdot1)-1\cdot(1\cdot1-0\cdot0)+1\cdot(1\cdot1-1\cdot0)=1-1+1=1\ \checkmark")],
  "C")

# ---------------------------------------------------------------- 21
q(21, "Cálculo",
  [T("Qual é a soma de x, y, z no sistema:"),
   M(("sys", ["2x+y-z=7", "y+z=3", "2z=4"])), opcoes("4", "5", "6", "7")],
  [T("O sistema é triangular: resolve-se de baixo para cima (substituição)."),
   T("**Passo 1.** Da 3.ª equação:"), M(r"2z=4\ \Rightarrow\ z=\dfrac{4}{2}=2"),
   T("**Passo 2.** Substitui-se z = 2 na 2.ª equação:"), M(r"y+2=3\ \Rightarrow\ y=3-2=1"),
   T("**Passo 3.** Substituem-se y = 1 e z = 2 na 1.ª equação:"),
   M(r"2x+1-2=7\ \Rightarrow\ 2x-1=7\ \Rightarrow\ 2x=8\ \Rightarrow\ x=4"),
   T("**Passo 4.** Soma:"), M(r"x+y+z=4+1+2=7")],
  "D")

# ---------------------------------------------------------------- 22
q(22, "Cálculo",
  [T("Qual é a solução do sistema:"), M(("sys", ["x-3y+2z=0", "x+y+z=3", "2x+y-z=2"])),
   opcoes(r"\{-1;1;2\}", r"\{1;-2;-1\}", r"\{0;2;3\}", r"\{1;1;1\}")],
  [T("**Passo 1.** Regra de Cramer. Determinante do sistema (desenvolvimento pela 1.ª linha):"),
   M([r"\Delta=", ("mat", [["1", "-3", "2"], ["1", "1", "1"], ["2", "1", "-1"]], "|")]),
   M(r"\Delta=1\cdot(1\cdot(-1)-1\cdot1)-(-3)\cdot(1\cdot(-1)-1\cdot2)+2\cdot(1\cdot1-1\cdot2)"),
   M(r"\Delta=1\cdot(-2)+3\cdot(-3)+2\cdot(-1)=-2-9-2=-13"),
   T("**Passo 2.** Δx (coluna dos coeficientes de x substituída pelos termos independentes 0, 3, 2):"),
   M([r"\Delta_{x}=", ("mat", [["0", "-3", "2"], ["3", "1", "1"], ["2", "1", "-1"]], "|")]),
   M(r"\Delta_{x}=0\cdot(1\cdot(-1)-1\cdot1)-(-3)\cdot(3\cdot(-1)-1\cdot2)+2\cdot(3\cdot1-1\cdot2)"),
   M(r"\Delta_{x}=0+3\cdot(-5)+2\cdot1=-15+2=-13"),
   T("**Passo 3.** Δy (coluna de y substituída):"),
   M([r"\Delta_{y}=", ("mat", [["1", "0", "2"], ["1", "3", "1"], ["2", "2", "-1"]], "|")]),
   M(r"\Delta_{y}=1\cdot(3\cdot(-1)-1\cdot2)-0\cdot(1\cdot(-1)-1\cdot2)+2\cdot(1\cdot2-3\cdot2)"),
   M(r"\Delta_{y}=1\cdot(-5)-0+2\cdot(-4)=-5-8=-13"),
   T("**Passo 4.** Δz (coluna de z substituída):"),
   M([r"\Delta_{z}=", ("mat", [["1", "-3", "0"], ["1", "1", "3"], ["2", "1", "2"]], "|")]),
   M(r"\Delta_{z}=1\cdot(1\cdot2-3\cdot1)-(-3)\cdot(1\cdot2-3\cdot2)+0\cdot(1\cdot1-1\cdot2)"),
   M(r"\Delta_{z}=1\cdot(-1)+3\cdot(-4)+0=-1-12=-13"),
   T("**Passo 5.** Valores das incógnitas:"),
   M(r"x=\dfrac{\Delta_{x}}{\Delta}=\dfrac{-13}{-13}=1\qquad y=\dfrac{\Delta_{y}}{\Delta}=\dfrac{-13}{-13}=1\qquad z=\dfrac{\Delta_{z}}{\Delta}=\dfrac{-13}{-13}=1"),
   T("**Verificação** (x = y = z = 1 em cada equação):"),
   M(r"1-3+2=0\ \checkmark\qquad 1+1+1=3\ \checkmark\qquad 2+1-1=2\ \checkmark"),
   M(r"S=\{1;1;1\}")],
  "D")

# ---------------------------------------------------------------- 23
q(23, "Cálculo",
  [T("Considere a equação (na prova impressa aparece numerada «22»):"),
   M([("mat", [["1", "0", "1"], ["k", "-1", "1"], ["1", "2", "-1"]], "["), "=6"]),
   T("Qual é o valor de k?"), opcoes("0", "1", "2", "3")],
  [T("**Passo 1.** Desenvolve-se o determinante pela 1.ª linha (elementos 1, 0 e 1):"),
   M(r"1\cdot\left[(-1)(-1)-1\cdot2\right]-0\cdot\left[k\cdot(-1)-1\cdot1\right]+1\cdot\left[k\cdot2-(-1)\cdot1\right]"),
   T("**Passo 2.** Calculam-se os parêntesis rectos:"),
   M(r"(-1)(-1)-1\cdot2=1-2=-1\qquad k\cdot2-(-1)\cdot1=2k+1"),
   T("**Passo 3.** Substitui-se:"),
   M(r"1\cdot(-1)-0+1\cdot(2k+1)=-1+2k+1=2k"),
   T("**Passo 4.** Iguala-se a 6:"), M(r"2k=6\ \Rightarrow\ k=\dfrac{6}{2}=3"),
   T("**Verificação** com k = 3 (regra de Sarrus): diagonais principais 1·(−1)·(−1) + 0·1·1 + 1·3·2 = 1 + 0 + 6 = 7; diagonais secundárias 1·(−1)·1 + 1·1·2 + 0·3·(−1) = −1 + 2 + 0 = 1; 7 − 1 = 6 ✓.")],
  "D", n_label="23 (22)")

# ---------------------------------------------------------------- 24
q(24, "Cálculo",
  [T("O conjunto de números reais que satisfazem a equação:"), M(r"2^{x}\cdot4^{x+1}\cdot8^{x+2}=16^{x+3}"),
   opcoes("-1", "0", "1", "2")],
  [T("**Passo 1.** Escrevem-se todas as bases como potências de 2 (4 = 2², 8 = 2³, 16 = 2⁴):"),
   M(r"4^{x+1}=\left(2^{2}\right)^{x+1}=2^{2(x+1)}=2^{2x+2}"),
   M(r"8^{x+2}=\left(2^{3}\right)^{x+2}=2^{3(x+2)}=2^{3x+6}"),
   M(r"16^{x+3}=\left(2^{4}\right)^{x+3}=2^{4(x+3)}=2^{4x+12}"),
   T("**Passo 2.** No 1.º membro somam-se os expoentes (mesma base):"),
   M(r"2^{x}\cdot2^{2x+2}\cdot2^{3x+6}=2^{x+2x+2+3x+6}=2^{6x+8}"),
   T("**Passo 3.** Igualam-se os expoentes (mesma base, base ≠ 1):"),
   M(r"6x+8=4x+12\ \Rightarrow\ 6x-4x=12-8\ \Rightarrow\ 2x=4\ \Rightarrow\ x=2"),
   T("**Verificação:**"), M(r"2^{2}\cdot4^{3}\cdot8^{4}=4\cdot64\cdot4096=1\,048\,576\qquad16^{5}=1\,048\,576\ \checkmark")],
  "D")

# ---------------------------------------------------------------- 25
q(25, "Cálculo",
  [T("Sabendo que 9ˣ − 3ˣ = 72, qual é o valor de x² + 2?"), M(r"9^{x}-3^{x}=72\ \Rightarrow\ x^{2}+2=\ ?"),
   opcoes("1", "2", "3", "6")],
  [T("**Passo 1.** Escreve-se 9ˣ como potência de base 3:"), M(r"9^{x}=\left(3^{2}\right)^{x}=\left(3^{x}\right)^{2}"),
   T("**Passo 2.** Mudança de variável t = 3ˣ (com t > 0):"), M(r"t^{2}-t=72\ \Rightarrow\ t^{2}-t-72=0"),
   T("**Passo 3.** Fórmula resolvente (a = 1, b = −1, c = −72):"),
   M(r"\Delta=(-1)^{2}-4\cdot1\cdot(-72)=1+288=289\qquad\sqrt{\Delta}=17"),
   M(r"t=\dfrac{1\pm17}{2}\ \Rightarrow\ t_{1}=\dfrac{18}{2}=9\qquad t_{2}=\dfrac{-16}{2}=-8"),
   T("**Passo 4.** t = −8 rejeita-se (3ˣ é sempre positivo). Com t = 9:"),
   M(r"3^{x}=9=3^{2}\ \Rightarrow\ x=2"),
   T("**Passo 5.** Valor pedido:"), M(r"x^{2}+2=2^{2}+2=4+2=6"),
   T("**Verificação:**"), M(r"9^{2}-3^{2}=81-9=72\ \checkmark")],
  "D")

# ---------------------------------------------------------------- 26
q(26, "Cálculo",
  [T("Qual é a solução da equação:"), M(r"4^{x}-5\cdot2^{x}+4=0\ ?"),
   opcoes(r"\{0;-2\}", r"\{0;2\}", r"\{1;4\}", r"\{4;3\}")],
  [T("**Passo 1.** Escreve-se 4ˣ como potência de base 2:"), M(r"4^{x}=\left(2^{2}\right)^{x}=\left(2^{x}\right)^{2}"),
   T("**Passo 2.** Mudança de variável t = 2ˣ (com t > 0):"), M(r"t^{2}-5t+4=0"),
   T("**Passo 3.** Fórmula resolvente (a = 1, b = −5, c = 4):"),
   M(r"\Delta=(-5)^{2}-4\cdot1\cdot4=25-16=9\qquad\sqrt{\Delta}=3"),
   M(r"t=\dfrac{5\pm3}{2}\ \Rightarrow\ t_{1}=\dfrac{8}{2}=4\qquad t_{2}=\dfrac{2}{2}=1"),
   T("**Passo 4.** Voltando a x:"),
   M(r"2^{x}=4=2^{2}\ \Rightarrow\ x=2\qquad 2^{x}=1=2^{0}\ \Rightarrow\ x=0"),
   T("**Verificação:**"), M(r"x=0:\ 1-5+4=0\ \checkmark\qquad x=2:\ 16-20+4=0\ \checkmark"),
   M(r"S=\{0;2\}")],
  "B")

# ---------------------------------------------------------------- 27
q(27, "Cálculo",
  [T("A solução da inequação é:"), M(r"2^{x-1}+2^{x}+2^{x+1}-2^{x+2}+2^{x+3}>240"),
   opcoes(r"]-\infty;5]", r"]5;+\infty[", r"]-\infty;5[", r"[2;+\infty[")],
  [T("**Passo 1.** Escrevem-se todas as potências em função de 2ˣ⁻¹ (propriedade aᵐ⁺ⁿ = aᵐ·aⁿ):"),
   M(r"2^{x}=2^{x-1}\cdot2^{1}=2\cdot2^{x-1}\qquad 2^{x+1}=2^{x-1}\cdot2^{2}=4\cdot2^{x-1}"),
   M(r"2^{x+2}=2^{x-1}\cdot2^{3}=8\cdot2^{x-1}\qquad 2^{x+3}=2^{x-1}\cdot2^{4}=16\cdot2^{x-1}"),
   T("**Passo 2.** Coloca-se 2ˣ⁻¹ em evidência:"),
   M(r"2^{x-1}\left(1+2+4-8+16\right)>240\ \Rightarrow\ 15\cdot2^{x-1}>240"),
   T("**Passo 3.** Divide-se por 15:"), M(r"2^{x-1}>\dfrac{240}{15}=16=2^{4}"),
   T("**Passo 4.** Como a base 2 é maior que 1, a função exponencial é crescente e a desigualdade mantém o sentido:"),
   M(r"x-1>4\ \Rightarrow\ x>5"),
   M(r"S=\ ]5;+\infty[")],
  "B")

# ---------------------------------------------------------------- 28
q(28, "Cálculo",
  [T("Qual é a solução da equação:"), M(r"\left(\log_{2}x\right)^{2}-3\log_{2}x+2=0\ ?"),
   opcoes(r"\{2;4\}", r"\{-2;4\}", r"\{2;-4\}", r"\{-2;-4\}")],
  [T("**Passo 1.** Condição de existência do logaritmo: x > 0."),
   T("**Passo 2.** Mudança de variável u = log₂ x:"), M(r"u^{2}-3u+2=0"),
   T("**Passo 3.** Fórmula resolvente (a = 1, b = −3, c = 2):"),
   M(r"\Delta=(-3)^{2}-4\cdot1\cdot2=9-8=1\qquad\sqrt{\Delta}=1"),
   M(r"u=\dfrac{3\pm1}{2}\ \Rightarrow\ u_{1}=\dfrac{4}{2}=2\qquad u_{2}=\dfrac{2}{2}=1"),
   T("**Passo 4.** Volta-se a x (definição de logaritmo):"),
   M(r"\log_{2}x=2\ \Rightarrow\ x=2^{2}=4\qquad\log_{2}x=1\ \Rightarrow\ x=2^{1}=2"),
   T("Ambos são positivos, logo são soluções."), M(r"S=\{2;4\}")],
  "A")

# ---------------------------------------------------------------- 29
q(29, "Cálculo",
  [T("Qual é a solução da equação:"), M(r"\log_{2}x+\log_{4}x=1\ ?"),
   opcoes(r"\sqrt[3]{2}", r"\sqrt[3]{4}", r"3\sqrt[3]{2}", r"2\sqrt[3]{4}")],
  [T("**Passo 1.** Condição de existência: x > 0."),
   T("**Passo 2.** Mudança para a base 2 (fórmula da mudança de base):"),
   M(r"\log_{4}x=\dfrac{\log_{2}x}{\log_{2}4}=\dfrac{\log_{2}x}{2}"),
   T("**Passo 3.** Substitui-se na equação:"),
   M(r"\log_{2}x+\dfrac{1}{2}\log_{2}x=1\ \Rightarrow\ \dfrac{3}{2}\log_{2}x=1"),
   T("**Passo 4.** Isola-se log₂ x:"), M(r"\log_{2}x=\dfrac{2}{3}"),
   T("**Passo 5.** Definição de logaritmo e conversão da potência fraccionária em radical:"),
   M(r"x=2^{\frac{2}{3}}=\sqrt[3]{2^{2}}=\sqrt[3]{4}"),
   T("**Verificação:** log₂ x = 2/3 e log₄ x = 1/3; soma:"), M(r"\dfrac{2}{3}+\dfrac{1}{3}=1\ \checkmark")],
  "B")

# ---------------------------------------------------------------- 30
q(30, "Cálculo",
  [T("Qual é a solução da inequação:"), M(r"\log_{3}(x+1)>\log_{3}6\ ?"),
   opcoes(r"[-1;5[", r"]-1;5[", r"]5;+\infty[", r"]-\infty;5[")],
  [T("**Passo 1.** Condição de existência do logaritmo: x + 1 > 0, isto é, x > −1."),
   T("**Passo 2.** A base 3 é maior que 1, logo a função logarítmica é crescente e a desigualdade mantém o sentido:"),
   M(r"x+1>6\ \Rightarrow\ x>6-1\ \Rightarrow\ x>5"),
   T("**Passo 3.** Intersecção com a condição de existência (x > 5 e x > −1):"),
   M(r"S=\ ]5;+\infty[")],
  "C")

# ---------------------------------------------------------------- 31
q(31, "Conceptual",
  [T("São elementos básicos que identificam um vector: Direcção, Comprimento e Sentido, cujo significado nos vectores são, respectivamente:"),
   T("A. Onde vai, tamanho e posição.   B. Onde vai, posição e tamanho.   C. Tamanho, onde vai e posição.   D. Posição, tamanho e onde vai.")],
  [T("**Passo 1.** Direcção: é a recta onde o vector está, isto é, «onde vai»."),
   T("**Passo 2.** Comprimento (módulo ou intensidade): é o «tamanho» do vector."),
   T("**Passo 3.** Sentido: é o lado da recta para onde o vector aponta, associado à «posição» da extremidade (orientação)."),
   T("**Passo 4.** Associando na ordem pedida (direcção, comprimento, sentido): onde vai, tamanho e posição. As alíneas B, C e D trocam a ordem (por exemplo, atribuem «posição» ou «tamanho» à direcção), logo estão erradas.")],
  "A")

# ---------------------------------------------------------------- 32
q(32, "Conceptual",
  [T("O vector unitário é dado por:"),
   opcoes(r"\vec{u}=\dfrac{1}{\Vert\vec{v}\Vert}\cdot\vec{v}", r"\vec{u}=\dfrac{1}{\Vert\vec{a}\Vert}", r"\vec{u}=\dfrac{k}{\Vert\vec{v}\Vert}\cdot\vec{v}", r"\vec{u}=k\,\dfrac{1}{\Vert\vec{v}\Vert}\cdot\vec{v}")],
  [T("**Passo 1.** O vector unitário tem módulo 1 e a mesma direcção e sentido de v. Obtém-se dividindo o vector pelo seu módulo:"),
   M(r"\vec{u}=\dfrac{\vec{v}}{\Vert\vec{v}\Vert}=\dfrac{1}{\Vert\vec{v}\Vert}\cdot\vec{v}"),
   T("**Passo 2.** Verificação de que o módulo é 1:"),
   M(r"\Vert\vec{u}\Vert=\dfrac{1}{\Vert\vec{v}\Vert}\cdot\Vert\vec{v}\Vert=1"),
   T("**Passo 3.** As alíneas C e D têm um factor k qualquer, que alteraria o módulo (não seria unitário); a alínea B não contém o vector v. Logo, só A está correcta.")],
  "A")

# ---------------------------------------------------------------- 33
q(33, "Cálculo",
  [T("Usando o vector v = (−9, 2), o vector unitário será igual a:"),
   opcoes(r"\left(\dfrac{-9}{\sqrt{85}},\dfrac{2}{\sqrt{85}}\right)", r"\left(\dfrac{-9}{-2},\dfrac{2}{-2}\right)", r"\left(\dfrac{-9}{-7},\dfrac{2}{-7}\right)", r"\left(\dfrac{-9}{11},\dfrac{2}{11}\right)")],
  [T("**Passo 1.** Módulo do vector:"),
   M(r"\Vert\vec{v}\Vert=\sqrt{(-9)^{2}+2^{2}}=\sqrt{81+4}=\sqrt{85}"),
   T("**Passo 2.** Divide-se cada componente pelo módulo:"),
   M(r"\vec{u}=\dfrac{1}{\sqrt{85}}\cdot(-9,2)=\left(\dfrac{-9}{\sqrt{85}},\dfrac{2}{\sqrt{85}}\right)"),
   T("**Verificação** (módulo de u):"),
   M(r"\sqrt{\left(\dfrac{-9}{\sqrt{85}}\right)^{2}+\left(\dfrac{2}{\sqrt{85}}\right)^{2}}=\sqrt{\dfrac{81}{85}+\dfrac{4}{85}}=\sqrt{\dfrac{85}{85}}=1\ \checkmark")],
  "A")

# ---------------------------------------------------------------- 34
q(34, "Cálculo",
  [T("Seja a = (p; p − 1) com p ∈ ℝ. Se |a| = √5, qual é o valor de p?"),
   M(r"\vec{a}=(p;\,p-1)\qquad\Vert\vec{a}\Vert=\sqrt{5}"),
   opcoes(r"\{1;-2\}", r"\{-1;2\}", r"\{1\}", r"\{2\}")],
  [T("**Passo 1.** Fórmula do módulo:"), M(r"\Vert\vec{a}\Vert=\sqrt{p^{2}+(p-1)^{2}}=\sqrt{5}"),
   T("**Passo 2.** Elevam-se ambos os membros ao quadrado:"), M(r"p^{2}+(p-1)^{2}=5"),
   T("**Passo 3.** Desenvolve-se o quadrado da diferença:"),
   M(r"p^{2}+p^{2}-2p+1=5\ \Rightarrow\ 2p^{2}-2p-4=0"),
   T("**Passo 4.** Divide-se por 2:"), M(r"p^{2}-p-2=0"),
   T("**Passo 5.** Fórmula resolvente (a = 1, b = −1, c = −2):"),
   M(r"\Delta=(-1)^{2}-4\cdot1\cdot(-2)=1+8=9\qquad p=\dfrac{1\pm3}{2}"),
   M(r"p_{1}=\dfrac{1+3}{2}=2\qquad p_{2}=\dfrac{1-3}{2}=-1"),
   T("**Verificação:**"),
   M(r"p=2:\ \sqrt{2^{2}+1^{2}}=\sqrt{5}\ \checkmark\qquad p=-1:\ \sqrt{(-1)^{2}+(-2)^{2}}=\sqrt{5}\ \checkmark"),
   M(r"S=\{-1;2\}")],
  "B")

# ---------------------------------------------------------------- 35
q(35, "Cálculo",
  [T("No SCO, R = (2; 3) e o vector RQ = (1; −1). Quais são as coordenadas do ponto Q?"),
   opcoes("(-5;-2)", "(5;2)", "(3;2)", "(7;10)")],
  [T("**Passo 1.** Um vector com origem em R e extremidade em Q calcula-se por:"),
   M(r"\overrightarrow{RQ}=Q-R\ \Rightarrow\ Q=R+\overrightarrow{RQ}"),
   T("**Passo 2.** Substituem-se as coordenadas:"),
   M(r"Q=(2;3)+(1;-1)=(2+1;\,3+(-1))=(3;2)")],
  "C")

# ---------------------------------------------------------------- 36
q(36, "Cálculo",
  [T("Para que os pontos P(0; 1), Q(3; 4) e R(2k; k) sejam colineares, qual deve ser o valor de k?"),
   opcoes("1", "-2", "2", "-1")],
  [T("**Passo 1.** Três pontos são colineares quando os vectores PQ e PR são paralelos (componentes proporcionais)."),
   M(r"\overrightarrow{PQ}=Q-P=(3-0;\,4-1)=(3;3)"),
   M(r"\overrightarrow{PR}=R-P=(2k-0;\,k-1)=(2k;\,k-1)"),
   T("**Passo 2.** Condição de paralelismo:"),
   M(r"\dfrac{3}{2k}=\dfrac{3}{k-1}\ \Rightarrow\ 3(k-1)=3\cdot2k"),
   T("**Passo 3.** Resolve-se:"),
   M(r"3k-3=6k\ \Rightarrow\ 3k-6k=3\ \Rightarrow\ -3k=3\ \Rightarrow\ k=-1"),
   T("**Verificação:** com k = −1, R = (−2; −1)."),
   M(r"m_{PQ}=\dfrac{4-1}{3-0}=1\qquad m_{PR}=\dfrac{-1-1}{-2-0}=\dfrac{-2}{-2}=1\ \checkmark")],
  "D")

# ---------------------------------------------------------------- 37
q(37, "Cálculo",
  [T("Sendo u = (5; 4) e v = (2; −3), qual é o vector u − v?"),
   opcoes("(3;7)", "(3;1)", "(7;1)", "(-3;-7)")],
  [T("**Passo 1.** A subtracção de vectores faz-se componente a componente:"),
   M(r"\vec{u}-\vec{v}=(5-2;\ 4-(-3))"),
   T("**Passo 2.** Calcula-se:"), M(r"(5-2;\ 4+3)=(3;7)")],
  "A")

# ---------------------------------------------------------------- 38
q(38, "Cálculo",
  [T("Sejam A(0; 1) e v = (1; 2). Qual das seguintes é uma equação vectorial da recta r?"),
   T("A. (x; y) = (1; 5) + k(1; 0), k ∈ ℝ;   B. (x; y) = (0; 1) + k(1; 2), k ∈ ℝ;   C. (x; y) = (1; 0) + k(1; 5), k ∈ ℝ;   D. (x; y) = (1; 0) + k(2; 3), k ∈ ℝ.")],
  [T("**Passo 1.** A equação vectorial de uma recta que passa pelo ponto A e tem vector director v é:"),
   M(r"(x;\,y)=A+k\,\vec{v},\qquad k\in\mathbb{R}"),
   T("**Passo 2.** Substituem-se A = (0; 1) e v = (1; 2):"),
   M(r"(x;\,y)=(0;\,1)+k\,(1;\,2),\qquad k\in\mathbb{R}"),
   T("**Passo 3.** As outras alíneas usam outro ponto ou outro vector director (por exemplo, a alínea A tem vector (1; 0)), logo não representam esta recta.")],
  "B")

# ---------------------------------------------------------------- 39
q(39, "Cálculo",
  [T("Qual é o coeficiente angular da recta que passa pelos pontos A(1; 4) e B(0; 1)?"),
   opcoes("-3", "3", r"\dfrac{1}{4}", "4")],
  [T("**Passo 1.** Coeficiente angular (declive) de uma recta por dois pontos:"),
   M(r"m=\dfrac{y_{B}-y_{A}}{x_{B}-x_{A}}"),
   T("**Passo 2.** Substituem-se as coordenadas:"),
   M(r"m=\dfrac{1-4}{0-1}=\dfrac{-3}{-1}=3")],
  "B")

# ---------------------------------------------------------------- 40
q(40, "Cálculo",
  [T("Dada a equação −4x + 6y = 8, o declive e a ordenada na origem são:"),
   opcoes(r"\dfrac{3}{2}\ \mathrm{e}\ \dfrac{4}{3}", r"\dfrac{2}{3}\ \mathrm{e}\ \dfrac{4}{3}", r"\dfrac{3}{2}\ \mathrm{e}\ \dfrac{4}{3}", r"\dfrac{3}{2}\ \mathrm{e}\ \dfrac{3}{4}")],
  [T("**Passo 1.** Passa-se a equação para a forma reduzida y = mx + b (m é o declive e b a ordenada na origem). Isola-se o termo em y:"),
   M(r"-4x+6y=8\ \Rightarrow\ 6y=4x+8"),
   T("**Passo 2.** Divide-se tudo por 6:"),
   M(r"y=\dfrac{4}{6}x+\dfrac{8}{6}"),
   T("**Passo 3.** Simplificam-se as fracções:"),
   M(r"y=\dfrac{2}{3}x+\dfrac{4}{3}"),
   T("**Passo 4.** Declive m = 2/3 e ordenada na origem b = 4/3."),
   T("**Verificação:** para x = 0, y = 8/6 = 4/3 ✓ (a recta corta o eixo dos y em 4/3).")],
  "B")

QUESTOES = Q
