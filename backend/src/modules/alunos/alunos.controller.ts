import { Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import { alunosService } from './alunos.service';
import { sendSuccess } from '../../utils/response.util';

const alunoSchema = z.object({
  nome: z.string().min(3, 'Nome é obrigatório'),
  apelido: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  matricula: z.string().optional(),
  turma_id: z.string().uuid().optional().nullable().or(z.literal('')).transform(v => v || null),
  data_nascimento: z.string(),
  genero: z.enum(['M', 'F']),
  tipo_documento: z.string().optional().default('BI'),
  numero_documento: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  nuit: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  nacionalidade: z.string().optional().default('Moçambicana'),
  provincia: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  distrito: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  pai: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  mae: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  nome_responsavel: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  contato_responsavel: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  email_responsavel: z.string().email().optional().nullable().or(z.literal('')).transform(v => v || null),
  status: z.enum(['ATIVO', 'INATIVO', 'TRANSFERIDO', 'EVADIDO']).default('ATIVO')
});

const alunoSelfUpdateSchema = z.object({
  pai: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  mae: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  contato_responsavel: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  email_responsavel: z.string().email().optional().nullable().or(z.literal('')).transform(v => v || null)
});

export class AlunosController {
  async list(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { turmaId, status, busca } = req.query as any;

      // Se for perfil de ALUNO, só pode listar a si mesmo
      let alunoIdFilter: string | undefined = undefined;
      if (req.user?.role === 'ALUNO') {
        alunoIdFilter = req.user.aluno_id || 'nao-encontrado';
      }

      const data = await alunosService.list(escolaId, { turmaId, status, busca, alunoId: alunoIdFilter });
      return sendSuccess(res, data, 'Alunos recuperados com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async getMeuPerfil(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const alunoId = req.user?.aluno_id;
      if (!alunoId) {
        return res.status(404).json({ success: false, message: 'Perfil de aluno não associado a este utilizador' });
      }
      const data = await alunosService.getById(escolaId, alunoId);
      if (!data) return res.status(404).json({ success: false, message: 'Aluno não encontrado' });
      return sendSuccess(res, data, 'Perfil pessoal do aluno recuperado');
    } catch (error) {
      next(error);
    }
  }

  async getMinhasNotas(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const alunoId = req.user?.aluno_id;
      if (!alunoId) {
        return res.status(404).json({ success: false, message: 'Perfil de aluno não associado a este utilizador' });
      }
      const data = await alunosService.getNotasDoAluno(escolaId, alunoId);
      return sendSuccess(res, data, 'Histórico de notas do aluno recuperado');
    } catch (error) {
      next(error);
    }
  }

  async getMeusPagamentos(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const alunoId = req.user?.aluno_id;
      if (!alunoId) {
        return res.status(404).json({ success: false, message: 'Perfil de aluno não associado a este utilizador' });
      }
      const data = await alunosService.getPagamentosDoAluno(escolaId, alunoId);
      return sendSuccess(res, data, 'Pagamentos do aluno recuperados');
    } catch (error) {
      next(error);
    }
  }

  async updateMinhaFiliacao(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const alunoId = req.user?.aluno_id;
      if (!alunoId) {
        return res.status(404).json({ success: false, message: 'Perfil de aluno não associado a este utilizador' });
      }
      const body = alunoSelfUpdateSchema.parse(req.body);
      const data = await alunosService.update(escolaId, alunoId, body);
      return sendSuccess(res, data, 'Dados de filiação actualizados com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async getById(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { id } = req.params;

      // Isolamento estrito do ALUNO: não pode ver outros alunos
      if (req.user?.role === 'ALUNO' && req.user.aluno_id !== id) {
        return res.status(403).json({ success: false, message: 'Acesso restrito: só pode visualizar o seu próprio perfil' });
      }

      const data = await alunosService.getById(escolaId, id);
      if (!data) return res.status(404).json({ success: false, message: 'Aluno não encontrado' });
      return sendSuccess(res, data, 'Detalhes do aluno recuperados');
    } catch (error) {
      next(error);
    }
  }

  async create(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const body = alunoSchema.parse(req.body);
      const data = await alunosService.create(escolaId, body as any);
      return sendSuccess(res, data, 'Aluno matriculado com sucesso', 201);
    } catch (error) {
      next(error);
    }
  }

  async update(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { id } = req.params;

      // Se for o próprio aluno atualizando, só pode alterar dados permitidos (pai, mãe, contato)
      if (req.user?.role === 'ALUNO') {
        if (req.user.aluno_id !== id) {
          return res.status(403).json({ success: false, message: 'Acesso não autorizado para alterar dados de outros alunos' });
        }
        const body = alunoSelfUpdateSchema.parse(req.body);
        const data = await alunosService.update(escolaId, id, body);
        return sendSuccess(res, data, 'Filiação actualizada com sucesso');
      }

      const body = alunoSchema.partial().parse(req.body);
      const data = await alunosService.update(escolaId, id, body);
      return sendSuccess(res, data, 'Dados do aluno atualizados');
    } catch (error) {
      next(error);
    }
  }

  async delete(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { id } = req.params;
      await alunosService.delete(escolaId, id);
      return sendSuccess(res, null, 'Aluno excluído com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async transferir(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { id } = req.params;
      const { novaTurmaId } = req.body;
      if (!novaTurmaId) {
        return res.status(400).json({ success: false, message: 'ID da nova turma é obrigatório' });
      }
      const data = await alunosService.transferirTurma(escolaId, id, novaTurmaId);
      return sendSuccess(res, data, 'Aluno transferido de turma com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async stats(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const data = await alunosService.getStats(escolaId);
      return sendSuccess(res, data, 'Estatísticas demográficas e retenção de alunos');
    } catch (error) {
      next(error);
    }
  }
}

export const alunosController = new AlunosController();
