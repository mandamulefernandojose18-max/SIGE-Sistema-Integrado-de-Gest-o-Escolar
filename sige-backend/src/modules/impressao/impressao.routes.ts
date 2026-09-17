import { Router } from 'express';
import { impressaoController } from './impressao.controller';
import { authMiddleware } from '../../middlewares/auth.middleware';
import { tenantMiddleware } from '../../middlewares/tenant.middleware';

const router = Router();

router.use(authMiddleware, tenantMiddleware);

router.get('/stats', (req, res, next) => impressaoController.stats(req, res, next));
router.get('/documentos-salvos', (req, res, next) => impressaoController.listarDocumentosSalvos(req, res, next));

router.get('/boletim/:alunoId', (req, res, next) => impressaoController.gerarBoletim(req, res, next));
router.get('/boletim/:alunoId/xlsx', (req, res, next) => impressaoController.exportarBoletimXlsx(req, res, next));
router.get('/boletim/:alunoId/json', (req, res, next) => impressaoController.exportarBoletimJson(req, res, next));

router.get('/recibo/:pagamentoId', (req, res, next) => impressaoController.gerarRecibo(req, res, next));
router.get('/ficha/:alunoId', (req, res, next) => impressaoController.gerarFichaAluno(req, res, next));

router.get('/declaracao/:alunoId', (req, res, next) => impressaoController.gerarDeclaracao(req, res, next));
router.get('/declaracao/:alunoId/xlsx', (req, res, next) => impressaoController.exportarDeclaracaoXlsx(req, res, next));
router.get('/declaracao/:alunoId/json', (req, res, next) => impressaoController.exportarDeclaracaoJson(req, res, next));

router.get('/certificado/:alunoId', (req, res, next) => impressaoController.gerarCertificado(req, res, next));
router.get('/certificado/:alunoId/xlsx', (req, res, next) => impressaoController.exportarCertificadoXlsx(req, res, next));
router.get('/certificado/:alunoId/json', (req, res, next) => impressaoController.exportarCertificadoJson(req, res, next));

router.get('/lote/turma/:turmaId', (req, res, next) => impressaoController.gerarLote(req, res, next));
router.get('/lote/turma/:turmaId/xlsx', (req, res, next) => impressaoController.exportarLoteXlsx(req, res, next));
router.get('/lote/turma/:turmaId/json', (req, res, next) => impressaoController.exportarLoteJson(req, res, next));

export default router;

