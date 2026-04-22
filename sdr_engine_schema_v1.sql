-- ============================================================
-- SDR AI ENGINE — Schema PostgreSQL
-- Módulos: lead_intake | qualification_engine | lead_scoring | 
--          decision_logic | conversation_flow
-- Integrações: ManyChat | WhatsApp | Google Calendar | sales_pipeline
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- 1. LEAD_INTAKE (Captura de Leads)
-- ============================================================
CREATE TYPE lead_source AS ENUM ('manychat', 'whatsapp', 'instagram', 'facebook', 'site', 'indicacao', 'evento', 'telefone');
CREATE TYPE lead_status AS ENUM ('new', 'processing', 'qualified', 'disqualified', 'converted', 'expired');
CREATE TYPE lead_stage AS ENUM ('intake', 'qualifying', 'scored', 'decided', 'routed', 'closed');

CREATE TABLE lead_intake (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Empresa
    company_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    external_id TEXT,
    source lead_source NOT NULL DEFAULT 'site',
    channel TEXT,
    status lead_status NOT NULL DEFAULT 'new',
    stage lead_stage NOT NULL DEFAULT 'intake',
    
    -- Dados do Lead
    lead_name TEXT,
    lead_email TEXT,
    lead_phone TEXT,
    lead_company TEXT,
    lead_role TEXT,
    
    -- Dados do Evento
    event_type TEXT,
    event_date DATE,
    event_date_flexibility INTEGER DEFAULT 7,
    guests_estimate INTEGER DEFAULT 0,
    budget_estimate NUMERIC(15, 2) DEFAULT 0,
    budget_currency TEXT DEFAULT 'BRL',
    budget_flexibility DECIMAL(3, 2) DEFAULT 0.10,
    
    -- Localização
    location_city TEXT,
    location_state TEXT,
    location_venue TEXT,
    
    -- Contexto
    urgency_level INTEGER DEFAULT 3 CHECK (urgency_level >= 1 AND urgency_level <= 5),
    decision_makers INTEGER DEFAULT 1,
    previous_events BOOLEAN DEFAULT FALSE,
    competitors_mentioned TEXT[],
    special_requirements TEXT,
    
    -- Meta
    raw_payload JSONB DEFAULT '{}',
    processed_at TIMESTAMPTZ,
    ai_session_id UUID,
    assigned_sdr_ai TEXT DEFAULT 'sdr_primary',
    
    -- Controle de Stale
    stale_at TIMESTAMPTZ,
    stale_reason TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_leads_company ON lead_intake(company_id);
CREATE INDEX idx_leads_status ON lead_intake(company_id, status);
CREATE INDEX idx_leads_stage ON lead_intake(company_id, stage);
CREATE INDEX idx_leads_email ON lead_intake(lead_email);
CREATE INDEX idx_leads_phone ON lead_intake(lead_phone);
CREATE INDEX idx_leads_date ON lead_intake(event_date);
CREATE INDEX idx_leads_source ON lead_intake(source, created_at DESC);
CREATE INDEX idx_leads_stale ON lead_intake(stale_at) WHERE status = 'new';
CREATE INDEX idx_leads_ai_session ON lead_intake(ai_session_id);

COMMENT ON TABLE lead_intake IS 'Captura inicial de leads de todas as fontes';

-- ============================================================
-- 2. QUALIFICATION_ENGINE
-- ============================================================

-- Banco de perguntas
CREATE TYPE question_type AS ENUM ('text', 'number', 'choice', 'date', 'boolean', 'range', 'multi_choice');
CREATE TYPE question_category AS ENUM ('basic', 'event_specs', 'budget', 'logistics', 'decision', 'qualification');

CREATE TABLE qualification_questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES tenants(id),
    question_key TEXT NOT NULL,
    question_text TEXT NOT NULL,
    question_type question_type NOT NULL,
    options JSONB DEFAULT '[]',
    validation_rule JSONB DEFAULT '{}',
    is_required BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 100,
    condition_logic JSONB DEFAULT '{}',
    category question_category DEFAULT 'basic',
    tags TEXT[],
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(company_id, question_key)
);

CREATE INDEX idx_questions_company ON qualification_questions(company_id, category);
CREATE INDEX idx_questions_active ON qualification_questions(company_id) WHERE is_active = TRUE;

-- Respostas
CREATE TABLE qualification_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID NOT NULL REFERENCES lead_intake(id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES qualification_questions(id),
    response_value JSONB,
    response_text TEXT,
    is_valid BOOLEAN DEFAULT TRUE,
    validation_errors TEXT[],
    confidence_score DECIMAL(3, 2) DEFAULT 1.00,
    ai_extracted BOOLEAN DEFAULT FALSE,
    asked_at TIMESTAMPTZ DEFAULT NOW(),
    answered_at TIMESTAMPTZ,
    turn_number INTEGER DEFAULT 1,
    session_id UUID
);

CREATE INDEX idx_responses_lead ON qualification_responses(lead_id, answered_at DESC);
CREATE INDEX idx_responses_question ON qualification_responses(question_id);
CREATE INDEX idx_responses_session ON qualification_responses(session_id);

-- Estado da qualificação
CREATE TABLE qualification_state (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID NOT NULL UNIQUE REFERENCES lead_intake(id) ON DELETE CASCADE,
    session_id UUID,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'expired', 'error')),
    
    questions_asked UUID[] DEFAULT '{}',
    questions_pending UUID[] DEFAULT '{}',
    pending_info JSONB DEFAULT '{}',
    
    qualification_score INTEGER DEFAULT 0,
    is_qualified BOOLEAN,
    disqualification_reason TEXT,
    ready_for_scoring BOOLEAN DEFAULT FALSE,
    
    max_questions INTEGER DEFAULT 15,
    questions_count INTEGER DEFAULT 0,
    last_interaction_at TIMESTAMPTZ DEFAULT NOW(),
    stale_threshold_minutes INTEGER DEFAULT 30,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_qual_state_lead ON qualification_state(lead_id);
CREATE INDEX idx_qual_state_status ON qualification_state(status);
CREATE INDEX idx_qual_state_scoring ON qualification_state(lead_id) WHERE ready_for_scoring = TRUE;

-- ============================================================
-- 3. LEAD_SCORING
-- ============================================================

CREATE TYPE score_tier AS ENUM ('S', 'A', 'B', 'C', 'D');
CREATE TYPE budget_rating AS ENUM ('insufficient', 'tight', 'good', 'excellent', 'luxury');
CREATE TYPE size_rating AS ENUM ('too_small', 'small', 'good', 'large', 'major');
CREATE TYPE date_rating AS ENUM ('past', 'too_close', 'urgent', 'good', 'future');
CREATE TYPE urgency_rating AS ENUM ('low', 'medium', 'high', 'critical');

CREATE TABLE lead_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID NOT NULL UNIQUE REFERENCES lead_intake(id) ON DELETE CASCADE,
    
    -- Scores Dimensionais
    score_budget INTEGER DEFAULT 0 CHECK (score_budget >= 0 AND score_budget <= 100),
    score_size INTEGER DEFAULT 0 CHECK (score_size >= 0 AND score_size <= 100),
    score_date INTEGER DEFAULT 0 CHECK (score_date >= 0 AND score_date <= 100),
    score_type INTEGER DEFAULT 0 CHECK (score_type >= 0 AND score_type <= 100),
    score_urgency INTEGER DEFAULT 0 CHECK (score_urgency >= 0 AND score_urgency <= 100),
    score_decision_power INTEGER DEFAULT 0 CHECK (score_decision_power >= 0 AND score_decision_power <= 100),
    
    -- Score Composto
    total_score INTEGER DEFAULT 0 CHECK (total_score >= 0 AND total_score <= 100),
    score_tier score_tier,
    
    -- Ratings
    budget_rating budget_rating,
    size_rating size_rating,
    date_rating date_rating,
    urgency_rating urgency_rating,
    
    -- Recomendação
    priority_level TEXT CHECK (priority_level IN ('critical', 'high', 'medium', 'low', 'none')),
    recommended_action TEXT,
    sla_hours INTEGER,
    
    -- Contexto
    scored_at TIMESTAMPTZ DEFAULT NOW(),
    scoring_version TEXT DEFAULT '1.0',
    ai_confidence DECIMAL(3, 2) DEFAULT 0.90,
    reasons JSONB DEFAULT '{}',
    
    CONSTRAINT chk_total_score CHECK (
        total_score = (score_budget + score_size + score_date + score_type + score_urgency) / 5
    )
);

CREATE INDEX idx_scores_lead ON lead_scores(lead_id);
CREATE INDEX idx_scores_tier ON lead_scores(score_tier);
CREATE INDEX idx_scores_priority ON lead_scores(priority_level);
CREATE INDEX idx_scores_total ON lead_scores(total_score DESC);

-- ============================================================
-- 4. DECISION_LOGIC
-- ============================================================

CREATE TYPE decision_category AS ENUM ('hot_lead', 'warm_lead', 'cold_lead', 'disqualified');
CREATE TYPE decision_action_type AS ENUM ('schedule_meeting', 'send_proposal', 'continue_qualifying', 'nurture', 'discard', 'escalate');

CREATE TABLE lead_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID NOT NULL REFERENCES lead_intake(id) ON DELETE CASCADE,
    qualification_id UUID REFERENCES qualification_state(id),
    score_id UUID REFERENCES lead_scores(id),
    
    priority_level TEXT CHECK (priority_level IN ('critical', 'high', 'medium', 'low', 'none')),
    decision_category decision_category,
    action_type decision_action_type,
    action_subtype TEXT,
    
    route_to UUID REFERENCES rbac_users(id),
    route_to_type TEXT CHECK (route_to_type IN ('sdr_human', 'account_executive', 'self_service', 'marketing')),
    
    calendar_event_id TEXT,
    meeting_scheduled_at TIMESTAMPTZ,
    
    message_template_key TEXT,
    message_custom TEXT,
    message_language TEXT DEFAULT 'pt',
    
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'executing', 'completed', 'failed', 'cancelled')),
    executed_at TIMESTAMPTZ,
    execution_result JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_decisions_lead ON lead_decisions(lead_id);
CREATE INDEX idx_decisions_status ON lead_decisions(status);
CREATE INDEX idx_decisions_route ON lead_decisions(route_to, status);
CREATE INDEX idx_decisions_meeting ON lead_decisions(meeting_scheduled_at);

-- ============================================================
-- 5. CONVERSATION_FLOW
-- ============================================================

CREATE TYPE conversation_platform AS ENUM ('manychat', 'whatsapp', 'instagram');
CREATE TYPE conversation_status AS ENUM ('active', 'paused', 'completed', 'error', 'timeout');

CREATE TABLE conversation_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID NOT NULL REFERENCES lead_intake(id) ON DELETE CASCADE,
    platform conversation_platform NOT NULL,
    external_session_id TEXT,
    
    status conversation_status DEFAULT 'active',
    current_node TEXT DEFAULT 'welcome',
    context JSONB DEFAULT '{}',
    memory JSONB DEFAULT '[]',
    
    turn_count INTEGER DEFAULT 0,
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    user_inactive_minutes INTEGER DEFAULT 0,
    escalation_triggered BOOLEAN DEFAULT FALSE,
    escalation_reason TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    
    UNIQUE(lead_id, platform)
);

CREATE INDEX idx_conv_lead ON conversation_sessions(lead_id);
CREATE INDEX idx_conv_platform ON conversation_sessions(platform);
CREATE INDEX idx_conv_status ON conversation_sessions(status);
CREATE INDEX idx_conv_inactive ON conversation_sessions(user_inactive_minutes) WHERE status = 'active';

-- Fluxo de nós
CREATE TYPE node_type AS ENUM ('message', 'question', 'wait_input', 'decision', 'ai_action', 'integration', 'end');

CREATE TABLE conversation_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_id TEXT UNIQUE NOT NULL,
    node_type node_type NOT NULL,
    node_name TEXT NOT NULL,
    
    -- Configuração
    content JSONB NOT NULL,  -- Mensagens, perguntas, condições
    config JSONB DEFAULT '{}',  -- Timeouts, validações
    
    -- Transições
    on_success TEXT,  -- Próximo nó em caso de sucesso
    on_error TEXT,    -- Próximo nó em caso de erro
    on_timeout TEXT,  -- Próximo nó em timeout
    
    -- Condicionais
    condition_logic JSONB,  -- Quando executar este nó
    
    -- Ações
    actions JSONB DEFAULT '[]',  -- Ações a executar neste nó
    
    -- Controle
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 100,
    tags TEXT[],
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_nodes_type ON conversation_nodes(node_type);
CREATE INDEX idx_nodes_active ON conversation_nodes() WHERE is_active = TRUE;

-- Log de mensagens
CREATE TABLE conversation_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    
    direction TEXT CHECK (direction IN ('in', 'out', 'system')),
    content TEXT NOT NULL,
    content_type TEXT DEFAULT 'text',  -- text, image, quick_reply, carousel
    platform_message_id TEXT,
    
    node_executed TEXT,
    context_snapshot JSONB,
    
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ
) PARTITION BY RANGE (sent_at);

-- Partições mensais
CREATE TABLE conversation_messages_2026_04 PARTITION OF conversation_messages
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

CREATE INDEX idx_messages_session ON conversation_messages(session_id, turn_number);
CREATE INDEX idx_messages_sent ON conversation_messages(sent_at DESC);

-- ============================================================
-- FUNÇÕES SDR
-- ============================================================

-- 1. Calcular Score do Lead
CREATE OR REPLACE FUNCTION calculate_lead_score(p_lead_id UUID)
RETURNS TABLE (total_score INTEGER, tier score_tier, priority TEXT) AS $$
DECLARE
    v_lead RECORD;
    v_budget_score INTEGER;
    v_size_score INTEGER;
    v_date_score INTEGER;
    v_type_score INTEGER;
    v_urgency_score INTEGER;
    v_total INTEGER;
    v_tier score_tier;
    v_priority TEXT;
BEGIN
    -- Buscar lead
    SELECT * INTO v_lead FROM lead_intake WHERE id = p_lead_id;
    
    IF NOT FOUND THEN
        RETURN QUERY SELECT 0, 'D'::score_tier, 'none'::TEXT;
        RETURN;
    END IF;
    
    -- Score Budget (baseado em budget_estimate / guests)
    IF v_lead.guests_estimate > 0 THEN
        DECLARE
            v_budget_per_person NUMERIC;
        BEGIN
            v_budget_per_person := v_lead.budget_estimate / v_lead.guests_estimate;
            
            v_budget_score := CASE
                WHEN v_budget_per_person < 50 THEN 20
                WHEN v_budget_per_person < 80 THEN 40
                WHEN v_budget_per_person < 150 THEN 70
                WHEN v_budget_per_person < 250 THEN 90
                ELSE 100
            END;
        END;
    ELSE
        v_budget_score := 30;
    END IF;
    
    -- Score Size
    v_size_score := CASE
        WHEN v_lead.guests_estimate < 30 THEN 20
        WHEN v_lead.guests_estimate < 80 THEN 50
        WHEN v_lead.guests_estimate < 200 THEN 75
        WHEN v_lead.guests_estimate < 500 THEN 90
        ELSE 100
    END;
    
    -- Score Date
    IF v_lead.event_date IS NOT NULL THEN
        DECLARE
            v_days_until INTEGER;
        BEGIN
            v_days_until := v_lead.event_date - CURRENT_DATE;
            
            v_date_score := CASE
                WHEN v_days_until < 0 THEN 0
                WHEN v_days_until < 15 THEN 30
                WHEN v_days_until < 45 THEN 60
                WHEN v_days_until < 120 THEN 85
                WHEN v_days_until < 180 THEN 90
                ELSE 70  -- Muito longe
            END;
        END;
    ELSE
        v_date_score := 50;
    END IF;
    
    -- Score Type (categorias premium valam mais)
    v_type_score := CASE v_lead.event_type
        WHEN 'casamento' THEN 95
        WHEN 'formatura' THEN 90
        WHEN 'corporate' THEN 90
        WHEN 'congresso' THEN 85
        WHEN 'aniversario' THEN 80
        ELSE 60
    END;
    
    -- Score Urgency
    v_urgency_score := v_lead.urgency_level * 20;  -- 1-5 -> 20-100
    
    -- Total (média ponderada)
    v_total := (v_budget_score * 30 + v_size_score * 25 + v_date_score * 20 + 
                v_type_score * 15 + v_urgency_score * 10) / 100;
    
    -- Tier (baseado no score_budget principalmente)
    v_tier := CASE
        WHEN v_total >= 85 AND v_budget_score >= 90 THEN 'S'::score_tier
        WHEN v_total >= 70 THEN 'A'::score_tier
        WHEN v_total >= 50 THEN 'B'::score_tier
        WHEN v_total >= 30 THEN 'C'::score_tier
        ELSE 'D'::score_tier
    END;
    
    -- Priority
    v_priority := CASE v_tier
        WHEN 'S'::score_tier THEN 'critical'
        WHEN 'A'::score_tier THEN 'high'
        WHEN 'B'::score_tier THEN 'medium'
        ELSE 'low'
    END;
    
    RETURN QUERY SELECT v_total, v_tier, v_priority;
END;
$$ LANGUAGE plpgsql;

-- 2. Tomar decisão automática
CREATE OR REPLACE FUNCTION make_lead_decision(p_lead_id UUID)
RETURNS TABLE (action decision_action_type, priority TEXT, sla INTEGER) AS $$
DECLARE
    v_score RECORD;
    v_action decision_action_type;
    v_sla INTEGER;
BEGIN
    -- Buscar score
    SELECT * INTO v_score FROM lead_scores WHERE lead_id = p_lead_id;
    
    IF NOT FOUND THEN
        -- Calcular se não existe
        SELECT * INTO v_score FROM calculate_lead_score(p_lead_id);
        
        -- Inserir
        INSERT INTO lead_scores (lead_id, total_score, score_tier, priority_level)
        SELECT p_lead_id, s.total_score, s.tier, s.priority
        FROM calculate_lead_score(p_lead_id) s;
    END IF;
    
    -- Decisão baseada na tier
    CASE v_score.tier
        WHEN 'S'::score_tier THEN
            v_action := 'schedule_meeting'::decision_action_type;
            v_sla := 2;
        WHEN 'A'::score_tier THEN
            v_action := 'schedule_meeting'::decision_action_type;
            v_sla := 24;
        WHEN 'B'::score_tier THEN
            v_action := 'continue_qualifying'::decision_action_type;
            v_sla := 72;
        WHEN 'C'::score_tier THEN
            v_action := 'nurture'::decision_action_type;
            v_sla := 168;
        ELSE
            v_action := 'discard'::decision_action_type;
            v_sla := 0;
    END CASE;
    
    RETURN QUERY SELECT v_action, v_score.priority, v_sla;
END;
$$ LANGUAGE plpgsql;

-- 3. Check stale leads
CREATE OR REPLACE FUNCTION check_stale_leads()
RETURNS TABLE (lead_id UUID, inactive_minutes INTEGER) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        l.id,
        EXTRACT(EPOCH FROM (NOW() - qs.last_interaction_at)) / 60 AS mins
    FROM lead_intake l
    JOIN qualification_state qs ON qs.lead_id = l.id
    WHERE l.status = 'new'
      AND qs.last_interaction_at < NOW() - INTERVAL '30 minutes'
      AND l.stale_at IS NULL;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- VIEWS
-- ============================================================

-- Pipeline de leads ativos
CREATE OR REPLACE VIEW v_sdr_pipeline AS
SELECT 
    l.id as lead_id,
    l.company_id,
    t.name as company_name,
    l.lead_name,
    l.lead_email,
    l.lead_phone,
    l.source,
    l.status,
    l.stage,
    l.event_type,
    l.event_date,
    l.guests_estimate,
    l.budget_estimate,
    ls.total_score,
    ls.score_tier,
    ls.priority_level,
    ld.action_type as next_action,
    ld.meeting_scheduled_at,
    cs.turn_count,
    cs.user_inactive_minutes,
    l.created_at
FROM lead_intake l
JOIN tenants t ON t.id = l.company_id
LEFT JOIN lead_scores ls ON ls.lead_id = l.id
LEFT JOIN lead_decisions ld ON ld.lead_id = l.id AND ld.status = 'pending'
LEFT JOIN conversation_sessions cs ON cs.lead_id = l.id
WHERE l.status IN ('new', 'processing', 'qualified')
ORDER BY ls.total_score DESC NULLS LAST, l.created_at ASC;

-- Performance SDR
CREATE OR REPLACE VIEW v_sdr_performance AS
SELECT 
    l.company_id,
    DATE_TRUNC('day', l.created_at) as date,
    COUNT(*) as leads_received,
    COUNT(*) FILTER (WHERE l.status = 'qualified') as leads_qualified,
    COUNT(*) FILTER (WHERE ls.score_tier IN ('S', 'A')) as high_score_leads,
    COUNT(*) FILTER (WHERE ld.action_type = 'schedule_meeting') as meetings_scheduled,
    AVG(ls.total_score) FILTER (WHERE ls.total_score > 0) as avg_score,
    AVG(EXTRACT(EPOCH FROM (ld.executed_at - l.created_at)) / 60) 
        FILTER (WHERE ld.status = 'completed') as avg_processing_minutes
FROM lead_intake l
LEFT JOIN lead_scores ls ON ls.lead_id = l.id
LEFT JOIN lead_decisions ld ON ld.lead_id = l.id
WHERE l.created_at >= DATE_TRUNC('month', NOW())
GROUP BY l.company_id, DATE_TRUNC('day', l.created_at);

-- ============================================================
-- SEED: Perguntas Padrão
-- ============================================================

INSERT INTO qualification_questions (question_key, question_text, question_type, options, is_required, priority, category) VALUES
('welcome', 'Olá! Sou o assistente da Orkestra. Vi que você tem interesse em um evento. Posso fazer algumas perguntas rápidas?', 'message', '[]', FALSE, 1, 'basic'),
('event_type', 'Que tipo de evento você está planejando?', 'choice', '[
  {"value": "casamento", "label": "Casamento", "score": 10},
  {"value": "aniversario", "label": "Aniversário", "score": 5},
  {"value": "corporate", "label": "Evento Corporativo", "score": 10},
  {"value": "congresso", "label": "Congresso", "score": 8},
  {"value": "formatura", "label": "Formatura", "score": 9},
  {"value": "outro", "label": "Outro", "score": 3}
]', TRUE, 10, 'event_specs'),
('event_date', 'Qual a data (ou período) desejado para o evento?', 'date', '[]', TRUE, 20, 'event_specs'),
('guest_count', 'Quantas pessoas você espera? (aproximado)', 'range', '{"min": 10, "max": 1000}', TRUE, 30, 'event_specs'),
('budget_per_person', 'Qual a faixa de investimento por pessoa?', 'choice', '[
  {"value": "economico", "label": "Até R$ 80/pessoa", "score": 1},
  {"value": "padrao", "label": "R$ 80-150/pessoa", "score": 3},
  {"value": "executivo", "label": "R$ 150-300/pessoa", "score": 5},
  {"value": "premium", "label": "Acima de R$ 300/pessoa", "score": 8}
]', TRUE, 40, 'budget'),
('location_city', 'Em qual cidade será o evento?', 'text', '[]', FALSE, 50, 'logistics'),
('urgency', 'Quão urgente é este evento?', 'choice', '[
  {"value": "1", "label": "Estou só pesquisando"},
  {"value": "2", "label": "Planejando nos próximos meses"},
  {"value": "3", "label": "Preciso de proposta em breve"},
  {"value": "4", "label": "Estou negociando com outros"},
  {"value": "5", "label": "Preciso fechar esta semana"}
]', TRUE, 60, 'decision')
ON CONFLICT DO NOTHING;

-- Seed nós de conversação
INSERT INTO conversation_nodes (node_id, node_type, node_name, content, on_success, is_active) VALUES
('welcome', 'message', 'Mensagem de Boas-vindas', '{"messages": ["Olá! Vejo que você está interessado em um evento. Como posso ajudar?"]}', 'ask_event_type', TRUE),
('ask_event_type', 'question', 'Pergunta tipo de evento', '{"question_key": "event_type", "timeout": 300}', 'ask_event_date', TRUE),
('ask_event_date', 'question', 'Pergunta data', '{"question_key": "event_date"}', 'ask_guest_count', TRUE),
('ask_guest_count', 'question', 'Pergunta convidados', '{"question_key": "guest_count"}', 'ask_budget', TRUE),
('ask_budget', 'question', 'Pergunta orçamento', '{"question_key": "budget_per_person"}', 'process_qualification', TRUE),
('process_qualification', 'ai_action', 'Processar qualificação', '{"action": "evaluate"}', 'route_decision', TRUE),
('route_hot', 'decision', 'Rota lead quente', '{"message": "Perfeito! Vou conectar você com um especialista para agendarmos uma reunião."}', 'end_scheduled', TRUE)
ON CONFLICT DO NOTHING;

COMMENT ON TABLE lead_intake IS 'Leads capturados de múltiplas fontes';
COMMENT ON TABLE lead_scores IS 'Scores calculados automaticamente para cada lead';
COMMENT ON TABLE lead_decisions IS 'Decisões automatizadas do sistema SDR';
COMMENT ON TABLE conversation_sessions IS 'Sessões de conversa com leads';
