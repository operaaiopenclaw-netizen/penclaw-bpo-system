import "dotenv/config";
import Fastify from "fastify";
import cors from "@fastify/cors";
import helmet from "@fastify/helmet";
import swagger from "@fastify/swagger";
import swaggerUi from "@fastify/swagger-ui";
import { config } from "./config/env";
import { prisma } from "./db";
import { agentRunsRoutes, approvalsRoutes, memoryRoutes, artifactsRoutes, dashboardRoutes, metricsRoutes, eventsRoutes, statesRoutes, kitchenRoutes, intelligenceRoutes, crmRoutes, serviceOrdersRoutes, productionOrdersRoutes, executionRoutes } from "./routes";
import { errorHandler, notFoundHandler } from "./utils/error-handler";
import { logger } from "./utils/logger";
import agentRunWorker, { closeWorker } from "./worker";

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

  // Routes
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

  // Health check
  app.get("/health", async () => ({ status: "ok", ts: Date.now() }));

  // Error handlers
  app.setErrorHandler(errorHandler);
  app.setNotFoundHandler(notFoundHandler);

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
