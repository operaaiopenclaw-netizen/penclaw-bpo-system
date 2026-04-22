import { FastifyReply, FastifyRequest } from "fastify";
import { prisma } from "../db";
import { AppError } from "../utils/app-error";
import { jsonLogger as logger } from "../utils/logger";
import { orchestrator } from "../orchestrator";
import { z } from "zod";

const approvalActionSchema = z.object({
  approved: z.boolean(),
  reason: z.string().optional()
});

const approvalIdSchema = z.object({
  id: z.string().uuid("Invalid approval ID")
});

export class ApprovalController {
  /**
   * Approve a request
   */
  async approve(
    request: FastifyRequest<{ Params: { id: string } }>,
    reply: FastifyReply
  ) {
    try {
      const { id } = approvalIdSchema.parse(request.params);
      const body = approvalActionSchema.parse(request.body);

      logger.info("ApprovalController: approving request", {
        approvalId: id,
        approved: body.approved
      });

      const approval = await prisma.approvalRequest.findUnique({
        where: { id }
      });

      if (!approval) {
        throw new AppError("Approval request not found", 404, "NOT_FOUND");
      }

      if (approval.status !== "pending") {
        throw new AppError("Approval request already processed", 409, "CONFLICT");
      }

      const updated = await prisma.approvalRequest.update({
        where: { id },
        data: {
          status: body.approved ? "APPROVED" : "REJECTED",
          approvedBy: request.user?.id || "system", // Assuming auth middleware sets user
          approvedAt: new Date(),
          justification: body.reason || approval.justification
        }
      });

      // Resume or reject the run
      if (body.approved) {
        logger.info("Resuming run after approval", { agentRunId: approval.agentRunId });
        // Async resume — orchestrator.resume() handles all status transitions
        orchestrator.resume(approval.agentRunId).catch((error) => {
          logger.error("Failed to resume run after approval", {
            agentRunId: approval.agentRunId,
            error: error instanceof Error ? error.message : String(error)
          });
        });
      } else {
        await prisma.agentRun.update({
          where: { id: approval.agentRunId },
          data: { status: "rejected" }
        });
      }

      return reply.status(200).send({
        success: true,
        data: updated,
        message: body.approved ? "Request approved" : "Request rejected"
      });

    } catch (error) {
      if (error instanceof AppError) throw error;
      
      const message = error instanceof Error ? error.message : "Approval failed";
      throw new AppError(message, 500, "APPROVAL_ERROR");
    }
  }

  /**
   * Reject a request (convenience method)
   */
  async reject(
    request: FastifyRequest<{ Params: { id: string } }>,
    reply: FastifyReply
  ) {
    // Force approved = false
    (request as any).body = { ...(request.body as any), approved: false };
    return this.approve(request, reply);
  }

  /**
   * Get approval by ID
   */
  async getById(
    request: FastifyRequest<{ Params: { id: string } }>,
    reply: FastifyReply
  ) {
    const { id } = approvalIdSchema.parse(request.params);

    const approval = await prisma.approvalRequest.findUnique({
      where: { id },
      include: {
        agentRun: true
      }
    });

    if (!approval) {
      throw new AppError("Approval request not found", 404, "NOT_FOUND");
    }

    return reply.status(200).send({
      success: true,
      data: approval
    });
  }

  /**
   * List pending approvals
   */
  async listPending(request: FastifyRequest, reply: FastifyReply) {
    const query = request.query as { limit?: string; offset?: string };

    const approvals = await prisma.approvalRequest.findMany({
      where: { status: "pending" },
      orderBy: { requestedAt: "asc" },
      take: query.limit ? parseInt(query.limit, 10) : 20,
      skip: query.offset ? parseInt(query.offset, 10) : 0,
      include: {
        agentRun: {
          select: {
            id: true,
            workflowType: true,
            companyId: true
          }
        }
      }
    });

    return reply.status(200).send({
      success: true,
      data: approvals,
      count: approvals.length
    });
  }
}

// Singleton
export const approvalController = new ApprovalController();
