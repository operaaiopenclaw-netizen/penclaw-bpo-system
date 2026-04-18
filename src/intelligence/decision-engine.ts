// ============================================================
// DECISION ENGINE — Converts analysis into executable actions
// ============================================================
import { prisma } from "../db";
import { logger } from "../utils/logger";
import { forecastEngine } from "./forecast-engine";
import { supplierIntelligence } from "./supplier-intelligence";
import { insightsEngine } from "./insights-engine";
import {
  OperationalDecisionPayload,
  PurchaseOrderDecision,
  RiskAlertDecision,
  ReorderDecision,
  DecisionCycleResult,
  RiskSeverity,
} from "./types";

// ---- Configuration constants ----
/** Days ahead to look for upcoming events */
const LOOKAHEAD_DAYS = 14;
/** Safety multiplier on top of forecast max */
const SAFETY_STOCK_FACTOR = 1.20;
/** Minimum forecast confidence required to auto-generate a PO (vs alert-only) */
const AUTO_PO_CONFIDENCE_THRESHOLD = 0.60;
/** Minimum supplier score to be eligible for auto-PO */
const MIN_SUPPLIER_SCORE_FOR_PO = 55;

export class DecisionEngine {
  /**
   * Run a full decision cycle for a tenant.
   * All evaluation steps run in parallel; results are deduplicated before persisting.
   */
  async runCycle(tenantId: string): Promise<DecisionCycleResult> {
    const start = Date.now();
    logger.info({ tenantId }, "DecisionEngine: cycle start");

    // Three evaluation dimensions run in parallel
    const [stockDecisions, eventDecisions, supplierDecisions] = await Promise.all([
      this.evaluateStockHealth(tenantId),
      this.evaluateUpcomingEventNeeds(tenantId),
      this.evaluateSupplierRisks(tenantId),
    ]);

    const all = this.deduplicate([
      ...stockDecisions,
      ...eventDecisions,
      ...supplierDecisions,
    ]);

    // Persist to DB and generate insights in parallel
    const [, insights] = await Promise.all([
      this.persistDecisions(tenantId, all),
      insightsEngine.generateFromDecisions(tenantId, all),
    ]);

    const pos    = all.filter(d => d.action === "CREATE_PURCHASE_ORDER") as PurchaseOrderDecision[];
    const alerts = all.filter(d => d.action === "ALERT_RISK") as RiskAlertDecision[];
    const reorders = all.filter(d => d.action === "SUGGEST_REORDER") as ReorderDecision[];
    const critical = alerts.filter(a => a.severity === "CRITICAL");

    const result: DecisionCycleResult = {
      tenantId,
      cycleRunAt: new Date(),
      decisions: all,
      insights,
      summary: {
        totalDecisions: all.length,
        purchaseOrders: pos.length,
        riskAlerts: alerts.length,
        criticalAlerts: critical.length,
        reorderSuggestions: reorders.length,
        estimatedProcurementCost: round2(
          pos.reduce((s, d) => s + d.totalEstimatedCost, 0)
        ),
      },
      durationMs: Date.now() - start,
    };

    logger.info({ tenantId, ...result.summary, durationMs: result.durationMs }, "DecisionEngine: cycle complete");

    return result;
  }

  // ----------------------------------------------------------
  // 1. Evaluate inventory health against min stock levels
  // ----------------------------------------------------------
  private async evaluateStockHealth(
    tenantId: string
  ): Promise<OperationalDecisionPayload[]> {
    const items = await prisma.inventoryItem.findMany({
      where: { minStockLevel: { not: null } },
    });

    const decisions: OperationalDecisionPayload[] = [];

    for (const item of items) {
      const min = item.minStockLevel!;
      const reorder = item.reorderPoint ?? min * 1.5;
      const current = item.currentQty;
      const unitPrice = item.unitPrice ?? 0;

      if (current < min * 0.5) {
        // CRITICAL — below 50% of minimum
        const replenish = Math.ceil(min * SAFETY_STOCK_FACTOR - current);
        decisions.push({
          action: "ALERT_RISK",
          type: "STOCK_SHORTAGE",
          severity: "CRITICAL",
          affectedItems: [item.code],
          message: `Estoque CRÍTICO: ${item.name} — atual: ${current}${item.unit} | mínimo: ${min}${item.unit} (${pct(current, min)}% do mínimo)`,
          financialImpact: round2(replenish * unitPrice),
          recommendedAction: `Reposição emergencial de ${replenish} ${item.unit} de ${item.name} (fornecedor: ${item.supplier ?? "não definido"})`,
          deadline: new Date(Date.now() + 24 * 3_600_000),
          confidence: 0.98,
          riskLevel: "R3",
        } satisfies RiskAlertDecision);
      } else if (current < min) {
        // LOW — between 50-100% of minimum
        const replenish = Math.ceil(reorder * SAFETY_STOCK_FACTOR - current);
        const urgency: ReorderDecision["urgency"] =
          current < min * 0.75 ? "high" : "medium";
        decisions.push({
          action: "SUGGEST_REORDER",
          itemCode: item.code,
          itemName: item.name,
          currentQty: current,
          reorderPoint: reorder,
          suggestedQty: replenish,
          unit: item.unit,
          estimatedCost: round2(replenish * unitPrice),
          urgency,
          confidence: 0.92,
          riskLevel: urgency === "high" ? "R2" : "R1",
        } satisfies ReorderDecision);
      } else if (current <= reorder) {
        // AT REORDER POINT — proactive restocking
        decisions.push({
          action: "SUGGEST_REORDER",
          itemCode: item.code,
          itemName: item.name,
          currentQty: current,
          reorderPoint: reorder,
          suggestedQty: Math.ceil(reorder * SAFETY_STOCK_FACTOR),
          unit: item.unit,
          estimatedCost: round2(Math.ceil(reorder * SAFETY_STOCK_FACTOR) * unitPrice),
          urgency: "low",
          confidence: 0.85,
          riskLevel: "R1",
        } satisfies ReorderDecision);
      }
    }

    return decisions;
  }

  // ----------------------------------------------------------
  // 2. Evaluate upcoming events — forecast + gap analysis
  // ----------------------------------------------------------
  private async evaluateUpcomingEventNeeds(
    tenantId: string
  ): Promise<OperationalDecisionPayload[]> {
    const lookahead = new Date(Date.now() + LOOKAHEAD_DAYS * 86_400_000);

    const [events, inventory, suppliers] = await Promise.all([
      prisma.event.findMany({
        where: {
          tenantId,
          eventDate: { gte: new Date(), lte: lookahead },
          status: {
            in: ["planned", "contracted", "PLANNED", "CONTRACTED",
                 "READY_FOR_PRODUCTION", "IN_PRODUCTION"],
          },
        },
        orderBy: { eventDate: "asc" },
      }),
      prisma.inventoryItem.findMany(),
      prisma.supplier.findMany({ where: { tenantId, isActive: true } }),
    ]);

    if (events.length === 0) return [];

    const decisions: OperationalDecisionPayload[] = [];

    for (const event of events) {
      if (!event.eventDate) continue;

      try {
        const daysUntil = Math.ceil(
          (event.eventDate.getTime() - Date.now()) / 86_400_000
        );

        const forecast = await forecastEngine.forecastEvent(
          tenantId,
          event.eventType ?? "corporativo",
          event.guests ?? 100,
          6,
          event.id
        );

        // Identify items where current stock < worst-case consumption × safety factor
        const shortfalls = forecast.forecasts
          .map(fc => {
            const inv = inventory.find(
              i =>
                i.code.toLowerCase().includes(fc.itemCode) ||
                i.name.toLowerCase().includes(fc.itemCode)
            );
            const available = inv?.currentQty ?? 0;
            const needed = fc.maxConsumption * SAFETY_STOCK_FACTOR;
            if (available >= needed) return null;
            return {
              itemCode: fc.itemCode,
              itemName: fc.itemName,
              category: fc.category,
              needed: Math.ceil(needed),
              available,
              gap: Math.ceil(needed - available),
              unit: fc.unit,
              unitPrice: inv?.unitPrice ?? 0,
            };
          })
          .filter(Boolean) as NonNullable<
          ReturnType<typeof this.buildShortfall>
        >[];

        if (shortfalls.length === 0) continue;

        const severity = daysToSeverity(daysUntil);
        const financialImpact = shortfalls.reduce(
          (s, sf) => s + sf.gap * sf.unitPrice,
          0
        );

        // Auto-generate PO when: confidence high enough + suppliers available + event soon enough
        if (
          suppliers.length > 0 &&
          forecast.overallConfidence >= AUTO_PO_CONFIDENCE_THRESHOLD &&
          daysUntil <= 12
        ) {
          const primaryCategory = shortfalls[0].category;
          const rankedSuppliers = await supplierIntelligence.rankSuppliersForItem(
            tenantId,
            primaryCategory
          );
          const best = rankedSuppliers.find(
            s => s.finalScore >= MIN_SUPPLIER_SCORE_FOR_PO
          );

          if (best) {
            decisions.push({
              action: "CREATE_PURCHASE_ORDER",
              supplierId: best.supplierId,
              supplierName: best.supplierName,
              items: shortfalls.map(sf => ({
                itemCode: sf.itemCode,
                itemName: sf.itemName,
                category: sf.category,
                quantityNeeded: sf.gap,
                unit: sf.unit,
                estimatedUnitPrice: sf.unitPrice,
                estimatedTotal: round2(sf.gap * sf.unitPrice),
              })),
              totalEstimatedCost: round2(financialImpact),
              deadline: new Date(event.eventDate.getTime() - 2 * 86_400_000),
              relatedEventId: event.id,
              confidence: forecast.overallConfidence,
              riskLevel: daysUntil <= 3 ? "R3" : "R2",
              justification: `Evento "${event.name}" (${event.eventType}, ${event.guests} convidados) em ${daysUntil} dia(s) — ${shortfalls.length} item(ns) abaixo do estoque necessário`,
            } satisfies PurchaseOrderDecision);
            continue;
          }
        }

        // Fallback: risk alert
        decisions.push({
          action: "ALERT_RISK",
          type: "STOCK_SHORTAGE",
          severity,
          affectedEventId: event.id,
          affectedItems: shortfalls.map(sf => sf.itemCode),
          message: `Evento "${event.name}" em ${daysUntil} dia(s) — ${shortfalls.length} item(ns) com estoque insuficiente (gap total: R$ ${fmt(financialImpact)})`,
          financialImpact: round2(financialImpact),
          recommendedAction:
            suppliers.length === 0
              ? "Cadastrar fornecedores para permitir geração automática de OC"
              : "Confirmar fornecedor manualmente e emitir OC — confiança da previsão abaixo do threshold",
          deadline: new Date(event.eventDate.getTime() - 2 * 86_400_000),
          confidence: forecast.overallConfidence,
          riskLevel: severity === "CRITICAL" ? "R3" : "R2",
        } satisfies RiskAlertDecision);
      } catch (err) {
        logger.warn({ eventId: event.id, err }, "DecisionEngine: event evaluation failed");
      }
    }

    return decisions;
  }

  // ----------------------------------------------------------
  // 3. Evaluate supplier portfolio risks
  // ----------------------------------------------------------
  private async evaluateSupplierRisks(
    tenantId: string
  ): Promise<OperationalDecisionPayload[]> {
    const scores = await supplierIntelligence.getAllSupplierScores(tenantId);
    const decisions: OperationalDecisionPayload[] = [];

    for (const score of scores) {
      if (score.recommendation === "avoid") {
        decisions.push({
          action: "ALERT_RISK",
          type: "SUPPLIER_FAILURE",
          severity: "HIGH",
          message: `Fornecedor "${score.supplierName}" abaixo do threshold: score ${score.finalScore.toFixed(0)}/100 | entrega: ${score.deliveryReliability}% | atraso: ${(score.delayRate * 100).toFixed(0)}%`,
          recommendedAction: `Substituir ${score.supplierName} para: ${score.categories.join(", ")}. Cotar alternativas com score > 60.`,
          deadline: new Date(Date.now() + 7 * 86_400_000),
          confidence: 0.87,
          riskLevel: "R2",
        } satisfies RiskAlertDecision);
      }

      if (score.priceTrend > 15 && score.totalOrders >= 3) {
        decisions.push({
          action: "ALERT_RISK",
          type: "PRICE_SPIKE",
          severity: score.priceTrend > 30 ? "HIGH" : "MEDIUM",
          message: `Alta de preço em "${score.supplierName}": +${score.priceTrend.toFixed(1)}% vs pedidos anteriores`,
          recommendedAction: `Renegociar contrato ou cotar alternativas. Impacto estimado de CMV: +${(score.priceTrend / 2).toFixed(1)}% se não revertido.`,
          deadline: new Date(Date.now() + 3 * 86_400_000),
          confidence: 0.79,
          riskLevel: "R2",
        } satisfies RiskAlertDecision);
      }
    }

    return decisions;
  }

  // ----------------------------------------------------------
  // Execute a pending decision (CREATE_PURCHASE_ORDER → real PO)
  // ----------------------------------------------------------
  async executeDecision(
    decisionId: string,
    executedBy: string
  ): Promise<{ success: boolean; message: string; orderId?: string }> {
    const decision = await prisma.operationalDecision.findUnique({
      where: { id: decisionId },
    });

    if (!decision)
      return { success: false, message: "Decision not found" };
    if (decision.status !== "pending")
      return { success: false, message: `Decision already in status: ${decision.status}` };

    const payload = decision.payload as unknown as OperationalDecisionPayload;

    if (payload.action === "CREATE_PURCHASE_ORDER") {
      const poPayload = payload as PurchaseOrderDecision;

      const { po } = await prisma.$transaction(async tx => {
        const po = await tx.purchaseOrder.create({
          data: {
            tenantId: decision.tenantId,
            supplierId: poPayload.supplierId,
            status: "sent",
            sourceDecisionId: decision.id,
            totalEstimatedCost: poPayload.totalEstimatedCost,
            requestedDelivery: poPayload.deadline,
            relatedEventId: poPayload.relatedEventId ?? null,
            notes: poPayload.justification,
          },
        });

        await tx.purchaseOrderItem.createMany({
          data: poPayload.items.map(item => ({
            purchaseOrderId: po.id,
            itemCode: item.itemCode,
            itemName: item.itemName,
            category: item.category,
            quantityOrdered: item.quantityNeeded,
            unit: item.unit,
            unitPrice: item.estimatedUnitPrice,
            totalPrice: item.estimatedTotal,
          })),
        });

        await tx.operationalDecision.update({
          where: { id: decisionId },
          data: {
            status: "executed",
            executedAt: new Date(),
            executedBy,
            relatedOrderId: po.id,
          },
        });

        return { po };
      });

      logger.info({ decisionId, orderId: po.id, supplier: poPayload.supplierName }, "DecisionEngine: PO executed");

      return {
        success: true,
        message: `Purchase order criado — fornecedor: ${poPayload.supplierName}, itens: ${poPayload.items.length}, custo: R$ ${fmt(poPayload.totalEstimatedCost)}`,
        orderId: po.id,
      };
    }

    // Non-PO decisions: mark executed
    await prisma.operationalDecision.update({
      where: { id: decisionId },
      data: { status: "executed", executedAt: new Date(), executedBy },
    });

    return {
      success: true,
      message: `Decision ${payload.action} marcada como executada`,
    };
  }

  // ----------------------------------------------------------
  // Helpers
  // ----------------------------------------------------------

  private deduplicate(
    decisions: OperationalDecisionPayload[]
  ): OperationalDecisionPayload[] {
    const seen = new Set<string>();
    return decisions.filter(d => {
      const key =
        d.action === "CREATE_PURCHASE_ORDER"
          ? `PO:${d.supplierId}:${d.relatedEventId ?? "stock"}`
          : d.action === "ALERT_RISK"
          ? `ALERT:${d.type}:${d.affectedEventId ?? (d.affectedItems ?? []).sort().join(",")}`
          : `REORDER:${d.itemCode}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  private async persistDecisions(
    tenantId: string,
    decisions: OperationalDecisionPayload[]
  ): Promise<void> {
    if (decisions.length === 0) return;

    const records = decisions.map(d => {
      const confidence =
        d.action === "CREATE_PURCHASE_ORDER"
          ? d.confidence
          : d.action === "ALERT_RISK"
          ? d.confidence
          : (d as ReorderDecision).confidence;

      const riskLevel =
        d.action === "CREATE_PURCHASE_ORDER"
          ? d.riskLevel
          : d.action === "ALERT_RISK"
          ? d.riskLevel
          : (d as ReorderDecision).riskLevel;

      const relatedEventId =
        d.action === "CREATE_PURCHASE_ORDER"
          ? d.relatedEventId ?? null
          : d.action === "ALERT_RISK"
          ? d.affectedEventId ?? null
          : null;

      const expiresAt =
        d.action === "CREATE_PURCHASE_ORDER"
          ? d.deadline
          : d.action === "ALERT_RISK"
          ? d.deadline
          : null;

      return {
        tenantId,
        action: d.action,
        confidence,
        riskLevel,
        payload: d as object,
        status: "pending",
        relatedEventId,
        expiresAt,
      };
    });

    await prisma.operationalDecision.createMany({ data: records });

    logger.info({ tenantId, count: records.length }, "DecisionEngine: decisions persisted");
  }

  // type-annotation helper (unused at runtime — guides TypeScript)
  private buildShortfall(_: unknown) {
    return null as null | {
      itemCode: string;
      itemName: string;
      category: string;
      needed: number;
      available: number;
      gap: number;
      unit: string;
      unitPrice: number;
    };
  }
}

// ---- module-level helpers ----

function daysToSeverity(days: number): RiskSeverity {
  if (days <= 1) return "CRITICAL";
  if (days <= 3) return "HIGH";
  if (days <= 7) return "MEDIUM";
  return "LOW";
}

function pct(current: number, min: number): string {
  return min > 0 ? ((current / min) * 100).toFixed(0) : "0";
}

function fmt(n: number): string {
  return n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function round2(n: number) { return Math.round(n * 100) / 100; }

export const decisionEngine = new DecisionEngine();
