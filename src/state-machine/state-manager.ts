// ============================================================
// STATE MANAGER - Core State Machine
// SPRINT 2: State Management
// ============================================================

import { prisma } from "../db";
import { logger } from "../utils/logger";

export type EntityType = 
  | "event" 
  | "proposal" 
  | "contract" 
  | "service_order" 
  | "production_order"
  | "lead";

export type State = 
  | "LEAD"
  | "QUALIFIED"
  | "PROPOSED"
  | "APPROVED"
  | "CONTRACTED"
  | "PLANNED"
  | "READY_FOR_PRODUCTION"
  | "IN_PRODUCTION"
  | "READY_FOR_EXECUTION"
  | "EXECUTING"
  | "CLOSED"
  | "ANALYZED"
  | "CANCELLED";

type ActorType = "user" | "agent" | "system" | "api" | "webhook";

interface StateTransitionRequest {
  tenantId: string;
  entityType: EntityType;
  entityId: string;
  fromState?: State; // opcional - verifica estado atual
  toState: State;
  reason?: string;
  actorType?: ActorType;
  actorId?: string;
  triggerEvent?: string;
  source?: string;
  autoValidate?: boolean;
}

interface TransitionResult {
  success: boolean;
  transitionId?: string;
  newStateId?: string;
  error?: string;
  warnings?: string[];
  blockedBy?: string;
}

export class StateManager {
  /**
   * Obter estado atual de uma entidade
   */
  async getCurrentState(
    tenantId: string,
    entityType: EntityType,
    entityId: string
  ): Promise<{ state: State; since: Date; version: number } | null> {
    const record = await prisma.entityStateRecord.findFirst({
      where: {
        tenantId,
        entityType,
        entityId,
        isCurrent: true
      },
      orderBy: { validFrom: "desc" }
    });

    if (!record) return null;

    return {
      state: record.currentState as State,
      since: record.validFrom,
      version: record.version
    };
  }

  /**
   * Definir estado inicial de uma entidade
   */
  async setInitialState(
    tenantId: string,
    entityType: EntityType,
    entityId: string,
    initialState: State = "LEAD",
    actorId?: string
  ): Promise<string> {
    // Verificar se já existe estado
    const existing = await this.getCurrentState(tenantId, entityType, entityId);
    if (existing) {
      throw new Error(`Entity ${entityType}:${entityId} already has state ${existing.state}`);
    }

    const record = await prisma.entityStateRecord.create({
      data: {
        tenantId,
        entityType,
        entityId,
        currentState: initialState,
        enteredBy: actorId,
        actorType: "system",
        isCurrent: true,
        validFrom: new Date(),
        version: 1
      }
    });

    // Log de transição inicial
    await this.logTransition({
      tenantId,
      entityType,
      entityId,
      fromState: null,
      toState: initialState,
      actorType: "system",
      actorId,
      reason: "Initial state set",
      status: "completed"
    });

    logger.info("StateManager: initial state set", {
      entityType,
      entityId,
      state: initialState
    });

    return record.id;
  }

  /**
   * Realizar transição de estado
   */
  async transition(request: StateTransitionRequest): Promise<TransitionResult> {
    const startTime = Date.now();

    logger.info("StateManager: attempting transition", {
      entityType: request.entityType,
      entityId: request.entityId,
      toState: request.toState
    });

    try {
      // 1. Verificar estado atual se fromState fornecido
      const current = await this.getCurrentState(
        request.tenantId,
        request.entityType,
        request.entityId
      );

      if (request.fromState && current?.state !== request.fromState) {
        return {
          success: false,
          error: `Expected state ${request.fromState} but entity is in ${current?.state}`,
          blockedBy: "STATE_MISMATCH"
        };
      }

      const fromState = current?.state || null;

      // 2. Verificar regras de transição
      const rule = await prisma.stateTransitionRule.findFirst({
        where: {
          tenantId: request.tenantId,
          entityType: request.entityType,
          fromState: fromState || "",
          toState: request.toState,
          isActive: true
        }
      });

      if (!rule && fromState) {
        // Verificar se é transição direta conhecida
        const directTransition = await this.isValidTransition(
          request.entityType,
          fromState,
          request.toState
        );

        if (!directTransition) {
          return {
            success: false,
            error: `Invalid transition from ${fromState} to ${request.toState} for ${request.entityType}`,
            blockedBy: "INVALID_TRANSITION"
          };
        }
      }

      // 3. Verificar permissões
      if (rule != null && (rule.allowedActors?.length ?? 0) > 0) {
        const actorKey = `${request.actorType}:${request.actorId || "anonymous"}`;
        const hasPermission = rule.allowedActors.some(allowed => {
          if (allowed === "system") return request.actorType === "system";
          if (allowed === request.actorType) return true;
          return allowed === actorKey;
        });

        if (!hasPermission) {
          return {
            success: false,
            error: `Actor ${actorKey} not authorized for this transition`,
            blockedBy: "UNAUTHORIZED"
          };
        }
      }

      // 4. Validações de integridade
      const warnings: string[] = [];
      
      if (request.autoValidate !== false) {
        const integrity = await this.checkIntegrityBeforeTransition(
          request.tenantId,
          request.entityType,
          request.entityId,
          request.toState
        );

        if (integrity.blocking) {
          // Log de transição bloqueada
          await this.logTransition({
            ...request,
            fromState,
            status: "blocked",
            blockedBy: integrity.blocking
          });

          return {
            success: false,
            error: `Transition blocked: ${integrity.blocking}`,
            blockedBy: integrity.blocking,
            warnings: integrity.warnings
          };
        }

        warnings.push(...integrity.warnings);
      }

      // 5. Executar transição
      const completedAt = new Date();
      
      // Inativar estado anterior
      if (current) {
        await prisma.entityStateRecord.updateMany({
          where: {
            tenantId: request.tenantId,
            entityType: request.entityType,
            entityId: request.entityId,
            isCurrent: true
          },
          data: {
            isCurrent: false,
            validUntil: new Date()
          }
        });
      }

      // Criar novo estado
      const newStateRecord = await prisma.entityStateRecord.create({
        data: {
          tenantId: request.tenantId,
          entityType: request.entityType,
          entityId: request.entityId,
          currentState: request.toState,
          previousState: fromState || undefined,
          enteredBy: request.actorId,
          actorType: request.actorType || "system",
          reason: request.reason,
          source: request.source,
          isCurrent: true,
          validFrom: new Date(),
          version: (current?.version || 0) + 1
        }
      });

      // 6. Log de sucesso
      const transitionLog = await this.logTransition({
        ...request,
        fromState,
        status: "completed",
        completedAt,
        durationMs: Date.now() - startTime
      });

      logger.info("StateManager: transition completed", {
        entityType: request.entityType,
        entityId: request.entityId,
        fromState,
        toState: request.toState,
        durationMs: Date.now() - startTime
      });

      return {
        success: true,
        transitionId: transitionLog,
        newStateId: newStateRecord.id,
        warnings: warnings.length > 0 ? warnings : undefined
      };

    } catch (error) {
      // Log de erro
      await this.logTransition({
        ...request,
        fromState: request.fromState ?? null,
        status: "failed",
        errorMessage: error instanceof Error ? error.message : "Unknown error"
      });

      logger.error("StateManager: transition failed", {
        error,
        entityType: request.entityType,
        entityId: request.entityId
      });

      return {
        success: false,
        error: error instanceof Error ? error.message : "Transition failed"
      };
    }
  }

  /**
   * Verificar integridade antes de transição
   */
  private async checkIntegrityBeforeTransition(
    tenantId: string,
    entityType: EntityType,
    entityId: string,
    toState: State
  ): Promise<{ blocking?: string; warnings: string[] }> {
    const warnings: string[] = [];

    // Verificações específicas por estado destino
    switch (toState) {
      case "APPROVED": {
        // Verificar se tem financials
        const event = await prisma.event.findFirst({
          where: {
            id: entityId,
            tenantId,
            revenueTotal: { not: null },
            cmvTotal: { not: null }
          }
        });

        if (!event?.revenueTotal || !event?.cmvTotal) {
          return {
            blocking: "MISSING_FINANCIALS",
            warnings: ["Evento sem dados financeiros completos"]
          };
        }

        // Verificar margem mínima
        if (event.marginPct && event.marginPct < 15) {
          warnings.push(`Margem de ${event.marginPct}% está abaixo do ideal (15%)`);
        }

        break;
      }

      case "IN_PRODUCTION": {
        // Verificar se planejamento existe
        const event = await prisma.event.findFirst({
          where: { id: entityId, tenantId }
        });

        if (!event?.eventDate) {
          return {
            blocking: "MISSING_PRODUCTION_DATA",
            warnings: ["Sem data de evento definida"]
          };
        }
        break;
      }

      case "READY_FOR_EXECUTION": {
        // Verificar estoque
        const hasSufficientStock = await this.checkStockAvailability(tenantId, entityId);
        if (!hasSufficientStock) {
          warnings.push("Estoque insuficiente para todos os itens");
        }
        break;
      }

      case "CLOSED": {
        // Verificar se evento foi executado
        const currentState = await this.getCurrentState(tenantId, entityType, entityId);
        if (currentState?.state !== "EXECUTING") {
          return {
            blocking: "NOT_EXECUTED",
            warnings: ["Evento não pode ser fechado sem ter sido executado"]
          };
        }
        break;
      }
    }

    return { warnings };
  }

  /**
   * Verificar disponibilidade de estoque
   */
  private async checkStockAvailability(
    tenantId: string,
    entityId: string
  ): Promise<boolean> {
    // Simplificado - em produção verificaria items do evento vs estoque real
    return true; // Placeholder
  }

  /**
   * Verificar se transição é válida
   */
  private async isValidTransition(
    entityType: EntityType,
    from: State,
    to: State
  ): Promise<boolean> {
    // Pipeline válido:
    // LEAD → QUALIFIED → PROPOSED → APPROVED → CONTRACTED → PLANNED → READY_FOR_PRODUCTION → IN_PRODUCTION → READY_FOR_EXECUTION → EXECUTING → CLOSED → ANALYZED
    
    const validFlows: Record<string, string[]> = {
      "LEAD": ["QUALIFIED", "CANCELLED"],
      "QUALIFIED": ["PROPOSED", "CANCELLED"],
      "PROPOSED": ["APPROVED", "CANCELLED"],
      "APPROVED": ["CONTRACTED", "CANCELLED"],
      "CONTRACTED": ["PLANNED", "CANCELLED"],
      "PLANNED": ["READY_FOR_PRODUCTION", "CANCELLED"],
      "READY_FOR_PRODUCTION": ["IN_PRODUCTION", "CANCELLED"],
      "IN_PRODUCTION": ["READY_FOR_EXECUTION", "CANCELLED"],
      "READY_FOR_EXECUTION": ["EXECUTING", "CANCELLED"],
      "EXECUTING": ["CLOSED"],
      "CLOSED": ["ANALYZED"],
      "ANALYZED": [],
      "CANCELLED": []
    };

    const validNext = validFlows[from] || [];
    return validNext.includes(to) || from === to; // Permitir atualização do mesmo estado
  }

  /**
   * Log de transição
   */
  private async logTransition(params: {
    tenantId: string;
    entityType: EntityType;
    entityId: string;
    fromState: State | null;
    toState?: string;
    status: "completed" | "failed" | "blocked";
    reason?: string;
    actorType?: ActorType;
    actorId?: string;
    triggerEvent?: string;
    source?: string;
    errorMessage?: string;
    blockedBy?: string;
    completedAt?: Date;
    durationMs?: number;
  }): Promise<string> {
    const transition = await prisma.stateTransition.create({
      data: {
        tenantId: params.tenantId,
        entityType: params.entityType,
        entityId: params.entityId,
        fromState: params.fromState || "",
        toState: params.toState || "",
        actorType: params.actorType || "system",
        actorId: params.actorId,
        reason: params.reason,
        blockedBy: params.blockedBy,
        status: params.status,
        errorMessage: params.errorMessage,
        completedAt: params.completedAt,
        durationMs: params.durationMs
      }
    });

    return transition.id;
  }

  /**
   * Obter histórico de transições
   */
  async getTransitionHistory(
    tenantId: string,
    entityType: EntityType,
    entityId: string,
    limit: number = 50
  ) {
    return prisma.stateTransition.findMany({
      where: {
        tenantId,
        entityType,
        entityId
      },
      orderBy: { attemptedAt: "desc" },
      take: limit
    });
  }

  /**
   * Reverter última transição (rollback)
   */
  async rollback(
    tenantId: string,
    entityType: EntityType,
    entityId: string,
    actorId?: string
  ): Promise<TransitionResult> {
    const current = await this.getCurrentState(tenantId, entityType, entityId);
    if (!current) {
      return { success: false, error: "No current state found" };
    }

    // Buscar estado anterior
    const previousRecord = await prisma.entityStateRecord.findFirst({
      where: {
        tenantId,
        entityType,
        entityId,
        isCurrent: false,
        validUntil: { not: null }
      },
      orderBy: { validUntil: "desc" }
    });

    if (!previousRecord?.previousState) {
      return { success: false, error: "No previous state to rollback to" };
    }

    // Realizar rollback
    const result = await this.transition({
      tenantId,
      entityType,
      entityId,
      fromState: current.state,
      toState: previousRecord.previousState as State,
      reason: "Rollback from " + current.state,
      actorType: "system",
      actorId
    });

    // Atualizar log anterior (find latest completed transition and mark rolled back)
    const latestTransition = await prisma.stateTransition.findFirst({
      where: { tenantId, entityType, entityId, status: "completed" },
      orderBy: { attemptedAt: "desc" }
    });
    if (latestTransition) {
      await prisma.stateTransition.update({
        where: { id: latestTransition.id },
        data: { status: "rolled_back" }
      });
    }

    return result;
  }
}

// Singleton
export const stateManager = new StateManager();
