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

  // Média Trimestral = (MAC + AT) / 2 arredondado para inteiro (ex.: 18 valores)
  let mediaFinal = 0;
  if (at > 0 && testesValidos.length > 0) {
    mediaFinal = Math.round((mac + at) / 2);
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

  // Comportamento automático
  let comportamento: 'NS' | 'S' | 'B' | 'MB' | 'E' = 'NS';
  if (mediaFinal >= 17.5) comportamento = 'E'; // Excelente
  else if (mediaFinal >= 15.5) comportamento = 'MB'; // Muito Bom
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
  mediaGeral: number;
  totalNegativas: number;
  temNotaInferiorA8: boolean;
  is12aClasse: boolean;
  motivo?: string;
} {
  const grauNormalizado = (grauAno || '').toLowerCase();
  const is12aClasse = grauNormalizado.includes('12');

  if (notasDisciplinas.length === 0) {
    return {
      aprovado: false,
      resultado: 'Reprovado',
      mediaGeral: 0,
      totalNegativas: 0,
      temNotaInferiorA8: false,
      is12aClasse,
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

  const mediaGeral = Number((soma / notasDisciplinas.length).toFixed(1));

  // Regra para classes que NÃO são a 12ª classe:
  // "Excepto a 12a classe, o aluno só Aprova se tiver todas as disciplinas notas positivas sem negativa em alguma disciplina."
  if (!is12aClasse) {
    if (totalNegativas > 0) {
      return {
        aprovado: false,
        resultado: 'Reprovado',
        mediaGeral,
        totalNegativas,
        temNotaInferiorA8,
        is12aClasse,
        motivo: `Reprovado: possui ${totalNegativas} disciplina(s) com nota negativa (Excepto na 12ª classe, é exigido 100% de positivas sem negativa em alguma disciplina)`
      };
    }

    if (mediaGeral < 9.5) {
      return {
        aprovado: false,
        resultado: 'Reprovado',
        mediaGeral,
        totalNegativas,
        temNotaInferiorA8,
        is12aClasse,
        motivo: 'Reprovado: média geral inferior a 9.5 valores'
      };
    }

    return {
      aprovado: true,
      resultado: 'Aprovado',
      mediaGeral,
      totalNegativas: 0,
      temNotaInferiorA8: false,
      is12aClasse,
      motivo: 'Aprovado com aproveitamento positivo em todas as disciplinas'
    };
  }

  // Regra específica da 12ª classe:
  // Admite até 2 negativas desde que nenhuma seja inferior a 8 e média geral >= 9.5
  if (temNotaInferiorA8) {
    return {
      aprovado: false,
      resultado: 'Reprovado',
      mediaGeral,
      totalNegativas,
      temNotaInferiorA8: true,
      is12aClasse: true,
      motivo: 'Reprovado na 12ª classe: possui classificação negativa inferior a 8 valores'
    };
  }

  if (totalNegativas > 2) {
    return {
      aprovado: false,
      resultado: 'Reprovado',
      mediaGeral,
      totalNegativas,
      temNotaInferiorA8: false,
      is12aClasse: true,
      motivo: 'Reprovado na 12ª classe: possui mais de 2 classificações negativas'
    };
  }

  if (mediaGeral < 9.5) {
    return {
      aprovado: false,
      resultado: 'Reprovado',
      mediaGeral,
      totalNegativas,
      temNotaInferiorA8: false,
      is12aClasse: true,
      motivo: 'Reprovado na 12ª classe: média geral inferior a 9.5 valores'
    };
  }

  return {
    aprovado: true,
    resultado: 'Aprovado',
    mediaGeral,
    totalNegativas,
    temNotaInferiorA8: false,
    is12aClasse: true,
    motivo: totalNegativas > 0
      ? `Aprovado na 12ª classe com ${totalNegativas} negativa(s) tolerada(s) (>= 8 valores)`
      : 'Aprovado na 12ª classe com aproveitamento pleno'
  };
}
