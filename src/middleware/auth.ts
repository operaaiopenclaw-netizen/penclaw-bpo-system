import { FastifyRequest, FastifyReply } from "fastify";
import jwt from "jsonwebtoken";
import { config } from "../config/env";
import { AppError } from "../utils/app-error";

export type Role = "operator" | "manager" | "finance" | "kitchen" | "admin";

export const ROLES: readonly Role[] = [
  "operator",
  "manager",
  "finance",
  "kitchen",
  "admin",
] as const;

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: Role;
  tenantId: string;
}

export interface JwtPayload extends AuthUser {
  iat?: number;
  exp?: number;
}

declare module "fastify" {
  interface FastifyRequest {
    user?: AuthUser;
  }
}

function isRole(value: unknown): value is Role {
  return typeof value === "string" && (ROLES as readonly string[]).includes(value);
}

export async function authenticate(request: FastifyRequest, _reply: FastifyReply) {
  const authHeader = request.headers.authorization;

  if (!authHeader) {
    throw new AppError("Authorization header required", 401, "UNAUTHORIZED");
  }

  const [type, token] = authHeader.split(" ");

  if (type !== "Bearer" || !token) {
    throw new AppError("Invalid authorization format", 401, "UNAUTHORIZED");
  }

  try {
    const decoded = jwt.verify(token, config.JWT_SECRET) as JwtPayload;
    if (!decoded.id || !decoded.tenantId || !isRole(decoded.role)) {
      throw new Error("Malformed token payload");
    }
    request.user = {
      id: decoded.id,
      email: decoded.email,
      name: decoded.name,
      role: decoded.role,
      tenantId: decoded.tenantId,
    };
  } catch (_err) {
    throw new AppError("Invalid or expired token", 401, "UNAUTHORIZED");
  }
}

export function requireRole(...roles: Role[]) {
  return async (request: FastifyRequest, reply: FastifyReply) => {
    if (!request.user) {
      await authenticate(request, reply);
    }
    if (!request.user || !roles.includes(request.user.role)) {
      throw new AppError("Insufficient permissions", 403, "FORBIDDEN");
    }
  };
}

// ------------------------------------------------------------
// Permission matrix (see DEPLOYMENT_PLAN_v1.md section 2.2)
// ------------------------------------------------------------
export const PERMISSIONS = {
  "operations.overview.read":     ["operator", "manager", "finance", "kitchen", "admin"] as Role[],
  "operations.risks.read":        ["operator", "manager", "finance", "kitchen", "admin"] as Role[],
  "operations.event.write":       ["manager", "admin"] as Role[],
  "operations.consumption.write": ["operator", "manager", "kitchen", "admin"] as Role[],
  "operations.production.write":  ["manager", "kitchen", "admin"] as Role[],
  "operations.reconcile.execute": ["manager", "finance", "admin"] as Role[],
  "operations.alerts.evaluate":   ["manager", "finance", "admin"] as Role[],
  "approvals.low.approve":        ["manager", "finance", "admin"] as Role[],
  "approvals.high.approve":       ["finance", "admin"] as Role[],
  "intelligence.read":            ["manager", "finance", "admin"] as Role[],
  "intelligence.execute":         ["manager", "finance", "admin"] as Role[],
  "users.manage":                 ["admin"] as Role[],
  "channels.manage":              ["admin"] as Role[],
} as const;

export type Permission = keyof typeof PERMISSIONS;

export function hasPermission(role: Role, permission: Permission): boolean {
  return (PERMISSIONS[permission] as readonly Role[]).includes(role);
}

export function requirePermission(permission: Permission) {
  return async (request: FastifyRequest, reply: FastifyReply) => {
    if (!request.user) {
      await authenticate(request, reply);
    }
    if (!request.user || !hasPermission(request.user.role, permission)) {
      throw new AppError(
        `Missing permission: ${permission}`,
        403,
        "FORBIDDEN",
      );
    }
  };
}

// ------------------------------------------------------------
// Dev bypass — NEVER bypasses in production. A real JWT always wins
// over the dev fallback, even in dev mode, so role-based tests work.
// ------------------------------------------------------------
export async function devAuth(request: FastifyRequest, reply: FastifyReply) {
  const hasToken = Boolean(request.headers.authorization);
  if (hasToken) {
    await authenticate(request, reply);
    return;
  }
  if (config.isDev) {
    request.user = {
      id: "dev-user",
      email: "dev@local",
      name: "Dev Admin",
      role: "admin",
      tenantId: config.DEFAULT_TENANT_ID,
    };
    return;
  }
  await authenticate(request, reply);
}
