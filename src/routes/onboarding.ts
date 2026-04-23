// ============================================================
// ONBOARDING — pós-assinatura do contrato
// ============================================================
// Dispara 3 trilhas paralelas para cada cliente recém-contratado:
//   ADM         — cadastro, docs, acessos, responsáveis
//   Financeiro  — faturamento, comissão plan, provisão
//   Operações   — evento/OS, equipe, kickoff
//
// Persistência: JSON em ./vault/{tenantId}/onboarding/cases.json
// (mesmo padrão do vault; production deveria migrar para Prisma).

import { FastifyInstance } from "fastify";
import { z } from "zod";
import { promises as fs } from "node:fs";
import path from "node:path";
import { config } from "../config/env";
import { authenticate } from "../middleware/auth";
import { AppError } from "../utils/app-error";

const DEFAULT_TENANT = config.DEFAULT_TENANT_ID;
const ROOT = path.resolve(process.cwd(), "vault");

type StepStatus = "pending" | "in_progress" | "done";
type Track = "adm" | "finance" | "ops";

type Step = {
  id: string;
  label: string;
  status: StepStatus;
  note?: string;
  completedAt?: string;
  completedBy?: string;
};

type OnboardingCase = {
  id: string;
  tenantId: string;
  contractId?: string;
  clientName: string;
  createdAt: string;
  createdBy?: string;
  status: "open" | "in_progress" | "completed";
  tracks: Record<Track, Step[]>;
};

// Checklist padrão — pode ser customizado por tenant no futuro.
const TEMPLATE: Record<Track, string[]> = {
  adm: [
    "Cadastro do cliente no sistema",
    "Coleta de documentos (CNPJ, contrato social, procuração)",
    "Setup de acesso ao portal do cliente",
    "Designação de gerente de conta responsável",
  ],
  finance: [
    "Emissão do primeiro boleto / NFSe",
    "Configuração do commission plan no contrato",
    "Provisão de comissão criada no DRE",
    "Conciliação bancária habilitada para o contrato",
  ],
  ops: [
    "Criação do evento ou ordem de serviço inicial",
    "Alocação da equipe operacional",
    "Briefing e kickoff agendado",
    "Calendário compartilhado com o cliente",
  ],
};

function caseFilePath(tenantId: string): string {
  return path.join(ROOT, tenantId, "onboarding", "cases.json");
}

async function loadCases(tenantId: string): Promise<OnboardingCase[]> {
  try {
    const raw = await fs.readFile(caseFilePath(tenantId), "utf8");
    return JSON.parse(raw) as OnboardingCase[];
  } catch {
    return [];
  }
}

async function saveCases(tenantId: string, cases: OnboardingCase[]): Promise<void> {
  const dir = path.dirname(caseFilePath(tenantId));
  await fs.mkdir(dir, { recursive: true });
  await fs.writeFile(caseFilePath(tenantId), JSON.stringify(cases, null, 2));
}

function buildTracks(): Record<Track, Step[]> {
  const make = (labels: string[]): Step[] =>
    labels.map((label, i) => ({
      id: `s_${Math.random().toString(36).slice(2, 8)}_${i}`,
      label,
      status: "pending" as const,
    }));
  return {
    adm: make(TEMPLATE.adm),
    finance: make(TEMPLATE.finance),
    ops: make(TEMPLATE.ops),
  };
}

function rollupStatus(c: OnboardingCase): "open" | "in_progress" | "completed" {
  const all = [...c.tracks.adm, ...c.tracks.finance, ...c.tracks.ops];
  if (all.every((s) => s.status === "done")) return "completed";
  if (all.some((s) => s.status !== "pending")) return "in_progress";
  return "open";
}

export async function onboardingRoutes(app: FastifyInstance): Promise<void> {
  app.addHook("preHandler", authenticate);

  // List all cases for the tenant.
  app.get<{ Querystring: { status?: string } }>("/cases", async (req) => {
    const tenantId = req.user?.tenantId ?? DEFAULT_TENANT;
    const cases = await loadCases(tenantId);
    const filtered = req.query.status
      ? cases.filter((c) => c.status === req.query.status)
      : cases;
    return { cases: filtered };
  });

  // Detail.
  app.get<{ Params: { id: string } }>("/cases/:id", async (req) => {
    const tenantId = req.user?.tenantId ?? DEFAULT_TENANT;
    const cases = await loadCases(tenantId);
    const found = cases.find((c) => c.id === req.params.id);
    if (!found) throw new AppError("Case not found", 404, "NOT_FOUND");
    return found;
  });

  // Create a new onboarding case (manually or triggered post-signature).
  app.post<{ Body: unknown }>("/cases", async (req, reply) => {
    const schema = z.object({
      clientName: z.string().min(1),
      contractId: z.string().uuid().optional(),
    });
    const parsed = schema.safeParse(req.body);
    if (!parsed.success) throw new AppError("Invalid payload", 400, "VALIDATION");

    const tenantId = req.user?.tenantId ?? DEFAULT_TENANT;
    const cases = await loadCases(tenantId);

    const newCase: OnboardingCase = {
      id: `onb_${Math.random().toString(36).slice(2, 10)}`,
      tenantId,
      contractId: parsed.data.contractId,
      clientName: parsed.data.clientName,
      createdAt: new Date().toISOString(),
      createdBy: req.user?.id,
      status: "open",
      tracks: buildTracks(),
    };

    cases.unshift(newCase);
    await saveCases(tenantId, cases);
    return reply.status(201).send(newCase);
  });

  // Update a step (mark in_progress, done, add note).
  app.patch<{
    Params: { id: string; track: Track; stepId: string };
    Body: unknown;
  }>("/cases/:id/tracks/:track/steps/:stepId", async (req, reply) => {
    const schema = z.object({
      status: z.enum(["pending", "in_progress", "done"]),
      note: z.string().optional(),
    });
    const parsed = schema.safeParse(req.body);
    if (!parsed.success) throw new AppError("Invalid payload", 400, "VALIDATION");

    const { id, track, stepId } = req.params;
    if (!["adm", "finance", "ops"].includes(track)) {
      throw new AppError("Invalid track", 400, "VALIDATION");
    }

    const tenantId = req.user?.tenantId ?? DEFAULT_TENANT;
    const cases = await loadCases(tenantId);
    const caseIdx = cases.findIndex((c) => c.id === id);
    if (caseIdx === -1) throw new AppError("Case not found", 404, "NOT_FOUND");

    const target = cases[caseIdx];
    const step = target.tracks[track].find((s) => s.id === stepId);
    if (!step) throw new AppError("Step not found", 404, "NOT_FOUND");

    step.status = parsed.data.status;
    step.note = parsed.data.note ?? step.note;
    if (parsed.data.status === "done") {
      step.completedAt = new Date().toISOString();
      step.completedBy = req.user?.id;
    }
    target.status = rollupStatus(target);

    await saveCases(tenantId, cases);
    return reply.send(target);
  });

  // Summary for the Onboarding dashboard.
  app.get("/summary", async (req) => {
    const tenantId = req.user?.tenantId ?? DEFAULT_TENANT;
    const cases = await loadCases(tenantId);

    const byStatus = { open: 0, in_progress: 0, completed: 0 };
    const byTrack: Record<Track, { pending: number; in_progress: number; done: number }> = {
      adm: { pending: 0, in_progress: 0, done: 0 },
      finance: { pending: 0, in_progress: 0, done: 0 },
      ops: { pending: 0, in_progress: 0, done: 0 },
    };

    for (const c of cases) {
      byStatus[c.status] += 1;
      for (const t of ["adm", "finance", "ops"] as Track[]) {
        for (const s of c.tracks[t]) {
          byTrack[t][s.status] += 1;
        }
      }
    }

    return { total: cases.length, byStatus, byTrack };
  });
}
