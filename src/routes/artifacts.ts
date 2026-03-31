import { FastifyInstance } from "fastify";
import { ArtifactController } from "../controllers/artifact-controller";

const controller = new ArtifactController();

export async function artifactRoutes(app: FastifyInstance) {
  app.post("/artifacts/render", controller.render);
}
