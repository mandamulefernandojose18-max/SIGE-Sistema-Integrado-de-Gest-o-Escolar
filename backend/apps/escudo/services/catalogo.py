"""Listas fixas do formulário: tipos de avaliação, disciplinas e classes do ensino moçambicano."""

TIPOS_AVALIACAO = ("1.ª ACS", "2.ª ACS", "3.ª ACS", "Avaliação Trimestral")
TRIMESTRES = ("I Trimestre", "II Trimestre", "III Trimestre")
DISCIPLINAS = (
    "Português", "Inglês", "Francês", "Matemática", "Matemática Ciências", "Matemática Letras", "Física", "Química", "Biologia", "Geografia", "História",
    "Filosofia", "Educação Física", "Educação Visual", "Desenho e Geometria Descritiva", "Agro-pecuária",
    "Tecnologias de Informação e Comunicação", "Empreendedorismo", "Educação Moral e Cívica", "Ciências Naturais",
    "Ciências Sociais", "Educação Musical", "Ofícios", "Línguas Moçambicanas",
)
CLASSES = tuple(f"{n}.ª Classe" for n in range(1, 13))


def escolher(valor, opcoes, nome):
    valor = (valor or "").strip()
    if valor not in opcoes:
        raise ValueError(f"Escolhe {nome} da lista.")
    return valor


def titulo_avaliacao(tipo, disciplina, classe, trimestre=""):
    """«1.ª ACS de Física · 11.ª Classe · II Trimestre»: o título passa a vir das escolhas, sem texto livre."""
    tipo = escolher(tipo, TIPOS_AVALIACAO, "o tipo de avaliação")
    disciplina = escolher(disciplina, DISCIPLINAS, "a disciplina")
    classe = escolher(classe, CLASSES, "a classe")
    partes = [f"{tipo} de {disciplina}", classe]
    if trimestre:
        partes.append(escolher(trimestre, TRIMESTRES, "o trimestre"))
    return " · ".join(partes)
