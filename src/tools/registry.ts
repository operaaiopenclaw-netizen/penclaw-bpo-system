import { ToolImplementation, ToolRegistryEntry } from "../types/tools";
import { EventAnalyzerTool } from "./event-analyzer";
import { CalculatorTool } from "./calculator";
import { RecipeCostTool } from "./recipe-cost";
import { FileReadTool } from "./file-read";
import { FileWriteTool } from "./file-write";
import { SqlQueryTool } from "./sql-query";
import { HttpRequestTool } from "./http-request";
import { logger } from "../utils/logger";

/**
 * Tool Registry
 * Manages all available tools
 */
export class ToolRegistry {
  private tools: Map<string, ToolImplementation>;
  private registry: ToolRegistryEntry[];

  constructor() {
    this.tools = new Map();
    this.registry = [];
    
    // Register default tools
    this.register(new EventAnalyzerTool());
    this.register(new CalculatorTool());
    this.register(new RecipeCostTool());
    this.register(new FileReadTool());
  }

  register(tool: ToolImplementation): void {
    this.tools.set(tool.name, tool);
    
    // Add to registry metadata
    this.registry.push({
      name: tool.name,
      description: tool.description,
      inputSchema: {}, // Would be defined per tool
      outputSchema: {},
      riskLevel: "R0",
      requiresApproval: false
    });
    
    logger.info("Tool registered", { name: tool.name });
  }

  get(name: string): ToolImplementation | undefined {
    return this.tools.get(name);
  }

  list(): ToolRegistryEntry[] {
    return [...this.registry];
  }

  async execute(toolName: string, input: any, context: any) {
    const tool = this.get(toolName);
    
    if (!tool) {
      throw new Error(`Tool ${toolName} not found`);
    }

    return tool.execute({
      toolName,
      input,
      context
    });
  }

  has(toolName: string): boolean {
    return this.tools.has(toolName);
  }
}

// Singleton
export const toolRegistry = new ToolRegistry();

// Export tools
export { EventAnalyzerTool, CalculatorTool, RecipeCostTool };
