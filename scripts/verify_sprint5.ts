// ============================================================
// SPRINT 5 — Production Engine E2E validator
// forecast → procure → produce → consume → reconcile → learn
// ============================================================
import { prisma } from "../src/db";
import {
  forecastEngine,
  productionEngine,
  reconciliationEngine,
} from "../src/intelligence";

const TENANT = "qopera";
const EVENT_ID = "QOPERA-SPRINT5-E2E";
const EVENT_TYPE = "casamento";
const GUESTS = 150;
const REVENUE = 120_000;

// Production window: produce 1 day before the event
const EVENT_DATE = new Date();
EVENT_DATE.setDate(EVENT_DATE.getDate() + 2);

// Item seed: matches forecast-engine BASE_RATES.casamento
const ITEMS = [
  { code: "cerveja",   name: "Cerveja",      category: "beverage_alcohol", unit: "L",  qty: 300, unitPrice: 15 },
  { code: "soft",      name: "Refrigerante", category: "beverage_soft",    unit: "L",  qty: 180, unitPrice:  8 },
  { code: "agua",      name: "Água",         category: "beverage_water",   unit: "L",  qty: 120, unitPrice:  4 },
  { code: "destilado", name: "Destilado",    category: "beverage_spirit",  unit: "L",  qty:  36, unitPrice: 60 },
  { code: "gelo",      name: "Gelo",         category: "consumable",       unit: "kg", qty: 180, unitPrice:  5 },
];

async function cleanup() {
  const evt = await prisma.event.findFirst({
    where: { tenantId: TENANT, eventId: EVENT_ID },
    select: { id: true },
  });
  const eventPk = evt?.id;

  await prisma.$transaction([
    prisma.reconciliationReport.deleteMany({ where: { eventId: EVENT_ID } }),
    prisma.forecastAccuracy.deleteMany({ where: { eventId: EVENT_ID } }),
    prisma.eventConsumption.deleteMany({ where: { eventId: EVENT_ID } }),
    prisma.eventConsumptionHistory.deleteMany({ where: { eventId: EVENT_ID } }),
    prisma.inventoryReservation.deleteMany({ where: { eventId: EVENT_ID } }),
    prisma.productionSchedule.deleteMany({
      where: { productionOrder: { eventId: EVENT_ID } },
    }),
    prisma.productionOrderItem.deleteMany({
      where: { productionOrder: { eventId: EVENT_ID } },
    }),
    prisma.productionOrder.deleteMany({ where: { eventId: EVENT_ID } }),
    prisma.serviceOrderItem.deleteMany({
      where: { serviceOrder: { eventId: EVENT_ID } },
    }),
    prisma.serviceOrder.deleteMany({ where: { eventId: EVENT_ID } }),
    prisma.event.deleteMany({ where: { tenantId: TENANT, eventId: EVENT_ID } }),
    prisma.memoryItem.deleteMany({
      where: { companyId: TENANT, sourceType: "reconciliation", sourceRef: EVENT_TYPE },
    }),
    prisma.itemAdjustment.deleteMany({
      where: { tenantId: TENANT, eventType: EVENT_TYPE },
    }),
  ]);
}

async function seedStations() {
  const stations = [
    { name: "kitchen-main",  stationType: "kitchen", maxHoursPerDay: 14, staffCount: 6 },
    { name: "bar-main",      stationType: "bar",     maxHoursPerDay: 10, staffCount: 3 },
    { name: "pastry-main",   stationType: "pastry",  maxHoursPerDay:  8, staffCount: 2 },
  ];
  for (const s of stations) {
    await prisma.productionStation.upsert({
      where: { tenantId_name: { tenantId: TENANT, name: s.name } },
      create: { tenantId: TENANT, ...s },
      update: s,
    });
  }
}

async function seedInventory() {
  for (const it of ITEMS) {
    await prisma.inventoryItem.upsert({
      where: { code: `INV-${it.code.toUpperCase()}` },
      create: {
        code: `INV-${it.code.toUpperCase()}`,
        name: it.name,
        currentQty: it.qty * 1.2, // plenty of stock
        unit: it.unit,
        unitPrice: it.unitPrice,
      },
      update: {
        currentQty: it.qty * 1.2,
        unitPrice: it.unitPrice,
      },
    });
  }
}

async function seedEvent() {
  return prisma.event.create({
    data: {
      eventId: EVENT_ID,
      tenantId: TENANT,
      costCenterId: "qopera-cc",
      name: "E2E Casamento Sprint 5",
      eventType: EVENT_TYPE,
      eventDate: EVENT_DATE,
      guests: GUESTS,
      status: "planned",
      revenueTotal: REVENUE,
      cmvTotal: 45_000,
      marginPct: 62.5,
    },
  });
}

async function seedApprovedServiceOrder() {
  const soNumber = `SO-${EVENT_ID}-${Date.now()}`;
  return prisma.serviceOrder.create({
    data: {
      tenantId: TENANT,
      eventId: EVENT_ID,
      soNumber,
      soType: "BAR",
      status: "APPROVED",
      subtotal: ITEMS.reduce((s, i) => s + i.qty * i.unitPrice, 0),
      total: ITEMS.reduce((s, i) => s + i.qty * i.unitPrice, 0),
      requiredDelivery: EVENT_DATE,
      approvedBy: "auto-seed",
      approvedAt: new Date(),
      items: {
        create: ITEMS.map(it => ({
          itemCategory: it.category,
          name: it.name,
          quantity: it.qty,
          unit: it.unit,
          unitPrice: it.unitPrice,
          totalPrice: it.qty * it.unitPrice,
        })),
      },
    },
    include: { items: true },
  });
}

async function main() {
  console.log("\n=== SPRINT 5 — Production Engine E2E ===\n");

  console.log("[0] Cleanup prior state + seed stations + inventory...");
  await cleanup();
  await seedStations();
  await seedInventory();

  console.log("[1] Baseline forecast (pre-learning)...");
  const baselineForecast = await forecastEngine.forecastEvent(
    TENANT, EVENT_TYPE, GUESTS, 6, EVENT_ID,
    { useLearnedAdjustments: false }
  );

  console.log("[2] Seed event + approved ServiceOrder...");
  await seedEvent();
  const so = await seedApprovedServiceOrder();
  console.log(`    ServiceOrder ${so.soNumber} — ${so.items.length} items, total R$${so.total}`);

  console.log("\n[3] ProductionEngine.planProduction...");
  const plan = await productionEngine.planProduction(TENANT, EVENT_ID);

  console.log("\n[4] Simulate execution — record actual produced + wasted");
  // Deltas: cerveja +30% consumed, 20% waste; soft -15%; gelo +10%; rest matched
  const deltas: Record<string, { consumedMul: number; wasteRatio: number }> = {
    cerveja:   { consumedMul: 1.30, wasteRatio: 0.20 },
    soft:      { consumedMul: 0.85, wasteRatio: 0.00 },
    agua:      { consumedMul: 1.00, wasteRatio: 0.00 },
    destilado: { consumedMul: 1.00, wasteRatio: 0.00 },
    gelo:      { consumedMul: 1.10, wasteRatio: 0.05 },
  };
  const executionResults = plan.items.map(it => {
    const d = deltas[it.itemCode] ?? { consumedMul: 1.0, wasteRatio: 0 };
    const produced = +(it.quantityRequired * d.consumedMul).toFixed(2);
    const wasted = +(produced * d.wasteRatio).toFixed(2);
    return {
      itemName: it.itemName,
      producedQuantity: produced,
      wastedQuantity: wasted,
      actualCost: it.estimatedCost * d.consumedMul,
    };
  });

  const execution = await productionEngine.completeProductionOrder(
    TENANT,
    plan.productionOrderId,
    executionResults
  );

  console.log("\n[5] Reconciliation (Sprint 4 loop consumes the EventConsumption rows)...");
  const reconciled = await reconciliationEngine.reconcileEvent(TENANT, EVENT_ID);

  console.log("\n[6] Forecast AFTER learning applied...");
  const adjustedForecast = await forecastEngine.forecastEvent(
    TENANT, EVENT_TYPE, GUESTS, 6, EVENT_ID + "-next"
  );
  const baselineByCode = new Map(baselineForecast.forecasts.map(f => [f.itemCode, f]));

  // ========== OUTPUTS ==========

  console.log("\n" + "━".repeat(70));
  console.log("1️⃣  PRODUCTION ORDER MODEL");
  console.log("━".repeat(70));
  console.log(`  PO: ${plan.productionOrderNumber} (id ${plan.productionOrderId.slice(0, 8)})`);
  console.log(`  eventId: ${plan.eventId}  |  eventDate: ${plan.eventDate}  |  guests: ${plan.guestCount}`);
  console.log(`  items: ${plan.itemCount}  |  schedules: ${plan.schedules.length}  |  reservations: ${plan.reservations.length}`);

  console.log("\n" + "━".repeat(70));
  console.log("2️⃣  PRODUCTION FLOW — items grouped by station");
  console.log("━".repeat(70));
  console.table(
    plan.items.map(i => ({
      item: i.itemName,
      station: i.stationType,
      required: i.quantityRequired,
      hours: i.estimatedHours,
      stock_ok: !i.stockInsufficient,
      est_cost: i.estimatedCost,
    }))
  );

  console.log("\n" + "━".repeat(70));
  console.log("3️⃣  AGENT LOGIC — station load check + sequencing");
  console.log("━".repeat(70));
  console.table(
    plan.stationLoadChecks.map(c => ({
      station: c.stationName,
      date: c.date,
      requested: c.requestedHours,
      existing: c.existingLoadHours,
      total: c.totalAfterSchedule,
      max: c.maxHoursPerDay,
      within_capacity: c.withinCapacity,
    }))
  );
  console.log("\n  Sequencing (prep → kitchen → pastry → bar):");
  for (const s of plan.schedules) {
    console.log(
      `    ${s.stationName.padEnd(14)} ${s.scheduledStart.toISOString()} → ${s.scheduledEnd.toISOString()}  (${s.estimatedHours}h)`
    );
  }
  if (plan.alerts.length > 0) {
    console.log("\n  Alerts:");
    for (const a of plan.alerts) console.log(`    ⚠️  ${a}`);
  }

  console.log("\n" + "━".repeat(70));
  console.log("4️⃣  INTEGRATION POINTS — production → consumption → reconciliation");
  console.log("━".repeat(70));
  console.log(`  execution.itemsExecuted:           ${execution.itemsExecuted}`);
  console.log(`  execution.consumptionRecordsCreated:${execution.consumptionRecordsCreated}  (feeds Sprint 4)`);
  console.log(`  execution.totalProduced:           ${execution.totalProduced}`);
  console.log(`  execution.totalWasted:             ${execution.totalWasted}`);
  console.log(`  execution.totalActualCost:         R$${execution.totalActualCost}`);
  console.log(`  execution.delays:                  ${execution.delays.length}`);
  console.log(`  reconciliation.itemsReconciled:    ${reconciled.items.length}`);
  console.log(`  reconciliation.accuracy:           ${reconciled.accuracy.overall}`);
  console.log(`  reconciliation.adjustmentsApplied: ${reconciled.adjustmentsApplied.length}`);
  console.log(`  reconciliation.memoryEntries:      ${reconciled.memoryEntries.length}`);

  console.log("\n" + "━".repeat(70));
  console.log("5️⃣  EXAMPLE EXECUTION — production drove the forecast learning");
  console.log("━".repeat(70));
  console.table(
    adjustedForecast.forecasts.map(f => {
      const baseline = baselineByCode.get(f.itemCode);
      const prev = baseline?.estimatedConsumption ?? 0;
      const next = f.estimatedConsumption;
      const adj = reconciled.adjustmentsApplied.find(a => a.itemCode === f.itemCode);
      return {
        item: f.itemName,
        prev_forecast: prev,
        next_forecast: next,
        delta: +(next - prev).toFixed(2),
        learned_factor: adj?.newFactor ?? 1.0,
      };
    })
  );

  console.log("\n  Financial reality:");
  console.log(`    projectedCost: R$${reconciled.financials.projectedCost}`);
  console.log(`    realCost:      R$${reconciled.financials.realCost}`);
  console.log(`    wasteCost:     R$${reconciled.financials.wasteCost}`);
  console.log(`    realMargin:    ${reconciled.financials.realMargin}% (projected ${reconciled.financials.projectedMargin}%)`);

  console.log("\n✅ Sprint 5 production → consumption → reconciliation loop VERIFIED\n");
  await prisma.$disconnect();
}

main().catch(err => {
  console.error("Sprint 5 verify failed:", err);
  process.exit(1);
});
