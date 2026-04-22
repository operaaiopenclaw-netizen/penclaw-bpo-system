import { WorkflowType, RiskLevel, RunStatus } from "../types/core";
import { PolicyEngine, type PolicyDecision, PolicyRule } from "../core/policy-engine";
import { WorkerService } from "./worker-service";
import { prisma } from "../db";
import { logger } from "../utils/logger";

export interface ExecutionContext {
  runId: string;
  companyId: string;
  workflowType: WorkflowType;
  stepOrder: number;
  inputData: Record<string, unknown>;
}

export interface StepResult {
  success: boolean;
  output?: unknown;
  error?: string;
  policyDecision: PolicyDecision;
  requiresApproval: boolean;
}

export class ExecutionEngine {
  private policyEngine: PolicyEngine;
  private workerService: WorkerService;

  constructor() {
    this.policyEngine = new PolicyEngine();
    this.workerService = new WorkerService();
  }

  async executeWorkflow(
    runId: string,
    workflowType: WorkflowType,
    riskLevel: RiskLevel,
    input: Record<string, unknown>
  ): Promise<StepResult> {
    const startTime = Date.now();

    logger.info("ExecutionEngine starting workflow", { 
      runId, 
      workflow: workflowType,
      riskLevel 
    });

    try {
      // 1. Classify and determine policy
      const policyDecision = this.policyEngine.evaluate(riskLevel);
      
      // 2. If requires approval, update status and wait
      if (policyDecision.requiresApproval) {
        await this.createApprovalRequest(runId, riskLevel, workflowType);
        
        await prisma.agentRun.update({
          where: { id: runId },
          data: { status: "waiting_approval" }
        });

        return {
          success: false,
          policyDecision,
          requiresApproval: true,
          error: "Approval required"
        };
      }

      // 3. Execute via worker
      const workerResult = await this.workerService.execute({
        runId,
        workflowType,
        riskLevel,
        input,
        companyId: input.companyId as string || "default"
      });

      // 4. Create execution step record
      await this.createStep(runId, {
        agentName: "execution_engine",
        actionType: "execute_workflow",
        inputPayload: { workflowType, riskLevel, input },
        outputPayload: workerResult,
        status: workerResult.success ? "completed" : "failed"
      });

      const latencyMs = Date.now() - startTime;

      // 5. Update run with results
      await prisma.agentRun.update({
        where: { id: runId },
        data: {
          status: workerResult.success ? "completed" : "failed",
          latencyMs,
          outputSummary: JSON.stringify(workerResult.output).slice(0, 200),
          finishedAt: new Date()
        }
      });

      return {
        success: workerResult.success,
        output: workerResult.output,
        error: workerResult.error,
        policyDecision,
        requiresApproval: false
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      
      logger.error("ExecutionEngine failed", { runId, error: errorMessage });

      await prisma.agentRun.update({
        where: { id: runId },
        data: {
          status: "failed",
          outputSummary: errorMessage,
          finishedAt: new Date()
        }
      });

      return {
        success: false,
        error: errorMessage,
        policyDecision: { allowed: false, requiresApproval: false, reason: "BLOCKED" },
        requiresApproval: false
      };
    }
  }

  async replayRun(
    originalRunId: string,
    overrideInput?: Record<string, unknown>
  ): Promise<StepResult> {
    logger.info("Replaying run", { originalRunId });

    // Get original run
    const original = await prisma.agentRun.findUnique({
      where: { id: originalRunId }
    });

    if (!original) {
      throw new Error(`Run ${originalRunId} not found`);
    }

    // Parse original input
    const originalInput = JSON.parse(original.inputSummary || "{}") as Record<string, unknown>;
    
    // Merge with overrides
    const input = overrideInput ? { ...originalInput, ...overrideInput } : originalInput;

    // Create new run
    const newRun = await prisma.agentRun.create({
      data: {
        companyId: original.companyId,
        workflowType: original.workflowType,
        status: "pending",
        inputSummary: JSON.stringify(input).slice(0, 200),
        riskLevel: original.riskLevel || "low"
      }
    });

    // Execute with same parameters
    return this.executeWorkflow(
      newRun.id,
      original.workflowType as unknown as WorkflowType,
      (original.riskLevel as RiskLevel) || "R1_SAFE_WRITE",
      input
    );
  }

  async approveRun(runId: string, approvedBy: string): Promise<void> {
    // Update approval status
    const approval = await prisma.approvalRequest.findFirst({
      where: { agentRunId: runId, status: "pending" }
    });

    if (approval) {
      await prisma.approvalRequest.update({
        where: { id: approval.id },
        data: {
          status: "approved",
          approvedBy,
          approvedAt: new Date()
        }
      });
    }

    // Update run and re-execute
    await prisma.agentRun.update({
      where: { id: runId },
      data: { status: "running" }
    });

    // Re-execution would happen here or via worker service
    logger.info("Run approved, ready for execution", { runId, approvedBy });
  }

  private async createApprovalRequest(
    runId: string,
    riskLevel: RiskLevel,
    requestedAction: string
  ): Promise<void> {
    await prisma.approvalRequest.create({
      data: {
        agentRunId: runId,
        riskLevel,
        requestedAction,
        status: "pending",
        justification: `Risk level ${riskLevel} requires manual approval`
      }
    });

    logger.info("Approval request created", { runId, riskLevel });
  }

  private async createStep(
    runId: string,
    stepData: {
      agentName: string;
      actionType: string;
      inputPayload: unknown;
      outputPayload: unknown;
      status: string;
    }
  ): Promise<void> {
    const count = await prisma.agentStep.count({
      where: { agentRunId: runId }
    });

    await prisma.agentStep.create({
      data: {
        agentRunId: runId,
        stepOrder: count + 1,
        agentName: stepData.agentName,
        actionType: stepData.actionType,
        inputPayload: stepData.inputPayload as any,
        outputPayload: stepData.outputPayload as any,
        status: stepData.status,
        startedAt: new Date(),
        finishedAt: new Date()
      }
    });
  }
}

// Singleton
export const executionEngine = new ExecutionEngine();
