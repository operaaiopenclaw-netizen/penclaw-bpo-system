// ============================================================
// EVENT OPS AGENT — Gastronomy execution engine
// Boundary: pre-event readiness, execution checkpoints,
//           occurrence logging, teardown, consumption snapshot.
// Does NOT do procurement. Does NOT do financial projection.
// ============================================================
import { BaseAgent, AgentExecutionContext, AgentExecutionResult, AgentAction } from "./base-agent";
import { prisma } from "../db";
import { logger } from "../utils/logger";

// Checkpoint sequence for a gastronomy event
const CHECKPOINT_SEQUENCE = [
  "SETUP",          // venue setup, kitchen prep, equipment check
  "PRE_SERVICE",    // staff briefing, bar setup, coffee station ready
  "SERVICE_START",  // service begins, floor active
  "SERVICE_ACTIVE", // mid-service monitoring
  "COFFEE_BREAK",   // optional — coffee / cocktail hour
  "SERVICE_END",    // last course served
  "TEARDOWN",       // breakdown, leftover record, equipment return
] as const;

type CheckpointStage = typeof CHECKPOINT_SEQUENCE[number];

interface ReadinessArea {
  area: string;
  ready: boolean;
  issues: string[];
  responsible: string;
}

export class EventOpsAgent extends BaseAgent {
  readonly name = "event_ops_agent";
  readonly description = "Execução gastronômica: prontidão, checkpoints, ocorrências, desmontagem, consumo real";
  readonly defaultRiskLevel = "R1" as const;

  async execute(context: AgentExecutionContext): Promise<AgentExecutionResult> {
    const start = Date.now();
    logger.info("EventOpsAgent executing", { runId: context.agentRunId });
    await this.logStep(context.agentRunId, "running", { input: context.input });

    try {
      const mode = String(context.input.mode ?? "pre_event"); // pre_event | execution | post_event
      const eventId    = context.input.eventId    ? String(context.input.eventId)    : undefined;
      const sessionId  = context.input.sessionId  ? String(context.input.sessionId)  : undefined;

      let result: Record<string, unknown>;
      let actions: AgentAction[];
      let riskLevel: "R0" | "R1" | "R2" | "R3" | "R4";

      switch (mode) {
        case "execution":
          ({ result, actions, riskLevel } = await this.executionMode(context, eventId, sessionId) as { result: Record<string, unknown>; actions: AgentAction[]; riskLevel: "R0" | "R1" | "R2" | "R3" | "R4" });
          break;
        case "post_event":
          ({ result, actions, riskLevel } = await this.postEventMode(context, eventId, sessionId) as { result: Record<string, unknown>; actions: AgentAction[]; riskLevel: "R0" | "R1" | "R2" | "R3" | "R4" });
          break;
        default:
          ({ result, actions, riskLevel } = await this.preEventMode(context, eventId) as { result: Record<string, unknown>; actions: AgentAction[]; riskLevel: "R0" | "R1" | "R2" | "R3" | "R4" });
      }

      const output: Record<string, unknown> = {
        _actions: actions,
        _summary: String(result._summary ?? ""),
        ...result,
      };
      output["_summary"] = String(result._summary ?? ""); // ensure top-level

      await this.logStep(context.agentRunId, "completed", { output });
      logger.info("EventOpsAgent completed", { runId: context.agentRunId, mode, actions: actions.length });

      return { success: true, output, riskLevel, latencyMs: Date.now() - start };

    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      await this.logStep(context.agentRunId, "failed", { error: msg });
      return {
        success: false,
        output: { _actions: [], _summary: `Falha: ${msg}`, error: msg },
        riskLevel: "R3",
        latencyMs: Date.now() - start
      };
    }
  }

  // ----------------------------------------------------------
  // MODE: pre_event — readiness checks before the event
  // ----------------------------------------------------------
  private async preEventMode(
    context: AgentExecutionContext,
    eventId?: string
  ) {
    const numGuests   = Math.max(1, parseInt(String(context.input.numGuests ?? 100)));
    const eventType   = String(context.input.eventType ?? "corporativo").toLowerCase();
    const eventDate   = context.input.eventDate ? new Date(String(context.input.eventDate)) : undefined;
    const daysUntil   = eventDate ? Math.ceil((eventDate.getTime() - Date.now()) / 86_400_000) : 30;

    const areas = this.assessReadiness(numGuests, eventType, daysUntil, context.input);
    const blockers = areas.filter(a => !a.ready);
    const actions: AgentAction[] = [];

    // Alert on unready critical areas
    for (const area of blockers) {
      actions.push({
        type: "ALERT_RISK",
        payload: {
          code: "READINESS_FAIL",
          message: `Área não pronta: ${area.area} — ${area.issues.join("; ")}`,
          severity: area.area === "kitchen" || area.area === "staff" ? "critical" : "warning",
          area: area.area,
          eventId,
          daysUntil
        }
      });
    }

    const allReady = blockers.length === 0;
    const riskLevel: "R1" | "R2" | "R3" = allReady ? "R1"
      : blockers.some(b => b.area === "staff" || b.area === "kitchen") ? "R3"
      : "R2";

    const result = {
      _summary: allReady
        ? `Evento pronto. ${areas.length} áreas verificadas. ${numGuests} pax.`
        : `${blockers.length} área(s) com pendências: ${blockers.map(b => b.area).join(", ")}`,
      mode: "pre_event",
      ready: allReady,
      daysUntil,
      readiness: areas,
      checklistTimeline: this.buildPreEventTimeline(daysUntil, eventType, numGuests),
      staffPlan: this.buildStaffPlan(numGuests, eventType),
      kitchenTimeline: this.buildKitchenTimeline(eventDate),
    };

    return { result, actions, riskLevel };
  }

  // ----------------------------------------------------------
  // MODE: execution — live event monitoring & checkpoints
  // ----------------------------------------------------------
  private async executionMode(
    context: AgentExecutionContext,
    eventId?: string,
    sessionId?: string
  ) {
    const stage = String(context.input.stage ?? "SERVICE_ACTIVE") as CheckpointStage;
    const numGuests = parseInt(String(context.input.numGuests ?? 100));
    const occurrences = this.extractOccurrences(context.input);
    const actions: AgentAction[] = [];

    // Confirm the current checkpoint
    if (sessionId) {
      actions.push({
        type: "CONFIRM_CHECKPOINT",
        payload: {
          sessionId,
          stage,
          confirmedAt: new Date().toISOString(),
          guestCount: numGuests,
          notes: context.input.notes ?? null
        }
      });
    }

    // Log any occurrences reported
    for (const occ of occurrences) {
      actions.push({
        type: "FLAG_OCCURRENCE",
        payload: {
          sessionId,
          eventId,
          type: occ.type,
          severity: occ.severity,
          description: occ.description,
          area: occ.area,
          reportedAt: new Date().toISOString()
        }
      });
    }

    const criticalOccs = occurrences.filter(o => o.severity === "critical");
    const riskLevel = criticalOccs.length > 0 ? "R3" : occurrences.length > 0 ? "R2" : "R1";

    const result = {
      _summary: `Checkpoint ${stage} confirmado. ${occurrences.length} ocorrência(s) registrada(s)${criticalOccs.length > 0 ? ` — ${criticalOccs.length} CRÍTICA(S)` : ""}.`,
      mode: "execution",
      stage,
      nextStage: this.nextCheckpoint(stage),
      checkpointConfirmed: !!sessionId,
      occurrencesLogged: occurrences.length,
      criticalOccurrences: criticalOccs.length,
      serviceMonitor: this.buildServiceMonitor(stage, numGuests, context.input),
    };

    return { result, actions, riskLevel };
  }

  // ----------------------------------------------------------
  // MODE: post_event — teardown + consumption snapshot
  // ----------------------------------------------------------
  private async postEventMode(
    context: AgentExecutionContext,
    eventId?: string,
    sessionId?: string
  ) {
    const numGuests    = parseInt(String(context.input.numGuests ?? 100));
    const consumedItems = this.extractConsumedItems(context.input);
    const actions: AgentAction[] = [];

    // Record actual consumption per item
    for (const item of consumedItems) {
      actions.push({
        type: "RECORD_CONSUMPTION",
        payload: {
          eventId,
          sessionId,
          itemCode: item.itemCode,
          itemName: item.itemName,
          quantityConsumed: item.quantityConsumed,
          quantityLeftover: item.quantityLeftover ?? 0,
          unit: item.unit,
          recordedAt: new Date().toISOString()
        }
      });
    }

    // Confirm teardown
    if (sessionId) {
      actions.push({
        type: "CONFIRM_TEARDOWN",
        payload: {
          sessionId,
          eventId,
          numGuests,
          itemsRecorded: consumedItems.length,
          confirmedAt: new Date().toISOString(),
          notes: context.input.teardownNotes ?? null
        }
      });
    }

    // Trigger reconciliation if consumption data provided
    if (consumedItems.length > 0 && eventId) {
      actions.push({
        type: "RECONCILE_EVENT",
        payload: {
          eventId,
          sessionId,
          numGuests,
          consumedItems
        }
      });
    }

    const result = {
      _summary: `Desmontagem confirmada. ${consumedItems.length} item(ns) de consumo registrado(s). Reconciliação ${consumedItems.length > 0 ? "solicitada" : "pendente (sem dados de consumo)"}.`,
      mode: "post_event",
      teardownConfirmed: !!sessionId,
      consumptionSnapshot: consumedItems,
      reconciliationRequested: consumedItems.length > 0,
      nextSteps: [
        "Conferir baixa de estoque via reconciliação",
        "Gerar relatório financeiro pós-evento",
        "Registrar consumo real no histórico para melhorar previsões futuras",
      ],
    };

    return { result, actions, riskLevel: "R1" as const };
  }

  // ----------------------------------------------------------
  // Readiness assessment — per area
  // ----------------------------------------------------------
  private assessReadiness(
    numGuests: number,
    eventType: string,
    daysUntil: number,
    input: Record<string, unknown>
  ): ReadinessArea[] {
    const staffRequired = Math.ceil(numGuests / 20) + 2;
    const staffConfirmed = parseInt(String(input.staffConfirmed ?? 0));
    const hasMenu       = Boolean(input.menuConfirmed ?? false);
    const hasVenue      = Boolean(input.venueConfirmed ?? daysUntil > 14);
    const hasEquipment  = Boolean(input.equipmentConfirmed ?? daysUntil > 7);
    const hasBar        = ["casamento", "formatura", "aniversario", "confraternizacao"].includes(eventType);

    const areas: ReadinessArea[] = [
      {
        area: "kitchen",
        ready: hasMenu,
        issues: hasMenu ? [] : ["Cardápio não confirmado com a cozinha"],
        responsible: "Chef de Produção"
      },
      {
        area: "staff",
        ready: staffConfirmed >= staffRequired,
        issues: staffConfirmed >= staffRequired ? [] : [
          `${staffRequired - staffConfirmed} pessoa(s) faltando (necessário: ${staffRequired}, confirmado: ${staffConfirmed})`
        ],
        responsible: "Gerente de Operações"
      },
      {
        area: "venue",
        ready: hasVenue,
        issues: hasVenue ? [] : ["Localização não confirmada"],
        responsible: "Coordenador de Logística"
      },
      {
        area: "equipment",
        ready: hasEquipment,
        issues: hasEquipment ? [] : ["Equipamentos não conferidos"],
        responsible: "Coordenador de Logística"
      },
    ];

    if (hasBar) {
      const barReady = Boolean(input.barConfirmed ?? daysUntil > 3);
      areas.push({
        area: "bar",
        ready: barReady,
        issues: barReady ? [] : ["Setup do bar não confirmado"],
        responsible: "Barman Responsável"
      });
    }

    if (eventType === "corporativo") {
      const coffeeReady = Boolean(input.coffeeStationConfirmed ?? true);
      areas.push({
        area: "coffee_station",
        ready: coffeeReady,
        issues: coffeeReady ? [] : ["Estação de café não montada"],
        responsible: "Equipe de Apoio"
      });
    }

    return areas;
  }

  private buildPreEventTimeline(
    daysUntil: number,
    eventType: string,
    numGuests: number
  ): Array<{ milestone: string; deadline: string; responsible: string; critical: boolean }> {
    const setupHours = this.calcSetupHours(eventType, numGuests);
    return [
      { milestone: "Confirmar cardápio com chef",      deadline: `D-${Math.max(daysUntil - 1, 5)}`,  responsible: "Chef de Produção",         critical: true  },
      { milestone: "Confirmar equipe de serviço",      deadline: "D-3",                               responsible: "Gerente de Operações",     critical: true  },
      { milestone: "Verificar estoque de bebidas",     deadline: "D-3",                               responsible: "Gestor de Estoque",        critical: true  },
      { milestone: "Briefing completo da equipe",      deadline: "D-1",                               responsible: "Chef de Produção",         critical: true  },
      { milestone: "Conferência de equipamentos",      deadline: "D-1",                               responsible: "Coordenador de Logística", critical: false },
      { milestone: "Chegada da equipe ao local",       deadline: `H-${setupHours}`,                   responsible: "Todos",                   critical: true  },
      { milestone: "Finalização do setup",             deadline: "H-1",                               responsible: "Coordenador de Logística", critical: true  },
      { milestone: "Último check antes de abertura",   deadline: "H-0:30",                            responsible: "Gerente de Operações",     critical: true  },
    ];
  }

  private buildStaffPlan(numGuests: number, eventType: string): Record<string, number> {
    const base = Math.ceil(numGuests / 20);
    const plan: Record<string, number> = {
      garcons: base,
      supervisores: Math.max(1, Math.ceil(base / 5)),
      cozinha: Math.ceil(numGuests / 50) + 1,
    };
    if (["casamento", "formatura", "aniversario"].includes(eventType)) {
      plan.barmans = Math.ceil(numGuests / 80) + 1;
    }
    if (eventType === "corporativo") {
      plan.coffee_station = 1;
    }
    plan.total = Object.values(plan).reduce((s, v) => s + v, 0);
    return plan;
  }

  private buildKitchenTimeline(eventDate?: Date): Array<{ time: string; activity: string }> {
    if (!eventDate) return [];
    const d = eventDate;
    return [
      { time: this.fmtRelative(d, -48), activity: "Compras e recebimento de insumos" },
      { time: this.fmtRelative(d, -24), activity: "Pré-preparo: marinadas, bases, massas" },
      { time: this.fmtRelative(d, -6),  activity: "Montagem de mise en place completa" },
      { time: this.fmtRelative(d, -3),  activity: "Início da cocção de proteínas" },
      { time: this.fmtRelative(d, -1),  activity: "Finalização e montagem de pratos frios" },
      { time: this.fmtRelative(d, 0),   activity: "Início do serviço — linha de produção ativa" },
    ];
  }

  private buildServiceMonitor(
    stage: CheckpointStage,
    numGuests: number,
    input: Record<string, unknown>
  ): Record<string, unknown> {
    return {
      stage,
      guestCount: numGuests,
      tablesTurned: input.tablesTurned ?? 0,
      coursesServed: input.coursesServed ?? 0,
      beverageConsumptionPct: input.beverageConsumptionPct ?? 0,
      kitchenStatus: input.kitchenStatus ?? "unknown",
      barStatus: input.barStatus ?? "unknown",
    };
  }

  private extractOccurrences(input: Record<string, unknown>): Array<{
    type: string; severity: string; description: string; area: string;
  }> {
    const raw = input.occurrences;
    if (!Array.isArray(raw)) return [];
    return raw.map((o: unknown) => {
      const obj = o as Record<string, unknown>;
      return {
        type:        String(obj.type        ?? "operational"),
        severity:    String(obj.severity    ?? "warning"),
        description: String(obj.description ?? ""),
        area:        String(obj.area        ?? "general"),
      };
    });
  }

  private extractConsumedItems(input: Record<string, unknown>): Array<{
    itemCode: string; itemName: string; quantityConsumed: number;
    quantityLeftover?: number; unit: string;
  }> {
    const raw = input.consumedItems ?? input.consumption;
    if (!Array.isArray(raw)) return [];
    return raw.map((i: unknown) => {
      const obj = i as Record<string, unknown>;
      return {
        itemCode:          String(obj.itemCode ?? ""),
        itemName:          String(obj.itemName ?? ""),
        quantityConsumed:  parseFloat(String(obj.quantityConsumed ?? obj.consumed ?? 0)),
        quantityLeftover:  obj.quantityLeftover !== undefined ? parseFloat(String(obj.quantityLeftover)) : undefined,
        unit:              String(obj.unit ?? "un"),
      };
    }).filter(i => i.itemCode);
  }

  private nextCheckpoint(stage: CheckpointStage): CheckpointStage | null {
    const idx = CHECKPOINT_SEQUENCE.indexOf(stage);
    return idx >= 0 && idx < CHECKPOINT_SEQUENCE.length - 1
      ? CHECKPOINT_SEQUENCE[idx + 1]
      : null;
  }

  private calcSetupHours(eventType: string, numGuests: number): number {
    const base: Record<string, number> = {
      casamento: 5, formatura: 6, corporativo: 3, aniversario: 4, confraternizacao: 4
    };
    return (base[eventType] ?? 4) + Math.ceil(numGuests / 150);
  }

  private fmtRelative(base: Date, offsetHours: number): string {
    const d = new Date(base.getTime() + offsetHours * 3_600_000);
    return d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  }
}

export const eventOpsAgent = new EventOpsAgent();

import { agentRegistry } from "./base-agent";
agentRegistry.register(eventOpsAgent);
