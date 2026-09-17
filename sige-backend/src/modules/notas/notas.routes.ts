import { Router } from 'express';
import { notasController } from './notas.controller';
import { authMiddleware } from '../../middlewares/auth.middleware';
import { tenantMiddleware } from '../../middlewares/tenant.middleware';
import { authorizeRoles } from '../../middlewares/rbac.middleware';

const router = Router();

router.use(authMiddleware, tenantMiddleware);

router.get('/stats', (req, res, next) => notasController.stats(req, res, next));
router.get('/', (req, res, next) => notasController.list(req, res, next));
router.post('/', authorizeRoles('SUPERADMIN', 'PROFESSOR'), (req, res, next) => notasController.lancar(req, res, next));
router.post('/lote', authorizeRoles('SUPERADMIN', 'PROFESSOR'), (req, res, next) => notasController.lancarLote(req, res, next));
router.post('/autorizar-desbloqueio', authorizeRoles('SUPERADMIN', 'DIRECTOR_ESCOLA', 'DAP'), (req, res, next) => notasController.autorizarDesbloqueio(req, res, next));

export default router;
