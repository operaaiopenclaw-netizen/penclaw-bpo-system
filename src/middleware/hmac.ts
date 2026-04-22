import crypto from "crypto";
import type { FastifyRequest, FastifyReply } from "fastify";
import { config } from "../config/env";
import { AppError } from "../utils/app-error";
import type { AuthUser } from "./auth";

const HEADER = "x-orkestra-signature";

function computeSignature(secret: string, rawBody: string): string {
  return crypto.createHmac("sha256", secret).update(rawBody).digest("hex");
}

function timingSafeEqualHex(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  try {
    return crypto.timingSafeEqual(Buffer.from(a, "hex"), Buffer.from(b, "hex"));
  } catch {
    return false;
  }
}

// Verify X-Orkestra-Signature header against HMAC-SHA256 of the raw body.
// In dev, absence of WEBHOOK_HMAC_SECRET is permitted (signature check skipped).
// In prod, absence of the secret fails closed.
export async function verifyHmac(
  request: FastifyRequest,
  _reply: FastifyReply,
) {
  const secret = config.WEBHOOK_HMAC_SECRET;

  if (!secret) {
    if (config.isProd) {
      throw new AppError(
        "WEBHOOK_HMAC_SECRET not configured",
        500,
        "CONFIG_ERROR",
      );
    }
    return; // dev/test: skip
  }

  const provided = request.headers[HEADER];
  if (typeof provided !== "string") {
    throw new AppError("Missing signature header", 401, "UNAUTHORIZED");
  }

  const raw =
    typeof request.body === "string"
      ? request.body
      : JSON.stringify(request.body ?? {});
  const expected = computeSignature(secret, raw);

  if (!timingSafeEqualHex(provided, expected)) {
    throw new AppError("Invalid signature", 401, "UNAUTHORIZED");
  }
}

export function signPayload(payload: unknown): string {
  const secret = config.WEBHOOK_HMAC_SECRET;
  if (!secret) throw new Error("WEBHOOK_HMAC_SECRET missing");
  const raw = typeof payload === "string" ? payload : JSON.stringify(payload);
  return computeSignature(secret, raw);
}

// Replaces devAuth for inbound webhooks. Verifies HMAC then synthesizes
// a `system` user bound to the tenant named in the payload (or the default
// tenant in dev). Used only by /operations/webhooks/*.
export function webhookAuth(role: AuthUser["role"] = "manager") {
  return async (request: FastifyRequest, reply: FastifyReply) => {
    await verifyHmac(request, reply);
    const body = (request.body ?? {}) as Record<string, unknown>;
    const tenantFromBody =
      typeof body.tenantId === "string" ? body.tenantId : null;
    const tenantId = tenantFromBody ?? config.DEFAULT_TENANT_ID;
    request.user = {
      id: "system-webhook",
      email: "system@orkestra",
      name: "Webhook System",
      role,
      tenantId,
    };
  };
}
