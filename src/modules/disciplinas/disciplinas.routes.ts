import { Router } from 'express';
import { disciplinasController } from './disciplinas.controller';
import { authMiddleware } from '../../middlewares/auth.middleware';
import { tenantMiddleware } from '../../middlewares/tenant.middleware';
import { authorizeRoles } from '../../middlewares/rbac.middleware';

const router = Router();

router.use(authMiddleware, tenantMiddleware);

router.get('/stats', (req, res, next) => disciplinasController.stats(req, res, next));
router.get('/', (req, res, next) => disciplinasController.list(req, res, next));
router.get('/:id', (req, res, next) => disciplinasController.getById(req, res, next));
router.post('/', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA'), (req, res, next) => disciplinasController.create(req, res, next));
router.put('/:id', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA'), (req, res, next) => disciplinasController.update(req, res, next));
router.delete('/:id', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA'), (req, res, next) => disciplinasController.delete(req, res, next));

export default router;
