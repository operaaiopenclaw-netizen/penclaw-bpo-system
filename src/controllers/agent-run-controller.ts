import { FastifyReply, FastifyRequest } from "fastify";
import { agentRunService } from "../services/agent-run-service";
import { prisma } from "../db";

export class AgentRunController {
  async create(req: FastifyRequest, reply: FastifyReply) {
    try {
      const result = await agentRunService.create(req.body as any);
      return reply.send({
        success: true,
        message: "Agent run queued for async processing",
        runId: result.runId,
        status: result.status
      });
    } catch (error: any) {
      return reply.status(500).send({
        statusCode: 500,
        error: "Internal Server Error",
        message: error?.message || "Unknown error"
      });
    }
  }

  async getById(req: FastifyRequest, reply: FastifyReply) {
    const { id } = req.params as { id?: string };

    if (!id) {
      return reply.status(400).send({
        statusCode: 400,
        error: "Bad Request",
        message: "Agent run id is required"
      });
    }

    try {
      const result = await agentRunService.getById(id);

      if (!result) {
        return reply.status(404).send({
          statusCode: 404,
          error: "Not Found",
          message: "Agent run not found"
        });
      }

      return reply.send(result);
    } catch (error: any) {
      return reply.status(500).send({
        statusCode: 500,
        error: "Internal Server Error",
        message: error?.message || "Unknown error"
      });
    }
  }

  async list(_req: FastifyRequest, reply: FastifyReply) {
    try {
      const result = await agentRunService.list();
      return reply.send(result);
    } catch (error: any) {
      return reply.status(500).send({
        statusCode: 500,
        error: "Internal Server Error",
        message: error?.message || "Unknown error"
      });
    }
  }

  async replay(req: FastifyRequest, reply: FastifyReply) {
    const { id } = req.params as { id?: string };

    if (!id) {
      return reply.status(400).send({
        statusCode: 400,
        error: "Bad Request",
        message: "Agent run id is required"
      });
    }

    try {
      // Get original run
      const original = await prisma.agentRun.findUnique({
        where: { id }
      });

      if (!original) {
        return reply.status(404).send({
          statusCode: 404,
          error: "Not Found",
          message: "Original agent run not found"
        });
      }

      // Parse original input
      let originalInput: Record<string, unknown> = {};
      try {
        originalInput = JSON.parse(original.inputSummary || "{}");
      } catch {
        originalInput = {};
      }

      // Create new run with same params
      const result = await agentRunService.create({
        companyId: original.companyId || undefined,
        workflowType: original.workflowType,
        input: originalInput
      });

      return reply.send({
        success: true,
        message: "Agent run replayed",
        originalRunId: id,
        newRunId: result.runId,
        workflowType: original.workflowType,
        status: result.status
      });
    } catch (error: any) {
      return reply.status(500).send({
        statusCode: 500,
        error: "Internal Server Error",
        message: error?.message || "Unknown error"
      });
    }
  }
}

export const agentRunController = new AgentRunController();
