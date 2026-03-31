import { prisma } from "../db";
import { WorkflowType, RiskLevel, RunStatus } from "../types/core";
import { PolicyEngine } from "../core/policy-engine";
import { WorkerService } from "../runtime/worker-service";
import { ToolExecutor, initializeGlobalRegistry } from "../tools/tool-executor";
import { toolRegistry } from "../tools/registry";
import { logger } from "../utils/logger";

export interface CreateAgentRunInput {
  companyId: string;
  workflowType: WorkflowType;
  input: Record<string, unknown>;
  riskLevel?: RiskLevel;
  userId?: string;
}

export class AgentService {
  private policyEngine: PolicyEngine;
  private workerService: WorkerService;
  private toolExecutor: ToolExecutor;

  constructor() {
    this.policyEngine = new PolicyEngine();
    this.workerService = new WorkerService();
    
    // Initialize global registry if not already
    if (!globalThis.__toolRegistry) {
      initializeGlobalRegistry(toolRegistry);
    }
    
    this.toolExecutor = new ToolExecutor();
  }

  /**
   * Create and execute a new agent run
   */
  async createRun(data: CreateAgentRunInput) {
    const run = await prisma.agentRun.create({
      data: {
        companyId: data.companyId,
        workflowType: data.workflowType,
        status: "pending",
        riskLevel: data.riskLevel || "R1_SAFE_WRITE",
        inputSummary: JSON.stringify(data.input).slice(0, 200),
        createdBy: data.userId || "system",
        startedAt: new Date(),
      },
    });

    logger.info("Agent run created", { runId: run.id, workflow: data.workflowType });

    // Start execution asynchronously
    this.executeRun(run.id, data).catch(err => {
      logger.error("Execute run failed", { runId: run.id, error: err.message });
    });

    return run;
  }

  /**
   * Execute a run
   */
  private async executeRun(runId: string, data: CreateAgentRunInput) {
    const startTime = Date.now();

    try {
      // Update status
      await prisma.agentRun.update({
        where: { id: runId },
        data: { status: "running" },
      });

      // Check policy
      const policy = this.policyEngine.evaluate(data.riskLevel || "R1_SAFE_WRITE");

      if (policy === "BLOCKED") {
        throw new Error("Run blocked by policy");
      }

      // Execute via worker
      const result = await this.workerService.execute({
        runId,
        workflowType: data.workflowType,
        riskLevel: data.riskLevel || "R1_SAFE_WRITE",
        input: data.input,
        companyId: data.companyId,
      });

      // Update final status
      await prisma.agentRun.update({
        where: { id: runId },
        data: {
          status: result.success ? "completed" : "failed",
          latencyMs: Date.now() - startTime,
          outputSummary: JSON.stringify(result.output).slice(0, 200),
          finishedAt: new Date(),
        },
      });

      logger.info("Agent run completed", { runId, success: result.success });

    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      
      await prisma.agentRun.update({
        where: { id: runId },
        data: {
          status: "failed",
          outputSummary: message,
          finishedAt: new Date(),
        },
      });

      logger.error("Agent run failed", { runId, error: message });
    }
  }

  /**
   * Get run by ID
   */
  async getRun(runId: string) {
    return prisma.agentRun.findUnique({
      where: { id: runId },
      include: {
        steps: { orderBy: { stepOrder: "asc" } },
        approvals: true,
        artifacts: true,
      },
    });
  }

  /**
   * Replay a run
   */
  async replayRun(originalRunId: string, overrideInput?: Record<string, unknown>) {
    const original = await this.getRun(originalRunId);
    
    if (!original) {
      throw new Error(`Run ${originalRunId} not found`);
    }

    // Parse original input
    let input: Record<string, unknown>;
    try {
      input = JSON.parse(original.inputSummary || "{}");
    } catch {
      input = {};
    }

    // Merge with overrides
    const mergedInput = overrideInput ? { ...input, ...overrideInput } : input;

    // Create new run
    return this.createRun({
      companyId: original.companyId || "default",
      workflowType: original.workflowType as WorkflowType,
      input: mergedInput,
      riskLevel: original.riskLevel as RiskLevel,
    });
  }

  /**
   * List runs
   */
  async listRuns(options?: { 
    companyId?: string; 
    status?: RunStatus;
    limit?: number;
  }) {
    return prisma.agentRun.findMany({
      where: {
        companyId: options?.companyId,
        status: options?.status,
      },
      orderBy: { createdAt: "desc" },
      take: options?.limit || 50,
    });
  }
}

// Singleton
export const agentService = new AgentService();
