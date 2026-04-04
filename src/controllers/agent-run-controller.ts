import { FastifyReply, FastifyRequest } from "fastify";
import { agentRunService } from "../services/agent-run-service";

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
}

export const agentRunController = new AgentRunController();
