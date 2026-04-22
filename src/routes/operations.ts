// ============================================================
// OPERATIONS ROUTES — /operations/*
// Input webhooks + dashboard feed + alert surface (Sprint 6)
// ============================================================
import type { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { z } from "zod";
import { prisma } from "../db";
import { config } from "../config/env";
import { logger } from "../utils/logger";
import { alertEngine, type OperationalContext } from "../core/alert-engine";
import { notificationDispatcher } from "../channels";
import {
  forecastEngine,
  productionEngine,
  reconciliationEngine,
} from "../intelligence";
import { devAuth, requirePermission } from "../middleware/auth";
import { enforceTenant } from "../middleware/tenant";
import { webhookAuth } from "../middleware/hmac";

const DEFAULT_TENANT = config.DEFAULT_TENANT_ID;

type SeverityRank = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

async function computeOperationalContext(
  tenantId: string,
  eventId: string
): Promise<OperationalContext> {
  const event = await prisma.event.findUnique({ where: { id: eventId } });
  if (!event) return { tenantId, eventId };

  // Stock coverage: compare forecast vs current inventory
  const forecast = await forecastEngine.forecastEvent(
    tenantId,
    event.eventType ?? "corporativo",
    event.guests ?? 100,
    6,
    eventId
  );

  const inventory = await prisma.inventoryItem.findMany();
  const byCode = new Map(inventory.map((i) => [i.code, i]));

  const stock = forecast.forecasts.map((it) => {
    const inv = byCode.get(it.itemCode);
    return {
      itemCode: it.itemCode,
      itemName: it.itemName,
      onHand: inv?.currentQty ?? 0,
      required: it.estimatedConsumption,
      safetyStock: inv?.minStockLevel ?? undefined,
    };
  });

  // Station capacity — aggregate schedules per station for the event date
  const stations = await prisma.productionStation.findMany({
    where: { tenantId, isActive: true },
  });

  const dayStart = new Date(event.eventDate ?? new Date());
  dayStart.setHours(0, 0, 0, 0);
  const dayEnd = new Date(dayStart);
  dayEnd.setDate(dayEnd.getDate() + 1);

  const schedules = await prisma.productionSchedule.findMany({
    where: {
      tenantId,
      scheduledStart: { gte: dayStart, lt: dayEnd },
    },
  });

  const loadByStation = new Map<string, number>();
  for (const s of schedules) {
    loadByStation.set(
      s.stationId,
      (loadByStation.get(s.stationId) ?? 0) + (s.estimatedHours ?? 0)
    );
  }

  const stationLoad = stations.map((st) => ({
    stationId: st.id,
    stationName: st.name,
    loadHours: loadByStation.get(st.id) ?? 0,
    capacityHours: st.maxHoursPerDay,
  }));

  // Margin — from reconciliation report if exists, otherwise event projected
  const recon = await prisma.reconciliationReport.findUnique({
    where: { eventId },
  });

  const margin = recon
    ? {
        projectedPct: recon.projectedMargin,
        realPct: recon.realMargin,
        deltaPct:
          recon.realMargin !== null && recon.projectedMargin !== null
            ? recon.realMargin - recon.projectedMargin
            : null,
      }
    : {
        projectedPct: event.marginPct ?? null,
        realPct: null,
        deltaPct: null,
      };

  // Reconciliation high-variance items
  const accuracy = await prisma.forecastAccuracy.findMany({
    where: { tenantId, eventId, scope: "item" },
    orderBy: { recordedAt: "desc" },
    take: 100,
  });

  const highVariances = accuracy
    .filter((a) => Math.abs(a.variancePct) > 0.25)
    .map((a) => ({ itemCode: a.scopeKey, variancePct: a.variancePct }));

  const overallAccuracyScore = recon ? recon.meanAccuracy / 100 : undefined;

  return {
    tenantId,
    eventId,
    stock,
    stations: stationLoad,
    margin,
    reconciliation: { overallAccuracyScore, highVariances },
  };
}

export async function operationsRoutes(fastify: FastifyInstance): Promise<void> {
  // Base auth for every /operations/* request — webhooks swap this hook
  // per-route via `config:{preHandler:[webhookAuth(...)]}` before the global
  // hook runs. `enforceTenant` is a no-op for webhooks since webhookAuth
  // already binds the user to the tenant named in the payload.
  fastify.addHook("preHandler", async (request, reply) => {
    if (request.user) return; // already populated by a route-level preHandler
    await devAuth(request, reply);
  });
  fastify.addHook("preHandler", enforceTenant);

  // ===========================================================
  // INPUT WEBHOOKS — HMAC-signed, no JWT required
  // ===========================================================

  // POST /operations/webhooks/event — manager role synthesized via HMAC
  fastify.post(
    "/webhooks/event",
    {
      preHandler: [
        webhookAuth("manager"),
        requirePermission("operations.event.write"),
      ],
    },
    async (request: FastifyRequest, reply: FastifyReply) => {
      const schema = z.object({
        tenantId: z.string().optional(),
        source: z.string().default("webhook"),
        eventId: z.string().optional(),
        name: z.string(),
        eventType: z.string().default("corporativo"),
        eventDate: z.string().optional(),
        guests: z.number().int().min(1),
        revenueTotal: z.number().optional(),
        marginPct: z.number().optional(),
        companyName: z.string().optional(),
        costCenterId: z.string().optional(),
      });
      try {
        const p = schema.parse(request.body);
        const tenantId = p.tenantId ?? DEFAULT_TENANT;

        const data = {
          tenantId,
          costCenterId: p.costCenterId ?? "default",
          name: p.name,
          companyName: p.companyName,
          eventType: p.eventType,
          eventDate: p.eventDate ? new Date(p.eventDate) : null,
          guests: p.guests,
          revenueTotal: p.revenueTotal ?? null,
          marginPct: p.marginPct ?? null,
          status: "planned",
        };

        const event = p.eventId
          ? await prisma.event.upsert({
              where: { id: p.eventId },
              create: { id: p.eventId, ...data },
              update: data,
            })
          : await prisma.event.create({ data });

        logger.info("operations.event received", {
          eventId: event.id,
          source: p.source,
        });

        return reply.send({ success: true, data: event });
      } catch (err) {
        logger.error("/operations/webhooks/event failed", { err });
        return reply.status(400).send({
          success: false,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }
  );

  // POST /operations/webhooks/consumption — kitchen role synthesized via HMAC
  fastify.post(
    "/webhooks/consumption",
    {
      preHandler: [
        webhookAuth("kitchen"),
        requirePermission("operations.consumption.write"),
      ],
    },
    async (request: FastifyRequest, reply: FastifyReply) => {
      const schema = z.object({
        tenantId: z.string().optional(),
        eventId: z.string(),
        items: z
          .array(
            z.object({
              itemCode: z.string(),
              itemName: z.string(),
              category: z.string(),
              unit: z.string(),
              quantityConsumed: z.number().min(0),
              quantityWasted: z.number().min(0).default(0),
              quantityReturned: z.number().min(0).default(0),
              purchaseOrderItemId: z.string().optional(),
            })
          )
          .min(1),
      });
      try {
        const p = schema.parse(request.body);
        const tenantId = p.tenantId ?? DEFAULT_TENANT;

        const created = await prisma.$transaction(
          p.items.map((item) =>
            prisma.eventConsumption.create({
              data: {
                tenantId,
                eventId: p.eventId,
                itemCode: item.itemCode,
                itemName: item.itemName,
                category: item.category,
                unit: item.unit,
                quantityConsumed: item.quantityConsumed,
                quantityWasted: item.quantityWasted,
                quantityReturned: item.quantityReturned,
                purchaseOrderItemId: item.purchaseOrderItemId,
              },
            })
          )
        );

        return reply.send({
          success: true,
          data: { recorded: created.length },
        });
      } catch (err) {
        logger.error("/operations/webhooks/consumption failed", { err });
        return reply.status(400).send({
          success: false,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }
  );

  // POST /operations/webhooks/production — kitchen role synthesized via HMAC
  fastify.post(
    "/webhooks/production",
    {
      preHandler: [
        webhookAuth("kitchen"),
        requirePermission("operations.production.write"),
      ],
    },
    async (request: FastifyRequest, reply: FastifyReply) => {
      const schema = z.object({
        tenantId: z.string().optional(),
        productionOrderId: z.string(),
        actualItems: z
          .array(
            z.object({
              itemName: z.string(),
              producedQuantity: z.number().min(0),
              wastedQuantity: z.number().min(0).default(0),
            })
          )
          .optional(),
      });
      try {
        const p = schema.parse(request.body);
        const tenantId = p.tenantId ?? DEFAULT_TENANT;
        const result = await productionEngine.completeProductionOrder(
          tenantId,
          p.productionOrderId,
          p.actualItems ?? []
        );
        return reply.send({ success: true, data: result });
      } catch (err) {
        logger.error("/operations/webhooks/production failed", { err });
        return reply.status(400).send({
          success: false,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }
  );

  // POST /operations/webhooks/telegram
  // Minimal Telegram bot webhook — accepts text commands.
  // In prod, rejects any chat_id not listed in TELEGRAM_ALLOWED_CHATS.
  fastify.post(
    "/webhooks/telegram",
    {
      preHandler: async (request, reply) => {
        // Bypass generic devAuth for this route — synthesize a manager user
        // bound to the default tenant. No JWT, no HMAC (Telegram controls
        // delivery; access is gated purely by chat_id whitelist).
        request.user = {
          id: "system-telegram",
          email: "system@orkestra",
          name: "Telegram Bot",
          role: "manager",
          tenantId: config.DEFAULT_TENANT_ID,
        };

        const body = (request.body ?? {}) as Record<string, any>;
        const chatId = (body.message ?? body.edited_message)?.chat?.id?.toString();
        const allow = config.telegramAllowedChats;
        const strict = config.isProd || allow.length > 0;
        if (strict && (!chatId || !allow.includes(chatId))) {
          logger.warn("telegram.webhook rejected", { chatId });
          return reply.status(403).send({ ok: false, error: "chat_id not whitelisted" });
        }
      },
    },
    async (request: FastifyRequest, reply: FastifyReply) => {
      const body = (request.body ?? {}) as Record<string, any>;
      const message = body.message ?? body.edited_message;
      const text: string = message?.text ?? "";
      const chatId = message?.chat?.id?.toString();

      logger.info("telegram.webhook received", { chatId, text });

      const [command, ...args] = text.trim().split(/\s+/);
      let responseBody = "";

      switch (command) {
        case "/status": {
          const runs = await prisma.agentRun.count({
            where: { status: "completed" },
          });
          const pending = await prisma.operationalDecision.count({
            where: { status: "pending" },
          });
          responseBody = `🟢 Orkestra online. runs=${runs} pending_decisions=${pending}`;
          break;
        }
        case "/evento": {
          const eventId = args[0];
          if (!eventId) {
            responseBody = "Uso: /evento <eventId>";
            break;
          }
          const ev = await prisma.event.findUnique({ where: { id: eventId } });
          if (!ev) {
            responseBody = `❌ Evento ${eventId} não encontrado`;
            break;
          }
          responseBody =
            `📅 ${ev.name}\n` +
            `Convidados: ${ev.guests ?? "?"}\n` +
            `Receita: R$${ev.revenueTotal ?? 0}\n` +
            `Margem projetada: ${ev.marginPct ?? "?"}%`;
          break;
        }
        case "/help":
        default:
          responseBody = [
            "Orkestra bot — comandos:",
            "/status — ping sistema",
            "/evento <id> — resumo do evento",
            "/help — esta mensagem",
          ].join("\n");
      }

      return reply.send({
        method: "sendMessage",
        chat_id: chatId,
        text: responseBody,
      });
    }
  );

  // ===========================================================
  // DASHBOARD FEEDS
  // ===========================================================

  // GET /operations/overview
  // Aggregate view for the ops dashboard
  fastify.get(
    "/overview",
    async (
      request: FastifyRequest<{ Querystring: { tenantId?: string } }>,
      reply: FastifyReply
    ) => {
      const tenantId = request.query.tenantId ?? DEFAULT_TENANT;
      try {
        const now = new Date();
        const in14Days = new Date(now.getTime() + 14 * 86400_000);

        const [upcomingEvents, openPOs, pendingApprovals, recentRecons] =
          await Promise.all([
            prisma.event.findMany({
              where: {
                tenantId,
                eventDate: { gte: now, lte: in14Days },
              },
              orderBy: { eventDate: "asc" },
              take: 20,
            }),
            prisma.purchaseOrder.count({
              where: {
                tenantId,
                status: { in: ["pending_approval", "draft", "confirmed"] },
              },
            }),
            prisma.approvalRequest.count({
              where: { status: "pending" },
            }),
            prisma.reconciliationReport.findMany({
              where: { tenantId },
              orderBy: { createdAt: "desc" },
              take: 5,
            }),
          ]);

        return reply.send({
          success: true,
          data: {
            upcomingEvents: upcomingEvents.map((e) => ({
              id: e.id,
              name: e.name,
              eventDate: e.eventDate,
              guests: e.guests,
              status: e.status,
              revenueTotal: e.revenueTotal,
              marginPct: e.marginPct,
            })),
            counters: {
              upcomingEvents: upcomingEvents.length,
              openPurchaseOrders: openPOs,
              pendingApprovals,
            },
            recentReconciliations: recentRecons.map((r) => ({
              eventId: r.eventId,
              meanAccuracy: r.meanAccuracy,
              projectedMargin: r.projectedMargin,
              realMargin: r.realMargin,
              createdAt: r.createdAt,
            })),
          },
        });
      } catch (err) {
        logger.error("/operations/overview failed", { err });
        return reply.status(500).send({
          success: false,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }
  );

  // GET /operations/risks?eventId=...
  // Risk radar — evaluates operational context and returns alerts (no dispatch)
  fastify.get(
    "/risks",
    async (
      request: FastifyRequest<{
        Querystring: { tenantId?: string; eventId?: string };
      }>,
      reply: FastifyReply
    ) => {
      const tenantId = request.query.tenantId ?? DEFAULT_TENANT;
      const { eventId } = request.query;
      try {
        if (!eventId) {
          return reply.status(400).send({
            success: false,
            error: "eventId query param is required",
          });
        }
        const ctx = await computeOperationalContext(tenantId, eventId);
        const alerts = alertEngine.evaluateOperational(ctx);
        const counts = alerts.reduce<Record<string, number>>((acc, a) => {
          acc[a.severity] = (acc[a.severity] ?? 0) + 1;
          return acc;
        }, {});
        return reply.send({
          success: true,
          data: { alerts, context: ctx, counts },
        });
      } catch (err) {
        logger.error("/operations/risks failed", { err });
        return reply.status(500).send({
          success: false,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }
  );

  // POST /operations/alerts/evaluate — manager/finance/admin
  fastify.post(
    "/alerts/evaluate",
    { preHandler: requirePermission("operations.alerts.evaluate") },
    async (request: FastifyRequest, reply: FastifyReply) => {
      const schema = z.object({
        tenantId: z.string().optional(),
        eventId: z.string(),
        dispatch: z.boolean().default(true),
      });
      try {
        const p = schema.parse(request.body);
        const tenantId = p.tenantId ?? DEFAULT_TENANT;
        const ctx = await computeOperationalContext(tenantId, p.eventId);
        const alerts = alertEngine.evaluateOperational(ctx);
        const delivery = p.dispatch
          ? await alertEngine.dispatchAlerts(alerts, {
              tenantId,
              eventId: p.eventId,
            })
          : [];
        return reply.send({
          success: true,
          data: {
            alerts,
            dispatched: delivery,
          },
        });
      } catch (err) {
        logger.error("/operations/alerts/evaluate failed", { err });
        return reply.status(400).send({
          success: false,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }
  );

  // GET /operations/channels
  // Which notification channels are configured right now
  fastify.get("/channels", async (_request, reply: FastifyReply) => {
    return reply.send({
      success: true,
      data: notificationDispatcher.listChannels(),
    });
  });

  // GET /operations/lifecycle/:eventId
  // End-to-end lifecycle trace for an event (forecast → PO → production → consumption → reconciliation)
  fastify.get(
    "/lifecycle/:eventId",
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
        const [event, purchaseOrders, prodOrders, consumption, recon] =
          await Promise.all([
            prisma.event.findUnique({ where: { id: eventId } }),
            prisma.purchaseOrder.findMany({
              where: { tenantId, relatedEventId: eventId },
              select: {
                id: true,
                status: true,
                totalEstimatedCost: true,
                totalActualCost: true,
                supplierId: true,
                createdAt: true,
              },
            }),
            prisma.productionOrder.findMany({
              where: { tenantId, eventId },
              include: { schedules: true, items: true },
            }),
            prisma.eventConsumption.findMany({
              where: { tenantId, eventId },
            }),
            prisma.reconciliationReport.findUnique({ where: { eventId } }),
          ]);

        if (!event) {
          return reply
            .status(404)
            .send({ success: false, error: "Event not found" });
        }

        return reply.send({
          success: true,
          data: {
            event,
            purchaseOrders,
            productionOrders: prodOrders,
            consumption,
            reconciliation: recon,
          },
        });
      } catch (err) {
        logger.error("/operations/lifecycle failed", { err });
        return reply.status(500).send({
          success: false,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }
  );

  // POST /operations/reconcile — manager/finance/admin
  fastify.post(
    "/reconcile",
    { preHandler: requirePermission("operations.reconcile.execute") },
    async (request: FastifyRequest, reply: FastifyReply) => {
      const schema = z.object({
        tenantId: z.string().optional(),
        eventId: z.string(),
      });
      try {
        const p = schema.parse(request.body);
        const tenantId = p.tenantId ?? DEFAULT_TENANT;
        const report = await reconciliationEngine.reconcileEvent(
          tenantId,
          p.eventId
        );
        return reply.send({ success: true, data: report });
      } catch (err) {
        logger.error("/operations/reconcile failed", { err });
        return reply.status(400).send({
          success: false,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }
  );

  // GET /operations/alerts/recent
  // Recent alerts across events (memory-backed)
  fastify.get(
    "/alerts/recent",
    async (
      request: FastifyRequest<{
        Querystring: { tenantId?: string; limit?: string; severity?: SeverityRank };
      }>,
      reply: FastifyReply
    ) => {
      const limit = Math.min(parseInt(request.query.limit ?? "20"), 100);
      try {
        const memories = await prisma.memoryItem.findMany({
          where: { memoryType: "insight" },
          orderBy: { createdAt: "desc" },
          take: limit,
        });
        return reply.send({
          success: true,
          data: memories,
          meta: { count: memories.length },
        });
      } catch (err) {
        logger.error("/operations/alerts/recent failed", { err });
        return reply.status(500).send({
          success: false,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }
  );
}
