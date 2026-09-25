import prisma from '../../config/database';

export class DisciplinasService {
  async list(escolaId: string, filtros?: { anoLetivo?: string; classe?: string }) {
    return prisma.disciplina.findMany({
      where: {
        escola_id: escolaId,
        ...(filtros?.anoLetivo ? { ano_letivo: filtros.anoLetivo } : {}),
        ...(filtros?.classe ? { classe: filtros.classe } : {})
      },
      include: {
        _count: { select: { alocacoes: true, notas: true } }
      },
      orderBy: [{ classe: 'asc' }, { nome: 'asc' }]
    });
  }

  async getById(escolaId: string, id: string) {
    return prisma.disciplina.findFirst({
      where: { id, escola_id: escolaId },
      include: {
        alocacoes: {
          include: {
            professor: true,
            turma: true
          }
        }
      }
    });
  }

  async create(escolaId: string, dados: {
    nome: string;
    codigo: string;
    classe?: string | null;
    area?: string | null;
    carga_horaria?: number;
    ano_letivo?: string;
  }) {
    return prisma.disciplina.create({
      data: {
        escola_id: escolaId,
        nome: dados.nome,
        codigo: dados.codigo.toUpperCase(),
        classe: dados.classe || '10ª Classe',
        area: dados.area || 'Geral',
        carga_horaria: dados.carga_horaria || 60,
        ano_letivo: dados.ano_letivo || '2026'
      }
    });
  }

  async update(escolaId: string, id: string, dados: any) {
    if (dados.codigo) dados.codigo = dados.codigo.toUpperCase();
    return prisma.disciplina.update({
      where: { id, escola_id: escolaId },
      data: dados
    });
  }

  async delete(escolaId: string, id: string) {
    // Remover alocações e notas dependentes antes de eliminar a disciplina
    await prisma.professorDisciplinaTurma.deleteMany({
      where: { escola_id: escolaId, disciplina_id: id }
    });
    await prisma.nota.deleteMany({
      where: { escola_id: escolaId, disciplina_id: id }
    });
    return prisma.disciplina.delete({
      where: { id, escola_id: escolaId }
    });
  }

  async getStats(escolaId: string) {
    const disciplinas = await prisma.disciplina.findMany({
      where: { escola_id: escolaId },
      include: {
        notas: {
          select: {
            media_final: true
          }
        }
      }
    });

    const rankingReprovacao: Array<{
      id: string;
      nome: string;
      codigo: string;
      totalNotas: number;
      mediaGeral: number;
      reprovados: number;
      taxaReprovacao: number;
    }> = [];

    let somaMediasGerais = 0;
    let disciplinasComNotas = 0;

    disciplinas.forEach(d => {
      const total = d.notas.length;
      if (total === 0) {
        rankingReprovacao.push({
          id: d.id,
          nome: d.nome,
          codigo: d.codigo,
          totalNotas: 0,
          mediaGeral: 0,
          reprovados: 0,
          taxaReprovacao: 0
        });
        return;
      }

      let soma = 0;
      let reprovados = 0;

      d.notas.forEach(n => {
        soma += n.media_final;
        // Padrão de aprovação de Moçambique: >= 9.5 valores
        if (n.media_final < 9.5) {
          reprovados++;
        }
      });

      const media = Number((soma / total).toFixed(1));
      const taxa = Number(((reprovados / total) * 100).toFixed(1));

      somaMediasGerais += media;
      disciplinasComNotas++;

      rankingReprovacao.push({
        id: d.id,
        nome: d.nome,
        codigo: d.codigo,
        totalNotas: total,
        mediaGeral: media,
        reprovados,
        taxaReprovacao: taxa
      });
    });

    // Ordenar pelas com maior taxa de reprovação
    rankingReprovacao.sort((a, b) => b.taxaReprovacao - a.taxaReprovacao);

    const mediaGeralEscola =
      disciplinasComNotas > 0 ? Number((somaMediasGerais / disciplinasComNotas).toFixed(1)) : 0;

    return {
      totalDisciplinas: disciplinas.length,
      mediaGeralEscola,
      rankingReprovacao: rankingReprovacao.slice(0, 10)
    };
  }
}

export const disciplinasService = new DisciplinasService();
