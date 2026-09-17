import { Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import { pautasService } from './pautas.service';
import { sendSuccess } from '../../utils/response.util';

const gerarPautaSchema = z.object({
  turma_id: z.string().uuid(),
  ano_letivo: z.string().default('2026'),
  periodo: z.string().default('1_TRIMESTRE')
});

const statusSchema = z.object({
  status: z.enum(['ABERTA', 'EM_CONSOLIDACAO', 'FECHADA'])
});

export class PautasController {
  async list(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { anoLetivo, periodo } = req.query as any;
      const data = await pautasService.list(escolaId, { anoLetivo, periodo });
      return sendSuccess(res, data, 'Pautas recuperadas com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async getById(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { id } = req.params;
      const data = await pautasService.getById(escolaId, id);
      if (!data) return res.status(404).json({ success: false, message: 'Pauta não encontrada' });
      return sendSuccess(res, data, 'Pauta e consolidação de notas recuperadas');
    } catch (error) {
      next(error);
    }
  }

  async gerar(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const body = gerarPautaSchema.parse(req.body);
      const data = await pautasService.gerarOuObterPauta(escolaId, body);
      return sendSuccess(res, data, 'Pauta gerada/acessada com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async alterarStatus(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { id } = req.params;
      const body = statusSchema.parse(req.body);
      const homologadoPor = req.user?.nome || 'Admin';
      const data = await pautasService.alterarStatus(escolaId, id, body.status, homologadoPor);
      return sendSuccess(res, data, `Status da pauta atualizado para ${body.status}`);
    } catch (error) {
      next(error);
    }
  }

  async stats(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { anoLetivo } = req.query as any;
      const data = await pautasService.getStats(escolaId, anoLetivo);
      return sendSuccess(res, data, 'Estatísticas de pautas fechadas vs pendentes');
    } catch (error) {
      next(error);
    }
  }

  async exportarPautaXlsx(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { id } = req.params;
      const { buffer, filename } = await pautasService.exportarPautaXlsx(escolaId, id);

      res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      res.setHeader('Content-Length', buffer.length.toString());
      return res.end(Buffer.from(buffer));
    } catch (error) {
      next(error);
    }
  }

  async exportarActaXlsx(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { id } = req.params;
      const { buffer, filename } = await pautasService.exportarActaXlsx(escolaId, id);

      res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      res.setHeader('Content-Length', buffer.length.toString());
      return res.end(Buffer.from(buffer));
    } catch (error) {
      next(error);
    }
  }

  async getPautaTurmaCompleta(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { turmaId } = req.params;
      const anoLetivo = (req.query.anoLetivo as string) || '2026';
      const data = await pautasService.getPautaCompleta(escolaId, turmaId, anoLetivo);
      return sendSuccess(res, data, 'Pauta geral completa da turma recuperada com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async getActaTurma(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { turmaId } = req.params;
      const anoLetivo = (req.query.anoLetivo as string) || '2026';
      const data = await pautasService.getActaConselhoAvaliacao(escolaId, turmaId, anoLetivo, req.query);
      return sendSuccess(res, data, 'Acta do conselho de avaliação recuperada com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async exportarPautaTurmaXlsx(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { turmaId } = req.params;
      const anoLetivo = (req.query.anoLetivo as string) || '2026';
      const { buffer, filename } = await pautasService.exportarPautaTurmaXlsx(escolaId, turmaId, anoLetivo);

      res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      res.setHeader('Content-Length', buffer.length.toString());
      return res.end(Buffer.from(buffer));
    } catch (error) {
      next(error);
    }
  }

  async exportarActaTurmaXlsx(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { turmaId } = req.params;
      const anoLetivo = (req.query.anoLetivo as string) || '2026';
      const { buffer, filename } = await pautasService.exportarActaTurmaXlsx(escolaId, turmaId, anoLetivo, req.query);

      res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      res.setHeader('Content-Length', buffer.length.toString());
      return res.end(Buffer.from(buffer));
    } catch (error) {
      next(error);
    }
  }

  async getEstatisticasGerais(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const anoLetivo = (req.query.anoLetivo as string) || '2026';
      const periodo = (req.query.periodo as string) || 'GLOBAL';
      const data = await pautasService.getEstatisticasAproveitamentoGeral(escolaId, anoLetivo, periodo);
      return sendSuccess(res, data, 'Estatísticas pedagógicas recuperadas com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async exportarEstatisticasGeraisXlsx(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const anoLetivo = (req.query.anoLetivo as string) || '2026';
      const periodo = (req.query.periodo as string) || 'GLOBAL';
      const { buffer, filename } = await pautasService.exportarEstatisticasGeraisXlsx(escolaId, anoLetivo, periodo);

      res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      res.setHeader('Content-Length', buffer.length.toString());
      return res.end(Buffer.from(buffer));
    } catch (error) {
      next(error);
    }
  }

  async exportarPautaTurmaJson(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { turmaId } = req.params;
      const anoLetivo = (req.query.anoLetivo as string) || '2026';
      const { json, filename } = await pautasService.exportarPautaJson(escolaId, turmaId, anoLetivo, req.user?.id);

      res.setHeader('Content-Type', 'application/json; charset=utf-8');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      return res.json(json);
    } catch (error) {
      next(error);
    }
  }

  async exportarActaTurmaJson(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { turmaId } = req.params;
      const anoLetivo = (req.query.anoLetivo as string) || '2026';
      const { json, filename } = await pautasService.exportarActaJson(escolaId, turmaId, anoLetivo, req.query, req.user?.id);

      res.setHeader('Content-Type', 'application/json; charset=utf-8');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      return res.json(json);
    } catch (error) {
      next(error);
    }
  }

  async exportarEstatisticasGeraisJson(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const anoLetivo = (req.query.anoLetivo as string) || '2026';
      const periodo = (req.query.periodo as string) || 'GLOBAL';
      const { json, filename } = await pautasService.exportarEstatisticasGeraisJson(escolaId, anoLetivo, periodo, req.user?.id);

      res.setHeader('Content-Type', 'application/json; charset=utf-8');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      return res.json(json);
    } catch (error) {
      next(error);
    }
  }
}

export const pautasController = new PautasController();
