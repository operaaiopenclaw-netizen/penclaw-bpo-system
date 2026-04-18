// ============================================================
// FORECAST ENGINE — Multi-factor consumption prediction
// ============================================================
import { prisma } from "../db";
import { logger } from "../utils/logger";
import { ConsumptionForecast, EventForecastResult } from "./types";

// ---- Base consumption rates (liters or kg per guest, normalized to 6h) ----
// Derived from empirical supply-agent data + industry benchmarks.
// Each row: { rate: L or kg per guest per 6h, unit, category }
const BASE_RATES: Record<
  string,
  Record<string, { rate: number; unit: string; category: string }>
> = {
  casamento: {
    cerveja:   { rate: 2.5,  unit: "L",  category: "beverage_alcohol" },
    soft:      { rate: 1.5,  unit: "L",  category: "beverage_soft" },
    agua:      { rate: 1.0,  unit: "L",  category: "beverage_water" },
    destilado: { rate: 0.30, unit: "L",  category: "beverage_spirit" },
    gelo:      { rate: 1.5,  unit: "kg", category: "consumable" },
    espumante: { rate: 0.25, unit: "L",  category: "beverage_alcohol" },
    suco:      { rate: 0.50, unit: "L",  category: "beverage_soft" },
  },
  formatura: {
    cerveja:   { rate: 3.0,  unit: "L",  category: "beverage_alcohol" },
    soft:      { rate: 2.0,  unit: "L",  category: "beverage_soft" },
    agua:      { rate: 0.80, unit: "L",  category: "beverage_water" },
    destilado: { rate: 0.40, unit: "L",  category: "beverage_spirit" },
    gelo:      { rate: 2.0,  unit: "kg", category: "consumable" },
  },
  corporativo: {
    cerveja:   { rate: 2.0,  unit: "L",  category: "beverage_alcohol" },
    soft:      { rate: 2.5,  unit: "L",  category: "beverage_soft" },
    agua:      { rate: 2.0,  unit: "L",  category: "beverage_water" },
    destilado: { rate: 0.20, unit: "L",  category: "beverage_spirit" },
    gelo:      { rate: 1.2,  unit: "kg", category: "consumable" },
    cafe:      { rate: 0.15, unit: "L",  category: "beverage_hot" },
  },
  aniversario: {
    cerveja:   { rate: 2.8,  unit: "L",  category: "beverage_alcohol" },
    soft:      { rate: 1.8,  unit: "L",  category: "beverage_soft" },
    agua:      { rate: 1.0,  unit: "L",  category: "beverage_water" },
    destilado: { rate: 0.30, unit: "L",  category: "beverage_spirit" },
    gelo:      { rate: 1.8,  unit: "kg", category: "consumable" },
  },
  confraternizacao: {
    cerveja:   { rate: 3.5,  unit: "L",  category: "beverage_alcohol" },
    soft:      { rate: 2.0,  unit: "L",  category: "beverage_soft" },
    agua:      { rate: 0.50, unit: "L",  category: "beverage_water" },
    destilado: { rate: 0.50, unit: "L",  category: "beverage_spirit" },
    gelo:      { rate: 2.5,  unit: "kg", category: "consumable" },
  },
};

// Fall back to corporate profile for unmapped event types
const DEFAULT_RATES = BASE_RATES.corporativo;

// ---- Statistical parameters ----
// Duration baseline: 6h. Each extra hour above baseline adds 12% consumption.
const DURATION_BASELINE_H = 6;
const DURATION_RATE_PER_H = 0.12;

// Large-event buffering: events with >200 guests have ~8% lower per-head consumption.
// Modelled as 8% reduction per doubling above 200 (log2 scale), capped at 3 doublings.
const LARGE_EVENT_THRESHOLD = 200;
const LARGE_EVENT_REDUCTION = 0.08;

// Confidence: mapped from number of historical data points
function computeConfidence(n: number): number {
  if (n === 0)  return 0.40;
  if (n <= 2)   return 0.55;
  if (n <= 4)   return 0.68;
  if (n <= 9)   return 0.80;
  if (n <= 19)  return 0.88;
  return 0.95;
}

// 90% confidence interval (Z = 1.645) around the estimate.
// Falls back to ±25% of the model-base when no history variance is available.
function ciRange(
  estimate: number,
  stddev: number,
  baseEstimate: number
): { min: number; max: number } {
  const Z90 = 1.645;
  if (stddev > 0 && estimate > 0) {
    return {
      min: Math.max(estimate - Z90 * stddev, estimate * 0.50),
      max: Math.min(estimate + Z90 * stddev, estimate * 2.50),
    };
  }
  return {
    min: baseEstimate * 0.75,
    max: baseEstimate * 1.25,
  };
}

// ---- Item name display map ----
const ITEM_NAMES: Record<string, string> = {
  cerveja:   "Cerveja",
  soft:      "Refrigerante",
  agua:      "Água",
  destilado: "Destilado",
  gelo:      "Gelo",
  espumante: "Espumante",
  suco:      "Suco",
  cafe:      "Café",
};

// ============================================================

export class ForecastEngine {
  /**
   * Forecast consumption for an event.
   * Queries historical data and inventory prices in parallel.
   */
  async forecastEvent(
    tenantId: string,
    eventType: string,
    guestCount: number,
    durationHours: number,
    eventId?: string
  ): Promise<EventForecastResult> {
    const normType = eventType.toLowerCase().trim();
    const baseRates = BASE_RATES[normType] ?? DEFAULT_RATES;

    // Parallel: fetch history + inventory prices
    const [history, inventoryItems] = await Promise.all([
      this.fetchHistory(tenantId, normType),
      prisma.inventoryItem.findMany({
        select: { code: true, name: true, unitPrice: true },
      }),
    ]);

    // Build per-item forecasts (CPU-bound, run synchronously)
    const forecasts: ConsumptionForecast[] = Object.entries(baseRates).map(
      ([itemCode, { rate, unit, category }]) =>
        this.computeItemForecast(
          itemCode,
          category,
          rate,
          unit,
          guestCount,
          durationHours,
          history.filter(h => h.itemCode === itemCode)
        )
    );

    // Estimate procurement cost at current inventory prices
    const totalEstimatedCost = forecasts.reduce((sum, fc) => {
      const inv = inventoryItems.find(
        i =>
          i.code.toLowerCase().includes(fc.itemCode) ||
          i.name.toLowerCase().includes(fc.itemCode)
      );
      return sum + fc.estimatedConsumption * (inv?.unitPrice ?? 0);
    }, 0);

    const overallConfidence =
      forecasts.reduce((s, f) => s + f.confidenceScore, 0) /
      Math.max(forecasts.length, 1);

    logger.debug("ForecastEngine: forecast computed", {
      eventType: normType,
      guestCount,
      durationHours,
      items: forecasts.length,
      overallConfidence,
    });

    return {
      eventId,
      eventType: normType,
      guestCount,
      durationHours,
      forecasts,
      overallConfidence: round2(overallConfidence),
      totalEstimatedCost: round2(totalEstimatedCost),
      generatedAt: new Date(),
    };
  }

  private computeItemForecast(
    itemCode: string,
    category: string,
    baseRatePerGuest: number,
    unit: string,
    guestCount: number,
    durationHours: number,
    history: Array<{ perGuestRate: number }>
  ): ConsumptionForecast {
    // Factor 1 — Duration
    const durationFactor =
      1 + Math.max(0, durationHours - DURATION_BASELINE_H) * DURATION_RATE_PER_H;

    // Factor 2 — Guest-count scale
    const guestScaleFactor =
      guestCount > LARGE_EVENT_THRESHOLD
        ? 1 -
          LARGE_EVENT_REDUCTION *
            Math.min(Math.log2(guestCount / LARGE_EVENT_THRESHOLD), 3)
        : 1.0;

    // Model baseline for this event
    const modelRatePerGuest = baseRatePerGuest * durationFactor * guestScaleFactor;
    const modelTotal = modelRatePerGuest * guestCount;

    // Factor 3 — Historical blend
    let histMean = 0;
    let histStddev = 0;
    if (history.length > 0) {
      histMean = history.reduce((s, h) => s + h.perGuestRate, 0) / history.length;
      const variance =
        history.reduce((s, h) => s + (h.perGuestRate - histMean) ** 2, 0) /
        history.length;
      histStddev = Math.sqrt(variance);
    }

    // Weight towards history as more data points accumulate (max 70% history)
    const histWeight = Math.min(history.length / 10, 1) * 0.7;
    const blendedRate =
      history.length > 0
        ? modelRatePerGuest * (1 - histWeight) + histMean * histWeight
        : modelRatePerGuest;

    const estimated = blendedRate * guestCount;
    const { min, max } = ciRange(estimated, histStddev * guestCount, modelTotal);

    return {
      itemCode,
      itemName: ITEM_NAMES[itemCode] ?? capitalize(itemCode),
      category,
      unit,
      estimatedConsumption: round1(estimated),
      minConsumption: round1(min),
      maxConsumption: round1(max),
      confidenceScore: computeConfidence(history.length),
      historicalDataPoints: history.length,
      perGuestRate: round3(blendedRate),
      adjustmentFactors: {
        eventType: 1.0,
        duration: round3(durationFactor),
        guestScale: round3(guestScaleFactor),
        historical: round3(histWeight),
      },
    };
  }

  private async fetchHistory(
    tenantId: string,
    eventType: string
  ): Promise<Array<{ itemCode: string; perGuestRate: number }>> {
    try {
      const rows = await prisma.eventConsumptionHistory.findMany({
        where: { tenantId, eventType },
        orderBy: { recordedAt: "desc" },
        take: 100,
        select: { itemCode: true, perGuestRate: true },
      });
      return rows.map(r => ({
        itemCode: r.itemCode,
        perGuestRate: Number(r.perGuestRate),
      }));
    } catch {
      return [];
    }
  }

  /**
   * Record actual post-event consumption to improve future forecasts.
   * Called from the post_event_closure workflow or the API.
   */
  async recordActualConsumption(
    tenantId: string,
    eventId: string,
    eventType: string,
    guestCount: number,
    items: Array<{
      itemCode: string;
      itemName: string;
      category: string;
      quantityConsumed: number;
      unit: string;
    }>
  ): Promise<void> {
    const records = items
      .filter(i => i.quantityConsumed >= 0)
      .map(item => ({
        tenantId,
        eventId,
        eventType: eventType.toLowerCase().trim(),
        guestCount,
        durationHours: 6, // default
        itemCode: item.itemCode,
        itemName: item.itemName,
        category: item.category,
        quantityConsumed: item.quantityConsumed,
        unit: item.unit,
        perGuestRate:
          guestCount > 0
            ? round4(item.quantityConsumed / guestCount)
            : 0,
      }));

    await prisma.eventConsumptionHistory.createMany({ data: records });

    logger.info({ eventId, eventType, records: records.length }, "ForecastEngine: consumption recorded");
  }
}

// ---- helpers ----
function round1(n: number) { return Math.round(n * 10) / 10; }
function round2(n: number) { return Math.round(n * 100) / 100; }
function round3(n: number) { return Math.round(n * 1000) / 1000; }
function round4(n: number) { return Math.round(n * 10000) / 10000; }
function capitalize(s: string) { return s.charAt(0).toUpperCase() + s.slice(1); }

export const forecastEngine = new ForecastEngine();
