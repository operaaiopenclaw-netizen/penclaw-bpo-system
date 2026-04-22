// ============================================================
// SPRINT 6 — Operation Layer E2E validator
// Lifecycle:
//   webhook(event.create) → forecast → risks → alerts(dispatch)
//   → consumption(webhook) → reconcile → overview → channels
// ============================================================
import { prisma } from "../src/db";
import { alertEngine } from "../src/core/alert-engine";
import { notificationDispatcher } from "../src/channels";
import { forecastEngine, reconciliationEngine } from "../src/intelligence";

const TENANT = "qopera-sprint6";
const EVENT_ID = "QOPERA-SPRINT6-E2E";
const EVENT_TYPE = "casamento";
const GUESTS = 200;
const REVENUE = 180_000;

const EVENT_DATE = new Date();
EVENT_DATE.setDate(EVENT_DATE.getDate() + 7);

const ITEMS = [
  { code: "cerveja", name: "Cerveja", category: "beverage_alcohol", unit: "L", qty: 400, unitPrice: 15 },
  { code: "soft", name: "Refrigerante", category: "beverage_soft", unit: "L", qty: 240, unitPrice: 8 },
  { code: "agua", name: "Água", category: "beverage_water", unit: "L", qty: 160, unitPrice: 4 },
  { code: "gelo", name: "Gelo", category: "consumable", unit: "kg", qty: 240, unitPrice: 5 },
];

function header(n: number, title: string) {
  console.log(`\n${"═".repeat(70)}`);
  console.log(`  [${n}] ${title}`);
  console.log("═".repeat(70));
}

async function cleanup() {
  const evt = await prisma.event.findFirst({
    where: { tenantId: TENANT, eventId: EVENT_ID },
    select: { id: true },
  });
  const pk = evt?.id;
  if (!pk) return;
  await prisma.$transaction([
    prisma.reconciliationReport.deleteMany({ where: { eventId: pk } }),
    prisma.forecastAccuracy.deleteMany({ where: { eventId: pk } }),
    prisma.eventConsumption.deleteMany({ where: { eventId: pk } }),
    prisma.event.deleteMany({ where: { id: pk } }),
    prisma.itemAdjustment.deleteMany({
      where: { tenantId: TENANT, eventType: EVENT_TYPE },
    }),
  ]);
}

async function seedInventory() {
  for (const it of ITEMS) {
    // Seed with short supply for "cerveja" to trigger ESTOQUE_INSUFICIENTE
    const onHand = it.code === "cerveja" ? it.qty * 0.4 : it.qty * 1.2;
    await prisma.inventoryItem.upsert({
      where: { code: it.code },
      update: { currentQty: onHand, unit: it.unit, unitPrice: it.unitPrice },
      create: {
        code: it.code,
        name: it.name,
        currentQty: onHand,
        unit: it.unit,
        unitPrice: it.unitPrice,
        minStockLevel: it.qty * 0.2,
        reorderPoint: it.qty * 0.3,
      },
    });
  }
}

async function main() {
  console.log("\n🎛️  SPRINT 6 — Operation Layer E2E");
  console.log(`tenant=${TENANT} event=${EVENT_ID} guests=${GUESTS}`);

  await cleanup();
  await seedInventory();

  // ---------- 1) Webhook simulado: event.create ----------
  header(1, "webhook(event.create) → Event row");
  const event = await prisma.event.create({
    data: {
      tenantId: TENANT,
      costCenterId: "default",
      name: "Sprint6 E2E Event",
      eventType: EVENT_TYPE,
      eventDate: EVENT_DATE,
      guests: GUESTS,
      revenueTotal: REVENUE,
      marginPct: 25.0,
      status: "planned",
    },
  });
  console.log(`✅ Event criado id=${event.id}`);

  // ---------- 2) Forecast direto pelo engine ----------
  header(2, "forecastEngine.forecastEvent");
  const forecast = await forecastEngine.forecastEvent(
    TENANT,
    EVENT_TYPE,
    GUESTS,
    6,
    event.id
  );
  console.log(`Forecast items=${forecast.forecasts.length} confidence=${(forecast.overallConfidence * 100).toFixed(0)}%`);
  forecast.forecasts.slice(0, 5).forEach((f) =>
    console.log(`  • ${f.itemCode.padEnd(12)} ${f.estimatedConsumption.toFixed(1)} ${f.unit}`)
  );

  // ---------- 3) Evaluate operational alerts ----------
  header(3, "alertEngine.evaluateOperational (stock/overload/margin)");
  // Build a synthetic context that mirrors what /operations/risks computes
  const inv = await prisma.inventoryItem.findMany();
  const byCode = new Map(inv.map((i) => [i.code, i]));

  const stock = forecast.forecasts.map((it) => {
    const inventoryItem = byCode.get(it.itemCode);
    return {
      itemCode: it.itemCode,
      itemName: it.itemName,
      onHand: inventoryItem?.currentQty ?? 0,
      required: it.estimatedConsumption,
      safetyStock: inventoryItem?.minStockLevel ?? undefined,
    };
  });

  const stations = [
    { stationId: "st-kitchen", stationName: "kitchen", loadHours: 14, capacityHours: 12 },
    { stationId: "st-bar", stationName: "bar", loadHours: 7, capacityHours: 10 },
  ];

  const alerts = alertEngine.evaluateOperational({
    tenantId: TENANT,
    eventId: event.id,
    stock,
    stations,
    margin: { projectedPct: 25, realPct: null, deltaPct: null },
    reconciliation: { highVariances: [], overallAccuracyScore: undefined },
  });

  console.log(`Alertas gerados: ${alerts.length}`);
  alerts.forEach((a) =>
    console.log(`  ${a.severity.padEnd(8)} ${a.rule.padEnd(28)} ${a.message}`)
  );

  // ---------- 4) Channels + dispatch ----------
  header(4, "notificationDispatcher.listChannels + dispatchAlerts");
  const channels = notificationDispatcher.listChannels();
  channels.forEach((c) =>
    console.log(`  • ${c.name.padEnd(10)} ${c.configured ? "🟢 configured" : "⚪ skipped"}`)
  );
  const delivery = await alertEngine.dispatchAlerts(alerts, {
    tenantId: TENANT,
    eventId: event.id,
  });
  const ok = delivery.filter((d) => d.ok).length;
  const skipped = delivery.filter((d) => d.skipped).length;
  const failed = delivery.filter((d) => !d.ok && !d.skipped).length;
  console.log(`Dispatch: delivered=${ok} skipped=${skipped} failed=${failed}`);

  // ---------- 5) Consumption webhook (simulado) ----------
  header(5, "webhook(consumption.update) — simulated");
  const consumptionRows = ITEMS.map((it) => {
    // Simulate 10-30% variance from forecast
    const forecastItem = forecast.forecasts.find((f) => f.itemCode === it.code);
    const base = forecastItem?.estimatedConsumption ?? it.qty;
    const variance = (Math.random() - 0.4) * 0.4; // -16% a +24%
    const consumed = Math.max(0, base * (1 + variance));
    const wasted = consumed * 0.08;
    return {
      tenantId: TENANT,
      eventId: event.id,
      itemCode: it.code,
      itemName: it.name,
      category: it.category,
      unit: it.unit,
      quantityConsumed: consumed,
      quantityWasted: wasted,
      quantityReturned: 0,
    };
  });

  await prisma.eventConsumption.createMany({ data: consumptionRows });
  console.log(`✅ ${consumptionRows.length} linhas de consumo registradas`);

  // ---------- 6) Reconcile → learning loop ----------
  header(6, "reconciliationEngine.reconcileEvent");
  const report = await reconciliationEngine.reconcileEvent(TENANT, event.id);
  console.log(`Itens reconciliados: ${report.items.length}`);
  console.log(`Mean accuracy: ${report.accuracy.overall.toFixed(1)}%`);
  console.log(`Margem projetada: ${report.financials.projectedMargin?.toFixed(1) ?? "—"}%`);
  console.log(`Margem real: ${report.financials.realMargin?.toFixed(1) ?? "—"}%`);
  console.log(`Ajustes aplicados: ${report.adjustmentsApplied.length}`);

  // ---------- 7) Re-evaluate risks com margem real ----------
  header(7, "Re-avaliação de riscos após reconciliation");
  const postAlerts = alertEngine.evaluateOperational({
    tenantId: TENANT,
    eventId: event.id,
    margin: {
      projectedPct: report.financials.projectedMargin,
      realPct: report.financials.realMargin,
      deltaPct: report.financials.marginDelta,
    },
  });
  console.log(`Alertas pós-reconciliation: ${postAlerts.length}`);
  postAlerts.forEach((a) =>
    console.log(`  ${a.severity.padEnd(8)} ${a.rule.padEnd(28)} ${a.message}`)
  );

  // ---------- 8) Summary ----------
  header(8, "SPRINT 6 SUMMARY");
  const adjustments = await prisma.itemAdjustment.findMany({
    where: { tenantId: TENANT, eventType: EVENT_TYPE },
    orderBy: { lastUpdated: "desc" },
  });
  console.log(`ItemAdjustments aprendidos: ${adjustments.length}`);
  adjustments.forEach((a) =>
    console.log(
      `  ${a.itemCode.padEnd(12)} factor=${a.factor.toFixed(3)} samples=${a.sampleSize}`
    )
  );
  console.log("\n✅ Sprint 6 E2E complete");
}

main()
  .catch((err) => {
    console.error("❌ verify_sprint6 failed", err);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
