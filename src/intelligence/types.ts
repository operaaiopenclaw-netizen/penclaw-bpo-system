// ============================================================
// INTELLIGENCE ENGINE — Shared Types
// ============================================================

// ---- Forecast Engine ----

export interface ConsumptionForecast {
  itemCode: string;
  itemName: string;
  category: string;
  unit: string;
  /** Blended model+history estimate */
  estimatedConsumption: number;
  /** 90% CI lower bound */
  minConsumption: number;
  /** 90% CI upper bound */
  maxConsumption: number;
  /** 0.0–1.0 */
  confidenceScore: number;
  historicalDataPoints: number;
  perGuestRate: number;
  adjustmentFactors: {
    eventType: number;
    duration: number;
    guestScale: number;
    historical: number;
  };
}

export interface EventForecastResult {
  eventId?: string;
  eventType: string;
  guestCount: number;
  durationHours: number;
  forecasts: ConsumptionForecast[];
  /** Mean confidence across all items */
  overallConfidence: number;
  /** Estimated cost at inventory unit prices */
  totalEstimatedCost: number;
  generatedAt: Date;
}

// ---- Supplier Intelligence ----

export interface SupplierScore {
  supplierId: string;
  supplierName: string;
  categories: string[];
  /** Percentage change in avg order value over last 90 days (negative = cheaper) */
  priceTrend: number;
  /** 0–100 */
  deliveryReliability: number;
  /** 0–100 */
  stockReliability: number;
  /** Fraction of late deliveries (0.0–1.0) */
  delayRate: number;
  /** Per-category delivery success rate */
  categoryPerformance: Record<string, number>;
  /** Weighted composite 0–100 */
  finalScore: number;
  totalOrders: number;
  lastOrderDate: Date | null;
  recommendation: "preferred" | "acceptable" | "avoid" | "unrated";
}

export interface RankedSupplier extends SupplierScore {
  rankPosition: number;
  reasonsRanked: string[];
}

// ---- Decision Engine ----

export type DecisionActionType =
  | "CREATE_PURCHASE_ORDER"
  | "ALERT_RISK"
  | "SUGGEST_REORDER"
  | "EMERGENCY_RESTOCK"
  | "FLAG_MARGIN_RISK"
  | "ESCALATE_REVIEW";

export type RiskSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface PurchaseOrderDecision {
  action: "CREATE_PURCHASE_ORDER";
  supplierId: string;
  supplierName: string;
  items: Array<{
    itemCode: string;
    itemName: string;
    category: string;
    quantityNeeded: number;
    unit: string;
    estimatedUnitPrice: number;
    estimatedTotal: number;
  }>;
  totalEstimatedCost: number;
  deadline: Date;
  relatedEventId?: string;
  confidence: number;
  riskLevel: "R1" | "R2" | "R3";
  justification: string;
}

export interface RiskAlertDecision {
  action: "ALERT_RISK";
  type:
    | "STOCK_SHORTAGE"
    | "PRICE_SPIKE"
    | "SUPPLIER_FAILURE"
    | "MARGIN_RISK"
    | "DELIVERY_DELAY";
  severity: RiskSeverity;
  affectedEventId?: string;
  affectedItems?: string[];
  message: string;
  financialImpact?: number;
  recommendedAction: string;
  deadline: Date;
  confidence: number;
  riskLevel: "R2" | "R3" | "R4";
}

export interface ReorderDecision {
  action: "SUGGEST_REORDER";
  itemCode: string;
  itemName: string;
  currentQty: number;
  reorderPoint: number;
  suggestedQty: number;
  unit: string;
  preferredSupplierId?: string;
  estimatedCost: number;
  urgency: "low" | "medium" | "high";
  confidence: number;
  riskLevel: "R1" | "R2";
}

export type OperationalDecisionPayload =
  | PurchaseOrderDecision
  | RiskAlertDecision
  | ReorderDecision;

// ---- Structured Insights ----

export type InsightType =
  | "PROCUREMENT"
  | "STOCK"
  | "SUPPLIER"
  | "FINANCIAL"
  | "OPERATIONAL"
  | "FORECAST";

export interface StructuredInsight {
  id: string;
  type: InsightType;
  /** Human-readable summary */
  message: string;
  impact: {
    /** BRL monetary impact (positive = savings/risk, negative = loss) */
    financial?: number;
    /** Qualitative operational impact */
    operational?: string;
    urgency: "immediate" | "within_week" | "within_month" | "informational";
  };
  /** Concrete next step — never generic */
  recommendation: string;
  /** 0.0–1.0 */
  confidence: number;
  relatedEntityId?: string;
  relatedEntityType?: "event" | "supplier" | "inventory_item";
  createdAt: Date;
  /** Links to an OperationalDecision that can be executed */
  actionDecisionId?: string;
}

// ---- Decision Cycle ----

export interface DecisionCycleResult {
  tenantId: string;
  cycleRunAt: Date;
  decisions: OperationalDecisionPayload[];
  insights: StructuredInsight[];
  summary: {
    totalDecisions: number;
    purchaseOrders: number;
    riskAlerts: number;
    criticalAlerts: number;
    reorderSuggestions: number;
    estimatedProcurementCost: number;
  };
  durationMs: number;
}

// ---- Gap Engine ----

export type GapSeverity = "OK" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type OverallRisk = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface StockGap {
  itemCode: string;
  itemName: string;
  category: string;
  unit: string;
  needed: number;
  available: number;
  committed: number;
  free: number;
  gap: number;
  coverageRatio: number;
  severity: GapSeverity;
  unitPrice: number;
  estimatedGapCost: number;
}

export interface GapAnalysisResult {
  eventId?: string;
  eventType: string;
  guestCount: number;
  analysisDate: Date;
  items: StockGap[];
  summary: {
    totalItems: number;
    sufficient: number;
    shortages: number;
    critical: number;
    estimatedTotalProcurementCost: number;
  };
  overallRisk: OverallRisk;
}

// ---- Procurement Decision Engine ----

export type ApprovalStatus = "AUTO_APPROVED" | "PENDING_APPROVAL" | "BLOCKED";

export interface PurchaseLineItem {
  itemCode: string;
  itemName: string;
  category: string;
  unit: string;
  quantity: number;
  unitPrice: number;
  totalPrice: number;
  urgency: "low" | "medium" | "high" | "critical";
  gapSeverity: GapSeverity;
}

export interface SupplierAlternative {
  supplierId: string;
  supplierName: string;
  finalScore: number;
  rankPosition: number;
  recommendation: string;
  reasonsRanked: string[];
}

export interface ProcurementDecision {
  action: "CREATE_PURCHASE_RECOMMENDATION";
  decisionId: string;
  supplierId: string;
  supplierName: string;
  supplierScore: number;
  supplierRecommendation: string;
  /** Ranked alternatives for this category (excluding the winner). Empty when no others exist. */
  alternatives: SupplierAlternative[];
  /** Human-readable reason the winner was picked */
  selectionReason: string;
  items: PurchaseLineItem[];
  totalCost: number;
  deadline: Date;
  confidence: number;
  riskLevel: "R1" | "R2" | "R3" | "R4";
  approvalStatus: ApprovalStatus;
  approvalReason?: string;
  justification: string;
  auditSnapshot: {
    gapItems: StockGap[];
    supplierScore: number;
    supplierDelayRate: number;
    forecastConfidence: number;
    thresholdApplied: string;
    decisionTimestamp: string;
    eventMarginPct?: number;
  };
  relatedEventId?: string;
}

export interface ProcurementRiskAlert {
  action: "ALERT_RISK";
  code: string;
  message: string;
  severity: "warning" | "critical";
  affectedItems: string[];
  financialImpact?: number;
  recommendedAction: string;
  riskLevel: "R2" | "R3" | "R4";
}

export interface ProcurementEngineResult {
  tenantId: string;
  eventId?: string;
  runAt: Date;
  durationMs: number;
  gapAnalysis: GapAnalysisResult;
  decisions: ProcurementDecision[];
  alerts: ProcurementRiskAlert[];
  summary: {
    totalDecisions: number;
    autoApproved: number;
    pendingApproval: number;
    blocked: number;
    criticalAlerts: number;
    estimatedTotalCost: number;
    overallRisk: OverallRisk;
  };
}

// ---- Action Dispatcher ----

export interface DispatchedAction {
  actionType: string;
  decisionId?: string;
  resultId?: string;
  status: "dispatched" | "skipped" | "failed";
  reason?: string;
}

export interface DispatchResult {
  agentRunId: string;
  dispatched: DispatchedAction[];
  purchaseOrdersCreated: number;
  alertsLogged: number;
  errors: string[];
}

// ---- Reconciliation Loop (Sprint 4) ----

export interface ReconciliationItem {
  itemCode: string;
  itemName: string;
  category: string;
  unit: string;
  forecast: number;
  purchased: number;
  consumed: number;
  wasted: number;
  returned: number;
  /** consumed - forecast (can be negative when under-forecast) */
  variance: number;
  /** variance relative to forecast, signed */
  variancePct: number;
  /** 0-100 — 100 = perfect match */
  accuracyScore: number;
  /** (consumed + wasted) * unitPrice — what the event actually cost in items */
  realItemCost: number;
  /** forecast * unitPrice — what we projected */
  projectedItemCost: number;
  /** wasted * unitPrice */
  wasteItemCost: number;
  unitPrice: number;
}

export interface ReconciliationFinancials {
  projectedCost: number;
  realCost: number;
  wasteCost: number;
  revenue: number | null;
  projectedMargin: number | null;
  realMargin: number | null;
  marginDelta: number | null;
}

export interface ReconciliationAccuracy {
  overall: number;
  byCategory: Record<string, number>;
  byEventType: Record<string, number>;
  itemCount: number;
}

export interface SupplierFeedbackUpdate {
  supplierId: string;
  supplierName: string;
  previousReliability: number | null;
  newReliability: number;
  deliveryAccuracyPct: number;
  quantityVariancePct: number;
  itemsEvaluated: number;
}

export interface MemoryPatternEntry {
  memoryType: "deviation" | "pattern" | "inefficiency";
  title: string;
  content: string;
  tags: string[];
  confidenceScore: number;
}

export interface ReconciliationReportResult {
  eventId: string;
  tenantId: string;
  eventType: string;
  guestCount: number;
  generatedAt: Date;
  items: ReconciliationItem[];
  accuracy: ReconciliationAccuracy;
  financials: ReconciliationFinancials;
  adjustmentsApplied: Array<{
    itemCode: string;
    eventType: string;
    previousFactor: number;
    newFactor: number;
    sampleSize: number;
  }>;
  supplierFeedback: SupplierFeedbackUpdate[];
  memoryEntries: MemoryPatternEntry[];
}
