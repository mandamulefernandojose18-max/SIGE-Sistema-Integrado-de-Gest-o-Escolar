import prisma from '../../config/database';
import { avaliarAprovacaoPauta } from '../../utils/avaliacoes-mocambique';

export class AlunosService {
  async list(escolaId: string, filtros?: { turmaId?: string; status?: string; busca?: string; alunoId?: string }) {
    return prisma.aluno.findMany({
      where: {
        escola_id: escolaId,
        ...(filtros?.alunoId ? { id: filtros.alunoId } : {}),
        ...(filtros?.turmaId ? { turma_id: filtros.turmaId } : {}),
        ...(filtros?.status ? { status: filtros.status } : {}),
        ...(filtros?.busca
          ? {
              OR: [
                { nome: { contains: filtros.busca } },
                { apelido: { contains: filtros.busca } },
                { matricula: { contains: filtros.busca } },
                { numero_documento: { contains: filtros.busca } },
                { nuit: { contains: filtros.busca } }
              ]
            }
          : {})
      },
      include: {
        turma: true,
        _count: { select: { notas: true, pagamentos: true, certificados: true } }
      },
      orderBy: { nome: 'asc' }
    });
  }

  async getById(escolaId: string, id: string) {
    return prisma.aluno.findFirst({
      where: { id, escola_id: escolaId },
      include: {
        turma: {
          include: {
            director_turma: true,
            director_classe: true
          }
        },
        notas: {
          include: { disciplina: true },
          orderBy: [{ periodo: 'asc' }, { disciplina: { nome: 'asc' } }]
        },
        pagamentos: {
          orderBy: { data_vencimento: 'desc' }
        },
        certificados: true
      }
    });
  }

  async getNotasDoAluno(escolaId: string, alunoId: string) {
    const aluno = await prisma.aluno.findFirst({
      where: { id: alunoId, escola_id: escolaId },
      include: { turma: true }
    });

    const notas = await prisma.nota.findMany({
      where: { escola_id: escolaId, aluno_id: alunoId },
      include: { disciplina: true, turma: true },
      orderBy: [{ periodo: 'asc' }, { disciplina: { nome: 'asc' } }]
    });

    // Agrupamento por disciplina para visão consolidada do aluno
    const disciplinasMap = new Map<string, any>();
    for (const n of notas) {
      const dId = n.disciplina_id;
      if (!disciplinasMap.has(dId)) {
        disciplinasMap.set(dId, {
          id: dId,
          nome: n.disciplina.nome,
          codigo: n.disciplina.codigo,
          t1: null,
          t2: null,
          t3: null,
          t4: null,
          trabalho: null,
          avaliacaoTrimestral: null,
          mediaFinal: null,
          faltas: 0
        });
      }
      const disc = disciplinasMap.get(dId);
      if (n.periodo === '1_TRIMESTRE') {
        disc.t1 = n.media_final !== null && n.media_final !== undefined ? n.media_final : (n.teste1 ?? null);
      } else if (n.periodo === '2_TRIMESTRE') {
        disc.t2 = n.media_final !== null && n.media_final !== undefined ? n.media_final : (n.teste1 ?? null);
      } else if (n.periodo === '3_TRIMESTRE') {
        disc.t3 = n.media_final !== null && n.media_final !== undefined ? n.media_final : (n.teste1 ?? null);
      }
      disc.faltas += (n.faltas || 0);
      if (n.media_final !== null && n.media_final !== undefined) {
        disc.mediaFinal = n.media_final;
      }
    }

    const disciplinas = Array.from(disciplinasMap.values()).map(d => {
      const trimestresValidos = [d.t1, d.t2, d.t3].filter(v => v !== null && v !== undefined && !isNaN(v)) as number[];
      if (trimestresValidos.length > 0) {
        const soma = trimestresValidos.reduce((acc, curr) => acc + curr, 0);
        d.mediaFinal = Number((soma / trimestresValidos.length).toFixed(1));
      }
      return d;
    });

    const avaliacao = avaliarAprovacaoPauta(
      disciplinas.map(d => ({ disciplina: d.nome, notaFinal: d.mediaFinal || 0 })),
      aluno?.turma?.grau_ano
    );

    return {
      aluno,
      mediaGeral: avaliacao.mediaGeral,
      situacao: avaliacao.resultado.toUpperCase(),
      totalNegativas: avaliacao.totalNegativas,
      motivo: avaliacao.motivo,
      disciplinas,
      notasRaw: notas
    };
  }

  async getPagamentosDoAluno(escolaId: string, alunoId: string) {
    return prisma.pagamento.findMany({
      where: { escola_id: escolaId, aluno_id: alunoId },
      orderBy: { data_vencimento: 'desc' }
    });
  }

  async create(escolaId: string, dados: {
    nome: string;
    apelido?: string;
    matricula?: string;
    turma_id?: string;
    data_nascimento: string;
    genero: string;
    tipo_documento?: string;
    numero_documento?: string;
    nuit?: string;
    nacionalidade?: string;
    provincia?: string;
    distrito?: string;
    pai?: string;
    mae?: string;
    nome_responsavel?: string;
    contato_responsavel?: string;
    email_responsavel?: string;
    status?: string;
  }) {
    // Gerar matrícula sequencial se não informada
    const matricula = dados.matricula || `MAT-${new Date().getFullYear()}-${Math.floor(1000 + Math.random() * 9000)}`;

    return prisma.aluno.create({
      data: {
        escola_id: escolaId,
        turma_id: dados.turma_id,
        matricula,
        nome: dados.nome,
        apelido: dados.apelido,
        data_nascimento: new Date(dados.data_nascimento),
        genero: dados.genero.toUpperCase(),
        tipo_documento: dados.tipo_documento || 'BI',
        numero_documento: dados.numero_documento,
        nuit: dados.nuit,
        nacionalidade: dados.nacionalidade || 'Moçambicana',
        provincia: dados.provincia,
        distrito: dados.distrito,
        pai: dados.pai,
        mae: dados.mae,
        nome_responsavel: dados.nome_responsavel,
        contato_responsavel: dados.contato_responsavel,
        email_responsavel: dados.email_responsavel,
        status: dados.status || 'ATIVO'
      },
      include: { turma: true }
    });
  }

  async update(escolaId: string, id: string, dados: any) {
    if (dados.data_nascimento) {
      dados.data_nascimento = new Date(dados.data_nascimento);
    }
    return prisma.aluno.update({
      where: { id, escola_id: escolaId },
      data: dados,
      include: { turma: true }
    });
  }

  async delete(escolaId: string, id: string) {
    return prisma.aluno.delete({
      where: { id, escola_id: escolaId }
    });
  }

  async getStats(escolaId: string) {
    const [totalAlunos, statusGroup, generoGroup, alunos] = await Promise.all([
      prisma.aluno.count({ where: { escola_id: escolaId } }),
      prisma.aluno.groupBy({
        by: ['status'],
        where: { escola_id: escolaId },
        _count: { _all: true }
      }),
      prisma.aluno.groupBy({
        by: ['genero'],
        where: { escola_id: escolaId },
        _count: { _all: true }
      }),
      prisma.aluno.findMany({
        where: { escola_id: escolaId },
        select: { data_nascimento: true, status: true }
      })
    ]);

    // Status mapping
    let ativos = 0;
    let inativos = 0;
    let transferidos = 0;
    let evadidos = 0;

    statusGroup.forEach(item => {
      if (item.status === 'ATIVO') ativos = item._count._all;
      else if (item.status === 'INATIVO') inativos = item._count._all;
      else if (item.status === 'TRANSFERIDO') transferidos = item._count._all;
      else if (item.status === 'EVADIDO') evadidos = item._count._all;
    });

    // Distribuição por gênero
    const genero = {
      M: 0,
      F: 0
    };
    generoGroup.forEach(g => {
      const chave = g.genero.toUpperCase() === 'F' ? 'F' : 'M';
      genero[chave] = (genero[chave] || 0) + g._count._all;
    });

    // Faixas etárias (< 12, 12-15, 16-18, > 18)
    const agora = new Date();
    const faixasEtarias = {
      'Menos de 12': 0,
      '12 a 15 anos': 0,
      '16 a 18 anos': 0,
      'Mais de 18': 0
    };

    alunos.forEach(a => {
      const idade = agora.getFullYear() - new Date(a.data_nascimento).getFullYear();
      if (idade < 12) faixasEtarias['Menos de 12']++;
      else if (idade <= 15) faixasEtarias['12 a 15 anos']++;
      else if (idade <= 18) faixasEtarias['16 a 18 anos']++;
      else faixasEtarias['Mais de 18']++;
    });

    // Taxa de retenção e evasão
    const taxaRetencao = totalAlunos > 0 ? Number(((ativos / totalAlunos) * 100).toFixed(1)) : 100;
    const taxaEvasao = totalAlunos > 0 ? Number(((evadidos / totalAlunos) * 100).toFixed(1)) : 0;

    return {
      totalGeral: totalAlunos,
      ativos,
      inativos,
      transferidos,
      evadidos,
      taxaRetencao,
      taxaEvasao,
      genero,
      faixasEtarias
    };
  }
}

export const alunosService = new AlunosService();
