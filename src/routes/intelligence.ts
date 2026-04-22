// ============================================================
// INTELLIGENCE ROUTES — /intelligence/*
// ============================================================
import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { z } from "zod";
import {
  decisionEngine,
  forecastEngine,
  supplierIntelligence,
  insightsEngine,
} from "../intelligence";
import { config } from "../config/env";
import { logger } from "../utils/logger";
import { prisma } from "../db";
import { devAuth, requirePermission } from "../middleware/auth";

const DEFAULT_TENANT = config.DEFAULT_TENANT_ID;

export async function intelligenceRoutes(fastify: FastifyInstance): Promise<void> {
  // Gate all /intelligence/* routes — manager/finance/admin.
  fastify.addHook("preHandler", devAuth);
  fastify.addHook("preHandler", requirePermission("intelligence.read"));

  // POST /intelligence/cycle
  // Trigger a full decision cycle: stock eval + event forecast + supplier audit
  fastify.post(
    "/cycle",
    async (
      request: FastifyRequest<{ Body: { tenantId?: string } }>,
      reply: FastifyReply
    ) => {
      const tenantId = request.body?.tenantId ?? DEFAULT_TENANT;
      try {
        const result = await decisionEngine.runCycle(tenantId);
        return reply.send({ success: true, data: result });
      } catch (err) {
        logger.error("Intelligence /cycle failed", { err });
        return reply.status(500).send({
          success: false,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }
  );

  // GET /intelligence/insights
  // Return structured actionable insights from pending decisions
  fastify.get(
    "/insights",
    async (
      request: FastifyRequest<{ Querystring: { tenantId?: string } }>,
      reply: FastifyReply
    ) => {
      const tenantId = request.query.tenantId ?? DEFAULT_TENANT;
      try {
        const insights = await insightsEngine.generateFullReport(tenantId);
        return reply.send({
          success: true,
          data: insights,
          meta: { count: insights.length },
        });
      } catch (err) {
        logger.error("Intelligence /insights failed", { err });
        return reply.status(500).send({
          success: false,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }
  );

  // GET /intelligence/forecast/:eventId
  // Forecast consumption for an existing event record
  fastify.get(
    "/forecast/:eventId",
    async (
      request: FastifyRequest<{
        Params: { eventId: string };
        Querystring: { tenantId?: string };
      }>,
      reply: FastifyReply
    ) => {
      const tenantId = request.query.tenantId ?? DEFAULT_TENANT;
      const { eventId } = request.params;
      try {
        const event = await prisma.event.findUnique({ where: { id: eventId } });
        if (!event)
          return reply.status(404).send({ success: false, error: "Event not found" });

        const forecast = await forecastEngine.forecastEvent(
          tenantId,
          event.eventType ?? "corporativo",
          event.guests ?? 100,
          6,
          eventId
        );
        return reply.send({ success: true, data: forecast });
      } catch (err) {
        logger.error("Intelligence GET /forecast failed", { err, eventId });
        return reply.status(500).send({
          success: false,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }
  );

  // POST /intelligence/forecast
  // Ad-hoc forecast without an existing event record
  fastify.post(
    "/forecast",
    async (
      request: FastifyRequest<{
        Body: {
          tenantId?: string;
          eventType: string;
          guestCount: number;
          durationHours?: number;
        };
      }>,
      reply: FastifyReply
    ) => {
      const schema = z.object({
        tenantId:      z.string().optional(),
        eventType:     z.string().min(1),
        guestCount:    z.number().int().min(1),
        durationHours: z.number().min(1).max(24).default(6),
      });
      try {
        const p = schema.parse(request.body);
        const tenantId = p.tenantId ?? DEFAULT_TENANT;
        const result = await forecastEngine.forecastEvent(
          tenantId,
          p.eventType,
          p.guestCount,
          p.durationHours
        );
        return reply.send({ success: true, data: result });
      } catch (err) {
        logger.error("Intelligence POST /forecast failed", { err });
        return reply.status(400).send({
          success: false,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }
  );

  // POST /intelligence/consumption/record
  // Feed actual post-event consumption into the forecast model
  fastify.post(
    "/consumption/record",
    async (
      request: FastifyRequest<{
        Body: {
          tenantId?: string;
          eventId: string;
          eventType: string;
          guestCount: number;
          items: Array<{
            itemCode: string;
            itemName: string;
            category: string;
            quantityConsumed: number;
            unit: string;
          }>;
        };
      }>,
      reply: FastifyReply
    ) => {
      const schema = z.object({
        tenantId:   z.string().optional(),
        eventId:    z.string(),
        eventType:  z.string(),
        guestCount: z.number().int().min(1),
        items: z
          .array(
            z.object({
              itemCode:         z.string(),
              itemName:         z.string(),
              category:         z.string(),
              quantityConsumed: z.number().min(0),
              unit:             z.string(),
            })
          )
          .min(1),
      });
      try {
        const p = schema.parse(request.body);
        const tenantId = p.tenantId ?? DEFAULT_TENANT;
        await forecastEngine.recordActualConsumption(
          tenantId,
          p.eventId,
          p.eventType,
          p.guestCount,
          p.items
        );
        return reply.send({
          success: true,
          message: `${p.items.length} consumption record(s) saved for future forecasts`,
        });
      } catch (err) {
        logger.error("Intelligence /consumption/record failed", { err });
        return reply.status(400).send({
          success: false,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }
  );

  // GET /intelligence/suppliers
  // Get supplier scores; filter by category if ?category=
  fastify.get(
    "/suppliers",
    async (
      request: FastifyRequest<{
        Querystring: { tenantId?: string; category?: string };
      }>,
      reply: FastifyReply
    ) => {
      const tenantId = request.query.tenantId ?? DEFAULT_TENANT;
      const { category } = request.query;
      try {
        const scores = category
          ? await supplierIntelligence.rankSuppliersForItem(tenantId, category)
          : await supplierIntelligence.getAllSupplierScores(tenantId);
        return reply.send({
          success: true,
          data: scores,
          meta: { count: scores.length },
        });
      } catch (err) {
        logger.error("Intelligence /suppliers failed", { err });
        return reply.status(500).send({
          success: false,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }
  );

  // GET /intelligence/decisions/pending
  // List pending operational decisions; filter by ?action=
  fastify.get(
    "/decisions/pending",
    async (
      request: FastifyRequest<{
        Querystring: { tenantId?: string; action?: string; limit?: string };
      }>,
      reply: FastifyReply
    ) => {
      const tenantId = request.query.tenantId ?? DEFAULT_TENANT;
      const limit = Math.min(parseInt(request.query.limit ?? "50"), 200);
      try {
        const decisions = await prisma.operationalDecision.findMany({
          where: {
            tenantId,
            status: "pending",
            ...(request.query.action && { action: request.query.action }),
            OR: [{ expiresAt: null }, { expiresAt: { gte: new Date() } }],
          },
          orderBy: { createdAt: "desc" },
          take: limit,
        });
        return reply.send({
          success: true,
          data: decisions,
          meta: { count: decisions.length },
        });
      } catch (err) {
        logger.error("Intelligence /decisions/pending failed", { err });
        return reply.status(500).send({
          success: false,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }
  );

  // POST /intelligence/decisions/:id/execute
  // Execute a pending decision (e.g., convert CREATE_PURCHASE_ORDER into a real PO)
  fastify.post(
    "/decisions/:id/execute",
    async (
      request: FastifyRequest<{
        Params: { id: string };
        Body: { executedBy?: string };
      }>,
      reply: FastifyReply
    ) => {
      const { id } = request.params;
      const executedBy = request.body?.executedBy ?? "api";
      try {
        const result = await decisionEngine.executeDecision(id, executedBy);
        return reply.status(result.success ? 200 : 400).send(result);
      } catch (err) {
        logger.error("Intelligence /decisions/:id/execute failed", { err, id });
        return reply.status(500).send({
          success: false,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }
  );

  // GET /intelligence/purchase-orders
  // List purchase orders (with supplier and items)
  fastify.get(
    "/purchase-orders",
    async (
      request: FastifyRequest<{
        Querystring: {
          tenantId?: string;
          status?: string;
          limit?: string;
        };
      }>,
      reply: FastifyReply
    ) => {
      const tenantId = request.query.tenantId ?? DEFAULT_TENANT;
      const limit = Math.min(parseInt(request.query.limit ?? "50"), 200);
      try {
        const orders = await prisma.purchaseOrder.findMany({
          where: {
            tenantId,
            ...(request.query.status && { status: request.query.status }),
          },
          include: { supplier: { select: { name: true, code: true } }, items: true },
          orderBy: { createdAt: "desc" },
          take: limit,
        });
        return reply.send({
          success: true,
          data: orders,
          meta: { count: orders.length },
        });
      } catch (err) {
        logger.error("Intelligence /purchase-orders failed", { err });
        return reply.status(500).send({
          success: false,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }
  );
}
