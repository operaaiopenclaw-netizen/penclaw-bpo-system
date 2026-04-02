export type ToolContext = {
  companyId: string;
  agentRunId: string;
  userId?: string;
  sessionId?: string;
};

export type ToolExecutionInput = {
  toolName: string;
  input: Record<string, unknown>;
  context: ToolContext;
};

export type ToolExecutionOutput = {
  success: boolean;
  data: unknown;
  error?: string;
  latencyMs?: number;
  cost?: {
    monetaryCost: number;
  };
};

export interface ToolImplementation {
  name: string;
  description: string;
  execute(input: ToolExecutionInput): Promise<ToolExecutionOutput>;
}

// Tool registry entries
export type ToolRegistryEntry = {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
  outputSchema: Record<string, unknown>;
  riskLevel: "R0" | "R1" | "R2" | "R3" | "R4";
  requiresApproval: boolean;
};

// Cost tracking per tool call
export type ToolCost = {
  model: string;
  tokensIn: number;
  tokensOut: number;
  monetaryCost: number;
};
