import { FastifyInstance } from "fastify";
import { config } from "../config/env";

const RATE_LIMIT_MAX = 100;
const RATE_LIMIT_WINDOW_MS = 15 * 60 * 1000; // 15 minutes

export async function setupRateLimiting(app: FastifyInstance) {
  await app.register(import("@fastify/rate-limit"), {
    max: RATE_LIMIT_MAX,
    timeWindow: RATE_LIMIT_WINDOW_MS,

    // Skip rate limiting in development
    skipOnError: config.isDev,

    // Custom error response
    errorResponseBuilder: (_req, context) => {
      const afterMs = typeof context.after === "number" ? context.after : parseInt(String(context.after), 10) || 60000;
      return {
        success: false,
        error: "RATE_LIMIT_EXCEEDED",
        message: `Rate limit exceeded. Try again in ${Math.ceil(afterMs / 1000)} seconds.`,
        retryAfter: Math.ceil(afterMs / 1000),
      };
    },

    // Different limits for different routes
    keyGenerator: (req) => {
      // Use user ID if authenticated, otherwise IP
      return (req as any).user?.id || req.ip;
    },

    // Custom rules
    allowList: [], // Add whitelisted IPs here
  });

  app.log.info({ max: RATE_LIMIT_MAX, window: RATE_LIMIT_WINDOW_MS }, "Rate limiting configured");
}
