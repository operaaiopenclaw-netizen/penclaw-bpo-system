import { FastifyInstance } from "fastify";
import { approvalController } from "../controllers/approval-controller";

export async function approvalsRoutes(app: FastifyInstance) {
  // POST /approvals/:id/approve
  app.post("/:id/approve", async (req, res) => approvalController.approve(req as any, res));

  // POST /approvals/:id/reject
  app.post("/:id/reject", async (req, res) => approvalController.reject(req as any, res));

  // GET /approvals/pending
  app.get("/pending", async (req, res) => approvalController.listPending(req, res));

  // GET /approvals/:id
  app.get("/:id", async (req, res) => approvalController.getById(req as any, res));
}
