import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { approvalController } from "../controllers/approval-controller";
import { prisma } from "../db";
import {
  devAuth,
  requirePermission,
  hasPermission,
} from "../middleware/auth";
import { AppError } from "../utils/app-error";

// Risk-aware gate: R3 requires finance/admin; R0/R1/R2 allow manager/finance/admin.
async function gateApprovalByRisk(
  request: FastifyRequest<{ Params: { id: string } }>,
  _reply: FastifyReply,
) {
  const { id } = request.params;
  const approval = await prisma.approvalRequest.findUnique({
    where: { id },
    select: { riskLevel: true },
  });
  if (!approval) {
    throw new AppError("Approval request not found", 404, "NOT_FOUND");
  }
  const role = request.user?.role;
  if (!role) {
    throw new AppError("Unauthenticated", 401, "UNAUTHORIZED");
  }
  const isHighRisk =
    approval.riskLevel === "R3" ||
    approval.riskLevel === "R4" ||
    approval.riskLevel === "high" ||
    approval.riskLevel === "critical";
  const permission = isHighRisk
    ? "approvals.high.approve"
    : "approvals.low.approve";
  if (!hasPermission(role, permission)) {
    throw new AppError(
      `Role '${role}' cannot approve a ${approval.riskLevel} request`,
      403,
      "FORBIDDEN",
    );
  }
}

export async function approvalsRoutes(app: FastifyInstance) {
  app.addHook("preHandler", devAuth);

  app.post(
    "/:id/approve",
    { preHandler: gateApprovalByRisk },
    async (req, res) => approvalController.approve(req as any, res),
  );

  app.post(
    "/:id/reject",
    { preHandler: gateApprovalByRisk },
    async (req, res) => approvalController.reject(req as any, res),
  );

  app.get(
    "/pending",
    { preHandler: requirePermission("approvals.low.approve") },
    async (req, res) => approvalController.listPending(req, res),
  );

  app.get("/:id", async (req, res) => approvalController.getById(req as any, res));
}
