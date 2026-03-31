import { readFile } from "fs/promises";
import { ToolImplementation, ToolExecutionInput, ToolExecutionOutput, ToolContext } from "../types/tools";
import { logger } from "../utils/logger";
import { AppError } from "../utils/app-error";

/**
 * File Read Tool
 * Safely reads file content with validation
 */
export class FileReadTool implements ToolImplementation {
  name = "file.read";
  description = "Read file content from filesystem";

  async execute({ input, context }: ToolExecutionInput): Promise<ToolExecutionOutput> {
    const startTime = Date.now();
    
    const filePath = String(input.path || "");
    
    logger.info("FileReadTool executing", { 
      path: filePath,
      runId: context.agentRunId 
    });

    // Security: validate path
    if (!filePath) {
      return {
        success: false,
        data: null,
        error: "File path is required",
        latencyMs: Date.now() - startTime
      };
    }

    // Block absolute paths outside workspace
    if (filePath.startsWith("/") && !filePath.includes("workspace-openclaw-bpo")) {
      return {
        success: false,
        data: null,
        error: "Access denied: path outside workspace",
        latencyMs: Date.now() - startTime
      };
    }

    // Block dangerous paths
    const dangerousPaths = ["/etc", "/usr", "/bin", "/sbin", "/root", ".."];
    for (const danger of dangerousPaths) {
      if (filePath.includes(danger)) {
        return {
          success: false,
          data: null,
          error: `Access denied: '${danger}' path not allowed`,
          latencyMs: Date.now() - startTime
        };
      }
    }

    try {
      // Default encoding
      const encoding = String(input.encoding || "utf-8") as BufferEncoding;
      
      // Read file
      const content = await readFile(filePath, encoding);
      
      const stats = {
        contentLength: content.length,
        lines: content.split("\n").length,
        encoding
      };

      logger.info("File read successfully", { 
        path: filePath,
        ...stats 
      });

      return {
        success: true,
        data: {
          path: filePath,
          content: content.slice(0, 100000), // Limit response size
          stats,
          truncated: content.length > 100000
        },
        latencyMs: Date.now() - startTime
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      
      logger.error("File read failed", { 
        path: filePath, 
        error: errorMessage 
      });

      // Specific error messages
      if (errorMessage.includes("ENOENT")) {
        return {
          success: false,
          data: null,
          error: `File not found: ${filePath}`,
          latencyMs: Date.now() - startTime
        };
      }

      if (errorMessage.includes("EACCES")) {
        return {
          success: false,
          data: null,
          error: `Permission denied: ${filePath}`,
          latencyMs: Date.now() - startTime
        };
      }

      if (errorMessage.includes("EISDIR")) {
        return {
          success: false,
          data: null,
          error: `Path is a directory, not a file: ${filePath}`,
          latencyMs: Date.now() - startTime
        };
      }

      return {
        success: false,
        data: null,
        error: `Read failed: ${errorMessage}`,
        latencyMs: Date.now() - startTime
      };
    }
  }

  /**
   * Check if file exists (helper method)
   */
  async exists(filePath: string): Promise<boolean> {
    try {
      await readFile(filePath, "utf-8");
      return true;
    } catch {
      return false;
    }
  }
}

// Export singleton instance
export const fileReadTool = new FileReadTool();
