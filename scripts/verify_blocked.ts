import { PrismaClient } from "@prisma/client";
const p = new PrismaClient();
(async () => {
  const pos = await p.purchaseOrder.count({
    where: { tenantId: "qopera", relatedEventId: "QOPERA-SPRINT3-BLOCKED" }
  });
  console.log(`POs for BLOCKED event: ${pos} (expected 0 — margin 3% < 8% threshold)`);
  await p.$disconnect();
})();
