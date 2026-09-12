import prisma from '../../config/database';

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
  async registrarEmissao(escolaId: string, tipo: string, descricao: string, usuarioId?: string) {
    return prisma.logImpressao.create({
      data: {
        escola_id: escolaId,
        usuario_id: usuarioId,
        tipo_documento: tipo,
        descricao
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
    const mediaGeralAluno = totalD > 0 ? Number((somaMedias / totalD).toFixed(1)) : 0;
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
    const nomeProprietario = `${pagamento.aluno.nome}_${pagamento.aluno.apelido || ''}`.trim().replace(/\s+/g, '_');
    const ano = agora.getFullYear();

    await this.registrarEmissao(escolaId, 'RECIBO', `Recibo ${pagamento.recibo_numero || pagamento.id} - ${pagamento.aluno.nome}`, usuarioId);

    // Requisito 7: Data e hora de impressão OBRIGATÓRIA no recibo (Ex.: 12/09/2026 08:45:25)
    return {
      titulo: 'RECIBO DE PAGAMENTO DE PROPINAS E EMOLUMENTOS',
      reciboNumero: pagamento.recibo_numero || `REC-${pagamento.id.slice(0, 8).toUpperCase()}`,
      filename: `Recibo_${nomeProprietario}_${ano}.pdf`,
      escola: pagamento.escola,
      aluno: {
        ...pagamento.aluno,
        nomeCompleto: `${pagamento.aluno.nome} ${pagamento.aluno.apelido || ''}`.trim()
      },
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

  async gerarDeclaracaoAluno(escolaId: string, alunoId: string, comNotas = false, usuarioId?: string) {
    const aluno = await prisma.aluno.findFirst({
      where: { id: alunoId, escola_id: escolaId },
      include: {
        escola: true,
        turma: true,
        notas: { include: { disciplina: true } }
      }
    });

    if (!aluno) throw new Error('Aluno não encontrado');

    const agora = new Date();
    const ano = aluno.turma?.ano_letivo || String(agora.getFullYear());
    const nomeProprietario = `${aluno.nome}_${aluno.apelido || ''}`.trim().replace(/\s+/g, '_');

    await this.registrarEmissao(escolaId, 'DECLARACAO', `Declaração Escolar - ${aluno.nome}`, usuarioId);

    // Requisito 7: Sem carimbo de horas na declaração
    return {
      titulo: comNotas ? 'DECLARAÇÃO COM NOTAS DE FREQUÊNCIA' : 'DECLARAÇÃO ESCOLAR DE MATRÍCULA',
      filename: `Declaracao_${nomeProprietario}_${ano}.pdf`,
      escola: aluno.escola,
      aluno: {
        ...aluno,
        nomeCompleto: `${aluno.nome} ${aluno.apelido || ''}`.trim()
      },
      comNotas,
      anoLectivo: ano,
      notas: aluno.notas,
      dataExtenso: formatarDataExtenso(agora, aluno.escola.distrito || aluno.escola.provincia || 'Maputo')
    };
  }

  async gerarCertificadoAluno(escolaId: string, alunoId: string, usuarioId?: string) {
    const aluno = await prisma.aluno.findFirst({
      where: { id: alunoId, escola_id: escolaId },
      include: {
        escola: true,
        turma: true,
        notas: { include: { disciplina: true } }
      }
    });

    if (!aluno) throw new Error('Aluno não encontrado');

    const agora = new Date();
    const ano = aluno.turma?.ano_letivo || String(agora.getFullYear());
    const nomeProprietario = `${aluno.nome}_${aluno.apelido || ''}`.trim().replace(/\s+/g, '_');

    // Calcular média geral
    let soma = 0;
    const disciplinasAvaliadas: Array<{ disciplina: string; notaFinal: number }> = [];
    aluno.notas.forEach(n => {
      soma += n.media_final;
      disciplinasAvaliadas.push({ disciplina: n.disciplina.nome, notaFinal: n.media_final });
    });
    const mediaGeral = aluno.notas.length > 0 ? Number((soma / aluno.notas.length).toFixed(1)) : 0;

    await this.registrarEmissao(escolaId, 'CERTIFICADO', `Certificado de Habilitações - ${aluno.nome}`, usuarioId);

    // Requisito 7: Sem carimbo de horas no certificado
    return {
      titulo: 'REPÚBLICA DE MOÇAMBIQUE\nMINISTÉRIO DA EDUCAÇÃO E DESENVOLVIMENTO HUMANO\nCERTIFICADO DE HABILITAÇÕES LITERÁRIAS',
      filename: `Certificado_${nomeProprietario}_${ano}.pdf`,
      codigoAutenticidade: `CERT-MZ-${aluno.escola.nif_cnpj}-${aluno.matricula}-${ano}`,
      escola: aluno.escola,
      aluno: {
        ...aluno,
        nomeCompleto: `${aluno.nome} ${aluno.apelido || ''}`.trim()
      },
      grauAno: aluno.turma?.grau_ano || '12ª Classe',
      anoLectivo: ano,
      mediaGeral,
      disciplinas: disciplinasAvaliadas,
      dataExtenso: formatarDataExtenso(agora, aluno.escola.distrito || aluno.escola.provincia || 'Maputo')
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
}

export const impressaoService = new ImpressaoService();
