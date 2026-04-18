// ============================================================
// RECONCILIATION ENGINE — Sprint 4
// forecast → execute → measure → learn → improve
// ============================================================
import { prisma } from "../db";
import { logger } from "../utils/logger";
import { forecastEngine } from "./forecast-engine";
import {
  ReconciliationReportResult,
  ReconciliationItem,
  ReconciliationFinancials,
  ReconciliationAccuracy,
  SupplierFeedbackUpdate,
  MemoryPatternEntry,
} from "./types";

// ---- Tuning parameters ----

// EWMA weight for the newest sample when updating ItemAdjustment
const LEARNING_ALPHA = 0.4;

// Clamp learned adjustment factor
const FACTOR_MIN = 0.5;
const FACTOR_MAX = 2.0;

// Memory heuristics
const DEVIATION_THRESHOLD_PCT = 0.25;    // |variance| > 25% → deviation
const RECURRING_DEVIATION_MIN = 3;       // same-sign variance N times → pattern
const INEFFICIENCY_WASTE_PCT = 0.15;     // waste/consumed > 15% → inefficiency

// Supplier feedback
const DELIVERY_WEIGHT = 0.6;
const QUANTITY_WEIGHT = 0.4;

export class ReconciliationEngine {
  /**
   * Reconcile a single event: compare forecast → purchased → consumed,
   * persist accuracy, update learned adjustments, update supplier scores,
   * write memory entries. Idempotent at the event level.
   */
  async reconcileEvent(
    tenantId: string,
    eventId: string
  ): Promise<ReconciliationReportResult> {
    const [event, consumptions, poItems] = await Promise.all([
      this.loadEvent(tenantId, eventId),
      prisma.eventConsumption.findMany({ where: { tenantId, eventId } }),
      this.loadPurchasedItems(tenantId, eventId),
    ]);

    if (!event) throw new Error(`Event not found for reconciliation: ${eventId}`);
    if (consumptions.length === 0)
      throw new Error(`No consumption records for event: ${eventId}`);

    const eventType = (event.eventType ?? "corporativo").toLowerCase();
    const guestCount = event.guests ?? 0;
    const durationHours = 6;

    // Raw forecast (no learned adjustments) — the comparison baseline
    const forecast = await forecastEngine.forecastEvent(
      tenantId,
      eventType,
      guestCount,
      durationHours,
      eventId,
      { useLearnedAdjustments: false }
    );

    // Price lookup from inventory
    const inventory = await prisma.inventoryItem.findMany({
      select: { code: true, name: true, unitPrice: true },
    });
    const priceFor = (itemCode: string): number => {
      const inv = inventory.find(
        i =>
          i.code.toLowerCase().includes(itemCode) ||
          i.name.toLowerCase().includes(itemCode)
      );
      return inv?.unitPrice ?? 0;
    };

    // Index for merges
    const forecastByCode = new Map(
      forecast.forecasts.map(f => [f.itemCode, f])
    );
    const purchasedByCode = aggregateByCode(poItems, "quantity");

    const items: ReconciliationItem[] = consumptions.map(c => {
      const fc = forecastByCode.get(c.itemCode);
      const forecastQty = fc?.estimatedConsumption ?? 0;
      const purchased = purchasedByCode.get(c.itemCode) ?? 0;
      const consumed = c.quantityConsumed;
      const wasted = c.quantityWasted;
      const returned = c.quantityReturned;
      const variance = consumed - forecastQty;
      const variancePct = forecastQty > 0 ? variance / forecastQty : 0;
      const accuracyScore = computeAccuracy(forecastQty, consumed);
      const unitPrice = priceFor(c.itemCode);

      return {
        itemCode: c.itemCode,
        itemName: c.itemName,
        category: c.category,
        unit: c.unit,
        forecast: round2(forecastQty),
        purchased: round2(purchased),
        consumed: round2(consumed),
        wasted: round2(wasted),
        returned: round2(returned),
        variance: round2(variance),
        variancePct: round4(variancePct),
        accuracyScore: round1(accuracyScore),
        realItemCost: round2((consumed + wasted) * unitPrice),
        projectedItemCost: round2(forecastQty * unitPrice),
        wasteItemCost: round2(wasted * unitPrice),
        unitPrice: round2(unitPrice),
      };
    });

    // ---- Accuracy aggregates ----
    const accuracy = aggregateAccuracy(items, eventType);

    // ---- Financial reality ----
    const financials = computeFinancials(event, items);

    // ---- Persist per-item accuracy samples ----
    await prisma.forecastAccuracy.createMany({
      data: items.map(it => ({
        tenantId,
        scope: "item",
        scopeKey: it.itemCode,
        eventId,
        eventType,
        forecasted: it.forecast,
        actual: it.consumed,
        variancePct: it.variancePct,
        accuracyScore: it.accuracyScore,
      })),
    });

    // ---- Category & eventType aggregates (one row each per reconciliation) ----
    const categoryRows = Object.entries(accuracy.byCategory).map(([cat, acc]) => ({
      tenantId,
      scope: "category",
      scopeKey: cat,
      eventId,
      eventType,
      forecasted: 0,
      actual: 0,
      variancePct: 0,
      accuracyScore: acc,
    }));
    const eventTypeRow = {
      tenantId,
      scope: "eventType",
      scopeKey: eventType,
      eventId,
      eventType,
      forecasted: 0,
      actual: 0,
      variancePct: 0,
      accuracyScore: accuracy.overall,
    };
    if (categoryRows.length > 0)
      await prisma.forecastAccuracy.createMany({ data: categoryRows });
    await prisma.forecastAccuracy.create({ data: eventTypeRow });

    // ---- Update learned ItemAdjustments (the actual feedback loop) ----
    const adjustmentsApplied = await this.updateItemAdjustments(
      tenantId,
      eventType,
      items
    );

    // ---- Update EventConsumptionHistory (feeds forecastEngine.blend) ----
    await prisma.eventConsumptionHistory.createMany({
      data: items.map(it => ({
        tenantId,
        eventId,
        eventType,
        guestCount,
        durationHours,
        itemCode: it.itemCode,
        itemName: it.itemName,
        category: it.category,
        quantityConsumed: it.consumed,
        unit: it.unit,
        perGuestRate: guestCount > 0 ? round4(it.consumed / guestCount) : 0,
      })),
    });

    // ---- Supplier feedback ----
    const supplierFeedback = await this.updateSupplierScores(
      tenantId,
      eventId,
      items
    );

    // ---- Memory entries ----
    const memoryEntries = await this.writeMemoryEntries(
      tenantId,
      eventType,
      items
    );

    // ---- Persist ReconciliationReport (idempotent via @@unique(eventId)) ----
    const payload = JSON.parse(
      JSON.stringify({ items, accuracy, financials, adjustmentsApplied, supplierFeedback })
    );
    await prisma.reconciliationReport.upsert({
      where: { eventId },
      create: {
        tenantId,
        eventId,
        eventType,
        guestCount,
        itemsReconciled: items.length,
        meanAccuracy: accuracy.overall,
        projectedCost: financials.projectedCost,
        realCost: financials.realCost,
        wasteCost: financials.wasteCost,
        projectedMargin: financials.projectedMargin,
        realMargin: financials.realMargin,
        payload,
      },
      update: {
        itemsReconciled: items.length,
        meanAccuracy: accuracy.overall,
        projectedCost: financials.projectedCost,
        realCost: financials.realCost,
        wasteCost: financials.wasteCost,
        projectedMargin: financials.projectedMargin,
        realMargin: financials.realMargin,
        payload,
      },
    });

    logger.info(
      { eventId, items: items.length, accuracy: accuracy.overall },
      "ReconciliationEngine: event reconciled"
    );

    return {
      eventId,
      tenantId,
      eventType,
      guestCount,
      generatedAt: new Date(),
      items,
      accuracy,
      financials,
      adjustmentsApplied,
      supplierFeedback,
      memoryEntries,
    };
  }

  // ============================================================
  // Private helpers
  // ============================================================

  private async loadEvent(tenantId: string, eventId: string) {
    return prisma.event.findFirst({
      where: { tenantId, OR: [{ id: eventId }, { eventId }] },
    });
  }

  private async loadPurchasedItems(tenantId: string, eventId: string) {
    const orders = await prisma.purchaseOrder.findMany({
      where: { tenantId, relatedEventId: eventId },
      include: {
        items: true,
        supplier: { select: { id: true, name: true, reliabilityScore: true } },
      },
    });
    return orders.flatMap(o =>
      o.items.map(i => ({
        itemCode: i.itemCode ?? "",
        quantity: i.quantityOrdered ?? 0,
        unitPrice: i.unitPrice ?? 0,
        supplierId: o.supplierId,
        supplierName: o.supplier?.name ?? null,
        previousReliability: o.supplier?.reliabilityScore ?? null,
      }))
    );
  }

  /**
   * Update ItemAdjustment using EWMA of variancePct.
   * factor_new = clamp(factor_current * (1 + alpha * variancePct), FACTOR_MIN, FACTOR_MAX)
   */
  private async updateItemAdjustments(
    tenantId: string,
    eventType: string,
    items: ReconciliationItem[]
  ) {
    const applied: ReconciliationReportResult["adjustmentsApplied"] = [];

    for (const it of items) {
      if (it.forecast === 0) continue; // cannot learn without a baseline

      const existing = await prisma.itemAdjustment.findUnique({
        where: {
          tenantId_itemCode_eventType: {
            tenantId,
            itemCode: it.itemCode,
            eventType,
          },
        },
      });

      const prevFactor = existing?.factor ?? 1.0;
      const prevMean = existing?.meanVariancePct ?? 0;
      const n = (existing?.sampleSize ?? 0) + 1;

      // EWMA on variancePct
      const newMean =
        existing
          ? prevMean * (1 - LEARNING_ALPHA) + it.variancePct * LEARNING_ALPHA
          : it.variancePct;

      // Apply the mean variance as a correction: forecast * (1 + meanVariance)
      const newFactor = clamp(1 + newMean, FACTOR_MIN, FACTOR_MAX);

      await prisma.itemAdjustment.upsert({
        where: {
          tenantId_itemCode_eventType: {
            tenantId,
            itemCode: it.itemCode,
            eventType,
          },
        },
        create: {
          tenantId,
          itemCode: it.itemCode,
          eventType,
          factor: newFactor,
          sampleSize: 1,
          meanVariancePct: it.variancePct,
          lastVariancePct: it.variancePct,
        },
        update: {
          factor: newFactor,
          sampleSize: n,
          meanVariancePct: newMean,
          lastVariancePct: it.variancePct,
        },
      });

      applied.push({
        itemCode: it.itemCode,
        eventType,
        previousFactor: round3(prevFactor),
        newFactor: round3(newFactor),
        sampleSize: n,
      });
    }

    return applied;
  }

  /**
   * Supplier feedback: delivery accuracy (purchased vs consumed+wasted)
   * + quantity variance (purchased vs consumed). Updates Supplier.reliabilityScore.
   */
  private async updateSupplierScores(
    tenantId: string,
    eventId: string,
    items: ReconciliationItem[]
  ): Promise<SupplierFeedbackUpdate[]> {
    const orders = await prisma.purchaseOrder.findMany({
      where: { tenantId, relatedEventId: eventId, supplierId: { not: null } },
      include: {
        items: true,
        supplier: { select: { id: true, name: true, reliabilityScore: true } },
      },
    });

    const updates: SupplierFeedbackUpdate[] = [];

    for (const po of orders) {
      if (!po.supplier || !po.supplierId) continue;

      // Link each PO item to its reconciliation item by itemCode
      const linked = po.items
        .map(poi => {
          const rec = items.find(r => r.itemCode === poi.itemCode);
          return rec ? { poi, rec } : null;
        })
        .filter((x): x is { poi: typeof po.items[0]; rec: ReconciliationItem } => !!x);

      if (linked.length === 0) continue;

      // Delivery accuracy: how close purchased matches (consumed + wasted)
      const deliveryAccuracySum = linked.reduce((s, { poi, rec }) => {
        const need = rec.consumed + rec.wasted;
        if (need === 0) return s + (poi.quantityOrdered === 0 ? 100 : 0);
        const devPct = Math.abs((poi.quantityOrdered ?? 0) - need) / need;
        return s + Math.max(0, 100 - devPct * 100);
      }, 0);
      const deliveryAccuracyPct = deliveryAccuracySum / linked.length;

      // Quantity variance: how much we over/under-ordered vs consumption (directional)
      const variancePctSum = linked.reduce((s, { poi, rec }) => {
        if (rec.consumed === 0) return s;
        return s + ((poi.quantityOrdered ?? 0) - rec.consumed) / rec.consumed;
      }, 0);
      const quantityVariancePct = variancePctSum / linked.length;

      // Blend with prior reliability (or neutral 75 if none)
      const prior = po.supplier.reliabilityScore ?? 75;
      const newScore = clamp(
        prior * (1 - DELIVERY_WEIGHT) +
          deliveryAccuracyPct * DELIVERY_WEIGHT -
          QUANTITY_WEIGHT * Math.abs(quantityVariancePct) * 100 * 0.1,
        0,
        100
      );

      await prisma.supplier.update({
        where: { id: po.supplierId },
        data: { reliabilityScore: round1(newScore) },
      });

      updates.push({
        supplierId: po.supplierId,
        supplierName: po.supplier.name,
        previousReliability: po.supplier.reliabilityScore,
        newReliability: round1(newScore),
        deliveryAccuracyPct: round1(deliveryAccuracyPct),
        quantityVariancePct: round4(quantityVariancePct),
        itemsEvaluated: linked.length,
      });
    }

    return updates;
  }

  /**
   * Write MemoryItem entries for deviations, recurring patterns, and inefficiencies.
   */
  private async writeMemoryEntries(
    tenantId: string,
    eventType: string,
    items: ReconciliationItem[]
  ): Promise<MemoryPatternEntry[]> {
    const entries: MemoryPatternEntry[] = [];

    for (const it of items) {
      // 1. Deviation: single-event signal
      if (Math.abs(it.variancePct) > DEVIATION_THRESHOLD_PCT && it.forecast > 0) {
        entries.push({
          memoryType: "deviation",
          title: `Desvio ${it.variancePct > 0 ? "acima" : "abaixo"} do previsto: ${it.itemName} em ${eventType}`,
          content: `Item ${it.itemCode} consumiu ${it.consumed} ${it.unit} vs previsto ${it.forecast} ${it.unit} (${(it.variancePct * 100).toFixed(1)}%).`,
          tags: ["deviation", it.itemCode, eventType, it.category],
          confidenceScore: 0.7,
        });
      }

      // 2. Recurring pattern: look back for same-sign deviations
      const prior = await prisma.forecastAccuracy.findMany({
        where: {
          tenantId,
          scope: "item",
          scopeKey: it.itemCode,
          eventType,
        },
        orderBy: { recordedAt: "desc" },
        take: 10,
      });
      const sameSign = prior.filter(
        p =>
          Math.sign(p.variancePct) === Math.sign(it.variancePct) &&
          Math.abs(p.variancePct) > 0.1
      );
      if (sameSign.length >= RECURRING_DEVIATION_MIN - 1 && it.variancePct !== 0) {
        entries.push({
          memoryType: "pattern",
          title: `Padrão recorrente: ${it.itemName} sistematicamente ${it.variancePct > 0 ? "sub-previsto" : "super-previsto"} em ${eventType}`,
          content: `${sameSign.length + 1} eventos com desvio de mesmo sinal. Ajuste aprendido aplicado ao forecast.`,
          tags: ["pattern", it.itemCode, eventType, "systemic"],
          confidenceScore: Math.min(0.95, 0.5 + sameSign.length * 0.1),
        });
      }

      // 3. Inefficiency: waste above threshold
      if (it.consumed > 0 && it.wasted / it.consumed > INEFFICIENCY_WASTE_PCT) {
        entries.push({
          memoryType: "inefficiency",
          title: `Ineficiência: desperdício de ${it.itemName} em ${eventType}`,
          content: `Desperdício de ${it.wasted} ${it.unit} (${((it.wasted / it.consumed) * 100).toFixed(1)}% do consumo). Custo perdido: R$${it.wasteItemCost.toFixed(2)}.`,
          tags: ["inefficiency", "waste", it.itemCode, eventType],
          confidenceScore: 0.8,
        });
      }
    }

    if (entries.length === 0) return entries;

    await prisma.memoryItem.createMany({
      data: entries.map(e => ({
        companyId: tenantId,
        memoryType: e.memoryType,
        title: e.title,
        content: e.content,
        tags: e.tags,
        sourceType: "reconciliation",
        sourceRef: eventType,
        confidenceScore: e.confidenceScore,
      })),
    });

    return entries;
  }
}

// ============================================================
// Pure helpers (exported for accuracy-scoring.ts reuse)
// ============================================================

export function computeAccuracy(forecast: number, actual: number): number {
  if (forecast === 0 && actual === 0) return 100;
  if (forecast === 0) return 0;
  const varPct = Math.abs((actual - forecast) / forecast);
  return Math.max(0, Math.min(100, 100 * (1 - varPct)));
}

function aggregateByCode<T extends { itemCode: string }>(
  arr: T[],
  key: keyof T
): Map<string, number> {
  const m = new Map<string, number>();
  for (const row of arr) {
    const v = Number(row[key] ?? 0);
    m.set(row.itemCode, (m.get(row.itemCode) ?? 0) + v);
  }
  return m;
}

function aggregateAccuracy(
  items: ReconciliationItem[],
  eventType: string
): ReconciliationAccuracy {
  const overall =
    items.length > 0
      ? items.reduce((s, i) => s + i.accuracyScore, 0) / items.length
      : 0;

  const byCategory: Record<string, number[]> = {};
  for (const it of items) {
    (byCategory[it.category] ??= []).push(it.accuracyScore);
  }
  const byCategoryMean = Object.fromEntries(
    Object.entries(byCategory).map(([k, arr]) => [
      k,
      round1(arr.reduce((s, v) => s + v, 0) / arr.length),
    ])
  );

  return {
    overall: round1(overall),
    byCategory: byCategoryMean,
    byEventType: { [eventType]: round1(overall) },
    itemCount: items.length,
  };
}

function computeFinancials(
  event: { revenueTotal: number | null; cmvTotal: number | null; marginPct: number | null },
  items: ReconciliationItem[]
): ReconciliationFinancials {
  const projectedCost = round2(items.reduce((s, i) => s + i.projectedItemCost, 0));
  const realCost = round2(items.reduce((s, i) => s + i.realItemCost, 0));
  const wasteCost = round2(items.reduce((s, i) => s + i.wasteItemCost, 0));
  const revenue = event.revenueTotal;
  const projectedMargin = event.marginPct;
  const realMargin =
    revenue && revenue > 0 ? round2(((revenue - realCost) / revenue) * 100) : null;
  const marginDelta =
    projectedMargin != null && realMargin != null
      ? round2(realMargin - projectedMargin)
      : null;

  return {
    projectedCost,
    realCost,
    wasteCost,
    revenue,
    projectedMargin,
    realMargin,
    marginDelta,
  };
}

function clamp(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, v));
}
function round1(n: number) { return Math.round(n * 10) / 10; }
function round2(n: number) { return Math.round(n * 100) / 100; }
function round3(n: number) { return Math.round(n * 1000) / 1000; }
function round4(n: number) { return Math.round(n * 10000) / 10000; }

export const reconciliationEngine = new ReconciliationEngine();
