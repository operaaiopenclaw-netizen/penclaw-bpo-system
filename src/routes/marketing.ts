// ============================================================
// MARKETING — Meta Ads + Google Ads + creative pipeline
// ============================================================
// Mock data until Meta/Google credentials wired. UI is real.

import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { z } from "zod";
import { promises as fs } from "node:fs";
import path from "node:path";
import { config } from "../config/env";
import { logger } from "../utils/logger";

const DEFAULT_TENANT = config.DEFAULT_TENANT_ID;
const STORE = path.resolve(process.cwd(), "vault", "_marketing");

type ChannelId = "meta" | "google" | "tiktok" | "organic";

type Campaign = {
  id: string;
  tenantId: string;
  name: string;
  channel: ChannelId;
  status: "active" | "paused" | "ended";
  budgetDaily: number;
  spendToDate: number;
  impressions: number;
  clicks: number;
  conversions: number;
  revenueAttributed: number;
  startedAt: string;
  endedAt?: string;
  creatives: string[];
};

async function load(tenantId: string): Promise<Campaign[]> {
  try {
    return JSON.parse(await fs.readFile(path.join(STORE, `${tenantId}.json`), "utf8"));
  } catch {
    return [];
  }
}

async function save(tenantId: string, list: Campaign[]) {
  await fs.mkdir(STORE, { recursive: true });
  await fs.writeFile(path.join(STORE, `${tenantId}.json`), JSON.stringify(list, null, 2));
}

function newId() {
  return `camp_${Math.random().toString(36).slice(2, 10)}`;
}

// --- provider stubs ----------------------------------------------------
// TODO MetaAdsProvider — requires META_AD_ACCOUNT_ID + META_SYSTEM_TOKEN
// TODO GoogleAdsProvider — requires GOOGLE_ADS_CUSTOMER_ID + OAuth refresh token

function providerStatus() {
  return {
    meta: process.env.META_SYSTEM_TOKEN ? "wired" : "mock",
    google: process.env.GOOGLE_ADS_REFRESH_TOKEN ? "wired" : "mock",
  };
}

// --- routes ------------------------------------------------------------

export async function marketingRoutes(fastify: FastifyInstance): Promise<void> {
  fastify.get("/status", async (_req, reply) => reply.send({ success: true, data: providerStatus() }));

  fastify.get("/campaigns", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z
      .object({
        tenantId: z.string().default(DEFAULT_TENANT),
        channel: z.enum(["meta", "google", "tiktok", "organic"]).optional(),
      })
      .parse(req.query);
    let list = await load(q.tenantId);
    if (q.channel) list = list.filter((c) => c.channel === q.channel);
    return reply.send({ success: true, data: list, meta: { provider: providerStatus() } });
  });

  fastify.post("/campaigns", async (req: FastifyRequest<{ Body: unknown }>, reply: FastifyReply) => {
    const body = z
      .object({
        tenantId: z.string().default(DEFAULT_TENANT),
        name: z.string().min(1),
        channel: z.enum(["meta", "google", "tiktok", "organic"]),
        budgetDaily: z.number().nonnegative(),
        creatives: z.array(z.string()).default([]),
      })
      .parse(req.body);
    const list = await load(body.tenantId);
    const c: Campaign = {
      id: newId(),
      tenantId: body.tenantId,
      name: body.name,
      channel: body.channel,
      status: "active",
      budgetDaily: body.budgetDaily,
      spendToDate: 0,
      impressions: 0,
      clicks: 0,
      conversions: 0,
      revenueAttributed: 0,
      startedAt: new Date().toISOString(),
      creatives: body.creatives,
    };
    list.push(c);
    await save(body.tenantId, list);
    logger.info({ campaignId: c.id, channel: c.channel }, "marketing: campaign created");
    return reply.status(201).send({ success: true, data: c });
  });

  fastify.patch("/campaigns/:id", async (
    req: FastifyRequest<{ Params: { id: string }; Body: unknown; Querystring: unknown }>,
    reply: FastifyReply,
  ) => {
    const q = z.object({ tenantId: z.string().default(DEFAULT_TENANT) }).parse(req.query);
    const body = z
      .object({
        status: z.enum(["active", "paused", "ended"]).optional(),
        budgetDaily: z.number().nonnegative().optional(),
      })
      .parse(req.body);
    const list = await load(q.tenantId);
    const ix = list.findIndex((c) => c.id === req.params.id);
    if (ix < 0) return reply.status(404).send({ success: false, error: "Not found" });
    if (body.status) list[ix].status = body.status;
    if (typeof body.budgetDaily === "number") list[ix].budgetDaily = body.budgetDaily;
    if (body.status === "ended") list[ix].endedAt = new Date().toISOString();
    await save(q.tenantId, list);
    return reply.send({ success: true, data: list[ix] });
  });

  fastify.get("/summary", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z.object({ tenantId: z.string().default(DEFAULT_TENANT) }).parse(req.query);
    const list = await load(q.tenantId);
    const totals = list.reduce(
      (acc, c) => ({
        spend: acc.spend + c.spendToDate,
        clicks: acc.clicks + c.clicks,
        impressions: acc.impressions + c.impressions,
        conversions: acc.conversions + c.conversions,
        revenue: acc.revenue + c.revenueAttributed,
      }),
      { spend: 0, clicks: 0, impressions: 0, conversions: 0, revenue: 0 },
    );
    const roas = totals.spend > 0 ? totals.revenue / totals.spend : 0;
    const cpc = totals.clicks > 0 ? totals.spend / totals.clicks : 0;
    const cpa = totals.conversions > 0 ? totals.spend / totals.conversions : 0;
    return reply.send({ success: true, data: { totals, roas, cpc, cpa, campaigns: list.length, provider: providerStatus() } });
  });
}
