import type { FastifyRequest, FastifyReply } from "fastify";
import { AppError } from "../utils/app-error";

// Rejects a request when the body/query/params name a different tenant
// than the one bound to the authenticated user. Admin bypasses cross-tenant
// guard only if an explicit `x-impersonate-tenant` header is set (internal use).
export async function enforceTenant(
  request: FastifyRequest,
  _reply: FastifyReply,
) {
  const user = request.user;
  if (!user) {
    throw new AppError("Unauthenticated", 401, "UNAUTHORIZED");
  }

  const candidates: string[] = [];
  const body = request.body as Record<string, unknown> | undefined;
  const query = request.query as Record<string, unknown> | undefined;
  const params = request.params as Record<string, unknown> | undefined;
  if (body && typeof body.tenantId === "string") candidates.push(body.tenantId);
  if (query && typeof query.tenantId === "string") candidates.push(query.tenantId);
  if (params && typeof params.tenantId === "string") candidates.push(params.tenantId);

  for (const t of candidates) {
    if (t !== user.tenantId) {
      if (user.role === "admin") {
        const impersonate = request.headers["x-impersonate-tenant"];
        if (typeof impersonate === "string" && impersonate === t) continue;
      }
      throw new AppError(
        "Cross-tenant access denied",
        403,
        "FORBIDDEN",
      );
    }
  }
}

// Canonical helper — always returns the authenticated tenantId. Use this
// instead of `body.tenantId ?? DEFAULT_TENANT` on write paths.
export function getTenantId(request: FastifyRequest): string {
  if (!request.user) {
    throw new AppError("Unauthenticated", 401, "UNAUTHORIZED");
  }
  return request.user.tenantId;
}
