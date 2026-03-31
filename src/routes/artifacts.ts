import { FastifyInstance } from "fastify";
import { z } from "zod";
import { prisma } from "../db";
import { AppError } from "../utils/app-error";
import { jsonLogger as logger } from "../utils/logger";
import { config } from "../config/env";
import { join } from "path";
import { writeFile, mkdir } from "fs/promises";

const RenderArtifactSchema = z.object({
  agentRunId: z.string().uuid(),
  artifactType: z.enum(["csv", "json", "pdf", "report"]),
  format: z.enum(["csv", "json", "pdf"]),
  data: z.record(z.unknown()),
});

export async function artifactsRoutes(app: FastifyInstance) {
  // POST /artifacts/render
  app.post("/render", async (req, res) => {
    const parsed = RenderArtifactSchema.parse(req.body);
    
    const id = `ART-${Date.now()}`;
    const fileName = `${id}.${parsed.format}`;
    
    // Ensure artifacts directory exists
    await mkdir(config.artifactsPath, { recursive: true });
    
    const filePath = join(config.artifactsPath, fileName);
    const content = parsed.format === "json" 
      ? JSON.stringify(parsed.data, null, 2)
      : "csv,pdf,content"; // Simplified
    
    // Write to disk
    await writeFile(filePath, content);

    const artifact = await prisma.artifact.create({
      data: {
        agentRunId: parsed.agentRunId,
        artifactType: parsed.artifactType,
        fileName,
        storageUrl: `file://${filePath}`,
        version: 1,
      },
    });

    logger.info("Artifact rendered", { id: artifact.id, type: parsed.artifactType });
    return { success: true, data: artifact };
  });

  // GET /artifacts/:id
  app.get("/:id", async (req, res) => {
    const { id } = req.params as { id: string };
    
    const artifact = await prisma.artifact.findUnique({ where: { id } });
    if (!artifact) throw new AppError("Artifact not found", 404, "NOT_FOUND");
    
    return { success: true, data: artifact, downloadUrl: artifact.storageUrl };
  });
}
