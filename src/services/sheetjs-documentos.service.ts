import * as XLSX from 'xlsx';

export class SheetJsDocumentosService {
  /**
   * Gera Pauta Escolar em XLSX usando SheetJS
   */
  /**
   * Gera Pauta Oficial de Aproveitamento Pedagógico em XLSX usando SheetJS
   * Estrutura hierárquica idêntica à pauta oficial (imagem de referência):
   * - Cabeçalho oficial do Ministério e da Escola
   * - Nível 1: Apelido, Gén, Disciplinas (mescladas em 4 colunas), Médias Trimestrais (3 colunas),
   *   Disciplinas Negativas (4 colunas), Média Geral e Resultado
   * - Nível 2: 1º, 2º, 3º, MFD; 1º, 2º, 3º; 1º, 2º, 3º, Total
   * - Células mescladas com !merges e larguras de coluna ajustadas
   */
  static gerarPautaXlsx(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null; codigo_escola?: string | null };
    turma: { id?: string; nome: string; grau_ano: string; ano_letivo: string; turno?: string; director_turma?: string };
    disciplinas: Array<{ id: string; nome: string; codigo: string }>;
    alunos: Array<{
      numero?: number;
      matricula?: string;
      nome: string;
      apelido?: string;
      nomeCompleto?: string;
      genero?: string;
      notasDisciplinas?: Record<string, { t1?: number | null; t2?: number | null; t3?: number | null; mfd?: number | null }>;
      mediasTrimestrais?: { t1?: number | null; t2?: number | null; t3?: number | null };
      negativas?: { t1?: number; t2?: number; t3?: number; fimDoAno?: number };
      mediaFinalGeral?: number;
      resultadoFinal?: string;
    }>;
  }): Buffer {
    const wb = XLSX.utils.book_new();

    const prov = (dados.escola.provincia || 'Inhambane').toUpperCase();
    const dist = (dados.escola.distrito || 'Morrumbene').toUpperCase();
    const nomeEscola = (dados.escola.nome || 'Escola Secundária de Cambine').toUpperCase();
    const anoLetivo = dados.turma.ano_letivo || '2026';
    const turno = (dados.turma.turno || 'MANHA').toUpperCase();
    const dtNome = dados.turma.director_turma || 'Manuel';

    const linhas: any[][] = [
      ['REPÚBLICA DE MOÇAMBIQUE'],
      [`GOVERNO DA PROVÍNCIA DE ${prov} | DISTRITO DE ${dist}`],
      [nomeEscola],
      [`PAUTA OFICIAL DE APROVEITAMENTO PEDAGÓGICO — ANO LECTIVO ${anoLetivo}`],
      [`Turma: ${dados.turma.grau_ano} ${dados.turma.nome} | Classe: ${dados.turma.grau_ano} | Turno: ${turno} | Director de Turma: ${dtNome}`],
      [], // Linha em branco separadora (Espaçamento de 2 cm)
      []  // Linha em branco separadora (Espaçamento de 2 cm)
    ];

    // Nível 1 do Cabeçalho da Tabela
    const headerRow1: any[] = ['Nome Completo do Aluno', 'Gén'];
    dados.disciplinas.forEach(d => {
      const cod = (d.codigo || d.nome || '').substring(0, 6).toUpperCase();
      headerRow1.push(cod, '', '', '');
    });
    headerRow1.push('Médias Trimestrais', '', '');
    headerRow1.push('Disciplinas Negativas', '', '', '');
    headerRow1.push('Média Geral');
    headerRow1.push('Resultado');
    linhas.push(headerRow1);

    // Nível 2 do Cabeçalho da Tabela
    const headerRow2: any[] = ['', ''];
    dados.disciplinas.forEach(() => {
      headerRow2.push('1º', '2º', '3º', 'MFD');
    });
    headerRow2.push('1º', '2º', '3º');
    headerRow2.push('1º', '2º', '3º', 'Total');
    headerRow2.push('');
    headerRow2.push('');
    linhas.push(headerRow2);

    // Linhas de dados dos alunos
    dados.alunos.forEach(a => {
      const nomeCompleto = (a.nomeCompleto || a.nome || '').toUpperCase();
      const gen = (a.genero || 'M').toUpperCase().startsWith('F') ? 'F' : 'M';

      const row: any[] = [nomeCompleto, gen];

      let countNeg1 = 0, countNeg2 = 0, countNeg3 = 0, countNegTotal = 0;

      dados.disciplinas.forEach(d => {
        const nd = a.notasDisciplinas?.[d.codigo] || a.notasDisciplinas?.[d.id] || {};
        const v1 = nd.t1 !== null && nd.t1 !== undefined && nd.t1 > 0 ? nd.t1 : '-';
        const v2 = nd.t2 !== null && nd.t2 !== undefined && nd.t2 > 0 ? nd.t2 : '-';
        const v3 = nd.t3 !== null && nd.t3 !== undefined && nd.t3 > 0 ? nd.t3 : '-';
        const temVal = (typeof v1 === 'number') || (typeof v2 === 'number') || (typeof v3 === 'number');
        const calcMfd = temVal ? Math.round(((typeof v1 === 'number' ? v1 : 0) + (typeof v2 === 'number' ? v2 : 0) + (typeof v3 === 'number' ? v3 : 0)) / 3) : '-';
        const mfd = nd.mfd !== null && nd.mfd !== undefined && nd.mfd > 0 ? nd.mfd : calcMfd;

        if (typeof v1 === 'number' && v1 < 9.5) countNeg1++;
        if (typeof v2 === 'number' && v2 < 9.5) countNeg2++;
        if (typeof v3 === 'number' && v3 < 9.5) countNeg3++;
        if (typeof mfd === 'number' && mfd < 9.5) countNegTotal++;

        row.push(v1, v2, v3, mfd);
      });

      // Médias Trimestrais
      const m1 = a.mediasTrimestrais?.t1 !== null && a.mediasTrimestrais?.t1 !== undefined && a.mediasTrimestrais.t1 > 0 ? a.mediasTrimestrais.t1 : '-';
      const m2 = a.mediasTrimestrais?.t2 !== null && a.mediasTrimestrais?.t2 !== undefined && a.mediasTrimestrais.t2 > 0 ? a.mediasTrimestrais.t2 : '-';
      const m3 = a.mediasTrimestrais?.t3 !== null && a.mediasTrimestrais?.t3 !== undefined && a.mediasTrimestrais.t3 > 0 ? a.mediasTrimestrais.t3 : '-';
      row.push(m1, m2, m3);

      // Disciplinas Negativas
      const negT1 = a.negativas?.t1 !== undefined ? a.negativas.t1 : countNeg1;
      const negT2 = a.negativas?.t2 !== undefined ? a.negativas.t2 : countNeg2;
      const negT3 = a.negativas?.t3 !== undefined ? a.negativas.t3 : countNeg3;
      const negTot = a.negativas?.fimDoAno !== undefined ? a.negativas.fimDoAno : (countNegTotal || (negT1 + negT2 + negT3));
      row.push(negT1, negT2, negT3, negTot);

      // Média Geral
      const medGeral = a.mediaFinalGeral && a.mediaFinalGeral > 0 ? a.mediaFinalGeral : '-';
      row.push(medGeral);

      // Resultado
      const resVal = a.resultadoFinal === 'A' || a.resultadoFinal === 'Aprovado' ? 'Aprovado' : (a.resultadoFinal === 'R' || a.resultadoFinal === 'Reprovado' ? 'Reprovado' : (a.resultadoFinal || 'Aprovado'));
      row.push(resVal);

      linhas.push(row);
    });

    const ws = XLSX.utils.aoa_to_sheet(linhas);

    // Configuração de Mesclagens (!merges)
    const totalCols = headerRow1.length;
    const rH1 = linhas.indexOf(headerRow1);
    const rH2 = rH1 + 1;
    const merges: XLSX.Range[] = [
      // Cabeçalhos superiores centralizados sobre todas as colunas
      { s: { r: 0, c: 0 }, e: { r: 0, c: totalCols - 1 } },
      { s: { r: 1, c: 0 }, e: { r: 1, c: totalCols - 1 } },
      { s: { r: 2, c: 0 }, e: { r: 2, c: totalCols - 1 } },
      { s: { r: 3, c: 0 }, e: { r: 3, c: totalCols - 1 } },
      { s: { r: 4, c: 0 }, e: { r: 4, c: totalCols - 1 } },

      // Nome Completo do Aluno (linhas do cabeçalho)
      { s: { r: rH1, c: 0 }, e: { r: rH2, c: 0 } },
      // Gén (linhas do cabeçalho)
      { s: { r: rH1, c: 1 }, e: { r: rH2, c: 1 } }
    ];

    let colCur = 2;
    // Disciplinas: mesclar cada disciplina sobre as 4 subcolunas
    dados.disciplinas.forEach(() => {
      merges.push({ s: { r: rH1, c: colCur }, e: { r: rH1, c: colCur + 3 } });
      colCur += 4;
    });

    // Médias Trimestrais: mesclar sobre as 3 subcolunas
    merges.push({ s: { r: rH1, c: colCur }, e: { r: rH1, c: colCur + 2 } });
    colCur += 3;

    // Disciplinas Negativas: mesclar sobre as 4 subcolunas
    merges.push({ s: { r: rH1, c: colCur }, e: { r: rH1, c: colCur + 3 } });
    colCur += 4;

    // Média Geral (linhas do cabeçalho)
    merges.push({ s: { r: rH1, c: colCur }, e: { r: rH2, c: colCur } });
    colCur += 1;

    // Resultado (linhas do cabeçalho)
    merges.push({ s: { r: rH1, c: colCur }, e: { r: rH2, c: colCur } });

    ws['!merges'] = merges;

    // Configuração de Larguras de Colunas (!cols)
    const cols: XLSX.ColInfo[] = [
      { wch: 32 }, // Nome Completo do Aluno
      { wch: 6 }   // Gén
    ];

    // Subcolunas de disciplinas
    dados.disciplinas.forEach(() => {
      cols.push({ wch: 6 }, { wch: 6 }, { wch: 6 }, { wch: 7 });
    });

    // Subcolunas de Médias Trimestrais
    cols.push({ wch: 6 }, { wch: 6 }, { wch: 6 });

    // Subcolunas de Disciplinas Negativas
    cols.push({ wch: 6 }, { wch: 6 }, { wch: 6 }, { wch: 7 });

    // Média Geral e Resultado
    cols.push({ wch: 12 }, { wch: 14 });

    ws['!cols'] = cols;

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
      [`BOLETIM DE APROVEITAMENTO ESCOLAR — ANO LECTIVO ${dados.anoLetivo}`],
      [],
      [], // Espaçamento de 2 cm
      [`Nome do Aluno: ${dados.aluno.nome.toUpperCase()} | Classe / Turma: ${dados.aluno.turma?.grau_ano || ''} - ${dados.aluno.turma?.nome || ''}`],
      [`Nº Matrícula: ${dados.aluno.matricula || '---'} | Turno: Manhã`],
      [],
      ['DISCIPLINA', '1º TRIM', '2º TRIM', '3º TRIM', 'MÉD. ANUAL', 'SITUAÇÃO']
    ];

    const fmtNota = (v?: number | null) => (v !== null && v !== undefined && v > 0) ? v : '---';

    dados.disciplinas.forEach(d => {
      const mfdVal = d.mfd !== null && d.mfd !== undefined && d.mfd > 0 ? d.mfd : '---';
      const sit = mfdVal !== '---' && Number(mfdVal) >= 9.5 ? 'Aprovado' : (mfdVal !== '---' ? 'Reprovado' : '---');
      linhas.push([
        d.nome,
        fmtNota(d.t1),
        fmtNota(d.t2),
        fmtNota(d.t3),
        mfdVal,
        sit
      ]);
    });

    linhas.push([
      'MÉDIA GLOBAL DO PERÍODO',
      '---',
      '---',
      '---',
      dados.medias.mfd ?? '---',
      dados.resultadoFinal || (dados.medias.mfd && dados.medias.mfd >= 9.5 ? 'Aprovado' : 'Em Avaliação')
    ]);

    linhas.push([]);
    linhas.push([`Decisão do Conselho: Resultado pedagógico do aluno: ${dados.resultadoFinal || 'Aprovado'} com média global de ${dados.medias.mfd || '---'} valores.`]);

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

  /**
   * Gera Certificado Oficial de Habilitações em XLSX usando SheetJS
   */
  static gerarCertificadoXlsx(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null };
    aluno: {
      nome: string;
      apelido?: string | null;
      nomeCompleto?: string;
      matricula?: string | null;
      genero?: string | null;
      data_nascimento?: Date | string | null;
      pai?: string | null;
      mae?: string | null;
      distrito?: string | null;
      provincia?: string | null;
      turma?: { nome?: string; grau_ano?: string; area?: string | null } | null;
    };
    grauAno?: string;
    anoLectivo?: string;
    directorNome?: string;
    chefeSecretariaNome?: string;
    mediaGlobal?: number;
    resultadoOficial?: string;
    pautaNumero?: string;
    termoExames?: string;
    codigoAutenticidade?: string;
    disciplinas?: Array<{ disciplina: string; notaFinal?: number | null; mediaFinal?: number | null }>;
  }): Buffer {
    const wb = XLSX.utils.book_new();

    const escolaNome = (dados.escola.nome || 'Escola Secundária').toUpperCase();
    const alunoNome = (dados.aluno.nomeCompleto || `${dados.aluno.nome} ${dados.aluno.apelido || ''}`).trim().toUpperCase();

    const linhas: any[][] = [
      ['REPÚBLICA DE MOÇAMBIQUE'],
      ['MINISTÉRIO DA EDUCAÇÃO E CULTURA'],
      ['INSTITUTO NACIONAL DE EXAMES, CERTIFICAÇÃO E EQUIVALÊNCIA'],
      [escolaNome],
      ['CERTIFICADO DE HABILITAÇÕES'],
      [],
      ['Aluno(a):', alunoNome, 'Nº Matrícula:', dados.aluno.matricula || '-'],
      ['Sexo:', dados.aluno.genero === 'F' ? 'Feminino' : 'Masculino', 'Classe / Grau:', dados.grauAno || '12ª Classe'],
      ['Filiação:', `${dados.aluno.pai || '-'} e ${dados.aluno.mae || '-'}`, 'Ano Lectivo:', dados.anoLectivo || '2026'],
      [],
      ['Disciplina Curricular', 'Classificação Final (Valores)', 'Situação']
    ];

    (dados.disciplinas || []).forEach(d => {
      const nota = d.notaFinal !== undefined && d.notaFinal !== null ? d.notaFinal : (d.mediaFinal !== undefined ? d.mediaFinal : '');
      const sit = typeof nota === 'number' ? (nota >= 9.5 ? 'Aprovado' : 'Reprovado') : '';
      linhas.push([d.disciplina, nota, sit]);
    });

    const media = Math.round(Number(dados.mediaGlobal || 14));
    linhas.push([]);
    linhas.push(['MÉDIA GLOBAL:', media, dados.resultadoOficial || 'APROVADO']);
    linhas.push(['Código de Autenticidade:', dados.codigoAutenticidade || '']);
    linhas.push([]);
    linhas.push(['O Chefe da Secretaria:', dados.chefeSecretariaNome || 'Secretaria', 'O Director da Escola:', dados.directorNome || 'Director']);

    const ws = XLSX.utils.aoa_to_sheet(linhas);
    ws['!cols'] = [{ wch: 35 }, { wch: 25 }, { wch: 20 }, { wch: 20 }];
    XLSX.utils.book_append_sheet(wb, ws, 'Certificado');
    return XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
  }

  /**
   * Gera Declaração Escolar com Notas em XLSX usando SheetJS
   */
  static gerarDeclaracaoXlsx(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null };
    aluno: {
      nome: string;
      apelido?: string | null;
      nomeCompleto?: string;
      matricula?: string | null;
      turma?: { nome?: string; grau_ano?: string } | null;
    };
    anoLectivo?: string;
    directorNome?: string;
    mediaGlobal?: number;
    resultadoOficial?: string;
    disciplinas?: Array<{ disciplina: string; notaFinal?: number | null }>;
  }): Buffer {
    const wb = XLSX.utils.book_new();

    const escolaNome = (dados.escola.nome || 'Escola Secundária').toUpperCase();
    const alunoNome = (dados.aluno.nomeCompleto || `${dados.aluno.nome} ${dados.aluno.apelido || ''}`).trim().toUpperCase();

    const linhas: any[][] = [
      ['REPÚBLICA DE MOÇAMBIQUE'],
      [`GOVERNO DA PROVÍNCIA DE ${(dados.escola.provincia || 'Maputo').toUpperCase()}`],
      [escolaNome],
      ['DECLARAÇÃO OFICIAL COM NOTAS'],
      [],
      ['Aluno(a):', alunoNome, 'Nº Matrícula:', dados.aluno.matricula || '-'],
      ['Turma:', dados.aluno.turma?.nome || '-', 'Ano Lectivo:', dados.anoLectivo || '2026'],
      [],
      ['Disciplina Curricular', 'Classificação Final (Valores)', 'Situação']
    ];

    (dados.disciplinas || []).forEach(d => {
      const nota = d.notaFinal !== undefined && d.notaFinal !== null ? d.notaFinal : '';
      const sit = typeof nota === 'number' ? (nota >= 9.5 ? 'Aprovado' : 'Reprovado') : '';
      linhas.push([d.disciplina, nota, sit]);
    });

    linhas.push([]);
    linhas.push(['MÉDIA GLOBAL:', Math.round(Number(dados.mediaGlobal || 14)), dados.resultadoOficial || 'Aprovado']);
    linhas.push([]);
    linhas.push(['O Director da Escola:', dados.directorNome || 'Director']);

    const ws = XLSX.utils.aoa_to_sheet(linhas);
    ws['!cols'] = [{ wch: 35 }, { wch: 25 }, { wch: 20 }, { wch: 20 }];
    XLSX.utils.book_append_sheet(wb, ws, 'Declaração');
    return XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
  }
}
