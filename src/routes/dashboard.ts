import { FastifyInstance } from "fastify";

export async function dashboardRoutes(app: FastifyInstance) {
  // GET /dashboard/ceo
  app.get("/ceo", async () => ({
    type: "ceo",
    title: "CEO Dashboard - Visão Estratégica",
    summary: {
      totalRevenue: 58000,
      totalProfit: 12000,
      avgMargin: 25.5,
      totalEvents: 4,
    },
    kpis: [
      { name: "Receita Total", value: 58000, formatted: "R$ 58.000,00" },
      { name: "Margem Média", value: 25.5, formatted: "25.5%" },
    ],
    alerts: [
      { level: "high", message: "2 eventos com margem crítica" },
    ],
  }));

  // GET /dashboard/commercial
  app.get("/commercial", async () => ({
    type: "commercial",
    title: "Sales Dashboard",
    summary: {
      ticketMedio: 14500,
      taxaConversao: 75.5,
      eventosEmRisco: 2,
    },
    kpis: [
      { name: "Ticket Médio", value: 14500, formatted: "R$ 14.500,00" },
      { name: "Taxa Conversão", value: 75.5, formatted: "75.5%" },
    ],
  }));

  // GET /dashboard/finance
  app.get("/finance", async () => ({
    type: "finance",
    title: "Finance Dashboard - DRE e Consistência",
    summary: {
      totalCMV: 41000,
      margemMedia: 24.8,
      inconsistencias: 1,
    },
    kpis: [
      { name: "CMV Total", value: 41000, formatted: "R$ 41.000,00" },
      { name: "Margem Média", value: 24.8, formatted: "24.8%" },
    ],
  }));

  // GET /dashboard/operations
  app.get("/operations", async () => ({
    type: "operations",
    title: "Ops Dashboard - Produção",
    summary: {
      desperdicioMedio: 8.5,
      itensCriticos: 3,
      eficiencia: 91.5,
    },
    kpis: [
      { name: "Desperdício", value: 8.5, formatted: "8.5%" },
      { name: "Eficiência", value: 91.5, formatted: "91.5%" },
    ],
  }));
}
