import { Router } from 'express';
import { notasController } from './notas.controller';
import { authMiddleware } from '../../middlewares/auth.middleware';
import { tenantMiddleware } from '../../middlewares/tenant.middleware';
import { authorizeRoles } from '../../middlewares/rbac.middleware';

const router = Router();

router.use(authMiddleware, tenantMiddleware);

router.get('/stats', (req, res, next) => notasController.stats(req, res, next));
router.get('/prazos-trimestres', (req, res, next) => notasController.getPrazosTrimestrais(req, res, next));
router.post('/prazos-trimestres', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'), (req, res, next) => notasController.salvarPrazosTrimestrais(req, res, next));
router.get('/autorizacoes', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'), (req, res, next) => notasController.listarAutorizacoes(req, res, next));
router.delete('/autorizacoes/:id', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'), (req, res, next) => notasController.revogarAutorizacao(req, res, next));
router.get('/', (req, res, next) => notasController.list(req, res, next));
router.post('/', authorizeRoles('SUPERADMIN', 'PROFESSOR'), (req, res, next) => notasController.lancar(req, res, next));
router.post('/lote', authorizeRoles('SUPERADMIN', 'PROFESSOR'), (req, res, next) => notasController.lancarLote(req, res, next));
router.post('/autorizar-desbloqueio', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'), (req, res, next) => notasController.autorizarDesbloqueio(req, res, next));

export default router;
