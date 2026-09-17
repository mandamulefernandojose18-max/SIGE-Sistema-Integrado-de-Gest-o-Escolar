import { Request, Response, NextFunction } from 'express';
import { dashboardService } from './dashboard.service';
import { sendSuccess } from '../../utils/response.util';

export class DashboardController {
  async getOverview(req: Request, res: Response, next: NextFunction) {
    try {
      const escolaId = req.tenant!.id;
      const data = await dashboardService.getOverview(escolaId);
      return sendSuccess(res, data, 'Visão geral do painel recuperada');
    } catch (error) {
      next(error);
    }
  }
}

export const dashboardController = new DashboardController();
