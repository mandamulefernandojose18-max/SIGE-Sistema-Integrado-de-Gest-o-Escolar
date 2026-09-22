import { Request, Response, NextFunction } from 'express';
import { impressaoService } from './impressao.service';
import { sendSuccess } from '../../utils/response.util';

export class ImpressaoController {
  async gerarBoletim(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { alunoId } = req.params;

      if (req.user?.role === 'ALUNO' && req.user.aluno_id !== alunoId) {
        return res.status(403).json({ success: false, message: 'Acesso restrito ao próprio boletim escolar' });
      }

      const anoLetivo = (req.query.anoLetivo as string) || req.tenant!.ano_letivo_ativo;
      const data = await impressaoService.gerarBoletimAluno(escolaId, alunoId, anoLetivo, req.user?.id);
      return sendSuccess(res, data, 'Dados de boletim gerados para impressão');
    } catch (error) {
      next(error);
    }
  }

  async gerarRecibo(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { pagamentoId } = req.params;
      const data = await impressaoService.gerarReciboPagamento(escolaId, pagamentoId, req.user?.id);

      if (req.user?.role === 'ALUNO' && req.user.aluno_id !== data.aluno.id) {
        return res.status(403).json({ success: false, message: 'Acesso restrito aos próprios recibos de pagamento' });
      }

      return sendSuccess(res, data, 'Dados do recibo gerados para impressão');
    } catch (error) {
      next(error);
    }
  }

  async gerarFichaAluno(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { alunoId } = req.params;

      if (req.user?.role === 'ALUNO' && req.user.aluno_id !== alunoId) {
        return res.status(403).json({ success: false, message: 'Acesso restrito à própria ficha cadastral' });
      }

      const data = await impressaoService.gerarFichaAluno(escolaId, alunoId, req.user?.id);
      return sendSuccess(res, data, 'Ficha do aluno gerada para impressão');
    } catch (error) {
      next(error);
    }
  }

  async gerarDeclaracao(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { alunoId } = req.params;
      const comNotas = req.query.comNotas === 'true';

      if (req.user?.role === 'ALUNO' && req.user.aluno_id !== alunoId) {
        return res.status(403).json({ success: false, message: 'Acesso restrito à própria declaração escolar' });
      }

      const data = await impressaoService.gerarDeclaracaoAluno(escolaId, alunoId, comNotas, req.user?.id);
      return sendSuccess(res, data, 'Declaração escolar oficial gerada');
    } catch (error) {
      next(error);
    }
  }

  async gerarCertificado(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { alunoId } = req.params;

      if (req.user?.role === 'ALUNO' && req.user.aluno_id !== alunoId) {
        return res.status(403).json({ success: false, message: 'Acesso restrito ao próprio certificado escolar' });
      }

      const data = await impressaoService.gerarCertificadoAluno(escolaId, alunoId, req.user?.id);
      return sendSuccess(res, data, 'Certificado oficial de habilitações gerado');
    } catch (error) {
      next(error);
    }
  }

  async gerarLote(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { turmaId } = req.params;
      const tipo = (req.query.tipo as any) || 'BOLETIM';

      const data = await impressaoService.gerarLoteTurma(escolaId, turmaId, tipo, req.user?.id);
      return sendSuccess(res, data, `Documentos em lote da turma gerados (${data.total} alunos)`);
    } catch (error) {
      next(error);
    }
  }

  async stats(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const data = await impressaoService.getStats(escolaId);
      return sendSuccess(res, data, 'Estatísticas de documentos impressos/gerados');
    } catch (error) {
      next(error);
    }
  }

  async exportarBoletimXlsx(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { alunoId } = req.params;
      const { buffer, filename } = await impressaoService.exportarBoletimXlsx(escolaId, alunoId);

      res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      return res.send(buffer);
    } catch (error) {
      next(error);
    }
  }

  async exportarDeclaracaoXlsx(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { alunoId } = req.params;
      const { buffer, filename } = await impressaoService.exportarDeclaracaoXlsx(escolaId, alunoId);

      res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      return res.send(buffer);
    } catch (error) {
      next(error);
    }
  }

  async exportarCertificadoXlsx(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { alunoId } = req.params;
      const { buffer, filename } = await impressaoService.exportarCertificadoXlsx(escolaId, alunoId);

      res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      return res.send(buffer);
    } catch (error) {
      next(error);
    }
  }

  async exportarLoteXlsx(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { turmaId } = req.params;
      const tipo = (req.query.tipo as any) || 'BOLETIM';
      const { buffer, filename } = await impressaoService.exportarLoteXlsx(escolaId, turmaId, tipo);

      res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      return res.send(buffer);
    } catch (error) {
      next(error);
    }
  }

  async exportarBoletimJson(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { alunoId } = req.params;
      const { json, filename } = await impressaoService.exportarBoletimJson(escolaId, alunoId, req.user?.id);

      res.setHeader('Content-Type', 'application/json; charset=utf-8');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      return res.json(json);
    } catch (error) {
      next(error);
    }
  }

  async exportarDeclaracaoJson(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { alunoId } = req.params;
      const { json, filename } = await impressaoService.exportarDeclaracaoJson(escolaId, alunoId, req.user?.id);

      res.setHeader('Content-Type', 'application/json; charset=utf-8');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      return res.json(json);
    } catch (error) {
      next(error);
    }
  }

  async exportarCertificadoJson(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { alunoId } = req.params;
      const { json, filename } = await impressaoService.exportarCertificadoJson(escolaId, alunoId, req.user?.id);

      res.setHeader('Content-Type', 'application/json; charset=utf-8');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      return res.json(json);
    } catch (error) {
      next(error);
    }
  }

  async exportarLoteJson(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { turmaId } = req.params;
      const tipo = (req.query.tipo as any) || 'BOLETIM';
      const { json, filename } = await impressaoService.exportarLoteJson(escolaId, turmaId, tipo, req.user?.id);

      res.setHeader('Content-Type', 'application/json; charset=utf-8');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      return res.json(json);
    } catch (error) {
      next(error);
    }
  }

  async exportarBoletimPdf(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { alunoId } = req.params;
      const anoLetivo = (req.query.anoLetivo as string) || req.tenant!.ano_letivo_ativo;
      const { buffer, filename } = await impressaoService.exportarBoletimPdf(escolaId, alunoId, anoLetivo);

      res.setHeader('Content-Type', 'application/pdf');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      return res.send(buffer);
    } catch (error) {
      next(error);
    }
  }

  async exportarBoletimDocx(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { alunoId } = req.params;
      const { buffer, filename } = await impressaoService.exportarBoletimDocx(escolaId, alunoId);

      res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      return res.send(buffer);
    } catch (error) {
      next(error);
    }
  }

  async exportarDeclaracaoPdf(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { alunoId } = req.params;
      const comNotas = req.query.comNotas !== 'false';
      const { buffer, filename } = await impressaoService.exportarDeclaracaoPdf(escolaId, alunoId, comNotas);

      res.setHeader('Content-Type', 'application/pdf');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      return res.send(buffer);
    } catch (error) {
      next(error);
    }
  }

  async exportarDeclaracaoDocx(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { alunoId } = req.params;
      const comNotas = req.query.comNotas !== 'false';
      const { buffer, filename } = await impressaoService.exportarDeclaracaoDocx(escolaId, alunoId, comNotas);

      res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      return res.send(buffer);
    } catch (error) {
      next(error);
    }
  }

  async exportarCertificadoPdf(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { alunoId } = req.params;
      const { buffer, filename } = await impressaoService.exportarCertificadoPdf(escolaId, alunoId);

      res.setHeader('Content-Type', 'application/pdf');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      return res.send(buffer);
    } catch (error) {
      next(error);
    }
  }

  async exportarCertificadoDocx(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { alunoId } = req.params;
      const { buffer, filename } = await impressaoService.exportarCertificadoDocx(escolaId, alunoId);

      res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      return res.send(buffer);
    } catch (error) {
      next(error);
    }
  }

  async exportarReciboPdf(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { pagamentoId } = req.params;
      const { buffer, filename } = await impressaoService.exportarReciboPdf(escolaId, pagamentoId, req.user?.nome);

      res.setHeader('Content-Type', 'application/pdf');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      return res.send(buffer);
    } catch (error) {
      next(error);
    }
  }

  async exportarReciboDocx(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const { pagamentoId } = req.params;
      const { buffer, filename } = await impressaoService.exportarReciboDocx(escolaId, pagamentoId);

      res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      return res.send(buffer);
    } catch (error) {
      next(error);
    }
  }

  async listarDocumentosSalvos(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const tipo = req.query.tipo as string;
      const data = await impressaoService.listarDocumentosSalvos(escolaId, tipo);
      return sendSuccess(res, data, 'Documentos gravados em JSON recuperados com sucesso');
    } catch (error) {
      next(error);
    }
  }
}

export const impressaoController = new ImpressaoController();

