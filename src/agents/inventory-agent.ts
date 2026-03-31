import { BaseAgent, AgentExecutionContext, AgentExecutionResult } from "./base-agent";
import { prisma } from "../db";
import { logger } from "../utils/logger";

export class InventoryAgent extends BaseAgent {
  readonly name = "inventory_agent";
  readonly description = "Gestão de estoque e sugestões de compra para eventos";
  readonly defaultRiskLevel = "R2" as const;

  async execute(context: AgentExecutionContext): Promise<AgentExecutionResult> {
    const startTime = Date.now();
    
    logger.info("InventoryAgent executing", { 
      runId: context.agentRunId,
      companyId: context.companyId 
    });

    await this.logStep(context.agentRunId, "running", { input: context.input });

    try {
      const eventType = String(context.input.eventType || context.input.tipoEvento || "");
      const numGuests = parseInt(String(context.input.numGuests || context.input.convidados || 0), 10);

      // Analisar necessidades baseadas no tipo de evento
      const needs = this.analyzeNeeds(eventType, numGuests);

      // Verificar estoque atual
      const stockStatus = await this.checkStock(context, needs);

      // Gerar sugestões de compra
      const purchaseSuggestions = this.generatePurchaseSuggestions(stockStatus);

      // Avaliar risco
      const stockRisk = this.assessRisk(stockStatus, purchaseSuggestions);

      // Calcular previsões
      const forecasts = this.calculateForecasts(stockStatus, purchaseSuggestions);

      const result = {
        purchaseSuggestions,
        stockRisk: stockRisk.level,
        basis: eventType || "unknown",
        needs,
        currentStock: stockStatus.current,
        shortages: stockRisk.shortages,
        critical: stockRisk.critical,
        alerts: stockRisk.alerts,
        forecasts,
        nextSteps: [
          "Verificar fornecedores aprovados",
          "Comparar preços de cotação",
          "Confirmar prazos de entrega",
          "Reservar itens críticos"
        ],
        suppliers: await this.getSuppliersForItems(purchaseSuggestions.map(p => p.itemId))
      };

      await this.logStep(context.agentRunId, "completed", { output: result });

      logger.info("InventoryAgent completed", { 
        runId: context.agentRunId,
        risk: stockRisk.level,
        suggestions: purchaseSuggestions.length
      });

      return {
        success: true,
        output: result,
        riskLevel: stockRisk.level === "high" ? "R3" : this.defaultRiskLevel,
        latencyMs: Date.now() - startTime
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      
      await this.logStep(context.agentRunId, "failed", { error: errorMessage });
      logger.error("InventoryAgent failed", { error: errorMessage });

      return {
        success: false,
        output: { error: errorMessage, stockRisk: "unknown" },
        riskLevel: "R3",
        latencyMs: Date.now() - startTime
      };
    }
  }

  // Analisar necessidades por tipo de evento
  private analyzeNeeds(eventType: string, numGuests: number): Array<{
    category: string;
    items: Array<{ name: string; unitPerGuest: number; total: number }>;
  }> {
    const perGuest = numGuests || 100;

    const needsMap: Record<string, Array<{ name: string; unitPerGuest: number; total: number }>> = {
      "casamento": [
        { name: "Guardanapos de linho", unitPerGuest: 1.2, total: Math.ceil(perGuest * 1.2) },
        { name: "Taças de champanhe", unitPerGuest: 1.5, total: Math.ceil(perGuest * 1.5) },
        { name: "Pratos sobremesa", unitPerGuest: 1.0, total: perGuest },
        { name: "Velas decorativas", unitPerGuest: 0.3, total: Math.ceil(perGuest * 0.3) }
      ],
      "corporativo": [
        { name: "Copos de café", unitPerGuest: 2.5, total: Math.ceil(perGuest * 2.5) },
        { name: "Pratos executivos", unitPerGuest: 1.0, total: perGuest },
        { name: "Garrafas de água", unitPerGuest: 1.0, total: perGuest },
        { name: "Canudos eco", unitPerGuest: 2.0, total: perGuest * 2 }
      ],
      "aniversario": [
        { name: "Pratos de bolo", unitPerGuest: 1.0, total: perGuest },
        { name: "Copos descartáveis", unitPerGuest: 1.5, total: Math.ceil(perGuest * 1.5) },
        { name: "Balões", unitPerGuest: 0.2, total: Math.ceil(perGuest * 0.2) }
      ],
      "default": [
        { name: "Copos", unitPerGuest: 1.5, total: Math.ceil(perGuest * 1.5) },
        { name: "Pratos", unitPerGuest: 1.0, total: perGuest },
        { name: "Talheres", unitPerGuest: 2.0, total: perGuest * 2 }
      ]
    };

    const needs = needsMap[eventType.toLowerCase()] || needsMap["default"];
    
    return [{
      category: eventType || "geral",
      items: needs
    }];
  }

  // Verificar estoque atual
  private async checkStock(
    context: AgentExecutionContext,
    needs: ReturnType<typeof this.analyzeNeeds>
  ): Promise<{
    current: Array<{ itemId: string; name: string; quantity: number; status: string }>;
    missing: Array<{ itemId: string; name: string; needed: number; available: number; gap: number }>;
  }> {
    const current: Array<{ itemId: string; name: string; quantity: number; status: string }> = [];
    const missing: Array<{ itemId: string; name: string; needed: number; available: number; gap: number }> = [];

    try {
      // Buscar itens no banco de dados
      const items = await prisma.inventoryItem.findMany({
        where: { companyId: context.companyId }
      });

      for (const need of needs) {
        for (const item of need.items) {
          const dbItem = items.find(i => 
            i.name.toLowerCase().includes(item.name.toLowerCase())
          );

          if (dbItem) {
            current.push({
              itemId: dbItem.id,
              name: dbItem.name,
              quantity: dbItem.currentStock || 0,
              status: this.getStockStatus(dbItem.currentStock || 0, item.total)
            });

            const gap = item.total - (dbItem.currentStock || 0);
            if (gap > 0) {
              missing.push({
                itemId: dbItem.id,
                name: dbItem.name,
                needed: item.total,
                available: dbItem.currentStock || 0,
                gap
              });
            }
          } else {
            missing.push({
              itemId: "unknown",
              name: item.name,
              needed: item.total,
              available: 0,
              gap: item.total
            });
          }
        }
      }
    } catch (error) {
      logger.warn("Failed to check stock via DB, using placeholder", { error });
    }

    return { current, missing };
  }

  private getStockStatus(available: number, needed: number): string {
    const ratio = needed > 0 ? available / needed : 0;
    if (ratio >= 1) return "sufficient";
    if (ratio >= 0.5) return "low";
    if (ratio >= 0.2) return "critical";
    return "insufficient";
  }

  // Gerar sugestões de compra
  private generatePurchaseSuggestions(
    stockStatus: ReturnType<typeof this.checkStock>
  ): Array<{
    itemId: string;
    name: string;
    quantity: number;
    urgency: "low" | "medium" | "high";
    estimatedCost: number;
    suppliers: string[];
  }> {
    return stockStatus.missing.map(miss => ({
      itemId: miss.itemId,
      name: miss.name,
      quantity: Math.ceil(miss.gap * 1.1), // 10% buffer
      urgency: miss.gap > 50 ? "high" : miss.gap > 20 ? "medium" : "low",
      estimatedCost: miss.gap * (Math.random() * 10 + 5), // Simulação
      suppliers: [] // Preenchido depois
    }));
  }

  // Avaliar risco
  private assessRisk(
    stockStatus: ReturnType<typeof this.checkStock>,
    suggestions: ReturnType<typeof this.generatePurchaseSuggestions>
  ): {
    level: "low" | "medium" | "high";
    shortages: number;
    critical: number;
    alerts: string[];
  } {
    const alerts: string[] = [];
    const criticalItems = stockStatus.missing.filter(m => m.gap > 50);
    
    if (criticalItems.length > 0) {
      alerts.push(`🚨 ${criticalItems.length} itens críticos faltando > 50 unidades`);
    }

    const highUrgencyItems = suggestions.filter(s => s.urgency === "high");
    if (highUrgencyItems.length > 3) {
      alerts.push("⚠️ Múltiplos itens alta urgência - requer compra imediata");
    }

    return {
      level: criticalItems.length > 0 ? "high" : highUrgencyItems.length > 0 ? "medium" : "low",
      shortages: stockStatus.missing.length,
      critical: criticalItems.length,
      alerts
    };
  }

  // Calcular previsões
  private calculateForecasts(
    stockStatus: ReturnType<typeof this.checkStock>,
    suggestions: ReturnType<typeof this.generatePurchaseSuggestions>
  ): {
    totalInvestment: number;
    deliveryTime: number;
    bufferDays: number;
  } {
    const totalInvestment = suggestions.reduce((sum, s) => sum + s.estimatedCost, 0);
    const maxUrgency = suggestions.some(s => s.urgency === "high") ? 2 : 
                       suggestions.some(s => s.urgency === "medium") ? 5 : 10;

    return {
      totalInvestment,
      deliveryTime: maxUrgency,
      bufferDays: Math.max(3, maxUrgency + 2)
    };
  }

  // Buscar fornecedores
  private async getSuppliersForItems(itemIds: string[]): Promise<Array<{
    id: string;
    name: string;
    rating: number;
    leadTime: number;
  }>> {
    // Simulação - na realidade buscaria do banco
    return [
      { id: "sup-001", name: "Distribuidora São Paulo", rating: 4.5, leadTime: 2 },
      { id: "sup-002", name: "Fornecedor Local", rating: 4.0, leadTime: 1 },
      { id: "sup-003", name: "Importadora Rio", rating: 4.7, leadTime: 5 }
    ].filter(() => true); // Placeholder
  }
}

// Singleton
export const inventoryAgent = new InventoryAgent();

// Auto-registration
import { agentRegistry } from "./base-agent";
agentRegistry.register(inventoryAgent);
