import request from 'supertest';
import app from '../src/app';

describe('1. Módulo de Autenticação e RBAC (JWT)', () => {
  it('Deve rejeitar login com credenciais incorretas (HTTP 401)', async () => {
    const res = await request(app)
      .post('/api/v1/auth/login')
      .send({
        email: 'naoexiste@sige.com',
        senha: 'senhaerradaxpto'
      });

    expect(res.status).toBe(401);
    expect(res.body.success).toBe(false);
  });

  it('Deve efetuar login com sucesso para o SuperAdmin e emitir JWT + Refresh Token', async () => {
    const res = await request(app)
      .post('/api/v1/auth/login')
      .send({
        email: 'admin.master@sige.com',
        senha: 'admin123'
      });

    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.tokens).toHaveProperty('accessToken');
    expect(res.body.data.tokens).toHaveProperty('refreshToken');
    expect(res.body.data.user.role).toBe('SUPERADMIN');
  });

  it('Deve validar a rota protegida /api/v1/auth/me com token Bearer válido', async () => {
    // 1. Obter token
    const loginRes = await request(app)
      .post('/api/v1/auth/login')
      .send({
        email: 'admin.master@sige.com',
        senha: 'admin123'
      });

    const token = loginRes.body.data.tokens.accessToken;

    // 2. Chamar rota protegida
    const meRes = await request(app)
      .get('/api/v1/auth/me')
      .set('Authorization', `Bearer ${token}`);

    expect(meRes.status).toBe(200);
    expect(meRes.body.data.user.email).toBe('admin.master@sige.com');
  });

  it('Deve efetuar login com sucesso para o Engenheiro SuperAdmin (mandamulefj.@sige.com) com senha Deusamo8', async () => {
    const res = await request(app)
      .post('/api/v1/auth/login')
      .send({
        email: 'mandamulefj.@sige.com',
        senha: 'Deusamo8'
      });

    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.tokens).toHaveProperty('accessToken');
    expect(res.body.data.user.role).toBe('SUPERADMIN');
    expect(res.body.data.user.nome).toContain('Mandamule');
  });

  it('Deve efetuar login com sucesso para utilizadores nominais com senhas individuais', async () => {
    // 1. Director António Costa com costa123
    const dirRes = await request(app)
      .post('/api/v1/auth/login')
      .send({
        email: 'antonio.costa@escola.edu.mz',
        senha: 'costa123'
      });
    expect(dirRes.status).toBe(200);
    expect(dirRes.body.data.user.role).toBe('DIRECTOR_ESCOLA');

    // 2. Professor Manuel Silva com silva123
    const profRes = await request(app)
      .post('/api/v1/auth/login')
      .send({
        email: 'manuel.silva@escola.edu.mz',
        senha: 'silva123'
      });
    expect(profRes.status).toBe(200);
    expect(profRes.body.data.user.role).toBe('PROFESSOR');

    // 3. Aluno Carlos Mandamule com mandamule123
    const alunoRes = await request(app)
      .post('/api/v1/auth/login')
      .send({
        email: 'carlos.mandamule@escola.edu.mz',
        senha: 'mandamule123'
      });
    expect(alunoRes.status).toBe(200);
    expect(alunoRes.body.data.user.role).toBe('ALUNO');
  });

  it('Deve rejeitar acesso a rota protegida sem token (HTTP 401)', async () => {
    const res = await request(app).get('/api/v1/auth/me');
    expect(res.status).toBe(401);
    expect(res.body.error).toBe('UNAUTHORIZED');
  });
});
