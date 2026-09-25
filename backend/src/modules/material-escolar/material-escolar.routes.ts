import { Router } from 'express';
import { materialEscolarController } from './material-escolar.controller';
import { authMiddleware } from '../../middlewares/auth.middleware';
import { tenantMiddleware } from '../../middlewares/tenant.middleware';
import { authorizeRoles } from '../../middlewares/rbac.middleware';

const router = Router();

router.use(authMiddleware, tenantMiddleware);

router.get('/classes', (req, res, next) => materialEscolarController.getClasses(req, res, next));
router.get('/', (req, res, next) => materialEscolarController.list(req, res, next));
router.get('/:id/download', (req, res, next) => materialEscolarController.download(req, res, next));
router.get('/:id', (req, res, next) => materialEscolarController.getById(req, res, next));

router.post(
  '/',
  authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP', 'CHEFE_SECRETARIA', 'PROFESSOR'),
  (req, res, next) => materialEscolarController.create(req, res, next)
);

router.delete(
  '/:id',
  authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP', 'CHEFE_SECRETARIA', 'PROFESSOR'),
  (req, res, next) => materialEscolarController.delete(req, res, next)
);

export default router;
