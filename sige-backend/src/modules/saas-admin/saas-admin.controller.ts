import { Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import { saasAdminService } from './saas-admin.service';
import { sendSuccess } from '../../utils/response.util';

const createEscolaSchema = z.object({
  nome: z.string().min(3),
  nif_cnpj: z.string().min(5),
  email: z.string().email(),
  telefone: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  endereco: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  provincia: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  distrito: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  plano_id: z.string().uuid(),
  adminNome: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  adminEmail: z.string().email().optional().nullable().or(z.literal('')).transform(v => v || null),
  adminSenha: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  usar_emblema_nacional: z.boolean().optional().default(false),
  logo_url: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  valor_contrato: z.union([z.number(), z.string()]).optional().nullable().transform(v => v ? Number(v) : null)
});

const updateEscolaSchema = z.object({
  nome: z.string().min(3).optional(),
  nif_cnpj: z.string().min(5).optional(),
  email: z.string().email().optional(),
  telefone: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  endereco: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  provincia: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  distrito: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  plano_id: z.string().uuid().optional().nullable().or(z.literal('')).transform(v => v || null),
  usar_emblema_nacional: z.boolean().optional(),
  logo_url: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  data_fim: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  data_fim_assinatura: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  dias_adicionais: z.union([z.number(), z.string()]).optional().nullable().transform(v => v ? Number(v) : null)
});

const renovarSchema = z.object({
  plano_id: z.string().uuid().optional(),
  diasAdicionais: z.number().int().positive().optional()
});

const precoPlanoSchema = z.object({
  preco: z.number().positive(),
  descricao: z.string().optional()
});

export class SaasAdminController {
  async getMetrics(req: Request, res: Response, next: NextFunction) {
    try {
      const data = await saasAdminService.getMetrics();
      return sendSuccess(res, data, 'Métricas do SaaS recuperadas em MZN');
    } catch (error) {
      next(error);
    }
  }

  async listEscolas(req: Request, res: Response, next: NextFunction) {
    try {
      const data = await saasAdminService.listEscolas();
      return sendSuccess(res, data, 'Escolas listadas com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async createEscola(req: Request, res: Response, next: NextFunction) {
    try {
      const body = createEscolaSchema.parse(req.body);
      const data = await saasAdminService.createEscola(body);
      return sendSuccess(res, data, 'Escola cadastrada com sucesso', 201);
    } catch (error) {
      next(error);
    }
  }

  async updateEscola(req: Request, res: Response, next: NextFunction) {
    try {
      const { id } = req.params;
      const body = updateEscolaSchema.parse(req.body);
      const data = await saasAdminService.updateEscola(id, body);
      return sendSuccess(res, data, 'Dados da escola actualizados');
    } catch (error) {
      next(error);
    }
  }

  async toggleStatus(req: Request, res: Response, next: NextFunction) {
    try {
      const { id } = req.params;
      const data = await saasAdminService.toggleStatusEscola(id);
      return sendSuccess(res, data, `Status da escola alterado para ${data.status}`);
    } catch (error) {
      next(error);
    }
  }

  async updatePrecoPlano(req: Request, res: Response, next: NextFunction) {
    try {
      const { id } = req.params;
      const body = precoPlanoSchema.parse(req.body);
      const data = await saasAdminService.atualizarPrecoPlano(id, body.preco, body.descricao);
      return sendSuccess(res, data, 'Preço do plano actualizado com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async renovarAssinatura(req: Request, res: Response, next: NextFunction) {
    try {
      const { id } = req.params;
      const body = renovarSchema.parse(req.body);
      const data = await saasAdminService.renovarAssinatura(id, body.plano_id, body.diasAdicionais);
      return sendSuccess(res, data, 'Assinatura renovada com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async getComprovativoContrato(req: Request, res: Response, next: NextFunction) {
    try {
      const id = req.params.id || req.tenant?.id;
      if (!id) return res.status(400).json({ success: false, message: 'ID da escola não informado' });
      const data = await saasAdminService.gerarComprovativoContrato(id);
      return sendSuccess(res, data, 'Comprovativo de licença gerado');
    } catch (error) {
      next(error);
    }
  }

  async listPlanos(req: Request, res: Response, next: NextFunction) {
    try {
      const data = await saasAdminService.listPlanos();
      return sendSuccess(res, data, 'Planos listados com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async verificarExpiracoes(req: Request, res: Response, next: NextFunction) {
    try {
      const result = await saasAdminService.triggerExpirationCheck();
      return sendSuccess(res, result, 'Verificação de expiração executada com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async deleteEscola(req: Request, res: Response, next: NextFunction) {
    try {
      const { id } = req.params;
      await saasAdminService.deleteEscola(id);
      return sendSuccess(res, null, 'Escola e todos os seus registos foram eliminados com sucesso');
    } catch (error) {
      next(error);
    }
  }
}

export const saasAdminController = new SaasAdminController();
