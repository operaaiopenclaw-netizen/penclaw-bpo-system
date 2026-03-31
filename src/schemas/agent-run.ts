import { z } from "zod";

export const createAgentRunSchema = z.object({
  companyId: z.string().min(1, "Company ID is required"),
  workflowType: z.enum([
    "contract_onboarding",
    "weekly_procurement", 
    "post_event_closure",
    "weekly_kickoff",
    "ceo_daily_briefing"
  ]),
  input: z.record(z.any()).default({})
});

export type CreateAgentRunInput = z.infer<typeof createAgentRunSchema>;

export const agentRunIdSchema = z.object({
  id: z.string().uuid("Invalid agent run ID")
});

export const replayAgentRunSchema = z.object({
  overrideInput: z.record(z.any()).optional()
});

export const agentRunQuerySchema = z.object({
  companyId: z.string().optional(),
  status: z.enum(["pending", "running", "completed", "failed", "waiting_approval"]).optional(),
  limit: z.coerce.number().min(1).max(100).default(20),
  offset: z.coerce.number().min(0).default(0)
});
