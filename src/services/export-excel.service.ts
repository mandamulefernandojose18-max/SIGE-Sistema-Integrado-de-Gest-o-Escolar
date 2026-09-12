import * as XLSX from 'xlsx';

export class ExportExcelService {
  /**
   * Gera a Pauta Oficial da Turma em formato XLSX
   */
  static gerarPautaXlsx(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null };
    turma: { nome: string; grau_ano: string; ano_letivo: string };
    periodo: string;
    disciplinas: Array<{ id: string; nome: string; codigo: string }>;
    alunos: Array<{
      numero: number;
      matricula: string;
      nomeCompleto: string;
      genero: string;
      notas: Record<string, number>;
      mediaGeral: number;
      faltas: number;
      comportamento: string;
      resultado: string;
    }>;
  }): Buffer {
    const wb = XLSX.utils.book_new();

    // Cabeçalho Oficial de Moçambique
    const rows: any[][] = [
      ['REPÚBLICA DE MOÇAMBIQUE'],
      [`GOVERNO DA PROVÍNCIA DE ${dados.escola.provincia?.toUpperCase() || 'INHAMBANE'}`],
      [`DIRECÇÃO PROVINCIAL DE EDUCAÇÃO E CULTURA`],
      [dados.escola.nome.toUpperCase()],
      [`PAUTA OFICIAL DE APROVEITAMENTO PEDAGÓGICO - ANO LECTIVO ${dados.turma.ano_letivo}`],
      [`TURMA: ${dados.turma.nome} | CLASSE: ${dados.turma.grau_ano} | PERÍODO: ${dados.periodo.replace('_', ' ')}`],
      [] // Linha em branco
    ];

    // Cabeçalhos de Coluna
    const colunas = [
      'Nº',
      'Matrícula',
      'Nome Completo do Aluno',
      'Género',
      ...dados.disciplinas.map(d => d.codigo || d.nome),
      'Média Geral',
      'Faltas',
      'Comportamento',
      'Resultado'
    ];
    rows.push(colunas);

    // Linhas de Alunos
    dados.alunos.forEach(a => {
      const notasRow = dados.disciplinas.map(d => a.notas[d.codigo || d.id] ?? '-');
      rows.push([
        a.numero,
        a.matricula,
        a.nomeCompleto,
        a.genero,
        ...notasRow,
        a.mediaGeral,
        a.faltas,
        a.comportamento,
        a.resultado
      ]);
    });

    const ws = XLSX.utils.aoa_to_sheet(rows);

    // Definir larguras das colunas
    ws['!cols'] = [
      { wch: 5 },
      { wch: 15 },
      { wch: 35 },
      { wch: 8 },
      ...dados.disciplinas.map(() => ({ wch: 10 })),
      { wch: 12 },
      { wch: 8 },
      { wch: 14 },
      { wch: 12 }
    ];

    XLSX.utils.book_append_sheet(wb, ws, 'Pauta Oficial');
    return XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
  }

  /**
   * Gera a Caderneta do Professor em formato XLSX
   */
  static gerarCadernetaProfessorXlsx(dados: {
    escola: { nome: string };
    professor: { nome: string; especialidade: string };
    disciplina: { nome: string; codigo: string };
    turma: { nome: string; grau_ano: string; ano_letivo: string };
    periodo: string;
    alunos: Array<{
      numero: number;
      matricula: string;
      nome: string;
      teste1: number;
      teste2: number;
      teste3?: number;
      teste4?: number;
      trabalho: number;
      at: number;
      mediaFinal: number;
      faltas: number;
      anotacao?: string;
      comportamento: string;
      resultado: string;
    }>;
  }): Buffer {
    const wb = XLSX.utils.book_new();

    const rows: any[][] = [
      ['REPÚBLICA DE MOÇAMBIQUE'],
      [dados.escola.nome.toUpperCase()],
      ['CADERNETA OFICIAL DO PROFESSOR'],
      [`PROFESSOR: ${dados.professor.nome} (${dados.professor.especialidade})`],
      [`DISCIPLINA: ${dados.disciplina.nome} | TURMA: ${dados.turma.nome} | TRIMESTRE: ${dados.periodo.replace('_', ' ')} | ANO: ${dados.turma.ano_letivo}`],
      []
    ];

    rows.push([
      'Nº',
      'Matrícula',
      'Nome do Aluno',
      'Teste 1',
      'Teste 2',
      'Teste 3',
      'Teste 4',
      'Trabalho (ACS)',
      'Prova Trimestral (AT)',
      'Média Final',
      'Faltas',
      'Anotação',
      'Comportamento',
      'Resultado'
    ]);

    dados.alunos.forEach(a => {
      rows.push([
        a.numero,
        a.matricula,
        a.nome,
        a.teste1,
        a.teste2,
        a.teste3 ?? '-',
        a.teste4 ?? '-',
        a.trabalho,
        a.at,
        a.mediaFinal,
        a.faltas,
        a.anotacao || '-',
        a.comportamento,
        a.resultado
      ]);
    });

    const ws = XLSX.utils.aoa_to_sheet(rows);
    ws['!cols'] = [
      { wch: 5 },
      { wch: 14 },
      { wch: 32 },
      { wch: 8 },
      { wch: 8 },
      { wch: 8 },
      { wch: 8 },
      { wch: 14 },
      { wch: 20 },
      { wch: 12 },
      { wch: 8 },
      { wch: 10 },
      { wch: 14 },
      { wch: 12 }
    ];

    XLSX.utils.book_append_sheet(wb, ws, 'Caderneta');
    return XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
  }

  /**
   * Gera a Acta e Estatística de Aproveitamento Pedagógico em XLSX
   */
  static gerarActaEstatisticaXlsx(dados: {
    escola: { nome: string; provincia?: string | null };
    turma: { nome: string; grau_ano: string; ano_letivo: string };
    periodo: string;
    estatisticas: {
      inscritos: { total: number; m: number; f: number };
      avaliados: { total: number; m: number; f: number };
      aprovados: { total: number; m: number; f: number };
      reprovados: { total: number; m: number; f: number };
      percentualAproveitamento: number;
    };
  }): Buffer {
    const wb = XLSX.utils.book_new();

    const rows: any[][] = [
      ['REPÚBLICA DE MOÇAMBIQUE'],
      [`DIRECÇÃO PROVINCIAL DE EDUCAÇÃO DE ${dados.escola.provincia?.toUpperCase() || 'INHAMBANE'}`],
      [dados.escola.nome.toUpperCase()],
      [`ACTA E MAPA ESTATÍSTICO DE APROVEITAMENTO PEDAGÓGICO`],
      [`TURMA: ${dados.turma.nome} | ANO LECTIVO: ${dados.turma.ano_letivo} | PERÍODO: ${dados.periodo}`],
      [],
      ['INDICADOR', 'HOMENS (M)', 'MULHERES (F)', 'TOTAL GERAL'],
      ['Alunos Inscritos', dados.estatisticas.inscritos.m, dados.estatisticas.inscritos.f, dados.estatisticas.inscritos.total],
      ['Alunos Avaliados', dados.estatisticas.avaliados.m, dados.estatisticas.avaliados.f, dados.estatisticas.avaliados.total],
      ['Alunos Aprovados', dados.estatisticas.aprovados.m, dados.estatisticas.aprovados.f, dados.estatisticas.aprovados.total],
      ['Alunos Reprovados', dados.estatisticas.reprovados.m, dados.estatisticas.reprovados.f, dados.estatisticas.reprovados.total],
      ['Taxa de Aproveitamento (%)', '-', '-', `${dados.estatisticas.percentualAproveitamento}%`],
      []
    ];

    const ws = XLSX.utils.aoa_to_sheet(rows);
    ws['!cols'] = [{ wch: 30 }, { wch: 15 }, { wch: 15 }, { wch: 15 }];
    XLSX.utils.book_append_sheet(wb, ws, 'Acta Estatística');
    return XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
  }
}
