import { PrismaClient } from "@prisma/client";
const p = new PrismaClient();
(async () => {
  const pos = await p.purchaseOrder.findMany({
    where: { tenantId: "qopera", relatedEventId: "QOPERA-SPRINT3-E2E-B" },
    include: { supplier: { select: { name: true, code: true, reliabilityScore: true } }, items: true }
  });
  console.log(`\n=== ${pos.length} PO(s) for QOPERA-SPRINT3-E2E-B ===`);
  for (const po of pos) {
    const m = po.metadata as any;
    console.log(`\nPO ${po.id.slice(0,8)} [${po.status}] supplier=${po.supplier?.name ?? 'NULL'} (${po.supplier?.code ?? '-'})`);
    console.log(`  totalCost: R$${po.totalEstimatedCost} | items: ${po.items.length}`);
    console.log(`  selectionReason: ${(m?.selectionReason ?? '').slice(0,100)}...`);
    console.log(`  alternatives: ${(m?.alternatives ?? []).map((a:any)=>`${a.supplierName}(score=${a.finalScore})`).join(', ') || 'none'}`);
  }
  // OperationalDecision audit
  const ops = await p.operationalDecision.findMany({
    where: { tenantId: "qopera" },
    orderBy: { createdAt: "desc" },
    take: 3
  });
  console.log(`\n=== ${ops.length} recent OperationalDecision ===`);
  for (const op of ops) {
    const pl = op.payload as any;
    console.log(`  ${op.action} [${op.riskLevel}] PO=${pl?.purchaseOrderId?.slice(0,8)} supplier=${pl?.supplierName} alts=${(pl?.alternatives??[]).length}`);
  }
  await p.$disconnect();
})();
