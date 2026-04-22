import { FastifyReply, FastifyRequest } from "fastify";
import { dashboardService } from "../services/dashboard-service";
import { AppError } from "../utils/app-error";

export class DashboardController {
  /**
   * CEO Dashboard
   */
  async ceo(request: FastifyRequest<{ Querystring: { companyId?: string } }>, reply: FastifyReply) {
    try {
      const companyId = (request.query as { companyId?: string }).companyId || "default";
      const result = await dashboardService.ceo(companyId as string);

      return reply.status(200).send({
        success: true,
        type: "ceo",
        data: result
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Dashboard failed";
      throw new AppError(message, 500, "DASHBOARD_ERROR");
    }
  }

  /**
   * Commercial Dashboard
   */
  async commercial(request: FastifyRequest<{ Querystring: { companyId?: string } }>, reply: FastifyReply) {
    try {
      const companyId = (request.query as { companyId?: string }).companyId || "default";
      const result = await dashboardService.commercial(companyId as string);

      return reply.status(200).send({
        success: true,
        type: "commercial",
        data: result
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Dashboard failed";
      throw new AppError(message, 500, "DASHBOARD_ERROR");
    }
  }

  /**
   * Finance Dashboard
   */
  async finance(request: FastifyRequest<{ Querystring: { companyId?: string } }>, reply: FastifyReply) {
    try {
      const companyId = (request.query as { companyId?: string }).companyId || "default";
      const result = await dashboardService.finance(companyId as string);

      return reply.status(200).send({
        success: true,
        type: "finance",
        data: result
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Dashboard failed";
      throw new AppError(message, 500, "DASHBOARD_ERROR");
    }
  }

  /**
   * Operations Dashboard
   */
  async operations(request: FastifyRequest<{ Querystring: { companyId?: string } }>, reply: FastifyReply) {
    try {
      const companyId = (request.query as { companyId?: string }).companyId || "default";
      const result = await dashboardService.operations(companyId as string);

      return reply.status(200).send({
        success: true,
        type: "operations",
        data: result
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Dashboard failed";
      throw new AppError(message, 500, "DASHBOARD_ERROR");
    }
  }
}

// Singleton
export const dashboardController = new DashboardController();
