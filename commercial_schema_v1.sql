-- ============================================================
-- SCHEMA COMERCIAL v1 — Orkestra Finance Brain
-- Empresas: QOpera, Laohana, Robusta
-- Módulos: products_catalog | pricing_rules | discount_policies | 
--          sales_targets | sales_pipeline | upsell_rules
-- ============================================================

-- ============================================================
-- EXTENSÕES
-- ============================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- COMPANIES (tabela base, já deve existir)
-- ============================================================
-- CREATE TABLE IF NOT EXISTS companies (...);

-- ============================================================
-- 1. PRODUCTS_CATALOG (Catálogo de Produtos/Serviços)
-- ============================================================
CREATE TABLE products_catalog (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    external_id TEXT,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL CHECK (category IN ('produto', 'servico', 'pacote')),
    subcategory TEXT NOT NULL,
    base_cost NUMERIC(15, 2) NOT NULL DEFAULT 0,
    suggested_price NUMERIC(15, 2) NOT NULL DEFAULT 0,
    margin_min DECIMAL(5, 2) NOT NULL DEFAULT 20.00,
    margin_target DECIMAL(5, 2) NOT NULL DEFAULT 35.00,
    unit_type TEXT NOT NULL CHECK (unit_type IN ('pessoa', 'hora', 'metro', 'unidade', 'kit', 'evento')),
    min_quantity INTEGER DEFAULT 1,
    max_quantity INTEGER DEFAULT 9999,
    is_active BOOLEAN DEFAULT TRUE,
    is_upsell BOOLEAN DEFAULT FALSE,
    bundle_rules JSONB DEFAULT '{}',
    seasonal_mult JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_margin CHECK (margin_min <= margin_target),
    CONSTRAINT chk_quantities CHECK (min_quantity <= max_quantity),
    UNIQUE(company_id, external_id)
);

CREATE INDEX idx_products_company ON products_catalog(company_id);
CREATE INDEX idx_products_category ON products_catalog(company_id, category);
CREATE INDEX idx_products_subcategory ON products_catalog(company_id, subcategory);
CREATE INDEX idx_products_active ON products_catalog(company_id) WHERE is_active = TRUE;
CREATE INDEX idx_products_upsell ON products_catalog(company_id) WHERE is_upsell = TRUE;

COMMENT ON TABLE products_catalog IS 'Catálogo de produtos e serviços das 3 empresas';

-- ============================================================
-- 2. PRICING_RULES (Regras de Precificação)
-- ============================================================
CREATE TABLE pricing_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products_catalog(id),
    rule_type TEXT NOT NULL CHECK (rule_type IN ('markup', 'tier', 'volume', 'seasonal', 'loyalty', 'combo')),
    rule_name TEXT NOT NULL,
    min_volume INTEGER DEFAULT 0,
    max_volume INTEGER DEFAULT 999999,
    markup_mult DECIMAL(5, 3) DEFAULT 2.000,
    discount_max DECIMAL(5, 2) DEFAULT 15.00,
    conditions JSONB DEFAULT '{}',
    priority INTEGER DEFAULT 100,
    valid_from DATE DEFAULT CURRENT_DATE,
    valid_until DATE DEFAULT '2099-12-31',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID NOT NULL,
    
    CONSTRAINT chk_dates CHECK (valid_from <= valid_until)
);

CREATE INDEX idx_pricing_company ON pricing_rules(company_id);
CREATE INDEX idx_pricing_product ON pricing_rules(product_id);
CREATE INDEX idx_pricing_type ON pricing_rules(company_id, rule_type);
CREATE INDEX idx_pricing_valid ON pricing_rules(company_id, valid_from, valid_until) WHERE is_active = TRUE;
CREATE INDEX idx_pricing_priority ON pricing_rules(company_id, priority DESC);

-- ============================================================
-- 3. DISCOUNT_POLICIES (Políticas de Desconto)
-- ============================================================
CREATE TABLE discount_policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    role_id UUID REFERENCES rbac_roles(id),
    policy_name TEXT NOT NULL,
    max_discount_pct DECIMAL(5, 2) NOT NULL DEFAULT 5.00,
    max_discount_value NUMERIC(15, 2) DEFAULT 500.00,
    min_margin_pct DECIMAL(5, 2) DEFAULT 15.00,
    approval_required BOOLEAN DEFAULT TRUE,
    approval_threshold NUMERIC(15, 2) DEFAULT 1000.00,
    reason_required BOOLEAN DEFAULT TRUE,
    exceptions JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_max_discount CHECK (max_discount_pct <= 50.00)
);

CREATE INDEX idx_discount_policies_company ON discount_policies(company_id);
CREATE INDEX idx_discount_policies_role ON discount_policies(role_id);

-- ============================================================
-- 4. SALES_TARGETS (Metas Comerciais)
-- ============================================================
CREATE TABLE sales_targets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES rbac_users(id),
    cost_center_id UUID REFERENCES cost_centers(id),
    period_type TEXT NOT NULL CHECK (period_type IN ('monthly', 'quarterly', 'yearly')),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    target_revenue NUMERIC(15, 2) NOT NULL DEFAULT 0,
    target_deals INTEGER NOT NULL DEFAULT 0,
    target_leads INTEGER NOT NULL DEFAULT 0,
    target_margin DECIMAL(5, 2) DEFAULT 30.00,
    weight_new DECIMAL(3, 2) DEFAULT 0.60,
    weight_recurring DECIMAL(3, 2) DEFAULT 0.40,
    bonus_threshold DECIMAL(5, 2) DEFAULT 100.00,
    bonus_multiplier DECIMAL(4, 2) DEFAULT 1.50,
    achieved_revenue NUMERIC(15, 2) DEFAULT 0,
    achieved_deals INTEGER DEFAULT 0,
    achieved_leads INTEGER DEFAULT 0,
    achieved_margin DECIMAL(5, 2) DEFAULT 0,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'cancelled')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_weights CHECK (weight_new + weight_recurring = 1.00)
);

CREATE INDEX idx_targets_company ON sales_targets(company_id, period_start);
CREATE INDEX idx_targets_user ON sales_targets(user_id, period_start);
CREATE INDEX idx_targets_period ON sales_targets(company_id, period_type, period_start);

-- ============================================================
-- 5. SALES_PIPELINE (Pipeline de Vendas)
-- ============================================================
CREATE TYPE pipeline_stage AS ENUM ('lead', 'qualificacao', 'diagnostico', 'proposta', 'negociacao', 'fechamento', 'onboarding', 'closed');
CREATE TYPE close_reason AS ENUM ('won', 'lost', 'cancelled', 'postponed', 'in_progress');

CREATE TABLE sales_pipeline (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    opportunity_id TEXT UNIQUE NOT NULL,
    -- Cliente
    client_name TEXT NOT NULL,
    client_email TEXT,
    client_phone TEXT,
    client_company TEXT,
    -- Evento
    event_type TEXT NOT NULL,
    event_date DATE,
    guests_estimate INTEGER DEFAULT 0,
    budget_estimate NUMERIC(15, 2) DEFAULT 0,
    -- Pipeline
    current_stage pipeline_stage NOT NULL DEFAULT 'lead',
    stage_history JSONB DEFAULT '[]',
    assigned_to UUID REFERENCES rbac_users(id),
    probability DECIMAL(5, 2) DEFAULT 10.00,
    expected_value NUMERIC(15, 2) DEFAULT 0,
    -- Produtos
    products JSONB DEFAULT '[]',
    total_value NUMERIC(15, 2) DEFAULT 0,
    discount_requested DECIMAL(5, 2) DEFAULT 0,
    discount_approved DECIMAL(5, 2) DEFAULT 0,
    final_value NUMERIC(15, 2) DEFAULT 0,
    margin_projected DECIMAL(5, 2) DEFAULT 0,
    -- Fechamento
    close_reason close_reason,
    lost_reason TEXT,
    closed_at TIMESTAMPTZ,
    closed_value NUMERIC(15, 2),
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_probability CHECK (probability >= 0 AND probability <= 100),
    CONSTRAINT chk_dates CHECK (event_date >= created_at::date OR event_date IS NULL)
);

CREATE INDEX idx_pipeline_company ON sales_pipeline(company_id, created_at DESC);
CREATE INDEX idx_pipeline_stage ON sales_pipeline(company_id, current_stage);
CREATE INDEX idx_pipeline_user ON sales_pipeline(assigned_to, current_stage);
CREATE INDEX idx_pipeline_event_date ON sales_pipeline(event_date);
CREATE INDEX idx_pipeline_probability ON sales_pipeline(company_id, probability DESC);
CREATE INDEX idx_pipeline_active ON sales_pipeline(company_id) WHERE current_stage != 'closed';

-- ============================================================
-- 6. UPSELL_RULES (Regras de Upsell)
-- ============================================================
CREATE TYPE upsell_rule_type AS ENUM ('automatic', 'manual', 'conditional');

CREATE TABLE upsell_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    trigger_product_id UUID NOT NULL REFERENCES products_catalog(id),
    suggested_product_id UUID NOT NULL REFERENCES products_catalog(id),
    rule_type upsell_rule_type DEFAULT 'conditional',
    condition_logic JSONB DEFAULT '{}',
    discount_auto DECIMAL(5, 2) DEFAULT 5.00,
    urgency_text TEXT,
    max_suggestions INTEGER DEFAULT 3,
    conversion_target DECIMAL(5, 2) DEFAULT 15.00,
    times_triggered INTEGER DEFAULT 0,
    times_converted INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 100,
    valid_from DATE DEFAULT CURRENT_DATE,
    valid_until DATE DEFAULT '2099-12-31',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_products CHECK (trigger_product_id != suggested_product_id)
);

CREATE INDEX idx_upsell_company ON upsell_rules(company_id);
CREATE INDEX idx_upsell_trigger ON upsell_rules(trigger_product_id);
CREATE INDEX idx_upsell_suggested ON upsell_rules(suggested_product_id);
CREATE INDEX idx_upsell_active ON upsell_rules(company_id) WHERE is_active = TRUE;

-- ============================================================
-- FUNÇÕES COMERCIAIS
-- ============================================================

-- 1. Calcular preço com regras
CREATE OR REPLACE FUNCTION calculate_price_with_rules(
    p_product_id UUID,
    p_quantity INTEGER,
    p_date DATE DEFAULT CURRENT_DATE
) RETURNS TABLE (base_price NUMERIC, final_price NUMERIC, rule_applied TEXT) AS $$
DECLARE
    v_product RECORD;
    v_rule RECORD;
    v_base NUMERIC;
    v_final NUMERIC;
    v_rule_name TEXT := 'default';
BEGIN
    -- Buscar produto
    SELECT * INTO v_product FROM products_catalog WHERE id = p_product_id AND is_active = TRUE;
    
    IF v_product IS NULL THEN
        RAISE EXCEPTION 'Produto não encontrado ou inativo';
    END IF;
    
    -- Preço base
    v_base := v_product.suggested_price * p_quantity;
    v_final := v_base;
    
    -- Aplicar regras
    FOR v_rule IN 
        SELECT * FROM pricing_rules 
        WHERE product_id = p_product_id 
          AND is_active = TRUE
          AND p_date BETWEEN valid_from AND valid_until
          AND p_quantity BETWEEN min_volume AND max_volume
        ORDER BY priority DESC, created_at DESC
        LIMIT 1
    LOOP
        v_rule_name := v_rule.rule_name;
        
        CASE v_rule.rule_type
            WHEN 'markup' THEN
                v_final := v_product.base_cost * v_rule.markup_mult * p_quantity;
            WHEN 'tier' THEN
                v_final := v_base * v_rule.markup_mult;
            WHEN 'volume' THEN
                v_final := v_base * (1 - (LEAST(p_quantity, v_rule.max_volume)::NUMERIC / v_rule.max_volume) * 0.1);
        END CASE;
    END LOOP;
    
    RETURN QUERY SELECT v_base, v_final, v_rule_name;
END;
$$ LANGUAGE plpgsql;

-- 2. Verificar se desconto é permitido
CREATE OR REPLACE FUNCTION check_discount_allowed(
    p_user_id UUID,
    p_discount_pct DECIMAL(5,2),
    p_discount_value NUMERIC,
    p_margin_pct DECIMAL(5,2)
) RETURNS TABLE (allowed BOOLEAN, requires_approval BOOLEAN, message TEXT) AS $$
DECLARE
    v_user_role RECORD;
    v_policy RECORD;
BEGIN
    -- Buscar policy do usuário
    SELECT dp.* INTO v_policy
    FROM rbac_user_roles ur
    JOIN rbac_roles r ON r.id = ur.role_id
    JOIN discount_policies dp ON dp.role_id = r.id
    WHERE ur.user_id = p_user_id
      AND (ur.valid_until IS NULL OR ur.valid_until > NOW())
      AND dp.is_active = TRUE
    ORDER BY dp.max_discount_pct DESC
    LIMIT 1;
    
    IF v_policy IS NULL THEN
        RETURN QUERY SELECT FALSE, TRUE, 'Nenhuma política de desconto encontrada para seu perfil'::TEXT;
        RETURN;
    END IF;
    
    -- Verificar margem mínima
    IF p_margin_pct < v_policy.min_margin_pct THEN
        RETURN QUERY SELECT FALSE, TRUE, 
            format('Margem %.1f%% abaixo do mínimo permitido (%.1f%%)', 
                   p_margin_pct, v_policy.min_margin_pct)::TEXT;
        RETURN;
    END IF;
    
    -- Verificar % máximo
    IF p_discount_pct > v_policy.max_discount_pct THEN
        RETURN QUERY SELECT FALSE, TRUE, 
            format('Desconto %.1f%% excede seu limite de %.1f%%', 
                   p_discount_pct, v_policy.max_discount_pct)::TEXT;
        RETURN;
    END IF;
    
    -- Verificar valor máximo
    IF p_discount_value > v_policy.max_discount_value THEN
        RETURN QUERY SELECT FALSE, v_policy.approval_required, 
            format('Valor de desconto excede R$ %.2f (requer aprovação)', 
                   v_policy.max_discount_value)::TEXT;
        RETURN;
    END IF;
    
    -- Verificar se precisa de aprovação por threshold
    IF p_discount_value > v_policy.approval_threshold THEN
        RETURN QUERY SELECT TRUE, TRUE, 
            format('Desconto aceito, mas requer aprovação (acima de R$ %.2f)', 
                   v_policy.approval_threshold)::TEXT;
        RETURN;
    END IF;
    
    -- Tudo OK
    RETURN QUERY SELECT TRUE, FALSE, 'Desconto aprovado automaticamente'::TEXT;
END;
$$ LANGUAGE plpgsql;

-- 3. Avançar estágio do pipeline
CREATE OR REPLACE FUNCTION advance_pipeline_stage(
    p_opportunity_id UUID,
    p_new_stage pipeline_stage,
    p_notes TEXT DEFAULT NULL
) RETURNS TABLE (success BOOLEAN, message TEXT) AS $$
DECLARE
    v_opp RECORD;
    v_probabilities CONSTANT DECIMAL(5,2)[] := ARRAY[10.00, 25.00, 40.00, 60.00, 75.00, 90.00, 100.00, 0.00];
    v_stage_idx INTEGER;
    v_new_idx INTEGER;
BEGIN
    SELECT * INTO v_opp FROM sales_pipeline WHERE id = p_opportunity_id;
    
    IF v_opp IS NULL THEN
        RETURN QUERY SELECT FALSE, 'Oportunidade não encontrada'::TEXT;
        RETURN;
    END IF;
    
    -- Validar transição
    v_stage_idx := array_position(ARRAY['lead','qualificacao','diagnostico','proposta','negociacao','fechamento','onboarding','closed']::TEXT[], v_opp.current_stage::TEXT);
    v_new_idx := array_position(ARRAY['lead','qualificacao','diagnostico','proposta','negociacao','fechamento','onboarding','closed']::TEXT[], p_new_stage::TEXT);
    
    IF v_new_idx < v_stage_idx AND p_new_stage != 'closed' THEN
        RETURN QUERY SELECT FALSE, 'Não é possível retroceder estágios'::TEXT;
        RETURN;
    END IF;
    
    -- Atualizar
    UPDATE sales_pipeline 
    SET current_stage = p_new_stage,
        probability = v_probabilities[v_new_idx],
        expected_value = total_value * (v_probabilities[v_new_idx] / 100),
        stage_history = stage_history || jsonb_build_array(jsonb_build_object(
            'from', v_opp.current_stage,
            'to', p_new_stage,
            'at', NOW(),
            'notes', p_notes
        )),
        last_activity_at = NOW(),
        updated_at = NOW()
    WHERE id = p_opportunity_id;
    
    RETURN QUERY SELECT TRUE, format('Avançado de %s para %s', v_opp.current_stage, p_new_stage)::TEXT;
END;
$$ LANGUAGE plpgsql;

-- 4. Sugerir upsells
CREATE OR REPLACE FUNCTION suggest_upsells(
    p_product_id UUID,
    p_client_id UUID DEFAULT NULL
) RETURNS TABLE (product_id UUID, name TEXT, discount DECIMAL(5,2), urgency TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ur.suggested_product_id,
        pc.name,
        ur.discount_auto,
        ur.urgency_text
    FROM upsell_rules ur
    JOIN products_catalog pc ON pc.id = ur.suggested_product_id
    WHERE ur.trigger_product_id = p_product_id
      AND ur.is_active = TRUE
      AND CURRENT_DATE BETWEEN ur.valid_from AND ur.valid_until
      AND ur.times_triggered < ur.max_suggestions
    ORDER BY ur.priority DESC, ur.conversion_target DESC
    LIMIT 3;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- VIEWS COMERCIAIS
-- ============================================================

-- Pipeline ativo por empresa
CREATE OR REPLACE VIEW v_pipeline_active AS
SELECT 
    sp.company_id,
    t.name as company_name,
    sp.current_stage,
    COUNT(*) as opportunities,
    SUM(sp.expected_value) as weighted_pipeline,
    SUM(sp.total_value) as gross_pipeline,
    AVG(sp.probability) as avg_probability
FROM sales_pipeline sp
JOIN tenants t ON t.id = sp.company_id
WHERE sp.current_stage != 'closed'
GROUP BY sp.company_id, t.name, sp.current_stage;

-- Performance de vendedores
CREATE OR REPLACE VIEW v_sales_performance AS
SELECT 
    sp.company_id,
    sp.assigned_to,
    u.email as vendedor,
    u.first_name || ' ' || COALESCE(u.last_name, '') as vendedor_name,
    COUNT(*) FILTER (WHERE sp.close_reason = 'won' AND sp.closed_at >= DATE_TRUNC('month', NOW())) as won_this_month,
    COUNT(*) FILTER (WHERE sp.closed_at >= DATE_TRUNC('month', NOW())) as total_closed_this_month,
    SUM(sp.closed_value) FILTER (WHERE sp.close_reason = 'won' AND sp.closed_at >= DATE_TRUNC('month', NOW())) as revenue_this_month,
    AVG(sp.probability) FILTER (WHERE sp.current_stage != 'closed') as avg_pipeline_probability
FROM sales_pipeline sp
JOIN rbac_users u ON u.id = sp.assigned_to
WHERE sp.assigned_to IS NOT NULL
GROUP BY sp.company_id, sp.assigned_to, u.email, u.first_name, u.last_name;

-- Metas vs Realizado
CREATE OR REPLACE VIEW v_targets_progress AS
SELECT 
    st.id,
    st.company_id,
    t.name as company,
    st.user_id,
    u.email as user_email,
    st.period_start,
    st.period_end,
    st.target_revenue,
    st.target_deals,
    st.achieved_revenue,
    st.achieved_deals,
    ROUND(st.achieved_revenue / NULLIF(st.target_revenue, 0) * 100, 2) as revenue_progress_pct,
    ROUND(st.achieved_deals::NUMERIC / NULLIF(st.target_deals, 0) * 100, 2) as deals_progress_pct
FROM sales_targets st
JOIN tenants t ON t.id = st.company_id
LEFT JOIN rbac_users u ON u.id = st.user_id
WHERE st.status = 'active';

-- ============================================================
-- SEED DATA (Produtos de Exemplo)
-- ============================================================

-- Inserir produtos QOpera
INSERT INTO products_catalog (company_id, external_id, name, description, category, subcategory, base_cost, suggested_price, margin_min, margin_target, unit_type, min_quantity)
SELECT 
    t.id,
    'QOP-COQUETEL-STD',
    'Coquetel Executivo Standard',
    'Coquetel corporativo com 10 opções de finger food',
    'servico',
    'coquel_executivo',
    65.00,
    120.00,
    25.00,
    45.00,
    'pessoa',
    30
FROM tenants t WHERE t.slug = 'qopera'
ON CONFLICT DO NOTHING;

-- Inserir produtos Laohana
INSERT INTO products_catalog (company_id, external_id, name, description, category, subcategory, base_cost, suggested_price, margin_min, margin_target, unit_type, min_quantity)
SELECT 
    t.id,
    'LAO-BUFFET-CHURR',
    'Buffet de Churrasco',
    'Churrasco completo com 15 cortes de carne + buffet de saladas',
    'servico',
    'buffet_churrasco',
    85.00,
    150.00,
    28.00,
    40.00,
    'pessoa',
    50
FROM tenants t WHERE t.slug = 'laohana'
ON CONFLICT DO NOTHING;

-- Inserir produtos Robusta
INSERT INTO products_catalog (company_id, external_id, name, description, category, subcategory, base_cost, suggested_price, margin_min, margin_target, unit_type, min_quantity)
SELECT 
    t.id,
    'ROB-TENDA-10X10',
    'Tenda 10x10m',
    'Tenda estruturada 10x10m com iluminação básica',
    'produto',
    'tenda',
    2500.00,
    4500.00,
    25.00,
    40.00,
    'unidade',
    1
FROM tenants t WHERE t.slug = 'robusta'
ON CONFLICT DO NOTHING;

COMMENT ON FUNCTION calculate_price_with_rules IS 'Calcula preço aplicando regras de precificação';
COMMENT ON FUNCTION check_discount_allowed IS 'Valida se desconto é permitido pelo perfil do usuário';
COMMENT ON FUNCTION advance_pipeline_stage IS 'Avança oportunidade para próximo estágio do funil';
COMMENT ON FUNCTION suggest_upsells IS 'Retorna produtos de upsell recomendados';
