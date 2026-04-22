// ============================================================
// EVENTS ROUTES - Event Store API
// SPRINT 1: Query endpoints
// ============================================================

import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { z } from "zod";
import { eventStore } from "../event-store";
import { eventHooks } from "../event-store/hooks";
import { logger } from "../utils/logger";
import { prisma } from "../db";
import { config } from "../config/env";

const DEFAULT_TENANT = config.DEFAULT_TENANT_ID;

const listEventsSchema = z.object({
  tenantId: z.string().default(DEFAULT_TENANT),
  limit: z.coerce.number().max(100).default(50),
  offset: z.coerce.number().default(0)
});

const listByAggregateSchema = z.object({
  tenantId: z.string().default(DEFAULT_TENANT),
  aggregateType: z.enum(["event", "inventory", "procurement", "finance", "commercial"]),
  aggregateId: z.string()
});

const listByTypeSchema = z.object({
  tenantId: z.string().default(DEFAULT_TENANT),
  eventType: z.enum([
    "event.created",
    "event.updated",
    "event.planning.created",
    "event.financials.created",
    "event.margin.calculated"
  ]),
  limit: z.coerce.number().max(100).default(50)
});

export async function eventsRoutes(fastify: FastifyInstance): Promise<void> {
  
  // GET /events - Listar todos os eventos do tenant
  fastify.get("/", async (request: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    try {
      const params = listEventsSchema.parse(request.query);
      
      const events = await eventStore.listByTenant(
        params.tenantId,
        params.limit,
        params.offset
      );

      return reply.send({
        success: true,
        data: events,
        meta: {
          tenantId: params.tenantId,
          count: events.length,
          limit: params.limit,
          offset: params.offset
        }
      });
    } catch (error) {
      logger.error("Events route: list failed", { error });
      return reply.status(400).send({
        success: false,
        error: "Invalid parameters",
        message: error instanceof Error ? error.message : "Unknown error"
      });
    }
  });

  // GET /events/aggregate/:aggregateType/:aggregateId
  fastify.get("/aggregate/:aggregateType/:aggregateId", async (
    request: FastifyRequest<{ 
      Params: { aggregateType: string; aggregateId: string };
      Querystring: unknown 
    }>,
    reply: FastifyReply
  ) => {
    try {
      const params = listByAggregateSchema.parse({
        ...(request.query as Record<string, unknown>),
        aggregateType: request.params.aggregateType,
        aggregateId: request.params.aggregateId
      });

      const events = await eventStore.listByAggregate(
        params.tenantId,
        params.aggregateType,
        params.aggregateId
      );

      return reply.send({
        success: true,
        data: events,
        meta: {
          tenantId: params.tenantId,
          aggregateType: params.aggregateType,
          aggregateId: params.aggregateId,
          count: events.length
        }
      });
    } catch (error) {
      logger.error("Events route: aggregate failed", { error });
      return reply.status(400).send({
        success: false,
        error: "Invalid parameters"
      });
    }
  });

  // GET /events/type/:eventType
  fastify.get("/type/:eventType", async (
    request: FastifyRequest<{ 
      Params: { eventType: string };
      Querystring: unknown 
    }>,
    reply: FastifyReply
  ) => {
    try {
      const params = listByTypeSchema.parse({
        ...(request.query as Record<string, unknown>),
        eventType: request.params.eventType
      });

      const events = await eventStore.listByType(
        params.tenantId,
        params.eventType,
        params.limit
      );

      return reply.send({
        success: true,
        data: events,
        meta: {
          tenantId: params.tenantId,
          eventType: params.eventType,
          count: events.length
        }
      });
    } catch (error) {
      logger.error("Events route: type failed", { error });
      return reply.status(400).send({
        success: false,
        error: "Invalid parameters"
      });
    }
  });

  // GET /events/:id
  fastify.get("/:id", async (
    request: FastifyRequest<{ Params: { id: string } }>,
    reply: FastifyReply
  ) => {
    try {
      const event = await eventStore.getById(request.params.id);

      if (!event) {
        return reply.status(404).send({
          success: false,
          error: "Event not found"
        });
      }

      return reply.send({
        success: true,
        data: event
      });
    } catch (error) {
      logger.error("Events route: getById failed", { error });
      return reply.status(500).send({
        success: false,
        error: "Internal error"
      });
    }
  });

  // POST /events/test - Criar evento de teste
  fastify.post("/test", async (
    request: FastifyRequest<{ Body: { eventName?: string } }>,
    reply: FastifyReply
  ) => {
    try {
      logger.info("Events route: creating test event");
      
      const result = await eventHooks.createTestEvent(
        request.body?.eventName || "Casamento Teste Orkestra"
      );

      // Buscar eventos criados para validação
      const systemEvents = await eventStore.listByAggregate(
        DEFAULT_TENANT,
        "event",
        result.eventId
      );

      return reply.send({
        success: true,
        message: "Test event created successfully",
        data: {
          eventId: result.eventId,
          tests: result.tests,
          systemEvents: systemEvents.map(e => ({
            id: e.id,
            eventType: e.eventType,
            status: e.status,
            createdAt: e.createdAt
          }))
        }
      });
    } catch (error) {
      logger.error("Events route: test failed", { error });
      return reply.status(500).send({
        success: false,
        error: "Failed to create test event",
        message: error instanceof Error ? error.message : "Unknown error"
      });
    }
  });

  // GET /events/test/validate - Validar dados de teste
  fastify.get("/test/validate", async (
    request: FastifyRequest<{ Querystring: { tenantId?: string } }>,
    reply: FastifyReply
  ) => {
    try {
      const tenantId = request.query.tenantId || DEFAULT_TENANT;
      
      // Contar eventos por tipo
      const allEvents = await eventStore.listByTenant(tenantId, 100, 0);
      
      const stats = {
        total: allEvents.length,
        byType: {} as Record<string, number>,
        byStatus: {} as Record<string, number>,
        byAggregate: {} as Record<string, number>
      };

      for (const event of allEvents) {
        stats.byType[event.eventType] = (stats.byType[event.eventType] || 0) + 1;
        stats.byStatus[event.status] = (stats.byStatus[event.status] || 0) + 1;
        stats.byAggregate[event.aggregateType] = (stats.byAggregate[event.aggregateType] || 0) + 1;
      }

      // Contar domain logs
      const domainLogs = await prisma.domainLog.count({
        where: { tenantId }
      });

      return reply.send({
        success: true,
        data: {
          tenantId,
          systemEvents: stats,
          domainLogsCount: domainLogs,
          validation: {
            hasEvents: stats.total > 0,
            hasCreatedEvents: stats.byType["event.created"] > 0,
            hasMarginEvents: stats.byType["event.margin.calculated"] > 0,
            hasFinanceEvents: stats.byType["event.financials.created"] > 0
          }
        }
      });
    } catch (error) {
      logger.error("Events route: validate failed", { error });
      return reply.status(500).send({
        success: false,
        error: "Validation failed"
      });
    }
  });
}
