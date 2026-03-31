import { WorkflowType } from "../types/core";
import { logger } from "../utils/logger";

export type AgentSequence = {
  agents: string[];
  description: string;
  estimatedLatency: number;
  riskLevel: "R1" | "R2" | "R3";
};

export class WorkflowRouter {
  private sequences: Map<WorkflowType, AgentSequence> = new Map();

  constructor() {
    // Initialize sequences
    this.sequences.set("contract_onboarding", {
      agents: [
        "contract_agent",
        "commercial_agent",
        "finance_agent",
        "inventory_agent",
        "event_ops_agent",
        "reporting_agent"
      ],
      description: "Onboarding completo de contrato - validação → comercial → financeiro → estoque → operação → relatório",
      estimatedLatency: 3000, // 3 seconds
      riskLevel: "R2"
    });

    this.sequences.set("weekly_procurement", {
      agents: ["inventory_agent", "finance_agent", "reporting_agent"],
      description: "Sugestões de compra semanal com análise financeira",
      estimatedLatency: 1500,
      riskLevel: "R2"
    });

    this.sequences.set("post_event_closure", {
      agents: ["event_ops_agent", "finance_agent", "reporting_agent"],
      description: "Fechamento financeiro e operacional pós-evento",
      estimatedLatency: 2000,
      riskLevel: "R2"
    });

    this.sequences.set("weekly_kickoff", {
      agents: ["event_ops_agent", "reporting_agent"],
      description: "Briefing semanal de kickoffs de eventos",
      estimatedLatency: 1000,
      riskLevel: "R1"
    });

    this.sequences.set("ceo_daily_briefing", {
      agents: ["reporting_agent"],
      description: "Briefing diário executivo",
      estimatedLatency: 500,
      riskLevel: "R1"
    });
  }

  /**
   * Route workflow to agent sequence
   */
  route(workflowType: WorkflowType): AgentSequence {
    const sequence = this.sequences.get(workflowType);
    
    if (!sequence) {
      logger.warn("Unknown workflow type, using default", { workflowType });
      return {
        agents: ["reporting_agent"],
        description: "Default sequence - unknown workflow",
        estimatedLatency: 500,
        riskLevel: "R1"
      };
    }

    logger.info("Workflow routed", { 
      workflowType,
      agents: sequence.agents,
      risk: sequence.riskLevel
    });

    return sequence;
  }

  /**
   * Get agent sequence for workflow
   */
  getAgents(workflowType: WorkflowType): string[] {
    return this.route(workflowType).agents;
  }

  /**
   * Get workflow description
   */
  getDescription(workflowType: WorkflowType): string {
    return this.route(workflowType).description;
  }

  /**
   * Check if workflow requires approval
   */
  requiresApproval(workflowType: WorkflowType): boolean {
    const sequence = this.route(workflowType);
    return sequence.riskLevel === "R3" || sequence.agents.includes("finance_agent");
  }

  /**
   * Get estimated latency for workflow
   */
  getEstimatedLatency(workflowType: WorkflowType): number {
    return this.route(workflowType).estimatedLatency;
  }

  /**
   * Get risk level for workflow
   */
  getRiskLevel(workflowType: WorkflowType): "R1" | "R2" | "R3" {
    return this.route(workflowType).riskLevel;
  }

  /**
   * List all available workflows
   */
  listWorkflows(): Array<{ type: WorkflowType; description: string; agents: string[] }> {
    return Array.from(this.sequences.entries()).map(([type, seq]) => ({
      type,
      description: seq.description,
      agents: seq.agents
    }));
  }

  /**
   * Register custom workflow
   */
  registerWorkflow(
    type: WorkflowType,
    sequence: AgentSequence
  ): void {
    this.sequences.set(type, sequence);
    logger.info("Workflow registered", { type, agents: sequence.agents });
  }
}

// Singleton
export const workflowRouter = new WorkflowRouter();
