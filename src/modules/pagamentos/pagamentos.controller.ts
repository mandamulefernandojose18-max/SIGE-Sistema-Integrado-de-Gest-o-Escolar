import { Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import { pagamentosService } from './pagamentos.service';
import { sendSuccess } from '../../utils/response.util';

const pagamentoSchema = z.object({
  aluno_id: z.string().uuid(),
  descricao: z.string().min(3),
  mes_referencia: z.string(),
  valor: z.number().positive(),
  data_vencimento: z.string()
});

const loteTurmaSchema = z.object({
  turma_id: z.string().uuid(),
  descricao: z.string().min(3),
  mes_referencia: z.string(),
  valor: z.number().positive(),
  data_vencimento: z.string()
});

const liquidarSchema = z.object({
  valor_pago: z.number().positive(),
  metodo_pagamento: z.string().default('TRANSFERENCIA'),
  data_pagamento: z.string().optional()
});

export class PagamentosController {
  async list(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      let { status, mesReferencia, alunoId } = req.query as any;

      // Requisito 9: Aluno só visualiza os seus próprios pagamentos e recibos
      if (req.user?.role === 'ALUNO') {
        alunoId = req.user.aluno_id || 'sem-acesso';
      }

      const data = await pagamentosService.list(escolaId, { status, mesReferencia, alunoId });
      return sendSuccess(res, data, 'Pagamentos recuperados com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async getById(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { id } = req.params;
      const data = await pagamentosService.getById(escolaId, id);
      if (!data) return res.status(404).json({ success: false, message: 'Registro de pagamento não encontrado' });

      // Requisito 9: Aluno só visualiza o seu próprio pagamento
      if (req.user?.role === 'ALUNO' && data.aluno_id !== req.user.aluno_id) {
        return res.status(403).json({ success: false, message: 'Acesso restrito aos próprios recibos de pagamento' });
      }

      return sendSuccess(res, data, 'Detalhes do pagamento recuperados');
    } catch (error) {
      next(error);
    }
  }

  async create(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const body = pagamentoSchema.parse(req.body);
      const data = await pagamentosService.create(escolaId, body);
      return sendSuccess(res, data, 'Cobrança gerada com sucesso', 201);
    } catch (error) {
      next(error);
    }
  }

  async gerarTurma(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const body = loteTurmaSchema.parse(req.body);
      const data = await pagamentosService.gerarMensalidadesTurma(escolaId, body);
      return sendSuccess(res, data, 'Mensalidades da turma geradas com sucesso', 201);
    } catch (error) {
      next(error);
    }
  }

  async liquidar(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { id } = req.params;
      const body = liquidarSchema.parse(req.body);
      const data = await pagamentosService.liquidar(escolaId, id, body);
      return sendSuccess(res, data, 'Pagamento liquidado e recibo emitido com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async stats(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { mesReferencia } = req.query as any;
      const data = await pagamentosService.getStats(escolaId, mesReferencia);
      return sendSuccess(res, data, 'Estatísticas financeiras e de inadimplência');
    } catch (error) {
      next(error);
    }
  }
}

export const pagamentosController = new PagamentosController();
