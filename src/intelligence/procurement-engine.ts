// ============================================================
// PROCUREMENT ENGINE — Event-specific procurement decision cycle
// Sprint 9: Demand → Gap → Supplier → Decision → Approval → Audit
// ============================================================
import { v4 as uuid } from "uuid";
import { logger } from "../utils/logger";
import { forecastEngine } from "./forecast-engine";
import { gapEngine } from "./gap-engine";
import { supplierIntelligence } from "./supplier-intelligence";
import type {
  GapAnalysisResult,
  StockGap,
  ProcurementDecision,
  ProcurementRiskAlert,
  ProcurementEngineResult,
  PurchaseLineItem,
  ApprovalStatus,
  RankedSupplier
} from "./types";

// ---- Approval thresholds (BRL) ----
const THRESHOLD_AUTO_R1 = 1_000;    // < R$1k  → auto-approve R1
const THRESHOLD_AUTO_R2 = 5_000;    // < R$5k  → auto-approve R2
const THRESHOLD_HUMAN_R3 = 10_000;  // < R$10k → require human R3
// >= R$10k → always R3
const SUPPLIER_AVOID_SCORE = 60;
const MARGIN_BLOCK_PCT = 8;

export interface ProcurementEngineInput {
  tenantId: string;
  eventType: string;
  guestCount: number;
  durationHours?: number;
  eventId?: string;
  eventDate?: Date;
  eventMarginPct?: number;
}

export class ProcurementEngine {
  async run(input: ProcurementEngineInput): Promise<ProcurementEngineResult> {
    const start = Date.now();
    const durationHours = input.durationHours ?? 6;

    logger.info("ProcurementEngine: starting", {
      tenantId: input.tenantId,
      eventId: input.eventId,
      eventType: input.eventType,
      guests: input.guestCount
    });

    // 1. DEMAND ENGINE — forecast with history blend
    const forecast = await forecastEngine.forecastEvent(
      input.tenantId,
      input.eventType,
      input.guestCount,
      durationHours,
      input.eventId
    );

    // 2. GAP ENGINE — demand vs free stock (accounting for reservations)
    const gapAnalysis = await gapEngine.analyse(
      input.tenantId,
      forecast.forecasts,
      input.eventType,
      input.guestCount,
      input.eventId,
      input.eventDate
    );

    const alerts: ProcurementRiskAlert[] = [];

    // Early exit: margin block
    if (input.eventMarginPct !== undefined && input.eventMarginPct < MARGIN_BLOCK_PCT) {
      alerts.push(buildMarginBlockAlert(input.eventMarginPct, gapAnalysis));
      logger.warn("ProcurementEngine: margin block", { margin: input.eventMarginPct });
      return buildResult(input, gapAnalysis, [], alerts, start);
    }

    const gaps = gapAnalysis.items.filter(g => g.gap > 0);

    // Critical item alert
    const critical = gaps.filter(g => g.severity === "CRITICAL");
    if (critical.length > 0) alerts.push(buildCriticalAlert(critical));

    if (gaps.length === 0) {
      logger.info("ProcurementEngine: no gaps detected");
      return buildResult(input, gapAnalysis, [], alerts, start);
    }

    // 3. SUPPLIER ENGINE — rank per category
    const categories = [...new Set(gaps.map(g => g.category))];
    const suppliersByCategory = await rankSuppliersPerCategory(input.tenantId, categories);

    // 4. GROUP gaps by best supplier per category
    const grouped = groupBySupplier(gaps, suppliersByCategory);

    // 5. DECISION ENGINE — one ProcurementDecision per supplier group
    const decisions: ProcurementDecision[] = [];

    for (const [, { supplier, alternatives, categories: cats, items }] of grouped.entries()) {
      const totalCost = items.reduce((s, i) => s + i.totalPrice, 0);
      const { approvalStatus, riskLevel, approvalReason, threshold } =
        evaluateApproval(totalCost, supplier, input.eventMarginPct);

      if (supplier.recommendation === "avoid") {
        alerts.push(buildSupplierAvoidAlert(supplier));
      }

      const deadline = input.eventDate
        ? new Date(input.eventDate.getTime() - 48 * 3_600_000)
        : new Date(Date.now() + 72 * 3_600_000);

      const altPayload = alternatives.slice(0, 3).map(a => ({
        supplierId: a.supplierId,
        supplierName: a.supplierName,
        finalScore: a.finalScore,
        rankPosition: a.rankPosition,
        recommendation: a.recommendation,
        reasonsRanked: a.reasonsRanked
      }));
      const selectionReason = buildSelectionReason(supplier, alternatives, cats);

      // AUDIT SNAPSHOT — full decision context, frozen at decision time
      decisions.push({
        action: "CREATE_PURCHASE_RECOMMENDATION",
        decisionId: uuid(),
        supplierId: supplier.supplierId,
        supplierName: supplier.supplierName,
        supplierScore: supplier.finalScore,
        supplierRecommendation: supplier.recommendation,
        alternatives: altPayload,
        selectionReason,
        items,
        totalCost: r2(totalCost),
        deadline,
        confidence: forecast.overallConfidence,
        riskLevel,
        approvalStatus,
        approvalReason,
        justification: buildJustification(supplier, items, totalCost, input, forecast.overallConfidence),
        auditSnapshot: {
          gapItems: items.map(i => gapAnalysis.items.find(g => g.itemCode === i.itemCode)!).filter(Boolean),
          supplierScore: supplier.finalScore,
          supplierDelayRate: supplier.delayRate,
          forecastConfidence: forecast.overallConfidence,
          thresholdApplied: threshold,
          decisionTimestamp: new Date().toISOString(),
          eventMarginPct: input.eventMarginPct
        },
        relatedEventId: input.eventId
      });
    }

    logger.info("ProcurementEngine: completed", {
      decisions: decisions.length,
      alerts: alerts.length,
      durationMs: Date.now() - start
    });

    return buildResult(input, gapAnalysis, decisions, alerts, start);
  }
}

// ---- Pure functions (module-level for testability) ----

async function rankSuppliersPerCategory(
  tenantId: string,
  categories: string[]
): Promise<Map<string, RankedSupplier[]>> {
  const map = new Map<string, RankedSupplier[]>();
  await Promise.all(
    categories.map(async cat => {
      try {
        const ranked = await supplierIntelligence.rankSuppliersForItem(tenantId, cat);
        map.set(cat, ranked);
      } catch {
        map.set(cat, []);
      }
    })
  );
  return map;
}

const FALLBACK_SUPPLIER: RankedSupplier = {
  supplierId: "unassigned",
  supplierName: "Fornecedor Não Atribuído",
  categories: [],
  priceTrend: 0,
  deliveryReliability: 75,
  stockReliability: 75,
  delayRate: 0,
  categoryPerformance: {},
  finalScore: 75,
  totalOrders: 0,
  lastOrderDate: null,
  recommendation: "unrated",
  rankPosition: 999,
  reasonsRanked: ["Sem fornecedor mapeado para esta categoria"]
};

interface SupplierGroup {
  supplier: RankedSupplier;
  alternatives: RankedSupplier[];
  categories: Set<string>;
  items: PurchaseLineItem[];
}

function groupBySupplier(
  gaps: StockGap[],
  suppliersByCategory: Map<string, RankedSupplier[]>
): Map<string, SupplierGroup> {
  const grouped = new Map<string, SupplierGroup>();

  for (const gap of gaps) {
    const ranked = suppliersByCategory.get(gap.category) ?? [];
    const winner =
      ranked.find(s => s.recommendation !== "avoid") ??
      ranked[0] ??
      FALLBACK_SUPPLIER;
    const alternatives = ranked.filter(s => s.supplierId !== winner.supplierId);

    const key = winner.supplierId;
    if (!grouped.has(key)) {
      grouped.set(key, { supplier: winner, alternatives: [], categories: new Set(), items: [] });
    }
    const group = grouped.get(key)!;
    group.categories.add(gap.category);
    // Merge alternatives (dedupe by supplierId, keep best rank)
    for (const alt of alternatives) {
      if (!group.alternatives.some(a => a.supplierId === alt.supplierId)) {
        group.alternatives.push(alt);
      }
    }

    group.items.push({
      itemCode: gap.itemCode,
      itemName: gap.itemName,
      category: gap.category,
      unit: gap.unit,
      quantity: Math.ceil(gap.gap),
      unitPrice: gap.unitPrice,
      totalPrice: r2(Math.ceil(gap.gap) * gap.unitPrice),
      urgency: severityToUrgency(gap.severity),
      gapSeverity: gap.severity
    });
  }

  // Sort alternatives per group by rankPosition ascending
  for (const g of grouped.values()) {
    g.alternatives.sort((a, b) => a.rankPosition - b.rankPosition);
  }

  return grouped;
}

function buildSelectionReason(
  supplier: RankedSupplier,
  alternatives: RankedSupplier[],
  categories: Set<string>
): string {
  if (supplier.supplierId === "unassigned") {
    const cats = [...categories].join(", ");
    return `Nenhum fornecedor cadastrado para categoria(s): ${cats}. PO criada como DRAFT aguardando cadastro.`;
  }
  const cats = [...categories].join("/");
  const altCount = alternatives.length;
  const parts = [
    `Selecionado ${supplier.supplierName} (rank #${supplier.rankPosition}) em ${cats}:`,
    `score ${supplier.finalScore}/100, entrega ${supplier.deliveryReliability.toFixed(0)}%.`
  ];
  if (supplier.reasonsRanked?.length) parts.push(supplier.reasonsRanked.slice(0, 2).join(" "));
  parts.push(altCount > 0 ? `${altCount} alternativa(s) disponível(is).` : `Única opção cadastrada.`);
  return parts.join(" ");
}

function evaluateApproval(
  totalCost: number,
  supplier: RankedSupplier,
  marginPct?: number
): { approvalStatus: ApprovalStatus; riskLevel: "R1"|"R2"|"R3"|"R4"; approvalReason?: string; threshold: string } {
  if (marginPct !== undefined && marginPct < MARGIN_BLOCK_PCT) {
    return {
      approvalStatus: "BLOCKED",
      riskLevel: "R4",
      approvalReason: `Margem ${marginPct.toFixed(1)}% abaixo do mínimo operacional (${MARGIN_BLOCK_PCT}%)`,
      threshold: "MARGIN_BLOCK"
    };
  }
  if (supplier.finalScore < SUPPLIER_AVOID_SCORE) {
    return {
      approvalStatus: "PENDING_APPROVAL",
      riskLevel: "R3",
      approvalReason: `Fornecedor com score ${supplier.finalScore}/100 (abaixo do mínimo 60)`,
      threshold: "SUPPLIER_AVOID"
    };
  }
  if (totalCost >= THRESHOLD_HUMAN_R3) {
    return {
      approvalStatus: "PENDING_APPROVAL",
      riskLevel: "R3",
      approvalReason: `Valor R$${totalCost.toLocaleString("pt-BR")} acima do limite de aprovação automática (R$${THRESHOLD_HUMAN_R3.toLocaleString("pt-BR")})`,
      threshold: "HIGH_VALUE_R3"
    };
  }
  if (totalCost >= THRESHOLD_AUTO_R2) {
    return {
      approvalStatus: "PENDING_APPROVAL",
      riskLevel: "R2",
      approvalReason: `Valor médio — enviado para validação`,
      threshold: "MEDIUM_VALUE_R2"
    };
  }
  if (totalCost >= THRESHOLD_AUTO_R1) {
    return { approvalStatus: "AUTO_APPROVED", riskLevel: "R2", threshold: "LOW_MEDIUM_R2" };
  }
  return { approvalStatus: "AUTO_APPROVED", riskLevel: "R1", threshold: "LOW_VALUE_R1" };
}

function buildJustification(
  supplier: RankedSupplier,
  items: PurchaseLineItem[],
  totalCost: number,
  input: ProcurementEngineInput,
  confidence: number
): string {
  const critCount = items.filter(i => i.gapSeverity === "CRITICAL").length;
  const parts = [
    `${items.length} item(ns) em déficit para ${input.eventType} com ${input.guestCount} pax.`
  ];
  if (critCount > 0) parts.push(`${critCount} item(ns) crítico(s) — risco de falha operacional.`);
  parts.push(
    `Fornecedor: ${supplier.supplierName} | Score ${supplier.finalScore}/100 | ` +
    `Entrega ${supplier.deliveryReliability.toFixed(0)}% | Atraso ${(supplier.delayRate * 100).toFixed(0)}%.`
  );
  parts.push(`Custo estimado: R$${totalCost.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}.`);
  parts.push(`Confiança da previsão: ${Math.round(confidence * 100)}%.`);
  return parts.join(" ");
}

function buildCriticalAlert(critical: StockGap[]): ProcurementRiskAlert {
  return {
    action: "ALERT_RISK",
    code: "CRITICAL_STOCK_SHORTAGE",
    message: `${critical.length} item(ns) com cobertura < 10%: ${critical.map(c => c.itemName).join(", ")}`,
    severity: "critical",
    affectedItems: critical.map(c => c.itemCode),
    financialImpact: r2(critical.reduce((s, c) => s + c.estimatedGapCost, 0)),
    recommendedAction: "Acionar fornecedor emergencial imediatamente. Avaliar substituição de item no menu.",
    riskLevel: "R3"
  };
}

function buildMarginBlockAlert(marginPct: number, gap: GapAnalysisResult): ProcurementRiskAlert {
  return {
    action: "ALERT_RISK",
    code: "MARGIN_BELOW_MINIMUM",
    message: `Margem ${marginPct.toFixed(1)}% abaixo do mínimo (${MARGIN_BLOCK_PCT}%). Compras bloqueadas automaticamente.`,
    severity: "critical",
    affectedItems: gap.items.map(i => i.itemCode),
    financialImpact: r2(gap.summary.estimatedTotalProcurementCost),
    recommendedAction: "Revisar precificação do evento ou reduzir escopo antes de liberar procurement.",
    riskLevel: "R4"
  };
}

function buildSupplierAvoidAlert(supplier: RankedSupplier): ProcurementRiskAlert {
  return {
    action: "ALERT_RISK",
    code: "SUPPLIER_AVOID_RECOMMENDED",
    message: `${supplier.supplierName}: score ${supplier.finalScore}/100, atraso ${(supplier.delayRate * 100).toFixed(0)}%. Sem alternativa nesta categoria.`,
    severity: "warning",
    affectedItems: [],
    recommendedAction: "Cadastrar fornecedor alternativo ou aprovar manualmente com ciência do risco.",
    riskLevel: "R2"
  };
}

function buildResult(
  input: ProcurementEngineInput,
  gapAnalysis: GapAnalysisResult,
  decisions: ProcurementDecision[],
  alerts: ProcurementRiskAlert[],
  start: number
): ProcurementEngineResult {
  return {
    tenantId: input.tenantId,
    eventId: input.eventId,
    runAt: new Date(),
    durationMs: Date.now() - start,
    gapAnalysis,
    decisions,
    alerts,
    summary: {
      totalDecisions: decisions.length,
      autoApproved: decisions.filter(d => d.approvalStatus === "AUTO_APPROVED").length,
      pendingApproval: decisions.filter(d => d.approvalStatus === "PENDING_APPROVAL").length,
      blocked: decisions.filter(d => d.approvalStatus === "BLOCKED").length,
      criticalAlerts: alerts.filter(a => a.severity === "critical").length,
      estimatedTotalCost: r2(decisions.reduce((s, d) => s + d.totalCost, 0)),
      overallRisk: gapAnalysis.overallRisk
    }
  };
}

function severityToUrgency(sev: StockGap["severity"]): PurchaseLineItem["urgency"] {
  const m: Record<string, PurchaseLineItem["urgency"]> = {
    CRITICAL: "critical", HIGH: "high", MEDIUM: "medium", LOW: "low", OK: "low"
  };
  return m[sev] ?? "low";
}

function r2(n: number) { return Math.round(n * 100) / 100; }

export const procurementEngine = new ProcurementEngine();
