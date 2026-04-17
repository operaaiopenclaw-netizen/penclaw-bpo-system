import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { z } from "zod";
import { prisma } from "../db";
import { logger } from "../utils/logger";
import { config } from "../config/env";

const DEFAULT_TENANT = config.DEFAULT_TENANT_ID;

export async function executionRoutes(fastify: FastifyInstance): Promise<void> {

  // POST /execution/sessions — iniciar sessão de execução
  fastify.post("/sessions", async (req: FastifyRequest<{ Body: unknown }>, reply: FastifyReply) => {
    const body = z.object({
      tenantId: z.string().default(DEFAULT_TENANT),
      eventId: z.string(),
      openedBy: z.string().optional()
    }).parse(req.body);

    const existing = await prisma.executionSession.findFirst({
      where: { eventId: body.eventId, status: "ACTIVE" }
    });
    if (existing) {
      return reply.status(409).send({ success: false, error: "Active session already exists for this event", data: existing });
    }

    const session = await prisma.executionSession.create({
      data: {
        tenantId: body.tenantId,
        eventId: body.eventId,
        openedBy: body.openedBy,
        checkpoints: {
          create: [
            { stage: "SETUP", status: "PENDING" },
            { stage: "SERVICE_START", status: "PENDING" },
            { stage: "SERVICE_END", status: "PENDING" },
            { stage: "TEARDOWN", status: "PENDING" }
          ]
        }
      },
      include: { checkpoints: true }
    });

    logger.info("ExecutionSession started", { id: session.id, eventId: body.eventId });
    return reply.status(201).send({ success: true, data: session });
  });

  // GET /execution/sessions/:id
  fastify.get("/sessions/:id", async (req: FastifyRequest<{ Params: { id: string } }>, reply: FastifyReply) => {
    const session = await prisma.executionSession.findUnique({
      where: { id: req.params.id },
      include: {
        checkpoints: { orderBy: { createdAt: "asc" } },
        occurrences: { orderBy: { reportedAt: "desc" } }
      }
    });
    if (!session) return reply.status(404).send({ success: false, error: "Session not found" });
    return reply.send({ success: true, data: session });
  });

  // GET /execution/sessions — listar sessões
  fastify.get("/sessions", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z.object({
      tenantId: z.string().default(DEFAULT_TENANT),
      eventId: z.string().optional(),
      status: z.string().optional(),
      limit: z.coerce.number().max(100).default(20)
    }).parse(req.query);

    const sessions = await prisma.executionSession.findMany({
      where: {
        tenantId: q.tenantId,
        ...(q.eventId ? { eventId: q.eventId } : {}),
        ...(q.status ? { status: q.status } : {})
      },
      orderBy: { openedAt: "desc" },
      take: q.limit,
      include: {
        _count: { select: { checkpoints: true, occurrences: true } }
      }
    });
    return reply.send({ success: true, data: sessions });
  });

  // PATCH /execution/sessions/:id/checkpoints/:checkpointId
  fastify.patch("/sessions/:id/checkpoints/:checkpointId", async (
    req: FastifyRequest<{ Params: { id: string; checkpointId: string }; Body: unknown }>,
    reply: FastifyReply
  ) => {
    const body = z.object({
      status: z.enum(["OK", "ISSUE", "BLOCKED"]),
      notes: z.string().optional(),
      checkedBy: z.string().optional()
    }).parse(req.body);

    const checkpoint = await prisma.executionCheckpoint.update({
      where: { id: req.params.checkpointId },
      data: { ...body, checkedAt: new Date() }
    });

    return reply.send({ success: true, data: checkpoint });
  });

  // POST /execution/sessions/:id/occurrences
  fastify.post("/sessions/:id/occurrences", async (req: FastifyRequest<{ Params: { id: string }; Body: unknown }>, reply: FastifyReply) => {
    const body = z.object({
      severity: z.enum(["INFO", "WARNING", "CRITICAL"]).default("INFO"),
      category: z.enum(["FOOD", "STAFF", "EQUIPMENT", "CLIENT", "SAFETY"]).optional(),
      description: z.string().min(1),
      reportedBy: z.string().optional()
    }).parse(req.body);

    const occurrence = await prisma.executionOccurrence.create({
      data: { sessionId: req.params.id, ...body }
    });

    if (body.severity === "CRITICAL") {
      logger.warn("Critical occurrence reported", { sessionId: req.params.id, description: body.description });
    }

    return reply.status(201).send({ success: true, data: occurrence });
  });

  // PATCH /execution/sessions/:id/occurrences/:occurrenceId/resolve
  fastify.patch("/sessions/:id/occurrences/:occurrenceId/resolve", async (
    req: FastifyRequest<{ Params: { id: string; occurrenceId: string }; Body: unknown }>,
    reply: FastifyReply
  ) => {
    const body = z.object({
      resolution: z.string().min(1),
      resolvedBy: z.string().optional()
    }).parse(req.body);

    const occurrence = await prisma.executionOccurrence.update({
      where: { id: req.params.occurrenceId },
      data: { ...body, resolvedAt: new Date() }
    });
    return reply.send({ success: true, data: occurrence });
  });

  // POST /execution/sessions/:id/complete
  fastify.post("/sessions/:id/complete", async (req: FastifyRequest<{ Params: { id: string }; Body: unknown }>, reply: FastifyReply) => {
    const body = z.object({
      closedBy: z.string().optional(),
      overallRating: z.number().min(1).max(5).optional(),
      clientSignOff: z.boolean().default(false),
      notes: z.string().optional()
    }).parse(req.body ?? {});

    const unresolvedCritical = await prisma.executionOccurrence.count({
      where: { sessionId: req.params.id, severity: "CRITICAL", resolvedAt: null }
    });

    if (unresolvedCritical > 0) {
      return reply.status(400).send({
        success: false,
        error: `Cannot complete session with ${unresolvedCritical} unresolved critical occurrence(s)`
      });
    }

    const session = await prisma.executionSession.update({
      where: { id: req.params.id },
      data: { status: "COMPLETED", closedAt: new Date(), ...body },
      include: {
        checkpoints: true,
        occurrences: true
      }
    });

    logger.info("ExecutionSession completed", { id: session.id, eventId: session.eventId, rating: body.overallRating });
    return reply.send({ success: true, data: session });
  });

  // GET /execution/sessions/:id/summary — resumo executivo
  fastify.get("/sessions/:id/summary", async (req: FastifyRequest<{ Params: { id: string } }>, reply: FastifyReply) => {
    const session = await prisma.executionSession.findUnique({
      where: { id: req.params.id },
      include: { checkpoints: true, occurrences: true }
    });
    if (!session) return reply.status(404).send({ success: false, error: "Session not found" });

    const checkpointSummary = {
      total: session.checkpoints.length,
      ok: session.checkpoints.filter(c => c.status === "OK").length,
      issues: session.checkpoints.filter(c => c.status === "ISSUE").length,
      blocked: session.checkpoints.filter(c => c.status === "BLOCKED").length,
      pending: session.checkpoints.filter(c => c.status === "PENDING").length
    };

    const occurrenceSummary = {
      total: session.occurrences.length,
      critical: session.occurrences.filter(o => o.severity === "CRITICAL").length,
      warnings: session.occurrences.filter(o => o.severity === "WARNING").length,
      info: session.occurrences.filter(o => o.severity === "INFO").length,
      resolved: session.occurrences.filter(o => o.resolvedAt !== null).length
    };

    const durationMinutes = session.closedAt
      ? Math.round((session.closedAt.getTime() - session.openedAt.getTime()) / 60000)
      : Math.round((Date.now() - session.openedAt.getTime()) / 60000);

    return reply.send({
      success: true,
      data: {
        session: { id: session.id, eventId: session.eventId, status: session.status, rating: session.overallRating },
        duration: { minutes: durationMinutes, openedAt: session.openedAt, closedAt: session.closedAt },
        checkpoints: checkpointSummary,
        occurrences: occurrenceSummary,
        clientSignOff: session.clientSignOff,
        notes: session.notes
      }
    });
  });
}
