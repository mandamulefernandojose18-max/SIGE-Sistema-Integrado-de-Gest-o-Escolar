import PDFDocument from 'pdfkit';
import fs from 'fs';
import path from 'path';

/**
 * Converte stream de PDFKit em Buffer
 */
function pdfDocToBuffer(doc: PDFKit.PDFDocument): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    doc.on('data', (chunk: Buffer) => chunks.push(chunk));
    doc.on('end', () => resolve(Buffer.concat(chunks)));
    doc.on('error', (err: Error) => reject(err));
  });
}

/**
 * Obtém o buffer da imagem do logotipo da escola ou fallback para o emblema nacional oficial
 */
function obterBufferLogotipo(logoBase64OuUrl?: string | null): Buffer | null {
  if (logoBase64OuUrl) {
    try {
      if (logoBase64OuUrl.startsWith('data:image')) {
        const parts = logoBase64OuUrl.split(',');
        if (parts.length > 1) {
          return Buffer.from(parts[1], 'base64');
        }
      } else if (/^[A-Za-z0-9+/=]+$/.test(logoBase64OuUrl.trim()) && logoBase64OuUrl.length > 100) {
        return Buffer.from(logoBase64OuUrl.trim(), 'base64');
      }
    } catch (e) {
      console.warn('Aviso: Erro ao descodificar logotipo base64 da escola:', e);
    }
  }

  // Fallback para o emblema nacional oficial de Moçambique
  try {
    const locais = [
      path.join(__dirname, '../../public/img/emblema-mocambique.png'),
      path.join(__dirname, '../public/img/emblema-mocambique.png'),
      path.join(process.cwd(), 'src/public/img/emblema-mocambique.png'),
      path.join(process.cwd(), 'dist/public/img/emblema-mocambique.png')
    ];
    for (const loc of locais) {
      if (fs.existsSync(loc)) {
        return fs.readFileSync(loc);
      }
    }
  } catch (_) {}

  return null;
}

export interface EscolaCabecalhoDoc {
  nome: string;
  provincia?: string | null;
  distrito?: string | null;
  codigo_escola?: string | null;
  logo_base64?: string | null;
  logo_url?: string | null;
  telefone?: string | null;
  email?: string | null;
}

/**
 * Utilitário de cabeçalho oficial de Moçambique com logotipo oficial preservado
 */
function desenharCabecalhoOficial(
  doc: PDFKit.PDFDocument,
  escola: EscolaCabecalhoDoc
) {
  const logoBuf = obterBufferLogotipo(escola.logo_base64 || escola.logo_url);
  const startY = doc.y;

  if (logoBuf) {
    try {
      const logoWidth = 42;
      const logoHeight = 42;
      const logoX = (doc.page.width - logoWidth) / 2;
      doc.image(logoBuf, logoX, startY, { fit: [logoWidth, logoHeight], align: 'center' });
      doc.y = startY + logoHeight + 6;
    } catch (err) {
      console.warn('Aviso: Não foi possível estampar o logotipo no documento PDF:', err);
      doc.y = startY;
    }
  }

  const prov = (escola.provincia || 'Maputo').toUpperCase();
  const dist = (escola.distrito || 'Cidade de Maputo').toUpperCase();
  const nomeEscola = (escola.nome || 'Escola Secundária').toUpperCase();

  doc
    .fontSize(10)
    .font('Helvetica-Bold')
    .text('REPÚBLICA DE MOÇAMBIQUE', { align: 'center' })
    .fontSize(8)
    .font('Helvetica')
    .text(`GOVERNO DA PROVÍNCIA DE ${prov}`, { align: 'center' })
    .text(`SERVIÇO DISTRITAL DE EDUCAÇÃO, JUVENTUDE E TECNOLOGIA DE ${dist}`, { align: 'center' })
    .fontSize(11)
    .font('Helvetica-Bold')
    .text(nomeEscola, { align: 'center' });

  if (escola.codigo_escola) {
    doc.fontSize(7).font('Helvetica').text(`Código da Instituição: ${escola.codigo_escola}`, { align: 'center' });
  }

  doc.moveDown(0.5);
  doc.strokeColor('#2B3A42').lineWidth(1).moveTo(40, doc.y).lineTo(doc.page.width - 40, doc.y).stroke();
  doc.moveDown(0.8);
}

export class PdfKitDocumentosService {
  /**
   * Recibo Oficial de Pagamento emitido no ato da liquidação
   */
  static async gerarReciboPdf(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null; codigo_escola?: string | null; telefone?: string | null; email?: string | null };
    pagamento: {
      id: string;
      recibo_numero?: string | null;
      descricao: string;
      mes_referencia: string;
      valor: number;
      valor_pago?: number | null;
      metodo_pagamento?: string | null;
      data_pagamento?: Date | string | null;
      status: string;
    };
    aluno: {
      id: string;
      nome: string;
      matricula?: string | null;
      turma?: { nome: string; grau_ano: string } | null;
      nuit?: string | null;
      numero_documento?: string | null;
    };
    operador?: string;
  }): Promise<Buffer> {
    const doc = new PDFDocument({ size: 'A4', margin: 40 });
    desenharCabecalhoOficial(doc, dados.escola);

    const numRecibo = dados.pagamento.recibo_numero || `REC-${new Date().getFullYear()}-${dados.pagamento.id.substring(0, 8).toUpperCase()}`;
    const dataPag = dados.pagamento.data_pagamento ? new Date(dados.pagamento.data_pagamento).toLocaleDateString('pt-PT') : new Date().toLocaleDateString('pt-PT');
    const valorPago = Number(dados.pagamento.valor_pago || dados.pagamento.valor || 0);

    doc.fontSize(13).font('Helvetica-Bold').text('RECIBO OFICIAL DE PAGAMENTO', { align: 'center' });
    doc.fontSize(9).font('Helvetica').text(`Nº DE SÉRIE: ${numRecibo}`, { align: 'center' });
    doc.moveDown(0.8);

    // Caixa de Dados
    const startY = doc.y;
    doc.rect(40, startY, doc.page.width - 80, 85).strokeColor('#CCCCCC').lineWidth(0.5).stroke();

    doc.fontSize(8.5).font('Helvetica-Bold').fillColor('#000000');
    doc.text(`Aluno(a): `, 50, startY + 10, { continued: true }).font('Helvetica').text(dados.aluno.nome.toUpperCase());
    doc.font('Helvetica-Bold').text(`Nº Matrícula: `, 50, startY + 25, { continued: true }).font('Helvetica').text(dados.aluno.matricula || 'N/A');
    doc.font('Helvetica-Bold').text(`Turma / Classe: `, 50, startY + 40, { continued: true }).font('Helvetica').text(dados.aluno.turma?.nome || dados.aluno.turma?.grau_ano || 'Geral');
    doc.font('Helvetica-Bold').text(`Documento / NUIT: `, 50, startY + 55, { continued: true }).font('Helvetica').text(`${dados.aluno.numero_documento || '---'} | NUIT: ${dados.aluno.nuit || '---'}`);

    doc.font('Helvetica-Bold').text(`Data de Emissão: `, 340, startY + 10, { continued: true }).font('Helvetica').text(dataPag);
    doc.font('Helvetica-Bold').text(`Mês / Período: `, 340, startY + 25, { continued: true }).font('Helvetica').text(dados.pagamento.mes_referencia || 'Anual');
    doc.font('Helvetica-Bold').text(`Método: `, 340, startY + 40, { continued: true }).font('Helvetica').text(dados.pagamento.metodo_pagamento || 'NUMERARIO');
    doc.font('Helvetica-Bold').text(`Situação: `, 340, startY + 55, { continued: true }).font('Helvetica-Bold').fillColor('#006600').text('LIQUIDADO / PAGO');
    doc.fillColor('#000000');

    doc.y = startY + 95;
    doc.moveDown(0.5);

    // Tabela do Pagamento
    const tableTop = doc.y;
    doc.rect(40, tableTop, doc.page.width - 80, 20).fillColor('#F0F0F0').fill();
    doc.fillColor('#000000').fontSize(8.5).font('Helvetica-Bold');
    doc.text('DESCRIÇÃO DO CONCEITO / SERVIÇO', 50, tableTop + 5);
    doc.text('MÊS REF.', 320, tableTop + 5);
    doc.text('VALOR TOTAL (MT)', 430, tableTop + 5, { width: 120, align: 'right' });

    doc.strokeColor('#CCCCCC').lineWidth(0.5).rect(40, tableTop, doc.page.width - 80, 45).stroke();
    doc.fontSize(8.5).font('Helvetica');
    doc.text(dados.pagamento.descricao, 50, tableTop + 26);
    doc.text(dados.pagamento.mes_referencia || '2026', 320, tableTop + 26);
    doc.font('Helvetica-Bold').text(`${valorPago.toFixed(2)} MT`, 430, tableTop + 26, { width: 120, align: 'right' });

    // Total Líquido
    const totalTop = tableTop + 50;
    doc.rect(300, totalTop, doc.page.width - 340, 25).strokeColor('#000000').lineWidth(1).stroke();
    doc.fontSize(9.5).font('Helvetica-Bold').text('TOTAL LIQUIDADO:', 310, totalTop + 7);
    doc.fontSize(10).font('Helvetica-Bold').text(`${valorPago.toFixed(2)} MT`, 430, totalTop + 7, { width: 120, align: 'right' });

    doc.y = totalTop + 45;
    doc.fontSize(8).font('Helvetica-Oblique').text(`Operador responsável pela emissão: ${dados.operador || 'Secretaria Geral'}. Documento processado por computador, válido sem rasuras.`, 40, doc.y, { align: 'center' });

    doc.moveDown(3);
    const sigY = doc.y;
    doc.strokeColor('#555555').lineWidth(0.8).moveTo(80, sigY).lineTo(250, sigY).stroke();
    doc.strokeColor('#555555').lineWidth(0.8).moveTo(340, sigY).lineTo(510, sigY).stroke();

    doc.fontSize(8).font('Helvetica-Bold');
    doc.text('O Encarregado / Aluno', 80, sigY + 5, { width: 170, align: 'center' });
    doc.text('A Tesouraria / Secretaria', 340, sigY + 5, { width: 170, align: 'center' });

    doc.end();
    return pdfDocToBuffer(doc);
  }

  /**
   * Boletim Escolar Trimestral / Anual do Aluno (MINEDH)
   */
  static async gerarBoletimPdf(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null; codigo_escola?: string | null };
    anoLetivo: string;
    periodo?: string;
    aluno: {
      id: string;
      nome: string;
      matricula?: string | null;
      turma?: { nome: string; grau_ano: string; turno?: string } | null;
    };
    disciplinas: Array<{
      id: string;
      nome: string;
      codigo: string;
      t1?: number | null;
      t2?: number | null;
      t3?: number | null;
      mfd?: number | null;
      anotacao?: string | null;
    }>;
    medias: {
      t1?: number | null;
      t2?: number | null;
      t3?: number | null;
      mfd?: number | null;
    };
    resultadoFinal?: string;
    observacao?: string;
  }): Promise<Buffer> {
    const doc = new PDFDocument({ size: 'A4', margin: 40 });
    desenharCabecalhoOficial(doc, dados.escola);

    doc.fontSize(12).font('Helvetica-Bold').text(`BOLETIM DE APROVEITAMENTO ESCOLAR — ANO LECTIVO ${dados.anoLetivo}`, { align: 'center' });
    doc.moveDown(0.6);

    // Cabeçalho de dados do aluno
    const boxY = doc.y;
    doc.rect(40, boxY, doc.page.width - 80, 45).strokeColor('#CCCCCC').lineWidth(0.5).stroke();
    doc.fontSize(8.5).font('Helvetica-Bold').fillColor('#000000');
    doc.text(`Nome do Aluno: `, 50, boxY + 8, { continued: true }).font('Helvetica').text(dados.aluno.nome.toUpperCase());
    doc.font('Helvetica-Bold').text(`Nº Matrícula: `, 50, boxY + 25, { continued: true }).font('Helvetica').text(dados.aluno.matricula || '---');
    doc.font('Helvetica-Bold').text(`Classe / Turma: `, 320, boxY + 8, { continued: true }).font('Helvetica').text(`${dados.aluno.turma?.grau_ano || ''} - ${dados.aluno.turma?.nome || ''}`);
    doc.font('Helvetica-Bold').text(`Turno: `, 320, boxY + 25, { continued: true }).font('Helvetica').text(dados.aluno.turma?.turno || 'Manhã');

    doc.y = boxY + 55;
    doc.moveDown(0.3);

    // Cabeçalho da Tabela
    const startTableY = doc.y;
    const colX = [40, 230, 290, 350, 410, 480, doc.page.width - 40];
    const rowHeight = 18;

    doc.rect(40, startTableY, doc.page.width - 80, rowHeight).fillColor('#EAEAEA').fill();
    doc.fillColor('#000000').fontSize(8).font('Helvetica-Bold');
    doc.text('DISCIPLINA', colX[0] + 5, startTableY + 5);
    doc.text('1º TRIM', colX[1] + 5, startTableY + 5, { width: 55, align: 'center' });
    doc.text('2º TRIM', colX[2] + 5, startTableY + 5, { width: 55, align: 'center' });
    doc.text('3º TRIM', colX[3] + 5, startTableY + 5, { width: 55, align: 'center' });
    doc.text('MÉD. ANUAL', colX[4] + 5, startTableY + 5, { width: 65, align: 'center' });
    doc.text('SITUAÇÃO', colX[5] + 5, startTableY + 5, { width: 70, align: 'center' });

    let currentY = startTableY + rowHeight;
    doc.font('Helvetica').fontSize(8);

    dados.disciplinas.forEach((disc, index) => {
      if (index % 2 === 1) {
        doc.rect(40, currentY, doc.page.width - 80, rowHeight).fillColor('#F9F9F9').fill();
      }
      doc.strokeColor('#DDDDDD').lineWidth(0.5).rect(40, currentY, doc.page.width - 80, rowHeight).stroke();
      doc.fillColor('#000000');

      doc.text(disc.nome, colX[0] + 5, currentY + 5);

      const fmtNota = (val?: number | null) => (val !== null && val !== undefined && val > 0) ? String(val) : '---';
      doc.text(fmtNota(disc.t1), colX[1] + 5, currentY + 5, { width: 55, align: 'center' });
      doc.text(fmtNota(disc.t2), colX[2] + 5, currentY + 5, { width: 55, align: 'center' });
      doc.text(fmtNota(disc.t3), colX[3] + 5, currentY + 5, { width: 55, align: 'center' });

      // Média final da disciplina
      const mfd = disc.mfd !== null && disc.mfd !== undefined && disc.mfd > 0 ? String(disc.mfd) : '---';
      if (disc.mfd !== null && disc.mfd !== undefined && disc.mfd > 0 && disc.mfd < 9.5) {
        doc.fillColor('#B91C1C').font('Helvetica-Bold');
      }
      doc.text(mfd, colX[4] + 5, currentY + 5, { width: 65, align: 'center' });
      doc.fillColor('#000000').font('Helvetica');

      // Situação
      const sit = disc.anotacao || (disc.mfd !== null && disc.mfd !== undefined && disc.mfd >= 9.5 ? 'Aprovado' : (disc.mfd ? 'Reprovado' : '---'));
      doc.text(sit, colX[5] + 5, currentY + 5, { width: 70, align: 'center' });

      currentY += rowHeight;
    });

    // Linha de Médias Globais
    doc.rect(40, currentY, doc.page.width - 80, rowHeight).fillColor('#E5E7EB').fill();
    doc.strokeColor('#999999').lineWidth(0.8).rect(40, currentY, doc.page.width - 80, rowHeight).stroke();
    doc.fillColor('#000000').font('Helvetica-Bold').fontSize(8);
    doc.text('MÉDIA GLOBAL DO PERÍODO', colX[0] + 5, currentY + 5);

    const fmtMed = (val?: number | null) => (val !== null && val !== undefined && val > 0) ? String(val) : '---';
    doc.text(fmtMed(dados.medias.t1), colX[1] + 5, currentY + 5, { width: 55, align: 'center' });
    doc.text(fmtMed(dados.medias.t2), colX[2] + 5, currentY + 5, { width: 55, align: 'center' });
    doc.text(fmtMed(dados.medias.t3), colX[3] + 5, currentY + 5, { width: 55, align: 'center' });
    doc.text(fmtMed(dados.medias.mfd), colX[4] + 5, currentY + 5, { width: 65, align: 'center' });

    const finalRes = dados.resultadoFinal || (dados.medias.mfd && dados.medias.mfd >= 9.5 ? 'Aprovado' : 'Em Avaliação');
    doc.text(finalRes, colX[5] + 5, currentY + 5, { width: 70, align: 'center' });

    currentY += rowHeight + 15;
    doc.y = currentY;

    // Resumo de Avaliação
    doc.fontSize(8.5).font('Helvetica-Bold').text(`Decisão do Conselho: `, 40, doc.y, { continued: true }).font('Helvetica').text(dados.observacao || `O aluno obteve o resultado de ${finalRes}. Conforme regulamento MINEDH, corte mínimo é de 9.5 valores.`);

    // Assinaturas
    doc.moveDown(3);
    const sigY = doc.y;
    doc.strokeColor('#555555').lineWidth(0.8).moveTo(60, sigY).lineTo(220, sigY).stroke();
    doc.strokeColor('#555555').lineWidth(0.8).moveTo(330, sigY).lineTo(490, sigY).stroke();

    doc.fontSize(8).font('Helvetica-Bold');
    doc.text('O Director de Turma', 60, sigY + 5, { width: 160, align: 'center' });
    doc.text('O Director da Escola', 330, sigY + 5, { width: 160, align: 'center' });

    doc.end();
    return pdfDocToBuffer(doc);
  }

  /**
   * Declaração Escolar com ou sem notas (MINEDH)
   */
  static async gerarDeclaracaoPdf(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null; codigo_escola?: string | null };
    aluno: {
      nome: string;
      apelido?: string | null;
      matricula?: string | null;
      numero_documento?: string | null;
      tipo_documento?: string | null;
      data_nascimento?: Date | string | null;
      naturalidade?: string | null;
      pai?: string | null;
      mae?: string | null;
      turma?: { nome: string; grau_ano: string } | null;
    };
    anoLectivo: string;
    comNotas?: boolean;
    disciplinas?: Array<{ nome: string; mfd?: number | null }>;
    mediaFinal?: number;
    resultadoFinal?: string;
  }): Promise<Buffer> {
    const doc = new PDFDocument({ size: 'A4', margin: 45 });
    desenharCabecalhoOficial(doc, dados.escola);

    doc.fontSize(13).font('Helvetica-Bold').text('DECLARAÇÃO COM NOTAS', { align: 'center' });
    doc.moveDown(1.5);

    const nomeCompleto = `${dados.aluno.nome} ${dados.aluno.apelido || ''}`.trim().toUpperCase();
    const docTipo = dados.aluno.tipo_documento || 'B.I.';
    const docNum = dados.aluno.numero_documento || '---';
    const filiacao = dados.aluno.pai && dados.aluno.mae ? `filho(a) de ${dados.aluno.pai} e de ${dados.aluno.mae}` : '';
    const classe = dados.aluno.turma?.grau_ano || 'Ensino Secundário';

    const textoDeclaracao = `Para os devidos efeitos se declara que ${nomeCompleto}, ${filiacao}, portador(a) do ${docTipo} nº ${docNum}, esteve matriculado(a) nesta instituição de ensino no Ano Lectivo de ${dados.anoLectivo}, frequentando a ${classe}, tendo obtido o seguinte aproveitamento pedagógico:`;

    doc.fontSize(9.5).font('Helvetica').lineGap(3).text(textoDeclaracao, 45, doc.y, { align: 'justify' });
    doc.moveDown(1);

    if (dados.comNotas && dados.disciplinas && dados.disciplinas.length > 0) {
      const tableTop = doc.y;
      doc.rect(45, tableTop, doc.page.width - 90, 18).fillColor('#EAEAEA').fill();
      doc.fillColor('#000000').fontSize(8.5).font('Helvetica-Bold');
      doc.text('DISCIPLINA CURRICULAR', 55, tableTop + 5);
      doc.text('CLASSIFICAÇÃO FINAL (0-20)', 360, tableTop + 5, { width: 140, align: 'center' });

      let curY = tableTop + 18;
      dados.disciplinas.forEach((d, i) => {
        if (i % 2 === 1) doc.rect(45, curY, doc.page.width - 90, 16).fillColor('#F9F9F9').fill();
        doc.strokeColor('#DDDDDD').lineWidth(0.5).rect(45, curY, doc.page.width - 90, 16).stroke();
        doc.fillColor('#000000').fontSize(8).font('Helvetica');
        doc.text(d.nome, 55, curY + 4);
        const notaStr = d.mfd !== null && d.mfd !== undefined ? `${d.mfd} Valores` : '---';
        doc.text(notaStr, 360, curY + 4, { width: 140, align: 'center' });
        curY += 16;
      });

      doc.y = curY + 10;
      doc.fontSize(9).font('Helvetica-Bold').text(`Média Final Global: ${dados.mediaFinal ? `${dados.mediaFinal} Valores` : '---'} | Resultado: ${dados.resultadoFinal || 'Aprovado'}`);
    }

    doc.moveDown(1.5);
    const dataExtenso = `${dados.escola.distrito || 'Maputo'}, aos ${new Date().getDate()} de ${new Date().toLocaleString('pt-PT', { month: 'long' })} de ${new Date().getFullYear()}.`;
    doc.fontSize(9).font('Helvetica').text(dataExtenso, { align: 'right' });

    doc.moveDown(3);
    const sigY = doc.y;
    doc.strokeColor('#555555').lineWidth(0.8).moveTo(80, sigY).lineTo(240, sigY).stroke();
    doc.strokeColor('#555555').lineWidth(0.8).moveTo(310, sigY).lineTo(470, sigY).stroke();

    doc.fontSize(8).font('Helvetica-Bold');
    doc.text('O Chefe da Secretaria', 80, sigY + 5, { width: 160, align: 'center' });
    doc.text('O Director da Escola', 310, sigY + 5, { width: 160, align: 'center' });

    doc.end();
    return pdfDocToBuffer(doc);
  }

  /**
   * Pauta Oficial Geral da Turma (Paisagem / Landscape)
   */
  static async gerarPautaPdf(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null; codigo_escola?: string | null };
    turma: { nome: string; grau_ano: string; turno?: string; ano_letivo: string; director_turma?: string };
    disciplinas: Array<{ id: string; nome: string; codigo: string }>;
    alunos: Array<{
      numero: number;
      matricula: string;
      nome: string;
      genero: string;
      mediasTrimestrais: { t1?: number | null; t2?: number | null; t3?: number | null };
      mediaFinalGeral: number;
      resultadoFinal: string;
    }>;
    estatistica?: any;
  }): Promise<Buffer> {
    const doc = new PDFDocument({ size: 'A4', layout: 'landscape', margin: 30 });
    desenharCabecalhoOficial(doc, dados.escola);

    doc.fontSize(11).font('Helvetica-Bold').text(`PAUTA OFICIAL DE AVALIAÇÃO — ${dados.turma.grau_ano} ${dados.turma.nome} — ANO LECTIVO ${dados.turma.ano_letivo}`, { align: 'center' });
    doc.moveDown(0.5);

    const startY = doc.y;
    const colW = { num: 25, mat: 60, nome: 220, gen: 30, t1: 45, t2: 45, t3: 45, mfd: 50, res: 60 };
    const rowH = 15;

    // Cabeçalho da Tabela
    doc.rect(30, startY, doc.page.width - 60, rowH).fillColor('#E5E7EB').fill();
    doc.fillColor('#000000').fontSize(7.5).font('Helvetica-Bold');
    doc.text('Nº', 35, startY + 4, { width: colW.num });
    doc.text('MATRÍCULA', 60, startY + 4, { width: colW.mat });
    doc.text('NOME COMPLETO DO ALUNO', 125, startY + 4, { width: colW.nome });
    doc.text('SEXO', 350, startY + 4, { width: colW.gen, align: 'center' });
    doc.text('1º TRIM', 385, startY + 4, { width: colW.t1, align: 'center' });
    doc.text('2º TRIM', 435, startY + 4, { width: colW.t2, align: 'center' });
    doc.text('3º TRIM', 485, startY + 4, { width: colW.t3, align: 'center' });
    doc.text('MÉD. FINAL', 535, startY + 4, { width: colW.mfd, align: 'center' });
    doc.text('RESULTADO', 590, startY + 4, { width: colW.res, align: 'center' });

    let currentY = startY + rowH;

    dados.alunos.forEach((aluno, i) => {
      // Nova página caso passe da margem inferior
      if (currentY > doc.page.height - 70) {
        doc.addPage({ size: 'A4', layout: 'landscape', margin: 30 });
        desenharCabecalhoOficial(doc, dados.escola);
        currentY = doc.y + 10;
      }

      if (i % 2 === 1) doc.rect(30, currentY, doc.page.width - 60, rowH).fillColor('#F9FAFB').fill();
      doc.strokeColor('#E5E7EB').lineWidth(0.5).rect(30, currentY, doc.page.width - 60, rowH).stroke();
      doc.fillColor('#000000').fontSize(7).font('Helvetica');

      doc.text(String(aluno.numero), 35, currentY + 4, { width: colW.num });
      doc.text(aluno.matricula, 60, currentY + 4, { width: colW.mat });
      doc.text(aluno.nome.toUpperCase(), 125, currentY + 4, { width: colW.nome });
      doc.text(aluno.genero || 'M', 350, currentY + 4, { width: colW.gen, align: 'center' });

      const fmt = (v?: number | null) => (v !== null && v !== undefined && v > 0) ? String(v) : '-';
      doc.text(fmt(aluno.mediasTrimestrais.t1), 385, currentY + 4, { width: colW.t1, align: 'center' });
      doc.text(fmt(aluno.mediasTrimestrais.t2), 435, currentY + 4, { width: colW.t2, align: 'center' });
      doc.text(fmt(aluno.mediasTrimestrais.t3), 485, currentY + 4, { width: colW.t3, align: 'center' });

      const mfdVal = aluno.mediaFinalGeral > 0 ? String(aluno.mediaFinalGeral) : '-';
      doc.font('Helvetica-Bold').text(mfdVal, 535, currentY + 4, { width: colW.mfd, align: 'center' });

      const resColor = aluno.resultadoFinal === 'A' ? '#059669' : (aluno.resultadoFinal === 'R' ? '#DC2626' : '#111827');
      doc.fillColor(resColor).text(aluno.resultadoFinal === 'A' ? 'Aprovado' : (aluno.resultadoFinal === 'R' ? 'Reprovado' : aluno.resultadoFinal), 590, currentY + 4, { width: colW.res, align: 'center' });
      doc.fillColor('#000000');

      currentY += rowH;
    });

    // Assinaturas no rodapé
    doc.y = currentY + 20;
    const sigY = doc.y;
    doc.strokeColor('#555555').lineWidth(0.8).moveTo(100, sigY).lineTo(280, sigY).stroke();
    doc.strokeColor('#555555').lineWidth(0.8).moveTo(340, sigY).lineTo(520, sigY).stroke();
    doc.strokeColor('#555555').lineWidth(0.8).moveTo(570, sigY).lineTo(750, sigY).stroke();

    doc.fontSize(7.5).font('Helvetica-Bold');
    doc.text('O Director de Turma', 100, sigY + 5, { width: 180, align: 'center' });
    doc.text('O Director Pedagógico (DAP)', 340, sigY + 5, { width: 180, align: 'center' });
    doc.text('O Director da Escola', 570, sigY + 5, { width: 180, align: 'center' });

    doc.end();
    return pdfDocToBuffer(doc);
  }

  /**
   * Guia de Transferência Escolar (Classe ---> Área ---> Turma de Destino)
   */
  static async gerarGuiaTransferenciaPdf(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null; codigo_escola?: string | null };
    aluno: {
      nome: string;
      apelido?: string | null;
      matricula?: string | null;
      numero_documento?: string | null;
      tipo_documento?: string | null;
      turma_origem?: { nome: string; grau_ano: string } | null;
    };
    transferencia: {
      classe_destino: string;
      area_destino: string;
      turma_destino?: { nome: string } | null;
      motivo?: string | null;
      autorizado_por?: string | null;
      data_transferencia?: Date | string | null;
    };
  }): Promise<Buffer> {
    const doc = new PDFDocument({ size: 'A4', margin: 45 });
    desenharCabecalhoOficial(doc, dados.escola);

    doc.fontSize(13).font('Helvetica-Bold').text('GUIA OFICIAL DE TRANSFERÊNCIA ESCOLAR', { align: 'center' });
    doc.moveDown(1);

    const nome = `${dados.aluno.nome} ${dados.aluno.apelido || ''}`.trim().toUpperCase();
    const docInfo = `${dados.aluno.tipo_documento || 'B.I.'} nº ${dados.aluno.numero_documento || '---'}`;
    const dt = dados.transferencia.data_transferencia ? new Date(dados.transferencia.data_transferencia).toLocaleDateString('pt-PT') : new Date().toLocaleDateString('pt-PT');

    const texto = `Certifica-se que o(a) aluno(a) ${nome}, portador(a) do documento ${docInfo}, com a matrícula nº ${dados.aluno.matricula || '---'}, frequente na ${dados.aluno.turma_origem?.grau_ano || 'classe anterior'} (${dados.aluno.turma_origem?.nome || 'Turma de Origem'}), foi devidamente transferido(a) para:

• Classe de Destino: ${dados.transferencia.classe_destino}
• Área Curricular / Especialidade: ${dados.transferencia.area_destino}
• Turma de Destino: ${dados.transferencia.turma_destino?.nome || 'A definir pela Secretaria'}
• Motivo da Transferência: ${dados.transferencia.motivo || 'A pedido do Encarregado de Educação'}
• Autorizado Por: ${dados.transferencia.autorizado_por || 'Direcção da Escola'}
• Data de Efectivação: ${dt}

Por ser verdade e ter sido deferido pela Direcção da Instituição, passa-se a presente Guia de Transferência que vai autenticada com o carimbo em uso nesta escola.`;

    doc.fontSize(9.5).font('Helvetica').lineGap(3).text(texto, 45, doc.y, { align: 'justify' });

    doc.moveDown(4);
    const sigY = doc.y;
    doc.strokeColor('#555555').lineWidth(0.8).moveTo(80, sigY).lineTo(240, sigY).stroke();
    doc.strokeColor('#555555').lineWidth(0.8).moveTo(310, sigY).lineTo(470, sigY).stroke();

    doc.fontSize(8).font('Helvetica-Bold');
    doc.text('O Chefe da Secretaria', 80, sigY + 5, { width: 160, align: 'center' });
    doc.text('O Director da Escola', 310, sigY + 5, { width: 160, align: 'center' });

    doc.end();
    return pdfDocToBuffer(doc);
  }

  /**
   * Acta do Conselho de Avaliação com campos opcionais e trimestres condicionados
   */
  static async gerarActaPdf(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null; codigo_escola?: string | null };
    turma: { nome: string; grau_ano: string; ano_letivo: string; director_turma?: string };
    conselho: {
      data?: string;
      prazo?: string;
      director_turma?: string;
      horaInicio?: string;
      horaFim?: string;
      presidente?: string;
      secretario?: string;
    };
    trimestresComNotas: { t1: boolean; t2: boolean; t3: boolean; fimAno: boolean };
    estatisticaEfectivo?: any;
    estatisticaAproveitamento?: any;
    disciplinas?: any[];
  }): Promise<Buffer> {
    const doc = new PDFDocument({ size: 'A4', margin: 40 });
    desenharCabecalhoOficial(doc, dados.escola);

    doc.fontSize(12).font('Helvetica-Bold').text(`ACTA DA SESSÃO DO CONSELHO DE AVALIAÇÃO`, { align: 'center' });
    doc.fontSize(9.5).font('Helvetica').text(`Turma: ${dados.turma.grau_ano} ${dados.turma.nome} — Ano Lectivo ${dados.turma.ano_letivo}`, { align: 'center' });
    doc.moveDown(0.8);

    const dt = dados.conselho.data || '___/___/2026';
    const dirTurma = dados.conselho.director_turma || dados.turma.director_turma || '____________________';
    const prazo = dados.conselho.prazo ? `Prazo de homologação: ${dados.conselho.prazo}.` : '';

    const preambulo = `Aos ${dt}, reuniu-se em sessão ordinária o Conselho de Avaliação da turma ${dados.turma.grau_ano} ${dados.turma.nome}, sob a direcção de ${dirTurma}, com a ordem de trabalhos de analisar o aproveitamento pedagógico e deliberar sobre as classificações dos estudantes. ${prazo}`;

    doc.fontSize(8.5).font('Helvetica').lineGap(2).text(preambulo, 40, doc.y, { align: 'justify' });
    doc.moveDown(0.8);

    // Condicionamento Trimestral: apenas exibe blocos que possuam notas lançadas
    const { t1, t2, t3, fimAno } = dados.trimestresComNotas;

    if (t1 && dados.estatisticaAproveitamento?.t1) {
      doc.fontSize(9.5).font('Helvetica-Bold').text('1. Síntese do 1º Trimestre:');
      const apr = dados.estatisticaAproveitamento.t1;
      doc.fontSize(8).font('Helvetica').text(`• Aprovados: ${apr.aprovados?.hm || 0} (${apr.aprovados?.pct || 0}%) | Reprovados: ${apr.reprovados?.hm || 0} (${apr.reprovados?.pct || 0}%)`);
      doc.moveDown(0.4);
    }

    if (t2 && dados.estatisticaAproveitamento?.t2) {
      doc.fontSize(9.5).font('Helvetica-Bold').text('2. Síntese do 2º Trimestre:');
      const apr = dados.estatisticaAproveitamento.t2;
      doc.fontSize(8).font('Helvetica').text(`• Aprovados: ${apr.aprovados?.hm || 0} (${apr.aprovados?.pct || 0}%) | Reprovados: ${apr.reprovados?.hm || 0} (${apr.reprovados?.pct || 0}%)`);
      doc.moveDown(0.4);
    }

    if (t3 && dados.estatisticaAproveitamento?.t3) {
      doc.fontSize(9.5).font('Helvetica-Bold').text('3. Síntese do 3º Trimestre:');
      const apr = dados.estatisticaAproveitamento.t3;
      doc.fontSize(8).font('Helvetica').text(`• Aprovados: ${apr.aprovados?.hm || 0} (${apr.aprovados?.pct || 0}%) | Reprovados: ${apr.reprovados?.hm || 0} (${apr.reprovados?.pct || 0}%)`);
      doc.moveDown(0.4);
    }

    if (!t1 && !t2 && !t3) {
      doc.fontSize(8.5).font('Helvetica-Oblique').fillColor('#666666').text('Nenhum trimestre com notas consolidadas até ao momento.');
      doc.fillColor('#000000');
    }

    doc.moveDown(1);
    doc.fontSize(8.5).font('Helvetica').text('Nada mais havendo a tratar, deu-se por encerrada a sessão da qual se lavrou a presente acta.', { align: 'justify' });

    doc.moveDown(3);
    const sigY = doc.y;
    doc.strokeColor('#555555').lineWidth(0.8).moveTo(60, sigY).lineTo(220, sigY).stroke();
    doc.strokeColor('#555555').lineWidth(0.8).moveTo(330, sigY).lineTo(490, sigY).stroke();

    doc.fontSize(8).font('Helvetica-Bold');
    doc.text('O Director de Turma / Presidente', 60, sigY + 5, { width: 160, align: 'center' });
    doc.text('O Director da Escola', 330, sigY + 5, { width: 160, align: 'center' });

    doc.end();
    return pdfDocToBuffer(doc);
  }
}
