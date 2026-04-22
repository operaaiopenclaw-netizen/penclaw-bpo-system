import { BaseAgent, AgentExecutionContext, AgentExecutionResult } from "./base-agent";
import { logger } from "../utils/logger";

export class OperationsAgent extends BaseAgent {
  readonly name = "operations_agent";
  readonly description = "Gera checklist operacional e detecta riscos em eventos";
  readonly defaultRiskLevel = "R2" as const;

  async execute(context: AgentExecutionContext): Promise<AgentExecutionResult> {
    const startTime = Date.now();
    
    logger.info("OperationsAgent executing", { 
      runId: context.agentRunId,
      companyId: context.companyId 
    });

    await this.logStep(context.agentRunId, "running", { input: context.input });

    try {
      // Extrair dados
      const evento = this.extractDadosEvento(context.input);
      const servicos = this.extractServicos(context.input);
      const financeiro = this.extractDadosFinanceiros(context.input);
      
      // Validar
      if (!evento.tipo || !evento.numPessoas) {
        return {
          success: false,
          output: { error: "Tipo de evento e número de pessoas são obrigatórios" },
          riskLevel: this.defaultRiskLevel,
          latencyMs: Date.now() - startTime
        };
      }

      // Gerar checklist completo
      const checklist = this.gerarChecklist(evento, servicos);
      
      // Detectar riscos
      const riscos = this.detectarRiscos(evento, financeiro, servicos);
      
      // Gerar estimativas
      const estimativas = this.calcularEstimativas(evento, servicos);
      
      // Construir resultado
      const result: any = {
        checklist,
        riscos,
        estimativas,
        acoesRecomendadas: this.gerarAcoesRecomendadas(riscos, checklist),
        resumoOperacional: this.gerarResumo(evento, checklist, riscos)
      };

      // Marcar artifact
      result._gerarArtifact = true;
      result._tipoArtifact = "checklist";

      // Salvar memory se houver riscos
      if (riscos.length > 0) {
        result._salvarMemoryRisk = true;
        result._riscosParaMemory = riscos;
      }

      await this.logStep(context.agentRunId, "completed", { output: result });

      logger.info("OperationsAgent completed", { 
        runId: context.agentRunId,
        numRiscos: riscos.length 
      });

      return {
        success: true,
        output: result,
        riskLevel: riscos.some(r => r.nivel === "ALTO") ? "R3" : this.defaultRiskLevel,
        latencyMs: Date.now() - startTime
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      await this.logStep(context.agentRunId, "failed", { error: errorMessage });
      logger.error("OperationsAgent failed", { error: errorMessage });

      return {
        success: false,
        output: { error: errorMessage },
        riskLevel: this.defaultRiskLevel,
        latencyMs: Date.now() - startTime
      };
    }
  }

  // ========== EXTRAÇÃO ==========

  private extractDadosEvento(input: Record<string, unknown>): {
    tipo: string;
    numPessoas: number;
    data: string | null;
    local: string | null;
    estilo: string;
  } {
    return {
      tipo: String(input.eventType || input.tipo || "evento").toLowerCase(),
      numPessoas: parseInt(String(input.numGuests || input.pessoas || 100)) || 100,
      data: String(input.eventDate || input.data || "").trim() || null,
      local: String(input.venue || input.local || "").trim() || null,
      estilo: String(input.estilo || input.tematica || "tradicional").toLowerCase()
    };
  }

  private extractServicos(input: Record<string, unknown>): {
    buffet: boolean;
    bebidas: boolean;
    decoracao: boolean;
    som: boolean;
    fotografia: boolean;
    staffAdicional: boolean;
  } {
    return {
      buffet: input.buffet !== false,
      bebidas: input.bebidas !== false,
      decoracao: !!input.decoracao,
      som: !!input.som,
      fotografia: !!input.fotografia,
      staffAdicional: !!input.staffAdicional
    };
  }

  private extractDadosFinanceiros(input: Record<string, unknown>): {
    orcamentoTotal: number;
    margemEsperada: number;
    valorPorPessoa: number;
  } {
    const numPessoas = parseInt(String(input.numGuests || 100)) || 100;
    const total = parseFloat(String(input.budget || input.orcamento || 0)) || 0;
    
    return {
      orcamentoTotal: total,
      margemEsperada: parseFloat(String(input.margem || 25)) || 25,
      valorPorPessoa: total > 0 ? total / numPessoas : 0
    };
  }

  // ========== CHECKLIST ==========

  private gerarChecklist(evento: any, servicos: any): {
    staff: string[];
    insumos: string[];
    bebidas: string[];
    equipamentos: string[];
    logistica: string[];
  } {
    const numPessoas = evento.numPessoas;
    const ratioGarcom = Math.ceil(numPessoas / 25);
    const ratioCopeiro = Math.ceil(numPessoas / 40);
    const ratioSeguranca = Math.ceil(numPessoas / 50);

    const staff = [
      `Chef de cozinha: ${numPessoas > 150 ? 2 : 1}`,
      `Chef de partie: ${Math.ceil(numPessoas / 80)}`,
      `Garçons: ${ratioGarcom}`,
      `Copeiros: ${Math.max(2, ratioCopeiro)}`,
      `Bartenders: ${Math.ceil(numPessoas / 40)}`,
      `Seguranças: ${ratioSeguranca}`,
      `Recepcionista/Hostess: ${numPessoas > 100 ? 2 : 1}`,
      `Gerente de evento: 1`,
      servicos.decoracao ? `Montador de decoração: ${numPessoas > 200 ? 3 : 2}` : null,
      servicos.som ? `Técnico de som/iluminação: ${numPessoas > 200 ? 2 : 1}` : null
    ].filter(Boolean) as string[];

    const insumos = this.gerarInsumos(evento, numPessoas);
    const bebidas = this.gerarListaBebidas(numPessoas, servicos);
    const equipamentos = this.gerarEquipamentos(numPessoas, servicos);
    const logistica = this.gerarLogistica(numPessoas);

    return { staff, insumos, bebidas, equipamentos, logistica };
  }

  private gerarInsumos(evento: any, pessoas: number): string[] {
    const base = [
      `Pratos: ${Math.ceil(pessoas * 1.2)} unidades`,
      `Talheres (jogos): ${pessoas} jogos`,
      `Copos: ${Math.ceil(pessoas * 2.5)} unidades`,
      `Guardanapos: ${pessoas} unidades`,
      `Toalhas de mesa: ${Math.ceil(pessoas / 8)} unidades`,
      `Bandejas de servir: ${Math.ceil(pessoas / 20)} unidades`
    ];

    if (evento.tipo === "casamento") {
      base.push("Taças de champagne (cerimonial)", "Cesta de flor para mesa", "Porta-copos personalizados");
    }

    return base;
  }

  private gerarListaBebidas(pessoas: number, servicos: any): string[] {
    const litrosPorPessoa = 3;
    const totalLitros = pessoas * litrosPorPessoa;
    
    return [
      `Água mineral: ${Math.ceil(totalLitros * 0.4)}L`,
      `Refrigerantes: ${Math.ceil(totalLitros * 0.3)}L`,
      `Sucos naturais: ${Math.ceil(totalLitros * 0.15)}L`,
      servicos.bebidas ? `Cerveja: ${Math.ceil(totalLitros * 0.1)}L` : null,
      servicos.bebidas ? `Vinhos: ${Math.ceil(pessoas / 8)} garrafas` : null,
      servicos.bebidas ? `Destilados (cervejaria): ${Math.ceil(pessoas / 20)}L` : null,
      `Gelo: ${Math.ceil(totalLitros / 5)}kg`
    ].filter(Boolean) as string[];
  }

  private gerarEquipamentos(pessoas: number, servicos: any): string[] {
    const mesas = Math.ceil(pessoas / 8);
    const cadeiras = Math.ceil(pessoas * 1.1);

    return [
      `Mesas: ${mesas} unidades (redondas 8 lugares)`,
      `Cadeiras: ${cadeiras} unidades`,
      `Buffet estação: ${pessoas > 100 ? 3 : 2} unidades`,
      `Mesa de doces: 1 unidade`,
      servicos.decoraacao ? "Suportes de decoração floral" : null,
      servicos.som ? "Sistema de som + microfones" : null,
      pessoas > 150 ? "Palco/Piso elevado" : null,
      pessoas > 200 ? "Tenda/cobertura" : null,
      "Expositores/Baleiros",
      "Carrinhos de servir"
    ].filter(Boolean) as string[];
  }

  private gerarLogistica(pessoas: number): string[] {
    return [
      "Caminhão refrigerado para transporte de perecíveis",
      "Carrinhos de transporte",
      "Mão de obra para carga/descarga",
      `Check-in de equipe: ${Math.ceil(pessoas / 50)} pontos`,
      "Kit primeiros socorros",
      "Fita crepe/nylon/etiquetas",
      "Extensões e equipamentos elétricos",
      "Sacos de lixo (capacidade 3x consumo)"
    ];
  }

  // ========== DETECÇÃO DE RISCOS ==========

  private detectarRiscos(evento: any, financeiro: any, servicos: any): Array<{
    categoria: string;
    descricao: string;
    nivel: "BAIXO" | "MEDIO" | "ALTO";
    acaoSugerida: string;
  }> {
    const riscos: Array<{categoria: string; descricao: string; nivel: "BAIXO" | "MEDIO" | "ALTO"; acaoSugerida: string}> = [];

    // Risco logístico - evento grande
    if (evento.numPessoas > 200) {
      riscos.push({
        categoria: "LOGISTICO",
        descricao: `Evento grande (${evento.numPessoas} pessoas) exige coordenação reforçada`,
        nivel: "ALTO",
        acaoSugerida: "Aumentar equipe em 30%; briefing detalhado; plano de emergência"
      });
    } else if (evento.numPessoas > 120) {
      riscos.push({
        categoria: "LOGISTICO",
        descricao: "Evento de médio porte - atenção à sincronia",
        nivel: "MEDIO",
        acaoSugerida: "Garantir 1 coordenador por 50 convidados"
      });
    }

    // Risco financeiro - margem baixa
    if (financeiro.margemEsperada < 20) {
      riscos.push({
        categoria: "FINANCEIRO",
        descricao: `Margem baixa (${financeiro.margemEsperada}%) - pouca folga para imprevistos`,
        nivel: "ALTO",
        acaoSugerida: "Revisar custos; negociar com fornecedores; considerar seguro"
      });
    } else if (financeiro.margemEsperada < 25) {
      riscos.push({
        categoria: "FINANCEIRO",
        descricao: "Margem apertada - monitorar custos extras",
        nivel: "MEDIO",
        acaoSugerida: "Bloquear gastos não essenciais; aprovação prévia"
      });
    }

    // Risco operacional - pouca equipe
    if (evento.numPessoas > 80 && !servicos.staffAdicional) {
      riscos.push({
        categoria: "OPERACIONAL",
        descricao: "Evento >80 pessoas sem staff adicional - sobrecarregará equipe",
        nivel: "ALTO",
        acaoSugerida: "Contratar garçons extra; reforço no bar; segurança adicional"
      });
    }

    // Risco de bebidas se não contratado
    if (evento.numPessoas > 60 && !servicos.bebidas) {
      riscos.push({
        categoria: "OPERACIONAL",
        descricao: "Grande evento sem serviço de bebidas pode gerar insatisfação",
        nivel: "MEDIO",
        acaoSugerida: "Confirmar com cliente se bebidas serão por conta do local"
      });
    }

    // Risco de equipamentos
    if (evento.numPessoas > 150 && !servicos.som) {
      riscos.push({
        categoria: "OPERACIONAL",
        descricao: "Evento grande sem sistema de som adequado",
        nivel: "MEDIO",
        acaoSugerida: "Alertar cliente sobre necessidade de PA ou contratar"
      });
    }

    return riscos;
  }

  // ========== ESTIMATIVAS ==========

  private calcularEstimativas(evento: any, servicos: any): {
    custoEstimado: number;
    tempoMontagem: string;
    tempoDesmontagem: string;
    pontoCritico: string;
  } {
    const base = evento.numPessoas * 150; // custo base/pessoa
    const comServicos = base * (1 + (servicos.decoracao ? 0.2 : 0) + (servicos.bebidas ? 0.25 : 0));

    return {
      custoEstimado: Math.round(comServicos),
      tempoMontagem: evento.numPessoas > 150 ? "8 horas" : "5 horas",
      tempoDesmontagem: "3 horas",
      pontoCritico: evento.numPessoas > 200 ? "Sincronizar 3+ equipes simultâneas" : "Transição coquetel → jantar"
    };
  }

  // ========== AÇÕES E RESUMO ==========

  private gerarAcoesRecomendadas(riscos: any[], checklist: any): string[] {
    const acoes = [
      "Reunião de briefing completa (H-2 dias)",
      "Check listagem de estoque vs checklist",
      "Confirmar fornecedores com 48h antecedência",
      "Teste de equipamentos (H-1 dia)",
      "Kit de emergência montado"
    ];

    if (riscos.some(r => r.nivel === "ALTO")) {
      acoes.unshift("⚠️ REUNIÃO EXTRA - riscos ALTOS identificados");
      acoes.push("Plano de contingência documentado");
    }

    return acoes;
  }

  private gerarResumo(evento: any, checklist: any, riscos: any[]): string {
    const riscoStr = riscos.length > 0 
      ? `| ${riscos.length} riscos (${riscos.filter(r => r.nivel === "ALTO").length} alto)`
      : "| Sem riscos críticos";
    
    return `Checklist ${evento.tipo} (${evento.numPessoas} pessoas): ${checklist.staff.length} funções, ${checklist.insumos.length} insumos ${riscoStr}`;
  }
}

// Singleton
export const operationsAgent = new OperationsAgent();

// Auto-register
import { agentRegistry } from "./base-agent";
agentRegistry.register(operationsAgent);
