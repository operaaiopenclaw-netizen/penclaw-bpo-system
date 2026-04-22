import { BaseAgent, AgentExecutionContext, AgentExecutionResult } from "./base-agent";
import { prisma } from "../db";
import { logger } from "../utils/logger";
import { analyzeWithClaude, isClaudeAvailable } from "../services/claude-client";

export class CrmAgent extends BaseAgent {
  readonly name = "crm_agent";
  readonly description = "Qualifica leads, pontua BANT, sugere proposta e ação comercial";
  readonly defaultRiskLevel = "R1" as const;

  async execute(context: AgentExecutionContext): Promise<AgentExecutionResult> {
    const startTime = Date.now();
    logger.info("CrmAgent executing", { runId: context.agentRunId });
    await this.logStep(context.agentRunId, "running", { input: context.input });

    try {
      const leadData = this.extractLeadData(context.input);
      const bantScore = this.scoreBant(leadData);
      const qualification = this.qualify(bantScore, leadData);
      const proposalHints = this.generateProposalHints(leadData);
      const nextActions = this.determineNextActions(qualification, leadData);

      const existingLead = await this.findOrSuggestLead(context.companyId, leadData);

      const baseRecommendation = this.buildRecommendation(qualification, leadData);
      const recommendation = await this.enrichWithClaude(leadData, bantScore, qualification, baseRecommendation);

      const result = {
        leadData,
        bantScore,
        qualification,
        proposalHints,
        nextActions,
        existingLeadId: existingLead?.id,
        alerts: this.generateAlerts(bantScore, leadData),
        recommendation
      };

      await this.logStep(context.agentRunId, "completed", { output: result });
      logger.info("CrmAgent completed", { runId: context.agentRunId, score: bantScore.total });

      return {
        success: true,
        output: result,
        riskLevel: qualification.risk,
        latencyMs: Date.now() - startTime
      };
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Unknown error";
      await this.logStep(context.agentRunId, "failed", { error: msg });
      return { success: false, output: { error: msg }, riskLevel: "R2", latencyMs: Date.now() - startTime };
    }
  }

  private extractLeadData(input: Record<string, unknown>) {
    return {
      contactName: String(input.contactName || input.clientName || ""),
      companyName: String(input.companyName || ""),
      email: String(input.email || ""),
      phone: String(input.phone || ""),
      source: String(input.source || "unknown"),
      budget: parseFloat(String(input.budget || input.valor || 0)),
      authority: String(input.authority || ""),
      need: String(input.need || input.eventType || ""),
      timeline: String(input.timeline || input.eventDate || ""),
      numGuests: parseInt(String(input.numGuests || input.guests || 0))
    };
  }

  private scoreBant(data: ReturnType<typeof this.extractLeadData>) {
    const budget = data.budget > 50000 ? 25 : data.budget > 20000 ? 15 : data.budget > 5000 ? 10 : 0;
    const authority = data.authority ? 25 : 10;
    const need = data.need ? 25 : 5;
    const timeline = data.timeline ? 25 : 5;
    return { budget, authority, need, timeline, total: budget + authority + need + timeline };
  }

  private qualify(score: { total: number }, data: ReturnType<typeof this.extractLeadData>) {
    if (score.total >= 80) return { level: "HOT", risk: "R1" as const, action: "Proposta imediata", probability: 0.75 };
    if (score.total >= 60) return { level: "WARM", risk: "R1" as const, action: "Follow-up em 24h", probability: 0.50 };
    if (score.total >= 40) return { level: "COOL", risk: "R2" as const, action: "Qualificar necessidade", probability: 0.25 };
    return { level: "COLD", risk: "R2" as const, action: "Nutrir com conteúdo", probability: 0.10 };
  }

  private generateProposalHints(data: ReturnType<typeof this.extractLeadData>) {
    const hints: string[] = [];
    if (data.numGuests > 300) hints.push("Evento grande — considerar desconto de volume (5-10%)");
    if (data.budget > 0) {
      const perGuest = data.numGuests > 0 ? data.budget / data.numGuests : 0;
      if (perGuest > 0) hints.push(`Budget per capita: R$ ${perGuest.toFixed(0)} — posicionar proposta em torno disso`);
    }
    const eventType = data.need.toLowerCase();
    if (eventType.includes("casamento")) hints.push("Casamento: incluir menu degustação, barra de drinks premium");
    if (eventType.includes("corporat")) hints.push("Corporativo: proposta concisa, foco em eficiência e pontualidade");
    if (eventType.includes("formatura")) hints.push("Formatura: buffet, DJ, decoração temática, segurança");
    return hints;
  }

  private determineNextActions(qual: { level: string; action: string }, data: ReturnType<typeof this.extractLeadData>) {
    const actions = [qual.action];
    if (!data.email) actions.push("Coletar e-mail para envio de proposta");
    if (data.budget === 0) actions.push("Qualificar orçamento disponível");
    if (!data.timeline) actions.push("Confirmar data do evento");
    if (data.numGuests === 0) actions.push("Confirmar número de convidados");
    return actions;
  }

  private async findOrSuggestLead(tenantId: string, data: ReturnType<typeof this.extractLeadData>) {
    if (!data.email && !data.phone) return null;
    try {
      return await prisma.lead.findFirst({
        where: {
          tenantId,
          OR: [
            ...(data.email ? [{ email: data.email }] : []),
            ...(data.phone ? [{ phone: data.phone }] : [])
          ]
        }
      });
    } catch { return null; }
  }

  private generateAlerts(score: { total: number }, data: ReturnType<typeof this.extractLeadData>) {
    const alerts: string[] = [];
    if (score.total < 40) alerts.push("⚠️ Lead frio — não investir muito tempo sem qualificação");
    if (data.budget > 100000) alerts.push("💰 Alto valor — envolver diretor comercial");
    if (!data.timeline) alerts.push("📅 Sem data definida — risco de pipeline irreal");
    return alerts;
  }

  private buildRecommendation(qual: { level: string; probability: number }, data: ReturnType<typeof this.extractLeadData>) {
    return `Lead ${qual.level}: probabilidade de conversão ${Math.round(qual.probability * 100)}%. ` +
      `Evento tipo '${data.need || "não informado"}' para ${data.numGuests || "?"} pessoas. ` +
      `Budget estimado: R$ ${data.budget > 0 ? data.budget.toLocaleString("pt-BR") : "não informado"}.`;
  }

  private async enrichWithClaude(
    leadData: ReturnType<typeof this.extractLeadData>,
    bantScore: { budget: number; authority: number; need: number; timeline: number; total: number },
    qualification: { level: string; action: string; probability: number },
    fallback: string
  ): Promise<string> {
    if (!isClaudeAvailable()) return fallback;
    try {
      const result = await analyzeWithClaude({
        systemPrompt: `Você é um especialista em vendas B2B de eventos de alto padrão no Brasil.
Analise leads e forneça recomendações estratégicas concisas (máximo 3 parágrafos).
Foco em: estratégia de abordagem, personalização da proposta, riscos e oportunidades.
Responda em português, tom profissional e direto.`,
        userContent: JSON.stringify({ leadData, bantScore, qualification }),
        maxTokens: 512
      });
      return result.text;
    } catch (err) {
      logger.warn("CrmAgent: Claude enrichment failed, using fallback", { error: err });
      return fallback;
    }
  }
}

export const crmAgent = new CrmAgent();

import { agentRegistry } from "./base-agent";
agentRegistry.register(crmAgent);
