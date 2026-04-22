-- ============================================================
-- MIGRATION V001 — BASELINE
-- Schema inicial: audit_log | decision_log | agent_action_log | RBAC | system_parameters
-- Multi-tenant + Particionamento + Immutable
-- ============================================================

-- Enable extensions
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

-- Seed: Tenant inicial Orkestra
INSERT INTO tenants (id, name, slug, settings) VALUES 
('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Orkestra Eventos', 'orkestra', '{"timezone": "America/Sao_Paulo", "currency": "BRL"}');

CREATE INDEX idx_tenants_slug ON tenants(slug);

-- ============================================================
-- COST_CENTERS
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

-- Seed: Centros de custo
INSERT INTO cost_centers (tenant_id, name, code) VALUES 
('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'LA ORANA', 'LA'),
('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'STATUS Opera', 'STATUS'),
('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Administrativo', 'ADM');

CREATE INDEX idx_cost_centers_tenant ON cost_centers(tenant_id);

-- ============================================================
-- AUDIT_LOG (Immutable + Particionado)
-- ============================================================
CREATE TABLE audit_log (
    id UUID NOT NULL DEFAULT uuid_generate_v4(),
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
    checksum_sha256 TEXT NOT NULL,
    previous_checksum TEXT,
    chain_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Partições iniciais
CREATE TABLE audit_log_2026_04 PARTITION OF audit_log
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE audit_log_2026_05 PARTITION OF audit_log
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

CREATE INDEX idx_audit_tenant_created ON audit_log(tenant_id, created_at);
CREATE INDEX idx_audit_actor_action ON audit_log(actor_id, action_type);
CREATE INDEX idx_audit_resource ON audit_log(resource_type, resource_id, created_at);

-- ============================================================
-- DECISION_LOG (Immutable + Particionado)
-- ============================================================
CREATE TABLE decision_log (
    id UUID NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cost_center_id UUID REFERENCES cost_centers(id),
    decision_id TEXT NOT NULL,
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
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

CREATE TABLE decision_log_2026_04 PARTITION OF decision_log
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

CREATE INDEX idx_decisions_tenant_model ON decision_log(tenant_id, model_name, created_at);
CREATE INDEX idx_decisions_confidence ON decision_log(confidence_score, created_at) WHERE confidence_score < 0.7;

-- ============================================================
-- AGENT_ACTION_LOG (Immutable + Particionado)
-- ============================================================
CREATE TABLE agent_action_log (
    id UUID NOT NULL DEFAULT uuid_generate_v4(),
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
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

CREATE TABLE agent_action_log_2026_04 PARTITION OF agent_action_log
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

CREATE INDEX idx_actions_session_turn ON agent_action_log(session_id, turn_number);
CREATE INDEX idx_actions_tool_status ON agent_action_log(tool_name, status, created_at);

-- ============================================================
-- RBAC
-- ============================================================
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

CREATE TABLE rbac_access_log (
    id UUID NOT NULL DEFAULT uuid_generate_v4(),
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
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

CREATE TABLE rbac_access_log_2026_04 PARTITION OF rbac_access_log
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

-- ============================================================
-- SYSTEM_PARAMETERS
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

-- ============================================================
-- AGENT_SESSIONS
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

-- ============================================================
-- MIGRATION RECORD
-- ============================================================
INSERT INTO schema_migrations (version, description, executed_at) 
VALUES (1, 'Baseline schema: audit_log, decision_log, agent_action_log, RBAC, system_parameters', NOW());
