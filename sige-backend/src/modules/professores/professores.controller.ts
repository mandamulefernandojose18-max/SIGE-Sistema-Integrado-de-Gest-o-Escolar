import { Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import { professoresService } from './professores.service';
import { sendSuccess } from '../../utils/response.util';
import prisma from '../../config/database';

const professorSchema = z.object({
  nome: z.string().min(3),
  apelido: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  genero: z.enum(['M', 'F']).default('M'),
  tipo_documento: z.string().optional().default('BI'),
  numero_documento: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  nuit: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  nacionalidade: z.string().optional().default('Moçambicana'),
  provincia: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  distrito: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  carreira: z.string().optional().default('DN1'),
  email: z.string().email(),
  telefone: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  especialidade: z.string().optional().default('Geral').or(z.literal('')).transform(v => v || 'Geral'),
  carga_horaria_semanal: z.union([z.number(), z.string()]).optional().transform(v => v ? Number(v) : 20),
  criarUsuario: z.boolean().optional(),
  senha: z.string().optional().nullable().or(z.literal('')).transform(v => v || '123456')
});

const alocacaoSchema = z.object({
  professor_id: z.string().uuid(),
  disciplina_id: z.string().uuid(),
  turma_id: z.string().uuid()
});

export class ProfessoresController {
  async list(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { especialidade, busca } = req.query as any;

      // Se for professor, isola apenas a si mesmo
      let professorIdFilter: string | undefined = undefined;
      if (req.user?.role === 'PROFESSOR') {
        professorIdFilter = req.user.professor_id || 'nao-encontrado';
      }

      const data = await professoresService.list(escolaId, {
        especialidade,
        busca,
        professorId: professorIdFilter
      });
      return sendSuccess(res, data, 'Professores recuperados com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async getById(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { id } = req.params;
      const data = await professoresService.getById(escolaId, id);
      if (!data) return res.status(404).json({ success: false, message: 'Professor não encontrado' });
      return sendSuccess(res, data, 'Detalhes do professor recuperados');
    } catch (error) {
      next(error);
    }
  }

  async create(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const body = professorSchema.parse(req.body);
      const data = await professoresService.create(escolaId, body as any);
      return sendSuccess(res, data, 'Professor cadastrado com sucesso', 201);
    } catch (error) {
      next(error);
    }
  }

  async update(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { id } = req.params;
      const body = professorSchema.partial().parse(req.body);
      const data = await professoresService.update(escolaId, id, body);
      return sendSuccess(res, data, 'Professor atualizado com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async delete(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { id } = req.params;
      await professoresService.delete(escolaId, id);
      return sendSuccess(res, null, 'Professor removido com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async alocar(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const body = alocacaoSchema.parse(req.body);
      const data = await professoresService.alocar(escolaId, body);
      return sendSuccess(res, data, 'Professor alocado com sucesso', 201);
    } catch (error) {
      next(error);
    }
  }

  async desalocar(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { id } = req.params;
      await professoresService.desalocar(escolaId, id);
      return sendSuccess(res, null, 'Alocação removida com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async stats(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const data = await professoresService.getStats(escolaId);
      return sendSuccess(res, data, 'Estatísticas do corpo docente recuperadas');
    } catch (error) {
      next(error);
    }
  }

  async getMinhasTurmas(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const professorId = req.user?.professor_id;

      if (req.user?.role === 'PROFESSOR') {
        if (!professorId) {
          return res.status(404).json({ success: false, message: 'Perfil de professor não associado' });
        }
        const data = await professoresService.getMinhasAlocacoes(escolaId, professorId);
        return sendSuccess(res, data, 'Turmas e disciplinas leccionadas recuperadas');
      }

      // Para SUPERADMIN, ADMIN_ESCOLA, DIRECTOR_ESCOLA, DAP: permite visualizar qualquer alocação
      const data = await prisma.professorDisciplinaTurma.findMany({
        where: { escola_id: escolaId },
        include: { turma: true, disciplina: true, professor: true },
        orderBy: [{ turma: { nome: 'asc' } }, { disciplina: { nome: 'asc' } }]
      });
      return sendSuccess(res, data, 'Alocações da escola recuperadas');
    } catch (error) {
      next(error);
    }
  }

  async getCaderneta(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { alocacaoId } = req.params;
      const data = await professoresService.getCadernetaCompleta(escolaId, alocacaoId);
      return sendSuccess(res, data, 'Caderneta do professor carregada com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async getCadernetaCompleta(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { alocacaoId } = req.params;
      const data = await professoresService.getCadernetaCompleta(escolaId, alocacaoId);
      return sendSuccess(res, data, 'Caderneta completa do professor carregada com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async exportarCadernetaXlsx(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { alocacaoId } = req.params;
      const { buffer, filename } = await professoresService.exportarCadernetaXlsx(escolaId, alocacaoId);

      res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      res.setHeader('Content-Length', buffer.length.toString());
      return res.send(buffer);
    } catch (error) {
      next(error);
    }
  }

  async getMeuPerfil(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const professorId = req.user?.professor_id || req.query.professorId as string;
      if (!professorId) {
        return res.status(404).json({ success: false, message: 'Perfil de professor não identificado' });
      }
      const data = await professoresService.getMeuPerfil(escolaId, professorId);
      return sendSuccess(res, data, 'Perfil do professor recuperado com sucesso');
    } catch (error) {
      next(error);
    }
  }
}

export const professoresController = new ProfessoresController();
