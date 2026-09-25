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
          font: 'Times New Roman'
        })
      ]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [
        new TextRun({
          text: `GOVERNO DA PROVÍNCIA DE ${prov}`,
          size: 18,
          font: 'Times New Roman'
        })
      ]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [
        new TextRun({
          text: `SERVIÇO DISTRITAL DE EDUCAÇÃO, JUVENTUDE E TECNOLOGIA DE ${dist}`,
          size: 18,
          font: 'Times New Roman'
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
          font: 'Times New Roman'
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
            font: 'Times New Roman'
          })
        ]
      })
    );
  }

  return paragraphs;
}

const MARGEM_PADRAO_2CM_DOCX = {
  top: 1134,
  bottom: 1134,
  left: 1134,
  right: 1134
};

const ESTILOS_PADRAO_TIMES = {
  default: {
    document: {
      run: {
        font: 'Times New Roman',
        size: 24 // 12pt oficial
      },
      paragraph: {
        spacing: {
          line: 360, // 1.5 do Word
          lineRule: 'auto' as const
        }
      }
    }
  }
};

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
    const pai = dados.aluno.pai || '...........................................';
    const mae = dados.aluno.mae || '...........................................';
    const classe = dados.aluno.turma?.grau_ano || '10ª Classe';
    const anoLectivo = dados.anoLectivo || '2026';

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
            font: 'Times New Roman'
          })
        ]
      }),
      new Paragraph({
        alignment: AlignmentType.JUSTIFIED,
        spacing: { after: 240, line: 360 },
        children: [
          new TextRun({ text: 'Para os devidos efeitos se declara que ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: nomeCompleto, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ', filho(a) de ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: pai, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ' e de ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: mae, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ', portador(a) do ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: docTipo, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ' número ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: docNum, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ', concluiu com aproveitamento a ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: classe, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ' neste estabelecimento de ensino, no ano lectivo de ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: anoLectivo, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ', com as seguintes classificações:', font: 'Times New Roman', size: 24 })
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
      styles: ESTILOS_PADRAO_TIMES,
      sections: [{
        properties: {
          page: {
            margin: MARGEM_PADRAO_2CM_DOCX
          }
        },
        children
      }]
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
      styles: ESTILOS_PADRAO_TIMES,
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
            size: 24 // 12pt oficial
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
            size: 24 // 12pt oficial
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
      styles: ESTILOS_PADRAO_TIMES,
      sections: [{ children }]
    });

    return Packer.toBuffer(doc);
  }

  /**
   * Gera Pauta Geral Oficial da Turma em formato Microsoft Word (DOCX)
   * Sem qualquer ícone, formato oficial governamental MEC.
   */
  static async gerarPautaDocx(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null; codigo_escola?: string | null; logo_base64?: string | null; logo_url?: string | null };
    turma: { nome: string; grau_ano: string; ano_letivo: string; turno?: string; director_turma?: string };
    disciplinas: Array<{ id: string; nome: string; codigo: string }>;
    alunos: Array<{
      numero: number;
      matricula: string;
      nome: string;
      apelido?: string;
      nomeCompleto?: string;
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
        spacing: { after: 1134 }, // Espaçamento de 2 cm (1134 dxa)
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
      new TableCell({ children: [new Paragraph({ alignment: AlignmentType.LEFT, children: [new TextRun({ text: 'Nome Completo do Aluno', bold: true, size: 16 })] })] }),
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
      const resText = a.resultadoFinal === 'A' || a.resultadoFinal === 'Aprovado' ? 'Aprovado' : (a.resultadoFinal === 'R' || a.resultadoFinal === 'Reprovado' ? 'Reprovado' : (a.resultadoFinal || 'Aprovado'));
      const isAprovado = resText === 'Aprovado';
      const nomeCompleto = (a.nomeCompleto || `${a.nome} ${a.apelido || ''}`).trim().toUpperCase();

      rows.push(
        new TableRow({
          children: [
            new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: String(a.numero), size: 16 })] })] }),
            new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: a.matricula, size: 16 })] })] }),
            new TableCell({ children: [new Paragraph({ alignment: AlignmentType.LEFT, children: [new TextRun({ text: nomeCompleto, size: 16 })] })] }),
            new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: a.genero || 'M', size: 16 })] })] }),
            new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: fmt(a.mediasTrimestrais.t1), size: 16 })] })] }),
            new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: fmt(a.mediasTrimestrais.t2), size: 16 })] })] }),
            new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: fmt(a.mediasTrimestrais.t3), size: 16 })] })] }),
            new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: a.mediaFinalGeral > 0 ? String(a.mediaFinalGeral) : '-', bold: true, size: 16 })] })] }),
            new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: resText, bold: true, color: isAprovado ? '000000' : 'DC2626', size: 16 })] })] })
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
      styles: ESTILOS_PADRAO_TIMES,
      sections: [{
        properties: {
          page: {
            size: {
              orientation: PageOrientation.LANDSCAPE
            },
            margin: MARGEM_PADRAO_2CM_DOCX
          }
        },
        children
      }]
    });

    return Packer.toBuffer(doc);
  }

  /**
   * Gera Certificado Oficial de Habilitações em Microsoft Word (DOCX)
   * Sem ícones, com estrutura idêntica à visualização MEC do sistema.
   */
  static async gerarCertificadoDocx(dados: {
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
    qrcodeData?: string | null;
    disciplinas?: Array<{ disciplina: string; notaFinal?: number | null; mediaFinal?: number | null }>;
  }): Promise<Buffer> {
    const chefeNome = dados.chefeSecretariaNome || 'Glória João Zunguze';
    const chefeCarreira = dados.chefeSecretariaCarreira || 'Técnica Profissional';
    const directorNome = dados.directorNome || 'Pero Chitofo Murrombe';
    const directorCarreira = dados.directorCarreira || 'Especialista de Educação';
    const escolaNome = (dados.escola.nome || 'Escola Secundária').toUpperCase();
    const distrito = dados.escola.distrito || 'Massinga';
    const provincia = dados.escola.provincia || 'Inhambane';
    const alunoNome = (dados.aluno.nomeCompleto || `${dados.aluno.nome} ${dados.aluno.apelido || ''}`).trim().toUpperCase();
    const sexo = ((dados.aluno.genero || 'M').toUpperCase() === 'M') ? 'Masculino' : 'Feminino';
    const alunoDistrito = dados.aluno.distrito || distrito;
    const alunoProvincia = dados.aluno.provincia || provincia;
    const pai = dados.aluno.pai || '...........................................';
    const mae = dados.aluno.mae || '...........................................';
    const anoLectivo = dados.anoLectivo || '2026';
    const grauClasse = dados.grauAno || dados.aluno.turma?.grau_ano || '12ª';
    const area = dados.aluno.turma?.area || 'Ciências e Letras';

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

    const textoDeclarativo = `b) ${chefeNome}, /${chefeCarreira}/, Chefe da secretaria da ${escolaNome}, distrito de ${distrito}, província de ${provincia}, CERTIFICO em cumprimento do despacho exarado em requerimento que fica arquivado nesta secretaria que ${alunoNome}, do Sexo ${sexo}, natural de ${alunoDistrito}, distrito de ${alunoDistrito}, província de ${alunoProvincia}, nascido no dia ${diaNasc} de ${mesNasc} de ${anoNasc}, filho/a de ${pai} e de ${mae}, concluiu nesta escola como aluno c) Interno, em Dezembro de ${anoLectivo}, a ${grauClasse} Classe na área de ${area}, tendo obtido os seguintes resultados:`;

    const children: (Paragraph | Table)[] = [
      ...criarCabecalhoOficialDocx(dados.escola),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 100, after: 60 },
        children: [
          new TextRun({ text: 'REPÚBLICA DE MOÇAMBIQUE', bold: true, size: 22 }),
        ]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 60 },
        children: [
          new TextRun({ text: 'MINISTÉRIO DA EDUCAÇÃO E CULTURA', bold: true, size: 20 }),
        ]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 100 },
        children: [
          new TextRun({ text: 'INSTITUTO NACIONAL DE EXAMES, CERTIFICAÇÃO E EQUIVALÊNCIA', bold: true, size: 18 }),
        ]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 120 },
        children: [
          new TextRun({ text: `a) ${escolaNome}`, italics: true, underline: {}, size: 20 }),
        ]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 200 },
        children: [
          new TextRun({ text: 'CERTIFICADO DE HABILITAÇÕES', bold: true, size: 28, underline: {} }),
        ]
      }),
      new Paragraph({
        alignment: AlignmentType.JUSTIFIED,
        spacing: { after: 200, line: 360 },
        children: [
          new TextRun({ text: 'b) ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: chefeNome, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ', /', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: chefeCarreira, italics: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: '/, Chefe da secretaria da ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: escolaNome, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ', distrito de ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: distrito, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ', província de ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: provincia, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ', CERTIFICO em cumprimento do despacho exarado em requerimento que fica arquivado nesta secretaria que ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: alunoNome, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ', do Sexo ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: sexo, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ', natural de ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: alunoDistrito, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ', distrito de ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: alunoDistrito, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ', província de ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: alunoProvincia, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ', nascido no dia ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: diaNasc, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ' de ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: mesNasc, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ' de ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: anoNasc, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ', filho/a de ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: pai, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ' e de ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: mae, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ', concluiu nesta escola como aluno c) ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: 'Interno', bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ', em ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: `Dezembro de ${anoLectivo}`, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ', a ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: grauClasse, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ' na área de ', font: 'Times New Roman', size: 24 }),
          new TextRun({ text: area, bold: true, font: 'Times New Roman', size: 24 }),
          new TextRun({ text: ', tendo obtido os seguintes resultados:', font: 'Times New Roman', size: 24 })
        ]
      })
    ];

    // Mapeamento das notas
    const notasMap = new Map<string, number>();
    (dados.disciplinas || []).forEach(d => {
      const val = d.notaFinal !== undefined && d.notaFinal !== null ? d.notaFinal : (d.mediaFinal !== undefined ? d.mediaFinal : null);
      if (val !== null && val !== undefined) {
        notasMap.set((d.disciplina || '').toLowerCase().trim(), Number(val));
      }
    });

    const obterNota = (nome: string) => {
      const k = nome.toLowerCase().trim();
      for (const [ch, vl] of notasMap.entries()) {
        if (ch.includes(k) || k.includes(ch)) {
          return Number.isInteger(vl) ? String(vl) : vl.toFixed(1);
        }
      }
      return '---';
    };

    const col1 = ['Português', 'Inglês', 'Francês', 'História', 'Geografia', 'Intr. Filosofia'];
    const col2 = ['Matemática', 'Química', 'Física', 'Biologia', 'Desenho e Geom. Desc.', 'Educação Visual'];
    const col3 = ['Educação Física', 'TIC\'s', 'Noções Empreend.', 'Agropecuária', 'Psicopedagogia'];

    const maxRows = Math.max(col1.length, col2.length, col3.length);
    const tableRows: TableRow[] = [];

    for (let i = 0; i < maxRows; i++) {
      const d1 = col1[i] || '';
      const n1 = d1 ? obterNota(d1) : '';
      const d2 = col2[i] || '';
      const n2 = d2 ? obterNota(d2) : '';
      const d3 = col3[i] || '';
      const n3 = d3 ? obterNota(d3) : '';

      tableRows.push(
        new TableRow({
          children: [
            new TableCell({
              children: [
                new Paragraph({
                  children: [
                    new TextRun({ text: d1, size: 18 }),
                    new TextRun({ text: d1 ? ` ( ${n1} ) val` : '', bold: true, size: 18 })
                  ]
                })
              ]
            }),
            new TableCell({
              children: [
                new Paragraph({
                  children: [
                    new TextRun({ text: d2, size: 18 }),
                    new TextRun({ text: d2 ? ` ( ${n2} ) val` : '', bold: true, size: 18 })
                  ]
                })
              ]
            }),
            new TableCell({
              children: [
                new Paragraph({
                  children: [
                    new TextRun({ text: d3, size: 18 }),
                    new TextRun({ text: d3 ? ` ( ${n3} ) val` : '', bold: true, size: 18 })
                  ]
                })
              ]
            })
          ]
        })
      );
    }

    children.push(
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
        rows: tableRows
      })
    );

    const mediaGlobalVal = Math.round(Number(dados.mediaGlobal !== undefined ? dados.mediaGlobal : 14) || 14);
    children.push(
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 180, after: 140 },
        children: [
          new TextRun({ text: `Média Global: ( ${mediaGlobalVal} ) Valores`, bold: true, size: 24 })
        ]
      }),
      new Paragraph({
        alignment: AlignmentType.JUSTIFIED,
        spacing: { after: 180, line: 320 },
        children: [
          new TextRun({
            text: `Os resultados constam da pauta nº ${dados.pautaNumero || '01'} e do livro de Termo de Exames nº ${dados.termoExames || '124'}, código do aluno ${dados.aluno.matricula || '-'}.\nE, por ser verdade passo o presente certificado que assino e autentico a tinta de óleo/selo branco em uso neste Estabelecimento de Ensino.`,
            size: 20
          })
        ]
      })
    );

    const agora = new Date();
    const meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
    const dataFormatada = `${distrito}, aos ${agora.getDate()} de ${meses[agora.getMonth()]} de ${agora.getFullYear()}`;

    children.push(
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 240 },
        children: [new TextRun({ text: dataFormatada, size: 20 })]
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
                  new Paragraph({ alignment: AlignmentType.LEFT, children: [new TextRun({ text: 'Extraí: _____________________', size: 18 })] }),
                  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80 }, children: [new TextRun({ text: 'O Chefe da Secretaria', bold: true, size: 18 })] }),
                  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: '_______________________________', size: 18 })] }),
                  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: chefeNome, bold: true, size: 18 })] }),
                  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: `/${chefeCarreira}/`, italics: true, size: 16 })] })
                ]
              }),
              new TableCell({
                children: (() => {
                  const conferiChildren: Paragraph[] = [
                    new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'Conferi: _____________________', size: 18 })] })
                  ];
                  if (dados.qrcodeData) {
                    try {
                      const base64Clean = dados.qrcodeData.replace(/^data:image\/\w+;base64,/, '');
                      const qrBuffer = Buffer.from(base64Clean, 'base64');
                      conferiChildren.push(
                        new Paragraph({
                          alignment: AlignmentType.CENTER,
                          spacing: { before: 80, after: 60 },
                          children: [
                            new ImageRun({
                              type: 'png',
                              data: qrBuffer,
                              transformation: { width: 55, height: 55 }
                            })
                          ]
                        })
                      );
                    } catch (err) {
                      console.warn('Aviso: Erro ao embutir QR Code no Word:', err);
                    }
                  }
                  conferiChildren.push(
                    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60 }, children: [new TextRun({ text: dados.codigoAutenticidade || '', size: 15, italics: true })] })
                  );
                  return conferiChildren;
                })()
              }),
              new TableCell({
                children: [
                  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'O Director da Escola', bold: true, size: 18 })] }),
                  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80 }, children: [new TextRun({ text: '_______________________________', size: 18 })] }),
                  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: directorNome, bold: true, size: 18 })] }),
                  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: `/${directorCarreira}/`, italics: true, size: 16 })] })
                ]
              })
            ]
          })
        ]
      })
    );

    const doc = new Document({
      styles: ESTILOS_PADRAO_TIMES,
      sections: [{
        properties: {
          page: {
            margin: MARGEM_PADRAO_2CM_DOCX
          }
        },
        children
      }]
    });

    return Packer.toBuffer(doc);
  }

  /**
   * Gera Boletim de Aproveitamento Escolar em Microsoft Word (DOCX)
   * Idêntico ao modelo oficial da imagem (media_1790202056793.png):
   * - Margens de 2 cm (1134 dxa)
   * - Espaçamento de 2 cm entre cabeçalho e título
   * - Tabela de notas com '---' para ausentes, linha de Média Global com fundo #E5E7EB,
   * - Decisão do Conselho e assinaturas de Director de Turma e Director da Escola.
   */
  static async gerarBoletimDocx(dados: {
    escola: { nome: string; provincia?: string | null; distrito?: string | null; codigo_escola?: string | null; nif_cnpj?: string | null; logo_base64?: string | null; logo_url?: string | null };
    anoLetivo: string;
    aluno: {
      nome: string;
      matricula?: string | null;
      turma?: string | { nome?: string; grau_ano?: string; turno?: string } | null;
      grau?: string;
    };
    disciplinas: Array<{
      nome: string;
      t1?: number | null;
      t2?: number | null;
      t3?: number | null;
      mediaFinal?: number | null;
      mfd?: number | null;
      faltas?: number;
      anotacao?: string | null;
    }>;
    mediaGeral?: number;
    medias?: { t1?: number | null; t2?: number | null; t3?: number | null; mfd?: number | null };
    resultado?: string;
    resultadoFinal?: string;
    observacao?: string;
    dataExtenso?: string;
  }): Promise<Buffer> {
    const turmaObj = typeof dados.aluno.turma === 'object' && dados.aluno.turma ? dados.aluno.turma : null;
    const turmaStr = turmaObj ? `${turmaObj.grau_ano || ''} - ${turmaObj.nome || ''}` : (dados.aluno.turma || '-');
    const turnoStr = turmaObj?.turno || 'Manhã';
    const finalResultado = dados.resultadoFinal || dados.resultado || (dados.mediaGeral && dados.mediaGeral >= 9.5 ? 'Aprovado' : 'Em Avaliação');
    const finalMediaGeral = dados.mediaGeral || dados.medias?.mfd || (dados.disciplinas.length > 0 ? Math.round(dados.disciplinas.reduce((acc, d) => acc + (d.mfd || d.mediaFinal || 0), 0) / dados.disciplinas.length) : 14);

    const children: (Paragraph | Table)[] = [
      ...criarCabecalhoOficialDocx(dados.escola),

      // Espaçamento obrigatório de 2 cm (1134 dxa) entre o cabeçalho e onde começa a informação
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 1134, after: 140 },
        children: [
          new TextRun({
            text: `BOLETIM DE APROVEITAMENTO ESCOLAR — ANO LECTIVO ${dados.anoLetivo}`,
            bold: true,
            size: 24,
            font: 'Times New Roman'
          })
        ]
      }),

      // Caixa de Dados do Aluno (idêntico à imagem)
      new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        rows: [
          new TableRow({
            children: [
              new TableCell({
                children: [
                  new Paragraph({
                    children: [
                      new TextRun({ text: 'Nome do Aluno: ', bold: true, size: 20 }),
                      new TextRun({ text: dados.aluno.nome.toUpperCase(), bold: true, size: 20 })
                    ]
                  })
                ]
              }),
              new TableCell({
                children: [
                  new Paragraph({
                    children: [
                      new TextRun({ text: 'Classe / Turma: ', bold: true, size: 20 }),
                      new TextRun({ text: String(turmaStr), size: 20 })
                    ]
                  })
                ]
              })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({
                children: [
                  new Paragraph({
                    children: [
                      new TextRun({ text: 'Nº Matrícula: ', bold: true, size: 20 }),
                      new TextRun({ text: dados.aluno.matricula || '---', size: 20 })
                    ]
                  })
                ]
              }),
              new TableCell({
                children: [
                  new Paragraph({
                    children: [
                      new TextRun({ text: 'Turno: ', bold: true, size: 20 }),
                      new TextRun({ text: String(turnoStr), size: 20 })
                    ]
                  })
                ]
              })
            ]
          })
        ]
      }),

      new Paragraph({ spacing: { before: 140, after: 100 }, children: [] })
    ];

    // Tabela de Disciplinas e Notas (idêntica à imagem)
    const fmtNota = (v?: number | null) => (v !== null && v !== undefined && v > 0) ? String(v) : '---';

    const rowsDisciplinas: TableRow[] = [
      new TableRow({
        tableHeader: true,
        children: [
          new TableCell({ shading: { fill: 'E5E7EB' }, children: [new Paragraph({ alignment: AlignmentType.LEFT, children: [new TextRun({ text: 'DISCIPLINA', bold: true, size: 18 })] })] }),
          new TableCell({ shading: { fill: 'E5E7EB' }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: '1º TRIM', bold: true, size: 18 })] })] }),
          new TableCell({ shading: { fill: 'E5E7EB' }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: '2º TRIM', bold: true, size: 18 })] })] }),
          new TableCell({ shading: { fill: 'E5E7EB' }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: '3º TRIM', bold: true, size: 18 })] })] }),
          new TableCell({ shading: { fill: 'E5E7EB' }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'MÉD. ANUAL', bold: true, size: 18 })] })] }),
          new TableCell({ shading: { fill: 'E5E7EB' }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'SITUAÇÃO', bold: true, size: 18 })] })] })
        ]
      })
    ];

    dados.disciplinas.forEach(d => {
      const mfdVal = d.mfd !== null && d.mfd !== undefined ? d.mfd : d.mediaFinal;
      const sitVal = d.anotacao || (mfdVal !== null && mfdVal !== undefined && mfdVal >= 9.5 ? 'Aprovado' : (mfdVal ? 'Reprovado' : '---'));
      const isNeg = mfdVal !== null && mfdVal !== undefined && mfdVal > 0 && mfdVal < 9.5;

      rowsDisciplinas.push(
        new TableRow({
          children: [
            new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: d.nome, size: 18 })] })] }),
            new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: fmtNota(d.t1), size: 18 })] })] }),
            new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: fmtNota(d.t2), size: 18 })] })] }),
            new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: fmtNota(d.t3), size: 18 })] })] }),
            new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: fmtNota(mfdVal), bold: true, color: isNeg ? 'DC2626' : undefined, size: 19 })] })] }),
            new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: sitVal, size: 18 })] })] })
          ]
        })
      );
    });

    // Linha de Média Global do Período (com fundo #E5E7EB idêntico à imagem)
    rowsDisciplinas.push(
      new TableRow({
        children: [
          new TableCell({ shading: { fill: 'E5E7EB' }, children: [new Paragraph({ alignment: AlignmentType.LEFT, children: [new TextRun({ text: 'MÉDIA GLOBAL DO PERÍODO', bold: true, size: 18 })] })] }),
          new TableCell({ shading: { fill: 'E5E7EB' }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: '---', size: 18 })] })] }),
          new TableCell({ shading: { fill: 'E5E7EB' }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: '---', size: 18 })] })] }),
          new TableCell({ shading: { fill: 'E5E7EB' }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: '---', size: 18 })] })] }),
          new TableCell({ shading: { fill: 'E5E7EB' }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: String(finalMediaGeral), bold: true, size: 19 })] })] }),
          new TableCell({ shading: { fill: 'E5E7EB' }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: finalResultado, bold: true, size: 19 })] })] })
        ]
      })
    );

    children.push(
      new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        rows: rowsDisciplinas
      }),
      new Paragraph({ spacing: { before: 160, after: 120 }, children: [] }),

      // Decisão do Conselho (idêntico à imagem)
      new Paragraph({
        spacing: { before: 140, after: 360 },
        children: [
          new TextRun({ text: 'Decisão do Conselho: ', bold: true, size: 20, font: 'Times New Roman' }),
          new TextRun({ text: dados.observacao || `Resultado pedagógico do aluno: ${finalResultado} com média global de ${finalMediaGeral} valores.`, size: 20, font: 'Times New Roman' })
        ]
      }),

      // Assinaturas de O Director de Turma e O Director da Escola
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
                  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'O Director de Turma', bold: true, size: 19 })] })
                ]
              }),
              new TableCell({
                children: [
                  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: '_______________________________', size: 18 })] }),
                  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'O Director da Escola', bold: true, size: 19 })] })
                ]
              })
            ]
          })
        ]
      })
    );

    const doc = new Document({
      styles: ESTILOS_PADRAO_TIMES,
      sections: [{
        properties: {
          page: {
            margin: MARGEM_PADRAO_2CM_DOCX
          }
        },
        children
      }]
    });

    return Packer.toBuffer(doc);
  }
}
