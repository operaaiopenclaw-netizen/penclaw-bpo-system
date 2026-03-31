import { ToolImplementation, ToolRegistryEntry } from "../types/tools";
import { EventAnalyzerTool } from "./event-analyzer";
import { CalculatorTool } from "./calculator";
import { RecipeCostTool } from "./recipe-cost";
import { FileReadTool } from "./file-read";
import { FileWriteTool } from "./file-write";
import { SqlQueryTool } from "./sql-query";
import { HttpRequestTool } from "./http-request";
import { StorageUploadTool } from "./storage-upload";
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
    
    // Register all 8 default tools
    this.register(new EventAnalyzerTool());
    this.register(new CalculatorTool());
    this.register(new RecipeCostTool());
    this.register(new FileReadTool());
    this.register(new FileWriteTool());
    this.register(new SqlQueryTool());
    this.register(new HttpRequestTool());
    this.register(new StorageUploadTool());
  }

  register(tool: ToolImplementation): void {
    this.tools.set(tool.name, tool);
    
    // Determine risk level based on tool type
    const riskLevel = this.determineRiskLevel(tool.name);
    
    // Add to registry metadata
    this.registry.push({
      name: tool.name,
      description: tool.description,
      inputSchema: {}, // Would be defined per tool
      outputSchema: {},
      riskLevel,
      requiresApproval: riskLevel === "R3" || riskLevel === "R4"
    });
    
    logger.info("Tool registered", { name: tool.name, riskLevel });
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

  /**
   * Determine risk level based on tool name
   */
  private determineRiskLevel(toolName: string): "R0" | "R1" | "R2" | "R3" | "R4" {
    const riskMap: Record<string, "R0" | "R1" | "R2" | "R3" | "R4"> = {
      "event_analyzer": "R0",
      "calculator": "R0",
      "recipe_cost": "R1",
      "file.read": "R1",
      "sql.query": "R1",
      "file.write": "R2",
      "http.request": "R2",
      "storage.upload": "R2"
    };
    
    return riskMap[toolName] || "R1";
  }
}

// Singleton instance
export const toolRegistry = new ToolRegistry();

// Export all tools
export { 
  EventAnalyzerTool, 
  CalculatorTool, 
  RecipeCostTool, 
  FileReadTool,
  FileWriteTool,
  SqlQueryTool,
  HttpRequestTool,
  StorageUploadTool
};
