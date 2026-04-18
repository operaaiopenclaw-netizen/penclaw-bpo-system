// ============================================================
// SUPPLIER INTELLIGENCE ENGINE — Historical scoring & ranking
// ============================================================
import { prisma } from "../db";
import { logger } from "../utils/logger";
import { SupplierScore, RankedSupplier } from "./types";

// Scoring weight matrix — must sum to 1.0
const WEIGHTS = {
  deliveryReliability: 0.40,
  priceCompetitiveness: 0.30,
  stockReliability: 0.20,
  responsiveness: 0.10, // placeholder until response-time tracking is added
};

// Penalty per percentage point of price increase (used to penalise suppliers
// whose prices have risen above market neutral).
const PRICE_TREND_PENALTY = 2.0;

// Neutral score for new suppliers with no order history (fair entry point)
const NEUTRAL_SCORE = 75;

export class SupplierIntelligenceEngine {
  /**
   * Score a single supplier using all available purchase order history.
   */
  async scoreSupplier(supplierId: string): Promise<SupplierScore> {
    const [supplier, orders] = await Promise.all([
      prisma.supplier.findUnique({ where: { id: supplierId } }),
      prisma.purchaseOrder.findMany({
        where: { supplierId },
        include: { items: { select: { category: true, status: true } } },
        orderBy: { createdAt: "desc" },
        take: 60,
      }),
    ]);

    if (!supplier) throw new Error(`Supplier not found: ${supplierId}`);

    const total = orders.length;
    const delivered = orders.filter(o => o.status === "delivered");
    const cancelled = orders.filter(o => o.status === "cancelled");

    // On-time calculation
    const onTime = delivered.filter(o => {
      if (!o.confirmedDelivery || !o.actualDelivery) return true; // unknown = assume ok
      return o.actualDelivery <= o.confirmedDelivery;
    });
    const late = delivered.length - onTime.length;

    const deliveryReliability =
      delivered.length > 0
        ? (onTime.length / delivered.length) * 100
        : NEUTRAL_SCORE;

    const delayRate =
      delivered.length > 0 ? late / delivered.length : 0;

    // Stock reliability = (total - cancelled) / total
    const stockReliability =
      total > 0
        ? ((total - cancelled.length) / total) * 100
        : NEUTRAL_SCORE;

    // Price trend
    const priceTrend = computePriceTrend(orders);

    // Price competitiveness score: 100 when priceTrend <= 0, penalised above 0
    const priceScore = Math.max(
      0,
      100 - Math.max(0, priceTrend) * PRICE_TREND_PENALTY
    );

    // Category-level delivery performance
    const categoryPerformance = computeCategoryPerformance(orders);

    // Weighted final score
    const finalScore =
      WEIGHTS.deliveryReliability * deliveryReliability +
      WEIGHTS.priceCompetitiveness * priceScore +
      WEIGHTS.stockReliability * stockReliability +
      WEIGHTS.responsiveness * NEUTRAL_SCORE; // uses neutral until real data arrives

    const recommendation: SupplierScore["recommendation"] =
      total === 0
        ? "unrated"
        : finalScore >= 80
        ? "preferred"
        : finalScore >= 60
        ? "acceptable"
        : "avoid";

    logger.debug("SupplierIntelligence: scored", {
      supplierId,
      finalScore: round1(finalScore),
      recommendation,
    });

    return {
      supplierId,
      supplierName: supplier.name,
      categories: supplier.categories,
      priceTrend: round2(priceTrend),
      deliveryReliability: round1(deliveryReliability),
      stockReliability: round1(stockReliability),
      delayRate: round3(delayRate),
      categoryPerformance,
      finalScore: round1(finalScore),
      totalOrders: total,
      lastOrderDate: orders[0]?.createdAt ?? null,
      recommendation,
    };
  }

  /**
   * Rank all active suppliers for a given item category.
   */
  async rankSuppliersForItem(
    tenantId: string,
    itemCategory: string
  ): Promise<RankedSupplier[]> {
    const suppliers = await prisma.supplier.findMany({
      where: {
        tenantId,
        isActive: true,
        categories: { has: itemCategory },
      },
      select: { id: true },
    });

    if (suppliers.length === 0) return [];

    const scored = await Promise.all(
      suppliers.map(s => this.scoreSupplier(s.id))
    );

    return scored
      .sort((a, b) => b.finalScore - a.finalScore)
      .map((score, idx) => ({
        ...score,
        rankPosition: idx + 1,
        reasonsRanked: buildRankingReasons(score, idx),
      }));
  }

  /**
   * Score all active suppliers for a tenant (in parallel).
   */
  async getAllSupplierScores(tenantId: string): Promise<SupplierScore[]> {
    const suppliers = await prisma.supplier.findMany({
      where: { tenantId, isActive: true },
      select: { id: true },
    });

    if (suppliers.length === 0) return [];

    return Promise.all(suppliers.map(s => this.scoreSupplier(s.id)));
  }
}

// ---- Private helpers (module-level, not class members) ----

function computePriceTrend(orders: Array<{
  createdAt: Date;
  totalActualCost: number | null;
  totalEstimatedCost: number | null;
}>): number {
  if (orders.length < 4) return 0;

  const sorted = [...orders].sort(
    (a, b) => a.createdAt.getTime() - b.createdAt.getTime()
  );
  const half = Math.floor(sorted.length / 2);
  const older = sorted.slice(0, half);
  const recent = sorted.slice(half);

  const avgCost = (grp: typeof sorted) => {
    const vals = grp
      .map(o => o.totalActualCost ?? o.totalEstimatedCost ?? 0)
      .filter(v => v > 0);
    return vals.length > 0 ? vals.reduce((s, v) => s + v, 0) / vals.length : 0;
  };

  const oldAvg = avgCost(older);
  const recentAvg = avgCost(recent);
  if (oldAvg === 0) return 0;

  return ((recentAvg - oldAvg) / oldAvg) * 100;
}

function computeCategoryPerformance(
  orders: Array<{ status: string; items: Array<{ category: string | null; status: string }> }>
): Record<string, number> {
  const perf: Record<string, { total: number; delivered: number }> = {};

  for (const order of orders) {
    for (const item of order.items) {
      const cat = item.category ?? "general";
      if (!perf[cat]) perf[cat] = { total: 0, delivered: 0 };
      perf[cat].total++;
      if (order.status === "delivered") perf[cat].delivered++;
    }
  }

  return Object.fromEntries(
    Object.entries(perf).map(([cat, { total, delivered }]) => [
      cat,
      total > 0 ? Math.round((delivered / total) * 100) : NEUTRAL_SCORE,
    ])
  );
}

function buildRankingReasons(score: SupplierScore, rank: number): string[] {
  const reasons: string[] = [];
  if (rank === 0) reasons.push("Melhor pontuação geral nesta categoria");
  if (score.deliveryReliability >= 90)
    reasons.push(`Alta confiabilidade de entrega: ${score.deliveryReliability}%`);
  if (score.priceTrend < -5)
    reasons.push(`Preços em queda: ${score.priceTrend.toFixed(1)}%`);
  if (score.stockReliability >= 90)
    reasons.push(`Alta disponibilidade: ${score.stockReliability}%`);
  if (score.totalOrders === 0)
    reasons.push("Sem histórico — avaliação neutra (elegível para trial)");
  if (score.recommendation === "preferred")
    reasons.push("Classificado como fornecedor preferencial");
  return reasons;
}

function round1(n: number) { return Math.round(n * 10) / 10; }
function round2(n: number) { return Math.round(n * 100) / 100; }
function round3(n: number) { return Math.round(n * 1000) / 1000; }

export const supplierIntelligence = new SupplierIntelligenceEngine();
