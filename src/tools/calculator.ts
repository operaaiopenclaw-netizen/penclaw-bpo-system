import { ToolImplementation, ToolExecutionInput, ToolExecutionOutput } from "../types/tools";
import { logger } from "../utils/logger";

/**
 * Tool: Calculator
 * Performs mathematical calculations
 */
export class CalculatorTool implements ToolImplementation {
  name = "calculator";
  description = "Perform mathematical calculations";

  async execute({ input }: ToolExecutionInput): Promise<ToolExecutionOutput> {
    const startTime = Date.now();
    
    logger.info("CalculatorTool executing", { expression: input.expression });

    try {
      const expression = input.expression as string;
      
      // Safe evaluation - limited operations
      const allowedChars = /^[\d+\-*/().\s]*$/;
      if (!allowedChars.test(expression)) {
        throw new Error("Invalid characters in expression");
      }

      // Evaluate (using Function constructor for sandboxed eval)
      const result = new Function(`return ${expression}`)();

      return {
        success: true,
        data: {
          expression,
          result: Number(result),
          currency: input.currency || "BRL"
        },
        latencyMs: Date.now() - startTime
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Calculation failed";
      
      logger.error("CalculatorTool failed", { error: errorMessage });
      
      return {
        success: false,
        data: null,
        error: errorMessage,
        latencyMs: Date.now() - startTime
      };
    }
  }
}
