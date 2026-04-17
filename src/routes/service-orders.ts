import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { z } from "zod";
import { prisma } from "../db";
import { logger } from "../utils/logger";
import { config } from "../config/env";

const DEFAULT_TENANT = config.DEFAULT_TENANT_ID;

export async function serviceOrdersRoutes(fastify: FastifyInstance): Promise<void> {

  // GET /service-orders
  fastify.get("/", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z.object({
      tenantId: z.string().default(DEFAULT_TENANT),
      eventId: z.string().optional(),
      status: z.string().optional(),
      limit: z.coerce.number().max(100).default(50)
    }).parse(req.query);

    const orders = await prisma.serviceOrder.findMany({
      where: {
        tenantId: q.tenantId,
        ...(q.eventId ? { eventId: q.eventId } : {}),
        ...(q.status ? { status: q.status } : {})
      },
      orderBy: { createdAt: "desc" },
      take: q.limit,
      include: { items: true, _count: { select: { soToPoMappings: true } } }
    });

    return reply.send({ success: true, data: orders, meta: { count: orders.length } });
  });

  // POST /service-orders
  fastify.post("/", async (req: FastifyRequest<{ Body: unknown }>, reply: FastifyReply) => {
    const body = z.object({
      tenantId: z.string().default(DEFAULT_TENANT),
      eventId: z.string(),
      proposalId: z.string().optional(),
      soType: z.enum(["CATERING", "BAR", "STRUCTURE", "STAFF"]),
      requiredDelivery: z.string().optional(),
      items: z.array(z.object({
        itemCategory: z.enum(["MENU", "DRINK", "EQUIPMENT", "SERVICE"]),
        name: z.string(),
        description: z.string().optional(),
        quantity: z.number().positive(),
        unit: z.string().optional(),
        unitPrice: z.number().nonnegative(),
        producesItemId: z.string().optional()
      }))
    }).parse(req.body);

    const subtotal = body.items.reduce((s, i) => s + i.quantity * i.unitPrice, 0);
    const count = await prisma.serviceOrder.count({ where: { tenantId: body.tenantId } });
    const soNumber = `OS-${new Date().getFullYear()}-${String(count + 1).padStart(4, "0")}`;

    const so = await prisma.serviceOrder.create({
      data: {
        tenantId: body.tenantId,
        eventId: body.eventId,
        proposalId: body.proposalId,
        soType: body.soType,
        soNumber,
        subtotal,
        total: subtotal,
        requiredDelivery: body.requiredDelivery ? new Date(body.requiredDelivery) : undefined,
        items: {
          create: body.items.map(i => ({
            ...i,
            totalPrice: i.quantity * i.unitPrice
          }))
        }
      },
      include: { items: true }
    });

    logger.info("ServiceOrder created", { id: so.id, number: soNumber, type: so.soType });
    return reply.status(201).send({ success: true, data: so });
  });

  // GET /service-orders/:id
  fastify.get("/:id", async (req: FastifyRequest<{ Params: { id: string } }>, reply: FastifyReply) => {
    const so = await prisma.serviceOrder.findUnique({
      where: { id: req.params.id },
      include: {
        items: true,
        soToPoMappings: {
          include: { productionOrder: { select: { id: true, poNumber: true, status: true } } }
        }
      }
    });
    if (!so) return reply.status(404).send({ success: false, error: "Service order not found" });
    return reply.send({ success: true, data: so });
  });

  // POST /service-orders/:id/approve
  fastify.post("/:id/approve", async (req: FastifyRequest<{ Params: { id: string }; Body: unknown }>, reply: FastifyReply) => {
    const body = z.object({ approvedBy: z.string().optional() }).parse(req.body ?? {});

    const so = await prisma.serviceOrder.update({
      where: { id: req.params.id },
      data: { status: "APPROVED", approvedBy: body.approvedBy, approvedAt: new Date() }
    });
    return reply.send({ success: true, data: so });
  });

  // POST /service-orders/:id/submit
  fastify.post("/:id/submit", async (req: FastifyRequest<{ Params: { id: string } }>, reply: FastifyReply) => {
    const so = await prisma.serviceOrder.update({
      where: { id: req.params.id },
      data: { status: "PENDING_APPROVAL" }
    });
    return reply.send({ success: true, data: so });
  });

  // POST /service-orders/:id/cancel
  fastify.post("/:id/cancel", async (req: FastifyRequest<{ Params: { id: string } }>, reply: FastifyReply) => {
    const so = await prisma.serviceOrder.update({
      where: { id: req.params.id },
      data: { status: "CANCELLED" }
    });
    return reply.send({ success: true, data: so });
  });

  // GET /service-orders/:id/production-orders
  fastify.get("/:id/production-orders", async (req: FastifyRequest<{ Params: { id: string } }>, reply: FastifyReply) => {
    const mappings = await prisma.soToPoMapping.findMany({
      where: { serviceOrderId: req.params.id },
      include: {
        productionOrder: {
          include: { items: true }
        }
      }
    });
    return reply.send({ success: true, data: mappings.map(m => m.productionOrder) });
  });

  // POST /service-orders/from-contract/:contractId — gera OS automática a partir do contrato
  fastify.post("/from-contract/:contractId", async (req: FastifyRequest<{ Params: { contractId: string } }>, reply: FastifyReply) => {
    const contract = await prisma.contract.findUnique({
      where: { id: req.params.contractId },
      include: { proposal: { include: { items: true } } }
    });

    if (!contract) return reply.status(404).send({ success: false, error: "Contract not found" });
    if (!contract.eventId) return reply.status(400).send({ success: false, error: "Contract has no associated event" });

    // Agrupar itens da proposta por tipo
    const cateringItems = contract.proposal.items.filter(i => ["menu", "bar"].includes(i.itemType));
    const structureItems = contract.proposal.items.filter(i => ["structure", "equipment"].includes(i.itemType));
    const staffItems = contract.proposal.items.filter(i => i.itemType === "staff");

    const created = [];
    const count = await prisma.serviceOrder.count({ where: { tenantId: contract.tenantId } });
    let idx = count;

    const createSO = async (type: "CATERING" | "BAR" | "STRUCTURE" | "STAFF", items: typeof contract.proposal.items) => {
      if (items.length === 0) return null;
      idx++;
      const soNumber = `OS-${new Date().getFullYear()}-${String(idx).padStart(4, "0")}`;
      const subtotal = items.reduce((s, i) => s + i.totalPrice, 0);
      return prisma.serviceOrder.create({
        data: {
          tenantId: contract.tenantId,
          eventId: contract.eventId!,
          proposalId: contract.proposalId,
          soType: type,
          soNumber,
          subtotal,
          total: subtotal,
          items: {
            create: items.map(i => ({
              itemCategory: i.itemType.toUpperCase() as "MENU" | "DRINK" | "EQUIPMENT" | "SERVICE",
              name: i.name,
              description: i.description ?? undefined,
              quantity: i.quantity,
              unit: i.unit ?? undefined,
              unitPrice: i.unitPrice,
              totalPrice: i.totalPrice
            }))
          }
        },
        include: { items: true }
      });
    };

    const catering = await createSO("CATERING", cateringItems);
    const structure = await createSO("STRUCTURE", structureItems);
    const staff = await createSO("STAFF", staffItems);

    if (catering) created.push(catering);
    if (structure) created.push(structure);
    if (staff) created.push(staff);

    logger.info("Service orders created from contract", { contractId: contract.id, count: created.length });
    return reply.status(201).send({ success: true, data: created, meta: { count: created.length } });
  });
}
