-- ============================================================
-- STATE MACHINE VIEWS
-- SPRINT 2: Operational Visibility
-- ============================================================

-- View: Estado atual das entidades
CREATE OR REPLACE VIEW v_entity_current_state AS
SELECT 
    es.id as state_id,
    es.tenant_id,
    es.entity_type,
    es.entity_id,
    es.current_state,
    es.previous_state,
    es.entered_at,
    es.entered_by,
    es.actor_type,
    es.reason,
    es.version,
    es.valid_from,
    es.created_at
FROM entity_states es
WHERE es.is_current = true;

-- View: Histórico completo de transições
CREATE OR REPLACE VIEW v_entity_transition_history AS
SELECT 
    st.id,
    st.tenant_id,
    st.entity_type,
    st.entity_id,
    st.from_state,
    st.to_state,
    st.actor_type,
    st.actor_id,
    st.reason,
    st.trigger_event,
    st.status,
    st.blocked_by,
    st.attempted_at,
    st.completed_at,
    st.duration_ms,
    st.error_message,
    -- Join com estado atual
    es.current_state as current_entity_state
FROM state_transitions st
LEFT JOIN entity_states es ON 
    es.tenant_id = st.tenant_id 
    AND es.entity_type = st.entity_type 
    AND es.entity_id = st.entity_id
    AND es.is_current = true
ORDER BY st.attempted_at DESC;

-- View: Eventos por estado atual (para dashboard)
CREATE OR REPLACE VIEW v_events_by_state AS
SELECT 
    e.company_id as tenant_id,
    e.id as event_id,
    e.event_id as event_code,
    e.event_type,
    e.event_date,
    e.client_name,
    e.num_guests,
    e.revenue_total,
    e.margin_pct,
    -- Estado atual
    COALESCE(es.current_state, 'UNKNOWN') as current_state,
    es.entered_at as state_entered_at,
    es.entered_by as state_changed_by,
    -- Dias desde entrar neste estado
    EXTRACT(DAY FROM (NOW() - es.entered_at)) as days_in_state,
    -- Última transição
    st.attempted_at as last_transition_at,
    st.status as last_transition_status,
    -- Flags
    CASE 
        WHEN es.current_state = 'PROPOSED' AND EXTRACT(DAY FROM (NOW() - es.entered_at)) > 7 THEN true
        ELSE false
    END as is_stale_proposal,
    CASE 
        WHEN es.current_state = 'APPROVED' AND EXTRACT(DAY FROM (NOW() - es.entered_at)) > 3 THEN true
        ELSE false
    END as needs_contract_urgent,
    CASE 
        WHEN es.current_state = 'PLANNED' AND e.event_date < NOW() + INTERVAL '48 hours' THEN true
        ELSE false
    END as production_overdue,
    CASE 
        WHEN es.current_state IN ('READY_FOR_EXECUTION', 'IN_PRODUCTION') AND e.event_date < NOW() THEN true
        ELSE false
    END as execution_overdue
FROM events e
LEFT JOIN entity_states es ON 
    es.tenant_id = e.company_id 
    AND es.entity_type = 'event' 
    AND es.entity_id = e.id
    AND es.is_current = true
LEFT JOIN state_transitions st ON 
    st.tenant_id = e.company_id 
    AND st.entity_type = 'event' 
    AND st.entity_id = e.id
    AND st.attempted_at = (
        SELECT MAX(attempted_at) 
        FROM state_transitions st2 
        WHERE st2.tenant_id = e.company_id 
        AND st2.entity_type = 'event' 
        AND st2.entity_id = e.id
    );

-- View: Gargalos operacionais
CREATE OR REPLACE VIEW v_operational_bottlenecks AS
SELECT 
    tenant_id,
    current_state as bottleneck_state,
    COUNT(*) as event_count,
    AVG(days_in_state) as avg_days_stalled,
    MIN(days_in_state) as min_days_stalled,
    MAX(days_in_state) as max_days_stalled,
    STRING_AGG(DISTINCT event_id, ',') as sample_events
FROM v_events_by_state
WHERE 
    -- Estados que indicam gargalo se durarem muito
    (current_state = 'QUALIFIED' AND days_in_state > 3)
    OR (current_state = 'PROPOSED' AND days_in_state > 7)
    OR (current_state = 'APPROVED' AND days_in_state > 2)
    OR (current_state = 'CONTRACTED' AND days_in_state > 5)
    OR (current_state = 'PLANNED' AND production_overdue = true)
    OR (current_state = 'READY_FOR_PRODUCTION' AND days_in_state > 1)
    OR (current_state = 'READY_FOR_EXECUTION' AND execution_overdue = true)
GROUP BY tenant_id, current_state
ORDER BY event_count DESC;

-- View: Taxa de sucesso de transições
CREATE OR REPLACE VIEW v_transition_success_rates AS
SELECT 
    tenant_id,
    from_state,
    to_state,
    COUNT(*) as total_attempts,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful,
    SUM(CASE WHEN status = 'blocked' THEN 1 ELSE 0 END) as blocked,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
    ROUND(
        (SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END)::numeric / COUNT(*)) * 100, 
        2
    ) as success_rate_pct,
    AVG(duration_ms) as avg_duration_ms
FROM state_transitions
GROUP BY tenant_id, from_state, to_state
ORDER BY total_attempts DESC;

-- View: Pipeline de eventos (funnel)
CREATE OR REPLACE VIEW v_event_pipeline_funnel AS
SELECT 
    tenant_id,
    current_state,
    COUNT(*) as event_count,
    SUM(revenue_total) as total_revenue,
    AVG(revenue_total) as avg_revenue,
    MIN(revenue_total) as min_revenue,
    MAX(revenue_total) as max_revenue,
    AVG(margin_pct) as avg_margin
FROM v_events_by_state
GROUP BY tenant_id, current_state
ORDER BY 
    CASE current_state
        WHEN 'LEAD' THEN 1
        WHEN 'QUALIFIED' THEN 2
        WHEN 'PROPOSED' THEN 3
        WHEN 'APPROVED' THEN 4
        WHEN 'CONTRACTED' THEN 5
        WHEN 'PLANNED' THEN 6
        WHEN 'READY_FOR_PRODUCTION' THEN 7
        WHEN 'IN_PRODUCTION' THEN 8
        WHEN 'READY_FOR_EXECUTION' THEN 9
        WHEN 'EXECUTING' THEN 10
        WHEN 'CLOSED' THEN 11
        WHEN 'ANALYZED' THEN 12
        ELSE 99
    END;

-- View: Eventos em risco (precisam de atenção)
CREATE OR REPLACE VIEW v_events_at_risk AS
SELECT 
    event_id,
    tenant_id as company_id,
    event_code,
    event_type,
    client_name,
    event_date,
    current_state,
    state_entered_at,
    days_in_state,
    revenue_total,
    margin_pct,
    last_transition_at,
    -- Categoria de risco
    CASE 
        WHEN is_stale_proposal THEN 'Proposta Estagnada'
        WHEN needs_contract_urgent THEN 'Contrato Pendente'
        WHEN production_overdue THEN 'Produção Atrasada'
        WHEN execution_overdue THEN 'Execução Atrasada'
        ELSE 'Alerta Operacional'
    END as risk_category,
    -- Prioridade
    CASE 
        WHEN execution_overdue THEN 'CRITICAL'
        WHEN production_overdue THEN 'HIGH'
        WHEN needs_contract_urgent AND days_in_state > 5 THEN 'HIGH'
        WHEN is_stale_proposal AND days_in_state > 14 THEN 'MEDIUM'
        ELSE 'LOW'
    END as priority
FROM v_events_by_state
WHERE 
    is_stale_proposal = true
    OR needs_contract_urgent = true
    OR production_overdue = true
    OR execution_overdue = true
ORDER BY 
    CASE 
        WHEN priority = 'CRITICAL' THEN 1
        WHEN priority = 'HIGH' THEN 2
        WHEN priority = 'MEDIUM' THEN 3
        ELSE 4
    END,
    days_in_state DESC;

-- View: Performance de transições por actor
CREATE OR REPLACE VIEW v_actor_transition_performance AS
SELECT 
    tenant_id,
    actor_type,
    actor_id,
    COUNT(*) as total_transitions,
    AVG(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) * 100 as success_rate_pct,
    AVG(duration_ms) as avg_duration_ms,
    COUNT(CASE WHEN status = 'blocked' THEN 1 END) as blocked_count
FROM state_transitions
GROUP BY tenant_id, actor_type, actor_id
ORDER BY total_transitions DESC;
