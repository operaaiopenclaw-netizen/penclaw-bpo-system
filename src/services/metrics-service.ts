/**
 * Metrics Service - Visibilidade do sistema
 */

import { prisma } from "../db";

export type RunMetrics = {
  total: number;
  byStatus: Record<string, number>;
  avgDurationMs?: number;
  recentRuns: number;
};

export type StepMetrics = {
  total: number;
  byAgent: Record<string, number>;
  avgLatencyMs?: number;
};

export class MetricsService {
  /**
   * Métricas de runs
   */
  async getRunMetrics(companyId?: string, days = 7): Promise<RunMetrics> {
    const since = new Date();
    since.setDate(since.getDate() - days);

    const where = companyId 
      ? { companyId, createdAt: { gte: since } }
      : { createdAt: { gte: since } };

    const [total, byStatus, recent, withDuration] = await Promise.all([
      prisma.agentRun.count({ where }),
      prisma.agentRun.groupBy({
        by: ["status"],
        where,
        _count: { id: true }
      }),
      prisma.agentRun.count({
        where: {
          ...where,
          createdAt: { gte: new Date(Date.now() - 24 * 60 * 60 * 1000) }
        }
      }),
      prisma.agentRun.findMany({
        where: {
          ...where,
          status: { in: ["completed", "failed"] },
          startedAt: { not: null },
          finishedAt: { not: null }
        },
        select: {
          startedAt: true,
          finishedAt: true
        },
        take: 100
      })
    ]);

    // Calcular duração média
    const durations = withDuration
      .filter(r => r.startedAt && r.finishedAt)
      .map(r => new Date(r.finishedAt!).getTime() - new Date(r.startedAt!).getTime());

    const avgDuration = durations.length > 0
      ? durations.reduce((a, b) => a + b, 0) / durations.length
      : undefined;

    const statusMap = byStatus.reduce((acc, s) => {
      acc[s.status] = s._count.id;
      return acc;
    }, {} as Record<string, number>);

    return {
      total,
      byStatus: statusMap,
      avgDurationMs: avgDuration,
      recentRuns: recent
    };
  }

  /**
   * Métricas de steps
   */
  async getStepMetrics(companyId?: string, days = 7): Promise<StepMetrics> {
    const since = new Date();
    since.setDate(since.getDate() - days);

    const where: any = {
      startedAt: { gte: since }
    };

    if (companyId) {
      where.agentRun = { companyId };
    }

    const [total, byAgent, withLatency] = await Promise.all([
      prisma.agentStep.count({ where }),
      prisma.agentStep.groupBy({
        by: ["agentName"],
        where,
        _count: { id: true }
      }),
      prisma.agentStep.findMany({
        where: {
          ...where,
          status: { in: ["completed", "failed"] },
          finishedAt: { not: null },
          startedAt: { not: null }
        },
        select: {
          startedAt: true,
          finishedAt: true,
          agentName: true
        },
        take: 200
      })
    ]);

    // Latência por agente
    const latencies = withLatency
      .filter(s => s.startedAt && s.finishedAt)
      .map(s => ({
        agent: s.agentName,
        latency: new Date(s.finishedAt!).getTime() - new Date(s.startedAt!).getTime()
      }));

    const avgLatency = latencies.length > 0
      ? latencies.reduce((a, b) => a + b.latency, 0) / latencies.length
      : undefined;

    const agentMap = byAgent.reduce((acc, a) => {
      acc[a.agentName] = (acc[a.agentName] || 0) + a._count.id;
      return acc;
    }, {} as Record<string, number>);

    // Agregar por agente nas latências
    const byAgentLatency: Record<string, { count: number; avg: number }> = {};
    latencies.forEach(l => {
      if (!byAgentLatency[l.agent]) {
        byAgentLatency[l.agent] = { count: 0, avg: 0 };
      }
      byAgentLatency[l.agent].count++;
      byAgentLatency[l.agent].avg += l.latency;
    });

    Object.keys(byAgentLatency).forEach(agent => {
      byAgentLatency[agent].avg /= byAgentLatency[agent].count;
    });

    return {
      total,
      byAgent: agentMap,
      avgLatencyMs: avgLatency
    };
  }

  /**
   * Health check do sistema
   */
  async getHealth(): Promise<{
    database: "ok" | "error";
    queue: "ok" | "error";
    timestamp: number;
  }> {
    const timestamp = Date.now();

    let database: "ok" | "error" = "ok";
    try {
      await prisma.agentRun.count({ take: 1 });
    } catch {
      database = "error";
    }

    // Queue status via redis seria aqui
    const queue: "ok" | "error" = "ok";

    return { database, queue, timestamp };
  }
}

export const metricsService = new MetricsService();
