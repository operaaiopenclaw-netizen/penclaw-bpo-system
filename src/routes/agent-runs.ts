import { FastifyInstance } from "fastify";
import { agentRunController } from "../controllers/agent-run-controller";

export async function agentRunsRoutes(app: FastifyInstance) {
  // POST /agent-runs
  app.post("/", async (req, res) => agentRunController.create(req, res));

  // GET /agent-runs (list)
  app.get("/", async (req, res) => agentRunController.list(req, res));

  // GET /agent-runs/:id
  app.get("/:id", async (req, res) => agentRunController.getById(req as any, res));
}
