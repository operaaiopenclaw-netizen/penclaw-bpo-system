// ============================================================
// PRISMA SEED
// Dados iniciais para o banco
// ============================================================

import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  console.log('🌱 Seeding database...')

  // 1. Seed Domain Rules
  console.log('  📋 Domain Rules...')
  await prisma.domainRule.createMany({
    data: [
      {
        domain: 'financial',
        ruleName: 'margin_threshold',
        ruleDescription: 'Margem mínima aceitável de 20%',
        ruleLogic: { minMargin: 20 },
        priority: 10
      },
      {
        domain: 'financial',
        ruleName: 'variance_limit',
        ruleDescription: 'Limite de variação CMV vs Estoque: 5%',
        ruleLogic: { maxVariance: 5 },
        priority: 20
      },
      {
        domain: 'kitchen',
        ruleName: 'recipe_validation',
        ruleDescription: 'Validação obrigatória de campos da receita',
        ruleLogic: { requiredFields: ['name', 'yield', 'ingredients'] },
        priority: 10
      },
      {
        domain: 'procurement',
        ruleName: 'stock_alert',
        ruleDescription: 'Alerta quando estoque < 7 dias',
        ruleLogic: { minDays: 7 },
        priority: 30
      },
      {
        domain: 'audit',
        ruleName: 'consistency_check',
        ruleDescription: 'Verificação de consistência de dados',
        ruleLogic: { maxDiff: 5 },
        priority: 10
      },
      {
        domain: 'general',
        ruleName: 'logging_mandatory',
        ruleDescription: 'Logging obrigatório para todas as ações',
        ruleLogic: { required: true },
        priority: 1
      },
      {
        domain: 'general',
        ruleName: 'policy_check',
        ruleDescription: 'Verificação de políticas antes de execução',
        ruleLogic: { required: true },
        priority: 1
      }
    ],
    skipDuplicates: true
  })

  // 2. Seed Recipes (exemplo)
  console.log('  🍳 Recipes...')
  await prisma.recipe.createMany({
    data: [
      {
        recipeId: 'REC001',
        name: 'Escondidinho de Carne Seca',
        category: 'principal',
        yield: 15,
        prepTimeMin: 90,
        complexity: 'medium',
        ingredients: JSON.stringify([
          { code: 'CAR-001', name: 'Carne Seca Desfiada', qty: 0.120, unit: 'kg' },
          { code: 'LEG-001', name: 'Mandioca Cozida', qty: 0.150, unit: 'kg' },
          { code: 'LAZ-001', name: 'Manteiga', qty: 0.010, unit: 'kg' },
          { code: 'QUE-001', name: 'Queijo Coalho Ralado', qty: 0.030, unit: 'kg' }
        ]),
        costPerServing: 0,
        instructions: 'Refogar carne -> Amassar mandioca -> Montar camadas -> Gratinar'
      },
      {
        recipeId: 'REC002',
        name: 'Salada Caesar com Frango',
        category: 'entrada',
        yield: 20,
        prepTimeMin: 25,
        complexity: 'low',
        ingredients: JSON.stringify([
          { code: 'FRG-001', name: 'Peito de Frango Grelhado', qty: 0.100, unit: 'kg' },
          { code: 'VEG-001', name: 'Alface Americana', qty: 0.080, unit: 'kg' },
          { code: 'MOL-001', name: 'Molho Caesar', qty: 0.030, unit: 'kg' }
        ]),
        costPerServing: 0
      },
      {
        recipeId: 'REC003',
        name: 'Mini Hamburguer Premium',
        category: 'finger_food',
        yield: 25,
        prepTimeMin: 45,
        complexity: 'medium',
        ingredients: JSON.stringify([
          { code: 'CAR-002', name: 'Blend Hamburguer', qty: 0.080, unit: 'kg' },
          { code: 'PAO-002', name: 'Mini Pao Brioche', qty: 1, unit: 'un' },
          { code: 'VEG-003', name: 'Tomate Cereja', qty: 0.010, unit: 'kg' }
        ]),
        costPerServing: 0
      },
      {
        recipeId: 'REC004',
        name: 'Ceviche de Peixe Branco',
        category: 'entrada',
        yield: 12,
        prepTimeMin: 20,
        complexity: 'high',
        ingredients: JSON.stringify([
          { code: 'PEI-001', name: 'File Peixe Branco', qty: 0.100, unit: 'kg' },
          { code: 'FRU-001', name: 'Limao Taiti', qty: 0.060, unit: 'kg' },
          { code: 'VEG-004', name: 'Cebola Roxa', qty: 0.020, unit: 'kg' }
        ]),
        costPerServing: 0
      },
      {
        recipeId: 'REC005',
        name: 'Arroz com Brócolis',
        category: 'acompanhamento',
        yield: 30,
        prepTimeMin: 40,
        complexity: 'low',
        ingredients: JSON.stringify([
          { code: 'GRA-001', name: 'Arroz Agulhinha', qty: 0.080, unit: 'kg' },
          { code: 'VEG-002', name: 'Brócolis Fresco', qty: 0.050, unit: 'kg' },
          { code: 'LAZ-002', name: 'Azeite Extra Virgem', qty: 0.005, unit: 'kg' }
        ]),
        costPerServing: 0
      }
    ],
    skipDuplicates: true
  })

  // 3. Seed Inventory (exemplo)
  console.log('  📦 Inventory Items...')
  await prisma.inventoryItem.createMany({
    data: [
      { code: 'CAR-001', name: 'Carne Seca Desfiada', currentQty: 50.5, unit: 'kg', unitPrice: 45.00, supplier: 'Açougue Modelo' },
      { code: 'LEG-001', name: 'Mandioca Cozida', currentQty: 30.0, unit: 'kg', unitPrice: 12.50, supplier: 'Hortifruti Central' },
      { code: 'LAZ-001', name: 'Manteiga', currentQty: 10.0, unit: 'kg', unitPrice: 35.00, supplier: 'Laticínios Sul' },
      { code: 'QUE-001', name: 'Queijo Coalho Ralado', currentQty: 15.0, unit: 'kg', unitPrice: 58.00, supplier: 'Queijaria Artesanal' },
      { code: 'FRG-001', name: 'Peito de Frango Grelhado', currentQty: 25.0, unit: 'kg', unitPrice: 28.00, supplier: 'Avícola Norte' },
      { code: 'VEG-001', name: 'Alface Americana', currentQty: 8.0, unit: 'kg', unitPrice: 6.50, supplier: 'Hortifruti Central' },
      { code: 'PAO-002', name: 'Mini Pao Brioche', currentQty: 200, unit: 'un', unitPrice: 1.20, supplier: 'Padaria Premium' },
      { code: 'PEI-001', name: 'File Peixe Branco', currentQty: 12.0, unit: 'kg', unitPrice: 85.00, supplier: 'Pescados Mar' }
    ],
    skipDuplicates: true
  })

  // 4. Seed Workflow Types
  console.log('  🔄 Workflow Types...')
  await prisma.workflowType.createMany({
    data: [
      { id: 'KITCHEN', name: 'Kitchen Control', description: 'Custos e produção' },
      { id: 'FINANCIAL', name: 'Financial', description: 'DRE, margens e rateios' },
      { id: 'PROCUREMENT', name: 'Procurement', description: 'Compras e estoque' },
      { id: 'PRICING', name: 'Pricing', description: 'Precificação e análise' },
      { id: 'AUDIT', name: 'Audit', description: 'Auditoria e validação' },
      { id: 'CALIBRATION', name: 'Calibration', description: 'Calibração do sistema' },
      { id: 'REPORTING', name: 'Reporting', description: 'Relatórios executivos' },
      { id: 'RECONCILIATION', name: 'Reconciliation', description: 'Sistema vs Real' },
      { id: 'FULL_PIPELINE', name: 'Full Pipeline', description: 'Pipeline completo' }
    ],
    skipDuplicates: true
  })

  // 5. Seed Risk Levels
  console.log('  ⚠️  Risk Levels...')
  await prisma.riskLevel.createMany({
    data: [
      { id: 'NONE', name: 'Sem Risco', minValue: 0, maxValue: 0 },
      { id: 'LOW', name: 'Risco Baixo', minValue: 1, maxValue: 1 },
      { id: 'MEDIUM', name: 'Risco Médio', minValue: 2, maxValue: 2 },
      { id: 'HIGH', name: 'Risco Alto', minValue: 3, maxValue: 3 },
      { id: 'CRITICAL', name: 'Risco Crítico', minValue: 4, maxValue: 4 }
    ],
    skipDuplicates: true
  })

  console.log('✅ Seed completed!')
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
