import { FastifyInstance } from "fastify";
import { z } from "zod";
import { memoryService } from "../services/memory-service";
import { jsonLogger as logger } from "../utils/logger";
import { AppError } from "../utils/app-error";

const CreateMemorySchema = z.object({
  companyId: z.string().min(1),
  memoryType: z.enum(["event", "recipe", "supplier", "insight", "decision", "error", "pattern", "EPISODIC", "DECLARATIVE"]),
  title: z.string().min(1),
  content: z.string().min(1),
  tags: z.array(z.string()).default([]),
});

const SearchMemorySchema = z.object({
  q: z.string().min(1),
  companyId: z.string().min(1),
});

export async function memoryRoutes(app: FastifyInstance) {
  // POST /memory
  app.post("/", async (req, res) => {
    const parsed = CreateMemorySchema.safeParse(req.body);
    if (!parsed.success) {
      throw new AppError(parsed.error.message, 422, "VALIDATION_ERROR");
    }
    
    const memory = await memoryService.create(parsed.data);

    logger.info("Memory created", { id: memory.id, type: parsed.data.memoryType });
    return { success: true, data: memory };
  });

  // GET /memory/search?q=...&companyId=...
  app.get("/search", async (req, res) => {
    const parsed = SearchMemorySchema.safeParse(req.query);
    if (!parsed.success) {
      throw new AppError(parsed.error.message, 422, "VALIDATION_ERROR");
    }
    
    const results = await memoryService.search(parsed.data.companyId, parsed.data.q);

    return { success: true, total: results.length, query: parsed.data.q, results };
  });

  // GET /memory/recent?companyId=...
  app.get("/recent", async (req, res) => {
    const { companyId, limit } = req.query as { companyId: string; limit?: string };
    
    if (!companyId) {
      throw new AppError("Company ID required", 422, "VALIDATION_ERROR");
    }

    const results = await memoryService.getRecent(companyId, limit ? parseInt(limit) : 10);

    return { success: true, count: results.length, results };
  });
}
