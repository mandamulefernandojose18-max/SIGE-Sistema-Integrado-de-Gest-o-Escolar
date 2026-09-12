import { Router } from 'express';
import { alunosController } from './alunos.controller';
import { authMiddleware } from '../../middlewares/auth.middleware';
import { tenantMiddleware } from '../../middlewares/tenant.middleware';
import { authorizeRoles } from '../../middlewares/rbac.middleware';

const router = Router();

router.use(authMiddleware, tenantMiddleware);

router.get('/perfil/me', (req, res, next) => alunosController.getMeuPerfil(req, res, next));
router.get('/me/notas', (req, res, next) => alunosController.getMinhasNotas(req, res, next));
router.get('/me/pagamentos', (req, res, next) => alunosController.getMeusPagamentos(req, res, next));
router.put('/perfil/me/filiacao', (req, res, next) => alunosController.updateMinhaFiliacao(req, res, next));
router.get('/stats', (req, res, next) => alunosController.stats(req, res, next));
router.get('/', (req, res, next) => alunosController.list(req, res, next));
router.get('/:id', (req, res, next) => alunosController.getById(req, res, next));
router.post('/', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP', 'CHEFE_SECRETARIA'), (req, res, next) => alunosController.create(req, res, next));
router.put('/:id', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP', 'CHEFE_SECRETARIA', 'ALUNO'), (req, res, next) => alunosController.update(req, res, next));
router.delete('/:id', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA'), (req, res, next) => alunosController.delete(req, res, next));

export default router;
