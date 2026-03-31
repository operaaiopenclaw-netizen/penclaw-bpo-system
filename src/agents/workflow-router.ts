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
    this.sequences.set("contract_onboarding", {
      agents: [
        "contract_agent",
        "commercial_agent",
        "finance_agent",
        "inventory_agent",
        "event_ops_agent",
        "reporting_agent"
      ],
      description: "Onboarding completo de contrato",
      estimatedLatency: 3000,
      riskLevel: "R2"
    });

    this.sequences.set("weekly_procurement", {
      agents: ["inventory_agent", "finance_agent", "reporting_agent"],
      description: "Sugestões de compra semanal",
      estimatedLatency: 1500,
      riskLevel: "R2"
    });

    this.sequences.set("post_event_closure", {
      agents: ["event_ops_agent", "finance_agent", "reporting_agent"],
      description: "Fechamento pós-evento",
      estimatedLatency: 2000,
      riskLevel: "R2"
    });

    this.sequences.set("weekly_kickoff", {
      agents: ["event_ops_agent", "reporting_agent"],
      description: "Briefing semanal",
      estimatedLatency: 1000,
      riskLevel: "R1"
    });

    this.sequences.set("ceo_daily_briefing", {
      agents: ["reporting_agent"],
      description: "Briefing diário CEO",
      estimatedLatency: 500,
      riskLevel: "R1"
    });
  }

  route(workflowType: WorkflowType): AgentSequence {
    const sequence = this.sequences.get(workflowType);
    if (!sequence) {
      logger.warn("Unknown workflow, using default", { workflowType });
      return { agents: ["reporting_agent"], description: "Default", estimatedLatency: 500, riskLevel: "R1" };
    }
    return sequence;
  }

  getAgents(workflowType: WorkflowType): string[] {
    return this.route(workflowType).agents;
  }

  listWorkflows(): Array<{ type: WorkflowType; agents: string[] }> {
    return Array.from(this.sequences.entries()).map(([type, seq]) => ({
      type,
      agents: seq.agents
    }));
  }
}

export const workflowRouter = new WorkflowRouter();
