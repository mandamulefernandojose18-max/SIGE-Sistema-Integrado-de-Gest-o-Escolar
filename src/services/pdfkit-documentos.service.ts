import PDFDocument from 'pdfkit';
import fs from 'fs';
import path from 'path';
import QRCode from 'qrcode';

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
 * Obtém estritamente o buffer do emblema nacional oficial da República de Moçambique
 */
function obterBufferEmblemaNacional(): Buffer | null {
  try {
    const locais = [
      path.join(__dirname, '../../public/img/emblema-mocambique.png'),
      path.join(__dirname, '../public/img/emblema-mocambique.png'),
      path.join(process.cwd(), 'src/public/img/emblema-mocambique.png'),
      path.join(process.cwd(), 'dist/public/img/emblema-mocambique.png'),
      path.join(process.cwd(), 'sige-frontend/img/emblema-mocambique.png')
    ];
    for (const loc of locais) {
      if (fs.existsSync(loc)) {
        return fs.readFileSync(loc);
      }
    }
  } catch (_) {}
  return null;
}

/**
 * Obtém o buffer da imagem do logotipo da escola ou fallback para o emblema nacional oficial
 */
function obterBufferLogotipo(logoBase64OuUrl?: string | null): Buffer | null {
  if (logoBase64OuUrl && logoBase64OuUrl.trim()) {
    try {
      let buf: Buffer | null = null;
      const trimmed = logoBase64OuUrl.trim();
      if (trimmed.startsWith('data:image')) {
        const parts = trimmed.split(',');
        if (parts.length > 1) {
          buf = Buffer.from(parts[1], 'base64');
        }
      } else if (/^[A-Za-z0-9+/=]+$/.test(trimmed) && trimmed.length > 100) {
        buf = Buffer.from(trimmed, 'base64');
      } else if (!trimmed.startsWith('http')) {
        const possiveisLocais = [
          path.resolve(process.cwd(), trimmed.replace(/^\//, '')),
          path.resolve(process.cwd(), 'src/public', trimmed.replace(/^\/?(public\/)?/, '')),
          path.resolve(process.cwd(), 'dist/public', trimmed.replace(/^\/?(public\/)?/, ''))
        ];
        for (const loc of possiveisLocais) {
          if (fs.existsSync(loc)) {
            const fBuf = fs.readFileSync(loc);
            if (fBuf.length > 300) {
              return fBuf;
            }
          }
        }
      }
      // Rejeita placeholders corrompidos ou minúsculos (ex: dummy pixel 1x1 tem ~68 bytes)
      if (buf && buf.length > 300) {
        return buf;
      }
    } catch (e) {
      console.warn('Aviso: Erro ao carregar logotipo da escola:', e);
    }
  }

  return obterBufferEmblemaNacional();
}

/**
 * Desenha marca d'água oficial translúcida do emblema da República no centro da página
 * Preserva sempre o Emblema Oficial da República como filigrana em todos os documentos.
 */
function desenharMarcaDaguaEmblema(doc: PDFKit.PDFDocument, logoBuf?: Buffer | null, tamanho = 200) {
  const emblemaBuf = obterBufferEmblemaNacional() || logoBuf;
  if (!emblemaBuf) return;
  try {
    const w = doc.page.width;
    const h = doc.page.height;
    doc.save();
    doc.opacity(0.06);
    doc.image(emblemaBuf, (w - tamanho) / 2, (h - tamanho) / 2, { fit: [tamanho, tamanho], align: 'center' });
    doc.restore();
  } catch (e) {
    console.warn('Aviso ao estampar marca d água:', e);
  }
}

export interface FragmentoTexto {
  text: string;
  bold?: boolean;
  italic?: boolean;
  underline?: boolean;
  size?: number;
}

/**
 * Renderiza um parágrafo contínuo com segmentos normais e em negrito ("bordados")
 * respeitando alinhamento justificado e espaçamento 1.5 do Word
 */
function renderizarParagrafoFormatado(
  doc: PDFKit.PDFDocument,
  segmentos: FragmentoTexto[],
  x: number,
  largura: number,
  tamanhoBase = 12,
  lineGap = 5.5,
  align: 'justify' | 'center' | 'left' | 'right' = 'justify'
) {
  doc.x = x;
  segmentos.forEach((seg, idx) => {
    const isLast = idx === segmentos.length - 1;
    const fontName = seg.bold ? 'Times-Bold' : (seg.italic ? 'Times-Italic' : 'Times-Roman');
    doc.font(fontName).fontSize(seg.size || tamanhoBase);
    doc.text(seg.text, {
      width: largura,
      align,
      lineGap,
      continued: !isLast,
      underline: !!seg.underline
    });
  });
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
    .font('Times-Bold')
    .text('REPÚBLICA DE MOÇAMBIQUE', { align: 'center' })
    .fontSize(8.5)
    .font('Times-Roman')
    .text(`GOVERNO DA PROVÍNCIA DE ${prov}`, { align: 'center' })
    .text(`SERVIÇO DISTRITAL DE EDUCAÇÃO, JUVENTUDE E TECNOLOGIA DE ${dist}`, { align: 'center' })
    .fontSize(11)
    .font('Times-Bold')
    .text(nomeEscola, { align: 'center' });

  if (escola.codigo_escola) {
    doc.fontSize(7.5).font('Times-Roman').text(`Código da Instituição: ${escola.codigo_escola}`, { align: 'center' });
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
    escola: { nome: string; provincia?: string | null; distrito?: string | null; codigo_escola?: string | null; telefone?: string | null; email?: string | null; logo_base64?: string | null; logo_url?: string | null };
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
    const doc = new PDFDocument({ size: 'A4', margin: 30 });
    const w = doc.page.width;
    const h = doc.page.height;

    // Moldura exterior
    doc.rect(18, 18, w - 36, h - 36).lineWidth(1.2).strokeColor('#222222').stroke();

    // Marca d'água central translúcida
    const logoBuf = obterBufferLogotipo(dados.escola.logo_base64 || dados.escola.logo_url);
    desenharMarcaDaguaEmblema(doc, logoBuf, 190);

    desenharCabecalhoOficial(doc, dados.escola);

    const numRecibo = dados.pagamento.recibo_numero || `REC-${new Date().getFullYear()}-${dados.pagamento.id.substring(0, 8).toUpperCase()}`;
    const dataPag = dados.pagamento.data_pagamento ? new Date(dados.pagamento.data_pagamento).toLocaleDateString('pt-PT') : new Date().toLocaleDateString('pt-PT');
    const valorPago = Number(dados.pagamento.valor_pago || dados.pagamento.valor || 0);

    doc.fontSize(14).font('Times-Bold').text('RECIBO OFICIAL DE PAGAMENTO', { align: 'center' });
    doc.fontSize(10).font('Times-Roman').text(`Nº DE SÉRIE: ${numRecibo}`, { align: 'center' });
    doc.moveDown(0.8);

    // Caixa de Dados
    const startY = doc.y;
    doc.rect(40, startY, doc.page.width - 80, 85).strokeColor('#CCCCCC').lineWidth(0.5).stroke();

    doc.fontSize(9.5).font('Times-Bold').fillColor('#000000');
    doc.text(`Aluno(a): `, 50, startY + 10, { continued: true }).font('Times-Roman').text(dados.aluno.nome.toUpperCase());
    doc.font('Times-Bold').text(`Nº Matrícula: `, 50, startY + 25, { continued: true }).font('Times-Roman').text(dados.aluno.matricula || 'N/A');
    doc.font('Times-Bold').text(`Turma / Classe: `, 50, startY + 40, { continued: true }).font('Times-Roman').text(dados.aluno.turma?.nome || dados.aluno.turma?.grau_ano || 'Geral');
    doc.font('Times-Bold').text(`Documento / NUIT: `, 50, startY + 55, { continued: true }).font('Times-Roman').text(`${dados.aluno.numero_documento || '---'} | NUIT: ${dados.aluno.nuit || '---'}`);

    doc.font('Times-Bold').text(`Data de Emissão: `, 340, startY + 10, { continued: true }).font('Times-Roman').text(dataPag);
    doc.font('Times-Bold').text(`Mês / Período: `, 340, startY + 25, { continued: true }).font('Times-Roman').text(dados.pagamento.mes_referencia || 'Anual');
    doc.font('Times-Bold').text(`Método: `, 340, startY + 40, { continued: true }).font('Times-Roman').text(dados.pagamento.metodo_pagamento || 'NUMERARIO');
    doc.font('Times-Bold').text(`Situação: `, 340, startY + 55, { continued: true }).font('Times-Bold').fillColor('#006600').text('LIQUIDADO / PAGO');
    doc.fillColor('#000000');

    doc.y = startY + 95;
    doc.moveDown(0.5);

    // Tabela do Pagamento
    const tableTop = doc.y;
    doc.rect(40, tableTop, doc.page.width - 80, 20).fillColor('#F0F0F0').fill();
    doc.fillColor('#000000').fontSize(9.5).font('Times-Bold');
    doc.text('DESCRIÇÃO DO CONCEITO / SERVIÇO', 50, tableTop + 5);
    doc.text('MÊS REF.', 320, tableTop + 5);
    doc.text('VALOR TOTAL (MT)', 430, tableTop + 5, { width: 120, align: 'right' });

    doc.strokeColor('#CCCCCC').lineWidth(0.5).rect(40, tableTop, doc.page.width - 80, 45).stroke();
    doc.fontSize(9.5).font('Times-Roman');
    doc.text(dados.pagamento.descricao, 50, tableTop + 26);
    doc.text(dados.pagamento.mes_referencia || '2026', 320, tableTop + 26);
    doc.font('Times-Bold').text(`${valorPago.toFixed(2)} MT`, 430, tableTop + 26, { width: 120, align: 'right' });

    // Total Líquido
    const totalTop = tableTop + 50;
    doc.rect(300, totalTop, doc.page.width - 340, 25).strokeColor('#000000').lineWidth(1).stroke();
    doc.fontSize(10.5).font('Times-Bold').text('TOTAL LIQUIDADO:', 310, totalTop + 7);
    doc.fontSize(11).font('Times-Bold').text(`${valorPago.toFixed(2)} MT`, 430, totalTop + 7, { width: 120, align: 'right' });

    doc.y = totalTop + 45;
    doc.fontSize(8.5).font('Times-Italic').text(`Operador responsável pela emissão: ${dados.operador || 'Secretaria Geral'}. Documento processado por computador, válido sem rasuras.`, 40, doc.y, { align: 'center' });

    doc.moveDown(2.5);
    const sigY = doc.y;
    doc.strokeColor('#555555').lineWidth(0.8).moveTo(80, sigY).lineTo(250, sigY).stroke();
    doc.strokeColor('#555555').lineWidth(0.8).moveTo(340, sigY).lineTo(510, sigY).stroke();

    doc.fontSize(9).font('Times-Bold');
    doc.text('O Encarregado / Aluno', 80, sigY + 5, { width: 170, align: 'center' });
    doc.text('A Tesouraria / Secretaria', 340, sigY + 5, { width: 170, align: 'center' });

    doc.end();
    return pdfDocToBuffer(doc);
  }

  /**
   * Boletim Escolar Trimestral / Anual do Aluno (MINEDH)
   */
  static async gerarBoletimPdf(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null; codigo_escola?: string | null; logo_base64?: string | null; logo_url?: string | null };
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
    const margin = 56.7; // 2 cm em pontos (2 * 28.3465)
    const doc = new PDFDocument({ size: 'A4', margin });
    const w = doc.page.width;
    const h = doc.page.height;
    const contentW = w - (margin * 2);

    // Moldura exterior ornamental oficial
    doc.rect(28, 28, w - 56, h - 56).lineWidth(1.2).strokeColor('#222222').stroke();

    // Marca d'água central translúcida
    const logoBuf = obterBufferLogotipo(dados.escola.logo_base64 || dados.escola.logo_url);
    desenharMarcaDaguaEmblema(doc, logoBuf, 210);

    desenharCabecalhoOficial(doc, dados.escola);

    // Espaçamento obrigatório de 2 cm (56.7 pt) entre o cabeçalho oficial e onde começa a informação
    doc.y += 56.7;

    doc.fontSize(12).font('Times-Bold').text(`BOLETIM DE APROVEITAMENTO ESCOLAR — ANO LECTIVO ${dados.anoLetivo}`, { align: 'center' });
    doc.moveDown(0.6);

    // Cabeçalho de dados do aluno (idêntico à imagem)
    const boxY = doc.y;
    doc.rect(margin, boxY, contentW, 44).strokeColor('#CCCCCC').lineWidth(0.7).stroke();
    doc.fontSize(9.5).font('Times-Bold').fillColor('#000000');
    doc.text(`Nome do Aluno: `, margin + 10, boxY + 8, { continued: true }).font('Times-Bold').text(dados.aluno.nome.toUpperCase());
    doc.font('Times-Bold').text(`Nº Matrícula: `, margin + 10, boxY + 25, { continued: true }).font('Times-Roman').text(dados.aluno.matricula || '---');
    doc.font('Times-Bold').text(`Classe / Turma: `, margin + 260, boxY + 8, { continued: true }).font('Times-Roman').text(`${dados.aluno.turma?.grau_ano || ''} - ${dados.aluno.turma?.nome || ''}`);
    doc.font('Times-Bold').text(`Turno: `, margin + 260, boxY + 25, { continued: true }).font('Times-Roman').text(dados.aluno.turma?.turno || 'Manhã');

    doc.y = boxY + 52;

    // Tabela de Disciplinas e Notas
    const startTableY = doc.y;
    // Colunas somam exatamente contentW (481.88 pt): 176 + 55 + 55 + 55 + 65 + 75.88 = 481.88
    const colX = [
      margin,
      margin + 176,
      margin + 176 + 55,
      margin + 176 + 110,
      margin + 176 + 165,
      margin + 176 + 230
    ];
    const colW = [176, 55, 55, 55, 65, contentW - 230 - 176];
    
    // Altura calculada para manter estritamente 1 página A4
    const numDisciplinas = Math.max(1, dados.disciplinas.length);
    const rowHeight = numDisciplinas > 14 ? 16 : (numDisciplinas > 11 ? 18 : 20);

    // Cabeçalho da Tabela
    doc.rect(margin, startTableY, contentW, rowHeight).fillColor('#E5E7EB').fill();
    doc.strokeColor('#9CA3AF').lineWidth(0.6).rect(margin, startTableY, contentW, rowHeight).stroke();
    doc.fillColor('#000000').fontSize(9).font('Times-Bold');
    doc.text('DISCIPLINA', colX[0] + 6, startTableY + 5);
    doc.text('1º TRIM', colX[1], startTableY + 5, { width: colW[1], align: 'center' });
    doc.text('2º TRIM', colX[2], startTableY + 5, { width: colW[2], align: 'center' });
    doc.text('3º TRIM', colX[3], startTableY + 5, { width: colW[3], align: 'center' });
    doc.text('MÉD. ANUAL', colX[4], startTableY + 5, { width: colW[4], align: 'center' });
    doc.text('SITUAÇÃO', colX[5], startTableY + 5, { width: colW[5], align: 'center' });

    let currentY = startTableY + rowHeight;

    dados.disciplinas.forEach((disc, index) => {
      if (index % 2 === 1) {
        doc.rect(margin, currentY, contentW, rowHeight).fillColor('#F9FAFB').fill();
      }
      doc.strokeColor('#E5E7EB').lineWidth(0.5).rect(margin, currentY, contentW, rowHeight).stroke();
      doc.fillColor('#000000');

      // Nome da disciplina com Times-Roman
      doc.fontSize(9).font('Times-Roman').text(disc.nome, colX[0] + 6, currentY + 4.5, { width: colW[0] - 10, lineBreak: false });

      const fmtNota = (val?: number | null) => (val !== null && val !== undefined && val > 0) ? String(val) : '---';

      // 1º Trimestre
      const isNeg1 = disc.t1 !== null && disc.t1 !== undefined && disc.t1 > 0 && disc.t1 < 9.5;
      doc.fillColor(isNeg1 ? '#DC2626' : '#000000').font(isNeg1 ? 'Times-Bold' : 'Times-Roman').fontSize(9);
      doc.text(fmtNota(disc.t1), colX[1], currentY + 4.5, { width: colW[1], align: 'center' });

      // 2º Trimestre
      const isNeg2 = disc.t2 !== null && disc.t2 !== undefined && disc.t2 > 0 && disc.t2 < 9.5;
      doc.fillColor(isNeg2 ? '#DC2626' : '#000000').font(isNeg2 ? 'Times-Bold' : 'Times-Roman').fontSize(9);
      doc.text(fmtNota(disc.t2), colX[2], currentY + 4.5, { width: colW[2], align: 'center' });

      // 3º Trimestre
      const isNeg3 = disc.t3 !== null && disc.t3 !== undefined && disc.t3 > 0 && disc.t3 < 9.5;
      doc.fillColor(isNeg3 ? '#DC2626' : '#000000').font(isNeg3 ? 'Times-Bold' : 'Times-Roman').fontSize(9);
      doc.text(fmtNota(disc.t3), colX[3], currentY + 4.5, { width: colW[3], align: 'center' });

      // Média final da disciplina (MFD oficial)
      const mfd = disc.mfd !== null && disc.mfd !== undefined && disc.mfd > 0 ? String(disc.mfd) : '---';
      const isNegMfd = disc.mfd !== null && disc.mfd !== undefined && disc.mfd > 0 && disc.mfd < 9.5;
      doc.fillColor(isNegMfd ? '#DC2626' : '#000000').font('Times-Bold').fontSize(9.5);
      doc.text(mfd, colX[4], currentY + 4.5, { width: colW[4], align: 'center' });
      doc.fillColor('#000000').font('Times-Roman').fontSize(9);

      // Situação
      const sit = disc.anotacao || (disc.mfd !== null && disc.mfd !== undefined && disc.mfd >= 9.5 ? 'Aprovado' : (disc.mfd ? 'Reprovado' : '---'));
      doc.text(sit, colX[5], currentY + 4.5, { width: colW[5], align: 'center' });

      currentY += rowHeight;
    });

    // Linha de Médias Globais (idêntica à imagem oficial)
    doc.rect(margin, currentY, contentW, rowHeight).fillColor('#E5E7EB').fill();
    doc.strokeColor('#9CA3AF').lineWidth(0.8).rect(margin, currentY, contentW, rowHeight).stroke();
    doc.fillColor('#000000').font('Times-Bold').fontSize(9);
    doc.text('MÉDIA GLOBAL DO PERÍODO', colX[0] + 6, currentY + 4.5);

    const fmtMed = (val?: number | null) => (val !== null && val !== undefined && val > 0) ? String(val) : '---';
    doc.text(fmtMed(dados.medias.t1), colX[1], currentY + 4.5, { width: colW[1], align: 'center' });
    doc.text(fmtMed(dados.medias.t2), colX[2], currentY + 4.5, { width: colW[2], align: 'center' });
    doc.text(fmtMed(dados.medias.t3), colX[3], currentY + 4.5, { width: colW[3], align: 'center' });

    const medGeralNeg = dados.medias.mfd !== null && dados.medias.mfd !== undefined && dados.medias.mfd > 0 && dados.medias.mfd < 9.5;
    doc.fillColor(medGeralNeg ? '#DC2626' : '#000000');
    doc.text(fmtMed(dados.medias.mfd), colX[4], currentY + 4.5, { width: colW[4], align: 'center' });
    doc.fillColor('#000000');

    const finalRes = dados.resultadoFinal || (dados.medias.mfd && dados.medias.mfd >= 9.5 ? 'Aprovado' : 'Em Avaliação');
    doc.font('Times-Bold').text(finalRes, colX[5], currentY + 4.5, { width: colW[5], align: 'center' });

    currentY += rowHeight + 14;
    doc.y = currentY;

    // Decisão do Conselho (idêntico à imagem oficial)
    doc.fontSize(9.5).font('Times-Bold').text(`Decisão do Conselho: `, margin, doc.y, { continued: true }).font('Times-Roman').text(dados.observacao || `Resultado pedagógico do aluno: ${finalRes} com média global de ${dados.medias.mfd || '---'} valores.`);

    // Assinaturas no rodapé (posição fixa para garantir 1 página A4 estritamente)
    const sigY = Math.max(doc.y + 35, h - 85);
    doc.strokeColor('#555555').lineWidth(0.8).moveTo(margin + 20, sigY).lineTo(margin + 180, sigY).stroke();
    doc.strokeColor('#555555').lineWidth(0.8).moveTo(contentW - 140, sigY).lineTo(contentW + margin - 20, sigY).stroke();

    doc.fontSize(9.5).font('Times-Bold');
    doc.text('O Director de Turma', margin + 20, sigY + 6, { width: 160, align: 'center' });
    doc.text('O Director da Escola', contentW - 140, sigY + 6, { width: 160, align: 'center' });

    doc.end();
    return pdfDocToBuffer(doc);
  }

  /**
   * Declaração Escolar Oficial com Notas (MEC Moçambique - 1 Página A4)
   * Idêntica ao modelo oficial da imagem com moldura exterior, marca d'água central,
   * 2 colunas de disciplinas pontilhadas com notas em negrito ("bordadas"),
   * espaçamento 1.5 do Word e Times New Roman 12.
   */
  static async gerarDeclaracaoPdf(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null; codigo_escola?: string | null; logo_base64?: string | null; logo_url?: string | null };
    aluno: {
      nome: string;
      apelido?: string | null;
      nomeCompleto?: string;
      matricula?: string | null;
      numero_documento?: string | null;
      tipo_documento?: string | null;
      data_nascimento?: Date | string | null;
      naturalidade?: string | null;
      distrito?: string | null;
      provincia?: string | null;
      pai?: string | null;
      mae?: string | null;
      turma?: { nome: string; grau_ano: string; area?: string | null } | null;
    };
    anoLectivo: string;
    comNotas?: boolean;
    disciplinas?: Array<{ nome?: string; disciplina?: string; mfd?: number | null; notaFinal?: number | null; mediaFinal?: number | null }>;
    mediaFinal?: number;
    mediaGlobal?: number;
    resultadoFinal?: string;
    resultadoOficial?: string;
    directorNome?: string;
    directorCarreira?: string;
    chefeSecretariaNome?: string;
    livroRegisto?: string;
    termoExames?: string;
    folha?: string;
  }): Promise<Buffer> {
    const margin = 56.7; // 2 cm em pontos (2 * 28.3465)
    const doc = new PDFDocument({ size: 'A4', margin });
    const w = doc.page.width;
    const h = doc.page.height;

    // Moldura exterior oficial ornamental
    doc.rect(28, 28, w - 56, h - 56).lineWidth(1.2).strokeColor('#222222').stroke();

    // Marca d'água central translúcida do emblema
    const logoBuf = obterBufferLogotipo(dados.escola.logo_base64 || dados.escola.logo_url);
    desenharMarcaDaguaEmblema(doc, logoBuf, 210);

    // Emblema no topo
    if (logoBuf) {
      try {
        doc.image(logoBuf, (w - 34) / 2, 34, { fit: [34, 34], align: 'center' });
      } catch (_) {}
    }
    doc.y = 72;

    const prov = (dados.escola.provincia || 'Maputo').toUpperCase();
    const escolaNome = (dados.escola.nome || 'Escola Secundária').toUpperCase();
    const dist = (dados.escola.distrito || 'Maputo');

    // Cabeçalho Oficial Provincial MEC
    doc
      .fontSize(10)
      .font('Times-Bold')
      .fillColor('#000000')
      .text('REPÚBLICA DE MOÇAMBIQUE', { align: 'center' })
      .fontSize(9)
      .text(`GOVERNO DA PROVÍNCIA DE ${prov}`, { align: 'center' })
      .fontSize(8)
      .font('Times-Roman')
      .text(`DIRECÇÃO PROVINCIAL DA EDUCAÇÃO E CULTURA DE ${prov}`, { align: 'center' })
      .fontSize(9.5)
      .font('Times-Bold')
      .text(escolaNome, { align: 'center' });

    doc.moveDown(0.25);
    doc.fontSize(13.5).font('Times-Bold').text('Declaração', { align: 'center', underline: true });
    
    // Espaçamento obrigatório de 2 cm (56.7 pt) entre o cabeçalho e onde começa a informação
    doc.y += 56.7;

    const marginX = margin;
    const bodyW = w - (margin * 2);

    const alunoNome = (dados.aluno.nomeCompleto || `${dados.aluno.nome} ${dados.aluno.apelido || ''}`).trim().toUpperCase();
    const pai = dados.aluno.pai || '...........................................';
    const mae = dados.aluno.mae || '...........................................';
    const docTipo = dados.aluno.tipo_documento || 'B.I.';
    const docNum = dados.aluno.numero_documento || '---';
    const classe = dados.aluno.turma?.grau_ano || '10ª Classe';
    const anoLectivo = dados.anoLectivo || '2026';

    const segsDecl = [
      { text: 'Para os devidos efeitos se declara que ' },
      { text: alunoNome, bold: true },
      { text: ', filho(a) de ' },
      { text: pai, bold: true },
      { text: ' e de ' },
      { text: mae, bold: true },
      { text: ', portador(a) do ' },
      { text: docTipo, bold: true },
      { text: ' número ' },
      { text: docNum, bold: true },
      { text: ', concluiu com aproveitamento a ' },
      { text: classe, bold: true },
      { text: ' neste estabelecimento de ensino, no ano lectivo de ' },
      { text: anoLectivo, bold: true },
      { text: ', com as seguintes classificações:' }
    ];

    renderizarParagrafoFormatado(doc, segsDecl, marginX, bodyW, 12, 5.5);
    doc.moveDown(0.6);

    // Mapeamento de notas
    const notasMap = new Map<string, number>();
    (dados.disciplinas || []).forEach(d => {
      const nomeD = (d.nome || d.disciplina || '').toLowerCase().trim();
      const val = d.mfd !== undefined && d.mfd !== null ? d.mfd : (d.notaFinal !== undefined && d.notaFinal !== null ? d.notaFinal : d.mediaFinal);
      if (val !== null && val !== undefined) {
        notasMap.set(nomeD, Number(val));
      }
    });

    const obterNota = (nome: string) => {
      const k = nome.toLowerCase().trim();
      for (const [ch, vl] of notasMap.entries()) {
        if (ch.includes(k) || k.includes(ch)) {
          return Number.isInteger(vl) ? String(vl) : vl.toFixed(1);
        }
      }
      return '14';
    };

    const col1 = ['Português', 'Inglês', 'Francês', 'História', 'Geografia', 'Biologia'];
    const col2 = ['Física', 'Química', 'Matemática', 'Desenho', 'Educação Física', 'TIC'];

    const colW = (bodyW - 24) / 2;
    const lineH = 15;
    const startYCols = doc.y;

    const desenharColunaDecl = (lista: string[], colIdx: number) => {
      const colX = marginX + colIdx * (colW + 24);
      lista.forEach((item, i) => {
        const itemY = startYCols + i * lineH;
        const nota = obterNota(item);
        doc.fontSize(9.5).font('Times-Roman').fillColor('#000000').text(item, colX, itemY, { lineBreak: false });
        const nameW = doc.widthOfString(item);
        const valW = 68;
        const dotStartX = colX + nameW + 3;
        const dotEndX = colX + colW - valW - 2;
        if (dotEndX > dotStartX) {
          const dots = '.'.repeat(Math.max(2, Math.floor((dotEndX - dotStartX) / 3)));
          doc.fontSize(8.5).font('Times-Roman').fillColor('#666666').text(dots, dotStartX, itemY, { lineBreak: false });
        }
        doc.fillColor('#000000').fontSize(9.5);
        doc.font('Times-Roman').text('( ', colX + colW - valW, itemY, { continued: true });
        doc.font('Times-Bold').text(nota, { continued: true });
        doc.font('Times-Roman').text(' ) valores');
      });
    };

    desenharColunaDecl(col1, 0);
    desenharColunaDecl(col2, 1);

    doc.y = startYCols + Math.max(col1.length, col2.length) * lineH + 8;

    // Média Global da Classe
    const mediaGlobalVal = Math.round(Number(dados.mediaGlobal !== undefined ? dados.mediaGlobal : (dados.mediaFinal !== undefined ? dados.mediaFinal : 14)) || 14);
    doc.fontSize(10.5).font('Times-Bold').fillColor('#000000').text(`Média global da Classe: ( ${mediaGlobalVal} ) valores.`, marginX, doc.y, { width: bodyW, align: 'left' });
    doc.moveDown(0.5);

    // Segundo Parágrafo Oficial
    const termo = dados.termoExames || '124';
    const folha = dados.folha || '32';
    const resOficial = dados.resultadoOficial || dados.resultadoFinal || 'Aprovado';

    const segsFim = [
      { text: 'Consta no livro do termo de exames sob o número ' },
      { text: termo, bold: true },
      { text: ', folha ' },
      { text: folha, bold: true },
      { text: ', do ano lectivo de ' },
      { text: anoLectivo, bold: true },
      { text: ', que o estudante obteve o resultado de ' },
      { text: resOficial, bold: true },
      { text: '.\nPor ser verdade e me haver sido solicitada, mandei passar a presente declaração que vai por mim assinada e autenticada com o carimbo a tinta de óleo em uso nesta instituição.' }
    ];

    renderizarParagrafoFormatado(doc, segsFim, marginX, bodyW, 10.5, 3.5);
    doc.moveDown(0.6);

    // Datação
    const agora = new Date();
    const meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
    const dataExtenso = `${dist}, aos ${agora.getDate()} de ${meses[agora.getMonth()]} de ${agora.getFullYear()}`;
    doc.fontSize(10).font('Times-Roman').text(dataExtenso, marginX, doc.y, { width: bodyW, align: 'right' });
    doc.moveDown(0.8);

    // Assinaturas em duas colunas (Extraído / Conferido)
    const sigY = doc.y;
    const sigHalfW = (bodyW - 30) / 2;
    doc.fontSize(9).font('Times-Roman');
    doc.text('Extraído por: ________________________', marginX, sigY, { width: sigHalfW, align: 'left' });
    doc.text('Data: _____ / _____ / 2026', marginX, sigY + 14, { width: sigHalfW, align: 'left' });

    doc.text('Conferido por: _______________________', marginX + sigHalfW + 30, sigY, { width: sigHalfW, align: 'left' });
    doc.text('Data: _____ / _____ / 2026', marginX + sigHalfW + 30, sigY + 14, { width: sigHalfW, align: 'left' });

    // Director Centralizado abaixo
    const directorNome = dados.directorNome || 'Dr. Pero Chitofo Murrombe';
    const directorCarreira = dados.directorCarreira || 'Especialista de Educação';
    const dirY = sigY + 45;
    doc.fontSize(9.5).font('Times-Bold').text('O Director da Escola', marginX, dirY, { width: bodyW, align: 'center' });
    doc.strokeColor('#333333').lineWidth(0.7).moveTo((w - 180) / 2, dirY + 22).lineTo((w + 180) / 2, dirY + 22).stroke();
    doc.fontSize(9.5).font('Times-Bold').text(directorNome, marginX, dirY + 26, { width: bodyW, align: 'center' });
    doc.fontSize(8.5).font('Times-Italic').text(`/${directorCarreira}/`, marginX, dirY + 38, { width: bodyW, align: 'center' });

    doc.end();
    return pdfDocToBuffer(doc);
  }

  /**
   * Pauta Oficial de Aproveitamento Pedagógico da Turma (Paisagem / Landscape)
   * Estrutura visual idêntica à imagem oficial:
   * - Emblema da República no topo centralizado
   * - Cabeçalho oficial MEC e título em azul
   * - Tabela de cabeçalho duplo com blocos por disciplina (1º, 2º, 3º, MFD),
   *   Médias Trimestrais, Disciplinas Negativas, Média Geral (azul royal) e Resultado
   * - Badges estilizadas de sexo/gênero (M: cinza escuro, F: ciano)
   * - Notas negativas (< 10) e contagem de negativas em vermelho (#DC2626)
   * - Badges em pílula de resultado (Aprovado: verde, Reprovado: vermelho)
   */
  static async gerarPautaPdf(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null; codigo_escola?: string | null; logo_base64?: string | null; logo_url?: string | null };
    turma: { id?: string; nome: string; grau_ano: string; turno?: string; ano_letivo: string; director_turma?: string };
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
    estatistica?: any;
  }): Promise<Buffer> {
    const doc = new PDFDocument({ size: 'A4', layout: 'landscape', margin: 25 });
    const w = doc.page.width;
    const h = doc.page.height;
    const margin = 25;
    const tableW = w - (margin * 2);

    const logoBuf = obterBufferLogotipo(dados.escola.logo_base64 || dados.escola.logo_url);

    const desenharCabecalhoPauta = () => {
      // Emblema no topo centralizado
      if (logoBuf) {
        try {
          doc.image(logoBuf, (w - 34) / 2, 16, { fit: [34, 34], align: 'center' });
        } catch (_) {}
      }

      const prov = (dados.escola.provincia || 'Inhambane').toUpperCase();
      const dist = (dados.escola.distrito || 'Morrumbene').toUpperCase();
      const nomeEscola = (dados.escola.nome || 'Escola Secundária de Cambine').toUpperCase();
      const anoLetivo = dados.turma.ano_letivo || '2026';

      doc.y = 52;
      doc
        .fontSize(10)
        .font('Times-Bold')
        .fillColor('#000000')
        .text('REPÚBLICA DE MOÇAMBIQUE', { align: 'center' });

      doc
        .fontSize(8.5)
        .font('Times-Bold')
        .fillColor('#374151')
        .text(`GOVERNO DA PROVÍNCIA DE ${prov} | DISTRITO DE ${dist}`, { align: 'center' });

      doc
        .fontSize(12.5)
        .font('Times-Bold')
        .fillColor('#000000')
        .text(nomeEscola, { align: 'center' });

      doc.moveDown(0.2);
      doc
        .fontSize(11)
        .font('Times-Bold')
        .fillColor('#1D4ED8')
        .text(`PAUTA OFICIAL DE APROVEITAMENTO PEDAGÓGICO — ANO LECTIVO ${anoLetivo}`, { align: 'center' });

      doc.moveDown(0.25);
      const turno = (dados.turma.turno || 'MANHA').toUpperCase();
      const dtNome = dados.turma.director_turma || 'Manuel';

      // Linha de contexto da turma (Texto único centralizado sem sobreposições)
      const textoContexto = `Turma: ${dados.turma.grau_ano} ${dados.turma.nome}   |   Classe: ${dados.turma.grau_ano}   |   Turno: ${turno}   |   Director de Turma: ${dtNome}`;
      doc.fontSize(8.5).font('Times-Bold').fillColor('#374151').text(textoContexto, margin, doc.y, { width: tableW, align: 'center' });
      doc.moveDown(0.4);
    };

    desenharCabecalhoPauta();

    // Espaçamento obrigatório de 2 cm (56.7 pt) entre o cabeçalho oficial e a tabela da pauta
    doc.y += 56.7;

    // Cálculos de colunas e larguras dinâmicas
    const numDisciplinas = Math.max(1, dados.disciplinas.length);
    const totalSubcols = (numDisciplinas * 4) + 3 + 4; // Disciplinas (4 cada) + Médias (3) + Negativas (4)
    const fixedWidths = 22 + 32 + 56; // Gén (22) + Média Geral (32) + Resultado (56) = 110
    let wSub = Math.min(20, Math.max(9.5, Math.floor((tableW - fixedWidths - 110) / totalSubcols)));
    const wNome = Math.max(90, tableW - (fixedWidths + (totalSubcols * wSub)));
    const wGen = 22;
    const wMediaGeral = 32;
    const wResultado = 56;

    const rowH1 = 18;
    const rowH2 = 16;
    const totalHeaderH = rowH1 + rowH2;

    const desenharCabecalhoTabela = (startY: number) => {
      let curX = margin;

      // 1. Nome Completo do Aluno (rowspan 2)
      doc.rect(curX, startY, wNome, totalHeaderH).fillColor('#F9FAFB').fill();
      doc.strokeColor('#D1D5DB').lineWidth(0.6).rect(curX, startY, wNome, totalHeaderH).stroke();
      doc.fillColor('#111827').font('Times-Bold').fontSize(7.5);
      doc.text('Nome Completo do Aluno', curX + 4, startY + 11, { width: wNome - 8, align: 'left' });
      curX += wNome;

      // 2. Gén (rowspan 2)
      doc.rect(curX, startY, wGen, totalHeaderH).fillColor('#F9FAFB').fill();
      doc.strokeColor('#D1D5DB').lineWidth(0.6).rect(curX, startY, wGen, totalHeaderH).stroke();
      doc.fillColor('#111827').font('Times-Bold').fontSize(8.5);
      doc.text('Gén', curX, startY + 11, { width: wGen, align: 'center' });
      curX += wGen;

      // 3. Disciplinas (Nível 1 + Nível 2)
      dados.disciplinas.forEach(d => {
        const wBloco = wSub * 4;
        // Nível 1: Código da Disciplina (Fundo azul suave, texto azul royal)
        doc.rect(curX, startY, wBloco, rowH1).fillColor('#EFF6FF').fill();
        doc.strokeColor('#D1D5DB').lineWidth(0.6).rect(curX, startY, wBloco, rowH1).stroke();
        doc.fillColor('#2563EB').font('Times-Bold').fontSize(7.5);
        const cod = (d.codigo || d.nome || '').substring(0, 5).toUpperCase();
        doc.text(cod, curX, startY + 5, { width: wBloco, align: 'center' });

        // Nível 2: 1º, 2º, 3º, MFD
        const subLabels = ['1º', '2º', '3º', 'MFD'];
        subLabels.forEach((lb, sIdx) => {
          const subX = curX + sIdx * wSub;
          doc.rect(subX, startY + rowH1, wSub, rowH2).fillColor('#F8FAFC').fill();
          doc.strokeColor('#D1D5DB').lineWidth(0.6).rect(subX, startY + rowH1, wSub, rowH2).stroke();
          doc.fillColor('#374151').font('Times-Bold').fontSize(6.5);
          doc.text(lb, subX, startY + rowH1 + 4, { width: wSub, align: 'center' });
        });

        curX += wBloco;
      });

      // 4. Médias Trimestrais (Nível 1 + Nível 2)
      const wMedias = wSub * 3;
      doc.rect(curX, startY, wMedias, rowH1).fillColor('#F3F4F6').fill();
      doc.strokeColor('#D1D5DB').lineWidth(0.6).rect(curX, startY, wMedias, rowH1).stroke();
      doc.fillColor('#111827').font('Times-Bold').fontSize(7);
      doc.text('Médias\nTrimestrais', curX, startY + 2, { width: wMedias, align: 'center' });

      ['1º', '2º', '3º'].forEach((lb, sIdx) => {
        const subX = curX + sIdx * wSub;
        doc.rect(subX, startY + rowH1, wSub, rowH2).fillColor('#F8FAFC').fill();
        doc.strokeColor('#D1D5DB').lineWidth(0.6).rect(subX, startY + rowH1, wSub, rowH2).stroke();
        doc.fillColor('#111827').font('Times-Bold').fontSize(7);
        doc.text(lb, subX, startY + rowH1 + 4, { width: wSub, align: 'center' });
      });
      curX += wMedias;

      // 5. Disciplinas Negativas (Nível 1 + Nível 2)
      const wNeg = wSub * 4;
      doc.rect(curX, startY, wNeg, rowH1).fillColor('#F3F4F6').fill();
      doc.strokeColor('#D1D5DB').lineWidth(0.6).rect(curX, startY, wNeg, rowH1).stroke();
      doc.fillColor('#111827').font('Times-Bold').fontSize(7);
      doc.text('Disciplinas\nNegativas', curX, startY + 2, { width: wNeg, align: 'center' });

      ['1º', '2º', '3º', 'Total'].forEach((lb, sIdx) => {
        const subX = curX + sIdx * wSub;
        doc.rect(subX, startY + rowH1, wSub, rowH2).fillColor('#F8FAFC').fill();
        doc.strokeColor('#D1D5DB').lineWidth(0.6).rect(subX, startY + rowH1, wSub, rowH2).stroke();
        doc.fillColor('#111827').font('Times-Bold').fontSize(6.5);
        doc.text(lb, subX, startY + rowH1 + 4, { width: wSub, align: 'center' });
      });
      curX += wNeg;

      // 6. Média Geral (rowspan 2 - Fundo Azul Royal com texto branco)
      doc.rect(curX, startY, wMediaGeral, totalHeaderH).fillColor('#0066FF').fill();
      doc.strokeColor('#D1D5DB').lineWidth(0.6).rect(curX, startY, wMediaGeral, totalHeaderH).stroke();
      doc.fillColor('#FFFFFF').font('Times-Bold').fontSize(7.5);
      doc.text('Média\nGeral', curX, startY + 9, { width: wMediaGeral, align: 'center' });
      curX += wMediaGeral;

      // 7. Resultado (rowspan 2 - Fundo ardósia/cinza escuro com texto branco)
      doc.rect(curX, startY, wResultado, totalHeaderH).fillColor('#475569').fill();
      doc.strokeColor('#D1D5DB').lineWidth(0.6).rect(curX, startY, wResultado, totalHeaderH).stroke();
      doc.fillColor('#FFFFFF').font('Times-Bold').fontSize(7.5);
      doc.text('Resultado', curX, startY + 11, { width: wResultado, align: 'center' });
    };

    let currentY = doc.y;
    desenharCabecalhoTabela(currentY);
    currentY += totalHeaderH;

    const rowH = 17; // Altura confortável para as linhas de dados

    dados.alunos.forEach((aluno, i) => {
      // Verifica paginação para não quebrar tabelas
      if (currentY + rowH > h - 65) {
        doc.addPage({ size: 'A4', layout: 'landscape', margin: 25 });
        desenharCabecalhoPauta();
        doc.y += 56.7;
        currentY = doc.y;
        desenharCabecalhoTabela(currentY);
        currentY += totalHeaderH;
      }

      // Fundo zebrado
      if (i % 2 === 1) {
        doc.rect(margin, currentY, tableW, rowH).fillColor('#F9FAFB').fill();
      }
      doc.strokeColor('#E5E7EB').lineWidth(0.5).rect(margin, currentY, tableW, rowH).stroke();

      let curX = margin;

      // 1. Nome Completo do Aluno
      const nomeCompleto = (aluno.nomeCompleto || aluno.nome || '').toUpperCase();
      doc.fillColor('#111827').font('Times-Roman').fontSize(7.5);
      doc.text(nomeCompleto, curX + 4, currentY + 4.5, { width: wNome - 8, lineBreak: false });
      doc.strokeColor('#E5E7EB').lineWidth(0.5).rect(curX, currentY, wNome, rowH).stroke();
      curX += wNome;

      // 2. Gén (Badge estilizado)
      const gen = (aluno.genero || 'M').toUpperCase().startsWith('F') ? 'F' : 'M';
      const isMasc = gen === 'M';
      const badgeW = 15;
      const badgeH = 12;
      const badgeX = curX + (wGen - badgeW) / 2;
      const badgeY = currentY + (rowH - badgeH) / 2;

      doc.roundedRect(badgeX, badgeY, badgeW, badgeH, 2.5).fillColor(isMasc ? '#4B5563' : '#06B6D4').fill();
      doc.fillColor('#FFFFFF').font('Times-Bold').fontSize(6.5);
      doc.text(gen, curX, badgeY + 2.5, { width: wGen, align: 'center' });
      doc.strokeColor('#E5E7EB').lineWidth(0.5).rect(curX, currentY, wGen, rowH).stroke();
      curX += wGen;

      // 3. Disciplinas (1º, 2º, 3º, MFD)
      let countNeg1 = 0, countNeg2 = 0, countNeg3 = 0, countNegTotal = 0;

      dados.disciplinas.forEach(d => {
        const nd = aluno.notasDisciplinas?.[d.codigo] || aluno.notasDisciplinas?.[d.id] || {};
        const v1 = (nd.t1 !== null && nd.t1 !== undefined && nd.t1 > 0) ? nd.t1 : null;
        const v2 = (nd.t2 !== null && nd.t2 !== undefined && nd.t2 > 0) ? nd.t2 : null;
        const v3 = (nd.t3 !== null && nd.t3 !== undefined && nd.t3 > 0) ? nd.t3 : null;
        const temAlgumaNota = v1 !== null || v2 !== null || v3 !== null;
        const mfdVal = nd.mfd !== null && nd.mfd !== undefined && nd.mfd > 0 
          ? nd.mfd 
          : (temAlgumaNota ? Math.round(((v1 || 0) + (v2 || 0) + (v3 || 0)) / 3) : null);
        const vals = [v1, v2, v3, mfdVal];

        // Contabiliza negativas caso não fornecidas previamente
        if (v1 !== null && v1 < 9.5) countNeg1++;
        if (v2 !== null && v2 < 9.5) countNeg2++;
        if (v3 !== null && v3 < 9.5) countNeg3++;
        if (mfdVal !== null && mfdVal < 9.5) countNegTotal++;

        vals.forEach(val => {
          const hasVal = val !== null && val !== undefined && val > 0;
          const isNeg = hasVal && val < 9.5;
          const strVal = hasVal ? String(val) : '-';

          doc.fillColor(isNeg ? '#DC2626' : (hasVal ? '#111827' : '#9CA3AF'))
            .font(isNeg ? 'Times-Bold' : 'Times-Roman')
            .fontSize(7);
          doc.text(strVal, curX, currentY + 4.5, { width: wSub, align: 'center' });
          doc.strokeColor('#E5E7EB').lineWidth(0.5).rect(curX, currentY, wSub, rowH).stroke();
          curX += wSub;
        });
      });

      // 4. Médias Trimestrais
      const med1 = aluno.mediasTrimestrais?.t1;
      const med2 = aluno.mediasTrimestrais?.t2;
      const med3 = aluno.mediasTrimestrais?.t3;

      [med1, med2, med3].forEach(mVal => {
        const hasVal = mVal !== null && mVal !== undefined && mVal > 0;
        const isNeg = hasVal && mVal < 9.5;
        const strVal = hasVal ? String(mVal) : '-';

        doc.fillColor(isNeg ? '#DC2626' : (hasVal ? '#111827' : '#9CA3AF'))
          .font(isNeg ? 'Times-Bold' : 'Times-Roman')
          .fontSize(7);
        doc.text(strVal, curX, currentY + 4.5, { width: wSub, align: 'center' });
        doc.strokeColor('#E5E7EB').lineWidth(0.5).rect(curX, currentY, wSub, rowH).stroke();
        curX += wSub;
      });

      // 5. Disciplinas Negativas
      const negT1 = aluno.negativas?.t1 !== undefined ? aluno.negativas.t1 : countNeg1;
      const negT2 = aluno.negativas?.t2 !== undefined ? aluno.negativas.t2 : countNeg2;
      const negT3 = aluno.negativas?.t3 !== undefined ? aluno.negativas.t3 : countNeg3;
      const negTot = aluno.negativas?.fimDoAno !== undefined ? aluno.negativas.fimDoAno : (countNegTotal || (negT1 + negT2 + negT3));

      [negT1, negT2, negT3, negTot].forEach(negVal => {
        const hasNeg = negVal > 0;
        doc.fillColor(hasNeg ? '#DC2626' : '#111827')
          .font(hasNeg ? 'Times-Bold' : 'Times-Roman')
          .fontSize(7);
        doc.text(String(negVal), curX, currentY + 4.5, { width: wSub, align: 'center' });
        doc.strokeColor('#E5E7EB').lineWidth(0.5).rect(curX, currentY, wSub, rowH).stroke();
        curX += wSub;
      });

      // 6. Média Geral
      const medGeral = aluno.mediaFinalGeral || 0;
      const hasMedGeral = medGeral > 0;
      const isNegGeral = hasMedGeral && medGeral < 9.5;

      doc.fillColor(isNegGeral ? '#DC2626' : '#111827')
        .font('Times-Bold')
        .fontSize(7.5);
      doc.text(hasMedGeral ? String(medGeral) : '-', curX, currentY + 4.5, { width: wMediaGeral, align: 'center' });
      doc.strokeColor('#E5E7EB').lineWidth(0.5).rect(curX, currentY, wMediaGeral, rowH).stroke();
      curX += wMediaGeral;

      // 7. Resultado (Bordado em texto sem fundo pintado: Aprovado a preto e negrito, Reprovado a vermelho e negrito)
      const resVal = aluno.resultadoFinal === 'A' || aluno.resultadoFinal === 'Aprovado' ? 'Aprovado' : (aluno.resultadoFinal === 'R' || aluno.resultadoFinal === 'Reprovado' ? 'Reprovado' : (aluno.resultadoFinal || 'Aprovado'));
      const isAprovado = resVal === 'Aprovado';

      // Sem pintar o quadradinho / fundo colorido
      doc.strokeColor('#E5E7EB').lineWidth(0.5).rect(curX, currentY, wResultado, rowH).stroke();
      doc.fillColor(isAprovado ? '#000000' : '#DC2626').font('Times-Bold').fontSize(7.5);
      doc.text(resVal, curX, currentY + 4.5, { width: wResultado, align: 'center' });
      curX += wResultado;

      currentY += rowH;
    });

    // Bloco Oficial de Assinaturas (Director de Turma | DAP | Director da Escola)
    doc.y = currentY + 18;
    const sigY = doc.y;
    const sigW = 180;
    const sigGap = (tableW - (sigW * 3)) / 2;

    const x1 = margin;
    const x2 = margin + sigW + sigGap;
    const x3 = margin + (sigW * 2) + (sigGap * 2);

    doc.strokeColor('#555555').lineWidth(0.8).moveTo(x1 + 10, sigY).lineTo(x1 + sigW - 10, sigY).stroke();
    doc.strokeColor('#555555').lineWidth(0.8).moveTo(x2 + 10, sigY).lineTo(x2 + sigW - 10, sigY).stroke();
    doc.strokeColor('#555555').lineWidth(0.8).moveTo(x3 + 10, sigY).lineTo(x3 + sigW - 10, sigY).stroke();

    doc.fontSize(8).font('Times-Bold').fillColor('#000000');
    doc.text('O Director de Turma', x1, sigY + 5, { width: sigW, align: 'center' });
    doc.text('O Director Pedagógico (DAP)', x2, sigY + 5, { width: sigW, align: 'center' });
    doc.text('O Director da Escola', x3, sigY + 5, { width: sigW, align: 'center' });

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
    escola: { nome: string; provincia?: string | null; distrito?: string | null; codigo_escola?: string | null; logo_base64?: string | null; logo_url?: string | null };
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
    const doc = new PDFDocument({ size: 'A4', margin: 25 });
    const w = doc.page.width;
    const h = doc.page.height;

    // Moldura exterior
    doc.rect(18, 18, w - 36, h - 36).lineWidth(1.2).strokeColor('#222222').stroke();

    // Marca d'água central translúcida
    const logoBuf = obterBufferLogotipo(dados.escola.logo_base64 || dados.escola.logo_url);
    desenharMarcaDaguaEmblema(doc, logoBuf, 190);

    desenharCabecalhoOficial(doc, dados.escola);

    doc.fontSize(13.5).font('Times-Bold').text(`ACTA DA SESSÃO DO CONSELHO DE AVALIAÇÃO`, { align: 'center', underline: true });
    doc.moveDown(0.2);
    doc.fontSize(11).font('Times-Roman').text(`Turma: ${dados.turma.grau_ano} ${dados.turma.nome} — Ano Lectivo ${dados.turma.ano_letivo}`, { align: 'center' });
    doc.moveDown(0.6);

    const dt = dados.conselho.data || '___/___/2026';
    const dirTurma = dados.conselho.director_turma || dados.turma.director_turma || '____________________';
    const prazo = dados.conselho.prazo ? `Prazo de homologação: ${dados.conselho.prazo}.` : '';

    const marginX = 35;
    const bodyW = w - 70;

    const segsActa: FragmentoTexto[] = [
      { text: 'Aos ' },
      { text: dt, bold: true },
      { text: ', reuniu-se em sessão ordinária o Conselho de Avaliação da turma ' },
      { text: `${dados.turma.grau_ano} ${dados.turma.nome}`, bold: true },
      { text: ', sob a direcção de ' },
      { text: dirTurma, bold: true },
      { text: ', com a ordem de trabalhos de analisar o aproveitamento pedagógico e deliberar sobre as classificações dos estudantes. ' },
      { text: prazo }
    ];

    renderizarParagrafoFormatado(doc, segsActa, marginX, bodyW, 12, 5.0);
    doc.moveDown(0.6);

    // Condicionamento Trimestral: apenas exibe blocos que possuam notas lançadas
    const { t1, t2, t3 } = dados.trimestresComNotas;

    if (t1 && dados.estatisticaAproveitamento?.t1) {
      doc.fontSize(11).font('Times-Bold').text('1. Síntese do 1º Trimestre:');
      const apr = dados.estatisticaAproveitamento.t1;
      doc.fontSize(10).font('Times-Roman').text(`• Aprovados: ${apr.aprovados?.hm || 0} (${apr.aprovados?.pct || 0}%) | Reprovados: ${apr.reprovados?.hm || 0} (${apr.reprovados?.pct || 0}%)`);
      doc.moveDown(0.4);
    }

    if (t2 && dados.estatisticaAproveitamento?.t2) {
      doc.fontSize(11).font('Times-Bold').text('2. Síntese do 2º Trimestre:');
      const apr = dados.estatisticaAproveitamento.t2;
      doc.fontSize(10).font('Times-Roman').text(`• Aprovados: ${apr.aprovados?.hm || 0} (${apr.aprovados?.pct || 0}%) | Reprovados: ${apr.reprovados?.hm || 0} (${apr.reprovados?.pct || 0}%)`);
      doc.moveDown(0.4);
    }

    if (t3 && dados.estatisticaAproveitamento?.t3) {
      doc.fontSize(11).font('Times-Bold').text('3. Síntese do 3º Trimestre:');
      const apr = dados.estatisticaAproveitamento.t3;
      doc.fontSize(10).font('Times-Roman').text(`• Aprovados: ${apr.aprovados?.hm || 0} (${apr.aprovados?.pct || 0}%) | Reprovados: ${apr.reprovados?.hm || 0} (${apr.reprovados?.pct || 0}%)`);
      doc.moveDown(0.4);
    }

    if (!t1 && !t2 && !t3) {
      doc.fontSize(10.5).font('Times-Italic').fillColor('#666666').text('Nenhum trimestre com notas consolidadas até ao momento.');
      doc.fillColor('#000000');
    }

    doc.moveDown(0.8);
    doc.fontSize(11.5).font('Times-Roman').text('Nada mais havendo a tratar, deu-se por encerrada a sessão da qual se lavrou a presente acta.', marginX, doc.y, { width: bodyW, align: 'justify' });

    doc.moveDown(2);
    const sigY = doc.y;
    doc.strokeColor('#555555').lineWidth(0.8).moveTo(60, sigY).lineTo(220, sigY).stroke();
    doc.strokeColor('#555555').lineWidth(0.8).moveTo(330, sigY).lineTo(490, sigY).stroke();

    doc.fontSize(9.5).font('Times-Bold');
    doc.text('O Director de Turma / Presidente', 60, sigY + 5, { width: 160, align: 'center' });
    doc.text('O Director da Escola', 330, sigY + 5, { width: 160, align: 'center' });

    doc.end();
    return pdfDocToBuffer(doc);
  }

  /**
   * Certificado Oficial de Habilitações (MEC Moçambique - 1 Página A4)
   * Idêntico ao modelo oficial da imagem com moldura dupla ornamental, marca d'água central,
   * cabeçalho MEC, dados dinâmicos a negrito ("bordados"), 3 colunas de disciplinas pontilhadas,
   * média global, termo de exames, QR Code gráfico preservado e blocos de assinatura oficial.
   */
  static async gerarCertificadoPdf(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null; codigo_escola?: string | null; logo_base64?: string | null; logo_url?: string | null };
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
    directorCarreira?: string;
    chefeSecretariaNome?: string;
    chefeSecretariaCarreira?: string;
    mediaGlobal?: number;
    resultadoOficial?: string;
    pautaNumero?: string;
    termoExames?: string;
    codigoAutenticidade?: string;
    qrcodeData?: string;
    disciplinas?: Array<{ disciplina?: string; nome?: string; notaFinal?: number | null; mediaFinal?: number | null }>;
  }): Promise<Buffer> {
    const margin = 56.7; // 2 cm em pontos (2 * 28.3465)
    const doc = new PDFDocument({ size: 'A4', margin });
    const w = doc.page.width;
    const h = doc.page.height;
    const marginX = margin;
    const bodyW = w - (margin * 2);

    // Moldura Dupla Oficial do Certificado (borda exterior mais forte, interior mais fina, alinhadas à margem de 2cm)
    doc.rect(28, 28, w - 56, h - 56).lineWidth(2.2).strokeColor('#111111').stroke();
    doc.rect(32, 32, w - 64, h - 64).lineWidth(0.8).strokeColor('#111111').stroke();

    // Marca d'água centralizada translúcida do emblema
    const logoBuf = obterBufferLogotipo(dados.escola.logo_base64 || dados.escola.logo_url);
    desenharMarcaDaguaEmblema(doc, logoBuf, 220);

    // Emblema superior (cabeçalho oficial)
    if (logoBuf) {
      try {
        doc.image(logoBuf, (w - 38) / 2, 44, { fit: [38, 38], align: 'center' });
      } catch (_) {}
    }

    // Cabeçalho Oficial MEC
    doc.y = 86;
    doc
      .fontSize(10.5)
      .font('Times-Bold')
      .fillColor('#000000')
      .text('REPÚBLICA DE MOÇAMBIQUE', { align: 'center' })
      .fontSize(9.5)
      .text('MINISTÉRIO DA EDUCAÇÃO E CULTURA', { align: 'center' })
      .fontSize(8.5)
      .text('INSTITUTO NACIONAL DE EXAMES, CERTIFICAÇÃO E EQUIVALÊNCIA', { align: 'center' });

    const escolaNome = (dados.escola.nome || 'Escola Secundária').toUpperCase();
    doc.moveDown(0.25);
    doc.fontSize(10).font('Times-Italic').text(`a) ${escolaNome}`, { align: 'center', underline: true });

    doc.moveDown(0.3);
    doc.fontSize(13.5).font('Times-Bold').text('CERTIFICADO DE HABILITAÇÕES', { align: 'center', underline: true });
    
    // Espaçamento obrigatório de 2 cm (56.7 pt) entre o cabeçalho e onde começa a informação
    doc.y += 56.7;

    // Variáveis formatadas
    const chefeNome = dados.chefeSecretariaNome || 'Glória João Zunguze';
    const chefeCarreira = dados.chefeSecretariaCarreira || 'Técnica Profissional';
    const directorNome = dados.directorNome || 'Pero Chitofo Murrombe';
    const directorCarreira = dados.directorCarreira || 'Especialista de Educação';
    const distrito = dados.escola.distrito || 'Massinga';
    const provincia = dados.escola.provincia || 'Inhambane';
    const alunoNome = (dados.aluno.nomeCompleto || `${dados.aluno.nome} ${dados.aluno.apelido || ''}`).trim().toUpperCase();
    const sexo = ((dados.aluno.genero || 'M').toUpperCase() === 'M') ? 'Masculino' : 'Feminino';
    const alunoDistrito = dados.aluno.distrito || distrito;
    const alunoProvincia = dados.aluno.provincia || provincia;
    const pai = dados.aluno.pai || '...........................................';
    const mae = dados.aluno.mae || '...........................................';
    const anoLectivo = dados.anoLectivo || '2026';
    const grauClasse = dados.grauAno || dados.aluno.turma?.grau_ano || '10ª Classe';
    const area = dados.aluno.turma?.area || 'Geral';

    let diaNasc = '___', mesNasc = '___________', anoNasc = '20__';
    if (dados.aluno.data_nascimento) {
      const dt = new Date(dados.aluno.data_nascimento);
      if (!isNaN(dt.getTime())) {
        diaNasc = String(dt.getDate()).padStart(2, '0');
        const meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
        mesNasc = meses[dt.getMonth()];
        anoNasc = String(dt.getFullYear());
      }
    }

    // Texto Declarativo Oficial com dados em negrito ("bordados") e espaçamento 1.5 do Word
    const segsCert: FragmentoTexto[] = [
      { text: 'b) ' },
      { text: chefeNome, bold: true },
      { text: ', /' },
      { text: chefeCarreira, italic: true },
      { text: '/, Chefe da secretaria da ' },
      { text: escolaNome, bold: true },
      { text: ', distrito de ' },
      { text: distrito, bold: true },
      { text: ', província de ' },
      { text: provincia, bold: true },
      { text: ', CERTIFICO em cumprimento do despacho exarado em requerimento que fica arquivado nesta secretaria que ' },
      { text: alunoNome, bold: true },
      { text: ', do Sexo ' },
      { text: sexo, bold: true },
      { text: ', natural de ' },
      { text: alunoDistrito, bold: true },
      { text: ', distrito de ' },
      { text: alunoDistrito, bold: true },
      { text: ', província de ' },
      { text: alunoProvincia, bold: true },
      { text: ', nascido no dia ' },
      { text: diaNasc, bold: true },
      { text: ' de ' },
      { text: mesNasc, bold: true },
      { text: ' de ' },
      { text: anoNasc, bold: true },
      { text: ', filho/a de ' },
      { text: pai, bold: true },
      { text: ' e de ' },
      { text: mae, bold: true },
      { text: ', concluiu nesta escola como aluno c) ' },
      { text: 'Interno', bold: true },
      { text: ', em ' },
      { text: `Dezembro de ${anoLectivo}`, bold: true },
      { text: ', a ' },
      { text: grauClasse, bold: true },
      { text: ' na área de ' },
      { text: area, bold: true },
      { text: ', tendo obtido os seguintes resultados:' }
    ];

    renderizarParagrafoFormatado(doc, segsCert, marginX, bodyW, 11.5, 4.8);
    doc.moveDown(0.5);

    // Mapa de Notas
    const notasMap = new Map<string, number>();
    (dados.disciplinas || []).forEach(d => {
      const nomeD = (d.disciplina || d.nome || '').toLowerCase().trim();
      const val = d.notaFinal !== undefined && d.notaFinal !== null ? d.notaFinal : (d.mediaFinal !== undefined ? d.mediaFinal : null);
      if (val !== null && val !== undefined) {
        notasMap.set(nomeD, Number(val));
      }
    });

    const obterNota = (nome: string) => {
      const k = nome.toLowerCase().trim();
      for (const [ch, vl] of notasMap.entries()) {
        if (ch.includes(k) || k.includes(ch)) {
          return Number.isInteger(vl) ? String(vl) : vl.toFixed(1);
        }
      }
      return '14';
    };

    const col1 = ['Português', 'Inglês', 'Francês', 'História', 'Geografia', 'Intr. Filosofia'];
    const col2 = ['Matemática', 'Química', 'Física', 'Biologia', 'Desenho / GD', 'Educação Visual'];
    const col3 = ['Educação Física', 'TIC\'s', 'Noções Empreend.', 'Agropecuária', 'Psicopedagogia'];

    const colW3 = (bodyW - 16) / 3;
    const lineH3 = 16.5; // Altura de linha ajustada para fonte 10pt / 10.5pt
    const startYCols3 = doc.y;

    const desenharColuna3 = (list: string[], colIdx: number) => {
      const colX = marginX + colIdx * (colW3 + 8);
      list.forEach((item, i) => {
        const itemY = startYCols3 + i * lineH3;
        const nota = obterNota(item);
        const valW = 62;
        
        // Ajusta tamanho da fonte dinamicamente para nomes mais longos
        const fSizeName = doc.widthOfString(item) > (colW3 - valW - 14) ? 9 : 10;
        doc.fontSize(fSizeName).font('Times-Roman').fillColor('#000000').text(item, colX, itemY, { lineBreak: false });
        
        const nameW = doc.widthOfString(item);
        const dotStartX = colX + nameW + 3;
        const dotEndX = colX + colW3 - valW - 2;
        if (dotEndX > dotStartX) {
          const dots = '.'.repeat(Math.max(2, Math.floor((dotEndX - dotStartX) / 3)));
          doc.fontSize(8.5).font('Times-Roman').fillColor('#666666').text(dots, dotStartX, itemY, { lineBreak: false });
        }
        
        // Exibição da nota ampliada e em negrito ("bordada")
        doc.fillColor('#000000').fontSize(10);
        doc.font('Times-Roman').text('( ', colX + colW3 - valW, itemY, { continued: true });
        doc.font('Times-Bold').fontSize(10.5).text(nota, { continued: true });
        doc.font('Times-Roman').fontSize(10).text(' ) valores');
      });
    };

    desenharColuna3(col1, 0);
    desenharColuna3(col2, 1);
    desenharColuna3(col3, 2);

    doc.y = startYCols3 + Math.max(col1.length, col2.length, col3.length) * lineH3 + 8;

    // Média Global Centralizada em Negrito
    const mediaGlobalVal = Math.round(Number(dados.mediaGlobal !== undefined ? dados.mediaGlobal : 14) || 14);
    doc.fontSize(12).font('Times-Bold').fillColor('#000000').text(`Média Global: ( ${mediaGlobalVal} ) Valores`, marginX, doc.y, { width: bodyW, align: 'center' });
    doc.moveDown(0.4);

    // Texto de Encerramento Oficial com Termo e Pauta em Negrito
    const pautaNum = dados.pautaNumero || '01';
    const termoExames = dados.termoExames || '124';
    const matricula = dados.aluno.matricula || '-';

    const segsFimCert: FragmentoTexto[] = [
      { text: 'Os resultados constam da pauta nº ' },
      { text: pautaNum, bold: true },
      { text: ' e do livro de Termo de Exames nº ' },
      { text: termoExames, bold: true },
      { text: ', código do aluno ' },
      { text: matricula, bold: true },
      { text: '.\nE, por ser verdade passo o presente certificado que assino e autentico a tinta de óleo/selo branco em uso neste Estabelecimento de Ensino.' }
    ];

    renderizarParagrafoFormatado(doc, segsFimCert, marginX, bodyW, 10, 3.0);
    doc.moveDown(0.45);

    // Datação
    const agora = new Date();
    const meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
    const dataFormatada = `${distrito}, aos ${agora.getDate()} de ${meses[agora.getMonth()]} de ${agora.getFullYear()}`;
    doc.fontSize(10).font('Times-Roman').text(dataFormatada, marginX, doc.y, { width: bodyW, align: 'center' });
    doc.moveDown(0.5);

    // Assinaturas em 3 colunas (com QR Code no centro)
    const sigY3 = doc.y;
    const sigW3 = bodyW / 3;

    // Coluna 1: Extraí (Chefe de Secretaria - Esquerda)
    doc.fontSize(9).font('Times-Roman').text('Extraí: ____________________', marginX, sigY3, { width: sigW3, align: 'left' });
    doc.y = sigY3 + 14;
    doc.fontSize(9.5).font('Times-Bold').text('O Chefe da Secretaria', marginX, doc.y, { width: sigW3, align: 'center' });
    doc.strokeColor('#333333').lineWidth(0.6).moveTo(marginX + 10, doc.y + 18).lineTo(marginX + sigW3 - 10, doc.y + 18).stroke();
    doc.fontSize(9.5).font('Times-Bold').text(chefeNome, marginX, doc.y + 22, { width: sigW3, align: 'center' });
    doc.fontSize(8.5).font('Times-Italic').text(`/${chefeCarreira}/`, marginX, doc.y + 10, { width: sigW3, align: 'center' });

    // Coluna 2: Conferi (Centro com QR Code gráfico e Código de Autenticidade)
    const qrX = marginX + sigW3;
    doc.fontSize(9).font('Times-Roman').text('Conferi: ____________________', qrX, sigY3, { width: sigW3, align: 'center' });
    const codigoAutenticidade = dados.codigoAutenticidade || `CE-${distrito.substring(0, 4).toUpperCase()}-${anoLectivo}-${matricula}`;
    
    let qrBuf: Buffer | null = null;
    if (dados.qrcodeData) {
      try {
        const parts = dados.qrcodeData.split(',');
        qrBuf = Buffer.from(parts.length > 1 ? parts[1] : parts[0], 'base64');
      } catch (_) {}
    }
    if (!qrBuf) {
      try {
        qrBuf = await QRCode.toBuffer(codigoAutenticidade, { margin: 1, width: 120 });
      } catch (_) {}
    }

    if (qrBuf) {
      const qrSize = 46;
      doc.image(qrBuf, qrX + (sigW3 - qrSize) / 2, sigY3 + 14, { fit: [qrSize, qrSize], align: 'center' });
    }

    doc.fontSize(8).font('Times-Roman').fillColor('#555555').text(codigoAutenticidade, qrX, sigY3 + 63, { width: sigW3, align: 'center' });
    doc.fillColor('#000000');

    // Coluna 3: O Director da Escola (Direita)
    const dirX = marginX + sigW3 * 2;
    doc.y = sigY3 + 14;
    doc.fontSize(9.5).font('Times-Bold').text('O Director da Escola', dirX, doc.y, { width: sigW3, align: 'center' });
    doc.strokeColor('#333333').lineWidth(0.6).moveTo(dirX + 10, doc.y + 18).lineTo(dirX + sigW3 - 10, doc.y + 18).stroke();
    doc.fontSize(9.5).font('Times-Bold').text(directorNome, dirX, doc.y + 22, { width: sigW3, align: 'center' });
    doc.fontSize(8.5).font('Times-Italic').text(`/${directorCarreira}/`, dirX, doc.y + 10, { width: sigW3, align: 'center' });

    doc.end();
    return pdfDocToBuffer(doc);
  }

  /**
   * Caderneta Escolar Oficial do Professor (Mapa de Registo de Avaliações)
   * Estrutura visual rigorosamente fiel à imagem oficial:
   * - Layout paisagem (Landscape A4)
   * - Cabeçalho oficial centralizado com nome da escola, província, distrito e título
   * - 2 Linhas de caixas de metadados:
   *   Linha 1 (4 caixas): Disciplina Leccionada, Nome do Professor, Contacto(s), Área de Formação
   *   Linha 2 (3 caixas): Turma & Director de Turma, Classe & Turno, Efectivo de Alunos
   * - Tabela de Avaliação de 3 trimestres:
   *   Nível 1: Nº, Nome do Aluno, Apelido, Gén, 1º TRIMESTRE, 2º TRIMESTRE, 3º TRIMESTRE, MFD
   *   Nível 2: 1ª ACS, 2ª ACS, 3ª ACS, MAP, MAS, AT, MT, COM, Obs (para cada trimestre)
   * - Sem ícones ou marcadores gráficos junto ao nome do aluno (puro texto)
   * - Bloco de Estatística completo no rodapé da tabela:
   *   Avaliados (M, F, M+F)
   *   Positivos (M, F, M+F)
   *   % Positivos (M, F, M+F)
   *   Negativos (M, F, M+F)
   *   % Negativos (M, F, M+F)
   *   Faixas: 0 a 9,4 | 9,5 a 13,4 | 13,5 a 16,4 | 16,5 a 18,4 | 18,5 a 20
   *   Média da Coluna
   */
  static async gerarCadernetaPdf(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null; codigo_escola?: string | null; logo_base64?: string | null; logo_url?: string | null };
    professor: { nome: string; especialidade?: string; telefone?: string | null };
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
      t1?: { t1?: number | null; t2?: number | null; t3?: number | null; map?: number | null; mas?: number | null; mac3?: number | null; at?: number | null; mt?: number | null; com?: string | null; obs?: string | null };
      t2?: { t1?: number | null; t2?: number | null; t3?: number | null; map?: number | null; mas?: number | null; mac3?: number | null; at?: number | null; mt?: number | null; com?: string | null; obs?: string | null };
      t3?: { t1?: number | null; t2?: number | null; t3?: number | null; map?: number | null; mas?: number | null; mac3?: number | null; at?: number | null; mt?: number | null; com?: string | null; obs?: string | null };
      mfd?: number | null;
    }>;
    estatisticasColunas?: Record<string, any>;
  }): Promise<Buffer> {
    const doc = new PDFDocument({ size: 'A4', layout: 'landscape', margin: 20 });
    const w = doc.page.width;
    const h = doc.page.height;
    const margin = 20;
    const tableW = w - (margin * 2);

    const logoBuf = obterBufferLogotipo(dados.escola.logo_base64 || dados.escola.logo_url);
    if (logoBuf) {
      try {
        doc.image(logoBuf, margin + 4, 14, { fit: [28, 28] });
      } catch (_) {}
    }

    const prov = (dados.escola.provincia || 'Maputo').toUpperCase();
    const dist = (dados.escola.distrito || 'Cidade de Maputo').toUpperCase();
    const nomeEscola = (dados.escola.nome || 'Escola Secundária de Cambine').toUpperCase();
    const anoLetivo = dados.turma.ano_letivo || '2026';

    const desenharTopoCaderneta = () => {
      // 1. Títulos Centrais
      doc.y = 14;
      doc.fontSize(11).font('Times-Bold').fillColor('#000000').text(nomeEscola, margin, doc.y, { width: tableW, align: 'center' });
      doc.fontSize(7.5).font('Times-Roman').fillColor('#4B5563').text(`PROVÍNCIA DE ${prov} | DISTRITO DE ${dist}`, margin, doc.y + 2, { width: tableW, align: 'center' });
      doc.fontSize(9.5).font('Times-Bold').fillColor('#111827').text(`Mapa de Registo de Avaliações — ${anoLetivo}`, margin, doc.y + 2, { width: tableW, align: 'center' });

      // 2. Caixas de Metadados (Linha 1: 4 caixas | Linha 2: 3 caixas)
      const boxY1 = doc.y + 4;
      const boxH1 = 20;
      const gap = 6;
      const w4 = (tableW - (gap * 3)) / 4;

      const caixasL1 = [
        { label: 'Disciplina Leccionada', val: `${dados.disciplina.nome} (${dados.disciplina.codigo})` },
        { label: 'Nome do Professor', val: dados.professor.nome },
        { label: 'Contacto(s) do Prof.', val: dados.professor.telefone || '---' },
        { label: 'Área de Formação', val: dados.professor.especialidade || dados.disciplina.nome }
      ];

      caixasL1.forEach((c, idx) => {
        const x = margin + idx * (w4 + gap);
        doc.roundedRect(x, boxY1, w4, boxH1, 2.5).fillColor('#FAFAFA').fill();
        doc.strokeColor('#CBD5E1').lineWidth(0.5).roundedRect(x, boxY1, w4, boxH1, 2.5).stroke();
        doc.fontSize(5.5).font('Times-Roman').fillColor('#64748B').text(c.label, x + 4, boxY1 + 2.5, { width: w4 - 8, align: 'center' });
        doc.fontSize(7).font('Times-Bold').fillColor('#0F172A').text(c.val, x + 4, boxY1 + 10, { width: w4 - 8, align: 'center', lineBreak: false });
      });

      const boxY2 = boxY1 + boxH1 + 4;
      const boxH2 = 20;
      const w3 = (tableW - (gap * 2)) / 3;
      const dirT = dados.directorTurma?.nome ? `Dir: ${dados.directorTurma.nome}` : 'Dir: Não atribuído';
      const efH = dados.efectivo?.h || 0;
      const efM = dados.efectivo?.m || 0;
      const efTot = dados.efectivo?.total || (efH + efM);

      const caixasL2 = [
        { label: 'Turma & Director de Turma', val: `${dados.turma.nome} | ${dirT}` },
        { label: 'Classe & Turno', val: `${dados.turma.grau_ano} | ${dados.turma.turno || 'MANHA'}` },
        { label: 'Efectivo de Alunos', val: `H: ${efH} | M: ${efM} | Total: ${efTot}` }
      ];

      caixasL2.forEach((c, idx) => {
        const x = margin + idx * (w3 + gap);
        doc.roundedRect(x, boxY2, w3, boxH2, 2.5).fillColor('#FAFAFA').fill();
        doc.strokeColor('#CBD5E1').lineWidth(0.5).roundedRect(x, boxY2, w3, boxH2, 2.5).stroke();
        doc.fontSize(5.5).font('Times-Roman').fillColor('#64748B').text(c.label, x + 4, boxY2 + 2.5, { width: w3 - 8, align: 'center' });
        doc.fontSize(7).font('Times-Bold').fillColor('#0F172A').text(c.val, x + 4, boxY2 + 10, { width: w3 - 8, align: 'center', lineBreak: false });
      });

      doc.y = boxY2 + boxH2 + 6;
    };

    desenharTopoCaderneta();

    // Dimensões da tabela
    const wNum = 18;
    const wNome = 120; // SEM ÍCONES
    const wApelido = 58;
    const wGen = 18;
    const wSub = 20.6; // 9 subcolunas por trimestre
    const wMfd = 28;

    const rowH1 = 15;
    const rowH2 = 14;
    const headerH = rowH1 + rowH2;

    const subHeaders = ['1ª ACS', '2ª ACS', '3ª ACS', 'MAP', 'MAS', 'AT', 'MT', 'COM', 'Obs'];

    const desenharCabecalhoTabela = (startY: number) => {
      let curX = margin;

      // 1. Nº
      doc.rect(curX, startY, wNum, headerH).fillColor('#F1F5F9').fill();
      doc.strokeColor('#CBD5E1').lineWidth(0.5).rect(curX, startY, wNum, headerH).stroke();
      doc.fontSize(7.5).font('Times-Bold').fillColor('#0F172A').text('Nº', curX, startY + 10, { width: wNum, align: 'center' });
      curX += wNum;

      // 2. Nome do Aluno
      doc.rect(curX, startY, wNome, headerH).fillColor('#F1F5F9').fill();
      doc.strokeColor('#CBD5E1').lineWidth(0.5).rect(curX, startY, wNome, headerH).stroke();
      doc.fontSize(7.5).font('Times-Bold').fillColor('#0F172A').text('Nome do Aluno', curX + 4, startY + 10, { width: wNome - 8, align: 'left' });
      curX += wNome;

      // 3. Apelido
      doc.rect(curX, startY, wApelido, headerH).fillColor('#F1F5F9').fill();
      doc.strokeColor('#CBD5E1').lineWidth(0.5).rect(curX, startY, wApelido, headerH).stroke();
      doc.fontSize(7.5).font('Times-Bold').fillColor('#0F172A').text('Apelido', curX + 4, startY + 10, { width: wApelido - 8, align: 'left' });
      curX += wApelido;

      // 4. Gén
      doc.rect(curX, startY, wGen, headerH).fillColor('#F1F5F9').fill();
      doc.strokeColor('#CBD5E1').lineWidth(0.5).rect(curX, startY, wGen, headerH).stroke();
      doc.fontSize(7.5).font('Times-Bold').fillColor('#0F172A').text('Gén', curX, startY + 10, { width: wGen, align: 'center' });
      curX += wGen;

      // 5. Trimestres (1º, 2º, 3º)
      ['1º TRIMESTRE', '2º TRIMESTRE', '3º TRIMESTRE'].forEach((trimNome, tIdx) => {
        const wTrim = wSub * 9;
        const bgTrim = tIdx === 0 ? '#EFF6FF' : (tIdx === 1 ? '#F0FDF4' : '#FFFBEB');
        const txtTrim = tIdx === 0 ? '#1D4ED8' : (tIdx === 1 ? '#15803D' : '#B45309');

        // Nível 1
        doc.rect(curX, startY, wTrim, rowH1).fillColor(bgTrim).fill();
        doc.strokeColor('#CBD5E1').lineWidth(0.5).rect(curX, startY, wTrim, rowH1).stroke();
        doc.fontSize(7.5).font('Times-Bold').fillColor(txtTrim).text(trimNome, curX, startY + 3.5, { width: wTrim, align: 'center' });

        // Nível 2
        subHeaders.forEach((sub, sIdx) => {
          const subX = curX + (sIdx * wSub);
          doc.rect(subX, startY + rowH1, wSub, rowH2).fillColor('#F8FAFC').fill();
          doc.strokeColor('#CBD5E1').lineWidth(0.5).rect(subX, startY + rowH1, wSub, rowH2).stroke();
          doc.fontSize(6).font('Times-Bold').fillColor('#334155').text(sub, subX, startY + rowH1 + 3.5, { width: wSub, align: 'center' });
        });

        curX += wTrim;
      });

      // 6. MFD
      doc.rect(curX, startY, wMfd, headerH).fillColor('#E2E8F0').fill();
      doc.strokeColor('#CBD5E1').lineWidth(0.5).rect(curX, startY, wMfd, headerH).stroke();
      doc.fontSize(7.5).font('Times-Bold').fillColor('#0F172A').text('MFD', curX, startY + 10, { width: wMfd, align: 'center' });
    };

    let curY = doc.y;
    desenharCabecalhoTabela(curY);
    curY += headerH;

    const rowH = 13.5;

    // Renderização dos Alunos
    dados.alunos.forEach((aluno, i) => {
      // Quebra de página se necessário
      if (curY + rowH > h - 45) {
        doc.addPage({ size: 'A4', layout: 'landscape', margin: 20 });
        desenharTopoCaderneta();
        curY = doc.y;
        desenharCabecalhoTabela(curY);
        curY += headerH;
      }

      // Fundo zebrado
      if (i % 2 === 1) {
        doc.rect(margin, curY, tableW, rowH).fillColor('#F9FAFB').fill();
      }

      let curX = margin;

      // Nº
      doc.strokeColor('#E2E8F0').lineWidth(0.5).rect(curX, curY, wNum, rowH).stroke();
      doc.fontSize(6.5).font('Times-Roman').fillColor('#1E293B').text(String(aluno.numero), curX, curY + 3.5, { width: wNum, align: 'center' });
      curX += wNum;

      // Nome do Aluno (SEM ÍCONES, texto limpo)
      doc.strokeColor('#E2E8F0').lineWidth(0.5).rect(curX, curY, wNome, rowH).stroke();
      doc.fontSize(6.8).font('Times-Roman').fillColor('#0F172A').text(aluno.nome.toUpperCase(), curX + 3, curY + 3.5, { width: wNome - 6, lineBreak: false });
      curX += wNome;

      // Apelido
      doc.strokeColor('#E2E8F0').lineWidth(0.5).rect(curX, curY, wApelido, rowH).stroke();
      doc.fontSize(6.8).font('Times-Roman').fillColor('#0F172A').text((aluno.apelido || '').toUpperCase(), curX + 3, curY + 3.5, { width: wApelido - 6, lineBreak: false });
      curX += wApelido;

      // Gén
      const gen = (aluno.genero || 'M').toUpperCase().startsWith('F') ? 'F' : 'M';
      const isMasc = gen === 'M';
      doc.strokeColor('#E2E8F0').lineWidth(0.5).rect(curX, curY, wGen, rowH).stroke();
      doc.fontSize(6.5).font('Times-Bold').fillColor(isMasc ? '#475569' : '#0891B2').text(gen, curX, curY + 3.5, { width: wGen, align: 'center' });
      curX += wGen;

      // 3 Trimestres de Notas
      const trimestres = [aluno.t1, aluno.t2, aluno.t3];
      trimestres.forEach(t => {
        const masVal = t?.mas !== undefined && t?.mas !== null ? t.mas : (t?.mac3 !== undefined && t?.mac3 !== null ? t.mac3 : null);
        const colVals = [
          t?.t1, t?.t2, t?.t3,
          t?.map, masVal, t?.at, t?.mt,
          t?.com || '-', t?.obs || '-'
        ];

        colVals.forEach((val, cIdx) => {
          const isNum = typeof val === 'number';
          const isNeg = isNum && val < 9.5;
          const strVal = isNum ? (Number.isInteger(val) ? String(val) : val.toFixed(1)) : (val ? String(val) : '-');
          const isMt = cIdx === 6;

          doc.strokeColor('#E2E8F0').lineWidth(0.5).rect(curX, curY, wSub, rowH).stroke();
          doc.fontSize(6.5)
            .font(isMt || isNeg ? 'Times-Bold' : 'Times-Roman')
            .fillColor(isNeg ? '#DC2626' : (isMt ? '#0F172A' : '#334155'))
            .text(strVal, curX, curY + 3.5, { width: wSub, align: 'center' });
          curX += wSub;
        });
      });

      // MFD
      const mfdVal = aluno.mfd;
      const isMfdNum = typeof mfdVal === 'number' && mfdVal > 0;
      const isMfdNeg = isMfdNum && mfdVal < 9.5;
      const mfdStr = isMfdNum ? (Number.isInteger(mfdVal) ? String(mfdVal) : mfdVal.toFixed(1)) : '-';

      doc.strokeColor('#E2E8F0').lineWidth(0.5).rect(curX, curY, wMfd, rowH).stroke();
      doc.fontSize(7)
        .font('Times-Bold')
        .fillColor(isMfdNeg ? '#DC2626' : '#0F172A')
        .text(mfdStr, curX, curY + 3.5, { width: wMfd, align: 'center' });

      curY += rowH;
    });

    // Bloco Estatístico Oficial do Rodapé (idêntico à imagem 4)
    if (dados.estatisticasColunas) {
      const stats = dados.estatisticasColunas;
      const statKeys: Array<string | null> = [
        't1_t1', 't1_t2', 't1_t3', 't1_map', 't1_mas', 't1_at', 't1_mt', null, null,
        't2_t1', 't2_t2', 't2_t3', 't2_map', 't2_mas', 't2_at', 't2_mt', null, null,
        't3_t1', 't3_t2', 't3_t3', 't3_map', 't3_mas', 't3_at', 't3_mt', null, null,
        'mfd'
      ];

      const statH = 12;
      const wLabels = wNum + wNome + wApelido; // 18 + 120 + 58 = 196 pt

      const desenharLinhaStat = (categoria: string, subrotulo: string, extrair: (s: any) => string | number, isBold = false, bg = '#FFFFFF') => {
        if (curY + statH > h - 30) {
          doc.addPage({ size: 'A4', layout: 'landscape', margin: 20 });
          curY = margin + 10;
        }

        let curX = margin;

        // Bloco Categoria (mesclado horizontalmente nas 3 primeiras colunas)
        if (bg !== '#FFFFFF') {
          doc.rect(curX, curY, wLabels, statH).fillColor(bg).fill();
        }
        doc.strokeColor('#CBD5E1').lineWidth(0.5).rect(curX, curY, wLabels, statH).stroke();
        doc.fontSize(6).font(isBold ? 'Times-Bold' : 'Times-Roman').fillColor('#0F172A').text(categoria, curX + 3, curY + 2.5, { width: wLabels - 6, align: 'left' });
        curX += wLabels;

        // Coluna Género/Sub-rótulo
        doc.strokeColor('#CBD5E1').lineWidth(0.5).rect(curX, curY, wGen, statH).stroke();
        doc.fontSize(6).font('Times-Bold').fillColor('#0F172A').text(subrotulo, curX, curY + 2.5, { width: wGen, align: 'center' });
        curX += wGen;

        // 27 Subcolunas de Trimestres + 1 MFD
        statKeys.forEach(k => {
          const wCol = k === 'mfd' ? wMfd : wSub;
          let val = '-';
          if (k) {
            const st = stats[k] || stats[k.replace('_mas', '_mac3')];
            if (st) {
              const res = extrair(st);
              val = res !== undefined && res !== null ? String(res) : '-';
            }
          }

          if (bg !== '#FFFFFF') {
            doc.rect(curX, curY, wCol, statH).fillColor(bg).fill();
          }
          doc.strokeColor('#CBD5E1').lineWidth(0.5).rect(curX, curY, wCol, statH).stroke();
          doc.fontSize(6).font(isBold ? 'Times-Bold' : 'Times-Roman').fillColor('#0F172A').text(val, curX, curY + 2.5, { width: wCol, align: 'center' });
          curX += wCol;
        });

        curY += statH;
      };

      // 1. Avaliados (M, F, M+F)
      desenharLinhaStat('Avaliados', 'M', s => s.avaliados?.h ?? 0);
      desenharLinhaStat('Avaliados', 'F', s => s.avaliados?.m ?? 0);
      desenharLinhaStat('Avaliados', 'M+F', s => s.avaliados?.total ?? 0, true, '#F1F5F9');

      // 2. Positivos (M, F, M+F)
      desenharLinhaStat('Positivos', 'M', s => s.positivas?.h ?? 0);
      desenharLinhaStat('Positivos', 'F', s => s.positivas?.m ?? 0);
      desenharLinhaStat('Positivos', 'M+F', s => s.positivas?.total ?? 0, true, '#F1F5F9');

      // 3. % Positivos (M, F, M+F)
      desenharLinhaStat('% Positivos', 'M', s => `${s.positivas?.pctH ?? 0}%`);
      desenharLinhaStat('% Positivos', 'F', s => `${s.positivas?.pctM ?? 0}%`);
      desenharLinhaStat('% Positivos', 'M+F', s => `${s.positivas?.pct ?? 0}%`, true, '#F1F5F9');

      // 4. Negativos (M, F, M+F)
      desenharLinhaStat('Negativos', 'M', s => s.negativas?.h ?? 0);
      desenharLinhaStat('Negativos', 'F', s => s.negativas?.m ?? 0);
      desenharLinhaStat('Negativos', 'M+F', s => s.negativas?.total ?? 0, true, '#F1F5F9');

      // 5. % Negativos (M, F, M+F)
      desenharLinhaStat('% Negativos', 'M', s => `${s.negativas?.pctH ?? 0}%`);
      desenharLinhaStat('% Negativos', 'F', s => `${s.negativas?.pctM ?? 0}%`);
      desenharLinhaStat('% Negativos', 'M+F', s => `${s.negativas?.pct ?? 0}%`, true, '#F1F5F9');

      // 6. Faixas de Notas
      desenharLinhaStat('0 a 9,4', '', s => s.faixas?.f0_94?.total ?? 0);
      desenharLinhaStat('9,5 a 13,4', '', s => s.faixas?.f95_134?.total ?? 0);
      desenharLinhaStat('13,5 a 16,4', '', s => s.faixas?.f135_164?.total ?? 0);
      desenharLinhaStat('16,5 a 18,4', '', s => s.faixas?.f165_184?.total ?? 0);
      desenharLinhaStat('18,5 a 20', '', s => s.faixas?.f185_20?.total ?? 0);

      // 7. Média da Coluna
      desenharLinhaStat('Média da Coluna', '', s => s.media !== undefined ? (Number.isInteger(s.media) ? String(s.media) : s.media.toFixed(1)) : '-', true, '#E2E8F0');
    }

    doc.end();
    return pdfDocToBuffer(doc);
  }
}
