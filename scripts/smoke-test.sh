#!/bin/bash
# ============================================================
# ORKESTRA.AI — SMOKE TEST COMPLETO
# Testa todos os agentes e workflows via HTTP
# Usage: bash scripts/smoke-test.sh
# Requer: servidor rodando em localhost:3001
# ============================================================

set -e

BASE="http://localhost:3001"
TENANT="a1b2c3d4-e5f6-7890-abcd-ef1234567890"
PASS=0
FAIL=0
TOTAL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

check() {
  local name="$1"
  local method="$2"
  local url="$3"
  local data="$4"
  local expect="$5"
  TOTAL=$((TOTAL+1))

  if [ -n "$data" ]; then
    RESP=$(curl -s -o /tmp/smoke_resp.json -w "%{http_code}" \
      -X "$method" "$BASE$url" \
      -H "Content-Type: application/json" \
      -d "$data" 2>/dev/null)
  else
    RESP=$(curl -s -o /tmp/smoke_resp.json -w "%{http_code}" \
      -X "$method" "$BASE$url" 2>/dev/null)
  fi

  BODY=$(cat /tmp/smoke_resp.json 2>/dev/null || echo "{}")

  if echo "$RESP" | grep -qE "^2" && ([ -z "$expect" ] || echo "$BODY" | grep -q "$expect"); then
    echo -e "  ${GREEN}✓${NC} [$RESP] $name"
    PASS=$((PASS+1))
    echo "$BODY" > /tmp/smoke_last_ok.json
  else
    echo -e "  ${RED}✗${NC} [$RESP] $name"
    echo -e "       ${YELLOW}$(echo $BODY | head -c 200)${NC}"
    FAIL=$((FAIL+1))
  fi
}

# Extrai campo JSON do último response bem-sucedido
extract() {
  python3 -c "import json,sys; d=json.load(open('/tmp/smoke_last_ok.json')); print(d$1)" 2>/dev/null || echo ""
}

echo -e "${BOLD}"
echo "╔══════════════════════════════════════════════╗"
echo "║       ORKESTRA.AI — SMOKE TEST v2.0          ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"
echo "  Base: $BASE"
echo "  Tenant: $TENANT"
echo ""

# ---- INFRAESTRUTURA ----
echo -e "${BLUE}${BOLD}[INFRA]${NC}"
check "Health check"                    GET  "/health"                  ""   "ok"
check "Swagger docs"                    GET  "/docs"                    ""   ""
check "Queue status"                    GET  "/metrics/queue"           ""   "waiting"

# ---- DASHBOARD ----
echo -e "\n${BLUE}${BOLD}[DASHBOARD]${NC}"
check "Dashboard financeiro"            GET  "/dashboard/financial?tenantId=$TENANT"    "" ""
check "Dashboard operações"             GET  "/dashboard/operations?tenantId=$TENANT"   "" ""
check "Dashboard CEO"                   GET  "/dashboard/ceo?tenantId=$TENANT"          "" ""

# ---- EVENTS ----
echo -e "\n${BLUE}${BOLD}[EVENTS]${NC}"
check "Listar eventos"                  GET  "/events?tenantId=$TENANT"  "" ""

# ---- CRM ----
echo -e "\n${BLUE}${BOLD}[CRM]${NC}"
check "Listar leads"                    GET  "/crm/leads?tenantId=$TENANT"              "" ""
check "Pipeline stats"                  GET  "/crm/pipeline?tenantId=$TENANT"           "" ""
check "Criar lead"                      POST "/crm/leads" \
  '{"tenantId":"'$TENANT'","contactName":"Teste Smoke","email":"smoke@test.com","eventType":"casamento","estimatedBudget":50000,"numGuests":100}' \
  "id"

# ---- SERVICE ORDERS ----
echo -e "\n${BLUE}${BOLD}[SERVICE ORDERS]${NC}"
check "Listar OS"                       GET  "/service-orders?tenantId=$TENANT"         "" ""

# ---- PRODUCTION ORDERS ----
echo -e "\n${BLUE}${BOLD}[PRODUCTION ORDERS]${NC}"
check "Listar OP"                       GET  "/production-orders?tenantId=$TENANT"      "" ""

# ---- EXECUTION ----
echo -e "\n${BLUE}${BOLD}[EXECUTION]${NC}"
check "Listar sessões de execução"      GET  "/execution/sessions?tenantId=$TENANT"     "" ""

# ---- MEMORY ----
echo -e "\n${BLUE}${BOLD}[MEMORY]${NC}"
check "Buscar memórias"                 GET  "/memory?tenantId=$TENANT"                 "" ""

# ---- INTELLIGENCE ----
echo -e "\n${BLUE}${BOLD}[INTELLIGENCE]${NC}"
check "Decisões operacionais"           GET  "/intelligence/decisions?tenantId=$TENANT" "" ""

# ---- WORKFLOW: lead_qualification ----
echo -e "\n${BLUE}${BOLD}[WORKFLOW: lead_qualification]${NC}"
check "Enfileirar lead_qualification"   POST "/agent-runs" \
  '{"tenantId":"'$TENANT'","workflowType":"lead_qualification","input":{"contactName":"Maria Joana","email":"maria@exemplo.com","eventType":"casamento","budget":120000,"numGuests":200,"timeline":"2026-08-15","authority":"decisora","source":"indicacao"}}' \
  "id"

RUN_ID=$(python3 -c "import json; d=json.load(open('/tmp/smoke_last_ok.json')); print(d.get('id',''))" 2>/dev/null || echo "")
sleep 3

if [ -n "$RUN_ID" ]; then
  check "Status do run"                 GET  "/agent-runs/$RUN_ID"                      "" ""
fi

# ---- WORKFLOW: event_procurement ----
echo -e "\n${BLUE}${BOLD}[WORKFLOW: event_procurement]${NC}"
check "Enfileirar event_procurement"    POST "/agent-runs" \
  '{"tenantId":"'$TENANT'","workflowType":"event_procurement","input":{"eventType":"casamento","numGuests":280,"durationHours":7,"eventId":"evt-001","eventDate":"2026-04-22T19:00:00Z","eventMarginPct":22}}' \
  "id"

PROC_RUN_ID=$(python3 -c "import json; d=json.load(open('/tmp/smoke_last_ok.json')); print(d.get('id',''))" 2>/dev/null || echo "")
sleep 5

if [ -n "$PROC_RUN_ID" ]; then
  check "Status procurement run"        GET  "/agent-runs/$PROC_RUN_ID"                 "" ""
fi

# ---- WORKFLOW: contract_to_event ----
echo -e "\n${BLUE}${BOLD}[WORKFLOW: contract_to_event]${NC}"
check "Enfileirar contract_to_event"    POST "/agent-runs" \
  '{"tenantId":"'$TENANT'","workflowType":"contract_to_event","input":{"contractId":"contract-001","eventId":"evt-001","eventType":"casamento","numGuests":280,"contractValue":188000}}' \
  "id"

# ---- APPROVALS ----
echo -e "\n${BLUE}${BOLD}[APPROVALS]${NC}"
check "Listar aprovações pendentes"     GET  "/approvals?tenantId=$TENANT&status=pending" "" ""

# ---- ARTIFACTS ----
echo -e "\n${BLUE}${BOLD}[ARTIFACTS]${NC}"
check "Listar artifacts"                GET  "/artifacts?tenantId=$TENANT"              "" ""

# ---- RESULTADO FINAL ----
echo ""
echo -e "${BOLD}════════════════════════════════════════════════${NC}"
echo -e "${BOLD}RESULTADO: ${GREEN}$PASS aprovados${NC} / ${RED}$FAIL falharam${NC} / $TOTAL total${NC}"
echo -e "${BOLD}════════════════════════════════════════════════${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
  echo -e "${GREEN}${BOLD}✅ Sistema operacional. Todos os testes passaram.${NC}"
  exit 0
else
  echo -e "${YELLOW}${BOLD}⚠  $FAIL teste(s) falharam. Verificar logs acima.${NC}"
  exit 1
fi
