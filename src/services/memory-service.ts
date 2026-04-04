/**
 * Memory Service - Persistência simples de aprendizado
 * Sem IA avançada - apenas logs estruturados
 */

import { prisma } from "../db";

export type MemoryType = 
  | "decision"    // Decisões importantes
  | "error"       // Erros encontrados
  | "pattern"     // Padrões recorrentes
  | "insight"     // Aprendizados pontuais
  | "event";      // Eventos marcantes

export type MemoryInput = {
  companyId: string;
  type: MemoryType;
  content: string;
  context?: Record<string, unknown>;
  agentRunId?: string;
};

export class MemoryService {
  /**
   * Salva entrada na memória
   */
  async log(memory: MemoryInput) {
    // Truncate content to reasonable size
    const truncated = memory.content.length > 10000 
      ? memory.content.slice(0, 10000) + "... [truncated]"
      : memory.content;

    return prisma.memoryItem.create({
      data: {
        companyId: memory.companyId,
        memoryType: memory.type,
        title: this._generateTitle(memory.type, memory.content),
        content: truncated,
        sourceType: memory.agentRunId ? "agent_run" : "system",
        sourceRef: memory.agentRunId || undefined,
        tags: [memory.type, ...this._extractTags(memory)],
        createdAt: new Date()
      }
    });
  }

  /**
   * Busca memórias por tipo
   */
  async getByType(companyId: string, type: MemoryType, limit = 20) {
    return prisma.memoryItem.findMany({
      where: {
        companyId,
        memoryType: type
      },
      orderBy: { createdAt: "desc" },
      take: limit
    });
  }

  /**
   * Busca memórias recentes (últimas 30 dias)
   */
  async getRecent(companyId: string, days = 30, limit = 50) {
    const since = new Date();
    since.setDate(since.getDate() - days);

    return prisma.memoryItem.findMany({
      where: {
        companyId,
        createdAt: { gte: since }
      },
      orderBy: { createdAt: "desc" },
      take: limit
    });
  }

  /**
   * Busca por palavra-chave (busca simples em content)
   */
  async search(companyId: string, query: string, limit = 10) {
    // Busca simples usando ILIKE
    const normalized = query.toLowerCase().trim();
    
    return prisma.memoryItem.findMany({
      where: {
        companyId,
        OR: [
          { content: { contains: normalized, mode: "insensitive" } },
          { title: { contains: normalized, mode: "insensitive" } }
        ]
      },
      orderBy: { createdAt: "desc" },
      take: limit
    });
  }

  /**
   * Gera resumo de aprendizado recente
   */
  async generateSummary(companyId: string, days = 7): Promise<string> {
    const memories = await this.getRecent(companyId, days, 100);
    
    const byType = memories.reduce((acc, m) => {
      acc[m.memoryType] = (acc[m.memoryType] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const summary = [
      `## Resumo de Aprendizado (últimos ${days} dias)`,
      ``,
      ...Object.entries(byType).map(([type, count]) => 
        `- ${type}: ${count} registros`
      ),
      ``,
      `Total: ${memories.length} memórias`
    ].join("\n");

    return summary;
  }

  // Helpers
  private _generateTitle(type: MemoryType, content: string): string {
    const prefix = {
      decision: "[Decisão]",
      error: "[Erro]",
      pattern: "[Padrão]",
      insight: "[Insight]",
      event: "[Evento]"
    }[type];

    // Pegar primeira frase ou primeiros 50 chars
    const snippet = content.split(/[.!?]/, 1)[0].slice(0, 50);
    return `${prefix} ${snippet}${snippet.length >= 50 ? "..." : ""}`;
  }

  private _extractTags(memory: MemoryInput): string[] {
    const tags: string[] = [];
    
    if (memory.agentRunId) {
      tags.push("agent-run");
    }
    
    // Extrair palavras relevantes do contexto
    if (memory.context) {
      if (memory.context.workflowType) {
        tags.push(String(memory.context.workflowType));
      }
      if (memory.context.agentName) {
        tags.push(String(memory.context.agentName));
      }
    }

    return tags;
  }
}

// Singleton
export const memoryService = new MemoryService();
