import { FastifyInstance } from "fastify";
import { artifactController } from "../controllers/artifact-controller";

export async function artifactsRoutes(app: FastifyInstance) {
  // POST /artifacts/render
  app.post("/render", async (req, res) => artifactController.render(req, res));

  // GET /artifacts/:id
  app.get("/:id", async (req, res) => artifactController.getById(req as any, res));

  // GET /artifacts?agentRunId=...
  app.get("/", async (req, res) => artifactController.listByRun(req as any, res));
}
