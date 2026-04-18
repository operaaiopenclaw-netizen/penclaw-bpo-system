// ============================================================
// INSIGHTS ENGINE — Converts decisions into structured, actionable insights
// ============================================================
import { prisma } from "../db";
import { logger } from "../utils/logger";
import {
  StructuredInsight,
  OperationalDecisionPayload,
  PurchaseOrderDecision,
  RiskAlertDecision,
  ReorderDecision,
  InsightType,
} from "./types";

function uuid(): string {
  return crypto.randomUUID();
}

export class InsightsEngine {
  /**
   * Generate structured insights from a batch of decisions.
   * Each insight is measurable, actionable, and connected to system execution.
   */
  async generateFromDecisions(
    tenantId: string,
    decisions: OperationalDecisionPayload[]
  ): Promise<StructuredInsight[]> {
    const purchaseOrders = decisions.filter(
      d => d.action === "CREATE_PURCHASE_ORDER"
    ) as PurchaseOrderDecision[];
    const riskAlerts = decisions.filter(
      d => d.action === "ALERT_RISK"
    ) as RiskAlertDecision[];
    const reorders = decisions.filter(
      d => d.action === "SUGGEST_REORDER"
    ) as ReorderDecision[];

    // Run DB-backed insights in parallel
    const [marginInsight, procEfficiencyInsight] = await Promise.all([
      this.marginInsight(tenantId),
      this.procurementEfficiencyInsight(tenantId),
    ]);

    const insights: StructuredInsight[] = [];

    // 1. Procurement execution insight
    if (purchaseOrders.length > 0) {
      insights.push(this.procurementInsight(purchaseOrders));
    }

    // 2. Critical stock alerts
    const criticals = riskAlerts.filter(r => r.severity === "CRITICAL");
    if (criticals.length > 0) {
      insights.push(this.criticalStockInsight(criticals));
    }

    // 3. Non-critical risk alerts (HIGH + MEDIUM)
    const nonCriticals = riskAlerts.filter(
      r => r.severity !== "CRITICAL" && r.type !== "SUPPLIER_FAILURE"
    );
    if (nonCriticals.length > 0) {
      insights.push(this.riskAlertInsight(nonCriticals));
    }

    // 4. Supplier health
    const supplierAlerts = riskAlerts.filter(
      r => r.type === "SUPPLIER_FAILURE" || r.type === "PRICE_SPIKE"
    );
    if (supplierAlerts.length > 0) {
      insights.push(this.supplierInsight(supplierAlerts));
    }

    // 5. Reorder summary
    if (reorders.length > 0) {
      insights.push(this.reorderInsight(reorders));
    }

    // 6. Financial margin analysis
    if (marginInsight) insights.push(marginInsight);

    // 7. Procurement efficiency
    if (procEfficiencyInsight) insights.push(procEfficiencyInsight);

    logger.debug("InsightsEngine: generated insights", { count: insights.length });

    return insights;
  }

  /**
   * Build a full report from persisted pending decisions (no new cycle needed).
   */
  async generateFullReport(tenantId: string): Promise<StructuredInsight[]> {
    const pending = await prisma.operationalDecision.findMany({
      where: {
        tenantId,
        status: "pending",
        OR: [{ expiresAt: null }, { expiresAt: { gte: new Date() } }],
      },
      orderBy: { createdAt: "desc" },
      take: 100,
    });

    const payloads = pending.map(d => d.payload as unknown as OperationalDecisionPayload);
    return this.generateFromDecisions(tenantId, payloads);
  }

  // ---- Per-category insight builders ----

  private procurementInsight(pos: PurchaseOrderDecision[]): StructuredInsight {
    const totalCost = pos.reduce((s, po) => s + po.totalEstimatedCost, 0);
    const highConf = pos.filter(po => po.confidence >= 0.75);
    const nearestDeadlineDays = Math.min(
      ...pos.map(po =>
        Math.ceil((new Date(po.deadline).getTime() - Date.now()) / 86_400_000)
      )
    );
    const avgConf = pos.reduce((s, po) => s + po.confidence, 0) / pos.length;

    return {
      id: uuid(),
      type: "PROCUREMENT",
      message: `${pos.length} ordem(ns) de compra identificada(s) — custo estimado: R$ ${fmt(totalCost)}`,
      impact: {
        financial: round2(totalCost),
        operational: `${pos.length} fornecedor(es) envolvido(s). Prazo mais próximo: ${nearestDeadlineDays} dia(s).`,
        urgency: nearestDeadlineDays <= 2 ? "immediate" : nearestDeadlineDays <= 7 ? "within_week" : "within_month",
      },
      recommendation:
        highConf.length > 0
          ? `Executar imediatamente: ${highConf.length} pedido(s) com confiança ≥ 75% (R$ ${fmt(highConf.reduce((s, po) => s + po.totalEstimatedCost, 0))}). Revisar: ${pos.length - highConf.length} pedido(s) com confiança menor.`
          : `Revisar todos os ${pos.length} pedido(s) antes de executar — confiança média abaixo de 75%.`,
      confidence: round2(avgConf),
      createdAt: new Date(),
    };
  }

  private criticalStockInsight(alerts: RiskAlertDecision[]): StructuredInsight {
    const totalImpact = alerts.reduce((s, a) => s + (a.financialImpact ?? 0), 0);
    const affectedEvents = [...new Set(alerts.flatMap(a => a.affectedEventId ? [a.affectedEventId] : []))];
    const items = [...new Set(alerts.flatMap(a => a.affectedItems ?? []))];

    return {
      id: uuid(),
      type: "STOCK",
      message: `${alerts.length} alerta(s) CRÍTICO(S): ${items.length} item(ns) com estoque insuficiente${affectedEvents.length > 0 ? ` — afeta ${affectedEvents.length} evento(s)` : ""}`,
      impact: {
        financial: totalImpact > 0 ? round2(totalImpact) : undefined,
        operational: "Risco direto de falha na execução de eventos confirmados. Possível cancelamento de serviço.",
        urgency: "immediate",
      },
      recommendation: alerts
        .map(a => a.recommendedAction)
        .filter((v, i, arr) => arr.indexOf(v) === i)
        .slice(0, 3)
        .join(" | "),
      confidence: 0.97,
      createdAt: new Date(),
    };
  }

  private riskAlertInsight(alerts: RiskAlertDecision[]): StructuredInsight {
    const highSeverity = alerts.filter(a => a.severity === "HIGH");
    const byType = groupBy(alerts, a => a.type);

    return {
      id: uuid(),
      type: "OPERATIONAL",
      message: `${alerts.length} alerta(s) operacional(is): ${Object.keys(byType).map(t => `${byType[t].length}× ${t}`).join(", ")}`,
      impact: {
        operational: `${highSeverity.length} alerta(s) de alta severidade requerem ação esta semana`,
        urgency: highSeverity.length > 0 ? "within_week" : "within_month",
      },
      recommendation: `Priorizar ${highSeverity.length} alertas HIGH. Revisar impacto nos eventos afetados e activar contingência.`,
      confidence: 0.88,
      createdAt: new Date(),
    };
  }

  private supplierInsight(alerts: RiskAlertDecision[]): StructuredInsight {
    const failures = alerts.filter(a => a.type === "SUPPLIER_FAILURE");
    const spikes = alerts.filter(a => a.type === "PRICE_SPIKE");

    return {
      id: uuid(),
      type: "SUPPLIER",
      message: `${failures.length} fornecedor(es) com risco operacional + ${spikes.length} alta(s) de preço detectada(s)`,
      impact: {
        operational: failures.length > 0
          ? `${failures.length} fornecedor(es) abaixo do threshold de qualidade — risco de falha em entregas futuras`
          : undefined,
        urgency: failures.length > 0 ? "within_week" : "within_month",
      },
      recommendation:
        failures.length > 0
          ? `Substituir ou colocar em probatório: ${failures.length} fornecedor(es). Cotar alternativas nas categorias afetadas. ${spikes.length > 0 ? `Renegociar preços com ${spikes.length} fornecedor(es) com alta.` : ""}`
          : `Monitorar tendência de preços. Cotar ${spikes.length} fornecedor(es) alternativo(s) para benchmark.`,
      confidence: 0.84,
      createdAt: new Date(),
    };
  }

  private reorderInsight(reorders: ReorderDecision[]): StructuredInsight {
    const high = reorders.filter(r => r.urgency === "high");
    const medium = reorders.filter(r => r.urgency === "medium");
    const totalCost = reorders.reduce((s, r) => s + r.estimatedCost, 0);

    return {
      id: uuid(),
      type: "STOCK",
      message: `${reorders.length} item(ns) atingiram ponto de reposição (${high.length} urgentes, ${medium.length} médios) — custo estimado R$ ${fmt(totalCost)}`,
      impact: {
        financial: round2(totalCost),
        operational: "Manutenção do estoque operacional mínimo para ciclos futuros",
        urgency: high.length > 0 ? "within_week" : "within_month",
      },
      recommendation: high.length > 0
        ? `Incluir no próximo pedido de compra: ${high.map(r => r.itemName).join(", ")} (urgente). Programar demais no ciclo semanal regular.`
        : `Programar reposição de ${reorders.length} item(ns) no ciclo semanal de compras.`,
      confidence: 0.90,
      createdAt: new Date(),
    };
  }

  // ---- DB-backed insights ----

  private async marginInsight(tenantId: string): Promise<StructuredInsight | null> {
    try {
      const events = await prisma.event.findMany({
        where: {
          tenantId,
          marginPct: { not: null },
          status: { in: ["CLOSED", "closed", "completed", "ANALYZED"] },
        },
        orderBy: { eventDate: "desc" },
        take: 12,
        select: { marginPct: true, netProfit: true, name: true, eventType: true },
      });

      if (events.length < 3) return null;

      const margins = events.map(e => e.marginPct ?? 0);
      const avg = margins.reduce((s, m) => s + m, 0) / margins.length;
      const negatives = events.filter(e => (e.marginPct ?? 0) < 0);
      const below20 = events.filter(e => (e.marginPct ?? 0) < 20 && (e.marginPct ?? 0) >= 0);
      const lossTotal = Math.abs(
        negatives.reduce((s, e) => s + (e.netProfit ?? 0), 0)
      );

      // Trend: compare last 3 vs previous events
      const recent = margins.slice(0, 3);
      const older = margins.slice(3);
      const recentAvg = recent.reduce((s, m) => s + m, 0) / recent.length;
      const olderAvg = older.length > 0 ? older.reduce((s, m) => s + m, 0) / older.length : recentAvg;
      const trend = recentAvg - olderAvg; // positive = improving

      const urgency: StructuredInsight["impact"]["urgency"] =
        negatives.length >= 2 ? "immediate" : avg < 15 ? "within_week" : "informational";

      return {
        id: uuid(),
        type: "FINANCIAL",
        message: `Margem média (${events.length} eventos): ${avg.toFixed(1)}%${trend !== 0 ? ` (tendência: ${trend > 0 ? "+" : ""}${trend.toFixed(1)}pp)` : ""}${negatives.length > 0 ? ` — ${negatives.length} evento(s) com margem negativa` : ""}`,
        impact: {
          financial: negatives.length > 0 ? round2(lossTotal) : undefined,
          operational: avg < 20
            ? `${below20.length + negatives.length} evento(s) abaixo do target de 20% — revisar CMV ou precificação`
            : "Margem dentro do target operacional (≥ 20%)",
          urgency,
        },
        recommendation: avg < 20
          ? `Identificar categorias de custo que puxam CMV acima do esperado. Revisar precificação nos ${below20.length + negatives.length} evento(s) abaixo do target. Benchmark: casamentos target ≥ 22%, corporativo ≥ 18%.`
          : `Margem saudável. Continuar monitoramento mensal. Avaliar oportunidade de expansão de volume.`,
        confidence: 0.95,
        createdAt: new Date(),
      };
    } catch (err) {
      logger.warn({ err }, "InsightsEngine: marginInsight failed");
      return null;
    }
  }

  private async procurementEfficiencyInsight(
    tenantId: string
  ): Promise<StructuredInsight | null> {
    try {
      const orders = await prisma.purchaseOrder.findMany({
        where: { tenantId, status: "delivered" },
        orderBy: { createdAt: "desc" },
        take: 20,
        select: {
          confirmedDelivery: true,
          actualDelivery: true,
          totalEstimatedCost: true,
          totalActualCost: true,
        },
      });

      if (orders.length < 3) return null;

      const late = orders.filter(o =>
        o.confirmedDelivery && o.actualDelivery && o.actualDelivery > o.confirmedDelivery
      );
      const onTimeRate = ((orders.length - late.length) / orders.length) * 100;

      const variances = orders
        .filter(o => o.totalEstimatedCost && o.totalActualCost)
        .map(o =>
          ((o.totalActualCost! - o.totalEstimatedCost!) / o.totalEstimatedCost!) * 100
        );
      const avgVariance =
        variances.length > 0
          ? variances.reduce((s, v) => s + v, 0) / variances.length
          : 0;

      const urgency: StructuredInsight["impact"]["urgency"] =
        onTimeRate < 70 ? "within_week" : "informational";

      return {
        id: uuid(),
        type: "PROCUREMENT",
        message: `Eficiência de compras (${orders.length} pedidos): ${onTimeRate.toFixed(0)}% no prazo, variação média de custo: ${avgVariance > 0 ? "+" : ""}${avgVariance.toFixed(1)}%`,
        impact: {
          operational: `${late.length} entrega(s) atrasada(s). ${avgVariance > 5 ? "Custo real acima do estimado em média." : "Custo dentro do esperado."}`,
          urgency,
        },
        recommendation:
          onTimeRate < 80
            ? `Renegociar SLAs com fornecedores com atraso > 30%. Avaliar fornecedores alternativos para categorias críticas.`
            : avgVariance > 10
            ? `Variação de custo de ${avgVariance.toFixed(1)}% acima do normal. Revisar estimativas de preço e considerar contratos de preço fixo.`
            : "Processo de compras eficiente. Manter monitoramento de SLA mensal.",
        confidence: 0.88,
        createdAt: new Date(),
      };
    } catch (err) {
      logger.warn({ err }, "InsightsEngine: procurementEfficiencyInsight failed");
      return null;
    }
  }
}

// ---- helpers ----
function fmt(n: number): string {
  return n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function round2(n: number) { return Math.round(n * 100) / 100; }
function groupBy<T>(arr: T[], fn: (t: T) => string): Record<string, T[]> {
  return arr.reduce((acc, item) => {
    const key = fn(item);
    (acc[key] = acc[key] ?? []).push(item);
    return acc;
  }, {} as Record<string, T[]>);
}

export const insightsEngine = new InsightsEngine();
