import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { z } from "zod";
import { prisma } from "../db";
import { logger } from "../utils/logger";
import { config } from "../config/env";

const DEFAULT_TENANT = config.DEFAULT_TENANT_ID;

export async function crmRoutes(fastify: FastifyInstance): Promise<void> {

  // ─── LEADS ───────────────────────────────────────────────────

  fastify.get("/leads", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z.object({
      tenantId: z.string().default(DEFAULT_TENANT),
      status: z.string().optional(),
      limit: z.coerce.number().max(100).default(50),
      offset: z.coerce.number().default(0)
    }).parse(req.query);

    const leads = await prisma.lead.findMany({
      where: { tenantId: q.tenantId, ...(q.status ? { status: q.status } : {}) },
      orderBy: { createdAt: "desc" },
      take: q.limit,
      skip: q.offset,
      include: { _count: { select: { proposals: true, activities: true } } }
    });

    return reply.send({ success: true, data: leads, meta: { count: leads.length } });
  });

  fastify.post("/leads", async (req: FastifyRequest<{ Body: unknown }>, reply: FastifyReply) => {
    const body = z.object({
      tenantId: z.string().default(DEFAULT_TENANT),
      companyName: z.string().optional(),
      contactName: z.string().min(1),
      email: z.string().email().optional(),
      phone: z.string().optional(),
      source: z.string().optional(),
      budget: z.number().optional(),
      need: z.string().optional(),
      timeline: z.string().optional(),
      assignedTo: z.string().optional()
    }).parse(req.body);

    const lead = await prisma.lead.create({
      data: {
        ...body,
        timeline: body.timeline ? new Date(body.timeline) : undefined
      }
    });

    logger.info("Lead created", { id: lead.id, contact: lead.contactName });
    return reply.status(201).send({ success: true, data: lead });
  });

  fastify.get("/leads/:id", async (req: FastifyRequest<{ Params: { id: string } }>, reply: FastifyReply) => {
    const lead = await prisma.lead.findUnique({
      where: { id: req.params.id },
      include: { activities: { orderBy: { createdAt: "desc" } }, proposals: true }
    });
    if (!lead) return reply.status(404).send({ success: false, error: "Lead not found" });
    return reply.send({ success: true, data: lead });
  });

  fastify.patch("/leads/:id/status", async (req: FastifyRequest<{ Params: { id: string }; Body: unknown }>, reply: FastifyReply) => {
    const body = z.object({ status: z.enum(["NEW", "CONTACTED", "QUALIFIED", "PROPOSAL_SENT", "WON", "LOST"]), reason: z.string().optional() }).parse(req.body);

    const timestamps: Record<string, Date> = {};
    if (body.status === "WON") timestamps.convertedAt = new Date();
    if (body.status === "LOST") timestamps.lostAt = new Date();
    if (body.status === "QUALIFIED") timestamps.qualifiedAt = new Date();
    if (body.status === "CONTACTED") timestamps.contactedAt = new Date();

    const lead = await prisma.lead.update({
      where: { id: req.params.id },
      data: { status: body.status, lostReason: body.reason, ...timestamps }
    });
    return reply.send({ success: true, data: lead });
  });

  fastify.post("/leads/:id/activities", async (req: FastifyRequest<{ Params: { id: string }; Body: unknown }>, reply: FastifyReply) => {
    const body = z.object({
      activityType: z.enum(["call", "email", "meeting", "note"]),
      description: z.string()
    }).parse(req.body);

    const activity = await prisma.leadActivity.create({
      data: { leadId: req.params.id, ...body }
    });
    return reply.status(201).send({ success: true, data: activity });
  });

  // ─── PROPOSALS ───────────────────────────────────────────────

  fastify.get("/proposals", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z.object({
      tenantId: z.string().default(DEFAULT_TENANT),
      status: z.string().optional(),
      leadId: z.string().optional(),
      limit: z.coerce.number().max(100).default(50)
    }).parse(req.query);

    const proposals = await prisma.proposal.findMany({
      where: { tenantId: q.tenantId, ...(q.status ? { status: q.status } : {}), ...(q.leadId ? { leadId: q.leadId } : {}) },
      orderBy: { createdAt: "desc" },
      take: q.limit,
      include: { items: true, lead: { select: { contactName: true, companyName: true } } }
    });
    return reply.send({ success: true, data: proposals });
  });

  fastify.post("/proposals", async (req: FastifyRequest<{ Body: unknown }>, reply: FastifyReply) => {
    const body = z.object({
      tenantId: z.string().default(DEFAULT_TENANT),
      leadId: z.string().optional(),
      validUntil: z.string(),
      currency: z.string().default("BRL"),
      items: z.array(z.object({
        itemType: z.string(),
        name: z.string(),
        description: z.string().optional(),
        quantity: z.number(),
        unit: z.string().optional(),
        unitPrice: z.number(),
        estimatedCost: z.number().optional()
      }))
    }).parse(req.body);

    const subtotal = body.items.reduce((s, i) => s + i.quantity * i.unitPrice, 0);
    const count = await prisma.proposal.count({ where: { tenantId: body.tenantId } });
    const proposalNumber = `PROP-${new Date().getFullYear()}-${String(count + 1).padStart(4, "0")}`;

    const proposal = await prisma.proposal.create({
      data: {
        tenantId: body.tenantId,
        leadId: body.leadId,
        proposalNumber,
        validUntil: new Date(body.validUntil),
        currency: body.currency,
        subtotal,
        totalAmount: subtotal,
        items: {
          create: body.items.map(i => ({
            ...i,
            totalPrice: i.quantity * i.unitPrice
          }))
        }
      },
      include: { items: true }
    });

    return reply.status(201).send({ success: true, data: proposal });
  });

  fastify.get("/proposals/:id", async (req: FastifyRequest<{ Params: { id: string } }>, reply: FastifyReply) => {
    const proposal = await prisma.proposal.findUnique({
      where: { id: req.params.id },
      include: { items: true, lead: true, contract: true }
    });
    if (!proposal) return reply.status(404).send({ success: false, error: "Proposal not found" });
    return reply.send({ success: true, data: proposal });
  });

  fastify.post("/proposals/:id/send", async (req: FastifyRequest<{ Params: { id: string } }>, reply: FastifyReply) => {
    const proposal = await prisma.proposal.update({
      where: { id: req.params.id },
      data: { status: "SENT", sentAt: new Date() }
    });
    return reply.send({ success: true, data: proposal });
  });

  fastify.post("/proposals/:id/approve", async (req: FastifyRequest<{ Params: { id: string }; Body: unknown }>, reply: FastifyReply) => {
    const body = z.object({ approvedBy: z.string().optional(), rejected: z.boolean().default(false), reason: z.string().optional() }).parse(req.body);

    const proposal = await prisma.proposal.update({
      where: { id: req.params.id },
      data: body.rejected
        ? { status: "REJECTED", rejectedReason: body.reason }
        : { status: "APPROVED", approvedBy: body.approvedBy, approvedAt: new Date() }
    });
    return reply.send({ success: true, data: proposal });
  });

  // ─── CONTRACTS ───────────────────────────────────────────────

  fastify.get("/contracts", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z.object({
      tenantId: z.string().default(DEFAULT_TENANT),
      status: z.string().optional(),
      limit: z.coerce.number().max(100).default(50)
    }).parse(req.query);

    const contracts = await prisma.contract.findMany({
      where: { tenantId: q.tenantId, ...(q.status ? { status: q.status } : {}) },
      orderBy: { createdAt: "desc" },
      take: q.limit,
      include: {
        proposal: { include: { items: true } },
        lead: { select: { contactName: true, companyName: true } }
      }
    });
    return reply.send({ success: true, data: contracts });
  });

  fastify.post("/contracts", async (req: FastifyRequest<{ Body: unknown }>, reply: FastifyReply) => {
    const body = z.object({
      tenantId: z.string().default(DEFAULT_TENANT),
      proposalId: z.string(),
      leadId: z.string(),
      signedAt: z.string(),
      signedByClient: z.string().optional(),
      signedByCompany: z.string().optional(),
      paymentTerms: z.string().optional(),
      cancellationPolicy: z.string().optional(),
      contractDocumentUrl: z.string().optional(),
      // Atribuição comercial (opcional aqui; obrigatório para ativar
      // CommissionPlan depois via POST /commercial/contracts/:id/commission-plan)
      salespersonId: z.string().uuid().optional(),
      salesManagerId: z.string().uuid().optional(),
      sdrId: z.string().uuid().optional(),
      // Margem projetada no momento da assinatura — se ausente, tenta
      // estimar via soma de ProposalItem.estimatedCost.
      projectedMargin: z.number().optional()
    }).parse(req.body);

    const proposal = await prisma.proposal.findUnique({
      where: { id: body.proposalId },
      include: { items: true }
    });
    if (!proposal) return reply.status(404).send({ success: false, error: "Proposal not found" });

    // Fallback para projectedMargin: receita − soma de estimatedCost.
    let projectedMargin = body.projectedMargin;
    if (projectedMargin === undefined) {
      const estimatedCost = proposal.items.reduce(
        (sum, it) => sum + (it.estimatedCost ?? 0) * it.quantity,
        0
      );
      if (estimatedCost > 0) {
        projectedMargin = proposal.totalAmount - estimatedCost;
      }
    }

    const count = await prisma.contract.count({ where: { tenantId: body.tenantId } });
    const contractNumber = `CTR-${new Date().getFullYear()}-${String(count + 1).padStart(4, "0")}`;

    const contract = await prisma.contract.create({
      data: {
        ...body,
        contractNumber,
        totalValue: proposal.totalAmount,
        projectedMargin,
        signedAt: new Date(body.signedAt)
      }
    });

    await prisma.proposal.update({ where: { id: body.proposalId }, data: { status: "CONVERTED" } });
    await prisma.lead.update({ where: { id: body.leadId }, data: { status: "WON", convertedAt: new Date() } });

    logger.info("Contract created", {
      id: contract.id,
      number: contractNumber,
      value: contract.totalValue,
      margin: projectedMargin
    });
    return reply.status(201).send({ success: true, data: contract });
  });

  fastify.get("/contracts/:id", async (req: FastifyRequest<{ Params: { id: string } }>, reply: FastifyReply) => {
    const contract = await prisma.contract.findUnique({
      where: { id: req.params.id },
      include: { proposal: { include: { items: true } }, lead: true }
    });
    if (!contract) return reply.status(404).send({ success: false, error: "Contract not found" });
    return reply.send({ success: true, data: contract });
  });

  fastify.patch("/contracts/:id/event", async (req: FastifyRequest<{ Params: { id: string }; Body: unknown }>, reply: FastifyReply) => {
    const body = z.object({ eventId: z.string() }).parse(req.body);
    const contract = await prisma.contract.update({ where: { id: req.params.id }, data: { eventId: body.eventId } });
    return reply.send({ success: true, data: contract });
  });

  // ─── CRM PIPELINE STATS ───────────────────────────────────────

  fastify.get("/pipeline", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z.object({ tenantId: z.string().default(DEFAULT_TENANT) }).parse(req.query);

    const [leads, proposals, contracts] = await Promise.all([
      prisma.lead.groupBy({ by: ["status"], where: { tenantId: q.tenantId }, _count: true }),
      prisma.proposal.groupBy({ by: ["status"], where: { tenantId: q.tenantId }, _count: true, _sum: { totalAmount: true } }),
      prisma.contract.aggregate({ where: { tenantId: q.tenantId, status: "ACTIVE" }, _count: true, _sum: { totalValue: true } })
    ]);

    return reply.send({
      success: true,
      data: {
        leads: leads.reduce((acc, l) => ({ ...acc, [l.status]: l._count }), {}),
        proposals: proposals.reduce((acc, p) => ({
          ...acc,
          [p.status]: { count: p._count, totalAmount: p._sum.totalAmount }
        }), {}),
        contracts: {
          active: contracts._count,
          totalValue: contracts._sum.totalValue
        }
      }
    });
  });
}
