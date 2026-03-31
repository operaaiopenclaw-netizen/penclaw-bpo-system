import { prisma } from "../db";
import { logger } from "../utils/logger";

export class DashboardService {
  /**
   * CEO Dashboard metrics
   */
  async ceo(companyId: string) {
    logger.info("DashboardService: CEO metrics", { companyId });

    const runs = await prisma.agentRun.findMany({
      where: { companyId },
      orderBy: { createdAt: "desc" },
      take: 50
    });

    return {
      totalRuns: runs.length,
      completedRuns: runs.filter(r => r.status === "completed").length,
      failedRuns: runs.filter(r => r.status === "failed").length,
      waitingApproval: runs.filter(r => r.status === "waiting_approval").length,
      totalCost: runs.reduce((acc, item) => acc + (item.totalCost || 0), 0)
    };
  }

  /**
   * Commercial Dashboard metrics
   */
  async commercial(companyId: string) {
    logger.info("DashboardService: commercial metrics", { companyId });

    const events = await prisma.event.findMany({
      where: { companyId },
      orderBy: { createdAt: "desc" },
      take: 50
    });

    const completed = events.filter(e => e.status === "completed").length;

    return {
      totalEvents: events.length,
      completedEvents: completed,
      pendingEvents: events.filter(e => e.status === "pending").length,
      averageMargin: completed > 0 
        ? events.filter(e => e.marginPct).reduce((acc, e) => acc + (e.marginPct || 0), 0) / completed 
        : 0
    };
  }

  /**
   * Finance Dashboard metrics
   */
  async finance(companyId: string) {
    logger.info("DashboardService: finance metrics", { companyId });

    const events = await prisma.event.findMany({
      where: { companyId, status: "completed" },
      take: 100
    });

    const totalRevenue = events.reduce((acc, e) => acc + (e.revenueTotal || 0), 0);
    const totalCMV = events.reduce((acc, e) => acc + (e.cmvTotal || 0), 0);

    return {
      totalRevenue,
      totalCMV,
      totalProfit: totalRevenue - totalCMV,
      averageMargin: totalRevenue > 0 ? ((totalRevenue - totalCMV) / totalRevenue) * 100 : 0
    };
  }

  /**
   * Operations Dashboard metrics
   */
  async operations(companyId: string) {
    logger.info("DashboardService: operations metrics", { companyId });

    const runs = await prisma.agentRun.findMany({
      where: { companyId, Status: "running" as any },
      take: 20
    });

    return {
      activeRuns: runs.length,
      averageLatency: runs.length > 0 
        ? runs.reduce((acc, r) => acc + (r.latencyMs || 0), 0) / runs.length 
        : 0,
      totalTokens: runs.reduce((acc, r) => acc + (r.totalTokens || 0), 0)
    };
  }
}

// Singleton
export const dashboardService = new DashboardService();
