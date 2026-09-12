import { Router } from 'express';
import { impressaoController } from './impressao.controller';
import { authMiddleware } from '../../middlewares/auth.middleware';
import { tenantMiddleware } from '../../middlewares/tenant.middleware';

const router = Router();

router.use(authMiddleware, tenantMiddleware);

router.get('/stats', (req, res, next) => impressaoController.stats(req, res, next));
router.get('/boletim/:alunoId', (req, res, next) => impressaoController.gerarBoletim(req, res, next));
router.get('/recibo/:pagamentoId', (req, res, next) => impressaoController.gerarRecibo(req, res, next));
router.get('/ficha/:alunoId', (req, res, next) => impressaoController.gerarFichaAluno(req, res, next));
router.get('/declaracao/:alunoId', (req, res, next) => impressaoController.gerarDeclaracao(req, res, next));
router.get('/certificado/:alunoId', (req, res, next) => impressaoController.gerarCertificado(req, res, next));
router.get('/lote/turma/:turmaId', (req, res, next) => impressaoController.gerarLote(req, res, next));

export default router;
