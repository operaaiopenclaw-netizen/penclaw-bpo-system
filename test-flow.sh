#!/bin/bash
# Script de teste manual do fluxo completo

echo "=============================================="
echo "TESTE DE FLUXO COMPLETO - OPENCLAW API"
echo "=============================================="

BASE_URL="http://localhost:3000"

echo ""
echo "[1/7] Verificando se servidor está rodando..."
if ! curl -s $BASE_URL/health > /dev/null; then
    echo "  ❌ Servidor não está rodando"
    echo "  💡 Execute: npm run dev"
    exit 1
fi

echo "  ✅ Servidor OK"

echo ""
echo "[2/7] Testando health check..."
curl -s $BASE_URL/health | jq .

echo ""
echo "[3/7] Criando agent run (contract_onboarding)..."
RUN_RESPONSE=$(curl -s -X POST $BASE_URL/agent-runs \
  -H "Content-Type: application/json" \
  -d '{
    "companyId": "test-orkestra-001",
    "workflowType": "contract_onboarding",
    "input": {
      "clientName": "Empresa Teste LTDA",
      "eventDate": "2025-12-15",
      "numGuests": 150,
      "budget": 75000,
      "eventType": "corporativo"
    }
  }')

echo "Response:"
echo $RUN_RESPONSE | jq .

RUN_ID=$(echo $RUN_RESPONSE | jq -r '.runId')
echo "  📝 Run ID: $RUN_ID"

echo ""
echo "[4/7] Buscando agent run criado..."
curl -s $BASE_URL/agent-runs/$RUN_ID | jq .

echo ""
echo "[5/7] Listando agent runs..."
curl -s "$BASE_URL/agent-runs?companyId=test-orkestra-001&limit=5" | jq .

echo ""
echo "[6/7] Criando memória..."
curl -s -X POST $BASE_URL/memory \
  -H "Content-Type: application/json" \
  -d '{
    "companyId": "test-orkestra-001",
    "memoryType": "episodic",
    "title": "Teste de Memória",
    "content": "Evento corporativo com 150 convidados",
    "tags": ["test", "evento", "corporativo"]
  }' | jq .

echo ""
echo "[7/7] Listando memórias..."
curl -s "$BASE_URL/memory?companyId=test-orkestra-001&limit=5" | jq .

echo ""
echo "=============================================="
echo "TESTE CONCLUÍDO!"
echo "=============================================="
echo ""
echo "Verifique:"
echo "  ✅ Run criado com status 'pending'"
echo "  ✅ Steps sendo gerados pelo worker"
echo "  ✅ Approvals (se houver risco alto)"
echo "  ✅ Memória salva"
echo ""
echo "Para ver status em tempo real:"
echo "  curl $BASE_URL/agent-runs/$RUN_ID"
echo ""
echo "Para ver todos os runs:"
echo "  curl $BASE_URL/agent-runs"
echo "=============================================="
