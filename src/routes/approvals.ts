import { FastifyInstance } from "fastify";
import { z } from "zod";
import { prisma } from "../db";
import { AppError } from "../utils/app-error";
import { jsonLogger as logger } from "../utils/logger";

const ApprovalActionSchema = z.object({
  approved: z.boolean(),
  reason: z.string().optional(),
});

export async function approvalsRoutes(app: FastifyInstance) {
  // POST /approvals/:id/approve
  app.post("/:id/approve", async (req, res) => {
    const { id } = req.params as { id: string };
    const parsed = ApprovalActionSchema.parse(req.body);

    const approval = await prisma.approvalRequest.findUnique({ where: { id } });
    if (!approval) throw new AppError("Approval not found", 404, "NOT_FOUND");
    if (approval.status !== "pending") throw new AppError("Already processed", 409, "CONFLICT");

    const updated = await prisma.approvalRequest.update({
      where: { id },
      data: {
        status: parsed.approved ? "APPROVED" : "REJECTED",
        approvedBy: "user-123",
        approvedAt: new Date(),
      },
    });

    // Update agent run status
    await prisma.agentRun.update({
      where: { id: approval.agentRunId },
      data: { status: parsed.approved ? "approved" : "rejected" },
    });

    logger.info("Approval processed", { id, approved: parsed.approved });
    return { success: true, data: updated };
  });

  // POST /approvals/:id/reject
  app.post("/:id/reject", async (req, res) => {
    const { id } = req.params as { id: string };
    const parsed = ApprovalActionSchema.parse(req.body);
    
    // Shortcut to approve with false
    req.body = { ...parsed, approved: false };
    return app.inject({ method: "POST", url: `/${id}/approve`, payload: req.body });
  });
}
