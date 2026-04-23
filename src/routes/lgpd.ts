// ============================================================
// LGPD — data export + right-to-erasure + consent log
// ============================================================

import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { z } from "zod";
import { prisma } from "../db";
import { config } from "../config/env";
import { logger } from "../utils/logger";

const DEFAULT_TENANT = config.DEFAULT_TENANT_ID;

export async function lgpdRoutes(fastify: FastifyInstance): Promise<void> {
  // Return all personal data associated with an email.
  fastify.get("/export", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z
      .object({ email: z.string().email(), tenantId: z.string().default(DEFAULT_TENANT) })
      .parse(req.query);

    const payload: Record<string, unknown> = { requestedAt: new Date().toISOString(), email: q.email };
    try {
      payload.users = await prisma.user.findMany({
        where: { email: q.email, tenantId: q.tenantId },
        select: { id: true, email: true, name: true, role: true, createdAt: true, lastLoginAt: true, isActive: true },
      });
    } catch {
      payload.users = [];
    }
    try {
      payload.leads = await prisma.lead.findMany({ where: { email: q.email, tenantId: q.tenantId } });
    } catch {
      payload.leads = [];
    }
    logger.info({ email: q.email }, "lgpd: export requested");
    return reply.send({ success: true, data: payload });
  });

  // Erase personally identifiable fields. Keeps financial records for
  // tax retention (5 years) per Brazilian law.
  fastify.post("/erase", async (req: FastifyRequest<{ Body: unknown }>, reply: FastifyReply) => {
    const body = z.object({ email: z.string().email(), tenantId: z.string().default(DEFAULT_TENANT), confirm: z.literal(true) }).parse(req.body);
    let affected = 0;
    try {
      const { count: userCount } = await prisma.user.updateMany({
        where: { email: body.email, tenantId: body.tenantId },
        data: { isActive: false, email: `erased-${Date.now()}@orkestra.local`, name: "[Removido - LGPD]" },
      });
      affected += userCount;
    } catch {
      /* tolerate */
    }
    try {
      const { count: leadCount } = await prisma.lead.updateMany({
        where: { email: body.email, tenantId: body.tenantId },
        data: { email: null, phone: null, contactName: "[Removido - LGPD]" },
      });
      affected += leadCount;
    } catch {
      /* tolerate */
    }
    logger.warn({ email: body.email, affected }, "lgpd: erasure executed");
    return reply.send({ success: true, data: { affected, erasedAt: new Date().toISOString() } });
  });

  // Consent log
  fastify.post("/consent", async (req: FastifyRequest<{ Body: unknown }>, reply: FastifyReply) => {
    const body = z
      .object({
        email: z.string().email().optional(),
        anonymousId: z.string().optional(),
        accepted: z.array(z.string()),
        userAgent: z.string().optional(),
      })
      .parse(req.body);
    logger.info({ accepted: body.accepted, email: body.email }, "lgpd: consent recorded");
    return reply.status(201).send({ success: true, data: { recordedAt: new Date().toISOString(), ...body } });
  });
}
