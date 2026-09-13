import * as XLSX from 'xlsx';

export class ExportExcelService {
  /**
   * Gera a Pauta Oficial da Turma em formato XLSX (conforme modelo oficial da imagem 3)
   */
  static gerarPautaXlsx(dados: {
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
  }): Buffer {
    const wb = XLSX.utils.book_new();

    const rows: any[][] = [
      ['REPÚBLICA DE MOÇAMBIQUE'],
      [`PROVÍNCIA DE ${dados.escola.provincia?.toUpperCase() || 'MAPUTO'} | DISTRITO DE ${dados.escola.distrito?.toUpperCase() || 'CIDADE DE MAPUTO'}`],
      [dados.escola.nome.toUpperCase()],
      [`PAUTA OFICIAL DE APROVEITAMENTO PEDAGÓGICO - ANO LECTIVO ${dados.turma.ano_letivo}`],
      [`TURMA: ${dados.turma.nome} | CLASSE: ${dados.turma.grau_ano} | TURNO: ${dados.turma.turno || 'DIURNO'} | DIRECTOR DE TURMA: ${dados.turma.director_turma || '-'}`],
      []
    ];

    const headerRow: string[] = ['Nº', 'Nome do Aluno', 'Apelido', 'Género'];
    dados.disciplinas.forEach(d => {
      const discNome = d.codigo || d.nome;
      headerRow.push(`${discNome} (1º)`, `${discNome} (2º)`, `${discNome} (3º)`, `${discNome} (MFD)`);
    });
    headerRow.push(
      'Média I Trim', 'Média II Trim', 'Média III Trim',
      'Neg. 1º', 'Neg. 2º', 'Neg. 3º', 'Neg. Fim Ano',
      'Média Final Geral', 'Resultado Final'
    );
    rows.push(headerRow);

    dados.alunos.forEach(a => {
      const row: any[] = [
        a.numero,
        a.nome,
        a.apelido || '',
        a.genero
      ];

      dados.disciplinas.forEach(d => {
        const nd = a.notasDisciplinas[d.codigo || d.id] || a.notasDisciplinas[d.id] || {};
        row.push(
          nd.t1 !== null && nd.t1 !== undefined ? nd.t1 : '-',
          nd.t2 !== null && nd.t2 !== undefined ? nd.t2 : '-',
          nd.t3 !== null && nd.t3 !== undefined ? nd.t3 : '-',
          nd.mfd !== null && nd.mfd !== undefined ? nd.mfd : '-'
        );
      });

      row.push(
        a.mediasTrimestrais.t1 !== null && a.mediasTrimestrais.t1 !== undefined ? a.mediasTrimestrais.t1 : '-',
        a.mediasTrimestrais.t2 !== null && a.mediasTrimestrais.t2 !== undefined ? a.mediasTrimestrais.t2 : '-',
        a.mediasTrimestrais.t3 !== null && a.mediasTrimestrais.t3 !== undefined ? a.mediasTrimestrais.t3 : '-',
        a.negativas.t1,
        a.negativas.t2,
        a.negativas.t3,
        a.negativas.fimDoAno,
        a.mediaFinalGeral,
        a.resultado
      );

      rows.push(row);
    });

    if (dados.estatistica) {
      rows.push([]);
      rows.push(['RESUMO ESTATÍSTICO DA TURMA']);
      rows.push(['INDICADOR', 'HOMENS (H)', 'MULHERES (M)', 'TOTAL GERAL', 'TAXA (%)']);
      rows.push(['Alunos Inscritos', dados.estatistica.inscritos.h, dados.estatistica.inscritos.m, dados.estatistica.inscritos.total, '100%']);
      rows.push(['Alunos Avaliados', dados.estatistica.avaliados.h, dados.estatistica.avaliados.m, dados.estatistica.avaliados.total, '-']);
      rows.push(['Aprovados', dados.estatistica.aprovados.h, dados.estatistica.aprovados.m, dados.estatistica.aprovados.total, `${dados.estatistica.aprovados.pct}%`]);
      rows.push(['Reprovados', dados.estatistica.reprovados.h, dados.estatistica.reprovados.m, dados.estatistica.reprovados.total, `${dados.estatistica.reprovados.pct}%`]);
    }

    const ws = XLSX.utils.aoa_to_sheet(rows);
    XLSX.utils.book_append_sheet(wb, ws, 'Pauta Oficial');
    return XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
  }

  /**
   * Gera a Caderneta Oficial da Disciplina em formato XLSX com todos os trimestres e estatísticas por coluna no rodapé (Imagem 2)
   */
  static gerarCadernetaProfessorXlsx(dados: {
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
      t1: { t1?: number | null; t2?: number | null; t3?: number | null; map?: number | null; mac3?: number | null; at?: number | null; mt?: number | null; faltas: number; anotacao?: string; comportamento?: string };
      t2: { t1?: number | null; t2?: number | null; t3?: number | null; map?: number | null; mac3?: number | null; at?: number | null; mt?: number | null; faltas: number; anotacao?: string; comportamento?: string };
      t3: { t1?: number | null; t2?: number | null; t3?: number | null; map?: number | null; mac3?: number | null; at?: number | null; mt?: number | null; faltas: number; anotacao?: string; comportamento?: string };
      mfd?: number | null;
    }>;
    estatisticasColunas?: Record<string, {
      avaliados: { h: number; m: number; total: number };
      positivas: { h: number; m: number; total: number; pct: number };
      negativas: { h: number; m: number; total: number; pct: number };
      media: number;
    }>;
  }): Buffer {
    const wb = XLSX.utils.book_new();

    const rows: any[][] = [
      ['REPÚBLICA DE MOÇAMBIQUE'],
      [`PROVÍNCIA DE ${dados.escola.provincia?.toUpperCase() || 'MAPUTO'} | DISTRITO DE ${dados.escola.distrito?.toUpperCase() || 'CIDADE DE MAPUTO'}`],
      [dados.escola.nome.toUpperCase()],
      [`MAPA DE REGISTO DE AVALIAÇÕES — ANO LECTIVO ${dados.turma.ano_letivo}`],
      [
        `DISCIPLINA: ${dados.disciplina.nome} (${dados.disciplina.codigo})`,
        `PROFESSOR: ${dados.professor.nome} (${dados.professor.telefone || '-'})`,
        `TURMA: ${dados.turma.nome} (${dados.turma.grau_ano})`,
        `DIRECTOR TURMA: ${dados.directorTurma?.nome || '-'}`,
        `EFECTIVO: H=${dados.efectivo?.h || 0} | M=${dados.efectivo?.m || 0} | TOTAL=${dados.efectivo?.total || 0}`
      ],
      []
    ];

    const colunas = [
      'Nº', 'Nome do Aluno', 'Apelido', 'Género',
      '1º Trim. 1ª ACS', '1º Trim. 2ª ACS', '1º Trim. 3ª ACS', '1º Trim. MAP', '1º Trim. MAC3', '1º Trim. AT', '1º Trim. MT', '1º Trim. COM', '1º Trim. Obs',
      '2º Trim. 1ª ACS', '2º Trim. 2ª ACS', '2º Trim. 3ª ACS', '2º Trim. MAP', '2º Trim. MAC3', '2º Trim. AT', '2º Trim. MT', '2º Trim. COM', '2º Trim. Obs',
      '3º Trim. 1ª ACS', '3º Trim. 2ª ACS', '3º Trim. 3ª ACS', '3º Trim. MAP', '3º Trim. MAC3', '3º Trim. AT', '3º Trim. MT', '3º Trim. COM', '3º Trim. Obs',
      'MFD'
    ];
    rows.push(colunas);

    dados.alunos.forEach(a => {
      rows.push([
        a.numero,
        a.nome,
        a.apelido || '',
        a.genero,
        a.t1.t1 ?? '-', a.t1.t2 ?? '-', a.t1.t3 ?? '-', a.t1.map ?? '-', a.t1.mac3 ?? '-', a.t1.at ?? '-', a.t1.mt ?? '-', a.t1.comportamento ?? 'S', a.t1.anotacao || '-',
        a.t2.t1 ?? '-', a.t2.t2 ?? '-', a.t2.t3 ?? '-', a.t2.map ?? '-', a.t2.mac3 ?? '-', a.t2.at ?? '-', a.t2.mt ?? '-', a.t2.comportamento ?? 'S', a.t2.anotacao || '-',
        a.t3.t1 ?? '-', a.t3.t2 ?? '-', a.t3.t3 ?? '-', a.t3.map ?? '-', a.t3.mac3 ?? '-', a.t3.at ?? '-', a.t3.mt ?? '-', a.t3.comportamento ?? 'S', a.t3.anotacao || '-',
        a.mfd ?? '-'
      ]);
    });

    if (dados.estatisticasColunas) {
      const stats = dados.estatisticasColunas;

      rows.push([]);
      rows.push(['ESTATÍSTICA POR COLUNA']);

      const linhaAvaliados: any[] = ['Alunos Avaliados', '', '', ''];
      const linhaPositivas: any[] = ['Notas Positivas (>= 10)', '', '', ''];
      const linhaPctPositivas: any[] = ['% Positivas', '', '', ''];
      const linhaNegativas: any[] = ['Notas Negativas (< 10)', '', '', ''];
      const linhaPctNegativas: any[] = ['% Negativas', '', '', ''];
      const linhaMedias: any[] = ['Média da Coluna', '', '', ''];

      const colunasMapeadas: Array<string | null> = [
        't1_t1', 't1_t2', 't1_t3', 't1_map', null, 't1_at', 't1_mt', null, null,
        't2_t1', 't2_t2', 't2_t3', 't2_map', null, 't2_at', 't2_mt', null, null,
        't3_t1', 't3_t2', 't3_t3', 't3_map', null, 't3_at', 't3_mt', null, null,
        'mfd'
      ];

      colunasMapeadas.forEach(key => {
        if (!key || !stats[key]) {
          linhaAvaliados.push('-');
          linhaPositivas.push('-');
          linhaPctPositivas.push('-');
          linhaNegativas.push('-');
          linhaPctNegativas.push('-');
          linhaMedias.push('-');
        } else {
          const s = stats[key];
          linhaAvaliados.push(s.avaliados.total);
          linhaPositivas.push(s.positivas.total);
          linhaPctPositivas.push(`${s.positivas.pct}%`);
          linhaNegativas.push(s.negativas.total);
          linhaPctNegativas.push(`${s.negativas.pct}%`);
          linhaMedias.push(s.media);
        }
      });

      rows.push(linhaAvaliados);
      rows.push(linhaPositivas);
      rows.push(linhaPctPositivas);
      rows.push(linhaNegativas);
      rows.push(linhaPctNegativas);
      rows.push(linhaMedias);
    }

    const ws = XLSX.utils.aoa_to_sheet(rows);
    XLSX.utils.book_append_sheet(wb, ws, 'Caderneta Oficial');
    return XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
  }

  /**
   * Gera a Acta do Conselho de Avaliação com as 3 tabelas oficiais (Imagem 1)
   */
  static gerarActaEstatisticaXlsx(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null };
    turma: { nome: string; grau_ano: string; ano_letivo: string; turno?: string; director_turma?: string };
    conselho: {
      presidente?: string;
      dataT1?: string;
      dataT2?: string;
      dataT3?: string;
      horaInicio?: string;
      horaFim?: string;
    };
    tabelaEfectivo: {
      t1: { inscritos: { h: number; m: number; hm: number }; desistentes: { h: number; m: number; hm: number }; transferidos: { h: number; m: number; hm: number }; falecidos: { h: number; m: number; hm: number }; avaliados: { h: number; m: number; hm: number } };
      t2: { inscritos: { h: number; m: number; hm: number }; desistentes: { h: number; m: number; hm: number }; transferidos: { h: number; m: number; hm: number }; falecidos: { h: number; m: number; hm: number }; avaliados: { h: number; m: number; hm: number } };
      t3: { inscritos: { h: number; m: number; hm: number }; desistentes: { h: number; m: number; hm: number }; transferidos: { h: number; m: number; hm: number }; falecidos: { h: number; m: number; hm: number }; avaliados: { h: number; m: number; hm: number } };
      fimAno: { inscritos: { h: number; m: number; hm: number }; desistentes: { h: number; m: number; hm: number }; transferidos: { h: number; m: number; hm: number }; falecidos: { h: number; m: number; hm: number }; avaliados: { h: number; m: number; hm: number } };
    };
    tabelaAproveitamento: {
      t1: { avaliados: { h: number; m: number; hm: number; pct: number }; naoSatisfatorio: { h: number; m: number; hm: number; pct: number }; satisfatorio: { h: number; m: number; hm: number; pct: number }; bom: { h: number; m: number; hm: number; pct: number }; muitoBom: { h: number; m: number; hm: number; pct: number }; excelente: { h: number; m: number; hm: number; pct: number }; aprovados: { h: number; m: number; hm: number; pct: number }; reprovados: { h: number; m: number; hm: number; pct: number } };
      t2: { avaliados: { h: number; m: number; hm: number; pct: number }; naoSatisfatorio: { h: number; m: number; hm: number; pct: number }; satisfatorio: { h: number; m: number; hm: number; pct: number }; bom: { h: number; m: number; hm: number; pct: number }; muitoBom: { h: number; m: number; hm: number; pct: number }; excelente: { h: number; m: number; hm: number; pct: number }; aprovados: { h: number; m: number; hm: number; pct: number }; reprovados: { h: number; m: number; hm: number; pct: number } };
      t3: { avaliados: { h: number; m: number; hm: number; pct: number }; naoSatisfatorio: { h: number; m: number; hm: number; pct: number }; satisfatorio: { h: number; m: number; hm: number; pct: number }; bom: { h: number; m: number; hm: number; pct: number }; muitoBom: { h: number; m: number; hm: number; pct: number }; excelente: { h: number; m: number; hm: number; pct: number }; aprovados: { h: number; m: number; hm: number; pct: number }; reprovados: { h: number; m: number; hm: number; pct: number } };
      fimAno: { avaliados: { h: number; m: number; hm: number; pct: number }; naoSatisfatorio: { h: number; m: number; hm: number; pct: number }; satisfatorio: { h: number; m: number; hm: number; pct: number }; bom: { h: number; m: number; hm: number; pct: number }; muitoBom: { h: number; m: number; hm: number; pct: number }; excelente: { h: number; m: number; hm: number; pct: number }; aprovados: { h: number; m: number; hm: number; pct: number }; reprovados: { h: number; m: number; hm: number; pct: number } };
    };
    disciplinas: Array<{
      nome: string;
      codigo: string;
      faixa0_9: { h: number; m: number; hm: number };
      faixa10_13: { h: number; m: number; hm: number };
      faixa14_16: { h: number; m: number; hm: number };
      faixa17_18: { h: number; m: number; hm: number };
      faixa19_20: { h: number; m: number; hm: number };
      avaliados: { h: number; m: number; hm: number };
      positivas: { h: number; m: number; hm: number; pct: number };
      negativas: { h: number; m: number; hm: number; pct: number };
    }>;
  }): Buffer {
    const wb = XLSX.utils.book_new();

    const rows: any[][] = [
      ['REPÚBLICA DE MOÇAMBIQUE'],
      [`GOVERNO DA PROVÍNCIA DE ${dados.escola.provincia?.toUpperCase() || 'MAPUTO'}`],
      [`GOVERNO DO DISTRITO DE ${dados.escola.distrito?.toUpperCase() || 'CIDADE DE MAPUTO'}`],
      [dados.escola.nome.toUpperCase()],
      ['SECTOR PEDAGÓGICO'],
      ['ACTA DO CONSELHO DE AVALIAÇÃO'],
      [
        `Sob presidência do senhor professor ${dados.conselho.presidente || dados.turma.director_turma || 'Director de Turma'}, ` +
        `director/substituto do director de turma ${dados.turma.nome} do grupo da ${dados.turma.grau_ano}, curso ${dados.turma.turno || 'Diurno'}, ` +
        `realizou-se o Conselho de Avaliação do Iº, IIº e IIIº Trimestres. No final colheram-se os resultados abaixo discriminados:`
      ],
      []
    ];

    rows.push(['TABELA 1: APROVEITAMENTO PEDAGÓGICO POR TRIMESTRE E FIM DO ANO (EFECTIVOS E MOVIMENTO)']);
    rows.push([
      'CATEGORIA',
      'Iº Trim (H)', 'Iº Trim (M)', 'Iº Trim (HM)',
      'IIº Trim (H)', 'IIº Trim (M)', 'IIº Trim (HM)',
      'IIIº Trim (H)', 'IIIº Trim (M)', 'IIIº Trim (HM)',
      'FIM ANO (H)', 'FIM ANO (M)', 'FIM ANO (HM)'
    ]);

    const te = dados.tabelaEfectivo;
    rows.push(['Efectivo Inicial / Matriculados', te.t1.inscritos.h, te.t1.inscritos.m, te.t1.inscritos.hm, te.t2.inscritos.h, te.t2.inscritos.m, te.t2.inscritos.hm, te.t3.inscritos.h, te.t3.inscritos.m, te.t3.inscritos.hm, te.fimAno.inscritos.h, te.fimAno.inscritos.m, te.fimAno.inscritos.hm]);
    rows.push(['Desistentes', te.t1.desistentes.h, te.t1.desistentes.m, te.t1.desistentes.hm, te.t2.desistentes.h, te.t2.desistentes.m, te.t2.desistentes.hm, te.t3.desistentes.h, te.t3.desistentes.m, te.t3.desistentes.hm, te.fimAno.desistentes.h, te.fimAno.desistentes.m, te.fimAno.desistentes.hm]);
    rows.push(['Transferidos', te.t1.transferidos.h, te.t1.transferidos.m, te.t1.transferidos.hm, te.t2.transferidos.h, te.t2.transferidos.m, te.t2.transferidos.hm, te.t3.transferidos.h, te.t3.transferidos.m, te.t3.transferidos.hm, te.fimAno.transferidos.h, te.fimAno.transferidos.m, te.fimAno.transferidos.hm]);
    rows.push(['Falecidos', te.t1.falecidos.h, te.t1.falecidos.m, te.t1.falecidos.hm, te.t2.falecidos.h, te.t2.falecidos.m, te.t2.falecidos.hm, te.t3.falecidos.h, te.t3.falecidos.m, te.t3.falecidos.hm, te.fimAno.falecidos.h, te.fimAno.falecidos.m, te.fimAno.falecidos.hm]);
    rows.push(['Efectivo Final / Avaliados', te.t1.avaliados.h, te.t1.avaliados.m, te.t1.avaliados.hm, te.t2.avaliados.h, te.t2.avaliados.m, te.t2.avaliados.hm, te.t3.avaliados.h, te.t3.avaliados.m, te.t3.avaliados.hm, te.fimAno.avaliados.h, te.fimAno.avaliados.m, te.fimAno.avaliados.hm]);
    rows.push([]);

    rows.push(['TABELA 2: CLASSIFICAÇÃO PEDAGÓGICA POR FAIXAS DE NOTAS']);
    rows.push([
      'FAIXA DE CLASSIFICAÇÃO',
      'Iº Trim (HM)', 'Iº Trim (%)',
      'IIº Trim (HM)', 'IIº Trim (%)',
      'IIIº Trim (HM)', 'IIIº Trim (%)',
      'FIM ANO (HM)', 'FIM ANO (%)'
    ]);

    const ta = dados.tabelaAproveitamento;
    rows.push(['Alunos Avaliados', ta.t1.avaliados.hm, '100%', ta.t2.avaliados.hm, '100%', ta.t3.avaliados.hm, '100%', ta.fimAno.avaliados.hm, '100%']);
    rows.push(['Não Satisfatório (0 a 9 valores)', ta.t1.naoSatisfatorio.hm, `${ta.t1.naoSatisfatorio.pct}%`, ta.t2.naoSatisfatorio.hm, `${ta.t2.naoSatisfatorio.pct}%`, ta.t3.naoSatisfatorio.hm, `${ta.t3.naoSatisfatorio.pct}%`, ta.fimAno.naoSatisfatorio.hm, `${ta.fimAno.naoSatisfatorio.pct}%`]);
    rows.push(['Satisfatório (10 a 13 valores)', ta.t1.satisfatorio.hm, `${ta.t1.satisfatorio.pct}%`, ta.t2.satisfatorio.hm, `${ta.t2.satisfatorio.pct}%`, ta.t3.satisfatorio.hm, `${ta.t3.satisfatorio.pct}%`, ta.fimAno.satisfatorio.hm, `${ta.fimAno.satisfatorio.pct}%`]);
    rows.push(['Bom (14 a 16 valores)', ta.t1.bom.hm, `${ta.t1.bom.pct}%`, ta.t2.bom.hm, `${ta.t2.bom.pct}%`, ta.t3.bom.hm, `${ta.t3.bom.pct}%`, ta.fimAno.bom.hm, `${ta.fimAno.bom.pct}%`]);
    rows.push(['Muito Bom (17 a 18 valores)', ta.t1.muitoBom.hm, `${ta.t1.muitoBom.pct}%`, ta.t2.muitoBom.hm, `${ta.t2.muitoBom.pct}%`, ta.t3.muitoBom.hm, `${ta.t3.muitoBom.pct}%`, ta.fimAno.muitoBom.hm, `${ta.fimAno.muitoBom.pct}%`]);
    rows.push(['Excelente (19 a 20 valores)', ta.t1.excelente.hm, `${ta.t1.excelente.pct}%`, ta.t2.excelente.hm, `${ta.t2.excelente.pct}%`, ta.t3.excelente.hm, `${ta.t3.excelente.pct}%`, ta.fimAno.excelente.hm, `${ta.fimAno.excelente.pct}%`]);
    rows.push(['TOTAL APROVADOS', ta.t1.aprovados.hm, `${ta.t1.aprovados.pct}%`, ta.t2.aprovados.hm, `${ta.t2.aprovados.pct}%`, ta.t3.aprovados.hm, `${ta.t3.aprovados.pct}%`, ta.fimAno.aprovados.hm, `${ta.fimAno.aprovados.pct}%`]);
    rows.push(['TOTAL REPROVADOS', ta.t1.reprovados.hm, `${ta.t1.reprovados.pct}%`, ta.t2.reprovados.hm, `${ta.t2.reprovados.pct}%`, ta.t3.reprovados.hm, `${ta.t3.reprovados.pct}%`, ta.fimAno.reprovados.hm, `${ta.fimAno.reprovados.pct}%`]);
    rows.push([]);

    rows.push(['TABELA 3: ESTATÍSTICA DE APROVEITAMENTO POR DISCIPLINA']);
    rows.push(['DISCIPLINA', '[0 - 9]', '[10 - 13]', '[14 - 16]', '[17 - 18]', '[19 - 20]', 'AVALIADOS', 'POSITIVAS', '% POSITIVAS', 'NEGATIVAS', '% NEGATIVAS']);
    dados.disciplinas.forEach(d => {
      rows.push([
        d.nome,
        d.faixa0_9.hm,
        d.faixa10_13.hm,
        d.faixa14_16.hm,
        d.faixa17_18.hm,
        d.faixa19_20.hm,
        d.avaliados.hm,
        d.positivas.hm,
        `${d.positivas.pct}%`,
        d.negativas.hm,
        `${d.negativas.pct}%`
      ]);
    });

    const ws = XLSX.utils.aoa_to_sheet(rows);
    XLSX.utils.book_append_sheet(wb, ws, 'Acta do Conselho');
    return XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
  }
}

