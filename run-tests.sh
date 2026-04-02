#!/bin/bash
# Script para executar testes automatizados

echo "=============================================="
echo "EXECUTANDO TESTES - OPENCLAW API"
echo "=============================================="

# Verificar se está no diretório correto
cd ~/.openclaw/workspace-openclaw-bpo

echo ""
echo "[1/3] Executando testes do Jest..."
npm test -- --testPathPattern="agent-run-flow" --verbose 2>&1 | tail -50

echo ""
echo "[2/3] Verificando cobertura..."
npm run test:coverage 2>&1 | grep -E "Test Suites|Tests|Coverage" || echo "Cobertura não disponível"

echo ""
echo "[3/3] Testando typecheck..."
npm run typecheck 2>&1 | tail -20

echo ""
echo "=============================================="
echo "TESTES CONCLUÍDOS!"
echo "=============================================="
