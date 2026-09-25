import app from './app';
import { env } from './config/env';
import prisma from './config/database';
import { startSubscriptionExpirationCron } from './jobs/subscription-expiration.job';

const server = app.listen(env.PORT, async () => {
  console.log('================================================================');
  console.log(`🚀 SIGE — Sistema Integrado de Gestão Escolar (SaaS Multi-Tenant)`);
  console.log(`📡 Servidor ativo em: ${env.APP_URL}`);
  console.log(`🌍 Ambiente: ${env.NODE_ENV}`);
  console.log(`⏰ Cron Job de Expiração configurado para: "${env.CRON_SCHEDULE}"`);
  console.log('================================================================');

  try {
    await prisma.$connect();
    console.log('✅ Conexão com o banco de dados estabelecida com sucesso!');
  } catch (error) {
    console.error('❌ Falha ao conectar ao banco de dados:', error);
  }

  // Inicializar agendador diário de verificação de expiração de assinaturas
  startSubscriptionExpirationCron();
});

// Tratamento de finalização graciosa
process.on('SIGTERM', async () => {
  console.log('Recebido SIGTERM. Encerrando servidor graciosamente...');
  server.close(async () => {
    await prisma.$disconnect();
    process.exit(0);
  });
});

process.on('SIGINT', async () => {
  console.log('Recebido SIGINT. Encerrando servidor graciosamente...');
  server.close(async () => {
    await prisma.$disconnect();
    process.exit(0);
  });
});
