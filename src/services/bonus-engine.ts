import { Prisma, PrismaClient } from "@prisma/client";
import { prisma } from "../db";
import { logger } from "../utils/logger";

// Motor de bônus composto. Calcula BonusAccrual a partir de BonusRule +
// BonusComponents para um período. Métricas são resolvidas a partir do
// banco (contracts/payments/leads) e multiplicadas pelos acceleradores.
//
// Modelo mental do accelerator band:
//   { minRatio: 0,   maxRatio: 1.0, multiplier: 1.0 }  // até 100% da meta: 1x
//   { minRatio: 1.0, maxRatio: 1.2, multiplier: 1.5 }  // 100-120%: 1.5x sobre o excedente
//   { minRatio: 1.2, multiplier: 2.0 }                 // acima de 120%: 2x
// O pagamento é piecewise-linear: cada banda multiplica o basePayout
// proporcional à fração atingida DENTRO dela.

type Tx = PrismaClient | Prisma.TransactionClient;

export type BonusMetric =
  | "REVENUE"
  | "MARGIN"
  | "CONVERSION"
  | "TICKET_AVG"
  | "EVENTS_CLOSED"
  | "NPS";

export interface AcceleratorBand {
  minRatio: number;
  maxRatio?: number; // sem limite superior na última banda
  multiplier: number;
}

export interface ComponentBreakdown {
  componentId: string;
  metric: BonusMetric;
  weight: number;
  target: number;
  actual: number;
  ratio: number;        // actual / target
  basePayout: number;
  payout: number;       // subtotal após acceleradores
}

// Calcula o accrual de um BonusRule para um período. Idempotente por
// (bonusRuleId, periodStart, periodEnd) via unique constraint.
export async function computeBonusAccrual(
  bonusRuleId: string,
  periodStart: Date,
  periodEnd: Date,
  tx: Tx = prisma,
): Promise<{ accrualId: string; totalAmount: number; breakdown: ComponentBreakdown[] }> {
  const rule = await tx.bonusRule.findUnique({
    where: { id: bonusRuleId },
    include: { components: true },
  });
  if (!rule) throw new Error(`BonusRule ${bonusRuleId} not found`);
  if (rule.status !== "ACTIVE") throw new Error(`BonusRule ${bonusRuleId} is not ACTIVE`);
  if (!rule.userId) throw new Error(`BonusRule ${bonusRuleId} has no userId — cannot accrue`);
  if (rule.components.length === 0) {
    throw new Error(`BonusRule ${bonusRuleId} has no components`);
  }

  const weightSum = rule.components.reduce((s, c) => s + c.weight, 0);
  if (Math.abs(weightSum - 1) > 0.0001) {
    throw new Error(
      `BonusRule ${bonusRuleId} component weights sum to ${weightSum}, expected 1.0`,
    );
  }

  // Ramp-up: se o usuário está nos primeiros N meses da regra, reduz os
  // targets por rampUpFactor.
  const rampFactor = isWithinRampUp(rule.effectiveFrom, periodStart, rule.rampUpMonths)
    ? rule.rampUpFactor
    : 1;

  const breakdown: ComponentBreakdown[] = [];
  let total = 0;

  for (const comp of rule.components) {
    const effectiveTarget = comp.target * rampFactor;
    const actual = await resolveMetric(
      comp.metric as BonusMetric,
      rule.userId,
      rule.tenantId,
      periodStart,
      periodEnd,
      tx,
    );
    const ratio = effectiveTarget > 0 ? actual / effectiveTarget : 0;
    const bands = parseBands(comp.acceleratorBands);
    const payout = computePiecewisePayout(ratio, comp.basePayout, comp.weight, bands);
    breakdown.push({
      componentId: comp.id,
      metric: comp.metric as BonusMetric,
      weight: comp.weight,
      target: effectiveTarget,
      actual,
      ratio,
      basePayout: comp.basePayout,
      payout,
    });
    total += payout;
  }

  // Teto do bônus
  if (rule.maxPayout !== null && rule.maxPayout !== undefined && total > rule.maxPayout) {
    total = rule.maxPayout;
  }

  const accrual = await tx.bonusAccrual.upsert({
    where: {
      bonusRuleId_periodStart_periodEnd: {
        bonusRuleId,
        periodStart,
        periodEnd,
      },
    },
    create: {
      tenantId: rule.tenantId,
      bonusRuleId,
      userId: rule.userId,
      periodStart,
      periodEnd,
      totalAmount: round2(total),
      breakdown: breakdown as unknown as Prisma.InputJsonValue,
      status: "COMPUTED",
    },
    update: {
      totalAmount: round2(total),
      breakdown: breakdown as unknown as Prisma.InputJsonValue,
      computedAt: new Date(),
    },
  });

  // Provisiona como despesa LOCKED para aparecer na previsão de despesa.
  // Recompute sobrescreve: remove provisions LOCKED/RELEASED antigas deste
  // accrual e recria com o valor atual (PAID/REVERSED permanecem).
  await tx.provisionedExpense.deleteMany({
    where: {
      sourceType: "BONUS",
      sourceId: accrual.id,
      status: { in: ["LOCKED", "RELEASED"] },
    },
  });
  await tx.provisionedExpense.create({
    data: {
      tenantId: rule.tenantId,
      sourceType: "BONUS",
      sourceId: accrual.id,
      beneficiaryId: rule.userId,
      amount: round2(total),
      forecastMonth: ymKey(periodEnd),
      status: "LOCKED",
    },
  });

  logger.info(
    { bonusRuleId, userId: rule.userId, total: round2(total), rampFactor, components: breakdown.length },
    "bonus: accrual computed",
  );

  return { accrualId: accrual.id, totalAmount: round2(total), breakdown };
}

// ---------------------------------------------------------------------------
// Resolução de métricas contra o banco
// ---------------------------------------------------------------------------

async function resolveMetric(
  metric: BonusMetric,
  userId: string,
  tenantId: string,
  periodStart: Date,
  periodEnd: Date,
  tx: Tx,
): Promise<number> {
  const range = { gte: periodStart, lte: periodEnd };

  switch (metric) {
    case "REVENUE": {
      // Soma totalValue dos contratos assinados no período pelo usuário.
      const agg = await tx.contract.aggregate({
        where: { tenantId, salespersonId: userId, signedAt: range, status: "ACTIVE" },
        _sum: { totalValue: true },
      });
      return agg._sum.totalValue ?? 0;
    }
    case "MARGIN": {
      const agg = await tx.contract.aggregate({
        where: { tenantId, salespersonId: userId, signedAt: range, status: "ACTIVE" },
        _sum: { projectedMargin: true },
      });
      return agg._sum.projectedMargin ?? 0;
    }
    case "EVENTS_CLOSED": {
      const count = await tx.contract.count({
        where: { tenantId, salespersonId: userId, signedAt: range, status: "ACTIVE" },
      });
      return count;
    }
    case "TICKET_AVG": {
      const agg = await tx.contract.aggregate({
        where: { tenantId, salespersonId: userId, signedAt: range, status: "ACTIVE" },
        _avg: { totalValue: true },
      });
      return agg._avg.totalValue ?? 0;
    }
    case "CONVERSION": {
      // Leads convertidos (assignedTo = userId) / leads tocados no período.
      const touched = await tx.lead.count({
        where: {
          tenantId,
          assignedTo: userId,
          OR: [
            { contactedAt: range },
            { qualifiedAt: range },
            { convertedAt: range },
          ],
        },
      });
      const converted = await tx.lead.count({
        where: { tenantId, assignedTo: userId, convertedAt: range },
      });
      return touched > 0 ? converted / touched : 0;
    }
    case "NPS": {
      // NPS não está modelado no banco. Retorna 0 até haver fonte.
      // Empresa pode preencher via endpoint dedicado (ex: override manual
      // no metadata do BonusAccrual após computar).
      return 0;
    }
    default:
      return 0;
  }
}

// ---------------------------------------------------------------------------
// Piecewise payout com acceleradores
// ---------------------------------------------------------------------------

// Dado ratio (actual/target), basePayout (valor se atingir 100%), weight
// (peso no bônus total) e bandas. Calcula payout final como soma das
// frações em cada banda × multiplier × weight × basePayout.
function computePiecewisePayout(
  ratio: number,
  basePayout: number,
  weight: number,
  bands: AcceleratorBand[],
): number {
  if (bands.length === 0) {
    // Sem acceleradores: linear até 100%, cap em 100%.
    return basePayout * weight * Math.min(1, Math.max(0, ratio));
  }
  const sorted = [...bands].sort((a, b) => a.minRatio - b.minRatio);
  let payout = 0;
  for (const band of sorted) {
    if (ratio <= band.minRatio) break;
    const upper = band.maxRatio ?? ratio;
    const filled = Math.min(ratio, upper) - band.minRatio;
    if (filled <= 0) continue;
    payout += basePayout * weight * filled * band.multiplier;
  }
  return payout;
}

function parseBands(v: Prisma.JsonValue | null): AcceleratorBand[] {
  if (!v || !Array.isArray(v)) return [];
  const out: AcceleratorBand[] = [];
  for (const item of v) {
    if (typeof item !== "object" || item === null || Array.isArray(item)) continue;
    const obj = item as Record<string, unknown>;
    if (typeof obj.minRatio === "number" && typeof obj.multiplier === "number") {
      out.push({
        minRatio: obj.minRatio,
        maxRatio: typeof obj.maxRatio === "number" ? obj.maxRatio : undefined,
        multiplier: obj.multiplier,
      });
    }
  }
  return out;
}

function isWithinRampUp(
  effectiveFrom: Date,
  periodStart: Date,
  rampUpMonths: number,
): boolean {
  if (rampUpMonths <= 0) return false;
  const monthsSince =
    (periodStart.getFullYear() - effectiveFrom.getFullYear()) * 12 +
    (periodStart.getMonth() - effectiveFrom.getMonth());
  return monthsSince < rampUpMonths;
}

function ymKey(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}
