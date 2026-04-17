import { BaseAgent, AgentExecutionContext, AgentExecutionResult } from "./base-agent";
import { prisma } from "../db";
import { logger } from "../utils/logger";

export class OsAgent extends BaseAgent {
  readonly name = "os_agent";
  readonly description = "Gera Ordens de Serviço (OS) a partir de contratos e dados do evento";
  readonly defaultRiskLevel = "R2" as const;

  async execute(context: AgentExecutionContext): Promise<AgentExecutionResult> {
    const startTime = Date.now();
    logger.info("OsAgent executing", { runId: context.agentRunId });
    await this.logStep(context.agentRunId, "running", { input: context.input });

    try {
      const eventId = String(context.input.eventId || "");
      const contractId = String(context.input.contractId || "");

      const osBreakdown = this.generateOsBreakdown(context.input);
      const existingOs = await this.checkExistingOs(eventId, context.companyId);
      const createdOs = contractId ? await this.autoCreateOs(contractId, context.companyId) : [];

      const result = {
        eventId,
        contractId,
        osBreakdown,
        existingOs: existingOs.map(os => ({ id: os.id, soNumber: os.soNumber, type: os.soType, status: os.status, total: os.total })),
        autoCreated: createdOs,
        recommendations: this.buildRecommendations(osBreakdown, existingOs),
        checklist: this.buildProductionChecklist(context.input),
        alerts: this.buildAlerts(osBreakdown, existingOs)
      };

      await this.logStep(context.agentRunId, "completed", { output: result });
      return { success: true, output: result, riskLevel: "R2", latencyMs: Date.now() - startTime };
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Unknown error";
      await this.logStep(context.agentRunId, "failed", { error: msg });
      return { success: false, output: { error: msg }, riskLevel: "R3", latencyMs: Date.now() - startTime };
    }
  }

  private generateOsBreakdown(input: Record<string, unknown>) {
    const guests = parseInt(String(input.numGuests || input.guests || 0));
    const eventType = String(input.eventType || "corporativo").toLowerCase();
    const revenue = parseFloat(String(input.contractValue || input.totalValue || input.valor || 0));

    const ratios: Record<string, Record<string, number>> = {
      casamento: { catering: 0.50, bar: 0.25, structure: 0.15, staff: 0.10 },
      corporativo: { catering: 0.45, bar: 0.15, structure: 0.25, staff: 0.15 },
      formatura: { catering: 0.40, bar: 0.30, structure: 0.20, staff: 0.10 },
      aniversario: { catering: 0.50, bar: 0.20, structure: 0.20, staff: 0.10 }
    };

    const ratio = ratios[eventType] || ratios["corporativo"];

    return {
      totalRevenue: revenue,
      guests,
      perGuestRevenue: guests > 0 ? revenue / guests : 0,
      serviceOrders: {
        CATERING: { estimatedValue: revenue * ratio.catering, rationale: `${(ratio.catering * 100).toFixed(0)}% do contrato` },
        BAR: { estimatedValue: revenue * ratio.bar, rationale: `${(ratio.bar * 100).toFixed(0)}% do contrato` },
        STRUCTURE: { estimatedValue: revenue * ratio.structure, rationale: `${(ratio.structure * 100).toFixed(0)}% do contrato` },
        STAFF: { estimatedValue: revenue * ratio.staff, rationale: `${(ratio.staff * 100).toFixed(0)}% do contrato` }
      }
    };
  }

  private async checkExistingOs(eventId: string, tenantId: string) {
    if (!eventId) return [];
    try {
      return await prisma.serviceOrder.findMany({
        where: { eventId, tenantId }
      });
    } catch { return []; }
  }

  private async autoCreateOs(contractId: string, tenantId: string) {
    try {
      const contract = await prisma.contract.findUnique({
        where: { id: contractId },
        include: { proposal: { include: { items: true } } }
      });
      if (!contract?.eventId) return [];

      // Verificar se já existem OS para o evento
      const existing = await prisma.serviceOrder.count({ where: { eventId: contract.eventId } });
      if (existing > 0) return [{ message: "OS already exist for this event", count: existing }];

      // Agrupar por tipo
      const groups: Record<string, typeof contract.proposal.items> = {
        CATERING: contract.proposal.items.filter(i => ["menu", "catering"].includes(i.itemType.toLowerCase())),
        BAR: contract.proposal.items.filter(i => ["bar", "drink", "bebida"].includes(i.itemType.toLowerCase())),
        STRUCTURE: contract.proposal.items.filter(i => ["structure", "equipment", "estrutura"].includes(i.itemType.toLowerCase())),
        STAFF: contract.proposal.items.filter(i => ["staff", "service"].includes(i.itemType.toLowerCase()))
      };

      const created: Array<{ soNumber: string; type: string; total: number }> = [];
      let idx = await prisma.serviceOrder.count({ where: { tenantId } });

      for (const [type, items] of Object.entries(groups)) {
        if (items.length === 0) continue;
        idx++;
        const soNumber = `OS-${new Date().getFullYear()}-${String(idx).padStart(4, "0")}`;
        const subtotal = items.reduce((s, i) => s + i.totalPrice, 0);

        await prisma.serviceOrder.create({
          data: {
            tenantId,
            eventId: contract.eventId!,
            proposalId: contract.proposalId,
            soType: type as "CATERING" | "BAR" | "STRUCTURE" | "STAFF",
            soNumber,
            subtotal,
            total: subtotal,
            items: {
              create: items.map(i => ({
                itemCategory: i.itemType.toUpperCase() as "MENU" | "DRINK" | "EQUIPMENT" | "SERVICE",
                name: i.name,
                description: i.description ?? undefined,
                quantity: i.quantity,
                unit: i.unit ?? undefined,
                unitPrice: i.unitPrice,
                totalPrice: i.totalPrice
              }))
            }
          }
        });
        created.push({ soNumber, type, total: subtotal });
      }

      return created;
    } catch (err) {
      logger.warn("OsAgent: autoCreateOs failed", { error: err });
      return [];
    }
  }

  private buildRecommendations(breakdown: ReturnType<typeof this.generateOsBreakdown>, existingOs: Awaited<ReturnType<typeof this.checkExistingOs>>) {
    const recs: string[] = [];
    if (existingOs.length === 0) recs.push("Nenhuma OS criada — gerar OS a partir do contrato assinado");
    const pendingApproval = existingOs.filter(os => os.status === "DRAFT").length;
    if (pendingApproval > 0) recs.push(`${pendingApproval} OS em rascunho — submeter para aprovação`);
    if (breakdown.guests > 200) recs.push("Evento grande — considerar dividir OS de catering por turno");
    return recs;
  }

  private buildProductionChecklist(input: Record<string, unknown>) {
    const guests = parseInt(String(input.numGuests || 0));
    const eventType = String(input.eventType || "evento");
    return [
      `Confirmar número de pax: ${guests}`,
      `Definir cardápio para ${eventType}`,
      "Calcular fichas técnicas por item do menu",
      "Verificar disponibilidade de estoque",
      "Emitir requisição de compra para itens em falta",
      "Confirmar cronograma de produção com chef",
      "Agendar ensaio de montagem",
      "Definir equipe de serviço"
    ];
  }

  private buildAlerts(breakdown: ReturnType<typeof this.generateOsBreakdown>, existingOs: Awaited<ReturnType<typeof this.checkExistingOs>>) {
    const alerts: string[] = [];
    if (breakdown.totalRevenue === 0) alerts.push("⚠️ Valor do contrato não informado — OS criadas sem valor");
    if (existingOs.filter(os => os.status === "CANCELLED").length > 0) alerts.push("🚫 Existem OS canceladas — verificar motivo");
    const inProd = existingOs.filter(os => os.status === "IN_PRODUCTION").length;
    if (inProd > 0) alerts.push(`🍳 ${inProd} OS em produção — monitorar progresso`);
    return alerts;
  }
}

export const osAgent = new OsAgent();

import { agentRegistry } from "./base-agent";
agentRegistry.register(osAgent);
