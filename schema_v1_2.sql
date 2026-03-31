-- ============================================================
-- SCHEMA SQL v1.2 - AGENT RUNTIME
-- Base de dados para Orkestra Finance Brain
-- ============================================================

-- Habilitar extensão UUID (PostgreSQL)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- TABELA 1: AGENT_RUNS
-- Registro de execuções de agentes
-- ============================================================
CREATE TABLE agent_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID,
    workflow_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    risk_level TEXT DEFAULT 'low',
    input_summary TEXT,
    output_summary TEXT,
    total_cost NUMERIC(15, 2) DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    latency_ms INTEGER,
    created_by TEXT,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_status CHECK (status IN ('pending', 'running', 'validating', 'approval_required', 'approved', 'rejected', 'completed', 'failed', 'rolled_back')),
    CONSTRAINT chk_risk_level CHECK (risk_level IN ('none', 'low', 'medium', 'high', 'critical'))
);

-- Índices
CREATE INDEX idx_agent_runs_company ON agent_runs(company_id);
CREATE INDEX idx_agent_runs_status ON agent_runs(status);
CREATE INDEX idx_agent_runs_workflow ON agent_runs(workflow_type);
CREATE INDEX idx_agent_runs_created_at ON agent_runs(created_at DESC);

-- ============================================================
-- TABELA 2: AGENT_STEPS
-- Passos individuais de cada execução
-- ============================================================
CREATE TABLE agent_steps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_run_id UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    step_order INTEGER NOT NULL,
    agent_name TEXT NOT NULL,
    action_type TEXT NOT NULL,
    input_payload JSONB DEFAULT '{}',
    output_payload JSONB DEFAULT '{}',
    status TEXT DEFAULT 'pending',
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_step_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'skipped', 'blocked')),
    CONSTRAINT uq_agent_run_step_order UNIQUE (agent_run_id, step_order)
);

-- Índices
CREATE INDEX idx_agent_steps_run ON agent_steps(agent_run_id);
CREATE INDEX idx_agent_steps_status ON agent_steps(status);
CREATE INDEX idx_agent_steps_action ON agent_steps(action_type);

-- ============================================================
-- TABELA 3: TOOL_CALLS
-- Chamadas de tools/engines registradas
-- ============================================================
CREATE TABLE tool_calls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_step_id UUID NOT NULL REFERENCES agent_steps(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    tool_input JSONB DEFAULT '{}',
    tool_output JSONB DEFAULT '{}',
    status TEXT DEFAULT 'pending',
    latency_ms INTEGER,
    cost_estimate NUMERIC(15, 4),
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_tool_status CHECK (status IN ('pending', 'success', 'error', 'timeout'))
);

-- Índices
CREATE INDEX idx_tool_calls_step ON tool_calls(agent_step_id);
CREATE INDEX idx_tool_calls_name ON tool_calls(tool_name);
CREATE INDEX idx_tool_calls_status ON tool_calls(status);
CREATE INDEX idx_tool_calls_created ON tool_calls(created_at DESC);

-- ============================================================
-- TABELA 4: APPROVAL_REQUESTS
-- Solicitações de aprovação manual
-- ============================================================
CREATE TABLE approval_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_run_id UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    risk_level TEXT NOT NULL,
    requested_action TEXT NOT NULL,
    justification TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    approved_by TEXT,
    approved_at TIMESTAMP,
    requested_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_approval_risk CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT chk_approval_status CHECK (status IN ('pending', 'approved', 'rejected', 'expired'))
);

-- Índices
CREATE INDEX idx_approvals_run ON approval_requests(agent_run_id);
CREATE INDEX idx_approvals_status ON approval_requests(status);
CREATE INDEX idx_approvals_risk ON approval_requests(risk_level);

-- ============================================================
-- TABELA 5: MEMORY_ITEMS
-- Persistência de memória e contexto
-- ============================================================
CREATE TABLE memory_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID,
    memory_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    source_type TEXT,
    source_ref TEXT,
    confidence_score NUMERIC(3, 2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    embedding_vector VECTOR(1536), -- Requer extensão pgvector
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_memory_type CHECK (memory_type IN ('event', 'recipe', 'supplier', 'insight', 'decision', 'error', 'pattern'))
);

-- Índices
CREATE INDEX idx_memory_company ON memory_items(company_id);
CREATE INDEX idx_memory_type ON memory_items(memory_type);
CREATE INDEX idx_memory_tags ON memory_items USING GIN(tags);
CREATE INDEX idx_memory_created ON memory_items(created_at DESC);

-- Índice vetorial (se pgvector instalado)
-- CREATE INDEX idx_memory_embedding ON memory_items USING ivfflat (embedding_vector vector_cosine_ops);

-- ============================================================
-- TABELA 6: DOMAIN_RULES
-- Regras de domínio configuráveis
-- ============================================================
CREATE TABLE domain_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID,
    domain TEXT NOT NULL,
    rule_name TEXT NOT NULL,
    rule_description TEXT,
    rule_logic JSONB NOT NULL, -- Para armazenar expressões/condições
    priority INTEGER DEFAULT 100,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT uq_domain_rule UNIQUE (company_id, domain, rule_name),
    CONSTRAINT chk_domain CHECK (domain IN ('kitchen', 'financial', 'procurement', 'pricing', 'audit', 'calibration', 'reporting', 'reconciliation', 'general'))
);

-- Índices
CREATE INDEX idx_domain_rules_company ON domain_rules(company_id);
CREATE INDEX idx_domain_rules_domain ON domain_rules(domain);
CREATE INDEX idx_domain_rules_active ON domain_rules(active) WHERE active = TRUE;

-- ============================================================
-- TABELA 7: ARTIFACTS
-- Artefatos gerados pelos agentes
-- ============================================================
CREATE TABLE artifacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_run_id UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL,
    file_name TEXT NOT NULL,
    storage_url TEXT,
    checksum TEXT,
    size_bytes INTEGER,
    content_type TEXT,
    version INTEGER DEFAULT 1,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_artifact_type CHECK (artifact_type IN ('csv', 'json', 'pdf', 'log', 'report', 'config', 'pop', 'dashboard'))
);

-- Índices
CREATE INDEX idx_artifacts_run ON artifacts(agent_run_id);
CREATE INDEX idx_artifacts_type ON artifacts(artifact_type);
CREATE INDEX idx_artifacts_created ON artifacts(created_at DESC);

-- ============================================================
-- TABELA 8: COST_EVENTS
-- Eventos de custo/tokens
-- ============================================================
CREATE TABLE cost_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_run_id UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    model_name TEXT,
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    monetary_cost NUMERIC(15, 6) DEFAULT 0,
    cost_category TEXT DEFAULT 'inference',
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_cost_category CHECK (cost_category IN ('inference', 'storage', 'api', 'compute', 'bandwidth'))
);

-- Índices
CREATE INDEX idx_cost_events_run ON cost_events(agent_run_id);
CREATE INDEX idx_cost_events_model ON cost_events(model_name);
CREATE INDEX idx_cost_events_created ON cost_events(created_at DESC);

-- ============================================================
-- TABELA 9: EVENTS (Orkestra)
-- Eventos do negócio (vinculação com agent_runs)
-- ============================================================
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id TEXT UNIQUE NOT NULL, -- EVT-XXXXX
    n_ctt TEXT NOT NULL, -- Número CTT
    company_id UUID,
    company_name TEXT NOT NULL,
    client_name TEXT,
    event_type TEXT,
    event_date DATE,
    num_guests INTEGER,
    status TEXT DEFAULT 'proposal',
    revenue_total NUMERIC(15, 2),
    cmv_total NUMERIC(15, 2),
    net_profit NUMERIC(15, 2),
    margin_pct NUMERIC(5, 2),
    agent_run_id UUID REFERENCES agent_runs(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_event_status CHECK (status IN ('proposal', 'proposal_sent', 'negotiating', 'confirmed', 'canceled', 'executed', 'closed'))
);

-- Índices
CREATE INDEX idx_events_company ON events(company_id);
CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_events_date ON events(event_date);
CREATE INDEX idx_events_ctt ON events(n_ctt);
CREATE INDEX idx_events_agent_run ON events(agent_run_id);

-- ============================================================
-- TABELA 10: RECIPES
-- Receitas/fichas técicas
-- ============================================================
CREATE TABLE recipes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipe_id TEXT UNIQUE NOT NULL, -- REC###
    name TEXT NOT NULL,
    category TEXT,
    yield INTEGER,
    prep_time_min INTEGER,
    complexity TEXT,
    ingredients JSONB DEFAULT '[]',
    cost_per_serving NUMERIC(10, 2),
    instructions TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_complexity CHECK (complexity IN ('low', 'medium', 'high'))
);

-- Índices
CREATE INDEX idx_recipes_category ON recipes(category);
CREATE INDEX idx_recipes_active ON recipes(active) WHERE active = TRUE;

-- ============================================================
-- VIEWS UTILITÁRIAS
-- ============================================================

-- View: Resumo de execuções
CREATE VIEW v_agent_runs_summary AS
SELECT 
    ar.id,
    ar.workflow_type,
    ar.status,
    ar.risk_level,
    ar.total_cost,
    ar.total_tokens,
    ar.latency_ms,
    COUNT(DISTINCT aps.id) as total_steps,
    COUNT(DISTINCT CASE WHEN aps.status = 'completed' THEN aps.id END) as completed_steps,
    COUNT(DISTINCT apr.id) as pending_approvals,
    ar.created_at,
    ar.started_at,
    ar.finished_at
FROM agent_runs ar
LEFT JOIN agent_steps aps ON aps.agent_run_id = ar.id
LEFT JOIN approval_requests apr ON apr.agent_run_id = ar.id AND apr.status = 'pending'
GROUP BY ar.id, ar.workflow_type, ar.status, ar.risk_level, ar.total_cost, 
         ar.total_tokens, ar.latency_ms, ar.created_at, ar.started_at, ar.finished_at;

-- View: Eventos financeiros
CREATE VIEW v_financial_events AS
SELECT 
    e.id,
    e.event_id,
    e.n_ctt,
    e.company_name,
    e.client_name,
    e.event_type,
    e.event_date,
    e.status,
    e.revenue_total,
    e.cmv_total,
    e.net_profit,
    e.margin_pct,
    CASE 
        WHEN e.margin_pct >= 30 THEN 'excelente'
        WHEN e.margin_pct >= 20 THEN 'bom'
        WHEN e.margin_pct >= 10 THEN 'aceitável'
        ELSE 'crítico'
    END as margin_status
FROM events e;

-- ============================================================
-- TRIGGERS
-- ============================================================

-- Trigger: Atualizar updated_at em memory_items
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_memory_items_updated_at
    BEFORE UPDATE ON memory_items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_domain_rules_updated_at
    BEFORE UPDATE ON domain_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_events_updated_at
    BEFORE UPDATE ON events
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_recipes_updated_at
    BEFORE UPDATE ON recipes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- DADOS INICIAIS (SEED)
-- ============================================================

-- Domain Rules Base
INSERT INTO domain_rules (domain, rule_name, rule_description, rule_logic, priority) VALUES
('financial', 'margin_threshold', 'Margem mínima aceitável', '{"min_margin": 20}', 10),
('financial', 'variance_limit', 'Limite de variação CMV vs Estoque', '{"max_variance": 5}', 20),
('kitchen', 'recipe_validation', 'Validação de receitas', '{"required_fields": ["name", "yield", "ingredients"]}', 10),
('procurement', 'stock_alert', 'Alerta de estoque baixo', '{"min_days": 7}', 30),
('audit', 'consistency_check', 'Verificação de consistência', '{"max_diff": 5}', 10),
('general', 'logging_mandatory', 'Logging obrigatório', '{"required": true}', 1),
('general', 'policy_check', 'Verificação de políticas', '{"required": true}', 1);

-- ============================================================
-- COMENTÁRIOS
-- ============================================================

COMMENT ON TABLE agent_runs IS 'Registro principal de execuções de agentes';
COMMENT ON TABLE agent_steps IS 'Passos individuais de cada execução com payloads JSON';
COMMENT ON TABLE tool_calls IS 'Chamadas de tools com rastreabilidade completa';
COMMENT ON TABLE approval_requests IS 'Solicitações de aprovação manual para ações sensíveis';
COMMENT ON TABLE memory_items IS 'Armazenamento persistente de contexto e memória';
COMMENT ON TABLE domain_rules IS 'Regras de negócio configuráveis por domínio';
COMMENT ON TABLE artifacts IS 'Artefatos gerados (relatórios, CSVs, JSONs)';
COMMENT ON TABLE cost_events IS 'Registro de custos e uso de tokens';
COMMENT ON TABLE events IS 'Eventos de negócio (Orkestra) vinculados a agent_runs';
COMMENT ON TABLE recipes IS 'Fichas técicas de receitas';

-- ============================================================
-- FIM DO SCHEMA
-- Versão: 1.2
-- Compatível com Agent Runtime Core v1.1
-- ============================================================
