// ============================================================
// VETAGENT: AI Chat Endpoint - POST /ai/chat
// ============================================================

import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { z } from "zod";
import { vetAgent } from "../services/vetAgent";
import { logger } from "../utils/logger";

// Request schema validation
const aiChatSchema = z.object({
  petId: z.string().min(1, "Pet ID is required"),
  message: z.string().min(1, "Message is required").max(2000, "Message too long"),
  userId: z.string().optional(),
  metadata: z.object({
    deviceType: z.string().optional(),
    appVersion: z.string().optional(),
  }).optional(),
});

type AIChatRequest = z.infer<typeof aiChatSchema>;

/**
 * AI Chat routes for VetAgent
 */
export async function aiChatRoutes(fastify: FastifyInstance): Promise<void> {
  // Health check
  fastify.get("/ai/health", async (_request: FastifyRequest, reply: FastifyReply) => {
    return reply.send({
      status: "ok",
      service: "VetAgent",
      timestamp: Date.now(),
    });
  });

  /**
   * POST /ai/chat
   * Main VetAgent endpoint for veterinary AI assistance
   */
  fastify.post(
    "/ai/chat",
    {
      schema: {
        summary: "VetAgent Chat",
        description: "Send a veterinary question about your pet to get AI-powered guidance",
        tags: ["AI"],
        body: {
          type: "object",
          required: ["petId", "message"],
          properties: {
            petId: { type: "string", description: "The pet's unique identifier" },
            message: { type: "string", maxLength: 2000, description: "Your veterinary question or concern" },
            userId: { type: "string", description: "Optional user identifier for tracking" },
            metadata: {
              type: "object",
              properties: {
                deviceType: { type: "string" },
                appVersion: { type: "string" },
              },
            },
          },
        },
        response: {
          200: {
            type: "object",
            properties: {
              success: { type: "boolean" },
              data: {
                type: "object",
                properties: {
                  analysis: { type: "string" },
                  possibleCauses: { type: "array", items: { type: "string" } },
                  severity: { type: "string", enum: ["low", "medium", "high"] },
                  recommendation: { type: "string" },
                  needsVet: { type: "boolean" },
                  triggeredSafetyRule: { type: ["string", "null"] },
                  disclaimer: { type: "string" },
                },
              },
              meta: {
                type: "object",
                properties: {
                  latencyMs: { type: "number" },
                  tokensUsed: { type: "number" },
                  safetyTriggered: { type: "boolean" },
                },
              },
            },
          },
          400: {
            type: "object",
            properties: {
              error: { type: "string" },
              details: { type: "object" },
            },
          },
          500: {
            type: "object",
            properties: {
              error: { type: "string" },
              message: { type: "string" },
            },
          },
        },
      },
    },
    async (request: FastifyRequest<{ Body: AIChatRequest }>, reply: FastifyReply) => {
      const startTime = Date.now();

      try {
        // Validate request
        const validation = aiChatSchema.safeParse(request.body);
        
        if (!validation.success) {
          logger.warn({ errors: validation.error.errors }, "Invalid AI chat request");
          return reply.status(400).send({
            error: "Invalid request",
            details: validation.error.flatten(),
          });
        }

        const { petId, message, userId, metadata } = validation.data;

        logger.info(
          { petId, messagePreview: message.substring(0, 50), userId: userId || "anonymous" },
          "VetAgent: Processing chat request"
        );

        // Process with VetAgent
        const result = await vetAgent.processQuestion({
          petId,
          message,
          userId,
          metadata,
        });

        // Build response
        return reply.send({
          success: true,
          data: result.response,
          meta: {
            latencyMs: result.latencyMs,
            tokensUsed: result.tokensUsed,
            safetyTriggered: result.safetyTriggered,
            totalLatencyMs: Date.now() - startTime,
          },
        });

      } catch (error) {
        logger.error({ error, petId: request.body?.petId }, "VetAgent: Error processing chat");
        
        const errorMessage = error instanceof Error ? error.message : "Unknown error";
        
        return reply.status(500).send({
          error: "Internal server error",
          message: errorMessage,
        });
      }
    }
  );

  /**
   * GET /ai/chat/history/:petId
   * Get conversation history for a pet
   */
  fastify.get(
    "/ai/chat/history/:petId",
    {
      schema: {
        summary: "Get Pet Chat History",
        description: "Retrieve recent VetAgent interactions for a specific pet",
        tags: ["AI"],
        params: {
          type: "object",
          required: ["petId"],
          properties: {
            petId: { type: "string" },
          },
        },
        querystring: {
          type: "object",
          properties: {
            limit: { type: "number", default: 10 },
          },
        },
      },
    },
    async (request: FastifyRequest<{
      Params: { petId: string };
      Querystring: { limit?: string };
    }>, reply: FastifyReply) => {
      try {
        const { petId } = request.params;
        const limit = Math.min(parseInt(request.query.limit || "10"), 50);

        const history = await vetAgent.getPetInteractionHistory(petId, limit);

        return reply.send({
          success: true,
          data: history,
          meta: { petId, count: history.length },
        });
      } catch (error) {
        logger.error({ error, petId: request.params.petId }, "VetAgent: Error getting history");
        
        if (error instanceof Error && error.message === "Pet not found") {
          return reply.status(404).send({
            error: "Pet not found",
            message: "No pet exists with the provided ID",
          });
        }

        return reply.status(500).send({
          error: "Internal server error",
        });
      }
    }
  );
}
