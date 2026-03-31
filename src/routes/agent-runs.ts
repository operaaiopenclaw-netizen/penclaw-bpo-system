import { FastifyInstance } from "fastify";
import { z } from "zod";
import { prisma } from "../db";
import { jsonLogger as logger } from "../utils/logger";
import { AppError } from "../utils/app-error";

const CreateRunSchema = z.object({
  companyId: z.string().uuid(),
  workflowType: z.enum(["KITCHEN", "DRE", "AUDIT", "RECONCILE", "FULL_PIPELINE"]),
  input: z.record(z.unknown()),
});

export async function agentRunsRoutes(app: FastifyInstance) {
  // POST /agent-runs
  app.post("/", async (req, res) => {
    const parsed = CreateRunSchema.safeParse(req.body);
    if (!parsed.success) {
      throw new AppError(parsed.error.message, 422, "VALIDATION_ERROR");
    }

    const run = await prisma.agentRun.create({
      data: {
        companyId: parsed.data.companyId,
        workflowType: parsed.data.workflowType,
        status: "running",
        inputSummary: JSON.stringify(parsed.data.input).slice(0, 200),
        startedAt: new Date(),
      },
    });

    logger.info("Agent run created", { runId: run.id });
    return { success: true, data: run };
  });

  // GET /agent-runs/:id
  app.get("/:id", async (req, res) => {
    const { id } = req.params as { id: string };
    
    const run = await prisma.agentRun.findUnique({
      where: { id },
      include: {
        steps: { orderBy: { stepOrder: "asc" } },
        approvals: true,
        artifacts: true,
      },
    });

    if (!run) throw new AppError("Agent run not found", 404, "NOT_FOUND");
    
    return { success: true, data: run };
  });

  // POST /agent-runs/:id/replay
  app.post("/:id/replay", async (req, res) => {
    const { id } = req.params as { id: string };
    const original = await prisma.agentRun.findUnique({ where: { id } });
    
    if (!original) throw new AppError("Original run not found", 404, "NOT_FOUND");

    const replay = await prisma.agentRun.create({
      data: {
        companyId: original.companyId,
        workflowType: original.workflowType,
        status: "pending",
        inputSummary: original.inputSummary,
      },
    });

    logger.info("Agent run replayed", { originalId: id, replayId: replay.id });
    return { success: true, data: replay };
  });
}
