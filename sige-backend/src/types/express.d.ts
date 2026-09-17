import { Request } from 'express';

export type UserRole =
  | 'SUPERADMIN'
  | 'ADMIN_ESCOLA'
  | 'DIRECTOR_ESCOLA'
  | 'DAP'
  | 'CHEFE_SECRETARIA'
  | 'PROFESSOR'
  | 'ALUNO'
  | 'FINANCEIRO';

export interface AuthUser {
  id: string;
  nome: string;
  email: string;
  role: UserRole;
  escola_id?: string | null;
  aluno_id?: string | null;
  professor_id?: string | null;
}

export interface TenantContext {
  id: string;
  nome: string;
  status: 'ATIVA' | 'PENDENTE' | 'EXPIRADA' | 'SUSPENSA';
  ano_letivo_ativo: string;
  bloqueada_manualmente?: boolean;
}

declare global {
  namespace Express {
    interface Request {
      user?: AuthUser;
      tenant?: TenantContext;
    }
  }
}
