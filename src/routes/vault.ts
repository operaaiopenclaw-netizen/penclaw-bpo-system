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
import { analyzeWithClaude, isClaudeAvailable } from "../services/claude-client";

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

  // AI-assisted draft generator. Uses Claude when ANTHROPIC_API_KEY is set;
  // falls back to deterministic templates otherwise so the endpoint always
  // works even without credentials (e.g. in CI or during local bring-up).
  fastify.post("/generate", async (req: FastifyRequest<{ Body: unknown }>, reply: FastifyReply) => {
    const body = z
      .object({
        kind: z.enum(["proposta", "contrato", "apresentacao-comercial", "brand-kit"]),
        context: z.string().max(4000).optional(),
      })
      .parse(req.body);

    const templates: Record<typeof body.kind, string> = {
      proposta:
        "# Proposta Comercial\n\n**Cliente:** {{cliente}}\n**Escopo:** {{escopo}}\n**Investimento:** {{valor}}\n\n---\n\n_Rascunho — revise antes de enviar._",
      contrato:
        "# Contrato de Prestação de Serviços\n\n**CONTRATANTE:** {{contratante}}\n**CONTRATADA:** Orkestra.AI\n**Objeto:** {{objeto}}\n**Vigência:** {{vigencia}}\n\n---\n\n_Minuta padrão — não é aconselhamento jurídico._",
      "apresentacao-comercial":
        "# Apresentação Comercial\n\n1. Problema do cliente\n2. Solução Orkestra\n3. Resultados esperados\n4. Investimento e prazos\n5. Próximos passos",
      "brand-kit":
        "# Brand Kit básico\n\n- Paleta: preto + off-white + gold + emerald\n- Tipografia: Inter\n- Tom: técnico, direto, confiante\n- Logo: ver /vault/brand-kit/",
    };

    if (!isClaudeAvailable()) {
      return reply.send({ success: true, data: { draft: templates[body.kind], provider: "template" } });
    }

    const systemByKind: Record<typeof body.kind, string> = {
      proposta: `Você é consultor comercial sênior da Orkestra.AI, BPO para eventos e agências no Brasil. Escreva uma proposta comercial em Markdown, em português, objetiva, sem exageros. Seções: Contexto do cliente, Escopo proposto, Cronograma, Investimento (estimativa em faixas R$), Próximos passos. Tom técnico e direto. Nunca use emojis. Nunca prometa resultado numérico garantido.`,
      contrato: `Você é redator contratual da Orkestra.AI. Produza uma minuta de contrato de prestação de serviços em Markdown, em português, clara e objetiva, com cláusulas: Objeto, Obrigações da contratada, Obrigações da contratante, Remuneração, Vigência, Rescisão, Confidencialidade, LGPD, Foro. Use placeholders {{nome}}, {{CNPJ}}, {{valor}}, {{vigencia}} onde os dados não vierem do contexto. Sempre termine com: "_Minuta padrão — não substitui validação jurídica._"`,
      "apresentacao-comercial": `Você é copywriter sênior da Orkestra.AI. Gere um roteiro de apresentação comercial em Markdown, em português, com 5 a 7 seções numeradas, cada uma com título curto e 2-4 bullets. Tom técnico e confiante. Nunca use emojis. Foque no problema do cliente e nos ganhos mensuráveis.`,
      "brand-kit": `Você é brand strategist. Gere um brand-kit resumido em Markdown, em português: Paleta (com hex), Tipografia, Tom de voz (3-5 adjetivos), Do's e Don'ts (3 cada), Aplicações mínimas. Use o tom Orkestra como referência se não houver contexto específico: preto + off-white + gold (#C9A961) + emerald (#00B38A), Inter, tom técnico-direto. Nunca use emojis.`,
    };

    const userContent = body.context?.trim()
      ? `Contexto fornecido pelo usuário:\n${body.context}\n\nGere o documento agora.`
      : `Sem contexto adicional — gere um template reutilizável com placeholders {{campo}} onde dados específicos do cliente seriam inseridos.`;

    try {
      const res = await analyzeWithClaude({
        systemPrompt: systemByKind[body.kind],
        userContent,
        maxTokens: 2000,
      });
      return reply.send({
        success: true,
        data: {
          draft: res.text,
          provider: "claude",
          tokens: { input: res.inputTokens, output: res.outputTokens, cached: res.cached ?? false },
        },
      });
    } catch (err) {
      logger.warn(
        { err: err instanceof Error ? err.message : String(err), kind: body.kind },
        "vault/generate: Claude call failed, returning template fallback",
      );
      return reply.send({
        success: true,
        data: { draft: templates[body.kind], provider: "template-fallback" },
      });
    }
  });
}
