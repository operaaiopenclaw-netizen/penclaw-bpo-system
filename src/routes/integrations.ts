// ============================================================
// INTEGRATIONS — aggregated topology / health of external providers
// ============================================================
// Read-only endpoint. Inspects env vars + runtime probes to report
// which providers are wired, which are mocked, and which are missing.
// Feeds the /ui/integrations.html topology view.

import { FastifyInstance, FastifyReply } from "fastify";
import { prisma } from "../db";
import { agentRunQueue } from "../queue";

type Status = "wired" | "mock" | "missing" | "error";

type Integration = {
  id: string;
  name: string;
  category: "ai" | "ads" | "messaging" | "billing" | "banking" | "infra" | "calendar" | "notify";
  status: Status;
  detail: string;
  envVars: string[];
  port?: number;
};

function boolToStatus(ok: boolean, hasFallback = false): Status {
  if (ok) return "wired";
  return hasFallback ? "mock" : "missing";
}

async function probeDatabase(): Promise<{ status: Status; detail: string }> {
  try {
    const t0 = Date.now();
    await prisma.$queryRaw`SELECT 1`;
    return { status: "wired", detail: `conectado em ${Date.now() - t0}ms` };
  } catch (err) {
    return { status: "error", detail: err instanceof Error ? err.message : "erro desconhecido" };
  }
}

async function probeRedis(): Promise<{ status: Status; detail: string }> {
  try {
    const t0 = Date.now();
    const client = await agentRunQueue.client;
    const pong = await client.ping();
    if (pong !== "PONG") return { status: "error", detail: "ping inválido" };
    return { status: "wired", detail: `PONG em ${Date.now() - t0}ms` };
  } catch (err) {
    return { status: "error", detail: err instanceof Error ? err.message : "erro desconhecido" };
  }
}

export async function integrationsRoutes(fastify: FastifyInstance): Promise<void> {
  fastify.get("/", async (_req, reply: FastifyReply) => {
    const [dbProbe, redisProbe] = await Promise.all([probeDatabase(), probeRedis()]);

    const integrations: Integration[] = [
      // ── AI ──
      {
        id: "claude",
        name: "Claude (Anthropic)",
        category: "ai",
        status: boolToStatus(!!process.env.ANTHROPIC_API_KEY, true),
        detail: process.env.ANTHROPIC_API_KEY
          ? "Opus 4.7 · chat, briefs, copy, drafts"
          : "fallback determinístico em templates",
        envVars: ["ANTHROPIC_API_KEY"],
      },

      // ── Ads ──
      {
        id: "meta-ads",
        name: "Meta Ads",
        category: "ads",
        status: boolToStatus(!!process.env.META_SYSTEM_TOKEN, true),
        detail: "Campanhas FB/IG — UI real, disparo mock sem token",
        envVars: ["META_AD_ACCOUNT_ID", "META_SYSTEM_TOKEN"],
      },
      {
        id: "google-ads",
        name: "Google Ads",
        category: "ads",
        status: boolToStatus(!!process.env.GOOGLE_ADS_REFRESH_TOKEN, true),
        detail: "Search + Display — requer OAuth refresh token",
        envVars: ["GOOGLE_ADS_CUSTOMER_ID", "GOOGLE_ADS_REFRESH_TOKEN"],
      },

      // ── Messaging ──
      {
        id: "whatsapp",
        name: `WhatsApp (${process.env.WHATSAPP_PROVIDER ?? "mock"})`,
        category: "messaging",
        status: boolToStatus(
          !!(
            (process.env.WHATSAPP_PROVIDER === "twilio" &&
              process.env.TWILIO_ACCOUNT_SID &&
              process.env.TWILIO_AUTH_TOKEN) ||
            (process.env.WHATSAPP_PROVIDER === "evolution" &&
              process.env.EVOLUTION_URL &&
              process.env.EVOLUTION_KEY)
          ),
          true,
        ),
        detail:
          process.env.WHATSAPP_PROVIDER === "twilio"
            ? "Twilio Business"
            : process.env.WHATSAPP_PROVIDER === "evolution"
              ? "Evolution API (self-host)"
              : "mensagens logadas apenas — configure provider",
        envVars: ["WHATSAPP_PROVIDER", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "EVOLUTION_URL", "EVOLUTION_KEY"],
      },
      {
        id: "telegram",
        name: "Telegram",
        category: "messaging",
        status: boolToStatus(!!(process.env.TELEGRAM_BOT_TOKEN && process.env.TELEGRAM_CHAT_ID)),
        detail: "canal de alertas operacionais",
        envVars: ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"],
      },

      // ── Billing ──
      {
        id: "billing",
        name: `Faturamento (${process.env.BILLING_PROVIDER ?? "mock"})`,
        category: "billing",
        status: boolToStatus(
          !!(
            (process.env.BILLING_PROVIDER === "asaas" && process.env.ASAAS_API_KEY) ||
            (process.env.BILLING_PROVIDER === "iugu" && process.env.IUGU_API_KEY)
          ),
          true,
        ),
        detail:
          process.env.BILLING_PROVIDER === "asaas"
            ? "Asaas — boletos + NFSe"
            : process.env.BILLING_PROVIDER === "iugu"
              ? "Iugu — recorrência + PIX"
              : "URLs mock de boleto/NFSe",
        envVars: ["BILLING_PROVIDER", "ASAAS_API_KEY", "IUGU_API_KEY"],
      },

      // ── Banking / Open Finance ──
      {
        id: "pluggy",
        name: "Pluggy (Open Finance)",
        category: "banking",
        status: boolToStatus(!!(process.env.PLUGGY_CLIENT_ID && process.env.PLUGGY_CLIENT_SECRET), true),
        detail: "conciliação bancária automática",
        envVars: ["PLUGGY_CLIENT_ID", "PLUGGY_CLIENT_SECRET"],
      },

      // ── Infra ──
      {
        id: "postgres",
        name: "PostgreSQL",
        category: "infra",
        status: dbProbe.status,
        detail: dbProbe.detail,
        envVars: ["DATABASE_URL"],
      },
      {
        id: "redis",
        name: "Redis",
        category: "infra",
        status: redisProbe.status,
        detail: redisProbe.detail,
        envVars: ["REDIS_URL"],
      },

      // ── Calendar ──
      {
        id: "google-calendar",
        name: "Google Calendar",
        category: "calendar",
        status: boolToStatus(!!process.env.GOOGLE_CALENDAR_CREDENTIALS, true),
        detail: "sincronização de compromissos",
        envVars: ["GOOGLE_CALENDAR_CREDENTIALS"],
      },

      // ── Notifications ──
      {
        id: "webhook",
        name: "Webhook genérico",
        category: "notify",
        status: boolToStatus(!!process.env.WEBHOOK_URL),
        detail: "canal custom para eventos",
        envVars: ["WEBHOOK_URL", "WEBHOOK_AUTH"],
      },
    ];

    // Aggregates
    const totals = integrations.reduce(
      (acc, i) => {
        acc[i.status] = (acc[i.status] ?? 0) + 1;
        return acc;
      },
      {} as Record<Status, number>,
    );
    const health: "ok" | "degraded" | "down" =
      (totals.error ?? 0) > 0 ? "down" : (totals.missing ?? 0) > (totals.wired ?? 0) ? "degraded" : "ok";

    return reply.send({
      success: true,
      data: {
        health,
        totals: {
          wired: totals.wired ?? 0,
          mock: totals.mock ?? 0,
          missing: totals.missing ?? 0,
          error: totals.error ?? 0,
          total: integrations.length,
        },
        integrations,
      },
    });
  });
}
