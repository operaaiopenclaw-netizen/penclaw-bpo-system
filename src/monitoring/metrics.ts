import { FastifyInstance } from "fastify";
import { prisma } from "../db";
import { logger } from "../utils/logger";

interface SystemMetrics {
  timestamp: string;
  health: {
    api: "up" | "down";
    database: "up" | "down";
  };
  runs: {
    total: number;
    completed: number;
    failed: number;
    pending: number;
  };
  performance: {
    avgLatency: number;
    p95Latency: number;
    p99Latency: number;
  };
  tools: {
    totalCalls: number;
    successRate: number;
  };
}

export async function getMetrics(): Promise<SystemMetrics> {
  const now = new Date().toISOString();
  
  // Check database health
  let dbHealth: "up" | "down" = "up";
  try {
    await prisma.$queryRaw`SELECT 1`;
  } catch (error) {
    dbHealth = "down";
    logger.error("Database health check failed", { error });
  }
  
  // Get run stats
  const runStats = await prisma.agentRun.groupBy({
    by: ["status"],
    _count: { id: true },
  });
  
  const statusCounts = runStats.reduce((acc, stat) => {
    acc[stat.status] = stat._count.id;
    return acc;
  }, {} as Record<string, number>);
  
  // Get latency metrics
  const recentRuns = await prisma.agentRun.findMany({
    where: { latencyMs: { not: null } },
    orderBy: { createdAt: "desc" },
    take: 100,
    select: { latencyMs: true },
  });
  
  const latencies = recentRuns.map(r => r.latencyMs || 0).sort((a, b) => a - b);
  const avgLatency = latencies.length > 0 
    ? latencies.reduce((a, b) => a + b, 0) / latencies.length 
    : 0;
  const p95Latency = latencies[Math.floor(latencies.length * 0.95)] || 0;
  const p99Latency = latencies[Math.floor(latencies.length * 0.99)] || 0;
  
  // Tool call stats (would be from a real table)
  const totalCalls = await prisma.toolCall.count();
  const successfulCalls = await prisma.toolCall.count({
    where: { status: "completed" },
  });
  const successRate = totalCalls > 0 ? (successfulCalls / totalCalls) * 100 : 100;
  
  return {
    timestamp: now,
    health: {
      api: "up",
      database: dbHealth,
    },
    runs: {
      total: await prisma.agentRun.count(),
      completed: statusCounts["completed"] || 0,
      failed: statusCounts["failed"] || 0,
      pending: statusCounts["pending"] || 0,
    },
    performance: {
      avgLatency: Math.round(avgLatency * 100) / 100,
      p95Latency,
      p99Latency,
    },
    tools: {
      totalCalls,
      successRate: Math.round(successRate * 100) / 100,
    },
  };
}

export async function setupMetricsRoute(app: FastifyInstance) {
  app.get("/metrics", async (request, reply) => {
    const metrics = await getMetrics();
    return { success: true, data: metrics };
  });
  
  // Health check endpoint
  app.get("/health/detailed", async (request, reply) => {
    const metrics = await getMetrics();
    const isHealthy = metrics.health.api === "up" && metrics.health.database === "up";
    
    return {
      status: isHealthy ? "healthy" : "unhealthy",
      version: "1.0.0",
      timestamp: new Date().toISOString(),
      checks: {
        database: metrics.health.database,
        api: metrics.health.api,
      },
      metrics,
    };
  });
}
