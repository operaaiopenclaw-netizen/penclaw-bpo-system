import { BaseAgent, AgentExecutionContext, AgentExecutionResult } from "./base-agent";
import { prisma } from "../db";
import { logger } from "../utils/logger";

export class EventOpsAgent extends BaseAgent {
  readonly name = "event_ops_agent";
  readonly description = "Operações de evento e gestão de kickoff";
  readonly defaultRiskLevel = "R2" as const;

  async execute(context: AgentExecutionContext): Promise<AgentExecutionResult> {
    const startTime = Date.now();
    
    logger.info("EventOpsAgent executing", { 
      runId: context.agentRunId,
      companyId: context.companyId 
    });

    await this.logStep(context.agentRunId, "running", { input: context.input });

    try {
      const eventId = String(context.input.eventId || "");
      const eventDate = String(context.input.eventDate || "");
      const eventType = String(context.input.eventType || "");

      // Verificar kickoff
      const kickoffStatus = await this.checkKickoffReady(context);

      // Gerar checklist completo
      const checklistItems = this.generateChecklist(context, kickoffStatus);

      // Verificar equipe
      const staffStatus = await this.checkStaff(context);

      // Verificar cronograma
      const scheduleStatus = this.checkSchedule(context);

      // Verificar responsável operacional
      const responsibleStatus = await this.assignResponsibles(context);

      // Insumos
      const suppliesStatus = await this.checkSupplies(context);

      const result = {
        kickoffReady: kickoffStatus.ready,
        checklistItems,
        status: {
          staff: staffStatus,
          schedule: scheduleStatus,
          responsible: responsibleStatus,
          supplies: suppliesStatus
        },
        riskFactors: this.identifyRisks(staffStatus, suppliesStatus, scheduleStatus),
        actionRequired: kickoffStatus.ready ? [] : this.getRequiredActions(checklistItems),
        timeline: this.generateTimeline(eventDate)
      };

      await this.logStep(context.agentRunId, "completed", { output: result });

      logger.info("EventOpsAgent completed", { 
        runId: context.agentRunId,
        kickoffReady: result.kickoffReady
      });

      return {
        success: true,
        output: result,
        riskLevel: kickoffStatus.ready ? "R1" : "R3",
        latencyMs: Date.now() - startTime
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      
      await this.logStep(context.agentRunId, "failed", { error: errorMessage });
      logger.error("EventOpsAgent failed", { error: errorMessage });

      return {
        success: false,
        output: { error: errorMessage, kickoffReady: false },
        riskLevel: "R3",
        latencyMs: Date.now() - startTime
      };
    }
  }

  // Verificar se kickoff está pronto
  private async checkKickoffReady(context: AgentExecutionContext): Promise<{
    ready: boolean;
    missing: string[];
    percentComplete: number;
  }> {
    const required = [
      "Confirmar equipe",
      "Confirmar insumos", 
      "Confirmar cronograma",
      "Confirmar responsável operacional"
    ];

    const missing: string[] = [];
    let checkCount = 0;

    // Simular verificações (na realidade buscaria do DB)
    for (const item of required) {
      const confirmed = await this.checkItemStatus(item, context);
      if (!confirmed) {
        missing.push(item);
      } else {
        checkCount++;
      }
    }

    return {
      ready: missing.length === 0,
      missing,
      percentComplete: Math.round((checkCount / required.length) * 100)
    };
  }

  // Gerar checklist completo
  private generateChecklist(
    context: AgentExecutionContext,
    kickoffStatus: ReturnType<typeof this.checkKickoffReady>
  ): Array<{
    item: string;
    status: "pending" | "in_progress" | "completed";
    owner: string;
    priority: "high" | "medium" | "low";
    deadline: string;
  }> {
    const eventDate = String(context.input.eventDate || "");
    const daysUntil = this.daysUntil(eventDate);

    return [
      {
        item: "Confirmar equipe de trabalho",
        status: kickoffStatus.percentComplete >= 25 ? "completed" : "pending",
        owner: "Chef de Produção",
        priority: "high",
        deadline: daysUntil > 7 ? "3 dias" : "24h"
      },
      {
        item: "Confirmar insumos e materiais",
        status: kickoffStatus.percentComplete >= 50 ? "completed" : "pending",
        owner: "Gestor de Estoque",
        priority: "high",
        deadline: daysUntil > 7 ? "48h" : "12h"
      },
      {
        item: "Confirmar cronograma de setup",
        status: kickoffStatus.percentComplete >= 75 ? "completed" : "pending",
        owner: "Coordenador de Logística",
        priority: "medium",
        deadline: daysUntil > 5 ? "48h" : "6h"
      },
      {
        item: "Confirmar responsável operacional",
        status: kickoffStatus.percentComplete === 100 ? "completed" : "pending",
        owner: "Gerente de Operações",
        priority: "high",
        deadline: daysUntil > 3 ? "24h" : "2h"
      },
      {
        item: "Briefing completo com equipe",
        status: "pending",
        owner: "Chef de Produção",
        priority: "medium",
        deadline: daysUntil > 2 ? "12h" : "1h"
      },
      {
        item: "Check-in final no local",
        status: "pending",
        owner: "Responsável no local",
        priority: "high",
        deadline: "0h"
      }
    ];
  }

  // Verificar equipe
  private async checkStaff(context: AgentExecutionContext): Promise<{
    confirmed: number;
    required: number;
    status: "sufficient" | "partial" | "critical";
    gaps: string[];
  }> {
    const numGuests = parseInt(String(context.input.numGuests || 0), 10);
    const required = Math.ceil(numGuests / 20) + 2; // 1 staff por 20 convidados + 2

    // Simulação - na realidade buscaria availability do DB
    const confirmed = required - Math.floor(Math.random() * 3);

    const status = confirmed >= required ? "sufficient" :
                   confirmed >= required * 0.7 ? "partial" : "critical";

    const gaps: string[] = [];
    if (confirmed < required) {
      gaps.push(`Faltam ${required - confirmed} pessoas na equipe`);
    }
    if (confirmed < required * 0.5) {
      gaps.push("Equipe crítica - contratação emergencial necessária");
    }

    return { confirmed, required, status, gaps };
  }

  // Verificar cronograma
  private checkSchedule(context: AgentExecutionContext): {
    defined: boolean;
    setupHours: number;
    bufferMinutes: number;
    risks: string[];
  } {
    const eventType = String(context.input.eventType || "");
    const size = parseInt(String(context.input.numGuests || 0), 10);

    const baseSetup = {
      "casamento": 4,
      "corporativo": 2,
      "aniversario": 3,
      "congresso": 6
    }[eventType.toLowerCase()] || 3;

    const setupHours = baseSetup + (size > 100 ? Math.ceil(size / 100) : 0);
    
    return {
      defined: true,
      setupHours,
      bufferMinutes: setupHours > 4 ? 60 : 30,
      risks: setupHours < 2 ? ["Setup curto - risco de atraso"] : []
    };
  }

  // Atribuir responsáveis
  private async assignResponsibles(context: AgentExecutionContext): Promise<{
    assigned: boolean;
    responsibles: Array<{ role: string; name: string; phone: string }>;
  }> {
    // Simulação
    return {
      assigned: true,
      responsibles: [
        { role: "Gerente de Operações", name: "Chef Principal", phone: "" },
        { role: "Responsável no Local", name: "TBD", phone: "" }
      ]
    };
  }

  // Verificar insumos
  private async checkSupplies(context: AgentExecutionContext): Promise<{
    complete: boolean;
    items: Array<{ name: string; ready: boolean; location: string }>;
  }> {
    return {
      complete: false,
      items: [
        { name: "Materiais de montagem", ready: false, location: "Centro de distribuição" },
        { name: "Insumos de preparação", ready: false, location: "Cozinha central" },
        { name: "Equipamentos de service", ready: false, location: "Galpão" }
      ]
    };
  }

  // Ações obrigatórias
  private getRequiredActions(checklist: ReturnType<typeof this.generateChecklist>): string[] {
    return checklist
      .filter(item => item.status === "pending" && item.priority === "high")
      .map(item => `${item.item} (${item.deadline})`);
  }

  // Identificar riscos
  private identifyRisks(
    staff: ReturnType<typeof this.checkStaff>,
    supplies: ReturnType<typeof this.checkSupplies>,
    schedule: ReturnType<typeof this.checkSchedule>
  ): Array<{ level: "high" | "medium" | "low"; description: string }> {
    const risks: Array<{ level: "high" | "medium" | "low"; description: string }> = [];

    if (staff.status === "critical") {
      risks.push({ level: "high", description: "Equipe insuficiente" });
    }
    if (!supplies.complete) {
      risks.push({ level: "medium", description: "Insumos não confirmados" });
    }
    if (schedule.setupHours < 3) {
      risks.push({ level: "medium", description: "Setup em tempo curto" });
    }

    return risks;
  }

  // Gerar timeline
  private generateTimeline(eventDateStr: string): Array<{
    time: string;
    activity: string;
    responsible: string;
  }> {
    if (!eventDateStr) return [];

    const eventDate = new Date(eventDateStr);
    
    return [
      { time: "D-3", activity: "Briefing completo com equipe", responsible: "Chef Produção" },
      { time: "D-2", activity: "Insumos despachados para local", responsible: "Estoque" },
      { time: "D-1", activity: "Setup de estruturas (se necessário)", responsible: "Logística" },
      { time: "H-4", activity: "Chegada da equipe e insumos", responsible: "Coordenação" },
      { time: "H-2", activity: "Preparações em andamento", responsible: "Cozinha" },
      { time: "H-1", activity: "Finalização de montagem", responsible: "Equipe geral" },
      { time: "H-0", activity: "Evento início", responsible: "Todos" }
    ];
  }

  // Helper: verificar item
  private async checkItemStatus(item: string, context: AgentExecutionContext): Promise<boolean> {
    // Na realidade, buscaria o status real do DB
    return Math.random() > 0.3; // 70% chance de estar pronto (simulação)
  }

  // Helper: dias até evento
  private daysUntil(dateStr: string): number {
    if (!dateStr) return 30;
    const eventDate = new Date(dateStr);
    return Math.ceil((eventDate.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
  }
}

// Singleton
export const eventOpsAgent = new EventOpsAgent();

// Auto-registration
import { agentRegistry } from "./base-agent";
agentRegistry.register(eventOpsAgent);
