# SALES ENGINE — Orkestra Finance Brain

**Versão:** 1.0  
**Data:** 2026-04-08  
**Tipo:** Processo Comercial Operacional Automatizado  
**Status:** Especificação Completa

---

## 🎯 VISÃO GERAL

Transformar o processo comercial manual em um **sistema operacional automatizado** com rastreabilidade total.

**Ciclo Comercial:**
```
[Lead] → Qualificação → Negócio → Contrato → Onboarding → Pós-venda → [Evento]
     ↑                                                              ↓
     └────────────── Loop Contínuo de Relacionamento ───────────────┘
```

---

## 📊 ARQUITETURA DO SALES ENGINE

```
┌─────────────────────────────────────────────────────────────────┐
│                     SALES ENGINE                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐   ┌─────────────┐   ┌──────────────────────┐   │
│  │   STAGE 1   │ → │   STAGE 2   │ → │      STAGE 3       │   │
│  │ Qualificação│   │   Negócio   │   │     Contrato       │   │
│  └──────┬──────┘   └──────┬──────┘   └──────────┬─────────┘   │
│         │                 │                     │              │
│    ┌────┴────┐      ┌────┴────┐          ┌──────┴──────┐      │
│    │CHECKLIST│      │CHECKLIST│          │  CHECKLIST   │      │
│    │Task 1   │      │Task 1   │          │  Task 1      │      │
│    │Task 2   │      │Task 2   │          │  Task 2      │      │
│    │Task N   │      │Task N   │          │  Task N      │      │
│    └────┬────┘      └────┬────┘          └──────┬──────┘      │
│         │                 │                     │              │
│         ▼                 ▼                     ▼              │
│    ┌─────────┐      ┌─────────┐          ┌──────────┐        │
│    │VALIDATE │      │VALIDATE │          │ VALIDATE │        │
│    │TRANSITION      │TRANSITION          │TRANSITION        │
│    └────┬────┘      └────┬────┘          └────┬───┘        │
│         │                 │                     │              │
└─────────┼─────────────────┼─────────────────────┼──────────────┘
          │                 │                     │
          ▼                 ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INTEGRATIONS                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────────────┐ │
│  │ financial   │  │  event      │  │    decision_engine     │ │
│  │   core      │  │  engine     │  │   (scoring/priority)   │ │
│  └─────────────┘  └─────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 OS 5 ESTÁGIOS DO CICLO COMERCIAL

### ETAPA 1: QUALIFICAÇÃO (Qualification)

**Objetivo:** Validar fit entre lead e empresa antes de investir tempo comercial.

**Checklist Automático:**
| # | Tarefa | Automação | Bloqueante |
|---|--------|-----------|------------|
| 1.1 | Coletar dados básicos (nome, email, telefone) | SDR AI auto | ✅ Sim |
| 1.2 | Identificar tipo de evento | SDR AI auto | ✅ Sim |
| 1.3 | Validar orçamento mínimo | Regra sistema | ✅ Sim |
| 1.4 | Confirmar data viável | Regra sistema | ✅ Sim |
| 1.5 | Verificar localização atendida | API geocoding | ✅ Sim |
| 1.6 | Calcular lead_score | IA automático | ✅ Sim |
| 1.7 | Classificar potencial | Regra sistema | ✅ Sim |
| 1.8 | Decidir: avançar ou descartar | SDR ou humano | ✅ Sim |

**Campos Obrigatórios para Avanço:**
```json
{
  "lead_name": "string",
  "lead_contact": "email | phone",
  "event_type": "enumerated",
  "event_date": "date (futura)",
  "guests_estimate": "integer >= 30",
  "budget_estimate": "numeric > min_threshold",
  "location_city": "string (cobertura)",
  "lead_score": "integer >= 50",
  "decision_maker_identified": "boolean: true"
}
```

**Regras de Transição:**
```
IF checklist_completo AND lead_score >= 50:
   → Avançar para NEGÓCIO
   → Criar oportunidade no sales_pipeline
   → Notificar Account Executive
ELSE IF lead_score < 30:
   → Mover para NURTURE
   → Agendar reengajamento (7 dias)
ELSE:
   → Manter em QUALIFICAÇÃO
   → SDR continua conversa
```

---

### ETAPA 2: NEGÓCIO (Deal/Business)

**Objetivo:** Construir proposta, negociar e alinhar expectativas.

**Checklist Automático:**
| # | Tarefa | Automação | Bloqueante |
|---|--------|-----------|------------|
| 2.1 | Montar proposta técnica | Sistema auto | ✅ Sim |
| 2.2 | Calcular pricing com regras | pricing_rules | ✅ Sim |
| 2.3 | Validar margem mínima | Margem ≥ 25% | ✅ Sim |
| 2.4 | Aplicar desconto (se aprovado) | discount_policies | ❌ Não |
| 2.5 | Gerar contrato base | Template auto | ✅ Sim |
| 2.6 | Enviar proposta ao cliente | Email/WhatsApp auto | ❌ Não |
| 2.7 | Aguardar feedback | Timer (SLA: 48h) | ❌ Não |
| 2.8 | Registrar objeções/lembretes | Sistema | ❌ Não |

**Campos Obrigatórios:**
```json
{
  "products_selected": "array<product_id>",
  "total_value_calculated": "numeric",
  "margin_calculated": "decimal >= 25.00",
  "proposal_sent": "boolean: true",
  "proposal_sent_at": "datetime",
  "client_feedback": "enum: [positive, negative, negotiate, delay]"
}
```

**Regras de Transição:**
```
IF margem_calculada >= 25% AND proposta_enviada:
   
IF cliente_aprova_proposta:
   → Avançar para CONTRATO
   → Gerar contrato com dados validados
   → Criar alerta: "Contrato pronto para assinatura"
   
ELSE IF cliente_negocia:
   → Manter em NEGÓCIO
   → Aplicar desconto (se regras permitirem)
   → Reprocessar proposta
   
ELSE IF cliente_rejeita:
   → Mover para LOST
   → Registrar motivo da perda
   → Notificar gestão
   
ELSE IF timeout_48h_sem_resposta:
   → Trigger follow-up automático
   → Escalar para humano se 4x sem resposta
```

---

### ETAPA 3: CONTRATO (Contract)

**Objetivo:** Formalizar acordo com assinatura e pagamento de entrada.

**Checklist Automático:**
| # | Tarefa | Automação | Bloqueante |
|---|--------|-----------|------------|
| 3.1 | Preencher dados do contrato | Sistema auto | ✅ Sim |
| 3.2 | Validar CNPJ/CPF do cliente | API Receita | ✅ Sim |
| 3.3 | Calcular condições de pagamento | Regras financeiras | ✅ Sim |
| 3.4 | Gerar PDF do contrato | Template + dados | ✅ Sim |
| 3.5 | Enviar para assinatura (DocuSign) | Integração API | ✅ Sim |
| 3.6 | Monitorar assinatura | Webhook | ✅ Sim |
| 3.7 | Receber entrada/first payment | Integração bancária | ✅ Sim |
| 3.8 | Confirmar contração | Sistema | ✅ Sim |

**Campos Obrigatórios:**
```json
{
  "contract_value": "numeric (igual proposta aprovada)",
  "client_document": "string (validado)",
  "client_address": "object {cep, street, city, state}",
  "payment_schedule": "array {date, amount, type}",
  "contract_pdf_url": "string (url)",
  "contract_sent_at": "datetime",
  "contract_signed_at": "datetime",
  "down_payment_received": "boolean: true",
  "down_payment_amount": "numeric",
  "down_payment_date": "date"
}
```

**Regras de Transição:**
```
IF contrato_assinado AND entrada_recebida (≥ 30%):
   → Avançar para ONBOARDING
   → Criar evento no event_engine
   → Alocar recursos no inventory
   → Notificar Chef de Cozinha / Produção
   → Gerar ordem de serviço
   
ELSE IF contrato_assinado AND entrada_pendente:
   → Manter em CONTRATO
   → Alerta: "Entrada em atraso"
   → Escalar para Financeiro após 24h
   
ELSE IF cliente_nao_assina_em_7dias:
   → Mover para HOLD
   → Alerta: "Contrato expirando"
   → Renegociar ou perder
```

---

### ETAPA 4: ONBOARDING (Event Setup)

**Objetivo:** Preparar evento, briefing completo, alinhamento operacional.

**Checklist Automático:**
| # | Tarefa | Automação | Bloqueante |
|---|--------|-----------|------------|
| 4.1 | Criar evento no sistema | Auto (contrato OK) | ✅ Sim |
| 4.2 | Agendar briefing com cliente | Google Calendar + regras | ✅ Sim |
| 4.3 | Coletar briefing completo | Form estruturado | ✅ Sim |
| 4.4 | Validar lista de convidados final | Import arquivo | ❌ Não |
| 4.5 | Aprovar cardápio final | Workflow chef | ✅ Sim |
| 4.6 | Confirmar alocação de staff | Inventory check | ✅ Sim |
| 4.7 | Aprovar montagem técnica | Robusta valida | ✅ Sim |
| 4.8 | Receber pagamento intermediário | Financeiro | ✅ Sim |

**Campos Obrigatórios:**
```json
{
  "event_id": "uuid (criado automaticamente)",
  "briefing_completed": "boolean: true",
  "briefing_date": "datetime",
  "final_guest_count": "integer",
  "menu_approved": "boolean: true",
  "menu_approved_by": "uuid (chef)",
  "staff_allocated": "boolean: true",
  "equipment_reserved": "boolean: true",
  "second_payment_received": "boolean: true",
  "pre_event_checklist_done": "boolean: true"
}
```

**Regras de Transição:**
```
IF briefing_completo AND menu_aprovado AND equipamento_reservado:
   → Status: PRONTO PARA EXECUÇÃO
   → Aguardar dia do evento
   → Não permite mais mudanças (freeze 7 dias antes)
   
ELSE IF faltando_segundo_pagamento:
   → Alerta D-14: "Pagamento pendente"
   → Bloquear alterações em cardápio
   → Escalar se D-7 sem pagamento
   
ELSE IF mudanças_apos_freeze:
   → Taxa extra aplicada automaticamente
   → Nova margem recalculada
   → Aprovação diretoria se > R$ 1.000
```

---

### ETAPA 5: PÓS-VENDA (Post-Sale)

**Objetivo:** Evento executado, cobrança final, relacionamento contínuo.

**Checklist Automático:**
| # | Tarefa | Automação | Bloqueante |
|---|--------|-----------|------------|
| 5.1 | Evento executado registro | Auto (data do evento) | ✅ Sim |
| 5.2 | Coletar feedback (NPS) | Survey auto (24h depois) | ❌ Não |
| 5.3 | Calcular CMV real vs estimado | Inventory + financeiro | ✅ Sim |
| 5.4 | Receber pagamento final | Integração bancária | ✅ Sim |
| 5.5 | Fechar financeiro do evento | Reconciliação auto | ✅ Sim |
| 5.6 | Gerar certificado/lembrança | Template auto | ❌ Não |
| 5.7 | Agendar follow-up futuro | Regra CRM (6 meses) | ❌ Não |
| 5.8 | Atualizar lifetime value do cliente | Auto | ❌ Não |

**Campos Obrigatórios:**
```json
{
  "event_executed": "boolean: true",
  "execution_date": "date",
  "cmv_actual": "numeric",
  "margin_actual": "decimal",
  "nps_score": "integer (0-10)",
  "final_payment_received": "boolean: true",
  "financial_closed": "boolean: true",
  "client_lifetime_value": "numeric (acumulado)",
  "next_contact_date": "date (6 meses)",
  "referral_generated": "boolean"
}
```

**Regras de Transição:**
```
IF evento_executado AND pagamento_final_recebido:
   → Status: CONCLUÍDO
   → Arquivar processo
   → Trigger: Pedir indicação (se NPS >= 8)
   → Trigger: Oferecer próximo evento (aniversário, etc)
   → Atualizar cliente para "VIP" se 3+ eventos
   
ELSE IF evento_executado AND pagamento_pendente:
   → Status: PENDÊNCIA FINANCEIRA
   → Alertas escalonados (3, 7, 15, 30 dias)
   → Ativar cobrança jurídica se > R$ 5.000
   
ELSE IF nps_bom (>= 8):
   → Trigger: Pedir review no Google
   → Trigger: Pedir depoimento para site
   → Trigger: Oferecer desconto indicação
```

---

## 🗂️ ESTRUTURA DE TABELAS

### Tabela Principal: sales_flows (Fluxos Comerciais)

```sql
CREATE TABLE sales_flows (
    -- Identificação
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES tenants(id),
    flow_id TEXT UNIQUE NOT NULL,  -- FLOW-2025-001
    
    -- Lead/Cliente
    lead_id UUID REFERENCES lead_intake(id),
    client_id UUID REFERENCES clients(id),  -- se já existe
    client_name TEXT NOT NULL,
    client_email TEXT,
    client_phone TEXT,
    client_document TEXT,  -- CPF/CNPJ
    
    -- Origem
    source TEXT NOT NULL,  -- manychat, whatsapp, site, indicacao
    source_detail JSONB,   -- ID da conversa, etc
    
    -- Evento (visão comercial)
    event_type TEXT,
    event_date DATE,
    event_time_start TIME,
    event_time_end TIME,
    guests_estimate INTEGER,
    guests_final INTEGER,
    location_city TEXT,
    location_venue TEXT,
    
    -- Valores
    ticket_estimate NUMERIC(15,2),
    ticket_final NUMERIC(15,2),
    potential_value TEXT,  -- small, medium, large, enterprise
    
    -- Status do Flow
    current_stage INTEGER DEFAULT 1,  -- 1=Qualif, 2=Negócio, 3=Contrato, 4=Onboarding, 5=Pós-venda
    stage_status TEXT DEFAULT 'active',  -- active, blocked, completed, lost, hold
    
    -- Scores
    lead_score INTEGER,
    deal_score INTEGER,
    priority TEXT,  -- low, medium, high, critical
    
    -- Atribuição
    assigned_sdr UUID,  -- SDR que qualificou
    assigned_ae UUID,   -- Account Executive
    assigned_pm UUID,   -- Project Manager (pós-venda)
    
    -- Timestamps de Stage
    stage_1_at TIMESTAMPTZ,  -- Qualificação
    stage_2_at TIMESTAMPTZ,  -- Negócio
    stage_3_at TIMESTAMPTZ,  -- Contrato
    stage_4_at TIMESTAMPTZ,  -- Onboarding
    stage_5_at TIMESTAMPTZ,  -- Pós-venda
    
    -- SLAs
    sla_stage_1_hours INTEGER DEFAULT 24,
    sla_stage_2_hours INTEGER DEFAULT 72,
    sla_stage_3_hours INTEGER DEFAULT 48,
    sla_stage_4_hours INTEGER DEFAULT 168,  -- 7 dias
    
    -- Alertas
    alert_level TEXT DEFAULT 'none',  -- none, warning, critical
    alert_reason TEXT,
    alert_at TIMESTAMPTZ,
    
    -- Outcomes
    outcome TEXT,  -- won, lost, cancelled, postponed
    outcome_reason TEXT,
    outcome_at TIMESTAMPTZ,
    
    -- Evento vinculado (quando ganho)
    event_id UUID,  -- FK para event_engine.events
    
    -- Controle
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Checklist de stage completo (calculado)
    stage_1_complete BOOLEAN DEFAULT FALSE,
    stage_2_complete BOOLEAN DEFAULT FALSE,
    stage_3_complete BOOLEAN DEFAULT FALSE,
    stage_4_complete BOOLEAN DEFAULT FALSE,
    stage_5_complete BOOLEAN DEFAULT FALSE
);
```

### Tabela: sales_tasks (Tarefas por Stage)

```sql
CREATE TABLE sales_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES tenants(id),
    flow_id UUID NOT NULL REFERENCES sales_flows(id),
    
    -- Hierarquia
    stage INTEGER NOT NULL,  -- 1, 2, 3, 4, 5
    task_order INTEGER,      -- ordem dentro do stage
    
    -- Task
    task_key TEXT NOT NULL,  -- identificador (ex: coletar_dados_basicos)
    task_name TEXT NOT NULL,
    task_description TEXT,
    
    -- Tipo
    task_type TEXT,  -- auto, manual, approval, integration
    
    -- Status
    status TEXT DEFAULT 'pending',  -- pending, in_progress, completed, blocked, skipped
    
    -- Validação
    required_fields JSONB,  -- campos obrigatórios
    validation_rules JSONB,  -- regras de validação
    
    -- Bloqueio de avanço
    is_blocking BOOLEAN DEFAULT TRUE,  -- se FALSE, pode avançar sem
    blocking_reason TEXT,
    
    -- Dados preenchidos
    completed_data JSONB,  -- dados coletados
    completed_by UUID,     -- quem completou
    completed_at TIMESTAMPTZ,
    
    -- Automações vinculadas
    triggers_on_complete JSONB,  -- ações ao completar
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Tabela: stage_transitions (Transições de Stage)

```sql
CREATE TABLE stage_transitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL,
    flow_id UUID NOT NULL REFERENCES sales_flows(id),
    
    from_stage INTEGER NOT NULL,
    to_stage INTEGER NOT NULL,
    
    trigger_type TEXT,  -- manual, auto, scheduled, system
    triggered_by UUID,  -- usuário ou sistema
    
    -- Validação
    validation_passed BOOLEAN,
    validation_errors JSONB,  -- se falhou
    
    -- Timestamp
    transition_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Contexto
    context JSONB  -- dados do momento da transição
);
```

### Tabela: sales_alerts (Alertas e Follow-ups)

```sql
CREATE TABLE sales_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL,
    flow_id UUID NOT NULL REFERENCES sales_flows(id),
    
    alert_type TEXT,  -- sla_violation, task_overdue, follow_up, escalation
    severity TEXT,    -- info, warning, critical
    
    message TEXT,
    suggested_action TEXT,
    
    -- Notificação
    notify_users UUID[],  -- quem recebe
    notify_channels TEXT[],  -- email, whatsapp, in_app
    
    -- Status
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    resolved_by UUID,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 🤖 AUTOMAÇÕES

### Automação 1: Criação Automática de Subtarefas

```sql
-- Trigger: ao criar novo flow, criar todas as tasks do stage 1
CREATE FUNCTION auto_create_stage_1_tasks()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO sales_tasks (company_id, flow_id, stage, task_key, task_name, task_order, is_blocking)
    VALUES
        (NEW.company_id, NEW.id, 1, 'coletar_nome', 'Coletar nome do lead', 1, TRUE),
        (NEW.company_id, NEW.id, 1, 'coletar_contato', 'Coletar email/telefone', 2, TRUE),
        (NEW.company_id, NEW.id, 1, 'identificar_tipo_evento', 'Identificar tipo de evento', 3, TRUE),
        (NEW.company_id, NEW.id, 1, 'coletar_data', 'Coletar data desejada', 4, TRUE),
        (NEW.company_id, NEW.id, 1, 'coletar_orcamento', 'Coletar orçamento estimado', 5, TRUE),
        (NEW.company_id, NEW.id, 1, 'calcular_lead_score', 'Calcular score do lead', 6, TRUE),
        (NEW.company_id, NEW.id, 1, 'decidir_avanco', 'Decidir: avançar ou descartar', 7, TRUE);
    
    RETURN NEW;
END;
```

### Automação 2: Mudança Automática de Status

```sql
-- Função: verificar se todas tasks do stage estão completas
CREATE FUNCTION check_stage_completion(p_flow_id UUID, p_stage INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_total INTEGER;
    v_completed INTEGER;
    v_blocking_incomplete INTEGER;
BEGIN
    -- contar tasks do stage
    SELECT COUNT(*), 
           COUNT(*) FILTER (WHERE status = 'completed'),
           COUNT(*) FILTER (WHERE is_blocking = TRUE AND status != 'completed')
    INTO v_total, v_completed, v_blocking_incomplete
    FROM sales_tasks
    WHERE flow_id = p_flow_id AND stage = p_stage;
    
    -- Só avança se todas bloqueantes estiverem completas
    RETURN (v_blocking_incomplete = 0);
END;
```

### Automação 3: Alertas de Atraso (SLA)

```sql
-- Job: checar SLAs vencidos
SELECT 
    f.id,
    f.current_stage,
    f.stage_1_at,
    EXTRACT(EPOCH FROM (NOW() - f.stage_1_at)) / 3600 as hours_elapsed,
    f.sla_stage_1_hours,
    CASE 
        WHEN EXTRACT(EPOCH FROM (NOW() - f.stage_1_at)) / 3600 > f.sla_stage_1_hours THEN 'VIOLATED'
        WHEN EXTRACT(EPOCH FROM (NOW() - f.stage_1_at)) / 3600 > f.sla_stage_1_hours * 0.8 THEN 'WARNING'
        ELSE 'OK'
    END as sla_status
FROM sales_flows f
WHERE f.current_stage = 1 
  AND f.stage_status = 'active'
  AND f.is_active = TRUE;
```

---

## 🔌 INTEGRAÇÕES

### Integração com Financial Core

```sql
-- ao concluir estágio de contrato:
INSERT INTO financial.accounts_receivable (
    company_id,
    client_id,
    contract_id,
    amount,
    due_date,
    payment_type  -- entrada, intermediario, final
)
SELECT 
    f.company_id,
    f.client_id,
    f.id,
    f.ticket_final * 0.30,  -- 30% entrada
    f.event_date - INTERVAL '30 days',
    'entrada'
FROM sales_flows f
WHERE f.current_stage = 3 AND tasks_completed;
```

### Integração com Event Engine

```sql
-- ao assinar contrato:
INSERT INTO event_engine.events (
    company_id,
    client_id,
    event_date,
    guests_count,
    event_type,
    location,
    budget,
    sales_flow_id
)
SELECT 
    company_id,
    client_id,
    event_date,
    guests_estimate,
    event_type,
    location_venue,
    ticket_final,
    id
FROM sales_flows
WHERE stage_transita_para = 4;
```

### Integração com Decision Engine

```sql
-- priorização automática:
SELECT 
    f.*,
    calculate_priority(
        lead_score := f.lead_score,
        ticket_estimate := f.ticket_estimate,
        days_until_event := f.event_date - CURRENT_DATE,
        source := f.source
    ) as priority_score
FROM sales_flows f
WHERE f.current_stage < 5
ORDER BY priority_score DESC;
```

---

## 📊 MÉTRICAS DO SALES ENGINE

| Métrica | Cálculo | Meta |
|---------|---------|------|
| Conversion Rate Per Stage | Stage N+1 / Stage N | > 40% |
| Avg Time per Stage | AVG(stage_N_at - stage_N-1_at) | Qualif: 2d, Neg: 5d, Cont: 3d, Onb: 7d |
| SLA Compliance | % dentro do prazo | > 85% |
| Pipeline Velocity | Valor / Tempo | > R$ 100K/mês |
| Win Rate | Won / (Won + Lost) | > 35% |
| Avg Deal Size | SUM(ticket_final) / COUNT | > R$ 25K |

---

🎛️ **Sales Engine v1.0 — Processo Comercial Operacional Completo**
