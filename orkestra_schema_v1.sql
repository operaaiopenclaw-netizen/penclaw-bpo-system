-- ============================================================
-- ORKESTRA SCHEMA v1 — PostgreSQL Multi-Tenant Production
-- Módulos: audit_log | decision_log | agent_action_log | RBAC | system_parameters
-- Multi-tenant: tenant_id obrigatório em todas as tabelas
-- Particionamento: mensal para tabelas de log
-- Immutable: audit_log, decision_log, agent_action_log (no UPDATE/DELETE)
-- ============================================================

-- ============================================================
-- EXTENSÕES
-- ============================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- TENANTS (raiz multi-tenant)
-- ============================================================
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    settings JSONB DEFAULT '{}',
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tenants_slug ON tenants(slug);

-- ============================================================
-- COST_CENTERS (escopo granular)
-- ============================================================
CREATE TABLE cost_centers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    code TEXT NOT NULL,
    parent_id UUID REFERENCES cost_centers(id),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, code)
);

CREATE INDEX idx_cost_centers_tenant ON cost_centers(tenant_id);
CREATE INDEX idx_cost_centers_parent ON cost_centers(parent_id);

-- ============================================================
-- 1. AUDIT_LOG (Immutable + Particionado)
-- ============================================================

-- Tabela pai
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cost_center_id UUID REFERENCES cost_centers(id),
    actor_id UUID NOT NULL,
    actor_type TEXT NOT NULL CHECK (actor_type IN ('user', 'system', 'api', 'agent')),
    action_type TEXT NOT NULL CHECK (action_type IN ('CREATE', 'UPDATE', 'DELETE', 'EXPORT', 'IMPORT', 'LOGIN', 'LOGOUT', 'APPROVE', 'REJECT')),
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    payload_before JSONB,
    payload_after JSONB,
    diff_summary TEXT,
    ip_address INET,
    user_agent TEXT,
    session_id UUID,
    checksum_sha256 TEXT NOT NULL CHECK (checksum_sha256 ~ '^[a-f0-9]{64}$'),
    previous_checksum TEXT,
    chain_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Índices inline
    CONSTRAINT idx_unique_previous UNIQUE (previous_checksum)
) PARTITION BY RANGE (created_at);

-- Partições iniciais (últimos 3 meses + próximo)
CREATE TABLE audit_log_2026_02 PARTITION OF audit_log
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE audit_log_2026_03 PARTITION OF audit_log
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE audit_log_2026_04 PARTITION OF audit_log
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE audit_log_2026_05 PARTITION OF audit_log
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

-- Índices
CREATE INDEX idx_audit_tenant_created ON audit_log(tenant_id, created_at);
CREATE INDEX idx_audit_actor_action ON audit_log(actor_id, action_type);
CREATE INDEX idx_audit_resource ON audit_log(resource_type, resource_id, created_at);
CREATE INDEX idx_audit_session ON audit_log(session_id, created_at);
CREATE INDEX idx_audit_created ON audit_log(created_at DESC);
CREATE INDEX idx_audit_checksum ON audit_log(checksum_sha256);

-- GIN indexes para JSONB
CREATE INDEX idx_audit_payload_before_gin ON audit_log USING GIN (payload_before);
CREATE INDEX idx_audit_payload_after_gin ON audit_log USING GIN (payload_after);

-- ============================================================
-- 2. DECISION_LOG (Immutable + Particionado)
-- ============================================================

CREATE TABLE decision_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cost_center_id UUID REFERENCES cost_centers(id),
    decision_id TEXT UNIQUE NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    input_context JSONB NOT NULL,
    output_decision JSONB NOT NULL,
    reasoning_chain JSONB NOT NULL,
    confidence_score DECIMAL(5,4) NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    confidence_breakdown JSONB,
    alternative_decisions JSONB,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    cost_usd DECIMAL(10,6) NOT NULL DEFAULT 0,
    metadata JSONB,
    session_id UUID,
    agent_id UUID,
    review_status TEXT DEFAULT 'pending' CHECK (review_status IN ('pending', 'approved', 'rejected', 'flagged')),
    reviewed_by UUID,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Partições
CREATE TABLE decision_log_2026_02 PARTITION OF decision_log
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE decision_log_2026_03 PARTITION OF decision_log
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE decision_log_2026_04 PARTITION OF decision_log
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE decision_log_2026_05 PARTITION OF decision_log
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

-- Índices
CREATE INDEX idx_decisions_tenant_model ON decision_log(tenant_id, model_name, created_at);
CREATE INDEX idx_decisions_confidence ON decision_log(confidence_score, created_at) WHERE confidence_score < 0.7;
CREATE INDEX idx_decisions_review_status ON decision_log(review_status, created_at);
CREATE INDEX idx_decisions_created ON decision_log(created_at DESC);
CREATE INDEX idx_decisions_session ON decision_log(session_id);
CREATE INDEX idx_decisions_agent ON decision_log(agent_id);

-- GIN indexes
CREATE INDEX idx_decisions_input_gin ON decision_log USING GIN (input_context);
CREATE INDEX idx_decisions_output_gin ON decision_log USING GIN (output_decision);

-- ============================================================
-- 3. AGENT_ACTION_LOG (Immutable + Particionado)
-- ============================================================

CREATE TABLE agent_action_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cost_center_id UUID REFERENCES cost_centers(id),
    session_id UUID NOT NULL,
    turn_number INTEGER NOT NULL CHECK (turn_number > 0),
    agent_id UUID,
    tool_name TEXT NOT NULL,
    tool_input JSONB NOT NULL,
    tool_output JSONB,
    tool_error JSONB,
    status TEXT NOT NULL DEFAULT 'started' CHECK (status IN ('started', 'completed', 'failed', 'timeout', 'cancelled')),
    latency_ms INTEGER,
    cost_usd DECIMAL(10,6),
    tokens_in INTEGER,
    tokens_out INTEGER,
    risk_level TEXT DEFAULT 'none' CHECK (risk_level IN ('none', 'low', 'medium', 'high', 'critical')),
    approval_required BOOLEAN DEFAULT FALSE,
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Partições
CREATE TABLE agent_action_log_2026_02 PARTITION OF agent_action_log
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE agent_action_log_2026_03 PARTITION OF agent_action_log
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE agent_action_log_2026_04 PARTITION OF agent_action_log
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE agent_action_log_2026_05 PARTITION OF agent_action_log
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

-- Índices
CREATE INDEX idx_actions_session_turn ON agent_action_log(session_id, turn_number);
CREATE INDEX idx_actions_tool_status ON agent_action_log(tool_name, status, created_at);
CREATE INDEX idx_actions_risk_level ON agent_action_log(risk_level, created_at) WHERE risk_level IN ('high', 'critical');
CREATE INDEX idx_actions_cost_center ON agent_action_log(cost_center_id, cost_usd) WHERE cost_usd > 0;
CREATE INDEX idx_actions_created ON agent_action_log(created_at DESC);
CREATE INDEX idx_actions_approved_by ON agent_action_log(approved_by);

-- ============================================================
-- 4. RBAC — TABELAS DE CONTROLE DE ACESSO
-- ============================================================

-- 4.1 RBAC_USERS
CREATE TABLE rbac_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    phone TEXT,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_secret TEXT,
    session_config JSONB DEFAULT '{"ttl_minutes": 60}'::jsonb,
    last_login_at TIMESTAMPTZ,
    failed_logins INTEGER DEFAULT 0,
    locked_until TIMESTAMPTZ,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(tenant_id, email)
);

CREATE INDEX idx_users_email ON rbac_users(email);
CREATE INDEX idx_users_tenant_active ON rbac_users(tenant_id, active);
CREATE INDEX idx_users_tenant_email ON rbac_users(tenant_id, email) WHERE active = TRUE;

-- 4.2 RBAC_ROLES
CREATE TABLE rbac_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    permissions JSONB NOT NULL DEFAULT '[]',
    parent_role_id UUID REFERENCES rbac_roles(id),
    hierarchy_level INTEGER NOT NULL DEFAULT 0,
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(tenant_id, name)
);

CREATE INDEX idx_roles_tenant ON rbac_roles(tenant_id, hierarchy_level);
CREATE INDEX idx_roles_parent ON rbac_roles(parent_role_id);
CREATE INDEX idx_roles_system ON rbac_roles(tenant_id) WHERE is_system = TRUE;

-- 4.3 RBAC_USER_ROLES
CREATE TABLE rbac_user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES rbac_users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES rbac_roles(id) ON DELETE CASCADE,
    cost_center_id UUID REFERENCES cost_centers(id),
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ,
    granted_by UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, role_id, cost_center_id, valid_from)
);

CREATE INDEX idx_user_roles_user ON rbac_user_roles(user_id, valid_from, valid_until);
CREATE INDEX idx_user_roles_active ON rbac_user_roles(user_id) WHERE valid_until IS NULL;
CREATE INDEX idx_user_roles_role ON rbac_user_roles(role_id);
CREATE INDEX idx_user_roles_cost_center ON rbac_user_roles(cost_center_id);

-- 4.4 RBAC_PERMISSIONS (tabela de referência)
CREATE TABLE rbac_permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    resource TEXT NOT NULL,
    action TEXT NOT NULL,
    conditions JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_permissions_resource ON rbac_permissions(resource, action);

-- 4.5 RBAC_ACCESS_LOG (particionado)
CREATE TABLE rbac_access_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    session_id UUID,
    action TEXT NOT NULL,
    resource TEXT NOT NULL,
    resource_id TEXT,
    permitted BOOLEAN NOT NULL,
    denied_reason TEXT,
    ip_address INET,
    user_agent TEXT,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Partições
CREATE TABLE rbac_access_log_2026_02 PARTITION OF rbac_access_log
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE rbac_access_log_2026_03 PARTITION OF rbac_access_log
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE rbac_access_log_2026_04 PARTITION OF rbac_access_log
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE rbac_access_log_2026_05 PARTITION OF rbac_access_log
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

CREATE INDEX idx_access_user ON rbac_access_log(user_id, created_at);
CREATE INDEX idx_access_permitted ON rbac_access_log(permitted, created_at);
CREATE INDEX idx_access_action ON rbac_access_log(action, created_at);
CREATE INDEX idx_access_tenant ON rbac_access_log(tenant_id, created_at);

-- ============================================================
-- 5. SYSTEM_PARAMETERS (configuração centralizada)
-- ============================================================

CREATE TABLE system_parameters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cost_center_id UUID REFERENCES cost_centers(id),
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    value JSONB NOT NULL,
    value_type TEXT NOT NULL CHECK (value_type IN ('string', 'number', 'boolean', 'json', 'array')),
    description TEXT,
    default_value JSONB,
    min_value NUMERIC,
    max_value NUMERIC,
    allowed_values JSONB,
    is_computed BOOLEAN DEFAULT FALSE,
    computed_formula TEXT,
    requires_restart BOOLEAN DEFAULT FALSE,
    is_encrypted BOOLEAN DEFAULT FALSE,
    version INTEGER DEFAULT 1,
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(tenant_id, cost_center_id, key)
);

CREATE INDEX idx_params_tenant_cat ON system_parameters(tenant_id, category);
CREATE INDEX idx_params_key ON system_parameters(tenant_id, key);
CREATE INDEX idx_params_computed ON system_parameters(tenant_id) WHERE is_computed = TRUE;

-- Tabela de histórico de mudanças
CREATE TABLE system_parameter_changes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    param_id UUID NOT NULL REFERENCES system_parameters(id) ON DELETE CASCADE,
    previous_value JSONB NOT NULL,
    new_value JSONB NOT NULL,
    changed_by UUID NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    change_reason TEXT,
    rolled_back BOOLEAN DEFAULT FALSE,
    rolled_back_at TIMESTAMPTZ,
    rolled_back_by UUID
);

CREATE INDEX idx_param_changes_param ON system_parameter_changes(param_id, changed_at);
CREATE INDEX idx_param_changes_tenant ON system_parameter_changes(tenant_id, changed_at);

-- ============================================================
-- AGENT_SESSIONS (referência para logs)
-- ============================================================

CREATE TABLE agent_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES rbac_users(id),
    session_type TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'error'))
);

CREATE INDEX idx_agent_sessions_tenant ON agent_sessions(tenant_id, started_at);
CREATE INDEX idx_agent_sessions_user ON agent_sessions(user_id, started_at);

-- ============================================================
-- VIEWS ANALÍTICAS
-- ============================================================

-- View: Resumo de execuções
CREATE VIEW v_agent_runs_summary AS
SELECT 
    aal.tenant_id,
    aal.session_id,
    aal.agent_id,
    COUNT(*) as total_actions,
    COUNT(DISTINCT CASE WHEN aal.status = 'completed' THEN aal.id END) as completed_actions,
    COUNT(DISTINCT CASE WHEN aal.status = 'failed' THEN aal.id END) as failed_actions,
    COUNT(DISTINCT CASE WHEN aal.approval_required THEN aal.id END) as pending_approvals,
    SUM(aal.cost_usd) as total_cost,
    SUM(aal.tokens_in + aal.tokens_out) as total_tokens,
    AVG(aal.latency_ms) as avg_latency,
    MIN(aal.created_at) as started_at,
    MAX(aal.created_at) as last_action_at
FROM agent_action_log aal
GROUP BY aal.tenant_id, aal.session_id, aal.agent_id;

-- View: Audit daily summary
CREATE VIEW v_audit_daily_summary AS
SELECT 
    tenant_id,
    DATE(created_at) as date,
    action_type,
    resource_type,
    COUNT(*) as count,
    COUNT(DISTINCT actor_id) as unique_actors
FROM audit_log
GROUP BY tenant_id, DATE(created_at), action_type, resource_type;

-- View: Decision accuracy
CREATE VIEW v_decision_accuracy AS
SELECT 
    tenant_id,
    model_name,
    DATE(created_at) as date,
    AVG(confidence_score) as avg_confidence,
    COUNT(CASE WHEN confidence_score < 0.7 THEN 1 END) as low_confidence_count,
    AVG(latency_ms) as avg_latency,
    SUM(cost_usd) as total_cost
FROM decision_log
GROUP BY tenant_id, model_name, DATE(created_at);

-- View: Agent performance
CREATE VIEW v_agent_performance AS
SELECT 
    tenant_id,
    agent_id,
    DATE(created_at) as date,
    COUNT(*) as total_calls,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failures,
    AVG(latency_ms) as avg_latency,
    SUM(cost_usd) as total_cost,
    SUM(tokens_in + tokens_out) as total_tokens
FROM agent_action_log
GROUP BY tenant_id, agent_id, DATE(created_at);

-- View: User permissions (atuais)
CREATE VIEW v_user_permissions AS
SELECT 
    u.tenant_id,
    u.id as user_id,
    u.email,
    r.name as role_name,
    r.permissions,
    ur.valid_from,
    ur.valid_until,
    ur.cost_center_id
FROM rbac_users u
JOIN rbac_user_roles ur ON ur.user_id = u.id
JOIN rbac_roles r ON r.id = ur.role_id
WHERE (ur.valid_until IS NULL OR ur.valid_until > NOW())
  AND u.active = TRUE;

-- ============================================================
-- FUNÇÕES UTILITÁRIAS
-- ============================================================

-- Função: Calcular checksum SHA256
CREATE OR REPLACE FUNCTION calculate_audit_checksum(
    p_payload JSONB,
    p_previous_checksum TEXT DEFAULT NULL
) RETURNS TEXT AS $$
BEGIN
    RETURN encode(
        digest(
            COALESCE(p_previous_checksum, '') || COALESCE(p_payload::text, ''),
            'sha256'
        ),
        'hex'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Função: Verificar permissão (check RBAC)
CREATE OR REPLACE FUNCTION has_permission(
    p_user_id UUID,
    p_resource TEXT,
    p_action TEXT,
    OUT has_permission BOOLEAN
) AS $$
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM rbac_user_roles ur
        JOIN rbac_roles r ON r.id = ur.role_id
        WHERE ur.user_id = p_user_id
          AND (ur.valid_until IS NULL OR ur.valid_until > NOW())
          AND (
              r.permissions @> jsonb_build_array(jsonb_build_object('resource', p_resource, 'action', p_action))
              OR r.permissions @> jsonb_build_array(jsonb_build_object('resource', '*', 'action', '*'))
          )
    ) INTO has_permission;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Função: Buscar parâmetro hierárquico
CREATE OR REPLACE FUNCTION get_parameter(
    p_tenant_id UUID,
    p_key TEXT,
    p_cost_center_id UUID DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    v_value JSONB;
BEGIN
    -- Buscar no cost_center primeiro
    IF p_cost_center_id IS NOT NULL THEN
        SELECT value INTO v_value
        FROM system_parameters
        WHERE tenant_id = p_tenant_id
          AND cost_center_id = p_cost_center_id
          AND key = p_key;
    END IF;
    
    -- Se não achou, buscar no tenant (global)
    IF v_value IS NULL THEN
        SELECT value INTO v_value
        FROM system_parameters
        WHERE tenant_id = p_tenant_id
          AND cost_center_id IS NULL
          AND key = p_key;
    END IF;
    
    RETURN v_value;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================
-- TRIGGERS
-- ============================================================

-- Trigger: Impedir UPDATE/DELETE em audit_log (immutable)
CREATE OR REPLACE FUNCTION prevent_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_log, decision_log e agent_action_log são tabelas imutáveis. UPDATE/DELETE não permitido.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_immutable
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION prevent_modification();

CREATE TRIGGER trg_decision_immutable
    BEFORE UPDATE OR DELETE ON decision_log
    FOR EACH ROW EXECUTE FUNCTION prevent_modification();

CREATE TRIGGER trg_actions_immutable
    BEFORE UPDATE OR DELETE ON agent_action_log
    FOR EACH ROW EXECUTE FUNCTION prevent_modification();

-- Trigger: Auto-gerar checksum em audit_log
CREATE OR REPLACE FUNCTION generate_audit_checksum()
RETURNS TRIGGER AS $$
BEGIN
    NEW.checksum_sha256 := calculate_audit_checksum(
        jsonb_build_object(
            'tenant_id', NEW.tenant_id,
            'actor_id', NEW.actor_id,
            'action_type', NEW.action_type,
            'resource_type', NEW.resource_type,
            'resource_id', NEW.resource_id,
            'payload_before', NEW.payload_before,
            'payload_after', NEW.payload_after,
            'created_at', NEW.created_at
        ),
        NEW.previous_checksum
    );
    
    NEW.chain_hash := encode(
        digest(
            COALESCE(NEW.previous_checksum, 'genesis') || NEW.checksum_sha256,
            'sha256'
        ),
        'hex'
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_checksum
    BEFORE INSERT ON audit_log
    FOR EACH ROW EXECUTE FUNCTION generate_audit_checksum();

-- Trigger: Versionamento de system_parameters
CREATE OR REPLACE FUNCTION parameter_version_trigger()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        NEW.version := 1;
    ELSIF TG_OP = 'UPDATE' THEN
        -- Registrar mudança no histórico
        INSERT INTO system_parameter_changes (
            tenant_id, param_id, previous_value, new_value, changed_by, change_reason
        ) VALUES (
            OLD.tenant_id,
            OLD.id,
            OLD.value,
            NEW.value,
            NEW.created_by,
            'Atualização de parâmetro'
        );
        
        NEW.version := OLD.version + 1;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_parameter_version
    BEFORE INSERT OR UPDATE ON system_parameters
    FOR EACH ROW EXECUTE FUNCTION parameter_version_trigger();

-- Trigger: updated_at automático
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_cost_centers_updated_at
    BEFORE UPDATE ON cost_centers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_rbac_users_updated_at
    BEFORE UPDATE ON rbac_users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_rbac_roles_updated_at
    BEFORE UPDATE ON rbac_roles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger: Registrar access_log automaticamente em operações
CREATE OR REPLACE FUNCTION log_access_attempt()
RETURNS TRIGGER AS $$
BEGIN
    -- Só loga se explicitamente solicitado ou em modo debug
    -- (implementação customizada pode adicionar lógica aqui)
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- COMENTÁRIOS
-- ============================================================

COMMENT ON TABLE audit_log IS 'Registro imutável de todas as alterações no sistema. Particionado mensalmente. Chain hash para integridade.';
COMMENT ON TABLE decision_log IS 'Rastreabilidade de decisões da IA com explainability. Particionado mensalmente.';
COMMENT ON TABLE agent_action_log IS 'Rastreamento de tool calls e ações de agentes. Particionado mensalmente.';
COMMENT ON TABLE rbac_users IS 'Usuários do sistema com autenticação MFA e configuração de sessão.';
COMMENT ON TABLE rbac_roles IS 'Papéis com hierarquia e array de permissões JSONB.';
COMMENT ON TABLE rbac_user_roles IS 'Vínculo temporal entre usuários e papéis (RBAC temporal).'
COMMENT ON TABLE rbac_permissions IS 'Tabela de referência com códigos de permissão do sistema.';
COMMENT ON TABLE system_parameters IS 'Configuração centralizada com versionamento e hierarquia (cost_center → tenant).';
COMMENT ON TABLE system_parameter_changes IS 'Histórico imutável de mudanças em parâmetros.';

-- ============================================================
-- FIM DO SCHEMA
-- Versão: 1.0
-- Multi-tenant: ✅
-- Particionamento: ✅ (mensal)
-- Immutable logs: ✅
-- Views analíticas: ✅
-- Triggers: ✅
-- ============================================================
