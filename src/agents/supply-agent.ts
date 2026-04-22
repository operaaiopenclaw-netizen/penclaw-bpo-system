// ============================================================
// SUPPLY AGENT — Powered by ForecastEngine
// ============================================================
import { BaseAgent, AgentExecutionContext, AgentExecutionResult } from "./base-agent";
import { logger } from "../utils/logger";
import { forecastEngine } from "../intelligence/forecast-engine";

// Unit price table (BRL) — used when no inventory record exists
const UNIT_PRICES: Record<string, number> = {
  cerveja:   12.00, // per litre (≈ 2× 600ml long-necks)
  soft:       6.50,
  agua:       3.20,
  destilado: 95.00,
  gelo:       2.80, // per kg
  espumante: 55.00,
  suco:       8.00,
  cafe:      18.00,
};

export class SupplyAgent extends BaseAgent {
  readonly name = "supply_agent";
  readonly description = "Previsão de consumo e lista de compras com forecast multi-fator";
  readonly defaultRiskLevel = "R2" as const;

  async execute(context: AgentExecutionContext): Promise<AgentExecutionResult> {
    const start = Date.now();
    logger.info("SupplyAgent executing", {
      runId: context.agentRunId,
      companyId: context.companyId,
    });
    await this.logStep(context.agentRunId, "running", { input: context.input });

    try {
      const eventType = String(
        context.input.eventType ?? context.input.tipo ?? "corporativo"
      ).toLowerCase();
      const numGuests = parseInt(
        String(context.input.numGuests ?? context.input.pessoas ?? 100),
        10
      ) || 100;
      const durationHours = parseFloat(
        String(context.input.durationHours ?? context.input.duracao ?? 6)
      ) || 6;

      if (!eventType || numGuests <= 0) {
        return {
          success: false,
          output: { error: "eventType e numGuests são obrigatórios" },
          riskLevel: this.defaultRiskLevel,
          latencyMs: Date.now() - start,
        };
      }

      // Use the intelligence forecast engine (includes historical data)
      const forecast = await forecastEngine.forecastEvent(
        context.companyId,
        eventType,
        numGuests,
        durationHours
      );

      // Build purchase list from forecast
      const purchaseList = this.buildPurchaseList(forecast.forecasts);

      // Cost estimate
      const costEstimate = this.estimateCost(forecast.forecasts);

      const result = {
        event: { type: eventType, guests: numGuests, durationHours },
        forecast: {
          overallConfidence: forecast.overallConfidence,
          basedOnHistoricalPoints: Math.max(
            ...forecast.forecasts.map(f => f.historicalDataPoints),
            0
          ),
          items: forecast.forecasts.map(f => ({
            item: f.itemName,
            estimated: f.estimatedConsumption,
            min: f.minConsumption,
            max: f.maxConsumption,
            unit: f.unit,
            confidence: f.confidenceScore,
            perGuestRate: f.perGuestRate,
          })),
        },
        purchaseList,
        costEstimate,
        safetyMargin: "20% aplicado no máximo previsto",
        observations: this.buildObservations(
          eventType,
          numGuests,
          forecast.overallConfidence
        ),
      };

      await this.logStep(context.agentRunId, "completed", { output: result });
      logger.info("SupplyAgent completed", { runId: context.agentRunId });

      return {
        success: true,
        output: result,
        riskLevel: costEstimate.total > 50_000 ? "R3" : this.defaultRiskLevel,
        latencyMs: Date.now() - start,
      };
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      logger.error("SupplyAgent failed", { error: msg });
      await this.logStep(context.agentRunId, "failed", { error: msg });
      return {
        success: false,
        output: { error: msg },
        riskLevel: this.defaultRiskLevel,
        latencyMs: Date.now() - start,
      };
    }
  }

  private buildPurchaseList(
    forecasts: Awaited<ReturnType<typeof forecastEngine.forecastEvent>>["forecasts"]
  ) {
    return forecasts
      .filter(f => f.maxConsumption > 0)
      .map(f => {
        // Use worst-case (maxConsumption) for purchase planning
        const qty = Math.ceil(f.maxConsumption * 1.2); // +20% safety

        return {
          item: f.itemName,
          category: f.category,
          quantityMin: f.minConsumption,
          quantityMax: f.maxConsumption,
          quantityToBuy: qty,
          unit: f.unit,
          confidenceScore: f.confidenceScore,
          urgency: f.confidenceScore >= 0.80 ? "confirmed" : "estimated",
        };
      });
  }

  private estimateCost(
    forecasts: Awaited<ReturnType<typeof forecastEngine.forecastEvent>>["forecasts"]
  ) {
    const lineItems = forecasts
      .filter(f => f.maxConsumption > 0)
      .map(f => {
        const price = UNIT_PRICES[f.itemCode] ?? 0;
        const qty = Math.ceil(f.maxConsumption * 1.2);
        return {
          item: f.itemName,
          quantity: qty,
          unit: f.unit,
          unitPrice: price,
          subtotal: Math.round(qty * price * 100) / 100,
        };
      });

    const total = lineItems.reduce((s, l) => s + l.subtotal, 0);

    return {
      total: Math.round(total * 100) / 100,
      lineItems,
      note: "Preços baseados em tabela padrão. Cotação real pode variar.",
    };
  }

  private buildObservations(
    eventType: string,
    guests: number,
    confidence: number
  ): string[] {
    const obs: string[] = [];

    if (confidence < 0.55) {
      obs.push("⚠️ Sem histórico de eventos similares — usando modelo base. Registre consumo real pós-evento para melhorar previsões.");
    } else if (confidence >= 0.85) {
      obs.push("✓ Alta confiança: previsão baseada em histórico robusto.");
    } else {
      obs.push(`ℹ️ Confiança moderada (${Math.round(confidence * 100)}%): poucos eventos anteriores similares.`);
    }

    if (guests > 300) {
      obs.push("📍 Evento grande (>300 convidados): eficiência de escala aplicada. Pedido com 96h antecedência recomendado.");
    } else if (guests > 200) {
      obs.push("📍 Evento médio-grande: pedido com 72h antecedência recomendado.");
    }

    if (eventType === "formatura") {
      obs.push("🎓 Formatura: consumo de cerveja historicamente 20% acima da média. Confirmar com organizador.");
    }
    if (eventType === "casamento") {
      obs.push("💍 Casamento: garantir estoque de espumante para brinde. Validar preferência do cliente.");
    }
    if (eventType === "confraternizacao") {
      obs.push("🎉 Confraternização: maior consumo de destilados. Considerar open bar parcial.");
    }

    return obs;
  }
}

export const supplyAgent = new SupplyAgent();

import { agentRegistry } from "./base-agent";
agentRegistry.register(supplyAgent);
