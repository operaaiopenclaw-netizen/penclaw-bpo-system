# SDR AI ENGINE — Orkestra Finance Brain

**Versão:** 1.0  
**Data:** 2026-04-08  
**Tipo:** Sales Development Representative Autônomo  
**Status:** Especificação Completa

---

## 🎯 VISÃO GERAL

SDR IA totalmente autônomo que captura, qualifica e encaminha leads sem intervenção humana.

**Fluxo:**
```
[ManyChat/WhatsApp] → [lead_intake] → [qualification_engine] 
                                           ↓
[lead_scoring] → [decision_logic] → [conversation_flow] 
                                           ↓
    [Alta] → Google Calendar (reunião)    [Média] → Continuar conversa    [Baixa] → Descartar
```

---

## 📥 1. LEAD_INTAKE (Captura de Leads)

### Tabela: lead_intake

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | UUID PK | |
| company_id | UUID FK | Empresa destino (QOpera/Laohana/Robusta) |
| external_id | TEXT | ID da origem (ManyChat user_id) |
| source | ENUM | manychat, whatsapp, instagram, facebook, site, indicacao, evento |
| channel | TEXT | Subcanal específico |
| status | ENUM | new, processing, qualified, disqualified, converted |
| stage | ENUM | intake, qualifying, scored, decided, routed |
| 
| **Dados do Lead** | | |
| lead_name | TEXT | Nome informado |
| lead_email | TEXT | Email (validado) |
| lead_phone | TEXT | Telefone (formatado BR) |
| lead_company | TEXT | Empresa do lead |
| lead_role | TEXT | Cargo |
| 
| **Dados do Evento** | | |
| event_type | TEXT | Tipo de evento (casamento, corporativo, etc) |
| event_date | DATE | Data desejada |
| event_date_flexibility | INTEGER | Flexibilidade em dias |
| guests_estimate | INTEGER | Número estimado de convidados |
| budget_estimate | NUMERIC | Orçamento declarado |
| budget_currency | TEXT | BRL, USD, EUR |
| budget_flexibility | DECIMAL(3,2) | % de margem no orçamento |
| 
| **Localização** | | |
| location_city | TEXT | Cidade |
| location_state | TEXT | Estado |
| location_venue | TEXT | Local já definido? |
| 
| **Contexto** | | |
| urgency_level | INTEGER | 1-5 (auto ou input) |
| decision_makers | INTEGER | Quantos decisores |
| previous_events | BOOLEAN | Já fez eventos antes |
| competitors_mentioned | TEXT[] | Concorrência mencionada |
| special_requirements | TEXT | Necessidades especiais |
| 
| **Meta** | | |
| raw_payload | JSONB | Payload bruto da origem |
| processed_at | TIMESTAMPTZ | Quando processou |
| ai_session_id | UUID | Sessão do agente |
| assigned_sdr_ai | TEXT | Qual instância processou |
| 
| **Timestamps** | | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |
| stale_at | TIMESTAMPTZ | Quando expira se não interagir |

**Índices importantes:**
```sql
CREATE INDEX idx_leads_status ON lead_intake(company_id, status);
CREATE INDEX idx_leads_stage ON lead_intake(company_id, stage);
CREATE INDEX idx_leads_date ON lead_intake(event_date);
CREATE INDEX idx_leads_stale ON lead_intake(stale_at) WHERE status = 'new';
```

---

## 🤖 2. QUALIFICATION_ENGINE (Motor de Qualificação)

### Tabela: qualification_questions (Banco de Perguntas)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | UUID PK | |
| company_id | UUID FK | Qual empresa (ou todas) |
| question_key | TEXT UNIQUE | Identificador (ex: budget_range) |
| question_text | TEXT | Texto da pergunta |
| question_type | ENUM | text, number, choice, date, boolean, range |
| options | JSONB | Opções para choice/range |
| validation_rule | JSONB | Regras de validação |
| is_required | BOOLEAN | Obrigatório? |
| priority | INTEGER | Ordem de perguntas |
| condition_logic | JSONB | Quando fazer esta pergunta |
| category | ENUM | basic, event_specs, budget, logistics, decision |
| tags | TEXT[] | Tags para agrupar |

**Exemplo de Perguntas:**
```json
[
  {
    "key": "guest_count",
    "text": "Quantas pessoas você espera no evento?",
    "type": "number",
    "validation": {"min": 10, "max": 1000},
    "required": true,
    "priority": 10,
    "category": "event_specs"
  },
  {
    "key": "budget_range", 
    "text": "Qual é a faixa de investimento previsto por pessoa?",
    "type": "choice",
    "options": [
      {"value": "经济", "label": "Até R$ 80/pessoa", "score": 1},
      {"value": "标准", "label": "R$ 80-150/pessoa", "score": 2},
      {"value": "高端", "label": "R$ 150-300/pessoa", "score": 3},
      {"value": "奢华", "label": "Acima de R$ 300/pessoa", "score": 4}
    ],
    "required": true
  }
]
```

### Tabela: qualification_responses

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | UUID PK | |
| lead_id | UUID FK | Referência ao lead |
| question_id | UUID FK | Qual pergunta |
| response_value | JSONB | Resposta (qualquer formato) |
| response_text | TEXT | Texto bruto |
| is_valid | BOOLEAN | Passou na validação? |
| validation_errors | TEXT[] | Erros encontrados |
| confidence_score | DECIMAL(3,2) | Confiança (0-1) |
| ai_extracted | BOOLEAN | Extraído por IA? |
| asked_at | TIMESTAMPTZ | Quando perguntou |
| answered_at | TIMESTAMPTZ | Quando respondeu |
| turn_number | INTEGER | Turno da conversa |

### Tabela: qualification_state (Estado da Conversa)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | UUID PK | |
| lead_id | UUID FK | |
| session_id | UUID | Sessão ManyChat/WhatsApp |
| status | ENUM | active, paused, completed, expired |
| questions_asked | UUID[] | IDs já perguntados |
| questions_pending | UUID[] | IDs restantes |
| pending_info | JSONB | O que ainda falta |
| qualification_score | INTEGER | 0-100 |
| is_qualified | BOOLEAN | Qualificado? |
| disqualification_reason | TEXT | Por que não qualificou |
| ready_for_scoring | BOOLEAN | Pronto para pontuar? |
| 
| **Controle** | | |
| max_questions | INTEGER | Limite de perguntas |
| questions_count | INTEGER | Feitas até agora |
| last_interaction_at | TIMESTAMPTZ | última mensagem |
| stale_threshold_minutes | INTEGER | Mins até expirar |
| 
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

---

## 📊 3. LEAD_SCORORING (Pontuação de Leads)

### Tabela: lead_scores

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | UUID PK | |
| lead_id | UUID FK | |
| 
| **Scores Dimensionais** | | |
| score_budget | INTEGER | 0-100 (quanto maior melhor) |
| score_size | INTEGER | 0-100 |
| score_date | INTEGER | 0-100 |
| score_type | INTEGER | 0-100 |
| score_urgency | INTEGER | 0-100 |
| score_decision_power | INTEGER | 0-100 |
| 
| **Score Composto** | | |
| total_score | INTEGER | 0-100 |
| score_tier | ENUM | S (90+), A (70-89), B (50-69), C (<50) |
| 
| **Fatores** | | |
| budget_rating | TEXT | insufficient, tight, good, excellent |
| size_rating | TEXT | too_small, small, good, large |
| date_rating | TEXT | past, too_close, good, future |
| urgency_rating | TEXT | low, medium, high, critical |
| 
| **Recomendação** | | |
| priority_level | ENUM | critical, high, medium, low |
| recommended_action | TEXT | schedule_meeting, continue_engagement, nurture, discard |
| sla_hours | INTEGER | Tempo máximo para resposta |
| 
| **Contexto** | | |
| scored_at | TIMESTAMPTZ | |
| scoring_version | TEXT | Versão do algoritmo |
| ai_confidence | DECIMAL(3,2) | |
| reasons | JSONB | Por que este score |

### Lógica de Scoring

```python
# Budget Score
def score_budget(budget_per_person):
    if budget_per_person < 50:
        return 20, "insufficient", "Orçamento abaixo do mínimo operacional"
    elif budget_per_person < 80:
        return 40, "tight", "Orçamento apertado, margem reduzida"
    elif budget_per_person < 150:
        return 70, "good", "Orçamento saudável"
    elif budget_per_person < 250:
        return 90, "excellent", "Orçamento premium"
    else:
        return 100, "luxury", "Orçamento alto padrão"

# Size Score
def score_size(guest_count):
    if guest_count < 30:
        return 20, "too_small", "Evento muito pequeno, pode não valer a pena"
    elif guest_count < 80:
        return 50, "small", "Tamanho aceitável"
    elif guest_count < 200:
        return 75, "good", "Tamanho ideal"
    elif guest_count < 500:
        return 90, "large", "Evento grande"
    else:
        return 100, "major", "Evento de grande porte"

# Date Score
def score_date(event_date, flexibility_days):
    days_until = (event_date - today).days
    
    if days_until < 0:
        return 0, "past", "Data já passou"
    elif days_until < 15:
        return 30, "too_close", "Data muito próxima, difícil operar"
    elif days_until < 45:
        return 60, "urgent", "Data próxima mas operável"
    elif days_until < 120:
        return 85, "good", "Data ideal para planejamento"
    else:
        # Longe demais pode desistir
        return 60 - (days_until - 120) / 30, "future", "Data distante, pode não converter"

# Peso dos fatores
WEIGHTS = {
    'budget': 0.30,
    'size': 0.25,
    'date': 0.20,
    'type': 0.15,
    'urgency': 0.10
}
```

---

## ⚡ 4. DECISION_LOGIC (Lógica de Decisão)

### Tabela: lead_decisions

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | UUID PK | |
| lead_id | UUID FK | |
| qualification_id | UUID FK | Estado da qualificação |
| score_id | UUID FK | Scores calculados |
| 
| **Decisão** | | |
| priority_level | ENUM | critical, high, medium, low |
| decision_category | ENUM | hot_lead, warm_lead, cold_lead, disqualified |
| action_type | ENUM | schedule_meeting, send_proposal, continue_qualifying, nurture, discard |
| action_subtype | TEXT | Especificação (ex: video_call, phone_call, visit) |
| 
| **Roteamento** | | |
| route_to | UUID | Vendedor/comercial indicado |
| route_to_type | ENUM | sdr_human, account_executive, self_service |
| calendar_event_id | TEXT | ID do evento Google Calendar |
| meeting_scheduled_at | TIMESTAMPTZ | Hora marcada |
| 
| **Mensagem** | | |
| message_template_key | TEXT | Template de resposta |
| message_custom | TEXT | Mensagem personalizada |
| message_language | TEXT | pt, en, es |
| 
| **Execução** | | |
| status | ENUM | pending, executing, completed, failed, cancelled |
| executed_at | TIMESTAMPTZ | Quando executou |
| execution_result | JSONB | Resultado das ações |
| 
| created_at | TIMESTAMPTZ | |

### Regras de Decisão

```yaml
# Regras de Roteamento
rules:
  - name: "Crítico - Reunião Imediata"
    condition: "score >= 85 AND budget_rating IN ['excellent', 'luxury'] AND urgency_rating == 'critical'"
    priority: critical
    action: schedule_meeting
    sla_hours: 2
    route_to: account_executive
    
  - name: "Alto - Agendar Reunião"
    condition: "score >= 70 AND date_rating IN ['good', 'urgent']"
    priority: high
    action: schedule_meeting
    sla_hours: 24
    route_to: sdr_human
    
  - name: "Médio - Continuar Conversa"
    condition: "score >= 50 AND score < 70"
    priority: medium
    action: continue_qualifying
    sla_hours: 72
    route_to: self_service
    
  - name: "Baixo - Nutrir"
    condition: "score >= 30 AND score < 50"
    priority: low
    action: nurture
    sla_hours: 168
    route_to: marketing_automation
    
  - name: "Descartar"
    condition: "score < 30 OR budget_rating == 'insufficient'"
    priority: none
    action: discard
    sla_hours: null
    route_to: null
```

---

## 💬 5. CONVERSATION_FLOW (Fluxo Conversacional)

### Tabela: conversation_sessions

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | UUID PK | |
| lead_id | UUID FK | |
| platform | ENUM | manychat, whatsapp, instagram |
| external_session_id | TEXT | ID da plataforma |
| 
| **Estado** | | |
| status | ENUM | active, paused, completed, error |
| current_node | TEXT | Nó atual do fluxo |
| context | JSONB | Variáveis de contexto |
| memory | JSONB | Memória da conversa |
| 
| **Controle** | | |
| turn_count | INTEGER | Quantas interações |
| last_message_at | TIMESTAMPTZ | |
| user_inactive_minutes | INTEGER | Minutos desde última resposta |
| escalation_triggered | BOOLEAN | Subiu para humano? |
| 
| created_at | TIMESTAMPTZ | |
| ended_at | TIMESTAMPTZ | |

### Tabela: conversation_nodes (Fluxo)

Nós do fluxo conversacional:

```yaml
nodes:
  # Início
  - id: welcome
    type: message
    text: "Olá! Sou o assistente da Orkestra. Vi que você tem interesse em um evento. Posso ajudar com algumas perguntas rápidas?"
    next: confirm_interest
    
  - id: confirm_interest
    type: wait_input
    timeout: 300  # 5 minutos
    on_yes: ask_event_type
    on_no: end_not_interested
    on_timeout: send_reminder
    
  # Coleta de dados
  - id: ask_event_type
    type: question
    question_ref: event_type
    validation: required
    on_valid: ask_event_date
    on_invalid: clarify_event_type
    
  - id: ask_event_date
    type: question
    question_ref: event_date
    validation:
      - not_past: true
      - min_days_ahead: 14
    on_valid: ask_guest_count
    on_invalid: explain_date_requirement
    
  - id: ask_guest_count
    type: question
    question_ref: guest_count
    validation:
      - min: 10
      - max: 1000
    on_valid: ask_budget_per_person
    
  - id: ask_budget_per_person
    type: question
    question_ref: budget_range
    adaptive: true  # Pergunta diferente baseado em event_type
    on_valid: process_qualification
    
  # Processamento
  - id: process_qualification
    type: ai_action
    action: evaluate_lead
    on_complete: route_based_on_score
    
  # Rotas
  - id: route_hot_lead
    type: decision
    condition: "score >= 70"
    actions:
      - send_message: "Perfeito! Você parece ter um evento interessante."
      - send_message: "Vou conectar você com um especialista que pode agendar uma reunião."
      - schedule_meeting: {priority: high}
      - update_pipeline: {stage: qualificacao}
      
  - id: route_warm_lead
    type: decision
    condition: "score >= 50 AND score < 70"
    actions:
      - send_message: "Ótimo! Tenho algumas opções que podem servir."
      - send_catalog: {category: budget_based}
      - ask: "Gostaria de ver alguns exemplos de eventos similares?"
      
  - id: route_cold_lead
    type: decision
    condition: "score < 50"
    actions:
      - send_message: "Entendi. Tenho algumas ideias que podem ajudar."
      - send_nurture_content: {type: inspiration}
      - set_reminder: {days: 7, action: re_engagement}
```

### Adaptive Logic (Lógica Adaptativa)

```python
def adapt_question_based_on_context(context):
    """Adapta pergunta baseada no contexto"""
    
    if context['event_type'] == 'casamento':
        return {
            'budget_question': 'Qual é a faixa de investimento por convidado que vocês planejam?',
            'tone': 'warm_ personal',
            'follow_up': 'Que momento especial! Onde será a cerimônia?'
        }
    elif context['event_type'] == 'corporate':
        return {
            'budget_question': 'Qual o investimento aprovado por participante?',
            'tone': 'professional',
            'follow_up': 'Qual o objetivo principal do evento?'
        }
    
    # Adptar baseado em budget
    if context['budget_per_person'] > 200:
        return {'suggest': 'premium_options', 'elevator_pitch': 'exclusive'}
    else:
        return {'suggest': 'smart_choices', 'elevator_pitch': 'value'}
```

---

## 🔌 6. INTEGRAÇÕES

### ManyChat Integration

```javascript
// Webhook ManyChat → Orkestra
app.post('/webhook/manychat', async (req, res) => {
    const { user_id, page_id, message, custom_fields } = req.body;
    
    // Criar ou atualizar lead
    const lead = await leadIntake.upsert({
        external_id: user_id,
        source: 'manychat',
        channel: `facebook:${page_id}`,
        raw_payload: req.body,
        lead_name: custom_fields.full_name,
        lead_email: custom_fields.email,
        // ... mapear outros campos
    });
    
    // Iniciar/continuar conversa
    const response = await conversationEngine.process({
        lead_id: lead.id,
        message: message.text,
        platform: 'manychat'
    });
    
    // Responder via ManyChat
    await manychatAPI.sendMessage(user_id, {
        messages: response.messages,
        actions: response.actions
    });
    
    res.json({ status: 'ok' });
});
```

### WhatsApp Integration

```javascript
// Twilio WhatsApp webhook
app.post('/webhook/whatsapp', async (req, res) => {
    const { From, Body, MediaUrl0 } = req.body;
    const phone = From.replace('whatsapp:', '');
    
    // Process similar ao ManyChat
    const lead = await leadIntake.findOrCreate({ phone });
    const response = await conversationEngine.process({
        lead_id: lead.id,
        message: Body,
        platform: 'whatsapp'
    });
    
    await twilio.messages.create({
        from: `whatsapp:${TWILIO_NUMBER}`,
        to: From,
        body: response.text
    });
});
```

### Google Calendar Integration

```python
from google.oauth2 import service_account
from googleapiclient.discovery import build

async def schedule_meeting(lead, decision):
    """Agendar reunião no Google Calendar"""
    
    # Determinar melhor horário
    suggested_slots = find_available_slots(
        duration_minutes=30,
        business_hours=(9, 18),
        timezone=lead.location_timezone or 'America/Sao_Paulo',
        lead_preference=lead.preferred_time
    )
    
    # Criar evento
    event = {
        'summary': f'Reunião Orkestra - {lead.lead_name}',
        'description': f'''Lead: {lead.lead_name}
Evento: {lead.event_type}
Pessoas: {lead.guests_estimate}
Orçamento: {lead.budget_estimate}
Score: {lead.score}

Link qualificação: https://orkestra.ai/qual/{lead.id}
''',
        'start': {'dateTime': suggested_slots[0].isoformat()},
        'end': {'dateTime': (suggested_slots[0] + timedelta(minutes=30)).isoformat()},
        'attendees': [
            {'email': lead.lead_email, 'displayName': lead.lead_name},
            # Adicionar vendedor da empresa
            {'email': decision.route_to_email}
        ],
        'conferenceData': {
            'createRequest': {
                'requestId': str(uuid.uuid4()),
                'conferenceSolutionKey': {'type': 'hangoutsMeet'}
            }
        }
    }
    
    calendar = build('calendar', 'v3', credentials=google_creds)
    created = calendar.events().insert(
        calendarId=decision.route_to_calendar_id,
        body=event,
        conferenceDataVersion=1
    ).execute()
    
    return created
```

### sales_pipeline Integration

```python
async def create_pipeline_opportunity(lead, decision):
    """Criar oportunidade após reunião agendada"""
    
    opportunity = await db.execute("""
        INSERT INTO sales_pipeline (
            company_id, opportunity_id, client_name, client_email,
            client_phone, event_type, event_date, guests_estimate,
            budget_estimate, current_stage, probability, expected_value,
            assigned_to, total_value, margin_projected
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
        RETURNING *
    """,
        lead.company_id,
        f"OPP-{datetime.now():%Y%m%d}-{str(uuid.uuid4())[:4].upper()}",
        lead.lead_name,
        lead.lead_email,
        lead.lead_phone,
        lead.event_type,
        lead.event_date,
        lead.guests_estimate,
        lead.budget_estimate,
        'qualificacao',  # Stage
        60,              # Probability
        lead.budget_estimate * (lead.guests_estimate or 100) * 0.6,  # Expected
        decision.route_to,  # Assigned
        lead.budget_estimate * (lead.guests_estimate or 100),  # Total
        decision.calculated_margin
    )
    
    return opportunity
```

---

## 📈 MÉTRICAS SDR

| Métrica | Fórmula | Meta |
|---------|---------|------|
| Lead Velocity | Leads processados / dia | > 20 |
| Qualification Rate | Qualificados / Total × 100 | > 40% |
| Scoring Accuracy | Acurácia predição | > 75% |
| Meeting Conversion | Reuniões agendadas / Qualificados | > 30% |
| Response Time | AVG(tempo resposta) | < 2 min |
| Escalation Rate | Subiu humano / Total | < 15% |

---

## 🎯 REGRAS DE OURO

1. **Nunca depender de humano** — SDR toma decisões autônomas
2. **SLA de 2 minutos** — primeira resposta sempre automática
3. **Escalation inteligente** — só subir quando realmente necessário
4. **Aprendizado contínuo** — ajustar scores baseado em conversões
5. **Multi-canal** — responder no mesmo canal (Não "mande WhatsApp")
6. **Fallback gentil** — se não entender, perguntar de novo

---

🎛️ **SDR AI Engine v1.0 — Especificação Completa**
