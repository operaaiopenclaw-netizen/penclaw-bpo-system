import { BaseAgent, AgentExecutionContext, AgentExecutionResult } from "./base-agent";
import { logger } from "../utils/logger";

export class ContractAgent extends BaseAgent {
  readonly name = "contract_agent";
  readonly description = "Processa e extrai campos de contratos de eventos";
  readonly defaultRiskLevel = "R1" as const;

  async execute(context: AgentExecutionContext): Promise<AgentExecutionResult> {
    const startTime = Date.now();
    
    logger.info("ContractAgent executing", { 
      runId: context.agentRunId,
      companyId: context.companyId 
    });

    await this.logStep(context.agentRunId, "running", { input: context.input });

    try {
      // Extrair campos do contrato
      const extractedFields = {
        clientName: this.extractClientName(context.input),
        eventDate: this.extractEventDate(context.input),
        eventType: this.extractEventType(context.input),
        numGuests: this.extractNumGuests(context.input),
        contractValue: this.extractContractValue(context.input),
        venue: this.extractVenue(context.input),
        observacoes: this.extractObservacoes(context.input)
      };

      // Validar campos obrigatórios
      const obrigatorios = ["clientName", "eventDate"];
      const faltantes = obrigatorios.filter(campo => !extractedFields[campo as keyof typeof extractedFields]);

      if (faltantes.length > 0) {
        await this.logStep(context.agentRunId, "failed", { 
          error: `Campos obrigatórios faltantes: ${faltantes.join(", ")}`
        });

        return {
          success: false,
          output: {
            error: "Campos obrigatórios faltantes",
            missing: faltantes,
            extracted: extractedFields
          },
          riskLevel: this.defaultRiskLevel,
          latencyMs: Date.now() - startTime
        };
      }

      // Campos calculados
      const calculados = {
        alertas: this.gerarAlertas(extractedFields),
        proximoPasso: "Validar data e escopo com cliente"
      };

      const result = {
        extractedFields,
        calculados,
        obligations: [
          "Validar data do evento",
          "Confirmar escopo contratado", 
          "Registrar cláusulas críticas",
          "Verificar disponibilidade de staff",
          "Reservar insumos principais"
        ]
      };

      await this.logStep(context.agentRunId, "completed", { output: result });

      logger.info("ContractAgent completed", { runId: context.agentRunId });

      return {
        success: true,
        output: result,
        riskLevel: this.defaultRiskLevel,
        latencyMs: Date.now() - startTime
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      
      await this.logStep(context.agentRunId, "failed", { error: errorMessage });
      
      logger.error("ContractAgent failed", { error: errorMessage });

      return {
        success: false,
        output: { error: errorMessage },
        riskLevel: this.defaultRiskLevel,
        latencyMs: Date.now() - startTime
      };
    }
  }

  // Métodos de extração
  private extractClientName(input: Record<string, unknown>): string | null {
    return String(input.clientName || input.cliente || input.nome || "").trim() || null;
  }

  private extractEventDate(input: Record<string, unknown>): string | null {
    const data = input.eventDate || input.data || input.dataEvento || "";
    if (!data) return null;
    
    // Validar formato de data
    const dateStr = String(data);
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    
    if (dateRegex.test(dateStr)) {
      return dateStr;
    }
    
    // Tentar converter de formato brasileiro
    const brRegex = /^(\d{2})\/(\d{2})\/(\d{4})$/;
    const match = dateStr.match(brRegex);
    if (match) {
      return `${match[3]}-${match[2]}-${match[1]}`;
    }
    
    return null;
  }

  private extractEventType(input: Record<string, unknown>): string | null {
    return String(input.eventType || input.tipoEvento || input.tipo || "").trim() || null;
  }

  private extractNumGuests(input: Record<string, unknown>): number | null {
    const guests = input.numGuests || input.quantidadeConvidados || input.convidados || input.qtd;
    if (!guests) return null;
    
    const num = parseInt(String(guests).replace(/\D/g, ""), 10);
    return isNaN(num) ? null : num;
  }

  private extractContractValue(input: Record<string, unknown>): number | null {
    const valor = input.contractValue || input.valor || input.valorContrato || input.preco;
    if (!valor) return null;
    
    const num = parseFloat(String(valor).replace(/[R$\s.]/g, "").replace(",", "."));
    return isNaN(num) ? null : num;
  }

  private extractVenue(input: Record<string, unknown>): string | null {
    return String(input.venue || input.local || input.endereco || "").trim() || null;
  }

  private extractObservacoes(input: Record<string, unknown>): string | null {
    return String(input.observacoes || input.notes || input.obs || "").trim() || null;
  }

  private gerarAlertas(fields: Record<string, unknown | null>): string[] {
    const alertas: string[] = [];
    
    if (!fields.eventDate) {
      alertas.push("Data do evento não informada");
    }
    
    const numGuests = fields.numGuests as number | null;
    if (numGuests && numGuests > 200) {
      alertas.push("Grande evento (>200 pessoas) - verificar equipe");
    }
    
    const valor = fields.contractValue as number | null;
    if (valor && valor > 50000) {
      alertas.push("Alto valor (>R$50k) - aprovação sugerida");
    }
    
    if (!fields.venue) {
      alertas.push("Local não informado - confirmar com cliente");
    }
    
    return alertas;
  }
}

// Singleton instance
export const contractAgent = new ContractAgent();

// Auto-register in agent registry
import { agentRegistry } from "./base-agent";
agentRegistry.register(contractAgent);
