import { FastifyInstance } from "fastify";
import { ArtifactController } from "../controllers/artifact-controller";

const controller = new ArtifactController();

export async function artifactsRoutes(app: FastifyInstance) {
  app.post("/render", controller.render);
}
