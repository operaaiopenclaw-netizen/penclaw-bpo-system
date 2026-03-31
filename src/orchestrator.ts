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

  async execute(params: {
    agentRunId: string;
    companyId: string;
    workflowType: WorkflowType;
    input: Record<string, unknown>;
  }) {
    const { agentRunId, companyId, workflowType, input } = params;

    logger.info("Orchestrator starting execution", { 
      runId: agentRunId,
      workflow: workflowType 
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
