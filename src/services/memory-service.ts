import { prisma } from "../db";
import { logger } from "../utils/logger";

export class MemoryService {
  /**
   * Create new memory
   */
  async create(data: {
    companyId: string;
    memoryType: string;
    title: string;
    content: string;
    tags?: string[];
  }) {
    logger.info("MemoryService: creating memory", { title: data.title });

    return prisma.memoryItem.create({
      data: {
        companyId: data.companyId,
        memoryType: data.memoryType,
        title: data.title,
        content: data.content,
        tags: data.tags || [],
        confidenceScore: 0.95
      }
    });
  }

  /**
   * Search memories
   */
  async search(companyId: string, q: string) {
    logger.info("MemoryService: searching", { companyId, query: q });

    return prisma.memoryItem.findMany({
      where: {
        companyId,
        OR: [
          { title: { contains: q, mode: "insensitive" } },
          { content: { contains: q, mode: "insensitive" } },
          { tags: { has: q } }
        ]
      },
      orderBy: { createdAt: "desc" },
      take: 20
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

  /**
   * Get memory by ID
   */
  async getById(id: string) {
    return prisma.memoryItem.findUnique({
      where: { id }
    });
  }

  /**
   * Update memory
   */
  async update(id: string, data: Partial<{
    title: string;
    content: string;
    tags: string[];
  }>) {
    return prisma.memoryItem.update({
      where: { id },
      data
    });
  }

  /**
   * Delete memory
   */
  async delete(id: string) {
    return prisma.memoryItem.delete({
      where: { id }
    });
  }
}

// Singleton
export const memoryService = new MemoryService();
