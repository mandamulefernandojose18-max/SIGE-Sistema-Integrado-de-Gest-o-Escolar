import { Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import { MaterialEscolarService } from './material-escolar.service';
import { sendSuccess } from '../../utils/response.util';
import prisma from '../../config/database';

const materialEscolarService = new MaterialEscolarService();

const materialSchema = z.object({
  classe: z.string().min(1, 'Classe é obrigatória'),
  disciplina_id: z.string().optional().nullable().or(z.literal('')).transform(v => v || null),
  titulo: z.string().min(2, 'Título deve ter pelo menos 2 caracteres'),
  descricao: z.string().optional().nullable(),
  tipo: z.string().optional().default('MANUAL'),
  nome_arquivo: z.string().optional(),
  extensao: z.string().optional(),
  tamanho_bytes: z.number().optional().default(0),
  conteudo_base64: z.string().optional().nullable(),
  tipo_mime: z.string().optional().nullable(),
  arquivo_url: z.string().optional().nullable(),
  publicado_por: z.string().optional().nullable()
});

export class MaterialEscolarController {
  private async obterClasseAluno(escolaId: string, alunoId?: string | null): Promise<string | null> {
    if (!alunoId) return null;
    const aluno = await prisma.aluno.findFirst({
      where: { id: alunoId, escola_id: escolaId },
      include: { turma: true }
    });
    return (aluno as any)?.turma?.grau_ano || null;
  }

  private classeCorresponde(classeMaterial: string, classeAluno: string | null): boolean {
    if (!classeMaterial || !classeAluno) return false;
    if (classeMaterial.toLowerCase().trim() === classeAluno.toLowerCase().trim()) return true;
    const numM = classeMaterial.replace(/\D/g, '');
    const numA = classeAluno.replace(/\D/g, '');
    return numM !== '' && numA !== '' && numM === numA;
  }

  async list(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      let classe = req.query.classe as string | undefined;
      const disciplinaId = req.query.disciplina_id as string | undefined;
      const search = req.query.search as string | undefined;

      // Se for aluno, restringe estritamente à sua classe
      if (req.user?.role === 'ALUNO') {
        const classeAluno = await this.obterClasseAluno(escolaId, req.user.aluno_id);
        if (!classeAluno) {
          return sendSuccess(res, [], 'Aluno não enturmado ou sem classe atribuída');
        }
        classe = classeAluno;
      }

      const data = await materialEscolarService.list(escolaId, { classe, disciplinaId, search });
      return sendSuccess(res, data, 'Materiais escolares recuperados com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async getClasses(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;

      // Se for aluno, restringe estritamente à sua classe
      if (req.user?.role === 'ALUNO') {
        const classeAluno = await this.obterClasseAluno(escolaId, req.user.aluno_id);
        if (!classeAluno) {
          return sendSuccess(res, []);
        }
        const classes = await materialEscolarService.getClassesDisponiveis(escolaId);
        const filtradas = classes.filter(c => this.classeCorresponde(c.classe, classeAluno));
        return sendSuccess(res, filtradas.length > 0 ? filtradas : [{ classe: classeAluno, totalMateriais: 0 }]);
      }

      const data = await materialEscolarService.getClassesDisponiveis(escolaId);
      return sendSuccess(res, data, 'Classes e contagem de materiais recuperadas com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async getById(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { id } = req.params;
      const data = await materialEscolarService.getById(escolaId, id);
      if (!data) {
        return res.status(404).json({ success: false, message: 'Material escolar não encontrado' });
      }

      // Se for aluno, restringe estritamente à sua classe
      if (req.user?.role === 'ALUNO') {
        const classeAluno = await this.obterClasseAluno(escolaId, req.user.aluno_id);
        if (!this.classeCorresponde(data.classe, classeAluno)) {
          return res.status(403).json({ success: false, message: 'Acesso negado: só pode consultar material escolar da sua classe' });
        }
      }

      return sendSuccess(res, data, 'Detalhes do material recuperados com sucesso');
    } catch (error) {
      next(error);
    }
  }

  async create(req: Request, res: Response, next: NextFunction) {
    try {
      if (req.user?.role === 'ALUNO') {
        return res.status(403).json({ success: false, message: 'Apenas professores e directores podem carregar ou importar materiais escolares' });
      }
      const escolaId = req.tenant!.id;
      const body = materialSchema.parse(req.body);
      const data = await materialEscolarService.create(escolaId, {
        ...body,
        publicado_por: body.publicado_por || req.user?.nome || 'Administração'
      });
      return sendSuccess(res, data, 'Material escolar publicado com sucesso', 201);
    } catch (error) {
      next(error);
    }
  }

  async download(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { id } = req.params;
      const data = await materialEscolarService.getById(escolaId, id);

      if (!data) {
        return res.status(404).json({ success: false, message: 'Material escolar não encontrado' });
      }

      // Se for aluno, restringe estritamente à sua classe
      if (req.user?.role === 'ALUNO') {
        const classeAluno = await this.obterClasseAluno(escolaId, req.user.aluno_id);
        if (!this.classeCorresponde(data.classe, classeAluno)) {
          return res.status(403).json({ success: false, message: 'Acesso negado: só pode descarregar material escolar da sua classe' });
        }
      }

      // Se possui URL externa e não tem base64, redireciona
      if (data.arquivo_url && !data.conteudo_base64) {
        return res.redirect(data.arquivo_url);
      }

      if (data.conteudo_base64) {
        let base64Pure = data.conteudo_base64;
        if (base64Pure.includes(',')) {
          base64Pure = base64Pure.split(',')[1];
        }

        const buffer = Buffer.from(base64Pure, 'base64');
        const filename = encodeURIComponent(data.nome_arquivo || `${data.titulo}.${data.extensao || 'pdf'}`);

        res.setHeader('Content-Type', data.tipo_mime || 'application/octet-stream');
        res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
        res.setHeader('Content-Length', buffer.length);
        return res.send(buffer);
      }

      return res.status(400).json({ success: false, message: 'Ficheiro não disponível para transferência direta' });
    } catch (error) {
      next(error);
    }
  }

  async delete(req: Request, res: Response, next: NextFunction) {
    try {
      if (req.user?.role === 'ALUNO') {
        return res.status(403).json({ success: false, message: 'Apenas professores e directores podem eliminar materiais escolares' });
      }
      const escolaId = req.tenant!.id;
      const { id } = req.params;
      await materialEscolarService.delete(escolaId, id);
      return sendSuccess(res, null, 'Material escolar removido com sucesso');
    } catch (error) {
      next(error);
    }
  }
}

export const materialEscolarController = new MaterialEscolarController();
