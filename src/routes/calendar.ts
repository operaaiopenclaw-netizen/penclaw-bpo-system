// ============================================================
// CALENDAR — unified week/month view aggregating events, OS, OP, execution
// ============================================================

import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { z } from "zod";
import { prisma } from "../db";
import { config } from "../config/env";

const DEFAULT_TENANT = config.DEFAULT_TENANT_ID;

type CalendarItem = {
  id: string;
  kind: "event" | "service-order" | "production-order" | "execution";
  title: string;
  subtitle?: string;
  status?: string;
  start: string;
  end?: string;
  ownerId?: string | null;
  link: string;
};

function dayRange(from: string, to: string) {
  const f = new Date(from);
  const t = new Date(to);
  return { f, t };
}

export async function calendarRoutes(fastify: FastifyInstance): Promise<void> {
  fastify.get("/range", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z
      .object({
        tenantId: z.string().default(DEFAULT_TENANT),
        from: z.string(),
        to: z.string(),
      })
      .parse(req.query);

    const { f, t } = dayRange(q.from, q.to);
    const items: CalendarItem[] = [];

    // Events
    try {
      const events = await prisma.event.findMany({
        where: { tenantId: q.tenantId, eventDate: { gte: f, lte: t } },
        take: 500,
      });
      for (const e of events) {
        items.push({
          id: e.id,
          kind: "event",
          title: (e as { name?: string; title?: string }).name ?? (e as { title?: string }).title ?? "Evento",
          subtitle: (e as { clientName?: string }).clientName ?? undefined,
          status: e.status ?? undefined,
          start: e.eventDate?.toISOString() ?? new Date().toISOString(),
          link: `events.html?id=${e.id}`,
        });
      }
    } catch {
      /* schema drift tolerated */
    }

    // Service orders (due or scheduled)
    try {
      const sos = await (prisma as any).serviceOrder.findMany({
        where: { tenantId: q.tenantId, scheduledFor: { gte: f, lte: t } },
        take: 500,
      });
      for (const o of sos ?? []) {
        items.push({
          id: o.id,
          kind: "service-order",
          title: `OS ${o.number ?? o.id.slice(0, 6)}`,
          subtitle: o.description ?? undefined,
          status: o.status ?? undefined,
          start: (o.scheduledFor ?? o.createdAt).toISOString(),
          link: `service-orders.html?id=${o.id}`,
        });
      }
    } catch {
      /* optional */
    }

    // Production orders
    try {
      const pos = await (prisma as any).productionOrder.findMany({
        where: { tenantId: q.tenantId, dueDate: { gte: f, lte: t } },
        take: 500,
      });
      for (const p of pos ?? []) {
        items.push({
          id: p.id,
          kind: "production-order",
          title: `OP ${p.number ?? p.id.slice(0, 6)}`,
          subtitle: p.description ?? undefined,
          status: p.status ?? undefined,
          start: (p.dueDate ?? p.createdAt).toISOString(),
          link: `production-orders.html?id=${p.id}`,
        });
      }
    } catch {
      /* optional */
    }

    // Sort
    items.sort((a, b) => a.start.localeCompare(b.start));

    return reply.send({ success: true, data: items, meta: { count: items.length, from: q.from, to: q.to } });
  });
}
