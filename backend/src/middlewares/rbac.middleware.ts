import { Request, Response, NextFunction } from 'express';
import { sendError } from '../utils/response.util';
import { AuthUser } from '../types/express';

export function authorizeRoles(...allowedRoles: Array<AuthUser['role']>) {
  return (req: Request, res: Response, next: NextFunction) => {
    if (!req.user) {
      return sendError(res, 'Acesso não autenticado', 401, 'UNAUTHORIZED');
    }

    if (!allowedRoles.includes(req.user.role)) {
      return sendError(
        res,
        `Acesso negado. Seu perfil (${req.user.role}) não possui permissão para este recurso.`,
        403,
        'FORBIDDEN'
      );
    }

    next();
  };
}
