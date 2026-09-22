import * as XLSX from 'xlsx';

export class SheetJsDocumentosService {
  /**
   * Gera Pauta Escolar em XLSX usando SheetJS
   */
  static gerarPautaXlsx(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null; codigo_escola?: string | null };
    turma: { nome: string; grau_ano: string; ano_letivo: string; turno?: string; director_turma?: string };
    disciplinas: Array<{ id: string; nome: string; codigo: string }>;
    alunos: Array<{
      numero: number;
      matricula: string;
      nome: string;
      genero: string;
      notasDisciplinas: Record<string, { t1?: number | null; t2?: number | null; t3?: number | null; mfd?: number | null }>;
      mediasTrimestrais: { t1?: number | null; t2?: number | null; t3?: number | null };
      mediaFinalGeral: number;
      resultadoFinal: string;
    }>;
  }): Buffer {
    const wb = XLSX.utils.book_new();

    const linhas: any[][] = [
      ['REPÚBLICA DE MOÇAMBIQUE'],
      [`GOVERNO DA PROVÍNCIA DE ${(dados.escola.provincia || 'Maputo').toUpperCase()}`],
      [`SERVIÇO DISTRITAL DE EDUCAÇÃO, JUVENTUDE E TECNOLOGIA DE ${(dados.escola.distrito || 'Cidade de Maputo').toUpperCase()}`],
      [(dados.escola.nome || 'Escola Secundária').toUpperCase()],
      [`PAUTA OFICIAL DE AVALIAÇÃO — ${dados.turma.grau_ano} ${dados.turma.nome} — ANO LECTIVO ${dados.turma.ano_letivo}`],
      [`Director de Turma: ${dados.turma.director_turma || 'Não atribuído'} | Turno: ${dados.turma.turno || 'Diurno'}`],
      [] // Linha em branco
    ];

    // Cabeçalho da tabela de alunos
    const header = ['Nº', 'Matrícula', 'Nome Completo', 'Sexo'];
    dados.disciplinas.forEach(d => {
      header.push(`${d.codigo || d.nome} (T1)`);
      header.push(`${d.codigo || d.nome} (T2)`);
      header.push(`${d.codigo || d.nome} (T3)`);
      header.push(`${d.codigo || d.nome} (MFD)`);
    });
    header.push('Média T1', 'Média T2', 'Média T3', 'Média Final', 'Resultado');
    linhas.push(header);

    // Linhas de alunos
    dados.alunos.forEach(a => {
      const row: any[] = [
        a.numero,
        a.matricula,
        a.nome.toUpperCase(),
        a.genero || 'M'
      ];

      dados.disciplinas.forEach(d => {
        const nd = a.notasDisciplinas[d.codigo || d.id] || a.notasDisciplinas[d.id] || {};
        row.push(nd.t1 ?? '');
        row.push(nd.t2 ?? '');
        row.push(nd.t3 ?? '');
        row.push(nd.mfd ?? '');
      });

      row.push(a.mediasTrimestrais.t1 ?? '');
      row.push(a.mediasTrimestrais.t2 ?? '');
      row.push(a.mediasTrimestrais.t3 ?? '');
      row.push(a.mediaFinalGeral > 0 ? a.mediaFinalGeral : '');
      row.push(a.resultadoFinal === 'A' ? 'Aprovado' : (a.resultadoFinal === 'R' ? 'Reprovado' : a.resultadoFinal));

      linhas.push(row);
    });

    const ws = XLSX.utils.aoa_to_sheet(linhas);

    // Definir larguras de colunas
    ws['!cols'] = [
      { wch: 5 },
      { wch: 14 },
      { wch: 35 },
      { wch: 8 }
    ];

    XLSX.utils.book_append_sheet(wb, ws, 'Pauta Oficial');
    return XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
  }

  /**
   * Gera Acta e Mapa Estatístico em XLSX com trimestres condicionados
   */
  static gerarActaXlsx(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null };
    turma: { nome: string; grau_ano: string; ano_letivo: string; director_turma?: string };
    conselho: {
      data?: string;
      prazo?: string;
      director_turma?: string;
    };
    trimestresComNotas: { t1: boolean; t2: boolean; t3: boolean; fimAno: boolean };
    estatisticaEfectivo?: any;
    estatisticaAproveitamento?: any;
    disciplinas?: any[];
  }): Buffer {
    const wb = XLSX.utils.book_new();

    const linhas: any[][] = [
      ['REPÚBLICA DE MOÇAMBIQUE'],
      [(dados.escola.nome || 'Escola Secundária').toUpperCase()],
      [`ACTA DA SESSÃO DO CONSELHO DE AVALIAÇÃO — ${dados.turma.grau_ano} ${dados.turma.nome}`],
      [`Data: ${dados.conselho.data || 'A definir'} | Prazo: ${dados.conselho.prazo || 'Sem prazo fixado'} | Director: ${dados.conselho.director_turma || dados.turma.director_turma || 'Não especificado'}`],
      []
    ];

    // Condicionamento Trimestral: só preenche o trimestre que tiver notas
    const { t1, t2, t3 } = dados.trimestresComNotas;

    if (t1 && dados.estatisticaAproveitamento?.t1) {
      linhas.push(['1. APROVEITAMENTO PEDAGÓGICO — 1º TRIMESTRE']);
      linhas.push(['Indicador', 'Homens (H)', 'Mulheres (M)', 'Total (HM)', '% Total']);
      const apr = dados.estatisticaAproveitamento.t1;
      linhas.push(['Aprovados', apr.aprovados?.h || 0, apr.aprovados?.m || 0, apr.aprovados?.hm || 0, `${apr.aprovados?.pct || 0}%`]);
      linhas.push(['Reprovados', apr.reprovados?.h || 0, apr.reprovados?.m || 0, apr.reprovados?.hm || 0, `${apr.reprovados?.pct || 0}%`]);
      linhas.push([]);
    }

    if (t2 && dados.estatisticaAproveitamento?.t2) {
      linhas.push(['2. APROVEITAMENTO PEDAGÓGICO — 2º TRIMESTRE']);
      linhas.push(['Indicador', 'Homens (H)', 'Mulheres (M)', 'Total (HM)', '% Total']);
      const apr = dados.estatisticaAproveitamento.t2;
      linhas.push(['Aprovados', apr.aprovados?.h || 0, apr.aprovados?.m || 0, apr.aprovados?.hm || 0, `${apr.aprovados?.pct || 0}%`]);
      linhas.push(['Reprovados', apr.reprovados?.h || 0, apr.reprovados?.m || 0, apr.reprovados?.hm || 0, `${apr.reprovados?.pct || 0}%`]);
      linhas.push([]);
    }

    if (t3 && dados.estatisticaAproveitamento?.t3) {
      linhas.push(['3. APROVEITAMENTO PEDAGÓGICO — 3º TRIMESTRE']);
      linhas.push(['Indicador', 'Homens (H)', 'Mulheres (M)', 'Total (HM)', '% Total']);
      const apr = dados.estatisticaAproveitamento.t3;
      linhas.push(['Aprovados', apr.aprovados?.h || 0, apr.aprovados?.m || 0, apr.aprovados?.hm || 0, `${apr.aprovados?.pct || 0}%`]);
      linhas.push(['Reprovados', apr.reprovados?.h || 0, apr.reprovados?.m || 0, apr.reprovados?.hm || 0, `${apr.reprovados?.pct || 0}%`]);
      linhas.push([]);
    }

    if (!t1 && !t2 && !t3) {
      linhas.push(['Sem notas trimestrais lançadas nesta turma até ao presente momento.']);
    }

    const ws = XLSX.utils.aoa_to_sheet(linhas);
    XLSX.utils.book_append_sheet(wb, ws, 'Acta do Conselho');
    return XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
  }

  /**
   * Gera Boletim Escolar em XLSX
   */
  static gerarBoletimXlsx(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null };
    aluno: { nome: string; matricula?: string | null; turma?: { nome: string; grau_ano: string } | null };
    anoLetivo: string;
    disciplinas: Array<{ nome: string; t1?: number | null; t2?: number | null; t3?: number | null; mfd?: number | null }>;
    medias: { t1?: number | null; t2?: number | null; t3?: number | null; mfd?: number | null };
    resultadoFinal?: string;
  }): Buffer {
    const wb = XLSX.utils.book_new();

    const linhas: any[][] = [
      ['REPÚBLICA DE MOÇAMBIQUE'],
      [(dados.escola.nome || 'Escola Secundária').toUpperCase()],
      [`BOLETIM ESCOLAR — ANO LECTIVO ${dados.anoLetivo}`],
      [`Aluno: ${dados.aluno.nome.toUpperCase()} | Nº Matrícula: ${dados.aluno.matricula || '---'}`],
      [`Turma: ${dados.aluno.turma?.grau_ano || ''} ${dados.aluno.turma?.nome || ''}`],
      [],
      ['Disciplina', '1º Trimestre', '2º Trimestre', '3º Trimestre', 'Média Final', 'Situação']
    ];

    dados.disciplinas.forEach(d => {
      linhas.push([
        d.nome,
        d.t1 ?? '',
        d.t2 ?? '',
        d.t3 ?? '',
        d.mfd ?? '',
        d.mfd && d.mfd >= 9.5 ? 'Aprovado' : (d.mfd ? 'Reprovado' : '')
      ]);
    });

    linhas.push([
      'MÉDIA GLOBAL',
      dados.medias.t1 ?? '',
      dados.medias.t2 ?? '',
      dados.medias.t3 ?? '',
      dados.medias.mfd ?? '',
      dados.resultadoFinal || ''
    ]);

    const ws = XLSX.utils.aoa_to_sheet(linhas);
    XLSX.utils.book_append_sheet(wb, ws, 'Boletim');
    return XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
  }

  /**
   * Gera Resumo Estatístico Geral da Escola/Classe em XLSX
   */
  static gerarEstatisticasXlsx(dados: {
    escola: { nome: string };
    anoLetivo: string;
    turmas: Array<{
      turmaNome: string;
      classe: string;
      totalAlunos: number;
      aprovados: number;
      reprovados: number;
      taxaAprovacao: number;
    }>;
  }): Buffer {
    const wb = XLSX.utils.book_new();

    const linhas: any[][] = [
      ['REPÚBLICA DE MOÇAMBIQUE'],
      [(dados.escola.nome || 'Escola').toUpperCase()],
      [`ESTATÍSTICAS GERAIS DE APROVEITAMENTO — ${dados.anoLetivo}`],
      [],
      ['Classe', 'Turma', 'Total Alunos', 'Aprovados', 'Reprovados', 'Taxa de Aprovação (%)']
    ];

    dados.turmas.forEach(t => {
      linhas.push([
        t.classe,
        t.turmaNome,
        t.totalAlunos,
        t.aprovados,
        t.reprovados,
        `${t.taxaAprovacao}%`
      ]);
    });

    const ws = XLSX.utils.aoa_to_sheet(linhas);
    XLSX.utils.book_append_sheet(wb, ws, 'Estatísticas Gerais');
    return XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
  }
}
