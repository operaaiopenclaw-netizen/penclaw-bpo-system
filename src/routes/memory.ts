import { FastifyInstance } from "fastify";
import { memoryService } from "../services/memory-service";

export async function memoryRoutes(app: FastifyInstance) {
  // GET /memory/:companyId - Lista memórias recentes
  app.get("/:companyId", async (req, res) => {
    const { companyId } = req.params as { companyId: string };
    const { type, limit, days } = req.query as { type?: string; limit?: string; days?: string };

    try {
      let result;
      
      if (type) {
        result = await memoryService.getByType(
          companyId,
          type as any,
          limit ? parseInt(limit) : 20
        );
      } else if (days) {
        result = await memoryService.getRecent(
          companyId,
          parseInt(days),
          limit ? parseInt(limit) : 50
        );
      } else {
        result = await memoryService.getRecent(companyId, 30, 50);
      }

      return res.send({
        success: true,
        data: result,
        count: result.length
      });
    } catch (error: any) {
      return res.status(500).send({
        error: "Failed to fetch memories",
        message: error?.message
      });
    }
  });

  // GET /memory/:companyId/search?q=termo
  app.get("/:companyId/search", async (req, res) => {
    const { companyId } = req.params as { companyId: string };
    const { q, limit } = req.query as { q?: string; limit?: string };

    if (!q) {
      return res.status(400).send({
        error: "Bad Request",
        message: "Query parameter 'q' is required"
      });
    }

    try {
      const result = await memoryService.search(
        companyId,
        q,
        limit ? parseInt(limit) : 10
      );

      return res.send({
        success: true,
        data: result,
        query: q,
        count: result.length
      });
    } catch (error: any) {
      return res.status(500).send({
        error: "Search failed",
        message: error?.message
      });
    }
  });

  // GET /memory/:companyId/summary
  app.get("/:companyId/summary", async (req, res) => {
    const { companyId } = req.params as { companyId: string };
    const { days } = req.query as { days?: string };

    try {
      const summary = await memoryService.generateSummary(
        companyId,
        days ? parseInt(days) : 7
      );

      return res.send({
        success: true,
        summary
      });
    } catch (error: any) {
      return res.status(500).send({
        error: "Failed to generate summary",
        message: error?.message
      });
    }
  });
}
