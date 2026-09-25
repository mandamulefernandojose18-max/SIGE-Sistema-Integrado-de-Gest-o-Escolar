import { Router } from 'express';
import { certificadosController } from './certificados.controller';
import { authMiddleware } from '../../middlewares/auth.middleware';
import { tenantMiddleware } from '../../middlewares/tenant.middleware';
import { authorizeRoles } from '../../middlewares/rbac.middleware';

const router = Router();

// Rota pública de verificação por QR Code (aberta para qualquer pessoa ou instituição)
router.get('/verificar/:codigo', (req, res, next) => certificadosController.verificarPublico(req, res, next));

// Rotas autenticadas da escola
router.use(authMiddleware, tenantMiddleware);

router.get('/stats', (req, res, next) => certificadosController.stats(req, res, next));
router.get('/', (req, res, next) => certificadosController.list(req, res, next));
router.get('/:id', (req, res, next) => certificadosController.getById(req, res, next));
router.post('/', authorizeRoles('SUPERADMIN', 'ADMIN_ESCOLA'), (req, res, next) => certificadosController.emitir(req, res, next));

export default router;
