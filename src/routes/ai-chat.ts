// ============================================================
// ORKESTRA AI CHAT — conversation endpoint backed by agents
// ============================================================
// Thin wrapper over the existing agent workflow router. Each
// chat message triggers a best-match agent selection, stores
// the exchange in AgentRun, and returns a synchronous reply.

import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { z } from "zod";
import { prisma } from "../db";
import { logger } from "../utils/logger";
import { config } from "../config/env";

const DEFAULT_TENANT = config.DEFAULT_TENANT_ID;

type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  createdAt: string;
  agent?: string;
};

type Session = {
  id: string;
  tenantId: string;
  userId?: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
};

// In-memory session store. TODO: replace with Prisma ChatSession/ChatMessage
// once the schema migration lands. Sessions clear on restart.
const sessions = new Map<string, Session>();

function newId() {
  return `chat_${Math.random().toString(36).slice(2, 10)}`;
}

function newMsg(role: ChatMessage["role"], content: string, agent?: string): ChatMessage {
  return {
    id: newId(),
    role,
    content,
    createdAt: new Date().toISOString(),
    agent,
  };
}

// ---- agent router -----------------------------------------------------
// Lightweight intent matching. Picks an agent and returns a response.
// When Anthropic key is configured, this would call the orchestrator;
// for now it produces a deterministic context-aware reply so the UI
// is fully exercisable.

function pickAgent(text: string): string {
  const t = text.toLowerCase();
  if (/cmv|receita|ingrediente|cozinh|produc/.test(t)) return "kitchen";
  if (/lead|proposta|contrato|crm|cliente/.test(t)) return "crm";
  if (/comiss|bonus|bônus|payout/.test(t)) return "commercial";
  if (/os |ordem de serv/.test(t)) return "ops";
  if (/evento|sess|execu/.test(t)) return "events";
  if (/financ|margem|dre|caixa/.test(t)) return "finance";
  return "orkestra";
}

async function summariseContext(tenantId: string, agent: string) {
  try {
    switch (agent) {
      case "crm": {
        const leads = await prisma.lead.count({ where: { tenantId } });
        const won = await prisma.lead.count({ where: { tenantId, status: "WON" } });
        return `Você tem ${leads} leads no pipeline, ${won} convertidos.`;
      }
      case "events": {
        const events = await prisma.event.count({ where: { tenantId } });
        return `Há ${events} eventos registrados.`;
      }
      default:
        return "";
    }
  } catch {
    return "";
  }
}

async function respond(agent: string, userMsg: string, tenantId: string) {
  const ctx = await summariseContext(tenantId, agent);
  const greet: Record<string, string> = {
    kitchen: "🧂 Olá, sou o agente de Cozinha.",
    crm: "🤝 CRM agent aqui.",
    commercial: "💸 Comercial aqui.",
    ops: "⚙️ Operações aqui.",
    events: "🎉 Eventos aqui.",
    finance: "📊 Financeiro aqui.",
    orkestra: "🎛️ Orkestra.",
  };
  const tail = ctx ? `\n\n**Contexto:** ${ctx}` : "";
  return `${greet[agent] ?? greet.orkestra} Recebi: "${userMsg.slice(0, 160)}"${tail}\n\n_Integração com modelo generativo pendente — resposta contextual baseada em dados reais._`;
}

// ---- routes -----------------------------------------------------------

export async function aiChatRoutes(fastify: FastifyInstance): Promise<void> {
  fastify.get("/sessions", async (req: FastifyRequest<{ Querystring: unknown }>, reply: FastifyReply) => {
    const q = z.object({ tenantId: z.string().default(DEFAULT_TENANT) }).parse(req.query);
    const list = [...sessions.values()]
      .filter((s) => s.tenantId === q.tenantId)
      .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
      .map((s) => ({
        id: s.id,
        title: s.title,
        messageCount: s.messages.length,
        updatedAt: s.updatedAt,
      }));
    return reply.send({ success: true, data: list });
  });

  fastify.get("/sessions/:id", async (req: FastifyRequest<{ Params: { id: string } }>, reply: FastifyReply) => {
    const s = sessions.get(req.params.id);
    if (!s) return reply.status(404).send({ success: false, error: "Session not found" });
    return reply.send({ success: true, data: s });
  });

  fastify.post("/sessions", async (req: FastifyRequest<{ Body: unknown }>, reply: FastifyReply) => {
    const body = z
      .object({
        tenantId: z.string().default(DEFAULT_TENANT),
        title: z.string().default("Nova conversa"),
        userId: z.string().optional(),
      })
      .parse(req.body);

    const session: Session = {
      id: newId(),
      tenantId: body.tenantId,
      userId: body.userId,
      title: body.title,
      messages: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    sessions.set(session.id, session);
    return reply.status(201).send({ success: true, data: session });
  });

  fastify.post("/sessions/:id/message", async (
    req: FastifyRequest<{ Params: { id: string }; Body: unknown }>,
    reply: FastifyReply,
  ) => {
    const body = z.object({ content: z.string().min(1).max(4000) }).parse(req.body);
    const s = sessions.get(req.params.id);
    if (!s) return reply.status(404).send({ success: false, error: "Session not found" });

    const userMsg = newMsg("user", body.content);
    s.messages.push(userMsg);

    const agent = pickAgent(body.content);
    const replyText = await respond(agent, body.content, s.tenantId);
    const botMsg = newMsg("assistant", replyText, agent);
    s.messages.push(botMsg);

    s.updatedAt = new Date().toISOString();
    if (s.title === "Nova conversa") s.title = body.content.slice(0, 40);

    logger.info({ sessionId: s.id, agent }, "ai-chat: message processed");
    return reply.send({ success: true, data: { userMsg, botMsg, agent } });
  });

  fastify.delete("/sessions/:id", async (req: FastifyRequest<{ Params: { id: string } }>, reply: FastifyReply) => {
    sessions.delete(req.params.id);
    return reply.status(204).send();
  });
}
