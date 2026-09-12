import { Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import bcrypt from 'bcryptjs';
import { escolaAdminService } from './escola-admin.service';
import { sendSuccess } from '../../utils/response.util';

const updateEscolaSchema = z.object({
  nome: z.string().min(3).optional(),
  telefone: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  email: z.string().email().optional(),
  endereco: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  logo_url: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  ano_letivo_ativo: z.string().optional().nullable().or(z.literal('')).transform(v => v || '2026'),
  provincia: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  distrito: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  director_nome: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  director_carreira: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  dap_nome: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  chefe_secretaria_nome: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  usar_emblema_nacional: z.boolean().optional(),
  trimestre_ativo: z.union([z.string(), z.number()]).optional()
});

const createTurmaSchema = z.object({
  nome: z.string().min(2),
  grau_ano: z.string().min(2),
  turno: z.enum(['MANHA', 'TARDE', 'NOITE']).default('MANHA'),
  sala: z.string().optional().nullable().or(z.literal('')).transform(v => v || undefined),
  ano_letivo: z.string().optional().nullable().or(z.literal('')).transform(v => v || '2026'),
  director_turma_id: z.string().uuid().optional().nullable().or(z.literal('')).transform(v => v || null),
  director_classe_id: z.string().uuid().optional().nullable().or(z.literal('')).transform(v => v || null)
});

const createAdminUserSchema = z.object({
  nome: z.string().min(3),
  email: z.string().email(),
  senha: z.string().min(6),
  role: z.enum(['DIRECTOR_ESCOLA', 'DAP', 'CHEFE_SECRETARIA', 'FINANCEIRO', 'ADMIN_ESCOLA'])
});

export class EscolaAdminController {
  async getInfo(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const data = await escolaAdminService.getEscolaInfo(escolaId);
      return sendSuccess(res, data, 'Informações da escola recuperadas');
    } catch (error) {
      next(error);
    }
  }

  async updateInfo(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const body = updateEscolaSchema.parse(req.body);
      const data = await escolaAdminService.updateEscolaInfo(escolaId, {
        ...body,
        trimestre_ativo: body.trimestre_ativo !== undefined ? String(body.trimestre_ativo) : undefined
      } as any);
      return sendSuccess(res, data, 'Configurações da escola atualizadas');
    } catch (error) {
      next(error);
    }
  }

  async listTurmas(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const anoLetivo = req.query.ano_letivo as string | undefined;
      const data = await escolaAdminService.listTurmas(escolaId, anoLetivo);
      return sendSuccess(res, data, 'Turmas listadas com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async createTurma(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const body = createTurmaSchema.parse(req.body);
      const data = await escolaAdminService.createTurma(escolaId, body);
      return sendSuccess(res, data, 'Turma criada com sucesso', 201);
    } catch (error) {
      next(error);
    }
  }

  async updateTurma(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { id } = req.params;
      const body = createTurmaSchema.partial().parse(req.body);
      const data = await escolaAdminService.updateTurma(escolaId, id, body);
      return sendSuccess(res, data, 'Turma atualizada com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async deleteTurma(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { id } = req.params;
      await escolaAdminService.deleteTurma(escolaId, id);
      return sendSuccess(res, null, 'Turma removida com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async getStats(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const stats = await escolaAdminService.getTurmasStats(escolaId);
      return sendSuccess(res, stats, 'Estatísticas de turmas recuperadas');
    } catch (error) {
      next(error);
    }
  }

  async listAdministrativos(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const data = await escolaAdminService.listAdministrativos(escolaId);
      return sendSuccess(res, data, 'Membros da equipa administrativa listados');
    } catch (error) {
      next(error);
    }
  }

  async createAdministrativo(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const body = createAdminUserSchema.parse(req.body);
      const senhaHash = await bcrypt.hash(body.senha, 10);
      const data = await escolaAdminService.createAdministrativo(escolaId, {
        nome: body.nome,
        email: body.email,
        senha_hash: senhaHash,
        role: body.role
      });
      return sendSuccess(res, { id: data.id, nome: data.nome, email: data.email, role: data.role }, 'Membro administrativo cadastrado', 201);
    } catch (error) {
      next(error);
    }
  }
}

export const escolaAdminController = new EscolaAdminController();
