import prisma from '../../config/database';
import { avaliarAprovacaoPauta } from '../../utils/avaliacoes-mocambique';
import { ExportExcelService } from '../../services/export-excel.service';
import { PdfKitDocumentosService } from '../../services/pdfkit-documentos.service';
import { DocxDocumentosService } from '../../services/docx-documentos.service';
import { SheetJsDocumentosService } from '../../services/sheetjs-documentos.service';
import { impressaoService } from '../impressao/impressao.service';

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
        is12aClasse: avaliacao.isClasseExame
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

    let disciplinas = await prisma.disciplina.findMany({
      where: {
        escola_id: escolaId,
        alocacoes: { some: { turma_id: turmaId } }
      },
      orderBy: { nome: 'asc' }
    });

    if (disciplinas.length === 0) {
      disciplinas = await prisma.disciplina.findMany({
        where: { escola_id: escolaId },
        orderBy: { nome: 'asc' }
      });
    }

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
    let totalNotasT1 = 0;
    let totalNotasT2 = 0;
    let totalNotasT3 = 0;

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
          somaT1 += v1; countT1++; totalNotasT1++;
          if (v1 < 9.5) negT1++;
        }
        if (v2 !== null && v2 !== undefined && v2 > 0) {
          somaT2 += v2; countT2++; totalNotasT2++;
          if (v2 < 9.5) negT2++;
        }
        if (v3 !== null && v3 !== undefined && v3 > 0) {
          somaT3 += v3; countT3++; totalNotasT3++;
          if (v3 < 9.5) negT3++;
        }

        const validas = [v1, v2, v3].filter(v => v !== null && v !== undefined && v > 0) as number[];
        // MFD oficial obrigatório: soma dos 3 trimestres dividida por 3 (ex.: 1 trimestre divide por 3)
        const mfd = validas.length > 0 ? Math.round(((Number(v1) || 0) + (Number(v2) || 0) + (Number(v3) || 0)) / 3) : null;

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

      const medT1 = countT1 > 0 ? Math.round(somaT1 / countT1) : null;
      const medT2 = countT2 > 0 ? Math.round(somaT2 / countT2) : null;
      const medT3 = countT3 > 0 ? Math.round(somaT3 / countT3) : null;

      const mediaFinalGeral = countMfd > 0 ? Math.round(somaMfd / countMfd) : 0;
      const negFimAno = disciplinasParaAvaliacao.filter(dp => dp.notaFinal < 9.5).length;

      let resultadoFinal = 'R';
      if (['D', 'T', 'VT', 'F', 'AM', 'PPF', 'PDF'].includes(anotacaoAluno)) {
        resultadoFinal = anotacaoAluno;
      } else if (disciplinasParaAvaliacao.length > 0) {
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
      },
      trimestresComNotas: {
        t1: totalNotasT1 > 0,
        t2: totalNotasT2 > 0,
        t3: totalNotasT3 > 0,
        fimAno: totalNotasT1 > 0 && totalNotasT2 > 0 && totalNotasT3 > 0
      }
    };
  }

  async getActaConselhoAvaliacao(escolaId: string, turmaId: string, anoLetivo = '2026', conselhoParams?: any) {
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
      let ppfH = 0, ppfM = 0;
      let amH = 0, amM = 0;

      alunos.forEach(a => {
        const isMasc = a.genero.toUpperCase() === 'M';
        const res = a.resultadoFinal;
        if (res === 'D') {
          if (isMasc) desH++; else desM++;
        } else if (res === 'T') {
          if (isMasc) trH++; else trM++;
        } else if (res === 'F') {
          if (isMasc) falH++; else falM++;
        } else if (res === 'PPF' || res === 'PDF') {
          if (isMasc) ppfH++; else ppfM++;
        } else if (res === 'AM') {
          if (isMasc) amH++; else amM++;
        }
      });

      const avH = Math.max(0, hInscritos - desH - trH - falH - ppfH - amH);
      const avM = Math.max(0, mInscritos - desM - trM - falM - ppfM - amM);
      const totAv = avH + avM;

      const getPctH = (val: number) => hInscritos > 0 ? Number(((val / hInscritos) * 100).toFixed(1)) : 0;
      const getPctM = (val: number) => mInscritos > 0 ? Number(((val / mInscritos) * 100).toFixed(1)) : 0;
      const getPctTot = (val: number) => totalAlunos > 0 ? Number(((val / totalAlunos) * 100).toFixed(1)) : 0;

      return {
        inscritos: { h: hInscritos, m: mInscritos, hm: totalAlunos, pctH: 100, pctM: 100, pct: 100 },
        desistentes: { h: desH, m: desM, hm: desH + desM, pctH: getPctH(desH), pctM: getPctM(desM), pct: getPctTot(desH + desM) },
        transferidos: { h: trH, m: trM, hm: trH + trM, pctH: getPctH(trH), pctM: getPctM(trM), pct: getPctTot(trH + trM) },
        falecidos: { h: falH, m: falM, hm: falH + falM, pctH: getPctH(falH), pctM: getPctM(falM), pct: getPctTot(falH + falM) },
        perdeuFaltas: { h: ppfH, m: ppfM, hm: ppfH + ppfM, pctH: getPctH(ppfH), pctM: getPctM(ppfM), pct: getPctTot(ppfH + ppfM) },
        anulouMatricula: { h: amH, m: amM, hm: amH + amM, pctH: getPctH(amH), pctM: getPctM(amM), pct: getPctTot(amH + amM) },
        avaliados: { h: avH, m: avM, hm: totAv, pctH: getPctH(avH), pctM: getPctM(avM), pct: getPctTot(totAv) }
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
        if (a.resultadoFinal === 'D' || a.resultadoFinal === 'T' || a.resultadoFinal === 'F') return;
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
      const avH = aprH + repH;
      const avM = aprM + repM;

      const getPctH = (val: number) => avH > 0 ? Number(((val / avH) * 100).toFixed(1)) : 0;
      const getPctM = (val: number) => avM > 0 ? Number(((val / avM) * 100).toFixed(1)) : 0;
      const getPctTot = (val: number) => totalAv > 0 ? Number(((val / totalAv) * 100).toFixed(1)) : 0;

      return {
        avaliados: { h: avH, m: avM, hm: totalAv, pctH: 100, pctM: 100, pct: 100 },
        naoSatisfatorio: { h: nsH, m: nsM, hm: nsH + nsM, pctH: getPctH(nsH), pctM: getPctM(nsM), pct: getPctTot(nsH + nsM) },
        satisfatorio: { h: satH, m: satM, hm: satH + satM, pctH: getPctH(satH), pctM: getPctM(satM), pct: getPctTot(satH + satM) },
        bom: { h: bomH, m: bomM, hm: bomH + bomM, pctH: getPctH(bomH), pctM: getPctM(bomM), pct: getPctTot(bomH + bomM) },
        muitoBom: { h: mbH, m: mbM, hm: mbH + mbM, pctH: getPctH(mbH), pctM: getPctM(mbM), pct: getPctTot(mbH + mbM) },
        excelente: { h: excH, m: excM, hm: excH + excM, pctH: getPctH(excH), pctM: getPctM(excM), pct: getPctTot(excH + excM) },
        aprovados: { h: aprH, m: aprM, hm: aprH + aprM, pctH: getPctH(aprH), pctM: getPctM(aprM), pct: getPctTot(aprH + aprM) },
        reprovados: { h: repH, m: repM, hm: repH + repM, pctH: getPctH(repH), pctM: getPctM(repM), pct: getPctTot(repH + repM) }
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
        if (a.resultadoFinal === 'D' || a.resultadoFinal === 'T' || a.resultadoFinal === 'F') return;
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

      const avH = posH + negH;
      const avM = posM + negM;
      const totalAv = avH + avM;
      const totalPos = posH + posM;
      const totalNeg = negH + negM;

      const pctPosH = avH > 0 ? Number(((posH / avH) * 100).toFixed(1)) : 0;
      const pctPosM = avM > 0 ? Number(((posM / avM) * 100).toFixed(1)) : 0;
      const pctPos = totalAv > 0 ? Number(((totalPos / totalAv) * 100).toFixed(1)) : 0;

      const pctNegH = avH > 0 ? Number(((negH / avH) * 100).toFixed(1)) : 0;
      const pctNegM = avM > 0 ? Number(((negM / avM) * 100).toFixed(1)) : 0;
      const pctNeg = totalAv > 0 ? Number(((totalNeg / totalAv) * 100).toFixed(1)) : 0;

      return {
        nome: d.nome,
        codigo: d.codigo,
        faixa0_9: { h: f0_9H, m: f0_9M, hm: f0_9H + f0_9M },
        faixa10_13: { h: f10_13H, m: f10_13M, hm: f10_13H + f10_13M },
        faixa14_16: { h: f14_16H, m: f14_16M, hm: f14_16H + f14_16M },
        faixa17_18: { h: f17_18H, m: f17_18M, hm: f17_18H + f17_18M },
        faixa19_20: { h: f19_20H, m: f19_20M, hm: f19_20H + f19_20M },
        avaliados: { h: avH, m: avM, hm: totalAv },
        positivas: { h: posH, m: posM, hm: totalPos, pctH: pctPosH, pctM: pctPosM, pct: pctPos },
        negativas: { h: negH, m: negM, hm: totalNeg, pctH: pctNegH, pctM: pctNegM, pct: pctNeg }
      };
    });

    // Campos de prazo, data e director de turma são estritamente opcionais
    const conselhoDef = {
      presidente: turma.director_turma || '',
      presidenteT1: turma.director_turma || '',
      presidenteT2: turma.director_turma || '',
      presidenteT3: turma.director_turma || '',
      data: '',
      prazo: '',
      director_turma: turma.director_turma || '',
      dataT1: '',
      dataT2: '',
      dataT3: '',
      horaInicioT1: '',
      minInicioT1: '',
      horaFimT1: '',
      minFimT1: '',
      horaInicioT2: '',
      minInicioT2: '',
      horaFimT2: '',
      minFimT2: '',
      horaInicioT3: '',
      minInicioT3: '',
      horaFimT3: '',
      minFimT3: ''
    };

    const conselho = { ...conselhoDef, ...(conselhoParams || {}) };

    return {
      escola,
      turma,
      conselho,
      tabelaEfectivo,
      tabelaAproveitamento,
      disciplinas: estatisticaDisciplinas,
      trimestresComNotas: pautaCompleta.trimestresComNotas
    };
  }

  async exportarPautaPdf(escolaId: string, turmaId: string, anoLetivo = '2026'): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.getPautaCompleta(escolaId, turmaId, anoLetivo);
    const buffer = await PdfKitDocumentosService.gerarPautaPdf({
      escola: dados.escola,
      turma: dados.turma,
      disciplinas: dados.disciplinas,
      alunos: dados.alunos
    });
    const filename = `Pauta_${dados.turma.nome.replace(/\s+/g, '_')}_${anoLetivo}.pdf`;
    return { buffer, filename };
  }

  async exportarPautaDocx(escolaId: string, turmaId: string, anoLetivo = '2026'): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.getPautaCompleta(escolaId, turmaId, anoLetivo);
    const buffer = await DocxDocumentosService.gerarPautaDocx({
      escola: dados.escola,
      turma: dados.turma,
      disciplinas: dados.disciplinas,
      alunos: dados.alunos
    });
    const filename = `Pauta_${dados.turma.nome.replace(/\s+/g, '_')}_${anoLetivo}.docx`;
    return { buffer, filename };
  }

  async exportarPautaTurmaXlsx(escolaId: string, turmaId: string, anoLetivo = '2026'): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.getPautaCompleta(escolaId, turmaId, anoLetivo);
    const buffer = SheetJsDocumentosService.gerarPautaXlsx({
      escola: dados.escola,
      turma: dados.turma,
      disciplinas: dados.disciplinas,
      alunos: dados.alunos
    });

    const filename = `Pauta_${dados.turma.nome.replace(/\s+/g, '_')}_${dados.turma.ano_letivo}.xlsx`;
    return { buffer, filename };
  }

  async exportarActaPdf(escolaId: string, turmaId: string, anoLetivo = '2026', conselhoParams?: any): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.getActaConselhoAvaliacao(escolaId, turmaId, anoLetivo, conselhoParams);
    const buffer = await PdfKitDocumentosService.gerarActaPdf({
      escola: dados.escola,
      turma: dados.turma,
      conselho: dados.conselho,
      trimestresComNotas: dados.trimestresComNotas,
      estatisticaAproveitamento: dados.tabelaAproveitamento
    });
    const filename = `Acta_${dados.turma.nome.replace(/\s+/g, '_')}_${anoLetivo}.pdf`;
    return { buffer, filename };
  }

  async exportarActaDocx(escolaId: string, turmaId: string, anoLetivo = '2026', conselhoParams?: any): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.getActaConselhoAvaliacao(escolaId, turmaId, anoLetivo, conselhoParams);
    const buffer = await DocxDocumentosService.gerarActaDocx({
      escola: dados.escola,
      turma: dados.turma,
      conselho: dados.conselho,
      trimestresComNotas: dados.trimestresComNotas,
      estatisticaAproveitamento: dados.tabelaAproveitamento
    });
    const filename = `Acta_${dados.turma.nome.replace(/\s+/g, '_')}_${anoLetivo}.docx`;
    return { buffer, filename };
  }

  async exportarActaTurmaXlsx(escolaId: string, turmaId: string, anoLetivo = '2026', conselhoParams?: any): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.getActaConselhoAvaliacao(escolaId, turmaId, anoLetivo, conselhoParams);
    const buffer = SheetJsDocumentosService.gerarActaXlsx({
      escola: dados.escola,
      turma: dados.turma,
      conselho: dados.conselho,
      trimestresComNotas: dados.trimestresComNotas,
      estatisticaAproveitamento: dados.tabelaAproveitamento
    });

    const filename = `Acta_${dados.turma.nome.replace(/\s+/g, '_')}_${dados.turma.ano_letivo}.xlsx`;
    return { buffer, filename };
  }

  async getEstatisticasAproveitamentoGeral(escolaId: string, anoLetivo = '2026', periodo = 'GLOBAL') {
    const escola = await prisma.escola.findUnique({ where: { id: escolaId } });
    if (!escola) throw new Error('Escola não encontrada');

    const turmas = await prisma.turma.findMany({
      where: { escola_id: escolaId, ano_letivo: anoLetivo },
      include: { director_turma: true },
      orderBy: [{ grau_ano: 'asc' }, { nome: 'asc' }]
    });

    const porTurma: any[] = [];
    const classesMap: Record<string, {
      classe: string;
      turmas: number;
      inscritos: { h: number; m: number; total: number };
      avaliados: { h: number; m: number; total: number };
      aprovados: { h: number; m: number; total: number; pct: number };
      reprovados: { h: number; m: number; total: number; pct: number };
    }> = {};

    const geralEscola = {
      totalTurmas: turmas.length,
      inscritos: { h: 0, m: 0, total: 0 },
      avaliados: { h: 0, m: 0, total: 0 },
      aprovados: { h: 0, m: 0, total: 0, pct: 0 },
      reprovados: { h: 0, m: 0, total: 0, pct: 0 }
    };

    const disciplinasAggMap: Record<string, {
      id: string;
      nome: string;
      codigo: string;
      avaliadosH: number;
      avaliadosM: number;
      aprovadosH: number;
      aprovadosM: number;
      somaNotas: number;
      qtdNotas: number;
    }> = {};

    for (const t of turmas) {
      const pauta = await this.getPautaCompleta(escolaId, t.id, anoLetivo);
      const est = pauta.estatistica;

      porTurma.push({
        turmaId: t.id,
        turmaNome: t.nome,
        grau_ano: t.grau_ano,
        turno: t.turno || 'Diurno',
        directorTurma: t.director_turma ? t.director_turma.nome : 'Não Alocado',
        inscritos: est.inscritos,
        avaliados: est.avaliados,
        aprovados: est.aprovados,
        reprovados: est.reprovados,
        trimestresComNotas: pauta.trimestresComNotas
      });

      // Agregação por Classe (Ex: 7ª, 8ª, 9ª, 10ª, 11ª, 12ª)
      const classeKey = t.grau_ano || 'Outra';
      if (!classesMap[classeKey]) {
        classesMap[classeKey] = {
          classe: classeKey,
          turmas: 0,
          inscritos: { h: 0, m: 0, total: 0 },
          avaliados: { h: 0, m: 0, total: 0 },
          aprovados: { h: 0, m: 0, total: 0, pct: 0 },
          reprovados: { h: 0, m: 0, total: 0, pct: 0 }
        };
      }
      const c = classesMap[classeKey];
      c.turmas += 1;
      c.inscritos.h += est.inscritos.h;
      c.inscritos.m += est.inscritos.m;
      c.inscritos.total += est.inscritos.total;
      c.avaliados.h += est.avaliados.h;
      c.avaliados.m += est.avaliados.m;
      c.avaliados.total += est.avaliados.total;
      c.aprovados.h += est.aprovados.h;
      c.aprovados.m += est.aprovados.m;
      c.aprovados.total += est.aprovados.total;
      c.reprovados.h += est.reprovados.h;
      c.reprovados.m += est.reprovados.m;
      c.reprovados.total += est.reprovados.total;

      // Agregação Geral da Escola
      geralEscola.inscritos.h += est.inscritos.h;
      geralEscola.inscritos.m += est.inscritos.m;
      geralEscola.inscritos.total += est.inscritos.total;
      geralEscola.avaliados.h += est.avaliados.h;
      geralEscola.avaliados.m += est.avaliados.m;
      geralEscola.avaliados.total += est.avaliados.total;
      geralEscola.aprovados.h += est.aprovados.h;
      geralEscola.aprovados.m += est.aprovados.m;
      geralEscola.aprovados.total += est.aprovados.total;
      geralEscola.reprovados.h += est.reprovados.h;
      geralEscola.reprovados.m += est.reprovados.m;
      geralEscola.reprovados.total += est.reprovados.total;

      // Agregação por Disciplina
      for (const d of pauta.disciplinas) {
        if (!disciplinasAggMap[d.id]) {
          disciplinasAggMap[d.id] = {
            id: d.id,
            nome: d.nome,
            codigo: d.codigo,
            avaliadosH: 0,
            avaliadosM: 0,
            aprovadosH: 0,
            aprovadosM: 0,
            somaNotas: 0,
            qtdNotas: 0
          };
        }
        const discAgg = disciplinasAggMap[d.id];
        for (const aluno of pauta.alunos) {
          const nd = aluno.notasDisciplinas[d.id];
          if (nd && nd.mfd !== null && nd.mfd !== undefined) {
            const isM = aluno.genero.toUpperCase() === 'M';
            if (isM) discAgg.avaliadosH++; else discAgg.avaliadosM++;
            discAgg.somaNotas += nd.mfd;
            discAgg.qtdNotas++;
            if (nd.mfd >= 9.5) {
              if (isM) discAgg.aprovadosH++; else discAgg.aprovadosM++;
            }
          }
        }
      }
    }

    // Calcular percentagens por classe
    Object.values(classesMap).forEach(c => {
      c.aprovados.pct = c.avaliados.total > 0 ? Number(((c.aprovados.total / c.avaliados.total) * 100).toFixed(1)) : 0;
      c.reprovados.pct = c.avaliados.total > 0 ? Number(((c.reprovados.total / c.avaliados.total) * 100).toFixed(1)) : 0;
    });

    // Calcular percentagens gerais da escola
    geralEscola.aprovados.pct = geralEscola.avaliados.total > 0 ? Number(((geralEscola.aprovados.total / geralEscola.avaliados.total) * 100).toFixed(1)) : 0;
    geralEscola.reprovados.pct = geralEscola.avaliados.total > 0 ? Number(((geralEscola.reprovados.total / geralEscola.avaliados.total) * 100).toFixed(1)) : 0;

    // Formatar disciplinas
    const porDisciplina = Object.values(disciplinasAggMap).map(d => {
      const avaliadosTotal = d.avaliadosH + d.avaliadosM;
      const aprovadosTotal = d.aprovadosH + d.aprovadosM;
      const reprovadosH = Math.max(0, d.avaliadosH - d.aprovadosH);
      const reprovadosM = Math.max(0, d.avaliadosM - d.aprovadosM);
      const reprovadosTotal = reprovadosH + reprovadosM;
      const pctAprovados = avaliadosTotal > 0 ? Number(((aprovadosTotal / avaliadosTotal) * 100).toFixed(1)) : 0;
      const pctReprovados = avaliadosTotal > 0 ? Number(((reprovadosTotal / avaliadosTotal) * 100).toFixed(1)) : 0;
      const mediaFinal = d.qtdNotas > 0 ? Number((d.somaNotas / d.qtdNotas).toFixed(1)) : null;

      return {
        id: d.id,
        nome: d.nome,
        codigo: d.codigo,
        avaliados: { h: d.avaliadosH, m: d.avaliadosM, total: avaliadosTotal },
        aprovados: { h: d.aprovadosH, m: d.aprovadosM, total: aprovadosTotal, pct: pctAprovados },
        reprovados: { h: reprovadosH, m: reprovadosM, total: reprovadosTotal, pct: pctReprovados },
        mediaFinal
      };
    }).sort((a, b) => a.nome.localeCompare(b.nome));

    return {
      escola: {
        id: escola.id,
        nome: escola.nome,
        provincia: escola.provincia,
        distrito: escola.distrito
      },
      anoLetivo,
      periodo,
      geralEscola,
      porClasse: Object.values(classesMap).sort((a, b) => a.classe.localeCompare(b.classe, undefined, { numeric: true })),
      porTurma,
      porDisciplina
    };
  }

  async exportarEstatisticasGeraisXlsx(escolaId: string, anoLetivo = '2026', periodo = 'GLOBAL'): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.getEstatisticasAproveitamentoGeral(escolaId, anoLetivo, periodo);
    const buffer = await ExportExcelService.gerarEstatisticasAproveitamentoXlsx(dados);
    const filename = `Estatisticas_Aproveitamento_${dados.escola.nome.replace(/\s+/g, '_')}_${anoLetivo}.xlsx`;
    return { buffer, filename };
  }

  async exportarPautaJson(escolaId: string, turmaId: string, anoLetivo = '2026', usuarioId?: string): Promise<{ json: any; filename: string }> {
    const dados = await this.getPautaCompleta(escolaId, turmaId, anoLetivo);
    const safeTurma = dados.turma.nome.replace(/\s+/g, '_');
    await impressaoService.salvarDocumentoJson({
      escolaId,
      tipoDocumento: 'PAUTA',
      titulo: `Pauta Geral - Turma ${dados.turma.nome}`,
      anoLetivo,
      dados,
      turmaId,
      usuarioId
    });
    return {
      json: dados,
      filename: `Pauta_${safeTurma}_${anoLetivo}.json`
    };
  }

  async exportarActaJson(escolaId: string, turmaId: string, anoLetivo = '2026', queryParams: any = {}, usuarioId?: string): Promise<{ json: any; filename: string }> {
    const dados = await this.getActaConselhoAvaliacao(escolaId, turmaId, anoLetivo, queryParams);
    const safeTurma = dados.turma.nome.replace(/\s+/g, '_');
    await impressaoService.salvarDocumentoJson({
      escolaId,
      tipoDocumento: 'ACTA',
      titulo: `Acta do Conselho - Turma ${dados.turma.nome}`,
      anoLetivo,
      dados,
      turmaId,
      usuarioId
    });
    return {
      json: dados,
      filename: `Acta_${safeTurma}_${anoLetivo}.json`
    };
  }

  async exportarEstatisticasGeraisJson(escolaId: string, anoLetivo = '2026', periodo = 'GLOBAL', usuarioId?: string): Promise<{ json: any; filename: string }> {
    const dados = await this.getEstatisticasAproveitamentoGeral(escolaId, anoLetivo, periodo);
    const safeEscola = dados.escola.nome.replace(/\s+/g, '_');
    await impressaoService.salvarDocumentoJson({
      escolaId,
      tipoDocumento: 'ESTATISTICA',
      titulo: `Estatísticas de Aproveitamento Geral - ${dados.escola.nome}`,
      anoLetivo,
      dados,
      usuarioId
    });
    return {
      json: dados,
      filename: `Estatisticas_${safeEscola}_${anoLetivo}_${periodo}.json`
    };
  }
}

export const pautasService = new PautasService();

