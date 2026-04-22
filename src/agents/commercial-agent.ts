import { BaseAgent, AgentExecutionContext, AgentExecutionResult } from "./base-agent";
import { prisma } from "../db";
import { logger } from "../utils/logger";

export class CommercialAgent extends BaseAgent {
  readonly name = "commercial_agent";
  readonly description = "Validação comercial de contratos e pipeline de vendas";
  readonly defaultRiskLevel = "R2" as const;

  async execute(context: AgentExecutionContext): Promise<AgentExecutionResult> {
    const startTime = Date.now();
    
    logger.info("CommercialAgent executing", { 
      runId: context.agentRunId,
      companyId: context.companyId 
    });

    await this.logStep(context.agentRunId, "running", { input: context.input });

    try {
      // Validações comerciais
      const validation = this.validateCommercial(context.input);
      
      if (!validation.valid) {
        await this.logStep(context.agentRunId, "failed", { 
          reason: validation.reason 
        });

        return {
          success: false,
          output: {
            commercialValidation: "rejected",
            reason: validation.reason,
            recommendations: validation.recommendations
          },
          riskLevel: "R3",
          latencyMs: Date.now() - startTime
        };
      }

      // Análise de pipeline
      const pipelineAnalysis = await this.analyzePipeline(context);

      // Verificar margem proposta
      const marginCheck = this.checkMargin(context.input);

      const result = {
        commercialValidation: validation.status,
        pipelineStage: this.determinePipelineStage(context.input),
        marginStatus: marginCheck.status,
        marginPercentage: marginCheck.percentage,
        clientHistory: await this.checkClientHistory(context),
        validationChecks: {
          priceApproved: marginCheck.ok,
          clientVerified: validation.clientOk,
          dateAvailable: validation.dateOk,
          staffAvailable: await this.checkStaffAvailability(context)
        },
        notes: "Negócio validado para onboarding",
        nextSteps: [
          "Gerar contrato formal",
          "Reservar data no calendário",
          "Notificar equipe de produção"
        ]
      };

      await this.logStep(context.agentRunId, "completed", { output: result });

      logger.info("CommercialAgent completed", { 
        runId: context.agentRunId,
        validation: result.commercialValidation
      });

      return {
        success: true,
        output: result,
        riskLevel: result.marginStatus === "critical" ? "R3" : this.defaultRiskLevel,
        latencyMs: Date.now() - startTime
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      
      await this.logStep(context.agentRunId, "failed", { error: errorMessage });
      logger.error("CommercialAgent failed", { error: errorMessage });

      return {
        success: false,
        output: { error: errorMessage },
        riskLevel: "R3",
        latencyMs: Date.now() - startTime
      };
    }
  }

  // Validações comerciais
  private validateCommercial(input: Record<string, unknown>): {
    valid: boolean;
    status: string;
    reason?: string;
    recommendations: string[];
    clientOk: boolean;
    dateOk: boolean;
  } {
    const recommendations: string[] = [];
    let clientOk = true;
    let dateOk = true;

    // Verificar margem mínima
    const valor = parseFloat(String(input.contractValue || input.valor || 0));
    const custo = parseFloat(String(input.estimatedCost || input.custo || 0));
    
    if (valor > 0 && custo > 0) {
      const margin = ((valor - custo) / valor) * 100;
      if (margin < 15) {
        recommendations.push("Margem abaixo de 15% - revisar com vendas");
        clientOk = false;
      }
    }

    // Verificar data
    const eventDate = String(input.eventDate || input.data || "");
    if (eventDate) {
      const daysUntil = this.daysUntilEvent(eventDate);
      if (daysUntil < 7) {
        recommendations.push("Evento em menos de 7 dias - verificar urgência");
        dateOk = false;
      }
    }

    const valid = recommendations.length === 0;

    return {
      valid,
      status: valid ? "approved" : "review_required",
      recommendations,
      clientOk,
      dateOk
    };
  }

  // Análise de pipeline
  private async analyzePipeline(context: AgentExecutionContext): Promise<{
    stage: string;
    conversionProbability: number;
    estimatedRevenue: number;
  }> {
    // Buscar eventos similares no histórico
    const similarEvents = await prisma.event.count({
      where: {
        tenantId: context.companyId,
        status: "completed"
      }
    });

    const conversionProbability = similarEvents > 10 ? 0.75 : 0.50;
    
    return {
      stage: "contract_signed",
      conversionProbability,
      estimatedRevenue: parseFloat(String(context.input.contractValue || 0))
    };
  }

  // Verificar margem
  private checkMargin(input: Record<string, unknown>): {
    ok: boolean;
    status: string;
    percentage: number | null;
  } {
    const valor = parseFloat(String(input.contractValue || input.valor || 0));
    const custo = parseFloat(String(input.estimatedCost || input.custo || 0));
    
    if (!valor || !custo) {
      return { ok: false, status: "unknown", percentage: null };
    }

    const margin = ((valor - custo) / valor) * 100;
    let status = "good";
    if (margin < 15) status = "critical";
    else if (margin < 25) status = "warning";

    return { ok: margin >= 15, status, percentage: Math.round(margin * 100) / 100 };
  }

  // Determinar estágio do pipeline
  private determinePipelineStage(input: Record<string, unknown>): string {
    const hasProposal = input.proposalSent || input.propostaEnviada;
    const hasContract = input.contractSigned || input.contratoAssinado;
    const hasPayment = input.paymentReceived || input.pagamentoRecebido;

    if (hasPayment) return "paid";
    if (hasContract) return "contract_signed";
    if (hasProposal) return "proposal_sent";
    return "qualified_lead";
  }

  // Verificar histórico do cliente
  private async checkClientHistory(context: AgentExecutionContext): Promise<{
    isReturningClient: boolean;
    previousEvents: number;
    averageRating: number | null;
  }> {
    const clientName = String(context.input.clientName || context.input.cliente || "");
    if (!clientName) {
      return { isReturningClient: false, previousEvents: 0, averageRating: null };
    }

    const previousEvents = await prisma.event.count({
      where: {
        tenantId: context.companyId,
        companyName: clientName
      }
    });

    return {
      isReturningClient: previousEvents > 0,
      previousEvents,
      averageRating: previousEvents > 0 ? 4.5 : null // Simulado
    };
  }

  // Verificar disponibilidade de staff
  private async checkStaffAvailability(context: AgentExecutionContext): Promise<boolean> {
    const eventDate = String(context.input.eventDate || "");
    const numGuests = parseInt(String(context.input.numGuests || context.input.convidados || 0), 10);
    
    if (!eventDate || !numGuests) return true;

    // Simplificação: assumir disponível
    return true;
  }

  // Calcular dias até evento
  private daysUntilEvent(eventDateStr: string): number {
    const eventDate = new Date(eventDateStr);
    const today = new Date();
    const diffTime = eventDate.getTime() - today.getTime();
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  }
}

// Singleton
export const commercialAgent = new CommercialAgent();

// Automático registration
import { agentRegistry } from "./base-agent";
agentRegistry.register(commercialAgent);
