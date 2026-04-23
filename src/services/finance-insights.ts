// Finance Insights — read-only analytics on top of the BPO data model.
// Smart alerts, cashflow forecast, subscription detection, category
// variance and Open Finance bridge. Every function takes tenantId and
// returns a structured payload ready for dashboard or ai-chat consumption.

import { prisma } from "../db";

type CashflowBucket = {
  date: string; // YYYY-MM-DD
  inflows: number;
  outflows: number;
  net: number;
  items: Array<{
    kind: "INSTALLMENT_DUE" | "COMMISSION_DUE" | "PROVISION_DUE";
    id: string;
    label: string;
    amount: number;
  }>;
};

export type CashflowForecast = {
  from: string;
  to: string;
  totalInflow: number;
  totalOutflow: number;
  net: number;
  buckets: CashflowBucket[];
};

function ymd(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function ensureBucket(map: Map<string, CashflowBucket>, date: string): CashflowBucket {
  let b = map.get(date);
  if (!b) {
    b = { date, inflows: 0, outflows: 0, net: 0, items: [] };
    map.set(date, b);
  }
  return b;
}

export async function getCashflowForecast(
  tenantId: string,
  days = 30,
): Promise<CashflowForecast> {
  const now = new Date();
  const from = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const to = new Date(from);
  to.setDate(to.getDate() + days);

  const [installments, commissions, provisions] = await Promise.all([
    prisma.contractInstallment.findMany({
      where: {
        tenantId,
        status: { in: ["PENDING", "PARTIAL", "OVERDUE"] },
        dueDate: { gte: from, lte: to },
      },
      select: {
        id: true,
        seq: true,
        dueDate: true,
        amount: true,
        paidAmount: true,
        contract: { select: { contractNumber: true } },
      },
    }),
    prisma.commissionEntry.findMany({
      where: {
        tenantId,
        status: { in: ["FORECAST", "LOCKED", "RELEASED"] },
        scheduledFor: { gte: from, lte: to },
      },
      select: {
        id: true,
        amount: true,
        scheduledFor: true,
        user: { select: { name: true } },
      },
    }),
    prisma.provisionedExpense.findMany({
      where: {
        tenantId,
        status: { in: ["LOCKED", "RELEASED"] },
      },
      select: {
        id: true,
        amount: true,
        forecastMonth: true,
        sourceType: true,
      },
    }),
  ]);

  const buckets = new Map<string, CashflowBucket>();
  let totalInflow = 0;
  let totalOutflow = 0;

  for (const inst of installments) {
    const due = inst.amount - (inst.paidAmount ?? 0);
    if (due <= 0) continue;
    const key = ymd(inst.dueDate);
    const b = ensureBucket(buckets, key);
    b.inflows += due;
    b.net += due;
    b.items.push({
      kind: "INSTALLMENT_DUE",
      id: inst.id,
      label: `Parcela ${inst.seq} · ${inst.contract?.contractNumber ?? ""}`,
      amount: due,
    });
    totalInflow += due;
  }

  for (const comm of commissions) {
    const key = ymd(comm.scheduledFor);
    const b = ensureBucket(buckets, key);
    b.outflows += comm.amount;
    b.net -= comm.amount;
    b.items.push({
      kind: "COMMISSION_DUE",
      id: comm.id,
      label: `Comissão · ${comm.user?.name ?? "?"}`,
      amount: comm.amount,
    });
    totalOutflow += comm.amount;
  }

  // Provisions are month-based rather than day-based; drop them on the
  // first day of the forecast month that falls in-window.
  for (const prov of provisions) {
    const [py, pm] = prov.forecastMonth.split("-").map(Number);
    if (!py || !pm) continue;
    const first = new Date(py, pm - 1, 1);
    if (first < from || first > to) continue;
    const key = ymd(first);
    const b = ensureBucket(buckets, key);
    b.outflows += prov.amount;
    b.net -= prov.amount;
    b.items.push({
      kind: "PROVISION_DUE",
      id: prov.id,
      label: `Provisão · ${prov.sourceType}`,
      amount: prov.amount,
    });
    totalOutflow += prov.amount;
  }

  const ordered = [...buckets.values()].sort((a, b) => a.date.localeCompare(b.date));

  return {
    from: ymd(from),
    to: ymd(to),
    totalInflow,
    totalOutflow,
    net: totalInflow - totalOutflow,
    buckets: ordered,
  };
}

// ----------------------------------------------------------------------
// Smart alerts — things a human should probably look at this week.

export type Alert = {
  id: string;
  severity: "info" | "warn" | "danger";
  kind: string;
  title: string;
  detail: string;
  link?: string;
};

export async function getAlerts(tenantId: string): Promise<Alert[]> {
  const out: Alert[] = [];
  const now = new Date();
  const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

  // Overdue installments
  const overdue = await prisma.contractInstallment.findMany({
    where: {
      tenantId,
      status: { in: ["PENDING", "PARTIAL"] },
      dueDate: { lt: now },
    },
    select: {
      id: true,
      seq: true,
      amount: true,
      paidAmount: true,
      dueDate: true,
      contract: { select: { contractNumber: true } },
    },
    take: 50,
  });
  for (const inst of overdue) {
    const remaining = inst.amount - (inst.paidAmount ?? 0);
    const daysLate = Math.floor(
      (now.getTime() - inst.dueDate.getTime()) / (24 * 60 * 60 * 1000),
    );
    out.push({
      id: `overdue:${inst.id}`,
      severity: daysLate > 15 ? "danger" : "warn",
      kind: "INSTALLMENT_OVERDUE",
      title: `Parcela atrasada · ${inst.contract?.contractNumber ?? ""}`,
      detail: `R$ ${remaining.toFixed(2)} · ${daysLate} dia(s) em atraso`,
      link: `/ui/finance.html?contract=${inst.contract?.contractNumber ?? ""}`,
    });
  }

  // Released commissions sitting unpaid for > 7 days
  const staleCommissions = await prisma.commissionEntry.findMany({
    where: {
      tenantId,
      status: "RELEASED",
      updatedAt: { lt: weekAgo },
    },
    select: { id: true, amount: true, user: { select: { name: true } } },
    take: 50,
  });
  for (const c of staleCommissions) {
    out.push({
      id: `stale-commission:${c.id}`,
      severity: "warn",
      kind: "COMMISSION_STALE",
      title: `Comissão liberada há +7d sem pagamento`,
      detail: `${c.user?.name ?? "?"} · R$ ${c.amount.toFixed(2)}`,
      link: `/ui/finance.html`,
    });
  }

  // Duplicate charge suspicion — two payments of the same amount to the
  // same contract within 24h. Flags accidental double-billing.
  const recentPayments = await prisma.payment.findMany({
    where: {
      tenantId,
      paidAt: { gte: new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000) },
    },
    select: {
      id: true,
      contractId: true,
      amount: true,
      paidAt: true,
      contract: { select: { contractNumber: true } },
    },
  });
  const seen = new Map<string, typeof recentPayments[number]>();
  for (const p of recentPayments) {
    const key = `${p.contractId}:${p.amount.toFixed(2)}`;
    const prev = seen.get(key);
    if (prev) {
      const gapMs = Math.abs(p.paidAt.getTime() - prev.paidAt.getTime());
      if (gapMs < 24 * 60 * 60 * 1000) {
        out.push({
          id: `dup:${prev.id}:${p.id}`,
          severity: "danger",
          kind: "PAYMENT_DUPLICATE",
          title: `Possível pagamento duplicado`,
          detail: `Contrato ${p.contract?.contractNumber ?? ""} · R$ ${p.amount.toFixed(2)} em menos de 24h`,
        });
      }
    }
    seen.set(key, p);
  }

  // Contracts signed but without a commission plan
  const noPlan = await prisma.contract.findMany({
    where: {
      tenantId,
      status: "ACTIVE",
      commissionPlan: null,
    },
    select: { id: true, contractNumber: true, totalValue: true },
    take: 20,
  });
  for (const c of noPlan) {
    out.push({
      id: `noplan:${c.id}`,
      severity: "warn",
      kind: "COMMISSION_PLAN_MISSING",
      title: `Contrato sem plano de comissão`,
      detail: `${c.contractNumber} · R$ ${c.totalValue.toFixed(2)} — defina o plano antes de fechar o mês`,
      link: `/ui/finance.html?contract=${c.contractNumber}`,
    });
  }

  return out;
}

// ----------------------------------------------------------------------
// Subscription / recurring-expense detection. Groups ProvisionedExpense
// entries by beneficiary+amount that appear 3+ months in a row.

export type Subscription = {
  beneficiaryId: string | null;
  amount: number;
  months: string[]; // sorted ascending
  monthlyEstimate: number;
};

export async function getSubscriptions(tenantId: string): Promise<Subscription[]> {
  const rows = await prisma.provisionedExpense.findMany({
    where: { tenantId },
    select: { beneficiaryId: true, amount: true, forecastMonth: true },
  });

  type Key = string;
  const buckets = new Map<Key, { beneficiaryId: string | null; amount: number; months: Set<string> }>();
  for (const r of rows) {
    const key = `${r.beneficiaryId ?? ""}:${r.amount.toFixed(2)}`;
    const b = buckets.get(key) ?? {
      beneficiaryId: r.beneficiaryId,
      amount: r.amount,
      months: new Set<string>(),
    };
    b.months.add(r.forecastMonth);
    buckets.set(key, b);
  }

  const out: Subscription[] = [];
  for (const b of buckets.values()) {
    if (b.months.size < 3) continue;
    const sorted = [...b.months].sort();
    out.push({
      beneficiaryId: b.beneficiaryId,
      amount: b.amount,
      months: sorted,
      monthlyEstimate: b.amount,
    });
  }
  out.sort((a, b) => b.months.length - a.months.length);
  return out;
}

// ----------------------------------------------------------------------
// Category breakdown — provisioned expenses grouped by sourceType with
// month-over-month delta.

export type CategoryBreakdown = {
  period: { current: string; previous: string };
  categories: Array<{
    sourceType: string;
    current: number;
    previous: number;
    deltaPct: number | null;
  }>;
};

export async function getCategoryBreakdown(
  tenantId: string,
  yyyymm?: string,
): Promise<CategoryBreakdown> {
  const now = new Date();
  const curr =
    yyyymm ?? `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const [cy, cm] = curr.split("-").map(Number);
  const prevDate = new Date(cy, cm - 2, 1);
  const prev = `${prevDate.getFullYear()}-${String(prevDate.getMonth() + 1).padStart(2, "0")}`;

  const [currentRows, previousRows] = await Promise.all([
    prisma.provisionedExpense.groupBy({
      by: ["sourceType"],
      where: { tenantId, forecastMonth: curr },
      _sum: { amount: true },
    }),
    prisma.provisionedExpense.groupBy({
      by: ["sourceType"],
      where: { tenantId, forecastMonth: prev },
      _sum: { amount: true },
    }),
  ]);

  const prevMap = new Map(previousRows.map((r) => [r.sourceType, r._sum.amount ?? 0]));
  const allTypes = new Set([
    ...currentRows.map((r) => r.sourceType),
    ...previousRows.map((r) => r.sourceType),
  ]);

  const categories = [...allTypes].map((sourceType) => {
    const current =
      currentRows.find((r) => r.sourceType === sourceType)?._sum.amount ?? 0;
    const previous = prevMap.get(sourceType) ?? 0;
    const deltaPct =
      previous > 0 ? (current - previous) / previous : current > 0 ? null : 0;
    return { sourceType, current, previous, deltaPct };
  });

  categories.sort((a, b) => b.current - a.current);

  return { period: { current: curr, previous: prev }, categories };
}

// ----------------------------------------------------------------------
// Open Finance account summary — stub. Real impl would call Pluggy, Belvo
// or the chosen Open Finance aggregator.

export type OFAccount = {
  id: string;
  institution: string;
  type: "CHECKING" | "SAVINGS" | "CREDIT_CARD" | "INVESTMENT";
  balance: number;
  currency: "BRL";
  lastSyncAt: string;
};

export function getOpenFinanceStatus() {
  const wired = !!(process.env.PLUGGY_CLIENT_ID && process.env.PLUGGY_CLIENT_SECRET);
  return { wired, provider: wired ? "pluggy" : "mock" };
}

export async function getOpenFinanceAccounts(_tenantId: string): Promise<OFAccount[]> {
  // TODO: replace with real Pluggy/Belvo call when creds are set.
  // Returns an empty list when unwired so the UI can render an empty state.
  return [];
}
