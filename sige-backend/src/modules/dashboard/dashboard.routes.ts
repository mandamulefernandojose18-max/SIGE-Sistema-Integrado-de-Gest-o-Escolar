import { Router } from 'express';
import { dashboardController } from './dashboard.controller';
import { authMiddleware } from '../../middlewares/auth.middleware';
import { tenantMiddleware } from '../../middlewares/tenant.middleware';

const router = Router();

router.use(authMiddleware, tenantMiddleware);

router.get('/overview', (req, res, next) => dashboardController.getOverview(req, res, next));

export default router;
