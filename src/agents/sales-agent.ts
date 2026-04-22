import { BaseAgent, AgentExecutionContext, AgentExecutionResult } from "./base-agent";
import { logger } from "../utils/logger";

export class SalesAgent extends BaseAgent {
  readonly name = "sales_agent";
  readonly description = "Gera propostas comerciais e follow-up para clientes";
  readonly defaultRiskLevel = "R2" as const;

  async execute(context: AgentExecutionContext): Promise<AgentExecutionResult> {
    const startTime = Date.now();
    
    logger.info("SalesAgent executing", { 
      runId: context.agentRunId,
      companyId: context.companyId 
    });

    await this.logStep(context.agentRunId, "running", { input: context.input });

    try {
      // Extrair dados do input
      const dadosCliente = this.extractDadosCliente(context.input);
      const dadosEvento = this.extractDadosEvento(context.input);
      
      // Validar dados mínimos
      if (!dadosCliente.nome || !dadosEvento.tipo || !dadosEvento.data) {
        await this.logStep(context.agentRunId, "failed", { 
          error: "Dados incompletos para proposta"
        });

        return {
          success: false,
          output: {
            error: "Dados incompletos",
            missing: this.identificarFaltantes(dadosCliente, dadosEvento)
          },
          riskLevel: this.defaultRiskLevel,
          latencyMs: Date.now() - startTime
        };
      }

      // Gerar proposta estruturada
      const proposta = this.gerarProposta(dadosCliente, dadosEvento, context.input);
      
      // Gerar texto formatado
      const propostaFormatada = this.formatarPropostaTexto(proposta);
      
      // Calcular estimativas
      const estimativas = this.calcularEstimativas(dadosEvento, context.input);
      
      // Definir próximos passos
      const proximosPassos = this.definirProximosPassos(proposta, dadosEvento);
      
      // Detectar follow-up necessário
      const followUp = this.detectarFollowUp(proposta);

      const result: any = {
        proposta: {
          ...proposta,
          estimativaFinanceira: estimativas
        },
        propostaFormatada,
        resumoComercial: this.gerarResumoComercial(proposta, estimativas),
        proximosPassos,
        followUp,
        diferenciais: this.listarDiferenciais(),
        validadeProposta: "15 dias"
      };

      // Marcar que gera artifact
      result._gerarArtifact = true;
      result._tipoArtifact = "proposal";

      await this.logStep(context.agentRunId, "completed", { output: result });

      logger.info("SalesAgent completed", { runId: context.agentRunId });

      return {
        success: true,
        output: result,
        riskLevel: proposta.valorEstimado > 50000 ? "R3" : this.defaultRiskLevel,
        latencyMs: Date.now() - startTime
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      
      await this.logStep(context.agentRunId, "failed", { error: errorMessage });
      
      logger.error("SalesAgent failed", { error: errorMessage });

      return {
        success: false,
        output: { error: errorMessage },
        riskLevel: this.defaultRiskLevel,
        latencyMs: Date.now() - startTime
      };
    }
  }

  // ========== MÉTODOS PRIVADOS ==========

  private extractDadosCliente(input: Record<string, unknown>): {
    nome: string | null;
    contato: string | null;
    segmento: string | null;
  } {
    return {
      nome: String(input.clientName || input.cliente || input.nome || "").trim() || null,
      contato: String(input.contato || input.telefone || input.email || "").trim() || null,
      segmento: String(input.segmento || input.segmentoCliente || "corporativo").trim()
    };
  }

  private extractDadosEvento(input: Record<string, unknown>): {
    tipo: string | null;
    data: string | null;
    numConvidados: number | null;
    local: string | null;
    observacoes: string | null;
  } {
    const dataBr = String(input.eventDate || input.data || input.dataEvento || "");
    let dataFormatada: string | null = null;
    
    if (dataBr) {
      const match = dataBr.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
      if (match) {
        dataFormatada = `${match[3]}-${match[2]}-${match[1]}`;
      } else if (/^\d{4}-\d{2}-\d{2}$/.test(dataBr)) {
        dataFormatada = dataBr;
      }
    }
    
    return {
      tipo: String(input.eventType || input.tipoEvento || input.tipo || "").trim() || null,
      data: dataFormatada,
      numConvidados: parseInt(String(input.numGuests || input.convidados || 0)) || null,
      local: String(input.venue || input.local || input.endereco || "").trim() || null,
      observacoes: String(input.observacoes || input.notes || "").trim() || null
    };
  }

  private identificarFaltantes(cliente: any, evento: any): string[] {
    const faltantes: string[] = [];
    if (!cliente.nome) faltantes.push("Nome do cliente");
    if (!evento.tipo) faltantes.push("Tipo do evento");
    if (!evento.data) faltantes.push("Data do evento");
    return faltantes;
  }

  private gerarProposta(cliente: any, evento: any, input: any): {
    cliente: string;
    evento: string;
    data: string;
    local: string | null;
    numConvidados: number;
    pacoteSugerido: string;
    servicosIncluidos: string[];
    valorEstimado: number;
    diferenciais: string[];
  } {
    const numConvidados = evento.numConvidados || 50;
    const valorBase = numConvidados * 450;
    const multiplicador = this.getMultiplicadorEvento(evento.tipo);
    const valorEstimado = Math.round(valorBase * multiplicador);
    
    return {
      cliente: cliente.nome,
      evento: evento.tipo || "Evento",
      data: evento.data,
      local: evento.local,
      numConvidados,
      pacoteSugerido: this.sugerirPacote(evento.tipo, numConvidados),
      servicosIncluidos: this.listarServicos(evento.tipo),
      valorEstimado,
      diferenciais: this.listarDiferenciais()
    };
  }

  private getMultiplicadorEvento(tipo: string): number {
    const multiplicadores: Record<string, number> = {
      casamento: 1.8,
      formatura: 1.5,
      corporativo: 1.3,
      aniversario: 1.2,
      confraternizacao: 1.1
    };
    return multiplicadores[tipo?.toLowerCase()] || 1.3;
  }

  private sugerirPacote(tipo: string, convidados: number): string {
    if (convidados < 80) return "Essencial";
    if (convidados < 200) return "Premium";
    return "Luxo Plus";
  }

  private listarServicos(tipo: string): string[] {
    const base = ["Buffet completo", "Bebidas", "Mão-de-obra (garçons, copeiros)"];
    
    const porTipo: Record<string, string[]> = {
      casamento: ["Decoração floral", "Bem-casados", "DJ/Violino", "Fotografia"],
      formatura: ["Decoração temática", "DJ", "Fotografia", "Cabine de fotos"],
      corporativo: ["Coffee break", "Projeção/TV", "Som", "Recepcionistas"],
      aniversario: ["Decoração", "DJ", "Bolo personalizado", "Fotografia"]
    };
    
    return [...base, ...(porTipo[tipo?.toLowerCase()] || ["Decoração básica", "Som"])];
  }

  private listarDiferenciais(): string[] {
    return [
      "Experiência 15+ anos em eventos premium",
      "Equipe treinada e uniformizada",
      "Fornecedores certificados",
      "Logística própria",
      "Seguro de evento incluso",
      "Suporte 24h durante evento"
    ];
  }

  private formatarPropostaTexto(proposta: any): string {
    return `
PROPOSTA COMERCIAL - ${proposta.evento.toUpperCase()}

Cliente: ${proposta.cliente}
Data: ${proposta.data}
Local: ${proposta.local || "A definir"}
Convidados: ${proposta.numConvidados}

PACOTE: ${proposta.pacoteSugerido}

SERVIÇOS INCLUSOS:
${proposta.servicosIncluidos.map((s: string) => "• " + s).join("\n")}

VALOR ESTIMADO: R$ ${proposta.valorEstimado.toLocaleString("pt-BR")}

DIFERENCIAIS ORKESTRA:
${this.listarDiferenciais().map(d => "✓ " + d).join("\n")}

VALIDADE: 15 dias

Próximos passos:
1. Aprovação da proposta
2. Assinatura de contrato (sinal 30%)
3. Briefing detalhado
4. Confirmação final (7 dias antes)
    `.trim();
  }

  private calcularEstimativas(evento: any, input: any): {
    valorTotal: number;
    porPessoa: number;
    categoria: string;
    observacao: string;
  } {
    const numConvidados = evento.numConvidados || 50;
    const valorBase = numConvidados * 450;
    const multiplicador = this.getMultiplicadorEvento(evento.tipo);
    const valorTotal = Math.round(valorBase * multiplicador);
    
    let categoria = "Médio";
    if (valorTotal > 100000) categoria = "Premium";
    else if (valorTotal > 50000) categoria = "Alto";
    else if (valorTotal < 30000) categoria = "Econômico";
    
    return {
      valorTotal,
      porPessoa: Math.round(valorTotal / numConvidados),
      categoria,
      observacao: "Valores estimados, sujeitos a confirmação ap briefing"
    };
  }

  private gerarResumoComercial(proposta: any, estimativas: any): string {
    return `Proposta ${proposta.pacoteSugerido} para ${proposta.cliente} - ${proposta.evento} (${proposta.numConvidados} convidados). Valor: R$ ${estimativas.valorTotal.toLocaleString("pt-BR")}. Validade: 15 dias.`;
  }

  private definirProximosPassos(proposta: any, evento: any): string[] {
    return [
      "Aprovação da proposta pelo cliente",
      "Agendamento de briefing detalhado",
      "Assinatura de contrato e pagamento de sinal",
      "Reunião de alinhamento (30 dias antes)",
      "Confirmação final (7 dias antes)",
      "Execução do evento"
    ];
  }

  private detectarFollowUp(proposta: any): {
    necessario: boolean;
    quando: string;
    mensagem: string;
    canais: string[];
  } {
    const valorAlto = proposta.valorEstimado > 80000;
    const eventoPremium = ["casamento", "formatura"].includes(proposta.evento?.toLowerCase());
    
    if (valorAlto || eventoPremium) {
      return {
        necessario: true,
        quando: "48 horas após envio se sem resposta",
        mensagem: `Olá ${proposta.cliente}! A proposta para seu ${proposta.evento} foi personalizada especialmente para você. Posso esclarecer dúvidas ou ajustar algo?`,
        canais: ["whatsapp", "email"]
      };
    }
    
    return {
      necessario: true,
      quando: "72 horas após envio se sem resposta",
      mensagem: `Oi! Verificando se recebeu nossa proposta para ${proposta.evento}. Estou à disposição!`,
      canais: ["email"]
    };
  }
}

// Singleton
export const salesAgent = new SalesAgent();

// Auto-register
import { agentRegistry } from "./base-agent";
agentRegistry.register(salesAgent);
