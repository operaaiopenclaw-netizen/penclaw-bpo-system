import { ToolImplementation, ToolExecutionInput, ToolExecutionOutput, ToolContext } from "../types/tools";
import { prisma } from "../db";
import { logger } from "../utils/logger";

/**
 * Tool: Event Analyzer
 * Analyzes event data and returns financial metrics
 */
export class EventAnalyzerTool implements ToolImplementation {
  name = "event_analyzer";
  description = "Analyze event data and calculate financial metrics";

  async execute({ input, context }: ToolExecutionInput): Promise<ToolExecutionOutput> {
    const startTime = Date.now();
    
    logger.info("EventAnalyzerTool executing", { 
      runId: context.agentRunId,
      eventId: input.eventId 
    });

    try {
      const eventId = input.eventId as string;
      
      // Fetch event data
      const event = await prisma.event.findFirst({
        where: { eventId }
      });

      if (!event) {
        return {
          success: false,
          data: null,
          error: `Event ${eventId} not found`,
          latencyMs: Date.now() - startTime
        };
      }

      // Calculate metrics
      const metrics = {
        revenue: event.revenueTotal || 0,
        cost: event.cmvTotal || 0,
        profit: (event.revenueTotal || 0) - (event.cmvTotal || 0),
        margin: event.revenueTotal 
          ? ((event.revenueTotal - (event.cmvTotal || 0)) / event.revenueTotal * 100)
          : 0
      };

      return {
        success: true,
        data: {
          event: {
            id: event.id,
            eventId: event.eventId,
            name: event.name,
            client: event.companyName,
            date: event.eventDate,
            status: event.status
          },
          metrics
        },
        latencyMs: Date.now() - startTime
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      
      logger.error("EventAnalyzerTool failed", { error: errorMessage });
      
      return {
        success: false,
        data: null,
        error: errorMessage,
        latencyMs: Date.now() - startTime
      };
    }
  }
}
