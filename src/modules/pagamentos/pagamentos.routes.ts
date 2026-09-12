import { Router } from 'express';
import { pagamentosController } from './pagamentos.controller';
import { authMiddleware } from '../../middlewares/auth.middleware';
import { tenantMiddleware } from '../../middlewares/tenant.middleware';
import { authorizeRoles } from '../../middlewares/rbac.middleware';

const router = Router();

router.use(authMiddleware, tenantMiddleware);
router.use(authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP', 'CHEFE_SECRETARIA', 'FINANCEIRO'));

router.get('/stats', (req, res, next) => pagamentosController.stats(req, res, next));
router.get('/', (req, res, next) => pagamentosController.list(req, res, next));
router.get('/:id', (req, res, next) => pagamentosController.getById(req, res, next));

router.post('/', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'FINANCEIRO'), (req, res, next) => pagamentosController.create(req, res, next));
router.post('/gerar-turma', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'FINANCEIRO'), (req, res, next) => pagamentosController.gerarTurma(req, res, next));
router.post('/:id/liquidar', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'FINANCEIRO'), (req, res, next) => pagamentosController.liquidar(req, res, next));

export default router;
