import {
  calcularMediaTrimestral,
  avaliarAprovacaoPauta
} from '../src/utils/avaliacoes-mocambique';
import {
  PROVINCIAS_MOCAMBIQUE,
  DISTRITOS_POR_PROVINCIA,
  CARREIRAS_DOCENTES,
  ANOTACOES_STATUS,
  COMPORTAMENTOS
} from '../src/utils/geografia-mocambique';

describe('4. Regras Oficiais de Avaliação e Geografia de Moçambique (MINEDH)', () => {
  describe('Geografia e Carreiras de Moçambique', () => {
    it('Deve conter as 11 províncias de Moçambique', () => {
      expect(PROVINCIAS_MOCAMBIQUE).toHaveLength(11);
      expect(PROVINCIAS_MOCAMBIQUE).toContain('Cidade de Maputo');
      expect(PROVINCIAS_MOCAMBIQUE).toContain('Província de Maputo');
      expect(PROVINCIAS_MOCAMBIQUE).toContain('Gaza');
      expect(PROVINCIAS_MOCAMBIQUE).toContain('Inhambane');
      expect(PROVINCIAS_MOCAMBIQUE).toContain('Sofala');
      expect(PROVINCIAS_MOCAMBIQUE).toContain('Manica');
      expect(PROVINCIAS_MOCAMBIQUE).toContain('Tete');
      expect(PROVINCIAS_MOCAMBIQUE).toContain('Zambézia');
      expect(PROVINCIAS_MOCAMBIQUE).toContain('Nampula');
      expect(PROVINCIAS_MOCAMBIQUE).toContain('Niassa');
      expect(PROVINCIAS_MOCAMBIQUE).toContain('Cabo Delgado');
    });

    it('Deve mapear distritos para todas as 11 províncias', () => {
      PROVINCIAS_MOCAMBIQUE.forEach(prov => {
        expect(DISTRITOS_POR_PROVINCIA[prov]).toBeDefined();
        expect(DISTRITOS_POR_PROVINCIA[prov].length).toBeGreaterThan(0);
      });
    });

    it('Deve conter Carreiras Docentes do MINEDH (DN4 até Professor Doutor)', () => {
      expect(CARREIRAS_DOCENTES).toContain('DN4');
      expect(CARREIRAS_DOCENTES).toContain('DN1');
      expect(CARREIRAS_DOCENTES).toContain('Mestre');
      expect(CARREIRAS_DOCENTES).toContain('Professor Doutor');
    });

    it('Deve conter as anotações especiais oficiais (D, T, VT, F, AM, PPF, PDF)', () => {
      const codigos = Object.keys(ANOTACOES_STATUS);
      expect(codigos).toContain('D');
      expect(codigos).toContain('T');
      expect(codigos).toContain('VT');
      expect(codigos).toContain('F');
      expect(codigos).toContain('AM');
      expect(codigos).toContain('PPF');
      expect(codigos).toContain('PDF');
    });

    it('Deve conter a escala de comportamentos (NS, S, B, MB, E)', () => {
      const siglas = COMPORTAMENTOS.map(c => c.codigo);
      expect(siglas).toEqual(['NS', 'S', 'B', 'MB', 'E']);
    });
  });

  describe('Cálculo de 6 Avaliações e Arredondamento Inteiro (0-20)', () => {
    it('Deve calcular a média trimestral com pesos oficiais e arredondar a inteiro', () => {
      // T1=12, T2=14, Trabalho=15, AT=13
      // MAC = (12+14+15)/3 = 13.67
      // Média = Math.round((13.67 + 13) / 2) = Math.round(13.33) = 13
      const res = calcularMediaTrimestral({
        teste1: 12,
        teste2: 14,
        trabalho: 15,
        avaliacao_trimestral: 13
      });

      expect(res.mediaFinal).toBe(13);
      expect(res.resultado).toBe('Aprovado');
      expect(res.cor).toBe('preto');
    });

    it('Deve classificar notas >= 9.5 como Aprovado (preto) e < 9.5 como Reprovado (vermelho)', () => {
      const aprovado = calcularMediaTrimestral({
        teste1: 10,
        teste2: 10,
        trabalho: 10,
        avaliacao_trimestral: 10
      });
      expect(aprovado.mediaFinal).toBe(10);
      expect(aprovado.resultado).toBe('Aprovado');
      expect(aprovado.cor).toBe('preto');

      const reprovado = calcularMediaTrimestral({
        teste1: 8,
        teste2: 8,
        trabalho: 8,
        avaliacao_trimestral: 8
      });
      expect(reprovado.mediaFinal).toBe(8);
      expect(reprovado.resultado).toBe('Reprovado');
      expect(reprovado.cor).toBe('vermelho');
    });
  });

  describe('Critérios de Aprovação Oficiais de Moçambique', () => {
    it('Regra Geral (Excepto 12ª classe): O aluno SÓ APROVA se tiver 100% de positivas (0 negativas)', () => {
      // Aluno da 10ª Classe com todas as notas positivas
      const alunoAprovado = avaliarAprovacaoPauta([
        { disciplina: 'Matemática', notaFinal: 14 },
        { disciplina: 'Português', notaFinal: 12 },
        { disciplina: 'Física', notaFinal: 10 },
        { disciplina: 'Química', notaFinal: 11 }
      ], '10ª Classe');
      expect(alunoAprovado.resultado).toBe('Aprovado');
      expect(alunoAprovado.aprovado).toBe(true);
      expect(alunoAprovado.totalNegativas).toBe(0);

      // Aluno da 10ª Classe com 1 negativa -> DEVE SER REPROVADO
      const alunoComUmaNegativa = avaliarAprovacaoPauta([
        { disciplina: 'Matemática', notaFinal: 8 },
        { disciplina: 'Português', notaFinal: 16 },
        { disciplina: 'Física', notaFinal: 15 },
        { disciplina: 'Química', notaFinal: 14 }
      ], '10ª Classe');
      expect(alunoComUmaNegativa.resultado).toBe('Reprovado');
      expect(alunoComUmaNegativa.aprovado).toBe(false);
      expect(alunoComUmaNegativa.totalNegativas).toBe(1);
      expect(alunoComUmaNegativa.motivo).toContain('Excepto na 12ª classe');
    });

    it('Regra da 12ª Classe: Aprova com média geral >= 9.5, máx 2 negativas e NENHUMA < 8', () => {
      // 12ª Classe com 2 negativas de 9 e 8 e média geral >= 9.5 -> APROVADO
      const aluno12Aprovado = avaliarAprovacaoPauta([
        { disciplina: 'Matemática', notaFinal: 8 },
        { disciplina: 'Física', notaFinal: 9 },
        { disciplina: 'Português', notaFinal: 14 },
        { disciplina: 'Química', notaFinal: 15 },
        { disciplina: 'Biologia', notaFinal: 12 }
      ], '12ª Classe');
      expect(aluno12Aprovado.resultado).toBe('Aprovado');
      expect(aluno12Aprovado.aprovado).toBe(true);
      expect(aluno12Aprovado.totalNegativas).toBe(2);

      // 12ª Classe com 1 negativa < 8 (ex: nota 7) -> REPROVADO
      const aluno12ComNotaBaixa = avaliarAprovacaoPauta([
        { disciplina: 'Matemática', notaFinal: 7 }, // < 8
        { disciplina: 'Física', notaFinal: 16 },
        { disciplina: 'Português', notaFinal: 14 },
        { disciplina: 'Química', notaFinal: 15 }
      ], '12ª Classe');
      expect(aluno12ComNotaBaixa.resultado).toBe('Reprovado');
      expect(aluno12ComNotaBaixa.aprovado).toBe(false);
      expect(aluno12ComNotaBaixa.temNotaInferiorA8).toBe(true);
      expect(aluno12ComNotaBaixa.motivo).toContain('inferior a 8 valores');

      // 12ª Classe com 3 negativas -> REPROVADO (máximo permitido é 2)
      const aluno12Com3Negativas = avaliarAprovacaoPauta([
        { disciplina: 'Matemática', notaFinal: 9 },
        { disciplina: 'Física', notaFinal: 8 },
        { disciplina: 'Química', notaFinal: 9 },
        { disciplina: 'Português', notaFinal: 16 },
        { disciplina: 'Biologia', notaFinal: 15 }
      ], '12ª Classe');
      expect(aluno12Com3Negativas.resultado).toBe('Reprovado');
      expect(aluno12Com3Negativas.aprovado).toBe(false);
      expect(aluno12Com3Negativas.totalNegativas).toBe(3);
    });
  });
});
