import "dotenv/config";
import Fastify from "fastify";
import cors from "@fastify/cors";
import helmet from "@fastify/helmet";
import swagger from "@fastify/swagger";
import swaggerUi from "@fastify/swagger-ui";
import { config } from "./config/env";
import { prisma } from "./db";
import { agentRunsRoutes, approvalsRoutes, memoryRoutes, artifactsRoutes, dashboardRoutes, metricsRoutes, eventsRoutes, statesRoutes, kitchenRoutes, intelligenceRoutes, crmRoutes, serviceOrdersRoutes, productionOrdersRoutes, executionRoutes, operationsRoutes, authRoutes, usersRoutes } from "./routes";
import { registerAuditHook } from "./middleware/audit";
import { errorHandler, notFoundHandler } from "./utils/error-handler";
import { logger } from "./utils/logger";
import agentRunWorker, { closeWorker } from "./worker";
import { bootstrapSeedIfEmpty } from "./services/bootstrap-seed";

const BOOT_AT = new Date().toISOString();

async function bootstrap() {
  const app = Fastify({
    logger: { level: config.LOG_LEVEL },
  });

  // Security
  await app.register(helmet);
  await app.register(cors, { origin: config.corsOrigins });

  // API Documentation
  await app.register(swagger, {
    openapi: {
      info: {
        title: "Openclaw API",
        description: "Orkestra Finance Brain",
        version: "1.0.0",
      },
      servers: [{ url: `http://localhost:${config.PORT}` }],
    },
  });

  await app.register(swaggerUi, { routePrefix: "/docs" });

  // Audit hook (records every mutating request after response)
  registerAuditHook(app);

  // Routes
  await app.register(authRoutes, { prefix: "/auth" });
  await app.register(usersRoutes, { prefix: "/users" });
  await app.register(agentRunsRoutes, { prefix: "/agent-runs" });
  await app.register(approvalsRoutes, { prefix: "/approvals" });
  await app.register(memoryRoutes, { prefix: "/memory" });
  await app.register(artifactsRoutes, { prefix: "/artifacts" });
  await app.register(metricsRoutes, { prefix: "/metrics" });
  await app.register(dashboardRoutes, { prefix: "/dashboard" });
  await app.register(eventsRoutes, { prefix: "/events" });
  await app.register(statesRoutes, { prefix: "/states" });
  await app.register(kitchenRoutes, { prefix: "/kitchen" });
  await app.register(intelligenceRoutes, { prefix: "/intelligence" });
  await app.register(crmRoutes, { prefix: "/crm" });
  await app.register(serviceOrdersRoutes, { prefix: "/service-orders" });
  await app.register(productionOrdersRoutes, { prefix: "/production-orders" });
  await app.register(executionRoutes, { prefix: "/execution" });
  await app.register(operationsRoutes, { prefix: "/operations" });

  // Liveness — always 200 while process is up.
  app.get("/health", async () => ({ status: "ok", ts: Date.now() }));

  // Version — surfaces the deployed commit. Railway injects RAILWAY_GIT_*
  // automatically; falls back to "unknown" when running locally without git.
  app.get("/version", async () => ({
    sha: process.env.RAILWAY_GIT_COMMIT_SHA ?? process.env.GIT_SHA ?? "unknown",
    branch: process.env.RAILWAY_GIT_BRANCH ?? "unknown",
    deploymentId: process.env.RAILWAY_DEPLOYMENT_ID ?? null,
    environment: process.env.RAILWAY_ENVIRONMENT_NAME ?? process.env.NODE_ENV,
    bootAt: BOOT_AT,
  }));

  // Readiness — verifies DB + Redis reachable. Returns 503 if any fails.
  app.get("/ready", async (_req, reply) => {
    const checks: Record<string, { ok: boolean; error?: string; ms?: number }> = {};
    const t0 = Date.now();
    try {
      await prisma.$queryRaw`SELECT 1`;
      checks.database = { ok: true, ms: Date.now() - t0 };
    } catch (err) {
      checks.database = {
        ok: false,
        error: err instanceof Error ? err.message : String(err),
      };
    }

    const t1 = Date.now();
    try {
      const { agentRunQueue } = await import("./queue");
      const client = await agentRunQueue.client;
      const pong = await client.ping();
      checks.redis = { ok: pong === "PONG", ms: Date.now() - t1 };
    } catch (err) {
      checks.redis = {
        ok: false,
        error: err instanceof Error ? err.message : String(err),
      };
    }

    const ok = Object.values(checks).every((c) => c.ok);
    return reply.status(ok ? 200 : 503).send({ ok, checks, ts: Date.now() });
  });

  // Error handlers
  app.setErrorHandler(errorHandler);
  app.setNotFoundHandler(notFoundHandler);

  // First-boot seed (no-op when users already exist)
  await bootstrapSeedIfEmpty();

  // Worker
  logger.info("Starting agent run worker...");
  void agentRunWorker;

  // Graceful shutdown
  process.on("SIGINT", async () => {
    await app.close();
    await closeWorker();
    await prisma.$disconnect();
    process.exit(0);
  });

  await app.listen({ port: config.PORT, host: "0.0.0.0" });

  app.log.info(`🚀 Server running at http://localhost:${config.PORT}`);
  app.log.info(`📚 Swagger UI: http://localhost:${config.PORT}/docs`);
}

bootstrap().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
