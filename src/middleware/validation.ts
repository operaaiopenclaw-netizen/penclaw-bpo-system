import { z } from "zod";
import { FastifyRequest, FastifyReply, FastifyInstance } from "fastify";
import { AppError } from "../utils/app-error";

export function validateBody<T>(schema: z.ZodType<T>) {
  return async (request: FastifyRequest, reply: FastifyReply) => {
    const result = schema.safeParse(request.body);
    
    if (!result.success) {
      const errors = result.error.errors.map(e => ({
        path: e.path.join("."),
        message: e.message,
      }));
      
      throw new AppError(`Validation failed: ${JSON.stringify(errors)}`, 422, "VALIDATION_ERROR");
    }
    
    // Attach validated data to request
    (request as any).validatedBody = result.data;
  };
}

export function validateParams<T extends z.ZodRawShape>(schema: z.ZodObject<T>) {
  return async (request: FastifyRequest, reply: FastifyReply) => {
    const result = schema.safeParse(request.params);
    
    if (!result.success) {
      throw new AppError(`Invalid params: ${result.error.message}`, 422, "VALIDATION_ERROR");
    }
    
    (request as any).validatedParams = result.data;
  };
}

export function validateQuery<T extends z.ZodRawShape>(schema: z.ZodObject<T>) {
  return async (request: FastifyRequest, reply: FastifyReply) => {
    const result = schema.safeParse(request.query);
    
    if (!result.success) {
      throw new AppError(`Invalid query: ${result.error.message}`, 422, "VALIDATION_ERROR");
    }
    
    (request as any).validatedQuery = result.data;
  };
}

// Request schemas
export const schemas = {
  createAgentRun: z.object({
    companyId: z.string().uuid(),
    workflowType: z.enum(["contract_onboarding", "weekly_procurement", "post_event_closure", "weekly_kickoff", "ceo_daily_briefing"]),
    input: z.record(z.unknown()),
    riskLevel: z.enum(["R0_READ_ONLY", "R1_SAFE_WRITE", "R2_EXTERNAL_EFFECT", "R3_FINANCIAL_IMPACT", "R4_DESTRUCTIVE"]).optional(),
  }),
  
  approvalAction: z.object({
    approved: z.boolean(),
    reason: z.string().optional(),
  }),
  
  createMemory: z.object({
    memoryType: z.enum(["event", "recipe", "supplier", "insight", "decision", "error", "pattern"]),
    title: z.string().min(1, "Title required"),
    content: z.string().min(1, "Content required"),
    tags: z.array(z.string()).default([]),
    companyId: z.string().uuid().optional(),
  }),
  
  searchMemory: z.object({
    query: z.string().min(1, "Query required"),
    limit: z.coerce.number().min(1).max(100).default(10),
  }),
  
  renderArtifact: z.object({
    agentRunId: z.string().uuid(),
    artifactType: z.enum(["csv", "json", "pdf", "report"]),
    format: z.enum(["csv", "json", "pdf"]),
    data: z.record(z.unknown()),
  }),
};
