import { FastifyReply, FastifyRequest } from "fastify";
import { AgentRunService } from "../services/agent-run-service";
import { createAgentRunSchema, agentRunIdSchema } from "../schemas/agent-run";
import { AppError } from "../utils/app-error";

const service = new AgentRunService();

export class AgentRunController {
  /**
   * Create new agent run
   */
  async create(request: FastifyRequest, reply: FastifyReply) {
    try {
      const body = createAgentRunSchema.parse(request.body);
      const result = await service.createAndExecute(body);
      return reply.status(201).send(result);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Validation failed";
      throw new AppError(message, 422, "VALIDATION_ERROR");
    }
  }

  /**
   * Get run by ID
   */
  async getById(
    request: FastifyRequest<{ Params: { id: string } }>,
    reply: FastifyReply
  ) {
    try {
      const { id } = agentRunIdSchema.parse(request.params);
      const result = await service.getById(id.id);
      return reply.status(200).send(result);
    } catch (error) {
      if (error instanceof Error && error.message.includes("not found")) {
        throw new AppError("Agent run not found", 404, "NOT_FOUND");
      }
      throw error;
    }
  }

  /**
   * List runs
   */
  async list(request: FastifyRequest, reply: FastifyReply) {
    const query = request.query as {
      companyId?: string;
      status?: string;
      limit?: string;
      offset?: string;
    };

    const result = await service.list({
      companyId: query.companyId,
      status: query.status,
      limit: query.limit ? parseInt(query.limit, 10) : 20,
      offset: query.offset ? parseInt(query.offset, 10) : 0
    });

    return reply.status(200).send(result);
  }
}

// Export singleton instance methods
export const agentRunController = new AgentRunController();
