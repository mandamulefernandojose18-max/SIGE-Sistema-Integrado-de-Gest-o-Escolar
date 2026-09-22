import prisma from '../../config/database';

export class PagamentosService {
  async list(escolaId: string, filtros?: { status?: string; mesReferencia?: string; alunoId?: string }) {
    return prisma.pagamento.findMany({
      where: {
        escola_id: escolaId,
        ...(filtros?.status ? { status: filtros.status } : {}),
        ...(filtros?.mesReferencia ? { mes_referencia: filtros.mesReferencia } : {}),
        ...(filtros?.alunoId ? { aluno_id: filtros.alunoId } : {})
      },
      include: {
        aluno: {
          include: { turma: true }
        }
      },
      orderBy: { data_vencimento: 'desc' }
    });
  }

  async getById(escolaId: string, id: string) {
    return prisma.pagamento.findFirst({
      where: { id, escola_id: escolaId },
      include: {
        aluno: {
          include: { turma: true }
        },
        escola: true
      }
    });
  }

  async create(escolaId: string, dados: {
    aluno_id: string;
    descricao: string;
    mes_referencia: string;
    valor: number;
    data_vencimento: string;
  }) {
    return prisma.pagamento.create({
      data: {
        escola_id: escolaId,
        aluno_id: dados.aluno_id,
        descricao: dados.descricao,
        mes_referencia: dados.mes_referencia,
        valor: dados.valor,
        data_vencimento: new Date(dados.data_vencimento),
        status: 'PENDENTE'
      },
      include: { aluno: true }
    });
  }

  async gerarMensalidadesTurma(escolaId: string, dados: {
    turma_id: string;
    mes_referencia: string;
    descricao: string;
    valor: number;
    data_vencimento: string;
  }) {
    const alunos = await prisma.aluno.findMany({
      where: { escola_id: escolaId, turma_id: dados.turma_id, status: 'ATIVO' }
    });

    const vencimento = new Date(dados.data_vencimento);
    const pagamentosCriados: any[] = [];

    for (const aluno of alunos) {
      // Evitar duplicidade de mensalidade no mesmo mês
      const existe = await prisma.pagamento.findFirst({
        where: {
          escola_id: escolaId,
          aluno_id: aluno.id,
          mes_referencia: dados.mes_referencia,
          descricao: dados.descricao
        }
      });

      if (!existe) {
        const p = await prisma.pagamento.create({
          data: {
            escola_id: escolaId,
            aluno_id: aluno.id,
            descricao: dados.descricao,
            mes_referencia: dados.mes_referencia,
            valor: dados.valor,
            data_vencimento: vencimento,
            status: 'PENDENTE'
          }
        });
        pagamentosCriados.push(p);
      }
    }

    return {
      gerados: pagamentosCriados.length,
      turmaAlunos: alunos.length
    };
  }

  async liquidar(escolaId: string, id: string, dados: {
    valor_pago: number;
    metodo_pagamento: string;
    data_pagamento?: string;
  }) {
    const pagamento = await prisma.pagamento.findFirst({
      where: { id, escola_id: escolaId }
    });

    if (!pagamento) throw new Error('Pagamento não encontrado');

    const agora = dados.data_pagamento ? new Date(dados.data_pagamento) : new Date();
    const reciboNumero = `REC-${agora.getFullYear()}-${Math.floor(10000 + Math.random() * 90000)}`;

    return prisma.pagamento.update({
      where: { id },
      data: {
        valor_pago: dados.valor_pago,
        status: 'PAGO',
        data_pagamento: agora,
        metodo_pagamento: dados.metodo_pagamento,
        recibo_numero: reciboNumero
      },
      include: { aluno: true }
    });
  }

  async getStats(escolaId: string, mesReferencia?: string) {
    const pagamentos = await prisma.pagamento.findMany({
      where: {
        escola_id: escolaId,
        ...(mesReferencia ? { mes_referencia: mesReferencia } : {})
      }
    });

    const totalAlunos = await prisma.aluno.count({
      where: { escola_id: escolaId, status: 'ATIVO' }
    });

    let totalFaturado = 0;
    let totalPendente = 0;
    let totalAtrasado = 0;
    let totalEsperado = 0;

    const agora = new Date();
    const alunosComPendencia = new Set<string>();

    pagamentos.forEach(p => {
      totalEsperado += p.valor;
      if (p.status === 'PAGO') {
        totalFaturado += p.valor_pago || p.valor;
      } else if (p.status === 'PENDENTE') {
        if (new Date(p.data_vencimento) < agora) {
          totalAtrasado += p.valor;
          if (p.aluno_id) alunosComPendencia.add(p.aluno_id);
        } else {
          totalPendente += p.valor;
        }
      }
    });

    const taxaInadimplencia = totalEsperado > 0 ? Number(((totalAtrasado / totalEsperado) * 100).toFixed(1)) : 0;
    const projecaoReceita = totalFaturado + totalPendente + totalAtrasado;

    // Alunos adimplentes (com pagamentos em dia)
    const totalInadimplentes = alunosComPendencia.size;
    const totalAdimplentes = Math.max(0, totalAlunos - totalInadimplentes);
    const percentualAdimplentes = totalAlunos > 0 ? Number(((totalAdimplentes / totalAlunos) * 100).toFixed(1)) : 100;

    // Faturamento dos últimos 6 meses
    const faturamentoHistorico: Record<string, number> = {};
    const hoje = new Date();
    for (let i = 5; i >= 0; i--) {
      const d = new Date(hoje.getFullYear(), hoje.getMonth() - i, 1);
      const chave = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
      faturamentoHistorico[chave] = 0;
    }

    const todosPagos = await prisma.pagamento.findMany({
      where: { escola_id: escolaId, status: 'PAGO' },
      select: { valor_pago: true, valor: true, data_pagamento: true }
    });

    todosPagos.forEach(p => {
      if (p.data_pagamento) {
        const chave = `${p.data_pagamento.getFullYear()}-${String(p.data_pagamento.getMonth() + 1).padStart(2, '0')}`;
        if (faturamentoHistorico[chave] !== undefined) {
          faturamentoHistorico[chave] += (p.valor_pago || p.valor);
        }
      }
    });

    return {
      totalFaturado: Number(totalFaturado.toFixed(2)),
      totalPendente: Number(totalPendente.toFixed(2)),
      totalAtrasado: Number(totalAtrasado.toFixed(2)),
      projecaoReceita: Number(projecaoReceita.toFixed(2)),
      taxaInadimplencia,
      totalAlunos,
      totalAdimplentes,
      totalInadimplentes,
      percentualAdimplentes,
      faturamentoHistorico
    };
  }
}

export const pagamentosService = new PagamentosService();
