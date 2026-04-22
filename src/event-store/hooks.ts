// ============================================================
// EVENT HOOKS - Integration hooks para eventos existentes
// SPRINT 1: Integration Layer
// ============================================================

import { prisma } from "../db";
import { logger } from "../utils/logger";
import {
  publishEventCreated,
  publishEventUpdated,
  publishMarginCalculated,
  publishEventFinancialsCreated
} from "./publisher";

interface HookContext {
  tenantId?: string;
  userId?: string;
  source?: "api" | "agent" | "system";
}

/**
 * Hook após criar evento
 */
export async function onEventCreated(
  eventId: string,
  eventData: Record<string, unknown>,
  context: HookContext = {}
): Promise<void> {
  logger.info("EventHook: onEventCreated", { eventId });

  try {
    // Publicar evento no backbone
    await publishEventCreated(eventId, eventData, {
      tenantId: context.tenantId,
      userId: context.userId
    });

    // Se tem dados financeiros, calcular margem
    if (eventData.revenueTotal && eventData.cmvTotal) {
      const revenue = Number(eventData.revenueTotal);
      const costs = Number(eventData.cmvTotal);
      const margin = revenue - costs;
      const marginPct = revenue > 0 ? (margin / revenue) * 100 : 0;

      // Publicar evento de margem calculada
      await publishMarginCalculated(eventId, {
        revenue,
        costs,
        margin,
        marginPct,
        recommendation: marginPct < 15 ? "Margem baixa - aprovação necessária" : "Margem aceitável"
      }, context);

      // Publicar evento financeiro
      await publishEventFinancialsCreated(eventId, {
        revenueTotal: revenue,
        cmvTotal: costs,
        netProfit: margin,
        marginPct
      }, context);
    }

    logger.info("EventHook: onEventCreated completed", { eventId });
  } catch (error) {
    logger.error("EventHook: onEventCreated failed", { error, eventId });
    // Não falha o hook - loga e continua
  }
}

/**
 * Hook após atualizar evento
 */
export async function onEventUpdated(
  eventId: string,
  oldData: Record<string, unknown> | null,
  newData: Record<string, unknown>,
  context: HookContext = {}
): Promise<void> {
  logger.debug("EventHook: onEventUpdated", { eventId });

  try {
    await publishEventUpdated(eventId, oldData, newData, {
      tenantId: context.tenantId,
      userId: context.userId
    });

    // Re-calcular margem se finanças mudaram
    if (newData.revenueTotal !== oldData?.revenueTotal || 
        newData.cmvTotal !== oldData?.cmvTotal) {
      
      const revenue = Number(newData.revenueTotal || 0);
      const costs = Number(newData.cmvTotal || 0);
      const margin = revenue - costs;
      const marginPct = revenue > 0 ? (margin / revenue) * 100 : 0;

      await publishMarginCalculated(eventId, {
        revenue,
        costs,
        margin,
        marginPct,
        recommendation: marginPct < 15 ? "Margem atualizada - abaixo do ideal" : "Margem atualizada"
      }, context);
    }
  } catch (error) {
    logger.error("EventHook: onEventUpdated failed", { error, eventId });
  }
}

/**
 * Hook após calcular planejamento
 */
export async function onPlanningCreated(
  eventId: string,
  planningData: Record<string, unknown>,
  context: HookContext = {}
): Promise<void> {
  logger.debug("EventHook: onPlanningCreated", { eventId });

  try {
    // Import dinâmico para evitar circular dependency
    const { publishEventPlanningCreated } = await import("./publisher");
    
    await publishEventPlanningCreated(eventId, planningData, {
      tenantId: context.tenantId,
      userId: context.userId
    });
  } catch (error) {
    logger.error("EventHook: onPlanningCreated failed", { error, eventId });
  }
}

/**
 * Criar evento de teste com dados completos
 */
export async function createTestEvent(eventName: string = "Teste Orkestra"): Promise<{ 
  eventId: string; 
  tests: { 
    eventPublished: boolean;
    marginPublished: boolean;
    financePublished: boolean;
  }
}> {
  const testTenantId = "orkestra-001";

  logger.info("EventHook: creating test event", { eventName });

  try {
    // 1. Criar evento base
    const event = await prisma.event.create({
      data: {
        eventId: `test-${Date.now()}`,
        tenantId: testTenantId,
        costCenterId: "test",
        name: eventName,
        companyName: "Orkestra Catering",
        eventType: "Casamento",
        eventDate: new Date("2026-06-15"),
        guests: 100,
        status: "test",
        revenueTotal: 25000,
        cmvTotal: 15000,
        netProfit: 10000,
        marginPct: 40
      }
    });

    // 2. Publicar evento criado
    await onEventCreated(
      event.id,
      {
        eventId: event.eventId,
        eventType: event.eventType,
        guests: event.guests,
        revenueTotal: event.revenueTotal,
        cmvTotal: event.cmvTotal,
        marginPct: event.marginPct
      },
      {
        tenantId: testTenantId,
        source: "system"
      }
    );

    // 3. Simular planejamento
    await onPlanningCreated(
      event.id,
      {
        planningId: `plan-${Date.now()}`,
        eventType: "Casamento",
        estimatedGuests: 100,
        menuType: "Buffet Premium",
        services: ["Cerimonial", "Fotografia", "Decoração"],
        notes: "Planejamento teste SPRINT 1"
      },
      {
        tenantId: testTenantId,
        source: "agent"
      }
    );

    // 4. Verificar resultados
    const systemEvents = await prisma.systemEvent.findMany({
      where: {
        tenantId: testTenantId,
        aggregateId: event.id
      },
      orderBy: { createdAt: "desc" },
      take: 5
    });

    const eventsPublished = {
      event: systemEvents.some(e => e.eventType === "event.created"),
      margin: systemEvents.some(e => e.eventType === "event.margin.calculated"),
      finance: systemEvents.some(e => e.eventType === "event.financials.created"),
      planning: systemEvents.some(e => e.eventType === "event.planning.created")
    };

    logger.info("EventHook: test event completed", {
      eventId: event.id,
      results: eventsPublished
    });

    return {
      eventId: event.id,
      tests: {
        eventPublished: eventsPublished.event,
        marginPublished: eventsPublished.margin,
        financePublished: eventsPublished.finance
      }
    };

  } catch (error) {
    logger.error("EventHook: createTestEvent failed", { error });
    throw error;
  }
}

// Named exports
export const eventHooks = {
  onEventCreated,
  onEventUpdated,
  onPlanningCreated,
  createTestEvent
};

// Default export
export default eventHooks;
