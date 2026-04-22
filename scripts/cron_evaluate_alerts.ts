// ============================================================
// Cron: evaluate + dispatch operational alerts for all upcoming events.
// Invocation: `npx tsx scripts/cron_evaluate_alerts.ts`
// Intended to be scheduled (e.g. Fly.io scheduled machines, systemd timer,
// k8s CronJob) every 15–30 minutes.
// ============================================================
import { prisma } from "../src/db";
import { alertEngine } from "../src/core/alert-engine";
import { forecastEngine } from "../src/intelligence";
import { logger } from "../src/utils/logger";

const HORIZON_DAYS = Number(process.env.ALERT_HORIZON_DAYS ?? 14);

interface TenantStats {
  tenantId: string;
  eventsEvaluated: number;
  alertsRaised: number;
  dispatched: number;
  failed: number;
}

async function evaluateTenant(tenantId: string): Promise<TenantStats> {
  const stats: TenantStats = {
    tenantId,
    eventsEvaluated: 0,
    alertsRaised: 0,
    dispatched: 0,
    failed: 0,
  };

  const horizon = new Date();
  horizon.setDate(horizon.getDate() + HORIZON_DAYS);

  const events = await prisma.event.findMany({
    where: {
      tenantId,
      eventDate: { gte: new Date(), lte: horizon },
      status: { notIn: ["cancelled", "completed"] },
    },
    select: { id: true, eventType: true, guests: true },
  });

  for (const event of events) {
    try {
      const forecast = await forecastEngine.forecastEvent(
        tenantId,
        event.eventType ?? "corporativo",
        event.guests ?? 100,
        6,
        event.id,
      );

      const inventory = await prisma.inventoryItem.findMany();
      const byCode = new Map(inventory.map((i) => [i.code, i]));
      const stock = forecast.forecasts.map((f) => {
        const inv = byCode.get(f.itemCode);
        return {
          itemCode: f.itemCode,
          itemName: f.itemName,
          onHand: inv?.currentQty ?? 0,
          required: f.estimatedConsumption,
          safetyStock: inv?.minStockLevel ?? undefined,
        };
      });

      const alerts = alertEngine.evaluateOperational({
        tenantId,
        eventId: event.id,
        stock,
      });

      stats.eventsEvaluated++;
      stats.alertsRaised += alerts.length;

      if (alerts.length === 0) continue;

      const delivery = await alertEngine.dispatchAlerts(alerts, {
        tenantId,
        eventId: event.id,
      });
      stats.dispatched += delivery.filter((d) => d.ok).length;
      stats.failed += delivery.filter((d) => !d.ok && !d.skipped).length;
    } catch (err) {
      logger.error("cron_evaluate_alerts: event failed", {
        eventId: event.id,
        err: err instanceof Error ? err.message : String(err),
      });
      stats.failed++;
    }
  }

  return stats;
}

async function main() {
  const started = Date.now();
  console.log(
    `⏰ cron_evaluate_alerts started horizon=${HORIZON_DAYS}d`,
  );

  // Enumerate tenants that have at least one upcoming event.
  const rows = await prisma.event.groupBy({
    by: ["tenantId"],
    where: {
      eventDate: {
        gte: new Date(),
        lte: new Date(Date.now() + HORIZON_DAYS * 86400_000),
      },
    },
  });

  const tenants = rows.map((r) => r.tenantId);
  if (tenants.length === 0) {
    console.log("no tenants with upcoming events — exiting clean");
    return;
  }

  const results: TenantStats[] = [];
  for (const tenantId of tenants) {
    const stats = await evaluateTenant(tenantId);
    results.push(stats);
    console.log(
      `  ${tenantId.slice(0, 8)}…  events=${stats.eventsEvaluated} alerts=${stats.alertsRaised} delivered=${stats.dispatched} failed=${stats.failed}`,
    );
  }

  const total = results.reduce(
    (acc, r) => ({
      eventsEvaluated: acc.eventsEvaluated + r.eventsEvaluated,
      alertsRaised: acc.alertsRaised + r.alertsRaised,
      dispatched: acc.dispatched + r.dispatched,
      failed: acc.failed + r.failed,
    }),
    { eventsEvaluated: 0, alertsRaised: 0, dispatched: 0, failed: 0 },
  );

  const elapsed = Date.now() - started;
  console.log(
    `\n✅ done tenants=${tenants.length} events=${total.eventsEvaluated} alerts=${total.alertsRaised} delivered=${total.dispatched} failed=${total.failed} elapsedMs=${elapsed}`,
  );

  if (total.failed > 0) process.exit(2);
}

main()
  .catch((err) => {
    console.error("❌ cron_evaluate_alerts failed", err);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
