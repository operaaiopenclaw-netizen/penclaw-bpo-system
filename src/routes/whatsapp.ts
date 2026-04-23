// ============================================================
// WHATSAPP — inbox + send + webhook (provider abstraction)
// ============================================================
// Mock provider active by default. Flip WHATSAPP_PROVIDER to
// "twilio" or "evolution" and set credentials to wire real send.

import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { z } from "zod";
import { promises as fs } from "node:fs";
import path from "node:path";
import { config } from "../config/env";
import { logger } from "../utils/logger";

const DEFAULT_TENANT = config.DEFAULT_TENANT_ID;
const STORE = path.resolve(process.cwd(), "vault", "_whatsapp");

type WaDirection = "in" | "out";
type WaStatus = "queued" | "sent" | "delivered" | "read" | "failed" | "received";

type WaMessage = {
  id: string;
  tenantId: string;
  phone: string;          // E.164
  direction: WaDirection;
  body: string;
  status: WaStatus;
  createdAt: string;
  externalId?: string;
  error?: string;
};

async function load(tenantId: string): Promise<WaMessage[]> {
  try {
    return JSON.parse(await fs.readFile(path.join(STORE, `${tenantId}.json`), "utf8"));
  } catch {
    return [];
  }
}

async function save(tenantId: string, list: WaMessage[]) {
  await fs.mkdir(STORE, { recursive: true });
  await fs.writeFile(path.join(STORE, `${tenantId}.json`), JSON.stringify(list, null, 2));
}

function newId() {
  return `wa_${Math.random().toString(36).slice(2, 10)}`;
}

// --- provider ----------------------------------------------------------

type Provider = {
  name: string;
  send(phone: string, body: string): Promise<{ externalId: string; status: WaStatus }>;
};

const MOCK: Provider = {
  name: "mock",
  async send(phone, body) {
    logger.info({ phone, preview: body.slice(0, 60) }, "[mock whatsapp] send");
    return { externalId: `mock-${Math.random().toString(36).slice(2, 10)}`, status: "sent" };
  },
};

// TODO: TwilioProvider — requires TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN + TWILIO_WA_FROM
// TODO: EvolutionAPIProvider — requires EVOLUTION_URL + EVOLUTION_KEY

function getProvider(): Provider {
  const chosen = (process.env.WHATSAPP_PROVIDER ?? "mock").toLowerCase();
  if (chosen !== "mock") logger.warn({ provider: chosen }, "whatsapp provider not wired, using mock");
  return MOCK;
}

// --- routes ------------------------------------------------------------

export async function whatsappRoutes(fastify: FastifyInstance): Promise<void> {
  fastify.get("/conversations", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z.object({ tenantId: z.string().default(DEFAULT_TENANT) }).parse(req.query);
    const list = await load(q.tenantId);
    const byPhone = new Map<string, WaMessage[]>();
    for (const m of list) {
      if (!byPhone.has(m.phone)) byPhone.set(m.phone, []);
      byPhone.get(m.phone)!.push(m);
    }
    const convs = [...byPhone.entries()].map(([phone, msgs]) => {
      msgs.sort((a, b) => a.createdAt.localeCompare(b.createdAt));
      const last = msgs[msgs.length - 1];
      return {
        phone,
        lastMessage: last.body.slice(0, 80),
        lastDirection: last.direction,
        lastAt: last.createdAt,
        unread: msgs.filter((m) => m.direction === "in" && m.status !== "read").length,
        total: msgs.length,
      };
    });
    convs.sort((a, b) => b.lastAt.localeCompare(a.lastAt));
    return reply.send({ success: true, data: convs, meta: { provider: getProvider().name } });
  });

  fastify.get("/messages", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z
      .object({
        tenantId: z.string().default(DEFAULT_TENANT),
        phone: z.string().min(1),
        limit: z.coerce.number().max(200).default(100),
      })
      .parse(req.query);
    const list = (await load(q.tenantId))
      .filter((m) => m.phone === q.phone)
      .sort((a, b) => a.createdAt.localeCompare(b.createdAt));
    return reply.send({ success: true, data: list.slice(-q.limit) });
  });

  fastify.post("/send", async (req: FastifyRequest<{ Body: unknown }>, reply: FastifyReply) => {
    const body = z
      .object({
        tenantId: z.string().default(DEFAULT_TENANT),
        phone: z.string().min(1),
        body: z.string().min(1).max(4000),
      })
      .parse(req.body);

    const provider = getProvider();
    const sent = await provider.send(body.phone, body.body);
    const msg: WaMessage = {
      id: newId(),
      tenantId: body.tenantId,
      phone: body.phone,
      direction: "out",
      body: body.body,
      status: sent.status,
      externalId: sent.externalId,
      createdAt: new Date().toISOString(),
    };
    const list = await load(body.tenantId);
    list.push(msg);
    await save(body.tenantId, list);
    return reply.status(201).send({ success: true, data: msg });
  });

  // Webhook for inbound messages
  fastify.post("/webhook", async (req: FastifyRequest<{ Body: unknown }>, reply: FastifyReply) => {
    const body = z
      .object({
        tenantId: z.string().default(DEFAULT_TENANT),
        phone: z.string(),
        body: z.string(),
        externalId: z.string().optional(),
      })
      .parse(req.body);
    const msg: WaMessage = {
      id: newId(),
      tenantId: body.tenantId,
      phone: body.phone,
      direction: "in",
      body: body.body,
      status: "received",
      externalId: body.externalId,
      createdAt: new Date().toISOString(),
    };
    const list = await load(body.tenantId);
    list.push(msg);
    await save(body.tenantId, list);
    logger.info({ phone: body.phone }, "whatsapp: inbound");
    return reply.status(201).send({ success: true, data: msg });
  });
}
