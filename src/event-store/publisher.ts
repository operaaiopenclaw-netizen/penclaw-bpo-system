// ============================================================
// EVENT PUBLISHER - Domain Event Publishers
// SPRINT 1: Integration Layer
// ============================================================

import { eventStore, EventStore } from "./index";
import { logger } from "../utils/logger";
import { prisma } from "../db";

// Tenant default para testes
const DEFAULT_TENANT = "orkestra-001";

interface EventContext {
  tenantId?: string;
  userId?: string;
  correlationId?: string;
  ipAddress?: string;
}

/**
 * Publicar evento de criação de evento
 */
export async function publishEventCreated(
  eventId: string,
  eventData: Record<string, unknown>,
  context: EventContext = {}
): Promise<void> {
  const correlationId = context.correlationId || `corr-${Date.now()}`;
  
  logger.info("EventPublisher: event.created", { eventId, correlationId });

  await eventStore.publish({
    tenantId: context.tenantId || DEFAULT_TENANT,
    aggregateType: "event",
    aggregateId: eventId,
    eventType: "event.created",
    payload: {
      ...eventData,
      publishedBy: "event-publisher",
      timestamp: new Date().toISOString()
    },
    source: context.userId ? "api" : "system",
    correlationId,
    createdBy: context.userId,
    ipAddress: context.ipAddress
  });

  // Log de domínio
  await eventStore.logDomain({
    tenantId: context.tenantId || DEFAULT_TENANT,
    domain: "event",
    action: "event.created",
    entityId: eventId,
    entityType: "Event",
    newState: eventData
  });

  logger.info("EventPublisher: event.created published", { eventId, correlationId });
}

/**
 * Publicar evento de atualização de evento
 */
export async function publishEventUpdated(
  eventId: string,
  oldData: Record<string, unknown> | null,
  newData: Record<string, unknown>,
  context: EventContext = {}
): Promise<void> {
  const correlationId = context.correlationId || `corr-${Date.now()}`;

  await eventStore.publish({
    tenantId: context.tenantId || DEFAULT_TENANT,
    aggregateType: "event",
    aggregateId: eventId,
    eventType: "event.updated",
    payload: {
      newData,
      oldData,
      diff: calculateDiff(oldData, newData),
      timestamp: new Date().toISOString()
    },
    source: context.userId ? "api" : "system",
    causationId: context.userId ? undefined : correlationId,
    correlationId,
    createdBy: context.userId,
    ipAddress: context.ipAddress
  });

  await eventStore.logDomain({
    tenantId: context.tenantId || DEFAULT_TENANT,
    domain: "event",
    action: "event.updated",
    entityId: eventId,
    entityType: "Event",
    oldState: oldData || undefined,
    newState: newData
  });
}

/**
 * Publicar evento de planejamento criado
 */
export async function publishEventPlanningCreated(
  eventId: string,
  planningData: Record<string, unknown>,
  context: EventContext = {}
): Promise<void> {
  const correlationId = context.correlationId || `corr-${Date.now()}`;

  await eventStore.publish({
    tenantId: context.tenantId || DEFAULT_TENANT,
    aggregateType: "event",
    aggregateId: eventId,
    eventType: "event.planning.created",
    payload: {
      ...planningData,
      timestamp: new Date().toISOString()
    },
    source: context.userId ? "api" : "agent",
    correlationId,
    createdBy: context.userId
  });

  await eventStore.logDomain({
    tenantId: context.tenantId || DEFAULT_TENANT,
    domain: "event",
    action: "event.planning.created",
    entityId: eventId,
    entityType: "EventPlanning",
    newState: planningData
  });
}

/**
 * Publicar evento de cálculo financeiro
 */
export async function publishEventFinancialsCreated(
  eventId: string,
  financialData: {
    revenueTotal: number;
    cmvTotal: number;
    netProfit: number;
    marginPct: number;
  },
  context: EventContext = {}
): Promise<void> {
  const correlationId = context.correlationId || `corr-${Date.now()}`;

  await eventStore.publish({
    tenantId: context.tenantId || DEFAULT_TENANT,
    aggregateType: "finance",
    aggregateId: eventId,
    eventType: "event.financials.created",
    payload: {
      ...financialData,
      calculatedAt: new Date().toISOString()
    },
    source: context.userId ? "api" : "agent",
    correlationId,
    createdBy: context.userId
  });

  await eventStore.logDomain({
    tenantId: context.tenantId || DEFAULT_TENANT,
    domain: "finance",
    action: "event.financials.created",
    entityId: eventId,
    entityType: "Event",
    newState: financialData
  });
}

/**
 * Publicar evento de cálculo de margem
 */
export async function publishMarginCalculated(
  eventId: string,
  marginData: {
    revenue: number;
    costs: number;
    margin: number;
    marginPct: number;
    recommendation: string;
  },
  context: EventContext = {}
): Promise<void> {
  const correlationId = context.correlationId || `corr-${Date.now()}`;

  await eventStore.publish({
    tenantId: context.tenantId || DEFAULT_TENANT,
    aggregateType: "finance",
    aggregateId: eventId,
    eventType: "event.margin.calculated",
    payload: {
      ...marginData,
      calculatedAt: new Date().toISOString()
    },
    source: context.userId ? "api" : "agent",
    correlationId,
    createdBy: context.userId
  });

  await eventStore.logDomain({
    tenantId: context.tenantId || DEFAULT_TENANT,
    domain: "finance",
    action: "event.margin.calculated",
    entityId: eventId,
    entityType: "Event",
    newState: marginData
  });
}

/**
 * Publicar evento de cálculo de preço
 */
export async function publishPriceCalculated(
  eventId: string,
  priceData: {
    basePrice: number;
    finalPrice: number;
    discountAmount: number;
    marginPct: number;
  },
  context: EventContext = {}
): Promise<void> {
  await eventStore.publish({
    tenantId: context.tenantId || DEFAULT_TENANT,
    aggregateType: "finance",
    aggregateId: eventId,
    eventType: "event.price.calculated",
    payload: {
      ...priceData,
      calculatedAt: new Date().toISOString()
    },
    source: context.userId ? "api" : "agent",
    createdBy: context.userId
  });
}

/**
 * Publicar evento de pacote comercial
 */
export async function publishCommercialPackageCalculated(
  eventId: string,
  packageData: {
    packageType: string;
    baseCost: number;
    suggestedPrice: number;
    margin: number;
    services: string[];
  },
  context: EventContext = {}
): Promise<void> {
  await eventStore.publish({
    tenantId: context.tenantId || DEFAULT_TENANT,
    aggregateType: "commercial",
    aggregateId: eventId,
    eventType: "commercial.package.calculated",
    payload: {
      ...packageData,
      calculatedAt: new Date().toISOString()
    },
    source: context.userId ? "api" : "agent",
    createdBy: context.userId
  });
}

/**
 * Publicar evento de cálculo de desconto
 */
export async function publishCommercialDiscountCalculated(
  eventId: string,
  discountData: {
    originalPrice: number;
    discountPct: number;
    discountAmount: number;
    finalPrice: number;
    marginAfterDiscount: number;
    approved: boolean;
  },
  context: EventContext = {}
): Promise<void> {
  await eventStore.publish({
    tenantId: context.tenantId || DEFAULT_TENANT,
    aggregateType: "commercial",
    aggregateId: eventId,
    eventType: "commercial.discount.calculated",
    payload: {
      ...discountData,
      calculatedAt: new Date().toISOString()
    },
    source: context.userId ? "api" : "agent",
    createdBy: context.userId
  });
}

/**
 * Publicar evento de recomendação comercial
 */
export async function publishCommercialRecommendationGenerated(
  eventId: string,
  recommendationData: {
    score: number;
    recommendation: string;
    actions: string[];
    alternatives: string[];
  },
  context: EventContext = {}
): Promise<void> {
  await eventStore.publish({
    tenantId: context.tenantId || DEFAULT_TENANT,
    aggregateType: "commercial",
    aggregateId: eventId,
    eventType: "commercial.recommendation.generated",
    payload: {
      ...recommendationData,
      generatedAt: new Date().toISOString()
    },
    source: context.userId ? "api" : "agent",
    createdBy: context.userId
  });
}

// Helper: calcular diferença entre objetos
function calculateDiff(
  oldObj: Record<string, unknown> | null,
  newObj: Record<string, unknown>
): Record<string, { old: unknown; new: unknown }> {
  if (!oldObj) return {};
  
  const diff: Record<string, { old: unknown; new: unknown }> = {};
  
  for (const [key, newValue] of Object.entries(newObj)) {
    const oldValue = oldObj[key];
    if (JSON.stringify(oldValue) !== JSON.stringify(newValue)) {
      diff[key] = { old: oldValue, new: newValue };
    }
  }
  
  return diff;
}

// Re-export for convenience
export { eventStore } from "./index";
