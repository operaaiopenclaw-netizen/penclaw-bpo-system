// ============================================================
// INVENTORY AGENT — Stock position, reservations, shortage detection
// Boundary: reads stock state, detects gaps, creates reservations.
// Does NOT select suppliers. Does NOT recommend purchases.
// Those are procurement_agent's responsibilities.
// ============================================================
import { BaseAgent, AgentExecutionContext, AgentExecutionResult, AgentAction } from "./base-agent";
import { prisma } from "../db";
import { logger } from "../utils/logger";
import { forecastEngine } from "../intelligence/forecast-engine";
import { gapEngine } from "../intelligence/gap-engine";

const SAFETY_FACTOR = 1.20;

export class InventoryAgent extends BaseAgent {
  readonly name = "inventory_agent";
  readonly description = "Posição de estoque, reservas e detecção de falta. Não faz procurement.";
  readonly defaultRiskLevel = "R2" as const;

  async execute(context: AgentExecutionContext): Promise<AgentExecutionResult> {
    const start = Date.now();
    logger.info("InventoryAgent executing", { runId: context.agentRunId });
    await this.logStep(context.agentRunId, "running", { input: context.input });

    try {
      const eventType  = String(context.input.eventType  ?? context.input.tipoEvento  ?? "corporativo");
      const numGuests  = Math.max(1, parseInt(String(context.input.numGuests ?? context.input.convidados ?? 100)));
      const durationHours = parseFloat(String(context.input.durationHours ?? context.input.duracao ?? 6)) || 6;
      const eventId    = context.input.eventId  ? String(context.input.eventId)  : undefined;
      const eventDate  = context.input.eventDate ? new Date(String(context.input.eventDate)) : undefined;

      // 1. Demand forecast
      const forecast = await forecastEngine.forecastEvent(
        context.companyId, eventType, numGuests, durationHours, eventId
      );

      // 2. Gap analysis — accounts for committed reservations from other events
      const gapResult = await gapEngine.analyse(
        context.companyId, forecast.forecasts, eventType, numGuests, eventId, eventDate
      );

      // 3. Build _actions
      const actions: AgentAction[] = [];

      // Reserve stock for this event (one action per item with available free stock)
      const reservable = gapResult.items.filter(i => i.free > 0 && eventId);
      for (const item of reservable) {
        const qtyToReserve = Math.min(item.free, item.needed);
        actions.push({
          type: "CREATE_STOCK_RESERVATION",
          payload: {
            tenantId: context.companyId,
            eventId: eventId!,
            itemCode: item.itemCode,
            itemName: item.itemName,
            quantityReserved: qtyToReserve,
            unit: item.unit,
            requiredBy: eventDate?.toISOString()
          }
        });
      }

      // Alert on critical gaps
      const critical = gapResult.items.filter(i => i.severity === "CRITICAL");
      for (const item of critical) {
        actions.push({
          type: "ALERT_RISK",
          payload: {
            code: "CRITICAL_STOCK_SHORTAGE",
            message: `Estoque crítico: ${item.itemName} — necessário ${item.needed}${item.unit}, livre ${item.free}${item.unit} (${Math.round(item.coverageRatio * 100)}% coberto)`,
            severity: "critical",
            itemCode: item.itemCode,
            gap: item.gap,
            estimatedCost: item.estimatedGapCost
          }
        });
      }

      // Alert on high gaps
      const high = gapResult.items.filter(i => i.severity === "HIGH");
      if (high.length > 0) {
        actions.push({
          type: "ALERT_RISK",
          payload: {
            code: "HIGH_STOCK_SHORTAGE",
            message: `${high.length} item(ns) com cobertura < 30%: ${high.map(i => i.itemName).join(", ")}`,
            severity: "warning",
            affectedItems: high.map(i => i.itemCode)
          }
        });
      }

      const riskLevel = gapResult.overallRisk === "CRITICAL" ? "R3"
                      : gapResult.overallRisk === "HIGH"     ? "R2"
                      : "R1";

      const output = {
        _actions: actions,
        _summary: `${gapResult.summary.shortages} item(ns) em falta de ${gapResult.summary.totalItems} analisados. Risco: ${gapResult.overallRisk}. Custo estimado de procurement: R$${gapResult.summary.estimatedTotalProcurementCost.toLocaleString("pt-BR")}.`,

        stockPosition: {
          eventType,
          guestCount: numGuests,
          forecastConfidence: forecast.overallConfidence,
          totalItems: gapResult.summary.totalItems,
          sufficient: gapResult.summary.sufficient,
          shortages: gapResult.summary.shortages,
          critical: gapResult.summary.critical,
          overallRisk: gapResult.overallRisk,
          estimatedProcurementCost: gapResult.summary.estimatedTotalProcurementCost,
        },

        gaps: gapResult.items
          .filter(i => i.severity !== "OK")
          .map(i => ({
            itemCode: i.itemCode,
            itemName: i.itemName,
            needed: i.needed,
            available: i.available,
            committed: i.committed,
            free: i.free,
            gap: i.gap,
            severity: i.severity,
            estimatedCost: i.estimatedGapCost,
          })),

        sufficient: gapResult.items
          .filter(i => i.severity === "OK")
          .map(i => ({ itemCode: i.itemCode, itemName: i.itemName, free: i.free, unit: i.unit })),

        reservationsCreated: reservable.length,
      };

      await this.logStep(context.agentRunId, "completed", { output });
      logger.info("InventoryAgent completed", {
        runId: context.agentRunId,
        risk: gapResult.overallRisk,
        gaps: gapResult.summary.shortages,
        actions: actions.length
      });

      return { success: true, output, riskLevel, latencyMs: Date.now() - start };

    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      await this.logStep(context.agentRunId, "failed", { error: msg });
      logger.error("InventoryAgent failed", { error: msg });
      return {
        success: false,
        output: { _actions: [], _summary: `Falha: ${msg}`, error: msg },
        riskLevel: "R3",
        latencyMs: Date.now() - start
      };
    }
  }
}

export const inventoryAgent = new InventoryAgent();

import { agentRegistry } from "./base-agent";
agentRegistry.register(inventoryAgent);
