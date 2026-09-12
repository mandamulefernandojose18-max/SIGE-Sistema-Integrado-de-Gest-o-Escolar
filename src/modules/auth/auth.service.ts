import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import crypto from 'crypto';
import prisma from '../../config/database';
import { env } from '../../config/env';

export class AuthService {
  async login(email: string, senha: string, ip: string, userAgent: string) {
    const usuario = await prisma.usuario.findUnique({
      where: { email },
      include: {
        escola: {
          include: {
            assinaturas: {
              orderBy: { data_fim: 'desc' },
              take: 1
            }
          }
        }
      }
    });

    if (!usuario || !usuario.ativo) {
      if (usuario) {
        await prisma.logAcesso.create({
          data: {
            escola_id: usuario.escola_id,
            usuario_id: usuario.id,
            ip,
            user_agent: userAgent,
            tipo: 'LOGIN_FALHA'
          }
        });
      }
      throw new Error('Credenciais inválidas ou usuário inativo');
    }

    const senhaValida = await bcrypt.compare(senha, usuario.senha_hash);
    if (!senhaValida) {
      await prisma.logAcesso.create({
        data: {
          escola_id: usuario.escola_id,
          usuario_id: usuario.id,
          ip,
          user_agent: userAgent,
          tipo: 'LOGIN_FALHA'
        }
      });
      throw new Error('Credenciais inválidas ou usuário inativo');
    }

    // Criar Access Token
    const accessToken = jwt.sign(
      {
        id: usuario.id,
        nome: usuario.nome,
        email: usuario.email,
        role: usuario.role,
        escola_id: usuario.escola_id
      },
      env.JWT_SECRET,
      { expiresIn: env.JWT_EXPIRES_IN as any }
    );

    // Criar Refresh Token
    const refreshTokenString = jwt.sign(
      { id: usuario.id, email: usuario.email, jti: crypto.randomUUID() },
      env.JWT_REFRESH_SECRET,
      { expiresIn: env.JWT_REFRESH_EXPIRES_IN as any }
    );

    const expiresAt = new Date();
    expiresAt.setDate(expiresAt.getDate() + 7);

    await prisma.refreshToken.create({
      data: {
        usuario_id: usuario.id,
        token: refreshTokenString,
        expires_at: expiresAt
      }
    });

    // Buscar último acesso antes de registrar o atual
    const ultimoAcessoLog = await prisma.logAcesso.findFirst({
      where: {
        usuario_id: usuario.id,
        tipo: 'LOGIN_SUCESSO'
      },
      orderBy: { createdAt: 'desc' }
    });

    const ultimoAcesso = ultimoAcessoLog ? ultimoAcessoLog.createdAt : new Date();

    // Registrar Log de Acesso
    await prisma.logAcesso.create({
      data: {
        escola_id: usuario.escola_id,
        usuario_id: usuario.id,
        ip,
        user_agent: userAgent,
        tipo: 'LOGIN_SUCESSO'
      }
    });

    return {
      user: {
        id: usuario.id,
        nome: usuario.nome,
        email: usuario.email,
        role: usuario.role,
        avatar_url: usuario.avatar_url,
        escola_id: usuario.escola_id,
        aluno_id: usuario.aluno_id,
        professor_id: usuario.professor_id,
        ultimo_acesso: ultimoAcesso
      },
      escola: usuario.escola ? {
        id: usuario.escola.id,
        nome: usuario.escola.nome,
        status: usuario.escola.status,
        ano_letivo_ativo: usuario.escola.ano_letivo_ativo,
        provincia: usuario.escola.provincia,
        distrito: usuario.escola.distrito,
        logo_url: usuario.escola.logo_url,
        usar_emblema_nacional: usuario.escola.usar_emblema_nacional,
        trimestre_ativo: usuario.escola.trimestre_ativo,
        bloqueada_manualmente: usuario.escola.bloqueada_manualmente,
        assinatura: usuario.escola.assinaturas[0] || null
      } : null,
      tokens: {
        accessToken,
        refreshToken: refreshTokenString
      }
    };
  }

  async getMe(usuarioId: string) {
    const usuario = await prisma.usuario.findUnique({
      where: { id: usuarioId },
      include: {
        escola: {
          include: {
            assinaturas: { orderBy: { data_fim: 'desc' }, take: 1, include: { plano: true } }
          }
        },
        aluno: true,
        professor: true
      }
    });

    if (!usuario) throw new Error('Utilizador não encontrado');

    const ultimoAcessoLog = await prisma.logAcesso.findFirst({
      where: { usuario_id: usuario.id, tipo: 'LOGIN_SUCESSO' },
      orderBy: { createdAt: 'desc' }
    });

    return {
      user: {
        id: usuario.id,
        nome: usuario.nome,
        email: usuario.email,
        role: usuario.role,
        avatar_url: usuario.avatar_url,
        escola_id: usuario.escola_id,
        aluno_id: usuario.aluno_id,
        professor_id: usuario.professor_id,
        ultimo_acesso: ultimoAcessoLog?.createdAt || new Date()
      },
      escola: usuario.escola ? {
        id: usuario.escola.id,
        nome: usuario.escola.nome,
        status: usuario.escola.status,
        ano_letivo_ativo: usuario.escola.ano_letivo_ativo,
        provincia: usuario.escola.provincia,
        distrito: usuario.escola.distrito,
        logo_url: usuario.escola.logo_url,
        usar_emblema_nacional: usuario.escola.usar_emblema_nacional,
        trimestre_ativo: usuario.escola.trimestre_ativo,
        bloqueada_manualmente: usuario.escola.bloqueada_manualmente,
        assinatura: usuario.escola.assinaturas[0] || null
      } : null,
      aluno: usuario.aluno,
      professor: usuario.professor
    };
  }

  async refreshToken(token: string) {
    try {
      const decoded = jwt.verify(token, env.JWT_REFRESH_SECRET) as { id: string; email: string };
      const storedToken = await prisma.refreshToken.findUnique({
        where: { token },
        include: { usuario: true }
      });

      if (!storedToken || storedToken.revoked || new Date(storedToken.expires_at) < new Date()) {
        throw new Error('Refresh token inválido ou expirado');
      }

      const newAccessToken = jwt.sign(
        {
          id: storedToken.usuario.id,
          nome: storedToken.usuario.nome,
          email: storedToken.usuario.email,
          role: storedToken.usuario.role,
          escola_id: storedToken.usuario.escola_id
        },
        env.JWT_SECRET,
        { expiresIn: env.JWT_EXPIRES_IN as any }
      );

      return { accessToken: newAccessToken };
    } catch (err) {
      throw new Error('Refresh token inválido ou expirado');
    }
  }

  async logout(token: string) {
    if (token) {
      await prisma.refreshToken.updateMany({
        where: { token },
        data: { revoked: true }
      });
    }
    return { message: 'Sessão encerrada com sucesso' };
  }

  async getAuthStats(escolaId?: string | null) {
    const whereEscola = escolaId ? { escola_id: escolaId } : {};

    const [totalUsuarios, usuariosAtivos, usuariosPorRole, logsRecentes, sessoesBloqueadas] = await Promise.all([
      prisma.usuario.count({ where: whereEscola }),
      prisma.usuario.count({ where: { ...whereEscola, ativo: true } }),
      prisma.usuario.groupBy({
        by: ['role'],
        where: whereEscola,
        _count: { _all: true }
      }),
      prisma.logAcesso.findMany({
        where: whereEscola,
        orderBy: { createdAt: 'desc' },
        take: 10,
        include: {
          usuario: { select: { nome: true, email: true, role: true } }
        }
      }),
      prisma.logAcesso.count({
        where: {
          ...whereEscola,
          tipo: 'ACESSO_BLOQUEADO_EXPIRADO'
        }
      })
    ]);

    // Estatísticas de logins dos últimos 7 dias
    const hoje = new Date();
    const seteDiasAtras = new Date(hoje);
    seteDiasAtras.setDate(hoje.getDate() - 7);

    const logsUltimos7Dias = await prisma.logAcesso.findMany({
      where: {
        ...whereEscola,
        createdAt: { gte: seteDiasAtras }
      },
      select: {
        createdAt: true,
        tipo: true
      }
    });

    const loginsPorDia: Record<string, number> = {};
    for (let i = 6; i >= 0; i--) {
      const d = new Date(hoje);
      d.setDate(hoje.getDate() - i);
      const chave = d.toISOString().split('T')[0];
      loginsPorDia[chave] = 0;
    }

    logsUltimos7Dias.forEach(log => {
      const chave = log.createdAt.toISOString().split('T')[0];
      if (loginsPorDia[chave] !== undefined && log.tipo === 'LOGIN_SUCESSO') {
        loginsPorDia[chave]++;
      }
    });

    return {
      totalUsuarios,
      usuariosAtivos,
      sessoesBloqueadas,
      usuariosPorRole: usuariosPorRole.map(u => ({ role: u.role, total: u._count._all })),
      loginsPorDia,
      logsRecentes
    };
  }
}

export const authService = new AuthService();
