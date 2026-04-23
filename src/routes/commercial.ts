import { FastifyInstance } from "fastify";
import { z } from "zod";
import { prisma } from "../db";
import { authenticate, requirePermission, AuthUser } from "../middleware/auth";
import { AppError } from "../utils/app-error";
import { logger } from "../utils/logger";

// Módulo Comercial — jornada do cliente até a assinatura do contrato.
// Pipeline, propostas, contratos, parcelas (definidas na venda), relatórios.
// NADA de comissão, pagamento recebido ou bônus aqui — isso vive em /finance.

export async function commercialRoutes(app: FastifyInstance): Promise<void> {
  // ─── CONTRACT INSTALLMENTS (parcelas definidas na venda) ──────

  app.post<{ Params: { id: string }; Body: unknown }>(
    "/contracts/:id/installments",
    { preHandler: requirePermission("installments.write") },
    async (req, reply) => {
      const { id: contractId } = req.params;
      const schema = z.object({
        installments: z
          .array(
            z.object({
              seq: z.number().int().positive(),
              dueDate: z.string().datetime(),
              amount: z.number().positive(),
            }),
          )
          .min(1),
      });
      const parsed = schema.safeParse(req.body);
      if (!parsed.success) throw new AppError("Invalid payload", 400, "VALIDATION");

      const contract = await prisma.contract.findUnique({ where: { id: contractId } });
      if (!contract) throw new AppError("Contract not found", 404, "NOT_FOUND");
      assertTenant(req.user, contract.tenantId);

      const existing = await prisma.contractInstallment.count({ where: { contractId } });
      if (existing > 0) {
        throw new AppError("Installments already exist for this contract", 409, "CONFLICT");
      }

      const sum = parsed.data.installments.reduce((s, i) => s + i.amount, 0);
      if (Math.abs(sum - contract.totalValue) > 0.01) {
        throw new AppError(
          `Installments sum (${sum}) does not match contract.totalValue (${contract.totalValue})`,
          400,
          "VALIDATION",
        );
      }

      const rows = parsed.data.installments.map((i) => ({
        tenantId: contract.tenantId,
        contractId,
        seq: i.seq,
        dueDate: new Date(i.dueDate),
        amount: i.amount,
      }));
      await prisma.contractInstallment.createMany({ data: rows });

      return reply.status(201).send({ created: rows.length });
    },
  );

  app.get<{ Params: { id: string } }>(
    "/contracts/:id/installments",
    { preHandler: authenticate },
    async (req) => {
      const contract = await prisma.contract.findUnique({
        where: { id: req.params.id },
        include: { installments: { orderBy: { seq: "asc" } } },
      });
      if (!contract) throw new AppError("Contract not found", 404, "NOT_FOUND");
      assertTenant(req.user, contract.tenantId);
      return { installments: contract.installments };
    },
  );

  // ─── PIPELINE DASHBOARD (sem dados de comissão) ──────────────

  app.get(
    "/dashboard",
    { preHandler: requirePermission("commercial.dashboard.read") },
    async (req) => {
      const user = req.user;
      if (!user) throw new AppError("Unauthenticated", 401, "UNAUTHORIZED");
      const visibleUserIds = await resolveVisibleUserIds(user, undefined);
      const tenantId = user.tenantId;
      const salesFilter = visibleUserIds ? { salespersonId: { in: visibleUserIds } } : {};

      const [pipelineActive, won, lost, topByMargin] = await Promise.all([
        prisma.contract.aggregate({
          where: { tenantId, status: "ACTIVE", ...salesFilter },
          _count: true,
          _sum: { totalValue: true, projectedMargin: true },
        }),
        prisma.contract.count({ where: { tenantId, status: "ACTIVE", ...salesFilter } }),
        prisma.contract.count({ where: { tenantId, status: "CANCELLED", ...salesFilter } }),
        prisma.contract.findMany({
          where: { tenantId, status: "ACTIVE", ...salesFilter },
          orderBy: { projectedMargin: "desc" },
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
        scope: visibleUserIds ? { userIds: visibleUserIds } : { tenant: tenantId },
        pipeline: {
          active: {
            count: pipelineActive._count,
            totalValue: pipelineActive._sum.totalValue ?? 0,
            totalMargin: pipelineActive._sum.projectedMargin ?? 0,
          },
          won,
          lost,
        },
        topContracts: topByMargin,
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
          "commercial: out-of-team query denied",
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
