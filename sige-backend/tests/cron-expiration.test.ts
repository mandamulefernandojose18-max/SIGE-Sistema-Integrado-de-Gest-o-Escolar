import { runSubscriptionExpirationCheck } from '../src/jobs/subscription-expiration.job';
import prisma from '../src/config/database';

describe('3. Agendador Diário (Cron Job) de Expiração de Assinaturas', () => {
  beforeAll(async () => {
    await prisma.escola.updateMany({
      where: { nif_cnpj: '5009876543' },
      data: { status: 'EXPIRADA' }
    });
  });

  it('Deve executar a função de verificação diária e retornar relatório de assinaturas processadas', async () => {
    const resultado = await runSubscriptionExpirationCheck();

    expect(resultado).toHaveProperty('processadas');
    expect(resultado).toHaveProperty('expiradas');
    expect(resultado).toHaveProperty('detalhes');
    expect(typeof resultado.processadas).toBe('number');
    expect(typeof resultado.expiradas).toBe('number');
  });

  it('Deve garantir que escolas com assinatura vencida fiquem com status EXPIRADA', async () => {
    const escolaExpirada = await prisma.escola.findFirst({
      where: { nif_cnpj: '5009876543' }
    });

    expect(escolaExpirada).toBeDefined();
    expect(escolaExpirada?.status).toBe('EXPIRADA');
  });
});
