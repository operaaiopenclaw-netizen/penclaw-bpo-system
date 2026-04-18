/**
 * Seeds suppliers for tenant "qopera" covering beverage + consumable categories.
 * Differentiated priceTable / reliability so ranking picks a clear winner per category.
 *
 * Run: npx ts-node scripts/seed_qopera_suppliers.ts
 */
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

const SUPPLIERS = [
  {
    code: "QOP-BEV-001",
    name: "Distribuidora Curitiba Bebidas",
    categories: ["beverage_alcohol", "beverage_soft", "beverage_water"],
    leadTimeDays: 2,
    reliabilityScore: 92,
    minOrderValue: 500,
    priceTable: {
      cerveja: 12.50,
      soft: 8.00,
      agua: 4.50,
      espumante: 45.00,
      suco: 14.00
    }
  },
  {
    code: "QOP-DES-001",
    name: "Destilaria Premium PR",
    categories: ["beverage_spirit", "beverage_alcohol"],
    leadTimeDays: 3,
    reliabilityScore: 88,
    minOrderValue: 1000,
    priceTable: {
      destilado: 95.00,
      cerveja: 14.00
    }
  },
  {
    code: "QOP-CON-001",
    name: "Descartáveis Sul Food Service",
    categories: ["consumable", "equipment", "disposable"],
    leadTimeDays: 2,
    reliabilityScore: 85,
    minOrderValue: 300,
    priceTable: {
      gelo: 3.50,
      consumable: 2.00
    }
  },
  {
    code: "QOP-BEV-002",
    name: "Atacadão Bebidas Curitiba",
    categories: ["beverage_alcohol", "beverage_soft", "beverage_water", "beverage_spirit"],
    leadTimeDays: 4,
    reliabilityScore: 72,
    minOrderValue: 2000,
    priceTable: {
      cerveja: 10.90,
      soft: 6.50,
      agua: 3.90,
      destilado: 89.00
    }
  },
  {
    code: "QOP-GEL-001",
    name: "Gelo Express 24h",
    categories: ["consumable"],
    leadTimeDays: 1,
    reliabilityScore: 95,
    minOrderValue: 100,
    priceTable: {
      gelo: 4.20
    }
  }
];

async function main() {
  console.log("Seeding qopera suppliers...\n");

  let created = 0, updated = 0;

  for (const s of SUPPLIERS) {
    const existing = await prisma.supplier.findFirst({
      where: { tenantId: "qopera", code: s.code }
    });

    if (existing) {
      await prisma.supplier.update({
        where: { id: existing.id },
        data: {
          categories: s.categories,
          leadTimeDays: s.leadTimeDays,
          reliabilityScore: s.reliabilityScore,
          minOrderValue: s.minOrderValue,
          priceTable: s.priceTable,
          isActive: true
        }
      });
      updated++;
      console.log(`  ~ UPDATE ${s.code.padEnd(14)} ${s.name}`);
    } else {
      await prisma.supplier.create({
        data: {
          tenantId: "qopera",
          code: s.code,
          name: s.name,
          categories: s.categories,
          leadTimeDays: s.leadTimeDays,
          reliabilityScore: s.reliabilityScore,
          minOrderValue: s.minOrderValue,
          priceTable: s.priceTable,
          isActive: true
        }
      });
      created++;
      console.log(`  + CREATE ${s.code.padEnd(14)} ${s.name}  cats:${JSON.stringify(s.categories)}  rel:${s.reliabilityScore}%`);
    }
  }

  console.log();
  console.log(`Created: ${created}  Updated: ${updated}`);

  const total = await prisma.supplier.count({ where: { tenantId: "qopera" } });
  console.log(`Total qopera suppliers: ${total}`);
}

main()
  .catch(e => { console.error(e); process.exit(1); })
  .finally(() => prisma.$disconnect());
