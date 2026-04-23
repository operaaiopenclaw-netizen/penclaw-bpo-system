// ============================================================
// VAULT — brand/document hub for each tenant
// ============================================================
// Upload / list / download institutional documents: contracts,
// presentations, flyers, proposals, brand-kit files, media.
//
// Storage: filesystem under /vault/{tenantId}/{category}/{filename}
// Metadata: JSON index per tenant at /vault/{tenantId}/_index.json
//
// This scaffold is intentionally simple — production should move
// to S3/R2 and a Vault model in Prisma.

import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { z } from "zod";
import { promises as fs } from "node:fs";
import path from "node:path";
import { config } from "../config/env";
import { logger } from "../utils/logger";

const DEFAULT_TENANT = config.DEFAULT_TENANT_ID;
const ROOT = path.resolve(process.cwd(), "vault");

const CATEGORIES = [
  "contratos",
  "apresentacoes",
  "flyers",
  "propostas",
  "brand-kit",
  "midia",
  "outros",
] as const;

type Category = typeof CATEGORIES[number];

type VaultDoc = {
  id: string;
  tenantId: string;
  category: Category;
  filename: string;
  size: number;
  mime: string;
  uploadedBy?: string;
  uploadedAt: string;
  tags: string[];
  notes?: string;
};

async function ensureDir(p: string) {
  await fs.mkdir(p, { recursive: true });
}

async function loadIndex(tenantId: string): Promise<VaultDoc[]> {
  const indexPath = path.join(ROOT, tenantId, "_index.json");
  try {
    const raw = await fs.readFile(indexPath, "utf8");
    return JSON.parse(raw) as VaultDoc[];
  } catch {
    return [];
  }
}

async function saveIndex(tenantId: string, docs: VaultDoc[]) {
  const dir = path.join(ROOT, tenantId);
  await ensureDir(dir);
  await fs.writeFile(path.join(dir, "_index.json"), JSON.stringify(docs, null, 2));
}

function newId() {
  return `doc_${Math.random().toString(36).slice(2, 10)}`;
}

export async function vaultRoutes(fastify: FastifyInstance): Promise<void> {
  fastify.get("/categories", async (_req, reply) => reply.send({ success: true, data: CATEGORIES }));

  fastify.get("/docs", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z
      .object({
        tenantId: z.string().default(DEFAULT_TENANT),
        category: z.enum(CATEGORIES).optional(),
      })
      .parse(req.query);
    const docs = await loadIndex(q.tenantId);
    const filtered = q.category ? docs.filter((d) => d.category === q.category) : docs;
    return reply.send({ success: true, data: filtered.sort((a, b) => b.uploadedAt.localeCompare(a.uploadedAt)) });
  });

  // Simplified upload: accept base64 content via JSON.
  // Production should use multipart/form-data.
  fastify.post("/docs", async (req: FastifyRequest<{ Body: unknown }>, reply: FastifyReply) => {
    const body = z
      .object({
        tenantId: z.string().default(DEFAULT_TENANT),
        category: z.enum(CATEGORIES),
        filename: z.string().min(1),
        mime: z.string().default("application/octet-stream"),
        contentBase64: z.string().min(1),
        uploadedBy: z.string().optional(),
        tags: z.array(z.string()).default([]),
        notes: z.string().optional(),
      })
      .parse(req.body);

    const buf = Buffer.from(body.contentBase64, "base64");
    const dir = path.join(ROOT, body.tenantId, body.category);
    await ensureDir(dir);
    const safeName = body.filename.replace(/[^a-zA-Z0-9._-]/g, "_");
    const id = newId();
    const storedName = `${id}__${safeName}`;
    await fs.writeFile(path.join(dir, storedName), buf);

    const doc: VaultDoc = {
      id,
      tenantId: body.tenantId,
      category: body.category,
      filename: storedName,
      size: buf.length,
      mime: body.mime,
      uploadedBy: body.uploadedBy,
      uploadedAt: new Date().toISOString(),
      tags: body.tags,
      notes: body.notes,
    };

    const docs = await loadIndex(body.tenantId);
    docs.push(doc);
    await saveIndex(body.tenantId, docs);

    logger.info({ docId: id, category: doc.category }, "vault: doc stored");
    return reply.status(201).send({ success: true, data: doc });
  });

  fastify.delete("/docs/:id", async (req: FastifyRequest<{ Params: { id: string }; Querystring: unknown }>, reply: FastifyReply) => {
    const q = z.object({ tenantId: z.string().default(DEFAULT_TENANT) }).parse(req.query);
    const docs = await loadIndex(q.tenantId);
    const ix = docs.findIndex((d) => d.id === req.params.id);
    if (ix < 0) return reply.status(404).send({ success: false, error: "Not found" });
    const doc = docs[ix];
    try {
      await fs.unlink(path.join(ROOT, q.tenantId, doc.category, doc.filename));
    } catch {
      /* already missing */
    }
    docs.splice(ix, 1);
    await saveIndex(q.tenantId, docs);
    return reply.status(204).send();
  });

  fastify.get("/docs/:id/download", async (req: FastifyRequest<{ Params: { id: string }; Querystring: unknown }>, reply: FastifyReply) => {
    const q = z.object({ tenantId: z.string().default(DEFAULT_TENANT) }).parse(req.query);
    const docs = await loadIndex(q.tenantId);
    const doc = docs.find((d) => d.id === req.params.id);
    if (!doc) return reply.status(404).send({ success: false, error: "Not found" });
    const p = path.join(ROOT, q.tenantId, doc.category, doc.filename);
    const buf = await fs.readFile(p);
    reply.header("content-type", doc.mime);
    reply.header("content-disposition", `attachment; filename="${doc.filename.split("__").slice(1).join("__")}"`);
    return reply.send(buf);
  });

  // AI-assisted draft generator stub
  fastify.post("/generate", async (req: FastifyRequest<{ Body: unknown }>, reply: FastifyReply) => {
    const body = z
      .object({
        kind: z.enum(["proposta", "contrato", "apresentacao-comercial", "brand-kit"]),
        context: z.string().max(2000).optional(),
      })
      .parse(req.body);
    // TODO: wire to generative model when credentials available.
    const template = {
      proposta: "# Proposta Comercial\n\n**Cliente:** {{cliente}}\n**Escopo:** {{escopo}}\n**Investimento:** {{valor}}\n\n---\n\n_Rascunho gerado automaticamente. Revise antes de enviar._",
      contrato: "# Contrato de Prestação de Serviços\n\n**CONTRATANTE:** {{contratante}}\n**CONTRATADA:** Orkestra.AI\n**Objeto:** {{objeto}}\n**Vigência:** {{vigencia}}\n\n---\n\n_Minuta padrão — não é aconselhamento jurídico._",
      "apresentacao-comercial": "# Apresentação Comercial\n\n1. Problema do cliente\n2. Solução Orkestra\n3. Resultados esperados\n4. Investimento e prazos\n5. Próximos passos",
      "brand-kit": "# Brand Kit básico\n\n- Paleta: preto + off-white + gold + emerald\n- Tipografia: Inter\n- Tom: técnico, direto, confiante\n- Logo: ver /vault/brand-kit/",
    }[body.kind];
    return reply.send({ success: true, data: { draft: template, context: body.context ?? null } });
  });
}
