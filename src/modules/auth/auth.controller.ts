import { Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import { authService } from './auth.service';
import { sendSuccess, sendError } from '../../utils/response.util';

const loginSchema = z.object({
  email: z.string().optional(),
  usuario: z.string().optional(),
  senha: z.string().min(4, 'A senha deve ter pelo menos 4 caracteres')
}).transform(d => ({
  email: (d.email || d.usuario || '').trim(),
  senha: d.senha
})).refine(d => d.email.length >= 3, {
  message: 'E-mail ou nome de utilizador inválido',
  path: ['email']
});

const refreshSchema = z.object({
  refreshToken: z.string().min(1, 'Refresh token é obrigatório')
});

export class AuthController {
  async login(req: Request, res: Response, next: NextFunction) {
    try {
      const data = loginSchema.parse(req.body);
      const ip = (req.headers['x-forwarded-for'] as string) || req.ip || '127.0.0.1';
      const userAgent = req.headers['user-agent'] || 'Desconhecido';

      const result = await authService.login(data.email, data.senha, ip, userAgent);
      return sendSuccess(res, result, 'Login efetuado com sucesso');
    } catch (error: any) {
      if (error.name === 'ZodError') return next(error);
      return sendError(res, error.message || 'Falha no login', 401, 'INVALID_CREDENTIALS');
    }
  }

  async refresh(req: Request, res: Response, next: NextFunction) {
    try {
      const data = refreshSchema.parse(req.body);
      const result = await authService.refreshToken(data.refreshToken);
      return sendSuccess(res, result, 'Token renovado com sucesso');
    } catch (error: any) {
      if (error.name === 'ZodError') return next(error);
      return sendError(res, error.message || 'Falha ao renovar token', 401, 'INVALID_REFRESH_TOKEN');
    }
  }

  async logout(req: Request, res: Response, next: NextFunction) {
    try {
      const token = req.body.refreshToken || req.headers['x-refresh-token'];
      const result = await authService.logout(token as string);
      return sendSuccess(res, result, 'Logout realizado com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async me(req: Request, res: Response, next: NextFunction) {
    try {
      const data = await authService.getMe(req.user!.id);
      return sendSuccess(res, data, 'Sessão do utilizador recuperada com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async stats(req: Request, res: Response, next: NextFunction) {
    try {
      const isSuperAdmin = req.user?.role === 'SUPERADMIN';
      const escolaId = isSuperAdmin ? null : req.tenant?.id;
      const stats = await authService.getAuthStats(escolaId, isSuperAdmin);
      return sendSuccess(res, stats, 'Estatísticas de autenticação recuperadas');
    } catch (error) {
      next(error);
    }
  }
}

export const authController = new AuthController();
