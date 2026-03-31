import { FastifyReply, FastifyRequest } from "fastify";
import { MemoryService } from "../services/memory-service";
import { AppError } from "../utils/app-error";

const service = new MemoryService();

export class MemoryController {
  /**
   * Create new memory
   */
  async create(
    request: FastifyRequest<{
      Body: {
        companyId: string;
        memoryType: string;
        title: string;
        content: string;
        tags?: string[];
      };
    }>,
    reply: FastifyReply
  ) {
    try {
      const result = await service.create(request.body);
      return reply.status(201).send({
        success: true,
        data: result
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to create memory";
      throw new AppError(message, 500, "CREATE_ERROR");
    }
  }

  /**
   * Search memories
   */
  async search(
    request: FastifyRequest<{ Querystring: { companyId: string; q: string } }>,
    reply: FastifyReply
  ) {
    try {
      const { companyId, q } = request.query;

      if (!companyId || !q) {
        throw new AppError("companyId and q are required", 422, "VALIDATION_ERROR");
      }

      const result = await service.search(companyId, q);
      return reply.status(200).send({
        success: true,
        count: result.length,
        results: result
      });
    } catch (error) {
      if (error instanceof AppError) throw error;
      const message = error instanceof Error ? error.message : "Search failed";
      throw new AppError(message, 500, "SEARCH_ERROR");
    }
  }
}

// Singleton
export const memoryController = new MemoryController();
