import request from 'supertest';
import app from '../src/app';
import prisma from '../src/config/database';

describe('2. Módulo Multi-Tenant e Bloqueio Automático por Expiração (HTTP 402)', () => {
  let tokenEscolaAtiva: string;
  let tokenEscolaExpirada: string;

  beforeAll(async () => {
    // Garante que a escola expirada (Instituto Educacional Progresso) está com status EXPIRADA
    await prisma.escola.updateMany({
      where: { nif_cnpj: '5009876543' },
      data: { status: 'EXPIRADA' }
    });

    // Login na Escola Ativa (Colégio São Francisco)
    const resAtiva = await request(app)
      .post('/api/v1/auth/login')
      .send({
        email: 'admin.escola@escola.edu.mz',
        senha: 'escola123'
      });
    tokenEscolaAtiva = resAtiva.body.data.tokens.accessToken;

    // Login na Escola Expirada (Instituto Educacional Progresso)
    const resExpirada = await request(app)
      .post('/api/v1/auth/login')
      .send({
        email: 'admin.progresso@sige.com',
        senha: 'escola123'
      });
    tokenEscolaExpirada = resExpirada.body.data.tokens.accessToken;
  });

  it('Deve permitir acesso normal (HTTP 200) para usuário de escola com assinatura ATIVA', async () => {
    const res = await request(app)
      .get('/api/v1/alunos')
      .set('Authorization', `Bearer ${tokenEscolaAtiva}`);

    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(Array.isArray(res.body.data)).toBe(true);
  });

  it('Deve BLOQUEAR com HTTP 402 (Payment Required) requisição de escola EXPIRADA com a mensagem exata requerida', async () => {
    const res = await request(app)
      .get('/api/v1/alunos')
      .set('Authorization', `Bearer ${tokenEscolaExpirada}`);

    expect(res.status).toBe(402);
    expect(res.body.success).toBe(false);
    expect(res.body.error).toBe('PAYMENT_REQUIRED');
    expect(res.body.message).toBe(
      'Assinatura expirada. Entre em contato com a administração do sistema para renovação.'
    );
    expect(res.body.escola.status).toBe('EXPIRADA');
  });

  it('Deve bloquear outras rotas escolares (como /professores) para o tenant expirado com HTTP 402', async () => {
    const res = await request(app)
      .get('/api/v1/professores')
      .set('Authorization', `Bearer ${tokenEscolaExpirada}`);

    expect(res.status).toBe(402);
    expect(res.body.error).toBe('PAYMENT_REQUIRED');
  });

  it('Deve permitir que a rota pública de verificação de certificado (/api/v1/certificados/verificar/:codigo) funcione sem bloqueio 402', async () => {
    const res = await request(app)
      .get('/api/v1/certificados/verificar/550e8400-e29b-41d4-a716-446655440000');

    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.autentico).toBe(true);
  });
});
