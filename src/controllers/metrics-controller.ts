import { FastifyReply, FastifyRequest } from "fastify";
import { metricsService } from "../services/metrics-service";

export class MetricsController {
  /**
   * GET /metrics - Visão geral
   */
  async getAll(req: FastifyRequest, reply: FastifyReply) {
    const { companyId, days } = req.query as { companyId?: string; days?: string };
    const periodDays = days ? parseInt(days) : 7;

    try {
      const [runs, steps, health] = await Promise.all([
        metricsService.getRunMetrics(companyId, periodDays),
        metricsService.getStepMetrics(companyId, periodDays),
        metricsService.getHealth()
      ]);

      return reply.send({
        success: true,
        period: `${periodDays}d`,
        runs: {
          total: runs.total,
          byStatus: runs.byStatus,
          avgDurationMs: runs.avgDurationMs,
          recent24h: runs.recentRuns
        },
        steps: {
          total: steps.total,
          byAgent: steps.byAgent,
          avgLatencyMs: steps.avgLatencyMs
        },
        health
      });
    } catch (error: any) {
      return reply.status(500).send({
        error: "Metrics failed",
        message: error?.message
      });
    }
  }

  /**
   * GET /metrics/runs
   */
  async getRuns(req: FastifyRequest, reply: FastifyReply) {
    const { companyId, days } = req.query as { companyId?: string; days?: string };
    
    try {
      const runs = await metricsService.getRunMetrics(
        companyId, 
        days ? parseInt(days) : 7
      );
      return reply.send({ success: true, data: runs });
    } catch (error: any) {
      return reply.status(500).send({ error: error?.message });
    }
  }

  /**
   * GET /metrics/steps
   */
  async getSteps(req: FastifyRequest, reply: FastifyReply) {
    const { companyId, days } = req.query as { companyId?: string; days?: string };
    
    try {
      const steps = await metricsService.getStepMetrics(
        companyId,
        days ? parseInt(days) : 7
      );
      return reply.send({ success: true, data: steps });
    } catch (error: any) {
      return reply.status(500).send({ error: error?.message });
    }
  }

  /**
   * GET /metrics/health
   */
  async getHealth(req: FastifyRequest, reply: FastifyReply) {
    try {
      const health = await metricsService.getHealth();
      return reply.send({ success: true, data: health });
    } catch (error: any) {
      return reply.status(500).send({ error: error?.message });
    }
  }
}

export const metricsController = new MetricsController();
