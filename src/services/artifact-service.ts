import { prisma } from "../db";
import { config } from "../config/env";
import { mkdir, writeFile, readFile } from "fs/promises";
import { join, dirname } from "path";
import { createHash } from "crypto";
import { logger } from "../utils/logger";

export class ArtifactService {
  /**
   * Render text artifact
   */
  async renderTextArtifact(data: {
    agentRunId: string;
    artifactType: string;
    fileName: string;
    content: string;
  }) {
    logger.info("ArtifactService: rendering text artifact", { 
      agentRunId: data.agentRunId,
      fileName: data.fileName 
    });

    // Ensure artifacts directory exists
    await mkdir(config.artifactsPath, { recursive: true });

    const fullPath = join(config.artifactsPath, data.fileName);
    
    // Ensure subdirectories exist
    await mkdir(dirname(fullPath), { recursive: true });

    // Write file
    await writeFile(fullPath, data.content, "utf-8");

    // Calculate checksum
    const checksum = createHash("sha256").update(data.content).digest("hex");

    // Create DB record
    const artifact = await prisma.artifact.create({
      data: {
        agentRunId: data.agentRunId,
        artifactType: data.artifactType,
        fileName: data.fileName,
        storageUrl: `file://${fullPath}`,
        sizeBytes: Buffer.byteLength(data.content, "utf-8"),
        checksum,
        version: 1
      }
    });

    logger.info("Artifact rendered", { 
      artifactId: artifact.id,
      checksum: checksum.slice(0, 16) + "..."
    });

    return artifact;
  }

  /**
   * Render JSON artifact
   */
  async renderJsonArtifact(data: {
    agentRunId: string;
    artifactType: string;
    fileName: string;
    content: Record<string, unknown>;
  }) {
    const content = JSON.stringify(data.content, null, 2);
    return this.renderTextArtifact({
      agentRunId: data.agentRunId,
      artifactType: data.artifactType,
      fileName: data.fileName,
      content
    });
  }

  /**
   * Get artifact by ID
   */
  async getById(id: string) {
    return prisma.artifact.findUnique({
      where: { id }
    });
  }

  /**
   * Get artifact content
   */
  async getContent(storageUrl: string): Promise<string> {
    const path = storageUrl.replace("file://", "");
    return readFile(path, "utf-8");
  }

  /**
   * List artifacts by run
   */
  async listByRun(agentRunId: string) {
    return prisma.artifact.findMany({
      where: { agentRunId },
      orderBy: { createdAt: "desc" }
    });
  }

  /**
   * Verify checksum
   */
  async verifyChecksum(id: string): Promise<boolean> {
    const artifact = await this.getById(id);
    if (!artifact) return false;

    try {
      const content = await this.getContent(artifact.storageUrl);
      const currentChecksum = createHash("sha256").update(content).digest("hex");
      return currentChecksum === artifact.checksum;
    } catch {
      return false;
    }
  }
}

// Singleton
export const artifactService = new ArtifactService();
