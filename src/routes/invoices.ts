// ============================================================
// INVOICES / FATURAMENTO — NF-e + boleto scaffolding
// ============================================================
// Provider abstraction. Wire Asaas / Iugu / NFSe.io by setting
// BILLING_PROVIDER and API key. Mock provider is active by default
// so UI flows are exercisable immediately.

import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { z } from "zod";
import { promises as fs } from "node:fs";
import path from "node:path";
import { config } from "../config/env";
import { logger } from "../utils/logger";

const DEFAULT_TENANT = config.DEFAULT_TENANT_ID;
const STORE = path.resolve(process.cwd(), "vault", "_billing");

type InvoiceStatus = "draft" | "issued" | "paid" | "overdue" | "cancelled";

type Invoice = {
  id: string;
  tenantId: string;
  number: string;
  customerName: string;
  customerDocument?: string;
  customerEmail?: string;
  amount: number;
  description: string;
  issueDate: string;
  dueDate: string;
  status: InvoiceStatus;
  boletoUrl?: string;
  nfseUrl?: string;
  externalId?: string;
  provider: string;
  metadata?: Record<string, unknown>;
};

async function load(tenantId: string): Promise<Invoice[]> {
  try {
    const p = path.join(STORE, `${tenantId}.json`);
    return JSON.parse(await fs.readFile(p, "utf8")) as Invoice[];
  } catch {
    return [];
  }
}

async function save(tenantId: string, list: Invoice[]) {
  await fs.mkdir(STORE, { recursive: true });
  await fs.writeFile(path.join(STORE, `${tenantId}.json`), JSON.stringify(list, null, 2));
}

function newId() {
  return `inv_${Math.random().toString(36).slice(2, 10)}`;
}

function nextNumber(list: Invoice[]) {
  const nums = list.map((i) => parseInt(i.number)).filter((n) => !isNaN(n));
  const max = nums.length ? Math.max(...nums) : 0;
  return String(max + 1).padStart(6, "0");
}

// --- provider ----------------------------------------------------------

type Provider = {
  name: string;
  issueBoleto(i: Invoice): Promise<{ url: string; externalId: string }>;
  issueNfse(i: Invoice): Promise<{ url: string; externalId: string }>;
};

const MOCK_PROVIDER: Provider = {
  name: "mock",
  async issueBoleto(i) {
    return { url: `https://mock.billing/boleto/${i.id}.pdf`, externalId: `mock-${i.id}` };
  },
  async issueNfse(i) {
    return { url: `https://mock.billing/nfse/${i.id}.pdf`, externalId: `mock-${i.id}` };
  },
};

// TODO: AsaasProvider — requires ASAAS_API_KEY env
// TODO: IuguProvider — requires IUGU_API_KEY env
// TODO: NFSeIOProvider — requires NFSE_API_KEY + CNPJ config

function getProvider(): Provider {
  const chosen = (process.env.BILLING_PROVIDER ?? "mock").toLowerCase();
  if (chosen !== "mock") {
    logger.warn({ provider: chosen }, "billing provider not wired, falling back to mock");
  }
  return MOCK_PROVIDER;
}

// --- routes ------------------------------------------------------------

export async function invoicesRoutes(fastify: FastifyInstance): Promise<void> {
  fastify.get("/", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z
      .object({
        tenantId: z.string().default(DEFAULT_TENANT),
        status: z.string().optional(),
      })
      .parse(req.query);
    let list = await load(q.tenantId);
    if (q.status) list = list.filter((i) => i.status === q.status);
    return reply.send({
      success: true,
      data: list.sort((a, b) => b.issueDate.localeCompare(a.issueDate)),
      meta: { count: list.length, provider: getProvider().name },
    });
  });

  fastify.post("/", async (req: FastifyRequest<{ Body: unknown }>, reply: FastifyReply) => {
    const body = z
      .object({
        tenantId: z.string().default(DEFAULT_TENANT),
        customerName: z.string().min(1),
        customerDocument: z.string().optional(),
        customerEmail: z.string().email().optional(),
        amount: z.number().positive(),
        description: z.string().min(1),
        dueDate: z.string(),
      })
      .parse(req.body);

    const list = await load(body.tenantId);
    const provider = getProvider();

    const base: Invoice = {
      id: newId(),
      tenantId: body.tenantId,
      number: nextNumber(list),
      customerName: body.customerName,
      customerDocument: body.customerDocument,
      customerEmail: body.customerEmail,
      amount: body.amount,
      description: body.description,
      issueDate: new Date().toISOString(),
      dueDate: body.dueDate,
      status: "issued",
      provider: provider.name,
    };

    const boleto = await provider.issueBoleto(base);
    const nfse = await provider.issueNfse(base);

    const invoice: Invoice = {
      ...base,
      boletoUrl: boleto.url,
      nfseUrl: nfse.url,
      externalId: boleto.externalId,
    };
    list.push(invoice);
    await save(body.tenantId, list);
    logger.info({ invoiceId: invoice.id, provider: provider.name }, "invoice issued");
    return reply.status(201).send({ success: true, data: invoice });
  });

  fastify.patch("/:id/status", async (
    req: FastifyRequest<{ Params: { id: string }; Body: unknown; Querystring: unknown }>,
    reply: FastifyReply,
  ) => {
    const q = z.object({ tenantId: z.string().default(DEFAULT_TENANT) }).parse(req.query);
    const body = z.object({ status: z.enum(["draft", "issued", "paid", "overdue", "cancelled"]) }).parse(req.body);
    const list = await load(q.tenantId);
    const ix = list.findIndex((i) => i.id === req.params.id);
    if (ix < 0) return reply.status(404).send({ success: false, error: "Not found" });
    list[ix].status = body.status;
    await save(q.tenantId, list);
    return reply.send({ success: true, data: list[ix] });
  });

  fastify.get("/summary", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z.object({ tenantId: z.string().default(DEFAULT_TENANT) }).parse(req.query);
    const list = await load(q.tenantId);
    const byStatus = list.reduce<Record<string, { count: number; total: number }>>((acc, i) => {
      acc[i.status] ??= { count: 0, total: 0 };
      acc[i.status].count += 1;
      acc[i.status].total += i.amount;
      return acc;
    }, {});
    const total = list.reduce((s, i) => s + i.amount, 0);
    return reply.send({ success: true, data: { total, count: list.length, byStatus, provider: getProvider().name } });
  });
}
