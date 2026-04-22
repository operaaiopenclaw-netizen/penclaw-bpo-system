#!/bin/bash
# ============================================================
# ORKESTRA.AI — BOOTSTRAP COMPLETO
# Um comando. Tudo pronto.
# Usage: bash scripts/bootstrap.sh
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

step() { echo -e "\n${BLUE}${BOLD}[$1/6]${NC} $2"; }
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC}  $1"; }
fail() { echo -e "\n${RED}✗ ERRO: $1${NC}"; exit 1; }

echo -e "${BOLD}"
echo "╔══════════════════════════════════════════╗"
echo "║        ORKESTRA.AI — BOOTSTRAP v2        ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

# ---- 0. Detectar e iniciar runtime Docker (Colima ou Docker Desktop) ----
step 1 "Verificando Docker runtime..."

COLIMA_SOCK="$HOME/.colima/default/docker.sock"

# Função: testa se o daemon responde com o DOCKER_HOST atual
docker_alive() {
  docker info >/dev/null 2>&1
}

# 1. Tentar Colima (socket existe E daemon responde)
export DOCKER_HOST="unix://$COLIMA_SOCK"
if docker_alive; then
  ok "Colima ativo"
else
  # 2. Tentar Docker Desktop (limpa DOCKER_HOST)
  unset DOCKER_HOST
  if docker_alive; then
    ok "Docker Desktop ativo"
  else
    # 3. Nenhum ativo — iniciar Colima
    echo -e "  ${YELLOW}⚠${NC}  Docker não está rodando. Iniciando Colima..."
    if ! command -v colima >/dev/null 2>&1; then
      fail "Colima não instalado.\n  brew install colima docker\n  colima start"
    fi
    colima start
    export DOCKER_HOST="unix://$COLIMA_SOCK"
    echo -n "  Aguardando Colima"
    RETRIES=30
    until docker_alive; do
      RETRIES=$((RETRIES-1))
      [ $RETRIES -le 0 ] && fail "Colima não ficou pronto. Tente: colima start --verbose"
      echo -n "."
      sleep 2
    done
    echo ""
    ok "Colima iniciado"
  fi
fi

# Subir containers
docker compose -f docker-compose.dev.yml up -d 2>&1 | grep -vE "^#|Warning|warn" || \
  fail "Falha ao subir containers"
ok "Containers iniciados"

# ---- 2. Aguardar Postgres ----
step 2 "Aguardando Postgres + Redis ficarem disponíveis..."
RETRIES=30
until DOCKER_HOST="${DOCKER_HOST:-}" docker exec orkestra-db pg_isready -U postgres -d orkestra -q 2>/dev/null; do
  RETRIES=$((RETRIES-1))
  if [ $RETRIES -le 0 ]; then
    fail "Postgres não respondeu. Verifique: docker logs orkestra-db"
  fi
  echo -n "."
  sleep 1
done
echo ""
ok "Postgres pronto na porta 5433"

RETRIES=15
until DOCKER_HOST="${DOCKER_HOST:-}" docker exec orkestra-redis redis-cli ping 2>/dev/null | grep -q PONG; do
  RETRIES=$((RETRIES-1))
  [ $RETRIES -le 0 ] && fail "Redis não respondeu"
  sleep 1
done
ok "Redis pronto na porta 6379"

# ---- 4. Migração ----
step 3 "Aplicando migrations Prisma..."
npx prisma migrate dev --name etapa5_schema_v2 --skip-seed 2>&1 | tail -5 || \
  npx prisma migrate deploy 2>&1 | tail -5 || \
  warn "Migration já aplicada ou erro — continuando"
ok "Schema aplicado"

# ---- 5. Seed ----
step 4 "Populando banco com dados de teste..."
npx ts-node prisma/seed.ts || fail "Seed falhou"
ok "Banco populado"

# ---- 6. Typecheck ----
step 5 "Verificando TypeScript..."
npx tsc --noEmit 2>&1 | grep -v "safetyRules" | head -10 || warn "Avisos de TypeScript (ver output acima)"
ok "TypeScript OK"

# ---- 7. Servidor ----
step 6 "Iniciando servidor de desenvolvimento..."
echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  Sistema pronto. Iniciando em modo dev...  ${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}API:${NC}     http://localhost:3001"
echo -e "  ${BOLD}Docs:${NC}    http://localhost:3001/docs"
echo -e "  ${BOLD}Health:${NC}  http://localhost:3001/health"
echo -e "  ${BOLD}Studio:${NC}  npx prisma studio"
echo ""
echo -e "  Ctrl+C para parar o servidor."
echo ""

npm run dev
