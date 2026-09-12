import { Request, Response, NextFunction } from 'express';
import { ZodError } from 'zod';
import { sendError } from '../utils/response.util';

export function errorHandler(err: any, req: Request, res: Response, next: NextFunction) {
  console.error('Unhandled Error:', err);

  if (err instanceof ZodError) {
    return sendError(
      res,
      'Dados de entrada inválidos',
      422,
      'VALIDATION_ERROR',
      err.errors.map(e => ({ campo: e.path.join('.'), mensagem: e.message }))
    );
  }

  if (err.code === 'P2002') {
    return sendError(res, 'Já existe um registro cadastrado com estes dados únicos.', 409, 'CONFLICT');
  }

  if (err.code === 'P2025') {
    return sendError(res, 'Registro não encontrado no banco de dados.', 404, 'NOT_FOUND');
  }

  return sendError(
    res,
    process.env.NODE_ENV === 'production' ? 'Erro interno no servidor' : err.message || 'Erro interno',
    500,
    'INTERNAL_SERVER_ERROR'
  );
}
