// ============================================================
// PROCUREMENT AGENT — Sprint 9
// Wraps the full procurement cycle: Demand → Gap → Supplier → Decision → Approval → Audit
// ============================================================
import { BaseAgent, AgentExecutionContext, AgentExecutionResult, AgentAction } from "./base-agent";
import { logger } from "../utils/logger";
import { procurementEngine } from "../intelligence/procurement-engine";
import { actionDispatcher } from "../services/action-dispatcher";
import { analyzeWithClaude, isClaudeAvailable } from "../services/claude-client";
import type { ProcurementEngineResult } from "../intelligence/types";

export class ProcurementAgent extends BaseAgent {
  readonly name = "procurement_agent";
  readonly description = "Engine completo de procurement: demanda → gap → fornecedor → decisão → aprovação → auditoria";
  readonly defaultRiskLevel = "R2" as const;

  async execute(context: AgentExecutionContext): Promise<AgentExecutionResult> {
    const start = Date.now();
    logger.info("ProcurementAgent executing", { runId: context.agentRunId });
    await this.logStep(context.agentRunId, "running", { input: context.input });

    try {
      const input = this.extractInput(context);

      // Run the full procurement decision cycle
      const engineResult = await procurementEngine.run({
        tenantId: context.companyId,
        eventType: input.eventType,
        guestCount: input.guestCount,
        durationHours: input.durationHours,
        eventId: input.eventId,
        eventDate: input.eventDate,
        eventMarginPct: input.eventMarginPct
      });

      // Wrap decisions and alerts as proper AgentAction objects (type field required by ActionDispatcher)
      const allActions: AgentAction[] = [
        ...engineResult.decisions.map(d => ({
          type: "CREATE_PURCHASE_RECOMMENDATION" as const,
          payload: d as unknown as Record<string, unknown>
        })),
        ...engineResult.alerts.map(a => ({
          type: "ALERT_RISK" as const,
          payload: a as unknown as Record<string, unknown>
        }))
      ];

      // Dispatch directly (agent owns this cycle — POs created here, not via orchestrator _actions[])
      const dispatchResult = await actionDispatcher.dispatch(
        context.agentRunId,
        context.companyId,
        allActions
      );

      // Optional Claude strategic insight (non-blocking)
      const strategicInsight = await this.getStrategicInsight(engineResult);

      // Determine output risk level from engine result
      const outputRisk = this.mapRisk(engineResult.summary.overallRisk);

      const output = {
        // _actions[] exposed for audit trail (already dispatched above — orchestrator will skip re-dispatch)
        _actions: allActions,
        _summary: `Procurement: ${engineResult.summary.totalDecisions} decisions, R$${engineResult.summary.estimatedTotalCost} total, risk ${engineResult.summary.overallRisk}`,
        // Demand summary
        demand: {
          eventType: input.eventType,
          guestCount: input.guestCount,
          durationHours: input.durationHours,
          forecastConfidence: engineResult.gapAnalysis.items.length > 0
            ? Math.round(
                engineResult.decisions.reduce((s, d) => s + d.confidence, 0) /
                Math.max(engineResult.decisions.length, 1) * 100
              )
            : 0
        },
        // Gap summary
        gaps: {
          totalItems: engineResult.gapAnalysis.summary.totalItems,
          sufficient: engineResult.gapAnalysis.summary.sufficient,
          shortages: engineResult.gapAnalysis.summary.shortages,
          critical: engineResult.gapAnalysis.summary.critical,
          estimatedProcurementCost: engineResult.gapAnalysis.summary.estimatedTotalProcurementCost,
          overallRisk: engineResult.summary.overallRisk,
          items: engineResult.gapAnalysis.items.filter(i => i.severity !== "OK").map(i => ({
            code: i.itemCode,
            name: i.itemName,
            needed: i.needed,
            available: i.available,
            committed: i.committed,
            free: i.free,
            gap: i.gap,
            severity: i.severity,
            estimatedCost: i.estimatedGapCost
          }))
        },
        // Decisions with approval status + supplier intelligence
        decisions: engineResult.decisions.map(d => ({
          decisionId: d.decisionId,
          supplierSelected: {
            supplierId: d.supplierId,
            supplierName: d.supplierName,
            score: d.supplierScore,
            recommendation: d.supplierRecommendation
          },
          alternatives: d.alternatives,
          selectionReason: d.selectionReason,
          confidence: d.confidence,
          // Legacy shape kept for backwards compatibility
          supplier: d.supplierName,
          supplierScore: d.supplierScore,
          items: d.items.length,
          totalCost: d.totalCost,
          riskLevel: d.riskLevel,
          approvalStatus: d.approvalStatus,
          approvalReason: d.approvalReason,
          deadline: d.deadline,
          justification: d.justification
        })),
        // Alerts
        alerts: engineResult.alerts.map(a => ({
          code: a.code,
          severity: a.severity,
          message: a.message,
          recommendedAction: a.recommendedAction,
          financialImpact: a.financialImpact
        })),
        // Dispatch results
        dispatch: {
          purchaseOrdersCreated: dispatchResult.purchaseOrdersCreated,
          alertsLogged: dispatchResult.alertsLogged,
          errors: dispatchResult.errors
        },
        // Summary
        summary: engineResult.summary,
        strategicInsight,
        durationMs: Date.now() - start
      };

      await this.logStep(context.agentRunId, "completed", { output });

      logger.info("ProcurementAgent completed", {
        runId: context.agentRunId,
        decisions: engineResult.summary.totalDecisions,
        autoApproved: engineResult.summary.autoApproved,
        pending: engineResult.summary.pendingApproval,
        totalCost: engineResult.summary.estimatedTotalCost
      });

      return {
        success: true,
        output,
        riskLevel: outputRisk,
        latencyMs: Date.now() - start
      };
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      await this.logStep(context.agentRunId, "failed", { error: msg });
      logger.error("ProcurementAgent failed", { runId: context.agentRunId, error: msg });
      return {
        success: false,
        output: { error: msg },
        riskLevel: "R3",
        latencyMs: Date.now() - start
      };
    }
  }

  private extractInput(context: AgentExecutionContext) {
    const i = context.input;
    return {
      eventType: String(i.eventType ?? i.tipoEvento ?? "corporativo").toLowerCase(),
      guestCount: Math.max(1, parseInt(String(i.numGuests ?? i.guests ?? i.convidados ?? 100))),
      durationHours: parseFloat(String(i.durationHours ?? i.duracao ?? 6)) || 6,
      eventId: i.eventId ? String(i.eventId) : undefined,
      eventDate: i.eventDate ? new Date(String(i.eventDate)) : undefined,
      eventMarginPct: i.eventMarginPct !== undefined ? parseFloat(String(i.eventMarginPct)) : undefined
    };
  }

  private mapRisk(overallRisk: string): "R1" | "R2" | "R3" | "R4" {
    const m: Record<string, "R1" | "R2" | "R3" | "R4"> = {
      LOW: "R1",
      MEDIUM: "R2",
      HIGH: "R3",
      CRITICAL: "R4"
    };
    return m[overallRisk] ?? "R2";
  }

  private async getStrategicInsight(result: ProcurementEngineResult): Promise<string | null> {
    if (!isClaudeAvailable()) return null;
    if (result.summary.totalDecisions === 0 && result.summary.criticalAlerts === 0) return null;

    try {
      const payload = await analyzeWithClaude({
        systemPrompt: `Você é um gerente de supply chain especializado em eventos de alto padrão no Brasil.
Analise os resultados do engine de procurement e forneça insights estratégicos (máximo 2 parágrafos).
Foco em: riscos críticos, oportunidades de economia, ações prioritárias.
Responda em português, tom executivo e direto.`,
        userContent: JSON.stringify({
          summary: result.summary,
          criticalAlerts: result.alerts.filter(a => a.severity === "critical"),
          blockedDecisions: result.decisions.filter(d => d.approvalStatus === "BLOCKED").length,
          overallRisk: result.gapAnalysis.overallRisk
        }),
        maxTokens: 400
      });
      return payload.text;
    } catch (err) {
      logger.warn("ProcurementAgent: Claude insight failed", { error: err });
      return null;
    }
  }
}

export const procurementAgent = new ProcurementAgent();

import { agentRegistry } from "./base-agent";
agentRegistry.register(procurementAgent);
