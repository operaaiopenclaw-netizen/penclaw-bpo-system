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
import { generateCopy, renderLandingPage, LPBrief } from "../services/landing-page-generator";

const DEFAULT_TENANT = config.DEFAULT_TENANT_ID;
const STORE = path.resolve(process.cwd(), "vault", "_marketing");
const LP_STORE = path.resolve(process.cwd(), "vault", "_landing-pages");

type LandingPage = {
  id: string;
  slug: string;
  tenantId: string;
  campaignId?: string;
  brief: LPBrief;
  copy: Awaited<ReturnType<typeof generateCopy>>;
  html: string;
  views: number;
  createdAt: string;
  updatedAt: string;
  publishedAt?: string;
  status: "draft" | "published" | "archived";
};

async function loadLPs(tenantId: string): Promise<LandingPage[]> {
  try {
    return JSON.parse(await fs.readFile(path.join(LP_STORE, `${tenantId}.json`), "utf8"));
  } catch {
    return [];
  }
}

async function saveLPs(tenantId: string, list: LandingPage[]) {
  await fs.mkdir(LP_STORE, { recursive: true });
  await fs.writeFile(path.join(LP_STORE, `${tenantId}.json`), JSON.stringify(list, null, 2));
}

function slugify(s: string): string {
  return s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
}

async function uniqueSlug(tenantId: string, desired: string): Promise<string> {
  const base = slugify(desired) || `lp-${Math.random().toString(36).slice(2, 8)}`;
  const all = await loadAllLPs();
  const used = new Set(all.map((l) => l.slug));
  if (!used.has(base)) return base;
  let i = 2;
  while (used.has(`${base}-${i}`)) i++;
  return `${base}-${i}`;
}

async function loadAllLPs(): Promise<LandingPage[]> {
  try {
    const files = await fs.readdir(LP_STORE);
    const lists = await Promise.all(
      files
        .filter((f) => f.endsWith(".json"))
        .map(async (f) => {
          try {
            return JSON.parse(await fs.readFile(path.join(LP_STORE, f), "utf8")) as LandingPage[];
          } catch {
            return [] as LandingPage[];
          }
        }),
    );
    return lists.flat();
  } catch {
    return [];
  }
}

export async function findPublishedLP(slug: string): Promise<LandingPage | null> {
  const all = await loadAllLPs();
  return all.find((l) => l.slug === slug && l.status === "published") ?? null;
}

export async function incrementLPView(lp: LandingPage): Promise<void> {
  lp.views += 1;
  const list = await loadLPs(lp.tenantId);
  const ix = list.findIndex((l) => l.id === lp.id);
  if (ix >= 0) {
    list[ix].views = lp.views;
    await saveLPs(lp.tenantId, list);
  }
}

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

  // ── Landing pages ────────────────────────────────────────────────
  const briefSchema = z.object({
    product: z.string().min(1),
    audience: z.string().min(1),
    problem: z.string().min(1),
    offer: z.string().min(1),
    cta: z.string().min(1),
    ctaHref: z.string().min(1),
    tone: z.enum(["formal", "direto", "acolhedor", "premium"]).optional(),
    highlights: z.array(z.string()).optional(),
    contactEmail: z.string().email().optional(),
    contactPhone: z.string().optional(),
  });

  fastify.get("/landing-pages", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z.object({ tenantId: z.string().default(DEFAULT_TENANT) }).parse(req.query);
    const list = await loadLPs(q.tenantId);
    const safe = list.map((lp) => ({ ...lp, html: undefined }));
    return reply.send({ success: true, data: safe });
  });

  fastify.get("/landing-pages/:id", async (
    req: FastifyRequest<{ Params: { id: string }; Querystring: unknown }>,
    reply: FastifyReply,
  ) => {
    const q = z.object({ tenantId: z.string().default(DEFAULT_TENANT) }).parse(req.query);
    const list = await loadLPs(q.tenantId);
    const lp = list.find((l) => l.id === req.params.id);
    if (!lp) return reply.status(404).send({ success: false, error: "Not found" });
    return reply.send({ success: true, data: lp });
  });

  fastify.post("/landing-pages", async (req: FastifyRequest<{ Body: unknown }>, reply: FastifyReply) => {
    const body = z
      .object({
        tenantId: z.string().default(DEFAULT_TENANT),
        brief: briefSchema,
        slug: z.string().optional(),
        campaignId: z.string().optional(),
      })
      .parse(req.body);

    const now = new Date().toISOString();
    const id = `lp_${Math.random().toString(36).slice(2, 10)}`;
    const slug = await uniqueSlug(body.tenantId, body.slug ?? body.brief.product);
    const copy = await generateCopy(body.brief);
    const html = renderLandingPage(body.brief, copy, { slug, lpId: id });

    const lp: LandingPage = {
      id,
      slug,
      tenantId: body.tenantId,
      campaignId: body.campaignId,
      brief: body.brief,
      copy,
      html,
      views: 0,
      createdAt: now,
      updatedAt: now,
      status: "draft",
    };

    const list = await loadLPs(body.tenantId);
    list.push(lp);
    await saveLPs(body.tenantId, list);
    logger.info({ lpId: id, slug }, "marketing: landing page created");
    return reply.status(201).send({ success: true, data: lp });
  });

  fastify.patch("/landing-pages/:id", async (
    req: FastifyRequest<{ Params: { id: string }; Body: unknown; Querystring: unknown }>,
    reply: FastifyReply,
  ) => {
    const q = z.object({ tenantId: z.string().default(DEFAULT_TENANT) }).parse(req.query);
    const body = z
      .object({
        status: z.enum(["draft", "published", "archived"]).optional(),
        brief: briefSchema.optional(),
        regenerate: z.boolean().optional(),
      })
      .parse(req.body);

    const list = await loadLPs(q.tenantId);
    const ix = list.findIndex((l) => l.id === req.params.id);
    if (ix < 0) return reply.status(404).send({ success: false, error: "Not found" });

    const lp = list[ix];
    if (body.brief) lp.brief = body.brief;
    if (body.regenerate || body.brief) {
      lp.copy = await generateCopy(lp.brief);
      lp.html = renderLandingPage(lp.brief, lp.copy, { slug: lp.slug, lpId: lp.id });
    }
    if (body.status) {
      lp.status = body.status;
      if (body.status === "published" && !lp.publishedAt) lp.publishedAt = new Date().toISOString();
    }
    lp.updatedAt = new Date().toISOString();
    list[ix] = lp;
    await saveLPs(q.tenantId, list);
    return reply.send({ success: true, data: lp });
  });

  fastify.delete("/landing-pages/:id", async (
    req: FastifyRequest<{ Params: { id: string }; Querystring: unknown }>,
    reply: FastifyReply,
  ) => {
    const q = z.object({ tenantId: z.string().default(DEFAULT_TENANT) }).parse(req.query);
    const list = await loadLPs(q.tenantId);
    const filtered = list.filter((l) => l.id !== req.params.id);
    if (filtered.length === list.length) return reply.status(404).send({ success: false, error: "Not found" });
    await saveLPs(q.tenantId, filtered);
    return reply.send({ success: true });
  });
}
