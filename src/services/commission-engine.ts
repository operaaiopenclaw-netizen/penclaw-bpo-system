import { Prisma, PrismaClient } from "@prisma/client";
import { prisma } from "../db";
import { logger } from "../utils/logger";

// Motor de comissões: gera e gerencia o ciclo de vida das CommissionEntry
// a partir de eventos de negócio. Pensado como funções puras sobre o
// cliente Prisma (ou uma transação) — nunca ancorado em `prisma` direto
// para que chamadas compostas (ex: onContractSigned dentro de outro
// endpoint transacional) herdem a transação do caller.

type Tx = PrismaClient | Prisma.TransactionClient;

// ---------------------------------------------------------------------------
// Criação de plano + entries no momento da assinatura
// ---------------------------------------------------------------------------

export interface SignPlanInput {
  contractId: string;
  commissionPct: number;         // ex: 0.05 = 5% sobre a base
  baseType?: "REVENUE" | "MARGIN";
  signingPct?: number;           // default 0.40
  installmentPct?: number;       // default 0.60
  carencyDays?: number;          // default 0
  managerOverridePct?: number;   // default 0
  sdrSplitPct?: number;          // default 0 (closer fica com 100%)
  discountThreshold?: number;    // default 0.10
  discountPenaltyPct?: number;   // default 0
  createdBy?: string;
}

// Dispara quando o contrato é assinado. Assume que Contract já tem
// installments criadas (ContractInstallment) — se não houver, gera
// apenas a entry de 40% do signing.
export async function onContractSigned(
  input: SignPlanInput,
  tx: Tx = prisma,
): Promise<{ planId: string; entries: number }> {
  const contract = await tx.contract.findUnique({
    where: { id: input.contractId },
    include: {
      installments: { orderBy: { seq: "asc" } },
      proposal: true,
      commissionPlan: true,
    },
  });
  if (!contract) throw new Error(`Contract ${input.contractId} not found`);
  if (contract.commissionPlan) {
    throw new Error(`Contract ${input.contractId} already has a commission plan (immutable)`);
  }
  if (!contract.salespersonId) {
    throw new Error(`Contract ${input.contractId} has no salespersonId — cannot assign commission`);
  }

  const baseType = input.baseType ?? "MARGIN";
  const signingPct = input.signingPct ?? 0.40;
  const installmentPct = input.installmentPct ?? 0.60;
  const carencyDays = input.carencyDays ?? 0;
  const managerOverridePct = input.managerOverridePct ?? 0;
  const sdrSplitPct = input.sdrSplitPct ?? 0;
  const closerSplitPct = 1 - sdrSplitPct;
  const discountThreshold = input.discountThreshold ?? 0.10;
  const discountPenaltyPct = input.discountPenaltyPct ?? 0;
  const discountApplied = contract.proposal?.discountAppliedPct ?? 0;

  if (Math.abs(signingPct + installmentPct - 1) > 0.0001) {
    throw new Error("signingPct + installmentPct must equal 1.0");
  }

  // Base absoluta: margem projetada OU faturamento total.
  const baseAmount =
    baseType === "MARGIN"
      ? (contract.projectedMargin ?? 0)
      : contract.totalValue;
  if (baseAmount <= 0) {
    throw new Error(
      `Invalid commission base: baseType=${baseType} amount=${baseAmount} — check Contract.projectedMargin`,
    );
  }

  // Percentual efetivo pós-penalty: se desconto > threshold, reduz a comissão.
  const penaltyActive = discountApplied > discountThreshold;
  const effectivePct = penaltyActive
    ? input.commissionPct * (1 - discountPenaltyPct)
    : input.commissionPct;

  const plan = await tx.commissionPlan.create({
    data: {
      tenantId: contract.tenantId,
      contractId: contract.id,
      baseType,
      baseAmount,
      baseMarginPct: baseType === "MARGIN" && contract.totalValue > 0
        ? baseAmount / contract.totalValue
        : null,
      signingPct,
      installmentPct,
      carencyDays,
      managerOverridePct,
      sdrSplitPct,
      closerSplitPct,
      discountAppliedPct: discountApplied,
      discountThreshold,
      discountPenaltyPct,
      commissionPct: effectivePct,
      createdBy: input.createdBy,
    },
  });

  // ---- Entries de signing (40%) ----
  const signingScheduled = endOfMonth(contract.signedAt);
  const signingAmountTotal = baseAmount * effectivePct * signingPct;

  const entries: Prisma.CommissionEntryCreateManyInput[] = [];

  entries.push(
    ...buildRoleEntries({
      tenantId: contract.tenantId,
      contractId: contract.id,
      installmentId: null,
      paymentId: null,
      triggerType: "SIGNING",
      amountTotal: signingAmountTotal,
      baseAmount,
      effectivePct,
      scheduledFor: signingScheduled,
      closer: { userId: contract.salespersonId, split: closerSplitPct },
      sdr: contract.sdrId ? { userId: contract.sdrId, split: sdrSplitPct } : null,
      manager: contract.salesManagerId
        ? { userId: contract.salesManagerId, pct: managerOverridePct }
        : null,
      // SIGNING entries nascem LOCKED — aguardam só o fim do mês.
      status: "LOCKED",
    }),
  );

  // ---- Entries das parcelas (60%) ----
  if (contract.installments.length > 0) {
    const installmentBase = baseAmount * effectivePct * installmentPct;
    const totalInstallmentAmount = contract.installments.reduce(
      (sum, i) => sum + i.amount,
      0,
    );
    for (const inst of contract.installments) {
      const share = totalInstallmentAmount > 0
        ? inst.amount / totalInstallmentAmount
        : 1 / contract.installments.length;
      const amountTotal = installmentBase * share;
      const scheduledFor = addDays(inst.dueDate, carencyDays);

      entries.push(
        ...buildRoleEntries({
          tenantId: contract.tenantId,
          contractId: contract.id,
          installmentId: inst.id,
          paymentId: null,
          triggerType: "INSTALLMENT",
          amountTotal,
          baseAmount: baseAmount * share,
          effectivePct,
          scheduledFor,
          closer: { userId: contract.salespersonId, split: closerSplitPct },
          sdr: contract.sdrId ? { userId: contract.sdrId, split: sdrSplitPct } : null,
          manager: contract.salesManagerId
            ? { userId: contract.salesManagerId, pct: managerOverridePct }
            : null,
          // INSTALLMENT entries nascem FORECAST — só viram LOCKED/RELEASED
          // quando o Payment chega.
          status: "FORECAST",
        }),
      );
    }
  }

  await tx.commissionEntry.createMany({ data: entries });

  // Provisão financeira (toda entry cria uma ProvisionedExpense LOCKED).
  await provisionEntries(contract.tenantId, entries, tx);

  logger.info(
    {
      contractId: contract.id,
      planId: plan.id,
      entries: entries.length,
      baseAmount,
      effectivePct,
      penaltyActive,
    },
    "commission: contract signed",
  );

  return { planId: plan.id, entries: entries.length };
}

// ---------------------------------------------------------------------------
// Liberação pro-rata ao confirmar Payment
// ---------------------------------------------------------------------------

// Ao confirmar um Payment, libera as comissões proporcionais da parcela
// coberta. Se o pagamento for parcial, libera só a fração correspondente
// via clone da entry (uma RELEASED com valor parcial + FORECAST restante).
export async function onPaymentConfirmed(
  paymentId: string,
  tx: Tx = prisma,
): Promise<{ released: number; releasedAmount: number }> {
  const payment = await tx.payment.findUnique({
    where: { id: paymentId },
    include: { installment: true },
  });
  if (!payment) throw new Error(`Payment ${paymentId} not found`);
  if (payment.status !== "CONFIRMED") {
    throw new Error(`Payment ${paymentId} is not CONFIRMED`);
  }
  if (!payment.installmentId || !payment.installment) {
    logger.info({ paymentId }, "commission: payment has no installment, skipping release");
    return { released: 0, releasedAmount: 0 };
  }

  const plan = await tx.commissionPlan.findUnique({
    where: { contractId: payment.contractId },
  });
  if (!plan) {
    logger.warn({ paymentId, contractId: payment.contractId }, "commission: no plan on contract");
    return { released: 0, releasedAmount: 0 };
  }

  // Atualiza paidAmount da installment (soma cumulativa de todos Payments CONFIRMED).
  const agg = await tx.payment.aggregate({
    where: { installmentId: payment.installmentId, status: "CONFIRMED" },
    _sum: { amount: true },
  });
  const paidSoFar = agg._sum.amount ?? 0;
  const fullyPaid = paidSoFar >= payment.installment.amount - 0.01;
  const paidRatio = Math.min(1, paidSoFar / payment.installment.amount);

  await tx.contractInstallment.update({
    where: { id: payment.installmentId },
    data: {
      paidAmount: paidSoFar,
      status: fullyPaid ? "PAID" : "PARTIAL",
    },
  });

  // Entries FORECAST da installment → proporcionais ao paidRatio.
  const forecastEntries = await tx.commissionEntry.findMany({
    where: {
      installmentId: payment.installmentId,
      status: "FORECAST",
    },
  });

  const releasedNow = new Date();
  const releaseAt = addDays(payment.paidAt, plan.carencyDays);
  let releasedCount = 0;
  let releasedAmount = 0;

  for (const entry of forecastEntries) {
    // Valor total previsto da entry; libera só a fração proporcional ao
    // que foi pago. Resto permanece FORECAST na mesma entry (reduzida).
    const fullAmount = entry.amount;
    const alreadyReleased = entry.metadata
      ? ((entry.metadata as { releasedAmount?: number }).releasedAmount ?? 0)
      : 0;
    const targetReleased = fullAmount * paidRatio;
    const delta = Math.max(0, targetReleased - alreadyReleased);
    if (delta < 0.01) continue;

    // Cria uma nova entry RELEASED para o delta + ajusta a FORECAST.
    const remainingForecast = fullAmount - (alreadyReleased + delta);
    const newReleased = await tx.commissionEntry.create({
      data: {
        tenantId: entry.tenantId,
        contractId: entry.contractId,
        installmentId: entry.installmentId,
        paymentId: payment.id,
        userId: entry.userId,
        role: entry.role,
        triggerType: entry.triggerType,
        amount: delta,
        baseAmount: entry.baseAmount * paidRatio,
        effectivePct: entry.effectivePct,
        status: releaseAt <= releasedNow ? "RELEASED" : "LOCKED",
        scheduledFor: releaseAt,
        releasedAt: releaseAt <= releasedNow ? releasedNow : null,
        metadata: { parentEntryId: entry.id, splitReason: "proportional_release" },
      },
    });
    releasedCount += 1;
    releasedAmount += delta;

    // Ajusta a FORECAST remanescente. Se zero → marca como "SPLIT_CONSUMED".
    await tx.commissionEntry.update({
      where: { id: entry.id },
      data: {
        amount: remainingForecast,
        metadata: {
          ...(entry.metadata as object ?? {}),
          releasedAmount: alreadyReleased + delta,
          ...(remainingForecast < 0.01
            ? { splitConsumed: true, consumedBy: newReleased.id }
            : {}),
        },
        status: remainingForecast < 0.01 ? "RELEASED" : "FORECAST",
        releasedAt: remainingForecast < 0.01 ? releasedNow : null,
      },
    });

    // Atualiza ProvisionedExpense: LOCKED → RELEASED na fração.
    await tx.provisionedExpense.updateMany({
      where: { sourceType: "COMMISSION", sourceId: entry.id, status: "LOCKED" },
      data: { status: "RELEASED" },
    });
  }

  logger.info(
    { paymentId, installmentId: payment.installmentId, releasedCount, releasedAmount, paidRatio },
    "commission: payment confirmed → entries released",
  );

  return { released: releasedCount, releasedAmount };
}

// ---------------------------------------------------------------------------
// Clawback: cancelamento ou inadimplência
// ---------------------------------------------------------------------------

// Estorna comissões provisionadas/liberadas. PAID nunca é estornado
// automaticamente — debita da próxima folha via flag no metadata.
export async function onContractCancelled(
  contractId: string,
  reason: string,
  tx: Tx = prisma,
): Promise<{ clawedBack: number; paidFlaggedForDebit: number }> {
  const entries = await tx.commissionEntry.findMany({
    where: { contractId, status: { in: ["FORECAST", "LOCKED", "RELEASED"] } },
  });
  const paidEntries = await tx.commissionEntry.findMany({
    where: { contractId, status: "PAID" },
  });

  const now = new Date();
  for (const e of entries) {
    await tx.commissionEntry.update({
      where: { id: e.id },
      data: {
        status: "CLAWED_BACK",
        clawedBackAt: now,
        clawbackReason: reason,
      },
    });
    await tx.provisionedExpense.updateMany({
      where: { sourceType: "COMMISSION", sourceId: e.id, status: { in: ["LOCKED", "RELEASED"] } },
      data: { status: "REVERSED", reversedReason: reason },
    });
  }

  // PAID: não muda status (imutável), mas marca metadata para debitar
  // da próxima folha do beneficiário.
  for (const e of paidEntries) {
    await tx.commissionEntry.update({
      where: { id: e.id },
      data: {
        metadata: {
          ...(e.metadata as object ?? {}),
          clawbackPending: true,
          clawbackReason: reason,
          clawbackFlaggedAt: now.toISOString(),
        },
      },
    });
  }

  logger.warn(
    { contractId, reason, clawedBack: entries.length, paidFlagged: paidEntries.length },
    "commission: contract cancelled → clawback triggered",
  );

  return { clawedBack: entries.length, paidFlaggedForDebit: paidEntries.length };
}

// ---------------------------------------------------------------------------
// Tick de liberação — roda periodicamente para virar LOCKED→RELEASED
// quando scheduledFor já passou (40% do signing, carência do payment).
// ---------------------------------------------------------------------------

export async function releaseDueLocks(
  tenantId: string,
  tx: Tx = prisma,
): Promise<{ released: number }> {
  const now = new Date();
  const due = await tx.commissionEntry.findMany({
    where: { tenantId, status: "LOCKED", scheduledFor: { lte: now } },
  });
  for (const e of due) {
    await tx.commissionEntry.update({
      where: { id: e.id },
      data: { status: "RELEASED", releasedAt: now },
    });
    await tx.provisionedExpense.updateMany({
      where: { sourceType: "COMMISSION", sourceId: e.id, status: "LOCKED" },
      data: { status: "RELEASED" },
    });
  }
  if (due.length > 0) {
    logger.info({ tenantId, released: due.length }, "commission: periodic release tick");
  }
  return { released: due.length };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

interface BuildRoleEntriesInput {
  tenantId: string;
  contractId: string;
  installmentId: string | null;
  paymentId: string | null;
  triggerType: "SIGNING" | "INSTALLMENT";
  amountTotal: number;     // total antes do split entre roles
  baseAmount: number;
  effectivePct: number;
  scheduledFor: Date;
  status: "LOCKED" | "FORECAST" | "RELEASED";
  closer: { userId: string; split: number };
  sdr: { userId: string; split: number } | null;
  manager: { userId: string; pct: number } | null;
}

function buildRoleEntries(
  i: BuildRoleEntriesInput,
): Prisma.CommissionEntryCreateManyInput[] {
  const rows: Prisma.CommissionEntryCreateManyInput[] = [];

  // Closer
  rows.push({
    tenantId: i.tenantId,
    contractId: i.contractId,
    installmentId: i.installmentId,
    paymentId: i.paymentId,
    userId: i.closer.userId,
    role: "CLOSER",
    triggerType: i.triggerType,
    amount: round2(i.amountTotal * i.closer.split),
    baseAmount: i.baseAmount,
    effectivePct: i.effectivePct,
    status: i.status,
    scheduledFor: i.scheduledFor,
  });

  // SDR (se houver split)
  if (i.sdr && i.sdr.split > 0) {
    rows.push({
      tenantId: i.tenantId,
      contractId: i.contractId,
      installmentId: i.installmentId,
      paymentId: i.paymentId,
      userId: i.sdr.userId,
      role: "SDR",
      triggerType: i.triggerType,
      amount: round2(i.amountTotal * i.sdr.split),
      baseAmount: i.baseAmount,
      effectivePct: i.effectivePct,
      status: i.status,
      scheduledFor: i.scheduledFor,
    });
  }

  // Gerente (override sobre o total — não sai do closer/sdr)
  if (i.manager && i.manager.pct > 0) {
    rows.push({
      tenantId: i.tenantId,
      contractId: i.contractId,
      installmentId: i.installmentId,
      paymentId: i.paymentId,
      userId: i.manager.userId,
      role: "MANAGER_OVERRIDE",
      triggerType: i.triggerType,
      amount: round2(i.amountTotal * i.manager.pct),
      baseAmount: i.baseAmount,
      effectivePct: i.effectivePct * i.manager.pct,
      status: i.status,
      scheduledFor: i.scheduledFor,
    });
  }

  return rows;
}

async function provisionEntries(
  tenantId: string,
  entries: Prisma.CommissionEntryCreateManyInput[],
  tx: Tx,
): Promise<void> {
  // Re-busca as entries criadas para ter os IDs definitivos
  const created = await tx.commissionEntry.findMany({
    where: {
      tenantId,
      contractId: entries[0]?.contractId,
      // apenas as que acabamos de criar (sem paymentId setado)
      paymentId: null,
    },
    orderBy: { createdAt: "desc" },
    take: entries.length,
  });

  await tx.provisionedExpense.createMany({
    data: created.map((e) => ({
      tenantId: e.tenantId,
      sourceType: "COMMISSION",
      sourceId: e.id,
      beneficiaryId: e.userId,
      amount: e.amount,
      forecastMonth: ymKey(e.scheduledFor),
      status: "LOCKED",
    })),
  });
}

function endOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0, 23, 59, 59, 999);
}

function addDays(d: Date, days: number): Date {
  const out = new Date(d);
  out.setDate(out.getDate() + days);
  return out;
}

function ymKey(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}
