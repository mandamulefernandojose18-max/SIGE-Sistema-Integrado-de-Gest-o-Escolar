"""
Validadores de Domínio e Normas Oficiais — SIGE / MINEDH (Moçambique)
"""
import re
from .exceptions import InvalidDomainValueViolation

PERIODOS_VALIDOS = {'1_TRIMESTRE', '2_TRIMESTRE', '3_TRIMESTRE', 'ANUAL'}
COMPORTAMENTOS_VALIDOS = {'NS', 'S', 'B', 'MB', 'E'}
ANOTACOES_VALIDAS = {'D', 'T', 'VT', 'F', 'AM', 'PPF', 'PDF'}
RESULTADOS_VALIDOS = {'Aprovado', 'Reprovado', 'Excluido', 'Dispensado', 'Admitido', 'Sem Nota'}

def validar_escala_nota(valor):
    """
    Garante que a nota escolar esteja estritamente dentro da escala oficial do MINEDH (0.0 a 20.0).
    """
    if valor is None:
        return
    try:
        val = float(valor)
    except (ValueError, TypeError):
        raise InvalidDomainValueViolation(f"O valor de nota '{valor}' não é um número válido.")

    if val < 0.0 or val > 20.0:
        raise InvalidDomainValueViolation(
            f"A nota {val} viola a escala regulamentar do MINEDH. O valor deve estar compreendido entre 0.0 e 20.0."
        )

def validar_faltas(valor):
    """
    Garante que a quantidade de faltas seja um número inteiro não negativo (>= 0).
    """
    if valor is None:
        return
    try:
        val = int(valor)
    except (ValueError, TypeError):
        raise InvalidDomainValueViolation(f"O valor de faltas '{valor}' deve ser um número inteiro.")

    if val < 0:
        raise InvalidDomainValueViolation(f"O número de faltas não pode ser negativo ({val}).")

def validar_nuit_mz(nuit):
    """
    Valida a sintaxe do NUIT moçambicano (Número Único de Identificação Tributária - 9 dígitos).
    """
    if not nuit:
        return
    nuit_str = str(nuit).strip()
    if not re.match(r'^\d{9}$', nuit_str):
        raise InvalidDomainValueViolation(
            f"O NUIT '{nuit}' é inválido. O NUIT em Moçambique deve conter exatamente 9 dígitos numéricos."
        )

def validar_periodo_academico(periodo):
    """
    Valida se o período acadêmico corresponde aos trimestres ou ano letivo oficial.
    """
    if not periodo:
        raise InvalidDomainValueViolation("O período acadêmico é obrigatório.")
    if periodo not in PERIODOS_VALIDOS:
        raise InvalidDomainValueViolation(
            f"Período '{periodo}' inválido. Valores aceitos: {', '.join(sorted(PERIODOS_VALIDOS))}."
        )

def validar_comportamento(comportamento):
    """
    Valida a sigla de comportamento segundo o Ministério da Educação (NS, S, B, MB, E).
    """
    if not comportamento:
        return
    if comportamento not in COMPORTAMENTOS_VALIDOS:
        raise InvalidDomainValueViolation(
            f"Classificação de comportamento '{comportamento}' inválida. Valores aceitos: {', '.join(sorted(COMPORTAMENTOS_VALIDOS))}."
        )

def validar_anotacao_minedh(anotacao):
    """
    Valida as siglas oficiais de anotações em pautas e cadernetas do MINEDH:
    D=Dispensado, T=Transferido, VT=Vindo de Transferência, F=Falecido,
    AM=Anulação de Matrícula, PPF=Pede Prova Final, PDF=Prova de Fim de Ciclo.
    """
    if not anotacao:
        return
    if anotacao not in ANOTACOES_VALIDAS:
        raise InvalidDomainValueViolation(
            f"Anotação '{anotacao}' inválida. Siglas normativas do MINEDH aceitas: {', '.join(sorted(ANOTACOES_VALIDAS))}."
        )
