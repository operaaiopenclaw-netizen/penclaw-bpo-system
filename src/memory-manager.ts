import { prisma } from "./db";
import { logger } from "./utils/logger";

export class MemoryManager {
  /**
   * Add episodic memory
   */
  async addEpisodicMemory(params: {
    companyId: string;
    title: string;
    content: string;
    tags?: string[];
  }) {
    logger.info("MemoryManager: adding episodic memory", { 
      companyId: params.companyId, 
      title: params.title 
    });

    return prisma.memoryItem.create({
      data: {
        companyId: params.companyId,
        memoryType: "EPISODIC",
        title: params.title,
        content: params.content,
        tags: params.tags || [],
        confidenceScore: 0.95,
      }
    });
  }

  /**
   * Add declarative memory (facts)
   */
  async addDeclarativeMemory(params: {
    companyId: string;
    title: string;
    content: string;
    tags?: string[];
  }) {
    logger.info("MemoryManager: adding declarative memory", { title: params.title });

    return prisma.memoryItem.create({
      data: {
        companyId: params.companyId,
        memoryType: "DECLARATIVE",
        title: params.title,
        content: params.content,
        tags: params.tags || [],
        confidenceScore: 1.0,
      }
    });
  }

  /**
   * Search memories by query
   */
  async search(params: {
    companyId: string;
    query: string;
    limit?: number;
  }) {
    const { query, limit = 10 } = params;

    return prisma.memoryItem.findMany({
      where: {
        companyId: params.companyId,
        OR: [
          { title: { contains: query, mode: "insensitive" } },
          { content: { contains: query, mode: "insensitive" } },
          { tags: { has: query } },
        ]
      },
      take: limit,
      orderBy: { createdAt: "desc" }
    });
  }

  /**
   * Get recent memories
   */
  async getRecent(companyId: string, limit = 10) {
    return prisma.memoryItem.findMany({
      where: { companyId },
      orderBy: { createdAt: "desc" },
      take: limit
    });
  }
}

// Singleton
export const memoryManager = new MemoryManager();
