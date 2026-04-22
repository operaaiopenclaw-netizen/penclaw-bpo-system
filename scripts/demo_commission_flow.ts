import { PrismaClient } from "@prisma/client";
import {
  onContractSigned,
  onPaymentConfirmed,
  onContractCancelled,
  releaseDueLocks,
} from "../src/services/commission-engine";
import { computeBonusAccrual } from "../src/services/bonus-engine";

// Demo end-to-end do fluxo Comercial↔Financeiro.
// Roda contra o DB local (DATABASE_URL do .env) e cria:
//  - 3 users (closer, sdr, gerente)
//  - 1 lead → proposal → contract (R$ 100k, margem R$ 30k)
//  - 3 installments (40/30/30)
//  - CommissionPlan 5% sobre MARGIN, split SDR 30%, manager override 10%
//  - Confirma pagamento da parcela 1 → libera comissão pro-rata
//  - Cancela contrato → clawback
//  - Computa bonus mensal com 2 componentes
//
// Uso: npx ts-node scripts/demo_commission_flow.ts
// Seguro para re-rodar: todos os registros vão para tenant = "demo-commercial".

const p = new PrismaClient();
const TENANT = "demo-commercial";

async function cleanup(): Promise<void> {
  // Ordem: filhos antes dos pais
  await p.provisionedExpense.deleteMany({ where: { tenantId: TENANT } });
  await p.bonusAccrual.deleteMany({ where: { tenantId: TENANT } });
  await p.bonusComponent.deleteMany({
    where: { bonusRule: { tenantId: TENANT } },
  });
  await p.bonusRule.deleteMany({ where: { tenantId: TENANT } });
  await p.commissionEntry.deleteMany({ where: { tenantId: TENANT } });
  await p.commissionPlan.deleteMany({ where: { tenantId: TENANT } });
  await p.payment.deleteMany({ where: { tenantId: TENANT } });
  await p.contractInstallment.deleteMany({ where: { tenantId: TENANT } });
  await p.contract.deleteMany({ where: { tenantId: TENANT } });
  await p.proposalItem.deleteMany({
    where: { proposal: { tenantId: TENANT } },
  });
  await p.proposal.deleteMany({ where: { tenantId: TENANT } });
  await p.lead.deleteMany({ where: { tenantId: TENANT } });
  await p.user.deleteMany({ where: { tenantId: TENANT } });
}

async function main(): Promise<void> {
  console.log("=== cleanup previous demo ===");
  await cleanup();

  console.log("=== seed users ===");
  const closer = await p.user.create({
    data: {
      tenantId: TENANT,
      email: "closer@demo.local",
      name: "Ana Closer",
      passwordHash: "x",
      role: "sales",
    },
  });
  const sdr = await p.user.create({
    data: {
      tenantId: TENANT,
      email: "sdr@demo.local",
      name: "Bruno SDR",
      passwordHash: "x",
      role: "sdr",
    },
  });
  const manager = await p.user.create({
    data: {
      tenantId: TENANT,
      email: "mgr@demo.local",
      name: "Carla Manager",
      passwordHash: "x",
      role: "sales_manager",
    },
  });
  await p.user.update({
    where: { id: closer.id },
    data: { managerId: manager.id },
  });
  await p.user.update({
    where: { id: sdr.id },
    data: { managerId: manager.id },
  });

  console.log("=== create lead/proposal/contract ===");
  const lead = await p.lead.create({
    data: {
      tenantId: TENANT,
      companyName: "Acme Eventos",
      contactName: "João Acme",
      status: "QUALIFIED",
      assignedTo: closer.id,
    },
  });
  const proposal = await p.proposal.create({
    data: {
      tenantId: TENANT,
      leadId: lead.id,
      proposalNumber: `DEMO-${Date.now()}`,
      subtotal: 100000,
      totalAmount: 100000,
      validUntil: new Date(Date.now() + 30 * 86400000),
      discountAppliedPct: 0.05, // desconto menor que threshold, sem penalty
      items: {
        create: [
          {
            itemType: "catering",
            name: "Jantar 200 convidados",
            quantity: 200,
            unitPrice: 500,
            totalPrice: 100000,
            estimatedCost: 70000,
          },
        ],
      },
    },
  });

  const signedAt = new Date();
  const contract = await p.contract.create({
    data: {
      tenantId: TENANT,
      proposalId: proposal.id,
      leadId: lead.id,
      contractNumber: `DEMO-CTR-${Date.now()}`,
      signedAt,
      totalValue: 100000,
      projectedMargin: 30000,
      salespersonId: closer.id,
      sdrId: sdr.id,
      salesManagerId: manager.id,
      installments: {
        create: [
          { tenantId: TENANT, seq: 1, dueDate: signedAt, amount: 40000 },
          {
            tenantId: TENANT,
            seq: 2,
            dueDate: new Date(signedAt.getTime() + 30 * 86400000),
            amount: 30000,
          },
          {
            tenantId: TENANT,
            seq: 3,
            dueDate: new Date(signedAt.getTime() + 60 * 86400000),
            amount: 30000,
          },
        ],
      },
    },
  });

  console.log("=== trigger onContractSigned (5% sobre MARGIN) ===");
  const plan = await p.$transaction((tx) =>
    onContractSigned(
      {
        contractId: contract.id,
        commissionPct: 0.05,
        baseType: "MARGIN",
        sdrSplitPct: 0.30,
        managerOverridePct: 0.10,
        carencyDays: 7,
      },
      tx,
    ),
  );
  console.log("  plan:", plan);

  const entries0 = await p.commissionEntry.findMany({
    where: { contractId: contract.id },
    orderBy: [{ triggerType: "asc" }, { userId: "asc" }],
  });
  printEntries("após signing", entries0);

  console.log("=== confirm payment da parcela 1 (R$ 40k) ===");
  const inst1 = await p.contractInstallment.findFirst({
    where: { contractId: contract.id, seq: 1 },
  });
  if (!inst1) throw new Error("Installment 1 not found");
  await p.$transaction(async (tx) => {
    const payment = await tx.payment.create({
      data: {
        tenantId: TENANT,
        contractId: contract.id,
        installmentId: inst1.id,
        amount: 40000,
        paidAt: new Date(),
        method: "PIX",
        status: "CONFIRMED",
      },
    });
    await onPaymentConfirmed(payment.id, tx);
  });

  const entries1 = await p.commissionEntry.findMany({
    where: { contractId: contract.id },
    orderBy: [{ createdAt: "asc" }],
  });
  printEntries("após payment parcela 1", entries1);

  console.log("=== simula fim da carência → releaseDueLocks ===");
  // Força scheduledFor no passado
  await p.commissionEntry.updateMany({
    where: { contractId: contract.id, status: "LOCKED" },
    data: { scheduledFor: new Date(Date.now() - 86400000) },
  });
  const { released } = await releaseDueLocks(TENANT);
  console.log(`  ${released} entries liberadas`);

  console.log("=== provisioned expenses por mês ===");
  const provs = await p.provisionedExpense.groupBy({
    by: ["forecastMonth", "status"],
    where: { tenantId: TENANT },
    _sum: { amount: true },
    orderBy: { forecastMonth: "asc" },
  });
  for (const r of provs) {
    console.log(
      `  ${r.forecastMonth} ${r.status}: R$ ${(r._sum.amount ?? 0).toFixed(2)}`,
    );
  }

  console.log("=== bonus rule (REVENUE 60% + EVENTS_CLOSED 40%, com accel) ===");
  const bonusRule = await p.bonusRule.create({
    data: {
      tenantId: TENANT,
      userId: closer.id,
      name: "Ana Closer — Mensal",
      periodType: "MONTHLY",
      effectiveFrom: new Date(signedAt.getFullYear(), signedAt.getMonth(), 1),
      rampUpMonths: 0,
      maxPayout: 20000,
      components: {
        create: [
          {
            metric: "REVENUE",
            weight: 0.6,
            target: 80000,
            basePayout: 5000,
            acceleratorBands: [
              { minRatio: 0, maxRatio: 1.0, multiplier: 1.0 },
              { minRatio: 1.0, maxRatio: 1.5, multiplier: 1.5 },
              { minRatio: 1.5, multiplier: 2.0 },
            ],
          },
          {
            metric: "EVENTS_CLOSED",
            weight: 0.4,
            target: 2,
            basePayout: 3000,
            acceleratorBands: [
              { minRatio: 0, maxRatio: 1.0, multiplier: 1.0 },
              { minRatio: 1.0, multiplier: 2.0 },
            ],
          },
        ],
      },
    },
  });
  const start = new Date(signedAt.getFullYear(), signedAt.getMonth(), 1);
  const end = new Date(signedAt.getFullYear(), signedAt.getMonth() + 1, 0);
  const accrual = await p.$transaction((tx) =>
    computeBonusAccrual(bonusRule.id, start, end, tx),
  );
  console.log("  accrual total: R$", accrual.totalAmount);
  console.log("  breakdown:", JSON.stringify(accrual.breakdown, null, 2));

  console.log("=== clawback (cancelamento) ===");
  const cb = await p.$transaction((tx) =>
    onContractCancelled(contract.id, "cliente desistiu", tx),
  );
  console.log("  ", cb);

  const entries2 = await p.commissionEntry.findMany({
    where: { contractId: contract.id },
    orderBy: [{ createdAt: "asc" }],
  });
  printEntries("após clawback", entries2);

  console.log("\n=== DONE ===");
  await p.$disconnect();
}

function printEntries(
  label: string,
  entries: Array<{
    id: string;
    role: string;
    triggerType: string;
    amount: number;
    status: string;
    userId: string;
  }>,
): void {
  console.log(`\n--- ${label}: ${entries.length} entries ---`);
  for (const e of entries) {
    console.log(
      `  ${e.id.slice(0, 8)} ${e.role.padEnd(18)} ${e.triggerType.padEnd(12)} R$ ${e.amount.toFixed(2).padStart(10)} ${e.status}`,
    );
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
