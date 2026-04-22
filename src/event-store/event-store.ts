// ============================================================
// EVENT STORE - Core Service
// SPRINT 1: Foundation Layer
// ============================================================

import { prisma } from "../db";
import { Prisma } from "@prisma/client";
import { logger } from "../utils/logger";

// Tipos de eventos suportados
export type EventType = 
  | "event.created"
  | "event.updated"
  | "event.planning.created"
  | "event.financials.created"
  | "event.margin.calculated"
  | "event.price.calculated"
  | "commercial.package.calculated"
  | "commercial.discount.calculated"
  | "commercial.recommendation.generated";

export type AggregateType = 
  | "event" 
  | "inventory" 
  | "procurement" 
  | "finance" 
  | "commercial";

export interface CreateEventInput {
  tenantId: string;
  aggregateType: AggregateType;
  aggregateId: string;
  eventType: EventType;
  payload: Record<string, unknown>;
  source?: "api" | "agent" | "system" | "manual";
  correlationId?: string;
  causationId?: string;
  createdBy?: string;
  ipAddress?: string;
}

export interface DomainLogInput {
  tenantId: string;
  domain: Exclude<AggregateType, "event"> | "event";
  action: string;
  entityId: string;
  entityType: string;
  oldState?: Record<string, unknown>;
  newState: Record<string, unknown>;
  processedBy?: string;
  processingTimeMs?: number;
}

export class EventStore {
  /**
   * Publicar evento no backbone
   */
  async publish(input: CreateEventInput): Promise<{ id: string; success: boolean }> {
    const startTime = Date.now();
    
    logger.info("EventStore: publishing event", {
      eventType: input.eventType,
      aggregateType: input.aggregateType,
      aggregateId: input.aggregateId,
      tenantId: input.tenantId
    });

    try {
      const event = await prisma.systemEvent.create({
        data: {
          tenantId: input.tenantId,
          aggregateType: input.aggregateType,
          aggregateId: input.aggregateId,
          eventType: input.eventType,
          payload: input.payload as Prisma.InputJsonValue,
          source: input.source || "api",
          correlationId: input.correlationId,
          causationId: input.causationId,
          status: "pending",
          createdBy: input.createdBy,
          ipAddress: input.ipAddress,
        }
      });

      logger.info("EventStore: event published", {
        eventId: event.id,
        eventType: input.eventType,
        latencyMs: Date.now() - startTime
      });

      return { id: event.id, success: true };
    } catch (error) {
      logger.error("EventStore: failed to publish event", { error, input });
      throw error;
    }
  }

  /**
   * Criar log de domínio vinculado a evento
   */
  async logDomain(input: DomainLogInput & { systemEventId?: string }): Promise<void> {
    try {
      // Se não tem systemEventId, cria evento implícito
      let systemEventId = input.systemEventId;
      
      if (!systemEventId) {
        // Cria evento implícito para o log
        const event = await prisma.systemEvent.create({
          data: {
            tenantId: input.tenantId,
            aggregateType: input.domain as AggregateType,
            aggregateId: input.entityId,
            eventType: input.action as EventType,
            payload: input.newState as Prisma.InputJsonValue,
            source: "system",
            status: "processed",
            processedAt: new Date(),
          }
        });
        systemEventId = event.id;
      }

      await prisma.domainLog.create({
        data: {
          systemEventId,
          tenantId: input.tenantId,
          domain: input.domain,
          action: input.action,
          entityId: input.entityId,
          entityType: input.entityType,
          oldState: (input.oldState || null) as Prisma.NullableJsonNullValueInput | Prisma.InputJsonValue,
          newState: input.newState as Prisma.InputJsonValue,
          processedBy: input.processedBy,
          processingTimeMs: input.processingTimeMs,
        }
      });

      logger.debug("EventStore: domain log created", {
        domain: input.domain,
        action: input.action,
        entityId: input.entityId
      });
    } catch (error) {
      logger.error("EventStore: failed to log domain", { error, input });
      throw error;
    }
  }

  /**
   * Listar eventos por tenant
   */
  async listByTenant(tenantId: string, limit: number = 50, offset: number = 0) {
    return prisma.systemEvent.findMany({
      where: { tenantId },
      orderBy: { createdAt: "desc" },
      take: limit,
      skip: offset,
      include: {
        domainLogs: true
      }
    });
  }

  /**
   * Listar eventos por aggregate
   */
  async listByAggregate(tenantId: string, aggregateType: AggregateType, aggregateId: string) {
    return prisma.systemEvent.findMany({
      where: {
        tenantId,
        aggregateType,
        aggregateId
      },
      orderBy: { createdAt: "asc" },
      include: {
        domainLogs: true
      }
    });
  }

  /**
   * Listar eventos por tipo
   */
  async listByType(tenantId: string, eventType: EventType, limit: number = 50) {
    return prisma.systemEvent.findMany({
      where: {
        tenantId,
        eventType
      },
      orderBy: { createdAt: "desc" },
      take: limit,
      include: {
        domainLogs: true
      }
    });
  }

  /**
   * Obter evento por ID com logs
   */
  async getById(eventId: string) {
    return prisma.systemEvent.findUnique({
      where: { id: eventId },
      include: {
        domainLogs: true
      }
    });
  }

  /**
   * Atualizar status do evento
   */
  async updateStatus(
    eventId: string, 
    status: "pending" | "processing" | "processed" | "failed",
    errorMessage?: string
  ) {
    return prisma.systemEvent.update({
      where: { id: eventId },
      data: {
        status,
        errorMessage,
        processedAt: status === "processed" ? new Date() : undefined
      }
    });
  }

  /**
   * Criar snapshot de agregado
   */
  async createSnapshot(
    tenantId: string,
    aggregateType: AggregateType,
    aggregateId: string,
    state: Record<string, unknown>,
    lastEventId: string,
    lastEventType: string,
    eventCount: number
  ) {
    // Buscar última versão
    const lastSnapshot = await prisma.eventSnapshot.findFirst({
      where: {
        tenantId,
        aggregateType,
        aggregateId
      },
      orderBy: { version: "desc" }
    });

    const nextVersion = (lastSnapshot?.version || 0) + 1;

    return prisma.eventSnapshot.create({
      data: {
        tenantId,
        aggregateType,
        aggregateId,
        version: nextVersion,
        state: state as Prisma.InputJsonValue,
        lastEventId,
        lastEventType,
        eventCount
      }
    });
  }

  /**
   * Obter último snapshot de agregado
   */
  async getLatestSnapshot(
    tenantId: string,
    aggregateType: AggregateType,
    aggregateId: string
  ) {
    return prisma.eventSnapshot.findFirst({
      where: {
        tenantId,
        aggregateType,
        aggregateId
      },
      orderBy: { version: "desc" }
    });
  }
}

// Singleton
export const eventStore = new EventStore();
