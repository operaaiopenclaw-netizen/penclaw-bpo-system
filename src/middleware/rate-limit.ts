import { FastifyInstance } from "fastify";
import { config } from "../config/env";

export async function setupRateLimiting(app: FastifyInstance) {
  await app.register(import("@fastify/rate-limit"), {
    max: config.RATE_LIMIT_MAX || 100,
    timeWindow: config.RATE_LIMIT_WINDOW_MS || 15 * 60 * 1000, // 15 minutes
    
    // Skip rate limiting in development
    skipOnError: config.isDev,
    
    // Custom error response
    errorResponseBuilder: (req, context) => {
      return {
        success: false,
        error: "RATE_LIMIT_EXCEEDED",
        message: `Rate limit exceeded. Try again in ${Math.ceil(context.after / 1000)} seconds.`,
        retryAfter: Math.ceil(context.after / 1000),
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
  
  app.log.info("Rate limiting configured", {
    max: config.RATE_LIMIT_MAX || 100,
    window: config.RATE_LIMIT_WINDOW_MS || 900000,
  });
}
