import { Router } from 'express';
import { pautasController } from './pautas.controller';
import { authMiddleware } from '../../middlewares/auth.middleware';
import { tenantMiddleware } from '../../middlewares/tenant.middleware';
import { authorizeRoles } from '../../middlewares/rbac.middleware';

const router = Router();

router.use(authMiddleware, tenantMiddleware);

router.get('/turma/:turmaId/completa', (req, res, next) => pautasController.getPautaTurmaCompleta(req, res, next));
router.get('/turma/:turmaId/acta', (req, res, next) => pautasController.getActaTurma(req, res, next));
router.get('/turma/:turmaId/export-xlsx', (req, res, next) => pautasController.exportarPautaTurmaXlsx(req, res, next));
router.get('/turma/:turmaId/acta-xlsx', (req, res, next) => pautasController.exportarActaTurmaXlsx(req, res, next));

router.get('/stats', (req, res, next) => pautasController.stats(req, res, next));
router.get('/', (req, res, next) => pautasController.list(req, res, next));
router.get('/:id', (req, res, next) => pautasController.getById(req, res, next));
router.get('/:id/export-xlsx', (req, res, next) => pautasController.exportarPautaXlsx(req, res, next));
router.get('/:id/acta-xlsx', (req, res, next) => pautasController.exportarActaXlsx(req, res, next));

router.post('/gerar', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP', 'CHEFE_SECRETARIA', 'PROFESSOR'), (req, res, next) => pautasController.gerar(req, res, next));
router.patch('/:id/status', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'), (req, res, next) => pautasController.alterarStatus(req, res, next));

export default router;
