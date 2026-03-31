import { prisma } from "../db";
import { orchestrator } from "../orchestrator";
import { jsonLogger as logger } from "../utils/logger";
import { CreateAgentRunInput } from "../schemas/agent-run";

export class AgentRunService {
  /**
   * Create and execute agent run
   */
  async createAndExecute(input: CreateAgentRunInput) {
    logger.info("AgentRunService: creating run", { 
      companyId: input.companyId,
      workflow: input.workflowType 
    });

    // Create run record
    const run = await prisma.agentRun.create({
      data: {
        companyId: input.companyId,
        workflowType: input.workflowType,
        status: "pending",
        inputSummary: JSON.stringify(input.input).slice(0, 200),
      },
    });

    // Execute asynchronously
    this.executeAsync(run.id, input).catch(err => {
      logger.error("Async execution failed", { runId: run.id, error: err.message });
    });

    return {
      success: true,
      data: run,
      message: "Agent run created and queued for execution"
    };
  }

  /**
   * Get run by ID
   */
  async getById(id: string) {
    const run = await prisma.agentRun.findUnique({
      where: { id },
      include: {
        steps: { orderBy: { stepOrder: "asc" } },
        approvals: true,
        artifacts: true,
      },
    });

    if (!run) {
      throw new Error(`Agent run ${id} not found`);
    }

    return {
      success: true,
      data: run
    };
  }

  /**
   * List runs with filters
   */
  async list(params: {
    companyId?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }) {
    const { companyId, status, limit = 20, offset = 0 } = params;

    const runs = await prisma.agentRun.findMany({
      where: {
        companyId,
        status,
      },
      orderBy: { createdAt: "desc" },
      take: limit,
      skip: offset,
    });

    const total = await prisma.agentRun.count({
      where: { companyId, status }
    });

    return {
      success: true,
      data: runs,
      meta: { total, limit, offset }
    };
  }

  /**
   * Execute run asynchronously
   */
  private async executeAsync(runId: string, input: CreateAgentRunInput) {
    await orchestrator.execute({
      agentRunId: runId,
      companyId: input.companyId,
      workflowType: input.workflowType,
      input: input.input
    });
  }
}

// Singleton
export const agentRunService = new AgentRunService();
