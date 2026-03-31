-- ============================================================
-- ORKESTRA FINANCE BRAIN - Analytics Views
-- ============================================================

-- View: Event Summary
CREATE VIEW vw_event_summary AS
SELECT 
    e.id,
    e.event_id,
    e.n_ctt,
    e.company_id,
    e.client_name,
    e.event_type,
    e.event_date,
    e.status,
    e.revenue_total,
    e.cmv_total,
    e.net_profit,
    e.margin_pct,
    CASE 
        WHEN e.margin_pct >= 40 THEN 'EXCELLENT'
        WHEN e.margin_pct >= 25 THEN 'GOOD'
        WHEN e.margin_pct >= 15 THEN 'WARNING'
        ELSE 'CRITICAL'
    END as margin_status
FROM events e
ORDER BY e.event_date DESC;

-- View: Monthly Performance
CREATE VIEW vw_monthly_performance AS
SELECT 
    DATE_TRUNC('month', e.event_date) as month,
    COUNT(*) as total_events,
    SUM(e.revenue_total) as total_revenue,
    SUM(e.cmv_total) as total_cmv,
    SUM(e.net_profit) as total_profit,
    AVG(e.margin_pct) as avg_margin,
    MIN(e.margin_pct) as min_margin,
    MAX(e.margin_pct) as max_margin
FROM events e
WHERE e.status = 'completed'
GROUP BY DATE_TRUNC('month', e.event_date)
ORDER BY month DESC;

-- View: Client Performance
CREATE VIEW vw_client_performance AS
SELECT 
    e.client_name,
    COUNT(*) as total_events,
    SUM(e.revenue_total) as total_revenue,
    SUM(e.net_profit) as total_profit,
    AVG(e.margin_pct) as avg_margin,
    MAX(e.event_date) as last_event
FROM events e
WHERE e.status = 'completed'
GROUP BY e.client_name
ORDER BY total_revenue DESC;

-- View: Recipe Cost Analysis
CREATE VIEW vw_recipe_cost_analysis AS
SELECT 
    r.id,
    r.name,
    r.category,
    r.portion_size,
    r.portion_unit,
    COALESCE(rc.total_cost, 0) as total_cost,
    COALESCE(rc.cost_per_portion, 0) as cost_per_portion,
    r.target_selling_price,
    CASE 
        WHEN r.target_selling_price > 0 
        THEN ((r.target_selling_price - COALESCE(rc.cost_per_portion, 0)) / r.target_selling_price * 100)
        ELSE 0
    END as margin_pct
FROM recipes r
LEFT JOIN recipe_costs rc ON r.id = rc.recipe_id
WHERE r.active = true;

-- View: Inventory Status
CREATE VIEW vw_inventory_status AS
SELECT 
    ii.id,
    ii.name,
    ii.category,
    ii.current_stock,
    ii.unit,
    ii.weighted_average_cost,
    ii.last_purchase_price,
    ii.supplier,
    CASE 
        WHEN ii.current_stock <= ii.min_stock_threshold THEN 'CRITICAL'
        WHEN ii.current_stock <= (ii.min_stock_threshold * 1.5) THEN 'LOW'
        WHEN ii.current_stock >= (ii.max_stock_threshold * 0.9) THEN 'EXCESS'
        ELSE 'OK'
    END as stock_status,
    (ii.current_stock * ii.weighted_average_cost) as inventory_value
FROM inventory_items ii
ORDER BY stock_status, category, name;

-- View: Agent Run Performance
CREATE VIEW vw_agent_run_performance AS
SELECT 
    ar.id,
    ar.workflow_type,
    ar.status,
    ar.risk_level,
    ar.total_cost,
    ar.total_tokens,
    ar.latency_ms,
    ar.created_at,
    ar.finished_at,
    EXTRACT(EPOCH FROM (ar.finished_at - ar.created_at)) as duration_seconds,
    CASE 
        WHEN ar.status = 'completed' THEN 'SUCCESS'
        WHEN ar.status = 'failed' THEN 'FAILURE'
        ELSE 'PENDING'
    END as run_outcome
FROM agent_runs ar
ORDER BY ar.created_at DESC;

-- View: Approval Queue
CREATE VIEW vw_approval_queue AS
SELECT 
    ap.id,
    ap.agent_run_id,
    ap.risk_level,
    ap.requested_action,
    ap.justification,
    ap.status,
    ap.created_at,
    ap.approved_by,
    ap.approved_at,
    DATEDIFF('day', ap.created_at, COALESCE(ap.approved_at, CURRENT_DATE)) as days_pending
FROM approvals ap
WHERE ap.status = 'pending'
ORDER BY ap.created_at ASC;

-- View: Memory Insights
CREATE VIEW vw_memory_insights AS
SELECT 
    mi.id,
    mi.memory_type,
    mi.title,
    mi.tags,
    mi.confidence_score,
    mi.created_at,
    CASE 
        WHEN mi.confidence_score >= 0.9 THEN 'HIGH_CONFIDENCE'
        WHEN mi.confidence_score >= 0.7 THEN 'MEDIUM_CONFIDENCE'
        ELSE 'LOW_CONFIDENCE'
    END as confidence_level
FROM memory_items mi
ORDER BY mi.created_at DESC;

-- Indexes for performance
CREATE INDEX idx_events_date ON events(event_date);
CREATE INDEX idx_events_company ON events(company_id);
CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_agent_runs_created ON agent_runs(created_at);
CREATE INDEX idx_approvals_status ON approvals(status);

-- Refresh materialized views (if needed)
-- CREATE MATERIALIZED VIEW mv_event_metrics AS ...
