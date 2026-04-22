import { BaseAgent, AgentExecutionContext, AgentExecutionResult } from "./base-agent";
import { prisma } from "../db";
import { logger } from "../utils/logger";
import { analyzeWithClaude, isClaudeAvailable } from "../services/claude-client";

export class FinanceAgent extends BaseAgent {
  readonly name = "finance_agent";
  readonly description = "Análise financeira de eventos com DRE e projeções";
  readonly defaultRiskLevel = "R3" as const;

  async execute(context: AgentExecutionContext): Promise<AgentExecutionResult> {
    const startTime = Date.now();
    
    logger.info("FinanceAgent executing", { 
      runId: context.agentRunId,
      companyId: context.companyId 
    });

    await this.logStep(context.agentRunId, "running", { input: context.input });

    try {
      // Buscar dados do evento
      const eventData = await this.getEventData(context);
      
      // Calcular projeção financeira
      const financialProjection = this.calculateProjection(context.input, eventData);
      
      // Validar margem
      const marginValidation = this.validateMargin(financialProjection);
      
      // Verificar provisões
      const provisionStatus = await this.checkProvisions(context, financialProjection);

      const baseRecs = this.generateRecommendations(marginValidation, financialProjection);
      const aiInsight = await this.getAiInsight(financialProjection, marginValidation, context.input);

      const result = {
        revenueForecast: financialProjection.revenue,
        estimatedMargin: financialProjection.margin,
        marginPercentage: financialProjection.marginPercentage,
        breakEvenPoint: financialProjection.breakEven,
        costBreakdown: financialProjection.costs,
        financialProvisionStatus: provisionStatus.status,
        actionRequired: provisionStatus.actionRequired,
        alerts: marginValidation.alerts,
        recommendations: baseRecs,
        aiInsight,
        riskAssessment: {
          level: marginValidation.riskLevel,
          requiresApproval: marginValidation.requiresApproval
        },
        nextSteps: [
          "Criar conta a receber no ERP",
          "Provisionar materiais via requisição de compra",
          "Reservar margem de contingência",
          "Agendar follow-up financeiro"
        ],
        compliance: {
          taxObligations: "pending",
          invoiceRequired: true,
          contractValueMatch: this.validateContractValue(context.input, eventData)
        }
      };

      await this.logStep(context.agentRunId, "completed", { output: result });

      logger.info("FinanceAgent completed", { 
        runId: context.agentRunId,
        margin: result.estimatedMargin,
        risk: result.riskAssessment.level
      });

      return {
        success: true,
        output: result,
        riskLevel: result.riskAssessment.level,
        latencyMs: Date.now() - startTime
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      
      await this.logStep(context.agentRunId, "failed", { error: errorMessage });
      logger.error("FinanceAgent failed", { error: errorMessage });

      return {
        success: false,
        output: { error: errorMessage },
        riskLevel: "R4",
        latencyMs: Date.now() - startTime
      };
    }
  }

  // Buscar dados do evento no banco
  private async getEventData(context: AgentExecutionContext): Promise<{
    id?: string;
    revenueTotal?: number;
    cmvTotal?: number;
    netProfit?: number;
    marginPct?: number;
  }> {
    const eventId = String(context.input.eventId || "");
    if (!eventId) return {};

    try {
      const event = await prisma.event.findFirst({
        where: {
          eventId,
          tenantId: context.companyId
        }
      });

      return event ? {
        id: event.id,
        revenueTotal: event.revenueTotal || undefined,
        cmvTotal: event.cmvTotal || undefined,
        netProfit: event.netProfit || undefined,
        marginPct: event.marginPct || undefined
      } : {};
    } catch (error) {
      logger.warn("Failed to fetch event data", { eventId, error });
      return {};
    }
  }

  // Calcular projeção financeira
  private calculateProjection(
    input: Record<string, unknown>,
    eventData: Record<string, unknown>
  ): {
    revenue: number;
    costs: {
      materials: number;
      labor: number;
      overhead: number;
      fixed: number;
      total: number;
    };
    margin: number;
    marginPercentage: number;
    breakEven: number;
  } {
    const revenue = parseFloat(String(input.revenueForecast || input.valor || eventData.revenueTotal || 0));
    
    const costs = {
      materials: parseFloat(String(input.materialsCost || input.custoMateriais || 0)),
      labor: parseFloat(String(input.laborCost || input.custoMaoDeObra || 0)),
      overhead: parseFloat(String(input.overheadCost || input.custoOverhead || revenue * 0.15)),
      fixed: parseFloat(String(input.fixedCost || input.custoFixo || revenue * 0.08)),
      get total() { return this.materials + this.labor + this.overhead + this.fixed; }
    };

    const margin = revenue - costs.total;
    const marginPercentage = revenue > 0 ? (margin / revenue) * 100 : 0;
    
    // Break-even (considerando margem de contribuição)
    const contributionMargin = revenue > 0 ? (revenue - costs.materials - costs.labor) / revenue : 0;
    const breakEven = contributionMargin > 0 ? costs.fixed / contributionMargin : 0;

    return {
      revenue,
      costs,
      margin,
      marginPercentage,
      breakEven
    };
  }

  // Validar margem
  private validateMargin(projection: {
    margin: number;
    marginPercentage: number;
  }): {
    valid: boolean;
    alerts: string[];
    riskLevel: "R0" | "R1" | "R2" | "R3" | "R4";
    requiresApproval: boolean;
  } {
    const alerts: string[] = [];
    let riskLevel: "R0" | "R1" | "R2" | "R3" | "R4" = "R1";
    let requiresApproval = false;

    if (projection.marginPercentage < 0) {
      alerts.push("⚠️ MARGEM NEGATIVA - Prejuízo estimado");
      riskLevel = "R4";
      requiresApproval = true;
    } else if (projection.marginPercentage < 10) {
      alerts.push("🔴 Margem crítica (< 10%) - Revisar imediatamente");
      riskLevel = "R3";
      requiresApproval = true;
    } else if (projection.marginPercentage < 20) {
      alerts.push("🟡 Margem baixa (10-20%) - Atenção necessária");
      riskLevel = "R2";
    }

    if (projection.margin > 50000) {
      alerts.push("💰 Alto valor de margem - registrar no sistema de incentivos");
    }

    return {
      valid: alerts.length === 0 || projection.margin > 0,
      alerts,
      riskLevel,
      requiresApproval
    };
  }

  // Verificar provisões
  private async checkProvisions(
    context: AgentExecutionContext,
    projection: { revenue: number; costs: { total: number }; margin: number }
  ): Promise<{
    status: string;
    actionRequired: string[];
  }> {
    const actions: string[] = [];

    // Verificar se precisa criar conta a receber
    if (projection.revenue > 0) {
      actions.push("Criar conta a receber no prazo de 1 dia útil");
    }

    // Verificar materiais
    if (projection.costs.total > 0) {
      actions.push("Provisionar materiais em até 48h antes do evento");
    }

    // Verificar margem para contingência
    if (projection.margin > 10000) {
      actions.push("Reservar 10% da margem para contingências");
    }

    // Note: accounts_payable integration is pending — skipped for now

    return {
      status: actions.length > 0 ? "created" : "not_required",
      actionRequired: actions
    };
  }

  // Gerar recomendações
  private generateRecommendations(
    marginValidation: { alerts: string[]; riskLevel: string },
    projection: { marginPercentage: number; breakEven: number }
  ): string[] {
    const recommendations: string[] = [];

    if (projection.marginPercentage < 15) {
      recommendations.push("Considerar revisão de preço ou redução de escopo");
      recommendations.push("Negociar com fornecedores para obter descontos");
    }

    if (projection.breakEven > 0.7) {
      recommendations.push("Break-even alto - verificar se evento é viável");
    }

    if (marginValidation.riskLevel === "R3" || marginValidation.riskLevel === "R4") {
      recommendations.push("Requer aprovação do diretor comercial");
      recommendations.push("Agendar reunião de crise se margem < 10%");
    }

    return recommendations;
  }

  private async getAiInsight(
    projection: { revenue: number; margin: number; marginPercentage: number; breakEven: number },
    validation: { riskLevel: string; alerts: string[] },
    input: Record<string, unknown>
  ): Promise<string | null> {
    if (!isClaudeAvailable()) return null;
    try {
      const result = await analyzeWithClaude({
        systemPrompt: `Você é um CFO especializado em empresas de eventos de alto padrão no Brasil.
Analise dados financeiros e forneça insights estratégicos concisos (máximo 2 parágrafos).
Foco em: viabilidade do evento, alavancas de melhoria de margem, riscos financeiros.
Responda em português, tom executivo e direto.`,
        userContent: JSON.stringify({ projection, riskLevel: validation.riskLevel, alerts: validation.alerts, eventType: input.eventType }),
        maxTokens: 400
      });
      return result.text;
    } catch (err) {
      logger.warn("FinanceAgent: Claude insight failed", { error: err });
      return null;
    }
  }

  // Validar match de valor do contrato
  private validateContractValue(
    input: Record<string, unknown>,
    eventData: Record<string, unknown>
  ): boolean {
    const inputValue = parseFloat(String(input.contractValue || input.valor || 0));
    const eventValue = parseFloat(String(eventData.revenueTotal || 0));
    
    if (!inputValue || !eventValue) return true;
    
    // Permitir 5% de diferença
    const diff = Math.abs(inputValue - eventValue) / eventValue;
    return diff <= 0.05;
  }
}

// Singleton
export const financeAgent = new FinanceAgent();

// Auto-registration
import { agentRegistry } from "./base-agent";
agentRegistry.register(financeAgent);
