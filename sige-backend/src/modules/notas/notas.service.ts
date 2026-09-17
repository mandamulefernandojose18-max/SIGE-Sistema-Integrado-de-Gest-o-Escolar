import prisma from '../../config/database';
import { calcularMediaTrimestral } from '../../utils/avaliacoes-mocambique';

export class NotasService {
  async list(escolaId: string, filtros: { turmaId?: string; disciplinaId?: string; periodo?: string; alunoId?: string }) {
    return prisma.nota.findMany({
      where: {
        escola_id: escolaId,
        ...(filtros.turmaId ? { turma_id: filtros.turmaId } : {}),
        ...(filtros.disciplinaId ? { disciplina_id: filtros.disciplinaId } : {}),
        ...(filtros.periodo ? { periodo: filtros.periodo } : {}),
        ...(filtros.alunoId ? { aluno_id: filtros.alunoId } : {})
      },
      include: {
        aluno: true,
        disciplina: true,
        turma: true
      },
      orderBy: [{ turma_id: 'asc' }, { aluno: { nome: 'asc' } }]
    });
  }

  async lancarNota(escolaId: string, dados: {
    aluno_id: string;
    disciplina_id: string;
    turma_id: string;
    periodo: string;
    teste1?: number | null;
    teste2?: number | null;
    teste3?: number | null;
    teste4?: number | null;
    trabalho?: number | null;
    avaliacao_trimestral?: number | null;
    faltas?: number;
    anotacao?: string | null;
    comportamento?: string | null;
  }) {
    const calc = calcularMediaTrimestral({
      teste1: dados.teste1,
      teste2: dados.teste2,
      teste3: dados.teste3,
      teste4: dados.teste4,
      trabalho: dados.trabalho,
      avaliacao_trimestral: dados.avaliacao_trimestral
    });

    const notaExistente = await prisma.nota.findFirst({
      where: {
        escola_id: escolaId,
        aluno_id: dados.aluno_id,
        disciplina_id: dados.disciplina_id,
        periodo: dados.periodo
      }
    });

    if (notaExistente) {
      return prisma.nota.update({
        where: { id: notaExistente.id },
        data: {
          turma_id: dados.turma_id,
          teste1: dados.teste1 ?? 0,
          teste2: dados.teste2 ?? 0,
          teste3: dados.teste3,
          teste4: dados.teste4,
          trabalho: dados.trabalho ?? 0,
          avaliacao_trimestral: dados.avaliacao_trimestral ?? 0,
          media_final: calc.mediaFinal,
          faltas: dados.faltas ?? notaExistente.faltas,
          anotacao: dados.anotacao ?? notaExistente.anotacao,
          comportamento: dados.comportamento || calc.comportamento,
          resultado: calc.resultado
        },
        include: { aluno: true, disciplina: true, turma: true }
      });
    } else {
      return prisma.nota.create({
        data: {
          escola_id: escolaId,
          aluno_id: dados.aluno_id,
          disciplina_id: dados.disciplina_id,
          turma_id: dados.turma_id,
          periodo: dados.periodo,
          teste1: dados.teste1 ?? 0,
          teste2: dados.teste2 ?? 0,
          teste3: dados.teste3,
          teste4: dados.teste4,
          trabalho: dados.trabalho ?? 0,
          avaliacao_trimestral: dados.avaliacao_trimestral ?? 0,
          media_final: calc.mediaFinal,
          faltas: dados.faltas ?? 0,
          anotacao: dados.anotacao,
          comportamento: dados.comportamento || calc.comportamento,
          resultado: calc.resultado
        },
        include: { aluno: true, disciplina: true, turma: true }
      });
    }
  }

  async lancarLote(escolaId: string, notas: Array<{
    aluno_id: string;
    disciplina_id: string;
    turma_id: string;
    periodo: string;
    teste1?: number | null;
    teste2?: number | null;
    teste3?: number | null;
    teste4?: number | null;
    trabalho?: number | null;
    avaliacao_trimestral?: number | null;
    faltas?: number;
    anotacao?: string | null;
    comportamento?: string | null;
  }>) {
    const resultados: any[] = [];
    for (const item of notas) {
      const nota = await this.lancarNota(escolaId, item);
      resultados.push(nota);
    }
    return resultados;
  }

  async validarPermissaoTrimestre(escolaId: string, professorId: string, turmaId: string, disciplinaId: string, periodo: string) {
    const escola = await prisma.escola.findUnique({ where: { id: escolaId } });
    if (!escola) throw new Error('Escola não encontrada');

    const trimestreAtivo = typeof escola.trimestre_ativo === 'string'
      ? (parseInt(escola.trimestre_ativo.replace(/\D/g, '')) || 1)
      : (escola.trimestre_ativo || 1);
    const match = periodo.match(/(\d)/);
    const trimestreNota = match ? parseInt(match[1], 10) : 1;

    if (trimestreNota < trimestreAtivo) {
      const permissao = await prisma.permissaoEdicaoNotas.findFirst({
        where: {
          escola_id: escolaId,
          professor_id: professorId,
          turma_id: turmaId,
          disciplina_id: disciplinaId,
          periodo: periodo,
          ativa: true
        }
      });

      if (!permissao) {
        throw new Error(`Edição de notas bloqueada para o ${trimestreNota}º Trimestre (Trimestre activo actual: ${trimestreAtivo}º). Solicite autorização de desbloqueio ao Director ou ao DAP.`);
      }
    }
  }

  async autorizarDesbloqueio(escolaId: string, dados: {
    professor_id?: string | null;
    turma_id: string;
    disciplina_id?: string | null;
    periodo: string;
    autorizado_por: string;
    motivo?: string;
  }) {
    const alocacoes = await prisma.professorDisciplinaTurma.findMany({
      where: {
        escola_id: escolaId,
        turma_id: dados.turma_id,
        ...(dados.professor_id ? { professor_id: dados.professor_id } : {}),
        ...(dados.disciplina_id ? { disciplina_id: dados.disciplina_id } : {})
      }
    });

    if (alocacoes.length > 0) {
      const perms: any[] = [];
      for (const aloc of alocacoes) {
        const p = await prisma.permissaoEdicaoNotas.create({
          data: {
            escola_id: escolaId,
            professor_id: aloc.professor_id,
            turma_id: dados.turma_id,
            disciplina_id: aloc.disciplina_id,
            periodo: dados.periodo,
            autorizado_por: dados.autorizado_por,
            motivo: dados.motivo || 'Autorizado pela Direcção Pedagógica (DAP)',
            ativa: true
          }
        });
        perms.push(p);
      }
      return perms[0];
    } else {
      const profId = dados.professor_id || (await prisma.professor.findFirst({ where: { escola_id: escolaId } }))?.id;
      const discId = dados.disciplina_id || (await prisma.disciplina.findFirst({ where: { escola_id: escolaId } }))?.id;
      if (profId && discId) {
        return prisma.permissaoEdicaoNotas.create({
          data: {
            escola_id: escolaId,
            professor_id: profId,
            turma_id: dados.turma_id,
            disciplina_id: discId,
            periodo: dados.periodo,
            autorizado_por: dados.autorizado_por,
            motivo: dados.motivo || 'Autorizado pela Direcção Pedagógica (DAP)',
            ativa: true
          }
        });
      }
      return null;
    }
  }

  async getStats(escolaId: string, filtros?: { turmaId?: string; periodo?: string }) {
    const notas = await prisma.nota.findMany({
      where: {
        escola_id: escolaId,
        ...(filtros?.turmaId ? { turma_id: filtros.turmaId } : {}),
        ...(filtros?.periodo ? { periodo: filtros.periodo } : {})
      },
      include: { turma: true, disciplina: true, aluno: true }
    });

    const corte = 9.5; // Nota mínima de corte oficial de Moçambique
    const totalNotas = notas.length;
    let somaNotas = 0;
    let acimaCorte = 0;
    let abaixoCorte = 0;
    let totalFaltas = 0;

    const mediasPorTurma: Record<string, { nome: string; soma: number; count: number; acima: number; abaixo: number }> = {};

    notas.forEach(n => {
      somaNotas += n.media_final;
      totalFaltas += n.faltas;

      if (n.media_final >= corte) acimaCorte++;
      else abaixoCorte++;

      if (!mediasPorTurma[n.turma_id]) {
        mediasPorTurma[n.turma_id] = {
          nome: n.turma.nome,
          soma: 0,
          count: 0,
          acima: 0,
          abaixo: 0
        };
      }
      mediasPorTurma[n.turma_id].soma += n.media_final;
      mediasPorTurma[n.turma_id].count++;
      if (n.media_final >= corte) mediasPorTurma[n.turma_id].acima++;
      else mediasPorTurma[n.turma_id].abaixo++;
    });

    const mediaGeral = totalNotas > 0 ? Number((somaNotas / totalNotas).toFixed(1)) : 0;
    const taxaAprovacao = totalNotas > 0 ? Number(((acimaCorte / totalNotas) * 100).toFixed(1)) : 0;

    const turmasFormatadas = Object.values(mediasPorTurma).map(t => ({
      nome: t.nome,
      media: Number((t.soma / t.count).toFixed(1)),
      acimaCorte: t.acima,
      abaixoCorte: t.abaixo
    }));

    return {
      corte,
      totalLancamentos: totalNotas,
      mediaGeral,
      acimaCorte,
      abaixoCorte,
      taxaAprovacao,
      totalFaltas,
      mediasPorTurma: turmasFormatadas
    };
  }
}

export const notasService = new NotasService();
