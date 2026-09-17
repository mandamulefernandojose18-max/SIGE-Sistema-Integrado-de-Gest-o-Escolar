import { Router } from 'express';
import { authController } from './auth.controller';
import { authMiddleware } from '../../middlewares/auth.middleware';

const router = Router();

router.post('/login', (req, res, next) => authController.login(req, res, next));
router.post('/refresh', (req, res, next) => authController.refresh(req, res, next));
router.post('/logout', (req, res, next) => authController.logout(req, res, next));

router.get('/me', authMiddleware, (req, res, next) => authController.me(req, res, next));
router.get('/stats', authMiddleware, (req, res, next) => authController.stats(req, res, next));

export default router;
