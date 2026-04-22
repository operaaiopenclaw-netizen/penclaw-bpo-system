import type { FastifyInstance, FastifyReply, FastifyRequest } from "fastify";
import { prisma } from "../db";
import { logger } from "../utils/logger";

const MUTATING = new Set(["POST", "PUT", "PATCH", "DELETE"]);

const SKIP_PATHS = [
  "/health",
  "/docs",
  "/metrics",
  "/auth/login",
];

function shouldSkip(path: string): boolean {
  return SKIP_PATHS.some((p) => path === p || path.startsWith(`${p}/`));
}

function extractResource(path: string): { resource: string; resourceId: string | null } {
  const parts = path.split("/").filter(Boolean);
  const resource = parts[0] ?? "unknown";
  const resourceId = parts[1] && parts[1].length > 8 ? parts[1] : null;
  return { resource, resourceId };
}

function redactPayload(body: unknown): unknown {
  if (!body || typeof body !== "object") return body;
  const clone: Record<string, unknown> = { ...(body as Record<string, unknown>) };
  for (const k of Object.keys(clone)) {
    const lower = k.toLowerCase();
    if (lower.includes("password") || lower.includes("secret") || lower.includes("token")) {
      clone[k] = "[REDACTED]";
    }
  }
  return clone;
}

export function registerAuditHook(app: FastifyInstance) {
  app.addHook("onResponse", async (request: FastifyRequest, reply: FastifyReply) => {
    try {
      if (!MUTATING.has(request.method)) return;
      if (shouldSkip(request.url)) return;

      const user = request.user;
      const tenantId = user?.tenantId ?? "anonymous";
      const { resource, resourceId } = extractResource(request.url);

      await prisma.auditLog.create({
        data: {
          tenantId,
          userId: user?.id ?? null,
          userEmail: user?.email ?? null,
          role: user?.role ?? null,
          action: request.method.toLowerCase(),
          resource,
          resourceId,
          method: request.method,
          path: request.url,
          statusCode: reply.statusCode,
          payload: redactPayload(request.body) as any,
          ip: request.ip,
          userAgent: request.headers["user-agent"] ?? null,
        },
      });
    } catch (err) {
      logger.warn({ err }, "audit log write failed");
    }
  });
}
