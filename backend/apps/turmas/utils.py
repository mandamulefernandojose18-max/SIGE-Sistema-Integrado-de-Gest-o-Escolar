import re
from django.core.exceptions import ValidationError

def extrair_identificador_turma(nome, grau_ano=""):
    """
    Extrai o tipo ('NUMERO', 'LETRA', 'OUTRO') e o identificador único da turma dentro da classe,
    independentemente de possuir prefixo da classe (ex: '11ª Classe Turma 1' vs 'Turma 1')
    e removendo sufixos de colisão legados como ' (1)'.

    Retorna:
        tuple: (tipo, valor, rotulo_amigavel)
        Exemplos:
          '11ª Classe Turma 1'      -> ('NUMERO', 1, 'Turma 1')
          '11ª Classe Turma 1 (1)'  -> ('NUMERO', 1, 'Turma 1')
          'Turma 1'                 -> ('NUMERO', 1, 'Turma 1')
          'Turma 2'                 -> ('NUMERO', 2, 'Turma 2')
          '10ª Classe Turma A'      -> ('LETRA', 'A', 'Turma A')
          'Turma B'                 -> ('LETRA', 'B', 'Turma B')
          '10ª Classe A'            -> ('LETRA', 'A', 'Turma A')
    """
    if not nome:
        return ('NENHUM', 0, '')

    nome_str = str(nome).strip()
    if nome_str.startswith('__TMP_'):
        return ('TEMPORARIO', 0, '')

    # Remove qualquer sufixo de colisão tipo ' (1)', ' (2)'
    nome_limpo = re.sub(r'\s*\(\d+\)$', '', nome_str).strip()

    # 1. Procura explícito 'Turma <numero>'
    m_num = re.search(r'turma\s*(\d+)', nome_limpo, re.IGNORECASE)
    if m_num:
        num = int(m_num.group(1))
        return ('NUMERO', num, f'Turma {num}')

    # 2. Procura explícito 'Turma <letra>'
    m_letra = re.search(r'turma\s*([a-zA-Z])\b', nome_limpo, re.IGNORECASE)
    if m_letra:
        letra = m_letra.group(1).upper()
        return ('LETRA', letra, f'Turma {letra}')

    # 3. Remover o prefixo do grau_ano para não confundir '11ª' ou '10ª' com o número da turma
    resto = nome_limpo
    if grau_ano:
        grau_str = str(grau_ano).strip()
        resto = re.sub(re.escape(grau_str), '', resto, flags=re.IGNORECASE).strip()
        # Variações tipo '11ª', '11'
        nums_grau = re.findall(r'\d+', grau_str)
        if nums_grau:
            g_num = nums_grau[0]
            resto = re.sub(rf'\b{g_num}[ªºa-zA-Z\s]*classe\b', '', resto, flags=re.IGNORECASE).strip()
            resto = re.sub(rf'\b{g_num}[ªº]\b', '', resto, flags=re.IGNORECASE).strip()

    # Procura número no restante
    nums = re.findall(r'\d+', resto)
    if nums:
        num = int(nums[-1])
        return ('NUMERO', num, f'Turma {num}')

    # Procura letra única no restante
    letras = re.findall(r'\b([a-zA-Z])\b', resto)
    if letras:
        letra = letras[-1].upper()
        return ('LETRA', letra, f'Turma {letra}')

    return ('OUTRO', nome_limpo.upper(), nome_limpo)


def obter_proximo_numero_turma_classe(escola, grau_ano, ano_letivo, tipo_sufixo='NUMERO', exclude_id=None):
    """
    Calcula a próxima numeração (ou letra) contínua para uma classe no ano letivo,
    verificando TODAS as turmas da classe, independentemente da secção ou área de estudo.
    """
    from apps.turmas.models import Turma
    qs = Turma.objects.filter(escola=escola, grau_ano__iexact=grau_ano, ano_letivo=ano_letivo)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)

    if tipo_sufixo == 'LETRA':
        letras = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        letras_usadas = set()
        for t in qs:
            tipo, val, _ = extrair_identificador_turma(t.nome, t.grau_ano)
            if tipo == 'LETRA':
                letras_usadas.add(val)
        for l in letras:
            if l not in letras_usadas:
                return l
        return 'A'
    else:
        max_num = 0
        for t in qs:
            tipo, val, _ = extrair_identificador_turma(t.nome, t.grau_ano)
            if tipo == 'NUMERO' and val > max_num:
                max_num = val
        return max_num + 1


def validar_unicidade_turma_na_classe(escola, grau_ano, nome, ano_letivo, exclude_id=None):
    """
    Valida que não existe outra turma com o mesmo número/letra na mesma classe e ano letivo,
    mesmo que pertençam a secções/áreas diferentes.
    """
    if not escola or not grau_ano or not nome:
        return

    from apps.turmas.models import Turma
    tipo, val, rotulo = extrair_identificador_turma(nome, grau_ano)
    if tipo not in ('NUMERO', 'LETRA'):
        return

    qs = Turma.objects.filter(
        escola=escola,
        grau_ano__iexact=str(grau_ano).strip(),
        ano_letivo=str(ano_letivo).strip()
    )
    if exclude_id:
        qs = qs.exclude(id=exclude_id)

    for t in qs:
        t_tipo, t_val, _ = extrair_identificador_turma(t.nome, t.grau_ano)
        if t_tipo == tipo and t_val == val:
            area_info = t.area or 'Geral'
            turno_info = t.turno or 'Diurno'
            raise ValidationError(
                f"Já existe a '{rotulo}' cadastrada na {grau_ano} (Secção/Área: '{area_info}', Turno: {turno_info}, Nome: '{t.nome}'). "
                f"Na mesma classe, a numeração das turmas (Turma 1, Turma 2, Turma 3...) deve ser sequencial e sem repetição, "
                f"independentemente da secção ou área de estudo."
            )
