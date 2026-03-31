import { FastifyInstance } from "fastify";
import { z } from "zod";
import { prisma } from "../db";
import { jsonLogger as logger } from "../utils/logger";

const CreateMemorySchema = z.object({
  memoryType: z.enum(["event", "recipe", "supplier", "insight", "decision", "error", "pattern"]),
  title: z.string().min(1),
  content: z.string().min(1),
  tags: z.array(z.string()).default([]),
  companyId: z.string().optional(),
});

const SearchMemorySchema = z.object({
  query: z.string().min(1),
  limit: z.coerce.number().default(10),
});

export async function memoryRoutes(app: FastifyInstance) {
  // POST /memory
  app.post("/", async (req, res) => {
    const parsed = CreateMemorySchema.parse(req.body);
    
    const memory = await prisma.memoryItem.create({
      data: {
        ...parsed,
        confidenceScore: 0.95,
      },
    });

    logger.info("Memory created", { id: memory.id, type: parsed.memoryType });
    return { success: true, data: memory };
  });

  // GET /memory/search?query=...&limit=10
  app.get("/search", async (req, res) => {
    const { query, limit } = SearchMemorySchema.parse(req.query);
    
    // Simple text search (use full-text search in production)
    const results = await prisma.memoryItem.findMany({
      where: {
        OR: [
          { title: { contains: query, mode: "insensitive" } },
          { content: { contains: query, mode: "insensitive" } },
          { tags: { has: query } },
        ],
      },
      take: limit,
      orderBy: { createdAt: "desc" },
    });

    return { success: true, total: results.length, query, results };
  });
}
