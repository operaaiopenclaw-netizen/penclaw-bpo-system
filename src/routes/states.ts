// ============================================================
// STATE ROUTES - State Machine API
// SPRINT 2: Query and Control endpoints
// ============================================================

import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { z } from "zod";
import { stateManager, State, EntityType } from "../state-machine/state-manager";
import { seedTransitionRules, EVENT_PIPELINE_RULES as transitionRules } from "../state-machine/transition-rules";
import { logger } from "../utils/logger";
import { prisma } from "../db";
import { config } from "../config/env";

const DEFAULT_TENANT = config.DEFAULT_TENANT_ID;

const getCurrentStateSchema = z.object({
  tenantId: z.string().default(DEFAULT_TENANT),
  entityType: z.enum(["event", "proposal", "contract", "service_order", "production_order", "lead"]),
  entityId: z.string()
});

const transitionSchema = z.object({
  tenantId: z.string().default(DEFAULT_TENANT),
  entityType: z.enum(["event", "proposal", "contract", "service_order", "production_order", "lead"]),
  entityId: z.string(),
  toState: z.enum([
    "LEAD", "QUALIFIED", "PROPOSED", "APPROVED", "CONTRACTED",
    "PLANNED", "READY_FOR_PRODUCTION", "IN_PRODUCTION",
    "READY_FOR_EXECUTION", "EXECUTING", "CLOSED", "ANALYZED", "CANCELLED"
  ]),
  reason: z.string().optional(),
  actorType: z.enum(["user", "agent", "system", "api"]).default("user"),
  actorId: z.string().optional(),
  source: z.string().optional()
});

const listByStateSchema = z.object({
  tenantId: z.string().default(DEFAULT_TENANT),
  entityType: z.enum(["event", "proposal", "contract", "service_order", "production_order"]).optional(),
  state: z.enum([
    "LEAD", "QUALIFIED", "PROPOSED", "APPROVED", "CONTRACTED",
    "PLANNED", "READY_FOR_PRODUCTION", "IN_PRODUCTION",
    "READY_FOR_EXECUTION", "EXECUTING", "CLOSED", "ANALYZED", "CANCELLED"
  ]).optional(),
  limit: z.coerce.number().max(100).default(50),
  offset: z.coerce.number().default(0)
});

export async function statesRoutes(fastify: FastifyInstance): Promise<void> {

  // GET /states/current - Obter estado atual
  fastify.get("/current", async (
    request: FastifyRequest<{ Querystring: unknown }>,
    reply: FastifyReply
  ) => {
    try {
      const params = getCurrentStateSchema.parse(request.query);
      
      const current = await stateManager.getCurrentState(
        params.tenantId,
        params.entityType,
        params.entityId
      );

      if (!current) {
        return reply.status(404).send({
          success: false,
          error: "No state found",
          message: `Entity ${params.entityType}:${params.entityId} has no state record`
        });
      }

      return reply.send({
        success: true,
        data: {
          entityType: params.entityType,
          entityId: params.entityId,
          currentState: current.state,
          since: current.since,
          version: current.version
        }
      });
    } catch (error) {
      logger.error("States route: getCurrent failed", { error });
      return reply.status(400).send({
        success: false,
        error: "Invalid parameters"
      });
    }
  });

  // POST /states/transition - Realizar transição
  fastify.post("/transition", async (
    request: FastifyRequest<{ Body: unknown }>,
    reply: FastifyReply
  ) => {
    try {
      const params = transitionSchema.parse(request.body);

      const result = await stateManager.transition({
        tenantId: params.tenantId,
        entityType: params.entityType,
        entityId: params.entityId,
        toState: params.toState,
        reason: params.reason,
        actorType: params.actorType,
        actorId: params.actorId,
        source: params.source,
        autoValidate: true
      });

      return reply.send({
        success: result.success,
        data: result.success ? {
          transitionId: result.transitionId,
          newStateId: result.newStateId,
          fromState: result.warnings ? undefined : undefined, // Populated in result
          toState: params.toState,
          warnings: result.warnings
        } : undefined,
        error: result.success ? undefined : {
          message: result.error,
          blockedBy: result.blockedBy
        }
      });
    } catch (error) {
      logger.error("States route: transition failed", { error });
      return reply.status(500).send({
        success: false,
        error: "Transition failed",
        message: error instanceof Error ? error.message : "Unknown error"
      });
    }
  });

  // GET /states/history/:entityType/:entityId - Histórico de transições
  fastify.get("/history/:entityType/:entityId", async (
    request: FastifyRequest<{ 
      Params: { entityType: string; entityId: string };
      Querystring: { tenantId?: string; limit?: string }
    }>,
    reply: FastifyReply
  ) => {
    try {
      const tenantId = request.query.tenantId || DEFAULT_TENANT;
      const entityType = request.params.entityType as EntityType;
      const entityId = request.params.entityId;
      const limit = parseInt(request.query.limit || "20");

      const history = await stateManager.getTransitionHistory(
        tenantId,
        entityType,
        entityId,
        limit
      );

      return reply.send({
        success: true,
        data: history,
        meta: {
          entityType,
          entityId,
          count: history.length
        }
      });
    } catch (error) {
      logger.error("States route: history failed", { error });
      return reply.status(500).send({
        success: false,
        error: "Failed to get history"
      });
    }
  });

  // GET /states/list - Listar entidades por estado
  fastify.get("/list", async (
    request: FastifyRequest<{ Querystring: unknown }>,
    reply: FastifyReply
  ) => {
    try {
      const params = listByStateSchema.parse(request.query);

      const states = await prisma.entityStateRecord.findMany({
        where: {
          tenantId: params.tenantId,
          isCurrent: true,
          ...(params.entityType && { entityType: params.entityType }),
          ...(params.state && { currentState: params.state })
        },
        take: params.limit,
        skip: params.offset,
        orderBy: { enteredAt: "desc" }
      });

      return reply.send({
        success: true,
        data: states,
        meta: {
          filter: {
            entityType: params.entityType,
            state: params.state
          },
          count: states.length,
          limit: params.limit,
          offset: params.offset
        }
      });
    } catch (error) {
      logger.error("States route: list failed", { error });
      return reply.status(400).send({
        success: false,
        error: "Invalid parameters"
      });
    }
  });

  // GET /states/pipeline - Visualizar pipeline
  fastify.get("/pipeline", async (
    request: FastifyRequest<{ Querystring: { tenantId?: string } }>,
    reply: FastifyReply
  ) => {
    try {
      const tenantId = request.query.tenantId || DEFAULT_TENANT;

      // Agregar eventos por estado — uses camelCase columns (V005 table)
      const pipeline = await prisma.$queryRaw`
        SELECT
          "currentState",
          COUNT(*)::int                                                              AS count,
          SUM(CASE WHEN "validFrom" < NOW() - INTERVAL '7 days' THEN 1 ELSE 0 END)::int AS stale,
          SUM(CASE WHEN "validFrom" < NOW() - INTERVAL '3 days' THEN 1 ELSE 0 END)::int AS warning
        FROM entity_states
        WHERE "tenantId" = ${tenantId}
          AND "isCurrent" = true
          AND "entityType" = 'event'
        GROUP BY "currentState"
        ORDER BY
          CASE "currentState"
            WHEN 'LEAD'                 THEN 1
            WHEN 'QUALIFIED'            THEN 2
            WHEN 'PROPOSED'             THEN 3
            WHEN 'APPROVED'             THEN 4
            WHEN 'CONTRACTED'           THEN 5
            WHEN 'PLANNED'              THEN 6
            WHEN 'READY_FOR_PRODUCTION' THEN 7
            WHEN 'IN_PRODUCTION'        THEN 8
            WHEN 'READY_FOR_EXECUTION'  THEN 9
            WHEN 'EXECUTING'            THEN 10
            WHEN 'CLOSED'               THEN 11
            WHEN 'ANALYZED'             THEN 12
            ELSE 99
          END
      `;

      return reply.send({
        success: true,
        data: pipeline,
        pipeline_order: [
          "LEAD", "QUALIFIED", "PROPOSED", "APPROVED", "CONTRACTED",
          "PLANNED", "READY_FOR_PRODUCTION", "IN_PRODUCTION",
          "READY_FOR_EXECUTION", "EXECUTING", "CLOSED", "ANALYZED"
        ]
      });
    } catch (error) {
      logger.error("States route: pipeline failed", { error });
      return reply.status(500).send({
        success: false,
        error: "Failed to get pipeline"
      });
    }
  });

  // POST /states/test - Criar cenário de teste completo
  fastify.post("/test", async (
    request: FastifyRequest<{ Body: { tenantId?: string } }>,
    reply: FastifyReply
  ) => {
    try {
      const tenantId = request.body?.tenantId || DEFAULT_TENANT;
      
      logger.info("States route: creating state machine test scenario");

      // 1. Criar evento de teste via raw SQL (events table uses snake_case columns)
      const testEventId = `test-state-${Date.now()}`;
      const rows = await prisma.$queryRaw<{ id: string }[]>`
        INSERT INTO events (id, tenant_id, cost_center_id, name, event_type, event_date, guests, status, event_id)
        SELECT
          gen_random_uuid(),
          t.id,
          cc.id,
          ${testEventId},
          'Casamento',
          '2026-06-15'::date,
          100,
          'test',
          ${testEventId}
        FROM tenants t
        CROSS JOIN LATERAL (
          SELECT id FROM cost_centers WHERE tenant_id = t.id LIMIT 1
        ) cc
        ORDER BY t.created_at
        LIMIT 1
        RETURNING id
      `;
      if (rows.length === 0) {
        return reply.status(500).send({ success: false, error: "No tenant or cost_center found to create test event" });
      }
      const testEvent = { id: rows[0].id };

      // 2. Criar seed de regras se necessário
      const existingRules = await prisma.stateTransitionRule.count({
        where: { tenantId }
      });

      if (existingRules === 0) {
        await seedTransitionRules(tenantId);
      }

      // 3. Inicializar estado
      const initialStateId = await stateManager.setInitialState(
        tenantId,
        "event",
        testEvent.id,
        "LEAD",
        "system"
      );

      // 4. Executar pipeline de teste
      const transitions = [
        { to: "QUALIFIED" as State, reason: "Lead qualificado manualmente" },
        { to: "PROPOSED" as State, reason: "Proposta gerada" },
        { to: "APPROVED" as State, reason: "Cliente aprovou proposta" },
        { to: "CONTRACTED" as State, reason: "Contrato assinado" },
        { to: "PLANNED" as State, reason: "Planejamento concluído" },
      ];

      const results = [];
      for (const transition of transitions) {
        const result = await stateManager.transition({
          tenantId,
          entityType: "event",
          entityId: testEvent.id,
          toState: transition.to,
          reason: transition.reason,
          actorType: "system",
          actorId: "test-runner"
        });
        results.push({ state: transition.to, success: result.success, error: result.error });
      }

      // 5. Obter estado final e histórico
      const currentState = await stateManager.getCurrentState(tenantId, "event", testEvent.id);
      const history = await stateManager.getTransitionHistory(tenantId, "event", testEvent.id, 10);

      logger.info("States route: test scenario completed", {
        eventId: testEvent.id,
        currentState: currentState?.state
      });

      return reply.send({
        success: true,
        message: "State machine test scenario created",
        data: {
          eventId: testEvent.id,
          scenario: {
            initialState: "LEAD",
            transitions: results,
            finalState: currentState?.state,
            transitionCount: history.length
          },
          pipeline: [
            "LEAD → QUALIFIED → PROPOSED → APPROVED → CONTRACTED → PLANNED"
          ]
        }
      });
    } catch (error) {
      logger.error("States route: test failed", { error });
      return reply.status(500).send({
        success: false,
        error: "Test scenario failed",
        message: error instanceof Error ? error.message : "Unknown error"
      });
    }
  });

  // GET /states/rules - Listar regras de transição
  fastify.get("/rules", async (
    request: FastifyRequest<{ Querystring: { tenantId?: string; entityType?: string } }>,
    reply: FastifyReply
  ) => {
    try {
      const tenantId = request.query.tenantId || DEFAULT_TENANT;
      const entityType = request.query.entityType;

      const rules = await prisma.stateTransitionRule.findMany({
        where: {
          tenantId,
          isActive: true,
          ...(entityType && { entityType })
        },
        orderBy: { priority: "asc" }
      });

      return reply.send({
        success: true,
        data: rules,
        meta: {
          tenantId,
          entityType: entityType || "all",
          count: rules.length
        }
      });
    } catch (error) {
      logger.error("States route: rules failed", { error });
      return reply.status(500).send({
        success: false,
        error: "Failed to get rules"
      });
    }
  });
}
