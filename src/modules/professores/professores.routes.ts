import { Router } from 'express';
import { professoresController } from './professores.controller';
import { authMiddleware } from '../../middlewares/auth.middleware';
import { tenantMiddleware } from '../../middlewares/tenant.middleware';
import { authorizeRoles } from '../../middlewares/rbac.middleware';

const router = Router();

router.use(authMiddleware, tenantMiddleware);

router.get('/minhas-turmas', authorizeRoles('PROFESSOR', 'SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'), (req, res, next) => professoresController.getMinhasTurmas(req, res, next));
router.get('/caderneta/:alocacaoId', authorizeRoles('PROFESSOR', 'SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'), (req, res, next) => professoresController.getCaderneta(req, res, next));
router.get('/caderneta/:alocacaoId/xlsx', authorizeRoles('PROFESSOR', 'SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'), (req, res, next) => professoresController.exportarCadernetaXlsx(req, res, next));

router.get('/stats', (req, res, next) => professoresController.stats(req, res, next));
router.get('/', (req, res, next) => professoresController.list(req, res, next));
router.get('/:id', (req, res, next) => professoresController.getById(req, res, next));
router.post('/', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'), (req, res, next) => professoresController.create(req, res, next));
router.put('/:id', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'), (req, res, next) => professoresController.update(req, res, next));
router.delete('/:id', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA'), (req, res, next) => professoresController.delete(req, res, next));

router.post('/alocar', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'), (req, res, next) => professoresController.alocar(req, res, next));
router.delete('/alocar/:id', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'), (req, res, next) => professoresController.desalocar(req, res, next));

export default router;
