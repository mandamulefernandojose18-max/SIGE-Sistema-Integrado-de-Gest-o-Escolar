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

    const buffer = ExportExcelService.gerarPautaXlsx({
      escola: {
        nome: dados.escola.nome,
        provincia: dados.escola.provincia,
        distrito: dados.escola.distrito
      },
      turma: {
        nome: dados.turma.nome,
        grau_ano: dados.turma.grau_ano,
        ano_letivo: dados.turma.ano_letivo
      },
      periodo: dados.pauta.periodo,
      disciplinas: dados.disciplinas,
      alunos: dados.alunos.map(a => ({
        numero: a.numero,
        matricula: a.matricula,
        nomeCompleto: a.nome,
        genero: a.genero,
        notas: a.notas,
        mediaGeral: a.mediaGeral,
        faltas: a.faltas,
        comportamento: a.comportamento,
        resultado: a.resultado
      }))
    });

    const filename = `Pauta_${dados.turma.nome.replace(/\s+/g, '_')}_${dados.pauta.periodo}_${dados.turma.ano_letivo}.xlsx`;
    return { buffer, filename };
  }

  async exportarActaXlsx(escolaId: string, id: string): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.getById(escolaId, id);
    if (!dados) throw new Error('Pauta não encontrada');

    // Calcular estatísticas por género
    const inscritos = { total: dados.alunos.length, m: 0, f: 0 };
    const avaliados = { total: 0, m: 0, f: 0 };
    const aprovados = { total: 0, m: 0, f: 0 };
    const reprovados = { total: 0, m: 0, f: 0 };

    dados.alunos.forEach(a => {
      const isFem = a.genero.toUpperCase() === 'F';
      if (isFem) inscritos.f++; else inscritos.m++;

      if (a.mediaGeral > 0) {
        avaliados.total++;
        if (isFem) avaliados.f++; else avaliados.m++;

        if (a.resultado === 'Aprovado') {
          aprovados.total++;
          if (isFem) aprovados.f++; else aprovados.m++;
        } else {
          reprovados.total++;
          if (isFem) reprovados.f++; else reprovados.m++;
        }
      }
    });

    const percentualAproveitamento = avaliados.total > 0
      ? Number(((aprovados.total / avaliados.total) * 100).toFixed(1))
      : 0;

    const buffer = ExportExcelService.gerarActaEstatisticaXlsx({
      escola: { nome: dados.escola.nome, provincia: dados.escola.provincia },
      turma: { nome: dados.turma.nome, grau_ano: dados.turma.grau_ano, ano_letivo: dados.turma.ano_letivo },
      periodo: dados.pauta.periodo,
      estatisticas: {
        inscritos,
        avaliados,
        aprovados,
        reprovados,
        percentualAproveitamento
      }
    });

    const filename = `Acta_${dados.turma.nome.replace(/\s+/g, '_')}_${dados.pauta.periodo}_${dados.turma.ano_letivo}.xlsx`;
    return { buffer, filename };
  }
}

export const pautasService = new PautasService();
