import { prisma } from "./db";
import { logger } from "./utils/logger";
import { AppError } from "./utils/app-error";
import { WorkflowType } from "./types/core";

// Imports
import { workflowRouter } from "./agents/workflow-router";
import { Planner } from "./planner";
import { Validator } from "./validator";
import { PolicyEngine } from "./core/policy-engine";
import { memoryManager } from "./memory-manager";
import { memoryService } from "./services/memory-service";

// Agents
import {
  contractAgent,
  commercialAgent,
  financeAgent,
  inventoryAgent,
  eventOpsAgent,
  reportingAgent
} from "./agents";

export class Orchestrator {
  private planner = new Planner();
  private validator = new Validator();
  private policyEngine = new PolicyEngine();

  private agents = {
    contract_agent: contractAgent,
    commercial_agent: commercialAgent,
    finance_agent: financeAgent,
    inventory_agent: inventoryAgent,
    event_ops_agent: eventOpsAgent,
    reporting_agent: reportingAgent
  };

  /**
   * Resume execution from where it left off (for approved runs)
   */
  async resume(agentRunId: string) {
    logger.info("Orchestrator resuming execution", { runId: agentRunId });

    // Get run with all steps
    const run = await prisma.agentRun.findUnique({
      where: { id: agentRunId },
      include: {
        steps: {
          orderBy: { stepOrder: "asc" }
        }
      }
    });

    if (!run) {
      throw new AppError("Run not found", 404);
    }

    if (run.status !== "waiting_approval") {
      throw new AppError(`Cannot resume run in status ${run.status}`, 400);
    }

    // Find input from first step
    const firstStep = run.steps[0];
    const input = firstStep?.inputPayload as Record<string, unknown> || {};
    
    // Get last output from completed steps
    const lastOutput = run.steps
      .filter(s => s.status === "completed")
      .reduce((acc, step) => {
        const output = step.outputPayload as Record<string, unknown>;
        return { ...acc, ...output };
      }, {} as Record<string, unknown>);

    // Find the step that was waiting approval and mark it completed
    const waitingStep = run.steps.find(s => s.status === "waiting_approval");
    if (waitingStep) {
      await prisma.agentStep.update({
        where: { id: waitingStep.id },
        data: {
          status: "completed",
          finishedAt: new Date()
        }
      });
    }

    // Continue execution from where it left off
    return this.execute({
      agentRunId,
      companyId: run.companyId || "",
      workflowType: run.workflowType as WorkflowType,
      input,
      resumeFrom: (waitingStep?.stepOrder || 0) + 1,
      lastOutput
    });
  }

  async execute(params: {
    agentRunId: string;
    companyId: string;
    workflowType: WorkflowType;
    input: Record<string, unknown>;
    resumeFrom?: number;
    lastOutput?: Record<string, unknown>;
  }) {
    const { agentRunId, companyId, workflowType, input, resumeFrom = 1, lastOutput = {} } = params;

    logger.info("Orchestrator starting execution", { 
      runId: agentRunId,
      workflow: workflowType,
      resumeFrom 
    });

    try {
      // Get agent sequence from router
      const sequence = workflowRouter.route(workflowType);
      const agentNames = sequence.agents;

      // Build execution plan
      const plan = this.planner.buildPlan(agentNames);

      // Update run status
      await prisma.agentRun.update({
        where: { id: agentRunId },
        data: { status: "planned" }
      });

      let lastOutput: Record<string, unknown> = {};

      // Execute each step
      for (const item of plan) {
        const result = await this.executeStep({
          item,
          agentRunId,
          companyId,
          input,
          lastOutput,
          workflowType
        });

        if (result.status === "waiting_approval") {
          return { status: "waiting_approval" };
        }

        if (result.status === "failed") {
          return { status: "failed", error: result.error };
        }

        lastOutput = { ...lastOutput, ...result.output };
      }

      // Update final status
      await prisma.agentRun.update({
        where: { id: agentRunId },
        data: {
          status: "completed",
          outputSummary: JSON.stringify(lastOutput).slice(0, 200),
          finishedAt: new Date()
        }
      });

      logger.info("Orchestrator completed", { runId: agentRunId });

      return {
        status: "completed",
        output: lastOutput
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";

      await prisma.agentRun.update({
        where: { id: agentRunId },
        data: {
          status: "failed",
          outputSummary: errorMessage,
          finishedAt: new Date()
        }
      });

      // Log error in memory
      await memoryService.log({
        companyId,
        type: "error",
        content: `Orchestration failed: ${errorMessage}`,
        context: {
          workflowType,
          agentRunId
        },
        agentRunId
      }).catch(() => {});

      throw new AppError(`Orchestration failed: ${errorMessage}`, 500);
    }
  }

  private async executeStep(params: {
    item: { stepOrder: number; agentName: string; actionType: string };
    agentRunId: string;
    companyId: string;
    input: Record<string, unknown>;
    lastOutput: Record<string, unknown>;
    workflowType: string;
  }) {
    const { item, agentRunId, companyId, input, lastOutput, workflowType } = params;

    const agent = this.agents[item.agentName as keyof typeof this.agents];
    if (!agent) {
      throw new AppError(`Agent not found: ${item.agentName}`, 500);
    }

    // Create step record
    const step = await prisma.agentStep.create({
      data: {
        agentRunId,
        stepOrder: item.stepOrder,
        agentName: item.agentName,
        actionType: item.actionType,
        inputPayload: { ...input, ...lastOutput },
        status: "running",
        startedAt: new Date()
      }
    });

    // Execute agent
    const result = await agent.execute({
      companyId,
      agentRunId,
      input: { ...input, ...lastOutput }
    });

    // Validate output
    const valid = this.validator.validateStepOutput(result.output);

    if (!valid) {
      await prisma.agentStep.update({
        where: { id: step.id },
        data: {
          status: "failed",
          finishedAt: new Date(),
          outputPayload: { error: "Invalid step output" }
        }
      });

      // Log validation error
      await memoryService.log({
        companyId,
        type: "error",
        content: `Step validation failed for ${item.agentName}: Invalid output`,
        context: {
          workflowType,
          agentRunId,
          stepOrder: item.stepOrder
        },
        agentRunId
      }).catch(() => {});

      return { status: "failed", error: "Invalid step output" };
    }

    // Check policy
    if (result.riskLevel) {
      const decision = this.policyEngine.evaluate(result.riskLevel);

      if (decision.requiresApproval) {
        // Create approval request
        await prisma.approvalRequest.create({
          data: {
            agentRunId,
            riskLevel: result.riskLevel,
            requestedAction: `Approve step ${item.stepOrder} from ${item.agentName}`,
            justification: decision.reason,
            status: "pending"
          }
        });

        await prisma.agentStep.update({
          where: { id: step.id },
          data: {
            status: "waiting_approval",
            outputPayload: result.output,
            finishedAt: new Date()
          }
        });

        await prisma.agentRun.update({
          where: { id: agentRunId },
          data: { status: "waiting_approval" }
        });

        return { status: "waiting_approval" };
      }
    }

    // Mark step as completed
    await prisma.agentStep.update({
      where: { id: step.id },
      data: {
        status: "completed",
        outputPayload: result.output,
        finishedAt: new Date()
      }
    });

    // Create artifact for step outputs (checklists, reports, etc)
    const artifactTypes = ["checklist", "report", "json", "csv"];
    const shouldCreateArtifact = result.output && (
      result.output.checklist ||
      result.output.report ||
      result.output.json ||
      result.output.csv ||
      result.output.items ||
      result.output.data
    );

    if (shouldCreateArtifact) {
      const artifactType = result.output.checklist ? "checklist" :
                          result.output.report ? "report" :
                          result.output.csv ? "csv" : "json";
      
      await prisma.artifact.create({
        data: {
          agentRunId,
          artifactType,
          fileName: `${item.agentName}_step${item.stepOrder}_${artifactType}.json`,
          metadata: {
            agentName: item.agentName,
            stepOrder: item.stepOrder,
            workflowType,
            contentType: artifactType
          },
          createdAt: new Date()
        }
      }).catch(() => {}); // Ignore artifact creation errors
    }

    // Store operational memory
    await memoryService.log({
      companyId,
      type: "decision",
      content: `Step ${item.stepOrder} (${item.agentName}) completed successfully`,
      context: {
        workflowType,
        agentName: item.agentName,
        stepOrder: item.stepOrder
      },
      agentRunId
    }).catch(() => {}); // Ignore errors

    // Store memory
    await memoryManager.addEpisodicMemory({
      companyId,
      title: `Step ${item.stepOrder} completed`,
      content: JSON.stringify({
        agentName: item.agentName,
        output: result.output,
        workflowType
      }),
      tags: [workflowType, item.agentName]
    }).catch(() => {}); // Ignore memory errors

    return { status: "completed", output: result.output };
  }
}

// Singleton
export const orchestrator = new Orchestrator();
