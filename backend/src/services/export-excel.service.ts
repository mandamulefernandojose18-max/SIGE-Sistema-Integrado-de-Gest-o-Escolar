import ExcelJS from 'exceljs';

export class ExportExcelService {
  /**
   * Configuração padronizada para conformidade estrita com o Microsoft Excel e Protected View
   */
  private static aplicarPropriedadesWorkbook(workbook: ExcelJS.Workbook) {
    workbook.creator = 'SIGE - Sistema Integrado de Gestão Escolar';
    workbook.lastModifiedBy = 'SIGE - Moçambique';
    workbook.created = new Date();
    workbook.modified = new Date();
  }

  /**
   * Aplica bordas e estilo num bloco de título mesclado garantindo integridade OpenXML
   */
  private static estilizarTituloMesclado(
    sheet: ExcelJS.Worksheet,
    rowNum: number,
    totalCols: number,
    isDestaque: boolean,
    fontSize: number = 10
  ) {
    sheet.mergeCells(rowNum, 1, rowNum, totalCols);
    for (let c = 1; c <= totalCols; c++) {
      const cell = sheet.getCell(rowNum, c);
      cell.border = {
        top: { style: rowNum === 1 ? 'medium' : 'thin', color: { argb: 'FF1E3A8A' } },
        bottom: { style: 'thin', color: { argb: 'FF1E3A8A' } },
        left: { style: c === 1 ? 'medium' : 'thin', color: { argb: 'FF1E3A8A' } },
        right: { style: c === totalCols ? 'medium' : 'thin', color: { argb: 'FF1E3A8A' } }
      };
      cell.alignment = { horizontal: 'center', vertical: 'middle', wrapText: true };
      cell.font = { name: 'Arial', size: fontSize, bold: true, color: { argb: 'FF1E3A8A' } };
      cell.fill = {
        type: 'pattern',
        pattern: 'solid',
        fgColor: { argb: isDestaque ? 'FFE0E7FF' : 'FFF8FAFC' }
      };
    }
  }

  /**
   * Gera a Pauta Oficial da Turma em formato XLSX nativo (ExcelJS)
   */
  static async gerarPautaXlsx(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null };
    turma: { nome: string; grau_ano: string; ano_letivo: string; turno?: string; director_turma?: string };
    disciplinas: Array<{ id: string; nome: string; codigo: string }>;
    alunos: Array<{
      numero: number;
      matricula: string;
      nome: string;
      apelido?: string;
      genero: string;
      notasDisciplinas: Record<string, { t1?: number | null; t2?: number | null; t3?: number | null; mfd?: number | null }>;
      mediasTrimestrais: { t1?: number | null; t2?: number | null; t3?: number | null };
      negativas: { t1: number; t2: number; t3: number; fimDoAno: number };
      mediaFinalGeral: number;
      resultado: string;
    }>;
    estatistica?: {
      inscritos: { h: number; m: number; total: number };
      avaliados: { h: number; m: number; total: number };
      aprovados: { h: number; m: number; total: number; pct: number };
      reprovados: { h: number; m: number; total: number; pct: number };
    };
  }): Promise<Buffer> {
    const workbook = new ExcelJS.Workbook();
    this.aplicarPropriedadesWorkbook(workbook);

    const sheet = workbook.addWorksheet('Pauta Oficial', {
      views: [{ state: 'normal' }],
      pageSetup: { orientation: 'landscape', paperSize: 9, fitToPage: true, fitToWidth: 1 }
    });

    const headerFill: ExcelJS.Fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF1E3A8A' } };
    const headerFont: Partial<ExcelJS.Font> = { name: 'Arial', size: 9, bold: true, color: { argb: 'FFFFFFFF' } };
    const borderThin: Partial<ExcelJS.Borders> = {
      top: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      left: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      bottom: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      right: { style: 'thin', color: { argb: 'FFCBD5E1' } }
    };

    const header1: string[] = ['Nº', 'Nome Completo', 'Gén'];
    dados.disciplinas.forEach(d => {
      const code = d.codigo || d.nome;
      header1.push(`${code} (1º)`, `${code} (2º)`, `${code} (3º)`, `${code} (MFD)`);
    });
    header1.push(
      'Média I', 'Média II', 'Média III',
      'Neg. 1º', 'Neg. 2º', 'Neg. 3º', 'Cadeiras Negativas',
      'Média Geral', 'Resultado Final'
    );
    const totalCols = header1.length;

    // Cabeçalho Institucional Oficial Bordado e Centralizado
    const titulos = [
      'REPÚBLICA DE MOÇAMBIQUE',
      `PROVÍNCIA DE ${dados.escola.provincia?.toUpperCase() || 'MAPUTO'} | DISTRITO DE ${dados.escola.distrito?.toUpperCase() || 'CIDADE DE MAPUTO'}`,
      dados.escola.nome.toUpperCase(),
      `PAUTA OFICIAL DE APROVEITAMENTO PEDAGÓGICO — ANO LECTIVO ${dados.turma.ano_letivo}`,
      `TURMA: ${dados.turma.nome} | CLASSE: ${dados.turma.grau_ano} | TURNO: ${dados.turma.turno || 'DIURNO'} | DIRECTOR DE TURMA: ${dados.turma.director_turma || '-'}`
    ];

    titulos.forEach((texto, idx) => {
      const rowNum = idx + 1;
      sheet.addRow([texto]);
      this.estilizarTituloMesclado(sheet, rowNum, totalCols, rowNum === 3, rowNum === 3 ? 12 : 9.5);
    });

    // Espaçamento entre cabeçalho institucional e conteúdo da tabela (~2 cm)
    const spacer1 = sheet.addRow([]);
    spacer1.height = 20;
    const spacer2 = sheet.addRow([]);
    spacer2.height = 20;

    const rowH1 = sheet.addRow(header1);
    rowH1.height = 26;
    rowH1.eachCell((cell) => {
      cell.fill = headerFill;
      cell.font = headerFont;
      cell.alignment = { horizontal: 'center', vertical: 'middle', wrapText: true };
      cell.border = borderThin;
    });

    dados.alunos.forEach((a, idx) => {
      const nomeCompleto = [a.nome, a.apelido].filter(Boolean).join(' ').trim();
      const rowData: any[] = [
        a.numero || (idx + 1),
        nomeCompleto,
        a.genero
      ];

      dados.disciplinas.forEach(d => {
        const nd = a.notasDisciplinas[d.codigo] || a.notasDisciplinas[d.id] || {};
        rowData.push(
          nd.t1 !== undefined && nd.t1 !== null ? nd.t1 : '-',
          nd.t2 !== undefined && nd.t2 !== null ? nd.t2 : '-',
          nd.t3 !== undefined && nd.t3 !== null ? nd.t3 : '-',
          nd.mfd !== undefined && nd.mfd !== null ? Math.round(nd.mfd) : '-'
        );
      });

      rowData.push(
        a.mediasTrimestrais.t1 !== undefined && a.mediasTrimestrais.t1 !== null ? Math.round(a.mediasTrimestrais.t1) : '-',
        a.mediasTrimestrais.t2 !== undefined && a.mediasTrimestrais.t2 !== null ? Math.round(a.mediasTrimestrais.t2) : '-',
        a.mediasTrimestrais.t3 !== undefined && a.mediasTrimestrais.t3 !== null ? Math.round(a.mediasTrimestrais.t3) : '-',
        a.negativas.t1,
        a.negativas.t2,
        a.negativas.t3,
        a.negativas.fimDoAno,
        Math.round(a.mediaFinalGeral),
        a.resultado
      );

      const row = sheet.addRow(rowData);
      row.height = 20;

      row.eachCell((cell, colNum) => {
        cell.font = { name: 'Arial', size: 9 };
        cell.border = borderThin;

        if (colNum === 2) {
          cell.alignment = { horizontal: 'left', vertical: 'middle' };
        } else {
          cell.alignment = { horizontal: 'center', vertical: 'middle' };
        }

        const val = cell.value;
        if (typeof val === 'number' && val < 9.5 && colNum <= totalCols - 2) {
          cell.font = { name: 'Arial', size: 9, color: { argb: 'FFDC2626' }, bold: true };
        }
        if (colNum === totalCols) {
          const valStr = String(val || '');
          const isAprovado = valStr === 'A' || valStr === 'Aprovado' || valStr.toUpperCase().includes('APROV');
          const cor = isAprovado ? 'FF000000' : 'FFDC2626'; // Aprovado a preto, Reprovado a vermelho
          cell.fill = { type: 'pattern', pattern: 'none' }; // Sem pintar o quadradinho de fundo
          cell.font = {
            name: 'Arial',
            size: 9,
            bold: true,
            color: { argb: cor }
          };
          cell.border = {
            top: { style: 'medium', color: { argb: cor } },
            bottom: { style: 'medium', color: { argb: cor } },
            left: { style: 'medium', color: { argb: cor } },
            right: { style: 'medium', color: { argb: cor } }
          };
        }
      });
    });

    sheet.columns.forEach((col, idx) => {
      if (idx === 0) col.width = 6;
      else if (idx === 1) col.width = 34; // Nome Completo
      else if (idx === 2) col.width = 6;  // Gén
      else col.width = 9;
    });

    const buffer = await workbook.xlsx.writeBuffer();
    return Buffer.from(buffer);
  }

  /**
   * Gera a Caderneta Oficial da Disciplina em formato XLSX nativo (ExcelJS)
   * Formatação estrita com linhas separadas por género (M, F, M+F) segundo modelo oficial MINEDH
   */
  static async gerarCadernetaProfessorXlsx(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null };
    professor: { nome: string; especialidade: string; telefone?: string | null };
    disciplina: { nome: string; codigo: string };
    turma: { nome: string; grau_ano: string; ano_letivo: string; turno?: string };
    directorTurma?: { nome: string; telefone?: string | null } | null;
    efectivo?: { h: number; m: number; total: number };
    alunos: Array<{
      numero: number;
      matricula: string;
      nome: string;
      apelido?: string;
      genero: string;
      t1: { t1?: number | null; t2?: number | null; t3?: number | null; map?: number | null; mas?: number | null; mac3?: number | null; at?: number | null; mt?: number | null; faltas: number; anotacao?: string; comportamento?: string };
      t2: { t1?: number | null; t2?: number | null; t3?: number | null; map?: number | null; mas?: number | null; mac3?: number | null; at?: number | null; mt?: number | null; faltas: number; anotacao?: string; comportamento?: string };
      t3: { t1?: number | null; t2?: number | null; t3?: number | null; map?: number | null; mas?: number | null; mac3?: number | null; at?: number | null; mt?: number | null; faltas: number; anotacao?: string; comportamento?: string };
      mfd?: number | null;
    }>;
    estatisticasColunas?: Record<string, any>;
  }): Promise<Buffer> {
    const workbook = new ExcelJS.Workbook();
    this.aplicarPropriedadesWorkbook(workbook);

    const sheet = workbook.addWorksheet('Caderneta Oficial', {
      views: [{ state: 'normal' }],
      pageSetup: { orientation: 'landscape', paperSize: 9, fitToPage: true, fitToWidth: 1 }
    });

    const headerFill: ExcelJS.Fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF1E3A8A' } };
    const headerFont: Partial<ExcelJS.Font> = { name: 'Arial', size: 9, bold: true, color: { argb: 'FFFFFFFF' } };
    const tHeadFill1: ExcelJS.Fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF1E40AF' } };
    const tHeadFill2: ExcelJS.Fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF2563EB' } };
    const tHeadFill3: ExcelJS.Fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF3B82F6' } };
    const borderThin: Partial<ExcelJS.Borders> = {
      top: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      left: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      bottom: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      right: { style: 'thin', color: { argb: 'FFCBD5E1' } }
    };

    const colunas = [
      'Nº', 'Nome Completo', 'Gén',
      '1º 1ªACS', '1º 2ªACS', '1º 3ªACS', '1º MAP', '1º MAS', '1º AT', '1º MT', '1º COM', '1º Obs',
      '2º 1ªACS', '2º 2ªACS', '2º 3ªACS', '2º MAP', '2º MAS', '2º AT', '2º MT', '2º COM', '2º Obs',
      '3º 1ªACS', '3º 2ªACS', '3º 3ªACS', '3º MAP', '3º MAS', '3º AT', '3º MT', '3º COM', '3º Obs',
      'MFD'
    ];
    const totalCols = colunas.length; // 31 colunas

    // Cabeçalho Oficial Bordado e Centralizado
    const titulos = [
      'REPÚBLICA DE MOÇAMBIQUE',
      `PROVÍNCIA DE ${dados.escola.provincia?.toUpperCase() || 'MAPUTO'} | DISTRITO DE ${dados.escola.distrito?.toUpperCase() || 'CIDADE DE MAPUTO'}`,
      dados.escola.nome.toUpperCase(),
      `CADERNETA DE AVALIAÇÃO CONTÍNUA DO PROFESSOR — ANO LECTIVO ${dados.turma.ano_letivo}`,
      `DISCIPLINA: ${dados.disciplina.nome} (${dados.disciplina.codigo}) | PROFESSOR: ${dados.professor.nome} | TURMA: ${dados.turma.nome} (${dados.turma.grau_ano}) | DIRECTOR TURMA: ${dados.directorTurma?.nome || '-'} | EFECTIVO: H=${dados.efectivo?.h || 0} M=${dados.efectivo?.m || 0} TOTAL=${dados.efectivo?.total || 0}`
    ];

    titulos.forEach((texto, idx) => {
      const rowNum = idx + 1;
      sheet.addRow([texto]);
      this.estilizarTituloMesclado(sheet, rowNum, totalCols, rowNum === 3, rowNum === 3 ? 12 : 9.5);
    });

    // Espaçador (~2 cm)
    const spc1 = sheet.addRow([]);
    spc1.height = 18;
    const spc2 = sheet.addRow([]);
    spc2.height = 18;

    const hRow = sheet.addRow(colunas);
    hRow.height = 24;
    hRow.eachCell((cell, colNum) => {
      if (colNum <= 3) cell.fill = headerFill;
      else if (colNum <= 12) cell.fill = tHeadFill1;
      else if (colNum <= 21) cell.fill = tHeadFill2;
      else if (colNum <= 30) cell.fill = tHeadFill3;
      else cell.fill = headerFill;

      cell.font = headerFont;
      cell.alignment = { horizontal: 'center', vertical: 'middle' };
      cell.border = borderThin;
    });

    dados.alunos.forEach((a, idx) => {
      const valMas1 = a.t1.mas ?? a.t1.mac3 ?? '-';
      const valMas2 = a.t2.mas ?? a.t2.mac3 ?? '-';
      const valMas3 = a.t3.mas ?? a.t3.mac3 ?? '-';

      const nomeCompleto = [a.nome, a.apelido].filter(Boolean).join(' ').trim();
      const rVals: any[] = [
        a.numero || (idx + 1),
        nomeCompleto,
        a.genero,
        a.t1.t1 ?? '-', a.t1.t2 ?? '-', a.t1.t3 ?? '-', a.t1.map ?? '-', valMas1, a.t1.at ?? '-', a.t1.mt ?? '-', a.t1.comportamento ?? 'S', a.t1.anotacao || '-',
        a.t2.t1 ?? '-', a.t2.t2 ?? '-', a.t2.t3 ?? '-', a.t2.map ?? '-', valMas2, a.t2.at ?? '-', a.t2.mt ?? '-', a.t2.comportamento ?? 'S', a.t2.anotacao || '-',
        a.t3.t1 ?? '-', a.t3.t2 ?? '-', a.t3.t3 ?? '-', a.t3.map ?? '-', valMas3, a.t3.at ?? '-', a.t3.mt ?? '-', a.t3.comportamento ?? 'S', a.t3.anotacao || '-',
        a.mfd !== null && a.mfd !== undefined && a.mfd > 0 ? Math.round(a.mfd) : '-'
      ];

      const row = sheet.addRow(rVals);
      row.height = 19;
      row.eachCell((cell, colNum) => {
        cell.font = { name: 'Arial', size: 9 };
        cell.border = borderThin;

        if (colNum === 2) {
          cell.alignment = { horizontal: 'left', vertical: 'middle' };
        } else {
          cell.alignment = { horizontal: 'center', vertical: 'middle' };
        }

        const val = cell.value;
        if (typeof val === 'number' && val < 9.5) {
          cell.font = { name: 'Arial', size: 9, color: { argb: 'FFDC2626' }, bold: true };
        }
      });
    });

    // Rodapé de Estatística Oficial da Caderneta em Linhas Separadas por Género
    if (dados.estatisticasColunas) {
      sheet.addRow([]);
      const stats = dados.estatisticasColunas;

      const colunasMapeadas: Array<string | null> = [
        't1_t1', 't1_t2', 't1_t3', 't1_map', 't1_mas', 't1_at', 't1_mt', null, null,
        't2_t1', 't2_t2', 't2_t3', 't2_map', 't2_mas', 't2_at', 't2_mt', null, null,
        't3_t1', 't3_t2', 't3_t3', 't3_map', 't3_mas', 't3_at', 't3_mt', null, null,
        'mfd'
      ];

      // Função que adiciona uma linha estatística por género
      const addStatRow = (categoriaTexto: string, genero: string, extrator: (s: any) => string | number, isBold = false) => {
        const rowVals: any[] = [categoriaTexto, '', genero];
        colunasMapeadas.forEach(key => {
          if (!key) {
            rowVals.push('-');
          } else {
            const colStat = stats[key] || stats[key.replace('_mas', '_mac3')];
            if (!colStat) {
              rowVals.push('-');
            } else {
              rowVals.push(extrator(colStat));
            }
          }
        });

        const r = sheet.addRow(rowVals);
        r.height = 18;
        const rowNum = r.number;

        for (let col = 1; col <= totalCols; col++) {
          const c = sheet.getCell(rowNum, col);
          c.border = borderThin;
          c.alignment = { horizontal: col <= 2 ? 'left' : 'center', vertical: 'middle' };
          c.font = { name: 'Arial', size: 8.5, bold: isBold };
          if (isBold) {
            c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF1F5F9' } };
          }
        }
      };

      // 1. Avaliados: M, F, M+F
      const startAv = sheet.rowCount + 1;
      addStatRow('Avaliados', 'M', s => s.avaliados ? (s.avaliados.h ?? 0) : '-');
      addStatRow('', 'F', s => s.avaliados ? (s.avaliados.f ?? s.avaliados.m ?? 0) : '-');
      addStatRow('', 'M+F', s => s.avaliados ? s.avaliados.total : '-', true);
      sheet.mergeCells(startAv, 1, startAv + 2, 2);

      // 2. Positivos: M, F, M+F
      const startPos = sheet.rowCount + 1;
      addStatRow('Positivos (>= 9.5)', 'M', s => s.positivas ? (s.positivas.h ?? 0) : '-');
      addStatRow('', 'F', s => s.positivas ? (s.positivas.m ?? 0) : '-');
      addStatRow('', 'M+F', s => s.positivas ? s.positivas.total : '-', true);
      sheet.mergeCells(startPos, 1, startPos + 2, 2);

      // 3. % Positivos: M, F, M+F
      const startPctPos = sheet.rowCount + 1;
      addStatRow('% Positivos', 'M', s => s.positivas ? (s.positivas.pctH !== undefined ? `${s.positivas.pctH}%` : '-') : '-');
      addStatRow('', 'F', s => s.positivas ? (s.positivas.pctM !== undefined ? `${s.positivas.pctM}%` : '-') : '-');
      addStatRow('', 'M+F', s => s.positivas ? `${s.positivas.pct}%` : '-', true);
      sheet.mergeCells(startPctPos, 1, startPctPos + 2, 2);

      // 4. Negativos: M, F, M+F
      const startNeg = sheet.rowCount + 1;
      addStatRow('Negativos (< 9.5)', 'M', s => s.negativas ? (s.negativas.h ?? 0) : '-');
      addStatRow('', 'F', s => s.negativas ? (s.negativas.m ?? 0) : '-');
      addStatRow('', 'M+F', s => s.negativas ? s.negativas.total : '-', true);
      sheet.mergeCells(startNeg, 1, startNeg + 2, 2);

      // 5. % Negativos: M, F, M+F
      const startPctNeg = sheet.rowCount + 1;
      addStatRow('% Negativos', 'M', s => s.negativas ? (s.negativas.pctH !== undefined ? `${s.negativas.pctH}%` : '-') : '-');
      addStatRow('', 'F', s => s.negativas ? (s.negativas.pctM !== undefined ? `${s.negativas.pctM}%` : '-') : '-');
      addStatRow('', 'M+F', s => s.negativas ? `${s.negativas.pct}%` : '-', true);
      sheet.mergeCells(startPctNeg, 1, startPctNeg + 2, 2);

      // 6. Faixas de Notas Oficiais (0 a 9,4 | 9,5 a 13,4 | 13,5 a 16,4 | 16,5 a 18,4 | 18,5 a 20)
      const addFaixaRow = (faixaLabel: string, keyFaixa: string) => {
        const rowVals: any[] = [faixaLabel, '', ''];
        colunasMapeadas.forEach(key => {
          if (!key) {
            rowVals.push('-');
          } else {
            const colStat = stats[key] || stats[key.replace('_mas', '_mac3')];
            if (!colStat || !colStat.faixas || !colStat.faixas[keyFaixa]) {
              rowVals.push('-');
            } else {
              rowVals.push(colStat.faixas[keyFaixa].total ?? 0);
            }
          }
        });
        const r = sheet.addRow(rowVals);
        r.height = 18;
        const rowNum = r.number;
        sheet.mergeCells(rowNum, 1, rowNum, 3);
        for (let col = 1; col <= totalCols; col++) {
          const c = sheet.getCell(rowNum, col);
          c.border = borderThin;
          c.alignment = { horizontal: col <= 3 ? 'left' : 'center', vertical: 'middle' };
          c.font = { name: 'Arial', size: 8.5 };
        }
      };

      addFaixaRow('Notas de 0 a 9,4', 'f0_94');
      addFaixaRow('Notas de 9,5 a 13,4', 'f95_134');
      addFaixaRow('Notas de 13,5 a 16,4', 'f135_164');
      addFaixaRow('Notas de 16,5 a 18,4', 'f165_184');
      addFaixaRow('Notas de 18,5 a 20', 'f185_20');

      // 7. Média da Coluna
      const rowMediaVals: any[] = ['Média da Coluna', '', ''];
      colunasMapeadas.forEach(key => {
        if (!key) {
          rowMediaVals.push('-');
        } else {
          const colStat = stats[key] || stats[key.replace('_mas', '_mac3')];
          if (!colStat || !colStat.media || colStat.media <= 0) {
            rowMediaVals.push('-');
          } else {
            rowMediaVals.push(colStat.media);
          }
        }
      });
      const rMedia = sheet.addRow(rowMediaVals);
      rMedia.height = 20;
      const mediaRowNum = rMedia.number;
      sheet.mergeCells(mediaRowNum, 1, mediaRowNum, 3);
      for (let col = 1; col <= totalCols; col++) {
        const c = sheet.getCell(mediaRowNum, col);
        c.border = borderThin;
        c.alignment = { horizontal: col <= 3 ? 'left' : 'center', vertical: 'middle' };
        c.font = { name: 'Arial', size: 9, bold: true, color: { argb: 'FF1E3A8A' } };
        c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFEFF6FF' } };
      }
    }

    sheet.columns = [
      { width: 6 },   // Nº
      { width: 34 },  // Nome Completo
      { width: 6 },   // Gén
      { width: 7 }, { width: 7 }, { width: 7 }, { width: 7 }, { width: 7 }, { width: 7 }, { width: 7 }, { width: 7 }, { width: 8 },
      { width: 7 }, { width: 7 }, { width: 7 }, { width: 7 }, { width: 7 }, { width: 7 }, { width: 7 }, { width: 7 }, { width: 8 },
      { width: 7 }, { width: 7 }, { width: 7 }, { width: 7 }, { width: 7 }, { width: 7 }, { width: 7 }, { width: 7 }, { width: 8 },
      { width: 8 }
    ];

    const buffer = await workbook.xlsx.writeBuffer();
    return Buffer.from(buffer);
  }

  /**
   * Gera a Acta Oficial do Conselho de Avaliação (ExcelJS) com as 3 tabelas oficiais por género (H, M, HM)
   */
  static async gerarActaEstatisticaXlsx(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null };
    turma: { nome: string; grau_ano: string; ano_letivo: string; turno?: string; director_turma?: string };
    conselho: {
      presidente?: string;
      presidenteT1?: string;
      presidenteT2?: string;
      presidenteT3?: string;
      dataT1?: string;
      dataT2?: string;
      dataT3?: string;
      horaInicioT1?: string;
      minInicioT1?: string;
      horaFimT1?: string;
      minFimT1?: string;
      horaInicioT2?: string;
      minInicioT2?: string;
      horaFimT2?: string;
      minFimT2?: string;
      horaInicioT3?: string;
      minInicioT3?: string;
      horaFimT3?: string;
      minFimT3?: string;
    };
    trimestresComNotas?: { t1?: boolean; t2?: boolean; t3?: boolean; fimAno?: boolean };
    tabelaEfectivo: any;
    tabelaAproveitamento: any;
    disciplinas: any[];
  }): Promise<Buffer> {
    const workbook = new ExcelJS.Workbook();
    this.aplicarPropriedadesWorkbook(workbook);

    const sheet = workbook.addWorksheet('Acta do Conselho', {
      views: [{ state: 'normal' }],
      pageSetup: { orientation: 'landscape', paperSize: 9, fitToPage: true, fitToWidth: 1 }
    });

    const headerFill: ExcelJS.Fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF1E3A8A' } };
    const headerFont: Partial<ExcelJS.Font> = { name: 'Arial', size: 9, bold: true, color: { argb: 'FFFFFFFF' } };
    const subHeaderFill: ExcelJS.Fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFDBEAFE' } };
    const borderThin: Partial<ExcelJS.Borders> = {
      top: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      left: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      bottom: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      right: { style: 'thin', color: { argb: 'FFCBD5E1' } }
    };

    const totalCols = 13;

    const p1 = dados.conselho.presidenteT1 || dados.conselho.presidente || 'Fernando José Mandamule';
    const p2 = dados.conselho.presidenteT2 || dados.conselho.presidente || 'Fernando José Mandamule';
    const p3 = dados.conselho.presidenteT3 || '_________________';
    const dt1 = dados.conselho.dataT1 || '26/05/2026';
    const dt2 = dados.conselho.dataT2 || '01/09/2026';
    const dt3 = dados.conselho.dataT3 || '____/____/2026';

    const hIni1 = dados.conselho.horaInicioT1 || '09';
    const mIni1 = dados.conselho.minInicioT1 || '30';
    const hFim1 = dados.conselho.horaFimT1 || '10';
    const mFim1 = dados.conselho.minFimT1 || '00';

    const hIni2 = dados.conselho.horaInicioT2 || '09';
    const mIni2 = dados.conselho.minInicioT2 || '30';
    const hFim2 = dados.conselho.horaFimT2 || '11';
    const mFim2 = dados.conselho.minFimT2 || '00';

    const hIni3 = dados.conselho.horaInicioT3 || '____';
    const mIni3 = dados.conselho.minInicioT3 || '____';
    const hFim3 = dados.conselho.horaFimT3 || '____';
    const mFim3 = dados.conselho.minFimT3 || '____';

    const textoProtocolar = `Sob presidência do senhor professor ${p1} (Iº Trimestre); ${p2} (IIº Trimestre); ${p3} (IIIº Trimestre); director/substituto do director de turma ${dados.turma.nome} do grupo da ${dados.turma.grau_ano}, curso ${dados.turma.turno || 'Diurno'}, realizou-se o Conselho de Avaliação do Iº; IIº, IIIº, Trimestre no dia ${dt1}; ${dt2}; ${dt3}, com início às ${hIni1} horas e ${mIni1} minutos e com término às ${hFim1} horas e ${mFim1} minutos (Iº Trim); ${hIni2} horas e ${mIni2} minutos e com término às ${hFim2} horas e ${mFim2} minutos (IIº Trim); ${hIni3} horas e ${mIni3} minutos e com término às ${hFim3} horas e ${mFim3} minutos (IIIº Trim). No final deste conselho colheram-se os resultados que abaixo vão discriminados de todos os membros que participaram:`;

    const titulos = [
      'REPÚBLICA DE MOÇAMBIQUE',
      `GOVERNO DA PROVÍNCIA DE ${dados.escola.provincia?.toUpperCase() || 'MAPUTO'} | DISTRITO DE ${dados.escola.distrito?.toUpperCase() || 'CIDADE DE MAPUTO'}`,
      dados.escola.nome.toUpperCase(),
      'SECTOR PEDAGÓGICO — ACTA DO CONSELHO DE AVALIAÇÃO',
      textoProtocolar
    ];

    titulos.forEach((texto, idx) => {
      const rowNum = idx + 1;
      sheet.addRow([texto]);
      this.estilizarTituloMesclado(sheet, rowNum, totalCols, rowNum === 4, rowNum === 4 ? 12 : 9);
    });

    sheet.addRow([]);

    // ==================== TABELA 1 ====================
    const t1Title = sheet.addRow(['APROVEITAMENTO ESCOLAR POR TRIMESTRES E FIM DO ANO (EFECTIVOS E MOVIMENTO)']);
    this.estilizarTituloMesclado(sheet, t1Title.number, 10, true, 10);

    const t1Head = sheet.addRow([
      'CATEGORIA', 'GÉN',
      'Iº TRIM (Nº)', 'Iº TRIM (%)',
      'IIº TRIM (Nº)', 'IIº TRIM (%)',
      'IIIº TRIM (Nº)', 'IIIº TRIM (%)',
      'FIM ANO (Nº)', 'FIM ANO (%)'
    ]);
    t1Head.eachCell(c => {
      c.fill = headerFill;
      c.font = headerFont;
      c.border = borderThin;
      c.alignment = { horizontal: 'center', vertical: 'middle' };
    });

    const te = dados.tabelaEfectivo;
    const addTeBlock = (label: string, key: string) => {
      const startRow = sheet.rowCount + 1;
      ['H', 'M', 'HM'].forEach((gen, gIdx) => {
        const prop = gen === 'H' ? 'h' : (gen === 'M' ? 'm' : 'hm');
        const pctProp = gen === 'H' ? 'pctH' : (gen === 'M' ? 'pctM' : 'pct');

        const tc = dados.trimestresComNotas || { t1: true, t2: true, t3: true, fimAno: true };
        const vT1 = tc.t1 && te.t1[key] ? te.t1[key][prop] : (tc.t1 ? 0 : '-');
        const pT1 = tc.t1 && te.t1[key] && te.t1[key][pctProp] !== undefined ? `${te.t1[key][pctProp]}%` : '-';

        const vT2 = tc.t2 && te.t2[key] ? te.t2[key][prop] : (tc.t2 ? 0 : '-');
        const pT2 = tc.t2 && te.t2[key] && te.t2[key][pctProp] !== undefined ? `${te.t2[key][pctProp]}%` : '-';

        const vT3 = tc.t3 && te.t3[key] ? te.t3[key][prop] : (tc.t3 ? 0 : '-');
        const pT3 = tc.t3 && te.t3[key] && te.t3[key][pctProp] !== undefined ? `${te.t3[key][pctProp]}%` : '-';

        const vFA = tc.fimAno && te.fimAno[key] ? te.fimAno[key][prop] : (tc.fimAno ? 0 : '-');
        const pFA = tc.fimAno && te.fimAno[key] && te.fimAno[key][pctProp] !== undefined ? `${te.fimAno[key][pctProp]}%` : '-';

        const r = sheet.addRow([
          gIdx === 0 ? label : '',
          gen,
          vT1, pT1,
          vT2, pT2,
          vT3, pT3,
          vFA, pFA
        ]);
        r.height = 18;
        for (let col = 1; col <= 10; col++) {
          const c = sheet.getCell(r.number, col);
          c.border = borderThin;
          c.alignment = { horizontal: col === 1 ? 'left' : 'center', vertical: 'middle' };
          c.font = { name: 'Arial', size: 8.5, bold: gen === 'HM' };
          if (gen === 'HM') {
            c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF1F5F9' } };
          }
        }
      });
      sheet.mergeCells(startRow, 1, startRow + 2, 1);
    };

    addTeBlock('Matrículas / Efectivo Inicial', 'inscritos');
    addTeBlock('Desistentes', 'desistentes');
    addTeBlock('Transferidos', 'transferidos');
    addTeBlock('Falecidos', 'falecidos');
    addTeBlock('Perdeu Ano/Direito por Faltas', 'perdeuFaltas');
    addTeBlock('Anulou Matrícula', 'anulouMatricula');
    addTeBlock('Alunos Avaliados', 'avaliados');

    sheet.addRow([]);

    // ==================== TABELA 2 ====================
    const t2Title = sheet.addRow(['APROVEITAMENTO PEDAGÓGICO POR FAIXAS E CRESCIMENTO']);
    this.estilizarTituloMesclado(sheet, t2Title.number, 13, true, 10);

    const t2Head = sheet.addRow([
      'CLASSIFICAÇÃO', 'GÉN',
      'Iº TRIM (Nº)', 'Iº TRIM (%)',
      'IIº TRIM (Nº)', 'IIº TRIM (%)',
      'IIIº TRIM (Nº)', 'IIIº TRIM (%)',
      'FIM ANO (Nº)', 'FIM ANO (%)',
      'CRESC. Iº-IIº', 'CRESC. IIº-IIIº', 'CRESC. GLOBAL'
    ]);
    t2Head.eachCell(c => {
      c.fill = headerFill;
      c.font = headerFont;
      c.border = borderThin;
      c.alignment = { horizontal: 'center', vertical: 'middle' };
    });

    const ta = dados.tabelaAproveitamento;
    const addTaBlock = (label: string, key: string, isAprov = false) => {
      const startRow = sheet.rowCount + 1;
      ['H', 'M', 'HM'].forEach((gen, gIdx) => {
        const prop = gen === 'H' ? 'h' : (gen === 'M' ? 'm' : 'hm');
        const pctProp = gen === 'H' ? 'pctH' : (gen === 'M' ? 'pctM' : 'pct');

        const tc = dados.trimestresComNotas || { t1: true, t2: true, t3: true, fimAno: true };
        const vT1 = tc.t1 && ta.t1[key] ? ta.t1[key][prop] : (tc.t1 ? 0 : '-');
        const pT1 = tc.t1 && ta.t1[key] && ta.t1[key][pctProp] !== undefined ? `${ta.t1[key][pctProp]}%` : (tc.t1 && key === 'avaliados' ? '100%' : '-');

        const vT2 = tc.t2 && ta.t2[key] ? ta.t2[key][prop] : (tc.t2 ? 0 : '-');
        const pT2 = tc.t2 && ta.t2[key] && ta.t2[key][pctProp] !== undefined ? `${ta.t2[key][pctProp]}%` : (tc.t2 && key === 'avaliados' ? '100%' : '-');

        const vT3 = tc.t3 && ta.t3[key] ? ta.t3[key][prop] : (tc.t3 ? 0 : '-');
        const pT3 = tc.t3 && ta.t3[key] && ta.t3[key][pctProp] !== undefined ? `${ta.t3[key][pctProp]}%` : (tc.t3 && key === 'avaliados' ? '100%' : '-');

        const vFA = tc.fimAno && ta.fimAno[key] ? ta.fimAno[key][prop] : (tc.fimAno ? 0 : '-');
        const pFA = tc.fimAno && ta.fimAno[key] && ta.fimAno[key][pctProp] !== undefined ? `${ta.fimAno[key][pctProp]}%` : (tc.fimAno && key === 'avaliados' ? '100%' : '-');

        // Cálculo do Crescimento (%) condicionado à existência de notas nos 2 períodos
        let c1_2 = '-';
        if (tc.t1 && tc.t2) {
          const nPT1 = ta.t1[key] && ta.t1[key][pctProp] ? Number(ta.t1[key][pctProp]) : 0;
          const nPT2 = ta.t2[key] && ta.t2[key][pctProp] ? Number(ta.t2[key][pctProp]) : 0;
          const dif1_2 = Number((nPT2 - nPT1).toFixed(1));
          c1_2 = dif1_2 > 0 ? `+${dif1_2}%` : (dif1_2 < 0 ? `${dif1_2}%` : '0%');
        }

        let c2_3 = '-';
        if (tc.t2 && tc.t3) {
          const nPT2 = ta.t2[key] && ta.t2[key][pctProp] ? Number(ta.t2[key][pctProp]) : 0;
          const nPT3 = ta.t3[key] && ta.t3[key][pctProp] ? Number(ta.t3[key][pctProp]) : 0;
          const dif2_3 = Number((nPT3 - nPT2).toFixed(1));
          c2_3 = dif2_3 > 0 ? `+${dif2_3}%` : (dif2_3 < 0 ? `${dif2_3}%` : '0%');
        }

        let cGlo = '-';
        if (tc.t1 && tc.fimAno) {
          const nPT1 = ta.t1[key] && ta.t1[key][pctProp] ? Number(ta.t1[key][pctProp]) : 0;
          const nPFA = ta.fimAno[key] && ta.fimAno[key][pctProp] ? Number(ta.fimAno[key][pctProp]) : 0;
          const difGlo = Number((nPFA - nPT1).toFixed(1));
          cGlo = difGlo > 0 ? `+${difGlo}%` : (difGlo < 0 ? `${difGlo}%` : '0%');
        }

        const r = sheet.addRow([
          gIdx === 0 ? label : '',
          gen,
          vT1, pT1,
          vT2, pT2,
          vT3, pT3,
          vFA, pFA,
          c1_2, c2_3, cGlo
        ]);
        r.height = 18;
        for (let col = 1; col <= 13; col++) {
          const c = sheet.getCell(r.number, col);
          c.border = borderThin;
          c.alignment = { horizontal: col === 1 ? 'left' : 'center', vertical: 'middle' };
          c.font = { name: 'Arial', size: 8.5, bold: gen === 'HM' || isAprov };
          if (isAprov) {
            c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFDCFCE7' } };
          } else if (gen === 'HM') {
            c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF1F5F9' } };
          }
        }
      });
      sheet.mergeCells(startRow, 1, startRow + 2, 1);
    };

    addTaBlock('Alunos Avaliados', 'avaliados');
    addTaBlock('Não Satisfatório (0 a 9,4)', 'naoSatisfatorio');
    addTaBlock('Satisfatório (9,5 a 13,4)', 'satisfatorio');
    addTaBlock('Bom (13,5 a 16,4)', 'bom');
    addTaBlock('Muito Bom (16,5 a 18,4)', 'muitoBom');
    addTaBlock('Excelente (18,5 a 20)', 'excelente');
    addTaBlock('TOTAL APROVADOS', 'aprovados', true);
    addTaBlock('TOTAL REPROVADOS', 'reprovados');

    sheet.addRow([]);

    // ==================== TABELA 3 ====================
    const t3ColsCount = 1 + (dados.disciplinas.length * 3);
    const t3Title = sheet.addRow(['ÁREA DE COMUNICAÇÃO E CIÊNCIAS SOCIAIS / ESTATÍSTICA POR DISCIPLINA']);
    this.estilizarTituloMesclado(sheet, t3Title.number, Math.max(t3ColsCount, 13), true, 10);

    // Linha 1 de cabeçalho com nomes das disciplinas
    const hDisc1: string[] = ['CLASSIFICAÇÃO'];
    dados.disciplinas.forEach(d => {
      hDisc1.push(d.nome.toUpperCase(), '', '');
    });
    const rHDisc1 = sheet.addRow(hDisc1);
    rHDisc1.height = 22;
    rHDisc1.eachCell((c, col) => {
      c.fill = headerFill;
      c.font = headerFont;
      c.border = borderThin;
      c.alignment = { horizontal: 'center', vertical: 'middle' };
    });

    // Mescla colunas das disciplinas no cabeçalho
    dados.disciplinas.forEach((_, idx) => {
      const startCol = 2 + (idx * 3);
      sheet.mergeCells(rHDisc1.number, startCol, rHDisc1.number, startCol + 2);
    });

    // Linha 2 de cabeçalho: H, M, HM para cada disciplina
    const hDisc2: string[] = ['FAIXA / PARÂMETRO'];
    dados.disciplinas.forEach(() => {
      hDisc2.push('H', 'M', 'HM');
    });
    const rHDisc2 = sheet.addRow(hDisc2);
    rHDisc2.height = 20;
    rHDisc2.eachCell(c => {
      c.fill = subHeaderFill;
      c.font = { name: 'Arial', size: 8.5, bold: true, color: { argb: 'FF1E3A8A' } };
      c.border = borderThin;
      c.alignment = { horizontal: 'center', vertical: 'middle' };
    });

    const addT3Row = (faixaLabel: string, propFaixa: string) => {
      const rVals: any[] = [faixaLabel];
      dados.disciplinas.forEach(d => {
        const obj = d[propFaixa] || { h: 0, m: 0, hm: 0 };
        rVals.push(obj.h ?? 0, obj.m ?? 0, obj.hm ?? 0);
      });
      const r = sheet.addRow(rVals);
      r.height = 18;
      r.eachCell((c, col) => {
        c.border = borderThin;
        c.alignment = { horizontal: col === 1 ? 'left' : 'center', vertical: 'middle' };
        c.font = { name: 'Arial', size: 8.5 };
      });
    };

    addT3Row('[0 - 9,4 valores]', 'faixa0_9');
    addT3Row('[9,5 - 13,4 valores]', 'faixa10_13');
    addT3Row('[13,5 - 16,4 valores]', 'faixa14_16');
    addT3Row('[16,5 - 18,4 valores]', 'faixa17_18');
    addT3Row('[18,5 - 20 valores]', 'faixa19_20');

    // Linhas de Resumo
    const addT3Summary = (label: string, propKey: string, isPct = false, isBold = false) => {
      const rVals: any[] = [label];
      dados.disciplinas.forEach(d => {
        const obj = d[propKey] || { h: 0, m: 0, hm: 0 };
        if (isPct) {
          rVals.push(
            obj.pctH !== undefined ? `${obj.pctH}%` : '-',
            obj.pctM !== undefined ? `${obj.pctM}%` : '-',
            obj.pct !== undefined ? `${obj.pct}%` : '-'
          );
        } else {
          rVals.push(obj.h ?? 0, obj.m ?? 0, obj.hm ?? 0);
        }
      });
      const r = sheet.addRow(rVals);
      r.height = 19;
      r.eachCell((c, col) => {
        c.border = borderThin;
        c.alignment = { horizontal: col === 1 ? 'left' : 'center', vertical: 'middle' };
        c.font = { name: 'Arial', size: 8.5, bold: isBold };
        if (isBold) {
          c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF8FAFC' } };
        }
      });
    };

    addT3Summary('Alunos Avaliados', 'avaliados', false, true);
    addT3Summary('Notas Positivas', 'positivas', false, true);
    addT3Summary('% Positivas', 'positivas', true, true);

    // Linha de Assinatura do Professor da Disciplina
    const rAssinatura: any[] = ['Assinatura do Professor'];
    dados.disciplinas.forEach(() => {
      rAssinatura.push('_________________', '', '');
    });
    const rAssRow = sheet.addRow(rAssinatura);
    rAssRow.height = 24;
    dados.disciplinas.forEach((_, idx) => {
      const startCol = 2 + (idx * 3);
      sheet.mergeCells(rAssRow.number, startCol, rAssRow.number, startCol + 2);
    });
    rAssRow.eachCell(c => {
      c.border = borderThin;
      c.alignment = { horizontal: 'center', vertical: 'middle' };
      c.font = { name: 'Arial', size: 8, italic: true };
    });

    const maxCols = Math.max(13, t3ColsCount);
    for (let c = 1; c <= maxCols; c++) {
      const col = sheet.getColumn(c);
      if (c === 1) col.width = 30;
      else col.width = 8;
    }

    const buffer = await workbook.xlsx.writeBuffer();
    return Buffer.from(buffer);
  }

  /**
   * Gera o Mapa Consolidado de Estatísticas do Aproveitamento Pedagógico Escolar
   * (Por Turma, Geral por Classe, Global da Escola e por Disciplina)
   */
  static async gerarEstatisticasAproveitamentoXlsx(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null };
    anoLetivo: string;
    periodo: string;
    geralEscola: {
      totalTurmas: number;
      inscritos: { h: number; m: number; total: number };
      avaliados: { h: number; m: number; total: number };
      aprovados: { h: number; m: number; total: number; pct: number };
      reprovados: { h: number; m: number; total: number; pct: number };
    };
    porClasse: Array<{
      classe: string;
      turmas: number;
      inscritos: { h: number; m: number; total: number };
      avaliados: { h: number; m: number; total: number };
      aprovados: { h: number; m: number; total: number; pct: number };
      reprovados: { h: number; m: number; total: number; pct: number };
    }>;
    porTurma: Array<{
      turmaNome: string;
      grau_ano: string;
      turno: string;
      directorTurma: string;
      inscritos: { h: number; m: number; total: number };
      avaliados: { h: number; m: number; total: number };
      aprovados: { h: number; m: number; total: number; pct: number };
      reprovados: { h: number; m: number; total: number; pct: number };
    }>;
    porDisciplina: Array<{
      nome: string;
      codigo: string;
      avaliados: { h: number; m: number; total: number };
      aprovados: { h: number; m: number; total: number; pct: number };
      reprovados: { h: number; m: number; total: number; pct: number };
      mediaFinal: number | null;
    }>;
  }): Promise<Buffer> {
    const workbook = new ExcelJS.Workbook();
    this.aplicarPropriedadesWorkbook(workbook);

    const borderThin: Partial<ExcelJS.Borders> = {
      top: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      left: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      bottom: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      right: { style: 'thin', color: { argb: 'FFCBD5E1' } }
    };
    const headerFill: ExcelJS.Fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF1E3A8A' } };
    const headerFont: Partial<ExcelJS.Font> = { name: 'Arial', size: 9, bold: true, color: { argb: 'FFFFFFFF' } };
    const subHeadFill: ExcelJS.Fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF3B82F6' } };

    // ================= ABA 1: RESUMO POR CLASSE E ESCOLA GLOBAL =================
    const shGeral = workbook.addWorksheet('Resumo Classes e Global', {
      views: [{ state: 'normal' }],
      pageSetup: { orientation: 'landscape', paperSize: 9, fitToPage: true }
    });

    shGeral.mergeCells('A1:L1');
    shGeral.getCell('A1').value = 'REPÚBLICA DE MOÇAMBIQUE - MINISTÉRIO DA EDUCAÇÃO E DESENVOLVIMENTO HUMANO';
    shGeral.getCell('A1').font = { name: 'Arial', size: 10, bold: true };
    shGeral.getCell('A1').alignment = { horizontal: 'center' };

    shGeral.mergeCells('A2:L2');
    shGeral.getCell('A2').value = `${dados.escola.nome.toUpperCase()} | ESTATÍSTICA DO APROVEITAMENTO PEDAGÓGICO - ANO LECTIVO ${dados.anoLetivo}`;
    shGeral.getCell('A2').font = { name: 'Arial', size: 11, bold: true, color: { argb: 'FF1E3A8A' } };
    shGeral.getCell('A2').alignment = { horizontal: 'center' };

    shGeral.addRow([]);

    // Tabela 1: Geral por Classe
    const rT1 = shGeral.addRow(['Nível / Classe', 'Qtd Turmas', 'Inscritos HM', 'Inscritos M', 'Inscritos Total', 'Avaliados HM', 'Avaliados M', 'Avaliados Total', 'Aprovados Total', '% Aprovados', 'Reprovados Total', '% Reprovados']);
    rT1.eachCell(c => {
      c.fill = headerFill;
      c.font = headerFont;
      c.alignment = { horizontal: 'center', vertical: 'middle', wrapText: true };
      c.border = borderThin;
    });

    dados.porClasse.forEach(c => {
      const row = shGeral.addRow([
        c.classe,
        c.turmas,
        c.inscritos.h,
        c.inscritos.m,
        c.inscritos.total,
        c.avaliados.h,
        c.avaliados.m,
        c.avaliados.total,
        c.aprovados.total,
        `${c.aprovados.pct}%`,
        c.reprovados.total,
        `${c.reprovados.pct}%`
      ]);
      row.eachCell((cell, colNum) => {
        cell.border = borderThin;
        cell.alignment = { horizontal: colNum <= 2 ? 'left' : 'center', vertical: 'middle' };
      });
    });

    // Linha Total Escola
    const ge = dados.geralEscola;
    const rowGlobal = shGeral.addRow([
      'TOTAL GERAL DA ESCOLA',
      ge.totalTurmas,
      ge.inscritos.h,
      ge.inscritos.m,
      ge.inscritos.total,
      ge.avaliados.h,
      ge.avaliados.m,
      ge.avaliados.total,
      ge.aprovados.total,
      `${ge.aprovados.pct}%`,
      ge.reprovados.total,
      `${ge.reprovados.pct}%`
    ]);
    rowGlobal.eachCell(c => {
      c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE0E7FF' } };
      c.font = { name: 'Arial', size: 9, bold: true, color: { argb: 'FF1E3A8A' } };
      c.border = borderThin;
      c.alignment = { horizontal: 'center', vertical: 'middle' };
    });

    shGeral.columns.forEach((col, idx) => {
      col.width = idx === 0 ? 18 : 13;
    });

    // ================= ABA 2: APROVEITAMENTO POR TURMA =================
    const shTurmas = workbook.addWorksheet('Aproveitamento por Turma', {
      views: [{ state: 'normal' }],
      pageSetup: { orientation: 'landscape', paperSize: 9, fitToPage: true }
    });

    shTurmas.mergeCells('A1:L1');
    shTurmas.getCell('A1').value = `${dados.escola.nome.toUpperCase()} - APROVEITAMENTO PEDAGÓGICO POR TURMA (${dados.anoLetivo})`;
    shTurmas.getCell('A1').font = { name: 'Arial', size: 11, bold: true, color: { argb: 'FF1E3A8A' } };
    shTurmas.getCell('A1').alignment = { horizontal: 'center' };

    const rHeadTurma = shTurmas.addRow([
      'Turma', 'Classe', 'Turno', 'Director de Turma',
      'Inscritos (HM)', 'Inscritos (M)', 'Inscritos Total',
      'Avaliados (HM)', 'Avaliados (M)', 'Avaliados Total',
      'Aprovados Total', '% Aproveitamento'
    ]);
    rHeadTurma.eachCell(c => {
      c.fill = headerFill;
      c.font = headerFont;
      c.alignment = { horizontal: 'center', vertical: 'middle', wrapText: true };
      c.border = borderThin;
    });

    dados.porTurma.forEach(t => {
      const r = shTurmas.addRow([
        t.turmaNome,
        t.grau_ano,
        t.turno,
        t.directorTurma,
        t.inscritos.h,
        t.inscritos.m,
        t.inscritos.total,
        t.avaliados.h,
        t.avaliados.m,
        t.avaliados.total,
        t.aprovados.total,
        `${t.aprovados.pct}%`
      ]);
      r.eachCell((cell, colNum) => {
        cell.border = borderThin;
        cell.alignment = { horizontal: colNum <= 4 ? 'left' : 'center', vertical: 'middle' };
      });
    });

    shTurmas.columns.forEach((col, idx) => {
      if (idx === 0) col.width = 16;
      else if (idx === 1) col.width = 10;
      else if (idx === 2) col.width = 12;
      else if (idx === 3) col.width = 24;
      else col.width = 13;
    });

    // ================= ABA 3: APROVEITAMENTO POR DISCIPLINA =================
    const shDisc = workbook.addWorksheet('Por Disciplina', {
      views: [{ state: 'normal' }],
      pageSetup: { orientation: 'landscape', paperSize: 9, fitToPage: true }
    });

    shDisc.mergeCells('A1:J1');
    shDisc.getCell('A1').value = `${dados.escola.nome.toUpperCase()} - APROVEITAMENTO COMPARATIVO POR DISCIPLINA (${dados.anoLetivo})`;
    shDisc.getCell('A1').font = { name: 'Arial', size: 11, bold: true, color: { argb: 'FF1E3A8A' } };
    shDisc.getCell('A1').alignment = { horizontal: 'center' };

    const rHeadDisc = shDisc.addRow([
      'Disciplina', 'Código',
      'Avaliados (HM)', 'Avaliados (M)', 'Avaliados Total',
      'Aprovados (HM)', 'Aprovados (M)', 'Aprovados Total',
      '% Aproveitamento', 'Média Final Geral'
    ]);
    rHeadDisc.eachCell(c => {
      c.fill = subHeadFill;
      c.font = headerFont;
      c.alignment = { horizontal: 'center', vertical: 'middle', wrapText: true };
      c.border = borderThin;
    });

    dados.porDisciplina.forEach(d => {
      const r = shDisc.addRow([
        d.nome,
        d.codigo,
        d.avaliados.h,
        d.avaliados.m,
        d.avaliados.total,
        d.aprovados.h,
        d.aprovados.m,
        d.aprovados.total,
        `${d.aprovados.pct}%`,
        d.mediaFinal !== null ? d.mediaFinal : '-'
      ]);
      r.eachCell((cell, colNum) => {
        cell.border = borderThin;
        cell.alignment = { horizontal: colNum <= 2 ? 'left' : 'center', vertical: 'middle' };
      });
    });

    shDisc.columns.forEach((col, idx) => {
      if (idx === 0) col.width = 25;
      else if (idx === 1) col.width = 12;
      else col.width = 14;
    });

    const buffer = await workbook.xlsx.writeBuffer();
    return Buffer.from(buffer);
  }

  /**
   * Gera o Boletim Escolar Oficial do Aluno em XLSX nativo (ExcelJS)
   */
  static async gerarBoletimXlsx(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null; nif_cnpj?: string | null };
    aluno: { nome: string; matricula: string; turma: string; grau: string; genero?: string };
    anoLetivo: string;
    disciplinas: Array<{ nome: string; t1?: number | null; t2?: number | null; t3?: number | null; mediaFinal?: number | null; faltas?: number }>;
    mediaGeral: number;
    resultado: string;
    dataExtenso?: string;
  }): Promise<Buffer> {
    const workbook = new ExcelJS.Workbook();
    this.aplicarPropriedadesWorkbook(workbook);

    const sheet = workbook.addWorksheet('Boletim Escolar', {
      views: [{ state: 'normal' }],
      pageSetup: { orientation: 'portrait', paperSize: 9, fitToPage: true }
    });

    const borderThin: Partial<ExcelJS.Borders> = {
      top: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      left: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      bottom: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      right: { style: 'thin', color: { argb: 'FFCBD5E1' } }
    };
    const headerFill: ExcelJS.Fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF1E3A8A' } };
    const headerFont: Partial<ExcelJS.Font> = { name: 'Arial', size: 9, bold: true, color: { argb: 'FFFFFFFF' } };

    // Cabeçalho Institucional Oficial Bordado e Centralizado
    const titulos = [
      'REPÚBLICA DE MOÇAMBIQUE — MINISTÉRIO DA EDUCAÇÃO E DESENVOLVIMENTO HUMANO',
      dados.escola.nome.toUpperCase(),
      `NUIT: ${dados.escola.nif_cnpj || '-'} | ${dados.escola.distrito || '-'}, ${dados.escola.provincia || 'Maputo'}`,
      `BOLETIM OFICIAL DE AVALIAÇÃO TRIMESTRAL — ANO LECTIVO ${dados.anoLetivo}`
    ];
    titulos.forEach((texto, idx) => {
      const rowNum = idx + 1;
      sheet.addRow([texto]);
      this.estilizarTituloMesclado(sheet, rowNum, 6, rowNum === 2, rowNum === 2 ? 12 : (rowNum === 4 ? 11 : 9.5));
    });

    // Espaçamento de ~2 cm entre cabeçalho institucional e conteúdo
    const sp1 = sheet.addRow([]);
    sp1.height = 18;
    const sp2 = sheet.addRow([]);
    sp2.height = 18;

    // Dados do Aluno em bloco bordado
    const rInfo1 = sheet.addRow([`Aluno: ${dados.aluno.nome}`, '', '', `Nº Matrícula: ${dados.aluno.matricula}`, '', '']);
    sheet.mergeCells(`A${rInfo1.number}:C${rInfo1.number}`);
    sheet.mergeCells(`D${rInfo1.number}:F${rInfo1.number}`);
    const rInfo2 = sheet.addRow([`Turma: ${dados.aluno.turma}`, '', '', `Grau / Classe: ${dados.aluno.grau}`, '', '']);
    sheet.mergeCells(`A${rInfo2.number}:C${rInfo2.number}`);
    sheet.mergeCells(`D${rInfo2.number}:F${rInfo2.number}`);

    [rInfo1, rInfo2].forEach(r => {
      r.height = 20;
      r.eachCell((cell, colNum) => {
        cell.border = borderThin;
        cell.font = { name: 'Arial', size: 9, bold: colNum === 1 || colNum === 4 };
        cell.alignment = { vertical: 'middle', horizontal: 'left' };
      });
    });

    sheet.addRow([]);

    // Tabela de Disciplinas
    const rHead = sheet.addRow(['Disciplina Curricular', '1º Trimestre', '2º Trimestre', '3º Trimestre', 'Média Final (MFD)', 'Faltas']);
    rHead.height = 22;
    rHead.eachCell(c => {
      c.fill = headerFill;
      c.font = headerFont;
      c.alignment = { horizontal: 'center', vertical: 'middle' };
      c.border = borderThin;
    });

    dados.disciplinas.forEach(disc => {
      const medFinal = disc.mediaFinal !== undefined && disc.mediaFinal !== null ? Math.round(disc.mediaFinal) : '-';
      const r = sheet.addRow([
        disc.nome,
        disc.t1 !== undefined && disc.t1 !== null ? Math.round(disc.t1) : '-',
        disc.t2 !== undefined && disc.t2 !== null ? Math.round(disc.t2) : '-',
        disc.t3 !== undefined && disc.t3 !== null ? Math.round(disc.t3) : '-',
        medFinal,
        disc.faltas || 0
      ]);
      r.height = 19;
      r.eachCell((cell, colNum) => {
        cell.border = borderThin;
        cell.alignment = { horizontal: colNum === 1 ? 'left' : 'center', vertical: 'middle' };
        cell.font = { name: 'Arial', size: 9 };
        if (colNum === 5 && typeof medFinal === 'number') {
          cell.font = { name: 'Arial', size: 9, bold: true, color: { argb: medFinal >= 9.5 ? 'FF15803D' : 'FFDC2626' } };
        }
      });
    });

    sheet.addRow([]);

    // Resumo de Resultados e Média Global Arredondada
    const mediaGlobalInt = Math.round(dados.mediaGeral || 0);
    const rResumo = sheet.addRow([
      `MÉDIA GLOBAL: ${mediaGlobalInt} VALORES`, '', '',
      `RESULTADO: ${dados.resultado.toUpperCase()}`, '', ''
    ]);
    sheet.mergeCells(`A${rResumo.number}:C${rResumo.number}`);
    sheet.mergeCells(`D${rResumo.number}:F${rResumo.number}`);
    sheet.getCell(`A${rResumo.number}`).font = { name: 'Arial', size: 10, bold: true, color: { argb: 'FF1E3A8A' } };
    sheet.getCell(`A${rResumo.number}`).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE0E7FF' } };
    sheet.getCell(`A${rResumo.number}`).border = borderThin;
    sheet.getCell(`D${rResumo.number}`).font = { name: 'Arial', size: 10, bold: true, color: { argb: dados.resultado.toUpperCase().includes('APROV') ? 'FF15803D' : 'FFDC2626' } };
    sheet.getCell(`D${rResumo.number}`).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE0E7FF' } };
    sheet.getCell(`D${rResumo.number}`).border = borderThin;

    sheet.addRow([]);
    const rData = sheet.addRow([dados.dataExtenso || `Maputo, ${new Date().toLocaleDateString('pt-PT')}`]);
    sheet.mergeCells(`A${rData.number}:F${rData.number}`);
    sheet.getCell(`A${rData.number}`).font = { name: 'Arial', size: 9, italic: true };
    sheet.getCell(`A${rData.number}`).alignment = { horizontal: 'right' };

    sheet.columns = [
      { width: 32 }, { width: 15 }, { width: 15 }, { width: 15 }, { width: 20 }, { width: 12 }
    ];

    const buffer = await workbook.xlsx.writeBuffer();
    return Buffer.from(buffer);
  }

  /**
   * Gera a Declaração Oficial com Notas em XLSX nativo (ExcelJS)
   */
  static async gerarDeclaracaoXlsx(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null };
    aluno: { nomeCompleto?: string; nome?: string; matricula: string; genero?: string; pai?: string | null; mae?: string | null; distrito?: string | null; provincia?: string | null; turma?: any };
    anoLectivo: string;
    grauAno?: string;
    directorNome?: string;
    directorCarreira?: string;
    chefeSecretariaNome?: string;
    disciplinas: Array<{ disciplina: string; notaFinal: number }>;
    mediaGlobal: number;
    resultadoOficial: string;
    siglaResultado: string;
    livroRegisto?: string;
    folha?: string;
    termoExames?: string;
    dataExtenso?: string;
  }): Promise<Buffer> {
    const workbook = new ExcelJS.Workbook();
    this.aplicarPropriedadesWorkbook(workbook);

    const sheet = workbook.addWorksheet('Declaração Oficial', {
      views: [{ state: 'normal' }],
      pageSetup: { orientation: 'portrait', paperSize: 9, fitToPage: true }
    });

    const borderThin: Partial<ExcelJS.Borders> = {
      top: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      left: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      bottom: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      right: { style: 'thin', color: { argb: 'FFCBD5E1' } }
    };
    const headerFill: ExcelJS.Fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF1E3A8A' } };
    const headerFont: Partial<ExcelJS.Font> = { name: 'Arial', size: 9, bold: true, color: { argb: 'FFFFFFFF' } };

    // Cabeçalho Oficial Bordado e Centralizado
    const titulos = [
      'REPÚBLICA DE MOÇAMBIQUE',
      `GOVERNO DA PROVÍNCIA DE ${(dados.escola.provincia || 'Maputo').toUpperCase()}`,
      dados.escola.nome.toUpperCase(),
      'DECLARAÇÃO OFICIAL COM NOTAS'
    ];
    titulos.forEach((texto, idx) => {
      const rowNum = idx + 1;
      sheet.addRow([texto]);
      this.estilizarTituloMesclado(sheet, rowNum, 4, rowNum === 3, rowNum === 3 ? 12 : (rowNum === 4 ? 13 : 9.5));
    });

    // Espaçamento de ~2 cm entre cabeçalho e conteúdo
    const sp1 = sheet.addRow([]);
    sp1.height = 18;
    const sp2 = sheet.addRow([]);
    sp2.height = 18;

    const alunoNome = (dados.aluno.nomeCompleto || dados.aluno.nome || 'ALUNO').toUpperCase();
    const directorNome = dados.directorNome || 'Director da Escola';
    const mediaGlobalInt = Math.round(dados.mediaGlobal || 14);

    const rTexto = sheet.addRow([
      `Eu, ${directorNome}, Director da instituição, declaro que ${alunoNome}, matriculado sob o nº ${dados.aluno.matricula}, concluiu o Ano Lectivo de ${dados.anoLectivo} com as classificações constantes abaixo:`
    ]);
    sheet.mergeCells(`A${rTexto.number}:D${rTexto.number}`);
    sheet.getCell(`A${rTexto.number}`).alignment = { wrapText: true, horizontal: 'left' };
    sheet.getCell(`A${rTexto.number}`).font = { name: 'Arial', size: 9.5 };
    rTexto.height = 36;

    sheet.addRow([]);

    const rHead = sheet.addRow(['Nº', 'Disciplina Curricular', 'Classificação Obtida', 'Situação Oficial']);
    rHead.height = 22;
    rHead.eachCell(c => {
      c.fill = headerFill;
      c.font = headerFont;
      c.alignment = { horizontal: 'center', vertical: 'middle' };
      c.border = borderThin;
    });

    dados.disciplinas.forEach((d, idx) => {
      const nota = Math.round(d.notaFinal);
      const sit = nota >= 9.5 ? 'Aprovado' : 'Reprovado';
      const r = sheet.addRow([idx + 1, d.disciplina, `${nota} valores`, sit]);
      r.height = 19;
      r.eachCell((c, colNum) => {
        c.border = borderThin;
        c.alignment = { horizontal: colNum === 2 ? 'left' : 'center', vertical: 'middle' };
        c.font = { name: 'Arial', size: 9 };
        if (colNum === 3) c.font = { name: 'Arial', size: 9, bold: true };
      });
    });

    sheet.addRow([]);

    const rMed = sheet.addRow(['MÉDIA GLOBAL DA CLASSE', '', `${mediaGlobalInt} VALORES`, dados.resultadoOficial.toUpperCase()]);
    sheet.mergeCells(`A${rMed.number}:B${rMed.number}`);
    sheet.getCell(`A${rMed.number}`).font = { name: 'Arial', size: 10, bold: true, color: { argb: 'FF1E3A8A' } };
    sheet.getCell(`A${rMed.number}`).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE0E7FF' } };
    sheet.getCell(`A${rMed.number}`).border = borderThin;
    sheet.getCell(`C${rMed.number}`).font = { name: 'Arial', size: 10, bold: true, color: { argb: 'FF1E3A8A' } };
    sheet.getCell(`C${rMed.number}`).alignment = { horizontal: 'center' };
    sheet.getCell(`C${rMed.number}`).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE0E7FF' } };
    sheet.getCell(`C${rMed.number}`).border = borderThin;
    sheet.getCell(`D${rMed.number}`).font = { name: 'Arial', size: 10, bold: true, color: { argb: dados.resultadoOficial.toUpperCase().includes('APROV') ? 'FF15803D' : 'FFDC2626' } };
    sheet.getCell(`D${rMed.number}`).alignment = { horizontal: 'center' };
    sheet.getCell(`D${rMed.number}`).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE0E7FF' } };
    sheet.getCell(`D${rMed.number}`).border = borderThin;

    sheet.addRow([]);
    const rReg = sheet.addRow([
      `Livro de Registo Académico: ${dados.livroRegisto || '01'} | Folha: ${dados.folha || '32'} | Termo de Exames: ${dados.termoExames || '124'}`
    ]);
    sheet.mergeCells(`A${rReg.number}:D${rReg.number}`);
    sheet.getCell(`A${rReg.number}`).font = { name: 'Arial', size: 8.5, italic: true };
    sheet.getCell(`A${rReg.number}`).alignment = { horizontal: 'center' };

    sheet.columns = [{ width: 8 }, { width: 38 }, { width: 25 }, { width: 18 }];

    const buffer = await workbook.xlsx.writeBuffer();
    return Buffer.from(buffer);
  }

  /**
   * Gera o Certificado de Habilitações em XLSX nativo (ExcelJS)
   */
  static async gerarCertificadoXlsx(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null };
    aluno: { nomeCompleto?: string; nome?: string; matricula: string; genero?: string; pai?: string | null; mae?: string | null; data_nascimento?: any; distrito?: string | null; provincia?: string | null; turma?: any };
    anoLectivo: string;
    grauAno?: string;
    directorNome?: string;
    directorCarreira?: string;
    chefeSecretariaNome?: string;
    chefeSecretariaCarreira?: string;
    disciplinas: Array<{ disciplina: string; notaFinal: number }>;
    mediaGlobal: number;
    resultadoOficial: string;
    siglaResultado?: string;
    livroRegisto?: string;
    termoExames?: string;
    pautaNumero?: string;
    dataExtenso?: string;
  }): Promise<Buffer> {
    const workbook = new ExcelJS.Workbook();
    this.aplicarPropriedadesWorkbook(workbook);

    const sheet = workbook.addWorksheet('Certificado de Habilitações', {
      views: [{ state: 'normal' }],
      pageSetup: { orientation: 'portrait', paperSize: 9, fitToPage: true }
    });

    const borderThin: Partial<ExcelJS.Borders> = {
      top: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      left: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      bottom: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      right: { style: 'thin', color: { argb: 'FFCBD5E1' } }
    };
    const headerFill: ExcelJS.Fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF1E3A8A' } };
    const headerFont: Partial<ExcelJS.Font> = { name: 'Arial', size: 9, bold: true, color: { argb: 'FFFFFFFF' } };

    // Cabeçalho Oficial Bordado e Centralizado
    const titulos = [
      'REPÚBLICA DE MOÇAMBIQUE',
      'MINISTÉRIO DA EDUCAÇÃO E DESENVOLVIMENTO HUMANO',
      dados.escola.nome.toUpperCase(),
      'CERTIFICADO DE HABILITAÇÕES LITERÁRIAS'
    ];
    titulos.forEach((texto, idx) => {
      const rowNum = idx + 1;
      sheet.addRow([texto]);
      this.estilizarTituloMesclado(sheet, rowNum, 3, rowNum === 3, rowNum === 3 ? 12 : (rowNum === 4 ? 13 : 9.5));
    });

    // Espaçamento de ~2 cm entre cabeçalho institucional e conteúdo
    const sp1 = sheet.addRow([]);
    sp1.height = 18;
    const sp2 = sheet.addRow([]);
    sp2.height = 18;

    const alunoNome = (dados.aluno.nomeCompleto || dados.aluno.nome || 'ALUNO').toUpperCase();
    const mediaGlobalInt = Math.round(dados.mediaGlobal || 14);

    const rTexto = sheet.addRow([
      `Certifico que ${alunoNome}, matriculado com o nº ${dados.aluno.matricula}, concluiu o nível do Ensino Secundário Geral no Ano Lectivo de ${dados.anoLectivo} com as classificações oficiais abaixo discriminadas:`
    ]);
    sheet.mergeCells(`A${rTexto.number}:C${rTexto.number}`);
    sheet.getCell(`A${rTexto.number}`).alignment = { wrapText: true, horizontal: 'left' };
    sheet.getCell(`A${rTexto.number}`).font = { name: 'Arial', size: 9.5 };
    rTexto.height = 36;

    sheet.addRow([]);

    const rHead = sheet.addRow(['Nº', 'Disciplina Curricular Oficial', 'Classificação Homologada']);
    rHead.height = 22;
    rHead.eachCell(c => {
      c.fill = headerFill;
      c.font = headerFont;
      c.alignment = { horizontal: 'center', vertical: 'middle' };
      c.border = borderThin;
    });

    dados.disciplinas.forEach((d, idx) => {
      const nota = Math.round(d.notaFinal);
      const r = sheet.addRow([idx + 1, d.disciplina, `( ${nota} ) valores`]);
      r.height = 19;
      r.eachCell((c, colNum) => {
        c.border = borderThin;
        c.alignment = { horizontal: colNum === 2 ? 'left' : 'center', vertical: 'middle' };
        c.font = { name: 'Arial', size: 9 };
        if (colNum === 3) c.font = { name: 'Arial', size: 9, bold: true };
      });
    });

    sheet.addRow([]);

    const rMed = sheet.addRow([
      `MÉDIA GERAL DO CURSO: ( ${mediaGlobalInt} ) VALORES`, '',
      `PAUTA: ${dados.pautaNumero || '01'} | TERMO: ${dados.termoExames || '124'}`
    ]);
    sheet.mergeCells(`A${rMed.number}:B${rMed.number}`);
    sheet.getCell(`A${rMed.number}`).font = { name: 'Arial', size: 10, bold: true, color: { argb: 'FF1E3A8A' } };
    sheet.getCell(`A${rMed.number}`).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FEF3C7' } };
    sheet.getCell(`A${rMed.number}`).border = borderThin;
    sheet.getCell(`C${rMed.number}`).font = { name: 'Arial', size: 9.5, bold: true };
    sheet.getCell(`C${rMed.number}`).alignment = { horizontal: 'center' };
    sheet.getCell(`C${rMed.number}`).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FEF3C7' } };
    sheet.getCell(`C${rMed.number}`).border = borderThin;

    sheet.addRow([]);
    const rDir = sheet.addRow([
      `O Director da Escola: ${dados.directorNome || 'Pero Chitofo Murrombe'} | Chefe da Secretaria: ${dados.chefeSecretariaNome || 'Glória João Zunguze'}`
    ]);
    sheet.mergeCells(`A${rDir.number}:C${rDir.number}`);
    sheet.getCell(`A${rDir.number}`).font = { name: 'Arial', size: 8.5, italic: true };
    sheet.getCell(`A${rDir.number}`).alignment = { horizontal: 'center' };

    sheet.columns = [{ width: 8 }, { width: 44 }, { width: 28 }];

    const buffer = await workbook.xlsx.writeBuffer();
    return Buffer.from(buffer);
  }

  /**
   * Gera um ficheiro XLSX consolidado com múltiplos documentos emitidos em lote
   */
  static async gerarLoteDocumentosXlsx(
    documentos: any[],
    tipo: 'BOLETIM' | 'DECLARACAO' | 'CERTIFICADO'
  ): Promise<Buffer> {
    const workbook = new ExcelJS.Workbook();
    this.aplicarPropriedadesWorkbook(workbook);

    const sheet = workbook.addWorksheet(`Lote ${tipo}`, {
      views: [{ state: 'normal' }],
      pageSetup: { orientation: 'landscape', paperSize: 9, fitToPage: true }
    });

    const borderThin: Partial<ExcelJS.Borders> = {
      top: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      left: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      bottom: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      right: { style: 'thin', color: { argb: 'FFCBD5E1' } }
    };
    const headerFill: ExcelJS.Fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF1E3A8A' } };
    const headerFont: Partial<ExcelJS.Font> = { name: 'Arial', size: 9, bold: true, color: { argb: 'FFFFFFFF' } };

    sheet.mergeCells('A1:G1');
    sheet.getCell('A1').value = `RELAÇÃO OFICIAL DE DOCUMENTOS EMITIDOS EM LOTE (${tipo})`;
    sheet.getCell('A1').font = { name: 'Arial', size: 12, bold: true, color: { argb: 'FF1E3A8A' } };
    sheet.getCell('A1').alignment = { horizontal: 'center' };

    const rHead = sheet.addRow(['Nº', 'Aluno / Nome Completo', 'Nº Matrícula', 'Gén', 'Turma', 'Média Global', 'Situação']);
    rHead.height = 22;
    rHead.eachCell(c => {
      c.fill = headerFill;
      c.font = headerFont;
      c.alignment = { horizontal: 'center', vertical: 'middle' };
      c.border = borderThin;
    });

    documentos.forEach((doc, idx) => {
      const aluno = doc.aluno || {};
      const nome = aluno.nomeCompleto || aluno.nome || '-';
      const mat = aluno.matricula || '-';
      const gen = aluno.genero || '-';
      const turma = aluno.turma?.nome || aluno.turma || doc.turma?.nome || '-';
      const med = Math.round(Number(doc.mediaGlobal !== undefined ? doc.mediaGlobal : (doc.mediaGeral !== undefined ? doc.mediaGeral : 14)) || 14);
      const sit = doc.resultadoOficial || doc.resultado || (med >= 9.5 ? 'Aprovado' : 'Reprovado');

      const r = sheet.addRow([idx + 1, nome, mat, gen, turma, med, sit]);
      r.height = 19;
      r.eachCell((c, colNum) => {
        c.border = borderThin;
        c.alignment = { horizontal: colNum === 2 ? 'left' : 'center', vertical: 'middle' };
        c.font = { name: 'Arial', size: 9 };
        if (colNum === 6) c.font = { name: 'Arial', size: 9, bold: true };
      });
    });

    sheet.columns = [
      { width: 8 }, { width: 34 }, { width: 18 }, { width: 8 }, { width: 18 }, { width: 15 }, { width: 18 }
    ];

    const buffer = await workbook.xlsx.writeBuffer();
    return Buffer.from(buffer);
  }
}
