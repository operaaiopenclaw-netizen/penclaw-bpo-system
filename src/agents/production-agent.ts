import { BaseAgent, AgentExecutionContext, AgentExecutionResult } from "./base-agent";
import { prisma } from "../db";
import { logger } from "../utils/logger";

export class ProductionAgent extends BaseAgent {
  readonly name = "production_agent";
  readonly description = "Planeja Ordens de Produção (OP), fichas técnicas e cronograma de cozinha";
  readonly defaultRiskLevel = "R2" as const;

  async execute(context: AgentExecutionContext): Promise<AgentExecutionResult> {
    const startTime = Date.now();
    logger.info("ProductionAgent executing", { runId: context.agentRunId });
    await this.logStep(context.agentRunId, "running", { input: context.input });

    try {
      const eventId = String(context.input.eventId || "");
      const tenantId = context.companyId;

      const approvedOs = await this.getApprovedOs(eventId, tenantId);
      const productionPlan = this.buildProductionPlan(context.input, approvedOs);
      const timeline = this.buildTimeline(context.input);
      const kitchenCapacity = this.assessKitchenCapacity(context.input, approvedOs);
      const ingredients = this.estimateIngredients(context.input, approvedOs);
      const existingOps = await this.getExistingOps(eventId, tenantId);

      const result = {
        eventId,
        approvedOsCount: approvedOs.length,
        existingOpsCount: existingOps.length,
        productionPlan,
        timeline,
        kitchenCapacity,
        ingredients,
        recommendations: this.buildRecommendations(approvedOs, existingOps, kitchenCapacity),
        alerts: this.buildAlerts(approvedOs, existingOps, kitchenCapacity)
      };

      await this.logStep(context.agentRunId, "completed", { output: result });
      return { success: true, output: result, riskLevel: "R2", latencyMs: Date.now() - startTime };
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Unknown error";
      await this.logStep(context.agentRunId, "failed", { error: msg });
      return { success: false, output: { error: msg }, riskLevel: "R3", latencyMs: Date.now() - startTime };
    }
  }

  private async getApprovedOs(eventId: string, tenantId: string) {
    if (!eventId) return [];
    try {
      return await prisma.serviceOrder.findMany({
        where: { eventId, tenantId, status: { in: ["APPROVED", "IN_PRODUCTION"] } },
        include: { items: true }
      });
    } catch { return []; }
  }

  private async getExistingOps(eventId: string, tenantId: string) {
    if (!eventId) return [];
    try {
      return await prisma.productionOrder.findMany({ where: { eventId, tenantId } });
    } catch { return []; }
  }

  private buildProductionPlan(input: Record<string, unknown>, approvedOs: Awaited<ReturnType<typeof this.getApprovedOs>>) {
    const guests = parseInt(String(input.numGuests || input.guests || 0));
    const eventDate = String(input.eventDate || "");

    const cateringOs = approvedOs.filter(os => os.soType === "CATERING");
    const barOs = approvedOs.filter(os => os.soType === "BAR");

    const plan = {
      totalItems: approvedOs.reduce((s, os) => s + os.items.length, 0),
      productionOrders: [] as Array<{ type: string; items: number; estimatedHours: number; crew: number }>
    };

    if (cateringOs.length > 0) {
      const itemCount = cateringOs.reduce((s, os) => s + os.items.length, 0);
      plan.productionOrders.push({
        type: "COZINHA",
        items: itemCount,
        estimatedHours: Math.max(4, Math.ceil(guests / 50)),
        crew: Math.max(2, Math.ceil(guests / 100))
      });
    }

    if (barOs.length > 0) {
      plan.productionOrders.push({
        type: "BAR",
        items: barOs.reduce((s, os) => s + os.items.length, 0),
        estimatedHours: 2,
        crew: Math.max(1, Math.ceil(guests / 150))
      });
    }

    return { guests, eventDate, ...plan };
  }

  private buildTimeline(input: Record<string, unknown>) {
    const eventDateStr = String(input.eventDate || "");
    if (!eventDateStr) return { note: "Data do evento não informada — cronograma não calculado" };

    const eventDate = new Date(eventDateStr);
    const d = (daysBack: number) => {
      const d = new Date(eventDate);
      d.setDate(d.getDate() - daysBack);
      return d.toISOString().split("T")[0];
    };

    return {
      eventDate: eventDate.toISOString().split("T")[0],
      purchaseDeadline: d(5),
      ingredientArrival: d(3),
      prepStart: d(2),
      finalPrep: d(1),
      setupDay: d(0),
      milestones: [
        { date: d(7), task: "Finalizar cardápio e fichas técnicas" },
        { date: d(5), task: "Emitir pedidos de compra" },
        { date: d(3), task: "Recebimento de materiais" },
        { date: d(2), task: "Início da produção (bases, molhos, cortes)" },
        { date: d(1), task: "Produção principal + mise en place" },
        { date: d(0), task: "Montagem e execução do evento" }
      ]
    };
  }

  private assessKitchenCapacity(input: Record<string, unknown>, approvedOs: Awaited<ReturnType<typeof this.getApprovedOs>>) {
    const guests = parseInt(String(input.numGuests || 0));
    const totalItems = approvedOs.reduce((s, os) => s + os.items.length, 0);

    let status: "OK" | "WARNING" | "CRITICAL" = "OK";
    const notes: string[] = [];

    if (guests > 500) { status = "WARNING"; notes.push("Evento acima de 500 pax — avaliar produção externa ou sublocalização"); }
    if (guests > 1000) { status = "CRITICAL"; notes.push("Evento acima de 1000 pax — produção compartilhada entre cozinhas necessária"); }
    if (totalItems > 20) notes.push(`${totalItems} itens no cardápio — considerar simplificar`);

    return { guests, totalItems, status, notes, estimatedKitchenHours: Math.max(6, Math.ceil(guests / 60)) };
  }

  private estimateIngredients(input: Record<string, unknown>, approvedOs: Awaited<ReturnType<typeof this.getApprovedOs>>) {
    const guests = parseInt(String(input.numGuests || 0));
    if (guests === 0) return { note: "Número de convidados não informado" };

    // Estimativas padrão por convidado
    return {
      proteins: { quantity: guests * 0.35, unit: "kg", note: "0.35kg proteína/pax" },
      vegetables: { quantity: guests * 0.25, unit: "kg", note: "0.25kg vegetais/pax" },
      starches: { quantity: guests * 0.20, unit: "kg", note: "0.20kg carboidratos/pax" },
      beveragesAlcohol: { quantity: guests * 0.75, unit: "L", note: "750ml álcool/pax" },
      beveragesSoft: { quantity: guests * 0.50, unit: "L", note: "500ml soft/pax" },
      disposables: { quantity: guests * 3, unit: "units", note: "3 peças descartáveis/pax" },
      estimatedCmv: guests * 45  // R$ 45/pax CMV estimado
    };
  }

  private buildRecommendations(
    approvedOs: Awaited<ReturnType<typeof this.getApprovedOs>>,
    existingOps: Awaited<ReturnType<typeof this.getExistingOps>>,
    capacity: ReturnType<typeof this.assessKitchenCapacity>
  ) {
    const recs: string[] = [];
    if (approvedOs.length === 0) recs.push("Nenhuma OS aprovada — aprovar OS antes de criar OPs");
    if (approvedOs.length > 0 && existingOps.length === 0) recs.push(`${approvedOs.length} OS aprovada(s) sem OP — criar ordens de produção`);
    if (capacity.status !== "OK") recs.push(...capacity.notes);
    if (existingOps.filter(op => op.status === "PENDING").length > 0) recs.push("OPs pendentes — agendar e atribuir chef responsável");
    return recs;
  }

  private buildAlerts(
    approvedOs: Awaited<ReturnType<typeof this.getApprovedOs>>,
    existingOps: Awaited<ReturnType<typeof this.getExistingOps>>,
    capacity: ReturnType<typeof this.assessKitchenCapacity>
  ) {
    const alerts: string[] = [];
    if (capacity.status === "CRITICAL") alerts.push("🔴 CAPACIDADE CRÍTICA — avaliar terceirização de produção");
    if (capacity.status === "WARNING") alerts.push("🟡 Capacidade no limite — confirmar recursos de cozinha");
    const cancelledOps = existingOps.filter(op => op.status === "CANCELLED").length;
    if (cancelledOps > 0) alerts.push(`🚫 ${cancelledOps} OP(s) cancelada(s) — verificar impacto no evento`);
    return alerts;
  }
}

export const productionAgent = new ProductionAgent();

import { agentRegistry } from "./base-agent";
agentRegistry.register(productionAgent);
