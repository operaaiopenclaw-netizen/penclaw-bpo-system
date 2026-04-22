import { mkdir, writeFile } from "fs/promises";
import { dirname, basename, extname, join, resolve } from "path";
import { createHash } from "crypto";
import { ToolImplementation, ToolExecutionInput, ToolExecutionOutput } from "../types/tools";
import { config } from "../config/env";
import { logger } from "../utils/logger";

/**
 * Storage Upload Tool
 * Uploads content to storage with checksum verification
 */
export class StorageUploadTool implements ToolImplementation {
  name = "storage.upload";
  description = "Upload content to storage with checksum verification";

  // Allowed extensions
  private readonly ALLOWED_EXTENSIONS = [
    ".txt", ".json", ".csv", ".md", ".pdf",
    ".png", ".jpg", ".jpeg", ".gif",
    ".yaml", ".yml", ".xml", ".html"
  ];

  // Max content size (10MB)
  private readonly MAX_CONTENT_SIZE = 10 * 1024 * 1024;

  async execute({ input, context }: ToolExecutionInput): Promise<ToolExecutionOutput> {
    const startTime = Date.now();
    
    const originalFileName = String(input.fileName || `artifact-${Date.now()}.txt`);
    const content = String(input.content || "");
    const subDir = String(input.subDir || "");
    
    logger.info("StorageUploadTool executing", { 
      fileName: originalFileName,
      contentSize: content.length,
      runId: context.agentRunId 
    });

    // Validate content
    if (!content) {
      return {
        success: false,
        data: null,
        error: "Content is required",
        latencyMs: Date.now() - startTime
      };
    }

    // Check size
    if (Buffer.byteLength(content, "utf-8") > this.MAX_CONTENT_SIZE) {
      return {
        success: false,
        data: null,
        error: `Content too large: ${Buffer.byteLength(content, "utf-8")} bytes (max: ${this.MAX_CONTENT_SIZE})`,
        latencyMs: Date.now() - startTime
      };
    }

    // Validate filename
    const fileName = this.sanitizeFileName(originalFileName);
    const validation = this.validateFileName(fileName);
    if (!validation.valid) {
      return {
        success: false,
        data: null,
        error: validation.error,
        latencyMs: Date.now() - startTime
      };
    }

    try {
      // Build path
      const baseDir = resolve(config.artifactsPath || "./storage/artifacts");
      const safeSubDir = subDir ? this.sanitizePath(subDir) : "";
      const dirPath = safeSubDir ? join(baseDir, safeSubDir) : baseDir;
      const fullPath = join(dirPath, fileName);

      // Ensure path is within base directory
      if (!fullPath.startsWith(baseDir)) {
        return {
          success: false,
          data: null,
          error: "Path traversal detected: upload path outside storage directory",
          latencyMs: Date.now() - startTime
        };
      }

      // Create directories
      await mkdir(dirname(fullPath), { recursive: true });

      // Write file
      await writeFile(fullPath, content, "utf-8");

      // Calculate checksums
      const sha256 = createHash("sha256").update(content).digest("hex");
      const md5 = createHash("md5").update(content).digest("hex");

      // Get file stats
      const stats = {
        size: Buffer.byteLength(content, "utf-8"),
        checksumSHA256: sha256,
        checksumMD5: md5,
        path: fullPath,
        relativePath: safeSubDir ? join(safeSubDir, fileName) : fileName
      };

      logger.info("Storage upload successful", { 
        path: fullPath,
        size: stats.size,
        sha256
      });

      return {
        success: true,
        data: {
          fileName,
          storageUrl: `file://${fullPath}`,
          ...stats
        },
        latencyMs: Date.now() - startTime
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      
      logger.error("Storage upload failed", { 
        error: errorMessage,
        fileName
      });

      if (errorMessage.includes("ENOSPC")) {
        return {
          success: false,
          data: null,
          error: "Insufficient disk space",
          latencyMs: Date.now() - startTime
        };
      }

      return {
        success: false,
        data: null,
        error: `Upload failed: ${errorMessage}`,
        latencyMs: Date.now() - startTime
      };
    }
  }

  /**
   * Sanitize filename
   */
  private sanitizeFileName(fileName: string): string {
    // Remove path components
    let sanitized = basename(fileName);
    
    // Replace dangerous characters
    sanitized = sanitized.replace(/[<>:"|?*\x00-\x1f]/g, "_");
    
    // Ensure has extension
    if (!extname(sanitized)) {
      sanitized += ".txt";
    }
    
    // Limit length
    if (sanitized.length > 255) {
      const ext = extname(sanitized);
      sanitized = sanitized.slice(0, 250 - ext.length) + ext;
    }
    
    return sanitized;
  }

  /**
   * Sanitize path component
   */
  private sanitizePath(subDir: string): string {
    return subDir
      .replace(/\.{2,}/g, "_") // Block ..
      .replace(/[<>:"|?*\\]/g, "_") // Windows forbidden chars
      .replace(/^\/+/, "") // Leading slashes
      .replace(/\/+$/, ""); // Trailing slashes
  }

  /**
   * Validate file name
   */
  private validateFileName(fileName: string): { valid: boolean; error?: string } {
    // Check extension
    const ext = extname(fileName).toLowerCase();
    if (!this.ALLOWED_EXTENSIONS.includes(ext)) {
      return { 
        valid: false, 
        error: `File extension not allowed: ${ext}. Allowed: ${this.ALLOWED_EXTENSIONS.join(", ")}` 
      };
    }

    // Block hidden files
    if (basename(fileName).startsWith(".")) {
      return { valid: false, error: "Hidden files not allowed" };
    }

    // Block executables
    const executableExts = [".exe", ".bat", ".cmd", ".sh", ".php", ".js", ".ts"];
    if (executableExts.includes(ext)) {
      return { valid: false, error: `Executable files not allowed: ${ext}` };
    }

    return { valid: true };
  }
}

// Export singleton
export const storageUploadTool = new StorageUploadTool();
