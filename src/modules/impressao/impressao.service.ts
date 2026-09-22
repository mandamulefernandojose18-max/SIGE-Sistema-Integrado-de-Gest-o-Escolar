import crypto from 'crypto';
import prisma from '../../config/database';
import { avaliarAprovacaoPauta } from '../../utils/avaliacoes-mocambique';
import { generateQrCodeDataUrl } from '../../utils/qrcode.util';
import { ExportExcelService } from '../../services/export-excel.service';
import { PdfKitDocumentosService } from '../../services/pdfkit-documentos.service';
import { DocxDocumentosService } from '../../services/docx-documentos.service';
import { SheetJsDocumentosService } from '../../services/sheetjs-documentos.service';

function formatarDataHoraCarimbo(d: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  const dia = pad(d.getDate());
  const mes = pad(d.getMonth() + 1);
  const ano = d.getFullYear();
  const h = pad(d.getHours());
  const m = pad(d.getMinutes());
  const s = pad(d.getSeconds());
  return `${dia}/${mes}/${ano} ${h}:${m}:${s}`;
}

function formatarDataExtenso(d: Date = new Date(), localidade = 'Maputo'): string {
  const meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
  return `${localidade}, aos ${d.getDate()} de ${meses[d.getMonth()]} de ${d.getFullYear()}`;
}

export class ImpressaoService {
  async registrarEmissao(escolaId: string, tipo: string, descricao: string, usuarioId?: string, conteudoJson?: any) {
    const jsonStr = conteudoJson ? (typeof conteudoJson === 'string' ? conteudoJson : JSON.stringify(conteudoJson)) : null;
    return prisma.logImpressao.create({
      data: {
        escola_id: escolaId,
        usuario_id: usuarioId,
        tipo_documento: tipo,
        descricao,
        conteudo_json: jsonStr
      }
    });
  }

  async gerarBoletimAluno(escolaId: string, alunoId: string, anoLetivo = '2026', usuarioId?: string) {
    const aluno = await prisma.aluno.findFirst({
      where: { id: alunoId, escola_id: escolaId },
      include: {
        escola: true,
        turma: true,
        notas: {
          include: { disciplina: true },
          orderBy: { periodo: 'asc' }
        }
      }
    });

    if (!aluno) throw new Error('Aluno não encontrado');

    const nomeProprietario = `${aluno.nome}_${aluno.apelido || ''}`.trim().replace(/\s+/g, '_');

    // Agrupar notas por disciplina
    const disciplinasMap: Record<string, {
      id: string;
      nome: string;
      codigo: string;
      t1: number;
      t2: number;
      t3: number;
      mediaFinal: number;
      faltas: number;
    }> = {};

    aluno.notas.forEach(n => {
      if (!disciplinasMap[n.disciplina_id]) {
        disciplinasMap[n.disciplina_id] = {
          id: n.disciplina_id,
          nome: n.disciplina.nome,
          codigo: n.disciplina.codigo,
          t1: 0,
          t2: 0,
          t3: 0,
          mediaFinal: 0,
          faltas: 0
        };
      }

      if (n.periodo === '1_TRIMESTRE') disciplinasMap[n.disciplina_id].t1 = n.media_final;
      else if (n.periodo === '2_TRIMESTRE') disciplinasMap[n.disciplina_id].t2 = n.media_final;
      else if (n.periodo === '3_TRIMESTRE') disciplinasMap[n.disciplina_id].t3 = n.media_final;

      disciplinasMap[n.disciplina_id].faltas += n.faltas;
    });

    let somaMedias = 0;
    const disciplinasArray = Object.values(disciplinasMap).map(d => {
      const notasValidas = [d.t1, d.t2, d.t3].filter(v => v > 0);
      const media = notasValidas.length > 0 ? Number((notasValidas.reduce((a, b) => a + b, 0) / notasValidas.length).toFixed(1)) : 0;
      d.mediaFinal = media;
      somaMedias += media;
      return d;
    });

    const totalD = disciplinasArray.length;
    const mediaGeralAluno = totalD > 0 ? Math.round(somaMedias / totalD) : 0;
    const resultado = mediaGeralAluno >= 9.5 ? 'Aprovado' : 'Reprovado';

    await this.registrarEmissao(escolaId, 'BOLETIM', `Boletim Escolar - ${aluno.nome} (${aluno.matricula})`, usuarioId);

    // Requisito 7: Sem carimbo de horas no boletim
    return {
      titulo: 'BOLETIM OFICIAL DE AVALIAÇÃO TRIMESTRAL',
      anoLetivo,
      filename: `Boletim_${nomeProprietario}_${anoLetivo}.pdf`,
      escola: aluno.escola,
      aluno: {
        id: aluno.id,
        nome: `${aluno.nome} ${aluno.apelido || ''}`.trim(),
        matricula: aluno.matricula,
        genero: aluno.genero,
        nuit: aluno.nuit,
        numero_documento: aluno.numero_documento,
        turma: aluno.turma?.nome || 'Sem Turma',
        grau: aluno.turma?.grau_ano || '-'
      },
      disciplinas: disciplinasArray,
      mediaGeral: mediaGeralAluno,
      resultado,
      dataExtenso: formatarDataExtenso(new Date(), aluno.escola.distrito || aluno.escola.provincia || 'Maputo')
    };
  }

  async gerarReciboPagamento(escolaId: string, pagamentoId: string, usuarioId?: string) {
    const pagamento = await prisma.pagamento.findFirst({
      where: { id: pagamentoId, escola_id: escolaId },
      include: {
        aluno: { include: { turma: true } },
        escola: true
      }
    });

    if (!pagamento) throw new Error('Pagamento não encontrado');

    const agora = new Date();
    const nomeProprietario = pagamento.aluno
      ? `${pagamento.aluno.nome}_${pagamento.aluno.apelido || ''}`.trim().replace(/\s+/g, '_')
      : `Candidato_${pagamento.id.slice(0, 8)}`;
    const ano = agora.getFullYear();

    await this.registrarEmissao(
      escolaId,
      'RECIBO',
      `Recibo ${pagamento.recibo_numero || pagamento.id} - ${pagamento.aluno?.nome || 'Inscrição'}`,
      usuarioId
    );

    const alunoDados = pagamento.aluno
      ? {
          id: pagamento.aluno.id,
          nome: pagamento.aluno.nome,
          apelido: pagamento.aluno.apelido || '',
          matricula: pagamento.aluno.matricula,
          turma: pagamento.aluno.turma,
          nuit: pagamento.aluno.nuit,
          numero_documento: pagamento.aluno.numero_documento,
          nomeCompleto: `${pagamento.aluno.nome} ${pagamento.aluno.apelido || ''}`.trim()
        }
      : {
          id: '',
          nome: 'Candidato / Inscrição',
          apelido: '',
          matricula: 'PENDENTE',
          turma: null,
          nuit: null,
          numero_documento: null,
          nomeCompleto: 'Candidato / Inscrição'
        };

    // Requisito 7: Data e hora de impressão OBRIGATÓRIA no recibo (Ex.: 12/09/2026 08:45:25)
    return {
      titulo: 'RECIBO DE PAGAMENTO DE PROPINAS E EMOLUMENTOS',
      reciboNumero: pagamento.recibo_numero || `REC-${pagamento.id.slice(0, 8).toUpperCase()}`,
      filename: `Recibo_${nomeProprietario}_${ano}.pdf`,
      escola: pagamento.escola,
      aluno: alunoDados,
      pagamento: {
        id: pagamento.id,
        descricao: pagamento.descricao,
        mesReferencia: pagamento.mes_referencia,
        valor: pagamento.valor,
        valorMZN: `${pagamento.valor.toLocaleString('pt-PT', { minimumFractionDigits: 2 })} MZN`,
        valorPago: pagamento.valor_pago || pagamento.valor,
        valorPagoMZN: `${(pagamento.valor_pago || pagamento.valor).toLocaleString('pt-PT', { minimumFractionDigits: 2 })} MZN`,
        metodo: pagamento.metodo_pagamento || 'TRANSFERENCIA',
        dataPagamento: pagamento.data_pagamento || agora,
        status: pagamento.status
      },
      carimboDataHora: formatarDataHoraCarimbo(agora),
      dataExtenso: formatarDataExtenso(agora, pagamento.escola.distrito || pagamento.escola.provincia || 'Maputo')
    };
  }

  async gerarFichaAluno(escolaId: string, alunoId: string, usuarioId?: string) {
    const aluno = await prisma.aluno.findFirst({
      where: { id: alunoId, escola_id: escolaId },
      include: {
        escola: true,
        turma: {
          include: {
            director_turma: true,
            director_classe: true
          }
        },
        notas: { include: { disciplina: true } },
        pagamentos: { orderBy: { data_vencimento: 'desc' } }
      }
    });

    if (!aluno) throw new Error('Aluno não encontrado');

    const agora = new Date();
    const nomeProprietario = `${aluno.nome}_${aluno.apelido || ''}`.trim().replace(/\s+/g, '_');
    const ano = agora.getFullYear();

    await this.registrarEmissao(escolaId, 'FICHA_ALUNO', `Ficha Cadastral - ${aluno.nome}`, usuarioId);

    // Requisito 7: Data e hora de impressão OBRIGATÓRIA na ficha (Ex.: 12/09/2026 08:45:25)
    return {
      titulo: 'FICHA GERAL DO ALUNO - REGISTO BIOGRÁFICO',
      filename: `Ficha_${nomeProprietario}_${ano}.pdf`,
      aluno: {
        ...aluno,
        nomeCompleto: `${aluno.nome} ${aluno.apelido || ''}`.trim()
      },
      escola: aluno.escola,
      carimboDataHora: formatarDataHoraCarimbo(agora),
      dataExtenso: formatarDataExtenso(agora, aluno.escola.distrito || aluno.escola.provincia || 'Maputo')
    };
  }

  async gerarDeclaracaoAluno(escolaId: string, alunoId: string, comNotas = true, usuarioId?: string) {
    const aluno = await prisma.aluno.findFirst({
      where: { id: alunoId, escola_id: escolaId },
      include: {
        escola: true,
        turma: {
          include: {
            director_turma: true
          }
        },
        notas: { include: { disciplina: true } }
      }
    });

    if (!aluno) throw new Error('Aluno não encontrado');

    const agora = new Date();
    const ano = aluno.turma?.ano_letivo || String(agora.getFullYear());
    const nomeProprietario = `${aluno.nome}_${aluno.apelido || ''}`.trim().replace(/\s+/g, '_');

    const [director, chefe] = await Promise.all([
      prisma.usuario.findFirst({ where: { escola_id: escolaId, role: 'DIRECTOR_ESCOLA' }, select: { nome: true } }),
      prisma.usuario.findFirst({ where: { escola_id: escolaId, role: 'CHEFE_SECRETARIA' }, select: { nome: true } })
    ]);

    // Consolidar notas por disciplina
    const notasPorDisciplina = new Map<string, number>();
    aluno.notas.forEach(n => {
      notasPorDisciplina.set(n.disciplina.nome, n.media_final);
    });

    const disciplinasAvaliadas: Array<{ disciplina: string; notaFinal: number }> = [];
    notasPorDisciplina.forEach((notaFinal, disciplina) => {
      disciplinasAvaliadas.push({ disciplina, notaFinal });
    });

    const avaliacao = avaliarAprovacaoPauta(disciplinasAvaliadas, aluno.turma?.grau_ano);

    await this.registrarEmissao(escolaId, 'DECLARACAO', `Declaração Escolar - ${aluno.nome}`, usuarioId);

    return {
      titulo: 'DECLARAÇÃO',
      filename: `Declaracao_${nomeProprietario}_${ano}.pdf`,
      escola: aluno.escola,
      aluno: {
        ...aluno,
        nomeCompleto: `${aluno.nome} ${aluno.apelido || ''}`.trim()
      },
      comNotas,
      anoLectivo: ano,
      directorNome: director?.nome || aluno.turma?.director_turma?.nome || 'Director da Escola',
      directorCarreira: 'Especialista de Educação',
      chefeSecretariaNome: chefe?.nome || 'Técnica Profissional',
      disciplinas: disciplinasAvaliadas,
      mediaGlobal: avaliacao.mediaGeral,
      resultadoOficial: avaliacao.resultado,
      siglaResultado: avaliacao.siglaResultado,
      livroRegisto: '01',
      termoExames: '124',
      folha: '32',
      dataExtenso: formatarDataExtenso(agora, aluno.escola.distrito || aluno.escola.provincia || 'Maputo')
    };
  }

  async gerarCertificadoAluno(escolaId: string, alunoId: string, usuarioId?: string) {
    const aluno = await prisma.aluno.findFirst({
      where: { id: alunoId, escola_id: escolaId },
      include: {
        escola: true,
        turma: {
          include: {
            director_turma: true
          }
        },
        notas: { include: { disciplina: true } }
      }
    });

    if (!aluno) throw new Error('Aluno não encontrado');

    const agora = new Date();
    const ano = aluno.turma?.ano_letivo || String(agora.getFullYear());
    const nomeProprietario = `${aluno.nome}_${aluno.apelido || ''}`.trim().replace(/\s+/g, '_');

    const [director, chefe] = await Promise.all([
      prisma.usuario.findFirst({ where: { escola_id: escolaId, role: 'DIRECTOR_ESCOLA' }, select: { nome: true } }),
      prisma.usuario.findFirst({ where: { escola_id: escolaId, role: 'CHEFE_SECRETARIA' }, select: { nome: true } })
    ]);

    const notasPorDisciplina = new Map<string, number>();
    aluno.notas.forEach(n => {
      notasPorDisciplina.set(n.disciplina.nome, n.media_final);
    });

    const disciplinasAvaliadas: Array<{ disciplina: string; notaFinal: number }> = [];
    notasPorDisciplina.forEach((notaFinal, disciplina) => {
      disciplinasAvaliadas.push({ disciplina, notaFinal });
    });

    const avaliacao = avaliarAprovacaoPauta(disciplinasAvaliadas, aluno.turma?.grau_ano);

    await this.registrarEmissao(escolaId, 'CERTIFICADO', `Certificado de Habilitações - ${aluno.nome}`, usuarioId);

    const codigoAutenticidade = `CERT-MZ-${aluno.escola.nif_cnpj || 'MINEDH'}-${aluno.matricula}-${ano}`;
    const qrcodeData = await generateQrCodeDataUrl(codigoAutenticidade).catch(() => '');

    return {
      titulo: 'CERTIFICADO DE HABILITAÇÕES',
      filename: `Certificado_${nomeProprietario}_${ano}.pdf`,
      codigoAutenticidade,
      qrcodeData,
      escola: aluno.escola,
      aluno: {
        ...aluno,
        nomeCompleto: `${aluno.nome} ${aluno.apelido || ''}`.trim()
      },
      grauAno: aluno.turma?.grau_ano || '12ª Classe',
      anoLectivo: ano,
      directorNome: director?.nome || aluno.turma?.director_turma?.nome || 'Pero Chitofo Murrombe',
      directorCarreira: 'Especialista de Educação',
      chefeSecretariaNome: chefe?.nome || 'Glória João Zunguze',
      chefeSecretariaCarreira: 'Técnica Profissional',
      mediaGlobal: avaliacao.mediaGeral,
      resultadoOficial: avaliacao.resultado,
      siglaResultado: avaliacao.siglaResultado,
      livroRegisto: '01',
      termoExames: '124',
      pautaNumero: '01',
      disciplinas: disciplinasAvaliadas,
      dataExtenso: formatarDataExtenso(agora, aluno.escola.distrito || aluno.escola.provincia || 'Massinga')
    };
  }

  async gerarLoteTurma(escolaId: string, turmaId: string, tipoDocumento: 'BOLETIM' | 'DECLARACAO' | 'CERTIFICADO' | 'FICHA', usuarioId?: string) {
    const alunos = await prisma.aluno.findMany({
      where: { escola_id: escolaId, turma_id: turmaId, status: 'ATIVO' },
      select: { id: true, nome: true, matricula: true },
      orderBy: { nome: 'asc' }
    });

    const documentos: any[] = [];
    for (const aluno of alunos) {
      if (tipoDocumento === 'BOLETIM') {
        documentos.push(await this.gerarBoletimAluno(escolaId, aluno.id, undefined, usuarioId));
      } else if (tipoDocumento === 'DECLARACAO') {
        documentos.push(await this.gerarDeclaracaoAluno(escolaId, aluno.id, false, usuarioId));
      } else if (tipoDocumento === 'CERTIFICADO') {
        documentos.push(await this.gerarCertificadoAluno(escolaId, aluno.id, usuarioId));
      } else if (tipoDocumento === 'FICHA') {
        documentos.push(await this.gerarFichaAluno(escolaId, aluno.id, usuarioId));
      }
    }

    return {
      total: documentos.length,
      tipoDocumento,
      turmaId,
      documentos
    };
  }

  async getStats(escolaId: string) {
    const [totalImpressoes, impressoes] = await Promise.all([
      prisma.logImpressao.count({ where: { escola_id: escolaId } }),
      prisma.logImpressao.findMany({
        where: { escola_id: escolaId },
        orderBy: { data_emissao: 'desc' },
        take: 100
      })
    ]);

    const porTipo: Record<string, number> = {
      BOLETIM: 0,
      PAUTA: 0,
      RECIBO: 0,
      FICHA_ALUNO: 0,
      CERTIFICADO: 0
    };

    // Últimos 7 dias
    const porDia: Record<string, number> = {};
    const hoje = new Date();
    for (let i = 6; i >= 0; i--) {
      const d = new Date(hoje);
      d.setDate(hoje.getDate() - i);
      const chave = d.toISOString().split('T')[0];
      porDia[chave] = 0;
    }

    impressoes.forEach(imp => {
      porTipo[imp.tipo_documento] = (porTipo[imp.tipo_documento] || 0) + 1;

      const diaChave = imp.data_emissao.toISOString().split('T')[0];
      if (porDia[diaChave] !== undefined) {
        porDia[diaChave]++;
      }
    });

    return {
      totalImpressoes,
      porTipo,
      porDia,
      recentes: impressoes.slice(0, 10)
    };
  }

  async exportarBoletimPdf(escolaId: string, alunoId: string, anoLetivo = '2026'): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.gerarBoletimAluno(escolaId, alunoId, anoLetivo);
    const buffer = await PdfKitDocumentosService.gerarBoletimPdf({
      escola: dados.escola,
      anoLetivo: dados.anoLetivo,
      aluno: {
        id: dados.aluno.id,
        nome: dados.aluno.nome,
        matricula: dados.aluno.matricula,
        turma: { nome: dados.aluno.turma, grau_ano: dados.aluno.grau }
      },
      disciplinas: dados.disciplinas.map(d => ({
        id: d.id,
        nome: d.nome,
        codigo: d.codigo,
        t1: d.t1,
        t2: d.t2,
        t3: d.t3,
        mfd: d.mediaFinal
      })),
      medias: {
        mfd: dados.mediaGeral
      },
      resultadoFinal: dados.resultado,
      observacao: `Resultado pedagógico do aluno: ${dados.resultado} com média global de ${dados.mediaGeral} valores.`
    });
    const nome = dados.aluno.nome.replace(/\s+/g, '_');
    return {
      buffer,
      filename: `Boletim_${nome}_${dados.anoLetivo}.pdf`
    };
  }

  async exportarBoletimDocx(escolaId: string, alunoId: string): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.gerarBoletimAluno(escolaId, alunoId);
    const buffer = await DocxDocumentosService.gerarDeclaracaoDocx({
      escola: dados.escola,
      anoLectivo: dados.anoLetivo,
      comNotas: true,
      aluno: {
        nome: dados.aluno.nome,
        matricula: dados.aluno.matricula,
        numero_documento: dados.aluno.numero_documento,
        turma: { nome: dados.aluno.turma, grau_ano: dados.aluno.grau }
      },
      disciplinas: dados.disciplinas.map(d => ({ nome: d.nome, mfd: d.mediaFinal })),
      mediaFinal: dados.mediaGeral,
      resultadoFinal: dados.resultado
    });
    const nome = dados.aluno.nome.replace(/\s+/g, '_');
    return {
      buffer,
      filename: `Boletim_${nome}_${dados.anoLetivo}.docx`
    };
  }

  async exportarBoletimXlsx(escolaId: string, alunoId: string): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.gerarBoletimAluno(escolaId, alunoId);
    const buffer = SheetJsDocumentosService.gerarBoletimXlsx({
      escola: dados.escola,
      aluno: {
        nome: dados.aluno.nome,
        matricula: dados.aluno.matricula,
        turma: { nome: dados.aluno.turma, grau_ano: dados.aluno.grau }
      },
      anoLetivo: dados.anoLetivo,
      disciplinas: dados.disciplinas.map(d => ({
        nome: d.nome,
        t1: d.t1,
        t2: d.t2,
        t3: d.t3,
        mfd: d.mediaFinal
      })),
      medias: { mfd: dados.mediaGeral },
      resultadoFinal: dados.resultado
    });
    const nome = dados.aluno.nome.replace(/\s+/g, '_');
    return {
      buffer,
      filename: `Boletim_${nome}_${dados.anoLetivo}.xlsx`
    };
  }

  async exportarDeclaracaoPdf(escolaId: string, alunoId: string, comNotas = true): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.gerarDeclaracaoAluno(escolaId, alunoId, comNotas);
    const buffer = await PdfKitDocumentosService.gerarDeclaracaoPdf({
      escola: dados.escola,
      anoLectivo: dados.anoLectivo,
      comNotas,
      aluno: dados.aluno,
      disciplinas: dados.disciplinas.map(d => ({ nome: d.disciplina, mfd: d.notaFinal })),
      mediaFinal: dados.mediaGlobal,
      resultadoFinal: dados.resultadoOficial
    });
    const nome = (dados.aluno.nomeCompleto || dados.aluno.nome).replace(/\s+/g, '_');
    return {
      buffer,
      filename: `Declaracao_${nome}_${dados.anoLectivo}.pdf`
    };
  }

  async exportarDeclaracaoDocx(escolaId: string, alunoId: string, comNotas = true): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.gerarDeclaracaoAluno(escolaId, alunoId, comNotas);
    const buffer = await DocxDocumentosService.gerarDeclaracaoDocx({
      escola: dados.escola,
      anoLectivo: dados.anoLectivo,
      comNotas,
      aluno: dados.aluno,
      disciplinas: dados.disciplinas.map(d => ({ nome: d.disciplina, mfd: d.notaFinal })),
      mediaFinal: dados.mediaGlobal,
      resultadoFinal: dados.resultadoOficial
    });
    const nome = (dados.aluno.nomeCompleto || dados.aluno.nome).replace(/\s+/g, '_');
    return {
      buffer,
      filename: `Declaracao_${nome}_${dados.anoLectivo}.docx`
    };
  }

  async exportarDeclaracaoXlsx(escolaId: string, alunoId: string): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.gerarDeclaracaoAluno(escolaId, alunoId, true);
    const buffer = await ExportExcelService.gerarDeclaracaoXlsx(dados);
    const nome = (dados.aluno.nomeCompleto || dados.aluno.nome || 'Aluno').replace(/\s+/g, '_');
    return {
      buffer,
      filename: `Declaracao_${nome}_${dados.anoLectivo}.xlsx`
    };
  }

  async exportarCertificadoPdf(escolaId: string, alunoId: string): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.gerarCertificadoAluno(escolaId, alunoId);
    const buffer = await PdfKitDocumentosService.gerarDeclaracaoPdf({
      escola: dados.escola,
      anoLectivo: dados.anoLectivo,
      comNotas: true,
      aluno: dados.aluno,
      disciplinas: dados.disciplinas.map(d => ({ nome: d.disciplina, mfd: d.notaFinal })),
      mediaFinal: dados.mediaGlobal,
      resultadoFinal: dados.resultadoOficial
    });
    const nome = (dados.aluno.nomeCompleto || dados.aluno.nome).replace(/\s+/g, '_');
    return {
      buffer,
      filename: `Certificado_${nome}_${dados.anoLectivo}.pdf`
    };
  }

  async exportarCertificadoDocx(escolaId: string, alunoId: string): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.gerarCertificadoAluno(escolaId, alunoId);
    const buffer = await DocxDocumentosService.gerarDeclaracaoDocx({
      escola: dados.escola,
      anoLectivo: dados.anoLectivo,
      comNotas: true,
      aluno: dados.aluno,
      disciplinas: dados.disciplinas.map(d => ({ nome: d.disciplina, mfd: d.notaFinal })),
      mediaFinal: dados.mediaGlobal,
      resultadoFinal: dados.resultadoOficial
    });
    const nome = (dados.aluno.nomeCompleto || dados.aluno.nome).replace(/\s+/g, '_');
    return {
      buffer,
      filename: `Certificado_${nome}_${dados.anoLectivo}.docx`
    };
  }

  async exportarCertificadoXlsx(escolaId: string, alunoId: string): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.gerarCertificadoAluno(escolaId, alunoId);
    const buffer = await ExportExcelService.gerarCertificadoXlsx(dados);
    const nome = (dados.aluno.nomeCompleto || dados.aluno.nome || 'Aluno').replace(/\s+/g, '_');
    return {
      buffer,
      filename: `Certificado_${nome}_${dados.anoLectivo}.xlsx`
    };
  }

  async exportarReciboPdf(escolaId: string, pagamentoId: string, operador?: string): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.gerarReciboPagamento(escolaId, pagamentoId);
    const buffer = await PdfKitDocumentosService.gerarReciboPdf({
      escola: dados.escola,
      pagamento: {
        id: dados.pagamento.id,
        recibo_numero: dados.reciboNumero,
        descricao: dados.pagamento.descricao,
        mes_referencia: dados.pagamento.mesReferencia,
        valor: dados.pagamento.valor,
        valor_pago: dados.pagamento.valorPago,
        metodo_pagamento: dados.pagamento.metodo,
        data_pagamento: dados.pagamento.dataPagamento,
        status: dados.pagamento.status
      },
      aluno: {
        id: dados.aluno.id || '',
        nome: (dados.aluno.nomeCompleto || dados.aluno.nome) || 'Candidato',
        matricula: dados.aluno.matricula,
        turma: dados.aluno.turma,
        nuit: dados.aluno.nuit,
        numero_documento: dados.aluno.numero_documento
      },
      operador
    });
    return {
      buffer,
      filename: `Recibo_${dados.reciboNumero || dados.pagamento.id}.pdf`
    };
  }

  async exportarReciboDocx(escolaId: string, pagamentoId: string): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.gerarReciboPagamento(escolaId, pagamentoId);
    const buffer = await DocxDocumentosService.gerarReciboDocx({
      escola: dados.escola,
      pagamento: {
        id: dados.pagamento.id,
        recibo_numero: dados.reciboNumero,
        descricao: dados.pagamento.descricao,
        mes_referencia: dados.pagamento.mesReferencia,
        valor: dados.pagamento.valor,
        valor_pago: dados.pagamento.valorPago,
        metodo_pagamento: dados.pagamento.metodo,
        data_pagamento: dados.pagamento.dataPagamento,
        status: dados.pagamento.status
      },
      aluno: {
        id: dados.aluno.id || '',
        nome: (dados.aluno.nomeCompleto || dados.aluno.nome) || 'Candidato',
        matricula: dados.aluno.matricula,
        turma: dados.aluno.turma
      }
    });
    return {
      buffer,
      filename: `Recibo_${dados.reciboNumero || dados.pagamento.id}.docx`
    };
  }

  async exportarLoteXlsx(
    escolaId: string,
    turmaId: string,
    tipo: 'BOLETIM' | 'DECLARACAO' | 'CERTIFICADO'
  ): Promise<{ buffer: Buffer; filename: string }> {
    const dadosLote = await this.gerarLoteTurma(escolaId, turmaId, tipo);
    const buffer = await ExportExcelService.gerarLoteDocumentosXlsx(dadosLote.documentos, tipo);
    const safeTurma = (dadosLote.documentos[0]?.aluno?.turma?.nome || 'Turma').replace(/\s+/g, '_');
    return {
      buffer,
      filename: `${tipo}_Lote_${safeTurma}_2026.xlsx`
    };
  }

  async salvarDocumentoJson(params: {
    escolaId: string;
    tipoDocumento: string;
    titulo: string;
    anoLetivo?: string;
    dados: any;
    alunoId?: string;
    turmaId?: string;
    usuarioId?: string;
  }) {
    const dadosStr = JSON.stringify(params.dados);
    const hash = crypto.createHash('md5').update(dadosStr).digest('hex');

    const docSalvo = await prisma.documentoSalvo.create({
      data: {
        escola_id: params.escolaId,
        usuario_id: params.usuarioId,
        aluno_id: params.alunoId,
        turma_id: params.turmaId,
        tipo_documento: params.tipoDocumento,
        titulo: params.titulo,
        ano_letivo: params.anoLetivo || '2026',
        dados_json: dadosStr,
        hash_md5: hash
      }
    });

    await this.registrarEmissao(
      params.escolaId,
      params.tipoDocumento,
      `Gravação JSON: ${params.titulo}`,
      params.usuarioId,
      dadosStr
    );

    return docSalvo;
  }

  async exportarBoletimJson(escolaId: string, alunoId: string, usuarioId?: string): Promise<{ json: any; filename: string }> {
    const dados = await this.gerarBoletimAluno(escolaId, alunoId);
    const nome = dados.aluno.nome.replace(/\s+/g, '_');
    await this.salvarDocumentoJson({
      escolaId,
      tipoDocumento: 'BOLETIM',
      titulo: `Boletim Escolar - ${dados.aluno.nome}`,
      anoLetivo: dados.anoLetivo,
      dados,
      alunoId,
      turmaId: typeof (dados.aluno as any)?.turma === 'object' ? (dados.aluno as any)?.turma?.id : undefined,
      usuarioId
    });
    return {
      json: dados,
      filename: `Boletim_${nome}_${dados.anoLetivo}.json`
    };
  }

  async exportarDeclaracaoJson(escolaId: string, alunoId: string, usuarioId?: string): Promise<{ json: any; filename: string }> {
    const dados = await this.gerarDeclaracaoAluno(escolaId, alunoId, true);
    const nome = (dados.aluno.nomeCompleto || dados.aluno.nome || 'Aluno').replace(/\s+/g, '_');
    await this.salvarDocumentoJson({
      escolaId,
      tipoDocumento: 'DECLARACAO',
      titulo: `Declaração com Notas - ${nome}`,
      anoLetivo: dados.anoLectivo,
      dados,
      alunoId,
      turmaId: typeof (dados.aluno as any)?.turma === 'object' ? (dados.aluno as any)?.turma?.id : undefined,
      usuarioId
    });
    return {
      json: dados,
      filename: `Declaracao_${nome}_${dados.anoLectivo}.json`
    };
  }

  async exportarCertificadoJson(escolaId: string, alunoId: string, usuarioId?: string): Promise<{ json: any; filename: string }> {
    const dados = await this.gerarCertificadoAluno(escolaId, alunoId);
    const nome = (dados.aluno.nomeCompleto || dados.aluno.nome || 'Aluno').replace(/\s+/g, '_');
    await this.salvarDocumentoJson({
      escolaId,
      tipoDocumento: 'CERTIFICADO',
      titulo: `Certificado de Habilitações - ${nome}`,
      anoLetivo: dados.anoLectivo,
      dados,
      alunoId,
      turmaId: typeof (dados.aluno as any)?.turma === 'object' ? (dados.aluno as any)?.turma?.id : undefined,
      usuarioId
    });
    return {
      json: dados,
      filename: `Certificado_${nome}_${dados.anoLectivo}.json`
    };
  }

  async exportarLoteJson(
    escolaId: string,
    turmaId: string,
    tipo: 'BOLETIM' | 'DECLARACAO' | 'CERTIFICADO',
    usuarioId?: string
  ): Promise<{ json: any; filename: string }> {
    const dadosLote = await this.gerarLoteTurma(escolaId, turmaId, tipo);
    const safeTurma = (dadosLote.documentos[0]?.aluno?.turma?.nome || 'Turma').replace(/\s+/g, '_');
    await this.salvarDocumentoJson({
      escolaId,
      tipoDocumento: tipo,
      titulo: `Emissão em Lote (${tipo}) - Turma ${safeTurma}`,
      anoLetivo: '2026',
      dados: dadosLote,
      turmaId,
      usuarioId
    });
    return {
      json: dadosLote,
      filename: `${tipo}_Lote_${safeTurma}_2026.json`
    };
  }

  async listarDocumentosSalvos(escolaId: string, tipo?: string) {
    const where: any = { escola_id: escolaId };
    if (tipo) where.tipo_documento = tipo;
    return prisma.documentoSalvo.findMany({
      where,
      orderBy: { criado_em: 'desc' },
      take: 50
    });
  }
}

export const impressaoService = new ImpressaoService();
