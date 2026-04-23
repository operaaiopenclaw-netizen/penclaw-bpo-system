// ============================================================
// CHECKLISTS — photo-evidence quality control (IziCheck-style)
// ============================================================
// Templates define reusable checklists per area/shift with
// recurrence. Runs instantiate a template for a given event/OS
// and track item-level completion with mandatory photo proof.
//
// Storage: filesystem under vault/_checklists/{templates|runs}/
// matches the pattern used by marketing, ai-chat, landing-pages.

import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { z } from "zod";
import { promises as fs } from "node:fs";
import path from "node:path";
import { config } from "../config/env";
import { logger } from "../utils/logger";

const DEFAULT_TENANT = config.DEFAULT_TENANT_ID;
const ROOT = path.resolve(process.cwd(), "vault", "_checklists");
const TPL_DIR = path.join(ROOT, "templates");
const RUN_DIR = path.join(ROOT, "runs");

const AREAS = ["cozinha", "salao", "bar", "montagem", "limpeza", "auditoria", "producao", "geral"] as const;
const SHIFTS = ["manha", "tarde", "noite", "integral"] as const;
const RECURRENCES = ["daily", "weekly", "monthly", "per-event", "one-off"] as const;

type Area = (typeof AREAS)[number];
type Shift = (typeof SHIFTS)[number];
type Recurrence = (typeof RECURRENCES)[number];

type TemplateItem = {
  id: string;
  title: string;
  description?: string;
  photoRequired: boolean;
  order: number;
};

type ChecklistTemplate = {
  id: string;
  tenantId: string;
  name: string;
  area: Area;
  shift: Shift;
  recurrence: Recurrence;
  items: TemplateItem[];
  active: boolean;
  createdAt: string;
  updatedAt: string;
};

type RunItem = {
  id: string;
  templateItemId: string;
  title: string;
  description?: string;
  photoRequired: boolean;
  order: number;
  // completion state
  completed: boolean;
  completedAt?: string;
  completedBy?: string;
  photoUrl?: string;
  notes?: string;
};

type ChecklistRun = {
  id: string;
  tenantId: string;
  templateId: string;
  name: string;
  area: Area;
  shift: Shift;
  eventId?: string;
  serviceOrderId?: string;
  scheduledFor: string;
  status: "pending" | "in_progress" | "completed" | "cancelled";
  items: RunItem[];
  startedAt?: string;
  completedAt?: string;
  completedBy?: string;
  createdAt: string;
  updatedAt: string;
};

function newId(prefix: string) {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

async function loadTemplates(tenantId: string): Promise<ChecklistTemplate[]> {
  try {
    return JSON.parse(await fs.readFile(path.join(TPL_DIR, `${tenantId}.json`), "utf8"));
  } catch {
    return [];
  }
}

async function saveTemplates(tenantId: string, list: ChecklistTemplate[]) {
  await fs.mkdir(TPL_DIR, { recursive: true });
  await fs.writeFile(path.join(TPL_DIR, `${tenantId}.json`), JSON.stringify(list, null, 2));
}

async function loadRuns(tenantId: string): Promise<ChecklistRun[]> {
  try {
    return JSON.parse(await fs.readFile(path.join(RUN_DIR, `${tenantId}.json`), "utf8"));
  } catch {
    return [];
  }
}

async function saveRuns(tenantId: string, list: ChecklistRun[]) {
  await fs.mkdir(RUN_DIR, { recursive: true });
  await fs.writeFile(path.join(RUN_DIR, `${tenantId}.json`), JSON.stringify(list, null, 2));
}

function completionPct(run: ChecklistRun): number {
  if (!run.items.length) return 0;
  const done = run.items.filter((i) => i.completed).length;
  return Math.round((done / run.items.length) * 100);
}

// ─── routes ────────────────────────────────────────────────────────

export async function checklistsRoutes(fastify: FastifyInstance): Promise<void> {
  // ── Templates ──
  fastify.get("/templates", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z
      .object({
        tenantId: z.string().default(DEFAULT_TENANT),
        area: z.enum(AREAS).optional(),
        active: z.coerce.boolean().optional(),
      })
      .parse(req.query);
    let list = await loadTemplates(q.tenantId);
    if (q.area) list = list.filter((t) => t.area === q.area);
    if (q.active !== undefined) list = list.filter((t) => t.active === q.active);
    return reply.send({ success: true, data: list });
  });

  fastify.post("/templates", async (req: FastifyRequest<{ Body: unknown }>, reply: FastifyReply) => {
    const body = z
      .object({
        tenantId: z.string().default(DEFAULT_TENANT),
        name: z.string().min(1),
        area: z.enum(AREAS),
        shift: z.enum(SHIFTS),
        recurrence: z.enum(RECURRENCES),
        items: z
          .array(
            z.object({
              title: z.string().min(1),
              description: z.string().optional(),
              photoRequired: z.boolean().default(true),
            }),
          )
          .min(1),
      })
      .parse(req.body);

    const now = new Date().toISOString();
    const tpl: ChecklistTemplate = {
      id: newId("tpl"),
      tenantId: body.tenantId,
      name: body.name,
      area: body.area,
      shift: body.shift,
      recurrence: body.recurrence,
      items: body.items.map((it, ix) => ({
        id: newId("tit"),
        title: it.title,
        description: it.description,
        photoRequired: it.photoRequired,
        order: ix,
      })),
      active: true,
      createdAt: now,
      updatedAt: now,
    };
    const list = await loadTemplates(body.tenantId);
    list.push(tpl);
    await saveTemplates(body.tenantId, list);
    logger.info({ templateId: tpl.id, area: tpl.area }, "checklist template created");
    return reply.status(201).send({ success: true, data: tpl });
  });

  fastify.patch("/templates/:id", async (
    req: FastifyRequest<{ Params: { id: string }; Body: unknown; Querystring: unknown }>,
    reply: FastifyReply,
  ) => {
    const q = z.object({ tenantId: z.string().default(DEFAULT_TENANT) }).parse(req.query);
    const body = z
      .object({
        name: z.string().optional(),
        active: z.boolean().optional(),
        items: z
          .array(
            z.object({
              title: z.string().min(1),
              description: z.string().optional(),
              photoRequired: z.boolean().default(true),
            }),
          )
          .optional(),
      })
      .parse(req.body);
    const list = await loadTemplates(q.tenantId);
    const ix = list.findIndex((t) => t.id === req.params.id);
    if (ix < 0) return reply.status(404).send({ success: false, error: "Template not found" });
    if (body.name !== undefined) list[ix].name = body.name;
    if (body.active !== undefined) list[ix].active = body.active;
    if (body.items) {
      list[ix].items = body.items.map((it, i) => ({
        id: newId("tit"),
        title: it.title,
        description: it.description,
        photoRequired: it.photoRequired,
        order: i,
      }));
    }
    list[ix].updatedAt = new Date().toISOString();
    await saveTemplates(q.tenantId, list);
    return reply.send({ success: true, data: list[ix] });
  });

  fastify.delete("/templates/:id", async (
    req: FastifyRequest<{ Params: { id: string }; Querystring: unknown }>,
    reply: FastifyReply,
  ) => {
    const q = z.object({ tenantId: z.string().default(DEFAULT_TENANT) }).parse(req.query);
    const list = await loadTemplates(q.tenantId);
    const filtered = list.filter((t) => t.id !== req.params.id);
    if (filtered.length === list.length) return reply.status(404).send({ success: false, error: "Not found" });
    await saveTemplates(q.tenantId, filtered);
    return reply.status(204).send();
  });

  // ── Runs ──
  fastify.get("/runs", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z
      .object({
        tenantId: z.string().default(DEFAULT_TENANT),
        eventId: z.string().optional(),
        serviceOrderId: z.string().optional(),
        status: z.enum(["pending", "in_progress", "completed", "cancelled"]).optional(),
        area: z.enum(AREAS).optional(),
      })
      .parse(req.query);
    let list = await loadRuns(q.tenantId);
    if (q.eventId) list = list.filter((r) => r.eventId === q.eventId);
    if (q.serviceOrderId) list = list.filter((r) => r.serviceOrderId === q.serviceOrderId);
    if (q.status) list = list.filter((r) => r.status === q.status);
    if (q.area) list = list.filter((r) => r.area === q.area);
    const withPct = list.map((r) => ({ ...r, completionPct: completionPct(r) }));
    return reply.send({ success: true, data: withPct });
  });

  fastify.get("/runs/:id", async (
    req: FastifyRequest<{ Params: { id: string }; Querystring: unknown }>,
    reply: FastifyReply,
  ) => {
    const q = z.object({ tenantId: z.string().default(DEFAULT_TENANT) }).parse(req.query);
    const list = await loadRuns(q.tenantId);
    const run = list.find((r) => r.id === req.params.id);
    if (!run) return reply.status(404).send({ success: false, error: "Run not found" });
    return reply.send({ success: true, data: { ...run, completionPct: completionPct(run) } });
  });

  // Create run by instantiating a template.
  fastify.post("/runs", async (req: FastifyRequest<{ Body: unknown }>, reply: FastifyReply) => {
    const body = z
      .object({
        tenantId: z.string().default(DEFAULT_TENANT),
        templateId: z.string(),
        scheduledFor: z.string(),
        eventId: z.string().optional(),
        serviceOrderId: z.string().optional(),
        name: z.string().optional(),
      })
      .parse(req.body);

    const templates = await loadTemplates(body.tenantId);
    const tpl = templates.find((t) => t.id === body.templateId);
    if (!tpl) return reply.status(404).send({ success: false, error: "Template not found" });
    if (!tpl.active) return reply.status(400).send({ success: false, error: "Template is inactive" });

    const now = new Date().toISOString();
    const run: ChecklistRun = {
      id: newId("run"),
      tenantId: body.tenantId,
      templateId: tpl.id,
      name: body.name ?? tpl.name,
      area: tpl.area,
      shift: tpl.shift,
      eventId: body.eventId,
      serviceOrderId: body.serviceOrderId,
      scheduledFor: body.scheduledFor,
      status: "pending",
      items: tpl.items.map((it) => ({
        id: newId("ri"),
        templateItemId: it.id,
        title: it.title,
        description: it.description,
        photoRequired: it.photoRequired,
        order: it.order,
        completed: false,
      })),
      createdAt: now,
      updatedAt: now,
    };

    const runs = await loadRuns(body.tenantId);
    runs.push(run);
    await saveRuns(body.tenantId, runs);
    logger.info({ runId: run.id, templateId: tpl.id }, "checklist run created");
    return reply.status(201).send({ success: true, data: run });
  });

  // Complete / undo a single item. Photo required enforced here.
  fastify.patch("/runs/:runId/items/:itemId", async (
    req: FastifyRequest<{
      Params: { runId: string; itemId: string };
      Body: unknown;
      Querystring: unknown;
    }>,
    reply: FastifyReply,
  ) => {
    const q = z.object({ tenantId: z.string().default(DEFAULT_TENANT) }).parse(req.query);
    const body = z
      .object({
        completed: z.boolean(),
        photoUrl: z.string().optional(),
        notes: z.string().optional(),
        completedBy: z.string().optional(),
      })
      .parse(req.body);

    const runs = await loadRuns(q.tenantId);
    const rIx = runs.findIndex((r) => r.id === req.params.runId);
    if (rIx < 0) return reply.status(404).send({ success: false, error: "Run not found" });
    const run = runs[rIx];
    const iIx = run.items.findIndex((i) => i.id === req.params.itemId);
    if (iIx < 0) return reply.status(404).send({ success: false, error: "Item not found" });
    const item = run.items[iIx];

    if (body.completed) {
      if (item.photoRequired && !body.photoUrl && !item.photoUrl) {
        return reply.status(400).send({
          success: false,
          error: "Foto obrigatória — anexe uma imagem antes de concluir este item",
        });
      }
      item.completed = true;
      item.completedAt = new Date().toISOString();
      item.completedBy = body.completedBy;
      if (body.photoUrl) item.photoUrl = body.photoUrl;
      if (body.notes) item.notes = body.notes;
    } else {
      item.completed = false;
      item.completedAt = undefined;
      item.completedBy = undefined;
    }

    run.items[iIx] = item;
    // Auto-advance status
    const pct = completionPct(run);
    if (pct === 100 && run.status !== "completed") {
      run.status = "completed";
      run.completedAt = new Date().toISOString();
      run.completedBy = body.completedBy;
    } else if (pct > 0 && run.status === "pending") {
      run.status = "in_progress";
      run.startedAt = run.startedAt ?? new Date().toISOString();
    } else if (pct === 0 && run.status !== "pending") {
      run.status = "pending";
      run.completedAt = undefined;
    }
    run.updatedAt = new Date().toISOString();
    runs[rIx] = run;
    await saveRuns(q.tenantId, runs);
    return reply.send({ success: true, data: { ...run, completionPct: pct } });
  });

  fastify.delete("/runs/:id", async (
    req: FastifyRequest<{ Params: { id: string }; Querystring: unknown }>,
    reply: FastifyReply,
  ) => {
    const q = z.object({ tenantId: z.string().default(DEFAULT_TENANT) }).parse(req.query);
    const runs = await loadRuns(q.tenantId);
    const filtered = runs.filter((r) => r.id !== req.params.id);
    if (filtered.length === runs.length) return reply.status(404).send({ success: false, error: "Not found" });
    await saveRuns(q.tenantId, filtered);
    return reply.status(204).send();
  });

  // ── Dashboard / ranking ──
  fastify.get("/summary", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z.object({ tenantId: z.string().default(DEFAULT_TENANT) }).parse(req.query);
    const runs = await loadRuns(q.tenantId);

    const now = new Date();
    const first = new Date(now.getFullYear(), now.getMonth(), 1).toISOString();

    const monthRuns = runs.filter((r) => r.scheduledFor >= first);
    const totalItems = monthRuns.reduce((acc, r) => acc + r.items.length, 0);
    const doneItems = monthRuns.reduce((acc, r) => acc + r.items.filter((i) => i.completed).length, 0);
    const overallPct = totalItems ? Math.round((doneItems / totalItems) * 100) : 0;

    // Ranking by completedBy
    const rankingMap = new Map<string, { completed: number; withPhoto: number }>();
    for (const r of monthRuns) {
      for (const i of r.items) {
        if (i.completed && i.completedBy) {
          const cur = rankingMap.get(i.completedBy) ?? { completed: 0, withPhoto: 0 };
          cur.completed += 1;
          if (i.photoUrl) cur.withPhoto += 1;
          rankingMap.set(i.completedBy, cur);
        }
      }
    }
    const ranking = Array.from(rankingMap.entries())
      .map(([user, stats]) => ({ user, ...stats }))
      .sort((a, b) => b.completed - a.completed)
      .slice(0, 10);

    // Status counts
    const byStatus = runs.reduce<Record<string, number>>((acc, r) => {
      acc[r.status] = (acc[r.status] ?? 0) + 1;
      return acc;
    }, {});

    // Area distribution (month)
    const byArea = monthRuns.reduce<Record<string, number>>((acc, r) => {
      acc[r.area] = (acc[r.area] ?? 0) + 1;
      return acc;
    }, {});

    return reply.send({
      success: true,
      data: {
        overallPct,
        totalRuns: runs.length,
        monthRuns: monthRuns.length,
        byStatus,
        byArea,
        ranking,
        period: first.slice(0, 7),
      },
    });
  });
}
