-- ============================================================
-- MIGRATION V003 — ADVANCED TRIGGERS & FUNCTIONS
-- Functions SHA256, RBAC checks, parameter hierarchy
-- ============================================================

-- ============================================================
-- FUNCTIONS UTILITÁRIAS
-- ============================================================

-- 1. Calcular checksum SHA256
CREATE OR REPLACE FUNCTION calculate_checksum(
    p_data JSONB,
    p_previous_checksum TEXT DEFAULT NULL
) RETURNS TEXT AS $$
BEGIN
    RETURN encode(
        digest(
            COALESCE(p_previous_checksum, 'genesis') || COALESCE(p_data::text, '{}'),
            'sha256'
        ),
        'hex'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION calculate_checksum IS 'Calcula hash SHA256 para integridade de dados audit_log';

-- 2. Verificar permissão (RBAC check)
CREATE OR REPLACE FUNCTION has_permission(
    p_user_id UUID,
    p_resource TEXT,
    p_action TEXT,
    OUT permitted BOOLEAN,
    OUT role_names TEXT[],
    OUT denied_reason TEXT
) AS $$
DECLARE
    v_roles JSONB;
    v_has_wildcard BOOLEAN;
BEGIN
    -- Buscar permissões agregadas de todos os roles do usuário
    SELECT 
        COALESCE(jsonb_agg(r.permissions), '[]'::jsonb),
        array_agg(r.name)
    INTO v_roles, role_names
    FROM rbac_user_roles ur
    JOIN rbac_roles r ON r.id = ur.role_id
    WHERE ur.user_id = p_user_id
      AND (ur.valid_until IS NULL OR ur.valid_until > NOW())
      AND r.active = TRUE;

    -- Verificar wildcard (*)
    SELECT EXISTS (
        SELECT 1 FROM jsonb_array_elements(v_roles) perm
        WHERE perm->>'resource' = '*' AND perm->>'action' = '*'
    ) INTO v_has_wildcard;

    IF v_has_wildcard THEN
        permitted := TRUE;
        denied_reason := NULL;
        RETURN;
    END IF;

    -- Verificar permissão específica
    SELECT EXISTS (
        SELECT 1 FROM jsonb_array_elements(v_roles) perm
        WHERE (perm->>'resource' = p_resource OR perm->>'resource' = '*')
          AND (perm->>'action' = p_action OR perm->>'action' = '*')
    ) INTO permitted;

    IF NOT permitted THEN
        denied_reason := format('User lacks permission %s:%s', p_resource, p_action);
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION has_permission IS 'Verifica se usuário tem permissão para um recurso/ação';

-- 3. Buscar parâmetro hierárquico
CREATE OR REPLACE FUNCTION get_parameter(
    p_tenant_id UUID,
    p_key TEXT,
    p_cost_center_id UUID DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    v_value JSONB;
BEGIN
    -- Tentar buscar no cost_center específico
    IF p_cost_center_id IS NOT NULL THEN
        SELECT value INTO v_value
        FROM system_parameters
        WHERE tenant_id = p_tenant_id
          AND cost_center_id = p_cost_center_id
          AND key = p_key
          AND is_computed = FALSE;
    END IF;
    
    -- Se não achou ou não especificou cc, buscar no tenant
    IF v_value IS NULL THEN
        SELECT value INTO v_value
        FROM system_parameters
        WHERE tenant_id = p_tenant_id
          AND cost_center_id IS NULL
          AND key = p_key
          AND is_computed = FALSE;
    END IF;
    
    RETURN v_value;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_parameter IS 'Busca parâmetro com herança: cost_center > tenant';

-- 4. Verificar margem aceitável
CREATE OR REPLACE FUNCTION check_margin_acceptable(
    p_revenue NUMERIC,
    p_cmv NUMERIC,
    p_tenant_id UUID,
    OUT margin_pct NUMERIC,
    OUT acceptable BOOLEAN,
    OUT threshold NUMERIC
) AS $$
BEGIN
    -- Calcular margem
    IF p_revenue > 0 THEN
        margin_pct := ((p_revenue - p_cmv) / p_revenue * 100)::NUMERIC(5,2);
    ELSE
        margin_pct := 0;
    END IF;
    
    -- Buscar threshold do tenant
    SELECT COALESCE((value->>0)::NUMERIC, 25) INTO threshold
    FROM system_parameters
    WHERE tenant_id = p_tenant_id
      AND key = 'threshold_go'
      AND cost_center_id IS NULL;
    
    acceptable := (margin_pct >= threshold);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION check_margin_acceptable IS 'Verifica se margem está acima do threshold configurado';

-- ============================================================
-- TRIGGERS
-- ============================================================

-- 1. Impedir UPDATE/DELETE em tabelas imutáveis
CREATE OR REPLACE FUNCTION prevent_modification()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'Tabela % é imutável. UPDATE não permitido. Use INSERT para novo registro.', TG_TABLE_NAME;
    ELSIF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Tabela % é imutável. DELETE não permitido.', TG_TABLE_NAME;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Aplicar em tabelas imutáveis
CREATE TRIGGER trg_audit_immutable
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION prevent_modification();

CREATE TRIGGER trg_decision_immutable
    BEFORE UPDATE OR DELETE ON decision_log
    FOR EACH ROW EXECUTE FUNCTION prevent_modification();

CREATE TRIGGER trg_actions_immutable
    BEFORE UPDATE OR DELETE ON agent_action_log
    FOR EACH ROW EXECUTE FUNCTION prevent_modification();

CREATE TRIGGER trg_access_log_immutable
    BEFORE UPDATE OR DELETE ON rbac_access_log
    FOR EACH ROW EXECUTE FUNCTION prevent_modification();

-- 2. Auto-gerar checksum em audit_log
CREATE OR REPLACE FUNCTION audit_log_checksum_trigger()
RETURNS TRIGGER AS $$
DECLARE
    v_payload JSONB;
BEGIN
    v_payload := jsonb_build_object(
        'tenant_id', NEW.tenant_id,
        'actor_id', NEW.actor_id,
        'action_type', NEW.action_type,
        'resource_type', NEW.resource_type,
        'resource_id', NEW.resource_id,
        'payload_before', NEW.payload_before,
        'payload_after', NEW.payload_after,
        'created_at', NEW.created_at
    );
    
    NEW.checksum_sha256 := calculate_checksum(v_payload, NEW.previous_checksum);
    
    -- Chain hash inclui previous
    NEW.chain_hash := calculate_checksum(
        jsonb_build_object('checksum', NEW.checksum_sha256),
        COALESCE(NEW.previous_checksum, 'genesis')
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_checksum
    BEFORE INSERT ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_checksum_trigger();

-- 3. Versionamento de system_parameters
CREATE OR REPLACE FUNCTION parameter_version_trigger()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        NEW.version := 1;
    ELSIF TG_OP = 'UPDATE' THEN
        -- Registrar mudança
        INSERT INTO system_parameter_changes (
            tenant_id, param_id, previous_value, new_value, changed_by, change_reason
        ) VALUES (
            OLD.tenant_id,
            OLD.id,
            OLD.value,
            NEW.value,
            NEW.created_by,
            TG_ARGV[0] -- pode receber reason como arg
        );
        
        NEW.version := OLD.version + 1;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_parameter_version
    BEFORE INSERT OR UPDATE ON system_parameters
    FOR EACH ROW EXECUTE FUNCTION parameter_version_trigger();

-- 4. updated_at automático
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_cost_centers_updated_at
    BEFORE UPDATE ON cost_centers
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_rbac_users_updated_at
    BEFORE UPDATE ON rbac_users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_rbac_roles_updated_at
    BEFORE UPDATE ON rbac_roles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 5. Log de acesso automático (opcional - pode ser chamado por app)
CREATE OR REPLACE FUNCTION log_access(
    p_user_id UUID,
    p_action TEXT,
    p_resource TEXT,
    p_permitted BOOLEAN
) RETURNS VOID AS $$
BEGIN
    INSERT INTO rbac_access_log (
        tenant_id, user_id, action, resource, permitted
    )
    SELECT 
        u.tenant_id,
        p_user_id,
        p_action,
        p_resource,
        p_permitted
    FROM rbac_users u
    WHERE u.id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- 6. Validação de hierarquia de roles (detectar ciclos)
CREATE OR REPLACE FUNCTION validate_role_hierarchy()
RETURNS TRIGGER AS $$
DECLARE
    v_level INTEGER := 0;
    v_current UUID := NEW.parent_role_id;
BEGIN
    -- Verificar se está criando ciclo
    WHILE v_current IS NOT NULL AND v_level < 10 LOOP
        IF v_current = NEW.id THEN
            RAISE EXCEPTION 'Ciclo detectado na hierarquia de roles';
        END IF;
        
        SELECT parent_role_id, hierarchy_level + 1 
        INTO v_current, v_level
        FROM rbac_roles
        WHERE id = v_current;
    END LOOP;
    
    -- Atualizar nível
    IF NEW.parent_role_id IS NULL THEN
        NEW.hierarchy_level := 0;
    ELSE
        SELECT COALESCE(hierarchy_level + 1, 0) 
        INTO NEW.hierarchy_level
        FROM rbac_roles
        WHERE id = NEW.parent_role_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_role_hierarchy
    BEFORE INSERT OR UPDATE ON rbac_roles
    FOR EACH ROW EXECUTE FUNCTION validate_role_hierarchy();

-- ============================================================
-- VIEWS ANALÍTICAS
-- ============================================================

-- 1. Resumo de execuções de agentes
CREATE OR REPLACE VIEW v_agent_runs_summary AS
SELECT 
    tenant_id,
    session_id,
    agent_id,
    COUNT(*) as total_actions,
    COUNT(*) FILTER (WHERE status = 'completed') as completed_actions,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_actions,
    COUNT(*) FILTER (WHERE approval_required) as pending_approvals,
    SUM(COALESCE(cost_usd, 0)) as total_cost,
    SUM(COALESCE(tokens_in, 0) + COALESCE(tokens_out, 0)) as total_tokens,
    AVG(latency_ms)::INTEGER as avg_latency,
    MIN(created_at) as started_at,
    MAX(created_at) as last_action_at
FROM agent_action_log
GROUP BY tenant_id, session_id, agent_id;

-- 2. Resumo diário de auditoria
CREATE OR REPLACE VIEW v_audit_daily_summary AS
SELECT 
    tenant_id,
    DATE(created_at) as date,
    action_type,
    resource_type,
    COUNT(*) as count,
    COUNT(DISTINCT actor_id) as unique_actors,
    COUNT(DISTINCT session_id) as unique_sessions
FROM audit_log
GROUP BY tenant_id, DATE(created_at), action_type, resource_type;

-- 3. Métricas de precisão das decisões
CREATE OR REPLACE VIEW v_decision_accuracy AS
SELECT 
    tenant_id,
    model_name,
    model_version,
    DATE(created_at) as date,
    COUNT(*) as total_decisions,
    AVG(confidence_score)::NUMERIC(5,4) as avg_confidence,
    COUNT(*) FILTER (WHERE confidence_score < 0.7) as low_confidence_count,
    COUNT(*) FILTER (WHERE confidence_score >= 0.9) as high_confidence_count,
    AVG(latency_ms)::INTEGER as avg_latency,
    SUM(COALESCE(cost_usd, 0)) as total_cost
FROM decision_log
GROUP BY tenant_id, model_name, model_version, DATE(created_at);

-- 4. Performance de agentes
CREATE OR REPLACE VIEW v_agent_performance AS
SELECT 
    tenant_id,
    agent_id,
    tool_name,
    DATE(created_at) as date,
    COUNT(*) as total_calls,
    COUNT(*) FILTER (WHERE status = 'failed') as failures,
    AVG(latency_ms)::INTEGER as avg_latency,
    SUM(COALESCE(cost_usd, 0)) as total_cost,
    SUM(COALESCE(tokens_in, 0)) as total_tokens_in,
    SUM(COALESCE(tokens_out, 0)) as total_tokens_out
FROM agent_action_log
GROUP BY tenant_id, agent_id, tool_name, DATE(created_at);

-- 5. Permissões ativas de usuários
CREATE OR REPLACE VIEW v_user_permissions AS
SELECT 
    u.tenant_id,
    u.id as user_id,
    u.email,
    u.first_name || ' ' || COALESCE(u.last_name, '') as full_name,
    r.name as role_name,
    r.permissions,
    ur.valid_from,
    ur.valid_until,
    ur.cost_center_id,
    cc.name as cost_center_name
FROM rbac_users u
JOIN rbac_user_roles ur ON ur.user_id = u.id
JOIN rbac_roles r ON r.id = ur.role_id
LEFT JOIN cost_centers cc ON cc.id = ur.cost_center_id
WHERE (ur.valid_until IS NULL OR ur.valid_until > NOW())
  AND u.active = TRUE
  AND r.active = TRUE;

-- 6. Logs de acesso não permitidos
CREATE OR REPLACE VIEW v_access_denials AS
SELECT 
    tenant_id,
    user_id,
    action,
    resource,
    resource_id,
    denied_reason,
    ip_address,
    created_at
FROM rbac_access_log
WHERE permitted = FALSE
ORDER BY created_at DESC;

-- ============================================================
-- FUNCTIONS ADICIONAIS
-- ============================================================

-- Calcular score GO/NO-GO
CREATE OR REPLACE FUNCTION calculate_event_score(
    p_revenue NUMERIC,
    p_cmv NUMERIC,
    p_tenant_id UUID,
    OUT score TEXT,
    OUT margin_pct NUMERIC,
    OUT reason TEXT
) AS $$
DECLARE
    v_threshold_go NUMERIC;
    v_threshold_alert NUMERIC;
    v_threshold_critical NUMERIC;
BEGIN
    -- Buscar thresholds
    SELECT COALESCE((get_parameter(p_tenant_id, 'threshold_go')->>0)::NUMERIC, 35) INTO v_threshold_go;
    SELECT COALESCE((get_parameter(p_tenant_id, 'threshold_alert')->>0)::NUMERIC, 25) INTO v_threshold_alert;
    SELECT COALESCE((get_parameter(p_tenant_id, 'threshold_critical')->>0)::NUMERIC, 15) INTO v_threshold_critical;
    
    -- Calcular margem
    IF p_revenue > 0 THEN
        margin_pct := ((p_revenue - p_cmv) / p_revenue * 100)::NUMERIC(5,2);
    ELSE
        margin_pct := 0;
    END IF;
    
    -- Determinar score
    IF margin_pct >= v_threshold_go THEN
        score := 'GO';
        reason := format('Margem %.1f%% acima do threshold GO (%.1f%%)', margin_pct, v_threshold_go);
    ELSIF margin_pct >= v_threshold_alert THEN
        score := 'GO*';
        reason := format('Margem %.1f%% aceitável (entre %.1f%% e %.1f%%)', margin_pct, v_threshold_alert, v_threshold_go);
    ELSIF margin_pct >= v_threshold_critical THEN
        score := 'NO-GO';
        reason := format('Margem %.1f%% abaixo do ideal, revisar orçamento', margin_pct);
    ELSE
        score := 'CRITICAL';
        reason := format('Margem %.1f%% crítica - evento pode gerar prejuízo', margin_pct);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Calcular markup de preço
CREATE OR REPLACE FUNCTION calculate_price(
    p_cost NUMERIC,
    p_category TEXT,
    p_tenant_id UUID,
    OUT price NUMERIC,
    OUT markup_applied NUMERIC
) AS $$
BEGIN
    -- Buscar markup por categoria
    SELECT COALESCE((get_parameter(p_tenant_id, 'markup_' || p_category)->>0)::NUMERIC, 
                   (get_parameter(p_tenant_id, 'markup_default')->>0)::NUMERIC, 
                   2.0)
    INTO markup_applied;
    
    price := ROUND(p_cost * markup_applied, 2);
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- MIGRATION RECORD
-- ============================================================
INSERT INTO schema_migrations (version, description, executed_at, execution_time_ms)
VALUES (3, 'Advanced triggers, functions, and analytics views', NOW(), 0)
ON CONFLICT (version) DO UPDATE SET 
    description = EXCLUDED.description,
    executed_at = NOW();

-- ============================================================
-- COMMENTS
-- ============================================================
COMMENT ON VIEW v_agent_runs_summary IS 'Resumo de execuções de agentes por sessão';
COMMENT ON VIEW v_audit_daily_summary IS 'Resumo diário de atividades de auditoria';
COMMENT ON VIEW v_decision_accuracy IS 'Métricas de precisão das decisões da IA';
COMMENT ON VIEW v_agent_performance IS 'Performance de agentes (custo, tokens, latência)';
COMMENT ON VIEW v_user_permissions IS 'Permissões ativas de cada usuário';
COMMENT ON VIEW v_access_denials IS 'Tentativas de acesso negadas (segurança)';
