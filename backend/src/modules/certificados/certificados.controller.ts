import { Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import { certificadosService } from './certificados.service';
import { sendSuccess } from '../../utils/response.util';

const emitirSchema = z.object({
  aluno_id: z.string().uuid(),
  tipo: z.enum(['CONCLUSAO', 'TRANSFERENCIA', 'MATRICULA']),
  emitido_por: z.string().optional()
});

export class CertificadosController {
  async list(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const tipo = req.query.tipo as string | undefined;
      const data = await certificadosService.list(escolaId, tipo);
      return sendSuccess(res, data, 'Certificados listados com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async getById(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { id } = req.params;
      const data = await certificadosService.getById(escolaId, id);
      if (!data) return res.status(404).json({ success: false, message: 'Certificado não encontrado' });
      return sendSuccess(res, data, 'Certificado recuperado com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async emitir(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const body = emitirSchema.parse(req.body);
      const emitidoPor = req.user?.nome || body.emitido_por;
      const data = await certificadosService.emitir(escolaId, { ...body, emitido_por: emitidoPor });
      return sendSuccess(res, data, 'Certificado emitido e QR Code gerado com sucesso', 201);
    } catch (error) {
      next(error);
    }
  }

  async verificarPublico(req: Request, res: Response, next: NextFunction) {
    try {
      const { codigo } = req.params;
      const data = await certificadosService.verificarAutenticidade(codigo);
      return sendSuccess(res, data, 'Resultado da autenticação de documento');
    } catch (error) {
      next(error);
    }
  }

  async stats(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const data = await certificadosService.getStats(escolaId);
      return sendSuccess(res, data, 'Estatísticas de certificados emitidos');
    } catch (error) {
      next(error);
    }
  }
}

export const certificadosController = new CertificadosController();
