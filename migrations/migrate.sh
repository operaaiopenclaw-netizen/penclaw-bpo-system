#!/bin/bash
# ============================================================
# MIGRATION MANAGER — Orkestra Finance Brain
# PostgreSQL migrations with versioning
# ============================================================

set -e

# Config
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-orkestra}"
DB_USER="${DB_USER:-postgres}"
DB_PASS="${DB_PASS:-postgres}"
MIGRATIONS_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Help
usage() {
    echo "🎛️  Orkestra Migration Manager"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  status       Show migration status"
    echo "  up           Run all pending migrations"
    echo "  version N    Migrate to specific version"
    echo "  seed         Insert seed data"
    echo "  reset        ⚠️  DROP and recreate database"
    echo ""
    echo "Environment:"
    echo "  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS"
    echo ""
    exit 1
}

# Database connection
export PGPASSWORD="$DB_PASS"
PSQL="psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -v ON_ERROR_STOP=1"

# Check connection
check_connection() {
    if ! $PSQL -c "SELECT 1" > /dev/null 2>&1; then
        echo -e "${RED}❌ Error: Cannot connect to database${NC}"
        echo "   Host: $DB_HOST:$DB_PORT"
        echo "   Database: $DB_NAME"
        echo "   User: $DB_USER"
        exit 1
    fi
    echo -e "${GREEN}✅ Connected to $DB_HOST:$DB_PORT/$DB_NAME${NC}"
}

# Create migration table
init_migration_table() {
    $PSQL << 'EOF' > /dev/null 2>&1 || true
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    description TEXT,
    executed_at TIMESTAMPTZ DEFAULT NOW(),
    execution_time_ms INTEGER
);
EOF
}

# Get current version
get_current_version() {
    local version
    version=$($PSQL -t -c "SELECT COALESCE(MAX(version), 0) FROM schema_migrations;" 2>/dev/null || echo "0")
    echo "$version" | xargs
}

# Get available migrations
get_available_migrations() {
    find "$MIGRATIONS_DIR" -maxdepth 1 -name "V[0-9][0-9][0-9]__*.sql" | sort -V
}

# Extract version from filename
get_version_from_file() {
    basename "$1" | grep -oE '^V[0-9]+' | sed 's/V//' | sed 's/^0*//'
}

# Extract description from filename
get_description_from_file() {
    basename "$1" | sed 's/^V[0-9]*__//' | sed 's/.sql$//' | tr '_' ' '
}

# Status command
status() {
    echo -e "${BLUE}🎛️  Migration Status${NC}"
    echo ""
    
    check_connection
    init_migration_table
    
    local current
    current=$(get_current_version)
    echo -e "Current version: ${GREEN}$current${NC}"
    echo ""
    
    echo "Migration files:"
    printf "%-8s %-12s %-50s %s\n" "Version" "Status" "File" "Description"
    echo "─────────────────────────────────────────────────────────────────────"
    
    for file in $(get_available_migrations); do
        local version description status
        version=$(get_version_from_file "$file")
        description=$(get_description_from_file "$file")
        
        if [ "$version" -le "$current" ]; then
            status="${GREEN}✅ Applied${NC}"
        else
            status="${YELLOW}⏳ Pending${NC}"
        fi
        
        printf "%-8s %-12b %-50s %s\n" "$version" "$status" "$(basename "$file")" "$description"
    done
    echo ""
}

# Run single migration
run_migration() {
    local file=$1
    local version description start_time end_time elapsed
    
    version=$(get_version_from_file "$file")
    description=$(get_description_from_file "$file")
    
    echo -e "${YELLOW}⏳ Running migration V$version: $description${NC}"
    
    start_time=$(date +%s)
    
    if $PSQL -f "$file"; then
        end_time=$(date +%s)
        elapsed=$(( (end_time - start_time) / 1000000 ))
        
        $PSQL -c "INSERT INTO schema_migrations (version, description, execution_time_ms) VALUES ($version, '$description', $elapsed);" > /dev/null
        
        echo -e "${GREEN}✅ Migration V$version completed in ${elapsed}ms${NC}"
    else
        echo -e "${RED}❌ Migration V$version FAILED${NC}"
        exit 1
    fi
}

# Up command
up() {
    echo -e "${BLUE}🚀 Running migrations...${NC}"
    echo ""
    
    check_connection
    init_migration_table
    
    local current
    current=$(get_current_version)
    echo -e "Current version: $current"
    echo ""
    
    local pending=0
    for file in $(get_available_migrations); do
        local version
        version=$(get_version_from_file "$file")
        
        if [ "$version" -gt "$current" ]; then
            pending=$((pending + 1))
            run_migration "$file"
        fi
    done
    
    if [ $pending -eq 0 ]; then
        echo -e "${GREEN}✅ All migrations are up to date${NC}"
    else
        echo ""
        echo -e "${GREEN}✅ Applied $pending migration(s)${NC}"
    fi
    
    echo ""
}

# Seed command
seed() {
    echo -e "${BLUE}🌱 Inserting seed data...${NC}"
    echo ""
    
    check_connection
    
    local tenant_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    
    # Permissions
    $PSQL << EOF
-- RBAC Permissions
INSERT INTO rbac_permissions (code, name, resource, action) VALUES
('event.read', 'Ver Eventos', 'event', 'read'),
('event.write', 'Editar Eventos', 'event', 'write'),
('event.delete', 'Excluir Eventos', 'event', 'delete'),
('financial.read', 'Ver Financeiro', 'financial', 'read'),
('financial.write', 'Editar Financeiro', 'financial', 'write'),
('pricing.calculate', 'Calcular Preços', 'pricing', 'execute'),
('agent.run', 'Executar Agentes', 'agent', 'execute'),
('audit.read', 'Ver Auditoria', 'audit', 'read'),
('admin.full', 'Administração Completa', '*', '*')
ON CONFLICT (code) DO NOTHING;
EOF

    # Roles
    $PSQL << EOF
-- System Roles
INSERT INTO rbac_roles (tenant_id, name, permissions, is_system) VALUES
('$tenant_id', 'super_admin', '[{"resource": "*", "action": "*"}]'::jsonb, true),
('$tenant_id', 'admin', '[{"resource": "event", "action": "*"}, {"resource": "financial", "action": "*"}, {"resource": "pricing", "action": "execute"}, {"resource": "agent", "action": "execute"}, {"resource": "audit", "action": "read"}]'::jsonb, true),
('$tenant_id', 'manager', '[{"resource": "event", "action": "read"}, {"resource": "event", "action": "write"}, {"resource": "financial", "action": "read"}, {"resource": "pricing", "action": "execute"}]'::jsonb, false),
('$tenant_id', 'financeiro', '[{"resource": "financial", "action": "*"}, {"resource": "event", "action": "read"}, {"resource": "audit", "action": "read"}]'::jsonb, false),
('$tenant_id', 'operador', '[{"resource": "event", "action": "read"}, {"resource": "event", "action": "write"}, {"resource": "pricing", "action": "execute"}]'::jsonb, false),
('$tenant_id', 'viewer', '[{"resource": "event", "action": "read"}, {"resource": "financial", "action": "read"}]'::jsonb, false)
ON CONFLICT DO NOTHING;
EOF

    # System Parameters
    $PSQL << EOF
-- Parameters
INSERT INTO system_parameters (tenant_id, category, key, value, value_type, description, created_by) VALUES
('$tenant_id', 'scoring', 'threshold_go', '"35"', 'number', 'Limite mínimo de margem para GO', '00000000-0000-0000-0000-000000000001'),
('$tenant_id', 'scoring', 'limite_confianca', '"0.70"', 'number', 'Confiança mínima para decisões automáticas', '00000000-0000-0000-0000-000000000001'),
('$tenant_id', 'financial', 'margem_minima', '"25"', 'number', 'Margem mínima aceitável', '00000000-0000-0000-0000-000000000001'),
('$tenant_id', 'financial', 'limite_variancia_cmv', '"5"', 'number', 'Limite de variação CMV vs Estoque', '00000000-0000-0000-0000-000000000001'),
('$tenant_id', 'pricing', 'markup_default', '"1.5"', 'number', 'Markup padrão', '00000000-0000-0000-0000-000000000001'),
('$tenant_id', 'pricing', 'markup_alimentacao', '"1.8"', 'number', 'Markup alimentação', '00000000-0000-0000-0000-000000000001'),
('$tenant_id', 'forecast', 'dias_previsao', '"90"', 'number', 'Dias de projeção de caixa', '00000000-0000-0000-0000-000000000001'),
('$tenant_id', 'forecast', 'buffer_perc', '"15"', 'number', 'Percentual de buffer', '00000000-0000-0000-0000-000000000001'),
('$tenant_id', 'security', 'max_tentativas_login', '"5"', 'number', 'Tentativas antes do bloqueio', '00000000-0000-0000-0000-000000000001'),
('$tenant_id', 'security', 'session_ttl_minutes', '"60"', 'number', 'TTL da sessão', '00000000-0000-0000-0000-000000000001')
ON CONFLICT DO NOTHING;
EOF

    echo -e "${GREEN}✅ Seed data completed${NC}"
    echo ""
}

# Reset command (DANGER)
reset() {
    echo -e "${RED}⚠️  WARNING: This will DROP the entire database!${NC}"
    echo ""
    read -p "Type 'RESET' to confirm: " confirm
    
    if [ "$confirm" != "RESET" ]; then
        echo "Aborted."
        exit 1
    fi
    
    echo -e "${RED}💀 Dropping database...${NC}"
    
    export PGPASSWORD="$DB_PASS"
    psql -h $DB_HOST -p $DB_PORT -U $DB_USER postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
    psql -h $DB_HOST -p $DB_PORT -U $DB_USER postgres -c "CREATE DATABASE $DB_NAME;"
    
    echo -e "${GREEN}✅ Database reset complete${NC}"
    echo ""
    
    # Re-run migrations
    up
}

# Main
main() {
    case "${1:-}" in
        status)
            status
            ;;
        up)
            up
            ;;
        version)
            echo "Specific version migration coming soon..."
            ;;
        seed)
            seed
            ;;
        reset)
            reset
            ;;
        *)
            usage
            ;;
    esac
}

main "$@"
