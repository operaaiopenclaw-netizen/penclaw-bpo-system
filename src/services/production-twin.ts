// ============================================================
// PRODUCTION DIGITAL TWIN — Production vs Consumption per event
// Tracks: planned → produced → served → leftover → loss
// Feeds: reconciliation loop, forecast calibration, CMV reporting
// ============================================================
import { prisma } from "../db";
import { logger } from "../utils/logger";

export interface ProductionRecord {
  itemCode: string;
  itemName: string;
  category: string;
  unit: string;
  planned: number;    // from ProductionOrder
  produced: number;   // kitchen output (recorded at POST_PRODUCTION)
  served: number;     // consumed at event (recorded at SERVICE_END)
  leftover: number;   // returned to stock
  loss: number;       // produced - served - leftover (waste)
  efficiency: number; // served / planned (0.0–1.0+)
  variance: number;   // served - planned (negative = under, positive = over)
}

export interface ReconciliationReport {
  eventId: string;
  eventType: string;
  guestCount: number;
  reconciledAt: Date;
  items: ProductionRecord[];
  summary: {
    totalPlanned: number;
    totalProduced: number;
    totalServed: number;
    totalLeftover: number;
    totalLoss: number;
    avgEfficiency: number;
    cmvActual: number;
    cmvPlanned: number;
    cmvVariancePct: number;
    overallStatus: "ON_TRACK" | "OVER_PRODUCED" | "UNDER_PRODUCED" | "HIGH_WASTE";
  };
  calibrationSignals: Array<{
    itemCode: string;
    itemName: string;
    actualPerGuestRate: number;
    plannedPerGuestRate: number;
    drift: number;
    recommendation: string;
  }>;
}

export class ProductionTwinService {
  /**
   * Record kitchen output (called when chef marks production complete).
   * Creates StockMovement entries to track what left the kitchen.
   */
  async recordProduction(
    tenantId: string,
    eventId: string,
    warehouseId: string,
    items: Array<{
      productId: string;
      itemCode: string;
      itemName: string;
      quantityProduced: number;
      unit: string;
    }>
  ): Promise<void> {
    const movements = items.map(item => ({
      tenantId,
      productId: item.productId,
      warehouseId,
      movementType: "PRODUCTION_OUTPUT",
      quantity: item.quantityProduced,
      sourceType: "EVENT",
      sourceId: eventId,
      eventId,
      reason: `Produção para evento ${eventId}`,
      metadata: { itemCode: item.itemCode, itemName: item.itemName, unit: item.unit } as object
    }));

    await prisma.stockMovement.createMany({ data: movements });

    logger.info("ProductionTwin: production recorded", {
      eventId,
      itemCount: items.length,
      totalQty: items.reduce((s, i) => s + i.quantityProduced, 0)
    });
  }

  /**
   * Record actual consumption at event end.
   * Called by ActionDispatcher when event_ops_agent emits RECORD_CONSUMPTION.
   */
  async recordConsumption(
    tenantId: string,
    eventId: string,
    warehouseId: string,
    items: Array<{
      productId: string;
      itemCode: string;
      itemName: string;
      quantityConsumed: number;
      quantityLeftover?: number;
      unit: string;
    }>
  ): Promise<void> {
    const consumptionMovements = items.map(item => ({
      tenantId,
      productId: item.productId,
      warehouseId,
      movementType: "EVENT_CONSUMPTION",
      quantity: item.quantityConsumed,
      sourceType: "EVENT",
      sourceId: eventId,
      eventId,
      reason: `Consumo no evento ${eventId}`,
      metadata: { itemCode: item.itemCode, unit: item.unit } as object
    }));

    await prisma.stockMovement.createMany({ data: consumptionMovements });

    // Record leftovers back to stock
    const leftoverItems = items.filter(i => (i.quantityLeftover ?? 0) > 0);
    if (leftoverItems.length > 0) {
      const leftoverMovements = leftoverItems.map(item => ({
        tenantId,
        productId: item.productId,
        warehouseId,
        movementType: "LEFTOVER_RETURN",
        quantity: item.quantityLeftover!,
        sourceType: "EVENT",
        sourceId: eventId,
        eventId,
        reason: `Sobra retornada do evento ${eventId}`,
        metadata: { itemCode: item.itemCode, unit: item.unit } as object
      }));
      await prisma.stockMovement.createMany({ data: leftoverMovements });
    }

    logger.info("ProductionTwin: consumption recorded", {
      eventId,
      consumed: items.length,
      leftovers: leftoverItems.length
    });
  }

  /**
   * Reconcile production vs consumption for an event.
   * Called by ActionDispatcher when event_ops_agent emits RECONCILE_EVENT.
   */
  async reconcile(
    tenantId: string,
    eventId: string,
    guestCount: number
  ): Promise<ReconciliationReport> {
    const event = await prisma.event.findFirst({
      where: { id: eventId, tenantId }
    });

    const eventType = event?.eventType ?? "corporativo";

    // Fetch all stock movements for this event
    const movements = await prisma.stockMovement.findMany({
      where: { tenantId, eventId },
      select: {
        movementType: true,
        quantity: true,
        productId: true,
        metadata: true
      }
    });

    // Fetch planned quantities from production orders
    const productionOrders = await prisma.productionOrder.findMany({
      where: { eventId, tenantId },
      include: { items: true }
    }).catch(() => []);

    // Build item map
    const itemMap = new Map<string, {
      itemCode: string; itemName: string; unit: string; category: string;
      planned: number; produced: number; served: number; leftover: number;
    }>();

    // Seed from production orders (planned)
    for (const po of productionOrders) {
      for (const item of po.items) {
        const itemKey = item.itemName;
        if (!itemMap.has(itemKey)) {
          itemMap.set(itemKey, {
            itemCode: itemKey,
            itemName: item.itemName,
            unit: "un",
            category: "food",
            planned: 0, produced: 0, served: 0, leftover: 0
          });
        }
        itemMap.get(itemKey)!.planned += item.plannedQuantity;
      }
    }

    // Apply movements
    for (const mov of movements) {
      const meta = mov.metadata as Record<string, unknown> | null;
      const itemCode = String(meta?.itemCode ?? mov.productId);
      if (!itemMap.has(itemCode)) {
        itemMap.set(itemCode, {
          itemCode,
          itemName: String(meta?.itemName ?? itemCode),
          unit: String(meta?.unit ?? "un"),
          category: "general",
          planned: 0, produced: 0, served: 0, leftover: 0
        });
      }
      const entry = itemMap.get(itemCode)!;
      if (mov.movementType === "PRODUCTION_OUTPUT") entry.produced += mov.quantity;
      if (mov.movementType === "EVENT_CONSUMPTION")  entry.served   += mov.quantity;
      if (mov.movementType === "LEFTOVER_RETURN")    entry.leftover += mov.quantity;
    }

    const items: ProductionRecord[] = Array.from(itemMap.values()).map(i => {
      const loss = Math.max(0, i.produced - i.served - i.leftover);
      const planned = i.planned > 0 ? i.planned : i.produced; // fallback if no PO
      const efficiency = planned > 0 ? r3(i.served / planned) : 1;
      const variance = r2(i.served - planned);
      return { ...i, loss: r2(loss), efficiency, variance };
    });

    // Summary
    const totalPlanned  = r2(items.reduce((s, i) => s + i.planned,  0));
    const totalProduced = r2(items.reduce((s, i) => s + i.produced, 0));
    const totalServed   = r2(items.reduce((s, i) => s + i.served,   0));
    const totalLeftover = r2(items.reduce((s, i) => s + i.leftover, 0));
    const totalLoss     = r2(items.reduce((s, i) => s + i.loss,     0));
    const avgEfficiency = items.length > 0
      ? r3(items.reduce((s, i) => s + i.efficiency, 0) / items.length)
      : 1;

    // CMV placeholders (real prices from InventoryItem)
    const cmvActual  = 0;
    const cmvPlanned = 0;

    const overallStatus = totalLoss / Math.max(totalProduced, 1) > 0.15 ? "HIGH_WASTE"
      : totalProduced > totalPlanned * 1.10 ? "OVER_PRODUCED"
      : totalServed   < totalPlanned * 0.80 ? "UNDER_PRODUCED"
      : "ON_TRACK";

    // Calibration signals for ForecastEngine
    const calibrationSignals = items
      .filter(i => i.served > 0 && guestCount > 0)
      .map(i => {
        const actualRate = r4(i.served / guestCount);
        const plannedRate = r4(i.planned / Math.max(guestCount, 1));
        const drift = r3(actualRate - plannedRate);
        return {
          itemCode: i.itemCode,
          itemName: i.itemName,
          actualPerGuestRate: actualRate,
          plannedPerGuestRate: plannedRate,
          drift,
          recommendation: Math.abs(drift) > 0.1 * plannedRate
            ? `Ajustar taxa de ${i.itemCode}: previsto ${plannedRate}, real ${actualRate} (drift ${drift > 0 ? "+" : ""}${drift})`
            : "Dentro da faixa esperada"
        };
      });

    const report: ReconciliationReport = {
      eventId,
      eventType,
      guestCount,
      reconciledAt: new Date(),
      items,
      summary: {
        totalPlanned,
        totalProduced,
        totalServed,
        totalLeftover,
        totalLoss,
        avgEfficiency,
        cmvActual,
        cmvPlanned,
        cmvVariancePct: 0,
        overallStatus
      },
      calibrationSignals
    };

    // Write calibration data to EventConsumptionHistory
    await this.writeCalibrationHistory(tenantId, eventId, eventType, guestCount, calibrationSignals, items);

    logger.info("ProductionTwin: reconciliation complete", {
      eventId,
      overallStatus,
      avgEfficiency,
      totalLoss,
      calibrationSignals: calibrationSignals.filter(s => Math.abs(s.drift) > 0).length
    });

    return report;
  }

  private async writeCalibrationHistory(
    tenantId: string,
    eventId: string,
    eventType: string,
    guestCount: number,
    signals: ReconciliationReport["calibrationSignals"],
    items: ProductionRecord[]
  ): Promise<void> {
    const records = items
      .filter(i => i.served > 0)
      .map(i => ({
        tenantId,
        eventId,
        eventType,
        guestCount,
        durationHours: 6,
        itemCode: i.itemCode,
        itemName: i.itemName,
        category: i.category,
        quantityConsumed: i.served,
        unit: i.unit,
        perGuestRate: guestCount > 0 ? r4(i.served / guestCount) : 0
      }));

    if (records.length > 0) {
      await prisma.eventConsumptionHistory.createMany({
        data: records,
        skipDuplicates: true
      }).catch(err => {
        logger.warn("ProductionTwin: could not write calibration history", { error: err });
      });
    }
  }
}

function r2(n: number) { return Math.round(n * 100) / 100; }
function r3(n: number) { return Math.round(n * 1000) / 1000; }
function r4(n: number) { return Math.round(n * 10000) / 10000; }

export const productionTwin = new ProductionTwinService();
