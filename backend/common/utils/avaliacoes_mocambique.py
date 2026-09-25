"""
Regras Oficiais de Avaliação e Aprovação - Sistema Nacional de Educação de Moçambique (MINEDH)
"""
from typing import Dict, Any, List, Optional
import math
import re

def calcular_media_trimestral(dados: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcula a média trimestral conforme normas do MINEDH:
    MAC = média aritmética das avaliações contínuas (testes e trabalhos)
    MT = (2 * MAC + AT) / 3 arredondado para número inteiro (escala 0-20)
    """
    testes_validos: List[float] = []
    for chave in ['teste1', 'teste2', 'teste3', 'teste4', 'trabalho']:
        val = dados.get(chave)
        if val is not None:
            try:
                num = float(val)
                testes_validos.append(num)
            except (ValueError, TypeError):
                pass

    at = 0.0
    val_at = dados.get('avaliacao_trimestral')
    if val_at is not None:
        try:
            at = float(val_at)
        except (ValueError, TypeError):
            pass

    mac = 0.0
    if len(testes_validos) > 0:
        soma = sum(testes_validos)
        mac = round(soma / len(testes_validos), 1)

    media_final = 0
    if at > 0 and len(testes_validos) > 0:
        media_final = int(round((2 * mac + at) / 3))
    elif len(testes_validos) > 0:
        media_final = int(round(mac))
    elif at > 0:
        media_final = int(round(at))

    # Limitar escala de 0 a 20
    media_final = max(0, min(20, media_final))

    aprovado = media_final >= 9.5
    resultado = 'Aprovado' if aprovado else 'Reprovado'
    cor = 'preto' if aprovado else 'vermelho'

    if media_final >= 18.5:
        comportamento = 'E'   # Excelente
    elif media_final >= 16.5:
        comportamento = 'MB'  # Muito Bom
    elif media_final >= 13.5:
        comportamento = 'B'   # Bom
    elif media_final >= 9.5:
        comportamento = 'S'   # Suficiente
    else:
        comportamento = 'NS'  # Não Suficiente

    return {
        'mediaContinua': mac,
        'mediaFinal': media_final,
        'resultado': resultado,
        'comportamento': comportamento,
        'cor': cor
    }

def avaliar_aprovacao_pauta(
    notas_disciplinas: List[Dict[str, Any]],
    grau_ano: Optional[str] = None
) -> Dict[str, Any]:
    """
    Critério Oficial de Aprovação na Pauta Anual do Aluno (MINEDH):
    - Excepto a 12ª classe: O aluno SÓ APROVA se tiver em TODAS as disciplinas notas positivas (zero negativas).
    - Na 12ª classe: O aluno aprova se tiver Média geral >= 9.5 valores, no máximo 2 negativas e nenhuma negativa < 8.
    """
    grau_normalizado = (grau_ano or '').lower()
    is_12a_classe = bool(re.search(r'(^|[^\d])12([ªaº\.\s]|$)', grau_normalizado))
    is_classe_exame = bool(re.search(r'(^|[^\d])(9|12)([ªaº\.\s]|$)', grau_normalizado))

    if not notas_disciplinas:
        return {
            'aprovado': False,
            'resultado': 'Reprovado',
            'siglaResultado': 'R',
            'mediaGeral': 0,
            'totalNegativas': 0,
            'temNotaInferiorA8': False,
            'is12aClasse': is_12a_classe,
            'isClasseExame': is_classe_exame,
            'motivo': 'Sem notas lançadas'
        }

    soma = 0.0
    total_negativas = 0
    tem_nota_inferior_a_8 = False

    for item in notas_disciplinas:
        nota = float(item.get('notaFinal', 0))
        soma += nota
        if nota < 9.5:
            total_negativas += 1
            if nota < 8.0:
                tem_nota_inferior_a_8 = True

    media_geral = int(round(soma / len(notas_disciplinas)))

    # 1. Regra Geral (Excepto 12ª classe): 100% de positivas
    if not is_12a_classe:
        if total_negativas > 0:
            return {
                'aprovado': False,
                'resultado': 'Reprovado',
                'siglaResultado': 'R',
                'mediaGeral': media_geral,
                'totalNegativas': total_negativas,
                'temNotaInferiorA8': tem_nota_inferior_a_8,
                'is12aClasse': False,
                'isClasseExame': is_classe_exame,
                'motivo': f'Reprovado: Excepto na 12ª classe, o aluno só aprova se tiver 100% de positivas (0 negativas). Possui {total_negativas} negativa(s).'
            }

        if media_geral < 9.5:
            return {
                'aprovado': False,
                'resultado': 'Reprovado',
                'siglaResultado': 'R',
                'mediaGeral': media_geral,
                'totalNegativas': total_negativas,
                'temNotaInferiorA8': tem_nota_inferior_a_8,
                'is12aClasse': False,
                'isClasseExame': is_classe_exame,
                'motivo': f'Reprovado: Média geral {media_geral} inferior a 9.5 valores.'
            }

        return {
            'aprovado': True,
            'resultado': 'Aprovado',
            'siglaResultado': 'A',
            'mediaGeral': media_geral,
            'totalNegativas': 0,
            'temNotaInferiorA8': False,
            'is12aClasse': False,
            'isClasseExame': is_classe_exame,
            'motivo': 'Aprovado com 100% de positivas (0 negativas).'
        }

    # 2. Regra da 12ª Classe: Média >= 9.5, máx 2 negativas e NENHUMA < 8
    if tem_nota_inferior_a_8:
        return {
            'aprovado': False,
            'resultado': 'Reprovado',
            'siglaResultado': 'R',
            'mediaGeral': media_geral,
            'totalNegativas': total_negativas,
            'temNotaInferiorA8': True,
            'is12aClasse': True,
            'isClasseExame': True,
            'motivo': 'Reprovado na 12ª classe: possui nota inferior a 8 valores.'
        }

    if total_negativas > 2:
        return {
            'aprovado': False,
            'resultado': 'Reprovado',
            'siglaResultado': 'R',
            'mediaGeral': media_geral,
            'totalNegativas': total_negativas,
            'temNotaInferiorA8': False,
            'is12aClasse': True,
            'isClasseExame': True,
            'motivo': f'Reprovado na 12ª classe: possui {total_negativas} negativas (máximo permitido é 2).'
        }

    if media_geral < 9.5:
        return {
            'aprovado': False,
            'resultado': 'Reprovado',
            'siglaResultado': 'R',
            'mediaGeral': media_geral,
            'totalNegativas': total_negativas,
            'temNotaInferiorA8': False,
            'is12aClasse': True,
            'isClasseExame': True,
            'motivo': f'Reprovado na 12ª classe: média geral {media_geral} inferior a 9.5 valores.'
        }

    return {
        'aprovado': True,
        'resultado': 'Aprovado',
        'siglaResultado': 'A',
        'mediaGeral': media_geral,
        'totalNegativas': total_negativas,
        'temNotaInferiorA8': False,
        'is12aClasse': True,
        'isClasseExame': True,
        'motivo': f'Aprovado na 12ª classe com {total_negativas} negativa(s) tolerada(s) (>= 8 valores) e média {media_geral}.' if total_negativas > 0 else f'Aprovado na 12ª classe com aproveitamento pleno e média {media_geral}.'
    }
