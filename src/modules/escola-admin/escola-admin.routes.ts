import { Router } from 'express';
import { escolaAdminController } from './escola-admin.controller';
import { authMiddleware } from '../../middlewares/auth.middleware';
import { tenantMiddleware } from '../../middlewares/tenant.middleware';
import { authorizeRoles } from '../../middlewares/rbac.middleware';

const router = Router();

// Todas as rotas requerem autenticação e validação do tenant (HTTP 402 se expirada)
router.use(authMiddleware, tenantMiddleware);

router.get('/info', (req, res, next) => escolaAdminController.getInfo(req, res, next));
router.put('/info', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA'), (req, res, next) => escolaAdminController.updateInfo(req, res, next));

router.get('/turmas', (req, res, next) => escolaAdminController.listTurmas(req, res, next));
router.post('/turmas', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'), (req, res, next) => escolaAdminController.createTurma(req, res, next));
router.put('/turmas/:id', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'), (req, res, next) => escolaAdminController.updateTurma(req, res, next));
router.delete('/turmas/:id', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA'), (req, res, next) => escolaAdminController.deleteTurma(req, res, next));
router.get('/turmas/stats', (req, res, next) => escolaAdminController.getStats(req, res, next));

router.get('/administrativos', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP', 'CHEFE_SECRETARIA'), (req, res, next) => escolaAdminController.listAdministrativos(req, res, next));
router.post('/administrativos', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA'), (req, res, next) => escolaAdminController.createAdministrativo(req, res, next));

export default router;
