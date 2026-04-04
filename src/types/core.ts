// ============================================================
// CORE TYPES - Openclaw API
// ============================================================

export type RiskLevel =
  | "R0" | "R1" | "R2" | "R3" | "R4"
  | "R0_READ_ONLY"
  | "R1_SAFE_WRITE"
  | "R2_EXTERNAL_EFFECT"
  | "R3_FINANCIAL_IMPACT"
  | "R4_DESTRUCTIVE";

export type RunStatus =
  | "pending"
  | "classified"
  | "planned"
  | "running"
  | "waiting_approval"
  | "blocked"
  | "completed"
  | "failed"
  | "cancelled"
  | "replayed";

export type WorkflowType =
  | "contract_onboarding"
  | "weekly_procurement"
  | "post_event_closure"
  | "weekly_kickoff"
  | "ceo_daily_briefing";

// Additional types for Orkestra domain
export type MemoryType =
  | "event"
  | "recipe"
  | "supplier"
  | "insight"
  | "decision"
  | "error"
  | "pattern";

export type ArtifactType =
  | "csv"
  | "json"
  | "pdf"
  | "report"
  | "log"
  | "config"
  | "pop"
  | "dashboard";

export type DashboardType =
  | "ceo"
  | "commercial"
  | "finance"
  | "operations";

// API Response wrapper
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// Agent Run Input
export interface AgentRunInput {
  eventId?: string;
  eventData?: Record<string, unknown>;
  params?: Record<string, unknown>;
  [key: string]: unknown;
}

// Approval Action
export interface ApprovalAction {
  approved: boolean;
  reason?: string;
}

// Memory Search Result
export interface MemorySearchResult {
  id: string;
  memoryType: MemoryType;
  title: string;
  content: string;
  tags: string[];
  confidenceScore: number;
  createdAt: string;
}
