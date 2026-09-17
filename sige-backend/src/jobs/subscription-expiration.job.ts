import cron from 'node-cron';
import prisma from '../config/database';
import { env } from '../config/env';

/**
 * Função executada para verificar e expirar assinaturas vencidas
 */
export async function runSubscriptionExpirationCheck(): Promise<{
  processadas: number;
  expiradas: number;
  detalhes: Array<{ escolaId: string; nome: string; dataFim: Date }>;
}> {
  const agora = new Date();
  console.log(`[CRON JOB] Iniciando verificação diária de expiração de assinaturas em: ${agora.toISOString()}`);

  // Buscar escolas ativas ou pendentes com assinaturas vencidas
  const escolasComAssinaturaVencida = await prisma.escola.findMany({
    where: {
      status: { in: ['ATIVA', 'PENDENTE'] },
      assinaturas: {
        some: {
          data_fim: { lt: agora },
          status: { in: ['ATIVA', 'PENDENTE'] }
        }
      }
    },
    include: {
      assinaturas: {
        orderBy: { data_fim: 'desc' },
        take: 1
      }
    }
  });

  const expiradasDetalhes: Array<{ escolaId: string; nome: string; dataFim: Date }> = [];

  for (const escola of escolasComAssinaturaVencida) {
    const ultimaAssinatura = escola.assinaturas[0];

    // Se a assinatura mais recente estiver vencida, atualiza para EXPIRADA
    if (ultimaAssinatura && new Date(ultimaAssinatura.data_fim) < agora) {
      await prisma.$transaction([
        prisma.escola.update({
          where: { id: escola.id },
          data: { status: 'EXPIRADA' }
        }),
        prisma.assinaturaEscola.updateMany({
          where: {
            escola_id: escola.id,
            status: { in: ['ATIVA', 'PENDENTE'] },
            data_fim: { lt: agora }
          },
          data: { status: 'EXPIRADA' }
        }),
        prisma.logAcesso.create({
          data: {
            escola_id: escola.id,
            tipo: 'ACESSO_BLOQUEADO_EXPIRADO',
            user_agent: 'SIGE_CRON_JOB_AUTOMATION',
            ip: '127.0.0.1'
          }
        })
      ]);

      expiradasDetalhes.push({
        escolaId: escola.id,
        nome: escola.nome,
        dataFim: ultimaAssinatura.data_fim
      });

      console.warn(`[CRON JOB] Escola [${escola.nome}] (${escola.id}) teve sua assinatura alterada para EXPIRADA.`);
    }
  }

  console.log(`[CRON JOB] Verificação concluída. Total verificadas: ${escolasComAssinaturaVencida.length}, Total expiradas hoje: ${expiradasDetalhes.length}`);

  return {
    processadas: escolasComAssinaturaVencida.length,
    expiradas: expiradasDetalhes.length,
    detalhes: expiradasDetalhes
  };
}

/**
 * Inicializa o cron job programado
 */
export function startSubscriptionExpirationCron() {
  const schedule = env.CRON_SCHEDULE;
  console.log(`[CRON] Agendador de expiração de assinaturas configurado com padrão: "${schedule}"`);

  cron.schedule(schedule, async () => {
    try {
      await runSubscriptionExpirationCheck();
    } catch (error) {
      console.error('[CRON ERROR] Erro na execução do job de expiração:', error);
    }
  });
}
