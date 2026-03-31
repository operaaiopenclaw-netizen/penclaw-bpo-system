import { BaseAgent, AgentExecutionContext, AgentExecutionResult } from "./base-agent";
import { prisma } from "../db";
import { logger } from "../utils/logger";

export class ReportingAgent extends BaseAgent {
  readonly name = "reporting_agent";
  readonly description = "Geração de relatórios e resumos executivos";
  readonly defaultRiskLevel = "R1" as const;

  async execute(context: AgentExecutionContext): Promise<AgentExecutionResult> {
    const startTime = Date.now();
    
    logger.info("ReportingAgent executing", { 
      runId: context.agentRunId,
      companyId: context.companyId 
    });

    await this.logStep(context.agentRunId, "running", { input: context.input });

    try {
      // Buscar dados do run
      const runData = await this.getRunData(context);
      
      // Gerar resumo
      const executiveSummary = {
        companyId: context.companyId,
        agentRunId: context.agentRunId,
        generatedAt: new Date().toISOString(),
        summary: this.generateSummary(runData),
        metrics: {
          totalAgents: runData.steps?.length || 0,
          successful: runData.completed || 0,
          failed: runData.failed || 0,
          latencyMs: runData.latency || 0
        },
        status: runData.status || "unknown",
        output: runData.output || {}
      };

      const result = {
        executiveSummary,
        generatedAt: executiveSummary.generatedAt,
        reportType: context.input.reportType || "executive_summary"
      };

      await this.logStep(context.agentRunId, "completed", { output: result });

      logger.info("ReportingAgent completed", { 
        runId: context.agentRunId,
        summary: result.executiveSummary.summary
      });

      return {
        success: true,
        output: result,
        riskLevel: this.defaultRiskLevel,
        latencyMs: Date.now() - startTime
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      
      await this.logStep(context.agentRunId, "failed", { error: errorMessage });
      
      return {
        success: false,
        output: { error: errorMessage },
        riskLevel: "R2",
        latencyMs: Date.now() - startTime
      };
    }
  }

  // Buscar dados do run
  private async getRunData(context: AgentExecutionContext) {
    try {
      const run = await prisma.agentRun.findUnique({
        where: { id: context.agentRunId },
        include: { steps: true }
      });

      return {
        status: run?.status,
        output: run?.outputSummary,
        latency: run?.latencyMs,
        steps: run?.steps,
        completed: run?.steps?.filter(s => s.status === "completed").length || 0,
        failed: run?.steps?.filter(s => s.status === "failed").length || 0
      };
    } catch {
      return { status: "unknown", output: null, latency: 0, steps: [], completed: 0, failed: 0 };
    }
  }

  // Gerar resumo textual
  private generateSummary(runData: any): string {
    return `Run ${runData.status} with ${runData.completed} agents completed successfully`;
  }
}

// Singleton
export const reportingAgent = new ReportingAgent();

// Registro
import { agentRegistry } from "./base-agent";
agentRegistry.register(reportingAgent);
