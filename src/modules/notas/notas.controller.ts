import { Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import { notasService } from './notas.service';
import { sendSuccess } from '../../utils/response.util';

const notaSchema = z.object({
  aluno_id: z.string().uuid(),
  disciplina_id: z.string().uuid(),
  turma_id: z.string().uuid(),
  periodo: z.string(),
  teste1: z.union([z.number(), z.string()]).optional().nullable().transform(v => v !== undefined && v !== null && v !== '' ? Number(v) : null),
  teste2: z.union([z.number(), z.string()]).optional().nullable().transform(v => v !== undefined && v !== null && v !== '' ? Number(v) : null),
  teste3: z.union([z.number(), z.string()]).optional().nullable().transform(v => v !== undefined && v !== null && v !== '' ? Number(v) : null),
  teste4: z.union([z.number(), z.string()]).optional().nullable().transform(v => v !== undefined && v !== null && v !== '' ? Number(v) : null),
  trabalho: z.union([z.number(), z.string()]).optional().nullable().transform(v => v !== undefined && v !== null && v !== '' ? Number(v) : null),
  nota_trabalho: z.union([z.number(), z.string()]).optional().nullable().transform(v => v !== undefined && v !== null && v !== '' ? Number(v) : null),
  avaliacao_trimestral: z.union([z.number(), z.string()]).optional().nullable().transform(v => v !== undefined && v !== null && v !== '' ? Number(v) : null),
  nota_exame: z.union([z.number(), z.string()]).optional().nullable().transform(v => v !== undefined && v !== null && v !== '' ? Number(v) : null),
  faltas: z.union([z.number(), z.string()]).optional().transform(v => v ? Number(v) : 0),
  anotacao: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  comportamento: z.string().optional().nullable().or(z.literal('')).transform(v => v || null)
}).transform(dados => ({
  ...dados,
  trabalho: dados.trabalho !== null && dados.trabalho !== undefined ? dados.trabalho : (dados.nota_trabalho ?? null),
  avaliacao_trimestral: dados.avaliacao_trimestral !== null && dados.avaliacao_trimestral !== undefined ? dados.avaliacao_trimestral : (dados.nota_exame ?? null)
}));

const loteSchema = z.object({
  notas: z.array(notaSchema)
});

const desbloqueioSchema = z.object({
  professor_id: z.string().uuid().optional().nullable().or(z.literal('')).transform(v => v || null),
  turma_id: z.string().uuid(),
  disciplina_id: z.string().uuid().optional().nullable().or(z.literal('')).transform(v => v || null),
  periodo: z.string(),
  duracao_horas: z.union([z.number(), z.string()]).optional().transform(v => v ? Number(v) : 48),
  motivo: z.string().optional().nullable().or(z.literal('')).transform(v => v || 'Autorizado pela Direção')
});

export class NotasController {
  async list(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      let { turmaId, disciplinaId, periodo, alunoId } = req.query as any;

      // Se for perfil de ALUNO, só pode listar as suas próprias notas
      if (req.user?.role === 'ALUNO') {
        alunoId = req.user.aluno_id;
      }

      const data = await notasService.list(escolaId, { turmaId, disciplinaId, periodo, alunoId });
      return sendSuccess(res, data, 'Notas recuperadas com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async lancar(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;

      // Requisito 21: Pessoal Administrativo não edita notas
      if (['DIRECTOR_ESCOLA', 'DAP', 'CHEFE_SECRETARIA', 'ADMIN_ESCOLA'].includes(req.user?.role || '')) {
        return res.status(403).json({
          success: false,
          message: 'O Pessoal Administrativo (Director da Escola, DAP, Chefe da Secretaria) não edita notas, apenas cuida da gestão escolar e emissão de documentos.'
        });
      }

      const body = notaSchema.parse(req.body);

      // Requisito 10: Professor só edita trimestre em curso sem autorização
      if (req.user?.role === 'PROFESSOR' && req.user.professor_id) {
        await notasService.validarPermissaoTrimestre(escolaId, req.user.professor_id, body.turma_id, body.disciplina_id, body.periodo);
      }

      const data = await notasService.lancarNota(escolaId, body);
      return sendSuccess(res, data, 'Nota gravada com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async lancarLote(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;

      // Requisito 21: Pessoal Administrativo não edita notas
      if (['DIRECTOR_ESCOLA', 'DAP', 'CHEFE_SECRETARIA', 'ADMIN_ESCOLA'].includes(req.user?.role || '')) {
        return res.status(403).json({
          success: false,
          message: 'O Pessoal Administrativo (Director da Escola, DAP, Chefe da Secretaria) não edita notas, apenas cuida da gestão escolar e emissão de documentos.'
        });
      }

      const body = loteSchema.parse(req.body);

      if (body.notas.length > 0 && req.user?.role === 'PROFESSOR' && req.user.professor_id) {
        const primeiraNota = body.notas[0];
        await notasService.validarPermissaoTrimestre(escolaId, req.user.professor_id, primeiraNota.turma_id, primeiraNota.disciplina_id, primeiraNota.periodo);
      }

      const data = await notasService.lancarLote(escolaId, body.notas);
      return sendSuccess(res, data, `${data.length} notas processadas com sucesso`);
    } catch (error) {
      next(error);
    }
  }

  async autorizarDesbloqueio(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const body = desbloqueioSchema.parse(req.body);
      const autorizadoPor = req.user?.nome || 'Director/DAP';

      const data = await notasService.autorizarDesbloqueio(escolaId, {
        ...body,
        autorizado_por: autorizadoPor
      });

      return sendSuccess(res, data, `Desbloqueio de edição para o ${body.periodo} concedido ao professor.`);
    } catch (error) {
      next(error);
    }
  }

  async stats(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { turmaId, periodo } = req.query as any;
      const data = await notasService.getStats(escolaId, { turmaId, periodo });
      return sendSuccess(res, data, 'Estatísticas de notas e médias da turma');
    } catch (error) {
      next(error);
    }
  }
}

export const notasController = new NotasController();
