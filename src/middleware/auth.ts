import { FastifyRequest, FastifyReply } from "fastify";
import jwt from "jsonwebtoken";
import { config } from "../config/env";
import { AppError } from "../utils/app-error";

export interface AuthUser {
  id: string;
  email: string;
  role: "admin" | "user" | "viewer";
  companyId?: string;
}

// Extend FastifyRequest
declare module "fastify" {
  interface FastifyRequest {
    user?: AuthUser;
  }
}

export async function authenticate(request: FastifyRequest, reply: FastifyReply) {
  const authHeader = request.headers.authorization;
  
  if (!authHeader) {
    throw new AppError("Authorization header required", 401, "UNAUTHORIZED");
  }
  
  const [type, token] = authHeader.split(" ");
  
  if (type !== "Bearer" || !token) {
    throw new AppError("Invalid authorization format", 401, "UNAUTHORIZED");
  }
  
  try {
    // Verify JWT (in production, use actual JWT secret)
    const decoded = jwt.verify(token, config.JWT_SECRET || "dev-secret") as AuthUser;
    request.user = decoded;
  } catch (error) {
    throw new AppError("Invalid or expired token", 401, "UNAUTHORIZED");
  }
}

export function requireRole(...roles: string[]) {
  return async (request: FastifyRequest, reply: FastifyReply) => {
    await authenticate(request, reply);
    
    if (!request.user || !roles.includes(request.user.role)) {
      throw new AppError("Insufficient permissions", 403, "FORBIDDEN");
    }
  };
}

// Development bypass
export async function devAuth(request: FastifyRequest, reply: FastifyReply) {
  if (config.isDev) {
    request.user = {
      id: "dev-user-123",
      email: "dev@local",
      role: "admin",
      companyId: "opera",
    };
    return;
  }
  
  await authenticate(request, reply);
}
