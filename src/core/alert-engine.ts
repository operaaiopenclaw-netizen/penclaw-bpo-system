/**
 * Alert Engine - Notificação automática de riscos
 * Simples, sem IA - apenas regras
 */

import { prisma } from "../db";
import { memoryService } from "../services/memory-service";
import { logger } from "../utils/logger";
import {
  notificationDispatcher,
  type ChannelDeliveryResult,
  type ChannelSeverity,
  type NotificationPayload,
} from "../channels";

export type AlertRule = {
  name: string;
  condition: (data: any) => boolean;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  message: string;
  category: "FINANCE" | "OPERATIONS" | "COMPLIANCE" | "LOGISTICS" | "INVENTORY" | "PRODUCTION";
};

export type TriggeredAlert = {
  rule: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  message: string;
  category: string;
  details?: Record<string, unknown>;
};

export type OperationalContext = {
  tenantId: string;
  eventId?: string;
  stock?: Array<{
    itemCode: string;
    itemName: string;
    onHand: number;
    required: number;
    safetyStock?: number;
  }>;
  stations?: Array<{
    stationId: string;
    stationName: string;
    loadHours: number;
    capacityHours: number;
  }>;
  margin?: {
    projectedPct?: number | null;
    realPct?: number | null;
    deltaPct?: number | null;
  };
  reconciliation?: {
    overallAccuracyScore?: number;
    highVariances?: Array<{ itemCode: string; variancePct: number }>;
  };
};

export class AlertEngine {
  // Regras pré-definidas
  private rules: AlertRule[] = [
    {
      name: "MARGEM_BAIXA",
      condition: (data) => data.margem < 20 || (data.margemEsperada && data.margemEsperada < 20),
      severity: "HIGH",
      message: "Margem inferior a 20% - alto risco financeiro",
      category: "FINANCE"
    },
    {
      name: "MARGEM_CRITICA",
      condition: (data) => data.margem < 15,
      severity: "CRITICAL",
      message: "Margem crítica (<15%) - aprovação obrigatória",
      category: "FINANCE"
    },
    {
      name: "EVENTO_GRANDE",
      condition: (data) => data.numPessoas > 300 || data.numConvidados > 300,
      severity: "MEDIUM",
      message: "Evento grande (>300 pessoas) - requer coordenação reforçada",
      category: "LOGISTICS"
    },
    {
      name: "EVENTO_MEGA",
      condition: (data) => data.numPessoas > 500 || data.numConvidados > 500,
      severity: "HIGH",
      message: "Evento mega (>500 pessoas) - briefing obrigatório 48h antes",
      category: "LOGISTICS"
    },
    {
      name: "STAFF_INSUFICIENTE",
      condition: (data) => {
        const ratio = data.staffCount / data.numPessoas;
        return !!(ratio && ratio < 0.05); // menos de 1 staff por 20 convidados
      },
      severity: "HIGH",
      message: "Staff insuficiente (<5% dos convidados)",
      category: "OPERATIONS"
    },
    {
      name: "ORCAMENTO_ALTO",
      condition: (data) => data.orcamentoTotal > 100000,
      severity: "LOW",
      message: "Orçamento elevado - sugerir validação gerencial",
      category: "FINANCE"
    },
    {
      name: "VALOR_ALTO_RISCO",
      condition: (data) => data.valorEstimado > 80000 || data.contractValue > 80000,
      severity: "MEDIUM",
      message: "Valor contratual elevado - verificar garantias",
      category: "COMPLIANCE"
    },
    {
      name: "PRAZO_CURTO",
      condition: (data) => {
        if (!data.data || !data.eventDate) return false;
        const eventDate = new Date(data.eventDate || data.data);
        const daysUntil = (eventDate.getTime() - Date.now()) / (1000 * 60 * 60 * 24);
        return daysUntil < 14 && daysUntil > 0;
      },
      severity: "MEDIUM",
      message: "Prazo curto (<14 dias) - prioridade máxima",
      category: "OPERATIONS"
    },
    {
      name: "PRAZO_CRITICO",
      condition: (data) => {
        if (!data.data && !data.eventDate) return false;
        const eventDate = new Date(data.eventDate || data.data);
        const daysUntil = (eventDate.getTime() - Date.now()) / (1000 * 60 * 60 * 24);
        return daysUntil < 7 && daysUntil > 0;
      },
      severity: "HIGH",
      message: "Prazo crítico (<7 dias) - ação imediata necessária",
      category: "OPERATIONS"
    },
    {
      name: "DATA_INVALIDA",
      condition: (data) => data.data === null && data.eventDate === null,
      severity: "CRITICAL",
      message: "Data do evento não definida - bloquear until confirmed",
      category: "COMPLIANCE"
    }
  ];

  /**
   * Avalia dados e gera alertas
   */
  async evaluate(
    agentRunId: string,
    companyId: string,
    data: Record<string, unknown>
  ): Promise<Array<{
    rule: string;
    severity: string;
    message: string;
    category: string;
  }>> {
    const triggered: Array<{
      rule: string;
      severity: string;
      message: string;
      category: string;
    }> = [];

    for (const rule of this.rules) {
      try {
        if (rule.condition(data)) {
          triggered.push({
            rule: rule.name,
            severity: rule.severity,
            message: rule.message,
            category: rule.category
          });

          // Salvar como alerta na memória
          await this.saveAlert(agentRunId, companyId, rule, data);

          // Log no console
          logger.warn(`ALERT: ${rule.name} - ${rule.message}`, {
            runId: agentRunId,
            severity: rule.severity,
            category: rule.category
          });
        }
      } catch (error) {
        logger.error("Alert rule evaluation error", {
          rule: rule.name,
          error: error instanceof Error ? error.message : String(error)
        });
      }
    }

    return triggered;
  }

  /**
   * Salva alerta na memória
   */
  private async saveAlert(
    agentRunId: string,
    companyId: string,
    rule: AlertRule,
    data: any
  ): Promise<void> {
    try {
      await memoryService.log({
        companyId,
        type: "insight",
        content: `ALERTA ${rule.severity}: ${rule.message}`,
        context: {
          agentRunId,
          rule: rule.name,
          severity: rule.severity,
          category: rule.category,
          dados: {
            margem: data.margem || data.margemEsperada,
            numPessoas: data.numPessoas || data.numConvidados || data.pessoas,
            staff: data.staffCount,
            valor: data.orcamentoTotal || data.valorEstimado,
            data: data.data || data.eventDate
          }
        },
        agentRunId
      });
    } catch (error) {
      logger.error("Failed to save alert to memory", { rule: rule.name });
    }
  }

  /**
   * Formata alertas para saída (preparado para WhatsApp/Email)
   */
  formatForNotification(alerts: Array<{
    rule: string;
    severity: string;
    message: string;
    category: string;
  }>): {
    whatsapp: string;
    email: string;
    count: number;
    hasCritical: boolean;
  } {
    const critical = alerts.filter(a => a.severity === "CRITICAL");
    const high = alerts.filter(a => a.severity === "HIGH");
    const medium = alerts.filter(a => a.severity === "MEDIUM");
    const low = alerts.filter(a => a.severity === "LOW");
    
    const emoji: Record<string, string> = {
      CRITICAL: "🚨",
      HIGH: "⚠️",
      MEDIUM: "⚡",
      LOW: "ℹ️"
    };

    // Formato WhatsApp (curto, direto)
    const whatsapp = [
      `🎛️ *ORKESTRA ALERTS*`,
      ``,
      `Detectados ${alerts.length} alerta(s):`,
      ...alerts.slice(0, 5).map(a => `${emoji[a.severity]} ${a.severity}: ${a.message}`),
      alerts.length > 5 ? `...e mais ${alerts.length - 5}` : "",
      ``,
      critical.length > 0 ? "⚠️ *AÇÃO IMEDIATA NECESSÁRIA*" : "",
      ``
    ].filter(Boolean).join("\n");

    // Formato Email (completo)
    const email = `
<!DOCTYPE html>
<html>
<head><title>Orkestra Alerts</title></head>
<body style="font-family: sans-serif; padding: 20px;">
  <h2>🎛️ Alertas do Sistema</h2>
  <p>Detectados <strong>${alerts.length}</strong> alerta(s) que precisam de atenção:</p>
  
  <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
    <tr style="background: #333; color: white;">
      <th style="padding: 10px; border: 1px solid #ddd;">Severidade</th>
      <th style="padding: 10px; border: 1px solid #ddd;">Categoria</th>
      <th style="padding: 10px; border: 1px solid #ddd;">Mensagem</th>
    </tr>
    ${alerts.map(a => `
    <tr style="background: ${a.severity === 'CRITICAL' ? '#ffcccc' : a.severity === 'HIGH' ? '#ffffcc' : '#f0f0f0'}">
      <td style="padding: 10px; border: 1px solid #ddd;">${emoji[a.severity]} ${a.severity}</td>
      <td style="padding: 10px; border: 1px solid #ddd;">${a.category}</td>
      <td style="padding: 10px; border: 1px solid #ddd;">${a.message}</td>
    </tr>
    `).join('')}
  </table>
  
  ${critical.length > 0 ? `
  <div style="background: #ff0000; color: white; padding: 15px; margin: 20px 0;">
    <strong>🚨 AÇÃO CRÍTICA IGEDIATA NECESSÁRIA</strong>
    <p>${critical.length} alerta(s) crítico(s) detectado(s).</p>
  </div>
  ` : ''}
  
  <p style="color: #666; font-size: 12px;">
    Gerado automaticamente por Orkestra Finance Brain
  </p>
</body>
</html>
`;

    return {
      whatsapp,
      email,
      count: alerts.length,
      hasCritical: critical.length > 0
    };
  }

  /**
   * Avalia contexto operacional (estoque, capacidade, margem, reconciliação)
   * e retorna alertas acionáveis. Independente do fluxo de eventos acima.
   */
  evaluateOperational(ctx: OperationalContext): TriggeredAlert[] {
    const out: TriggeredAlert[] = [];

    // 1) Estoque — shortage & near-safety
    for (const s of ctx.stock ?? []) {
      const deficit = s.required - s.onHand;
      if (deficit > 0) {
        const coverage = s.onHand / Math.max(s.required, 1);
        const severity: AlertRule["severity"] =
          coverage < 0.5 ? "CRITICAL" : coverage < 0.8 ? "HIGH" : "MEDIUM";
        out.push({
          rule: "ESTOQUE_INSUFICIENTE",
          severity,
          category: "INVENTORY",
          message: `Estoque insuficiente: ${s.itemName} (${s.onHand}/${s.required} ${s.itemCode}) — faltam ${deficit.toFixed(2)}`,
          details: {
            itemCode: s.itemCode,
            onHand: s.onHand,
            required: s.required,
            deficit,
            coveragePct: Number((coverage * 100).toFixed(1)),
          },
        });
      } else if (s.safetyStock && s.onHand - s.required < s.safetyStock) {
        out.push({
          rule: "ESTOQUE_PROX_SEGURANCA",
          severity: "LOW",
          category: "INVENTORY",
          message: `Estoque próximo do limite de segurança: ${s.itemName} (safety=${s.safetyStock})`,
          details: { itemCode: s.itemCode, onHand: s.onHand, safetyStock: s.safetyStock },
        });
      }
    }

    // 2) Produção — station overload
    for (const st of ctx.stations ?? []) {
      if (st.capacityHours <= 0) continue;
      const util = st.loadHours / st.capacityHours;
      if (util > 1.2) {
        out.push({
          rule: "PRODUCAO_SOBRECARGA_CRITICA",
          severity: "CRITICAL",
          category: "PRODUCTION",
          message: `Estação ${st.stationName} sobrecarregada: ${(util * 100).toFixed(0)}% (${st.loadHours.toFixed(1)}h / ${st.capacityHours.toFixed(1)}h)`,
          details: {
            stationId: st.stationId,
            loadHours: st.loadHours,
            capacityHours: st.capacityHours,
            utilizationPct: Number((util * 100).toFixed(1)),
          },
        });
      } else if (util > 1.0) {
        out.push({
          rule: "PRODUCAO_SOBRECARGA",
          severity: "HIGH",
          category: "PRODUCTION",
          message: `Estação ${st.stationName} acima da capacidade: ${(util * 100).toFixed(0)}%`,
          details: {
            stationId: st.stationId,
            loadHours: st.loadHours,
            capacityHours: st.capacityHours,
            utilizationPct: Number((util * 100).toFixed(1)),
          },
        });
      } else if (util > 0.9) {
        out.push({
          rule: "PRODUCAO_PROX_CAPACIDADE",
          severity: "MEDIUM",
          category: "PRODUCTION",
          message: `Estação ${st.stationName} próxima do limite: ${(util * 100).toFixed(0)}%`,
          details: {
            stationId: st.stationId,
            loadHours: st.loadHours,
            capacityHours: st.capacityHours,
            utilizationPct: Number((util * 100).toFixed(1)),
          },
        });
      }
    }

    // 3) Margem projetada (após reconciliação)
    if (ctx.margin) {
      const { projectedPct, realPct, deltaPct } = ctx.margin;
      if (realPct !== null && realPct !== undefined && realPct < 15) {
        out.push({
          rule: "MARGEM_REAL_CRITICA",
          severity: "CRITICAL",
          category: "FINANCE",
          message: `Margem real crítica: ${realPct.toFixed(1)}% (<15%)`,
          details: { realPct, projectedPct, deltaPct },
        });
      } else if (realPct !== null && realPct !== undefined && realPct < 20) {
        out.push({
          rule: "MARGEM_REAL_BAIXA",
          severity: "HIGH",
          category: "FINANCE",
          message: `Margem real abaixo do alvo: ${realPct.toFixed(1)}% (<20%)`,
          details: { realPct, projectedPct, deltaPct },
        });
      }
      if (deltaPct !== null && deltaPct !== undefined && deltaPct <= -5) {
        out.push({
          rule: "MARGEM_DESVIO",
          severity: "HIGH",
          category: "FINANCE",
          message: `Margem real caiu ${Math.abs(deltaPct).toFixed(1)}pp vs projeção`,
          details: { realPct, projectedPct, deltaPct },
        });
      }
    }

    // 4) Reconciliação — variâncias elevadas sistêmicas
    if (ctx.reconciliation) {
      const hv = ctx.reconciliation.highVariances ?? [];
      if (hv.length >= 3) {
        out.push({
          rule: "RECONCILIACAO_VARIANCIA_ALTA",
          severity: "MEDIUM",
          category: "OPERATIONS",
          message: `${hv.length} itens com variância >25% — ajuste de forecast recomendado`,
          details: { items: hv.slice(0, 8) },
        });
      }
      if (
        typeof ctx.reconciliation.overallAccuracyScore === "number" &&
        ctx.reconciliation.overallAccuracyScore < 0.6
      ) {
        out.push({
          rule: "FORECAST_ACCURACY_BAIXA",
          severity: "MEDIUM",
          category: "OPERATIONS",
          message: `Accuracy geral ${(ctx.reconciliation.overallAccuracyScore * 100).toFixed(0)}% — revisar parâmetros`,
          details: { overallAccuracyScore: ctx.reconciliation.overallAccuracyScore },
        });
      }
    }

    return out;
  }

  /**
   * Converte alertas para payloads de notificação e envia via dispatcher.
   * Cada alerta vira uma notificação independente — ordem por severidade.
   */
  async dispatchAlerts(
    alerts: TriggeredAlert[],
    ctx?: { tenantId?: string; eventId?: string }
  ): Promise<ChannelDeliveryResult[]> {
    if (!alerts.length) return [];

    const rank: Record<string, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
    const ordered = [...alerts].sort(
      (a, b) => (rank[a.severity] ?? 9) - (rank[b.severity] ?? 9)
    );

    const all: ChannelDeliveryResult[] = [];
    for (const a of ordered) {
      const payload: NotificationPayload = {
        title: `${a.category} — ${a.rule}`,
        body: a.message,
        severity: a.severity as ChannelSeverity,
        category: a.category,
        tenantId: ctx?.tenantId,
        eventId: ctx?.eventId,
        metadata: a.details,
      };
      const res = await notificationDispatcher.dispatch(payload);
      all.push(...res);
    }
    return all;
  }

  /**
   * Obtém alertas recentes de um run
   */
  async getRunAlerts(agentRunId: string): Promise<any[]> {
    try {
      const memories = await prisma.memoryItem.findMany({
        where: {
          memoryType: "alert",
          sourceRef: agentRunId
        },
        orderBy: { createdAt: "desc" }
      });
      return memories;
    } catch {
      return [];
    }
  }
}

// Singleton
export const alertEngine = new AlertEngine();
