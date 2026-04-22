-- ============================================================
-- TELEGRAM + WHATSAPP ENGINE — Schema PostgreSQL
-- Módulos: Mensagens, Leads, Conversas, Comandos
-- Versão: 1.0
-- ============================================================

-- ============================================================
-- 1. PLATFORMS (Canais de entrada)
-- ============================================================
CREATE TYPE platform_type AS ENUM ('telegram', 'whatsapp', 'manychat');

CREATE TABLE platforms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    platform platform_type NOT NULL,
    platform_name TEXT NOT NULL,  -- "QOpera Comercial", "Estoque Laohana"
    
    -- Configuração de API
    bot_token TEXT,  -- Telegram
    api_key TEXT,    -- WhatsApp/ManyChat
    webhook_url TEXT,
    webhook_secret TEXT,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_connected BOOLEAN DEFAULT FALSE,
    last_ping_at TIMESTAMPTZ,
    last_error TEXT,
    
    -- Configurações
    config JSONB DEFAULT '{}',  -- configurações específicas
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(company_id, platform, platform_name)
);

-- ============================================================
-- 2. USERS (Usuários Telegram/WhatsApp)
-- ============================================================
CREATE TABLE chat_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Identificadores
    external_id TEXT NOT NULL,  -- Telegram user ID ou WhatsApp phone
    platform_id UUID NOT NULL REFERENCES platforms(id),
    
    -- Dados básicos
    first_name TEXT,
    last_name TEXT,
    username TEXT,
    phone TEXT,
    email TEXT,
    
    -- Vinculação interna
    internal_user_id UUID REFERENCES rbac_users(id),  -- Se já é usuário do sistema
    
    -- Preferências
    language_code TEXT DEFAULT 'pt',
    timezone TEXT DEFAULT 'America/Sao_Paulo',
    prefers_voice BOOLEAN DEFAULT FALSE,  -- Prefere áudio
    
    -- Status
    is_bot BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_blocked BOOLEAN DEFAULT FALSE,
    block_reason TEXT,
    
    -- Primeiro contato
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(platform_id, external_id)
);

CREATE INDEX idx_chat_users_platform ON chat_users(platform_id, external_id);
CREATE INDEX idx_chat_users_internal ON chat_users(internal_user_id);

-- ============================================================
-- 3. CONVERSATIONS (Sessões de conversa)
-- ============================================================
CREATE TYPE conversation_status AS ENUM ('active', 'closed', 'paused', 'expired');

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    platform_id UUID NOT NULL REFERENCES platforms(id),
    user_id UUID NOT NULL REFERENCES chat_users(id),
    
    -- Identificador externo
    external_chat_id TEXT,  -- ID do chat no Telegram/WhatsApp
    
    -- Estado
    status conversation_status DEFAULT 'active',
    current_stage TEXT DEFAULT 'welcome',  -- welcome, qualification, deal, etc
    
    -- Controle
    turn_count INTEGER DEFAULT 0,
    message_count INTEGER DEFAULT 0,
    
    -- Contexto
    context_data JSONB DEFAULT '{}',  -- Variáveis da conversa
    extracted_entities JSONB DEFAULT '{}',  -- Entidades extraídas
    
    -- Lead/Evento vinculado
    lead_id UUID REFERENCES lead_intake(id),
    flow_id UUID REFERENCES sales_flows(id),
    
    -- Timestamps
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(platform_id, external_chat_id)
);

CREATE INDEX idx_conversations_user ON conversations(user_id, status);
CREATE INDEX idx_conversations_active ON conversations(platform_id) WHERE status = 'active';
CREATE INDEX idx_conversations_lead ON conversations(lead_id);

-- ============================================================
-- 4. MESSAGES (Mensagens trocadas)
-- ============================================================
CREATE TYPE message_direction AS ENUM ('in', 'out', 'system');
CREATE TYPE message_type AS ENUM ('text', 'voice', 'image', 'document', 'video', 'location', 'contact');

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES chat_users(id),  -- NULL se mensagem do sistema
    
    direction message_direction NOT NULL,
    message_type message_type NOT NULL DEFAULT 'text',
    
    -- Conteúdo
    text_content TEXT,
    voice_url TEXT,  -- URL do áudio
    voice_duration_seconds INTEGER,
    file_url TEXT,
    file_name TEXT,
    file_size INTEGER,
    
    -- Mídia
    media_url TEXT,
    media_caption TEXT,
    
    -- Processamento
    is_processed BOOLEAN DEFAULT FALSE,  -- Já processou com IA?
    processing_result JSONB,  -- Resultado do processamento
    
    -- Comando extraído
    is_command BOOLEAN DEFAULT FALSE,
    command_parsed JSONB,  -- {command: 'entrada', args: [...]}
    
    -- Timestamps
    sent_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    processed_at TIMESTAMPTZ,
    
    -- IDs externos
    external_message_id TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY RANGE (sent_at);

-- Partições mensais
CREATE TABLE messages_2026_04 PARTITION OF messages
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

CREATE INDEX idx_messages_conversation ON messages(conversation_id, sent_at DESC);
CREATE INDEX idx_messages_command ON messages(is_command) WHERE is_command = TRUE;
CREATE INDEX idx_messages_unprocessed ON messages(is_processed) WHERE is_processed = FALSE;

-- ============================================================
-- 5. COMMANDS (Comandos registrados)
-- ============================================================
CREATE TABLE commands_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    message_id UUID REFERENCES messages(id),
    user_id UUID REFERENCES chat_users(id),
    conversation_id UUID REFERENCES conversations(id),
    
    -- Comando
    command TEXT NOT NULL,  -- 'entrada', 'saida', 'evento', etc
    command_args JSONB,  -- Argumentos parseados
    command_raw TEXT,  -- Texto original do comando
    
    -- Execução
    executed_at TIMESTAMPTZ,
    execution_status TEXT DEFAULT 'pending',  -- pending, success, error
    execution_result JSONB,  -- Resultado da execução
    execution_error TEXT,
    
    -- Ação associada
    action_taken TEXT,  -- O que foi feito
    record_id UUID,  -- ID do registro criado/atualizado
    record_table TEXT,  -- Tabela afetada
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_commands_user ON commands_log(user_id, created_at DESC);
CREATE INDEX idx_commands_executed ON commands_log(executed_at) WHERE execution_status = 'pending';

-- ============================================================
-- 6. WEBHOOK QUEUE (Fila de webhooks)
-- ============================================================
CREATE TABLE webhook_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    platform_id UUID NOT NULL REFERENCES platforms(id),
    
    -- Payload
    event_type TEXT NOT NULL,  -- 'message', 'callback', 'command'
    payload JSONB NOT NULL,
    
    -- Processamento
    status TEXT DEFAULT 'pending',  -- pending, processing, completed, failed
    attempt_count INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    
    -- Retentativa
    next_attempt_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Error
    last_error TEXT,
    last_error_at TIMESTAMPTZ,
    
    -- Resultado
    processing_result JSONB,
    processed_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_webhook_pending ON webhook_queue(status, next_attempt_at) 
    WHERE status IN ('pending', 'failed');

-- ============================================================
-- 7. QUICK REPLIES (Respostas rápidas configuráveis)
-- ============================================================
CREATE TABLE quick_replies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES tenants(id),
    
    trigger_word TEXT NOT NULL,  -- Palavra que dispara
    reply_text TEXT NOT NULL,    -- Resposta
    reply_voice_url TEXT,         -- Áudio
    
    -- Contexto
    requires_stage TEXT,  -- Só responde se conversa em determinado stage
    
    -- Config
    priority INTEGER DEFAULT 100,
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_quick_replies ON quick_replies(company_id, trigger_word);

-- ============================================================
-- 8. VOICE SETTINGS (Preferências de voz)
-- ============================================================
CREATE TABLE voice_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    conversation_id UUID UNIQUE REFERENCES conversations(id),
    
    -- Config ElevenLabs
    voice_id TEXT DEFAULT '21m00Tcm4TlvDq8ikWAM',  -- Rachel (PT-BR)
    model_id TEXT DEFAULT 'eleven_multilingual_v2',
    
    -- Parâmetros
    stability DECIMAL(3,2) DEFAULT 0.50,
    similarity_boost DECIMAL(3,2) DEFAULT 0.75,
    style DECIMAL(3,2) DEFAULT 0.30,
    
    -- Quando usar voz
    use_voice_on_welcome BOOLEAN DEFAULT TRUE,
    use_voice_on_important BOOLEAN DEFAULT TRUE,
    
    -- Cache
    voice_cache_enabled BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- FUNÇÕES
-- ============================================================

-- 1. Criar ou resgatar usuário por mensagem
CREATE OR REPLACE FUNCTION get_or_create_chat_user(
    p_platform_id UUID,
    p_external_id TEXT,
    p_first_name TEXT DEFAULT NULL,
    p_last_name TEXT DEFAULT NULL,
    p_username TEXT DEFAULT NULL,
    p_phone TEXT DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_user_id UUID;
BEGIN
    -- Tenta buscar existente
    SELECT id INTO v_user_id
    FROM chat_users
    WHERE platform_id = p_platform_id AND external_id = p_external_id;
    
    -- Se não existe, cria
    IF v_user_id IS NULL THEN
        INSERT INTO chat_users (
            external_id, platform_id, first_name, last_name, username, phone
        ) VALUES (
            p_external_id, p_platform_id, p_first_name, p_last_name, p_username, p_phone
        )
        RETURNING id INTO v_user_id;
    ELSE
        -- Atualiza último contato
        UPDATE chat_users
        SET last_seen_at = NOW(),
            first_name = COALESCE(p_first_name, first_name),
            last_name = COALESCE(p_last_name, last_name)
        WHERE id = v_user_id;
    END IF;
    
    RETURN v_user_id;
END;
$$ LANGUAGE plpgsql;

-- 2. Criar nova conversa
CREATE OR REPLACE FUNCTION start_conversation(
    p_platform_id UUID,
    p_user_id UUID,
    p_external_chat_id TEXT
) RETURNS UUID AS $$
DECLARE
    v_conv_id UUID;
BEGIN
    -- Verifica se já existe conversa ativa
    SELECT id INTO v_conv_id
    FROM conversations
    WHERE platform_id = p_platform_id
      AND user_id = p_user_id
      AND status = 'active'
    ORDER BY started_at DESC
    LIMIT 1;
    
    -- Se não existe, cria nova
    IF v_conv_id IS NULL THEN
        INSERT INTO conversations (
            platform_id, user_id, external_chat_id
        ) VALUES (
            p_platform_id, p_user_id, p_external_chat_id
        )
        RETURNING id INTO v_conv_id;
    END IF;
    
    RETURN v_conv_id;
END;
$$ LANGUAGE plpgsql;

-- 3. Registrar mensagem recebida
CREATE OR REPLACE FUNCTION receive_message(
    p_conversation_id UUID,
    p_user_id UUID,
    p_text TEXT,
    p_message_type message_type DEFAULT 'text',
    p_external_id TEXT DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_message_id UUID;
    v_is_command BOOLEAN;
    v_command_parsed JSONB;
BEGIN
    -- Detecta se é comando
    v_is_command := FALSE;
    v_command_parsed := NULL;
    
    IF p_text LIKE '/%' OR p_text ~* '^(entrada|saida|evento|caixa|lead|opp)\s' THEN
        v_is_command := TRUE;
        -- Parse básico (simplificado)
        v_command_parsed := jsonb_build_object(
            'raw', p_text,
            'detected_at', NOW()
        );
    END IF;
    
    -- Insere mensagem
    INSERT INTO messages (
        conversation_id, user_id, direction, message_type,
        text_content, is_command, command_parsed,
        external_message_id
    ) VALUES (
        p_conversation_id, p_user_id, 'in', p_message_type,
        p_text, v_is_command, v_command_parsed,
        p_external_id
    )
    RETURNING id INTO v_message_id;
    
    -- Atualiza conversa
    UPDATE conversations
    SET message_count = message_count + 1,
        last_message_at = NOW()
    WHERE id = p_conversation_id;
    
    RETURN v_message_id;
END;
$$ LANGUAGE plpgsql;

-- 4. Enviar resposta
CREATE OR REPLACE FUNCTION send_message(
    p_conversation_id UUID,
    p_text TEXT,
    p_voice_url TEXT DEFAULT NULL,
    p_message_type message_type DEFAULT 'text'
) RETURNS UUID AS $$
DECLARE
    v_message_id UUID;
BEGIN
    INSERT INTO messages (
        conversation_id, direction, message_type,
        text_content, voice_url, sent_at
    ) VALUES (
        p_conversation_id, 'out', p_message_type,
        p_text, p_voice_url, NOW()
    )
    RETURNING id INTO v_message_id;
    
    -- Incrementa turno
    UPDATE conversations
    SET turn_count = turn_count + 1
    WHERE id = p_conversation_id;
    
    RETURN v_message_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- VIEWS
-- ============================================================

-- Conversas ativas com última mensagem
CREATE OR REPLACE VIEW v_active_conversations AS
SELECT 
    c.id as conversation_id,
    c.platform_id,
    c.user_id,
    cu.first_name,
    cu.phone,
    c.status,
    c.current_stage,
    c.turn_count,
    c.message_count,
    c.lead_id,
    c.started_at,
    c.last_message_at,
    EXTRACT(EPOCH FROM (NOW() - c.last_message_at)) / 60 as minutes_since_last
FROM conversations c
JOIN chat_users cu ON cu.id = c.user_id
WHERE c.status = 'active'
ORDER BY c.last_message_at DESC;

-- Mensagens não processadas
CREATE OR REPLACE VIEW v_unprocessed_messages AS
SELECT 
    m.id as message_id,
    m.conversation_id,
    m.user_id,
    m.text_content,
    m.is_command,
    m.received_at,
    EXTRACT(EPOCH FROM (NOW() - m.received_at)) as seconds_waiting
FROM messages m
WHERE m.direction = 'in'
  AND m.is_processed = FALSE
ORDER BY m.received_at ASC;

-- Comandos pendentes de execução
CREATE OR REPLACE VIEW v_pending_commands AS
SELECT 
    cl.id as command_id,
    cl.command,
    cl.command_raw,
    cl.command_args,
    cl.created_at,
    m.text_content as original_message,
    c.external_chat_id
FROM commands_log cl
JOIN messages m ON m.id = cl.message_id
JOIN conversations c ON c.id = cl.conversation_id
WHERE cl.execution_status = 'pending'
ORDER BY cl.created_at ASC;

-- ============================================================
-- SEED: Plataformas de exemplo
-- ============================================================

-- (Inserido via V002__seed_data ou posterior)

-- ============================================================
-- COMENTÁRIOS
-- ============================================================

COMMENT ON TABLE platforms IS 'Configurações de APIs Telegram/WhatsApp/ManyChat';
COMMENT ON TABLE chat_users IS 'Usuários dos canais de chat';
COMMENT ON TABLE conversations IS 'Sessões de conversa';
COMMENT ON TABLE messages IS 'Mensagens trocadas (particionadas)';
COMMENT ON TABLE commands_log IS 'Log de comandos executados';
COMMENT ON TABLE webhook_queue IS 'Fila de webhooks para processar';
COMMENT ON TABLE voice_settings IS 'Configurações de voz por conversa';
