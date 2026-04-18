// ============================================================
// ACTION DISPATCHER — Central DB writer for agent _actions[]
// All agent side-effects MUST go through here. No agent writes DB directly.
// ============================================================
import { prisma } from "../db";
import { Prisma } from "@prisma/client";
import { memoryService } from "./memory-service";
import { productionTwin } from "./production-twin";
import { logger } from "../utils/logger";
import type { AgentAction } from "../agents/base-agent";
import type {
  ProcurementDecision,
  ProcurementRiskAlert,
  DispatchResult,
  DispatchedAction
} from "../intelligence/types";

export class ActionDispatcher {
  async dispatch(
    agentRunId: string,
    companyId: string,
    actions: AgentAction[]
  ): Promise<DispatchResult> {
    const result: DispatchResult = {
      agentRunId,
      dispatched: [],
      purchaseOrdersCreated: 0,
      alertsLogged: 0,
      errors: []
    };

    for (const action of actions) {
      try {
        const dispatched = await this.dispatchOne(agentRunId, companyId, action);
        result.dispatched.push(dispatched);
        if (action.type === "CREATE_PURCHASE_RECOMMENDATION") result.purchaseOrdersCreated++;
        if (action.type === "ALERT_RISK") result.alertsLogged++;
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        result.errors.push(`${action.type}: ${msg}`);
        result.dispatched.push({ actionType: action.type, status: "failed", reason: msg });
        logger.error("ActionDispatcher: dispatch failed", { agentRunId, action: action.type, error: msg });
      }
    }

    logger.info("ActionDispatcher: completed", {
      agentRunId,
      total: actions.length,
      purchaseOrders: result.purchaseOrdersCreated,
      alerts: result.alertsLogged,
      errors: result.errors.length
    });

    return result;
  }

  private async dispatchOne(
    agentRunId: string,
    companyId: string,
    action: AgentAction
  ): Promise<DispatchedAction> {
    switch (action.type) {
      case "CREATE_PURCHASE_RECOMMENDATION":
        return this.createPurchaseRecommendation(agentRunId, companyId, action.payload as unknown as ProcurementDecision);
      case "ALERT_RISK":
        return this.logRiskAlert(agentRunId, companyId, action.payload as unknown as ProcurementRiskAlert);
      case "CREATE_STOCK_RESERVATION":
        return this.createStockReservation(agentRunId, companyId, action.payload);
      case "RELEASE_STOCK_RESERVATION":
        return this.releaseStockReservation(agentRunId, action.payload);
      case "RECORD_PRODUCTION":
        return this.recordProduction(agentRunId, companyId, action.payload);
      case "RECORD_CONSUMPTION":
        return this.recordConsumption(agentRunId, companyId, action.payload);
      case "RECONCILE_EVENT":
        return this.reconcileEvent(agentRunId, companyId, action.payload);
      case "CONFIRM_CHECKPOINT":
        return this.confirmCheckpoint(agentRunId, companyId, action.payload);
      case "FLAG_OCCURRENCE":
        return this.flagOccurrence(agentRunId, companyId, action.payload);
      case "RESOLVE_OCCURRENCE":
        return this.resolveOccurrence(agentRunId, companyId, action.payload);
      case "CONFIRM_TEARDOWN":
        return this.confirmTeardown(agentRunId, companyId, action.payload);
      case "CREATE_FINANCIAL_PROVISION":
        return this.logToMemory(agentRunId, companyId, action);
      case "CREATE_SERVICE_ORDER":
        return this.logToMemory(agentRunId, companyId, action);
      case "CREATE_PRODUCTION_ORDER":
        return this.logToMemory(agentRunId, companyId, action);
      case "QUALIFY_LEAD":
        return this.logToMemory(agentRunId, companyId, action);
      case "CREATE_REPORT_ARTIFACT":
        return this.logToMemory(agentRunId, companyId, action);
      case "REQUEST_APPROVAL":
        return this.logToMemory(agentRunId, companyId, action);
      case "BLOCK_EVENT":
        return this.logToMemory(agentRunId, companyId, action);
      default:
        logger.warn("ActionDispatcher: unhandled action type", { actionType: action.type });
        return { actionType: action.type, status: "skipped", reason: "Unhandled action type" };
    }
  }

  // ── Stock reservations ──────────────────────────────────────

  private async createStockReservation(
    agentRunId: string,
    companyId: string,
    payload: Record<string, unknown>
  ): Promise<DispatchedAction> {
    const { tenantId, eventId, itemCode, quantityReserved, requiredBy } = payload;

    const reservation = await prisma.inventoryReservation.create({
      data: {
        tenantId: String(tenantId ?? companyId),
        eventId: String(eventId),
        productId: String(itemCode),  // itemCode used as productId (InventoryItem.code)
        quantityReserved: Number(quantityReserved),
        status: "PENDING",
        requiredBy: requiredBy ? new Date(String(requiredBy)) : null,
        metadata: payload as object
      }
    });

    logger.info("ActionDispatcher: stock reservation created", {
      agentRunId, reservationId: reservation.id, itemCode, quantityReserved
    });

    return { actionType: "CREATE_STOCK_RESERVATION", resultId: reservation.id, status: "dispatched" };
  }

  private async releaseStockReservation(
    agentRunId: string,
    payload: Record<string, unknown>
  ): Promise<DispatchedAction> {
    const { reservationId, eventId, itemCode } = payload;

    if (reservationId) {
      await prisma.inventoryReservation.updateMany({
        where: { id: String(reservationId) },
        data: { status: "RELEASED" }
      });
    } else if (eventId && itemCode) {
      await prisma.inventoryReservation.updateMany({
        where: { eventId: String(eventId), productId: String(itemCode), status: "PENDING" },
        data: { status: "RELEASED" }
      });
    }

    return { actionType: "RELEASE_STOCK_RESERVATION", status: "dispatched" };
  }

  // ── Production twin ─────────────────────────────────────────

  private async recordProduction(
    agentRunId: string,
    companyId: string,
    payload: Record<string, unknown>
  ): Promise<DispatchedAction> {
    const { tenantId, eventId, warehouseId, items } = payload;
    await productionTwin.recordProduction(
      String(tenantId ?? companyId),
      String(eventId),
      String(warehouseId ?? "default"),
      (items as Array<{
        productId: string; itemCode: string; itemName: string;
        quantityProduced: number; unit: string;
      }>) ?? []
    );
    return { actionType: "RECORD_PRODUCTION", status: "dispatched" };
  }

  private async recordConsumption(
    agentRunId: string,
    companyId: string,
    payload: Record<string, unknown>
  ): Promise<DispatchedAction> {
    const { tenantId, eventId, warehouseId, consumedItems } = payload;

    const items = (consumedItems as Array<{
      itemCode: string; itemName: string;
      quantityConsumed: number; quantityLeftover?: number; unit: string;
    }> ?? []).map(i => ({
      productId: i.itemCode,
      itemCode: i.itemCode,
      itemName: i.itemName,
      quantityConsumed: i.quantityConsumed,
      quantityLeftover: i.quantityLeftover,
      unit: i.unit
    }));

    await productionTwin.recordConsumption(
      String(tenantId ?? companyId),
      String(eventId),
      String(warehouseId ?? "default"),
      items
    );
    return { actionType: "RECORD_CONSUMPTION", status: "dispatched" };
  }

  private async reconcileEvent(
    agentRunId: string,
    companyId: string,
    payload: Record<string, unknown>
  ): Promise<DispatchedAction> {
    const { eventId, numGuests } = payload;
    const report = await productionTwin.reconcile(
      companyId,
      String(eventId),
      Number(numGuests ?? 0)
    );

    await memoryService.log({
      companyId,
      type: "decision",
      content: `Reconciliation: ${report.summary.overallStatus} — efficiency ${report.summary.avgEfficiency}, loss ${report.summary.totalLoss}`,
      context: { action: "RECONCILE_EVENT", eventId, summary: report.summary },
      agentRunId
    }).catch(() => {});

    return { actionType: "RECONCILE_EVENT", resultId: String(eventId), status: "dispatched" };
  }

  // ── Event ops ───────────────────────────────────────────────

  private async confirmCheckpoint(
    agentRunId: string,
    companyId: string,
    payload: Record<string, unknown>
  ): Promise<DispatchedAction> {
    await memoryService.log({
      companyId,
      type: "decision",
      content: `Checkpoint confirmed: ${payload.checkpointName}`,
      context: { action: "CONFIRM_CHECKPOINT", ...payload },
      agentRunId
    }).catch(() => {});

    logger.info("ActionDispatcher: checkpoint confirmed", {
      agentRunId, checkpoint: payload.checkpointName, eventId: payload.eventId
    });

    return { actionType: "CONFIRM_CHECKPOINT", status: "dispatched" };
  }

  private async flagOccurrence(
    agentRunId: string,
    companyId: string,
    payload: Record<string, unknown>
  ): Promise<DispatchedAction> {
    await memoryService.log({
      companyId,
      type: "error",
      content: String(payload.description ?? payload.type),
      context: { action: "FLAG_OCCURRENCE", ...payload },
      agentRunId
    }).catch(() => {});

    logger.warn("ActionDispatcher: occurrence flagged", {
      agentRunId, type: payload.type, severity: payload.severity, eventId: payload.eventId
    });

    return { actionType: "FLAG_OCCURRENCE", status: "dispatched" };
  }

  private async resolveOccurrence(
    agentRunId: string,
    companyId: string,
    payload: Record<string, unknown>
  ): Promise<DispatchedAction> {
    await memoryService.log({
      companyId,
      type: "decision",
      content: `Occurrence resolved: ${payload.occurrenceId}`,
      context: { action: "RESOLVE_OCCURRENCE", ...payload },
      agentRunId
    }).catch(() => {});

    return { actionType: "RESOLVE_OCCURRENCE", status: "dispatched" };
  }

  private async confirmTeardown(
    agentRunId: string,
    companyId: string,
    payload: Record<string, unknown>
  ): Promise<DispatchedAction> {
    await memoryService.log({
      companyId,
      type: "decision",
      content: `Teardown confirmed for event ${payload.eventId} — ${payload.numGuests} guests`,
      context: { action: "CONFIRM_TEARDOWN", ...payload },
      agentRunId
    }).catch(() => {});

    logger.info("ActionDispatcher: teardown confirmed", {
      agentRunId, eventId: payload.eventId
    });

    return { actionType: "CONFIRM_TEARDOWN", status: "dispatched" };
  }

  // ── Procurement (retained from v1) ──────────────────────────

  private async createPurchaseRecommendation(
    agentRunId: string,
    companyId: string,
    decision: ProcurementDecision
  ): Promise<DispatchedAction> {
    if (decision.approvalStatus === "BLOCKED") {
      await memoryService.log({
        companyId,
        type: "decision",
        content: `BLOCKED: ${decision.justification}`,
        context: {
          action: "CREATE_PURCHASE_RECOMMENDATION",
          approvalStatus: "BLOCKED",
          approvalReason: decision.approvalReason,
          decisionId: decision.decisionId,
          totalCost: decision.totalCost
        },
        agentRunId
      }).catch(() => {});

      return {
        actionType: "CREATE_PURCHASE_RECOMMENDATION",
        decisionId: decision.decisionId,
        status: "skipped",
        reason: `Blocked: ${decision.approvalReason}`
      };
    }

    const supplierId = decision.supplierId === "unassigned" ? null : (decision.supplierId || null);
    // PO status:
    //   - supplierId present  → "confirmed" (supplier locked in, ready for human approval gate)
    //   - supplierId null     → "draft"     (no supplier cadastrado; suggestions carried in metadata)
    // Pending-approval decisions remain "pending_approval" regardless of supplier
    const poStatus = decision.approvalStatus === "PENDING_APPROVAL"
      ? "pending_approval"
      : (supplierId ? "confirmed" : "draft");

    const poMetadata: Record<string, unknown> = {
      selectionReason: decision.selectionReason,
      alternatives: decision.alternatives ?? [],
      supplierScore: decision.supplierScore,
      supplierRecommendation: decision.supplierRecommendation,
      approvalStatus: decision.approvalStatus,
      riskLevel: decision.riskLevel
    };
    if (!supplierId && decision.alternatives && decision.alternatives.length > 0) {
      poMetadata.supplierSuggestions = decision.alternatives;
    }

    let poId: string | undefined;

    // Create the PO regardless of whether supplierId is assigned
    {
      // Idempotency: skip if a PO for this decision already exists
      const existing = await prisma.purchaseOrder.findFirst({
        where: { sourceDecisionId: decision.decisionId },
        select: { id: true }
      });
      if (existing) {
        logger.warn("ActionDispatcher: PO already exists for decision — skipped (idempotent)", {
          decisionId: decision.decisionId, existingPoId: existing.id
        });
        return {
          actionType: "CREATE_PURCHASE_RECOMMENDATION",
          decisionId: decision.decisionId,
          resultId: existing.id,
          status: "skipped",
          reason: "Idempotent: PO already exists"
        };
      }

      const po = await prisma.$transaction(async tx => {
        const po = await tx.purchaseOrder.create({
          data: {
            tenantId: companyId,
            supplierId: supplierId,
            status: poStatus,
            sourceDecisionId: decision.decisionId,
            totalEstimatedCost: decision.totalCost,
            requestedDelivery: decision.deadline,
            relatedEventId: decision.relatedEventId ?? null,
            notes: decision.justification,
            metadata: poMetadata as Prisma.InputJsonValue
          }
        });

        await tx.purchaseOrderItem.createMany({
          data: decision.items.map(item => ({
            purchaseOrderId: po.id,
            itemCode: item.itemCode,
            itemName: item.itemName,
            category: item.category,
            quantityOrdered: item.quantity,
            unit: item.unit,
            unitPrice: item.unitPrice,
            totalPrice: item.totalPrice
          }))
        });

        return po;
      });
      poId = po.id;

      // Audit trail: OperationalDecision record
      await prisma.operationalDecision.create({
        data: {
          tenantId: companyId,
          action: "CREATE_PURCHASE_ORDER",
          confidence: decision.confidence,
          riskLevel: decision.riskLevel,
          status: "executed",
          executedAt: new Date(),
          executedBy: agentRunId,
          relatedOrderId: po.id,
          payload: {
            decisionId: decision.decisionId,
            purchaseOrderId: po.id,
            supplierId,
            supplierName: decision.supplierName,
            supplierScore: decision.supplierScore,
            selectionReason: decision.selectionReason,
            alternatives: decision.alternatives ?? [],
            totalCost: decision.totalCost,
            approvalStatus: decision.approvalStatus,
            poStatus,
            itemCount: decision.items.length,
            agentRunId
          } as unknown as Prisma.InputJsonValue
        }
      }).catch(() => {}); // Non-blocking
    }

    await memoryService.log({
      companyId,
      type: "decision",
      content: decision.justification,
      context: {
        action: "CREATE_PURCHASE_RECOMMENDATION",
        decisionId: decision.decisionId,
        purchaseOrderId: poId,
        poStatus,
        approvalStatus: decision.approvalStatus,
        riskLevel: decision.riskLevel,
        supplierId,
        supplierName: decision.supplierName,
        supplierScore: decision.supplierScore,
        selectionReason: decision.selectionReason,
        alternatives: decision.alternatives ?? [],
        totalCost: decision.totalCost,
        confidence: decision.confidence,
        itemCount: decision.items.length,
        auditSnapshot: decision.auditSnapshot
      },
      agentRunId
    }).catch(() => {});

    logger.info("ActionDispatcher: purchase recommendation created", {
      decisionId: decision.decisionId, poId,
      supplier: decision.supplierName,
      totalCost: decision.totalCost,
      approval: decision.approvalStatus
    });

    return {
      actionType: "CREATE_PURCHASE_RECOMMENDATION",
      decisionId: decision.decisionId,
      resultId: poId,
      status: "dispatched"
    };
  }

  private async logRiskAlert(
    agentRunId: string,
    companyId: string,
    alert: ProcurementRiskAlert
  ): Promise<DispatchedAction> {
    await memoryService.log({
      companyId,
      type: "error",
      content: alert.message,
      context: {
        action: "ALERT_RISK",
        code: alert.code,
        severity: alert.severity,
        riskLevel: alert.riskLevel,
        affectedItems: alert.affectedItems,
        financialImpact: alert.financialImpact,
        recommendedAction: alert.recommendedAction
      },
      agentRunId
    }).catch(() => {});

    logger.warn("ActionDispatcher: risk alert logged", {
      code: alert.code, severity: alert.severity, message: alert.message
    });

    return { actionType: "ALERT_RISK", status: "dispatched" };
  }

  // ── Catch-all memory logger ──────────────────────────────────

  private async logToMemory(
    agentRunId: string,
    companyId: string,
    action: AgentAction
  ): Promise<DispatchedAction> {
    await memoryService.log({
      companyId,
      type: "decision",
      content: `Action: ${action.type}`,
      context: { action: action.type, payload: action.payload },
      agentRunId
    }).catch(() => {});

    return { actionType: action.type, status: "dispatched" };
  }
}

export const actionDispatcher = new ActionDispatcher();
