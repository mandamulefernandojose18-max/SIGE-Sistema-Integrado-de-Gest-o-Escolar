import { Router } from 'express';
import { saasAdminController } from './saas-admin.controller';
import { authMiddleware } from '../../middlewares/auth.middleware';
import { authorizeRoles } from '../../middlewares/rbac.middleware';

const router = Router();

// Rota para a própria escola obter comprovativo de contrato
router.get('/minha-escola/comprovativo-contrato', authMiddleware, (req, res, next) => saasAdminController.getComprovativoContrato(req, res, next));

// Todas as rotas do SaaS Admin abaixo exigem SUPERADMIN
router.use(authMiddleware, authorizeRoles('SUPERADMIN'));

router.get('/metrics', (req, res, next) => saasAdminController.getMetrics(req, res, next));
router.get('/escolas', (req, res, next) => saasAdminController.listEscolas(req, res, next));
router.post('/escolas', (req, res, next) => saasAdminController.createEscola(req, res, next));
router.put('/escolas/:id', (req, res, next) => saasAdminController.updateEscola(req, res, next));
router.delete('/escolas/:id', (req, res, next) => saasAdminController.deleteEscola(req, res, next));
router.patch('/escolas/:id/toggle-status', (req, res, next) => saasAdminController.toggleStatus(req, res, next));
router.post('/escolas/:id/renovar', (req, res, next) => saasAdminController.renovarAssinatura(req, res, next));
router.get('/escolas/:id/comprovativo-contrato', (req, res, next) => saasAdminController.getComprovativoContrato(req, res, next));

router.get('/planos', (req, res, next) => saasAdminController.listPlanos(req, res, next));
router.put('/planos/:id/preco', (req, res, next) => saasAdminController.updatePrecoPlano(req, res, next));

router.post('/verificar-expiracoes', (req, res, next) => saasAdminController.verificarExpiracoes(req, res, next));

export default router;
