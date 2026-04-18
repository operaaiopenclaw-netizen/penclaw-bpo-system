// ============================================================
// GAP ENGINE — Demand vs Free Stock (accounting for reservations)
// ============================================================
import { prisma } from "../db";
import { logger } from "../utils/logger";
import { ConsumptionForecast } from "./types";
import type { GapAnalysisResult, StockGap, GapSeverity, OverallRisk } from "./types";

// Safety multiplier applied on top of maxConsumption
const SAFETY_FACTOR = 1.2;

export class GapEngine {
  /**
   * Analyse stock gaps for a specific event.
   * Considers committed reservations from other events to compute free stock.
   */
  async analyse(
    tenantId: string,
    forecasts: ConsumptionForecast[],
    eventType: string,
    guestCount: number,
    eventId?: string,
    requiredBy?: Date
  ): Promise<GapAnalysisResult> {
    const [inventoryItems, reservations] = await Promise.all([
      prisma.inventoryItem.findMany(),
      this.fetchCommittedReservations(tenantId, eventId, requiredBy)
    ]);

    const items: StockGap[] = forecasts.map(fc =>
      this.computeGap(fc, inventoryItems, reservations)
    );

    const shortages = items.filter(i => i.gap > 0);
    const critical = items.filter(i => i.severity === "CRITICAL");
    const estimatedTotalProcurementCost = items.reduce((s, i) => s + i.estimatedGapCost, 0);

    return {
      eventId,
      eventType,
      guestCount,
      analysisDate: new Date(),
      items,
      summary: {
        totalItems: items.length,
        sufficient: items.length - shortages.length,
        shortages: shortages.length,
        critical: critical.length,
        estimatedTotalProcurementCost: round2(estimatedTotalProcurementCost)
      },
      overallRisk: this.computeOverallRisk(critical.length, shortages.length)
    };
  }

  private computeGap(
    fc: ConsumptionForecast,
    inventory: Array<{ code: string; name: string; currentQty: number; unit: string; unitPrice: number | null }>,
    reservations: Map<string, number>
  ): StockGap {
    const inv = inventory.find(
      i => i.code.toLowerCase().includes(fc.itemCode) || i.name.toLowerCase().includes(fc.itemCode)
    );

    const available = inv?.currentQty ?? 0;
    const committed = reservations.get(fc.itemCode) ?? 0;
    const free = Math.max(0, available - committed);
    const needed = round2(fc.maxConsumption * SAFETY_FACTOR);
    const gap = Math.max(0, round2(needed - free));
    const coverageRatio = needed > 0 ? round3(free / needed) : 1;
    const unitPrice = inv?.unitPrice ?? 0;

    return {
      itemCode: inv?.code ?? fc.itemCode,
      itemName: inv?.name ?? fc.itemName,
      category: fc.category,
      unit: fc.unit,
      needed,
      available,
      committed,
      free,
      gap,
      coverageRatio,
      severity: this.computeSeverity(coverageRatio, gap),
      unitPrice,
      estimatedGapCost: round2(gap * unitPrice)
    };
  }

  private computeSeverity(coverageRatio: number, gap: number): GapSeverity {
    if (gap === 0) return "OK";
    if (coverageRatio < 0.10) return "CRITICAL";
    if (coverageRatio < 0.30) return "HIGH";
    if (coverageRatio < 0.60) return "MEDIUM";
    return "LOW";
  }

  private computeOverallRisk(criticalCount: number, shortageCount: number): OverallRisk {
    if (criticalCount > 0) return "CRITICAL";
    if (shortageCount > 4) return "HIGH";
    if (shortageCount > 1) return "MEDIUM";
    if (shortageCount > 0) return "LOW";
    return "LOW";
  }

  private async fetchCommittedReservations(
    tenantId: string,
    excludeEventId?: string,
    requiredBy?: Date
  ): Promise<Map<string, number>> {
    const result = new Map<string, number>();
    try {
      const where: Record<string, unknown> = {
        tenantId,
        status: { in: ["PENDING", "CONFIRMED"] }
      };
      if (excludeEventId) where.eventId = { not: excludeEventId };
      if (requiredBy) where.requiredBy = { lte: requiredBy };

      const reservations = await prisma.inventoryReservation.findMany({
        where,
        select: { productId: true, quantityReserved: true }
      });

      for (const r of reservations) {
        const current = result.get(r.productId) ?? 0;
        result.set(r.productId, current + r.quantityReserved);
      }
    } catch (err) {
      logger.warn("GapEngine: could not fetch reservations", { error: err });
    }
    return result;
  }
}

function round2(n: number) { return Math.round(n * 100) / 100; }
function round3(n: number) { return Math.round(n * 1000) / 1000; }

export const gapEngine = new GapEngine();
