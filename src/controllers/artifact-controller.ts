import { FastifyReply, FastifyRequest } from "fastify";
import { artifactService } from "../services/artifact-service";
import { AppError } from "../utils/app-error";
import { z } from "zod";

const RenderArtifactSchema = z.object({
  agentRunId: z.string().uuid(),
  artifactType: z.enum(["csv", "json", "pdf", "report", "text"]),
  fileName: z.string().min(1),
  content: z.string().or(z.record(z.any()))
});

export class ArtifactController {
  /**
   * Render new artifact
   */
  async render(request: FastifyRequest, reply: FastifyReply) {
    try {
      const parsed = RenderArtifactSchema.safeParse(request.body);
      if (!parsed.success) {
        throw new AppError(parsed.error.message, 422, "VALIDATION_ERROR");
      }

      const data = parsed.data;

      // Determine if content is object or string
      const content = typeof data.content === "object" 
        ? JSON.stringify(data.content, null, 2)
        : data.content;

      const result = await artifactService.renderTextArtifact({
        agentRunId: data.agentRunId,
        artifactType: data.artifactType,
        fileName: data.fileName,
        content
      });

      return reply.status(201).send({
        success: true,
        data: result
      });
    } catch (error) {
      if (error instanceof AppError) throw error;
      const message = error instanceof Error ? error.message : "Render failed";
      throw new AppError(message, 500, "RENDER_ERROR");
    }
  }

  /**
   * Get artifact by ID
   */
  async getById(
    request: FastifyRequest<{ Params: { id: string } }>,
    reply: FastifyReply
  ) {
    try {
      const { id } = request.params;
      const artifact = await artifactService.getById(id);

      if (!artifact) {
        throw new AppError("Artifact not found", 404, "NOT_FOUND");
      }

      return reply.status(200).send({
        success: true,
        data: artifact
      });
    } catch (error) {
      if (error instanceof AppError) throw error;
      const message = error instanceof Error ? error.message : "Failed to get artifact";
      throw new AppError(message, 500, "GET_ERROR");
    }
  }

  /**
   * List artifacts by run
   */
  async listByRun(
    request: FastifyRequest<{ Querystring: { agentRunId: string } }>,
    reply: FastifyReply
  ) {
    try {
      const { agentRunId } = request.query;
      
      if (!agentRunId) {
        throw new AppError("agentRunId is required", 422, "VALIDATION_ERROR");
      }

      const results = await artifactService.listByRun(agentRunId);

      return reply.status(200).send({
        success: true,
        count: results.length,
        results
      });
    } catch (error) {
      if (error instanceof AppError) throw error;
      const message = error instanceof Error ? error.message : "Failed to list artifacts";
      throw new AppError(message, 500, "LIST_ERROR");
    }
  }
}

// Singleton
export const artifactController = new ArtifactController();
