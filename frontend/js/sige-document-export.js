/**
 * SIGE — Sistema Integrado de Gestão Escolar
 * Motor Super Avançado de Geração de Documentos e Relatórios
 * 
 * Bibliotecas Oficiais Integradas:
 * - PDF: jsPDF (com jsPDF-AutoTable)
 * - XLSX: Excel.js (ExcelJS)
 * - Word (DOCX): docx.js (docx)
 * 
 * Regra Obrigatória: Em cada painel, botões de interface NÃO devem ter "js" no texto.
 * Utilizam rótulos elegantes como: "PDF", "Excel", "Word".
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.SigeExport = factory();
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // Utilitário para descarregar Blob no navegador
  function descarregarBlob(blob, nomeFicheiro) {
    if (window.navigator && window.navigator.msSaveOrOpenBlob) {
      window.navigator.msSaveOrOpenBlob(blob, nomeFicheiro);
      return;
    }
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = nomeFicheiro;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    }, 1500);
  }

  // Obter metadados da instituição activa
  function obterMetadadosInstituicao() {
    let escolaNome = 'ESCOLA SECUNDÁRIA GERAL';
    let localidade = 'REPÚBLICA DE MOÇAMBIQUE | MINISTÉRIO DA EDUCAÇÃO E DESENVOLVIMENTO HUMANO';
    let anoLetivo = '2026';

    try {
      if (window.state && window.state.instituicao && window.state.instituicao.nome) {
        escolaNome = window.state.instituicao.nome.toUpperCase();
        if (window.state.instituicao.distrito || window.state.instituicao.provincia) {
          localidade = `PROVÍNCIA DE ${window.state.instituicao.provincia || 'MAPUTO'} | DISTRITO DE ${window.state.instituicao.distrito || 'MAPUTO'}`;
        }
      } else {
        const stored = localStorage.getItem('sige_instituicao');
        if (stored) {
          const inst = JSON.parse(stored);
          if (inst.nome) escolaNome = inst.nome.toUpperCase();
          if (inst.distrito || inst.provincia) {
            localidade = `PROVÍNCIA DE ${inst.provincia || 'MAPUTO'} | DISTRITO DE ${inst.distrito || 'MAPUTO'}`;
          }
        }
      }
    } catch (_) {}

    return {
      pais: 'REPÚBLICA DE MOÇAMBIQUE',
      ministerio: 'MINISTÉRIO DA EDUCAÇÃO E DESENVOLVIMENTO HUMANO',
      escola: escolaNome,
      localidade: localidade,
      anoLetivo: anoLetivo,
      dataEmissao: new Date().toLocaleDateString('pt-PT')
    };
  }

  // Extrair colunas e linhas de um elemento <table> do DOM
  function extrairDadosTabela(tabelaOuId, opcoes = {}) {
    const tableEl = typeof tabelaOuId === 'string' ? document.getElementById(tabelaOuId) : tabelaOuId;
    if (!tableEl) return null;

    const ignorarUltimaColuna = opcoes.ignorarAcoes !== false;
    const cabecalhos = [];
    const linhas = [];

    // 1. Obter cabeçalhos
    const theadRows = tableEl.querySelectorAll('thead tr');
    if (theadRows.length > 0) {
      const ultimaLinhaThead = theadRows[theadRows.length - 1];
      const ths = ultimaLinhaThead.querySelectorAll('th, td');
      ths.forEach((th, idx) => {
        if (ignorarUltimaColuna && idx === ths.length - 1 && (th.textContent.includes('Acções') || th.textContent.includes('Ações') || th.textContent.includes('Comprovativo') || th.textContent.includes('Liquidação'))) {
          return;
        }
        cabecalhos.push(th.innerText.trim().replace(/\s+/g, ' '));
      });
    }

    // Se o thead tinha rowspan/colspan ou colunas complexas, tentar fallback
    if (cabecalhos.length === 0) {
      const primeiroTr = tableEl.querySelector('tr');
      if (primeiroTr) {
        primeiroTr.querySelectorAll('th, td').forEach((cell) => {
          cabecalhos.push(cell.innerText.trim().replace(/\s+/g, ' '));
        });
      }
    }

    // 2. Obter linhas do corpo
    const tbodyRows = tableEl.querySelectorAll('tbody tr');
    tbodyRows.forEach((tr) => {
      // Ignorar linhas de placeholder / carregamento / vazias
      if (tr.children.length === 1 && tr.children[0].getAttribute('colspan')) {
        return;
      }
      const linha = [];
      const cells = tr.querySelectorAll('td, th');
      cells.forEach((td, idx) => {
        if (ignorarUltimaColuna && idx === cells.length - 1 && (cabecalhos.length < cells.length)) {
          return;
        }
        // Limpar botões e ícones
        let texto = td.innerText.trim().replace(/\s+/g, ' ');
        linha.push(texto);
      });
      if (linha.length > 0) {
        linhas.push(linha);
      }
    });

    return { cabecalhos, linhas };
  }

  // =========================================================================
  // 1. MOTOR PDF COM jsPDF E jsPDF-AutoTable
  // =========================================================================
  async function exportarPdf({
    titulo = 'Documento Oficial',
    subtitulo = '',
    cabecalhos = [],
    linhas = [],
    orientacao = 'landscape',
    nomeFicheiro = 'Documento.pdf',
    metadadosExtras = {},
    rodapeAssinaturas = true
  }) {
    const { jsPDF } = window.jspdf || window;
    if (!jsPDF) {
      console.error('[SigeExport] jsPDF não está disponível globalmente.');
      throw new Error('A biblioteca jsPDF não foi carregada.');
    }

    const doc = new jsPDF({
      orientation: orientacao,
      unit: 'mm',
      format: 'a4'
    });

    const meta = obterMetadadosInstituicao();
    const isLandscape = orientacao === 'landscape';
    const pageWidth = isLandscape ? 297 : 210;
    const pageHeight = isLandscape ? 210 : 297;
    const marginX = 14;

    // Cabeçalho institucional desenhado no topo da página
    function desenharCabecalhoOficial() {
      doc.setFont('times', 'bold');
      doc.setFontSize(11);
      doc.setTextColor(20, 30, 60);
      doc.text(meta.pais, pageWidth / 2, 12, { align: 'center' });

      doc.setFont('times', 'normal');
      doc.setFontSize(8.5);
      doc.setTextColor(80, 80, 80);
      doc.text(meta.ministerio, pageWidth / 2, 16.5, { align: 'center' });

      doc.setFont('times', 'bold');
      doc.setFontSize(10.5);
      doc.setTextColor(30, 58, 138); // Navy blue oficial
      doc.text(meta.escola, pageWidth / 2, 21.5, { align: 'center' });

      doc.setFont('times', 'italic');
      doc.setFontSize(7.5);
      doc.setTextColor(100, 100, 100);
      doc.text(meta.localidade, pageWidth / 2, 25.5, { align: 'center' });

      // Linha separadora institucional
      doc.setDrawColor(30, 58, 138);
      doc.setLineWidth(0.5);
      doc.line(marginX, 27.5, pageWidth - marginX, 27.5);

      // Título do Documento
      doc.setFont('times', 'bold');
      doc.setFontSize(12);
      doc.setTextColor(15, 23, 42);
      doc.text(titulo.toUpperCase(), pageWidth / 2, 33, { align: 'center' });

      // Subtítulo / Metadados da turma ou período
      if (subtitulo) {
        doc.setFont('times', 'normal');
        doc.setFontSize(8.5);
        doc.setTextColor(70, 70, 70);
        doc.text(subtitulo, pageWidth / 2, 37.5, { align: 'center' });
      }
    }

    desenharCabecalhoOficial();

    let startY = subtitulo ? 41 : 37;

    // Se houver metadados adicionais em caixa (Turma, Disciplina, Professor, etc.)
    const metaKeys = Object.keys(metadadosExtras);
    if (metaKeys.length > 0) {
      doc.setFillColor(248, 250, 252);
      doc.setDrawColor(226, 232, 240);
      doc.roundedRect(marginX, startY, pageWidth - (marginX * 2), 10, 1, 1, 'FD');

      doc.setFont('times', 'normal');
      doc.setFontSize(8);
      doc.setTextColor(30, 41, 59);

      const colW = (pageWidth - (marginX * 2)) / metaKeys.length;
      metaKeys.forEach((k, i) => {
        const xPos = marginX + (i * colW) + 2;
        doc.setFont('times', 'bold');
        doc.text(`${k}: `, xPos, startY + 6.5);
        const wBold = doc.getTextWidth(`${k}: `);
        doc.setFont('times', 'normal');
        doc.text(String(metadadosExtras[k] || '-'), xPos + wBold, startY + 6.5);
      });

      startY += 14;
    }

    // Renderizar tabela principal via AutoTable
    if (cabecalhos.length > 0 && linhas.length > 0) {
      if (typeof doc.autoTable === 'function') {
        doc.autoTable({
          head: [cabecalhos],
          body: linhas,
          startY: startY,
          margin: { left: marginX, right: marginX, bottom: 25 },
          styles: {
            font: 'times',
            fontSize: isLandscape ? 7.5 : 8,
            cellPadding: 1.8,
            overflow: 'linebreak',
            lineColor: [203, 213, 225],
            lineWidth: 0.2
          },
          headStyles: {
            fillColor: [30, 58, 138],
            textColor: [255, 255, 255],
            fontStyle: 'bold',
            halign: 'center',
            fontSize: isLandscape ? 8 : 8.5
          },
          alternateRowStyles: {
            fillColor: [248, 250, 252]
          },
          didParseCell: function (data) {
            // Destaque para notas negativas (< 9.5) a vermelho
            if (data.section === 'body') {
              const val = parseFloat(String(data.cell.raw).replace(',', '.'));
              if (!isNaN(val) && val >= 0 && val < 9.5) {
                data.cell.styles.textColor = [220, 38, 38];
                data.cell.styles.fontStyle = 'bold';
              }
            }
          },
          didDrawPage: function (data) {
            // Rodapé em cada página
            const strPage = `Página ${data.pageNumber} | SIGE — Sistema Integrado de Gestão Escolar`;
            doc.setFont('times', 'italic');
            doc.setFontSize(7.5);
            doc.setTextColor(140, 140, 140);
            doc.text(strPage, marginX, pageHeight - 8);
            doc.text(`Emitido em: ${meta.dataEmissao}`, pageWidth - marginX, pageHeight - 8, { align: 'right' });
          }
        });
      }
    }

    // Bloco de Assinaturas no final do relatório (se couber ou em nova página)
    if (rodapeAssinaturas) {
      let finalY = (doc.lastAutoTable && doc.lastAutoTable.finalY) ? doc.lastAutoTable.finalY + 14 : startY + 20;
      if (finalY + 25 > pageHeight - 15) {
        doc.addPage();
        finalY = 30;
      }

      const sigWidth = (pageWidth - (marginX * 2)) / 3;
      const sigY = finalY + 12;

      doc.setFont('times', 'normal');
      doc.setFontSize(8);
      doc.setTextColor(50, 50, 50);

      // Assinatura 1: O Professor / Responsável
      doc.setDrawColor(150, 150, 150);
      doc.line(marginX + 10, sigY, marginX + sigWidth - 10, sigY);
      doc.text('O Professor / Técnico', marginX + (sigWidth / 2), sigY + 4, { align: 'center' });

      // Assinatura 2: O Director de Turma / Pedagógico
      doc.line(marginX + sigWidth + 10, sigY, marginX + (sigWidth * 2) - 10, sigY);
      doc.text('O Director de Turma / DAE', marginX + sigWidth + (sigWidth / 2), sigY + 4, { align: 'center' });

      // Assinatura 3: O Director da Escola
      doc.line(marginX + (sigWidth * 2) + 10, sigY, marginX + (sigWidth * 3) - 10, sigY);
      doc.text('O Director da Instituição', marginX + (sigWidth * 2) + (sigWidth / 2), sigY + 4, { align: 'center' });
    }

    const safeNome = nomeFicheiro.toLowerCase().endsWith('.pdf') ? nomeFicheiro : `${nomeFicheiro}.pdf`;
    doc.save(safeNome);
    return true;
  }

  // =========================================================================
  // 2. MOTOR EXCEL COM Excel.js (ExcelJS)
  // =========================================================================
  async function exportarExcel({
    titulo = 'Relatório Oficial SIGE',
    subtitulo = '',
    cabecalhos = [],
    linhas = [],
    nomeAba = 'Dados',
    nomeFicheiro = 'Relatorio.xlsx',
    metadadosExtras = {}
  }) {
    const ExcelJS = window.ExcelJS;
    if (!ExcelJS) {
      console.error('[SigeExport] ExcelJS não está disponível globalmente.');
      throw new Error('A biblioteca Excel.js não foi carregada.');
    }

    const workbook = new ExcelJS.Workbook();
    workbook.creator = 'SIGE — Sistema Integrado de Gestão Escolar';
    workbook.lastModifiedBy = 'SIGE';
    workbook.created = new Date();
    workbook.modified = new Date();

    const meta = obterMetadadosInstituicao();
    const worksheet = workbook.addWorksheet(nomeAba.substring(0, 31), {
      pageSetup: { paperSize: 9, orientation: 'landscape' },
      views: [{ state: 'frozen', ySplit: 5 }]
    });

    const totalCols = Math.max(cabecalhos.length, 6);

    // Linha 1: Faixa Principal de Título Institucional
    const r1 = worksheet.addRow([meta.pais + ' — ' + meta.ministerio]);
    worksheet.mergeCells(1, 1, 1, totalCols);
    r1.height = 22;
    r1.getCell(1).font = { name: 'Times New Roman', size: 10, bold: true, color: { argb: 'FFFFFFFF' } };
    r1.getCell(1).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF0F172A' } };
    r1.getCell(1).alignment = { vertical: 'middle', horizontal: 'center' };

    // Linha 2: Nome da Escola
    const r2 = worksheet.addRow([meta.escola]);
    worksheet.mergeCells(2, 1, 2, totalCols);
    r2.height = 24;
    r2.getCell(1).font = { name: 'Times New Roman', size: 12, bold: true, color: { argb: 'FFFFFFFF' } };
    r2.getCell(1).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF1E3A8A' } };
    r2.getCell(1).alignment = { vertical: 'middle', horizontal: 'center' };

    // Linha 3: Título do Documento
    const r3 = worksheet.addRow([titulo.toUpperCase() + (subtitulo ? ` | ${subtitulo}` : '')]);
    worksheet.mergeCells(3, 1, 3, totalCols);
    r3.height = 20;
    r3.getCell(1).font = { name: 'Times New Roman', size: 10, bold: true, color: { argb: 'FF1E293B' } };
    r3.getCell(1).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF1F5F9' } };
    r3.getCell(1).alignment = { vertical: 'middle', horizontal: 'center' };

    // Linha 4: Metadados adicionais ou linha em branco
    const metaStr = Object.entries(metadadosExtras).map(([k, v]) => `${k}: ${v}`).join('  |  ');
    const r4 = worksheet.addRow([metaStr ? `${metaStr}  |  Emissão: ${meta.dataEmissao}` : `Ano Lectivo: ${meta.anoLetivo}  |  Data de Emissão: ${meta.dataEmissao}`]);
    worksheet.mergeCells(4, 1, 4, totalCols);
    r4.height = 18;
    r4.getCell(1).font = { name: 'Times New Roman', size: 8.5, italic: true, color: { argb: 'FF64748B' } };
    r4.getCell(1).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF8FAFC' } };
    r4.getCell(1).alignment = { vertical: 'middle', horizontal: 'center' };

    // Linha 5: Cabeçalho das Colunas
    const cabecalhoRow = worksheet.addRow(cabecalhos);
    cabecalhoRow.height = 25;
    cabecalhoRow.eachCell((cell) => {
      cell.font = { name: 'Times New Roman', size: 9.5, bold: true, color: { argb: 'FFFFFFFF' } };
      cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF2563EB' } };
      cell.alignment = { vertical: 'middle', horizontal: 'center', wrapText: true };
      cell.border = {
        top: { style: 'thin', color: { argb: 'FFCBD5E1' } },
        left: { style: 'thin', color: { argb: 'FFCBD5E1' } },
        bottom: { style: 'medium', color: { argb: 'FF1E3A8A' } },
        right: { style: 'thin', color: { argb: 'FFCBD5E1' } }
      };
    });

    // Linhas de Dados
    linhas.forEach((linhaDados, idx) => {
      const row = worksheet.addRow(linhaDados);
      row.height = 20;
      const isAlt = idx % 2 === 1;

      row.eachCell((cell, colNum) => {
        cell.font = { name: 'Times New Roman', size: 9 };
        if (isAlt) {
          cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF8FAFC' } };
        }
        cell.border = {
          top: { style: 'thin', color: { argb: 'FFE2E8F0' } },
          left: { style: 'thin', color: { argb: 'FFE2E8F0' } },
          bottom: { style: 'thin', color: { argb: 'FFE2E8F0' } },
          right: { style: 'thin', color: { argb: 'FFE2E8F0' } }
        };

        // Alinhamento inteligente
        const rawVal = cell.value;
        const numVal = parseFloat(String(rawVal).replace(',', '.'));
        if (!isNaN(numVal) && String(rawVal).trim().match(/^-?\d+(\.\d+)?$/)) {
          cell.value = numVal;
          cell.alignment = { vertical: 'middle', horizontal: 'center' };
          if (numVal >= 0 && numVal < 9.5) {
            cell.font = { name: 'Times New Roman', size: 9, bold: true, color: { argb: 'FFDC2626' } };
          }
        } else {
          cell.alignment = { vertical: 'middle', horizontal: colNum <= 3 ? 'left' : 'center' };
        }
      });
    });

    // Ajuste Automático de Largura das Colunas
    worksheet.columns.forEach((col, idx) => {
      let maxLen = (cabecalhos[idx] || '').length;
      col.eachCell({ includeEmpty: false }, (cell, rowNum) => {
        if (rowNum > 4) {
          const valLen = String(cell.value || '').length;
          if (valLen > maxLen && valLen < 45) maxLen = valLen;
        }
      });
      col.width = Math.max(maxLen + 3, 10);
    });

    const buffer = await workbook.xlsx.writeBuffer();
    const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    const safeNome = nomeFicheiro.toLowerCase().endsWith('.xlsx') ? nomeFicheiro : `${nomeFicheiro}.xlsx`;
    descarregarBlob(blob, safeNome);
    return true;
  }

  // =========================================================================
  // 3. MOTOR WORD (DOCX) COM docx.js (docx)
  // =========================================================================
  async function exportarWord({
    titulo = 'Documento Oficial',
    subtitulo = '',
    cabecalhos = [],
    linhas = [],
    orientacao = 'portrait',
    nomeFicheiro = 'Documento.docx',
    metadadosExtras = {}
  }) {
    const docxLib = window.docx;
    if (!docxLib) {
      console.error('[SigeExport] docx.js não está disponível globalmente.');
      throw new Error('A biblioteca docx.js não foi carregada.');
    }

    const {
      Document,
      Packer,
      Paragraph,
      TextRun,
      Table,
      TableRow,
      TableCell,
      WidthType,
      AlignmentType,
      BorderStyle,
      PageOrientation
    } = docxLib;

    const meta = obterMetadadosInstituicao();
    const isLandscape = orientacao === 'landscape';

    // Montar Cabeçalho do Word
    const elementosCorpo = [
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 60 },
        children: [
          new TextRun({
            text: meta.pais,
            bold: true,
            size: 20, // 10pt
            font: 'Times New Roman'
          })
        ]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 60 },
        children: [
          new TextRun({
            text: meta.ministerio,
            size: 16, // 8pt
            color: '64748B',
            font: 'Times New Roman'
          })
        ]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 120 },
        children: [
          new TextRun({
            text: meta.escola,
            bold: true,
            size: 22, // 11pt
            color: '1E3A8A',
            font: 'Times New Roman'
          })
        ]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 200 },
        border: {
          bottom: { style: BorderStyle.SINGLE, size: 8, color: '1E3A8A', space: 4 }
        },
        children: [
          new TextRun({
            text: meta.localidade,
            size: 15,
            color: '94A3B8',
            italics: true,
            font: 'Times New Roman'
          })
        ]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 100, after: 80 },
        children: [
          new TextRun({
            text: titulo.toUpperCase(),
            bold: true,
            size: 24, // 12pt
            color: '0F172A',
            font: 'Times New Roman'
          })
        ]
      })
    ];

    if (subtitulo) {
      elementosCorpo.push(
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 160 },
          children: [
            new TextRun({
              text: subtitulo,
              size: 17,
              color: '475569',
              font: 'Times New Roman'
            })
          ]
        })
      );
    }

    // Metadados adicionais em caixa informativa
    const metaEntries = Object.entries(metadadosExtras);
    if (metaEntries.length > 0) {
      const metaCells = metaEntries.map(([k, v]) => {
        return new TableCell({
          shading: { fill: 'F8FAFC' },
          borders: {
            top: { style: BorderStyle.SINGLE, size: 4, color: 'CBD5E1' },
            bottom: { style: BorderStyle.SINGLE, size: 4, color: 'CBD5E1' },
            left: { style: BorderStyle.SINGLE, size: 4, color: 'CBD5E1' },
            right: { style: BorderStyle.SINGLE, size: 4, color: 'CBD5E1' }
          },
          children: [
            new Paragraph({
              alignment: AlignmentType.CENTER,
              children: [
                new TextRun({ text: `${k}: `, bold: true, size: 16, font: 'Times New Roman' }),
                new TextRun({ text: String(v || '-'), size: 16, font: 'Times New Roman' })
              ]
            })
          ]
        });
      });

      elementosCorpo.push(
        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE },
          rows: [new TableRow({ children: metaCells })]
        })
      );

      elementosCorpo.push(new Paragraph({ spacing: { after: 160 } }));
    }

    // Montar Tabela Principal
    if (cabecalhos.length > 0 && linhas.length > 0) {
      const colWidthPercent = Math.floor(100 / cabecalhos.length);

      const tableRows = [
        new TableRow({
          tableHeader: true,
          children: cabecalhos.map(h => new TableCell({
            width: { size: colWidthPercent, type: WidthType.PERCENTAGE },
            shading: { fill: '1E3A8A' },
            margins: { top: 100, bottom: 100, left: 80, right: 80 },
            borders: {
              top: { style: BorderStyle.SINGLE, size: 4, color: 'CBD5E1' },
              bottom: { style: BorderStyle.SINGLE, size: 6, color: '1E3A8A' },
              left: { style: BorderStyle.SINGLE, size: 4, color: 'CBD5E1' },
              right: { style: BorderStyle.SINGLE, size: 4, color: 'CBD5E1' }
            },
            children: [
              new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [
                  new TextRun({
                    text: h,
                    bold: true,
                    size: 16,
                    color: 'FFFFFF',
                    font: 'Times New Roman'
                  })
                ]
              })
            ]
          }))
        })
      ];

      linhas.forEach((linhaDados, idx) => {
        const isAlt = idx % 2 === 1;
        tableRows.push(
          new TableRow({
            children: linhaDados.map((val, colIdx) => {
              const numVal = parseFloat(String(val).replace(',', '.'));
              const isNeg = (!isNaN(numVal) && numVal >= 0 && numVal < 9.5);
              return new TableCell({
                width: { size: colWidthPercent, type: WidthType.PERCENTAGE },
                shading: { fill: isAlt ? 'F8FAFC' : 'FFFFFF' },
                margins: { top: 60, bottom: 60, left: 60, right: 60 },
                borders: {
                  top: { style: BorderStyle.SINGLE, size: 4, color: 'E2E8F0' },
                  bottom: { style: BorderStyle.SINGLE, size: 4, color: 'E2E8F0' },
                  left: { style: BorderStyle.SINGLE, size: 4, color: 'E2E8F0' },
                  right: { style: BorderStyle.SINGLE, size: 4, color: 'E2E8F0' }
                },
                children: [
                  new Paragraph({
                    alignment: colIdx <= 2 ? AlignmentType.LEFT : AlignmentType.CENTER,
                    children: [
                      new TextRun({
                        text: String(val || '-'),
                        size: 15,
                        font: 'Times New Roman',
                        bold: isNeg,
                        color: isNeg ? 'DC2626' : '1E293B'
                      })
                    ]
                  })
                ]
              });
            })
          })
        );
      });

      elementosCorpo.push(
        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE },
          rows: tableRows
        })
      );
    }

    // Assinaturas Oficiais
    elementosCorpo.push(new Paragraph({ spacing: { before: 300, after: 100 } }));
    const assinaturasTable = new Table({
      width: { size: 100, type: WidthType.PERCENTAGE },
      rows: [
        new TableRow({
          children: [
            new TableCell({
              borders: {
                top: { style: BorderStyle.NONE },
                bottom: { style: BorderStyle.NONE },
                left: { style: BorderStyle.NONE },
                right: { style: BorderStyle.NONE }
              },
              children: [
                new Paragraph({
                  alignment: AlignmentType.CENTER,
                  border: { top: { style: BorderStyle.SINGLE, size: 4, color: '94A3B8' } },
                  children: [new TextRun({ text: 'O Professor / Técnico', size: 15, font: 'Times New Roman' })]
                })
              ]
            }),
            new TableCell({
              borders: {
                top: { style: BorderStyle.NONE },
                bottom: { style: BorderStyle.NONE },
                left: { style: BorderStyle.NONE },
                right: { style: BorderStyle.NONE }
              },
              children: [
                new Paragraph({
                  alignment: AlignmentType.CENTER,
                  border: { top: { style: BorderStyle.SINGLE, size: 4, color: '94A3B8' } },
                  children: [new TextRun({ text: 'O Director de Turma / DAE', size: 15, font: 'Times New Roman' })]
                })
              ]
            }),
            new TableCell({
              borders: {
                top: { style: BorderStyle.NONE },
                bottom: { style: BorderStyle.NONE },
                left: { style: BorderStyle.NONE },
                right: { style: BorderStyle.NONE }
              },
              children: [
                new Paragraph({
                  alignment: AlignmentType.CENTER,
                  border: { top: { style: BorderStyle.SINGLE, size: 4, color: '94A3B8' } },
                  children: [new TextRun({ text: 'O Director da Instituição', size: 15, font: 'Times New Roman' })]
                })
              ]
            })
          ]
        })
      ]
    });
    elementosCorpo.push(assinaturasTable);

    const doc = new Document({
      sections: [{
        properties: {
          page: {
            orientation: isLandscape ? PageOrientation.LANDSCAPE : PageOrientation.PORTRAIT,
            margin: {
              top: 720,    // 0.5 inch
              right: 720,
              bottom: 720,
              left: 720
            }
          }
        },
        children: elementosCorpo
      }]
    });

    let blob;
    try {
      blob = await Packer.toBlob(doc);
    } catch (_) {
      const b64 = await Packer.toBase64String(doc);
      const byteChars = atob(b64);
      const byteNumbers = new Array(byteChars.length);
      for (let i = 0; i < byteChars.length; i++) {
        byteNumbers[i] = byteChars.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      blob = new Blob([byteArray], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
    }

    const safeNome = nomeFicheiro.toLowerCase().endsWith('.docx') ? nomeFicheiro : `${nomeFicheiro}.docx`;
    descarregarBlob(blob, safeNome);
    return true;
  }

  // =========================================================================
  // EXPORTAÇÃO UNIVERSAL A PARTIR DE TABELA OU ELEMENTO HTML
  // =========================================================================
  async function exportarTabelaHtml(tabelaOuId, formato, opcoes = {}) {
    const dados = extrairDadosTabela(tabelaOuId, opcoes);
    if (!dados || dados.linhas.length === 0) {
      alert('Não existem dados carregados nesta tabela para exportar.');
      return false;
    }

    const config = {
      titulo: opcoes.titulo || 'Relatório Oficial SIGE',
      subtitulo: opcoes.subtitulo || '',
      cabecalhos: dados.cabecalhos,
      linhas: dados.linhas,
      orientacao: opcoes.orientacao || (dados.cabecalhos.length > 7 ? 'landscape' : 'portrait'),
      nomeFicheiro: opcoes.nomeFicheiro || `Relatorio_${new Date().toISOString().slice(0, 10)}`,
      metadadosExtras: opcoes.metadadosExtras || {}
    };

    const fmt = String(formato).toLowerCase();
    if (fmt === 'pdf') {
      return await exportarPdf(config);
    } else if (fmt === 'excel' || fmt === 'xlsx') {
      return await exportarExcel(config);
    } else if (fmt === 'word' || fmt === 'docx') {
      return await exportarWord(config);
    } else {
      console.warn('[SigeExport] Formato não reconhecido:', formato);
    }
  }

  // Retornar API pública do módulo
  return {
    exportarPdf,
    exportarExcel,
    exportarWord,
    exportarTabelaHtml,
    extrairDadosTabela,
    obterMetadadosInstituicao,
    descarregarBlob
  };
}));
