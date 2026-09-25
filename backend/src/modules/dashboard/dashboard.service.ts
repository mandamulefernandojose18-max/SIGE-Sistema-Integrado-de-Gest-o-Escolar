import prisma from '../../config/database';

export class DashboardService {
  async getOverview(escolaId: string) {
    const agora = new Date();

    const [
      escola,
      totalAlunos,
      alunosAtivos,
      totalProfessores,
      totalTurmas,
      totalDisciplinas,
      pagamentosPendentes,
      pagamentosRecebidos,
      certificadosEmitidos,
      notasLancadas
    ] = await Promise.all([
      prisma.escola.findUnique({
        where: { id: escolaId },
        include: {
          assinaturas: { orderBy: { data_fim: 'desc' }, take: 1, include: { plano: true } }
        }
      }),
      prisma.aluno.count({ where: { escola_id: escolaId } }),
      prisma.aluno.count({ where: { escola_id: escolaId, status: 'ATIVO' } }),
      prisma.professor.count({ where: { escola_id: escolaId, ativo: true } }),
      prisma.turma.count({ where: { escola_id: escolaId } }),
      prisma.disciplina.count({ where: { escola_id: escolaId } }),
      prisma.pagamento.aggregate({
        where: { escola_id: escolaId, status: 'PENDENTE' },
        _sum: { valor: true },
        _count: { _all: true }
      }),
      prisma.pagamento.aggregate({
        where: { escola_id: escolaId, status: 'PAGO' },
        _sum: { valor_pago: true },
        _count: { _all: true }
      }),
      prisma.certificado.count({ where: { escola_id: escolaId } }),
      prisma.nota.count({ where: { escola_id: escolaId } })
    ]);

    const ultimaAssinatura = escola?.assinaturas[0] || null;
    let diasRestantesAssinatura = 0;
    if (ultimaAssinatura) {
      const diffMs = new Date(ultimaAssinatura.data_fim).getTime() - agora.getTime();
      diasRestantesAssinatura = Math.max(0, Math.ceil(diffMs / (1000 * 60 * 60 * 24)));
    }

    return {
      escola: {
        id: escola?.id,
        nome: escola?.nome,
        status: escola?.status,
        anoLetivo: escola?.ano_letivo_ativo,
        plano: ultimaAssinatura?.plano.nome || 'NENHUM',
        diasRestantesAssinatura,
        dataVencimentoAssinatura: ultimaAssinatura?.data_fim || null
      },
      indicadores: {
        totalAlunos,
        alunosAtivos,
        totalProfessores,
        totalTurmas,
        totalDisciplinas,
        certificadosEmitidos,
        notasLancadas,
        moeda: 'MZN',
        totalRecebido: Number((pagamentosRecebidos._sum.valor_pago || 0).toFixed(2)),
        totalPendente: Number((pagamentosPendentes._sum.valor || 0).toFixed(2)),
        totalRecebidoMZN: `${Number(pagamentosRecebidos._sum.valor_pago || 0).toLocaleString('pt-PT', { minimumFractionDigits: 2 })} MZN`,
        totalPendenteMZN: `${Number(pagamentosPendentes._sum.valor || 0).toLocaleString('pt-PT', { minimumFractionDigits: 2 })} MZN`,
        qtdPagamentosPendentes: pagamentosPendentes._count._all
      }
    };
  }
}

export const dashboardService = new DashboardService();
