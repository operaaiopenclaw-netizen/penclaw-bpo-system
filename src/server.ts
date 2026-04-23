import "dotenv/config";
import path from "node:path";
import { promises as fs } from "node:fs";
import Fastify from "fastify";
import cors from "@fastify/cors";
import helmet from "@fastify/helmet";
import fastifyStatic from "@fastify/static";
import swagger from "@fastify/swagger";
import swaggerUi from "@fastify/swagger-ui";
import { config } from "./config/env";
import { prisma } from "./db";
import { agentRunsRoutes, approvalsRoutes, memoryRoutes, artifactsRoutes, dashboardRoutes, metricsRoutes, eventsRoutes, statesRoutes, kitchenRoutes, intelligenceRoutes, crmRoutes, serviceOrdersRoutes, productionOrdersRoutes, executionRoutes, operationsRoutes, authRoutes, usersRoutes, commercialRoutes, aiChatRoutes, calendarRoutes, vaultRoutes, invoicesRoutes, whatsappRoutes, marketingRoutes, lgpdRoutes, hrRoutes, financeRoutes, onboardingRoutes, checklistsRoutes, integrationsRoutes } from "./routes";
import { findPublishedLP, incrementLPView } from "./routes/marketing";
import { registerAuditHook } from "./middleware/audit";
import { errorHandler, notFoundHandler } from "./utils/error-handler";
import { logger } from "./utils/logger";
import agentRunWorker, { closeWorker } from "./worker";
import { bootstrapSeedIfEmpty } from "./services/bootstrap-seed";

const BOOT_AT = new Date().toISOString();

export async function bootstrap() {
  const app = Fastify({
    logger: { level: config.LOG_LEVEL },
  });

  // Security — disable CSP because the bundled /ui/ dashboard ships inline
  // <script> blocks; enabling CSP with default rules would silently break them.
  // We keep all other helmet protections (HSTS, X-Content-Type-Options, etc).
  await app.register(helmet, { contentSecurityPolicy: false });
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

  // Static dashboard UI at /ui/* (index.html, login.html, operations.html, users.html).
  // cacheControl:false + setHeaders forces no-store so browsers always fetch the
  // latest HTML/JS — dashboard code lives inline so staleness = silent breakage.
  await app.register(fastifyStatic, {
    root: path.resolve(process.cwd(), "dashboard"),
    prefix: "/ui/",
    decorateReply: false,
    cacheControl: false,
    setHeaders: (res) => {
      res.setHeader("Cache-Control", "no-store, must-revalidate");
    },
  });

  // Friendly root — bounce to the public landing.
  // Auth-protected pages live under /ui/* and redirect to /ui/login.html themselves.
  app.get("/", async (_req, reply) => reply.redirect("/ui/landing.html", 302));
  app.get("/login", async (_req, reply) => reply.redirect("/ui/login.html", 302));

  // SEO files must live at root per convention — crawlers don't look under /ui/.
  const dashboardRoot = path.resolve(process.cwd(), "dashboard");
  app.get("/robots.txt", async (_req, reply) => {
    const buf = await fs.readFile(path.join(dashboardRoot, "robots.txt"));
    reply.type("text/plain").send(buf);
  });
  app.get("/sitemap.xml", async (_req, reply) => {
    const buf = await fs.readFile(path.join(dashboardRoot, "sitemap.xml"));
    reply.type("application/xml").send(buf);
  });

  // Public landing pages — generated via /marketing/landing-pages and served
  // at /lp/:slug when status=published. No auth. View counter bumped async.
  app.get<{ Params: { slug: string } }>("/lp/:slug", async (req, reply) => {
    const lp = await findPublishedLP(req.params.slug);
    if (!lp) return reply.status(404).type("text/html").send(
      `<!doctype html><meta charset="utf-8"><title>Não encontrada</title>
       <body style="font-family:system-ui;padding:60px;background:#0B0B0C;color:#F5F3EF">
       <h1>Landing page não encontrada</h1><p>Verifique o link ou fale com quem enviou.</p></body>`,
    );
    void incrementLPView(lp).catch(() => {});
    return reply.type("text/html").send(lp.html);
  });

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
  await app.register(commercialRoutes, { prefix: "/commercial" });
  await app.register(aiChatRoutes,     { prefix: "/ai-chat" });
  await app.register(calendarRoutes,   { prefix: "/calendar" });
  await app.register(vaultRoutes,      { prefix: "/vault" });
  await app.register(invoicesRoutes,   { prefix: "/invoices" });
  await app.register(whatsappRoutes,   { prefix: "/whatsapp" });
  await app.register(marketingRoutes,  { prefix: "/marketing" });
  await app.register(lgpdRoutes,       { prefix: "/lgpd" });
  await app.register(hrRoutes,         { prefix: "/hr" });
  await app.register(financeRoutes,    { prefix: "/finance" });
  await app.register(onboardingRoutes, { prefix: "/onboarding" });
  await app.register(checklistsRoutes, { prefix: "/checklists" });
  await app.register(integrationsRoutes, { prefix: "/integrations" });

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

  // Tests call bootstrap() and use app.inject() — they don't need a bound port.
  // Production enters via the `if (require.main === module)` block below.
  return app;
}

if (require.main === module) {
  bootstrap()
    .then(async (app) => {
      await app.listen({ port: config.PORT, host: "0.0.0.0" });
      app.log.info(`🚀 Server running at http://localhost:${config.PORT}`);
      app.log.info(`📚 Swagger UI: http://localhost:${config.PORT}/docs`);
    })
    .catch((err) => {
      console.error("Fatal error:", err);
      process.exit(1);
    });
}
