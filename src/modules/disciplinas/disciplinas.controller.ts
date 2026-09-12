import { Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import { disciplinasService } from './disciplinas.service';
import { sendSuccess } from '../../utils/response.util';

const disciplinaSchema = z.object({
  nome: z.string().min(2),
  codigo: z.string().min(2),
  carga_horaria: z.number().int().positive().optional(),
  ano_letivo: z.string().optional()
});

export class DisciplinasController {
  async list(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const anoLetivo = req.query.ano_letivo as string | undefined;
      const data = await disciplinasService.list(escolaId, anoLetivo);
      return sendSuccess(res, data, 'Disciplinas recuperadas com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async getById(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { id } = req.params;
      const data = await disciplinasService.getById(escolaId, id);
      if (!data) return res.status(404).json({ success: false, message: 'Disciplina não encontrada' });
      return sendSuccess(res, data, 'Detalhes da disciplina recuperados');
    } catch (error) {
      next(error);
    }
  }

  async create(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const body = disciplinaSchema.parse(req.body);
      const data = await disciplinasService.create(escolaId, body);
      return sendSuccess(res, data, 'Disciplina criada com sucesso', 201);
    } catch (error) {
      next(error);
    }
  }

  async update(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { id } = req.params;
      const body = disciplinaSchema.partial().parse(req.body);
      const data = await disciplinasService.update(escolaId, id, body);
      return sendSuccess(res, data, 'Disciplina atualizada com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async delete(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { id } = req.params;
      await disciplinasService.delete(escolaId, id);
      return sendSuccess(res, null, 'Disciplina removida com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async stats(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const data = await disciplinasService.getStats(escolaId);
      return sendSuccess(res, data, 'Estatísticas de reprovação e médias por disciplina');
    } catch (error) {
      next(error);
    }
  }
}

export const disciplinasController = new DisciplinasController();
