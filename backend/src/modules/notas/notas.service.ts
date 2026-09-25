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

  async getPrazosTrimestrais(escolaId: string) {
    const doc = await prisma.documentoSalvo.findFirst({
      where: { escola_id: escolaId, tipo_documento: 'CONFIG_PRAZOS_NOTAS' }
    });
    let data: any = null;
    if (doc && doc.dados_json) {
      try {
        data = JSON.parse(doc.dados_json);
      } catch (_) {}
    }

    const t1_ini = data?.data_inicio_t1 || data?.t1_inicio || '2026-02-01';
    const t1_fim = data?.data_fim_t1 || data?.t1_fim || '2026-05-15';
    const t2_ini = data?.data_inicio_t2 || data?.t2_inicio || '2026-06-01';
    const t2_fim = data?.data_fim_t2 || data?.t2_fim || '2026-08-31';
    const t3_ini = data?.data_inicio_t3 || data?.t3_inicio || '2026-09-01';
    const t3_fim = data?.data_fim_t3 || data?.t3_fim || '2026-11-30';

    return {
      t1_inicio: t1_ini,
      t1_fim: t1_fim,
      t2_inicio: t2_ini,
      t2_fim: t2_fim,
      t3_inicio: t3_ini,
      t3_fim: t3_fim,
      data_inicio_t1: t1_ini,
      data_fim_t1: t1_fim,
      data_inicio_t2: t2_ini,
      data_fim_t2: t2_fim,
      data_inicio_t3: t3_ini,
      data_fim_t3: t3_fim
    };
  }

  async salvarPrazosTrimestrais(escolaId: string, dados: any) {
    const docExistente = await prisma.documentoSalvo.findFirst({
      where: { escola_id: escolaId, tipo_documento: 'CONFIG_PRAZOS_NOTAS' }
    });

    const payload = {
      data_inicio_t1: dados.data_inicio_t1 || dados.t1_inicio,
      data_fim_t1: dados.data_fim_t1 || dados.t1_fim,
      data_inicio_t2: dados.data_inicio_t2 || dados.t2_inicio,
      data_fim_t2: dados.data_fim_t2 || dados.t2_fim,
      data_inicio_t3: dados.data_inicio_t3 || dados.t3_inicio,
      data_fim_t3: dados.data_fim_t3 || dados.t3_fim,
      t1_inicio: dados.data_inicio_t1 || dados.t1_inicio,
      t1_fim: dados.data_fim_t1 || dados.t1_fim,
      t2_inicio: dados.data_inicio_t2 || dados.t2_inicio,
      t2_fim: dados.data_fim_t2 || dados.t2_fim,
      t3_inicio: dados.data_inicio_t3 || dados.t3_inicio,
      t3_fim: dados.data_fim_t3 || dados.t3_fim
    };
    if (docExistente) {
      return prisma.documentoSalvo.update({
        where: { id: docExistente.id },
        data: {
          dados_json: JSON.stringify(payload),
          criado_em: new Date()
        }
      });
    } else {
      return prisma.documentoSalvo.create({
        data: {
          escola_id: escolaId,
          tipo_documento: 'CONFIG_PRAZOS_NOTAS',
          titulo: 'Calendário e Prazos de Lançamento de Notas',
          ano_letivo: '2026',
          dados_json: JSON.stringify(payload)
        }
      });
    }
  }

  async listarAutorizacoesDesbloqueio(escolaId: string) {
    const perms = await prisma.permissaoEdicaoNotas.findMany({
      where: { escola_id: escolaId, ativa: true },
      include: {
        professor: true
      },
      orderBy: { createdAt: 'desc' }
    });

    const turmas = await prisma.turma.findMany({ where: { escola_id: escolaId } });
    const turmasMap = new Map(turmas.map(t => [t.id, t.nome]));

    return perms.map(p => ({
      ...p,
      turma_nome: turmasMap.get(p.turma_id) || p.turma_id
    }));
  }

  async revogarAutorizacaoDesbloqueio(escolaId: string, permissaoId: string) {
    return prisma.permissaoEdicaoNotas.update({
      where: { id: permissaoId },
      data: { ativa: false }
    });
  }

  async validarPermissaoTrimestre(escolaId: string, professorId: string, turmaId: string, disciplinaId: string, periodo: string) {
    const escola = await prisma.escola.findUnique({ where: { id: escolaId } });
    if (!escola) throw new Error('Escola não encontrada');

    const prazos = await this.getPrazosTrimestrais(escolaId);
    const hoje = new Date();
    hoje.setHours(0, 0, 0, 0);

    const match = periodo.match(/(\d)/);
    const trimestreNum = match ? parseInt(match[1], 10) : 1;

    const dataInicioStr = prazos[`t${trimestreNum}_inicio`];
    const dataFimStr = prazos[`t${trimestreNum}_fim`];

    let foraDoPrazo = false;
    let motivoBloqueio = '';

    if (dataInicioStr && dataFimStr) {
      const dtInicio = new Date(dataInicioStr);
      dtInicio.setHours(0, 0, 0, 0);
      const dtFim = new Date(dataFimStr);
      dtFim.setHours(23, 59, 59, 999);

      if (hoje < dtInicio) {
        foraDoPrazo = true;
        motivoBloqueio = `O período oficial de lançamento de notas para o ${trimestreNum}º Trimestre só abre em ${new Date(dataInicioStr).toLocaleDateString('pt-PT')}.`;
      } else if (hoje > dtFim) {
        foraDoPrazo = true;
        motivoBloqueio = `O prazo oficial de lançamento para o ${trimestreNum}º Trimestre expirou em ${new Date(dataFimStr).toLocaleDateString('pt-PT')}. Lançamento bloqueado por atraso.`;
      }
    }

    const trimestreAtivo = typeof escola.trimestre_ativo === 'string'
      ? (parseInt(escola.trimestre_ativo.replace(/\D/g, '')) || 1)
      : (escola.trimestre_ativo || 1);

    if (trimestreNum < trimestreAtivo) {
      foraDoPrazo = true;
      if (!motivoBloqueio) {
        motivoBloqueio = `Edição de notas bloqueada para o ${trimestreNum}º Trimestre (Trimestre activo actual: ${trimestreAtivo}º).`;
      }
    }

    if (foraDoPrazo) {
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
        throw new Error(`${motivoBloqueio} Solicite autorização de desbloqueio / prorrogação de prazo à Direcção Pedagógica (DAP).`);
      }

      // Validar prazo de validade da autorização excepcional em horas
      const matchHoras = permissao.motivo?.match(/\[(\d+)\s*h\]/);
      const horasValidade = matchHoras ? parseInt(matchHoras[1], 10) : 48;
      const dataExpiracao = new Date(permissao.createdAt.getTime() + horasValidade * 3600 * 1000);

      if (new Date() > dataExpiracao) {
        await prisma.permissaoEdicaoNotas.update({
          where: { id: permissao.id },
          data: { ativa: false }
        });
        throw new Error(`A autorização de desbloqueio para o ${trimestreNum}º Trimestre expirou em ${dataExpiracao.toLocaleString('pt-PT')}. Solicite nova prorrogação à Direcção.`);
      }
    }
  }

  async autorizarDesbloqueio(escolaId: string, dados: {
    professor_id?: string | null;
    turma_id: string;
    disciplina_id?: string | null;
    periodo: string;
    duracao_horas?: number;
    autorizado_por: string;
    motivo?: string;
  }) {
    const horas = dados.duracao_horas || 48;
    const motivoCompleto = `${dados.motivo || 'Autorizado pela Direcção'} [${horas}h]`;

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
            motivo: motivoCompleto,
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
            motivo: motivoCompleto,
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
