import { FastifyInstance } from "fastify";
import { z } from "zod";
import { prisma } from "../db";
import { authenticate, requirePermission, AuthUser } from "../middleware/auth";
import { AppError } from "../utils/app-error";
import {
  onContractSigned,
  onPaymentConfirmed,
  onContractCancelled,
  releaseDueLocks,
} from "../services/commission-engine";
import { computeBonusAccrual } from "../services/bonus-engine";
import { logger } from "../utils/logger";

// Módulo Financeiro. Dono das comissões (despesa), pagamentos recebidos,
// bônus e do dashboard financeiro unificado. Comercial pára na assinatura
// do contrato; tudo monetário vive aqui.

export async function financeRoutes(app: FastifyInstance): Promise<void> {
  // ─── COMMISSION PLAN (vinculado ao contrato mas definido pelo financeiro) ──

  app.post<{ Params: { id: string }; Body: unknown }>(
    "/contracts/:id/commission-plan",
    { preHandler: requirePermission("commission.plan.write") },
    async (req, reply) => {
      const { id: contractId } = req.params;
      const schema = z.object({
        commissionPct: z.number().min(0).max(1),
        baseType: z.enum(["REVENUE", "MARGIN"]).default("MARGIN"),
        signingPct: z.number().min(0).max(1).default(0.4),
        installmentPct: z.number().min(0).max(1).default(0.6),
        carencyDays: z.number().int().min(0).default(0),
        managerOverridePct: z.number().min(0).max(1).default(0),
        sdrSplitPct: z.number().min(0).max(1).default(0),
        discountThreshold: z.number().min(0).max(1).default(0.1),
        discountPenaltyPct: z.number().min(0).max(1).default(0),
      });
      const parsed = schema.safeParse(req.body);
      if (!parsed.success) throw new AppError("Invalid payload", 400, "VALIDATION");

      const contract = await prisma.contract.findUnique({ where: { id: contractId } });
      if (!contract) throw new AppError("Contract not found", 404, "NOT_FOUND");
      assertTenant(req.user, contract.tenantId);

      const result = await prisma.$transaction(async (tx) =>
        onContractSigned(
          { contractId, createdBy: req.user?.id, ...parsed.data },
          tx,
        ),
      );
      return reply.status(201).send(result);
    },
  );

  // ─── PAYMENTS (recebimentos) ─────────────────────────────────

  app.post<{ Body: unknown }>(
    "/payments",
    { preHandler: requirePermission("payments.write") },
    async (req, reply) => {
      const schema = z.object({
        contractId: z.string().uuid(),
        installmentId: z.string().uuid().optional(),
        amount: z.number().positive(),
        paidAt: z.string().datetime(),
        method: z.enum(["PIX", "BOLETO", "CARD", "TRANSFER", "CHECK", "OTHER"]),
        externalRef: z.string().optional(),
        note: z.string().optional(),
      });
      const parsed = schema.safeParse(req.body);
      if (!parsed.success) throw new AppError("Invalid payload", 400, "VALIDATION");
      const body = parsed.data;

      const contract = await prisma.contract.findUnique({ where: { id: body.contractId } });
      if (!contract) throw new AppError("Contract not found", 404, "NOT_FOUND");
      assertTenant(req.user, contract.tenantId);

      const result = await prisma.$transaction(async (tx) => {
        const payment = await tx.payment.create({
          data: {
            tenantId: contract.tenantId,
            contractId: body.contractId,
            installmentId: body.installmentId,
            amount: body.amount,
            paidAt: new Date(body.paidAt),
            method: body.method,
            externalRef: body.externalRef,
            note: body.note,
            status: "CONFIRMED",
          },
        });
        const released = await onPaymentConfirmed(payment.id, tx);
        return { payment, released };
      });
      return reply.status(201).send(result);
    },
  );

  app.get<{ Querystring: { contractId?: string } }>(
    "/payments",
    { preHandler: authenticate },
    async (req) => {
      const tenantId = req.user?.tenantId;
      if (!tenantId) throw new AppError("Unauthenticated", 401, "UNAUTHORIZED");
      const payments = await prisma.payment.findMany({
        where: {
          tenantId,
          ...(req.query.contractId ? { contractId: req.query.contractId } : {}),
        },
        orderBy: { paidAt: "desc" },
        take: 200,
      });
      return { payments };
    },
  );

  // ─── COMMISSION ENTRIES ──────────────────────────────────────

  app.get<{
    Querystring: {
      userId?: string;
      status?: string;
      contractId?: string;
      period?: "month" | "year" | "lifetime";
      from?: string;
      to?: string;
    };
  }>(
    "/commissions",
    { preHandler: requirePermission("commission.entry.read") },
    async (req) => {
      const user = req.user;
      if (!user) throw new AppError("Unauthenticated", 401, "UNAUTHORIZED");
      const visibleUserIds = await resolveVisibleUserIds(user, req.query.userId);
      const window = periodWindow(req.query.period, req.query.from, req.query.to);

      const entries = await prisma.commissionEntry.findMany({
        where: {
          tenantId: user.tenantId,
          ...(visibleUserIds ? { userId: { in: visibleUserIds } } : {}),
          ...(req.query.status ? { status: req.query.status } : {}),
          ...(req.query.contractId ? { contractId: req.query.contractId } : {}),
          ...(window ? { scheduledFor: { gte: window.from, lte: window.to } } : {}),
        },
        orderBy: { scheduledFor: "asc" },
        take: 500,
      });
      return { entries, period: window ?? null };
    },
  );

  app.post<{ Params: { id: string }; Body: unknown }>(
    "/commissions/:id/pay",
    { preHandler: requirePermission("commission.entry.pay") },
    async (req, reply) => {
      const schema = z.object({
        payrollId: z.string().optional(),
        note: z.string().optional(),
      });
      const parsed = schema.safeParse(req.body ?? {});
      if (!parsed.success) throw new AppError("Invalid payload", 400, "VALIDATION");

      const entry = await prisma.commissionEntry.findUnique({ where: { id: req.params.id } });
      if (!entry) throw new AppError("Entry not found", 404, "NOT_FOUND");
      assertTenant(req.user, entry.tenantId);
      if (entry.status !== "RELEASED") {
        throw new AppError(
          `Only RELEASED entries can be paid (got ${entry.status})`,
          400,
          "VALIDATION",
        );
      }

      const now = new Date();
      const [updated] = await prisma.$transaction([
        prisma.commissionEntry.update({
          where: { id: entry.id },
          data: { status: "PAID", paidAt: now, paidInPayrollId: parsed.data.payrollId },
        }),
        prisma.provisionedExpense.updateMany({
          where: { sourceType: "COMMISSION", sourceId: entry.id, status: "RELEASED" },
          data: { status: "PAID" },
        }),
      ]);
      return reply.send(updated);
    },
  );

  app.post<{ Params: { id: string }; Body: unknown }>(
    "/contracts/:id/clawback",
    { preHandler: requirePermission("commission.entry.pay") },
    async (req, reply) => {
      const schema = z.object({ reason: z.string().min(3) });
      const parsed = schema.safeParse(req.body);
      if (!parsed.success) throw new AppError("Invalid payload", 400, "VALIDATION");

      const contract = await prisma.contract.findUnique({ where: { id: req.params.id } });
      if (!contract) throw new AppError("Contract not found", 404, "NOT_FOUND");
      assertTenant(req.user, contract.tenantId);

      const result = await prisma.$transaction((tx) =>
        onContractCancelled(req.params.id, parsed.data.reason, tx),
      );
      return reply.send(result);
    },
  );

  app.post(
    "/commissions/tick",
    { preHandler: requirePermission("commission.entry.pay") },
    async (req, reply) => {
      const user = req.user;
      if (!user) throw new AppError("Unauthenticated", 401, "UNAUTHORIZED");
      const result = await releaseDueLocks(user.tenantId);
      return reply.send(result);
    },
  );

  // ─── BONUS ───────────────────────────────────────────────────

  app.post<{ Body: unknown }>(
    "/bonus-rules",
    { preHandler: requirePermission("bonus.rule.write") },
    async (req, reply) => {
      const schema = z.object({
        name: z.string().min(1),
        userId: z.string().uuid().optional(),
        role: z.string().optional(),
        periodType: z.enum(["MONTHLY", "QUARTERLY", "ANNUAL"]).default("MONTHLY"),
        effectiveFrom: z.string().datetime(),
        effectiveTo: z.string().datetime().optional(),
        rampUpMonths: z.number().int().min(0).default(0),
        rampUpFactor: z.number().min(0).max(1).default(0.6),
        maxPayout: z.number().positive().optional(),
        components: z
          .array(
            z.object({
              metric: z.enum([
                "REVENUE",
                "MARGIN",
                "CONVERSION",
                "TICKET_AVG",
                "EVENTS_CLOSED",
                "NPS",
              ]),
              weight: z.number().min(0).max(1),
              target: z.number().nonnegative(),
              basePayout: z.number().nonnegative(),
              acceleratorBands: z
                .array(
                  z.object({
                    minRatio: z.number(),
                    maxRatio: z.number().optional(),
                    multiplier: z.number(),
                  }),
                )
                .optional(),
            }),
          )
          .min(1),
      });
      const parsed = schema.safeParse(req.body);
      if (!parsed.success) throw new AppError("Invalid payload", 400, "VALIDATION");
      const user = req.user;
      if (!user) throw new AppError("Unauthenticated", 401, "UNAUTHORIZED");

      const weightSum = parsed.data.components.reduce((s, c) => s + c.weight, 0);
      if (Math.abs(weightSum - 1) > 0.0001) {
        throw new AppError(
          `Component weights must sum to 1.0 (got ${weightSum})`,
          400,
          "VALIDATION",
        );
      }

      const rule = await prisma.bonusRule.create({
        data: {
          tenantId: user.tenantId,
          name: parsed.data.name,
          userId: parsed.data.userId,
          role: parsed.data.role,
          periodType: parsed.data.periodType,
          effectiveFrom: new Date(parsed.data.effectiveFrom),
          effectiveTo: parsed.data.effectiveTo ? new Date(parsed.data.effectiveTo) : undefined,
          rampUpMonths: parsed.data.rampUpMonths,
          rampUpFactor: parsed.data.rampUpFactor,
          maxPayout: parsed.data.maxPayout,
          components: {
            createMany: {
              data: parsed.data.components.map((c) => ({
                metric: c.metric,
                weight: c.weight,
                target: c.target,
                basePayout: c.basePayout,
                acceleratorBands: c.acceleratorBands ?? [],
              })),
            },
          },
        },
        include: { components: true },
      });
      return reply.status(201).send(rule);
    },
  );

  app.post<{ Params: { id: string }; Body: unknown }>(
    "/bonus-rules/:id/compute",
    { preHandler: requirePermission("bonus.accrual.compute") },
    async (req, reply) => {
      const schema = z.object({
        periodStart: z.string().datetime(),
        periodEnd: z.string().datetime(),
      });
      const parsed = schema.safeParse(req.body);
      if (!parsed.success) throw new AppError("Invalid payload", 400, "VALIDATION");

      const rule = await prisma.bonusRule.findUnique({ where: { id: req.params.id } });
      if (!rule) throw new AppError("BonusRule not found", 404, "NOT_FOUND");
      assertTenant(req.user, rule.tenantId);

      const result = await prisma.$transaction((tx) =>
        computeBonusAccrual(
          req.params.id,
          new Date(parsed.data.periodStart),
          new Date(parsed.data.periodEnd),
          tx,
        ),
      );
      return reply.send(result);
    },
  );

  app.get<{ Querystring: { userId?: string; status?: string } }>(
    "/bonus-accruals",
    { preHandler: authenticate },
    async (req) => {
      const user = req.user;
      if (!user) throw new AppError("Unauthenticated", 401, "UNAUTHORIZED");
      const visibleUserIds = await resolveVisibleUserIds(user, req.query.userId);
      const accruals = await prisma.bonusAccrual.findMany({
        where: {
          tenantId: user.tenantId,
          ...(visibleUserIds ? { userId: { in: visibleUserIds } } : {}),
          ...(req.query.status ? { status: req.query.status } : {}),
        },
        orderBy: { periodStart: "desc" },
        take: 200,
      });
      return { accruals };
    },
  );

  app.post<{ Params: { id: string } }>(
    "/bonus-accruals/:id/approve",
    { preHandler: requirePermission("bonus.accrual.approve") },
    async (req, reply) => {
      const user = req.user;
      if (!user) throw new AppError("Unauthenticated", 401, "UNAUTHORIZED");
      const accrual = await prisma.bonusAccrual.findUnique({ where: { id: req.params.id } });
      if (!accrual) throw new AppError("Accrual not found", 404, "NOT_FOUND");
      assertTenant(user, accrual.tenantId);
      if (accrual.status !== "COMPUTED") {
        throw new AppError(
          `Only COMPUTED accruals can be approved (got ${accrual.status})`,
          400,
          "VALIDATION",
        );
      }
      const updated = await prisma.bonusAccrual.update({
        where: { id: accrual.id },
        data: { status: "APPROVED", approvedBy: user.id, approvedAt: new Date() },
      });
      return reply.send(updated);
    },
  );

  // ─── FINANCE DASHBOARD (com filtros mês/ano/vitalício) ────────

  app.get<{
    Querystring: {
      period?: "month" | "year" | "lifetime";
      from?: string;
      to?: string;
      userId?: string;
    };
  }>(
    "/dashboard",
    { preHandler: requirePermission("commercial.dashboard.read") },
    async (req) => {
      const user = req.user;
      if (!user) throw new AppError("Unauthenticated", 401, "UNAUTHORIZED");
      const tenantId = user.tenantId;
      const visibleUserIds = await resolveVisibleUserIds(user, req.query.userId);
      const window = periodWindow(req.query.period ?? "month", req.query.from, req.query.to);
      const userFilter = visibleUserIds ? { userId: { in: visibleUserIds } } : {};

      const schedFilter = window
        ? { scheduledFor: { gte: window.from, lte: window.to } }
        : {};
      const paidFilter = window ? { paidAt: { gte: window.from, lte: window.to } } : {};

      const [
        commissionForecast,
        commissionReleased,
        commissionPaid,
        commissionByUser,
        paymentsReceived,
        topContracts,
      ] = await Promise.all([
        prisma.commissionEntry.aggregate({
          where: {
            tenantId,
            status: { in: ["FORECAST", "LOCKED"] },
            ...userFilter,
            ...schedFilter,
          },
          _sum: { amount: true },
          _count: true,
        }),
        prisma.commissionEntry.aggregate({
          where: { tenantId, status: "RELEASED", ...userFilter, ...schedFilter },
          _sum: { amount: true },
          _count: true,
        }),
        prisma.commissionEntry.aggregate({
          where: { tenantId, status: "PAID", ...userFilter, ...paidFilter },
          _sum: { amount: true },
          _count: true,
        }),
        prisma.commissionEntry.groupBy({
          by: ["userId"],
          where: { tenantId, ...userFilter, ...schedFilter },
          _sum: { amount: true },
          _count: true,
        }),
        prisma.payment.aggregate({
          where: {
            tenantId,
            status: "CONFIRMED",
            ...(window ? { paidAt: { gte: window.from, lte: window.to } } : {}),
          },
          _sum: { amount: true },
          _count: true,
        }),
        prisma.contract.findMany({
          where: {
            tenantId,
            status: "ACTIVE",
            ...(visibleUserIds ? { salespersonId: { in: visibleUserIds } } : {}),
          },
          orderBy: { totalValue: "desc" },
          take: 10,
          select: {
            id: true,
            contractNumber: true,
            totalValue: true,
            projectedMargin: true,
            signedAt: true,
            salespersonId: true,
            lead: { select: { companyName: true } },
          },
        }),
      ]);

      return {
        period: window ?? { label: "lifetime", from: null, to: null },
        scope: visibleUserIds ? { userIds: visibleUserIds } : { tenant: tenantId },
        commissions: {
          forecast: {
            count: commissionForecast._count,
            amount: commissionForecast._sum.amount ?? 0,
          },
          released: {
            count: commissionReleased._count,
            amount: commissionReleased._sum.amount ?? 0,
          },
          paid: {
            count: commissionPaid._count,
            amount: commissionPaid._sum.amount ?? 0,
          },
          byUser: commissionByUser.map((r) => ({
            userId: r.userId,
            count: r._count,
            amount: r._sum.amount ?? 0,
          })),
        },
        payments: {
          received: {
            count: paymentsReceived._count,
            amount: paymentsReceived._sum.amount ?? 0,
          },
        },
        topContracts,
      };
    },
  );
}

// ─── Helpers ───────────────────────────────────────────────────

function assertTenant(user: AuthUser | undefined, tenantId: string): void {
  if (!user) throw new AppError("Unauthenticated", 401, "UNAUTHORIZED");
  if (user.tenantId !== tenantId) {
    throw new AppError("Cross-tenant access denied", 403, "FORBIDDEN");
  }
}

async function resolveVisibleUserIds(
  user: AuthUser,
  explicitUserId: string | undefined,
): Promise<string[] | undefined> {
  if (user.role === "finance" || user.role === "admin") {
    return explicitUserId ? [explicitUserId] : undefined;
  }
  if (user.role === "sales_manager" || user.role === "manager") {
    const reports = await prisma.user.findMany({
      where: { tenantId: user.tenantId, managerId: user.id },
      select: { id: true },
    });
    const ids = [user.id, ...reports.map((r) => r.id)];
    if (explicitUserId) {
      if (!ids.includes(explicitUserId)) {
        logger.warn(
          { userId: user.id, requested: explicitUserId },
          "finance: out-of-team query denied",
        );
        throw new AppError("Cannot query users outside your team", 403, "FORBIDDEN");
      }
      return [explicitUserId];
    }
    return ids;
  }
  if (explicitUserId && explicitUserId !== user.id) {
    throw new AppError("Can only query your own data", 403, "FORBIDDEN");
  }
  return [user.id];
}

// Resolve a time window for dashboard filters. "month" = current month,
// "year" = current year, "lifetime" or missing = unbounded (returns null).
// Explicit from/to strings override the preset.
function periodWindow(
  preset?: "month" | "year" | "lifetime",
  from?: string,
  to?: string,
): { label: string; from: Date; to: Date } | null {
  if (from && to) {
    return { label: "custom", from: new Date(from), to: new Date(to) };
  }
  const now = new Date();
  if (preset === "year") {
    return {
      label: "year",
      from: new Date(now.getFullYear(), 0, 1),
      to: new Date(now.getFullYear(), 11, 31, 23, 59, 59, 999),
    };
  }
  if (preset === "month") {
    return {
      label: "month",
      from: new Date(now.getFullYear(), now.getMonth(), 1),
      to: new Date(now.getFullYear(), now.getMonth() + 1, 0, 23, 59, 59, 999),
    };
  }
  return null;
}
