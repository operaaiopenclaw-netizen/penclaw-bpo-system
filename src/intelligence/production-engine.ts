// ============================================================
// PRODUCTION ENGINE — Sprint 5
// Controls: what / when / how much / in which sequence
// ============================================================
import { prisma } from "../db";
import { logger } from "../utils/logger";
import {
  ProductionPlan,
  ProductionItemPlan,
  ProductionExecutionResult,
  StationLoadCheck,
  StationType,
} from "./types";

// ---- Station mapping: itemCategory → station ----
const STATION_MAP: Record<string, StationType> = {
  beverage_alcohol: "bar",
  beverage_soft: "bar",
  beverage_water: "bar",
  beverage_spirit: "bar",
  beverage_hot: "bar",
  consumable: "kitchen",
  food: "kitchen",
  catering: "kitchen",
  pastry: "pastry",
  sobremesa: "pastry",
  confeitaria: "pastry",
  prep: "prep",
};

// ---- Production rates (items per hour per station) ----
const STATION_RATES: Record<StationType, number> = {
  bar: 60,      // bar can prepare 60 drink-units/hour
  kitchen: 30,  // 30 plates/hour
  pastry: 20,   // 20 desserts/hour
  prep: 40,
};

// ---- PO number counter (simple timestamp-based) ----
function generatePoNumber(): string {
  const now = new Date();
  const ts = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, "0")}${String(now.getDate()).padStart(2, "0")}${String(now.getHours()).padStart(2, "0")}${String(now.getMinutes()).padStart(2, "0")}${String(now.getSeconds()).padStart(2, "0")}`;
  const rnd = Math.random().toString(36).slice(2, 6).toUpperCase();
  return `OP-${ts}-${rnd}`;
}

function stationForCategory(category: string): StationType {
  return STATION_MAP[category?.toLowerCase()] ?? "kitchen";
}

function hoursFor(stationType: StationType, itemCount: number): number {
  const rate = STATION_RATES[stationType];
  return Math.max(0.5, Math.ceil((itemCount / rate) * 10) / 10);
}

export class ProductionEngine {
  /**
   * Plan production for an event:
   * - Loads approved ServiceOrders for the event
   * - Groups items by station (kitchen/bar/pastry)
   * - Checks station capacity for the production window
   * - Reserves inventory
   * - Creates ProductionOrder + Items + Schedules + Reservations
   */
  async planProduction(
    tenantId: string,
    eventId: string,
    options: { productionWindowDays?: number } = {}
  ): Promise<ProductionPlan> {
    const windowDays = options.productionWindowDays ?? 1;

    const [event, approvedSos, stations, inventory] = await Promise.all([
      prisma.event.findFirst({
        where: { tenantId, OR: [{ id: eventId }, { eventId }] },
      }),
      prisma.serviceOrder.findMany({
        where: {
          tenantId,
          eventId,
          status: { in: ["APPROVED", "IN_PRODUCTION"] },
        },
        include: { items: true },
      }),
      prisma.productionStation.findMany({
        where: { tenantId, isActive: true },
      }),
      prisma.inventoryItem.findMany({
        select: { code: true, name: true, currentQty: true, unitPrice: true },
      }),
    ]);

    if (!event) throw new Error(`Event not found: ${eventId}`);
    if (approvedSos.length === 0)
      throw new Error(`No approved ServiceOrders for event: ${eventId}`);
    if (stations.length === 0)
      throw new Error(`No active production stations for tenant: ${tenantId}`);

    const eventDate = event.eventDate ?? new Date();
    const scheduledDate = new Date(eventDate);
    scheduledDate.setDate(scheduledDate.getDate() - windowDays);

    // ---- Map every SO item to production item plan ----
    const itemsPlan: ProductionItemPlan[] = [];
    const alerts: string[] = [];

    for (const so of approvedSos) {
      for (const soItem of so.items) {
        const category = soItem.itemCategory ?? "food";
        const stationType = stationForCategory(category);
        const inv = inventory.find(
          i =>
            i.code.toLowerCase() === soItem.name.toLowerCase() ||
            i.name.toLowerCase().includes(soItem.name.toLowerCase())
        );
        const available = inv?.currentQty ?? 0;
        const stockInsufficient = available < soItem.quantity;
        if (stockInsufficient) {
          alerts.push(
            `Estoque insuficiente para ${soItem.name}: disponível=${available}, necessário=${soItem.quantity}`
          );
        }
        itemsPlan.push({
          itemCode: soItem.name.toLowerCase(),
          itemName: soItem.name,
          category,
          stationType,
          quantityRequired: soItem.quantity,
          unit: soItem.unit ?? "units",
          estimatedHours: hoursFor(stationType, soItem.quantity),
          estimatedCost: soItem.totalPrice,
          inventoryAvailable: available,
          stockInsufficient,
        });
      }
    }

    // ---- Aggregate hours by station ----
    const hoursByStation = new Map<StationType, number>();
    for (const it of itemsPlan) {
      hoursByStation.set(
        it.stationType,
        (hoursByStation.get(it.stationType) ?? 0) + it.estimatedHours
      );
    }

    // ---- Capacity check per station for the target date ----
    const stationLoadChecks: StationLoadCheck[] = [];
    const scheduledDateStr = scheduledDate.toISOString().slice(0, 10);
    const dayStart = new Date(scheduledDate);
    dayStart.setHours(0, 0, 0, 0);
    const dayEnd = new Date(dayStart);
    dayEnd.setHours(23, 59, 59, 999);

    for (const [stationType, requestedHours] of hoursByStation) {
      const station = stations.find(s => s.stationType === stationType);
      if (!station) {
        alerts.push(
          `Estação '${stationType}' não cadastrada — pulando itens desta estação`
        );
        continue;
      }
      const existingLoad = await prisma.productionSchedule.aggregate({
        where: {
          tenantId,
          stationId: station.id,
          scheduledStart: { gte: dayStart, lte: dayEnd },
          status: { not: "CANCELLED" },
        },
        _sum: { estimatedHours: true },
      });
      const existingHours = existingLoad._sum.estimatedHours ?? 0;
      const totalAfter = existingHours + requestedHours;
      const withinCapacity = totalAfter <= station.maxHoursPerDay;
      if (!withinCapacity) {
        alerts.push(
          `Estação ${station.name} saturada em ${scheduledDateStr}: ${existingHours}h + ${requestedHours}h > ${station.maxHoursPerDay}h/dia`
        );
      }
      stationLoadChecks.push({
        stationId: station.id,
        stationName: station.name,
        stationType,
        date: scheduledDateStr,
        maxHoursPerDay: station.maxHoursPerDay,
        existingLoadHours: round1(existingHours),
        requestedHours: round1(requestedHours),
        totalAfterSchedule: round1(totalAfter),
        withinCapacity,
      });
    }

    // ---- Create ProductionOrder + Items (single PO covering all stations) ----
    const poNumber = generatePoNumber();
    const productionOrder = await prisma.productionOrder.create({
      data: {
        tenantId,
        eventId,
        sourceSoIds: approvedSos.map(s => s.id),
        poNumber,
        status: "SCHEDULED",
        productionDate: scheduledDate,
        requiredReadyAt: eventDate,
        items: {
          create: itemsPlan.map(i => ({
            itemName: i.itemName,
            plannedQuantity: i.quantityRequired,
            estimatedCost: i.estimatedCost,
            metadata: {
              itemCode: i.itemCode,
              stationType: i.stationType,
              category: i.category,
              unit: i.unit,
            } as any,
          })),
        },
      },
    });

    // ---- Schedules per station (sequenced by stationType order) ----
    const stationOrder: StationType[] = ["prep", "kitchen", "pastry", "bar"];
    let cursor = new Date(dayStart);
    cursor.setHours(8, 0, 0, 0); // start at 08:00

    const scheduleRows = [];
    for (const type of stationOrder) {
      const hours = hoursByStation.get(type);
      if (!hours || hours === 0) continue;
      const station = stations.find(s => s.stationType === type);
      if (!station) continue;

      const start = new Date(cursor);
      const end = new Date(start);
      end.setMinutes(end.getMinutes() + hours * 60);

      const schedule = await prisma.productionSchedule.create({
        data: {
          tenantId,
          stationId: station.id,
          productionOrderId: productionOrder.id,
          scheduledStart: start,
          scheduledEnd: end,
          estimatedHours: hours,
          status: "SCHEDULED",
        },
      });
      scheduleRows.push({
        scheduleId: schedule.id,
        stationName: station.name,
        stationType: type,
        scheduledStart: start,
        scheduledEnd: end,
        estimatedHours: hours,
      });
      cursor = end;
    }

    // ---- Inventory reservations ----
    const reservations = [];
    for (const it of itemsPlan) {
      const reservation = await prisma.inventoryReservation.create({
        data: {
          tenantId,
          eventId,
          productId: it.itemCode, // use itemCode as productId fallback
          quantityReserved: it.quantityRequired,
          status: "RESERVED",
          requiredBy: eventDate,
          metadata: {
            productionOrderId: productionOrder.id,
            itemCode: it.itemCode,
            itemName: it.itemName,
          } as any,
        },
      });
      reservations.push({
        reservationId: reservation.id,
        itemCode: it.itemCode,
        quantityReserved: it.quantityRequired,
      });
    }

    logger.info(
      { eventId, productionOrderId: productionOrder.id, items: itemsPlan.length },
      "ProductionEngine: plan created"
    );

    return {
      eventId,
      tenantId,
      eventDate: eventDate.toISOString().slice(0, 10),
      guestCount: event.guests ?? 0,
      itemCount: itemsPlan.length,
      productionOrderId: productionOrder.id,
      productionOrderNumber: poNumber,
      items: itemsPlan,
      schedules: scheduleRows,
      stationLoadChecks,
      reservations,
      alerts,
      createdAt: new Date(),
    };
  }

  /**
   * Execute a production order: records actual produced + wasted quantities,
   * creates EventConsumption rows (feeding Sprint 4 reconciliation loop),
   * updates InventoryReservation status, marks PO + schedules completed.
   */
  async completeProductionOrder(
    tenantId: string,
    productionOrderId: string,
    results: Array<{
      itemName: string;
      producedQuantity: number;
      wastedQuantity: number;
      actualCost?: number;
    }>
  ): Promise<ProductionExecutionResult> {
    const po = await prisma.productionOrder.findUnique({
      where: { id: productionOrderId },
      include: { items: true, schedules: { include: { station: true } } },
    });
    if (!po) throw new Error(`ProductionOrder not found: ${productionOrderId}`);

    // Update each ProductionOrderItem + collect EventConsumption rows
    const consumptionRows: Array<{
      tenantId: string;
      eventId: string;
      itemCode: string;
      itemName: string;
      category: string;
      unit: string;
      quantityConsumed: number;
      quantityWasted: number;
      quantityReturned: number;
    }> = [];

    let totalProduced = 0;
    let totalWasted = 0;
    let totalActualCost = 0;
    let itemsExecuted = 0;

    for (const item of po.items) {
      const match = results.find(
        r => r.itemName.toLowerCase() === item.itemName.toLowerCase()
      );
      if (!match) continue;

      const meta = (item.metadata as any) ?? {};
      const itemCode = meta.itemCode ?? item.itemName.toLowerCase();
      const category = meta.category ?? "food";
      const unit = meta.unit ?? "units";

      await prisma.productionOrderItem.update({
        where: { id: item.id },
        data: {
          producedQuantity: match.producedQuantity,
          wastedQuantity: match.wastedQuantity,
          actualCost: match.actualCost ?? item.estimatedCost,
        },
      });

      consumptionRows.push({
        tenantId,
        eventId: po.eventId,
        itemCode,
        itemName: item.itemName,
        category,
        unit,
        quantityConsumed: match.producedQuantity,
        quantityWasted: match.wastedQuantity,
        quantityReturned: 0,
      });

      totalProduced += match.producedQuantity;
      totalWasted += match.wastedQuantity;
      totalActualCost += match.actualCost ?? item.estimatedCost ?? 0;
      itemsExecuted++;
    }

    // Create EventConsumption rows (this closes the loop: production feeds reconciliation)
    if (consumptionRows.length > 0) {
      await prisma.eventConsumption.createMany({ data: consumptionRows });
    }

    // Update InventoryReservation.quantityConsumed for matching items
    for (const row of consumptionRows) {
      await prisma.inventoryReservation.updateMany({
        where: {
          tenantId,
          eventId: po.eventId,
          productId: row.itemCode,
        },
        data: {
          quantityConsumed: row.quantityConsumed,
          status: "CONSUMED",
        },
      });
    }

    // Close schedules + capture delays
    const now = new Date();
    const delays: ProductionExecutionResult["delays"] = [];
    for (const sch of po.schedules) {
      const delayMs = now.getTime() - sch.scheduledEnd.getTime();
      const delayMinutes = Math.max(0, Math.round(delayMs / 60000));
      const scheduleStatus = delayMinutes > 30 ? "DELAYED" : "COMPLETED";
      await prisma.productionSchedule.update({
        where: { id: sch.id },
        data: {
          status: scheduleStatus,
          actualStart: sch.scheduledStart,
          actualEnd: now,
          delayReason: delayMinutes > 30 ? `Concluída com ${delayMinutes} min de atraso` : null,
        },
      });
      if (delayMinutes > 30) {
        delays.push({
          scheduleId: sch.id,
          stationName: sch.station.name,
          delayMinutes,
        });
      }
    }

    // Update ProductionOrder status
    await prisma.productionOrder.update({
      where: { id: productionOrderId },
      data: {
        status: "COMPLETED",
        actualReadyAt: now,
      },
    });

    logger.info(
      {
        productionOrderId,
        eventId: po.eventId,
        items: itemsExecuted,
        consumption: consumptionRows.length,
      },
      "ProductionEngine: production completed → consumption recorded"
    );

    return {
      productionOrderId,
      eventId: po.eventId,
      itemsExecuted,
      consumptionRecordsCreated: consumptionRows.length,
      totalProduced: round2(totalProduced),
      totalWasted: round2(totalWasted),
      totalActualCost: round2(totalActualCost),
      delays,
      completedAt: now,
    };
  }

  /**
   * Get current station load (utilization) for a given date.
   * Useful for capacity dashboards.
   */
  async getStationLoad(
    tenantId: string,
    date: Date
  ): Promise<Array<{ stationName: string; loadHours: number; maxHours: number; utilizationPct: number }>> {
    const dayStart = new Date(date);
    dayStart.setHours(0, 0, 0, 0);
    const dayEnd = new Date(dayStart);
    dayEnd.setHours(23, 59, 59, 999);

    const stations = await prisma.productionStation.findMany({
      where: { tenantId, isActive: true },
    });

    const result = [];
    for (const s of stations) {
      const agg = await prisma.productionSchedule.aggregate({
        where: {
          tenantId,
          stationId: s.id,
          scheduledStart: { gte: dayStart, lte: dayEnd },
          status: { not: "CANCELLED" },
        },
        _sum: { estimatedHours: true },
      });
      const load = agg._sum.estimatedHours ?? 0;
      result.push({
        stationName: s.name,
        loadHours: round1(load),
        maxHours: s.maxHoursPerDay,
        utilizationPct: round1((load / s.maxHoursPerDay) * 100),
      });
    }
    return result;
  }
}

// ---- helpers ----
function round1(n: number) { return Math.round(n * 10) / 10; }
function round2(n: number) { return Math.round(n * 100) / 100; }

export const productionEngine = new ProductionEngine();
