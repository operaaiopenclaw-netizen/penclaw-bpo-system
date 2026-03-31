import { writeFile, mkdir, access, constants } from "fs/promises";
import { dirname } from "path";
import { ToolImplementation, ToolExecutionInput, ToolExecutionOutput } from "../types/tools";
import { logger } from "../utils/logger";

/**
 * File Write Tool
 * Safely writes file content with validation
 */
export class FileWriteTool implements ToolImplementation {
  name = "file.write";
  description = "Write content to a file";

  async execute({ input, context }: ToolExecutionInput): Promise<ToolExecutionOutput> {
    const startTime = Date.now();
    
    const filePath = String(input.path || "");
    const content = String(input.content || "");
    
    logger.info("FileWriteTool executing", { 
      path: filePath,
      bytes: Buffer.byteLength(content, "utf-8"),
      runId: context.agentRunId 
    });

    // Security validation
    const validation = this.validatePath(filePath);
    if (!validation.valid) {
      return {
        success: false,
        data: null,
        error: validation.error,
        latencyMs: Date.now() - startTime
      };
    }

    // Check if file exists (prevent overwrite unless allowed)
    const overwrite = input.allowOverwrite === true;
    const fileExists = await this.fileExists(filePath);
    
    if (fileExists && !overwrite) {
      return {
        success: false,
        data: null,
        error: `File already exists: ${filePath}. Use allowOverwrite: true to overwrite.`,
        latencyMs: Date.now() - startTime
      };
    }

    try {
      // Create parent directories
      const dir = dirname(filePath);
      await mkdir(dir, { recursive: true });

      // Encoding
      const encoding = String(input.encoding || "utf-8") as BufferEncoding;
      
      // Write file
      await writeFile(filePath, content, encoding);
      
      const bytesWritten = Buffer.byteLength(content, encoding);

      logger.info("File written successfully", { 
        path: filePath,
        bytesWritten,
        existed: fileExists
      });

      return {
        success: true,
        data: {
          path: filePath,
          bytes: bytesWritten,
          created: !fileExists,
          overwritten: fileExists
        },
        latencyMs: Date.now() - startTime
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      
      logger.error("File write failed", { 
        path: filePath, 
        error: errorMessage 
      });

      if (errorMessage.includes("EACCES")) {
        return {
          success: false,
          data: null,
          error: `Permission denied: ${filePath}`,
          latencyMs: Date.now() - startTime
        };
      }

      if (errorMessage.includes("ENOSPC")) {
        return {
          success: false,
          data: null,
          error: `Insufficient disk space`,
          latencyMs: Date.now() - startTime
        };
      }

      return {
        success: false,
        data: null,
        error: `Write failed: ${errorMessage}`,
        latencyMs: Date.now() - startTime
      };
    }
  }

  /**
   * Validate file path for security
   */
  private validatePath(filePath: string): { valid: boolean; error?: string } {
    if (!filePath) {
      return { valid: false, error: "File path is required" };
    }

    // Block paths with .. (path traversal)
    if (filePath.includes("..") || filePath.includes("~")) {
      return { valid: false, error: "Path traversal not allowed" };
    }

    // Block absolute paths outside workspace
    const dangerousPaths = ["/etc", "/usr", "/bin", "/sbin", "/root", "/sys", "/proc"];
    for (const danger of dangerousPaths) {
      if (filePath.startsWith(danger)) {
        return { valid: false, error: `Access denied: '${danger}' path not allowed` };
      }
    }

    // Block sensitive files
    const sensitiveFiles = [".env", ".git", ".ssh"];
    for (const sensitive of sensitiveFiles) {
      if (filePath.includes(sensitive)) {
        return { 
          valid: false, 
          error: `Access denied: cannot write to '${sensitive}' files` 
        };
      }
    }

    return { valid: true };
  }

  /**
   * Check if file exists
   */
  private async fileExists(filePath: string): Promise<boolean> {
    try {
      await access(filePath, constants.F_OK);
      return true;
    } catch {
      return false;
    }
  }
}

// Export singleton
export const fileWriteTool = new FileWriteTool();
