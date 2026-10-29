"""
Módulo de Conversão Numérica para Extenso em Português (Moçambique) — SIGE
Converte quantias monetárias em Meticais (MT) e Centavos para a forma por extenso
rigorosamente em conformidade com as normas gramaticais de Moçambique.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Union

UNIDADES = {
    0: 'zero', 1: 'um', 2: 'dois', 3: 'três', 4: 'quatro',
    5: 'cinco', 6: 'seis', 7: 'sete', 8: 'oito', 9: 'nove',
    10: 'dez', 11: 'onze', 12: 'doze', 13: 'treze', 14: 'catorze',
    15: 'quinze', 16: 'dezasseis', 17: 'dezassete', 18: 'dezoito', 19: 'dezanove'
}

DEZENAS = {
    20: 'vinte', 30: 'trinta', 40: 'quarenta', 50: 'cinquenta',
    60: 'sessenta', 70: 'setenta', 80: 'oitenta', 90: 'noventa'
}

CENTENAS = {
    100: 'cento', 200: 'duzentos', 300: 'trezentos', 400: 'quatrocentos',
    500: 'quinhentos', 600: 'seiscentos', 700: 'setecentos', 800: 'oitocentos', 900: 'novecentos'
}


def _numero_ate_99(n: int) -> str:
    if n in UNIDADES:
        return UNIDADES[n]
    d = (n // 10) * 10
    u = n % 10
    if u == 0:
        return DEZENAS.get(d, '')
    return f"{DEZENAS[d]} e {UNIDADES[u]}"


def _numero_ate_999(n: int) -> str:
    if n == 100:
        return 'cem'
    if n < 100:
        return _numero_ate_99(n)
    c = (n // 100) * 100
    resto = n % 100
    if resto == 0:
        return CENTENAS.get(c, '')
    return f"{CENTENAS[c]} e {_numero_ate_99(resto)}"


def _inteiro_para_extenso(n: int) -> str:
    if n == 0:
        return 'zero'
    if n < 1000:
        return _numero_ate_999(n)

    if n < 1_000_000:
        milhares = n // 1000
        resto = n % 1000
        if milhares == 1:
            str_milhares = 'mil'
        else:
            str_milhares = f"{_numero_ate_999(milhares)} mil"

        if resto == 0:
            return str_milhares
        if resto <= 100 or resto % 100 == 0:
            return f"{str_milhares} e {_numero_ate_999(resto)}"
        return f"{str_milhares} e {_numero_ate_999(resto)}"

    if n < 1_000_000_000:
        milhoes = n // 1_000_000
        resto = n % 1_000_000
        if milhoes == 1:
            str_milhoes = 'um milhão'
        else:
            str_milhoes = f"{_numero_ate_999(milhoes)} milhões"

        if resto == 0:
            return str_milhoes
        if resto < 1000 or resto % 100_000 == 0:
            return f"{str_milhoes} e {_inteiro_para_extenso(resto)}"
        return f"{str_milhoes} e {_inteiro_para_extenso(resto)}"

    bilhoes = n // 1_000_000_000
    resto = n % 1_000_000_000
    if bilhoes == 1:
        str_bilhoes = 'um bilião'
    else:
        str_bilhoes = f"{_numero_ate_999(bilhoes)} biliões"

    if resto == 0:
        return str_bilhoes
    return f"{str_bilhoes} e {_inteiro_para_extenso(resto)}"


def numero_para_extenso_meticais(valor: Union[int, float, Decimal, str, None], capitalizar: bool = True) -> str:
    """
    Converte um valor numérico em sua representação por extenso na moeda Meticais (Moçambique).
    Exemplos:
        1500    -> "Mil e quinhentos meticais"
        1500.50 -> "Mil e quinhentos meticais e cinquenta centavos"
        1       -> "Um metical"
        0       -> "Zero meticais"
    """
    if valor is None or valor == '' or valor == '-':
        return 'Zero meticais' if capitalizar else 'zero meticais'

    try:
        if isinstance(valor, str):
            # Normalizar separadores
            v_str = valor.replace('MT', '').replace('MZN', '').replace(' ', '').replace(',', '.')
            d_val = Decimal(v_str)
        else:
            d_val = Decimal(str(valor))
    except Exception:
        return 'Zero meticais' if capitalizar else 'zero meticais'

    # Arredondar para 2 casas decimais
    d_val = d_val.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    int_part = int(d_val)
    centavos = int((d_val - int_part) * 100)

    if int_part == 0 and centavos == 0:
        res = 'zero meticais'
    elif int_part == 0 and centavos > 0:
        res = 'um centavo' if centavos == 1 else f"{_inteiro_para_extenso(centavos)} centavos"
    else:
        if int_part == 1:
            nome_moeda = 'metical'
        elif int_part >= 1_000_000 and int_part % 1_000_000 == 0:
            nome_moeda = 'de meticais'
        else:
            nome_moeda = 'meticais'

        extenso_int = _inteiro_para_extenso(int_part)
        res = f"{extenso_int} {nome_moeda}"

        if centavos > 0:
            cents_str = 'um centavo' if centavos == 1 else f"{_inteiro_para_extenso(centavos)} centavos"
            res = f"{res} e {cents_str}"

    if capitalizar and res:
        res = res[0].upper() + res[1:]
    return res


def formatar_valor_com_extenso(valor: Union[int, float, Decimal, str, None], sufixo_moeda: str = 'MT') -> str:
    """
    Formata o valor exibindo tanto os algarismos quanto o extenso.
    Exemplos:
        1500    -> "1500 MT (Mil e quinhentos meticais)"
        1500.50 -> "1500,50 MT (Mil e quinhentos meticais e cinquenta centavos)"
    """
    if valor is None or valor == '':
        return f"0 {sufixo_moeda} (Zero meticais)"

    extenso = numero_para_extenso_meticais(valor, capitalizar=True)

    try:
        if isinstance(valor, str):
            v_str = valor.replace('MT', '').replace('MZN', '').replace(' ', '').replace(',', '.')
            d_val = Decimal(v_str)
        else:
            d_val = Decimal(str(valor))
        
        # Formatar algarismos: se inteiro sem casas decimais, manter inteiro limpo (ex: 1500)
        if d_val == d_val.to_integral():
            num_formatado = f"{int(d_val)}"
        else:
            num_formatado = f"{d_val:.2f}".replace('.', ',')
    except Exception:
        num_formatado = str(valor)

    return f"{num_formatado} {sufixo_moeda} ({extenso})"
