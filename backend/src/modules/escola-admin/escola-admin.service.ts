import prisma from '../../config/database';

export class EscolaAdminService {
  async getEscolaInfo(escolaId: string) {
    return prisma.escola.findUnique({
      where: { id: escolaId },
      include: {
        plano: true,
        assinaturas: {
          orderBy: { data_fim: 'desc' },
          take: 1
        },
        _count: {
          select: {
            turmas: true,
            alunos: true,
            professores: true,
            disciplinas: true
          }
        }
      }
    });
  }

  async updateEscolaInfo(escolaId: string, dados: {
    nome?: string;
    telefone?: string;
    email?: string;
    endereco?: string;
    logo_url?: string;
    ano_letivo_ativo?: string;
    provincia?: string;
    distrito?: string;
    director_nome?: string;
    director_carreira?: string;
    dap_nome?: string;
    chefe_secretaria_nome?: string;
    usar_emblema_nacional?: boolean;
    trimestre_ativo?: string;
  }) {
    return prisma.escola.update({
      where: { id: escolaId },
      data: dados
    });
  }

  // Gestão de Turmas
  async listTurmas(escolaId: string, anoLetivo?: string) {
    return prisma.turma.findMany({
      where: {
        escola_id: escolaId,
        ...(anoLetivo ? { ano_letivo: anoLetivo } : {})
      },
      include: {
        director_turma: {
          select: { id: true, nome: true, apelido: true, carreira: true }
        },
        director_classe: {
          select: { id: true, nome: true, apelido: true, carreira: true }
        },
        _count: { select: { alunos: true, alocacoes: true, pautas: true } }
      },
      orderBy: { nome: 'asc' }
    });
  }

  async createTurma(escolaId: string, dados: {
    nome: string;
    grau_ano: string;
    turno: string;
    sala?: string;
    ano_letivo?: string;
    director_turma_id?: string | null;
    director_classe_id?: string | null;
  }) {
    return prisma.turma.create({
      data: {
        escola_id: escolaId,
        nome: dados.nome,
        grau_ano: dados.grau_ano,
        turno: dados.turno,
        sala: dados.sala,
        ano_letivo: dados.ano_letivo || '2026',
        director_turma_id: dados.director_turma_id,
        director_classe_id: dados.director_classe_id
      },
      include: {
        director_turma: true,
        director_classe: true
      }
    });
  }

  async updateTurma(escolaId: string, turmaId: string, dados: {
    nome?: string;
    grau_ano?: string;
    turno?: string;
    sala?: string;
    ano_letivo?: string;
    director_turma_id?: string | null;
    director_classe_id?: string | null;
  }) {
    return prisma.turma.update({
      where: { id: turmaId, escola_id: escolaId },
      data: dados,
      include: {
        director_turma: true,
        director_classe: true
      }
    });
  }

  async deleteTurma(escolaId: string, turmaId: string) {
    // Desassociar alunos da turma com segurança
    await prisma.aluno.updateMany({
      where: { escola_id: escolaId, turma_id: turmaId },
      data: { turma_id: null }
    });

    // Remover alocações e notas associadas à turma
    await prisma.professorDisciplinaTurma.deleteMany({
      where: { escola_id: escolaId, turma_id: turmaId }
    });
    await prisma.nota.deleteMany({
      where: { escola_id: escolaId, turma_id: turmaId }
    });
    await prisma.pauta.deleteMany({
      where: { escola_id: escolaId, turma_id: turmaId }
    });

    return prisma.turma.delete({
      where: { id: turmaId, escola_id: escolaId }
    });
  }

  async getTurmasStats(escolaId: string) {
    const [totalTurmas, turmas, alunosPorTurma] = await Promise.all([
      prisma.turma.count({ where: { escola_id: escolaId } }),
      prisma.turma.findMany({
        where: { escola_id: escolaId },
        include: { _count: { select: { alunos: true } } }
      }),
      prisma.aluno.groupBy({
        by: ['turma_id'],
        where: { escola_id: escolaId, status: 'ATIVO' },
        _count: { _all: true }
      })
    ]);

    const turnosCount: Record<string, number> = { MANHA: 0, TARDE: 0, NOITE: 0 };
    turmas.forEach(t => {
      const turno = t.turno.toUpperCase();
      turnosCount[turno] = (turnosCount[turno] || 0) + 1;
    });

    const ocupacaoTurmas = turmas.map(t => ({
      turmaId: t.id,
      nome: t.nome,
      grau_ano: t.grau_ano,
      totalAlunos: t._count.alunos
    }));

    return {
      totalTurmas,
      turnos: turnosCount,
      ocupacao: ocupacaoTurmas
    };
  }

  async listAdministrativos(escolaId: string) {
    return prisma.usuario.findMany({
      where: {
        escola_id: escolaId,
        role: { in: ['DIRECTOR_ESCOLA', 'DAP', 'CHEFE_SECRETARIA', 'FINANCEIRO', 'ADMIN_ESCOLA'] }
      },
      select: {
        id: true,
        nome: true,
        email: true,
        role: true,
        ativo: true,
        createdAt: true,
        updatedAt: true
      },
      orderBy: { nome: 'asc' }
    });
  }

  async createAdministrativo(escolaId: string, dados: {
    nome: string;
    email: string;
    senha_hash: string;
    role: 'DIRECTOR_ESCOLA' | 'DAP' | 'CHEFE_SECRETARIA' | 'FINANCEIRO' | 'ADMIN_ESCOLA';
  }) {
    return prisma.usuario.create({
      data: {
        escola_id: escolaId,
        nome: dados.nome,
        email: dados.email,
        senha_hash: dados.senha_hash,
        role: dados.role,
        ativo: true
      }
    });
  }

  async toggleNotas(escolaId: string, permitir?: boolean) {
    const escola = await prisma.escola.findUnique({ where: { id: escolaId } });
    if (!escola) throw new Error('Escola não encontrada');
    const novoValor = permitir !== undefined ? permitir : !escola.permitir_visualizacao_notas;
    const updated = await prisma.escola.update({
      where: { id: escolaId },
      data: { permitir_visualizacao_notas: novoValor }
    });
    return { permitir_visualizacao_notas: updated.permitir_visualizacao_notas };
  }

  async listUsuariosCredenciais(escolaId: string) {
    const usuarios = await prisma.usuario.findMany({
      where: { escola_id: escolaId },
      select: {
        id: true,
        nome: true,
        email: true,
        role: true,
        ativo: true,
        telefone: true,
        createdAt: true,
        updatedAt: true,
        logs_acesso: {
          orderBy: { createdAt: 'desc' },
          take: 1,
          select: { createdAt: true }
        }
      },
      orderBy: [{ role: 'asc' }, { nome: 'asc' }]
    });

    return usuarios.map(u => ({
      id: u.id,
      nome: u.nome,
      email: u.email,
      role: u.role,
      ativo: u.ativo,
      telefone: u.telefone,
      createdAt: u.createdAt,
      ultimo_acesso: u.logs_acesso[0]?.createdAt || u.updatedAt
    }));
  }
}

export const escolaAdminService = new EscolaAdminService();
