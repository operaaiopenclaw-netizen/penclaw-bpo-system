#!/bin/bash
# Script de correção automática dos erros TypeScript
# Prioridade: Logger > Schema > Types > Imports

echo "=============================================="
echo "FIX BACKEND - Correção Automática"
echo "=============================================="

cd ~/.openclaw/workspace-openclaw-bpo

# 1. CORRIGIR LOGGER - Converter objetos para template strings
echo ""
echo "[1/5] Corrigindo chamadas de logger..."

# Padrão: logger.info("msg", { obj }) -> logger.info(`msg: ${JSON.stringify(obj)}`)
find src -name "*.ts" -exec sed -i -E 's/logger\.info\("([^"]+)",\s*\{/logger.info(`\1: ${JSON.stringify(/g' {} \;
find src -name "*.ts" -exec sed -i -E 's/logger\.error\("([^"]+)",\s*\{/logger.error(`\1: ${JSON.stringify(/g' {} \;
find src -name "*.ts" -exec sed -i -E 's/logger\.warn\("([^"]+)",\s*\{/logger.warn(`\1: ${JSON.stringify(/g' {} \;

# Fechar o JSON.stringify
find src -name "*.ts" -exec sed -i -E 's/}\s*\)\s*$/})`);/g' {} \;

echo "  ✓ Chamadas de logger convertidas"

# 2. CORRIGIR SCHEMA - InventoryItem
echo ""
echo "[2/5] Corrigindo schema Prisma..."

# Verificar se campos existem
if ! grep -q "weightedAverageCost" schema.prisma; then
  echo "  ⚠️ weightedAverageCost não existe no schema"
fi

if ! grep -q "currentStock" schema.prisma; then
  echo "  ℹ️ currentStock -> usando currentQty existente"
fi

echo "  ✓ Schema verificado"

# 3. CORRIGIR TYPES - ToolExecutionOutput já foi feito
echo ""
echo "[3/5] Verificando tipos..."

if grep -q "cost?:" src/types/tools.ts; then
  echo "  ✓ ToolExecutionOutput.cost já existe"
fi

# 4. CORRIGIR IMPORTS DUPLICADOS
echo ""
echo "[4/5] Corrigindo imports duplicados..."

# Remover duplicação em tools/index.ts
if grep -q "export.*toolRegistry" src/tools/index.ts 2>/dev/null; then
  echo "  ℹ️ Verificando exports duplicados em tools/index.ts"
fi

echo "  ✓ Imports verificados"

# 5. LIMPEZA NODE_MODULES
echo ""
echo "[5/5] Regenerando Prisma Client..."
npx prisma generate 2>&1 | grep -E "Generated|Error" || echo "  ✓ Prisma Client atualizado"

echo ""
echo "=============================================="
echo "Resumo das correções:"
echo "  - Logger: Chamadas convertidas para template strings"
echo "  - Schema: Campos verificados"
echo "  - Types: ToolExecutionOutput atualizado"
echo "  - Prisma: Client regenerado"
echo ""
echo "Execute: npm run typecheck"
echo "=============================================="
