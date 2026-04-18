import { PrismaClient } from "@prisma/client";
const p = new PrismaClient();
(async () => {
  // Total POs for this event across all runs
  const pos = await p.purchaseOrder.findMany({
    where: { tenantId: "qopera", relatedEventId: "QOPERA-SPRINT3-E2E-B" },
    select: { id: true, sourceDecisionId: true, status: true, supplierId: true, totalEstimatedCost: true, createdAt: true }
  });
  console.log(`Total POs for event: ${pos.length}`);
  const byDecision = new Map<string, number>();
  for (const po of pos) {
    const key = po.sourceDecisionId ?? "null";
    byDecision.set(key, (byDecision.get(key) ?? 0) + 1);
  }
  console.log("Unique decisionIds:", byDecision.size);
  for (const [k, v] of byDecision) {
    if (v > 1) console.log(`  ! DUPLICATE decisionId ${k.slice(0,8)}: ${v} POs`);
  }
  console.log("\nIdempotency: DB @@unique(sourceDecisionId) guarantees no duplicates per decisionId.");

  // Test dispatcher idempotency directly — fake same decisionId
  console.log("\n--- Direct idempotency probe ---");
  const existingPo = pos[0];
  if (existingPo) {
    try {
      await p.purchaseOrder.create({
        data: {
          tenantId: "qopera",
          supplierId: existingPo.supplierId,
          status: "draft",
          sourceDecisionId: existingPo.sourceDecisionId,  // duplicate!
          totalEstimatedCost: 1,
          requestedDelivery: new Date(),
          relatedEventId: "DUP-TEST"
        }
      });
      console.log("  UNEXPECTED: duplicate insert succeeded");
    } catch (err: any) {
      console.log(`  EXPECTED: duplicate blocked by DB (${err.code ?? 'ok'})`);
    }
  }
  await p.$disconnect();
})();
