import { WorkflowType, RiskLevel, RunStatus } from "../types/core";
import { PolicyEngine } from "../core/policy-engine";
import { prisma } from "../db";
import { logger } from "../utils/logger";

export interface WorkerTask {
  runId: string;
  workflowType: WorkflowType;
  riskLevel: RiskLevel;
  input: Record<string, unknown>;
  companyId: string;
}

export interface WorkerResult {
  success: boolean;
  output?: unknown;
  error?: string;
  latencyMs: number;
}

export class WorkerService {
  private policyEngine: PolicyEngine;
  private isRunning: boolean = false;

  constructor() {
    this.policyEngine = new PolicyEngine();
  }

  async execute(task: WorkerTask): Promise<WorkerResult> {
    const startTime = Date.now();
    
    logger.info("Worker starting execution", { runId: task.runId, workflow: task.workflowType });

    try {
      // Step 1: Policy Check
      const policy = this.policyEngine.evaluate(task.riskLevel);
      
      if (!policy.allowed) {
        throw new Error(`Workflow blocked by policy for risk level: ${task.riskLevel}`);
      }

      // Step 2: Update status to running
      await this.updateRunStatus(task.runId, "running");

      // Step 3: Execute based on workflow type
      const result = await this.executeWorkflow(task);

      // Step 4: Update final status
      await this.updateRunStatus(task.runId, "completed", result);

      const latencyMs = Date.now() - startTime;
      
      logger.info("Worker execution completed", { 
        runId: task.runId, 
        latencyMs,
        success: result.success 
      });

      return {
        ...result,
        latencyMs
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      
      logger.error("Worker execution failed", { runId: task.runId, error: errorMessage });
      
      await this.updateRunStatus(task.runId, "failed", { success: false, error: errorMessage, latencyMs: Date.now() - startTime });

      return {
        success: false,
        error: errorMessage,
        latencyMs: Date.now() - startTime
      };
    }
  }

  private async executeWorkflow(task: WorkerTask): Promise<WorkerResult> {
    // Route to appropriate engine
    switch (task.workflowType) {
      case "contract_onboarding":
        return this.executeContractOnboarding(task);
      
      case "weekly_procurement":
        return this.executeWeeklyProcurement(task);
      
      case "post_event_closure":
        return this.executePostEventClosure(task);
      
      case "weekly_kickoff":
        return this.executeWeeklyKickoff(task);
      
      case "ceo_daily_briefing":
        return this.executeCeoBriefing(task);
      
      default:
        throw new Error(`Unknown workflow type: ${task.workflowType}`);
    }
  }

  private async executeContractOnboarding(task: WorkerTask): Promise<WorkerResult> {
    logger.info("Executing contract onboarding workflow", { runId: task.runId });
    
    // Simulate execution - in real implementation, call Python engines
    await this.simulateDelay(500);
    
    return {
      success: true,
      output: {
        contractId: task.input.contractId,
        status: "onboarded",
        timestamp: new Date().toISOString()
      },
      latencyMs: 0 // Will be set by caller
    };
  }

  private async executeWeeklyProcurement(task: WorkerTask): Promise<WorkerResult> {
    logger.info("Executing weekly procurement workflow", { runId: task.runId });
    
    await this.simulateDelay(800);
    
    return {
      success: true,
      output: {
        procurementPlan: "generated",
        suppliersContacted: 5,
        timestamp: new Date().toISOString()
      },
      latencyMs: 0
    };
  }

  private async executePostEventClosure(task: WorkerTask): Promise<WorkerResult> {
    logger.info("Executing post-event closure workflow", { runId: task.runId });
    
    await this.simulateDelay(1200);
    
    return {
      success: true,
      output: {
        eventId: task.input.eventId,
        status: "closed",
        financialSummary: "generated"
      },
      latencyMs: 0
    };
  }

  private async executeWeeklyKickoff(task: WorkerTask): Promise<WorkerResult> {
    logger.info("Executing weekly kickoff workflow", { runId: task.runId });
    
    await this.simulateDelay(600);
    
    return {
      success: true,
      output: {
        weekPlan: "created",
        teamNotifications: 3
      },
      latencyMs: 0
    };
  }

  private async executeCeoBriefing(task: WorkerTask): Promise<WorkerResult> {
    logger.info("Executing CEO daily briefing workflow", { runId: task.runId });
    
    await this.simulateDelay(1000);
    
    return {
      success: true,
      output: {
        briefingType: "ceo_daily",
        metricsGenerated: true,
        alerts: []
      },
      latencyMs: 0
    };
  }

  private async updateRunStatus(
    runId: string, 
    status: RunStatus, 
    result?: WorkerResult
  ): Promise<void> {
    try {
      await prisma.agentRun.update({
        where: { id: runId },
        data: {
          status,
          outputSummary: result ? JSON.stringify(result) : undefined,
          finishedAt: status === "completed" || status === "failed" ? new Date() : undefined
        }
      });
    } catch (error) {
      logger.error("Failed to update run status", { runId, error });
    }
  }

  private simulateDelay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  start(): void {
    this.isRunning = true;
    logger.info("Worker service started");
  }

  stop(): void {
    this.isRunning = false;
    logger.info("Worker service stopped");
  }

  get isActive(): boolean {
    return this.isRunning;
  }
}

// Singleton instance
export const workerService = new WorkerService();
