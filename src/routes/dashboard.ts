import { FastifyInstance } from "fastify";
import { DashboardController } from "../controllers/dashboard-controller";

const controller = new DashboardController();

export async function dashboardRoutes(app: FastifyInstance) {
  // CEO Dashboard
  app.get("/ceo", controller.ceo);

  // Commercial Dashboard
  app.get("/commercial", controller.commercial);

  // Finance Dashboard
  app.get("/finance", controller.finance);

  // Operations Dashboard
  app.get("/operations", controller.operations);
}
