"""
Validadores de Domínio e Normas Oficiais — SIGE / MEC (Moçambique)
"""
import re
from .exceptions import InvalidDomainValueViolation

PERIODOS_VALIDOS = {'1_TRIMESTRE', '2_TRIMESTRE', '3_TRIMESTRE', 'ANUAL', 'EXAME'}
COMPORTAMENTOS_VALIDOS = {'NS', 'S', 'B', 'MB', 'E'}
ANOTACOES_VALIDAS = {'D', 'T', 'VT', 'F', 'AM', 'PPF', 'PDF'}
RESULTADOS_VALIDOS = {'Aprovado', 'Reprovado', 'Excluido', 'Dispensado', 'Admitido', 'Sem Nota'}

def validar_escala_nota(valor):
    """
    Garante que a nota escolar esteja estritamente dentro da escala oficial do MEC (0.0 a 20.0).
    """
    if valor is None:
        return
    try:
        val = float(valor)
    except (ValueError, TypeError):
        raise InvalidDomainValueViolation(f"O valor de nota '{valor}' não é um número válido.")

    if val < 0.0 or val > 20.0:
        raise InvalidDomainValueViolation(
            f"A nota {val} viola a escala regulamentar do MEC. O valor deve estar compreendido entre 0.0 e 20.0."
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
    Valida a sintaxe do NUIT moçambicano (Número Único de Identificação Tributária - no máximo 9 dígitos, apenas números).
    """
    if not nuit:
        return
    nuit_str = str(nuit).strip()
    if not re.match(r'^\d{1,9}$', nuit_str):
        raise InvalidDomainValueViolation(
            f"O NUIT '{nuit}' é inválido. O NUIT em Moçambique não pode conter letras e é limitado a no máximo 9 dígitos numéricos."
        )

def validar_telefone_sem_letras(telefone, nome_campo="Contacto/Telefone"):
    """
    Garante que campos de telefone ou telemóvel não aceitem letras e contenham apenas números.
    """
    if not telefone:
        return
    tel_str = str(telefone).strip()
    if re.search(r'[a-zA-Z\u00C0-\u017F]', tel_str):
        raise InvalidDomainValueViolation(
            f"O campo '{nome_campo}' ('{telefone}') não pode conter letras. Deve conter apenas números."
        )

def validar_campo_numerico_sem_letras(valor, nome_campo="Campo Numérico"):
    """
    Garante que qualquer campo que leve número ou quantidade não possa aceitar inserção de letras.
    """
    if valor is None:
        return
    val_str = str(valor).strip()
    if re.search(r'[a-zA-Z\u00C0-\u017F]', val_str):
        raise InvalidDomainValueViolation(
            f"O campo '{nome_campo}' ('{valor}') não pode conter letras. Deve conter apenas valores numéricos."
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
    Valida as siglas oficiais de anotações em pautas e cadernetas do MEC:
    D=Dispensado, T=Transferido, VT=Vindo de Transferência, F=Falecido,
    AM=Anulação de Matrícula, PPF=Pede Prova Final, PDF=Prova de Fim de Ciclo.
    """
    if not anotacao:
        return
    if anotacao not in ANOTACOES_VALIDAS:
        raise InvalidDomainValueViolation(
            f"Anotação '{anotacao}' inválida. Siglas normativas do MEC aceitas: {', '.join(sorted(ANOTACOES_VALIDAS))}."
        )

def validar_unicidade_codigo_sistema(codigo, exclude_aluno_id=None, exclude_prof_id=None, exclude_usuario_id=None, exclude_turma_id=None):
    """
    Garante a unicidade global absoluta do código de acesso/identificação.
    Nunca permite coincidência entre os códigos de alunos ou de qualquer funcionário
    (Direcção Geral, Direcção Pedagógica, Chefia de Secretaria, Professores, DT, DC).
    """
    if not codigo:
        return
    from common.utils.geografia_mocambique import codigo_ja_existe_globalmente
    if codigo_ja_existe_globalmente(
        codigo=codigo,
        exclude_aluno_id=exclude_aluno_id,
        exclude_prof_id=exclude_prof_id,
        exclude_usuario_id=exclude_usuario_id,
        exclude_turma_id=exclude_turma_id,
    ):
        raise InvalidDomainValueViolation(
            f"O código '{codigo}' viola a regra de unicidade global do SIGE. "
            "Não pode haver coincidência entre códigos de alunos e de qualquer funcionário."
        )
