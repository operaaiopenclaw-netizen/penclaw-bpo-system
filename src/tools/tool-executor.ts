import { prisma } from "../db";
import { ToolExecutionInput, ToolExecutionOutput, ToolContext } from "../types/tools";
import { ToolRegistry } from "./registry";
import { logger } from "../utils/logger";

// Global registry declaration
declare global {
  var __toolRegistry: ToolRegistry | undefined;
}

/**
 * ToolExecutor
 * Executes tools and tracks execution in database
 */
export class ToolExecutor {
  private registry: ToolRegistry;

  constructor(registry?: ToolRegistry) {
    // Use provided registry or global
    this.registry = registry || globalThis.__toolRegistry;
    
    if (!this.registry) {
      throw new Error("Tool registry not initialized. Call initializeGlobalRegistry() first.");
    }
  }

  async execute(
    agentStepId: string, 
    toolInput: ToolExecutionInput
  ): Promise<ToolExecutionOutput> {
    const startedAt = Date.now();

    logger.info(`Tool execution starting: ${toolInput.toolName} for step ${agentStepId}`);

    // Create tool call record in database
    const toolCall = await prisma.toolCall.create({
      data: {
        agentStepId,
        toolName: toolInput.toolName,
        toolInput: toolInput.input as any,
        context: toolInput.context as any,
        status: "running",
        createdAt: new Date()
      }
    });

    try {
      // Get tool from registry
      const tool = this.registry.get(toolInput.toolName);
      
      if (!tool) {
        throw new Error(`Tool not found: ${toolInput.toolName}`);
      }

      // Execute tool
      const result = await tool.execute(toolInput);
      
      const latencyMs = Date.now() - startedAt;

      // Update tool call record with success
      await prisma.toolCall.update({
        where: { id: toolCall.id },
        data: {
          toolOutput: result.data as any,
          status: result.success ? "completed" : "failed",
          latencyMs,
          costEstimate: result.cost?.monetaryCost || 0
        }
      });

      logger.info(`Tool execution completed: ${toolInput.toolName} in ${latencyMs}ms`);

      return {
        ...result,
        latencyMs
      };

    } catch (error) {
      const latencyMs = Date.now() - startedAt;
      const errorMessage = error instanceof Error ? error.message : "Unknown error";

      // Update tool call record with failure
      await prisma.toolCall.update({
        where: { id: toolCall.id },
        data: {
          status: "failed",
          toolOutput: { error: errorMessage } as any,
          latencyMs
        }
      });

      logger.error(`Tool execution failed: ${toolInput.toolName} - ${errorMessage}`);

      return {
        success: false,
        data: null,
        error: errorMessage,
        latencyMs
      };
    }
  }

  /**
   * Execute multiple tools in parallel
   */
  async executeParallel(
    agentStepId: string,
    inputs: ToolExecutionInput[]
  ): Promise<ToolExecutionOutput[]> {
    return Promise.all(
      inputs.map(input => this.execute(agentStepId, input))
    );
  }

  /**
   * Get execution history for a step
   */
  async getHistory(agentStepId: string) {
    return prisma.toolCall.findMany({
      where: { agentStepId },
      orderBy: { createdAt: "asc" }
    });
  }
}

/**
 * Initialize global tool registry
 */
export function initializeGlobalRegistry(registry: ToolRegistry): void {
  globalThis.__toolRegistry = registry;
  logger.info("Global tool registry initialized");
}

/**
 * Get global tool registry
 */
export function getGlobalRegistry(): ToolRegistry | undefined {
  return globalThis.__toolRegistry;
}

// Singleton executor
export function createToolExecutor(registry?: ToolRegistry) {
  return new ToolExecutor(registry);
}
