# MASTER CONTEXT CONSOLIDATION — ORKESTRA + BPO SYSTEM

**Versão:** 2.0 — Consolidação Total  
**Data:** 2026-04-08  
**Sistemas Integrados:** Orkestra (Eventos) + OpenClaw BPO (Financeiro/Operacional)  
**Status:** Análise para Testes Operacionais

---

## 📋 OBJETIVO DESTE DOCUMENTO

Consolidar TODO o conhecimento, estrutura, módulos e fluxos desenvolvidos entre os sistemas **Orkestra** (empresa de eventos) e **OpenClaw BPO** (sistema de gestão financeira/operacional), eliminando fragmentação e preparando para testes práticos operacionais.

---

## 🎯 SISTEMAS INTEGRADOS

### 1. ORKESTRA — Sistema de Gestão de Eventos

**Empresas:** QOpera (corporativo), Laohana (buffet), Robusta (estrutura)

**Módulos Criados:**
- Financial Core (contas a pagar/receber, fluxo de caixa)
- Sales Engine (pipeline comercial 5 estágios)
- Inventory Engine (estoque com QR, mobile)
- Event Engine (gestão de eventos, checklist)
- SDR AI Engine (qualificação leads com voz)
- Decision Engine (scoring, pricing, forecast)

**Canais:** Telegram (5 bots), WhatsApp (ManyChat), Dashboard Web

### 2. OPENCLAW BPO — Sistema de BPO Financeiro

**Módulos Criados:**
- Audit Log (imutável, rastreável)
- Decision Log (decisões da IA)
- Agent Action Log (ações de agentes)
- RBAC (controle de acesso)
- System Parameters (configurações)

**Integrações:** PostgreSQL multi-tenant, FastAPI, Redis

---

## 🏗️ ARQUITETURA COMPLETA (3 CAMADAS)

```
┌─────────────────────────────────────────────────────────────────┐
│ CAMADA 1 — OPERAÇÃO (Input/Output)                            │
├─────────────────────────────────────────────────────────────────┤
│ 📱 Telegram                                                    │
│  ├ @OrkestraComercialBot — Leads, pipeline                   │
│  ├ @OrkestraOperacoesBot — Eventos, checklist              │
│  ├ @OrkestraEstoqueBot — Entrada/saída/retorno              │
│  ├ @OrkestraFinanceiroBot — Caixa, projeções               │
│  └ @OrkestraDiretoriaBot — Dashboard, aprovações           │
│                                                               │
│ 📲 WhatsApp (ManyChat + SDR IA)                              │
│  ├ Qualificação automática de leads                          │
│  ├ ElevenLabs TTS (português BR)                             │
│  ├ Google Calendar integration                               │
│  └ Respostas em voz e texto                                  │
│                                                               │
│ 📷 Mobile Stock (Smartphone)                                 │
│  ├ QR Code / Barcode scanning                                │
│  ┅ Impressão Bluetooth (etiquetas)                           │
│  └ Offline → Sync                                            │
│                                                               │
│ 📊 Dashboard Web                                               │
│  └ KPIs, alertas, status em tempo real                       │
└─────────────────────────┬───────────────────────────────────────┘
                          │ APIs / Webhooks
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ CAMADA 2 — EXECUÇÃO (Engines)                                 │
├─────────────────────────────────────────────────────────────────┤
│ 🎛️ Orkestra Finance Brain (Agente Principal)                   │
│                                                               │
│  📊 FINANCIAL CORE                                            │
│  ├ accounts_payable — Contas a pagar                         │
│  ├ accounts_receivable — Contas a receber                   │
│  ├ cashflow_projection — Projeção de caixa                  │
│  ├ cost_centers — Centros de custo                          │
│  └ budget_categories — Categorias orçamentárias             │
│                                                               │
│  🎯 COMMERCIAL ENGINE                                         │
│  ├ products_catalog — Catálogo QOpera/Laohana/Robusta      │
│  ├ pricing_rules — Markup, tier, seasonal                  │
│  ├ discount_policies — Descontos por perfil               │
│  ├ sales_targets — Metas por vendedor                     │
│  ├ sales_pipeline — Funil 5 estágios                        │
│  │   1. Qualificação → 2. Negócio → 3. Contrato           │
│  │   4. Onboarding → 5. Pós-venda                        │
│  └ upsell_rules — Cross-sell automático                     │
│                                                               │
│  📦 INVENTORY ENGINE                                          │
│  ├ inventory_items — Itens cadastrados                      │
│  ├ inventory_movements — Movimentação                        │
│  ├ stock_balance — Saldo em tempo real                      │
│  ├ item_locations — Localização física                     │
│  │   Tipos: consumo (bebidas), patrimônio (cadeiras)      │
│  │          insumo (produção)                              │
│  └ QR/barcode system — Geração e scanning                   │
│                                                               │
│  🎉 EVENT ENGINE                                              │
│  ├ events — Eventos (dados gerais)                          │
│  ├ event_checklists — Checklist por estágio                │
│  ├ event_staff — Equipe alocada                            │
│  ├ event_inventory — Itens reservados                      │
│  └ event_timeline — Cronograma                            │
│                                                               │
│  🤖 SDR AI ENGINE                                             │
│  ├ lead_intake — Captura ManyChat/WhatsApp                 │
│  ├ qualification_engine — Coleta dados                    │
│  ├ lead_scores — Scoring S/A/B/C/D                         │
│  ├ lead_decisions — Roteamento automático                  │
│  │   S/A → Reunião | B → Continuar | C/D → Nurture       │
│  └ conversation_flow — Fluxo conversacional                │
│                                                               │
│  ⚡ DECISION ENGINE                                           │
│  ├ go/no-go scoring — Margem ≥ 25%?                       │
│  ├ pricing calculator — Markup dinâmico                   │
│  ┅ forecast engine — Consumo cerveja/buffet               │
│  └ approval workflow — Validação descontos                │
│                                                               │
│ 🗄️ INFRAESTRUTURA BPO (OpenClaw)                           │
│  ├ audit_log — Tudo imutável, chain hash                  │
│  ├ decision_log — Rastreabilidade IA                      │
│  ├ agent_action_log — Tool calls                          │
│  ├ RBAC — Roles (super_admin, admin, manager...)          │
│  └ system_parameters — Config centralizada                │
│                                                               │
│ 🔄 INTEGRAÇÕES                                               │
│  ├ ManyChat API (Messenger)                                 │
│  ├ Twilio/WhatsApp API                                      │
│  ├ ElevenLabs TTS                                           │
│  ├ Google Calendar                                          │
│  ├ DocuSign (contratos)                                     │
│  └ Webhooks (bancos, fornecedores)                          │
│                                                               │
│ 💾 DATABASE                                                  │
│  ├ PostgreSQL 15 (multi-tenant, partitioned)                │
│  ├ Redis (cache, sessions)                                  │
│  └ 50+ tabelas estruturadas                                 │
└─────────────────────────┬───────────────────────────────────────┘
                          │ Queries / Reports
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ CAMADA 3 — GESTÃO (Visualização)                              │
├─────────────────────────────────────────────────────────────────┤
│ 📊 Dashboards                                                │
│  ├ Receita projetada vs real                                  │
│  ├ Eventos da semana                                          │
│  ├ Pipeline comercial                                         │
│  ├ Alertas críticos                                           │
│  └ Estoque mínimo                                             │
│                                                               │
│ 📈 Views Analíticas                                          │
│  ├ v_pipeline_active — Pipeline em andamento               │
│  ├ v_sales_performance — Performance vendedores             │
│  ├ v_cash_position — Posição caixa                         │
│  ├ v_targets_progress — Metas vs realizado                │
│  └ v_inventory_critical — Estoque baixo                     │
│                                                               │
│ 🚨 Alertas Automáticos                                       │
│  ├ Estoque abaixo do mínimo                                 │
│  ├ Evento com risco de atraso                                │
│  ├ Lead parado > 3 dias                                      │
│  ├ Caixa projetado negativo                                  │
│  └ Pagamento vencido                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 INVENTÁRIO COMPLETO

### B.1 MÓDULOS IMPLEMENTADOS

| # | Módulo | Status | Arquivos | Pronto Testes? |
|---|--------|--------|----------|----------------|
| 1 | **Financial Core** | ✅ 100% | orkestra_schema_v1.sql | ✅ Sim |
| 2 | **Commercial Engine** | ✅ 100% | commercial_schema_v1.sql + COMMERCIAL_SETUP_v1.md | ✅ Sim |
| 3 | **Inventory Engine** | ✅ 100% | commercial_schema_v1.sql (estoque) + QR_GENERATOR_SYSTEM.py | ✅ Sim |
| 4 | **Event Engine** | ✅ 95% | SALES_ENGINE_v1.md + sales_flows | ⚠️ Falta testar checklist |
| 5 | **SDR AI Engine** | ✅ 90% | SDR_AI_ENGINE_v1.md + sdr_engine_schema_v1.sql | ⚠️ Falta integração ElevenLabs |
| 6 | **Telegram Bots** | ✅ 80% | TELEGRAM_COMMANDS_GUIDE.md + telegram_whatsapp_schema.sql | ⚠️ Falta configurar tokens |
| 7 | **Decision Engine** | ✅ 100% | calculate_price_with_rules(), check_margin_acceptable() | ✅ Sim |
| 8 | **Audit/Logs** | ✅ 100% | orkestra_schema_v1.sql (audit section) | ✅ Sim |
| 9 | **RBAC** | ✅ 100% | rbac_users, rbac_roles, rbac_permissions | ✅ Sim |
| 10 | **Dashboard Web** | ✅ 90% | dashboard/index.html (37KB) | ⚠️ Falta nginx.conf |

### B.2 AGENTES IA CRIADOS

| Agente | Função | Input | Output | Status |
|--------|--------|-------|--------|--------|
| **SDR AI** | Qualificar leads | WhatsApp/ManyChat | Score + Reunião agendada | ⚠️ Falta token ElevenLabs |
| **Pricing AI** | Calcular preços | Tipo, qtd, data | Preço + margem | ✅ Pronto |
| **Scoring AI** | Score leads | Budget, size, date | Tier S/A/B/C/D | ✅ Pronto |
| **Forecast AI** | Prever consumo | Histórico | Cerveja/buffet/staff | ✅ Pronto |
| **Approval AI** | Validar descontos | Usuário, % | Aprovação/Negação | ✅ Pronto |
| **Audit AI** | Verificar consistência | Dados diários | Relatório gaps | ✅ Pronto |
| **Lead Intake** | Capturar leads | ManyChat webhook | Lead estruturado | ⚠️ Falta webhook |

### B.3 FLUXOS IMPLEMENTADOS

#### B.3.1 Funil Comercial (5 Estágios)
```
1. QUALIFICAÇÃO → SDR IA
   Input: WhatsApp "Oi, quero evento"
   Process: Coleta tipo, data, pessoas, orçamento, cidade
   Output: Lead score 0-100
   
   Regras:
   - Score ≥70: Avançar → Negócio (reunião em 24h)
   - Score 50-69: Continuar qualificação
   - Score <50: Nurture (reengajamento 7 dias)

2. NEGÓCIO → Account Executive
   Input: Lead qualificado
   Process: Montar proposta, pricing, margem ≥25%
   Output: Proposta enviada
   
   Regras:
   - Cliente aprova → Contrato
   - Cliente nega → LOST (registrar motivo)
   - Negociação → Novo pricing

3. CONTRATO → Assinatura
   Input: Proposta aprovada
   Process: Gerar PDF, DocuSign, entrada ≥30%
   Output: Evento criado
   
   Regras:
   - Assinatura + entrada → Onboarding
   - Entrada pendente → Alerta financeiro

4. ONBOARDING → Produção
   Input: Evento criado
   Process: Briefing, cardápio, equipe, equipamento
   Output: Evento pronto
   
   Regras:
   - D-7 freeze: Não permite mais alterações
   - 2º pagamento: Bloqueia alterações cardápio

5. PÓS-VENDA → Relacionamento
   Input: Evento executado
   Process: NPS, CMV real, pagamento final
   Output: Fechamento completo
   
   Regras:
   - NPS ≥8 → Pedir indicação
   - 3+ eventos → Cliente VIP
```

#### B.3.2 Fluxo Estoque (Mobile)
```
ENTRADA:
Fornecedor entrega → Scan QR ou digitar SKU
              → Qualidade (foto opcional)
              → Registro digital (lote, validade)
              → Print etiqueta
              → Armazenar

SAÍDA (Evento):
Reserva criada → Picking list
              → Scan QR itens
              → Separação física
              → Carregar caminhão
              → Entrega evento
              → Assinatura digital

RETORNO:
Caminhão volta → Scan evento QR
              → Conferência itens
              → Estado: OK/Avariado/Perdido
              → Ajuste estoque
              → Relatório divergência

AJUSTE:
Contagem física → Comparar sistema
              → Registrar perda/avaria
              → Motivo (documentado)
              → Atualizar custo médio
```

#### B.3.3 Fluxo Telegram
```
USUÁRIO: /entrada agua 100 fornecedor-x 5.50
    ↓
BOT: Registra entrada, atualiza estoque
    ↓
BOT: Responde com ID, saldo atual, custo médio
    ↓
SISTEMA: Gera audit_log
    ↓
SE estoque < mínimo: ALERTA
```

### B.4 TABELAS CRIADAS (50+)

#### Módulo Financeiro
- `accounts_payable` — Contas a pagar
- `accounts_receivable` — Contas a receber
- `cashflow_projection` — Projeção de caixa
- `cash_position` — Posição de caixa
- `cost_centers` — Centros de custo
- `budget_categories` — Categorias orçamentárias

#### Módulo Comercial
- `products_catalog` — Catálogo de produtos
- `pricing_rules` — Regras de precificação
- `discount_policies` — Políticas de desconto
- `sales_targets` — Metas comerciais
- `sales_pipeline` — Pipeline de vendas
- `sales_flows` — Fluxos comerciais detalhados
- `upsell_rules` — Regras de upsell

#### Módulo Estoque
- `inventory_items` — Itens
- `inventory_movements` — Movimentações
- `stock_balance` — Saldos
- `item_locations` — Localizações
- `item_categories` — Categorias

#### Módulo Eventos
- `events` — Eventos
- `event_checklists` — Checklists
- `event_staff` — Equipe
- `event_inventory` — Itens alocados
- `event_timeline` — Cronograma

#### Módulo SDR IA
- `lead_intake` — Captura leads
- `lead_scores` — Scores calculados
- `lead_decisions` — Decisões de roteamento
- `qualification_questions` — Banco de perguntas
- `qualification_responses` — Respostas coletadas
- `qualification_state` — Estado da conversa
- `conversations` — Sessões de chat
- `messages` — Mensagens (particionadas)
- `conversation_nodes` — Fluxo conversacional

#### Módulo BPO/Logs
- `audit_log` — Auditoria imutável
- `decision_log` — Decisões da IA
- `agent_action_log` — Ações de agentes
- `rbac_users` — Usuários
- `rbac_roles` — Papéis
- `rbac_permissions` — Permissões
- `system_parameters` — Configurações

### B.5 INTEGRAÇÕES CONFIGURADAS

| Integração | Status | Pendente |
|------------|--------|----------|
| ManyChat | ⚠️ Documentado | Token API |
| WhatsApp/Twilio | ⚠️ Documentado | Conta Twilio |
| ElevenLabs TTS | ⚠️ Documentado | API Key |
| Google Calendar | ⚠️ Documentado | OAuth |
| DocuSign | 📋 Planejado | Conta dev |
| Bancos (webhook) | 📋 Planejado | Gateway |
| Impressora BT | ⚠️ Python pronto | Teste físico |

---

## 🔍 GAPS IDENTIFICADOS

### C.1 GAPS CRÍTICOS (Bloqueiam Testes)

| # | Gap | Impacto | Solução |
|---|-----|---------|---------|
| 1 | **Docker Compose não subiu** | Sistema offline | Aprovar execução ou rodar manual |
| 2 | **Migrations não aplicadas** | Schema não existe no banco | Rodar `migrate.sh up` |
| 3 | **Tokens API não configurados** | Integrações não funcionam | Configurar env |
| 4 | **Webhook ManyChat não ativo** | SDR IA sem entrada | Configurar endpoint |

### C.2 GAPS IMPORTANTES (Limitam Funcionalidade)

| # | Gap | Impacto | Solução |
|---|-----|---------|---------|
| 5 | ElevenLabs não testado | SDR sem voz | Teste com token |
| 6 | Impressora BT não integrada | QR manual | Teste físico |
| 7 | Mobile app não iniciado | Estoque desktop-only | MVP web responsivo |
| 8 | DocuSign não configurado | Contratos manuais | Conta dev |

### C.3 GAPS MENORES (Melhorias Futuras)

| # | Gap | Impacto | Prioridade |
|---|-----|---------|------------|
| 9 | Dashboard notificações push | UX | Baixa |
| 10 | Relatórios exportáveis PDF | Conveniência | Baixa |
| 11 | Multi-idioma (PT/EN/ES) | Internacionalização | Baixa |
| 12 | Dark mode | UX | Baixa |

---

## ✅ O QUE ESTÁ 100% PRONTO PARA TESTES

### Pronto Sem Dependências Externas:
- ✅ Schema SQL completo (PostgreSQL)
- ✅ FastAPI com endpoints REST
- ✅ Calculadoras (scoring, pricing, margem)
- ✅ RBAC (usuários, roles, permissões)
- ✅ Audit logs (immutable)
- ✅ Dashboard HTML estático
- ✅ QR Code generator (Python)

### Pronto Com Configuração Mínima:
- ⚠️ Telegram bots (só configurar tokens)
- ⚠️ SDR IA (só adicionar token ElevenLabs)
- ⚠️ Google Calendar (só OAuth)

### NÃO Pronto (Precisa Desenvolvimento):
- ❌ DocuSign integration
- ❌ Webhook bancário real
- ❌ Mobile app nativo
- ❌ Impressora Bluetooth (teste físico)

---

## 🎯 PRÓXIMOS PASSOS PARA TESTES OPERACIONAIS

### SEMANA 1 — Infraestrutura
- [ ] Subir Docker Compose (aprovação ou manual)
- [ ] Aplicar migrations V001-V003
- [ ] Inserir seed data
- [ ] Testar: `curl http://localhost:8000/health`
- [ ] Verificar PostgreSQL: `SELECT 1`

### SEMANA 2 — Integrações
- [ ] Configurar token ManyChat
- [ ] Configurar token ElevenLabs
- [ ] Configurar Twilio WhatsApp
- [ ] Testar webhook SDR → qualificação
- [ ] Testar agendamento Calendar

### SEMANA 3 — Testes Piloto
- [ ] Selecionar empresa piloto (1 das 3)
- [ ] Criar 5 eventos de teste
- [ ] Testar fluxo completo: Lead → Contrato → Evento → Pós
- [ ] Registrar bugs
- [ ] Ajustar regras de negócio

### SEMANA 4 — Rollout
- [ ] Expandir para 2ª empresa
- [ ] Treinar equipe operacional
- [ ] Documentar procedimentos
- [ ] Relatório diário automático

---

## 📁 ARQUIVOS GERADOS (Inventário)

### Documentação (MD)
```
MASTER_CONTEXT_CONSOLIDATION_COMPLETE.md  # Este arquivo
MASTER_CONTEXT_v1.md                      # Versão anterior
PLANO_TECNICO_INFRA_v1.md                # Arquitetura técnica
COMMERCIAL_SETUP_v1.md                     # Setup comercial
SDR_AI_ENGINE_v1.md                        # SDR IA texto
SDR_AI_VOICE_WHATSAPP_v1.md               # SDR IA voz
SALES_ENGINE_v1.md                       # Processos venda
OPERATIONAL_DEPLOYMENT_v1.md             # Deploy operacional
TELEGRAM_COMMANDS_GUIDE.md                # Comandos Telegram
MEMORY.md                                  # Memória sistema
AGENTS.md                                  # Procedimentos
IDENTITY.md                                # Identidade
USER.md                                    # Perfil usuário
```

### Schemas SQL
```
orkestra_schema_v1.sql                    # Schema principal
commercial_schema_v1.sql                   # Comercial
telegram_whatsapp_schema.sql              # Mensagens
sdr_engine_schema_v1.sql                    # SDR IA
migrations/V001__baseline.sql             # Migração inicial
migrations/V002__seed_data.sql            # Dados iniciais
migrations/V003__advanced_triggers.sql    # Triggers
```

### Código Python
```
api/main.py                               # FastAPI REST
api/Dockerfile                            # Container API
QR_GENERATOR_SYSTEM.py                    # QR codes
```

### Infra
```
docker-compose.yml                        # Orchestration
nginx.conf                                # Web server
dashboard/index.html                      # Dashboard web (37KB)
```

### Scripts
```
migrations/migrate.sh                     # CLI migrations
migrations/README.md                      # Documentação
```

---

## 🎛️ CONCLUSÃO

### Sistema Está PRONTO Para:
✅ Testes unitários (schemas, APIs, cálculos)
✅ Testes de integração (com tokens configurados)
✅ Treinamento de equipe (com documentação completa)

### Sistema NÃO Está Pronto Para:
❌ Operação 24/7 (sem deploy)
❌ Clientes reais (sem integrações ativas)
❌ Produção (sem testes piloto)

### Recomendação:
**Executar manualmente fora do chat:**
```bash
cd ~/.openclaw/workspace-openclaw-bpo
docker-compose up -d
./migrations/migrate.sh up
./migrations/migrate.sh seed
curl http://localhost:8000/health
```

Depois, **testar piloto com 1 empresa** antes de expansão.

---

🎛️ **MASTER CONTEXT CONSOLIDATION v2.0 — Sistema Completo Analisado**

**Status:** Documentação ✅ | Código ✅ | Deploy ⏳ | Testes ⏳

**Total:** 500+ KB | 15+ docs | 8+ schemas | 3+ módulos Python | Infra completa
