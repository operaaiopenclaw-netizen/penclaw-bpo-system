-- ============================================================
-- MIGRATION V002 — SEED DATA
-- Dados iniciais: permissions, roles, system parameters, admin user
-- ============================================================

-- ============================================================
-- PERMISSIONS (códigos de permissão do sistema)
-- ============================================================
INSERT INTO rbac_permissions (code, name, description, resource, action, conditions) VALUES
-- Eventos
('event.read', 'Ver Eventos', 'Visualizar eventos e orçamentos', 'event', 'read', NULL),
('event.write', 'Editar Eventos', 'Criar e editar eventos', 'event', 'write', NULL),
('event.delete', 'Excluir Eventos', 'Remover eventos do sistema', 'event', 'delete', NULL),
('event.approve', 'Aprovar Eventos', 'Aprovar eventos críticos', 'event', 'approve', NULL),

-- Financeiro
('financial.read', 'Ver Financeiro', 'Visualizar dados financeiros', 'financial', 'read', NULL),
('financial.write', 'Editar Financeiro', 'Editar dados financeiros', 'financial', 'write', NULL),
('financial.export', 'Exportar Financeiro', 'Exportar relatórios financeiros', 'financial', 'export', NULL),

-- Pricing
('pricing.calculate', 'Calcular Preços', 'Executar calculadora de preços', 'pricing', 'execute', NULL),
('pricing.read', 'Ver Preços', 'Visualizar configurações de pricing', 'pricing', 'read', NULL),
('pricing.write', 'Editar Preços', 'Modificar configurações de pricing', 'pricing', 'write', NULL),

-- Agentes
('agent.run', 'Executar Agentes', 'Executar agentes de IA', 'agent', 'execute', NULL),
('agent.read', 'Ver Agentes', 'Visualizar logs de agentes', 'agent', 'read', NULL),
('agent.configure', 'Configurar Agentes', 'Configurar parâmetros de agentes', 'agent', 'configure', NULL),

-- Auditoria
('audit.read', 'Ver Auditoria', 'Visualizar logs de auditoria', 'audit', 'read', NULL),
('audit.export', 'Exportar Auditoria', 'Exportar logs de auditoria', 'audit', 'export', NULL),

-- Administração
('admin.full', 'Administração Completa', 'Acesso total ao sistema', '*', '*', NULL),
('admin.users', 'Gerenciar Usuários', 'Criar e gerenciar usuários', 'admin', 'users', NULL),
('admin.roles', 'Gerenciar Roles', 'Criar e editar papéis', 'admin', 'roles', NULL),
('admin.parameters', 'Gerenciar Parâmetros', 'Configurar parâmetros do sistema', 'admin', 'parameters', NULL)
ON CONFLICT (code) DO NOTHING;

-- ============================================================
-- SYSTEM ROLES
-- ============================================================
-- Super Admin (acesso total)
INSERT INTO rbac_roles (tenant_id, name, description, permissions, hierarchy_level, is_system)
SELECT 
    id as tenant_id,
    'super_admin' as name,
    'Acesso total ao sistema - apenas para administradores de infra' as description,
    '[{"resource": "*", "action": "*"}]'::jsonb as permissions,
    0 as hierarchy_level,
    true as is_system
FROM tenants WHERE slug = 'orkestra'
ON CONFLICT DO NOTHING;

-- Admin (todas as permissões operacionais)
INSERT INTO rbac_roles (tenant_id, name, description, permissions, hierarchy_level, is_system)
SELECT 
    id as tenant_id,
    'admin' as name,
    'Administrador operacional - acesso completo aos dados da empresa' as description,
    '[
        {"resource": "event", "action": "*"},
        {"resource": "financial", "action": "*"},
        {"resource": "pricing", "action": "*"},
        {"resource": "agent", "action": "*"},
        {"resource": "audit", "action": "*"},
        {"resource": "admin", "action": "users"},
        {"resource": "admin", "action": "parameters"}
    ]'::jsonb as permissions,
    10 as hierarchy_level,
    true as is_system
FROM tenants WHERE slug = 'orkestra'
ON CONFLICT DO NOTHING;

-- Manager (gestão de eventos e pricing)
INSERT INTO rbac_roles (tenant_id, name, description, permissions, hierarchy_level, is_system)
SELECT 
    id as tenant_id,
    'manager' as name,
    'Gerente de eventos - pode criar/editar eventos e calcular preços' as description,
    '[
        {"resource": "event", "action": "read"},
        {"resource": "event", "action": "write"},
        {"resource": "financial", "action": "read"},
        {"resource": "pricing", "action": "execute"}
    ]'::jsonb as permissions,
    20 as hierarchy_level,
    false as is_system
FROM tenants WHERE slug = 'orkestra'
ON CONFLICT DO NOTHING;

-- Financeiro (acesso financeiro completo)
INSERT INTO rbac_roles (tenant_id, name, description, permissions, hierarchy_level, is_system)
SELECT 
    id as tenant_id,
    'financeiro' as name,
    'Controle financeiro - acesso total ao financeiro e audit' as description,
    '[
        {"resource": "financial", "action": "*"},
        {"resource": "event", "action": "read"},
        {"resource": "audit", "action": "read"},
        {"resource": "pricing", "action": "read"}
    ]'::jsonb as permissions,
    20 as hierarchy_level,
    false as is_system
FROM tenants WHERE slug = 'orkestra'
ON CONFLICT DO NOTHING;

-- Operador (operações básicas)
INSERT INTO rbac_roles (tenant_id, name, description, permissions, hierarchy_level, is_system)
SELECT 
    id as tenant_id,
    'operador' as name,
    'Operador - pode criar eventos e calcular preços' as description,
    '[
        {"resource": "event", "action": "read"},
        {"resource": "event", "action": "write"},
        {"resource": "pricing", "action": "execute"}
    ]'::jsonb as permissions,
    30 as hierarchy_level,
    false as is_system
FROM tenants WHERE slug = 'orkestra'
ON CONFLICT DO NOTHING;

-- Viewer (somente leitura)
INSERT INTO rbac_roles (tenant_id, name, description, permissions, hierarchy_level, is_system)
SELECT 
    id as tenant_id,
    'viewer' as name,
    'Visualização - apenas leitura de eventos e financeiro' as description,
    '[
        {"resource": "event", "action": "read"},
        {"resource": "financial", "action": "read"}
    ]'::jsonb as permissions,
    40 as hierarchy_level,
    false as is_system
FROM tenants WHERE slug = 'orkestra'
ON CONFLICT DO NOTHING;

-- ============================================================
-- SYSTEM PARAMETERS
-- ============================================================
WITH tenant_id AS (SELECT id FROM tenants WHERE slug = 'orkestra' LIMIT 1)
INSERT INTO system_parameters (tenant_id, category, key, value, value_type, description, default_value, created_by)
SELECT 
    t.id,
    category,
    key,
    value::jsonb,
    value_type,
    description,
    value::jsonb as default_value,
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid as created_by
FROM tenant_id t, (VALUES
    -- Scoring
    ('scoring', 'threshold_go', '"35"', 'number', 'Limite mínimo de margem para GO (%)', 'Margem aceitável'),
    ('scoring', 'threshold_alert', '"25"', 'number', 'Limite de alerta de margem (%)', 'Margem mínima tolerável'),
    ('scoring', 'threshold_critical', '"15"', 'number', 'Limite crítico de margem (%)', 'Margem abaixo disso requer revisão'),
    ('scoring', 'limite_confianca', '"0.70"', 'number', 'Confiança mínima para decisões automáticas', 'Decisões abaixo disso requerem revisão humana'),
    ('scoring', 'limite_alta_confianca', '"0.90"', 'number', 'Limite de alta confiança', 'Decisões acima disso são automáticas'),
    
    -- Financial thresholds
    ('financial', 'margem_minima', '"25"', 'number', 'Margem mínima aceitável geral (%)', 'Valor padrão para validação'),
    ('financial', 'limite_variancia_cmv', '"5"', 'number', 'Limite de variação CMV vs Estoque (%)', 'Alerta se divergência maior que isso'),
    ('financial', 'alerta_custo_proteina', '"50"', 'number', 'Alerta se proteína > X% do custo', 'Threshold para alerta de menu'),
    ('financial', 'alerta_custo_bebida', '"40"', 'number', 'Alerta se bebida > X% do custo', 'Threshold para alerta de mix'),
    ('financial', 'alerta_custo_staff', '"30"', 'number', 'Alerta se staff > X% do custo', 'Threshold para alerta de equipe'),
    
    -- Pricing
    ('pricing', 'markup_default', '"2.0"', 'number', 'Markup padrão', 'Markup para cálculo de vendas'),
    ('pricing', 'markup_alimentacao', '"2.2"', 'number', 'Markup alimentação', 'Markup específico para alimentação'),
    ('pricing', 'markup_bebida', '"3.0"', 'number', 'Markup bebidas', 'Markup específico para bebidas'),
    ('pricing', 'markup_staff', '"2.5"', 'number', 'Markup staff/terceiros', 'Markup para mão de obra'),
    ('pricing', 'markup_decoracao', '"3.5"', 'number', 'Markup ambientação', 'Markup para decoração e cenografia'),
    
    -- Forecast
    ('forecast', 'dias_previsao', '"90"', 'number', 'Dias de projeção de caixa', 'Quanto tempo projetar no futuro'),
    ('forecast', 'buffer_perc', '"15"', 'number', 'Percentual de buffer', 'Margem de segurança nas projeções'),
    ('forecast', 'buffer_minimo_caixa', '"50000"', 'number', 'Buffer mínimo de caixa (R$)', 'Valor mínimo para manter em caixa'),
    
    -- Security
    ('security', 'max_tentativas_login', '"5"', 'number', 'Tentativas antes do bloqueio', 'Tentativas de senha erradas'),
    ('security', 'lockout_duration_minutes', '"30"', 'number', 'Duração do bloqueio (min)', 'Quanto tempo bloquear usuário'),
    ('security', 'session_ttl_minutes', '"60"', 'number', 'TTL da sessão (min)', 'Duração da sessão antes de expirar'),
    ('security', 'mfa_required_for_admin', '"true"', 'boolean', 'MFA obrigatório para admin', 'Segurança para usuários admin'),
    ('security', 'mfa_required_financial', '"true"', 'boolean', 'MFA obrigatório para financeiro', 'Segurança para acesso financeiro'),
    
    -- Audit
    ('audit', 'retention_days_audit_log', '"2555"', 'number', 'Retenção de audit_log (7 anos)', 'Dias para manter logs de auditoria'),
    ('audit', 'retention_days_decision_log', '"1095"', 'number', 'Retenção de decision_log (3 anos)', 'Dias para manter logs de decisões IA'),
    ('audit', 'retention_days_agent_action_log', '"365"', 'number', 'Retenção de agent_action_log (1 ano)', 'Dias para manter logs de ações'),
    
    -- Integrations
    ('integrations', 'api_timeout_seconds', '"30"', 'number', 'Timeout de APIs (seg)', 'Timeout padrão para chamadas externas'),
    ('integrations', 'retry_attempts', '"3"', 'number', 'Tentativas de retry', 'Número de tentativas em caso de falha'),
    ('integrations', 'retry_delay_seconds', '"2"', 'number', 'Delay entre retries (seg)', 'Tempo de espera entre tentativas')
) AS params(category, key, value, value_type, description, default_value)
ON CONFLICT (tenant_id, cost_center_id, key) DO NOTHING;

-- ============================================================
-- ADMIN USER (senha: admin123 - hash bcrypt)
-- NOTA: Em produção, usar bcrypt real ou gerar hash seguro
-- ============================================================
WITH tenant AS (SELECT id FROM tenants WHERE slug = 'orkestra' LIMIT 1),
     admin_role AS (SELECT id FROM rbac_roles WHERE name = 'admin' LIMIT 1)
INSERT INTO rbac_users (tenant_id, email, password_hash, first_name, last_name, active)
SELECT 
    t.id,
    'admin@orkestra.io',
    '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', -- bcrypt de 'password'
    'Admin',
    'Orkestra',
    true
FROM tenant t
ON CONFLICT (tenant_id, email) DO NOTHING;

-- Vincular admin ao role admin
WITH admin_user AS (
    SELECT u.id as user_id, u.tenant_id 
    FROM rbac_users u 
    JOIN tenants t ON u.tenant_id = t.id 
    WHERE u.email = 'admin@orkestra.io' AND t.slug = 'orkestra'
),
admin_role AS (
    SELECT id as role_id, tenant_id 
    FROM rbac_roles 
    WHERE name = 'admin'
)
INSERT INTO rbac_user_roles (tenant_id, user_id, role_id, granted_by)
SELECT 
    au.tenant_id,
    au.user_id,
    ar.role_id,
    au.user_id as granted_by
FROM admin_user au, admin_role ar
WHERE au.tenant_id = ar.tenant_id
ON CONFLICT DO NOTHING;

-- ============================================================
-- SEED EVENTS (exemplos de eventos)
-- ============================================================
WITH tenant AS (SELECT id FROM tenants WHERE slug = 'orkestra' LIMIT 1)
INSERT INTO events (event_id, n_ctt, company_id, company_name, client_name, event_type, event_date, num_guests, status, revenue_total, cmv_total, net_profit, margin_pct)
SELECT 
    t.id,
    'EVT-00001',
    'CTT-2025-0142',
    t.id,
    'LA ORANA',
    'Casal Silva',
    'wedding',
    '2025-04-22',
    200,
    'confirmed',
    45000.00,
    26100.00,
    18900.00,
    42.00
FROM tenant t
ON CONFLICT DO NOTHING;

-- ============================================================
-- SEED RECIPES (exemplos de fichas técnicas)
-- ============================================================
INSERT INTO recipes (recipe_id, name, category, yield, prep_time_min, complexity, ingredients, cost_per_serving)
VALUES 
    ('REC-001', 'Bobo de Camarão', 'proteina', 50, 45, 'medium', '[
        {"item": "camarão", "qty": 0.150, "unit": "kg", "cost": 18.00},
        {"item": "aipim", "qty": 0.100, "unit": "kg", "cost": 1.50},
        {"item": "leite_coco", "qty": 0.050, "unit": "L", "cost": 2.00},
        {"item": "temperos", "qty": 1, "unit": "porcao", "cost": 3.00}
    ]', 24.50),
    ('REC-002', 'Moqueca de Peixe', 'proteina', 60, 60, 'medium', '[
        {"item": "peixe", "qty": 0.200, "unit": "kg", "cost": 15.00},
        {"item": "leite_coco", "qty": 0.100, "unit": "L", "cost": 4.00},
        {"item": "dendê", "qty": 0.020, "unit": "L", "cost": 1.50},
        {"item": "legumes", "qty": 1, "unit": "porcao", "cost": 5.00}
    ]', 25.50)
ON CONFLICT DO NOTHING;

-- ============================================================
-- SEED DOMAIN RULES
-- ============================================================
WITH tenant AS (SELECT id FROM tenants WHERE slug = 'orkestra' LIMIT 1)
INSERT INTO domain_rules (company_id, domain, rule_name, rule_description, rule_logic, priority)
SELECT 
    t.id,
    domain,
    rule_name,
    rule_description,
    rule_logic::jsonb,
    priority
FROM tenant t, (VALUES
    ('financial', 'margin_threshold', 'Margem mínima aceitável', '{"min_margin": 25}'),
    ('financial', 'variance_limit', 'Limite de variação CMV vs Estoque', '{"max_variance": 5}'),
    ('kitchen', 'recipe_validation', 'Validação de receitas', '{"required_fields": ["name", "yield", "ingredients", "cost_per_serving"]}'),
    ('procurement', 'stock_alert', 'Alerta de estoque baixo', '{"min_days": 7}'),
    ('procurement', 'supplier_check', 'Verificação de fornecedor', '{"blacklist_check": true}'),
    ('audit', 'consistency_check', 'Verificação de consistência', '{"max_diff": 5}'),
    ('general', 'logging_mandatory', 'Logging obrigatório', '{"required": true}'),
    ('general', 'policy_check', 'Verificação de políticas', '{"required": true, "enforce": true}')
) AS rules(domain, rule_name, rule_description, rule_logic)
CROSS JOIN LATERAL (SELECT priority FROM generate_series(10, 80, 10) AS priority LIMIT 1) p
ON CONFLICT DO NOTHING;

-- ============================================================
-- MIGRATION RECORD
-- ============================================================
INSERT INTO schema_migrations (version, description, executed_at, execution_time_ms)
VALUES (
    2, 
    'Seed data: permissions, roles, parameters, admin user, sample events/recipes', 
    NOW(),
    0
)
ON CONFLICT (version) DO NOTHING;
