/**
 * Regras Oficiais de Avaliação e Aprovação - Sistema Nacional de Educação de Moçambique
 */

export interface DadosAvaliacaoTrimestre {
  teste1?: number | null;
  teste2?: number | null;
  teste3?: number | null;
  teste4?: number | null;
  trabalho?: number | null;
  avaliacao_trimestral?: number | null;
}

export function calcularMediaTrimestral(dados: DadosAvaliacaoTrimestre): {
  mediaContinua: number;
  mediaFinal: number;
  resultado: 'Aprovado' | 'Reprovado';
  comportamento: 'NS' | 'S' | 'B' | 'MB' | 'E';
  cor: 'preto' | 'vermelho';
} {
  // Testes realizados
  const testesValidos: number[] = [];
  if (dados.teste1 !== undefined && dados.teste1 !== null && !isNaN(dados.teste1)) testesValidos.push(Number(dados.teste1));
  if (dados.teste2 !== undefined && dados.teste2 !== null && !isNaN(dados.teste2)) testesValidos.push(Number(dados.teste2));
  if (dados.teste3 !== undefined && dados.teste3 !== null && !isNaN(dados.teste3)) testesValidos.push(Number(dados.teste3));
  if (dados.teste4 !== undefined && dados.teste4 !== null && !isNaN(dados.teste4)) testesValidos.push(Number(dados.teste4));
  if (dados.trabalho !== undefined && dados.trabalho !== null && !isNaN(dados.trabalho)) testesValidos.push(Number(dados.trabalho));

  const at = dados.avaliacao_trimestral !== undefined && dados.avaliacao_trimestral !== null && !isNaN(dados.avaliacao_trimestral)
    ? Number(dados.avaliacao_trimestral)
    : 0;

  let mac = 0;
  if (testesValidos.length > 0) {
    const soma = testesValidos.reduce((acc, curr) => acc + curr, 0);
    mac = Number((soma / testesValidos.length).toFixed(1));
  }

  // Média Trimestral Oficial MINEDH: MT = (2 * MAC + AT) / 3 arredondado para número inteiro
  let mediaFinal = 0;
  if (at > 0 && testesValidos.length > 0) {
    mediaFinal = Math.round((2 * mac + at) / 3);
  } else if (testesValidos.length > 0) {
    mediaFinal = Math.round(mac);
  } else if (at > 0) {
    mediaFinal = Math.round(at);
  }

  // Limitar escala de 0 a 20
  mediaFinal = Math.max(0, Math.min(20, mediaFinal));

  const aprovado = mediaFinal >= 9.5;
  const resultado: 'Aprovado' | 'Reprovado' = aprovado ? 'Aprovado' : 'Reprovado';
  const cor: 'preto' | 'vermelho' = aprovado ? 'preto' : 'vermelho';

  // Comportamento automático segundo intervalos oficiais MINEDH:
  // NS (0 a 9.4), S (9.5 a 13.4), B (13.5 a 16.4), MB (16.5 a 18.4), E (18.5 a 20)
  let comportamento: 'NS' | 'S' | 'B' | 'MB' | 'E' = 'NS';
  if (mediaFinal >= 18.5) comportamento = 'E'; // Excelente
  else if (mediaFinal >= 16.5) comportamento = 'MB'; // Muito Bom
  else if (mediaFinal >= 13.5) comportamento = 'B'; // Bom
  else if (mediaFinal >= 9.5) comportamento = 'S'; // Suficiente
  else comportamento = 'NS'; // Não Suficiente

  return {
    mediaContinua: mac,
    mediaFinal,
    resultado,
    comportamento,
    cor
  };
}

/**
 * Critério Oficial de Aprovação na Pauta Anual do Aluno (Requisito 25 e Directriz Oficial MINEDH):
 * - Excepto a 12ª classe: O aluno SÓ APROVA se tiver em TODAS as disciplinas notas positivas (zero negativas).
 * - Na 12ª classe: O aluno aprova se tiver Média geral >= 9,5 valores, no máximo 2 negativas e nenhuma negativa < 8.
 */
export function avaliarAprovacaoPauta(
  notasDisciplinas: Array<{ disciplina: string; notaFinal: number }>,
  grauAno?: string
): {
  aprovado: boolean;
  resultado: 'Aprovado' | 'Reprovado';
  siglaResultado: 'A' | 'R';
  mediaGeral: number;
  totalNegativas: number;
  temNotaInferiorA8: boolean;
  is12aClasse: boolean;
  isClasseExame: boolean;
  motivo?: string;
} {
  const grauNormalizado = (grauAno || '').toLowerCase();
  const is12aClasse = /\b12\b/.test(grauNormalizado);
  const isClasseExame = /\b(9|12)\b/.test(grauNormalizado);

  if (notasDisciplinas.length === 0) {
    return {
      aprovado: false,
      resultado: 'Reprovado',
      siglaResultado: 'R',
      mediaGeral: 0,
      totalNegativas: 0,
      temNotaInferiorA8: false,
      is12aClasse,
      isClasseExame,
      motivo: 'Sem notas lançadas'
    };
  }

  let soma = 0;
  let totalNegativas = 0;
  let temNotaInferiorA8 = false;

  for (const item of notasDisciplinas) {
    soma += item.notaFinal;
    if (item.notaFinal < 9.5) {
      totalNegativas++;
      if (item.notaFinal < 8) {
        temNotaInferiorA8 = true;
      }
    }
  }

  const mediaGeral = Math.round(soma / notasDisciplinas.length);

  // 1. Regra Geral (Excepto 12ª classe): O aluno SÓ APROVA se tiver em TODAS as disciplinas notas positivas (zero negativas)
  if (!is12aClasse) {
    if (totalNegativas > 0) {
      return {
        aprovado: false,
        resultado: 'Reprovado',
        siglaResultado: 'R',
        mediaGeral,
        totalNegativas,
        temNotaInferiorA8,
        is12aClasse: false,
        isClasseExame,
        motivo: `Reprovado: Excepto na 12ª classe, o aluno só aprova se tiver 100% de positivas (0 negativas). Possui ${totalNegativas} negativa(s).`
      };
    }

    if (mediaGeral < 9.5) {
      return {
        aprovado: false,
        resultado: 'Reprovado',
        siglaResultado: 'R',
        mediaGeral,
        totalNegativas,
        temNotaInferiorA8,
        is12aClasse: false,
        isClasseExame,
        motivo: `Reprovado: Média geral ${mediaGeral} inferior a 9.5 valores.`
      };
    }

    return {
      aprovado: true,
      resultado: 'Aprovado',
      siglaResultado: 'A',
      mediaGeral,
      totalNegativas: 0,
      temNotaInferiorA8: false,
      is12aClasse: false,
      isClasseExame,
      motivo: 'Aprovado com 100% de positivas (0 negativas).'
    };
  }

  // 2. Regra da 12ª Classe: Aprova com média geral >= 9.5, máx 2 negativas e NENHUMA < 8
  if (temNotaInferiorA8) {
    return {
      aprovado: false,
      resultado: 'Reprovado',
      siglaResultado: 'R',
      mediaGeral,
      totalNegativas,
      temNotaInferiorA8: true,
      is12aClasse: true,
      isClasseExame: true,
      motivo: 'Reprovado na 12ª classe: possui nota inferior a 8 valores.'
    };
  }

  if (totalNegativas > 2) {
    return {
      aprovado: false,
      resultado: 'Reprovado',
      siglaResultado: 'R',
      mediaGeral,
      totalNegativas,
      temNotaInferiorA8: false,
      is12aClasse: true,
      isClasseExame: true,
      motivo: `Reprovado na 12ª classe: possui ${totalNegativas} negativas (máximo permitido é 2).`
    };
  }

  if (mediaGeral < 9.5) {
    return {
      aprovado: false,
      resultado: 'Reprovado',
      siglaResultado: 'R',
      mediaGeral,
      totalNegativas,
      temNotaInferiorA8,
      is12aClasse: true,
      isClasseExame: true,
      motivo: `Reprovado na 12ª classe: média geral ${mediaGeral} inferior a 9.5 valores.`
    };
  }

  return {
    aprovado: true,
    resultado: 'Aprovado',
    siglaResultado: 'A',
    mediaGeral,
    totalNegativas,
    temNotaInferiorA8: false,
    is12aClasse: true,
    isClasseExame: true,
    motivo: totalNegativas > 0
      ? `Aprovado na 12ª classe com ${totalNegativas} negativa(s) tolerada(s) (>= 8 valores) e média ${mediaGeral}.`
      : `Aprovado na 12ª classe com aproveitamento pleno e média ${mediaGeral}.`
  };
}
