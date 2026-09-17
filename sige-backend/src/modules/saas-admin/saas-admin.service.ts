import prisma from '../../config/database';
import { runSubscriptionExpirationCheck } from '../../jobs/subscription-expiration.job';
import bcrypt from 'bcryptjs';

export class SaasAdminService {
  async getMetrics() {
    const [totalEscolas, escolasAtivas, escolasExpiradas, escolasPendentes, escolasSuspensas, assinaturas, planos] =
      await Promise.all([
        prisma.escola.count(),
        prisma.escola.count({ where: { status: 'ATIVA' } }),
        prisma.escola.count({ where: { status: 'EXPIRADA' } }),
        prisma.escola.count({ where: { status: 'PENDENTE' } }),
        prisma.escola.count({ where: { status: 'SUSPENSA' } }),
        prisma.assinaturaEscola.findMany({
          where: { status: 'ATIVA' },
          include: { plano: true }
        }),
        prisma.plano.findMany({
          include: {
            _count: { select: { escolas: true, assinaturas: true } }
          },
          orderBy: { preco: 'asc' }
        })
      ]);

    // Cálculo do MRR (Receita Mensal Recorrente em MZN)
    let mrr = 0;
    assinaturas.forEach((ass) => {
      if (ass.plano.nome === 'MENSAL') {
        mrr += ass.valor;
      } else if (ass.plano.nome === 'TRIMESTRAL') {
        mrr += ass.valor / 3;
      } else if (ass.plano.nome === 'SEMESTRAL') {
        mrr += ass.valor / 6;
      } else if (ass.plano.nome === 'ANUAL') {
        mrr += ass.valor / 12;
      }
    });

    const arr = mrr * 12;
    const churn = totalEscolas > 0 ? (escolasExpiradas / totalEscolas) * 100 : 0;

    return {
      moeda: 'MZN',
      mrr: Number(mrr.toFixed(2)),
      arr: Number(arr.toFixed(2)),
      churn: Number(churn.toFixed(1)),
      escolas: {
        total: totalEscolas,
        ativas: escolasAtivas,
        expiradas: escolasExpiradas,
        pendentes: escolasPendentes,
        suspensas: escolasSuspensas
      },
      planos: planos.map(p => ({
        id: p.id,
        nome: p.nome,
        descricao: p.descricao,
        preco: p.preco,
        duracao_dias: p.duracao_dias,
        totalEscolas: p._count.escolas
      }))
    };
  }

  async listEscolas() {
    return prisma.escola.findMany({
      include: {
        plano: true,
        assinaturas: {
          orderBy: { data_fim: 'desc' },
          take: 1
        },
        _count: {
          select: { alunos: true, professores: true, turmas: true, usuarios: true }
        }
      },
      orderBy: { createdAt: 'desc' }
    });
  }

  async createEscola(dados: {
    nome: string;
    nif_cnpj: string;
    email: string;
    telefone?: string | null;
    endereco?: string | null;
    plano_id: string;
    adminNome?: string | null;
    adminEmail?: string | null;
    adminSenha?: string | null;
    provincia?: string | null;
    distrito?: string | null;
    usar_emblema_nacional?: boolean;
    logo_url?: string | null;
    valor_contrato?: number | null;
  }) {
    const plano = await prisma.plano.findUnique({ where: { id: dados.plano_id } });
    if (!plano) throw new Error('Plano selecionado não existe');

    const agora = new Date();
    const dataFim = new Date(agora);
    dataFim.setDate(dataFim.getDate() + plano.duracao_dias);

    const slug = dados.nome.toLowerCase().replace(/[^a-z0-9]/g, '').slice(0, 12) || 'escola';
    const adminNome = dados.adminNome || `Director(a) - ${dados.nome}`;
    let adminEmail = dados.adminEmail || dados.email || `admin@${slug}.edu.mz`;
    const adminSenha = dados.adminSenha || '123456';

    const existingUser = await prisma.usuario.findUnique({ where: { email: adminEmail } });
    if (existingUser) {
      adminEmail = `${slug}_${Math.floor(1000 + Math.random() * 9000)}@escola.edu.mz`;
    }

    const senhaHash = await bcrypt.hash(adminSenha, 10);
    const valorCobrado = dados.valor_contrato !== undefined && dados.valor_contrato !== null && dados.valor_contrato > 0
      ? dados.valor_contrato
      : plano.preco;

    return prisma.$transaction(async (tx) => {
      const escola = await tx.escola.create({
        data: {
          nome: dados.nome,
          nif_cnpj: dados.nif_cnpj,
          email: dados.email,
          telefone: dados.telefone || '+258 ',
          endereco: dados.endereco || undefined,
          plano_id: plano.id,
          status: 'ATIVA',
          provincia: dados.provincia || 'Maputo',
          distrito: dados.distrito || 'Cidade de Maputo',
          usar_emblema_nacional: dados.usar_emblema_nacional !== false,
          logo_url: dados.logo_url || undefined
        }
      });

      await tx.assinaturaEscola.create({
        data: {
          escola_id: escola.id,
          plano_id: plano.id,
          data_inicio: agora,
          data_fim: dataFim,
          valor: valorCobrado,
          status: 'ATIVA',
          metodo_pagamento: 'TRANSFERENCIA'
        }
      });

      const adminUser = await tx.usuario.create({
        data: {
          escola_id: escola.id,
          nome: adminNome,
          email: adminEmail,
          senha_hash: senhaHash,
          role: 'ADMIN_ESCOLA',
          ativo: true
        }
      });

      return { escola, adminUser };
    });
  }

  async updateEscola(escolaId: string, dados: {
    nome?: string;
    nif_cnpj?: string;
    email?: string;
    telefone?: string | null;
    endereco?: string | null;
    provincia?: string | null;
    distrito?: string | null;
    plano_id?: string | null;
    usar_emblema_nacional?: boolean;
    logo_url?: string | null;
    data_fim?: string | null;
    data_fim_assinatura?: string | null;
    dias_adicionais?: number | null;
  }) {
    const escola = await prisma.escola.findUnique({
      where: { id: escolaId },
      include: { assinaturas: { orderBy: { data_fim: 'desc' }, take: 1 } }
    });
    if (!escola) throw new Error('Escola não encontrada');

    return prisma.$transaction(async (tx) => {
      const updateData: any = {};
      if (dados.nome !== undefined) updateData.nome = dados.nome;
      if (dados.nif_cnpj !== undefined) updateData.nif_cnpj = dados.nif_cnpj;
      if (dados.email !== undefined) updateData.email = dados.email;
      if (dados.telefone !== undefined) updateData.telefone = dados.telefone;
      if (dados.endereco !== undefined) updateData.endereco = dados.endereco;
      if (dados.provincia !== undefined) updateData.provincia = dados.provincia;
      if (dados.distrito !== undefined) updateData.distrito = dados.distrito;
      if (dados.plano_id !== undefined && dados.plano_id !== null) updateData.plano_id = dados.plano_id;
      if (dados.usar_emblema_nacional !== undefined) updateData.usar_emblema_nacional = dados.usar_emblema_nacional;
      if (dados.logo_url !== undefined) updateData.logo_url = dados.logo_url;

      const escolaAtualizada = await tx.escola.update({
        where: { id: escolaId },
        data: updateData
      });

      const dataFimStr = dados.data_fim || dados.data_fim_assinatura;
      if (escola.assinaturas[0]) {
        let novaDataFim: Date | null = null;
        if (dataFimStr) {
          novaDataFim = new Date(dataFimStr);
        }
        if (dados.dias_adicionais && dados.dias_adicionais > 0) {
          const base = novaDataFim || new Date(escola.assinaturas[0].data_fim);
          base.setDate(base.getDate() + dados.dias_adicionais);
          novaDataFim = base;
        }

        if (novaDataFim) {
          await tx.assinaturaEscola.update({
            where: { id: escola.assinaturas[0].id },
            data: { data_fim: novaDataFim }
          });
        }
      }

      return escolaAtualizada;
    });
  }

  async toggleStatusEscola(escolaId: string) {
    const escola = await prisma.escola.findUnique({ where: { id: escolaId } });
    if (!escola) throw new Error('Escola não encontrada');

    const novoStatus = escola.status === 'ATIVA' ? 'SUSPENSA' : 'ATIVA';
    const bloqueadaManualmente = novoStatus === 'SUSPENSA';

    return prisma.escola.update({
      where: { id: escolaId },
      data: {
        status: novoStatus,
        bloqueada_manualmente: bloqueadaManualmente
      }
    });
  }

  async atualizarPrecoPlano(planoId: string, preco: number, descricao?: string) {
    return prisma.plano.update({
      where: { id: planoId },
      data: {
        preco,
        ...(descricao ? { descricao } : {})
      }
    });
  }

  async renovarAssinatura(escolaId: string, planoId?: string, diasAdicionais?: number) {
    const escola = await prisma.escola.findUnique({
      where: { id: escolaId },
      include: {
        plano: true,
        assinaturas: { orderBy: { data_fim: 'desc' }, take: 1 }
      }
    });

    if (!escola) throw new Error('Escola não encontrada');

    const targetPlanoId = planoId || escola.plano_id;
    if (!targetPlanoId) throw new Error('Nenhum plano associado');

    const plano = await prisma.plano.findUnique({ where: { id: targetPlanoId } });
    if (!plano) throw new Error('Plano não encontrado');

    const agora = new Date();
    let novaDataInicio = agora;
    const ultimaAssinatura = escola.assinaturas[0];

    if (ultimaAssinatura && new Date(ultimaAssinatura.data_fim) > agora) {
      novaDataInicio = new Date(ultimaAssinatura.data_fim);
    }

    const duracao = diasAdicionais || plano.duracao_dias;
    const novaDataFim = new Date(novaDataInicio);
    novaDataFim.setDate(novaDataFim.getDate() + duracao);

    const [novaAssinatura, escolaAtualizada] = await prisma.$transaction([
      prisma.assinaturaEscola.create({
        data: {
          escola_id: escola.id,
          plano_id: plano.id,
          data_inicio: novaDataInicio,
          data_fim: novaDataFim,
          valor: plano.preco,
          status: 'ATIVA',
          metodo_pagamento: 'TRANSFERENCIA'
        }
      }),
      prisma.escola.update({
        where: { id: escola.id },
        data: {
          status: 'ATIVA',
          plano_id: plano.id,
          bloqueada_manualmente: false
        }
      })
    ]);

    return {
      message: `Assinatura da escola [${escola.nome}] renovada com sucesso até ${novaDataFim.toLocaleDateString('pt-PT')}`,
      escola: escolaAtualizada,
      assinatura: novaAssinatura
    };
  }

  async gerarComprovativoContrato(escolaId: string) {
    const escola = await prisma.escola.findUnique({
      where: { id: escolaId },
      include: {
        plano: true,
        assinaturas: { orderBy: { data_fim: 'desc' }, take: 1 }
      }
    });

    if (!escola) throw new Error('Escola não encontrada');

    const assinatura = escola.assinaturas[0];
    const agora = new Date();

    return {
      reciboNumero: `REC-SAAS-${escola.nif_cnpj}-${agora.getFullYear()}`,
      titulo: 'RECIBO DE PAGAMENTO E COMPROVATIVO DE LICENÇA SAAS',
      dataEmissao: agora,
      escola: {
        id: escola.id,
        nome: escola.nome,
        nif_cnpj: escola.nif_cnpj,
        email: escola.email,
        telefone: escola.telefone,
        endereco: escola.endereco,
        provincia: escola.provincia,
        distrito: escola.distrito
      },
      licenca: {
        plano: escola.plano?.nome || 'MENSAL',
        valorMZN: assinatura ? `${assinatura.valor.toLocaleString('pt-PT', { minimumFractionDigits: 2 })} MZN` : '0,00 MZN',
        dataInicio: assinatura ? assinatura.data_inicio : agora,
        dataFim: assinatura ? assinatura.data_fim : agora,
        status: escola.status,
        ativo: escola.status === 'ATIVA'
      },
      emitidoPor: 'Direcção de Operações do SIGE Moçambique'
    };
  }

  async listPlanos() {
    return prisma.plano.findMany({ orderBy: { duracao_dias: 'asc' } });
  }

  async alterarStatusEscola(escolaId: string, status: 'ATIVA' | 'PENDENTE' | 'EXPIRADA' | 'SUSPENSA') {
    return prisma.escola.update({
      where: { id: escolaId },
      data: { status }
    });
  }

  async triggerExpirationCheck() {
    return runSubscriptionExpirationCheck();
  }

  async deleteEscola(escolaId: string) {
    return await prisma.$transaction(async (tx) => {
      await tx.nota.deleteMany({ where: { escola_id: escolaId } });
      await tx.pagamento.deleteMany({ where: { escola_id: escolaId } });
      await tx.pauta.deleteMany({ where: { escola_id: escolaId } });
      await tx.certificado.deleteMany({ where: { escola_id: escolaId } });
      await tx.permissaoEdicaoNotas.deleteMany({ where: { escola_id: escolaId } });
      await tx.logImpressao.deleteMany({ where: { escola_id: escolaId } });
      await tx.logAcesso.deleteMany({ where: { escola_id: escolaId } });
      await tx.professorDisciplinaTurma.deleteMany({ where: { escola_id: escolaId } });
      await tx.aluno.deleteMany({ where: { escola_id: escolaId } });
      await tx.professor.deleteMany({ where: { escola_id: escolaId } });
      await tx.turma.deleteMany({ where: { escola_id: escolaId } });
      await tx.disciplina.deleteMany({ where: { escola_id: escolaId } });
      await tx.assinaturaEscola.deleteMany({ where: { escola_id: escolaId } });
      await tx.usuario.deleteMany({ where: { escola_id: escolaId } });
      return await tx.escola.delete({ where: { id: escolaId } });
    });
  }
}

export const saasAdminService = new SaasAdminService();
