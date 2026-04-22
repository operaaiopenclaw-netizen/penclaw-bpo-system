// ============================================================
// KITCHEN ROUTES
// POST /kitchen/sync — bridge Python pipeline → Prisma Event
// ============================================================

import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { z } from "zod";
import { syncKitchenFinancials } from "../services/kitchen-sync";
import { logger } from "../utils/logger";

const syncQuerySchema = z.object({
  eventId: z.string().optional(),
});

export async function kitchenRoutes(fastify: FastifyInstance): Promise<void> {
  // POST /kitchen/sync
  fastify.post(
    "/sync",
    async (
      request: FastifyRequest<{ Querystring: unknown }>,
      reply: FastifyReply
    ) => {
      try {
        const { eventId } = syncQuerySchema.parse(request.query);

        logger.info("KitchenSync: sync requested", { filter: eventId ?? "all" });

        const result = await syncKitchenFinancials(eventId);

        const statusCode = result.success ? 200 : 207; // 207 = partial success

        return reply.status(statusCode).send({
          success:            result.success,
          eventsProcessed:    result.eventsProcessed,
          eventsCreated:      result.eventsCreated,
          eventsUpdated:      result.eventsUpdated,
          statesTransitioned: result.statesTransitioned,
          statesSkipped:      result.statesSkipped,
          workflowsQueued:    result.workflowsQueued,
          workflowsFailed:    result.workflowsFailed,
          ...(result.errors.length > 0 && { errors: result.errors }),
        });
      } catch (err) {
        logger.error("KitchenSync route: unexpected error", { error: err });
        return reply.status(500).send({
          success: false,
          error: "Sync failed",
          message: err instanceof Error ? err.message : "Unknown error",
        });
      }
    }
  );
}
