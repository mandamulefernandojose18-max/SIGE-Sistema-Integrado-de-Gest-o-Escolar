import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { env } from '../config/env';
import prisma from '../config/database';
import { sendError } from '../utils/response.util';
import { AuthUser } from '../types/express';

export async function authMiddleware(req: Request, res: Response, next: NextFunction) {
  try {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return sendError(res, 'Token de autenticação não fornecido ou inválido', 401, 'UNAUTHORIZED');
    }

    const token = authHeader.split(' ')[1];
    const decoded = jwt.verify(token, env.JWT_SECRET) as {
      id: string;
      email: string;
      role: AuthUser['role'];
      escola_id?: string | null;
    };

    // Verificar se o usuário ainda existe e está ativo
    const user = await prisma.usuario.findUnique({
      where: { id: decoded.id },
      select: {
        id: true,
        nome: true,
        email: true,
        role: true,
        escola_id: true,
        aluno_id: true,
        professor_id: true,
        ativo: true
      }
    });

    if (!user || !user.ativo) {
      return sendError(res, 'Usuário inativo ou não encontrado', 401, 'UNAUTHORIZED');
    }

    req.user = {
      id: user.id,
      nome: user.nome,
      email: user.email,
      role: user.role as AuthUser['role'],
      escola_id: user.escola_id,
      aluno_id: user.aluno_id,
      professor_id: user.professor_id
    };

    next();
  } catch (error: any) {
    if (error.name === 'TokenExpiredError') {
      return sendError(res, 'Token expirado. Por favor renove sua sessão.', 401, 'TOKEN_EXPIRED');
    }
    return sendError(res, 'Token de autenticação inválido', 401, 'INVALID_TOKEN');
  }
}
