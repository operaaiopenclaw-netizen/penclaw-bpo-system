/**
 * Importa os 161 ingredientes do evento "Aniversário 15 anos Yohanna"
 * para a tabela inventory_items com os preços estimados de Curitiba.
 *
 * Uso: npx ts-node scripts/import_yohanna_inventory.ts [--dry-run]
 */
import { PrismaClient } from "@prisma/client";
import * as fs from "fs";
import * as path from "path";

const prisma = new PrismaClient();
const DRY_RUN = process.argv.includes("--dry-run");

// Prefixo de código por unidade/categoria
function buildCode(name: string, index: number): string {
  const n = name.toLowerCase();
  let prefix = "ING";
  if (n.includes("queijo") || n.includes("burrata") || n.includes("stracciatella")) prefix = "LAT";
  else if (n.includes("carne") || n.includes("bovino") || n.includes("acém") || n.includes("peito") || n.includes("músculo")) prefix = "CAR";
  else if (n.includes("frango")) prefix = "AVI";
  else if (n.includes("sashimi") || n.includes("sushi") || n.includes("nigiri") || n.includes("atum") || n.includes("salmão")) prefix = "PEI";
  else if (n.includes("água") || n.includes("refrigerante") || n.includes("vinho") || n.includes("leite") && n.includes("l")) prefix = "BEV";
  else if (n.includes("tomate") || n.includes("cenoura") || n.includes("cebola") || n.includes("brócolis") ||
           n.includes("abobrinha") || n.includes("beterraba") || n.includes("berinjela") || n.includes("pepino") ||
           n.includes("acelga") || n.includes("repolho") || n.includes("salsão") || n.includes("salsinha") ||
           n.includes("hortelã") || n.includes("manjericão") || n.includes("ciboulette")) prefix = "HOR";
  else if (n.includes("morango") || n.includes("manga") || n.includes("limão") || n.includes("laranja") ||
           n.includes("abacaxi") || n.includes("mirtilo") || n.includes("framboesa") || n.includes("uva") ||
           n.includes("pêssego") || n.includes("goiaba")) prefix = "FRU";
  else if (n.includes("pão") || n.includes("massa") || n.includes("farinha") || n.includes("brioche") ||
           n.includes("focaccia") || n.includes("grissini") || n.includes("torrada")) prefix = "PAD";
  else if (n.includes("parma") || n.includes("coppa") || n.includes("salame") || n.includes("pancetta") ||
           n.includes("linguiça") || n.includes("lombo")) prefix = "FRI";
  else if (n.includes("sorvete") || n.includes("chocolate") || n.includes("gelatina") || n.includes("açúcar") ||
           n.includes("leite condensado") || n.includes("baunilha")) prefix = "CON";
  else if (n.includes("azeite") || n.includes("óleo") || n.includes("vinagre") || n.includes("molho")) prefix = "CON";

  const seq = String(index).padStart(3, "0");
  const abbr = name.replace(/[^a-zA-ZÀ-ÿ]/g, "").slice(0, 3).toUpperCase();
  return `${prefix}-${abbr}-${seq}`;
}

interface CmvIngredient {
  name: string;
  qty: number;
  unit: string;
  price_per_unit: number;
  total_cost: number;
  confidence: string;
  notes: string;
}

async function main() {
  const cmvPath = path.join(__dirname, "../kitchen_data/yohanna_cmv_estimate.json");
  const cmvData = JSON.parse(fs.readFileSync(cmvPath, "utf-8"));
  const ingredients: CmvIngredient[] = cmvData.ingredients;

  console.log(`\nImportando ${ingredients.length} ingredientes para inventory_items...`);
  if (DRY_RUN) console.log("  [DRY-RUN] Nenhuma escrita no banco.\n");

  // Get existing codes to avoid collision
  const existing = await prisma.inventoryItem.findMany({ select: { code: true, name: true } });
  const existingNames = new Set(existing.map((e) => e.name.toLowerCase()));
  const existingCodes = new Set(existing.map((e) => e.code));

  let created = 0;
  let updated = 0;
  let skipped = 0;

  for (let i = 0; i < ingredients.length; i++) {
    const ing = ingredients[i];
    const nameLower = ing.name.toLowerCase();

    // Try to find existing by name (case-insensitive match)
    const existingItem = existing.find(
      (e) => e.name.toLowerCase() === nameLower ||
             e.name.toLowerCase().includes(nameLower) ||
             nameLower.includes(e.name.toLowerCase())
    );

    // Normalize unit to uppercase
    const unit = ing.unit.toUpperCase();

    if (existingItem && !DRY_RUN) {
      // Update price only if existing
      await prisma.inventoryItem.update({
        where: { code: existingItem.code },
        data: { unitPrice: ing.price_per_unit }
      });
      updated++;
      console.log(`  ~ UPDATED: ${ing.name} → R$${ing.price_per_unit}/${unit}`);
    } else if (!existingNames.has(nameLower)) {
      // Generate unique code
      let code = buildCode(ing.name, i + 1);
      let attempt = 0;
      while (existingCodes.has(code)) {
        attempt++;
        code = buildCode(ing.name, i + 1 + attempt * 100);
      }
      existingCodes.add(code);

      const payload = {
        code,
        name: ing.name,
        unit,
        unitPrice: ing.price_per_unit,
        currentQty: 0,
        minStockLevel: 0,
        reorderPoint: 0,
        supplier: "A definir — estimativa Curitiba/PR Abr 2026",
        entryHistory: []
      };

      if (!DRY_RUN) {
        await prisma.inventoryItem.create({ data: payload });
      }
      created++;
      if (created <= 20 || ing.price_per_unit >= 50) {
        console.log(`  + CREATE: [${code}] ${ing.name} — R$${ing.price_per_unit}/${unit}  (${ing.confidence})`);
      }
    } else {
      skipped++;
    }
  }

  // Summary
  const total = await prisma.inventoryItem.count();
  console.log(`\n${"=".repeat(55)}`);
  console.log(`  Criados:    ${created}`);
  console.log(`  Atualizados: ${updated}`);
  console.log(`  Ignorados:  ${skipped} (já existiam com nome similar)`);
  console.log(`  Total inventory_items agora: ${total}`);
  console.log(`${"=".repeat(55)}\n`);

  // Verification: top 5 highest unit price in DB
  const top5 = await prisma.inventoryItem.findMany({
    orderBy: { unitPrice: "desc" },
    take: 5,
    select: { code: true, name: true, unitPrice: true, unit: true }
  });
  console.log("  Top 5 por preço unitário:");
  top5.forEach((r) => console.log(`    ${r.code} | ${r.name} — R$${r.unitPrice}/${r.unit}`));
}

main()
  .catch((e) => { console.error(e); process.exit(1); })
  .finally(() => prisma.$disconnect());
