// ============================================================
// SPRINT 4 — Reconciliation Loop E2E validator
// forecast → execute → measure → learn → improve
// ============================================================
import { prisma } from "../src/db";
import { forecastEngine, reconciliationEngine } from "../src/intelligence";

const TENANT = "qopera";
const EVENT_ID = "QOPERA-SPRINT4-E2E";
const EVENT_TYPE = "casamento";
const GUESTS = 150;
const DURATION = 6;
const REVENUE = 120_000;

async function cleanup() {
  await prisma.$transaction([
    prisma.reconciliationReport.deleteMany({ where: { eventId: EVENT_ID } }),
    prisma.forecastAccuracy.deleteMany({ where: { eventId: EVENT_ID } }),
    prisma.eventConsumption.deleteMany({ where: { eventId: EVENT_ID } }),
    prisma.eventConsumptionHistory.deleteMany({ where: { eventId: EVENT_ID } }),
    prisma.purchaseOrderItem.deleteMany({
      where: { purchaseOrder: { relatedEventId: EVENT_ID } },
    }),
    prisma.purchaseOrder.deleteMany({ where: { relatedEventId: EVENT_ID } }),
    prisma.event.deleteMany({ where: { tenantId: TENANT, eventId: EVENT_ID } }),
    prisma.memoryItem.deleteMany({
      where: { companyId: TENANT, sourceType: "reconciliation", sourceRef: EVENT_TYPE },
    }),
    // Reset item adjustments so the run is reproducible
    prisma.itemAdjustment.deleteMany({
      where: { tenantId: TENANT, eventType: EVENT_TYPE },
    }),
  ]);
}

async function seedEvent() {
  return prisma.event.create({
    data: {
      eventId: EVENT_ID,
      tenantId: TENANT,
      costCenterId: "qopera-cc",
      name: "E2E Casamento Sprint 4",
      eventType: EVENT_TYPE,
      eventDate: new Date(),
      guests: GUESTS,
      status: "completed",
      revenueTotal: REVENUE,
      cmvTotal: 45_000,
      marginPct: 62.5,
    },
  });
}

async function seedPurchaseOrder(forecastItems: { itemCode: string; estimatedConsumption: number }[]) {
  // Pick first active supplier with category beverage_alcohol
  const supplier = await prisma.supplier.findFirst({
    where: { tenantId: TENANT, isActive: true },
  });
  if (!supplier) throw new Error("No supplier seeded — run seed_qopera_suppliers first");

  // Purchase exactly what the forecast said (so we can measure purchase vs consumption)
  return prisma.purchaseOrder.create({
    data: {
      tenantId: TENANT,
      supplierId: supplier.id,
      status: "delivered",
      relatedEventId: EVENT_ID,
      totalEstimatedCost: 25_000,
      totalActualCost: 25_000,
      items: {
        create: forecastItems.map(f => ({
          itemCode: f.itemCode,
          itemName: f.itemCode,
          category: "beverage_alcohol",
          quantityOrdered: f.estimatedConsumption,
          quantityReceived: f.estimatedConsumption,
          unit: "L",
          unitPrice: 12,
          totalPrice: f.estimatedConsumption * 12,
          status: "delivered",
        })),
      },
    },
    include: { items: true },
  });
}

async function seedConsumption(forecastItems: { itemCode: string; itemName: string; category: string; unit: string; estimatedConsumption: number }[]) {
  // Simulate reality: cerveja consumed +30% (under-forecast), soft -15% (over-forecast),
  // gelo +10%, destilado matched, agua matched, and cerveja wastes 20%.
  const deltas: Record<string, { consumedMul: number; wasteRatio: number }> = {
    cerveja:   { consumedMul: 1.30, wasteRatio: 0.20 },
    soft:      { consumedMul: 0.85, wasteRatio: 0.00 },
    agua:      { consumedMul: 1.00, wasteRatio: 0.00 },
    destilado: { consumedMul: 1.00, wasteRatio: 0.00 },
    gelo:      { consumedMul: 1.10, wasteRatio: 0.05 },
    espumante: { consumedMul: 0.90, wasteRatio: 0.00 },
    suco:      { consumedMul: 1.05, wasteRatio: 0.00 },
  };

  const data = forecastItems.map(f => {
    const d = deltas[f.itemCode] ?? { consumedMul: 1.0, wasteRatio: 0 };
    const consumed = +(f.estimatedConsumption * d.consumedMul).toFixed(2);
    const wasted = +(consumed * d.wasteRatio).toFixed(2);
    return {
      tenantId: TENANT,
      eventId: EVENT_ID,
      itemCode: f.itemCode,
      itemName: f.itemName,
      category: f.category,
      unit: f.unit,
      quantityConsumed: consumed,
      quantityWasted: wasted,
      quantityReturned: 0,
    };
  });

  await prisma.eventConsumption.createMany({ data });
}

async function main() {
  console.log("\n=== SPRINT 4 — Consumption Reconciliation Loop ===\n");

  console.log("[0] Cleanup prior state...");
  await cleanup();

  // ---- 1. Forecast BEFORE reconciliation (raw) ----
  console.log("[1] Initial forecast (pre-reconciliation)...");
  const baselineForecast = await forecastEngine.forecastEvent(
    TENANT, EVENT_TYPE, GUESTS, DURATION, EVENT_ID,
    { useLearnedAdjustments: false }
  );
  const baselineByCode = new Map(baselineForecast.forecasts.map(f => [f.itemCode, f]));

  // ---- 2. Seed event + PO + consumption ----
  console.log("[2] Seed event, PO (delivered), consumption records...");
  await seedEvent();
  await seedPurchaseOrder(baselineForecast.forecasts);
  await seedConsumption(baselineForecast.forecasts);

  // ---- 3. Reconcile ----
  console.log("[3] Running ReconciliationEngine...\n");
  const report = await reconciliationEngine.reconcileEvent(TENANT, EVENT_ID);

  // ---- 4. Forecast AFTER reconciliation (with learned adjustments) ----
  console.log("[4] Forecast AFTER learning applied...\n");
  const adjustedForecast = await forecastEngine.forecastEvent(
    TENANT, EVENT_TYPE, GUESTS, DURATION, EVENT_ID + "-next"
  );

  // ========== OUTPUTS ==========

  console.log("━".repeat(70));
  console.log("1️⃣  MODELS CREATED");
  console.log("━".repeat(70));
  const modelCounts = {
    EventConsumption: await prisma.eventConsumption.count({ where: { eventId: EVENT_ID } }),
    ForecastAccuracy: await prisma.forecastAccuracy.count({ where: { eventId: EVENT_ID } }),
    ItemAdjustment: await prisma.itemAdjustment.count({ where: { tenantId: TENANT, eventType: EVENT_TYPE } }),
    ReconciliationReport: await prisma.reconciliationReport.count({ where: { eventId: EVENT_ID } }),
  };
  console.log(modelCounts);

  console.log("\n" + "━".repeat(70));
  console.log("2️⃣  RECONCILIATION OUTPUT (per item)");
  console.log("━".repeat(70));
  console.table(
    report.items.map(i => ({
      item: i.itemName,
      forecast: i.forecast,
      purchased: i.purchased,
      consumed: i.consumed,
      wasted: i.wasted,
      variance: i.variance,
      "variance%": (i.variancePct * 100).toFixed(1) + "%",
      accuracy: i.accuracyScore,
    }))
  );

  console.log("\n" + "━".repeat(70));
  console.log("3️⃣  ACCURACY METRICS");
  console.log("━".repeat(70));
  console.log(`  overall:    ${report.accuracy.overall}`);
  console.log(`  byCategory: ${JSON.stringify(report.accuracy.byCategory)}`);
  console.log(`  byEventType:${JSON.stringify(report.accuracy.byEventType)}`);

  console.log("\n" + "━".repeat(70));
  console.log("4️⃣  FORECAST ADJUSTMENT — next run reflects learning");
  console.log("━".repeat(70));
  console.table(
    adjustedForecast.forecasts.map(f => {
      const baseline = baselineByCode.get(f.itemCode);
      const prev = baseline?.estimatedConsumption ?? 0;
      const next = f.estimatedConsumption;
      const applied = report.adjustmentsApplied.find(a => a.itemCode === f.itemCode);
      return {
        item: f.itemName,
        "prev_est": prev,
        "next_est": next,
        "delta": +(next - prev).toFixed(2),
        "factor": applied?.newFactor ?? 1.0,
      };
    })
  );

  console.log("\n" + "━".repeat(70));
  console.log("5️⃣  SUPPLIER SCORE UPDATE");
  console.log("━".repeat(70));
  for (const sf of report.supplierFeedback) {
    console.log(`  ${sf.supplierName}:`);
    console.log(`    previousReliability: ${sf.previousReliability}`);
    console.log(`    newReliability:      ${sf.newReliability}`);
    console.log(`    deliveryAccuracy:    ${sf.deliveryAccuracyPct}%`);
    console.log(`    quantityVariance:    ${(sf.quantityVariancePct * 100).toFixed(1)}%`);
    console.log(`    itemsEvaluated:      ${sf.itemsEvaluated}`);
  }

  console.log("\n" + "━".repeat(70));
  console.log("6️⃣  FINANCIAL REALITY");
  console.log("━".repeat(70));
  console.log(`  projected cost:   R$ ${report.financials.projectedCost}`);
  console.log(`  real cost:        R$ ${report.financials.realCost}`);
  console.log(`  waste cost:       R$ ${report.financials.wasteCost}`);
  console.log(`  revenue:          R$ ${report.financials.revenue}`);
  console.log(`  projected margin: ${report.financials.projectedMargin}%`);
  console.log(`  real margin:      ${report.financials.realMargin}%`);
  console.log(`  margin delta:     ${report.financials.marginDelta}pp`);

  console.log("\n" + "━".repeat(70));
  console.log("7️⃣  MEMORY ENTRIES");
  console.log("━".repeat(70));
  for (const m of report.memoryEntries) {
    console.log(`  [${m.memoryType}] ${m.title}`);
    console.log(`    ${m.content}`);
    console.log(`    tags=${JSON.stringify(m.tags)} confidence=${m.confidenceScore}`);
  }
  if (report.memoryEntries.length === 0) console.log("  (none)");

  console.log("\n✅ Sprint 4 reconciliation loop VERIFIED\n");
  await prisma.$disconnect();
}

main().catch(err => {
  console.error("Sprint 4 verify failed:", err);
  process.exit(1);
});
