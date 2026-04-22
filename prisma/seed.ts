// ============================================================
// ORKESTRA.AI — SEED REALÍSTICO v2.0
// 3 empresas: QOpera / Laohana / Robusta
// Dados: fornecedores, estoque, eventos, leads, histórico de consumo
// ============================================================
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

// ---- Tenant IDs fixos ----
const TENANTS = {
  qopera:  "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  laohana: "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  robusta: "c3d4e5f6-a7b8-9012-cdef-123456789012",
};

// ---- Stable UUIDs for seeded entities ----
const IDS = {
  // Cost centers
  ccQopera:  "cc000001-0000-0000-0000-000000000001",
  ccLaohana: "cc000001-0000-0000-0000-000000000002",
  // Events
  evt001: "e0000001-0000-0000-0000-000000000001",
  evt002: "e0000001-0000-0000-0000-000000000002",
  evt003: "e0000001-0000-0000-0000-000000000003",
  evt004: "e0000001-0000-0000-0000-000000000004",
  evt005: "e0000001-0000-0000-0000-000000000005",
  // Leads
  lead001: "1ead0001-0000-0000-0000-000000000001",
  lead002: "1ead0001-0000-0000-0000-000000000002",
  lead003: "1ead0001-0000-0000-0000-000000000003",
  lead004: "1ead0001-0000-0000-0000-000000000004",
  lead005: "1ead0001-0000-0000-0000-000000000005",
  // Proposal + Contract + Client
  client001:   "c11e0001-0000-0000-0000-000000000001",
  proposal001: "b0000001-0000-0000-0000-000000000001",
  contract001: "d0000001-0000-0000-0000-000000000001",
};

// ---- Datas helper ----
const daysFromNow = (d: number) => new Date(Date.now() + d * 86_400_000);

async function main() {
  console.log("🌱 Orkestra Seed v2.0 — iniciando...\n");

  await seedSuppliers();
  await seedInventory();
  await seedEvents();
  await seedLeads();
  await seedConsumptionHistory();
  await seedProposalAndContract();

  console.log("\n✅ Seed concluído. Sistema pronto para testes operacionais.");
}

// ============================================================
// FORNECEDORES
// ============================================================
async function seedSuppliers() {
  console.log("📦 Criando fornecedores...");

  const suppliers = [
    {
      id: "sup-001",
      tenantId: TENANTS.qopera,
      name: "Distribuidora Paulista de Bebidas",
      code: "DPB-001",
      contactEmail: "vendas@dpb.com.br",
      contactPhone: "(11) 3333-4444",
      categories: ["beverage_alcohol", "beverage_soft", "beverage_water", "beverage_spirit"],
      isActive: true,
      leadTimeDays: 2,
    },
    {
      id: "sup-002",
      tenantId: TENANTS.qopera,
      name: "Frigorífico Nobre Carnes",
      code: "FNC-001",
      contactEmail: "compras@frigorificonobre.com.br",
      contactPhone: "(11) 4444-5555",
      categories: ["meat", "protein", "food"],
      isActive: true,
      leadTimeDays: 1,
    },
    {
      id: "sup-003",
      tenantId: TENANTS.qopera,
      name: "Hortifruti Premium SP",
      code: "HPS-001",
      contactEmail: "pedidos@hortifrutipremium.com.br",
      contactPhone: "(11) 5555-6666",
      categories: ["vegetable", "fruit", "fresh", "food"],
      isActive: true,
      leadTimeDays: 1,
    },
    {
      id: "sup-004",
      tenantId: TENANTS.qopera,
      name: "Laticínios Fazenda Bela Vista",
      code: "LFB-001",
      contactEmail: "vendas@fbv.com.br",
      contactPhone: "(11) 6666-7777",
      categories: ["dairy", "food"],
      isActive: true,
      leadTimeDays: 2,
    },
    {
      id: "sup-005",
      tenantId: TENANTS.qopera,
      name: "Descartáveis & Utilidades BR",
      code: "DUB-001",
      contactEmail: "comercial@dubr.com.br",
      contactPhone: "(11) 7777-8888",
      categories: ["consumable", "disposable", "equipment"],
      isActive: true,
      leadTimeDays: 3,
    },
    {
      id: "sup-006",
      tenantId: TENANTS.qopera,
      name: "Espumantes & Vinhos Especiais",
      code: "EVE-001",
      contactEmail: "somm@evespeciais.com.br",
      contactPhone: "(11) 8888-9999",
      categories: ["beverage_alcohol", "beverage_spirit"],
      isActive: true,
      leadTimeDays: 5,
    },
  ];

  for (const s of suppliers) {
    await prisma.supplier.upsert({
      where: { id: s.id },
      create: s,
      update: s,
    });
  }

  // Pedidos históricos para scoring de fornecedores
  const now = new Date();
  const poHistory = [
    // sup-001 (bebidas) — excelente histórico
    ...Array.from({ length: 15 }, (_, i) => ({
      tenantId: TENANTS.qopera,
      supplierId: "sup-001",
      status: "delivered",
      totalEstimatedCost: 2500 + i * 180,
      totalActualCost: 2480 + i * 175,
      requestedDelivery: new Date(now.getTime() - (i + 1) * 12 * 86_400_000),
      confirmedDelivery: new Date(now.getTime() - (i + 1) * 12 * 86_400_000),
      actualDelivery: new Date(now.getTime() - (i + 1) * 12 * 86_400_000 + 3_600_000),
    })),
    // sup-002 (carnes) — bom, 1 atraso
    ...Array.from({ length: 8 }, (_, i) => ({
      tenantId: TENANTS.qopera,
      supplierId: "sup-002",
      status: "delivered",
      totalEstimatedCost: 4200 + i * 300,
      totalActualCost: 4350 + i * 290,
      requestedDelivery: new Date(now.getTime() - (i + 2) * 10 * 86_400_000),
      confirmedDelivery: new Date(now.getTime() - (i + 2) * 10 * 86_400_000),
      actualDelivery: i === 3
        ? new Date(now.getTime() - (i + 2) * 10 * 86_400_000 + 2 * 86_400_000) // atraso
        : new Date(now.getTime() - (i + 2) * 10 * 86_400_000 + 1_800_000),
    })),
    // sup-005 (descartáveis) — score médio, tendência de alta de preço
    ...Array.from({ length: 6 }, (_, i) => ({
      tenantId: TENANTS.qopera,
      supplierId: "sup-005",
      status: i === 5 ? "cancelled" : "delivered",
      totalEstimatedCost: 800 + i * 120,
      totalActualCost: 850 + i * 160, // preço subindo
      requestedDelivery: new Date(now.getTime() - (i + 1) * 20 * 86_400_000),
      confirmedDelivery: new Date(now.getTime() - (i + 1) * 20 * 86_400_000),
      actualDelivery: i < 5 ? new Date(now.getTime() - (i + 1) * 20 * 86_400_000 + 7_200_000) : null,
    })),
  ];

  for (const po of poHistory) {
    await prisma.purchaseOrder.create({ data: po as Parameters<typeof prisma.purchaseOrder.create>[0]["data"] });
  }

  console.log(`   ✓ ${suppliers.length} fornecedores + ${poHistory.length} pedidos históricos`);
}

// ============================================================
// ESTOQUE
// ============================================================
async function seedInventory() {
  console.log("📊 Criando itens de estoque...");

  const items = [
    // Bebidas — estoque propositalmente baixo para disparar procurement
    { code: "BEV-CER-001", name: "Cerveja Long Neck 600ml",   currentQty: 48,   unit: "L",   unitPrice: 12.50, minStockLevel: 80,  reorderPoint: 100, supplier: "sup-001" },
    { code: "BEV-SOF-001", name: "Refrigerante 2L",           currentQty: 120,  unit: "L",   unitPrice: 6.80,  minStockLevel: 60,  reorderPoint: 80,  supplier: "sup-001" },
    { code: "BEV-AGU-001", name: "Água Mineral 500ml",        currentQty: 200,  unit: "L",   unitPrice: 3.20,  minStockLevel: 100, reorderPoint: 150, supplier: "sup-001" },
    { code: "BEV-DES-001", name: "Destilado Premium",         currentQty: 8,    unit: "L",   unitPrice: 95.00, minStockLevel: 15,  reorderPoint: 20,  supplier: "sup-006" },
    { code: "BEV-ESP-001", name: "Espumante Brut",            currentQty: 18,   unit: "L",   unitPrice: 58.00, minStockLevel: 10,  reorderPoint: 15,  supplier: "sup-006" },
    { code: "BEV-SUC-001", name: "Suco Natural 1L",           currentQty: 30,   unit: "L",   unitPrice: 8.50,  minStockLevel: 20,  reorderPoint: 30,  supplier: "sup-001" },
    { code: "CON-GEL-001", name: "Gelo em Cubo (saco 5kg)",   currentQty: 35,   unit: "kg",  unitPrice: 2.80,  minStockLevel: 40,  reorderPoint: 60,  supplier: "sup-001" },
    // Proteínas
    { code: "CAR-BOV-001", name: "Picanha Bovina",            currentQty: 12,   unit: "kg",  unitPrice: 89.00, minStockLevel: 20,  reorderPoint: 30,  supplier: "sup-002" },
    { code: "CAR-FRA-001", name: "Filé de Frango",            currentQty: 28,   unit: "kg",  unitPrice: 22.00, minStockLevel: 30,  reorderPoint: 45,  supplier: "sup-002" },
    { code: "CAR-PEI-001", name: "Salmão Fresco",             currentQty: 5,    unit: "kg",  unitPrice: 145.00, minStockLevel: 8,  reorderPoint: 12,  supplier: "sup-002" },
    // Hortifruti
    { code: "HOR-SAL-001", name: "Mix de Folhas",             currentQty: 4,    unit: "kg",  unitPrice: 18.00, minStockLevel: 8,  reorderPoint: 12,  supplier: "sup-003" },
    { code: "HOR-TOM-001", name: "Tomate Italiano",           currentQty: 9,    unit: "kg",  unitPrice: 12.00, minStockLevel: 10, reorderPoint: 15,  supplier: "sup-003" },
    // Laticínios
    { code: "LAT-QUE-001", name: "Queijo Minas Frescal",      currentQty: 6,    unit: "kg",  unitPrice: 38.00, minStockLevel: 5,  reorderPoint: 8,   supplier: "sup-004" },
    { code: "LAT-CRE-001", name: "Creme de Leite",            currentQty: 15,   unit: "L",   unitPrice: 14.00, minStockLevel: 10, reorderPoint: 15,  supplier: "sup-004" },
    // Descartáveis
    { code: "DES-PRA-001", name: "Prato Descartável Premium", currentQty: 800,  unit: "un",  unitPrice: 0.85,  minStockLevel: 500, reorderPoint: 800, supplier: "sup-005" },
    { code: "DES-TAL-001", name: "Talher Descartável (kit)",  currentQty: 400,  unit: "kit", unitPrice: 1.20,  minStockLevel: 300, reorderPoint: 500, supplier: "sup-005" },
    { code: "DES-CON-001", name: "Copo Plástico 300ml",       currentQty: 1200, unit: "un",  unitPrice: 0.35,  minStockLevel: 600, reorderPoint: 900, supplier: "sup-005" },
  ];

  for (const item of items) {
    await prisma.inventoryItem.upsert({
      where: { code: item.code },
      create: item,
      update: item,
    });
  }

  console.log(`   ✓ ${items.length} itens de estoque`);
}

// ============================================================
// EVENTOS (próximos 30 dias — variados)
// ============================================================
async function seedEvents() {
  console.log("🎉 Criando eventos...");

  const events = [
    {
      id: IDS.evt001,
      tenantId: TENANTS.qopera,
      costCenterId: IDS.ccQopera,
      eventId: "QOPERA-2026-001",
      name: "Casamento Silva & Rodrigues",
      eventType: "casamento",
      eventDate: daysFromNow(5),
      guests: 280,
      status: "contracted",
      revenueTotal: 185000,
      cmvTotal: 0,
      netProfit: 0,
      marginPct: 0,
    },
    {
      id: IDS.evt002,
      tenantId: TENANTS.qopera,
      costCenterId: IDS.ccQopera,
      eventId: "QOPERA-2026-002",
      name: "Formatura Medicina UNIFESP 2026",
      eventType: "formatura",
      eventDate: daysFromNow(9),
      guests: 450,
      status: "contracted",
      revenueTotal: 320000,
      cmvTotal: 0,
      netProfit: 0,
      marginPct: 0,
    },
    {
      id: IDS.evt003,
      tenantId: TENANTS.qopera,
      costCenterId: IDS.ccQopera,
      eventId: "QOPERA-2026-003",
      name: "Confraternização Anual Bradesco",
      eventType: "corporativo",
      eventDate: daysFromNow(12),
      guests: 180,
      status: "planned",
      revenueTotal: 95000,
      cmvTotal: 0,
      netProfit: 0,
      marginPct: 0,
    },
    {
      id: IDS.evt004,
      tenantId: TENANTS.qopera,
      costCenterId: IDS.ccQopera,
      eventId: "QOPERA-2026-004",
      name: "Aniversário 50 anos Dr. Marcelo",
      eventType: "aniversario",
      eventDate: daysFromNow(18),
      guests: 120,
      status: "planned",
      revenueTotal: 68000,
      cmvTotal: 0,
      netProfit: 0,
      marginPct: 0,
    },
    {
      id: IDS.evt005,
      tenantId: TENANTS.laohana,
      costCenterId: IDS.ccLaohana,
      eventId: "LAOHANA-2026-001",
      name: "Workshop Gastronômico Laohana",
      eventType: "corporativo",
      eventDate: daysFromNow(7),
      guests: 60,
      status: "contracted",
      revenueTotal: 28000,
      cmvTotal: 0,
      netProfit: 0,
      marginPct: 0,
    },
  ];

  for (const evt of events) {
    await prisma.event.upsert({
      where: { eventId: evt.eventId },
      create: evt,
      update: { ...evt },
    });
  }

  console.log(`   ✓ ${events.length} eventos (próximos 30 dias)`);
}

// ============================================================
// LEADS (pipeline CRM)
// ============================================================
async function seedLeads() {
  console.log("🎯 Criando leads no pipeline CRM...");

  const leads = [
    {
      id: IDS.lead001,
      tenantId: TENANTS.qopera,
      contactName: "Fernanda Oliveira",
      companyName: "Eventos FO",
      email: "fernanda.oliveira@eventosFO.com.br",
      phone: "(11) 99876-5432",
      source: "instagram",
      status: "QUALIFIED",
      budget: 220000,
      metadata: { eventType: "casamento", numGuests: 350, eventDate: daysFromNow(90).toISOString(), notes: "Casamento temático vintage. Cliente exigente, alto potencial." },
    },
    {
      id: IDS.lead002,
      tenantId: TENANTS.qopera,
      contactName: "Ricardo Mendes",
      companyName: "TechCorp Brasil",
      email: "r.mendes@techcorp.com.br",
      phone: "(11) 3888-9900",
      source: "indicacao",
      status: "CONTACTED",
      budget: 85000,
      metadata: { eventType: "corporativo", numGuests: 200, eventDate: daysFromNow(45).toISOString(), notes: "Evento de lançamento de produto. Decisão até fim do mês." },
    },
    {
      id: IDS.lead003,
      tenantId: TENANTS.qopera,
      contactName: "Patrícia Sousa",
      companyName: null,
      email: "patricia.sousa@gmail.com",
      phone: "(11) 97654-3210",
      source: "site",
      status: "NEW",
      budget: 180000,
      metadata: { eventType: "formatura", numGuests: 400, eventDate: daysFromNow(120).toISOString(), notes: "Formatura de Direito. Orçamento ainda não confirmado." },
    },
    {
      id: IDS.lead004,
      tenantId: TENANTS.qopera,
      contactName: "Carlos Drummond",
      companyName: "Grupo Drummond Investimentos",
      email: "c.drummond@grupodrum.com.br",
      phone: "(11) 3222-1111",
      source: "linkedin",
      status: "PROPOSAL_SENT",
      budget: 95000,
      metadata: { eventType: "aniversario", numGuests: 150, eventDate: daysFromNow(60).toISOString(), notes: "70 anos do fundador. Evento exclusivo, 3 opções de proposta enviadas." },
    },
    {
      id: IDS.lead005,
      tenantId: TENANTS.laohana,
      contactName: "Ana Beatriz Lima",
      companyName: "Studio ABL",
      email: "ana@studioabl.com.br",
      phone: "(11) 94444-3333",
      source: "indicacao",
      status: "QUALIFIED",
      budget: 42000,
      metadata: { eventType: "corporativo", numGuests: 80, eventDate: daysFromNow(55).toISOString(), notes: "Workshop de culinária + jantar gourmet. Já conhece a Laohana." },
    },
  ];

  for (const lead of leads) {
    // Map seed fields to actual schema fields
    const { eventType, estimatedBudget, numGuests, eventDate, notes, ...rest } = lead as any;
    const mapped = {
      ...rest,
      budget: estimatedBudget,
      timeline: eventDate,
      need: eventType,
      metadata: { notes, numGuests } as any,
    };
    await prisma.lead.upsert({
      where: { id: lead.id },
      create: mapped,
      update: mapped,
    });
  }

  console.log(`   ✓ ${leads.length} leads no pipeline`);
}

// ============================================================
// HISTÓRICO DE CONSUMO (alimenta o ForecastEngine)
// ============================================================
async function seedConsumptionHistory() {
  console.log("📈 Criando histórico de consumo para previsões...");

  // Histórico de eventos passados para calibrar o forecast
  const pastEvents = [
    { eventType: "casamento",  guests: 250, date: new Date("2026-03-15") },
    { eventType: "casamento",  guests: 310, date: new Date("2026-02-28") },
    { eventType: "casamento",  guests: 180, date: new Date("2026-01-20") },
    { eventType: "formatura",  guests: 380, date: new Date("2026-03-08") },
    { eventType: "formatura",  guests: 420, date: new Date("2025-12-14") },
    { eventType: "corporativo",guests: 150, date: new Date("2026-04-05") },
    { eventType: "corporativo",guests: 200, date: new Date("2026-03-22") },
    { eventType: "corporativo",guests: 120, date: new Date("2026-02-10") },
    { eventType: "aniversario", guests: 100, date: new Date("2026-04-01") },
    { eventType: "aniversario", guests: 140, date: new Date("2026-02-20") },
  ];

  // Taxas reais observadas (levemente acima/abaixo do modelo base para criar variância)
  const actualRates: Record<string, Record<string, number>> = {
    casamento:   { cerveja: 2.6, soft: 1.4, agua: 0.9, destilado: 0.28, gelo: 1.6, espumante: 0.30, suco: 0.55 },
    formatura:   { cerveja: 3.2, soft: 2.1, agua: 0.75, destilado: 0.45, gelo: 2.2 },
    corporativo: { cerveja: 2.1, soft: 2.6, agua: 2.1, destilado: 0.18, gelo: 1.3, cafe: 0.17 },
    aniversario: { cerveja: 2.9, soft: 1.9, agua: 1.05, destilado: 0.32, gelo: 1.9 },
  };

  const records: Array<{
    tenantId: string; eventId: string; eventType: string; guestCount: number;
    durationHours: number; itemCode: string; itemName: string; category: string;
    quantityConsumed: number; unit: string; perGuestRate: number; recordedAt: Date;
  }> = [];

  const itemMeta: Record<string, { name: string; category: string; unit: string }> = {
    cerveja:   { name: "Cerveja",       category: "beverage_alcohol", unit: "L" },
    soft:      { name: "Refrigerante",  category: "beverage_soft",    unit: "L" },
    agua:      { name: "Água",          category: "beverage_water",   unit: "L" },
    destilado: { name: "Destilado",     category: "beverage_spirit",  unit: "L" },
    gelo:      { name: "Gelo",          category: "consumable",       unit: "kg" },
    espumante: { name: "Espumante",     category: "beverage_alcohol", unit: "L" },
    suco:      { name: "Suco",          category: "beverage_soft",    unit: "L" },
    cafe:      { name: "Café",          category: "beverage_hot",     unit: "L" },
  };

  pastEvents.forEach((evt, idx) => {
    const rates = actualRates[evt.eventType] ?? actualRates["corporativo"];
    const variance = () => 0.92 + Math.random() * 0.18; // ±9% variância
    Object.entries(rates).forEach(([itemCode, baseRate]) => {
      const meta = itemMeta[itemCode];
      if (!meta) return;
      const perGuestRate = baseRate * variance();
      const qty = perGuestRate * evt.guests;
      records.push({
        tenantId: TENANTS.qopera,
        eventId: `past-evt-${idx + 1}`,
        eventType: evt.eventType,
        guestCount: evt.guests,
        durationHours: 6,
        itemCode,
        itemName: meta.name,
        category: meta.category,
        quantityConsumed: Math.round(qty * 10) / 10,
        unit: meta.unit,
        perGuestRate: Math.round(perGuestRate * 10000) / 10000,
        recordedAt: evt.date,
      });
    });
  });

  await prisma.eventConsumptionHistory.createMany({ data: records, skipDuplicates: true });

  console.log(`   ✓ ${records.length} registros de consumo histórico (${pastEvents.length} eventos passados)`);
}

// ============================================================
// PROPOSTA + CONTRATO (para testar o pipeline CRM→Contrato)
// ============================================================
async function seedProposalAndContract() {
  console.log("📝 Criando proposta e contrato de exemplo...");

  const clientId = IDS.client001;
  await prisma.client.upsert({
    where: { id: clientId },
    create: {
      id: clientId,
      tenantId: TENANTS.qopera,
      name: "Silva & Rodrigues Eventos",
      email: "contato@silvarodigues.com.br",
      phone: "(11) 91234-5678",
      document: "123.456.789-00",
    },
    update: {},
  });

  const proposalId = IDS.proposal001;
  await prisma.proposal.upsert({
    where: { id: proposalId },
    create: {
      id: proposalId,
      tenantId: TENANTS.qopera,
      leadId: IDS.lead001,
      proposalNumber: "QOP-PROP-2026-001",
      status: "APPROVED",
      subtotal: 185000,
      taxAmount: 8000,
      totalAmount: 188000,
      validUntil: daysFromNow(30),
      approvedBy: "Fernanda Oliveira",
      approvedAt: new Date("2026-04-10"),
      metadata: {
        eventType: "casamento",
        eventDate: daysFromNow(90).toISOString(),
        numGuests: 350,
        venue: "Espaço Vila Nova",
        clientEmail: "fernanda.oliveira@eventosFO.com.br",
        notes: "Proposta aprovada em reunião 2026-04-10",
      },
      items: {
        create: [
          { itemType: "menu",      name: "Menu Jantar Completo",      description: "Entrada, prato principal, sobremesa", quantity: 350, unit: "pax", unitPrice: 320, totalPrice: 112000 },
          { itemType: "bar",       name: "Open Bar Premium 6h",       description: "Bebidas nacionais e importadas",     quantity: 1,   unit: "vb",  unitPrice: 42000, totalPrice: 42000 },
          { itemType: "structure", name: "Locação de Estrutura",      description: "Tendas, iluminação, som",          quantity: 1,   unit: "vb",  unitPrice: 22000, totalPrice: 22000 },
          { itemType: "staff",     name: "Equipe de Serviço",         description: "30 garçons + 5 supervisores",      quantity: 35,  unit: "pax", unitPrice: 200,  totalPrice: 7000 },
        ],
      },
    },
    update: {},
  });

  await prisma.contract.upsert({
    where: { id: IDS.contract001 },
    create: {
      id: IDS.contract001,
      tenantId: TENANTS.qopera,
      proposalId,
      leadId: IDS.lead001,
      eventId: IDS.evt001,
      contractNumber: "QOP-2026-001",
      status: "ACTIVE",
      totalValue: 188000,
      signedAt: new Date("2026-04-12"),
      signedByClient: "Fernanda Oliveira",
      signedByCompany: "QOpera Gastronomia",
      paymentTerms: "50% entrada + 50% no dia",
      cancellationPolicy: "Cancelamento até 30 dias antes sem multa.",
      metadata: { clientId },
    },
    update: {},
  });

  console.log("   ✓ Cliente + Proposta aprovada + Contrato ativo");
}

main()
  .catch(e => {
    console.error("\n❌ Erro no seed:", e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
