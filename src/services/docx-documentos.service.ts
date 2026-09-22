import {
  Document,
  Paragraph,
  TextRun,
  Table,
  TableRow,
  TableCell,
  WidthType,
  AlignmentType,
  HeadingLevel,
  BorderStyle,
  ImageRun,
  Packer,
  PageOrientation
} from 'docx';
import fs from 'fs';
import path from 'path';

/**
 * Obtém o buffer da imagem do logotipo da escola ou fallback para o emblema nacional oficial
 */
function obterBufferLogotipoDocx(logoBase64OuUrl?: string | null): Buffer | null {
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
      console.warn('Aviso: Erro ao descodificar logotipo base64 da escola no DOCX:', e);
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

function criarCabecalhoOficialDocx(escola: {
  nome: string;
  provincia?: string | null;
  distrito?: string | null;
  codigo_escola?: string | null;
  logo_base64?: string | null;
  logo_url?: string | null;
}): Paragraph[] {
  const prov = (escola.provincia || 'Maputo').toUpperCase();
  const dist = (escola.distrito || 'Cidade de Maputo').toUpperCase();
  const nomeEscola = (escola.nome || 'Escola Secundária').toUpperCase();

  const paragraphs: Paragraph[] = [];
  const logoBuf = obterBufferLogotipoDocx(escola.logo_base64 || escola.logo_url);

  if (logoBuf) {
    try {
      paragraphs.push(
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 140 },
          children: [
            new ImageRun({
              type: 'png',
              data: logoBuf,
              transformation: {
                width: 48,
                height: 48
              }
            })
          ]
        })
      );
    } catch (err) {
      console.warn('Aviso: Erro ao renderizar logo no Word:', err);
    }
  }

  paragraphs.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [
        new TextRun({
          text: 'REPÚBLICA DE MOÇAMBIQUE',
          bold: true,
          size: 24,
          font: 'Arial'
        })
      ]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [
        new TextRun({
          text: `GOVERNO DA PROVÍNCIA DE ${prov}`,
          size: 18,
          font: 'Arial'
        })
      ]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [
        new TextRun({
          text: `SERVIÇO DISTRITAL DE EDUCAÇÃO, JUVENTUDE E TECNOLOGIA DE ${dist}`,
          size: 18,
          font: 'Arial'
        })
      ]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 120 },
      children: [
        new TextRun({
          text: nomeEscola,
          bold: true,
          size: 22,
          font: 'Arial'
        })
      ]
    })
  );

  if (escola.codigo_escola) {
    paragraphs.push(
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 200 },
        children: [
          new TextRun({
            text: `Código Institucional: ${escola.codigo_escola}`,
            size: 16,
            italics: true,
            font: 'Arial'
          })
        ]
      })
    );
  }

  return paragraphs;
}

export class DocxDocumentosService {
  /**
   * Gera Declaração Escolar em DOCX (Word)
   */
  static async gerarDeclaracaoDocx(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null; codigo_escola?: string | null };
    aluno: {
      nome: string;
      apelido?: string | null;
      matricula?: string | null;
      numero_documento?: string | null;
      tipo_documento?: string | null;
      data_nascimento?: Date | string | null;
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
    const nomeCompleto = `${dados.aluno.nome} ${dados.aluno.apelido || ''}`.trim().toUpperCase();
    const docTipo = dados.aluno.tipo_documento || 'B.I.';
    const docNum = dados.aluno.numero_documento || '---';
    const filiacao = dados.aluno.pai && dados.aluno.mae ? `filho(a) de ${dados.aluno.pai} e de ${dados.aluno.mae}` : '';
    const classe = dados.aluno.turma?.grau_ano || 'Ensino Secundário';

    const textoDeclaracao = `Para os devidos efeitos se declara que ${nomeCompleto}, ${filiacao}, portador(a) do ${docTipo} nº ${docNum}, esteve matriculado(a) nesta instituição de ensino no Ano Lectivo de ${dados.anoLectivo}, frequentando a ${classe}, tendo obtido a seguinte situação pedagógica:`;

    const children: any[] = [
      ...criarCabecalhoOficialDocx(dados.escola),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 200, after: 240 },
        children: [
          new TextRun({
            text: 'DECLARAÇÃO OFICIAL COM NOTAS',
            bold: true,
            size: 26,
            font: 'Arial'
          })
        ]
      }),
      new Paragraph({
        alignment: AlignmentType.JUSTIFIED,
        spacing: { after: 240, line: 360 },
        children: [
          new TextRun({
            text: textoDeclaracao,
            size: 22,
            font: 'Arial'
          })
        ]
      })
    ];

    if (dados.comNotas && dados.disciplinas && dados.disciplinas.length > 0) {
      const rows: TableRow[] = [
        new TableRow({
          children: [
            new TableCell({
              width: { size: 70, type: WidthType.PERCENTAGE },
              children: [new Paragraph({ children: [new TextRun({ text: 'DISCIPLINA CURRICULAR', bold: true, size: 20 })] })]
            }),
            new TableCell({
              width: { size: 30, type: WidthType.PERCENTAGE },
              children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'MÉDIA ANUAL (0-20)', bold: true, size: 20 })] })]
            })
          ]
        })
      ];

      dados.disciplinas.forEach(d => {
        rows.push(
          new TableRow({
            children: [
              new TableCell({
                children: [new Paragraph({ children: [new TextRun({ text: d.nome, size: 20 })] })]
              }),
              new TableCell({
                children: [
                  new Paragraph({
                    alignment: AlignmentType.CENTER,
                    children: [new TextRun({ text: d.mfd !== null && d.mfd !== undefined ? `${d.mfd} Valores` : '---', size: 20 })]
                  })
                ]
              })
            ]
          })
        );
      });

      children.push(
        new Table({
          rows,
          width: { size: 100, type: WidthType.PERCENTAGE }
        }),
        new Paragraph({
          spacing: { before: 200, after: 200 },
          children: [
            new TextRun({
              text: `Média Final: ${dados.mediaFinal || '---'} Valores | Resultado: ${dados.resultadoFinal || 'Aprovado'}`,
              bold: true,
              size: 22
            })
          ]
        })
      );
    }

    const dataExtenso = `${dados.escola.distrito || 'Maputo'}, aos ${new Date().getDate()} de ${new Date().toLocaleString('pt-PT', { month: 'long' })} de ${new Date().getFullYear()}.`;

    children.push(
      new Paragraph({
        alignment: AlignmentType.RIGHT,
        spacing: { before: 300, after: 500 },
        children: [new TextRun({ text: dataExtenso, size: 20, italics: true })]
      }),
      new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        borders: {
          top: { style: BorderStyle.NONE },
          bottom: { style: BorderStyle.NONE },
          left: { style: BorderStyle.NONE },
          right: { style: BorderStyle.NONE },
          insideHorizontal: { style: BorderStyle.NONE },
          insideVertical: { style: BorderStyle.NONE }
        },
        rows: [
          new TableRow({
            children: [
              new TableCell({
                children: [
                  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: '_______________________________', size: 20 })] }),
                  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'O Chefe da Secretaria', bold: true, size: 20 })] })
                ]
              }),
              new TableCell({
                children: [
                  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: '_______________________________', size: 20 })] }),
                  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'O Director da Escola', bold: true, size: 20 })] })
                ]
              })
            ]
          })
        ]
      })
    );

    const doc = new Document({
      sections: [{ children }]
    });

    return Packer.toBuffer(doc);
  }

  /**
   * Gera Recibo Oficial de Pagamento em DOCX
   */
  static async gerarReciboDocx(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null; codigo_escola?: string | null };
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
    };
  }): Promise<Buffer> {
    const numRecibo = dados.pagamento.recibo_numero || `REC-${new Date().getFullYear()}-${dados.pagamento.id.substring(0, 8).toUpperCase()}`;
    const dt = dados.pagamento.data_pagamento ? new Date(dados.pagamento.data_pagamento).toLocaleDateString('pt-PT') : new Date().toLocaleDateString('pt-PT');
    const valor = Number(dados.pagamento.valor_pago || dados.pagamento.valor || 0);

    const doc = new Document({
      sections: [
        {
          children: [
            ...criarCabecalhoOficialDocx(dados.escola),
            new Paragraph({
              alignment: AlignmentType.CENTER,
              spacing: { before: 200, after: 100 },
              children: [
                new TextRun({ text: 'RECIBO OFICIAL DE PAGAMENTO', bold: true, size: 26 }),
                new TextRun({ text: `\nNº DE SÉRIE: ${numRecibo}`, size: 20 })
              ]
            }),
            new Paragraph({
              spacing: { before: 200, after: 100 },
              children: [
                new TextRun({ text: `Aluno: `, bold: true, size: 22 }),
                new TextRun({ text: `${dados.aluno.nome.toUpperCase()}\n`, size: 22 }),
                new TextRun({ text: `Nº Matrícula: `, bold: true, size: 20 }),
                new TextRun({ text: `${dados.aluno.matricula || '---'} | `, size: 20 }),
                new TextRun({ text: `Turma: `, bold: true, size: 20 }),
                new TextRun({ text: `${dados.aluno.turma?.grau_ano || ''} - ${dados.aluno.turma?.nome || ''}\n`, size: 20 }),
                new TextRun({ text: `Data de Pagamento: `, bold: true, size: 20 }),
                new TextRun({ text: `${dt} | `, size: 20 }),
                new TextRun({ text: `Método: `, bold: true, size: 20 }),
                new TextRun({ text: `${dados.pagamento.metodo_pagamento || 'Numerário'}\n`, size: 20 }),
                new TextRun({ text: `Descrição: `, bold: true, size: 20 }),
                new TextRun({ text: `${dados.pagamento.descricao} (${dados.pagamento.mes_referencia})\n`, size: 20 }),
                new TextRun({ text: `VALOR LIQUIDADO: `, bold: true, size: 24 }),
                new TextRun({ text: `${valor.toFixed(2)} MT`, bold: true, size: 24 })
              ]
            }),
            new Paragraph({
              spacing: { before: 400 },
              alignment: AlignmentType.CENTER,
              children: [
                new TextRun({ text: '________________________________________\n', size: 20 }),
                new TextRun({ text: 'A Tesouraria / Secretaria Escolar', bold: true, size: 20 })
              ]
            })
          ]
        }
      ]
    });

    return Packer.toBuffer(doc);
  }

  /**
   * Gera Acta de Conselho de Avaliação em DOCX (com campos opcionais e trimestres condicionados)
   */
  static async gerarActaDocx(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null; codigo_escola?: string | null };
    turma: { nome: string; grau_ano: string; ano_letivo: string; director_turma?: string };
    conselho: {
      data?: string;
      prazo?: string;
      director_turma?: string;
    };
    trimestresComNotas: { t1: boolean; t2: boolean; t3: boolean; fimAno: boolean };
    estatisticaAproveitamento?: any;
  }): Promise<Buffer> {
    const dt = dados.conselho.data || '___/___/2026';
    const dir = dados.conselho.director_turma || dados.turma.director_turma || '____________________';

    const children: any[] = [
      ...criarCabecalhoOficialDocx(dados.escola),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 200, after: 120 },
        children: [
          new TextRun({
            text: `ACTA DA SESSÃO DO CONSELHO DE AVALIAÇÃO — ${dados.turma.grau_ano} ${dados.turma.nome}`,
            bold: true,
            size: 24
          })
        ]
      }),
      new Paragraph({
        alignment: AlignmentType.JUSTIFIED,
        spacing: { after: 200, line: 360 },
        children: [
          new TextRun({
            text: `Aos ${dt}, reuniu-se ordinariamente o Conselho de Avaliação da turma ${dados.turma.grau_ano} ${dados.turma.nome}, sob a presidência de ${dir}, para proceder ao apuramento e análise dos resultados pedagógicos da turma no ano lectivo de ${dados.turma.ano_letivo}. ${dados.conselho.prazo ? `Prazo de homologação estipulado: ${dados.conselho.prazo}.` : ''}`,
            size: 22
          })
        ]
      })
    ];

    if (dados.trimestresComNotas.t1 && dados.estatisticaAproveitamento?.t1) {
      const apr = dados.estatisticaAproveitamento.t1;
      children.push(
        new Paragraph({
          children: [
            new TextRun({ text: '1. Síntese do 1º Trimestre: ', bold: true, size: 22 }),
            new TextRun({ text: `Aprovados: ${apr.aprovados?.hm || 0} (${apr.aprovados?.pct || 0}%) | Reprovados: ${apr.reprovados?.hm || 0} (${apr.reprovados?.pct || 0}%)`, size: 22 })
          ]
        })
      );
    }

    if (dados.trimestresComNotas.t2 && dados.estatisticaAproveitamento?.t2) {
      const apr = dados.estatisticaAproveitamento.t2;
      children.push(
        new Paragraph({
          children: [
            new TextRun({ text: '2. Síntese do 2º Trimestre: ', bold: true, size: 22 }),
            new TextRun({ text: `Aprovados: ${apr.aprovados?.hm || 0} (${apr.aprovados?.pct || 0}%) | Reprovados: ${apr.reprovados?.hm || 0} (${apr.reprovados?.pct || 0}%)`, size: 22 })
          ]
        })
      );
    }

    if (dados.trimestresComNotas.t3 && dados.estatisticaAproveitamento?.t3) {
      const apr = dados.estatisticaAproveitamento.t3;
      children.push(
        new Paragraph({
          children: [
            new TextRun({ text: '3. Síntese do 3º Trimestre: ', bold: true, size: 22 }),
            new TextRun({ text: `Aprovados: ${apr.aprovados?.hm || 0} (${apr.aprovados?.pct || 0}%) | Reprovados: ${apr.reprovados?.hm || 0} (${apr.reprovados?.pct || 0}%)`, size: 22 })
          ]
        })
      );
    }

    children.push(
      new Paragraph({
        alignment: AlignmentType.JUSTIFIED,
        spacing: { before: 200, after: 400 },
        children: [
          new TextRun({
            text: 'Concluída a apreciação pedagógica, foram homologadas as classificações pelo conselho pedagógico, lavrando-se a presente acta para constar.',
            size: 22
          })
        ]
      }),
      new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        borders: {
          top: { style: BorderStyle.NONE },
          bottom: { style: BorderStyle.NONE },
          left: { style: BorderStyle.NONE },
          right: { style: BorderStyle.NONE },
          insideHorizontal: { style: BorderStyle.NONE },
          insideVertical: { style: BorderStyle.NONE }
        },
        rows: [
          new TableRow({
            children: [
              new TableCell({
                children: [
                  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: '_______________________________', size: 20 })] }),
                  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'O Director de Turma', bold: true, size: 20 })] })
                ]
              }),
              new TableCell({
                children: [
                  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: '_______________________________', size: 20 })] }),
                  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'O Director da Escola', bold: true, size: 20 })] })
                ]
              })
            ]
          })
        ]
      })
    );

    const doc = new Document({
      sections: [{ children }]
    });

    return Packer.toBuffer(doc);
  }

  /**
   * Gera Pauta Geral Oficial da Turma em formato Microsoft Word (DOCX)
   * Sem qualquer ícone, formato oficial governamental MINEDH.
   */
  static async gerarPautaDocx(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null; codigo_escola?: string | null; logo_base64?: string | null; logo_url?: string | null };
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
  }): Promise<Buffer> {
    const children: (Paragraph | Table)[] = [];
    children.push(...criarCabecalhoOficialDocx(dados.escola));

    children.push(
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 100, after: 80 },
        children: [
          new TextRun({
            text: `PAUTA GERAL DE AVALIAÇÃO — ${dados.turma.grau_ano} ${dados.turma.nome}`,
            bold: true,
            size: 24
          })
        ]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 200 },
        children: [
          new TextRun({
            text: `Ano Lectivo: ${dados.turma.ano_letivo} | Turno: ${dados.turma.turno || 'Diurno'} | Director de Turma: ${dados.turma.director_turma || 'Não atribuído'}`,
            size: 18,
            italics: true
          })
        ]
      })
    );

    // Tabela de Alunos e Notas
    const headerRowCells = [
      new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'Nº', bold: true, size: 16 })] })] }),
      new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'Matrícula', bold: true, size: 16 })] })] }),
      new TableCell({ children: [new Paragraph({ alignment: AlignmentType.LEFT, children: [new TextRun({ text: 'Nome Completo', bold: true, size: 16 })] })] }),
      new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'Sexo', bold: true, size: 16 })] })] }),
      new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'T1', bold: true, size: 16 })] })] }),
      new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'T2', bold: true, size: 16 })] })] }),
      new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'T3', bold: true, size: 16 })] })] }),
      new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'Média Final', bold: true, size: 16 })] })] }),
      new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'Resultado', bold: true, size: 16 })] })] })
    ];

    const rows: TableRow[] = [
      new TableRow({
        tableHeader: true,
        children: headerRowCells
      })
    ];

    dados.alunos.forEach(a => {
      const fmt = (v?: number | null) => (v !== null && v !== undefined && v > 0) ? String(v) : '-';
      const resText = a.resultadoFinal === 'A' ? 'Aprovado' : (a.resultadoFinal === 'R' ? 'Reprovado' : a.resultadoFinal);

      rows.push(
        new TableRow({
          children: [
            new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: String(a.numero), size: 16 })] })] }),
            new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: a.matricula, size: 16 })] })] }),
            new TableCell({ children: [new Paragraph({ alignment: AlignmentType.LEFT, children: [new TextRun({ text: a.nome.toUpperCase(), size: 16 })] })] }),
            new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: a.genero || 'M', size: 16 })] })] }),
            new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: fmt(a.mediasTrimestrais.t1), size: 16 })] })] }),
            new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: fmt(a.mediasTrimestrais.t2), size: 16 })] })] }),
            new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: fmt(a.mediasTrimestrais.t3), size: 16 })] })] }),
            new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: a.mediaFinalGeral > 0 ? String(a.mediaFinalGeral) : '-', bold: true, size: 16 })] })] }),
            new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: resText, bold: true, size: 16 })] })] })
          ]
        })
      );
    });

    children.push(
      new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        rows
      })
    );

    // Rodapé de Assinaturas
    children.push(
      new Paragraph({ spacing: { before: 300, after: 100 }, children: [] }),
      new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        borders: {
          top: { style: BorderStyle.NONE },
          bottom: { style: BorderStyle.NONE },
          left: { style: BorderStyle.NONE },
          right: { style: BorderStyle.NONE },
          insideHorizontal: { style: BorderStyle.NONE },
          insideVertical: { style: BorderStyle.NONE }
        },
        rows: [
          new TableRow({
            children: [
              new TableCell({
                children: [
                  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: '_______________________________', size: 18 })] }),
                  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'O Director de Turma', bold: true, size: 18 })] })
                ]
              }),
              new TableCell({
                children: [
                  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: '_______________________________', size: 18 })] }),
                  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'O Director Adjunto Pedagógico', bold: true, size: 18 })] })
                ]
              }),
              new TableCell({
                children: [
                  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: '_______________________________', size: 18 })] }),
                  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'O Director da Escola', bold: true, size: 18 })] })
                ]
              })
            ]
          })
        ]
      })
    );

    const doc = new Document({
      sections: [{
        properties: {
          page: {
            size: {
              orientation: PageOrientation.LANDSCAPE
            }
          }
        },
        children
      }]
    });

    return Packer.toBuffer(doc);
  }
}
