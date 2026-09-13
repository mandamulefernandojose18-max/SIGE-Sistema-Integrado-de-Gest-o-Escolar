import prisma from '../../config/database';
import { avaliarAprovacaoPauta } from '../../utils/avaliacoes-mocambique';
import { ExportExcelService } from '../../services/export-excel.service';

export class PautasService {
  async list(escolaId: string, filtros?: { anoLetivo?: string; periodo?: string }) {
    return prisma.pauta.findMany({
      where: {
        escola_id: escolaId,
        ...(filtros?.anoLetivo ? { ano_letivo: filtros.anoLetivo } : {}),
        ...(filtros?.periodo ? { periodo: filtros.periodo } : {})
      },
      include: {
        turma: {
          include: {
            director_turma: true,
            director_classe: true,
            _count: { select: { alunos: true } }
          }
        }
      },
      orderBy: [{ ano_letivo: 'desc' }, { turma: { nome: 'asc' } }]
    });
  }

  async getById(escolaId: string, id: string) {
    const pauta = await prisma.pauta.findFirst({
      where: { id, escola_id: escolaId },
      include: {
        escola: true,
        turma: {
          include: {
            director_turma: true,
            director_classe: true,
            alunos: {
              where: { status: 'ATIVO' },
              orderBy: { nome: 'asc' }
            }
          }
        }
      }
    });

    if (!pauta) return null;

    // Buscar todas as notas desta turma e período
    const notas = await prisma.nota.findMany({
      where: {
        escola_id: escolaId,
        turma_id: pauta.turma_id,
        periodo: pauta.periodo
      },
      include: { disciplina: true }
    });

    // Disciplinas ministradas nesta turma
    const disciplinas = await prisma.disciplina.findMany({
      where: {
        escola_id: escolaId,
        alocacoes: { some: { turma_id: pauta.turma_id } }
      }
    });

    // Mapear consolidação por aluno com a Regra Oficial de Moçambique:
    // "Excepto a 12a classe, o aluno só Aprova se tiver todas as disciplinas notas positivas sem negativa em alguma disciplina."
    const consolidadoAlunos = pauta.turma.alunos.map((aluno, index) => {
      const notasAluno = notas.filter(n => n.aluno_id === aluno.id);
      const notasPorDisciplina: Record<string, number> = {};
      const notasFormatadas: Record<string, { final: number; faltas: number }> = {};
      const disciplinasParaAvaliacao: Array<{ disciplina: string; notaFinal: number }> = [];
      let totalFaltas = 0;
      let comportamento = 'S';

      disciplinas.forEach(d => {
        const notaD = notasAluno.find(n => n.disciplina_id === d.id);
        const notaValor = notaD ? notaD.media_final : 0;
        const faltas = notaD ? notaD.faltas : 0;
        if (notaD?.comportamento) comportamento = notaD.comportamento;
        totalFaltas += faltas;

        notasPorDisciplina[d.codigo || d.id] = notaValor;
        notasFormatadas[d.codigo || d.id] = { final: notaValor, faltas };

        if (notaD) {
          disciplinasParaAvaliacao.push({
            disciplina: d.codigo || d.nome,
            notaFinal: notaValor
          });
        }
      });

      const avaliacao = avaliarAprovacaoPauta(disciplinasParaAvaliacao, pauta.turma.grau_ano);

      return {
        numero: index + 1,
        alunoId: aluno.id,
        matricula: aluno.matricula,
        nome: `${aluno.nome} ${aluno.apelido || ''}`.trim(),
        genero: aluno.genero,
        notas: notasPorDisciplina,
        notasDetalhes: notasFormatadas,
        mediaFinal: avaliacao.mediaGeral,
        mediaGeral: avaliacao.mediaGeral,
        faltas: totalFaltas,
        comportamento,
        totalNegativas: avaliacao.totalNegativas,
        situacao: avaliacao.resultado,
        resultado: avaliacao.resultado,
        motivo: avaliacao.motivo,
        is12aClasse: avaliacao.is12aClasse
      };
    });

    return {
      pauta,
      escola: pauta.escola,
      turma: pauta.turma,
      disciplinas: disciplinas.map(d => ({ id: d.id, nome: d.nome, codigo: d.codigo })),
      alunos: consolidadoAlunos
    };
  }

  async gerarOuObterPauta(escolaId: string, dados: { turma_id: string; ano_letivo: string; periodo: string }) {
    let pauta = await prisma.pauta.findFirst({
      where: {
        escola_id: escolaId,
        turma_id: dados.turma_id,
        ano_letivo: dados.ano_letivo,
        periodo: dados.periodo
      }
    });

    if (!pauta) {
      pauta = await prisma.pauta.create({
        data: {
          escola_id: escolaId,
          turma_id: dados.turma_id,
          ano_letivo: dados.ano_letivo,
          periodo: dados.periodo,
          status: 'ABERTA'
        }
      });
    }

    return pauta;
  }

  async alterarStatus(escolaId: string, id: string, status: 'ABERTA' | 'EM_CONSOLIDACAO' | 'FECHADA', homologadoPor?: string) {
    return prisma.pauta.update({
      where: { id, escola_id: escolaId },
      data: {
        status,
        data_fechamento: status === 'FECHADA' ? new Date() : null,
        homologado_por: homologadoPor
      }
    });
  }

  async getStats(escolaId: string, anoLetivo?: string) {
    const where = {
      escola_id: escolaId,
      ...(anoLetivo ? { ano_letivo: anoLetivo } : {})
    };

    const [totalTurmas, pautas] = await Promise.all([
      prisma.turma.count({ where: { escola_id: escolaId } }),
      prisma.pauta.findMany({ where })
    ]);

    let fechadas = 0;
    let consolidacao = 0;
    let abertas = 0;

    pautas.forEach(p => {
      if (p.status === 'FECHADA') fechadas++;
      else if (p.status === 'EM_CONSOLIDACAO') consolidacao++;
      else abertas++;
    });

    const totalPautas = pautas.length;
    const percentualFechadas = totalPautas > 0 ? Number(((fechadas / totalPautas) * 100).toFixed(1)) : 0;
    const percentualPendentes = Number((100 - percentualFechadas).toFixed(1));

    return {
      totalTurmas,
      totalPautas,
      fechadas,
      consolidacao,
      abertas,
      pendentes: abertas + consolidacao,
      percentualFechadas,
      percentualPendentes
    };
  }

  async exportarPautaXlsx(escolaId: string, id: string): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.getById(escolaId, id);
    if (!dados) throw new Error('Pauta não encontrada');

    return this.exportarPautaTurmaXlsx(escolaId, dados.turma.id, dados.turma.ano_letivo);
  }

  async exportarActaXlsx(escolaId: string, id: string): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.getById(escolaId, id);
    if (!dados) throw new Error('Pauta não encontrada');

    return this.exportarActaTurmaXlsx(escolaId, dados.turma.id, dados.turma.ano_letivo);
  }

  async getPautaCompleta(escolaId: string, turmaId: string, anoLetivo = '2026') {
    const turma = await prisma.turma.findFirst({
      where: { id: turmaId, escola_id: escolaId },
      include: {
        escola: true,
        director_turma: true,
        director_classe: true,
        alunos: {
          where: { status: 'ATIVO' },
          orderBy: { nome: 'asc' }
        }
      }
    });

    if (!turma) throw new Error('Turma não encontrada');

    const disciplinas = await prisma.disciplina.findMany({
      where: {
        escola_id: escolaId,
        alocacoes: { some: { turma_id: turmaId } }
      },
      orderBy: { nome: 'asc' }
    });

    const notas = await prisma.nota.findMany({
      where: {
        escola_id: escolaId,
        turma_id: turmaId
      }
    });

    const notasMap = new Map<string, any>();
    notas.forEach(n => {
      notasMap.set(`${n.aluno_id}_${n.disciplina_id}_${n.periodo}`, n);
    });

    let inscritosH = 0, inscritosM = 0;
    let avaliadosH = 0, avaliadosM = 0;
    let aprovadosH = 0, aprovadosM = 0;
    let reprovadosH = 0, reprovadosM = 0;

    const alunosProcessados = turma.alunos.map((aluno, idx) => {
      const isMasc = (aluno.genero || 'M').toUpperCase() === 'M';
      if (isMasc) inscritosH++; else inscritosM++;

      const notasDisciplinas: Record<string, { t1?: number | null; t2?: number | null; t3?: number | null; mfd?: number | null }> = {};
      const disciplinasParaAvaliacao: Array<{ disciplina: string; notaFinal: number }> = [];

      let somaT1 = 0, countT1 = 0;
      let somaT2 = 0, countT2 = 0;
      let somaT3 = 0, countT3 = 0;
      let negT1 = 0, negT2 = 0, negT3 = 0;
      let somaMfd = 0, countMfd = 0;
      let anotacaoAluno = '';

      disciplinas.forEach(d => {
        const n1 = notasMap.get(`${aluno.id}_${d.id}_1_TRIMESTRE`);
        const n2 = notasMap.get(`${aluno.id}_${d.id}_2_TRIMESTRE`);
        const n3 = notasMap.get(`${aluno.id}_${d.id}_3_TRIMESTRE`);

        if (n1?.anotacao) anotacaoAluno = n1.anotacao;
        if (n2?.anotacao) anotacaoAluno = n2.anotacao;
        if (n3?.anotacao) anotacaoAluno = n3.anotacao;

        const v1 = n1?.media_final ?? null;
        const v2 = n2?.media_final ?? null;
        const v3 = n3?.media_final ?? null;

        if (v1 !== null && v1 !== undefined && v1 > 0) {
          somaT1 += v1; countT1++;
          if (v1 < 9.5) negT1++;
        }
        if (v2 !== null && v2 !== undefined && v2 > 0) {
          somaT2 += v2; countT2++;
          if (v2 < 9.5) negT2++;
        }
        if (v3 !== null && v3 !== undefined && v3 > 0) {
          somaT3 += v3; countT3++;
          if (v3 < 9.5) negT3++;
        }

        const validas = [v1, v2, v3].filter(v => v !== null && v !== undefined && v > 0) as number[];
        const mfd = validas.length > 0 ? Math.round(validas.reduce((a, b) => a + b, 0) / validas.length) : null;

        if (mfd !== null) {
          somaMfd += mfd;
          countMfd++;
          disciplinasParaAvaliacao.push({
            disciplina: d.codigo || d.nome,
            notaFinal: mfd
          });
        }

        notasDisciplinas[d.codigo || d.id] = { t1: v1, t2: v2, t3: v3, mfd };
      });

      const medT1 = countT1 > 0 ? Number((somaT1 / countT1).toFixed(1)) : null;
      const medT2 = countT2 > 0 ? Number((somaT2 / countT2).toFixed(1)) : null;
      const medT3 = countT3 > 0 ? Number((somaT3 / countT3).toFixed(1)) : null;

      const mediaFinalGeral = countMfd > 0 ? Number((somaMfd / countMfd).toFixed(1)) : 0;
      const negFimAno = disciplinasParaAvaliacao.filter(dp => dp.notaFinal < 9.5).length;

      let resultadoFinal = 'R';
      if (anotacaoAluno === 'D') {
        resultadoFinal = 'D';
      } else if (anotacaoAluno === 'T') {
        resultadoFinal = 'T';
      } else {
        const avaliacao = avaliarAprovacaoPauta(disciplinasParaAvaliacao, turma.grau_ano);
        resultadoFinal = avaliacao.resultado === 'Aprovado' ? 'A' : 'R';
      }

      if (countMfd > 0 && resultadoFinal !== 'D' && resultadoFinal !== 'T') {
        if (isMasc) avaliadosH++; else avaliadosM++;
        if (resultadoFinal === 'A') {
          if (isMasc) aprovadosH++; else aprovadosM++;
        } else {
          if (isMasc) reprovadosH++; else reprovadosM++;
        }
      }

      return {
        numero: idx + 1,
        alunoId: aluno.id,
        matricula: aluno.matricula,
        nome: aluno.nome,
        apelido: aluno.apelido || '',
        nomeCompleto: `${aluno.nome} ${aluno.apelido || ''}`.trim(),
        genero: aluno.genero || 'M',
        notasDisciplinas,
        mediasTrimestrais: { t1: medT1, t2: medT2, t3: medT3 },
        negativas: { t1: negT1, t2: negT2, t3: negT3, fimDoAno: negFimAno },
        mediaFinalGeral,
        resultadoFinal
      };
    });

    const totalInscritos = inscritosH + inscritosM;
    const totalAvaliados = avaliadosH + avaliadosM;
    const totalAprovados = aprovadosH + aprovadosM;
    const totalReprovados = reprovadosH + reprovadosM;
    const pctAprovados = totalAvaliados > 0 ? Number(((totalAprovados / totalAvaliados) * 100).toFixed(1)) : 0;
    const pctReprovados = totalAvaliados > 0 ? Number(((totalReprovados / totalAvaliados) * 100).toFixed(1)) : 0;

    return {
      escola: turma.escola,
      turma: {
        id: turma.id,
        nome: turma.nome,
        grau_ano: turma.grau_ano,
        turno: turma.turno,
        ano_letivo: turma.ano_letivo,
        director_turma: turma.director_turma ? turma.director_turma.nome : 'Director de Turma',
        director_turma_tel: turma.director_turma?.telefone || ''
      },
      disciplinas: disciplinas.map(d => ({ id: d.id, nome: d.nome, codigo: d.codigo })),
      alunos: alunosProcessados,
      estatistica: {
        inscritos: { h: inscritosH, m: inscritosM, total: totalInscritos },
        avaliados: { h: avaliadosH, m: avaliadosM, total: totalAvaliados },
        aprovados: { h: aprovadosH, m: aprovadosM, total: totalAprovados, pct: pctAprovados },
        reprovados: { h: reprovadosH, m: reprovadosM, total: totalReprovados, pct: pctReprovados }
      }
    };
  }

  async getActaConselhoAvaliacao(escolaId: string, turmaId: string, anoLetivo = '2026') {
    const pautaCompleta = await this.getPautaCompleta(escolaId, turmaId, anoLetivo);
    const { escola, turma, disciplinas, alunos } = pautaCompleta;

    const totalAlunos = alunos.length;
    let hInscritos = 0, mInscritos = 0;
    alunos.forEach(a => {
      if (a.genero.toUpperCase() === 'M') hInscritos++; else mInscritos++;
    });

    const periodos = ['t1', 't2', 't3', 'fimAno'] as const;

    const calcEfectivoPorPeriodo = (_periodo: typeof periodos[number]) => {
      let desH = 0, desM = 0;
      let trH = 0, trM = 0;
      let falH = 0, falM = 0;

      alunos.forEach(a => {
        const isMasc = a.genero.toUpperCase() === 'M';
        if (a.resultadoFinal === 'D') {
          if (isMasc) desH++; else desM++;
        } else if (a.resultadoFinal === 'T') {
          if (isMasc) trH++; else trM++;
        }
      });

      const avH = Math.max(0, hInscritos - desH - trH - falH);
      const avM = Math.max(0, mInscritos - desM - trM - falM);

      return {
        inscritos: { h: hInscritos, m: mInscritos, hm: totalAlunos },
        desistentes: { h: desH, m: desM, hm: desH + desM },
        transferidos: { h: trH, m: trM, hm: trH + trM },
        falecidos: { h: falH, m: falM, hm: falH + falM },
        avaliados: { h: avH, m: avM, hm: avH + avM }
      };
    };

    const tabelaEfectivo = {
      t1: calcEfectivoPorPeriodo('t1'),
      t2: calcEfectivoPorPeriodo('t2'),
      t3: calcEfectivoPorPeriodo('t3'),
      fimAno: calcEfectivoPorPeriodo('fimAno')
    };

    const calcAproveitamentoPorPeriodo = (periodo: typeof periodos[number]) => {
      let nsH = 0, nsM = 0;
      let satH = 0, satM = 0;
      let bomH = 0, bomM = 0;
      let mbH = 0, mbM = 0;
      let excH = 0, excM = 0;
      let aprH = 0, aprM = 0;
      let repH = 0, repM = 0;

      alunos.forEach(a => {
        if (a.resultadoFinal === 'D' || a.resultadoFinal === 'T') return;
        const isMasc = a.genero.toUpperCase() === 'M';

        let mediaAluno: number | null = null;
        if (periodo === 't1') mediaAluno = a.mediasTrimestrais.t1 ?? null;
        else if (periodo === 't2') mediaAluno = a.mediasTrimestrais.t2 ?? null;
        else if (periodo === 't3') mediaAluno = a.mediasTrimestrais.t3 ?? null;
        else mediaAluno = a.mediaFinalGeral;

        if (mediaAluno === null || mediaAluno === undefined || mediaAluno <= 0) return;

        if (mediaAluno < 9.5) {
          if (isMasc) nsH++; else nsM++;
        } else if (mediaAluno < 13.5) {
          if (isMasc) satH++; else satM++;
        } else if (mediaAluno < 16.5) {
          if (isMasc) bomH++; else bomM++;
        } else if (mediaAluno < 18.5) {
          if (isMasc) mbH++; else mbM++;
        } else {
          if (isMasc) excH++; else excM++;
        }

        let isAprovado = false;
        if (periodo === 'fimAno') {
          isAprovado = a.resultadoFinal === 'A';
        } else {
          const negPeriodo = a.negativas[periodo as 't1' | 't2' | 't3'];
          const is12 = (turma.grau_ano || '').includes('12');
          if (is12) {
            isAprovado = mediaAluno >= 9.5 && negPeriodo <= 2;
          } else {
            isAprovado = mediaAluno >= 9.5 && negPeriodo === 0;
          }
        }

        if (isAprovado) {
          if (isMasc) aprH++; else aprM++;
        } else {
          if (isMasc) repH++; else repM++;
        }
      });

      const totalAv = aprH + aprM + repH + repM;
      const getPct = (val: number) => totalAv > 0 ? Number(((val / totalAv) * 100).toFixed(1)) : 0;

      return {
        avaliados: { h: aprH + repH, m: aprM + repM, hm: totalAv, pct: 100 },
        naoSatisfatorio: { h: nsH, m: nsM, hm: nsH + nsM, pct: getPct(nsH + nsM) },
        satisfatorio: { h: satH, m: satM, hm: satH + satM, pct: getPct(satH + satM) },
        bom: { h: bomH, m: bomM, hm: bomH + bomM, pct: getPct(bomH + bomM) },
        muitoBom: { h: mbH, m: mbM, hm: mbH + mbM, pct: getPct(mbH + mbM) },
        excelente: { h: excH, m: excM, hm: excH + excM, pct: getPct(excH + excM) },
        aprovados: { h: aprH, m: aprM, hm: aprH + aprM, pct: getPct(aprH + aprM) },
        reprovados: { h: repH, m: repM, hm: repH + repM, pct: getPct(repH + repM) }
      };
    };

    const tabelaAproveitamento = {
      t1: calcAproveitamentoPorPeriodo('t1'),
      t2: calcAproveitamentoPorPeriodo('t2'),
      t3: calcAproveitamentoPorPeriodo('t3'),
      fimAno: calcAproveitamentoPorPeriodo('fimAno')
    };

    const estatisticaDisciplinas = disciplinas.map(d => {
      let f0_9H = 0, f0_9M = 0;
      let f10_13H = 0, f10_13M = 0;
      let f14_16H = 0, f14_16M = 0;
      let f17_18H = 0, f17_18M = 0;
      let f19_20H = 0, f19_20M = 0;
      let posH = 0, posM = 0;
      let negH = 0, negM = 0;

      alunos.forEach(a => {
        if (a.resultadoFinal === 'D' || a.resultadoFinal === 'T') return;
        const isMasc = a.genero.toUpperCase() === 'M';
        const nd = a.notasDisciplinas[d.codigo || d.id] || a.notasDisciplinas[d.id];
        const mfd = nd?.mfd ?? null;

        if (mfd !== null && mfd !== undefined && mfd > 0) {
          if (mfd < 9.5) {
            if (isMasc) f0_9H++; else f0_9M++;
            if (isMasc) negH++; else negM++;
          } else {
            if (isMasc) posH++; else posM++;
            if (mfd < 13.5) {
              if (isMasc) f10_13H++; else f10_13M++;
            } else if (mfd < 16.5) {
              if (isMasc) f14_16H++; else f14_16M++;
            } else if (mfd < 18.5) {
              if (isMasc) f17_18H++; else f17_18M++;
            } else {
              if (isMasc) f19_20H++; else f19_20M++;
            }
          }
        }
      });

      const totalAv = posH + posM + negH + negM;
      const totalPos = posH + posM;
      const totalNeg = negH + negM;
      const pctPos = totalAv > 0 ? Number(((totalPos / totalAv) * 100).toFixed(1)) : 0;
      const pctNeg = totalAv > 0 ? Number(((totalNeg / totalAv) * 100).toFixed(1)) : 0;

      return {
        nome: d.nome,
        codigo: d.codigo,
        faixa0_9: { h: f0_9H, m: f0_9M, hm: f0_9H + f0_9M },
        faixa10_13: { h: f10_13H, m: f10_13M, hm: f10_13H + f10_13M },
        faixa14_16: { h: f14_16H, m: f14_16M, hm: f14_16H + f14_16M },
        faixa17_18: { h: f17_18H, m: f17_18M, hm: f17_18H + f17_18M },
        faixa19_20: { h: f19_20H, m: f19_20M, hm: f19_20H + f19_20M },
        avaliados: { h: posH + negH, m: posM + negM, hm: totalAv },
        positivas: { h: posH, m: posM, hm: totalPos, pct: pctPos },
        negativas: { h: negH, m: negM, hm: totalNeg, pct: pctNeg }
      };
    });

    return {
      escola,
      turma,
      conselho: {
        presidente: turma.director_turma || 'Director de Turma',
        dataT1: '26/05/2026',
        dataT2: '01/08/2026',
        dataT3: '15/11/2026',
        horaInicio: '08:30',
        horaFim: '10:00'
      },
      tabelaEfectivo,
      tabelaAproveitamento,
      disciplinas: estatisticaDisciplinas
    };
  }

  async exportarPautaTurmaXlsx(escolaId: string, turmaId: string, anoLetivo = '2026'): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.getPautaCompleta(escolaId, turmaId, anoLetivo);
    const buffer = ExportExcelService.gerarPautaXlsx({
      escola: {
        nome: dados.escola.nome,
        provincia: dados.escola.provincia,
        distrito: dados.escola.distrito
      },
      turma: {
        nome: dados.turma.nome,
        grau_ano: dados.turma.grau_ano,
        ano_letivo: dados.turma.ano_letivo,
        turno: dados.turma.turno,
        director_turma: dados.turma.director_turma
      },
      disciplinas: dados.disciplinas,
      alunos: dados.alunos.map(a => ({
        numero: a.numero,
        matricula: a.matricula,
        nome: a.nome,
        apelido: a.apelido,
        genero: a.genero,
        notasDisciplinas: a.notasDisciplinas,
        mediasTrimestrais: a.mediasTrimestrais,
        negativas: a.negativas,
        mediaFinalGeral: a.mediaFinalGeral,
        resultado: a.resultadoFinal
      })),
      estatistica: dados.estatistica
    });

    const filename = `Pauta_${dados.turma.nome.replace(/\s+/g, '_')}_${dados.turma.ano_letivo}.xlsx`;
    return { buffer, filename };
  }

  async exportarActaTurmaXlsx(escolaId: string, turmaId: string, anoLetivo = '2026'): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.getActaConselhoAvaliacao(escolaId, turmaId, anoLetivo);
    const buffer = ExportExcelService.gerarActaEstatisticaXlsx({
      escola: {
        nome: dados.escola.nome,
        provincia: dados.escola.provincia,
        distrito: dados.escola.distrito
      },
      turma: {
        nome: dados.turma.nome,
        grau_ano: dados.turma.grau_ano,
        ano_letivo: dados.turma.ano_letivo,
        turno: dados.turma.turno,
        director_turma: dados.turma.director_turma
      },
      conselho: dados.conselho,
      tabelaEfectivo: dados.tabelaEfectivo,
      tabelaAproveitamento: dados.tabelaAproveitamento,
      disciplinas: dados.disciplinas
    });

    const filename = `Acta_${dados.turma.nome.replace(/\s+/g, '_')}_${dados.turma.ano_letivo}.xlsx`;
    return { buffer, filename };
  }
}

export const pautasService = new PautasService();

