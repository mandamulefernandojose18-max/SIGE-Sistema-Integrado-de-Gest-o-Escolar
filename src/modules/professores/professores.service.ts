import prisma from '../../config/database';
import bcrypt from 'bcryptjs';
import { ExportExcelService } from '../../services/export-excel.service';

export class ProfessoresService {
  async list(escolaId: string, filtros?: { especialidade?: string; busca?: string; professorId?: string }) {
    return prisma.professor.findMany({
      where: {
        escola_id: escolaId,
        ...(filtros?.professorId ? { id: filtros.professorId } : {}),
        ...(filtros?.especialidade ? { especialidade: filtros.especialidade } : {}),
        ...(filtros?.busca
          ? {
              OR: [
                { nome: { contains: filtros.busca } },
                { apelido: { contains: filtros.busca } },
                { email: { contains: filtros.busca } },
                { especialidade: { contains: filtros.busca } },
                { numero_documento: { contains: filtros.busca } },
                { nuit: { contains: filtros.busca } }
              ]
            }
          : {})
      },
      include: {
        alocacoes: {
          include: {
            turma: true,
            disciplina: true
          }
        },
        _count: { select: { alocacoes: true } }
      },
      orderBy: { nome: 'asc' }
    });
  }

  async getById(escolaId: string, id: string) {
    return prisma.professor.findFirst({
      where: { id, escola_id: escolaId },
      include: {
        alocacoes: {
          include: {
            turma: true,
            disciplina: true
          }
        }
      }
    });
  }

  async create(escolaId: string, dados: {
    nome: string;
    apelido?: string | null;
    genero?: string | null;
    tipo_documento?: string | null;
    numero_documento?: string | null;
    nuit?: string | null;
    nacionalidade?: string | null;
    provincia?: string | null;
    distrito?: string | null;
    carreira?: string | null;
    email: string;
    telefone?: string | null;
    especialidade: string;
    carga_horaria_semanal?: number;
    criarUsuario?: boolean;
    senha?: string;
  }) {
    let usuarioId: string | undefined;

    if (dados.criarUsuario) {
      const senhaHash = await bcrypt.hash(dados.senha || 'professor123', 10);
      const usuario = await prisma.usuario.create({
        data: {
          escola_id: escolaId,
          nome: `${dados.nome} ${dados.apelido || ''}`.trim(),
          email: dados.email,
          senha_hash: senhaHash,
          role: 'PROFESSOR',
          telefone: dados.telefone,
          ativo: true
        }
      });
      usuarioId = usuario.id;
    }

    const professor = await prisma.professor.create({
      data: {
        escola_id: escolaId,
        nome: dados.nome,
        apelido: dados.apelido,
        genero: dados.genero || 'M',
        tipo_documento: dados.tipo_documento || 'BI',
        numero_documento: dados.numero_documento,
        nuit: dados.nuit,
        nacionalidade: dados.nacionalidade || 'Moçambicana',
        provincia: dados.provincia,
        distrito: dados.distrito,
        carreira: dados.carreira || 'DN1',
        email: dados.email,
        telefone: dados.telefone,
        especialidade: dados.especialidade,
        carga_horaria_semanal: dados.carga_horaria_semanal || 20,
        ativo: true
      }
    });

    if (usuarioId) {
      await prisma.usuario.update({
        where: { id: usuarioId },
        data: { professor_id: professor.id }
      });
    }

    return professor;
  }

  async update(escolaId: string, id: string, dados: any) {
    return prisma.professor.update({
      where: { id, escola_id: escolaId },
      data: dados
    });
  }

  async delete(escolaId: string, id: string) {
    return prisma.professor.delete({
      where: { id, escola_id: escolaId }
    });
  }

  async alocar(escolaId: string, dados: { professor_id: string; disciplina_id: string; turma_id: string }) {
    // Verificar se já existe alocação idêntica
    const existente = await prisma.professorDisciplinaTurma.findFirst({
      where: {
        escola_id: escolaId,
        professor_id: dados.professor_id,
        disciplina_id: dados.disciplina_id,
        turma_id: dados.turma_id
      }
    });

    if (existente) {
      throw new Error('Esta alocação de professor, disciplina e turma já existe.');
    }

    return prisma.professorDisciplinaTurma.create({
      data: {
        escola_id: escolaId,
        professor_id: dados.professor_id,
        disciplina_id: dados.disciplina_id,
        turma_id: dados.turma_id
      },
      include: {
        professor: true,
        disciplina: true,
        turma: true
      }
    });
  }

  async desalocar(escolaId: string, alocacaoId: string) {
    return prisma.professorDisciplinaTurma.delete({
      where: { id: alocacaoId, escola_id: escolaId }
    });
  }

  async getStats(escolaId: string) {
    const [totalProfessores, totalAlunosAtivos, alocacoes, professores] = await Promise.all([
      prisma.professor.count({ where: { escola_id: escolaId, ativo: true } }),
      prisma.aluno.count({ where: { escola_id: escolaId, status: 'ATIVO' } }),
      prisma.professorDisciplinaTurma.findMany({
        where: { escola_id: escolaId },
        include: { disciplina: true }
      }),
      prisma.professor.findMany({
        where: { escola_id: escolaId, ativo: true },
        include: {
          alocacoes: {
            include: { turma: true, disciplina: true }
          }
        }
      })
    ]);

    // Proporção Aluno / Professor
    const proporcaoAlunoProfessor = totalProfessores > 0 ? Number((totalAlunosAtivos / totalProfessores).toFixed(1)) : 0;

    // Estimativa de aulas lecionadas no mês
    // Média de 4.2 semanas/mês * carga horária ou número de alocações
    let totalCargaSemanal = 0;
    professores.forEach(p => {
      totalCargaSemanal += p.carga_horaria_semanal;
    });
    const totalAulasMes = Math.round(totalCargaSemanal * 4.2);

    // Especialidades mais comuns
    const especialidades: Record<string, number> = {};
    professores.forEach(p => {
      especialidades[p.especialidade] = (especialidades[p.especialidade] || 0) + 1;
    });

    return {
      totalProfessores,
      totalAlunosAtivos,
      proporcaoAlunoProfessor,
      totalAulasMes,
      totalAlocacoes: alocacoes.length,
      especialidades
    };
  }

  async getMinhasAlocacoes(escolaId: string, professorId: string) {
    return prisma.professorDisciplinaTurma.findMany({
      where: {
        escola_id: escolaId,
        professor_id: professorId
      },
      include: {
        turma: true,
        disciplina: true,
        professor: true
      }
    });
  }

  async getCadernetaData(escolaId: string, alocacaoId: string, trimestreFiltro?: number) {
    const alocacao = await prisma.professorDisciplinaTurma.findFirst({
      where: { id: alocacaoId, escola_id: escolaId },
      include: {
        professor: true,
        disciplina: true,
        turma: {
          include: {
            alunos: {
              where: { status: 'ATIVO' },
              orderBy: { nome: 'asc' }
            }
          }
        },
        escola: true
      }
    });

    if (!alocacao) throw new Error('Alocação do professor não encontrada');

    const trimestre = trimestreFiltro || (typeof alocacao.escola.trimestre_ativo === 'string' ? parseInt(alocacao.escola.trimestre_ativo) || 1 : 1);
    const periodoFiltro = `${trimestre}_TRIMESTRE`;

    // Buscar notas dos alunos para esta turma e disciplina no trimestre
    const notas = await prisma.nota.findMany({
      where: {
        escola_id: escolaId,
        turma_id: alocacao.turma_id,
        disciplina_id: alocacao.disciplina_id,
        periodo: periodoFiltro
      }
    });

    const notasMap = new Map(notas.map(n => [n.aluno_id, n]));

    const alunosData = alocacao.turma.alunos.map((aluno, index) => {
      const n = notasMap.get(aluno.id);
      return {
        numero: index + 1,
        alunoId: aluno.id,
        matricula: aluno.matricula,
        nome: `${aluno.nome} ${aluno.apelido || ''}`.trim(),
        genero: aluno.genero,
        teste1: n?.teste1 ?? 0,
        teste2: n?.teste2 ?? 0,
        teste3: n?.teste3 ?? undefined,
        teste4: n?.teste4 ?? undefined,
        trabalho: n?.trabalho ?? 0,
        at: n?.avaliacao_trimestral ?? 0,
        mediaFinal: n?.media_final ?? 0,
        faltas: n?.faltas ?? 0,
        anotacao: n?.anotacao ?? undefined,
        comportamento: n?.comportamento ?? 'S',
        resultado: n?.resultado ?? (n?.media_final && n.media_final >= 9.5 ? 'Aprovado' : 'Reprovado')
      };
    });

    return {
      escola: alocacao.escola,
      professor: alocacao.professor,
      disciplina: alocacao.disciplina,
      turma: alocacao.turma,
      trimestre,
      alunos: alunosData
    };
  }

  async exportarCadernetaXlsx(escolaId: string, alocacaoId: string, trimestreFiltro?: number): Promise<{ buffer: Buffer; filename: string }> {
    const dados = await this.getCadernetaData(escolaId, alocacaoId, trimestreFiltro);
    const buffer = ExportExcelService.gerarCadernetaProfessorXlsx({
      escola: { nome: dados.escola.nome },
      professor: { nome: dados.professor.nome, especialidade: dados.professor.especialidade },
      disciplina: { nome: dados.disciplina.nome, codigo: dados.disciplina.codigo },
      turma: { nome: dados.turma.nome, grau_ano: dados.turma.grau_ano, ano_letivo: dados.turma.ano_letivo },
      periodo: `${dados.trimestre}º Trimestre`,
      alunos: dados.alunos
    });

    const filename = `Caderneta_${dados.professor.nome.replace(/\s+/g, '_')}_${dados.disciplina.codigo}_${dados.turma.nome.replace(/\s+/g, '_')}_${dados.turma.ano_letivo}.xlsx`;
    return { buffer, filename };
  }
}

export const professoresService = new ProfessoresService();
