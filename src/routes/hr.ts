// ============================================================
// HR — Openings + Candidates + AI pre-screening
// ============================================================

import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { z } from "zod";
import { promises as fs } from "node:fs";
import path from "node:path";
import { config } from "../config/env";
import { logger } from "../utils/logger";

const DEFAULT_TENANT = config.DEFAULT_TENANT_ID;
const STORE = path.resolve(process.cwd(), "vault", "_hr");

type JobOpening = {
  id: string;
  tenantId: string;
  title: string;
  department: string;
  description: string;
  requirements: string[];
  status: "open" | "paused" | "closed";
  createdAt: string;
  closedAt?: string;
};

type Candidate = {
  id: string;
  tenantId: string;
  name: string;
  email?: string;
  phone?: string;
  resume: string;             // raw text (plain/markdown)
  appliedTo?: string;         // openingId
  aiScore?: number;           // 0-100
  aiRationale?: string;
  aiRecommendation?: "fit" | "borderline" | "reject";
  stage: "new" | "screening" | "interview" | "offer" | "hired" | "rejected";
  notes: string[];
  createdAt: string;
  updatedAt: string;
};

async function loadOpenings(tenantId: string): Promise<JobOpening[]> {
  try { return JSON.parse(await fs.readFile(path.join(STORE, `${tenantId}.openings.json`), "utf8")); }
  catch { return []; }
}
async function saveOpenings(tenantId: string, list: JobOpening[]) {
  await fs.mkdir(STORE, { recursive: true });
  await fs.writeFile(path.join(STORE, `${tenantId}.openings.json`), JSON.stringify(list, null, 2));
}
async function loadCandidates(tenantId: string): Promise<Candidate[]> {
  try { return JSON.parse(await fs.readFile(path.join(STORE, `${tenantId}.candidates.json`), "utf8")); }
  catch { return []; }
}
async function saveCandidates(tenantId: string, list: Candidate[]) {
  await fs.mkdir(STORE, { recursive: true });
  await fs.writeFile(path.join(STORE, `${tenantId}.candidates.json`), JSON.stringify(list, null, 2));
}

function newId(prefix: string) {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

// Simple keyword scorer. Real impl should call Anthropic/embeddings.
function preScreenCandidate(resume: string, opening: JobOpening): {
  score: number;
  rationale: string;
  recommendation: Candidate["aiRecommendation"];
} {
  const text = resume.toLowerCase();
  const hits = opening.requirements.filter((r) => text.includes(r.toLowerCase())).length;
  const score = opening.requirements.length === 0
    ? 50
    : Math.round((hits / opening.requirements.length) * 100);
  const recommendation: Candidate["aiRecommendation"] =
    score >= 70 ? "fit" : score >= 40 ? "borderline" : "reject";
  const rationale = `Atende ${hits}/${opening.requirements.length} requisitos listados. ` +
    (recommendation === "fit" ? "Forte match — recomendo entrevista." :
     recommendation === "borderline" ? "Match parcial — avaliar caso a caso." :
     "Lacunas importantes — perfil abaixo do esperado.");
  return { score, rationale, recommendation };
}

export async function hrRoutes(fastify: FastifyInstance): Promise<void> {
  // --- openings ---
  fastify.get("/openings", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z.object({ tenantId: z.string().default(DEFAULT_TENANT) }).parse(req.query);
    return reply.send({ success: true, data: await loadOpenings(q.tenantId) });
  });

  fastify.post("/openings", async (req: FastifyRequest<{ Body: unknown }>, reply: FastifyReply) => {
    const body = z.object({
      tenantId: z.string().default(DEFAULT_TENANT),
      title: z.string().min(1),
      department: z.string().min(1),
      description: z.string().min(1),
      requirements: z.array(z.string()).default([]),
    }).parse(req.body);
    const list = await loadOpenings(body.tenantId);
    const o: JobOpening = {
      id: newId("open"), tenantId: body.tenantId, title: body.title,
      department: body.department, description: body.description,
      requirements: body.requirements, status: "open", createdAt: new Date().toISOString(),
    };
    list.push(o);
    await saveOpenings(body.tenantId, list);
    return reply.status(201).send({ success: true, data: o });
  });

  fastify.patch("/openings/:id", async (req: FastifyRequest<{ Params: { id: string }; Body: unknown; Querystring: unknown }>, reply: FastifyReply) => {
    const q = z.object({ tenantId: z.string().default(DEFAULT_TENANT) }).parse(req.query);
    const body = z.object({ status: z.enum(["open", "paused", "closed"]) }).parse(req.body);
    const list = await loadOpenings(q.tenantId);
    const ix = list.findIndex((o) => o.id === req.params.id);
    if (ix < 0) return reply.status(404).send({ success: false, error: "Not found" });
    list[ix].status = body.status;
    if (body.status === "closed") list[ix].closedAt = new Date().toISOString();
    await saveOpenings(q.tenantId, list);
    return reply.send({ success: true, data: list[ix] });
  });

  // --- candidates ---
  fastify.get("/candidates", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z.object({
      tenantId: z.string().default(DEFAULT_TENANT),
      openingId: z.string().optional(),
      stage: z.string().optional(),
    }).parse(req.query);
    let list = await loadCandidates(q.tenantId);
    if (q.openingId) list = list.filter((c) => c.appliedTo === q.openingId);
    if (q.stage) list = list.filter((c) => c.stage === q.stage);
    list.sort((a, b) => (b.aiScore ?? 0) - (a.aiScore ?? 0));
    return reply.send({ success: true, data: list });
  });

  fastify.post("/candidates", async (req: FastifyRequest<{ Body: unknown }>, reply: FastifyReply) => {
    const body = z.object({
      tenantId: z.string().default(DEFAULT_TENANT),
      name: z.string().min(1),
      email: z.string().email().optional(),
      phone: z.string().optional(),
      resume: z.string().min(20),
      appliedTo: z.string().optional(),
    }).parse(req.body);

    let aiScore: number | undefined;
    let aiRationale: string | undefined;
    let aiRecommendation: Candidate["aiRecommendation"];
    if (body.appliedTo) {
      const openings = await loadOpenings(body.tenantId);
      const opening = openings.find((o) => o.id === body.appliedTo);
      if (opening) {
        const s = preScreenCandidate(body.resume, opening);
        aiScore = s.score;
        aiRationale = s.rationale;
        aiRecommendation = s.recommendation;
      }
    }

    const c: Candidate = {
      id: newId("cand"), tenantId: body.tenantId, name: body.name,
      email: body.email, phone: body.phone, resume: body.resume,
      appliedTo: body.appliedTo, aiScore, aiRationale, aiRecommendation,
      stage: "new", notes: [],
      createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(),
    };
    const list = await loadCandidates(body.tenantId);
    list.push(c);
    await saveCandidates(body.tenantId, list);
    logger.info({ candidateId: c.id, aiScore }, "hr: candidate added");
    return reply.status(201).send({ success: true, data: c });
  });

  fastify.patch("/candidates/:id", async (req: FastifyRequest<{ Params: { id: string }; Body: unknown; Querystring: unknown }>, reply: FastifyReply) => {
    const q = z.object({ tenantId: z.string().default(DEFAULT_TENANT) }).parse(req.query);
    const body = z.object({
      stage: z.enum(["new", "screening", "interview", "offer", "hired", "rejected"]).optional(),
      addNote: z.string().optional(),
    }).parse(req.body);
    const list = await loadCandidates(q.tenantId);
    const ix = list.findIndex((c) => c.id === req.params.id);
    if (ix < 0) return reply.status(404).send({ success: false, error: "Not found" });
    if (body.stage) list[ix].stage = body.stage;
    if (body.addNote) list[ix].notes.push(`${new Date().toISOString()}: ${body.addNote}`);
    list[ix].updatedAt = new Date().toISOString();
    await saveCandidates(q.tenantId, list);
    return reply.send({ success: true, data: list[ix] });
  });

  fastify.get("/summary", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z.object({ tenantId: z.string().default(DEFAULT_TENANT) }).parse(req.query);
    const [openings, candidates] = await Promise.all([loadOpenings(q.tenantId), loadCandidates(q.tenantId)]);
    const openCount = openings.filter((o) => o.status === "open").length;
    const byStage = candidates.reduce<Record<string, number>>((acc, c) => {
      acc[c.stage] = (acc[c.stage] ?? 0) + 1;
      return acc;
    }, {});
    const fitRate = candidates.length === 0 ? 0
      : candidates.filter((c) => c.aiRecommendation === "fit").length / candidates.length;
    return reply.send({ success: true, data: { openCount, totalCandidates: candidates.length, byStage, fitRate } });
  });
}
