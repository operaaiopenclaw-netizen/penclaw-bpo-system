import { prisma } from "../db";
import { createToolExecutor, getGlobalRegistry } from "../tools/tool-executor";
import { ToolExecutor } from "../tools/tool-executor";
import { ToolRegistry } from "../tools/registry";
import { logger } from "../utils/logger";

export type AgentExecutionContext = {
  companyId: string;
  agentRunId: string;
  input: Record<string, unknown>;
  userId?: string;
  metadata?: Record<string, unknown>;
};

export type AgentExecutionResult = {
  success: boolean;
  output: Record<string, unknown>;
  nextAgent?: string;
  riskLevel?: "R0" | "R1" | "R2" | "R3" | "R4";
  latencyMs?: number;
  toolCalls?: number;
};

export abstract class BaseAgent {
  abstract readonly name: string;
  abstract readonly description: string;
  abstract readonly defaultRiskLevel: "R0" | "R1" | "R2" | "R3" | "R4";

  protected toolRegistry?: ToolRegistry;
  protected toolExecutor?: ToolExecutor;

  constructor() {}

  private ensureTools(): void {
    if (this.toolRegistry && this.toolExecutor) {
      return;
    }

    const registry = getGlobalRegistry();

    if (!registry) {
      throw new Error(
        "Global tool registry not initialized before tool execution."
      );
    }

    this.toolRegistry = registry;
    this.toolExecutor = createToolExecutor(registry);
  }

  abstract execute(context: AgentExecutionContext): Promise<AgentExecutionResult>;

  protected async logStep(
    agentRunId: string,
    status: "pending" | "running" | "completed" | "failed",
    metadata?: Record<string, unknown>
  ): Promise<void> {
    try {
      const count = await prisma.agentStep.count({
        where: { agentRunId }
      });

      await prisma.agentStep.create({
        data: {
          agentRunId,
          stepOrder: count + 1,
          agentName: this.name,
          actionType: status,
          status,
          inputPayload: (metadata?.input ?? null) as any,
          outputPayload: (metadata?.output ?? null) as any,
          startedAt: status === "running" ? new Date() : undefined,
          finishedAt:
            status === "completed" || status === "failed"
              ? new Date()
              : undefined
        }
      });
    } catch (error) {
      logger.error("Failed to log agent step", {
        agentRunId,
        agentName: this.name,
        error: error instanceof Error ? error.message : "Unknown error"
      });
    }
  }

  protected async executeTool(
    stepId: string,
    toolName: string,
    input: Record<string, unknown>,
    companyId = ""
  ) {
    this.ensureTools();

    return this.toolExecutor!.execute(stepId, {
      toolName,
      input,
      context: {
        companyId,
        agentRunId: stepId
      }
    });
  }

  protected validateOutput(output: Record<string, unknown>): boolean {
    return output !== null && typeof output === "object";
  }
}

export class AgentRegistry {
  private agents: Map<string, BaseAgent> = new Map();

  register(agent: BaseAgent): void {
    this.agents.set(agent.name, agent);
    logger.info("Agent registered", {
      name: agent.name,
      riskLevel: agent.defaultRiskLevel
    });
  }

  get(name: string): BaseAgent | undefined {
    return this.agents.get(name);
  }

  list(): Array<{ name: string; description: string; riskLevel: string }> {
    return Array.from(this.agents.values()).map((a) => ({
      name: a.name,
      description: a.description,
      riskLevel: a.defaultRiskLevel
    }));
  }
}

export const agentRegistry = new AgentRegistry();
