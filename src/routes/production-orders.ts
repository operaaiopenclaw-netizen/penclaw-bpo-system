import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { z } from "zod";
import { prisma } from "../db";
import { logger } from "../utils/logger";
import { config } from "../config/env";

const DEFAULT_TENANT = config.DEFAULT_TENANT_ID;

export async function productionOrdersRoutes(fastify: FastifyInstance): Promise<void> {

  // GET /production-orders
  fastify.get("/", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z.object({
      tenantId: z.string().default(DEFAULT_TENANT),
      eventId: z.string().optional(),
      status: z.string().optional(),
      limit: z.coerce.number().max(100).default(50)
    }).parse(req.query);

    const orders = await prisma.productionOrder.findMany({
      where: {
        tenantId: q.tenantId,
        ...(q.eventId ? { eventId: q.eventId } : {}),
        ...(q.status ? { status: q.status } : {})
      },
      orderBy: { createdAt: "desc" },
      take: q.limit,
      include: {
        items: true,
        productionBatches: { select: { id: true, status: true, batchNumber: true } }
      }
    });

    return reply.send({ success: true, data: orders, meta: { count: orders.length } });
  });

  // POST /production-orders
  fastify.post("/", async (req: FastifyRequest<{ Body: unknown }>, reply: FastifyReply) => {
    const body = z.object({
      tenantId: z.string().default(DEFAULT_TENANT),
      eventId: z.string(),
      sourceSoIds: z.array(z.string()).default([]),
      productionDate: z.string().optional(),
      productionLocation: z.string().optional(),
      responsibleChefId: z.string().optional(),
      requiredReadyAt: z.string().optional(),
      items: z.array(z.object({
        itemName: z.string(),
        plannedQuantity: z.number().positive(),
        recipeId: z.string().optional(),
        estimatedCost: z.number().optional(),
        sourceSoItemId: z.string().optional()
      }))
    }).parse(req.body);

    const count = await prisma.productionOrder.count({ where: { tenantId: body.tenantId } });
    const poNumber = `OP-${new Date().getFullYear()}-${String(count + 1).padStart(4, "0")}`;

    const po = await prisma.productionOrder.create({
      data: {
        tenantId: body.tenantId,
        eventId: body.eventId,
        sourceSoIds: body.sourceSoIds,
        poNumber,
        productionDate: body.productionDate ? new Date(body.productionDate) : undefined,
        productionLocation: body.productionLocation,
        responsibleChefId: body.responsibleChefId,
        requiredReadyAt: body.requiredReadyAt ? new Date(body.requiredReadyAt) : undefined,
        items: { create: body.items }
      },
      include: { items: true }
    });

    // Criar mapeamentos SO → OP
    if (body.sourceSoIds.length > 0) {
      await prisma.soToPoMapping.createMany({
        data: body.sourceSoIds.map(soId => ({
          serviceOrderId: soId,
          productionOrderId: po.id
        }))
      });
      await prisma.serviceOrder.updateMany({
        where: { id: { in: body.sourceSoIds } },
        data: { status: "IN_PRODUCTION" }
      });
    }

    logger.info("ProductionOrder created", { id: po.id, number: poNumber, event: body.eventId });
    return reply.status(201).send({ success: true, data: po });
  });

  // GET /production-orders/:id
  fastify.get("/:id", async (req: FastifyRequest<{ Params: { id: string } }>, reply: FastifyReply) => {
    const po = await prisma.productionOrder.findUnique({
      where: { id: req.params.id },
      include: {
        items: true,
        productionBatches: true,
        soToPoMappings: {
          include: { serviceOrder: { select: { id: true, soNumber: true, soType: true } } }
        }
      }
    });
    if (!po) return reply.status(404).send({ success: false, error: "Production order not found" });
    return reply.send({ success: true, data: po });
  });

  // POST /production-orders/:id/schedule
  fastify.post("/:id/schedule", async (req: FastifyRequest<{ Params: { id: string }; Body: unknown }>, reply: FastifyReply) => {
    const body = z.object({
      productionDate: z.string(),
      productionLocation: z.string().optional(),
      responsibleChefId: z.string().optional(),
      requiredReadyAt: z.string().optional()
    }).parse(req.body);

    const po = await prisma.productionOrder.update({
      where: { id: req.params.id },
      data: {
        status: "SCHEDULED",
        productionDate: new Date(body.productionDate),
        productionLocation: body.productionLocation,
        responsibleChefId: body.responsibleChefId,
        requiredReadyAt: body.requiredReadyAt ? new Date(body.requiredReadyAt) : undefined
      }
    });
    return reply.send({ success: true, data: po });
  });

  // POST /production-orders/:id/start
  fastify.post("/:id/start", async (req: FastifyRequest<{ Params: { id: string } }>, reply: FastifyReply) => {
    const po = await prisma.productionOrder.update({
      where: { id: req.params.id },
      data: { status: "IN_PRODUCTION" }
    });
    return reply.send({ success: true, data: po });
  });

  // POST /production-orders/:id/complete
  fastify.post("/:id/complete", async (req: FastifyRequest<{ Params: { id: string }; Body: unknown }>, reply: FastifyReply) => {
    const body = z.object({ actualReadyAt: z.string().optional() }).parse(req.body ?? {});

    const po = await prisma.productionOrder.update({
      where: { id: req.params.id },
      data: {
        status: "READY",
        actualReadyAt: body.actualReadyAt ? new Date(body.actualReadyAt) : new Date()
      }
    });
    return reply.send({ success: true, data: po });
  });

  // POST /production-orders/:id/cancel
  fastify.post("/:id/cancel", async (req: FastifyRequest<{ Params: { id: string } }>, reply: FastifyReply) => {
    const po = await prisma.productionOrder.update({
      where: { id: req.params.id },
      data: { status: "CANCELLED" }
    });
    return reply.send({ success: true, data: po });
  });

  // POST /production-orders/:id/batches — criar lote de produção
  fastify.post("/:id/batches", async (req: FastifyRequest<{ Params: { id: string }; Body: unknown }>, reply: FastifyReply) => {
    const body = z.object({
      recipeId: z.string().optional(),
      batchNumber: z.string().optional(),
      plannedQuantity: z.number().positive(),
      preparedBy: z.string().optional()
    }).parse(req.body);

    const po = await prisma.productionOrder.findUnique({ where: { id: req.params.id } });
    if (!po) return reply.status(404).send({ success: false, error: "Production order not found" });

    const batch = await prisma.productionBatch.create({
      data: {
        tenantId: po.tenantId,
        productionOrderId: req.params.id,
        ...body
      }
    });
    return reply.status(201).send({ success: true, data: batch });
  });

  // PATCH /production-orders/batches/:batchId — atualizar lote
  fastify.patch("/batches/:batchId", async (req: FastifyRequest<{ Params: { batchId: string }; Body: unknown }>, reply: FastifyReply) => {
    const body = z.object({
      status: z.enum(["SCHEDULED", "IN_PROGRESS", "COMPLETED", "REJECTED", "WASTED"]).optional(),
      producedQuantity: z.number().optional(),
      wastedQuantity: z.number().optional(),
      qualityScore: z.number().min(0).max(10).optional(),
      qualityNotes: z.string().optional(),
      checkedBy: z.string().optional(),
      startedAt: z.string().optional(),
      completedAt: z.string().optional()
    }).parse(req.body);

    const batch = await prisma.productionBatch.update({
      where: { id: req.params.batchId },
      data: {
        ...body,
        startedAt: body.startedAt ? new Date(body.startedAt) : undefined,
        completedAt: body.completedAt ? new Date(body.completedAt) : undefined
      }
    });
    return reply.send({ success: true, data: batch });
  });

  // POST /production-orders/from-service-order/:soId — gera OP automática a partir de OS
  fastify.post("/from-service-order/:soId", async (req: FastifyRequest<{ Params: { soId: string }; Body: unknown }>, reply: FastifyReply) => {
    const body = z.object({
      productionDate: z.string().optional(),
      productionLocation: z.string().optional()
    }).parse(req.body ?? {});

    const so = await prisma.serviceOrder.findUnique({
      where: { id: req.params.soId },
      include: { items: true }
    });
    if (!so) return reply.status(404).send({ success: false, error: "Service order not found" });
    if (!["APPROVED", "IN_PRODUCTION"].includes(so.status)) {
      return reply.status(400).send({ success: false, error: "Service order must be APPROVED before creating production order" });
    }

    const count = await prisma.productionOrder.count({ where: { tenantId: so.tenantId } });
    const poNumber = `OP-${new Date().getFullYear()}-${String(count + 1).padStart(4, "0")}`;

    const po = await prisma.productionOrder.create({
      data: {
        tenantId: so.tenantId,
        eventId: so.eventId,
        sourceSoIds: [so.id],
        poNumber,
        productionDate: body.productionDate ? new Date(body.productionDate) : undefined,
        productionLocation: body.productionLocation,
        items: {
          create: so.items.map(i => ({
            itemName: i.name,
            plannedQuantity: i.quantity,
            sourceSoItemId: i.id,
            estimatedCost: i.totalPrice
          }))
        }
      },
      include: { items: true }
    });

    await prisma.soToPoMapping.create({
      data: { serviceOrderId: so.id, productionOrderId: po.id }
    });
    await prisma.serviceOrder.update({ where: { id: so.id }, data: { status: "IN_PRODUCTION" } });

    return reply.status(201).send({ success: true, data: po });
  });
}
