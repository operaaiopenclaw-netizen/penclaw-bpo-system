import { RiskLevel } from "../types/core";

export type PolicyDecision = {
  allowed: boolean;
  requiresApproval: boolean;
  reason: string;
  riskLevel?: RiskLevel;
};

export type PolicyRule = {
  riskLevel: RiskLevel;
  allowed: boolean;
  requiresApproval: boolean;
  reason: string;
  autoExecute?: boolean;
  requiresDoubleApproval?: boolean;
  logLevel: "info" | "warn" | "error" | "audit";
};

// Policy rules based on OpenClaw spec
const POLICY_RULES: Record<RiskLevel, PolicyRule> = {
  R0_READ_ONLY: {
    riskLevel: "R0_READ_ONLY",
    allowed: true,
    requiresApproval: false,
    autoExecute: true,
    reason: "Read-only queries - safe",
    logLevel: "info",
  },
  R1_SAFE_WRITE: {
    riskLevel: "R1_SAFE_WRITE",
    allowed: true,
    requiresApproval: false,
    autoExecute: true,
    reason: "Safe writes (logs, notes) - auto-approve",
    logLevel: "info",
  },
  R2_EXTERNAL_EFFECT: {
    riskLevel: "R2_EXTERNAL_EFFECT",
    allowed: true,
    requiresApproval: false,
    reason: "External effects allowed with mandatory logging",
    logLevel: "warn",
  },
  R3_FINANCIAL_IMPACT: {
    riskLevel: "R3_FINANCIAL_IMPACT",
    allowed: true,
    requiresApproval: true,
    reason: "Financial impact requires approval",
    logLevel: "audit",
  },
  R4_DESTRUCTIVE: {
    riskLevel: "R4_DESTRUCTIVE",
    allowed: true,
    requiresApproval: true,
    requiresDoubleApproval: true,
    reason: "Destructive action requires double approval flow",
    logLevel: "error",
  },
};

export class PolicyEngine {
  private rules: Record<RiskLevel, PolicyRule>;

  constructor(customRules?: Partial<Record<RiskLevel, PolicyRule>>) {
    // Merge default rules with any custom overrides
    this.rules = { ...POLICY_RULES, ...customRules };
  }

  /**
   * Evaluate a risk level and return policy decision
   */
  evaluate(riskLevel: RiskLevel): PolicyDecision {
    const rule = this.rules[riskLevel];
    
    if (!rule) {
      return {
        allowed: false,
        requiresApproval: true,
        reason: `Unknown risk level: ${riskLevel}`,
        riskLevel,
      };
    }

    return {
      allowed: rule.allowed,
      requiresApproval: rule.requiresApproval,
      reason: rule.reason,
      riskLevel,
    };
  }

  /**
   * Check if action requires double approval
   */
  requiresDoubleApproval(riskLevel: RiskLevel): boolean {
    return this.rules[riskLevel]?.requiresDoubleApproval ?? false;
  }

  /**
   * Check if action can auto-execute
   */
  canAutoExecute(riskLevel: RiskLevel): boolean {
    return this.rules[riskLevel]?.autoExecute ?? false;
  }

  /**
   * Get log level for risk
   */
  getLogLevel(riskLevel: RiskLevel): string {
    return this.rules[riskLevel]?.logLevel ?? "info";
  }

  /**
   * Validate if a workflow type requires elevated permissions
   */
  validateWorkflow(workflowType: string, riskLevel: RiskLevel): PolicyDecision {
    // Special rules for specific workflows
    if (workflowType === "financial_transfer" && riskLevel !== "R3_FINANCIAL_IMPACT") {
      return {
        allowed: false,
        requiresApproval: true,
        reason: "Financial workflows must be R3 or higher",
        riskLevel,
      };
    }

    if (workflowType === "data_deletion" && riskLevel !== "R4_DESTRUCTIVE") {
      return {
        allowed: false,
        requiresApproval: true,
        reason: "Data deletion workflows must be R4",
        riskLevel,
      };
    }

    return this.evaluate(riskLevel);
  }
}

// Singleton instance
export const policyEngine = new PolicyEngine();

// Helper functions
export function evaluateRisk(riskLevel: RiskLevel): PolicyDecision {
  return policyEngine.evaluate(riskLevel);
}

export function isApprovalRequired(riskLevel: RiskLevel): boolean {
  return policyEngine.evaluate(riskLevel).requiresApproval;
}

export function canExecuteImmediately(riskLevel: RiskLevel): boolean {
  const decision = policyEngine.evaluate(riskLevel);
  return decision.allowed && !decision.requiresApproval;
}
