import { FastifyInstance } from "fastify";
import { metricsController } from "../controllers/metrics-controller";

export async function metricsRoutes(app: FastifyInstance) {
  // GET /metrics - Visão geral
  app.get("/", async (req, res) => metricsController.getAll(req, res));

  // GET /metrics/runs
  app.get("/runs", async (req, res) => metricsController.getRuns(req, res));

  // GET /metrics/steps
  app.get("/steps", async (req, res) => metricsController.getSteps(req, res));

  // GET /metrics/health
  app.get("/health", async (req, res) => metricsController.getHealth(req, res));
}
