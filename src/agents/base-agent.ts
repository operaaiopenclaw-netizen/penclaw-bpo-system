import { prisma } from "../db";
import { createToolExecutor, getGlobalRegistry } from "../tools/tool-executor";
import { ToolExecutor } from "../tools/tool-executor";
import { ToolRegistry } from "../tools/registry";
import { logger } from "../utils/logger";

// ============================================================
// ACTION CONTRACT — every agent output MUST include _actions[]
// All DB mutations flow through ActionDispatcher, never directly.
// ============================================================

export type AgentActionType =
  | "CREATE_PURCHASE_RECOMMENDATION"
  | "CREATE_STOCK_RESERVATION"
  | "RELEASE_STOCK_RESERVATION"
  | "CREATE_SERVICE_ORDER"
  | "CREATE_PRODUCTION_ORDER"
  | "CREATE_FINANCIAL_PROVISION"
  | "QUALIFY_LEAD"
  | "CREATE_REPORT_ARTIFACT"
  | "ALERT_RISK"
  | "REQUEST_APPROVAL"
  | "BLOCK_EVENT"
  | "RECORD_PRODUCTION"
  | "RECORD_CONSUMPTION"
  | "RECONCILE_EVENT"
  | "FLAG_OCCURRENCE"
  | "RESOLVE_OCCURRENCE"
  | "CONFIRM_CHECKPOINT"
  | "CONFIRM_TEARDOWN";

export interface AgentAction {
  type: AgentActionType;
  payload: Record<string, unknown>;
}

export interface AgentOutput {
  _actions: AgentAction[];
  _summary: string;
  [key: string]: unknown;
}

export type AgentExecutionContext = {
  companyId: string;
  agentRunId: string;
  input: Record<string, unknown>;
  userId?: string;
  metadata?: Record<string, unknown>;
};

export type AgentExecutionResult = {
  success: boolean;
  output: AgentOutput | Record<string, unknown>;
  nextAgent?: string;
  riskLevel?: "R0" | "R1" | "R2" | "R3" | "R4";
  latencyMs?: number;
  toolCalls?: number;
};

/** Normalizes any output object to conform to AgentOutput contract. */
export function normalizeOutput(raw: Record<string, unknown>): AgentOutput {
  return {
    ...raw,
    _actions: Array.isArray(raw._actions) ? (raw._actions as AgentAction[]) : [],
    _summary: typeof raw._summary === "string" ? raw._summary : "",
  };
}

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
    // Step lifecycle is managed exclusively by the Orchestrator, which creates
    // and updates the agent_steps record for each plan item.
    // Creating additional records here conflicts with the orchestrator's
    // (agentRunId, stepOrder) unique constraint and produces phantom steps.
    // Internal agent progress should use logger, not DB step records.
    logger.debug(`Agent ${this.name} logStep: ${status}`, { agentRunId });
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
